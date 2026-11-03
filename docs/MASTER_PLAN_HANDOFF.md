# Career OS: Master Plan e handoff completo

> Atualização de 03/11/2026: veja [WORKSPACE_TRANSFER.md](WORKSPACE_TRANSFER.md) para a versão centralizada, migrações iniciais, transferência offline e 24 testes atuais. Os itens históricos abaixo descrevem a base anterior.

> Documento de continuidade para outra IA ou outra máquina. Este arquivo consolida contexto, decisões, evolução, arquitetura, funcionalidades, design, restrições, preferências do usuário e próximos passos.

## 1. Contexto humano e objetivo

O projeto nasceu da dificuldade de obter entrevistas para estágio em desenvolvimento, automação ou TI, apesar de já existirem:

- LinkedIn atualizado;
- GitHub sanitizado;
- projeto real de automação em Python;
- experiência prática com Playwright, dashboards, logs e processamento de arquivos;
- graduação em Bacharelado em Tecnologia da Informação, atualmente no 2º termo.

O usuário procura principalmente:

- estágio em desenvolvimento;
- estágio em automação;
- estágio em TI;
- QA;
- dados/BI;
- Python e back-end;
- vagas remotas ou na região de Presidente Prudente;
- preferência por bolsa acima de R$ 2.000 e/ou vale-alimentação/refeição.

O gargalo identificado foi a combinação de:

1. filtros automáticos por semestre e previsão de formatura;
2. grande volume de candidaturas necessário;
3. formulários repetitivos;
4. currículo genérico para vagas diferentes;
5. falta de métricas para distinguir problema de elegibilidade, currículo ou estratégia.

## 2. Restrições e princípios definidos

- Não mentir semestre, curso ou experiência.
- Não inventar métricas ou tecnologias.
- Não expor dados internos da empresa, relatórios, sistemas, caminhos, credenciais ou nomes confidenciais.
- Não contornar CAPTCHA.
- Não executar testes comportamentais ou técnicos.
- Não aceitar termos automaticamente.
- Não clicar em enviar candidatura sem revisão humana.
- Usar automação para reduzir trabalho repetitivo, não para gerar spam.
- Usar evidências reais para cada afirmação profissional.
- Manter o projeto local-first e adequado para portfólio.

## 3. Preferências de trabalho do usuário

- Respostas e implementações práticas.
- Arquivos completos e prontos para copiar ou executar.
- Mudanças focadas, sem quebrar funcionalidades existentes.
- Estrutura clara por arquivo e função.
- Validação com testes ao final.
- Interface profissional para portfólio.
- Automação robusta, mas com controles manuais em pontos críticos.
- Inicialização simples para Windows.
- Sanitização rigorosa antes de publicar no GitHub.

## 4. Evolução do produto

### Etapa 0: investigação de mercado

Foram pesquisadas vagas de estágio em Presidente Prudente e remotas. O filtro de semestre apareceu como obstáculo real. A estratégia mudou de Jovem Aprendiz administrativo para estágio em desenvolvimento, automação, QA, dados e TI.

### Etapa 1: MVP inicial

Objetivo: organizar o processo.

Implementado:

- FastAPI;
- SQLite;
- perfil estruturado;
- cadastro manual de vagas;
- score de aderência;
- bloqueio por semestre;
- resumo e carta heurísticos;
- pipeline de status;
- exportação CSV;
- base de Playwright com revisão humana.

### Etapa 2: ingestão, currículo e métricas

Objetivo: reduzir entrada manual e medir o funil.

Implementado:

- RSS/Atom;
- APIs JSON configuráveis;
- proteção básica contra SSRF;
- upload e leitura de PDF;
- pré-preenchimento de perfil;
- dashboard de métricas;
- seleção entre heurístico, Codex e Claude;
- fallback heurístico.

### Etapa 3: extensão e redesign

Objetivo: captura em um clique e experiência de produto.

Implementado:

- extensão Manifest V3;
- `activeTab` e `scripting`;
- extratores Gupy, Indeed, LinkedIn, Sólides e Vagas.com.br;
- extrator genérico;
- pesquisas prontas;
- dashboard SaaS com sidebar azul-marinho;
- cartões, métricas e layout responsivo;
- launcher `.bat`;
- atalho Windows.

### Etapa 4: instalador, análise e assistente

Objetivo: distribuição e candidatura assistida.

Implementado:

- launcher Python;
- PyInstaller spec;
- Inno Setup;
- workflow Windows no GitHub Actions;
- banco de respostas;
- preenchimento assistido pela extensão;
- análise PDF/DOCX;
- score ATS, estrutura, conteúdo e aderência;
- geração de currículo DOCX por vaga.

