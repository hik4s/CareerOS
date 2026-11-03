# CareerOS — handoff completo da sessão de 03/11/2026

Este arquivo reúne decisões, entregas, infraestrutura, validações, limitações e
próximos passos. Complementa os documentos históricos; nenhum foi apagado.
Não contém senhas, chaves privadas, tokens de usuário ou credenciais de IA.

## 1. Estado real ao encerrar

- Produto atual: **CareerOS Cloud 1.0.0**, web, gratuito e multiusuário.
- URL publicada e observada no navegador: **https://careeros-v1.onrender.com**.
- Render e Supabase foram efetivamente criados/configurados pelos conectores.
- `/api/health`: HTTP 200, status ok, configured true, version 1.0.0.
- `/api/jobs` sem sessão: HTTP 401, Authentication required.
- `/api/auth/providers`: HTTP 200, ready false, providers vazios, oauth_setup_required.
- **Bloqueio concreto: Google/GitHub ainda estão desabilitados no Supabase.**
  O site apresenta aviso de configuração e desabilita os botões de login.
  A infraestrutura está instalada, mas ainda não se deve afirmar que o cadastro
  de usuários ou o fluxo inteiro está operacional.
- Não foram criadas contas reais, não houve chamada paga a provedores de IA,
  não houve migração de dados pessoais da instalação local.

## 2. Intenção e regras confirmadas pelo usuário

O usuário quer organizar a busca de vagas e candidaturas, analisar e adaptar
currículos com fatos reais e reduzir trabalho repetitivo. Quer permitir outras
pessoas, sem comercializar inicialmente. Não divulgará o endereço, mas rejeitou
cadastro por convite: cadastro aberto com autenticação e isolamento obrigatório.

Requisitos aprovados:

- Custo inicial zero; não contratar infraestrutura paga sem decisão explícita.
- Português do Brasil, interface profissional, aproveitando identidade visual.
- Cada pessoa conecta seu próprio provedor/modelo/chave e paga seus tokens.
- CareerOS orienta a execução e economiza tokens; não oferece uma chave global.
- Processamento por regras antes de IA; só chamar IA quando solicitado.
- Chave de IA em memória da página e da requisição, sem persistência.
- Contexto mínimo, reutilização por conta, limites de saída e histórico de uso.
- Estimativa antes da consulta e consentimento do envio ao provedor.
- Não inventar experiências, métricas, semestre ou qualificações.
- Não enviar candidaturas, aceitar termos, contornar CAPTCHA ou fazer testes.
- Preservar código, documentos e dados; branches separadas, sem alterar main.
- O usuário autorizou configurar Render/Supabase e implementar sem confirmações
  rotineiras. Essa autorização não fornece credenciais OAuth inexistentes.

## 3. Repositório, branches e commits

Repositório: https://github.com/hik4s/CareerOS, tornado público pelo usuário.

| Referência | Conteúdo/estado |
| --- | --- |
| main / 19ff2fb687bbdb5c36e39f421d3499eba38241d3 | Base original, V1 do CareerOS local, não alterada nesta sessão |
| codex/workspace-foundation-2026-11-03 / 4b1b544021175fe12e1ef6364e5f00baac53e3b1 | Versão local centralizada, adoção de schema, backup/restauração CLI |
| codex/web-mvp-2026-11-03 / 2efc55bca15aac2ee6bf48d965a1e4bfddea9d24 | MVP web, Supabase, BYOK e extensão cloud |
| PR #1, https://github.com/hik4s/CareerOS/pull/1 | Draft do MVP, não mesclado |
| codex/v1-release-2026-11-03 | **Branch servida pelo Render**; consultar HEAD atual antes de alterar |
| 7d0b66aaecbe6fdbf04120f54bf520000d4a28f0 | Preparação V1.0.0 e detecção OAuth; primeiro código V1 publicado |
| codex/desktop-paused-2026-11-03 / 43759cfdcf8295dd979f9818ae9dd8cdc3684fe6 | Snapshot incompleto do desktop, preservado e fora da implantação web |

O handoff e release notes podem estar em um commit posterior ao commit de código
V1 acima. Consultar o HEAD da branch V1 para incluir os documentos mais recentes.
Não há instalador Windows 1.0.0 nem tag/release binária criada nesta entrega.
O release web é identificado pela versão da API e pela branch publicada.

