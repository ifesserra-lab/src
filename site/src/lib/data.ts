import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  Painel,
  AcaoRaw,
  AtividadeRaw,
  ExtensionistaRaw,
  AcaoIndexItem,
  ExtIndexItem,
  Investimento,
  Pendencias,
  TemasPayload,
  Jornada,
  type Forproex,
  type JornadaPublico,
} from './schema';
import { norm } from './url';
import { z } from 'zod';

/**
 * Fonte da verdade = JSON do ETL Python em ../docs/api (fora de site/).
 * Lido via fs no build (SSG). Em F5 vira variável de ambiente. cwd = site/.
 */
const API_DIR = resolve(process.cwd(), '..', 'docs', 'api');

const readJson = (rel: string): unknown => JSON.parse(readFileSync(resolve(API_DIR, rel), 'utf-8'));

// Arquivos agregados que NÃO são entidades individuais.
const AGGREGATES = new Set(['index.json', 'todos.json']);
const listJson = (sub: string): string[] =>
  readdirSync(resolve(API_DIR, sub))
    .filter((f) => f.endsWith('.json') && !AGGREGATES.has(f))
    .sort();

// Lê os JSON de entidade de um dir, ignorando qualquer não-objeto (defensivo).
function readEntities(sub: string): Record<string, any>[] {
  return listJson(sub)
    .map((f) => readJson(`${sub}/${f}`))
    .filter((d): d is Record<string, any> => !!d && typeof d === 'object' && !Array.isArray(d));
}

/* ---------- painel ---------- */
export function getPainel() {
  return Painel.parse(readJson('painel.json'));
}
export function getForproex(): Forproex | null {
  return getPainel().forproex ?? null;
}

/* ---------- normalizadores (chaves cruas → limpas) ---------- */
export interface AtividadeSub { atividade_id: string; numero: string; nome: string; publico: number; aprovados: number; certificados: number; equipe: number; }
export interface EquipeMembro { nome: string; funcoes: string[]; vinculo: string; }
export interface Acao {
  id: string; processo: string; titulo: string; natureza: string; tipo: string;
  coordenador: string; fomento: string; vinculante: string; grandeArea: string; areaTema: string;
  relatorioAprovado: string; dataCadastro: string; resumo: string;
  totalParticipacoes: number; publicoTotal: number;
  atividades: AtividadeSub[]; equipe: EquipeMembro[];
}

function normAcao(json: unknown): Acao {
  const r = AcaoRaw.parse(json) as Record<string, any>;
  const pick = (a: string, b: string) => (r[a] && String(r[a]).trim() ? r[a] : r[b]) ?? '';
  return {
    id: r.acao_id,
    processo: r['Processo nº'] ?? '',
    titulo: r['Título ação'] ?? '',
    natureza: r['Natureza'] ?? '',
    tipo: r['Tipo ação'] ?? '',
    coordenador: r['Coordenador(a)'] ?? '',
    fomento: r['Fomento'] ?? '',
    vinculante: r['Ação vinculante'] ?? '',
    grandeArea: pick('Grande área conhecimento', 'Grande área conhecimento (inferida)'),
    areaTema: pick('Área temática principal', 'Área temática principal (inferida)'),
    relatorioAprovado: r['Relatório aprovado'] ?? '',
    dataCadastro: r['Data de cadastro'] ?? '',
    resumo: r['Resumo'] ?? '',
    totalParticipacoes: r.total_participacoes ?? 0,
    publicoTotal: r.publico_alvo_total ?? 0,
    atividades: (r.atividades ?? []).map((a: any) => ({
      atividade_id: String(a.atividade_id), numero: a.numero ?? '', nome: a.atividade ?? '',
      publico: a.publico ?? 0, aprovados: a.aprovados ?? 0, certificados: a.certificados ?? 0,
      equipe: a.equipe ?? 0,
    })),
    // acao equipe traz `funcoes` (array); atividade traz `funcao` (string) — unificamos.
    equipe: (r.equipe_execucao ?? []).map((e: any) => ({
      nome: e.nome ?? '', funcoes: e.funcoes ?? (e.funcao ? [e.funcao] : []), vinculo: e.vinculo ?? '',
    })),
  };
}

