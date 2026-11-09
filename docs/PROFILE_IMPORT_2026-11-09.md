# Busca livre e importação de perfil — 2026-11-09

## Comportamento

A busca não exige habilidades, cargos ou formação previamente cadastrados. A opção
de compatibilidade fica desmarcada por padrão em perfis vazios. Mesmo que uma aba
antiga envie `profile_only=true`, a API faz a busca normal com os outros filtros.
Perfis preenchidos continuam usando as regras de compatibilidade existentes.

Em **Meu perfil → Preencher perfil com currículo**, a pessoa pode enviar PDF/DOCX
ou selecionar um currículo já salvo. O upload usa o parser isolado e os limites
existentes: 5 MiB por arquivo, até 30 páginas PDF e até 10 currículos por conta.
O arquivo enviado fica na área privada de currículos da conta.

`GET /api/resumes/{id}/profile-preview` consulta somente um currículo acessível
pela conta autenticada e devolve sugestões, sem alterar o perfil. A extração local
identifica nome, contatos, links profissionais, cidade explicitamente rotulada,
formação, semestre explícito, conclusão, objetivo, resumo e habilidades. Campos
não identificados não são sugeridos. Não usa provedor de IA nem OCR. A interpretação
é heurística e precisa de revisão; não garante extrair todo formato de currículo.

A prévia permite escolher cada campo. Campos já preenchidos ficam desmarcados;
a pessoa pode selecioná-los para substituição. **Preencher campos selecionados**
edita somente o formulário. **Salvar perfil** confirma a persistência. Erros,
troca de página ou troca de conta não aplicam sugestões pendentes a outro formulário.

O parser passou a emitir JSON UTF-8 explicitamente: no Windows, o uso anterior
da codificação padrão do pipe podia quebrar documentos com acentos.

## Validação

- Testes de extração com DOCX fictício, campos ausentes, JavaScript versus Java,
  autenticação, currículo não encontrado e prévia sem gravação.
- Regressão HTTP: perfil vazio com `profile_only=true` retorna as vagas correspondentes.
- Integração de upload DOCX com subprocesso e obtenção da prévia.
- Script Node `scripts/test_profile_import.cjs`: aplicação somente dos campos
  escolhidos, preservação das edições atuais e rejeição de campos fora do contrato.
- Verificação local no Edge headless, viewport 390 × 844: upload, prévia, seleção,
  preenchimento, salvamento explícito, ausência de overflow e resposta de conta antiga.
  Rede/conta foram simuladas; não é homologação do Supabase publicado.
- A seleção também preserva campos editados depois de abrir a prévia. Para substituir
  uma edição posterior, selecione novamente o campo. Cidades conhecidas e títulos
  de formação/profissão são descartados pela heurística de nome.
- CI passa a incluir testes regionais/de fontes e o script de importação do perfil.

Validação local final: Python 3.11.9 / Node 20.15.0; 118 testes cloud/regionais/de
fontes aprovados, dois scripts Node aprovados e o teste móvel Edge aprovado.
Suíte Python completa: 140 aprovados e duas falhas desktop anteriores abaixo.
O workflow remoto usa Python 3.12 / Node 22; sua execução deve ser consultada no PR.

Para repetir o teste de navegador, instale Playwright no ambiente de testes
(`python -m pip install playwright`) e execute
`python scripts/test_profile_import_browser.py`. No Windows ele usa Edge instalado;
em Linux usa Chromium do Playwright (`python -m playwright install chromium`).
`CAREEROS_TEST_BROWSER_CHANNEL` permite selecionar outro canal compatível.

Comandos locais e contagens finais ficam no PR. A suíte completa identificou duas
falhas anteriores de backup desktop no Windows, reproduzidas também no main
original: `test_workspace_roundtrip` e `test_reject_tampered_archive` em
`tests/test_workspace.py`, ambos por conexão SQLite ainda aberta (`WinError 32`).
Esses fluxos desktop não foram alterados nesta entrega.

## Direção do produto definida pelo usuário

Evoluir para candidaturas rápidas em várias vagas, primeiro externas e depois
com publicação de vagas e recebimento de candidaturas dentro do CareerOS.
A candidatura externa assistida é a próxima etapa: começar por um portal definido,
preencher dados do perfil revisado e currículo selecionado, mostrar campos pendentes
e manter a confirmação final da pessoa. Compatibilidade por portal precisa ser
comprovada; capturar uma vaga não equivale a conseguir enviar uma candidatura.

O módulo de empresas/vagas nativas exige definir contas de recrutadores, propriedade
das vagas e candidaturas, consentimento de compartilhamento do currículo e estados
do processo. Esses dois fluxos ainda não estão implementados neste recorte.
