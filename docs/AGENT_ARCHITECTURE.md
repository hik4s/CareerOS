# Arquitetura multiagente e custo

## Política

1. Regras locais executam primeiro: parsing, deduplicação, score, datas e métricas.
2. Agentes econômicos cuidam de extração, classificação de e-mail e triagem.
3. Agentes balanceados cuidam de currículo, carta e revisão.
4. Agentes premium só são acionados para estratégia, ambiguidade ou revisão crítica explícita.
5. Tarefas independentes podem executar em paralelo, com no máximo quatro trabalhadores no desktop.
6. Cada execução pode registrar agente, tier, provedor, volume aproximado e resultado.

## Agentes planejados

- SourcingAgent: normaliza vagas.
- EligibilityAgent: detecta bloqueios objetivos.
- ResumeAgent: gera currículo específico.
- ReviewerAgent: valida fatos, ATS e aderência.
- ApplicationAgent: sugere respostas aprovadas.
- EmailAgent: classifica retornos.
- FollowUpAgent: agenda acompanhamento.
- LearningAgent: mede variantes e conversão.
- SecurityAgent: redige dados antes de prompts externos.

## Roteamento

- Codex economy: Luna; balanced: Terra; premium: Sol.
- Claude economy: Haiku; balanced: Sonnet; premium: Opus.
- Heurístico: regras locais em todos os níveis.

Nomes são configurações lógicas. A disponibilidade real depende do CLI/conta conectada.
