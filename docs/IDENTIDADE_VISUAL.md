# Identidade visual do CareerOS

Referência da identidade aprovada na tela de acesso React em `/auth`.
A interface do painel e a tela de entrada compartilham a marca, a tipografia
e a base azul escura com acentos roxos.

![Logo CareerOS](brand/careeros-logo.svg)

## Logo, ícone e vetores

| Ativo | Uso |
| --- | --- |
| [Logo CareerOS](brand/careeros-logo.svg) | Assinatura completa sobre superfície escura. “Career” branco e “OS” lilás. |
| [Ícone C](brand/careeros-icon.svg) | Marca compacta. Base de 34 × 34, raio 11, letra branca Manrope 800 a 24 px. |
| [Órbitas](brand/careeros-orbits.svg) | Motivo decorativo de círculos concêntricos, cortado pelo canto inferior direito do painel escuro. |
| [Ícones de provedores](../frontend/auth/icons.jsx) | Vetores do Google em suas quatro cores e do GitHub em `currentColor`. Usar com o nome do provedor. |

Os SVGs da marca usam texto editável. Para manter o desenho das letras em
exportações externas, instale Manrope ou converta o texto em curvas no editor.
Na interface, mantenha o símbolo e o nome juntos sempre que houver espaço.
Os vetores decorativos ficam fora da leitura por tecnologias assistivas.

## Cores

| Cor | Hex | Aplicação |
| --- | --- | --- |
| Azul profundo | `#141A32` | Barra lateral e painel narrativo de acesso |
| Roxo principal | `#7053E9` | Símbolo C, ações primárias e contorno de foco |
| Lilás de marca | `#B4A2FF` | “OS”, destaque editorial e órbitas |
| Brilho violeta | `#392A73` | Gradiente radial no painel escuro |
| Fundo | `#F6F7FB` | Fundo do painel e área de formulário |
| Branco | `#FFFFFF` | Cartão, texto da marca e ações primárias |
| Texto principal | `#242A42` | Texto sobre superfícies claras |
| Texto secundário | `#626984` | Descrições e instruções do formulário |
| Texto sobre escuro | `#C0C5DB` | Descrições no painel narrativo |
| Roxo de texto | `#5B3ED0` | Links e modo ativo |
| Lilás claro | `#F2EFFB` | Fundo do seletor de modo |
| Borda | `#E8EAF1` | Cartões e divisores |
| Borda de campo | `#DCE0EC` | Inputs e botões sociais |
| Campo | `#FCFCFF` | Fundo dos inputs |
| Sucesso | `#E9F7F0` / `#225D43` | Fundo e texto da confirmação |
| Erro | `#FFF0F0` / `#9C303E` | Fundo e texto de erro |

## Tipografia

| Família | Pesos | Uso |
| --- | --- | --- |
| Manrope | 400, 500, 600, 700, 800 | Logo, títulos e chamadas |
| DM Sans | 400, 500, 600, 700 | Corpo, formulários, botões e avisos |

O logotipo usa 25 px e peso 800. Na entrada, a chamada editorial usa
`clamp(36px, 4.3vw, 66px)` com entrelinha 1,04 e espaçamento de letras
`-.055em`. O título do formulário usa `clamp(24px, 3vw, 33px)`.
Rótulos usam 13 px e peso 700. As legendas usam 12 px e as chamadas em
caixa alta do painel escuro usam 11 px com espaçamento de `.16em`.

## Composição e interação

- Desktop com duas colunas. O painel azul apresenta a marca, a chamada
  “Organize seu próximo grande passo.” e o cartão “Seu espaço de evolução”.
  O painel claro centraliza o formulário.
- Cartão branco de até 460 px, raio 24 px, borda de 1 px e sombra suave.
  Campos e ação principal têm altura mínima visual de 46 px e raio de 10 px.
- O seletor segmentado alterna **Entrar** e **Criar conta**. Recuperação e
  redefinição de senha têm títulos e ações próprios.
- Os campos usam rótulos visíveis, autocomplete e foco roxo com deslocamento.
  A ação Mostrar/Ocultar mantém o campo no mesmo lugar.
- O envio desativa ações concorrentes e indica espera. Avisos de sucesso e
  erro aparecem no formulário, com texto e estados acessíveis.
- Botões sociais usam fundo branco, borda leve e ícone junto do nome.
- A transição do título dura 200 ms e respeita `prefers-reduced-motion`.
- Até 760 px, a composição passa para uma coluna. A marca e a chamada ficam
  acima do cartão. O conteúdo decorativo secundário é reduzido no celular.

## Fontes de implementação

- [Estilos globais e do painel](../app/cloud/static/style.css)
- [Estilos da entrada](../app/cloud/static/auth.css)
- [Componente React da entrada](../frontend/auth/Auth.jsx)
- [Código e build do frontend](../frontend/auth/README.md)

Para novas telas, reutilize essa paleta, os estados de foco e a hierarquia
tipográfica. Mantenha o texto de ação específico e os avisos próximos ao campo
ou ao botão que os originou.
