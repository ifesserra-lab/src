#!/usr/bin/env bash
#
# PURGE de PII do histórico do git (DESTRUTIVO E IRREVERSÍVEL).
#
# Remove de TODO o histórico os diretórios de backup que contêm PII
# (CPF + Nome de alunos em participações/formados):
#     data_backup_20260718_092219/
#     data_backup_recoleta_111507/
#
# Trabalha num CLONE-MIRROR isolado (não toca no teu repositório de trabalho até
# você re-clonar). Reescreve todos os SHAs e faz FORCE-PUSH — quebra clones/PRs
# existentes. Requer git-filter-repo (brew install git-filter-repo).
#
# >>> LEIA ANTES DE RODAR <<<
#   1. O repo é PÚBLICO: os dados já expostos NÃO voltam atrás. ROTACIONE a senha
#      do SRC e a chave Mistral ANTES/DEPOIS — o purge só reduz exposição futura.
#   2. Avise quem tem clone (todos precisam re-clonar; rebases quebram).
#   3. PRs antigos e caches do GitHub podem reter os blobs: após o push, abra um
#      ticket no GitHub Support pedindo limpeza de refs/caches (ex.: refs/pull/*).
#   4. Faça um backup do mirror antes (o script guarda em .git-mirror-backup).
#
# Uso:  bash scripts/purge-pii-history.sh
#       (pede confirmação explícita antes do force-push)

set -Eeuo pipefail

PATHS=(data_backup_20260718_092219 data_backup_recoleta_111507)
REPO_URL="$(git -C "$(dirname "${BASH_SOURCE[0]}")/.." remote get-url origin)"
WORK="$(mktemp -d)/src-purge"
MIRROR="$WORK/src.git"

command -v git-filter-repo >/dev/null || { echo "ERRO: instale git-filter-repo (brew install git-filter-repo)"; exit 1; }

echo "Repo:   $REPO_URL"
echo "Remove: ${PATHS[*]}"
echo "Área:   $WORK"
echo

echo ">> clonando mirror…"
git clone --mirror "$REPO_URL" "$MIRROR"
cp -a "$MIRROR" "$WORK/src-mirror-backup.git"   # backup de segurança
echo ">> backup do mirror em: $WORK/src-mirror-backup.git"

cd "$MIRROR"
echo ">> tamanho ANTES:"; du -sh .

ARGS=(); for p in "${PATHS[@]}"; do ARGS+=(--path "$p"); done
echo ">> reescrevendo histórico (removendo os paths)…"
git filter-repo "${ARGS[@]}" --invert-paths --force

echo ">> tamanho DEPOIS:"; du -sh .
echo ">> conferindo que a PII sumiu do histórico (deve ser 0):"
git log --all --pretty=format: --name-only 2>/dev/null | grep -cE "$(IFS='|'; echo "${PATHS[*]}")" || echo 0

echo
echo "############################################################"
echo "# PRÓXIMO PASSO É IRREVERSÍVEL: force-push reescreve a main #"
echo "# remota e QUEBRA todos os clones/PRs existentes.           #"
echo "############################################################"
read -r -p 'Digite EXATAMENTE  CONFIRMO PURGE  para prosseguir: ' RESP
if [ "$RESP" != "CONFIRMO PURGE" ]; then
  echo "abortado. Nada foi enviado. Mirror reescrito fica em: $MIRROR"
  exit 0
fi

# filter-repo remove o remote 'origin' por segurança — re-adiciona e envia tudo.
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"
git push --force --mirror origin

echo
echo "OK — histórico reescrito e enviado."
echo "AGORA:"
echo "  1. ROTACIONE a senha do SRC e a chave Mistral (dados já foram públicos)."
echo "  2. No teu working copy: apague e RE-CLONE o repo (o antigo tem SHAs velhos)."
echo "  3. Avise colaboradores para re-clonarem."
echo "  4. GitHub Support: peça limpeza de caches/refs/pull antigos que retenham os blobs."
echo "  5. Confira Settings → Branches (proteções) e re-rode os workflows se preciso."
