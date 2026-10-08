# ES-DB — Especificação de Design (Biblioteca)

> **Nota de versão.** O *shell* da aplicação (barra superior, navegação e janela)
> foi reformulado no estilo Playnite/Helium e passou a ser definido em
> [INTERFACE.md](INTERFACE.md); os filtros, antes na
> barra e no menu lateral, estão em [FILTROS.md](FILTROS.md).
> As seções 3 (menu lateral) e 4 (barra de ferramentas) abaixo descrevem o
> **desenho de referência original** da Biblioteca; onde divergirem do shell
> atual, valem a interface e os filtros. As seções 5 e 6 (**grade, cards,
> visualização em lista e estados**) permanecem vigentes.

## 1. Objetivo

Esta especificação define a experiência visual da tela de **Biblioteca** do ES-DB: todos os dados vêm do banco local e nenhuma interação depende de rede.

A tela privilegia descoberta e leitura rápida: o usuário escolhe plataformas nos filtros, ajusta a visualização e explora seus jogos em uma grade de capas.

## 2. Estrutura da tela

```text
┌───────────────────────────────────────────────────────────────────────────┐
│ Barra de ferramentas: busca | período | ordenar | visualização | atualizar│
├──────────────────┬────────────────────────────────────────────────────────┤
│ Início           │                                                        │
│ Biblioteca       │  Título e contexto                                     │
│ Estatísticas     │  “Todos os jogos” · 128 jogos · 342 h                  │
│ Linha do tempo   │                                                        │
│ Retrospectiva    │                                                        │
│ Configurações    │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│                  │  │  capa  │ │  capa  │ │  capa  │ │  capa  │           │
│ Todas (128)      │  │        │ │        │ │        │ │        │           │
│ Plataformas      │  └────────┘ └────────┘ └────────┘ └────────┘           │
│ ▸ PlayStation 2  │  título     título     título     título               │
│ ▸ PlayStation 3  │  plataforma · tempo jogado                             │
│ ▸ Mega Drive     │                                                        │
│ ▸ SNES           │                                                        │
│ ▸ Xbox 360       │                                                        │
│                  │                                                        │
│ ...              │                                                        │
└──────────────────┴────────────────────────────────────────────────────────┘
```

Os números e títulos na ilustração são apenas exemplos. A barra superior permanece visível; o menu lateral e o conteúdo abaixo dela podem rolar de forma independente.

## 3. Navegação lateral — plataformas

### Conteúdo

O menu lateral ocupa o lado esquerdo e contém:

1. A navegação principal: **Início**, **Biblioteca**, **Estatísticas**, **Linha do tempo**, **Retrospectiva** e **Configurações**.
2. A seção de filtros da Biblioteca, visível quando Biblioteca está ativa.
3. **Todos os jogos**, com o total de jogos que possuem pelo menos uma sessão válida.
4. A seção **Plataformas**, em ordem alfabética pelo nome legível (`games.platform`).
5. Um item por plataforma, com nome e total de jogos jogados nela.

As plataformas vêm exclusivamente dos dados importados. Não há plataformas vazias, lista fixa de sistemas nem ícones baixados da internet. O identificador técnico `system` não é mostrado na navegação principal.

### Seleção e comportamento

- Ao abrir o aplicativo, **Início** é o destino padrão. Ao abrir Biblioteca, **Todos os jogos** é a seleção inicial e remove o filtro de plataforma.
- A navegação principal troca de página; não é um filtro. **Estatísticas** abre o painel analítico geral e **Retrospectiva** abre a visão anual.
- Clicar ou pressionar Enter em uma plataforma aplica esse filtro a toda a Biblioteca: título, contagem, grade, busca, ordenação e estado vazio.
- O item selecionado deve ter contraste claro, indicador visual persistente e texto acessível indicando “selecionado”.
- A seleção permanece ao alternar entre grade e lista e enquanto o usuário altera busca, ordem ou período.
- Quando uma plataforma não tem resultado após busca/filtro de período, ela continua selecionável e mostra o estado vazio; não some do menu.
- Com muitas plataformas, apenas a seção Plataformas rola internamente. A navegação principal e o item Todos os jogos permanecem fixos.
- No tamanho mínimo de janela suportado, o menu pode ser recolhido por um botão na barra superior. Quando recolhido, deve continuar acessível por teclado e exibir dicas de ferramenta nos ícones.

