# ES-DB — Interface (Shell da Aplicação)

> **Atualização 1:** Biblioteca como pílula padrão; Resumo agregado; ícones da
> barra superior à direita e maiores; correção dos seletores; filtro em popup.
> Ver [ATUALIZACAO1.md](ATUALIZACAO1.md).

> Esta especificação define a **estrutura geral da interface** após a
> reformulação baseada no **Playnite (modo Desktop)** com o tema **Helium**.
> Ela substitui as partes de *layout de shell* (barra, navegação, janela) da
> [DESIGN.md](DESIGN.md); o detalhe da grade/cards/
> estados da Biblioteca continua naquele documento.

## 1. Direção visual

- Inspiração: Playnite Desktop + tema Helium — escuro, neutro, elegante.
- **Duas tonalidades**: um *chrome* (barra superior + navegação) e um **painel
  de conteúdo escuro arredondado**. No tema claro, o chrome é claro e o painel
  permanece escuro; no tema escuro, tudo é escuro e coeso.
- Cor de destaque **vermelha**, reservada a seleção, foco e ações primárias, e
  nunca como única indicação de estado (acessibilidade).

## 2. Estrutura

```text
┌───────────────────────────────────────────────────────────────────────────┐
│ ES-DB   [ Buscar jogos… ]  [ Filtros ]            [ Atualizar ]  [⚙]  │
├───────────┬───────────────────────────────────────────────────────────────┤
│ ( Resumo )│  ┌──────────────── painel de conteúdo (escuro) ─────────────┐  │
│ Estatíst. │  │  Título da página          Período [ … ]                  │  │
│ Atividade │  │  … conteúdo da página …                                   │  │
│ Conquistas│  │                                                           │  │
│ Retrosp.  │  └───────────────────────────────────────────────────────────┘  │
└───────────┴───────────────────────────────────────────────────────────────┘
```

### Barra superior

| Ordem | Elemento | Função |
| --- | --- | --- |
| 1 | Logo "ES-DB" | Identidade. |
| 2 | Busca | Campo em pílula, `Ctrl+F`; filtra a Biblioteca por título, plataforma e caminho da ROM. |
| 3 | Filtros | Abre o painel de filtros da Biblioteca (ver [FILTROS.md](FILTROS.md)). |
| 4 | Atualizar | Sincroniza os dados (`Ctrl+R`). |
| 5 | Engrenagem (⚙) | Abre **Configurações**. |

### Navegação lateral (pílulas)

Ordem fixa: **Resumo · Estatísticas · Atividade · Conquistas · Retrospectiva**.
A pílula selecionada recebe o destaque de acento. A **Biblioteca** não é uma
pílula: é alcançada por "Explorar biblioteca" (no Resumo), pela busca ou pelos
Filtros. **Configurações** é alcançada pela engrenagem.

### Painel de conteúdo

Cada página é exibida dentro de um painel escuro arredondado, com seu título à
esquerda e, quando aplicável, o seletor de **Período** à direita do cabeçalho.

## 3. Páginas

| Pílula | Página | Conteúdo |
| --- | --- | --- |
| Resumo | Início (painel) | Indicadores do período, destaques, evolução do tempo, atalhos. |
| Estatísticas | Estatísticas | Indicadores, gráficos e rankings (design §7). |
| Atividade | Atividade | Feed pessoal + Sessões ([ATIVIDADE.md](ATIVIDADE.md)). |
| Conquistas | Conquistas | Troféus por emulador ([CONQUISTAS.md](CONQUISTAS.md)). |
| Retrospectiva | Retrospectiva | Leitura anual estilo "Replay" ([RETROSPECTIVA.md](RETROSPECTIVA.md)). |
| (botão/⚙) | Biblioteca / Configurações | Grade de jogos; preferências e fontes. |

## 4. Tema e cores

A paleta separa **chrome** e **painel**:

| Papel | Escuro | Claro |
| --- | --- | --- |
| Fundo do chrome | `#0C0D10` | `#ECEEF1` |
| Superfície do chrome | `#141519` | `#FFFFFF` |
| Fundo do painel | `#15171C` | `#15171C` (escuro em ambos) |
| Texto do painel | `#E8EAED` | `#E8EAED` |
| Acento | `#EB5E54` | `#B5392C` |

- Três modos: **claro**, **escuro** e **seguir o sistema** (RF-10).
- Trocar o tema não altera a posição nem o estado dos filtros.
- Cantos arredondados (6–16 px), bordas sutis, pílulas e busca arredondadas.

### Animações

- Transições de página, hover de cards, troca de tema e abertura de painéis usam
  animações **suaves e fluidas**, curtas (120–240 ms) e com easing natural.
- As animações nunca bloqueiam a interação nem atrasam a exibição de dados; em
  listas grandes, preferir *fade*/opacidade a reflows custosos (RNF-13).
- Respeitar a preferência do sistema por **redução de movimento**: quando ativa,
  as transições são encurtadas ou suprimidas sem perda de função.

## 5. Acessibilidade e atalhos

- Todos os controles têm `accessibleName` e dica de ferramenta.
- Foco sempre perceptível (contorno de acento), além da cor.
- Contraste mínimo 4,5:1 para texto normal, incluindo o acento sobre o painel.
- Atalhos: `Ctrl+F` busca, `Ctrl+R` atualizar, `Ctrl+1` grade, `Ctrl+2` lista.

## 6. Responsividade

- Utilizável entre 1.024 px e 2.560 px (RNF-01).
- O painel de conteúdo e a grade se adaptam; a navegação em pílulas permanece
  acessível.

## 7. Critérios de aceite

1. A barra superior tem logo, busca, Filtros, Atualizar e engrenagem.
2. A navegação tem as cinco pílulas na ordem definida; a selecionada é destacada.
3. Biblioteca e Configurações são acessíveis sem serem pílulas.
4. O conteúdo aparece em painel escuro sobre o chrome, nos três temas, sem perder
   estado de filtros ao trocar de tema.
5. O acento é vermelho e nunca é a única indicação de estado.
6. Toda a navegação é operável por teclado, com foco visível.
