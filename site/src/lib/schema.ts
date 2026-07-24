import { z } from 'zod';

/**
 * Contrato de dados (F0) — espelha o JSON emitido por
 * `src_etl/dashboard/export_json.py`. Campos usados nas páginas são tipados;
 * o resto passa por `.passthrough()` para não quebrar quando o ETL crescer.
 *
 * Par rótulo→contagem, formato usado em todo o painel: ["Extensão", 83].
 */
export const Pair = z.tuple([z.string(), z.number()]);
export type Pair = z.infer<typeof Pair>;

/** Linha mista (ex.: ["Curso", 53, 37] — rótulo, valor e %). */
export const Row = z.array(z.union([z.string(), z.number()]));
export type Row = z.infer<typeof Row>;

const pairs = z.array(Pair);
const rows = z.array(Row);

export const VisaoGeral = z
  .object({
    n_acoes: z.number(),
    n_acoes_ativas: z.number(),
    total_atividades: z.number(),
    total_publico: z.number(),
    total_equipe: z.number(),
    media_equipe: z.number(),
    taxa_cert: z.number(),
    natureza: pairs,
    tipo: pairs,
    anos: pairs,
    coordenadores: pairs,
    grande_area: pairs,
    fomento: pairs,
    // rico (presente no JSON; não era tipado):
    area_tematica: pairs.optional(),
    relatorio: pairs.optional(),
    situacao: pairs.optional(),
    certificado: pairs.optional(),
    funcao: pairs.optional(),
    top_publico: pairs.optional(),
    n_at_inferida: z.number().optional(),
    n_ga_inferida: z.number().optional(),
  })
  .passthrough();

export const Indicadores = z
  .object({
    alunos_unicos: z.number(),
    total_publico: z.number(),
    total_equipe: z.number(),
    equipe_unica: z.number(),
    publico_por_ano: pairs,
    composicao_equipe: pairs,
    recorrencia: pairs,
    turma_dist: pairs,
    publico_por_coord: pairs.optional(),
    aprovado_por_tipo: pairs.optional(),
    cert_por_tipo: pairs.optional(),
    media_part_pessoa: z.number().optional(),
    razao_aluno_equipe: z.number().optional(),
    turma_media: z.number().optional(),
  })
  .passthrough();

export const Impacto = z
  .object({
    horas_aluno: z.number(),
    funil_conv: z.number(),
    funil_pct: z.number(),
    gap_cert: z.number(),
    renovacao: pairs,
    vinculo: pairs,
    idade: pairs,
    gap_coord: pairs,
    ch_por_tipo: pairs.optional(),
    meses: pairs.optional(),
    duracao: pairs.optional(),
    funil_dias: z.number().optional(),
    multi_ano: z.number().optional(),
    cr5: z.number().optional(),
    cr10: z.number().optional(),
    hhi: z.number().optional(),
    pct_externo: z.number().optional(),
    horas_por_part: z.number().optional(),
  })
  .passthrough();

export const RedeProgramas = z
  .object({
    n_programas: z.number(),
    n_coord_colab: z.number(),
    n_parcerias: z.number(),
    programas_publico: pairs,
    coord_colab: pairs,
    top_parcerias: pairs,
    programas: pairs.optional(),
    maior_programa: Pair.optional(),
    grafo_nodes: z.array(z.string()).optional(),
    grafo_edges: z.array(z.array(z.number())).optional(),
  })
  .passthrough();

export const Formados = z
  .object({
    total_formados: z.number(),
    em_ext_qualquer: z.number(),
    pct_qualquer: z.number(),
    papel_dist: pairs,
    por_curso: pairs,
    participou_dist: pairs.optional(),
    em_ext_publico: z.number().optional(),
    em_ext_equipe: z.number().optional(),
  })
  .passthrough();