## 4. Histórico e mudanças de direção nesta sessão

1. Repositório localizado; lidos README, MASTER_PLAN_HANDOFF, release notes e testes.
2. Base local com FastAPI/SQLite/frontend estático/extensão já tinha captura,
   scoring, perfil, currículo, EML, aprendizagem, agentes conceituais e empacotamento.
3. Corrigida versão divergente: FastAPI 0.5 versus health 0.6; versão local em
   app/version.py e builds Inno compartilham a constante 0.6.0.
4. Migração inicial por PRAGMA user_version=1, transacional e idempotente; adiciona
   colunas com defaults constantes; layouts antigos incompatíveis recusados com rollback.
5. Backup/restauração offline por python -m app.workspace export/restore. ZIP com
   snapshot SQLite, uploads, manifesto SHA256. Restauração exige pasta nova,
   ajusta caminhos DOCX e recusa corrupção/traversal. Até 512 MiB; sem keyring.
6. Usuário pediu EXE único sem BAT, janela pywebview e atualização por Releases.
   Runtime, instalador e downloader começaram; foram pausados quando o usuário
   preferiu investigar hospedagem web e compatibilidade entre dispositivos.
7. Pesquisa comparou Render+Supabase, Cloudflare, Vercel, Koyeb e Railway.
   Render+Supabase escolhido para reaproveitar Python com custo zero inicial.
8. Confirmados multiusuário gratuito, cadastro aberto e IA BYOK com economia.
9. MVP web implementado isoladamente; 61 testes locais e CI passaram.
10. Conectores Render/Supabase conectados pelo usuário; organização/workspace
    selecionados. Projeto, schema, Storage e serviço criados. Preparada V1.0.0;
    novos testes elevam a suíte a 64. Deploy live e verificações reais executadas.
11. OAuth permanece uma pendência de autenticação/configuração, sem enfraquecer
    a segurança para contorná-la.

## 5. Inventário Render

| Campo | Valor |
| --- | --- |
| Workspace confirmado | My Workspace |
| Workspace ID | tea-dbkuk5vf3r2c73fvfdvg |
| Serviço | careeros-v1 |
| Service ID | srv-dbkv4rajnfac73a26hig |
| Dashboard retornado pelo Render | https://dashboard.render.com/web/srv-dbkv4rajnfac73a26hig |
| URL | https://careeros-v1.onrender.com |
| Plano | free, uma instância |
| Região | virginia |
| Runtime | Python 3.12.8 |
| Repo/branch | hik4s/CareerOS, codex/v1-release-2026-11-03 |
| Build | pip install -r requirements-cloud.txt |
| Start | uvicorn app.cloud.main:app --host 0.0.0.0 --port $PORT |
| Primeiro deploy V1 | dep-dbkv4rqjnfac73a26khg, depois desativado pela atualização de env |
| Deploy com env completa, validado live | dep-dbkv50923ouc7391stpg |
| Deploy automático real | yes / trigger commit |

Variáveis configuradas no Render: PYTHON_VERSION, SUPABASE_URL,
SUPABASE_ANON_KEY (usada uma chave **publishable** moderna válida), APP_URL e
ALLOWED_ORIGINS. APP_URL/ALLOWED_ORIGINS apontam para a URL pública acima.
Não foram configuradas chaves de IA, service_role ou senha de banco.

`render.yaml` declara checksPass, mas a criação pelo conector só suporta yes/no
e deixou o recurso real em trigger commit. Logo não afirmar que o serviço real
aguarda CI: hoje publica cada commit. A mudança para checksPass e health check
específico /api/health exige configuração adicional no dashboard/API apropriada.
O healthCheckPath do recurso criado está vazio; a raiz responde normalmente.
Atualização de env pelo conector já solicita deploy; não disparar duplicado.

## 6. Inventário Supabase