### Componentes Qt

- `QListView` ou `QTreeView` com modelo próprio para os itens da navegação.
- `QSortFilterProxyModel` para eventual filtro de plataformas, sem recriar widgets.
- `QSplitter` entre menu e área de conteúdo, permitindo ao usuário ajustar a largura.
- Largura inicial: 240 px; mínimo: 192 px; máximo: 320 px.

## 4. Barra de ferramentas

A barra de ferramentas é horizontal, no topo da área de conteúdo, e não deve ser confundida com o menu lateral.

| Ordem | Controle | Comportamento |
| --- | --- | --- |
| 1 | Alternar menu lateral | Recolhe/expande a navegação de plataformas. |
| 2 | Busca | Campo com ícone e atalho `Ctrl+F`; filtra por título, plataforma e caminho da ROM. Placeholder: “Buscar jogos…”. |
| 3 | Período | `QComboBox` com 7 dias, 30 dias, mês atual, ano atual, todo o histórico e intervalo personalizado. Afeta métricas e disponibilidade dos jogos na grade conforme o filtro escolhido. |
| 4 | Ordenar | `QComboBox`: mais jogado, jogado recentemente, título A–Z e número de sessões. Padrão: mais jogado. |
| 5 | Alternar visualização | Botões exclusivos para **Grade** e **Lista**; Grade é o padrão. |
| 6 | Atualizar dados | Botão com ícone e texto acessível; executa a sincronização local e exibe seu estado. |

Em larguras menores, os controles devem reduzir de forma previsível: busca preservada e expansível; período, ordenação e visualização agrupados em um menu de opções; botão de atualização mantido como ícone com dica de ferramenta.

## 5. Área de conteúdo

### Cabeçalho de contexto

Acima da grade, mostrar:

- título da seleção: **Todos os jogos** ou o nome da plataforma;
- quantidade de jogos no resultado atual;
- tempo jogado acumulado no período, quando houver;
- chips dos filtros ativos, removíveis individualmente, exceto o filtro de plataforma selecionado no menu lateral.

Exemplo: `PlayStation 2 · 34 jogos · 82 h 16 min`.

### Grade de jogos

A grade é a visualização principal. Cada card representa um jogo e contém:

1. Capa em proporção vertical (recomendação: 2:3), obtida automaticamente de
   `downloaded_media/<system>/covers/` do ES-DE por junção determinística
   ([ESDE.md](ESDE.md) §4).
2. Placeholder ilustrado com iniciais do título quando não houver capa
   correspondente no ES-DE nem capa local informada pelo usuário.
3. Título em até duas linhas, com elipse ao exceder.
4. Plataforma em uma linha secundária.
5. Tempo jogado no período selecionado e quantidade de sessões.
6. Indicador discreto de “jogado recentemente” quando a última sessão estiver nos últimos 7 dias.

Não usar capas remotas: as capas são **arquivos locais** — as que o ES-DE já
baixou ou as que o usuário informar. Elas devem ser carregadas de forma
assíncrona, com cache de miniaturas local em `~/ES-DB/cache/`, para não
bloquear a interface.

| Largura da área de conteúdo | Colunas preferenciais | Largura mínima do card |
| --- | --- | --- |
| 1.024–1.279 px | 3 | 208 px |
| 1.280–1.679 px | 4 | 220 px |
| 1.680–2.159 px | 5 | 228 px |
| 2.160 px ou mais | 6 | 240 px |

O número de colunas pode diminuir para respeitar a largura mínima. Espaçamento entre cards: 20 px; margem interna da área: 24 px.

### Interações do card

- Clique ou Enter abre a página de detalhes do jogo.
- Foco por teclado mostra borda de alto contraste sem depender apenas de sombra ou cor.
- Hover eleva levemente o card e revela ações secundárias, sem esconder informações essenciais.
- Menu de contexto: abrir detalhes, copiar caminho da ROM e editar metadados locais.
- A seleção de um card não altera o filtro de plataforma.

### Visualização em lista

A lista é alternativa à grade e usa as mesmas fontes, filtros e ordenação. Cada linha mostra miniatura, título, plataforma, tempo total no período, sessões e última vez jogado. Ela é indicada para bibliotecas extensas e deve usar `QTableView` ou `QListView` virtualizado.

### Screenshots nos detalhes do jogo

