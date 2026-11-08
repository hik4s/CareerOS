# CareerOS

**Organização de candidaturas, descoberta de vagas e análise de currículos com Python.**

O CareerOS reúne oportunidades, perfil profissional, currículos e acompanhamento de candidaturas em um painel. O objetivo é reduzir o trabalho de organizar a procura por emprego, preservando a revisão humana das informações e do envio das candidaturas.

**Estado atual:** MVP web em evolução, com código de versão cloud `1.1.1`. A versão local e seu instalador Windows têm ciclo independente. A existência de integrações no código não garante disponibilidade ou cobertura de todas as fontes.

[![Cloud checks](https://github.com/hik4s/CareerOS/actions/workflows/cloud-ci.yml/badge.svg)](https://github.com/hik4s/CareerOS/actions/workflows/cloud-ci.yml)

## Visão rápida

| Área | Implementação |
| --- | --- |
| Backend | Python, FastAPI, Pydantic e HTTPX |
| Dados e acesso cloud | Supabase Auth, PostgreSQL e Storage; migração com políticas RLS |
| Interface | HTML, CSS e JavaScript; React no módulo de autenticação |
| Navegador | Extensões Chrome/Edge Manifest V3, separadas para local e cloud |
| Documentos | Leitura de PDF/DOCX e exportação de dados da conta |
| Qualidade | Testes pytest e workflow GitHub Actions |
| Distribuição | Configuração Render para web; PyInstaller/Inno Setup para o modo local |

## O que o MVP implementa

- Perfil profissional estruturado, cadastro de vagas e acompanhamento de status.
- Captura da página de uma vaga pela extensão, com revisão antes de salvar.
- Busca por termos, localização, modalidade e nível, com paginação, deduplicação e informação sobre o estado das fontes.
- Filtro aproximado por distância entre centros de cidades brasileiras.
- Descoberta regional opcional de fontes por cidade, com cache e limites de coleta.
- Upload e leitura de currículos PDF/DOCX, análise por regras e comparação com vagas.
- Assistência de texto e avaliação por regras ou por provedores de IA configurados pelo usuário.
- Exportação autenticada da conta e fluxo de exclusão.
- No modo local, ferramentas próprias de assistência ao preenchimento e empacotamento Windows.

### Cobertura de vagas

O motor combina catálogos públicos e integrações opcionais. Há coletores para Greenhouse, Arbeitnow, sitemap de vagas e feeds configuráveis. Jooble, Gupy/parceiro, JSearch, SearchApi e SerpApi dependem da configuração e do acesso autorizado correspondente.

**A extensão capturar uma página do LinkedIn ou Indeed não significa que exista uma API de busca direta desses portais.** A descoberta regional depende de SearchApi ou SerpApi e importa apenas páginas compatíveis com o extrator. Cobertura, cotas e atualização dependem das fontes.

Consulte [fontes, filtros e limites da busca](docs/BUSCA_DE_VAGAS.md).

## Decisões técnicas demonstradas

- Separação entre execução local e serviço cloud.
- Verificação de sessão e acesso aos registros no contexto do usuário.
- Validação de entrada, limites para documentos e tratamento de falhas de serviços externos.
- Coleta concorrente com cache e limites de trabalho.
- Integração de IA com contexto limitado, chave por requisição e reutilização de respostas por conta.
- Testes negativos para autenticação, acesso a recursos de terceiros e dados inválidos.

Pontos de entrada para revisão:

| Tema | Código e evidências |
| --- | --- |
| API e validações | [main.py](app/cloud/main.py), [test_cloud_api.py](tests/test_cloud_api.py) |
| Autenticação | [auth.py](app/cloud/auth.py), [test_cloud_auth_resilience.py](tests/test_cloud_auth_resilience.py) |
| Descoberta regional | [source_discovery.py](app/cloud/source_discovery.py), [test_source_discovery.py](tests/test_source_discovery.py) |
| IA aplicada | [ai.py](app/cloud/ai.py), [test_cloud_ai.py](tests/test_cloud_ai.py) |
| Políticas de dados | [migração SQL](supabase/migrations/202611030001_cloud.sql), [teste RLS](supabase/tests/cloud_rls.sql) |

## Executar a versão web em desenvolvimento

Requer Python 3.12. Na raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-cloud.txt
.\.venv\Scripts\python.exe -m uvicorn app.cloud.main:app --reload --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000`. Sem configuração de autenticação, a página e o health check podem ser inspecionados; as rotas privadas recusam acesso.

Para usar os dados da conta, prepare um projeto Supabase, aplique a migração e configure `SUPABASE_URL`, `SUPABASE_ANON_KEY` e as origens permitidas no ambiente do processo. Use somente a chave pública apropriada no serviço web. O roteiro completo de banco, autenticação, Storage e publicação está no [guia web](docs/WEB_MVP.md).

As chaves de IA são informadas no fluxo da aplicação. Os conectores opcionais de busca usam configuração própria do servidor. Esses serviços podem ter cotas e cobrança conforme a conta do usuário.

### Modo local e extensão

No Windows, `start_career_os.bat` prepara e inicia a versão local. Consulte [como usar](COMO_USAR_CAREER_OS.txt) e [backup/restauração local](docs/WORKSPACE_TRANSFER.md).

- [Extensão cloud](extension-cloud/README.md): captura autenticada; não preenche nem envia candidaturas.
- [Extensão local](extension/README.md): fluxo independente do serviço cloud.
- `build_windows.bat`: empacotamento local; requer as ferramentas descritas no projeto.

## Verificar

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q tests/test_cloud*.py tests/test_regional_search.py tests/test_source_discovery.py
```

O workflow Cloud checks executa a suíte `test_cloud*.py`, verificações de sintaxe e uma verificação de carregamento. O comando acima inclui também os testes regionais, ainda fora desse filtro do workflow.

Testes com serviços simulados não comprovam OAuth, RLS, Storage ou chamadas de IA no ambiente publicado. A validação real deve usar contas de teste e registrar o resultado.

## Roteiro de demonstração

Com o ambiente configurado: entrar → revisar perfil → buscar uma vaga → salvar e atualizar o status → carregar um currículo → comparar as informações → exportar os dados da conta. Uma segunda conta deve permanecer sem acesso aos registros da primeira.

Não há link público de demonstração documentado neste README. Screenshots e vídeo do fluxo ainda precisam ser adicionados.

## Limites e próximos passos do MVP

1. Medir relevância, cobertura e tempo de resposta da busca com um conjunto fixo de consultas.
2. Incluir testes regionais no CI e registrar a validação real de autenticação, RLS e Storage.
3. Publicar demonstração com dados fictícios e instruções reproduzíveis.
4. Dividir os módulos grandes de interface e descoberta por responsabilidade.
5. Evoluir a análise de aderência com critérios explicáveis e avaliação de resultados.

O score atual é heurístico; não representa probabilidade de contratação. A integração com LLMs demonstra IA aplicada, não treinamento de um modelo próprio. O envio final da candidatura continua sob responsabilidade da pessoa usuária.

## Documentação

- [Busca e fontes](docs/BUSCA_DE_VAGAS.md)
- [Configuração web](docs/WEB_MVP.md)
- [Arquitetura técnica](docs/TECHNICAL_DOCUMENTATION_COMPLETE.md)
- [Planejamento e continuidade](docs/MASTER_PLAN_HANDOFF.md)

Documentos antigos de release e escopo registram fases anteriores. Este resumo distingue as capacidades atuais das próximas entregas; os testes e o ambiente configurado continuam sendo necessários para confirmar cada fluxo.
