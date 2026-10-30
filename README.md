# Career OS v0.3

Aplicativo local para capturar, analisar e acompanhar vagas de estágio em tecnologia.

## Início rápido no Windows

1. Extraia o projeto.
2. Dê duplo clique em `start_career_os.bat`.
3. Na primeira execução, aguarde a criação do ambiente e instalação das dependências.
4. O painel abrirá em `http://127.0.0.1:8000`.

Para criar atalho na Área de Trabalho:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1
```

## Extensão

Dê duplo clique em `install_extension.bat`, ative o modo do desenvolvedor e carregue a pasta `extension`. Abra uma vaga, clique na extensão e use **Capturar vaga atual**.

Adaptadores incluídos: Gupy, Indeed, LinkedIn, Sólides e Vagas.com.br, além de extrator genérico para outros portais.

## Fluxo recomendado

1. Execute o app.
2. Faça upload do currículo em **Currículo**.
3. Revise o perfil.
4. Abra **Buscar vagas**.
5. Abra uma pesquisa pré-configurada.
6. Entre nos detalhes de uma vaga e capture pela extensão.
7. Em **Minhas vagas**, revise score e bloqueios.
8. Gere material adequado.
9. Abra a vaga, revise o formulário e envie manualmente.
10. Atualize o status para medir conversão.

O envio final e perguntas eliminatórias permanecem sob revisão humana. O sistema não contorna CAPTCHA ou testes.

## Versão 0.4

Novidades: instalador Windows reproduzível, assistente de candidatura, banco de respostas e análise de currículo PDF/DOCX por vaga.

### Gerar o instalador no Windows

Instale Python 3.12 e Inno Setup 6. Depois execute:

```bat
build_windows.bat
```

Saída esperada:

```text
installer\CareerOS-Setup-0.4.0.exe
```

Alternativamente, publique o projeto no GitHub e execute manualmente o workflow **Windows Installer**. O artefato produzido contém o instalador.

### Assistente de candidatura

Na extensão, clique em **Preencher candidatura**. O sistema reconhece perguntas abertas, consulta respostas aprovadas e preenche somente correspondências conhecidas. Todos os campos são destacados para revisão. O sistema nunca envia o formulário.

### Análise de currículo

Em **Análise de currículo**, envie PDF ou DOCX e opcionalmente escolha uma vaga. O relatório separa:

- estrutura;
- conteúdo e evidências;
- legibilidade ATS;
- aderência à vaga;
- pontos fortes;
- melhorias;
- palavras-chave presentes e ausentes.
