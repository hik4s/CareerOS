# Busca de vagas no CareerOS

O perfil é opcional para pesquisar. Se “Somente vagas compatíveis com meu perfil”
estiver marcado e ainda não houver habilidades, cargos de interesse ou formação,
a busca continua com os termos e filtros informados, sem personalização por perfil.
Com dados no perfil, o filtro mantém a avaliação de compatibilidade existente.

Em **Buscar vagas**, use palavras-chave, localização, modalidade e nível.
Para remoto no Brasil, combine a modalidade **Remoto** com **Brasil** na
localização. Vagas remotas sem região informada ficam disponíveis sem esse
filtro. Modalidade e nível dependem dos dados publicados pela fonte.
Marque **Buscar palavras-chave somente no título** para exigir que todos
os termos relevantes apareçam no cargo, incluindo equivalentes como
estágio e intern. Na busca ampla, os resultados indicam se os termos
estão no título, nos detalhes ou se a vaga foi sugerida pela fonte.
Use vírgulas para buscar alternativas. Por exemplo, **estágio Python,
estágio em TI** busca vagas que correspondam a pelo menos um desses grupos.

Para incluir cidades próximas, escolha um raio em **Distância da cidade**
e informe uma cidade brasileira. A distância aproximada é em linha reta
entre os centros das cidades. O raio altera apenas o filtro de localização.
Os outros filtros continuam valendo, e vagas sem cidade identificável ficam
fora. A ordenação mantém a relevância em primeiro lugar e usa a distância
para desempatar. O catálogo local é um recorte brasileiro de
[`cities15000` do GeoNames](https://www.geonames.org/export/), com nomes
normalizados, UF e coordenadas arredondadas, sob licença CC BY 4.0.
Os resultados aparecem em uma lista paginada. Clique no título para ler
a descrição e use **Revisar e salvar** para adicionar a oportunidade a **Minhas vagas**.
Na janela da vaga, escolha **Português (Brasil)** ou **Original**. A tradução
usa os modelos do navegador em dispositivos compatíveis. O navegador pode
precisar baixar os modelos no primeiro uso e oferece português genérico quando
a variante brasileira não está disponível. [Documentação do tradutor](https://developer.chrome.com/docs/ai/translator-api).
O link de candidatura abre a página da vaga no site de origem.

## Cobertura

- Greenhouse de Grupo QuintoAndar, Brex, Stone, Wellhub, VTEX, SumUp,
  Wildlife Studios, Ebury, RD Station, ília, Banco PAN e Zup Innovation.
- Primeira página do feed público Arbeitnow, com foco internacional.
- Até 30 anúncios por coleta do sitemap do OnJob.io. O CareerOS extrai os
  dados estruturados da página de cada anúncio e mantém seu link de origem.

Em **Importar link**, cole a URL de uma vaga para preencher o formulário.
O CareerOS aproveita os dados de anúncios que já estão no catálogo ou em
páginas estruturadas de fontes configuradas. Para outros links, preencha os
dados no formulário ou capture a vaga aberta no navegador com a extensão.

### Páginas de carreira de empresas

Para adicionar um catálogo autorizado, configure
`CAREEROS_EMPLOYER_SITEMAP_URL` com a URL HTTPS do sitemap XML de vagas
e `CAREEROS_EMPLOYER_JOB_PATH_PREFIX` com o caminho dos anúncios, como
`/jobs/`. O sitemap deve ser do tipo `urlset` e apontar para páginas do
mesmo domínio com dados estruturados `JobPosting`. A coleta lê até 30
anúncios dessa fonte por rodada.

Para um feed autorizado RSS 2.0 ou Atom, configure `CAREEROS_JOB_FEED_URL`
com a URL HTTPS do feed de vagas. Até 500 anúncios entram na mesma busca.
O título, o link e a descrição vêm do feed. A URL precisa fornecer um
catálogo de vagas, pois o CareerOS interpreta cada entrada como um anúncio.

### Fontes que exigem credenciais

- **Gupy**. Configure `CAREEROS_GUPY_FEED_URL` e `CAREEROS_GUPY_FEED_TOKEN`
  com a URL HTTPS e o valor de autorização fornecidos pela Gupy após aprovar
  o CareerOS como parceiro. O feed inclui vagas compartilhadas com o parceiro.
- **Jooble Brasil**. Configure `CAREEROS_JOOBLE_BR_API_KEY` no servidor.
  O CareerOS envia os termos e a localização da busca ao Jooble, usa Brasil
  como localização padrão e integra até 50 resultados por consulta.
  A descrição exibida é o resumo retornado pela API. Consultas repetidas
  usam cache de 15 minutos para reduzir o consumo da cota.

Cadastre os valores diretamente no ambiente do serviço. A API do Jooble usa
a chave no caminho da requisição. Mantenha logs HTTP de saída em nível
`WARNING` ou superior quando a chave estiver configurada.

**LinkedIn, Indeed e Glassdoor via JSearch.** Para ativar a integração opcional,
configure `CAREEROS_JSEARCH_API_KEY` com uma chave autorizada para o uso previsto.
O agregador fornece um recorte de estágios de tecnologia no Brasil. A coleta faz
uma consulta por portal a cada 24 horas por instância e inclui apenas anúncios
com link do portal correspondente. Os filtros do CareerOS são aplicados ao
catálogo recebido. A cobertura depende da indexação do agregador.
[Documentação e plano gratuito do JSearch](https://www.openwebninja.com/api/jsearch)

**SerpApi e SearchApi.** Configure `CAREEROS_SERPAPI_API_KEY` para o catálogo
Google Jobs da SerpApi e `CAREEROS_SEARCHAPI_API_KEY` para os catálogos Google
Jobs e LinkedIn da SearchApi. Cada catálogo consulta estágios de tecnologia
no Brasil uma vez por dia por instância, em segundo plano. Os resultados
entram na lista do CareerOS com o portal de origem e o nome do agregador.
Links equivalentes de LinkedIn e Indeed são agrupados pelo identificador da
vaga. Cadastre as chaves apenas no ambiente do servidor.
[SerpApi](https://serpapi.com/google-jobs-api) · [SearchApi](https://www.searchapi.io/google-jobs)

Indeed também oferece um plugin para parceiros que exibe cards próprios. A API
documentada do LinkedIn permite publicação por parceiros. Para InfoJobs,
Catho, Vagas.com.br, Empregos.com.br, Trabalha Brasil, Trampos,
CIEE, Nube e SINE, ainda não há um feed de busca confirmado para o CareerOS.

## Implementação

A rota autenticada `GET /api/discovery/jobs` consulta os feeds em paralelo.
A busca ignora caixa e acentuação, reconhece termos como **estágio/intern**
e **dados/data**, e prioriza resultados com os termos no título. A empresa
tem prioridade sobre palavras encontradas apenas na descrição. Vagas com
prazo informado deixam a busca após o vencimento. Quando uma fonte falha,
vagas mantidas no catálogo recebem a indicação de abertura não reconfirmada.

URLs que diferem apenas por rastreamento são agrupados. Anúncios com título,
empresa, localização e descrição substancial idênticos também são agrupados.
Os resultados são paginados em grupos de 20. **Atualização das fontes** mostra
quantas vagas únicas cada fonte acrescentou à busca atual.
A interface informa quando uma fonte está temporariamente indisponível.

Enquanto o servidor está ativo, os feeds são atualizados a cada cinco
minutos e os sitemaps, aproximadamente a cada hora. Uma busca também
pode iniciar a coleta se o cache estiver vazio ou vencido. A Jooble é
consultada por pesquisa, com cache próprio, para respeitar a cota.

A coleta bem-sucedida substitui o catálogo da fonte. Vagas removidas da
fonte saem da busca. Se a coleta falhar, o último catálogo e seu horário
continuam disponíveis. **Atualização das fontes** mostra o estado de cada
origem, inclusive quando uma coleta por sitemap só conseguiu atualizar parte
dos anúncios. Se uma página falhar mas ainda constar no sitemap, a versão
anterior da vaga é mantida até uma nova verificação. Os catálogos também
são gravados em `data/discovery`, ou em
`CAREEROS_DISCOVERY_CACHE_DIR` quando configurado. Em hospedagem com disco
efêmero, os arquivos podem ser perdidos em reinícios ou novos deploys.
O CareerOS filtra localmente os catálogos Greenhouse, Arbeitnow e Gupy.
As descrições são convertidas em texto com quebras de
linha e limitadas a 30 mil caracteres.

- [Documentação da API pública Greenhouse](https://docs.greenhouse.io/job-board.html)
- [Documentação do feed Arbeitnow](https://www.arbeitnow.com/blog/job-board-api)
- [Feed para parceiros da Gupy](https://developers.gupy.io/docs/integra%C3%A7%C3%A3o-com-job-boards-parceiros)
- [API de busca do Jooble](https://jooblehelpcenter.freshdesk.com/pt-PT/support/solutions/articles/60001448238-documentac%C3%A3o-da-jooble-rest-api)

## Descoberta regional automática — 05/11/2026

A cidade informada inicia uma busca de portais locais por SearchApi (preferencial)
ou SerpApi, reutilizando `CAREEROS_SEARCHAPI_API_KEY` ou
`CAREEROS_SERPAPI_API_KEY` do servidor. Sem uma dessas chaves, a interface informa
que a descoberta está indisponível. Nenhum serviço foi contratado nesta etapa.
A consulta externa contém somente a cidade, sem currículo ou contato.

A coleta ocorre em segundo plano, com cache compartilhado por cidade por 24 h.
São examinados até quatro domínios e dois links de detalhes adicionais por
região. Apenas páginas com `JobPosting` válido entram como vagas e passam pelos
filtros existentes de região, termos e perfil. Portais sem formato compatível
aparecem como links “Consultar no portal”, sem inflar o número de vagas.
Isso não garante cobertura de todos os sites ou cidades; novos adaptadores
continuam necessários para fontes sem dados estruturados.

Proteções: HTTPS público com DNS validado e IP fixado na conexão, TLS verificado,
sem seguir redirecionamentos, respeito a robots.txt, limite de 1 MiB por resposta,
resolução DNS com espera de 2 s e no máximo duas threads, duas coletas simultâneas
e oito regiões em fila. Há limite de 20 consultas orgânicas por dia UTC por
processo (reinícios zeram esse contador). Cache em disco segue a mesma pasta
`CAREEROS_DISCOVERY_CACHE_DIR`; no Render gratuito é efêmero. A tela acompanha a
atualização regional enquanto a busca continua aberta.

Validação: testes com páginas simuladas de Curitiba e Recife exercitam o parser
real de JobPosting, além de cache concorrente, robots e proteção de rede.
A coleta real de novos domínios não foi validada de ponta a ponta nesta etapa:
o ambiente local não resolveu DNS direto e o painel Render exigiu novo login.
A presença das chaves em produção ainda precisa ser confirmada. O adaptador
Inova Prudente existente permanece disponível independentemente dessa camada.
