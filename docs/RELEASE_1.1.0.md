# CareerOS Cloud 1.1.0 — exportação da conta

A aba **Meus dados** oferece **Baixar minha cópia em ZIP**. A rota autenticada
`GET /api/workspace/export.zip` reúne perfil, todas as vagas, histórico de IA e
metadados de currículos em `workspace.json`, os arquivos em `resumes/` e um
`manifest.json` com SHA-256 de cada conteúdo exportado.

As consultas usam o JWT e o filtro de proprietário da conta. Há validação
adicional do dono em cada página de registros e dos caminhos de arquivos antes
do download autenticado no Storage. Nomes originais não determinam caminhos no
ZIP. Chaves de IA e tokens de sessão não entram na exportação.

A leitura é paginada e continua mesmo se o servidor devolver páginas menores
que o solicitado. Em erro de arquivo/Storage, a exportação inteira é cancelada;
não se entrega um ZIP que silenciosamente omite currículos. Limites: 64 MiB
descompactados no total e 10.000 registros por categoria. Arquivos temporários
são removidos após a resposta concluída e nos caminhos de erro.

O arquivo contém dados pessoais e não é criptografado. O navegador deve
baixá-lo somente em um dispositivo do proprietário. Evitar alterações na conta
em outras abas durante a operação: é uma cópia durante um intervalo, não uma
transação única de banco. Não inclui contas Auth, senha ou configuração global
do servidor. Não há importação/restauração cloud ou agendamento automático.

Validação: 73 testes Python aprovados, incluindo nove testes de exportação;
JavaScript e diff-check aprovados. Não foi possível homologar com uma sessão
OAuth real: o dashboard Supabase continua preso na verificação de segurança.
O recurso não depende de nova tabela, bucket ou infraestrutura paga.