/* ---------- ações ---------- */
export function getAcoes(): Acao[] {
  return readEntities('acoes').map(normAcao);
}
export function getAcoesIndex() {
  return z.array(AcaoIndexItem).parse(readJson('acoes/index.json'));
}

/* ---------- atividades ---------- */
export interface Atividade {
  id: string; numero: string; nome: string; acaoId: string; acaoTitulo: string;
  processo: string; coordenador: string;
  publico: { total: number; aprovados: number; certificados: number; situacao: Record<string, number> };
  equipe: EquipeMembro[];
}
function normAtividade(json: unknown): Atividade {
  const r = AtividadeRaw.parse(json) as Record<string, any>;
  const pa = r.publico_alvo ?? {};
  return {
    id: r.atividade_id, numero: r.numero ?? '', nome: r.atividade ?? '',
    acaoId: r.acao_id, acaoTitulo: r.acao_titulo ?? '', processo: r.processo ?? '',
    coordenador: r.coordenador_acao ?? '',
    publico: { total: pa.total ?? 0, aprovados: pa.aprovados ?? 0, certificados: pa.certificados ?? 0, situacao: pa.situacao ?? {} },
    equipe: (r.equipe_execucao ?? []).map((e: any) => ({
      nome: e.nome ?? '', funcoes: e.funcoes ?? (e.funcao ? [e.funcao] : []), vinculo: e.vinculo ?? '',
    })),
  };
}
export function getAtividades(): Atividade[] {
  return readEntities('atividades').map(normAtividade);
}

/* ---------- extensionistas ---------- */
export interface ExtParticipacao { acao_id: string; titulo: string; tipo: string; ano: string; n: number; pub: number; funcoes: string[]; }
export interface ExtAtividade { ano: string; atividade_id: string; acao_id: string; atividade: string; pub: number; }
export interface Colaborador { nome: string; slug: string | null; acoes_comuns: number; }
export interface Extensionista {
  slug: string; nome: string; resumo: string; anos: (string | number)[]; funcoes: string[];
  coordenadas: ExtParticipacao[]; participacoes: ExtParticipacao[]; colaboradores: Colaborador[];
  atividades: ExtAtividade[]; impCoord: number; impEq: number; impacto: number;
  temas: { tema: string; n: number }[];
}
function normExt(json: unknown): Extensionista {
  const r = ExtensionistaRaw.parse(json) as Record<string, any>;
  return {
    slug: r.slug, nome: r.nome, resumo: r.resumo_ia ?? '',
    anos: r.anos ?? [], funcoes: r.funcoes ?? [],
    coordenadas: r.acoes_coordenadas ?? [], participacoes: r.participacoes_equipe ?? [],
    colaboradores: r.colaboradores ?? [],
    atividades: r.atividades ?? [],
    impCoord: r.imp_coord ?? 0, impEq: r.imp_eq ?? 0, impacto: r.impacto ?? 0,
    temas: r.temas ?? [],
  };
}
export function getExtensionistas(): Extensionista[] {
  return readEntities('extensionistas').map(normExt);
}
export function getExtIndex() {
  return z.array(ExtIndexItem).parse(readJson('extensionistas/index.json'));
}

/**
 * Mapa nome-normalizado → slug (fonte canônica p/ links a extensionistas).
 * Só linkamos nomes que TÊM página (coordenadores e equipe de execução).
 */
let _slugMap: Map<string, string> | null = null;
export function getSlugMap(): Map<string, string> {
  if (_slugMap) return _slugMap;
  _slugMap = new Map(getExtIndex().map((e) => [norm(e.nome), e.slug]));
  return _slugMap;
}
export function slugFor(nome: string): string | null {
  return getSlugMap().get(norm(nome)) ?? null;
}

/* ---------- páginas agregadas de topo ---------- */
export function getInvestimento() {
  return Investimento.parse(readJson('investimento.json'));
}
export function getPendencias() {
  return Pendencias.parse(readJson('pendencias-relatorio.json'));
}
export function getTemas() {
  return TemasPayload.parse(readJson('temas.json'));
}
export function getJornada() {
  return Jornada.parse(readJson('jornada.json'));
}
export function getComunidade(): JornadaPublico {
  return getJornada().publico;
}
export function getApiIndex() {
  const ApiIndex = z
    .object({ descricao: z.string(), privacidade: z.string(), endpoints: z.array(z.string()) })
    .passthrough();
  return ApiIndex.parse(readJson('index.json'));
}

