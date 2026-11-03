# JobsFinder Cloud MVP

O modo web usa FastAPI com Supabase Auth, PostgreSQL e Storage privados via REST. O modo local continua disponível pelo fluxo do README. A entrada web é `app.cloud.main:app`; não execute `app.main:app` no Render. O servidor não precisa de SQLite persistente, disco Render, instalador Windows ou chaves globais de provedores de IA.

## 1. Criar e preparar o Supabase

1. Crie um projeto Supabase e guarde a senha do banco no seu gerenciador de segredos. Aguarde o provisionamento.
2. Em **Project Settings → API**, copie a URL do projeto (`https://<project-ref>.supabase.co`) e a chave pública **anon**. Nunca use `service_role`, secret key ou senha de banco no JobsFinder, no frontend ou na extensão.
3. Abra **SQL Editor → New query**, cole o conteúdo integral de `supabase/migrations/202611030001_cloud.sql` e execute uma vez em um projeto novo. Alternativa com Supabase CLI: associe o projeto e execute `supabase db push`. A migração cria tabelas, índices, RLS por `auth.uid()`, limites de currículos e bucket **privado** `career-resumes`, com acesso por pasta do usuário. Não torne o bucket público e não desative RLS.
4. Em **Authentication → Providers**, habilite Google e GitHub. Crie as credenciais OAuth nos consoles de cada provedor e configure o callback de ambos como `https://<project-ref>.supabase.co/auth/v1/callback`. Para Google, configure também as origens JavaScript exigidas pelo console. Os client secrets pertencem ao Supabase, não ao Render ou ao repositório.
5. Em **Authentication → URL Configuration**, configure **Site URL** para a origem pública do JobsFinder (`APP_URL`, por exemplo `https://jobsfinder-b5a9.onrender.com`). Adicione essa origem e o endereço de retorno usado pelo frontend à **Redirect URLs** permitida. Para o frontend atual, permita `https://jobsfinder-b5a9.onrender.com/`. Para desenvolvimento, adicione explicitamente `http://localhost:8000/` (ou a porta que usar). Não use curingas amplos de produção.

## 2. Publicar no Render

1. Envie este repositório à sua conta GitHub sem `.env`, tokens, currículos ou outros arquivos pessoais.
2. No Render, escolha **New → Blueprint**, conecte o repositório e selecione `render.yaml`. A integração Git requer sua autenticação e a escolha do repositório no Render. Também é possível criar manualmente um **Web Service**, runtime Python, plano Free, com os comandos abaixo.
3. Configure as variáveis do serviço:

| Variável | Valor |
| --- | --- |
| `SUPABASE_URL` | URL HTTPS do seu projeto Supabase |
| `SUPABASE_ANON_KEY` | Chave pública anon do mesmo projeto |
| `APP_URL` | Origem HTTPS pública deste serviço Render, sem caminho |
| `ALLOWED_ORIGINS` | Origens HTTPS permitidas separadas por vírgula; inclua `APP_URL` |

4. Build: `pip install -r requirements-cloud.txt`. Start: `uvicorn app.cloud.main:app --host 0.0.0.0 --port $PORT`. Health check: `/api/health`. Use uma instância gratuita e um único worker; não adicione disco ou SQLite. O serviço pode hibernar conforme as regras do plano gratuito.
5. Confirme `/api/config` com `configured: true`, abra o painel, entre com Google e GitHub e confira a conta autenticada. Variáveis ausentes não devem abrir acesso anônimo: as rotas privadas recusam acesso. Ajuste Site URL/Redirect URLs no Supabase para o domínio final antes do teste OAuth.

O projeto inclui configuração de publicação, mas esta entrega não cria projeto Supabase, contas OAuth nem serviço Render sem as contas/credenciais do proprietário. Nenhuma URL publicada é presumida.

## 3. Extensão autenticada

Baixe **Extensão** no painel (`/api/extension.zip`) e siga `extension-cloud/README.md`. A pasta `extension` é a versão local e permanece separada. A versão cloud usa HTTPS por padrão, autorização opcional somente à origem escolhida e `POST /api/jobs` com Bearer do usuário. Na conexão, copie o token de acesso exibido pelo botão do painel e cole no popup. Esse token dá acesso à conta: copie em dispositivo próprio e não compartilhe. O token fica somente na sessão do navegador, expira e não tem atualização automática neste MVP. Desconecte também na extensão ao sair; um JWT emitido pode continuar válido até sua expiração.