| Campo | Valor |
| --- | --- |
| Organização confirmada | CareerOS |
| Organization ID | wvhmsjyzmrhxbmicsvde |
| Plano/custo cotado | free, US$ 0/mês para projeto |
| Nome do projeto | CareerOS |
| Project ref / ID | jylrurstgybvzgsikiiv |
| Região | sa-east-1 (São Paulo) |
| Estado na criação | ACTIVE_HEALTHY |
| API URL | https://jylrurstgybvzgsikiiv.supabase.co |
| Callback OAuth a cadastrar | https://jylrurstgybvzgsikiiv.supabase.co/auth/v1/callback |
| Bucket | career-resumes, privado, limite 5242880 bytes |
| Migração aplicada | 20261103141352 / careeros_cloud_initial |
| SQL correspondente | supabase/migrations/202611030001_cloud.sql |

Tabelas: cloud_profiles, cloud_jobs, cloud_ai_runs e cloud_resumes. Todas têm
user_id associado a auth.users e RLS ativa. Políticas exigem auth.uid=user_id
nas leituras e escritas. Backend usa chave pública+Bearer do usuário; nunca
service_role. Storage exige pasta do próprio UUID. Há trigger serializado para
limite de dez currículos por conta e bucket com MIME types PDF/DOCX.

Auditoria de segurança: lints vazios. Performance: apenas dois avisos INFO de
índices ainda não usados (cloud_ai_cache_idx e cloud_resumes_owner_idx), esperado
para banco novo; não removê-los apenas por isso. Referência do aviso:
https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index

O teste supabase/tests/cloud_rls.sql foi realmente executado com sucesso no
projeto, com duas contas sintéticas e rollback. Testou leitura, inserção,
alteração e exclusão cruzada. Consulta posterior confirmou zero usuários de
teste restantes. Não houve exclusão de dados do usuário.

## 7. Bloqueio de login: próximos passos obrigatórios

GET público de settings do Auth foi consultado com a chave pública. Retorno:
google=false, github=false, anonymous_users=false, email=true,
disable_signup=false, mailer_autoconfirm=false. Nenhum OAuth habilitado.

O conector Supabase disponível não oferece PATCH de Auth config ou cadastro de
clientes Google/GitHub. Não foi encontrado token de Management API; não procurar
credenciais internas nem reutilizar tokens de conectores. O dashboard aberto no
navegador mostrou uma tela de login. O usuário forneceu credenciais pelo formulário
seguro, sem exposição ao agente; a submissão chegou a um desafio hCaptcha de
arrastar imagem, ainda sem sinal positivo de autenticação. Não houve tentativa
de resolver o CAPTCHA sem confirmação no momento; foi preparado handoff para
interação do usuário. Autorizações gerais
do usuário não substituem login real nem client IDs/client secrets OAuth.

Para liberar acesso:

1. Autenticar legitimamente no painel Supabase da organização correta.
2. Em Auth URL Configuration, configurar Site URL https://careeros-v1.onrender.com
   e Redirect URL https://careeros-v1.onrender.com/.
3. Registrar app OAuth no GitHub Developer Settings e/ou cliente Google Cloud.
   Homepage/origem: https://careeros-v1.onrender.com. Callback: URL Supabase acima.
4. Configurar client ID e client secret diretamente no provedor Supabase e habilitar.
   Nunca colocar secrets OAuth no GitHub, Render, frontend ou handoff.
5. Reabrir o site: /api/auth/providers deve listar o provedor. Os botões são
   habilitados automaticamente, sem alteração de código.
6. Testar login com duas contas reais e recursos privados antes de chamar V1
   plenamente utilizável. Testar também refresh, logout e extensão.

Não desativar confirmação de e-mail, liberar usuário anônimo ou inventar conta
de demonstração para esconder a pendência. SMTP padrão não é uma solução para
cadastro público amplo; Google/GitHub seguem sendo o desenho aprovado.

## 8. Arquitetura e arquivos importantes

- app/cloud/main.py: entrada web, rotas perfil/vagas/currículos/config/health,
  detecção OAuth, validações e download do ZIP da extensão.
- app/cloud/auth.py: valida Bearer no Supabase /auth/v1/user em cada requisição.
- app/cloud/store.py: REST Supabase, filtros por dono e propagação do JWT.
- app/cloud/config.py: SUPABASE_URL e SUPABASE_ANON_KEY; ALLOWED_ORIGINS ou alias
  CORS_ORIGINS. Recusa secret/service-role e redige configuração inválida.
