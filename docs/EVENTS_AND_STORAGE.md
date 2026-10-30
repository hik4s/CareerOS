# Eventos, aprendizado e armazenamento

## Fluxo automático

1. Uma vaga manual ou capturada gera `captured`.
2. Gerar currículo registra `resume_generated` e fixa a variante A/B na atribuição da vaga.
3. Alterar o funil para `applied`, `interview`, `offer` ou `rejected` gera o evento correspondente.
4. Importar EML pode gerar evento quando há uma única correspondência segura entre a mensagem e uma vaga.
5. O painel de Aprendizado consulta os eventos agregados imediatamente.

## Idempotência

Eventos de estágio usam chaves únicas. Marcar a mesma vaga como `applied` duas vezes não duplica a conversão. Currículos, por serem versões distintas, possuem eventos separados.

## Onde os dados ficam

### Dados operacionais e eventos

SQLite local:

```text
%LOCALAPPDATA%\CareerOS\career_os.db
```

Tabelas principais:

- `analytics_events`: stream de eventos.
- `job_attribution`: variante, currículo e origem atribuídos à vaga.
- `experiment_events`: eventos usados nos experimentos.
- `experiments`: definição dos testes A/B.
- `resume_versions`: versões de currículo.

SQLite não é uma vault. É o armazenamento local estruturado do produto.

### Segredos

Tokens, senhas e chaves devem ficar no keyring do sistema. No Windows, o backend esperado é o Windows Credential Locker. O SQLite não armazena esses segredos.

## Modelo de privacidade

- Local-first por padrão.
- Nenhum evento é enviado a um servidor externo automaticamente.
- Prompts externos passam pela camada de redação.
- Banco e uploads permanecem em LocalAppData.
- Backup e criptografia integral do banco devem ser adicionados antes de sincronização em nuvem.