### Etapa 5: multiagente e produtividade

Objetivo: agentes especializados com consumo controlado.

Implementado:

- orquestrador e tiers `local`, `economy`, `balanced`, `premium`;
- agentes conceituais por domínio;
- paralelismo local com até quatro workers;
- follow-up;
- importação EML;
- keyring;
- redação de dados;
- seção de agentes;
- seção de aprendizado;
- seção de e-mail;
- seção de follow-up.

### Etapa 6: aprendizado automático

Objetivo: conectar o comportamento real ao aprendizado.

Implementado:

- `analytics_events`;
- `job_attribution`;
- evento automático `captured`;
- evento `resume_generated`;
- eventos de etapa `applied`, `interview`, `offer`, `rejected`;
- idempotência por chave única;
- atribuição de resultados à variante do currículo;
- associação de EML somente com match único;
- atualização imediata do painel de Aprendizado.

## 5. Arquitetura atual

```text
FastAPI + SQLite + frontend estático
        |
        +-- Extensão Chromium
        +-- RSS/APIs
        +-- PDF/DOCX
        +-- Codex CLI / Claude Code CLI
        +-- Windows keyring
        +-- PyInstaller / Inno Setup
```

O backend está em `app/main.py`; serviços estão em `app/services`; o frontend está em `app/static`; a extensão está em `extension`.

## 6. Identidade visual

A identidade foi aprovada pelo usuário.

Características:

- sidebar azul-marinho;
- fundo cinza-claro;
- cartões brancos;
- azul-violeta como cor de ação;
- tipografia corporativa;
- bordas arredondadas;
- sombras discretas;
- layout SaaS;
- responsividade básica.

Seções atuais:

```text
Visão geral
Buscar vagas
Minhas vagas
Currículo
Análise de currículo
Assistente
Aprendizado
Follow-up
E-mail
Agentes
Automações
Inteligência
Perfil
```

## 7. Funcionalidades atuais

### Perfil

- dados pessoais;
- curso e termo;
- conclusão prevista;
- LinkedIn e GitHub;
- skills;
- evidências;
- objetivos e preferências.

### Vagas

- manual;
- extensão;
- RSS;
- API JSON;
- score;
- bloqueios;
- status;
- exportação.

### Currículo

- upload PDF;
- parser;
- análise PDF/DOCX;
- score ATS;
- comparação por vaga;
- DOCX específico por vaga;
- variante A/B.

### Assistente

- banco de respostas;
- padrões reconhecíveis;
- preenchimento assistido;
- revisão obrigatória.

### Aprendizado

- stream de eventos;
- atribuição;
- experimentos;
- conversão por variante;
- idempotência.

### Segurança

- armazenamento local;
- keyring para segredos;
- redação de e-mail e tokens;
- nenhum segredo no banco por design.

## 8. Armazenamento

Dados operacionais:

```text
%LOCALAPPDATA%\CareerOS\career_os.db
%LOCALAPPDATA%\CareerOS\uploads\
```

Segredos:

```text
Windows Credential Locker via keyring
```

Não implementar criptografia integral do banco agora. O usuário explicitamente decidiu priorizar outras funcionalidades.

## 9. Estado de testes

Última execução:

```text
16 passed
```

Cobertura funcional dos testes:

- scoring;
- semestre;
- currículo;
- análise;
- ingestão;
- agentes;
- e-mail;
- segurança;
- DOCX;
- tracking;
- atribuição;
- idempotência.

## 10. Pontos técnicos que a próxima IA deve corrigir primeiro

1. Centralizar versão em `app/version.py` ou constante única. Hoje o objeto FastAPI ainda informa 0.5.0 e `/api/health` informa 0.6.0.
2. Criar migrações de schema. A inicialização atual não altera tabelas antigas quando a estrutura muda.
3. Adicionar teste de integração completo para endpoints.
4. Persistir `agent_runs` em todas as execuções externas.
5. Separar `app/main.py` em routers.
6. Dividir `app/static/app.js` em módulos.
7. Criar backup/exportação integral antes de troca de máquina.
8. Validar instalador em Windows real.
9. Corrigir workflow e nomes de versão se necessário.
10. Revisar correspondência de e-mail para evitar falso positivo.

## 11. Backlog priorizado

### Prioridade alta