- app/cloud/version.py: versão CLOUD 1.0.0; versão local permanece independente.
- app/cloud/ai.py: regras, contexto, adaptadores IA, cache, estimativa e histórico.
- app/cloud/resume_parser.py: subprocesso com timeout/limites para PDF/DOCX.
- app/cloud/static: interface pt-BR responsiva, sidebar azul-marinho, violeta,
  páginas visão geral/vagas/perfil/currículos/IA/captura e OAuth Supabase.
- static/vendor/supabase.js: SDK fixado em 2.49.1, licença MIT e atribuição incluídas.
- extension-cloud: MV3 Chrome/Edge autenticada para captura; extensão local intacta.
- requirements-cloud.txt: runtime sem dependências desktop.
- render.yaml e .github/workflows/cloud-ci.yml: implantação e verificações.
- docs/WEB_MVP.md, docs/WEB_MVP_DESIGN.md e docs/RELEASE_1.0.0.md.

API principal: GET /api/config, /api/health, /api/auth/providers; GET/PUT profile;
CRUD jobs e POST jobs/{UUID}/analyze; GET metrics; upload/list/download/delete
resumes; POST ai/estimate e ai/run; GET ai/history; GET /api/extension.zip.

## 9. IA: comportamento e limites reais

Provedores: heuristic (sem chamada), OpenAI Chat Completions, Anthropic Messages
e DeepSeek Chat Completions. Identificador do modelo é informado pelo usuário,
não pressupõe modelos específicos disponíveis na conta. Endpoints fixos;
sem URL de proxy arbitrária. Nenhum teste utilizou créditos ou chave real.

Chave é guardada só em variável JS da página e enviada ao backend apenas para
gerar. Não vai a banco, Storage, histórico, localStorage/sessionStorage ou env.
Troca de conta/logout limpa estado; respostas atrasadas são verificadas pelo dono.
Token de autenticação do app é gerenciado pelo Supabase SDK, separadamente da chave IA.

Fluxo: perfil+vaga+currículo opcional → estimativa → consentimento explícito →
geração. Tarefas: avaliação, resumo, carta e revisão pontual. Contexto até 40
skills, seis evidências, 6.000 caracteres da vaga, 6.000 do currículo, instrução
até 2.000 e trecho anterior até 6.000. Contatos não são selecionados do perfil;
email/links/padrões comuns de telefone são retirados do trecho do currículo,
mas isso não garante anonimização integral de texto livre.

Tokens de entrada estimados por caracteres/3. Saída entre 128 e 2.048 tokens.
Preços opcionais informados pelo usuário em USD/milhão, sem atualização automática,
sem teto financeiro garantido ou promessa de reproduzir descontos/impostos.
Histórico registra tokens reais quando o provedor informa e custo estimado.
Cache persistido por conta+hash de contexto/tarefa/provedor/modelo/limite; chaves
não entram no hash. Duplicações simultâneas são controladas no processo único.
Sem retries pagos automáticos; timeouts avisam que a consulta pode ter sido cobrada.
Resposta já paga é exibida mesmo se salvar histórico falhar.

Não há roteamento automático de modelos por preço nesta V1; escolha é explícita.
Não integra sessão local do Codex/Claude CLI nem converte Plus/assinatura em API.

## 10. Arquivos e extensão

Upload até 5 MiB, dez currículos por conta, PDF/DOCX. Parser isolado com timeout
15s; Linux limita memória a 192 MiB e CPU a 10s. PDF até 30 páginas, extração até
200.000 caracteres; DOCX expandido até 25 MiB. Não há OCR para PDF digitalizado.
Downloads via URL temporária de 60s. Contexto IA é recortado separadamente.

Extensão cloud: conexão por origem HTTPS explícita e token de sessão copiado do
painel. Solicita permissão apenas para a origem escolhida; token somente em
chrome.storage.session, vinculado à origem e limpo ao desconectar/expirar.
MVP não renova token automaticamente: recopiá-lo após expiração. JWT pode permanecer
válido até expirar após logout do painel; desconectar também no popup.
Token dá acesso à conta e não deve ser compartilhado. Chave de IA nunca entra na extensão.
Captura por clique, revisão humana; não há autopreenchimento cloud nesta V1.

## 11. Verificações e limitações de homologação

- 64 testes Python aprovados na V1, com avisos de depreciação não bloqueantes.
- CI remoto da preparação V1 passou (run 41652051193); commits de documentação
  subsequentes podem gerar novos runs. Conferir status do HEAD final.
