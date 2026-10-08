# ES-DB — Atualização 2 (Update2)

Segunda rodada de ajustes, mantendo a identidade visual e funcional do projeto.

## 1. Página de Conquistas ([CONQUISTAS.md](CONQUISTAS.md))

- Os **anéis** (Jogos 100%, Por plataforma, Por troféu, Raras) foram movidos para
  **baixo de tudo** (rodapé da página), após a lista de jogos e o detalhe.
- Os cartões de **pontuação/nível** (Nível Sony + pontos + Gamerscore) foram
  **reduzidos** e reposicionados no **canto superior direito** da página, em uma
  única linha compacta: `Nível <categoria> · <pts> pts · <G> G`, com a
  distribuição por grau e os pontos que faltam para o próximo nível.

## 2. Aba Atividade — agrupamento por jogo/dia ([ATIVIDADE.md](ATIVIDADE.md))

O feed deixou de listar eventos avulsos e passou a **agrupar, por jogo e por
dia**, tudo o que aconteceu com aquele jogo naquele dia:

- **Horas jogadas** (soma das sessões do dia) e selo de "primeira vez jogando".
- **Marcos** de tempo acumulado (ex.: "Alcançou 1 h de jogo").
- **Conquistas** desbloqueadas naquele dia (nome + grau).
- **Screenshots** registradas naquele dia (data obtida pela modificação do
  arquivo, melhor-esforço).

Cada card mostra a capa, o título do jogo, a data e as linhas de atividade.
Quando um dado do mesmo jogo ocorre em outro dia, é criado **um novo card** para
aquele dia (um card por jogo por dia).

## 3. Ativar/desativar conquistas ([CONQUISTAS.md](CONQUISTAS.md))

Em **Configurações → Conquistas** há a opção **"Habilitar conquistas"**:

- **Habilitado** (padrão): permanece como está — aba Conquistas, pontuação,
  anéis, conquistas no feed e no Resumo.
- **Desabilitado**: **tudo relacionado a conquistas é ocultado** — a pílula
  Conquistas some da navegação, o feed de Atividade não mostra desbloqueios, o
  Resumo não exibe a seção de conquistas e as pastas dos emuladores ficam
  ocultas nas Configurações. Ao alternar a opção, **o aplicativo é reiniciado**
  para aplicar o novo estado.

A preferência é persistida em `config.json` (`achievements_enabled`).

## 4. Tema claro unificado e opção "Sistema" ([INTERFACE.md](INTERFACE.md))

- O **modo claro** foi corrigido e unificado: todo o aplicativo fica claro
  (painel, cards e texto), usando um branco **levemente mais escuro** para
  separar seções; o texto passa a ser escuro e o acento vermelho é um pouco mais
  forte para contraste sobre branco. Os gráficos (anéis, radar, barras mensais) e
  os ícones da barra superior passaram a seguir o tema ativo.
- A seleção de tema foi renomeada para **Claro / Escuro** e ganhou a opção
  **Sistema**, que segue automaticamente o esquema de cor do sistema operacional
  (e reaplica quando o SO troca).

## 5. Pasta do programa renomeada

A pasta de dados do aplicativo passou de `~/ES-DE-STATS` para **`~/ES-DB`** e o
subdiretório de bancos de `DATABASE/` para **`database/`** (variável de ambiente
`ES_DB_HOME`). Estrutura: `~/ES-DB/{database,derived,cache}` + `config.json`.

### Casamento de jogo (sessão × conquista)

Como o título da conquista do emulador pode diferir do título da sessão
(`God of War: Ascension™` vs `God of War : Ascension`), o agrupamento usa um
**título normalizado** (sem `™/®/©`, sem pontuação, caixa única) para unir a
sessão e as conquistas do mesmo jogo no mesmo card. Sem correspondência, as
conquistas formam seu próprio grupo pelo título do emulador.
