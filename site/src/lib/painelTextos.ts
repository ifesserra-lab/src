// AUTO-EXTRAÍDO de docs/painel.html — textos verbatim (sec-desc + 'O que significa?').
export const PT: Record<string,{sd:string;ex:string}> = {
  "Ações por natureza e tipo": {
    "sd": "Distribuição das ações por natureza acadêmica.",
    "ex": "Conta quantas ações registradas no SRC pertencem a cada natureza (Extensão, Ensino, Pesquisa, Pós-Graduação ou Desenvolvimento Institucional). Cada ação conta uma vez, pela natureza declarada no cadastro. Serve para ver o perfil do campus: predominância de Extensão indica vocação de atendimento à comunidade externa."
  },
  "Fomento e relatório final": {
    "sd": "Fonte de fomento vinculada à ação.",
    "ex": "Origem do apoio financeiro declarada no cadastro (FAPES, PAEX-IFES, PRONATEC etc.). 'SEM VÍNCULO' significa que a ação não declarou fonte de fomento — geralmente executada só com recursos próprios/voluntariado. Percentual alto de SEM VÍNCULO sinaliza baixa captação de recursos externos."
  },
  "Ações por ano de cadastro": {
    "sd": "Volume de ações cadastradas por ano.",
    "ex": "Quantidade de ações registradas no SRC em cada ano (pela data de cadastro, não pela data de execução). Mostra a tendência histórica de produção do campus. Atenção: o ano corrente sempre parece menor porque ainda está em curso, e quedas em 2020–2021 refletem a pandemia."
  },
  "Grande área e área temática": {
    "sd": "85 categorias inferidas por IA (Mistral) a partir do resumo.",
    "ex": "Classificação CNPq da ação (Engenharias, Ciências Humanas etc.). Como mais da metade dos cadastros originais deixou o campo vazio, as categorias faltantes foram deduzidas por IA (Mistral) lendo título + resumo da ação, sempre escolhendo dentro da tabela oficial e só quando a confiança é ≥ 60%. O valor original nunca é sobrescrito: a inferência fica marcada no dado como '(inferida)'."
  },
  "Top 10 — coordenadores e ações": {
    "sd": "Proponentes mais recorrentes — só ações com participação registrada.",
    "ex": "Ranking dos coordenadores(as) pelo número de ações em que constam como responsáveis. Ações sem nenhum participante registrado (público e equipe zerados) são EXCLUÍDAS desta contagem, para medir produção efetiva e não apenas cadastros. Coordenador é dado público do sistema."
  },
  "Situação e certificação do público-alvo": {
    "sd": "Situação registrada do público-alvo.",
    "ex": "Status final de cada participação de público-alvo conforme lançado no SRC: APROVADO (concluiu com êxito), CURSANDO (em andamento), REPROVADO (não atingiu os critérios). A base é participações, não pessoas — uma pessoa pode estar APROVADO numa atividade e CURSANDO em outra."
  },
  "Equipe executora por função (top 8)": {
    "sd": "",
    "ex": "Composição de quem EXECUTA as ações, pela função declarada de cada vínculo de equipe: bolsistas, voluntários, coordenador, professores etc. Mede a força de trabalho da extensão — em particular o protagonismo discente (funções de aluno) frente ao corpo docente."
  },
  "Alunos atendidos: por ano e por coordenador(a)": {
    "sd": "Alcance (participações de público) por ano de cadastro da ação.",
    "ex": "Soma das participações de público-alvo agrupadas pelo ano de cadastro da ação correspondente. Diferente do gráfico 'ações por ano' (que conta cadastros), este mede PESSOAS alcançadas ao longo do tempo — uma ação só, se for grande, pode dominar o ano. Base: participações (a mesma pessoa em 2 atividades conta 2)."
  },
  "Recorrência e tamanho de turma": {
    "sd": "Quantas pessoas distintas participaram de 1, 2, 3–4 ou 5+ ações.",
    "ex": "Pessoas únicas (deduplicadas por CPF) classificadas pelo número de participações que acumulam. A faixa '1 ação' é o público de passagem; '5+' é o núcleo fiel que orbita a extensão do campus. Recorrência alta aumenta a diferença entre participações totais e alunos únicos."
  },
  "Taxa de aprovação e de certificação por tipo": {
    "sd": "% de participantes com situação APROVADO, por tipo.",
    "ex": "Dentro de cada tipo (Curso, Projeto, Evento, Programa), a fração das participações de público-alvo cujo status é APROVADO. Taxas menores em formatos longos (Projeto/Curso) normalmente refletem evasão ao longo do tempo; eventos pontuais aprovam quase todos os presentes."
  },
  "Composição da equipe executora": {
    "sd": "Perfil dos membros de equipe por função.",
    "ex": "Vínculos de equipe agrupados em classes: Discente (aluno bolsista, voluntário, atividade curricular), Docente (professor), Técnico(a) e Outros (colaboradores externos, convidados, funções não tipificadas). Mede quem faz a extensão acontecer — e o peso do protagonismo estudantil."
  },
  "Programas por nº de ações vinculadas": {
    "sd": "Ações \"guarda-chuva\" que agregam outras (campo Ação vinculante) — ex.: LAMPEX, LEDS.",
    "ex": "No SRC, uma ação pode declarar outra como 'Ação vinculante' — isso cria programas guarda-chuva que abrigam projetos/cursos/eventos filhos. Este gráfico conta quantas ações filhas cada programa agrega, usando a consulta oficial de ações vinculadas do sistema (não o campo de texto, que é incompleto). Só entram filhas com participação registrada (público ou equipe > 0). Mede o papel estruturante do programa: quanto mais filhas, mais ele funciona como plataforma."
  },
  "Programas por público agregado": {
    "sd": "Público-alvo do próprio programa + das ações filhas.",
    "ex": "Alcance total do ecossistema de cada programa: soma o público-alvo registrado nas atividades do PRÓPRIO programa com o público de todas as suas ações filhas. Exemplo: LAMPEX = participantes das suas 117 atividades internas + participantes dos projetos vinculados a ele. Mede o impacto consolidado do programa como um todo, não apenas o que está formalmente 'dentro' dele. Base: participações (pessoas podem repetir entre atividades)."
  },
  "Rede de colaboração entre coordenadores(as)": {
    "sd": "Cada elo liga dois coordenadores que compartilham uma mesma pessoa na equipe. Passe o mouse nos nós para ver os nomes.",
    "ex": "Grafo de 'quem ajuda quem': dois coordenadores ficam conectados quando uma mesma pessoa (identificada por CPF, nunca exibido) participou da equipe de execução de ações de ambos. Linhas mais grossas = mais pessoas em comum. Mostra os núcleos de cooperação real do campus — laboratórios e grupos que trocam bolsistas, voluntários e colaboradores. Exibe os 14 coordenadores mais conectados."
  },
  "Coordenadores(as) mais colaborativos": {
    "sd": "Nº de parceiros distintos (coordenadores com equipe em comum).",
    "ex": "Para cada coordenador(a), o número de OUTROS coordenadores com quem compartilha ao menos uma pessoa de equipe. É o 'grau' do nó na rede acima: valores altos indicam articuladores — pessoas que conectam grupos diferentes da extensão."
  },
  "Principais parcerias": {
    "sd": "Pares de coordenadores com mais pessoas de equipe em comum.",
    "ex": "As duplas de coordenadores com maior interseção de equipe. Muitas pessoas em comum normalmente indica laboratório/grupo compartilhado ou linha de trabalho conjunta de longo prazo — parcerias estruturais, não pontuais."
  },
  "Formados que participaram de Extensão": {
    "sd": "Formados com ao menos uma participação (público-alvo ou equipe) em ação de Extensão.",
    "ex": "Cruza a lista oficial de formados do campus (planilhas acadêmicas 2020–2025, deduplicadas por matrícula) com os participantes das ações de natureza Extensão. 'Participou' = o nome do formado aparece ao menos uma vez como público-alvo OU membro de equipe. Como as planilhas não trazem CPF, o casamento é por nome normalizado — homônimos ou grafias diferentes podem gerar pequeno erro."
  },
  "Formados na Extensão por curso (participantes/total)": {
    "sd": "Nº de formados de cada curso que participaram da Extensão.",
    "ex": "Recorte por curso de graduação: quantos formados de cada curso têm registro de participação em extensão (o rótulo mostra participantes/total do curso). Permite comparar o quanto cada curso expõe seus alunos à extensão antes de formar."
  },
  "Horas-aluno e perfil etário": {
    "sd": "Esforço formativo = carga horária × nº de participações de público.",
    "ex": "Soma, por tipo de ação, das horas de formação entregues: para cada participação de público conta a carga horária (C.H) da atividade. É a métrica de esforço/impacto usada em relatórios de extensão — mede volume de formação efetivamente ofertado, não apenas número de pessoas."
  },
  "Funil de engajamento (público → equipe)": {
    "sd": "303 pessoas (6.3%) foram atendidas e depois entraram numa equipe — mediana de 428 dias.",
    "ex": "Conta pessoas (por CPF, nunca exibido) cuja primeira participação foi como público-alvo e que MAIS TARDE apareceram na equipe de execução de alguma ação. É o 'ciclo virtuoso' da extensão: quem é atendido depois vira protagonista. O tempo mediano indica quanto leva essa transição."
  },
  "Gap de certificação por coordenador(a)": {
    "sd": "504 participações APROVADAS sem certificado emitido.",
    "ex": "Participantes com situação APROVADO mas sem certificado registrado no SRC — têm direito e não receberam. Agrupado por coordenador(a) responsável, é uma lista de pendência acionável: basta emitir. Difere da taxa geral de certificação por isolar só os casos que já deveriam estar certificados."
  },
  "Renovação da equipe por ano (% de pessoas novas)": {
    "sd": "Fração de membros de equipe que são novos (nunca haviam atuado antes).",
    "ex": "A cada ano, quantos % das pessoas na equipe de execução nunca tinham participado antes. Alto = oxigenação/entrada de novos extensionistas; baixo = dependência de um núcleo veterano. Ajuda a avaliar sustentabilidade da força de trabalho da extensão ao longo do tempo."
  },
  "Sazonalidade — atividades por mês de início": {
    "sd": "Quando as atividades começam ao longo do ano.",
    "ex": "Distribui as atividades pelo mês de início. Revela o ritmo do calendário de extensão — concentração no 2º semestre (agosto–outubro) indica alinhamento com o calendário letivo. Útil para planejar editais, bolsas e infraestrutura nos períodos de pico."
  },
  "Duração das atividades e vínculo da equipe": {
    "sd": "Distribuição das atividades por tempo de execução.",
    "ex": "Classifica cada atividade pelo intervalo início→término: pontual (evento de 1 dia), curta (até 1 mês), média (1–6 meses) ou longa (>6 meses). Mostra o mix entre ações pontuais de grande alcance e trabalho contínuo de proximidade."
  },
  "Continuidade e concentração": {
    "sd": "",
    "ex": "Continuidade: ações que rodam em vários anos tendem a estar institucionalizadas (programas, laboratórios). Concentração: CR5/CR10 = quanto do público está nas maiores ações; HHI (índice Herfindahl-Hirschman) resume a concentração — abaixo de 1500 o alcance é bem distribuído entre muitas ações."
  },
  "1 · Política de Gestão": {
    "sd": "Registro e conclusão formal do ciclo das ações.",
    "ex": "Capacidade de registrar, acompanhar e concluir as ações no SRC. 150 de 201 ações têm relatório final aprovado; 51 pendentes."
  },
  "2 · Infraestrutura": {
    "sd": "10 programas com público (de 17 nomes distintos, 20 processos), por pessoas distintas atingidas.",
    "ex": "Programas são iniciativas contínuas que abrigam várias atividades/edições. Ações de mesmo nome (processos distintos) são agrupadas e as pessoas contadas uma só vez. Servem de proxy de infraestrutura de extensão (o SRC não traz orçamento nem espaços)."
  },
  "3 · Política Acadêmica — protagonismo e formação": {
    "sd": "Equipe executora por vínculo · 197 de 306 formados passaram pela extensão.",
    "ex": "Quem executa a extensão (protagonismo estudantil) e como ela toca a formação: 566 dos 907 membros de equipe são discentes."
  },
  "4 · Relação Universidade-Sociedade": {
    "sd": "Alcance e perfil do público.",
    "ex": "Alcance da extensão. Falta a satisfação/percepção da comunidade e a mudança social pós-ação — núcleo desta dimensão segundo a literatura (coleta a implementar)."
  },
  "5 · Produção Acadêmica (extensão × pesquisa)": {
    "sd": "FWCI mediano dos extensionistas-pesquisadores: 1.19 (acima da média mundial se >1).",
    "ex": "Cruzamento com o Horizon (FAPES/FACTO/Lattes/OpenAlex). FWCI/citações medem impacto CIENTÍFICO — entram como associação, não como impacto de extensão."
  }
};