const ProgItem = z.object({ titulo: z.string(), publico: z.number(), atividades: z.number(), processos: z.number() }).passthrough();
export const Forproex = z
  .object({
    tot: z.number(), aprov: z.number(), com_part: z.number(), pend: z.number(),
    programas: z.number(), programas_dist: z.number(),
    teq: z.number(), disc: z.number(), serv: z.number(), conv: z.number(),
    form_alc: z.number(), n_form: z.number(), npub: z.number(), atend: z.number(),
    preuni: z.number(), n_idade: z.number(),
    prog_list: z.array(ProgItem),
    prod: z.object({ coord: z.number(), com_ext: z.number(), fwci: z.number() }).passthrough(),
  })
  .passthrough();
export type Forproex = z.infer<typeof Forproex>;

export const Painel = z
  .object({
    visao_geral: VisaoGeral,
    indicadores: Indicadores,
    impacto: Impacto,
    rede_programas: RedeProgramas,
    formados: Formados.nullable(),
    forproex: Forproex.nullable().optional(),
  })
  .passthrough();

/* ---- temas & clusters ---- */
const TreemapGroup = z.object({ nome: z.string(), parts: z.array(Pair) }).passthrough();
const TreemapDrillItem = z.object({ t: z.string(), c: z.string(), v: z.number() }).passthrough();
export const TreemapPayload = z
  .object({
    dim: z.string(),
    medida: z.string(),
    crumb_all: z.string(),
    colors: z.record(z.string()),
    labels: z.record(z.string()),
    groups: z.array(TreemapGroup),
    drill: z.record(z.array(TreemapDrillItem)),
    zero: z.record(z.number()),
  })
  .passthrough();
export type TreemapPayload = z.infer<typeof TreemapPayload>;

export const TemaCard = z
  .object({
    tema: z.string(),
    acoes: z.number(),
    publico: z.number(),
    pessoas: z.number(),
    coordenadores: z.array(z.object({ nome: z.string(), slug: z.string().nullable(), n: z.number() }).passthrough()),
    exemplos: z.array(z.object({ titulo: z.string(), acao_id: z.string() }).passthrough()),
    resumo: z.string().nullable().optional(),
  })
  .passthrough();
export const TemasPayload = z.object({ treemap: TreemapPayload, temas: z.array(TemaCard) }).passthrough();
export type TemasPayload = z.infer<typeof TemasPayload>;
export type TemaCard = z.infer<typeof TemaCard>;

/* ---- jornada do formado ---- */
const PorAno = z.object({ ano: z.string(), k: z.number(), total: z.number(), itens: rows }).passthrough();
export const JornadaPublico = z
  .object({
    n_pessoas: z.number(), n_alunos: z.number(), n_nao: z.number(), pct_nao: z.number(),
    papel_nao: rows, papel_alunos: rows, top_inic_nao: rows,
    cluster_nao: rows, area_nao: rows,
    recorrencia: pairs, por_ano_nao: pairs,
    um_so: z.number(), um_so_pct: z.number(),
  })
  .passthrough();
export const Jornada = z
  .object({
    n_formados: z.number(), com_ext: z.number(), pct_ext: z.number(),
    med_ing_ext: z.number(), med_ext_form: z.number(), med_dur: z.number(),
    apos_formar: z.number(),
    dist_ing_ext: pairs,
    inic_por_ano: z.array(PorAno), clust_por_ano: z.array(PorAno), area_por_ano: z.array(PorAno),
    fase: pairs, decis: z.array(z.number()), por_curso: pairs,
    publico: JornadaPublico,
  })
  .passthrough();
export type Jornada = z.infer<typeof Jornada>;
export type JornadaPublico = z.infer<typeof JornadaPublico>;