A captura envia título, empresa, URL, localização, modalidade e descrição para revisão. Não há preenchimento automático ou envio de candidatura na extensão cloud. Não coloque chaves BYOK no popup ou nas variáveis do servidor. As chaves de provedor pertencem ao fluxo autenticado de IA e não à extensão.

## 4. Verificação antes de uso

Execute `pip install -r requirements-cloud.txt pytest` e `python -m pytest -q tests/test_cloud*.py`. O workflow **Cloud checks** faz as verificações sem credenciais reais. Para smoke test real, use duas contas distintas: crie uma vaga/currículo em A e confirme que B não consegue ler, alterar ou baixar o recurso de A; confira também token expirado e ausência de token. No Storage confirme o bucket privado. Apague os dados de teste depois.

Os testes locais não substituem aplicar e verificar as políticas no projeto Supabase real. Faça backup e revisão de políticas antes de disponibilizar dados pessoais em produção. Não publique logs com cabeçalhos Authorization, tokens, chaves BYOK ou conteúdo de currículos.


## 5. IA por usuário (BYOK)

O MVP oferece OpenAI (Chat Completions), Anthropic (Messages) e DeepSeek
(Chat Completions). Informe o identificador exato de um modelo compatível na sua
conta. A chave é solicitada na tela, fica na memória da página e acompanha somente
a requisição de geração ao backend; não é salva em banco, histórico, Storage,
localStorage ou variáveis do Render. Atualizar a página ou sair apaga essa chave.
O backend a utiliza apenas na chamada HTTPS ao endpoint fixo do provedor.

Escolha uma tarefa, vaga e opcionalmente currículo; faça a estimativa e autorize
explicitamente o envio antes de gerar. O contexto contém campos profissionais
selecionados, até seis evidências, até 6.000 caracteres da descrição e até 6.000
caracteres do currículo. E-mail, links e padrões comuns de telefone são removidos
do trecho do currículo; isso não garante anonimização integral do texto livre.
O perfil não envia campos de contato. Revisão pontual usa o trecho fornecido,
em vez de acumular um histórico inteiro de conversa.

A contagem de entrada é aproximada (caracteres/3), sem chamada extra de IA. O
limite de saída vai ao provedor. Custos são opcionais e usam preços que a própria
pessoa informa em USD/milhão de tokens. A estimativa não é uma cotação automática
nem um teto financeiro garantido. Tokens reais, quando fornecidos, ficam no
histórico. Modelo e provedor são escolhidos explicitamente; não há roteamento
pago automático, modelo premium automático ou repetição automática de falhas.

Consultas idênticas reutilizam resultados dentro da mesma conta, inclusive entre
sessões. Mudanças no contexto, tarefa, modelo ou limite invalidam o cache. O cache
não é compartilhado com outras pessoas. Se o provedor responder mas o histórico
falhar, o resultado ainda é exibido para evitar uma segunda cobrança desnecessária.

A análise por regras, sem API, continua disponível. Não usa Codex/Claude CLI do
computador do usuário nem transforma uma assinatura de aplicativo em crédito API.

## 6. Estado desta entrega

61 testes Python aprovados na sessão, incluindo 37 testes cloud/extensão e suíte
local anterior. Verificadas respostas HTTP da página, scripts e ZIP da extensão;
JavaScript compilado com Node sem erros. Sem credenciais reais, ainda não foram
executados login OAuth real, teste RLS no Supabase, upload real de Storage ou
consulta cobrada a um provedor. A instalação do navegador de testes falhou;
layout e navegação precisam de homologação no navegador conectado.

O arquivo `supabase/tests/cloud_rls.sql` testa duas contas com rollback e deve
ser executado no banco de teste após a migração. O Render está preparado para
publicar alterações da branch conectada somente após checks de CI aprovados
(`autoDeployTrigger: checksPass`); a integração Git precisa ser autorizada na sua
conta Render. Comece usando a branch web MVP e mantenha a versão local separada.

O processamento de PDF/DOCX roda em processo separado com timeout de 15 segundos.
No Linux, memória e CPU do parser são limitadas; PDFs acima de 30 páginas são
recusados, assim como DOCX com conteúdo expandido acima de 25 MiB.


## Exportação da conta (1.1.0)

Em **Meus dados**, baixe o ZIP autenticado com registros e currículos privados.
Inclui manifesto SHA256. Limites e cuidados: [RELEASE_1.1.0.md](RELEASE_1.1.0.md).
A exportação é manual; não há importação/restauração cloud nesta versão.
