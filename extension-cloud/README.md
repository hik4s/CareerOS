# CareerOS Cloud — Chrome / Edge (Manifest V3)

1. No painel CareerOS autenticado, baixe `/api/extension.zip` e extraia o ZIP.
2. Abra `chrome://extensions` ou `edge://extensions`, ative **Modo do desenvolvedor**, escolha **Carregar sem compactação** e selecione a pasta que contém `manifest.json`.
3. No painel, copie o token para extensão. No popup, informe a origem HTTPS do seu CareerOS, cole o token e clique **Salvar origem e conectar**. Aceite acesso somente à origem informada.
4. Abra os detalhes de uma vaga e clique **Capturar vaga atual**. Revise o conteúdo salvo no painel.

HTTP é permitido somente para desenvolvimento em `localhost`, `127.0.0.1` ou `[::1]`. Não informe caminhos no endereço. A extensão pede acesso opcional ao endereço configurado; a vaga aberta é lida apenas após seu clique, com `activeTab`. Não há permissão obrigatória para todos os sites.

O token é uma credencial da sua conta, não uma chave de IA. Só é guardado em `chrome.storage.session`, vinculado à origem configurada. Expira conforme a sessão Supabase; após expirar ou reiniciar o navegador, copie um token novo. Não cole tokens em terceiros, mensagens ou repositórios. **Desconectar** remove token, origem e permissão concedida. Trocar de origem invalida o token anterior. O logout do painel não revoga imediatamente tokens já emitidos: desconecte a extensão também; um token emitido pode permanecer válido até expirar.

Esta versão captura vagas. Não preenche formulários, não envia candidaturas e não contorna CAPTCHA. O conteúdo extraído da página não é confiável: confira descrição, título e empresa antes de usar.