- Node syntax checks, compileall e diff-check aprovados.
- HTTP smoke dos assets, página e ZIP aprovado.
- Página pública observada no navegador real após deploy; aviso OAuth correto,
  botões desabilitados quando não há provedor. Um log de extensão interna do
  navegador não correspondeu a erro do código do CareerOS.
- RLS real testada em SQL; quatro tabelas com relrowsecurity=true e bucket privado.
- Não houve login OAuth real, Storage real por sessão de usuário, interação de
  extensão em site de vagas ou chamada paga de IA. Não declarar esses itens testados.
- Planos gratuitos podem hibernar/pausar e têm cotas. Sem disco Render para dados.
- Backup automático de produção cloud ainda não implementado; backup CLI anterior
  é apenas do workspace SQLite local e não faz backup do Supabase.
- PWA/offline/sincronização não implementados; desktop está pausado.

## 12. Preservação do desktop e da versão local

Snapshot desktop separado: codex/desktop-paused-2026-11-03. Inclui pywebview,
mutex Local\\CareerOS.Desktop, readiness/shutdown do servidor local 8765,
cópia segura de dados legados, PyInstaller, Inno Setup, bootstrapper WebView2
verificado por assinatura Microsoft, downgrade guard, espera do mutex e
workflow Windows com instalador+checksum e draft Release.

Atualizador implementado parcialmente: consulta Releases estáveis públicas,
compara versões, valida origem/nome/tamanho/SHA256/MZ e baixa; trata offline.
Integração app.desktop_actions ainda ausente, portanto não há app desktop
completo/funcional nem build Windows homologado. O usuário escolheu web depois;
não misturar esse snapshot no deploy. docs/DESKTOP_PAUSED.md registra o estado.

A base local histórica continua com app/main.py, app/db.py, app/workspace.py,
app/static e extension. Não apagar diretórios data, uploads ou documentos.

## 13. Ambiente de desenvolvimento e retomada

Checkout web nesta sessão: /workspace/scratch/b0e059c79f62/CareerOS-web.
Checkout desktop pausado: /workspace/scratch/b0e059c79f62/CareerOS.
Paths scratch são temporários; GitHub é a fonte persistente para código.
História Git local foi reconstruída pelo conector: hashes locais de baseline
podem diferir dos remotos. **Clonar a branch remota em um novo ambiente** em vez
de forçar push da história local sobre o GitHub.

Teste cloud: python -m pytest -q tests/test_cloud*.py.
Suíte completa exige também dependências legadas (feedparser, keyring etc.).
Iniciar web: python -m uvicorn app.cloud.main:app --host 127.0.0.1 --port 8000,
com configuração Supabase disponível no ambiente do processo. Não salvar chaves
de usuário em .env. Para produção usar o startCommand do Render.

Durante a sessão o ambiente reiniciou e perdeu pacotes instalados/handles de
navegador, mas preservou os arquivos. Reinstaladas dependências. Uma chamada
Render foi rejeitada por mudança do catálogo, não por regra de segurança; foi
confirmada ausência de serviço antes da repetição, evitando duplicação.

## 14. Ordem recomendada no próximo chat

1. Ler este arquivo, docs/RELEASE_1.0.0.md e docs/WEB_MVP.md.
2. Se houver handoff de navegador ativo, concluir o CAPTCHA e verificar login
   legítimo antes de qualquer configuração. Não presumir sessão autenticada.
3. Conferir GitHub HEAD/CI e serviço Render existente; **não criar duplicatas**.
3. Resolver login legítimo do dashboard e clientes OAuth, Site URL e redirects.
4. Confirmar /api/auth/providers ready=true e testar duas contas reais.
5. Homologar perfil, CRUD, currículo privado, análise local e extensão.
6. Mediante chave do próprio usuário na interface, homologar uma consulta pequena
   e a repetição em cache; conferir tokens/custo sem registrar chave.
7. Ajustar autoDeploy real para checksPass e healthCheckPath /api/health se houver
   acesso apropriado; não confundir yaml com configuração já aplicada ao recurso.
8. Priorizar exportação/backup cloud, exclusão de conta/dados, quotas e proteção
   contra abuso antes de ampliar o público. PWA/offline somente depois.
