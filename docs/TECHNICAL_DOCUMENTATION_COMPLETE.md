# Career OS v0.6: documentação técnica completa

> Documento de referência para desenvolvimento, manutenção, instalação, testes e continuidade do projeto.

## 1. Resumo executivo

Career OS é uma aplicação local-first para organizar e otimizar a busca por estágio e vagas iniciais em tecnologia. O produto centraliza vagas, analisa elegibilidade e aderência, gera currículos por vaga, auxilia o preenchimento de candidaturas, mede o funil real e aprende com os resultados observados.

A aplicação usa FastAPI no backend, interface web estática responsiva, SQLite para persistência local, uma extensão Chromium Manifest V3 para captura de vagas e preenchimento assistido, além de integração opcional com Codex CLI e Claude Code CLI.

O sistema é deliberadamente human-in-the-loop. Ele não contorna CAPTCHA, não realiza testes seletivos, não aceita termos e não envia candidaturas sem revisão humana.

## 2. Estado atual

Versão funcional documentada: `0.6.0` no endpoint `/api/health`.

Observação técnica: a instanciação de `FastAPI` ainda possui `version='0.5.0'`, enquanto o health check informa `0.6.0`. A próxima alteração deve centralizar a versão em uma constante única para eliminar essa divergência.

Validação mais recente:

- Compilação Python aprovada.
- 16 testes automatizados aprovados.
- Interface validada em Chromium headless.
- Aprendizado automático e idempotência de eventos validados.
- Empacotamento Windows preparado com PyInstaller e Inno Setup.

## 3. Arquitetura geral

```text
Navegador / Dashboard
        |
        v
FastAPI local em 127.0.0.1:8765
        |
        +-- Perfil e currículos
        +-- Vagas e scoring
        +-- Banco de respostas
        +-- Assistente de candidatura
        +-- Orquestrador de agentes
        +-- Aprendizado e atribuição
        +-- Follow-up
        +-- Importação EML
        +-- Segurança e keyring
        |
        v
SQLite local em %LOCALAPPDATA%\CareerOS\career_os.db

Extensão Chromium Manifest V3
        |
        +-- Captura página ativa
        +-- Envia vaga à API local
        +-- Detecta perguntas abertas
        +-- Preenche respostas aprovadas
```

### 3.1 Backend

Arquivos principais:

- `app/main.py`: endpoints REST, composição dos serviços e fluxos principais.
- `app/db.py`: schema SQLite, conexão e inicialização.
- `app/models.py`: modelos Pydantic de entrada.
- `app/config.py`: diretórios e limites de upload.

### 3.2 Frontend

- `app/static/index.html`: estrutura das telas.
- `app/static/styles.css`: identidade visual responsiva.
- `app/static/app.js`: navegação, chamadas REST, renderização e formulários.

### 3.3 Extensão

- `extension/manifest.json`: Manifest V3.
- `extension/background.js`: extração de vaga e preenchimento assistido.
- `extension/popup.html`: popup da extensão.
- `extension/popup.js`: ações de captura e assistência.

### 3.4 Serviços de domínio

- `scoring.py`: aderência e bloqueio por semestre.
- `resume.py`: extração básica de PDF.
- `resume_analysis.py`: análise estrutural, ATS, conteúdo e match.
- `resume_generator.py`: geração de DOCX por vaga.
- `assistant.py`: banco padrão e sugestão de respostas.
- `ingestion.py`: RSS, Atom e APIs JSON.
- `providers.py`: heurístico, Codex e Claude.
- `agent_orchestrator.py`: tiers de custo e paralelismo.
- `learning.py`: pesos e relatórios de experimentos.
- `event_tracker.py`: eventos automáticos, atribuição e idempotência.
- `email_import.py`: leitura e classificação de EML.
- `security.py`: keyring, redação e fingerprint.

## 4. Persistência e segurança

### 4.1 Dados operacionais

No aplicativo instalado:

```text
%LOCALAPPDATA%\CareerOS\career_os.db
%LOCALAPPDATA%\CareerOS\uploads\
```

Em desenvolvimento:

