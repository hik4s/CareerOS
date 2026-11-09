# Ampliação do motor de busca — 2026-11-09

## Objetivo e entrega

Ampliar cobertura pública sem exigir contratação de agregadores, recuperar vagas
brasileiras descartadas por inferência geográfica incompleta e reconhecer cargos
equivalentes sem eliminar palavras exigidas na consulta.

- 13 → 32 catálogos fixos, com mais 19 empresas em Greenhouse/Lever/Ashby.
- Cadastro validado em `app/cloud/job_sources.json`: somente provedores conhecidos,
  identificadores de board restritos e hosts fixos; não aceita URLs arbitrárias.
- Conectores com dados de modalidade, locais secundários, contratação, publicação
  e endereço de candidatura quando informados pela fonte.
- Lever paginado, limitado a 1.000 anúncios e protegido contra página repetida.
- Coleta parcial mantém entradas anteriores não reconfirmadas dentro do limite,
  em vez de apagar anúncios após falha numa página posterior.
- Seis requisições HTTP simultâneas; cache e coleta progressiva existentes preservados.
- Busca por cargos equivalentes PT/EN e grafias frontend/back-end/full stack.
- Metadado explícito de contratação participa da busca e do filtro de nível.
- Publicação como desempate após relevância/distância, sem criar datas ausentes.
- Contagem bruta de catálogos separada dos resultados filtrados/deduplicados na UI.
- Link de candidatura fornecido pelo provedor quando válido, com fallback para
  a página da vaga e rejeição de esquemas inseguros.

## Geografia e procedência

O filtro anterior tinha uma expressão curta de cidades/estados. A regressão
reproduziu Presidente Prudente/SP e Santos/SP sendo excluídos de Brasil.

`app/cloud/brazil_municipalities.csv` contém 5.571 pares normalizados nome/UF,
extraídos em 09/11/2026 da API pública oficial do IBGE:
https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome

Documentação: https://servicodados.ibge.gov.br/api/docs/localidades
Fonte dos nomes e UFs: IBGE. A cópia é local: cada busca não consulta o IBGE.
A base de coordenadas GeoNames e sua atribuição CC BY 4.0 permanecem como antes.
O cadastro completo de nomes amplia a inferência de país, sem inventar coordenadas
ou prometer raio para todos os municípios.

País explícito do provedor prevalece sobre inferência por nomes. Um sufixo MA/ES
isolado não transforma Boston/Espanha em Brasil. Localidade e país de cada endereço
Ashby são mantidos juntos; uma cidade estrangeira homônima não vira município
brasileiro por separar o país numa string independente. Remoto mundial/LatAm depende
de indicação explícita, e exclusões conhecidas de Brasil continuam bloqueadas.

## Medição real

Registro integral: [SEARCH_BENCHMARK_2026-11-09.json](SEARCH_BENCHMARK_2026-11-09.json).
Coleta em 09/11/2026, 09:44 no horário de Brasília. Somente os catálogos públicos
fixos, sem credenciais, perfil pessoal, filtro de senioridade ou integrações pagas.
Os dois motores foram comparados sobre a mesma coleta dos catálogos originais.

| Medida | Antes | Ampliado |
| --- | ---: | ---: |
| Catálogos públicos fixos | 13 | 32 |
| Anúncios brutos | 1.682 | 4.311 |
| Resultados únicos classificados para Brasil | 549 | 943 |
| Correspondências a “desenvolvedor python” | 4 | 110 |
| Correspondências a “frontend” | 3 | 23 |
| Correspondências a “backend” | 18 | 64 |
| Correspondências a “estágio” | 14 | 16 |
| Correspondências a “estágio python” | 2 | 2 |

As 32 fontes responderam com sucesso nessa coleta, concluída em 10,14 s. Isso é
tempo de coleta completa no ambiente local; a API de busca continua devolvendo
catálogos prontos enquanto outros são atualizados. Não é SLA nem medição do Render.

O ganho de volume não comprova precisão de cada resultado, validade de candidatura
ou adequação ao perfil. A expansão trouxe principalmente outras áreas/níveis; a
amostra de estágio Python não cresceu. Não somar consultas sobrepostas como vagas
diferentes. Vagas sem encerramento informado podem exigir confirmação no portal.

Para repetir somente a medição atual: `python scripts/measure_search_catalog.py`.
Use `--output relatorio.json` para salvar o agregado. O script não consulta os
agregadores pagos nem envia dados de conta; atualiza apenas cache de vagas públicas.
O resultado histórico muda com publicação/remoção de vagas nas empresas.

## Validação

- 31 testes novos de geografia, equivalências, metadados, fontes, paginação,
  cache parcial e ordenação, incluindo integração do conector com a rota autenticada.
- Regressões reproduzidas antes das correções; revisão independente encontrou
  três casos importantes, todos corrigidos e cobertos pelos testes.
- 149 testes cloud/regionais/fontes aprovados no ambiente local.
- Scripts Node de carregamento/importação aprovados e sintaxe JavaScript verificada.
- Edge headless em viewport móvel: busca sem perfil, resumo das fontes, publicação,
  links seguros e sem overflow; fluxo de perfil também continua aprovado.
  Rede/conta do teste de UI são simuladas; a coleta pública acima foi real.
- Suíte Python completa: 171 passed, 2 failed. Falhas desktop anteriores
  `test_workspace_roundtrip` e `test_reject_tampered_archive` por conexão SQLite
  aberta no Windows continuam documentadas no recorte anterior de importação.
- Ambiente local: Python 3.11.9 e Node 20.15.0. CI usa Python 3.12 e Node 22.

Não houve merge, deploy ou mudança no banco de contas. A candidatura externa
assistida e o módulo de empresas continuam etapas seguintes do produto.
