# CareerOS web MVP — decisões aprovadas em 03/11/2026

Objetivo: aplicativo gratuito e multiusuário, acessível pelo navegador, sem instalador.
Cadastro aberto por OAuth Google/GitHub. Cada conta acessa apenas seus dados.
Render hospeda FastAPI; Supabase fornece Auth, PostgreSQL com RLS e arquivos privados.
Preservar a versão local e o trabalho desktop pausado em outra branch.

Alternativas consideradas: desktop + instalador (acesso dependente de sistema e instalação),
Cloudflare + Supabase (maior adaptação das dependências Python) e Render + Supabase
(escolhido para reaproveitar Python). Planos gratuitos têm cotas e pausas, sem garantia de disponibilidade.

MVP: perfil, vagas CRUD e etapas, score heurístico, upload/download privado PDF/DOCX,
captura autenticada pela extensão, IA BYOK, estimativa prévia e histórico de consumo.
IA: usuário informa provedor, modelo e chave; chave somente em memória na página e
na requisição corrente do backend. Sem keyring, armazenamento de chave ou chave global.
Endpoints de provedores fixos; sem proxies arbitrários. Resultado reutilizado por
conta e hash dos dados relevantes. Não inventar experiência, nem enviar candidaturas.
Preços opcionais informados pelo usuário; estimativa não é cobrança ou teto garantido.

Não incluir nesta etapa: sincronização offline, instalação desktop, Graph/Outlook,
pagamentos, tarefas agendadas, crawler autônomo ou bypass de testes/CAPTCHA.
Autenticação e isolamento não dependem de o endereço ser pouco divulgado.

Plano de execução: (1) Auth/REST/RLS e dados; (2) interface web; (3) BYOK com controle
de contexto, cache e testes; (4) extensão e configuração Render; (5) testes integrados,
revisão e branch GitHub. Publicação real requer contas Supabase/Render configuradas.
