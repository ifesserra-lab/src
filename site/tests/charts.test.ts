import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import { describe, expect, test, beforeAll } from 'vitest';
import type { Pair } from '../src/lib/schema';

import Tile from '../src/components/Tile.astro';
import PairBar from '../src/components/PairBar.astro';
import Donut from '../src/components/Donut.astro';
import Treemap from '../src/components/Treemap.astro';
import RankingTable from '../src/components/RankingTable.astro';
import LineChart from '../src/components/LineChart.astro';
import Funnel from '../src/components/Funnel.astro';
import StackedBar from '../src/components/StackedBar.astro';
import Timeline from '../src/components/Timeline.astro';

// Amostras fixas → saída SVG determinística → snapshot estável.
// Qualquer mudança acidental no output de um chart falha o teste (critério F2).
const anos: Pair[] = [
  ['2019', 26], ['2020', 16], ['2021', 22], ['2022', 31], ['2023', 36], ['2024', 28],
];
const natureza: Pair[] = [['Extensão', 83], ['Ensino', 54], ['Pesquisa', 3]];
const tipo: Pair[] = [['Projeto', 53], ['Curso', 52], ['Evento', 21]];
const recorrencia: Pair[] = [['1 ação', 3486], ['2 ações', 619], ['3–4 ações', 514], ['5+', 226]];
const equipe: Pair[] = [['Outros', 1395], ['Discente', 680], ['Docente', 134], ['Técnico(a)', 98]];
const coord: Pair[] = [['Ana', 13], ['Bruno', 8], ['Carla', 7]];

let container: AstroContainer;
beforeAll(async () => {
  container = await AstroContainer.create();
});

const render = (C: any, props: Record<string, unknown>) => container.renderToString(C, { props });

describe('componentes de chart — snapshot SVG/HTML', () => {
  test('Tile', async () => {
    expect(await render(Tile, { label: 'Iniciativas', value: '201', color: 'var(--c1)', spark: [3, 5, 4, 8, 9, 12] }))
      .toMatchSnapshot();
  });
  test('PairBar', async () => {
    expect(await render(PairBar, { data: tipo, color: 'var(--c1)' })).toMatchSnapshot();
  });
  test('Donut', async () => {
    expect(await render(Donut, { data: natureza, centerLabel: 'iniciativas' })).toMatchSnapshot();
  });
  test('Treemap', async () => {
    expect(await render(Treemap, { data: tipo })).toMatchSnapshot();
  });
  test('RankingTable', async () => {
    expect(await render(RankingTable, { data: coord, colLabel: 'Coord', colValue: 'Ações' })).toMatchSnapshot();
  });
  test('LineChart', async () => {
    expect(await render(LineChart, { data: anos, color: 'var(--c2)', id: 't' })).toMatchSnapshot();
  });
  test('Funnel', async () => {
    expect(await render(Funnel, { data: recorrencia, color: 'var(--c4)' })).toMatchSnapshot();
  });
  test('StackedBar', async () => {
    expect(await render(StackedBar, { data: equipe })).toMatchSnapshot();
  });
  test('Timeline', async () => {
    expect(await render(Timeline, { data: anos, color: 'var(--c1)' })).toMatchSnapshot();
  });
});
