# ES-DB — Painel de Filtros da Biblioteca

> Inspirado no painel de filtros do **Playnite (modo Desktop)**, reduzido ao
> escopo do projeto. Acionado pelo botão **Filtros** da barra superior
> ([INTERFACE.md](INTERFACE.md) §2).

## 1. Objetivo

Concentrar, em um painel, todos os controles de refino da Biblioteca que antes
ficavam espalhados, mantendo o espírito do Playnite (multi-seleção, direção de
ordenação, opções e predefinições salvas). Os campos disponíveis dependem dos
dados existentes: além das sessões, o ES-DB usa os **metadados do ES-DE**
(`gamelist.xml`) quando o jogo tem correspondência ([ESDE.md](ESDE.md) §4).

## 2. Campos (RF-FL-01)

### 2.1 Sempre disponíveis (derivados das sessões)

| Campo | Tipo | Comportamento |
| --- | --- | --- |
| Plataformas | Multi-seleção (checkboxes) | Nenhuma marcada = todas. Várias marcadas combinam (OU). |
| Período | Seletor | Predefinidos + intervalo personalizado (RF-04). |
| Ordenar por | Combo + direção (▲/▼) | Mais jogado, jogado recentemente, título, nº de sessões; a direção inverte a ordem natural. |
| Visualização | Grade / Lista | Padrão: Grade. |
| Opções | Checkboxes | "Apenas jogados recentemente (7 dias)", "Ocultar inícios rápidos", "Apenas com screenshots", "Apenas com capa". |
| Limpar | Botão | Restaura todos os filtros ao padrão. |
| Predefinições | Combo + Salvar/Excluir | Presets nomeados (ver §4). |

### 2.2 Disponíveis com metadados do ES-DE

Estes campos aparecem **somente quando** há jogos com metadados correspondentes
no `gamelist.xml`; caso contrário, ficam ocultos. As opções de cada combo vêm
dos valores realmente presentes na biblioteca, em ordem alfabética.

| Campo | Tipo | Origem (`gamelist.xml`) |
| --- | --- | --- |
| Gênero | Multi-seleção | `genre` (valores combinam por OU) |
| Desenvolvedora | Multi-seleção | `developer` |
| Publisher | Multi-seleção | `publisher` |
| Jogadores | Seletor | `players` (1, 2, 2+…) |

Jogos sem metadados nunca são excluídos por um filtro de metadado vazio; um
filtro de gênero/desenvolvedora/publisher só restringe entre os jogos que
possuem aquele campo preenchido, e o painel indica quantos itens não têm
metadados.

## 3. Fora do escopo

Mesmo com o `gamelist.xml`, a fonte não possui estes dados, então **não** há
filtros de: lojas/bibliotecas, categorias, tags, séries, classificação etária,
região, notas de usuário/comunidade, conquistas como filtro, tamanho de
instalação, instalado/não instalado, favorito/oculto. A nota (`rating`) do
ES-DE é exibida na página do jogo, mas não é oferecida como filtro nesta versão.

## 4. Predefinições (presets) (RF-FL-02)

1. O usuário salva o conjunto atual de filtros com um nome; aplica e exclui
   predefinições.
2. As predefinições são **persistidas localmente** (JSON em `user_settings` do
   banco derivado) e incluem: plataformas, período, ordenação + direção,
   visualização, opções e, quando aplicável, gênero, desenvolvedora, publisher e
   jogadores.
3. Aplicar uma predefinição ajusta todos os controles e reconsulta a Biblioteca.

## 5. Comportamento

- Os filtros afetam a Biblioteca (grade/lista), o cabeçalho de contexto e os
  chips de filtros ativos.
- São combináveis com a busca da barra superior.
- O cabeçalho de contexto reflete a seleção: "Todos os jogos", o nome quando há
  uma só plataforma, ou "N plataformas".

## 6. Critérios de aceite

1. Marcar uma ou mais plataformas filtra a grade de acordo; nenhuma marcada mostra
   todas.
2. A direção de ordenação inverte o resultado do campo escolhido.
3. As opções (recentes, ocultar inícios rápidos, apenas com screenshots, apenas
   com capa) filtram corretamente e são combináveis.
4. Os filtros de gênero, desenvolvedora, publisher e jogadores aparecem quando há
   metadados do ES-DE e restringem corretamente; ficam ocultos quando não há
   metadados, e jogos sem metadado não somem por um filtro de metadado vazio.
5. Salvar uma predefinição e aplicá-la restaura exatamente o estado salvo; excluir
   a remove da lista.
6. Limpar devolve todos os filtros ao padrão sem afetar a plataforma via outra via.
7. Não existem filtros para os campos ausentes listados em §3.
