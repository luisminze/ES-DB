# ES-DB — Aba Atividade (Feed Pessoal)

> **Atualização 1:** o feed passou a incluir os desbloqueios de conquistas
> cronologicamente. Ver [ATUALIZACAO1.md](ATUALIZACAO1.md).
> **Atualização 2:** o feed passou a **agrupar por jogo/dia** (horas, conquistas e
> screenshots num só card). Ver [ATUALIZACAO2.md](ATUALIZACAO2.md).

> Visual inspirado no **feed de atividade da Steam**; conteúdo inspirado no
> plugin **PlayerActivities** do Playnite — porém **apenas do usuário atual**,
> sem recursos sociais (amigos, curtir, comentar, publicar status).

## 1. Objetivo

Apresentar a jornada do próprio jogador como uma linha de eventos, derivada das
sessões já importadas, em um formato de feed agradável de percorrer.

## 2. Estrutura

- A aba tem alternância **Feed / Sessões**.
- **Feed**: eventos em ordem decrescente, agrupados por mês (divisor "MÊS DE ANO").
- **Sessões**: a tabela cronológica de sessões (equivale à antiga "Linha do
  tempo", MAIN.md RF-08), com filtro por plataforma.

Cada evento traz um avatar (inicial do usuário) e um horário. Eventos grandes são
cards com capa; eventos menores são linhas compactas.

## 3. Eventos derivados (RF-AT-01)

| Tipo | Origem | Apresentação |
| --- | --- | --- |
| Primeira vez jogando | 1ª sessão normal de um jogo | Card com capa, "Você jogou X pela primeira vez". |
| Marco de tempo | Tempo acumulado do jogo cruza um limiar | Card, "Você alcançou N h em X". Limiar: 1, 5, 10, 25, 50, 100, 250, 500, 1000 h. |
| Estreia em plataforma | 1ª sessão normal em uma plataforma | Linha, "Primeira vez em <plataforma>". |
| Resumo diário | Agregado do dia | Linha, "Você jogou <tempo> em N jogos". |

Regras:
- Sessões de **duração zero** (inícios rápidos) e inválidas **não** geram eventos.
- As capas usam o mesmo placeholder da Biblioteca quando não há arte local.
- Clicar em um evento com jogo abre a página de detalhes do jogo.

## 4. Critérios de aceite

1. O feed lista apenas atividades do usuário atual; não há elementos sociais.
2. Cada jogo gera um evento de "primeira vez" e cada plataforma um de "estreia".
3. Marcos de tempo aparecem ao cruzar os limiares definidos, uma vez cada.
4. O resumo diário conta jogos distintos e tempo do dia.
5. A alternância Sessões mostra a tabela cronológica com filtro por plataforma.
6. Inícios rápidos não produzem eventos.