A página de detalhes inclui a seção **Screenshots** após o histórico de sessões. Ela mostra contador de capturas, grade de miniaturas locais e ação para abrir o visualizador. Quando houver muitas imagens, carregar inicialmente apenas as miniaturas visíveis e o restante sob demanda.

O visualizador abre sobre a página de detalhes, com navegação anterior/próxima, zoom, ajuste à janela e metadados do arquivo. A associação, varredura, estados de erro e regras de acesso local são definidos em [SCREENSHOTS.md](SCREENSHOTS.md). Não exibir controles de mover, apagar ou compartilhar arquivos.

## 6. Estados da Biblioteca

| Estado | Apresentação | Ação principal |
| --- | --- | --- |
| Carregando | Esqueletos de cards e texto “Carregando biblioteca…” | Nenhuma; preservar o último resultado quando existir. |
| Sem fonte | Ilustração local, explicação curta | “Selecionar banco de dados”. |
| Sem jogos | Mensagem de que ainda não há sessões importadas | “Atualizar dados”. |
| Sem resultado | Ícone de busca, filtros ativos e mensagem contextual | “Limpar filtros”. |
| Fonte indisponível | Aviso não bloqueante no topo, com o caminho configurado | “Tentar novamente” ou “Alterar fonte”. |
| Erro de importação | Aviso com resumo e link para Integridade | “Ver detalhes”. |

## 7. Página de Estatísticas

A aba **Estatísticas** apresenta os hábitos do jogador no período global selecionado. É uma página própria: não mostra a grade de jogos nem a lista de plataformas como conteúdo principal.

### Estrutura

1. Cabeçalho com título **Estatísticas**, seletor de período e resumo do filtro atual.
2. Faixa de indicadores: tempo jogado, sessões, média por sessão, jogos jogados e plataformas exploradas.
3. Gráfico de atividade por dia ou semana, com alternância entre as duas granularidades.
4. Distribuição de tempo por plataforma.
5. Ranking dos jogos mais jogados, com título, plataforma, tempo e sessões.
6. Bloco de hábitos: dia mais ativo, horário mais frequente, maior sequência e última sessão registrada.

Os cards de indicadores e gráficos devem responder ao mesmo seletor de período. Um clique em jogo ou plataforma leva à respectiva página filtrada; essa navegação não altera silenciosamente as métricas já exibidas.

### Regras visuais

- Indicadores em cards compactos, priorizando o valor e depois o rótulo.
- Gráficos com legenda, tooltip acessível e alternativa em tabela ou texto.
- Rankings em lista numerada; os três primeiros podem receber realce discreto, sem usar cor como único diferenciador.
- Quando não houver sessões normais no período, mostrar zeros, explicação curta e ação para alterar o período; não exibir gráficos artificiais.

## 8. Página de Retrospectiva

A aba **Retrospectiva** mostra uma leitura anual da jornada do jogador. Ela combina narrativa curta e estatísticas consolidadas para responder “como foi meu ano jogando?”.

Os cálculos, regras de cobertura, calendário anual, distribuição por hora, comparações e critérios de robustez estão definidos em [RETROSPECTIVA.md](RETROSPECTIVA.md).

### Estrutura

1. Cabeçalho com título **Retrospectiva**, seletor de ano e opção de navegar para ano anterior/próximo quando houver dados.
2. Card de abertura com a narrativa baseada nos dados — por exemplo, “Em 2026, você jogou 142 horas em 38 jogos”.
3. Indicadores anuais: tempo total, sessões, jogos, plataformas, média por sessão e maior sequência.
4. Destaques do ano: jogo mais jogado, plataforma favorita, mês mais ativo e dia mais ativo.
5. Linha ou barras de atividade por mês, permitindo visualizar períodos de maior e menor atividade.
6. Calendário anual de atividade e distribuição do tempo pelas 24 horas do dia.
7. Ranking anual dos 10 jogos e plataformas mais jogados, com participação no tempo do ano.
8. Comparação com o ano anterior quando ambos tiverem dados: variação de tempo, sessões, jogos e plataformas. Sem ano anterior comparável, substituir por explicação neutra.

### Regras da retrospectiva