9. Atualizar este handoff e a documentação com evidências, sem apagar histórico.

## 15. Prompt pronto para retomada

> Continue o CareerOS Cloud V1 a partir da branch codex/v1-release-2026-11-03 do
> repositório hik4s/CareerOS. Leia HANDOFF_CAREEROS_2026-11-03.md inteiro antes de
> agir. O site https://careeros-v1.onrender.com já está publicado no Render free
> e conectado ao Supabase jylrurstgybvzgsikiiv, com schema/RLS/Storage configurados.
> A pendência principal é habilitar clientes OAuth Google/GitHub e configurar Site
> URL/redirects, pois os provedores estavam false. Não crie recursos duplicados,
> não pague infraestrutura, não desabilite autenticação e não persista chaves IA.
> Há 64 testes locais aprovados e RLS real testada com rollback. Preserve main e
> desktop pausado. Valide o que for concluído e registre limitações honestamente.

## 16. Atualização final do acesso ao painel

O login via formulário seguro foi submetido pelo usuário, mas o Supabase exibiu
um hCaptcha com desafio visual. O agente não recebeu senhas nem leu valores
de credenciais. A autenticação permanece não confirmada. A autorização geral
não permite resolver o CAPTCHA sem confirmação específica no momento. O usuário
pode concluir a interação na aba entregue para destravar a configuração OAuth.
Não recomeçar a criação de projeto/serviço, pois ambos já existem e estão ativos.


## 17. Continuação: versão Cloud 1.1.0 e exportação manual da conta

Em 03/11/2026 o usuário pediu continuar implementando. A aba Supabase foi
reaberta e ainda exibia hCaptcha, com login não confirmado. O agente não
resolveu o desafio nem presumiu autenticação. Não repetir a criação de projeto
ou serviço e não enfraquecer Auth para contornar essa pendência.

Foi implementada a exportação manual pelo painel, independente da liberação
OAuth. Versão cloud: 1.1.0 (extensão continua 1.0.0, sem alteração de formato).
Branch de desenvolvimento: codex/cloud-account-export-2026-11-03. Integração
prevista na branch já servida codex/v1-release-2026-11-03 após aprovação do CI.
Consultar os HEADs remotos e o health do Render para confirmar a publicação;
não inferir deploy somente pela existência deste documento.

Novos arquivos: app/cloud/export.py, tests/test_cloud_export.py e
 docs/RELEASE_1.1.0.md. Alterados store.py (download binário privado e limitado),
main.py (router), frontend (aba Meus dados, download ZIP), versão e teste de release.

GET /api/workspace/export.zip requer sessão autenticada. O ZIP contém:
- workspace.json com perfil, todas as vagas, histórico de IA e metadados de currículos;
- resumes/<UUID>.pdf|docx com os arquivos privados originais;
- manifest.json com hashes SHA256 dos arquivos exportados.

Cada consulta conserva filtro de owner e Bearer, com validação do dono a cada
página. Caminhos de arquivos têm prefixo UUID da conta; não são usados nomes
originais como caminhos do ZIP. Não exporta chaves de IA, tokens, senhas Auth,
service_role nem dados de outra conta. UI confere dono antes de iniciar e depois
do download para descartar resposta que chegue após troca de conta.

Limites: 64 MiB total descompactado, 10.000 registros por categoria, arquivos
individuais até 5 MiB, construção de um ZIP por vez no processo. Paginação até
página vazia evita truncamento quando a API impõe páginas menores. Qualquer
falha de Storage cancela o ZIP inteiro, sem omissão silenciosa. Tempfiles
removidos após resposta concluída ou erro. Não constitui snapshot transacional,
backup automático, backup administrativo de todo Supabase nem restauração.
O usuário deve guardar o ZIP, que contém dados pessoais sem criptografia.

Validação desta continuação: 73 testes locais Python aprovados, nove de exportação,
Node syntax check e git diff --check aprovados. Testes cobrem dados e arquivos no
ZIP, integridade, rejeição de owner estrangeiro, paginação inclusive com teto
menor no servidor, limite de tamanho, limpeza de temporários e autenticação.
O teste de defesa por proprietário inicialmente detectou uma leitura que só
validava depois de acumular todas as páginas; a validação foi movida para cada
página e a suíte passou. Ainda não houve teste de exportação com OAuth real,
pois o login continua bloqueado na verificação de segurança.

