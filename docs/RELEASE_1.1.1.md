# CareerOS Cloud 1.1.1

Falhas temporárias do serviço de login deixam de ser apresentadas como sessão
expirada. O usuário recebe uma orientação para tentar novamente, sem repetição
automática. Sessões inválidas continuam sem acesso. Respostas inesperadas do
provedor também falham de modo fechado.

A API instrui navegadores e intermediários a não armazenar respostas em cache.
Foram adicionados no-referrer e nosniff às respostas. Nenhum dado, chave ou
permissão de banco foi alterado.

Google e GitHub ainda dependem do cadastro dos clientes OAuth no provedor e
da configuração no Supabase. Esta versão não ativa esses provedores.
