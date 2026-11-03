# Continuidade e transferência do workspace

## Estado em 03/11/2026

Versão do aplicativo: `app/version.py` (`0.6.0`). API, OpenAPI e builds
Windows leem essa constante. O workflow e o batch fornecem a versão ao Inno Setup.

O banco usa `PRAGMA user_version=1`. A adoção inicial cria tabelas ausentes
e acrescenta colunas com valores padrão constantes, incluindo `resume_versions.variant`.
A atualização é transacional e idempotente. Bancos de uma versão de schema futura
são recusados. Layouts antigos que exigem reconstrução de chaves ou colunas de data
são recusados com rollback; exigem uma migração específica, sem adivinhação destrutiva.

## Backup e restauração

Feche o CareerOS antes de exportar ou restaurar para manter arquivos e banco
consistentes entre si. Execute os comandos na raiz do projeto, com Python e
dependências instaladas. No Windows, use `.venv\Scripts\python.exe` se necessário.

```powershell
python -m app.workspace export C:\Backups\career-os.zip
python -m app.workspace restore C:\Backups\career-os.zip C:\CareerOS-Restaurado
```

A exportação usa os caminhos `CAREER_OS_DB` e `CAREER_OS_UPLOAD_DIR` quando
definidos; caso contrário, usa os caminhos de `app/config.py`. Confirme o diretório
da instalação em `/api/security/status`, sobretudo ao alternar entre executável
e código-fonte. Um nome de backup já existente não é sobrescrito.

O ZIP contém um snapshot SQLite, uploads e manifesto SHA-256. Inclui perfil,
vagas, eventos, respostas, análises e histórico armazenados no banco. O limite
atual é 512 MiB descompactados. Credenciais do keyring e configuração `.env`
ficam fora; conecte novamente os provedores na outra máquina. O arquivo contém
dados pessoais e não é criptografado.

A restauração exige uma pasta inexistente. Valida manifesto, hashes, caminhos,
integridade SQLite e versão do schema antes de disponibilizar os arquivos.
Caminhos absolutos dos DOCX gerados são ajustados à nova pasta de uploads.

Para usar os dados restaurados pelo código-fonte, abra um PowerShell na raiz:

```powershell
$env:CAREER_OS_DB = 'C:\CareerOS-Restaurado\career_os.db'
$env:CAREER_OS_UPLOAD_DIR = 'C:\CareerOS-Restaurado\uploads'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Esse bloco oferece transferência por linha de comando. Ainda falta integrar
os controles de backup/restauração ao painel e ao executável distribuído.

## Validação

24 testes aprovados em Linux com Python 3.12: suíte anterior, migração repetida,
preservação de registros, rollback, recusa de schema futuro, API/OpenAPI,
perfil e roundtrip de backup com currículo. Corrupção e path traversal recusados.
Build e instalação em Windows real continuam pendentes.

## Próximas tarefas

1. Testar o instalador Windows desta branch e transferência entre máquinas.
2. Adicionar backup/restauração à interface com fechamento controlado do banco.
3. Persistir auditoria de execuções externas em `agent_runs`.