```text
career-os/data/career_os.db
career-os/data/uploads/
```

SQLite guarda vagas, perfil, status, eventos, experimentos, versões de currículo, respostas, follow-ups, e-mails importados e logs de agentes.

SQLite não é uma vault. O projeto é local-first, mas o banco não possui criptografia integral própria.

### 4.2 Segredos

Tokens e chaves devem ser armazenados pelo `keyring` do sistema operacional. No Windows, o backend esperado é o Windows Credential Locker.

Não salvar no SQLite:

- senhas;
- API keys;
- access tokens;
- refresh tokens;
- credenciais de e-mail;
- cookies de portais.

### 4.3 Redação

Antes de enviar texto para modelos externos, usar `app.services.security.redact()` para remover e-mails e valores de tokens/chaves conhecidos.

## 5. Modelo de dados

Tabelas relevantes:

### Perfil e documentos

- `profile`: JSON do perfil, currículo original e texto extraído.
- `resume_analyses`: análises de currículo.
- `resume_versions`: currículos gerados por vaga e variante.

### Vagas e candidaturas

- `jobs`: vaga normalizada, score, análise e etapa.
- `materials`: resumos e cartas gerados.
- `answer_bank`: respostas aprovadas para formulários.
- `followups`: acompanhamentos agendados.

### Fontes e e-mails

- `sources`: RSS e APIs configuradas.
- `email_imports`: mensagens EML importadas e classificadas.

### Inteligência e aprendizado

- `settings`: provedor selecionado.
- `agent_runs`: estrutura para auditoria de agentes.
- `experiments`: testes A/B.
- `experiment_events`: eventos ponderados por experimento.
- `analytics_events`: stream idempotente de eventos.
- `job_attribution`: atribuição entre vaga, fonte, variante e currículo.

## 6. Eventos automáticos

Eventos implementados:

```text
captured
resume_generated
applied
interview
offer
rejected
```

Fontes dos eventos:

- inclusão manual;
- extensão do navegador;
- alteração do status no funil;
- geração de currículo;
- importação de e-mail com correspondência segura.

### 6.1 Idempotência

Eventos de etapa usam chaves únicas, por exemplo:

```text
42:stage:applied
42:stage:interview
```

Repetir a mesma etapa não duplica a métrica.

### 6.2 Atribuição

A última variante de currículo associada à vaga antes da candidatura recebe os eventos seguintes. A tabela `job_attribution` registra experimento, variante, versão de currículo e fonte.

## 7. Motor de aprendizado

O painel consulta `analytics_events` em tempo real e calcula:

- eventos totais;
- capturas;
- candidaturas;
- entrevistas;
- ofertas;
- conversão por variante;
- taxa de entrevista;
- taxa de oferta.

Os resultados mostram associação observada, não causalidade comprovada. Variantes não devem ser promovidas com amostra pequena.

## 8. Sistema multiagente

Agentes conceituais:

- `SourcingAgent`: ingestão e normalização.
- `EligibilityAgent`: requisitos e bloqueios.
- `ResumeAgent`: currículo por vaga.
- `ReviewerAgent`: verdade, ATS e aderência.
- `ApplicationAgent`: respostas e formulários.
- `EmailAgent`: classificação de retornos.
- `FollowUpAgent`: acompanhamento.
- `LearningAgent`: eventos e experimentos.
- `SecurityAgent`: redação e segredos.

### Política de custo

```text
Regras locais primeiro
Economy para extração e classificação
Balanced para escrita e revisão
Premium apenas para estratégia complexa solicitada
```

Mapeamento lógico atual:

```text
Codex: economy=Luna, balanced=Terra, premium=Sol
Claude: economy=Haiku, balanced=Sonnet, premium=Opus
Heurístico: rules em todos os níveis
```

Os nomes são lógicos e precisam ser adaptados aos modelos realmente disponíveis na conta ou CLI do usuário.

## 9. Funcionalidades por módulo

### Busca e captura