- Migrações de banco.
- Backup/restauração.
- Exportar e importar workspace completo.
- OAuth Microsoft Graph.
- Auditoria real dos agentes e consumo.
- Eventos automáticos vindos da extensão após preenchimento/revisão.
- Tela de detalhes da vaga.
- Histórico de currículos e download posterior.
- Editor visual do currículo antes da geração.

### Prioridade média

- OCR para PDF escaneado.
- Templates múltiplos de currículo.
- Recomendação de microprojetos por lacuna.
- Follow-up com notificações locais.
- Regras por plataforma.
- Testes E2E da extensão.
- Configuração de meta semanal.
- Filtros e busca interna.

### Prioridade futura

- Sincronização opcional em nuvem.
- Multiusuário.
- API externa autenticada.
- Marketplace de adaptadores.
- Publicação da extensão.
- Telemetria opt-in.

## 12. Processo recomendado para continuar em outra máquina

1. Subir somente arquivos sanitizados para GitHub.
2. Confirmar `.gitignore`.
3. Não incluir `data/career_os.db`.
4. Não incluir currículos ou uploads.
5. Não incluir `.env`.
6. Clonar na nova máquina.
7. Criar `.venv`.
8. Instalar `requirements.txt`.
9. Executar `pytest -q`.
10. Executar `python scripts/seed.py` somente em instalação nova.
11. Iniciar com `start_career_os.bat` ou Uvicorn.
12. Instalar a extensão sem compactação.

Comandos:

```powershell
git clone <URL_DO_REPOSITORIO>
cd career-os
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
python scripts\seed.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

## 13. Checklist antes de publicar

- [ ] Remover `data/career_os.db`.
- [ ] Remover `data/uploads`.
- [ ] Remover `.env`.
- [ ] Remover currículos PDF/DOCX pessoais.
- [ ] Remover tokens e headers de APIs.
- [ ] Remover nomes internos e caminhos corporativos.
- [ ] Remover `.venv`, caches e builds.
- [ ] Executar testes.
- [ ] Revisar README.
- [ ] Fazer busca por termos proibidos internos.
- [ ] Confirmar que arquivos de exemplo usam dados sintéticos.

## 14. Prompt de handoff para outra IA

```text
Você está continuando o projeto Career OS v0.6.

Leia primeiro:
1. docs/MASTER_PLAN_HANDOFF.md
2. docs/TECHNICAL_DOCUMENTATION_COMPLETE.md
3. docs/EVENTS_AND_STORAGE.md
4. docs/AGENT_ARCHITECTURE.md
5. docs/TEST_REPORT.md

Estado atual:
- FastAPI + SQLite + frontend estático.
- Extensão Chrome/Edge Manifest V3.
- Captura e scoring de vagas.
- Currículo PDF/DOCX, análise ATS e geração DOCX por vaga.
- Banco de respostas e preenchimento assistido.
- Agentes com tiers de custo.
- Follow-up, importação EML e keyring.
- Eventos automáticos e aprendizado por variante.
- 16 testes aprovados.

Regras:
- Não inventar fatos profissionais.
- Não expor dados corporativos.
- Não automatizar CAPTCHA, testes ou envio final.
- Manter revisão humana.
- Preservar a identidade visual.
- Sempre executar testes após alterações.
- Entregar arquivos completos, não patches incompletos.

Primeira tarefa recomendada:
centralizar a versão, criar migrações e implementar exportação/importação integral do workspace para facilitar troca de máquina.
```

## 15. Memória essencial do chat

- O usuário quer transformar a busca por vagas em um processo operacional mensurável.
- O projeto também deve ser uma peça forte de portfólio.
- O usuário está confortável com Python, Playwright, automação e dashboards.
- O usuário quer execução simples no Windows e instalação por `.exe`.
- O usuário aprovou a identidade visual atual.
- O usuário quer agentes simultâneos com baixo consumo de tokens.
- O usuário quer Codex e Claude como provedores opcionais.
- O usuário prioriza implementação prática e validação, não apenas brainstorming.
- O usuário quer preservar dados e termos internos da empresa fora do repositório público.
- O usuário decidiu não priorizar criptografia integral do banco de eventos no momento.
- O produto deve ajudar a gerar entrevistas, mas não pode prometer contratação.

## 16. Definição de pronto

Uma funcionalidade só está pronta quando:

- possui fluxo utilizável no frontend ou API;
- é persistida corretamente;
- não inventa dados;
- respeita revisão humana;
- possui teste mínimo;
- não expõe segredo;
- não quebra funcionalidades existentes;
- tem documentação atualizada;
- funciona no Windows ou possui instrução clara de build.
