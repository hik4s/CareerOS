# Busca de vagas no CareerOS

Abra **Buscar vagas** no menu do painel. Preencha cargo ou palavra-chave,
localização e o filtro de remoto conforme necessário. Os campos de texto
podem ficar vazios. Use **Revisar e salvar** para conferir uma vaga antes
de adicioná-la a **Minhas vagas**. A candidatura acontece no portal original.

## Cobertura

| Fonte | Como aparece |
| --- | --- |
| Grupo QuintoAndar e Brex | Resultados dos respectivos quadros públicos Greenhouse |
| Arbeitnow | Resultados da primeira página do feed público, com foco internacional |
| LinkedIn, Gupy, InfoJobs e Indeed | Links para a busca externa, com parâmetros quando suportados |
| Catho, Vagas.com.br, Glassdoor, Empregos.com.br, Trabalha Brasil, Jooble, Trampos, CIEE, Nube e SINE | Atalhos para os portais, com filtros aplicados no próprio site |

As APIs públicas trazem um recorte dos catálogos. O CareerOS não consulta
todos os empregadores da Greenhouse nem agrega resultados dos portais
marcados como externos. O botão **Abrir vaga** mantém a fonte acessível.
A extensão pode ser usada para capturar uma vaga encontrada no portal.

- [Documentação da API pública Greenhouse](https://docs.greenhouse.io/job-board.html)
- [Documentação do feed Arbeitnow](https://www.arbeitnow.com/blog/job-board-api)
- [API de vagas da Gupy, autenticada](https://developers.gupy.io/reference/findjobs)
- [API de publicação do LinkedIn, para integrações autorizadas](https://learn.microsoft.com/pt-br/linkedin/talent/job-postings/api/overview)

## Implementação

A rota autenticada GET /api/discovery/jobs consulta uma lista fixa de feeds
em paralelo. A busca local ignora diferenças de caixa e acentuação e
filtra pelo texto da localização. Resultados repetidos com o mesmo URL
aparecem uma vez. A resposta traz até 50 itens e informa o total encontrado.
O estado de cada fonte é exibido. Uma falha externa não impede o uso dos
links ou a leitura das outras fontes.

O cache em memória dura cinco minutos por feed, com uma espera curta para
novas consultas após falhas. O servidor não transmite o perfil, o currículo,
o token da sessão nem os termos digitados aos feeds. Os parâmetros
dos links externos são enviados ao portal somente ao abrir o link.
As descrições de feeds são normalizadas como texto e podem ser abreviadas.