Para testar manualmente após OAuth: entrar, salvar perfil e vaga, enviar currículo,
gerar uma análise por regras, abrir Meus dados e baixar o ZIP; verificar registros,
arquivo e hashes. Outra conta não pode obter a mesma exportação ou currículo.
A conta continua intacta após exportar. Próximas prioridades permanecem OAuth,
homologação real e backup/restauração cloud com desenho específico.


## 18. Publicação confirmada da 1.1.0

- PR #3: https://github.com/hik4s/CareerOS/pull/3, integrado na branch publicada;
  main continua intacta.
- Commit de implementação: d7f661764cfcf73a874caefb51bbac964af3f4d6.
- Merge na branch codex/v1-release-2026-11-03:
  328a9f79fbe67cac0af4524821442fc94d66075e.
- Checks GitHub 41662048473 e 41662158785 passaram antes da integração.
- Render NÃO iniciou deploy automático após o merge, apesar de exibir yes/commit.
  Foi necessário solicitar deploy manual pelo conector, sem nova alteração de código.
  A integração Git do Render precisa ser validada no painel; não prometer que
  próximos pushes serão publicados automaticamente com a configuração atual.
- Deploy dep-dbl1fnff3r2c7386ateg confirmado LIVE em 03/11/2026.
- Health HTTP real confirmou status ok, configured true, version 1.1.0.
- A aba Meus dados e a API de exportação fazem parte desse commit publicado.
  A homologação com uma sessão de usuário real continua pendente de OAuth.
- Nenhum recurso pago foi criado e não houve alteração de schema nesta continuação.

Este arquivo mantém as informações da V1 como histórico e acrescenta as mudanças
sem apagar decisões ou evidências anteriores. Usar esta seção como estado mais
recente de código/deploy, preservando a pendência de autenticação da seção 7.


## 19. Login e correção de resiliência da autenticação (1.1.1)

O usuário concluiu o hCaptcha e o painel Supabase confirmou a sessão autenticada.
O projeto CareerOS foi aberto. Google e GitHub continuam Disabled. O formulário
GitHub está sem Client ID/Client Secret. Nenhum cliente OAuth foi criado nem
credencial salva. O navegador GitHub não estava autenticado; a solicitação segura
de login foi bloqueada pela revisão automática por limite de uso, antes de
executar a ação. Não contornar o bloqueio por outro canal ou inventar credenciais.
Site URL e redirects ainda precisam ser verificados/configurados no painel.

Na continuação, corrigido require_user: indisponibilidade, limite do Supabase,
falha de rede e resposta inválida agora resultam em 503 + Retry-After: 30, sem
acesso ao banco e sem repetir chamadas. Somente 401/403 do serviço de Auth
resultam em sessão inválida (401 + WWW-Authenticate). Nenhuma falha libera acesso
a dados. Mensagens de erro não expõem token nem resposta privada do upstream.
Respostas /api/* usam Cache-Control: no-store, inclusive erros e downloads.
Todas as respostas incluem Referrer-Policy: no-referrer e nosniff.

Novos testes em tests/test_cloud_auth_resilience.py reproduziram dez falhas antes
da implementação e passaram depois. A suíte cloud passou com 59 testes.
A suíte completa inicialmente não coletou test_core.py por falta de feedparser
no ambiente; verificar a execução final antes de afirmar que toda a suíte passou.
O ambiente recém-instalado usa Starlette 1.10.0 e emite aviso de depreciação do
TestClient com httpx; não há mudança de dependências nesta correção.

Branch: codex/auth-resilience-2026-11-03. Versão alvo: 1.1.1. Consultar GitHub e
Render para confirmar integração e publicação; este registro não prova deploy.

Validação final local: após instalar feedparser no ambiente, a suíte completa
passou com 83 testes e três avisos de depreciação (Starlette TestClient/httpx
e lifecycle on_event legado do desktop). Não foram ocultados avisos.

A revisão detectou que respostas 500 inesperadas contornam o middleware de
cabeçalhos. Corrigido com handler genérico de erro sanitizado e os mesmos
cabeçalhos de privacidade. Regressão reproduzida antes do ajuste; suíte final
84 testes aprovados (11 novos), três avisos de depreciação. PR #4.