/* ---------- payloads de treemap interativo (nicho×status, pessoa×papel) ---------- */
import type { TreemapPayload } from './schema';

const STATUS_COR: Record<string, string> = { ativa: 'var(--good)', intermediaria: 'var(--c3)', dormente: 'var(--muted)' };
const STATUS_LBL: Record<string, string> = { ativa: 'Ativa', intermediaria: 'Intermediária', dormente: 'Dormente' };

/** Investimento: nicho › status › iniciativa (área ∝ público). Espelha o treemap da página. */
export function getInvestTreemap(): TreemapPayload {
  const inv = getInvestimento();
  const groups: TreemapPayload['groups'] = [];
  const drill: TreemapPayload['drill'] = {};
  const zero: TreemapPayload['zero'] = {};
  const porNicho = new Map<string, { parts: Map<string, number>; itens: { t: string; c: string; v: number }[]; z: number }>();
  for (const it of inv.iniciativas ?? []) {
    const g = porNicho.get(it.nicho) ?? { parts: new Map(), itens: [], z: 0 };
    const st = it.status || 'dormente';
    g.parts.set(st, (g.parts.get(st) ?? 0) + it.publico);
    if (it.publico > 0) g.itens.push({ t: (it.titulo || '—').slice(0, 60), c: st, v: it.publico });
    else g.z += 1;
    porNicho.set(it.nicho, g);
  }
  for (const [nicho, g] of porNicho) {
    groups.push({ nome: nicho, parts: [...g.parts.entries()].sort((a, b) => b[1] - a[1]) as any });
    drill[nicho] = g.itens.sort((a, b) => b.v - a.v);
    zero[nicho] = g.z;
  }
  groups.sort((a, b) => b.parts.reduce((s, [, v]) => s + Number(v), 0) - a.parts.reduce((s, [, v]) => s + Number(v), 0));
  return { dim: 'status', medida: 'público', crumb_all: 'Todos os nichos', colors: STATUS_COR, labels: STATUS_LBL, groups, drill, zero };
}

/** Extensionistas: pessoa › papel (coordenou/equipe) › iniciativa (área ∝ pessoas impactadas). */
export function getExtTreemap(top = 16): TreemapPayload {
  const linhas = getExtensionistas()
    .map((p) => {
      const coordIds = new Set(p.coordenadas.map((r) => r.acao_id));
      const impByAcao = new Map<string, number>();
      for (const at of p.atividades) impByAcao.set(at.acao_id, (impByAcao.get(at.acao_id) ?? 0) + (at.pub ?? 0));
      const coord = p.coordenadas.map((r) => ({ t: (r.titulo || '—').slice(0, 60), v: r.pub ?? 0 }));
      const eq = p.participacoes.filter((r) => !coordIds.has(r.acao_id)).map((r) => ({ t: (r.titulo || '—').slice(0, 60), v: impByAcao.get(r.acao_id) ?? 0 }));
      const ic = coord.reduce((s, x) => s + x.v, 0);
      const ie = eq.reduce((s, x) => s + x.v, 0);
      return { nome: p.nome, coord, eq, ic, ie, impacto: ic + ie };
    })
    .filter((r) => r.impacto > 0)
    .sort((a, b) => b.impacto - a.impacto)
    .slice(0, top);
  const groups: TreemapPayload['groups'] = [];
  const drill: TreemapPayload['drill'] = {};
  const zero: TreemapPayload['zero'] = {};
  for (const r of linhas) {
    groups.push({ nome: r.nome, parts: [['coordena', r.ic], ['equipe', r.ie]] as any });
    const itens = [...r.coord.map((x) => ({ t: x.t, c: 'coordena', v: x.v })), ...r.eq.map((x) => ({ t: x.t, c: 'equipe', v: x.v }))];
    drill[r.nome] = itens.filter((i) => i.v > 0).sort((a, b) => b.v - a.v);
    zero[r.nome] = itens.filter((i) => i.v === 0).length;
  }
  return {
    dim: 'papel', medida: 'pessoas impactadas', crumb_all: 'Top extensionistas',
    colors: { coordena: 'var(--c1)', equipe: 'var(--c2)' }, labels: { coordena: 'coordenou', equipe: 'equipe' },
    groups, drill, zero,
  };
}