- atalhos para plataformas;
- captura pela extensão;
- extratores dedicados para Gupy, Indeed, LinkedIn, Sólides e Vagas.com.br;
- extrator genérico;
- cadastro manual;
- RSS/Atom;
- APIs JSON configuráveis;
- deduplicação por URL.

### Análise de vaga

- identificação de tecnologias;
- score de aderência;
- detecção de semestre mínimo;
- classificação `apply`, `review` ou `skip`;
- benefícios e modelo de trabalho.

### Currículo

- upload de PDF;
- leitura de PDF textual;
- leitura de DOCX para análise;
- extração de contato, links, curso, semestre e skills;
- avaliação ATS;
- análise de estrutura e conteúdo;
- comparação com vaga;
- geração de DOCX de uma coluna por vaga.

### Candidatura assistida

- banco editável de respostas;
- reconhecimento por padrões;
- preenchimento apenas de perguntas conhecidas;
- destaque visual dos campos preenchidos;
- revisão obrigatória;
- sem envio automático.

### Follow-up

- vaga, data, canal, template, notas e status;
- ordenação cronológica;
- conclusão manual.

### E-mail

- importação múltipla de `.eml`;
- classificação `interview`, `rejected`, `application` ou `other`;
- associação automática somente quando há uma correspondência única e segura.

## 10. API principal

Endpoints centrais:

```text
GET    /api/health
GET    /api/profile
PUT    /api/profile
POST   /api/resume/upload
POST   /api/resume/analyze
POST   /api/jobs
GET    /api/jobs
POST   /api/import/browser
POST   /api/jobs/{id}/analyze
POST   /api/jobs/{id}/materials
POST   /api/jobs/{id}/resume.docx
PUT    /api/jobs/{id}/stage
GET    /api/metrics
GET    /api/learning
GET    /api/agents/plan
GET    /api/answers
POST   /api/assistant/suggest
GET    /api/followups
POST   /api/followups
POST   /api/email/import
GET    /api/security/status
GET    /api/onboarding
```

## 11. Instalação e build Windows

### Desenvolvimento

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts\seed.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

### Inicialização simplificada

```text
start_career_os.bat
```

### Build do executável e instalador

Pré-requisitos:

- Windows;
- Python 3.12;
- Inno Setup 6.

Executar:

```bat
build_windows.bat
```

Saída esperada:

```text
installer\CareerOS-Setup-0.6.0.exe
```

Também existe o workflow:

```text
.github/workflows/windows-installer.yml
```

## 12. Testes

Executar:

```powershell
pytest -q
```

Estado atual: 16 testes aprovados.

A suíte cobre:

- semestre e score;
- parser de currículo;
- análise de currículo;
- normalização de vaga;
- roteamento de agentes;
- classificação de e-mail;
- redação de dados;
- geração de DOCX;
- eventos automáticos;
- atribuição de variante;
- idempotência;
- atualização do aprendizado.

## 13. Limitações conhecidas

- `FastAPI(version='0.5.0')` diverge do health check `0.6.0`.
- OAuth direto com Outlook/Microsoft Graph ainda não está concluído.
- PDFs escaneados não possuem OCR.
- O banco local não possui criptografia integral.
- Não há migrações formais do schema; o schema usa `CREATE TABLE IF NOT EXISTS`.
- O frontend está concentrado em um único `app.js` e deve ser modularizado se crescer.
- A associação de e-mail é baseada em correspondência textual simples.
- `agent_runs` está preparado, mas nem todos os agentes gravam auditoria completa.
- O sistema não executa o envio final da candidatura.

## 14. Prioridades técnicas recomendadas

1. Centralizar a versão do produto.
2. Criar migrações de banco versionadas.
3. Persistir auditoria real de todas as execuções de agentes.
4. Implementar OAuth Microsoft Graph com consentimento delegado.
5. Adicionar testes de API com TestClient e testes E2E da extensão.
6. Modularizar frontend e separar componentes.
7. Adicionar backup e restauração local.
8. Criar importação/exportação integral do perfil e histórico.
9. Melhorar correspondência de e-mail com score e revisão manual.
10. Adicionar OCR opcional para currículos escaneados.