- O seletor de ano é próprio da página; ele não é substituído pelo seletor de período da Biblioteca ou Estatísticas.
- O ano atual usa dados até o momento da consulta, com o rótulo “até hoje”.
- As mesmas regras de cálculo da especificação principal se aplicam: sessões de duração zero não compõem tempo, jogos jogados, sequência ou destaques por tempo.
- Sessões que cruzam meia-noite, uma hora, mês ou ano são fracionadas antes de alimentar calendários e gráficos.
- A narrativa só pode afirmar fatos obtidos das métricas exibidas na página. Não deve inferir gênero, conclusão de jogo, humor ou hábitos não registrados.
- Quando o intervalo de sessões observadas não cobrir todo o ano, a página deve avisar que a retrospectiva usa histórico parcial.
- A primeira versão permite imprimir pelo diálogo nativo do Qt. Exportação dedicada para imagem/PDF permanece evolução futura.

## 9. Direção visual

- Tom: diário de jogos contemporâneo e acolhedor; evitar aparência de planilha ou painel corporativo.
- Fundo: neutro escuro no tema escuro e neutro quente/claro no tema claro.
- Hierarquia: as capas são o elemento de maior cor; chrome da interface e cards devem ser discretos.
- Tipografia: fonte sans-serif nativa do sistema; título de jogo com peso semibold; metadados com contraste suficiente e menor peso.
- Cor: uma cor de destaque configurada pelo tema, reservada para seleção, foco e ações primárias. Não usá-la como única indicação de estado.
- Forma: raios moderados (8–12 px), sombras sutis apenas em hover/elevado e espaçamento generoso.
- Temas: claro, escuro e seguir o sistema. A mudança de tema não deve alterar a posição ou o estado dos filtros.

## 10. Acessibilidade e atalhos

- Ordem de foco: navegação principal → filtros de plataforma (em Biblioteca) → barra de ferramentas → cabeçalho de contexto → conteúdo da página.
- `Tab` e `Shift+Tab` navegam entre regiões; setas navegam entre itens da barra lateral e cards; Enter abre a seleção; Esc limpa foco de busca ou fecha menus.
- `Ctrl+F`: focar busca. `Ctrl+R`: atualizar dados. `Ctrl+1`: grade. `Ctrl+2`: lista.
- Todos os ícones têm `accessibleName`, `accessibleDescription` quando necessário e dica de ferramenta.
- Contraste mínimo de 4,5:1 para texto normal; estado de foco sempre perceptível.
- Gráficos e ícones devem ter alternativa textual nos detalhes do item ou por dicas de ferramenta.

## 11. Critérios de aceite

1. A navegação segue o shell atual (pílulas **Resumo · Estatísticas · Atividade · Conquistas · Retrospectiva**, com Biblioteca e Configurações fora das pílulas), conforme [INTERFACE.md](INTERFACE.md). As seções 3 e 4 deste documento descrevem o menu lateral de referência original e não prevalecem onde divergirem da Interface.
2. Ao abrir a Biblioteca, o usuário vê a grade de jogos e **Todos os jogos** selecionado no menu de plataformas.
3. A lista de plataformas corresponde aos valores únicos de `games.platform` dos jogos importados e mostra a contagem correta de jogos em cada uma.
4. Ao selecionar uma plataforma, a grade, cabeçalho e resultados de busca refletem apenas jogos daquela plataforma.
5. A busca, o período e a ordenação podem ser combinados sem perder a plataforma selecionada.
6. Um card sem capa usa placeholder local legível e nunca tenta consultar a internet.
7. Grade e lista exibem os mesmos jogos e métricas sob os mesmos filtros.
8. Estatísticas mostra os indicadores, gráficos, rankings e hábitos do período selecionado com valores consistentes com as regras de cálculo.
9. Retrospectiva mostra indicadores e destaques do ano selecionado; quando houver ano anterior comparável, mostra a comparação; quando não houver, comunica essa ausência sem erro.
10. Nos detalhes do jogo, a seção Screenshots abre o visualizador local e não oferece operações que modifiquem as imagens de origem.
11. Com 10 mil jogos, a rolagem permanece fluida e a interface não bloqueia ao filtrar, ordenar ou carregar miniaturas.
12. Toda função descrita pode ser executada por teclado, e a seleção/foco tem contraste visível nos temas claro e escuro.
13. A Biblioteca permanece utilizável entre 1.024 px e 2.560 px de largura; o menu lateral pode ser recolhido sem perder acesso às plataformas.
