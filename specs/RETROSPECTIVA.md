# ES-DB — Especificação de Retrospectiva Anual

## 1. Propósito e referência

A retrospectiva é o relatório anual pessoal do ES-DB. Seu propósito é contar uma história verificável da atividade de jogo com métricas, destaques e visualizações que permitam explorar o ano sem transformar dados incompletos em conclusões exageradas.

O desenho funcional é inspirado no [Playnite Year In Review](https://github.com/SparrowBrain/Playnite.YearInReview): destaque do jogo mais jogado, ranking, calendário de atividade e distribuição por hora. A implementação é inteiramente original, local e baseada somente no banco GameSessionTracker. Não há dependência de Playnite, importação de relatório de terceiros, ranking entre amigos ou comunicação de rede.

## 2. Fonte de verdade e escopo dos dados

O relatório usa somente sessões válidas importadas em `Session` e os metadados correspondentes de `Game` e plataforma. Todos os valores são recalculados do banco derivado local; CSVs exportados pelo script não participam do cálculo.

| Disponível para a retrospectiva | Não disponível na fonte — fora do escopo |
| --- | --- |
| início, fim e duração de cada sessão | conquistas, troféus e progresso no jogo |
| jogo, plataforma e identificador técnico do sistema | gênero, nota crítica, desenvolvedora e data de lançamento |
| tempo por dia, hora, jogo e plataforma | data em que o usuário adquiriu/adicionou o jogo |
| sessões, primeiras/últimas partidas e sequência | dados de outros jogadores, amigos ou comparações sociais |

Uma sessão de duração zero permanece disponível em Integridade, mas não participa de tempo, jogos jogados, rankings, calendário, horário favorito, sequências ou destaques anuais.

## 3. Contrato do relatório

### 3.1 Geração e reprodutibilidade

Ao abrir um ano, a aplicação gera um `YearReview` em memória a partir dos dados atuais. O relatório contém metadados suficientes para auditar o resultado:

```text
YearReview
  year, generated_at, timezone, calculation_version,
  source_id, observed_first_session_at, observed_last_session_at,
  coverage_status, metrics, highlights, rankings,
  monthly_activity, calendar_days, hourly_activity, quality_summary
```

- `generated_at`: data/hora local em que a visualização foi calculada.
- `timezone`: fuso aplicado ao separar sessões entre dias, meses e horas.
- `calculation_version`: versão das regras de cálculo. Ela permite evoluir a lógica sem confundir relatórios impressos em versões diferentes.
- `observed_first_session_at` e `observed_last_session_at`: primeira e última sessão presentes no banco dentro do ano. Eles descrevem a cobertura observada, não provam que o histórico seja completo.
- `coverage_status`: `spans_full_calendar_year`, `starts_after_year_begin`, `ends_before_year_end`, `partial_range` ou `unknown`. A classificação é informativa e nunca deve alegar ausência de jogo fora do intervalo observado.

O relatório é recalculável e não deve ser salvo como cópia canônica dos dados. Uma exportação ou impressão inclui `generated_at`, `timezone` e `calculation_version` no rodapé para preservar o contexto. Futuramente, o usuário poderá optar por guardar um *snapshot* local e imutável; isso não é necessário na V1.

### 3.2 Elegibilidade

- Um ano aparece no seletor se possui ao menos uma sessão normal válida que intercepte aquele ano.
- Sessões que atravessam 1º de janeiro ou 31 de dezembro contribuem somente com a fração de duração dentro do ano escolhido.
- Se não houver sessão normal válida, a página informa que não existe retrospectiva para o ano. Não mostra rankings vazios, narrativa genérica ou zero como se fosse atividade real.
- O ano atual recebe o marcador **“até hoje”** e não é comparado como ano completo com o anterior.

## 4. Cálculos obrigatórios

Todas as quebras temporais seguem o fuso configurado pelo usuário. Para evitar perdas ou dupla contagem, uma sessão é fracionada nos limites de ano, mês, dia e hora antes de cada agregado correspondente.

| Grupo | Métrica | Definição |
| --- | --- | --- |
| Visão geral | Tempo total | Soma dos segundos normais dentro do ano. |
| Visão geral | Sessões | Quantidade de sessões normais que têm qualquer fração dentro do ano; uma sessão cruzando o ano conta uma vez. |
| Visão geral | Jogos e plataformas | Contagens distintas com tempo maior que zero dentro do ano. |
| Visão geral | Média de sessão | Tempo total dividido por sessões; “—” quando não houver sessões. |
| Destaque | Jogo do ano | Maior tempo no ano; desempate por número de sessões, depois título e `external_game_id`. |
| Destaque | Plataforma do ano | Maior tempo entre plataformas; mesmos critérios de desempate. |
| Destaque | Mês e dia mais ativos | Maior tempo acumulado no período; empate favorece o período mais recente. |
| Hábitos | Horário favorito | Hora local de 0 a 23 com maior tempo após fracionamento horário; em empate, mostrar todas as horas empatadas ou o intervalo de horas, sem escolher arbitrariamente. |
| Hábitos | Maior sequência | Maior sequência de dias consecutivos com ao menos um segundo de jogo normal. |
| Hábitos | Sessão mais longa | Sessão individual de maior duração registrada no ano; se cruzar o ano, apresentar sua duração total e sinalizar que atravessou a fronteira anual. |
| Hábitos | Dia mais diverso | Dia com maior número de jogos distintos com tempo maior que zero; desempate pelo maior tempo do dia. |
| Distribuição | Concentração | Percentual do tempo total representado pelo jogo do ano e pelo top 3. Só exibir se o denominador for maior que zero. |

### 4.1 Rankings

- Exibir os 10 jogos e 10 plataformas com maior tempo no ano, ou todos quando houver menos itens.
- Para cada item, mostrar posição, título, tempo, sessões e participação percentual no tempo anual.
- Barras horizontais são normalizadas pelo primeiro colocado, mas o texto sempre informa o valor absoluto para evitar interpretação enganosa.
- Itens empatados dividem a mesma posição visual; o próximo número de posição salta de acordo com a classificação densa (`1, 1, 2`) para facilitar a leitura.

### 4.2 Calendário anual

1. Exibir todos os dias do ano, incluindo dias sem atividade, em uma grade de calor mensal.
2. A intensidade representa o tempo jogado no dia. A escala deve usar quatro ou cinco faixas calculadas sobre os dias com atividade, preservando uma faixa distinguível para o menor valor positivo.
3. Cada célula oferece, por foco ou clique, data, tempo total, sessões e até três jogos mais jogados naquele dia.
4. Dia sem atividade tem rótulo acessível “sem atividade registrada”; cor isoladamente não pode ser a única informação.
5. O calendário usa sessões já fracionadas na meia-noite; uma sessão que cruza dois dias contribui ao dia correto.

### 4.3 Atividade mensal e horário

- O gráfico mensal inclui os 12 meses, inclusive valores zero, e apresenta tempo e sessões no tooltip/alternativa textual.
- A distribuição por hora inclui as 24 horas e também fraciona sessões que cruzam uma hora. Ela pode ser apresentada como gráfico circular de 24 horas ou barras; a alternativa tabular é obrigatória.
- Para relatórios com menos de 7 dias ativos, exibir uma observação de amostra pequena e evitar linguagem de preferência (“seu horário favorito”). Usar “horário com mais tempo registrado”.

### 4.4 Métricas adicionais da apresentação "Replay"

Derivadas das mesmas sessões normais do ano, para alimentar o layout da §6:

- **Novos jogos no ano**: jogos cujo primeiro registro (first_played) cai no ano.
- **Dia/Noite**: fração do tempo nas horas 6–18 (dia) vs. demais (noite),
  calculada sobre o histograma horário já fracionado.
- **Maior sequência (datas e jogos)**: além do tamanho, o intervalo (início e fim)
  da maior sequência de dias consecutivos e o conjunto de jogos jogados nesse
  intervalo.
- **Por jogo (top 3)**: distribuição mensal do próprio jogo e sua maior sequência
  de **dias consecutivos** no ano.

Essas métricas obedecem às mesmas regras de fracionamento e exclusão de sessões
inválidas/zero das seções anteriores.

## 5. Narrativa e linguagem

A abertura é derivada de modelos locais e factuais, nunca de IA remota. Ela cita apenas dados já visíveis no relatório.

Exemplos válidos:

- “Em 2026, você registrou 142 h 18 min em 38 jogos.”
- “Seu jogo com mais tempo foi *Forza Horizon 2*, com 24 h 10 min.”
- “Outubro foi seu mês mais ativo, e você manteve uma sequência de 6 dias.”

Exemplos proibidos:

- “Você terminou 12 jogos.”
- “Foi um ano mais feliz/relaxante.”
- “Você prefere jogos de corrida.”

Se a cobertura do ano não abranger de janeiro a dezembro, a narrativa acrescenta “com base no histórico disponível de [data] a [data]” e não usa superlativos absolutos como “seu ano inteiro”.

## 6. Layout e interação (estilo "Replay")

A apresentação segue o formato "Year in Review"/"Replay": uma história vertical,
rolável e centrada, inspirada no Steam Replay e no Playnite Year in Review.

```text
Retrospectiva                                              [ ‹ ] [ 2026 ▾ ] [ › ]  [Imprimir]
<narrativa factual> — histórico parcial (…) · até hoje

┌─ RETROSPECTIVA 2026 · <usuário> ─┐ ┌─ Sessões ──────┐ ┌─ Dia/Noite ─────┐
│ 28  Jogos jogados                │ │ 106            │ │ 42% de dia      │
│ ▲ N a mais que em 2025           │ │ ▲/▼ vs 2025    │ │ 58% de noite    │
│ Novos: 28 · Plataformas: 9       │ │ 17h52 · 10 dias│ │                 │
└──────────────────────────────────┘ └────────────────┘ └─────────────────┘
[ capa top 1 · 41% · 31 sess. ] [ capa top 2 ] [ capa top 3 ]     (tiles de capa)

Onde você jogou (radar de plataformas)        Os números (lista com líderes)

Vamos dar uma olhada nos seus jogos mais jogados…
┌ banner (capa + título + 9% / sessões / dias consecutivos) ┐  (herói por jogo, top 3)
│ gráfico mensal do jogo · faixa de screenshots · "Ver na biblioteca"
└───────────────────────────────────────────────────────────┘

Sua maior sequência diária: N
<data início> ───────────────────── <data fim>
Durante esse tempo, você jogou M jogos diferentes:  [capas…]  [Exibir mais]
```

### Blocos

1. **Grade de destaques**: tiles grandes (Jogos jogados com variação vs. ano
   anterior; Sessões com variação; distribuição **dia/noite**) e três **tiles de
   capa** dos jogos mais jogados (% do tempo e nº de sessões).
2. **Onde você jogou**: gráfico de **teia/radar** com as plataformas de maior
   tempo (substitui o radar de gêneros da referência, inexistente na fonte).
3. **Os números**: lista com líderes pontilhados (tempo total, sessões, jogos,
   plataformas, novos jogos, maior sequência, inícios rápidos, sessão mais longa).
4. **Heróis dos jogos mais jogados** (top 3): banner com capa, título, subtítulo
   factual e três estatísticas (% do tempo total, sessões, **dias consecutivos**),
   seguido do **gráfico mensal do jogo** e da **faixa de capturas de tela**.
5. **Maior sequência diária**: título com o tamanho, linha do tempo com datas de
   início e fim e as **capas dos jogos** jogados no período ("Exibir mais").

### Adaptações de escopo

Como a fonte não tem conquistas, dispositivo de entrada nem gênero, os painéis
análogos da referência são substituídos por métricas reais: **plataformas** no
lugar de gêneros; **dia/noite** (histograma horário) no lugar de mouse/controle;
"Os números" com métricas locais. "Página da loja" não existe (sem rede); resta
"Ver na biblioteca" (abre os detalhes locais).

As capas usam o mesmo placeholder da Biblioteca quando não há arte local. Todos os
elementos que levam ao detalhe de um jogo são clicáveis e navegáveis por teclado.

## 7. Comparação anual

Comparação só aparece se o ano anterior possuir pelo menos uma sessão normal válida e cobertura observada de pelo menos 30 dias. Ela apresenta variação absoluta e percentual de:

- tempo jogado;
- sessões;
- jogos distintos;
- plataformas distintas;
- maior sequência.

Se o relatório atual for de ano em curso ou um dos anos tiver cobertura parcial, a comparação recebe o aviso **“comparação parcial: os períodos observados não representam anos completos”**. Porcentagens não são calculadas contra zero; nesse caso, mostrar somente o valor absoluto e uma explicação.

## 8. Qualidade, erros e privacidade

- Um resumo de qualidade informa sessões inválidas/ignoradas, sessões rápidas excluídas e intervalo de cobertura observada.
- Nenhuma visualização deve falhar se faltarem capa, plataforma ou metadados locais. Usar placeholder “Plataforma não informada” quando necessário.
- O relatório não usa rede, contas, compartilhamento, importação de relatórios de terceiros ou leaderboard. A impressão é local pelo diálogo nativo do Qt.
- O cache de agregados, se houver, é invalidado por nova importação, mudança de fuso, mudança de versão de cálculo ou alteração de metadados que afetem a apresentação.

## 9. Componentes de domínio e testes

Implementar os cálculos em módulos Python sem Qt:

```text
services/year_review/
  session_splitter.py       # ano, mês, dia e hora, sem perdas de segundos
  calculator.py             # YearReview a partir de sessões válidas
  narrative.py              # textos factuais locais
  comparison.py             # regras e avisos de comparação anual
  coverage.py               # intervalo e status de cobertura observada
  models.py                 # YearReview e objetos de apresentação
```

Testes unitários obrigatórios:

1. sessão que começa em dezembro e termina em janeiro;
2. sessão que cruza meia-noite e mudança de hora;
3. repartição de uma sessão entre duas horas sem perder nem duplicar segundos;
4. ano bissexto e calendário com 366 dias;
5. empates em jogo, plataforma, mês, dia e horário;
6. sessão zero, negativa, inválida e divergente;
7. denominador zero em percentuais e comparação anual;
8. fuso configurado diferente do offset de origem;
9. dados parciais que exigem aviso de cobertura;
10. invariância: a soma dos agregados mensais, diários e horários é igual ao tempo total anual.

## 10. Critérios de aceite

1. A retrospectiva de um ano com dados mostra o jogo do ano, indicadores, top 10, plataformas, gráfico mensal, calendário e distribuição por hora com valores consistentes entre si.
2. A soma do calendário, dos meses e das 24 horas é igual ao tempo total exibido no relatório, respeitando a tolerância de arredondamento da apresentação.
3. Sessões que atravessam dia, mês, hora ou ano são repartidas corretamente sem omissão ou dupla contagem.
4. Um ano sem sessões normais mostra um estado vazio explícito, sem narrativa nem rankings fictícios.
5. O ano atual é identificado como parcial; comparações de cobertura parcial são sinalizadas.
6. Foco de teclado em célula do calendário, barra de ranking ou gráfico fornece a mesma informação essencial disponível visualmente.
7. A retrospectiva funciona integralmente sem rede e nenhuma ação dela gera tráfego de rede.
