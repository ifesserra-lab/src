#!/usr/bin/env bash
#
# Atualização semanal do painel de Extensão — SRC/Ifes Campus Serra.
#
# Roda o pipeline COMPLETO do ETL (raspagem + IA + consolidação + export JSON)
# LOCALMENTE — porque depende de credenciais (login do SRC, chave Mistral) e dos
# dados brutos que NÃO ficam no repositório. Depois commita o JSON atualizado em
# docs/api e dá push na main; o GitHub Actions (pages-astro.yml) rebuilda o site
# Astro e publica no GitHub Pages.
#
# O agendamento de DOMINGO em produção é feito no CI (.github/workflows/
# atualizar.yml, com as credenciais como GitHub Secrets). Use ESTE script para
# rodar localmente quando precisar atualizar TAMBÉM as seções que dependem dos
# formados (jornada, comunidade, FORPROEX) — cujos .xlsx (PII) só existem aqui.
#
# Uso manual:  bash scripts/atualizar.sh
# Variáveis:   SRC_SKIP_SCRAPE=1  → pula raspagem/IA, só reexporta e publica
#              SRC_NO_PUSH=1      → gera tudo mas não commita/push (teste)

set -Eeuo pipefail

# ---- localização (o script funciona de qualquer cwd; launchd tem cwd '/') ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO"

# PATH mínimo para launchd (que roda com ambiente enxuto): git, node, brew bins.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

VENV="$REPO/.venv/bin"
LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/atualizar.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }
falha() { log "ERRO na etapa: $1 — abortando SEM publicar."; exit 1; }

log "===== início da atualização semanal ====="

if [ ! -x "$VENV/src-etl-export" ]; then
  log "venv não encontrado em $VENV — rode: python -m venv .venv && .venv/bin/pip install -e ."
  exit 1
fi

# ---- git: parte da main limpa e atualizada ----
git switch main            >>"$LOG" 2>&1 || falha "git switch main"
git pull --ff-only origin main >>"$LOG" 2>&1 || log "aviso: git pull falhou (seguindo com local)"

# ---- pipeline do ETL ----
if [ "${SRC_SKIP_SCRAPE:-0}" != "1" ]; then
  log "1/6 raspando ações públicas (Playwright)…"
  "$VENV/src-etl" --campus Serra --out data --workers 4 >>"$LOG" 2>&1 || falha "src-etl (ações)"

  log "2/6 raspando participações (login)…"
  "$VENV/src-etl-part" --from-index data/serra/_index.json --out data/participacoes --workers 3 >>"$LOG" 2>&1 || falha "src-etl-part"

  log "3/6 enriquecendo categorias (IA/Mistral)…"
  "$VENV/src-etl-enrich" --acoes data/serra --min-conf 0.6 >>"$LOG" 2>&1 || falha "src-etl-enrich"

  log "4/6 consolidando…"
  "$VENV/src-etl-consolidate" --out data/serra_consolidado.json >>"$LOG" 2>&1 || falha "src-etl-consolidate"

  log "5/6 vínculos (programas guarda-chuva)…"
  "$VENV/src-etl-vinculadas" --acoes data/serra >>"$LOG" 2>&1 || falha "src-etl-vinculadas"
else
  log "SRC_SKIP_SCRAPE=1 — pulando raspagem/IA; reexportando do consolidado atual."
fi

log "6/6 exportando API JSON (docs/api)…"
"$VENV/src-etl-export" \
  --consolidado data/serra_consolidado.json \
  --acoes data/serra --part data/participacoes --formandos data/formandos \
  --out docs >>"$LOG" 2>&1 || falha "src-etl-export"

# ---- publicar: commit + push do JSON → dispara o deploy Astro no CI ----
git add docs/api docs/llms.txt >>"$LOG" 2>&1 || true
if git diff --cached --quiet; then
  log "nenhuma mudança nos dados — nada a publicar."
  log "===== fim (sem mudanças) ====="
  exit 0
fi

if [ "${SRC_NO_PUSH:-0}" = "1" ]; then
  log "SRC_NO_PUSH=1 — mudanças preparadas mas NÃO commitadas. Rode 'git status'."
  exit 0
fi

git commit -q -m "chore(data): atualização semanal automática do painel" >>"$LOG" 2>&1 || falha "git commit"
git push origin main >>"$LOG" 2>&1 || falha "git push"
log "publicado: push na main → GitHub Actions rebuilda e publica o site Astro."
log "===== fim (publicado) ====="
