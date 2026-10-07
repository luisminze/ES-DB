# ES-DB — Atualização 1 (Update1)

Consolidação das mudanças solicitadas na primeira rodada de atualização. Todas
foram implementadas de forma **original**, mantendo a identidade visual (carvão +
acento vermelho, rótulos "kicker") e funcional do projeto, sem rede.

## 1. Retrospectiva ([RETROSPECTIVA.md](RETROSPECTIVA.md))

- **Removidos** o calendário anual de atividade e a distribuição por hora.
- **Banner de destaques** abaixo do podium dos 3 jogos mais jogados: números
  grandes (Jogos jogados, Sessões, Dia/Noite) com **comparação ano-a-ano**
  (▲ "N a mais que em AAAA" / ▼ "N a menos"; "sem base comparável" quando não há
  ano anterior) e sub-informações (novos no ano, plataformas, tempo, maior
  sequência, média por sessão).
- **"Explore os jogos que \<usuário\> jogou neste ano"**: grade de até **100
  jogos** com capa do ES-DE, **% do tempo do ano** e **número de vezes jogadas**
  (`N×`), e selo **"1ª VEZ"** para jogos cujo primeiro registro cai no ano.
- **Abertura** acima do podium: "Aqui vai o ano AAAA" — ano em destaque vermelho,
  nome do usuário e tempo total do ano.

## 2. Navegação e Resumo ([INTERFACE.md](INTERFACE.md))

- A **Biblioteca** passou a ser a primeira pílula e a página inicial padrão; o
  **Resumo** foi reposicionado (acesso pelo rodapé da navegação).
- O **Resumo** passou a **englobar** os dados das abas **Estatísticas**,
  **Conquistas** e **Retrospectiva** em um único painel de visão geral
  (indicadores + rankings do período; nível/pontuação + anéis de conquistas;
  banner anual + capas do ano com atalho "Ver retrospectiva completa").

## 3. Atividade ([ATIVIDADE.md](ATIVIDADE.md))

- O feed passou a incluir, **cronologicamente**, os **desbloqueios de
  conquistas** (ícone do troféu + "Você desbloqueou \"X\" em \<jogo\> (grau)"),
  intercalados com as sessões e marcos.

## 4. Pontuação e níveis de conquistas ([CONQUISTAS.md](CONQUISTAS.md))

### Sony (RPCS3 · shadPS4)

Pontuação local baseada no sistema oficial da Sony, por troféu desbloqueado:

| Grau | Pontos |
| --- | --- |
| Bronze | 15 |
| Prata | 30 |
| Ouro | 90 |
| Platina | 300 |

Exemplo: 100 Bronze + 20 Prata + 10 Ouro + 2 Platina = **3.600 pontos**.

**Nível** (categoria por pontos acumulados), atualizado automaticamente:

| Pontos | Categoria |
| --- | --- |
| 1–299 | 🥉 Bronze |
| 300–599 | 🥈 Prata |
| 600–998 | 🥇 Ouro |
| ≥ 999 | 🏆 Platina |

### Xbox (Xenia)

**Gamerscore** = soma do valor (G) de todas as conquistas desbloqueadas
(ex.: 10 + 20 + 50 + 100 = 180G).

### Anéis da aba Conquistas

Quatro gráficos de anel (donut) no topo da aba, na identidade do ES-DB:
**Jogos 100%** (percentual de jogos totalmente desbloqueados), **Por plataforma**
(desbloqueios por emulador), **Por troféu** (por grau) e **Raras** (ouro +
platina). A aba também exibe o nível/pontuação Sony e o Gamerscore.

## 5. Barra superior e controles ([INTERFACE.md](INTERFACE.md))

- Os ícones de **Filtros, Atualizar e Configurações** foram agrupados no **canto
  superior direito** e **aumentados** para um tamanho adequado.
- Correção dos seletores (`QComboBox` de Período e Ano): a **borda direita**
  deixou de ficar quebrada e passou a ter cantos arredondados simétricos.

## 6. Filtros ([FILTROS.md](FILTROS.md))

- O painel de Filtros virou um **menu suspenso** (popup) ancorado ao ícone de
  Filtros, **renovado** em colunas: **Plataformas**, **Gênero (ES-DE)**,
  **Desenvolvedora (ES-DE)** e **Opções**, com predefinições (salvar/aplicar/
  excluir) e os botões Limpar/Aplicar.

## 7. Repositório

As alterações foram documentadas aqui e commitadas/enviadas ao GitHub
(`luisminze/ES-DB`).
