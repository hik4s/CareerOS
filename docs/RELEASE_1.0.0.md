# CareerOS Cloud 1.0.0 — 03/11/2026

V1 web publicada em https://careeros-v1.onrender.com.

## Implementado

- FastAPI web separado do aplicativo local.
- Perfil e vagas por usuário, CRUD, etapas e análise heurística.
- Currículos PDF/DOCX em Storage privado, links temporários e limite por usuário.
- Autenticação preparada para Google/GitHub por Supabase Auth.
- IA BYOK: OpenAI, Anthropic e DeepSeek; chave somente na sessão e requisição.
- Estimativa prévia, confirmação de envio, contexto limitado, cache por conta e histórico.
- Extensão cloud autenticada para captura manual, separada da extensão local.
- Processamento de documentos isolado, com timeout e limites de recursos.
- Render gratuito com deploy automático por commit na branch V1.
- Detecção real dos provedores OAuth; botões indisponíveis não simulam login.

## Validação realizada

- 64 testes Python aprovados; checks GitHub da preparação V1 aprovados.
- Migração aplicada ao Supabase; teste SQL de isolamento entre duas contas passou com rollback.
- RLS habilitada nas quatro tabelas; bucket privado com limite de 5 MiB.
- Auditoria Supabase sem alertas de segurança.
- Deploy Render live, página observada no navegador, health HTTP 200 versão 1.0.0.
- API protegida retorna 401 sem Bearer.

## Bloqueio de ativação

A infraestrutura está publicada, mas o cadastro/login social ainda NÃO está
operacional. O Supabase confirmou google=false e github=false. É necessário
registrar/configurar clientes OAuth, habilitá-los e definir Site URL/redirects.
As conexões atuais não expõem edição de Auth config; o dashboard pediu login.
Não houve acesso anônimo, remoção de autenticação ou simulação de contas para
contornar esse bloqueio. Login real e uso ponta a ponta permanecem pendentes.

Não foi executada chamada paga de IA. Planos gratuitos têm cotas e hibernação.
Ver HANDOFF_CAREEROS_2026-11-03.md para inventário completo e retomada.