/* ---- investimento / pendências / sem-participação ---- */
const InvestNicho = z.object({ nicho: z.string(), iniciativas: z.number(), publico: z.number(), ativas: z.number(), dormentes: z.number(), publico_ativo: z.number().optional(), publico_dormente: z.number().optional(), intermediarias: z.number().optional() }).passthrough();
const InvestAcao = z.object({ acao_id: z.string(), titulo: z.string(), nicho: z.string(), tipo: z.string(), fomento: z.string(), publico: z.number(), ano_ultima: z.number() }).passthrough();
const InvestIniciativa = z.object({ acao_id: z.string(), titulo: z.string(), nicho: z.string(), tipo: z.string(), natureza: z.string().optional(), fomento: z.string().optional(), coordenador: z.string().optional(), publico: z.number(), participacoes: z.number().optional(), ano_ultima: z.number().optional(), status: z.string(), url: z.string().optional() }).passthrough();
const InvestRec = z.object({ grupo: z.string(), cor: z.string(), descricao: z.string(), exemplos: z.array(z.string()) }).passthrough();
const LimitesImpacto = z.object({ texto: z.string(), sugestoes: z.array(z.object({ titulo: z.string(), detalhe: z.string() }).passthrough()), exemplos_subestimados: z.array(z.string()).optional() }).passthrough();
export const Investimento = z
  .object({
    ano_referencia: z.number(),
    criterio_status: z.record(z.string()).optional(),
    nicho_definicao: z.any().optional(),
    impacto_definicao: z.any().optional(),
    totais: z.record(z.number()),
    por_nicho: z.array(InvestNicho),
    top_ativas: z.array(InvestAcao),
    top_dormentes: z.array(InvestAcao),
    recomendacoes: z.array(InvestRec),
    iniciativas: z.array(InvestIniciativa).optional(),
    limites_impacto: LimitesImpacto.optional(),
  })
  .passthrough();
export type Investimento = z.infer<typeof Investimento>;

export const PendenciaRow = z
  .object({
    acao_id: z.string(), titulo: z.string(), tipo: z.string(),
    coordenador: z.string(), coordenador_slug: z.string().nullable().optional(),
    ano: z.string(), inicio: z.string().optional(), termino: z.string().optional(),
    ultimo: z.string().optional(), pendente: z.boolean(), pub: z.number(), eq: z.number(),
  })
  .passthrough();
export const Pendencias = z
  .object({ com: z.array(PendenciaRow), zero: z.array(PendenciaRow), leaderboard: z.array(Pair) })
  .passthrough();
export type Pendencias = z.infer<typeof Pendencias>;
export type PendenciaRow = z.infer<typeof PendenciaRow>;

export type Painel = z.infer<typeof Painel>;
export type VisaoGeral = z.infer<typeof VisaoGeral>;
export type Indicadores = z.infer<typeof Indicadores>;
export type Impacto = z.infer<typeof Impacto>;
export type RedeProgramas = z.infer<typeof RedeProgramas>;
export type Formados = z.infer<typeof Formados>;

/* ---- entidades de detalhe (F3) ----
   Detalhes usam .passthrough(): garantimos só a chave de identidade; o resto
   (chaves com espaço/parênteses, ex. "Título ação") é normalizado no data.ts. */
export const AcaoRaw = z.object({ acao_id: z.string() }).passthrough();
export const AtividadeRaw = z.object({ atividade_id: z.string(), acao_id: z.string() }).passthrough();
export const ExtensionistaRaw = z.object({ slug: z.string(), nome: z.string() }).passthrough();

export const AcaoIndexItem = z
  .object({
    acao_id: z.string(),
    titulo: z.string(),
    tipo: z.string(),
    natureza: z.string(),
    coordenador: z.string(),
    ano: z.string(),
    total_participacoes: z.number(),
  })
  .passthrough();

export const ExtIndexItem = z
  .object({
    slug: z.string(),
    nome: z.string(),
    funcoes: z.array(z.string()),
    anos: z.array(z.union([z.string(), z.number()])),
    coordena: z.number(),
    equipe: z.number(),
    imp_coord: z.number().optional(),
    imp_eq: z.number().optional(),
    impacto: z.number().optional(),
  })
  .passthrough();

export type AcaoIndexItem = z.infer<typeof AcaoIndexItem>;
export type ExtIndexItem = z.infer<typeof ExtIndexItem>;
