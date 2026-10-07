# ES-DB — Especificação de Produto e Técnica

## 1. Visão geral

O **ES-DB** é um aplicativo desktop exclusivamente local que transforma o
histórico de sessões de jogo — registrado por um script integrado ao
**ES-DE** (EmulationStation Desktop Edition) — em uma experiência visual clara,
moderna e pessoal. A aplicação lê o banco de dados de sessões, consolida os
registros e centraliza, em uma única interface, as áreas **Resumo**,
**Estatísticas**, **Atividade**, **Conquistas** e **Retrospectiva**, além da
**Biblioteca** de jogos.

O ES-DB não inicia emuladores e nunca modifica as fontes que **analisa** (a
leitura é sempre em somente leitura). Como evolução de escopo, ele passou a
poder, de forma **local e opcional**, **criar o próprio banco de sessões** e
**instalar os scripts de evento do ES-DE** que o preenchem, além de **gerenciar
vários bancos** — ver [ESDE.md](ESDE.md).

A configuração é simplificada a um **único passo**: o usuário informa o
**diretório de configuração do ES-DE** (por padrão `~/ES-DE`). A partir dele, o
ES-DB identifica e utiliza automaticamente os recursos necessários — scripts,
imagens baixadas, metadados (`gamelist.xml`), banco de sessões e demais
arquivos de configuração — sem exigir ajustes manuais adicionais (§4, RF-01,
[ESDE.md](ESDE.md)). O armazenamento interno do próprio ES-DB (banco derivado,
cache e bancos de sessão geridos) fica sob a pasta do programa `~/ES-DE-STATS`
(§13 e [ESDE.md](ESDE.md) §2).

> As evoluções desta versão (integração com o ES-DE, gravação de sessões, nova
> interface, filtros, aba de Atividade e aba de Conquistas) estão consolidadas
> na **seção 14** e em especificações dedicadas.

### Princípio de operação local

Todo dado, processamento e interface permanecem no computador do usuário. O
aplicativo não deve fazer chamadas de rede, integrar contas, autenticar
usuários, consumir APIs externas, enviar telemetria ou sincronizar arquivos.
Ele deve funcionar integralmente com a rede desativada e sem solicitar
permissões de rede. Não haverá versão mobile nesta fase.

## 2. Problema e objetivo

Jogadores que usam o ES-DE acumulam centenas de títulos e sessões, mas não têm
uma visão centralizada sobre:

- quais jogos realmente jogam;
- quanto tempo investiram em cada plataforma e título;
- seus hábitos ao longo de dias, meses e anos;
- marcos e períodos que contam sua história com jogos.

O objetivo é permitir que o usuário compreenda e relembre sua atividade de jogo
em poucos segundos, com uma interface moderna, organizada e fluida, preservando
a privacidade: os dados permanecem no computador do usuário.

## 3. Público-alvo

- Usuários do ES-DE com um script que registra abertura e encerramento de jogos.
- Colecionadores de ROMs que querem visualizar a biblioteca que de fato usam.
- Jogadores retrô interessados em relatórios pessoais e retrospectivas anuais.

## 4. Premissas e limites

### 4.1 Fonte de sessões: esquema GameSessionTracker

O ES-DB lê o histórico de sessões de um SQLite no esquema **GameSessionTracker**.
Os scripts `game-start`/`game-end` (instalados no ES-DE) fornecem os dados a
partir dos hooks de evento do ES-DE; eventuais CSV/TXT exportados são artefatos
derivados e **não** são a fonte de importação.

O banco de sessões pode estar em dois lugares equivalentes, ambos sugeridos
automaticamente quando existirem:

- `~/ES-DE-STATS/DATABASE/<nome>.db` — banco criado e gerido pelo próprio ES-DB
  ([ESDE.md](ESDE.md));
- `~/GameSessionTracker/database/games.db` — instalação original do script
  (na máquina inspecionada: `/home/strokyze/GameSessionTracker/database/games.db`).

O banco contém as tabelas abaixo. A aplicação executa a consulta de sessão com
`JOIN`, sem depender de CSVs.

```sql
CREATE TABLE games (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  platform TEXT NOT NULL,
  system TEXT,
  rom TEXT,
  UNIQUE(name, platform)
);

CREATE TABLE sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id INTEGER NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  duration INTEGER NOT NULL,
  FOREIGN KEY(game_id) REFERENCES games(id)
);
CREATE INDEX idx_sessions_game ON sessions(game_id);
CREATE INDEX idx_sessions_start ON sessions(start_time);
```

| Campo de origem | Semântica e regra de leitura |
| --- | --- |
| `sessions.id` | Identificador externo, incremental e único. É a chave de sincronização. |
| `sessions.game_id` | Chave para `games.id`. |
| `sessions.start_time`, `end_time` | Texto no formato `%Y-%m-%dT%H:%M:%S%z`, por exemplo `2026-10-05T20:47:10-0300`. O parser precisa aceitar offset sem dois-pontos. |
| `sessions.duration` | Inteiro em segundos, calculado pelo script a partir dos horários. Pode ser `0` e nunca deveria ser negativo. |
| `games.name` | Nome recebido pelo hook e apresentado como título. |
| `games.platform` | Nome legível da plataforma, usado para navegação e agrupamento principal. É obrigatório. |
| `games.system` | Identificador técnico do sistema do ES-DE (por exemplo, `ps2` ou `xbox360`). É opcional como detalhe técnico, mas é a **chave de junção** com os recursos do ES-DE (§4.2). |
| `games.rom` | Caminho informado pelo hook. Pode conter barras invertidas antes de espaços/caracteres especiais e é atualizado a cada novo início do mesmo `(name, platform)`; portanto, não é identidade estável. O **basename sem extensão** é a chave de junção com a mídia/metadados do ES-DE (§4.2). |

O início de uma partida é escrito apenas em um arquivo efêmero de runtime; a
linha em `sessions` é inserida somente no encerramento. Logo, a fonte SQLite não
possui sessões abertas. Encerramentos anormais podem deixar o arquivo de
runtime, mas não devem produzir sessão parcial nem tempo estimado nesta versão
(ver o protocolo aprimorado em [RASTREAMENTO_SESSOES.md](RASTREAMENTO_SESSOES.md)).

O script aceita sessões de duração zero e já existem registros desse tipo. Elas
devem ser importadas e identificadas como **inícios rápidos**; por padrão contam
para quantidade de sessões, mas não para tempo, sequência de dias ou “jogos
jogados”. O filtro de qualidade permite ocultá-las.

### 4.2 Integração com o ES-DE (configuração única)

Além da fonte de sessões, o ES-DB utiliza o **diretório de configuração do
ES-DE** como repositório de recursos locais. O usuário informa esse diretório
**uma única vez** (padrão `~/ES-DE`; pode ser sobrescrito pela variável de
ambiente própria do ES-DE ou ajustado em Configurações) e o ES-DB identifica
automaticamente:

| Recurso | Local no ES-DE | Uso no ES-DB |
| --- | --- | --- |
| **Scripts de evento** | `scripts/game-start/`, `scripts/game-end/` | Instalar/detectar os hooks que gravam as sessões ([ESDE.md](ESDE.md) §5). |
| **Imagens baixadas** | `downloaded_media/<system>/<tipo>/` | Capas, screenshots e demais artes da Biblioteca e da página do jogo (§7, [DESIGN.md](DESIGN.md), [SCREENSHOTS.md](SCREENSHOTS.md)). |
| **Metadados** | `gamelists/<system>/gamelist.xml` | Descrição, gênero, desenvolvedora, publisher, nota e data de lançamento (§7, RF-05, [FILTROS.md](FILTROS.md)). |
| **Banco de sessões** | sugerido automaticamente (§4.1) | Fonte das sessões importadas. |
| **Configuração** | `settings/es_settings.xml` | Localizar diretório de mídia/ROMs quando o usuário usar caminhos personalizados. |

Regras de junção determinística, 100% local e sem rede:

1. `games.system` corresponde ao **nome da pasta de sistema** do ES-DE
   (`ps2`, `snes`, `xbox360`…). É a chave primária de junção.
2. O **basename do arquivo de ROM sem extensão** (de `games.rom`, ou do
   `<path>` do `gamelist.xml`) corresponde ao **nome-base dos arquivos de
   mídia** do ES-DE. Exemplo real: a ROM `Black (USA) (PlayStation 2).chd`
   casa com `downloaded_media/ps2/covers/Black (USA) (PlayStation 2).png` e com
   a entrada `<game>` cujo `<path>` é `./Black (USA) (PlayStation 2).chd`.
3. Quando não houver correspondência única, o jogo usa o placeholder da
   Biblioteca e os metadados ricos ficam vazios; nunca se associa mídia/metadado
   de jogo diferente por aproximação.

Tipos de mídia disponíveis por sistema (`downloaded_media/<system>/`):
`covers`, `screenshots`, `marquees`, `miximages`, `3dboxes`, `backcovers`,
`fanart`, `physicalmedia`, `titlescreens`, `videos`, `manuals`. O ES-DB usa
`covers` como capa principal da Biblioteca e `screenshots` na galeria do jogo
([SCREENSHOTS.md](SCREENSHOTS.md)); os demais tipos são evolução futura.

Campos lidos de cada `<game>` do `gamelist.xml`: `name`, `desc`, `genre`,
`developer`, `publisher`, `rating` (0.0–1.0), `releasedate` (`AAAAMMDDT000000`)
e `players`. Todos são **opcionais** e apenas enriquecem a apresentação e os
filtros; nenhuma métrica de tempo depende deles. A leitura do `gamelist.xml` e
da mídia é sempre em **somente leitura**.

### 4.3 Fora do escopo desta versão

- Sincronização em nuvem, rede social ou ranking entre usuários.
- Qualquer conexão de rede, conta de usuário, autenticação, telemetria,
  atualização remota ou integração com serviço externo.
- Controle remoto do ES-DE ou inicialização de ROMs.
- Scraping de capas/metadados pela internet (o ES-DB apenas **lê** o que o
  ES-DE já baixou localmente).
- Alteração de qualquer fonte analisada (banco de sessões, `gamelist.xml`,
  mídia, scripts de terceiros).
- Aplicativo móvel, versão web hospedada ou PWA.

## 5. Requisitos funcionais

### RF-01 — Configuração da fonte (passo único)

1. Na primeira abertura, o usuário informa o **diretório do ES-DE**; o ES-DB
   sugere `~/ES-DE` quando existir.
2. A partir desse diretório, o ES-DB detecta automaticamente scripts, mídia,
   `gamelist.xml` e o banco de sessões (§4.2). O usuário não precisa configurar
   cada recurso separadamente.
3. Quando nenhum banco de sessões é encontrado, o ES-DB oferece **criar um**
   e **instalar os scripts** apontando para ele ([ESDE.md](ESDE.md)).
4. A aplicação valida o acesso somente leitura do banco, a presença das
   tabelas/colunas e índices esperados e mostra a quantidade de jogos e sessões
   encontrada antes de salvar.
5. Todos os caminhos detectados podem ser revistos ou sobrescritos em
   Configurações; cada fonte analisada permanece em modo somente leitura.

### RF-02 — Importação e atualização

1. A primeira importação lê todo o histórico disponível.
2. Atualizações posteriores buscam `sessions.id` maior que o maior ID
   sincronizado e importam essas sessões uma única vez.
3. Como a tabela `games` é atualizada por `INSERT ... ON CONFLICT(name, platform)
   DO UPDATE`, a sincronização deve reler e fazer *upsert* de todos os jogos a
   cada atualização, preservando no banco derivado o `games.id` de origem. Não
   deve pressupor que `system` ou `rom` sejam imutáveis.
4. A cada importação, o ES-DB reconcilia o enriquecimento do ES-DE: resolve
   capa, screenshots e metadados por junção (§4.2) e registra o que não casou.
5. O usuário pode atualizar manualmente e habilitar atualização automática em
   intervalo configurável.
6. A interface apresenta data/hora da última sincronização, quantidade
   importada, ignorada e com erro.
7. A falha de atualização não remove dados já consolidados.
8. Em concorrência com o script, a leitura deve usar conexão SQLite somente
   leitura, `busy_timeout` e uma transação de leitura consistente; se estiver
   bloqueada, deve manter os dados anteriores e permitir nova tentativa.

### RF-03 — Biblioteca de jogos

1. Exibir os jogos conhecidos em grade de cards e em lista compacta
   ([DESIGN.md](DESIGN.md)).
2. Cada item apresenta título, plataforma, capa (do ES-DE quando disponível),
   tempo total, número de sessões e última vez jogado.
3. Permitir busca por título, caminho da ROM e plataforma.
4. Permitir ordenar por mais jogado, jogado recentemente, título e número de
   sessões.
5. Permitir filtrar pelo painel de Filtros ([FILTROS.md](FILTROS.md)):
   plataforma, período, opções e, quando houver metadados do ES-DE, gênero,
   desenvolvedora e publisher.
6. A identidade de um jogo deve ser `source_id + games.id`. A apresentação e
   eventuais agrupamentos usam `(name, platform)`, chave única da fonte. O
   caminho da ROM é somente metadado (o script pode alterá-lo para a mesma
   identidade), mas seu basename serve de chave de junção com o ES-DE (§4.2).

### RF-04 — Painel inicial (Resumo)

O painel exibe, para o período selecionado:

- tempo total jogado;
- quantidade de sessões e média por sessão;
- quantidade de jogos e plataformas jogados;
- jogo e plataforma mais jogados;
- atividade recente;
- evolução do tempo jogado por dia/semana;
- distribuição de tempo por plataforma;
- atalhos para explorar a Biblioteca e abrir a Retrospectiva.

Períodos predefinidos: últimos 7 dias, últimos 30 dias, mês atual, ano atual,
todo o histórico e intervalo personalizado.

### RF-05 — Página do jogo

Cada jogo possui uma página de detalhes com:

- identidade do jogo (título, plataforma, caminho e capa do ES-DE, se houver);
- metadados do ES-DE quando disponíveis: descrição, gênero, desenvolvedora,
  publisher, nota e data de lançamento;
- total de tempo, sessões, primeira e última sessão;
- média, menor e maior duração de sessão;
- gráfico de atividade no tempo;
- histórico cronológico de sessões;
- galeria de **Screenshots** ([SCREENSHOTS.md](SCREENSHOTS.md));
- comparação com a média da biblioteca;
- opção de corrigir localmente título, capa e associação de plataforma, sem
  alterar a fonte.

### RF-06 — Página da plataforma

Para cada sistema/plataforma, exibir tempo total, jogos únicos, sessões,
títulos mais jogados e evolução temporal. O usuário pode navegar da plataforma
aos jogos relacionados.

### RF-06A — Estatísticas do jogador

1. A navegação principal disponibiliza a aba dedicada **Estatísticas**, separada
   da Biblioteca e da Retrospectiva ([INTERFACE.md](INTERFACE.md)).
2. Para o período selecionado, a página exibe tempo total, sessões, média por
   sessão, jogos jogados, plataformas exploradas, dia mais ativo, horário mais
   frequente, maior sequência e última sessão.
3. A página apresenta evolução diária/semanal, distribuição por plataforma e
   ranking dos jogos mais jogados.
4. Indicadores, gráficos e rankings usam as mesmas regras de cálculo do painel
   e respeitam o período selecionado.
5. Ao selecionar um jogo ou plataforma no ranking, o usuário pode navegar ao
   detalhe correspondente sem que as métricas da página sejam recalculadas
   silenciosamente.

### RF-07 — Retrospectiva

1. Gerar uma retrospectiva para qualquer ano com dados disponíveis; o ano atual
   deve refletir os dados até a data presente.
2. A retrospectiva inclui: tempo total, sessões, jogos e plataformas explorados,
   média por sessão, jogo/plataforma do ano, mês e dia mais ativos, maior
   sequência de dias jogando, ranking anual de jogos/plataformas e comparação
   com o ano anterior quando houver base comparável.
3. Exibir uma narrativa curta, calculada a partir dos fatos (por exemplo, “seu
   mês mais ativo foi julho”).
4. Permitir navegar entre anos e compartilhar/exportar um resumo visual como
   imagem ou PDF em etapa posterior. Nesta versão, a tela responsiva em desktop
   e a impressão pelo diálogo nativo do Qt devem funcionar corretamente.
5. A retrospectiva deve incluir calendário anual de atividade, distribuição por
   hora e aviso de cobertura quando o histórico observado não abranger o ano
   completo. A especificação detalhada está em
   [RETROSPECTIVA.md](RETROSPECTIVA.md).

### RF-08 — Linha do tempo (Sessões)

Exibir sessões em ordem cronológica, agrupadas por dia, com filtros por jogo,
plataforma e intervalo. Cada registro informa início, fim, duração e jogo. Esta
visão é apresentada dentro da aba **Atividade**, no modo **Sessões**
([ATIVIDADE.md](ATIVIDADE.md)).

### RF-09 — Qualidade e transparência dos dados

1. Uma área de integridade lista IDs duplicados (erro de cópia), jogo ausente
   no `JOIN`, timestamp inválido, duração negativa, duração divergente da
   diferença entre horários e duração zero.
2. No esquema atual, não há sessões abertas no banco. No protocolo aprimorado,
   `active_sessions` pode exibir uma partida em curso separadamente — nunca como
   sessão contabilizada ([RASTREAMENTO_SESSOES.md](RASTREAMENTO_SESSOES.md)).
3. Todas as métricas exibidas informam o filtro de período aplicado e excluem
   registros inválidos. Registros de duração zero são exibidos e só contam na
   métrica de sessões, conforme a regra da seção 8.

### RF-09A — Rastreamento aprimorado de sessões

O GameSessionTracker pode evoluir seu protocolo de escrita com chave de
correlação, sessão ativa persistida, *heartbeat*, pausas explícitas, recuperação
auditável e *snapshot* de metadados por sessão. O ES-DB deve manter
compatibilidade com o esquema atual e tratar a fonte aprimorada somente em
leitura. Regras completas, migração e critérios de aceite estão em
[RASTREAMENTO_SESSOES.md](RASTREAMENTO_SESSOES.md).

### RF-09B — Visualizador de screenshots

1. O ES-DB exibe, nos detalhes do jogo, as capturas associadas àquele jogo.
2. As fontes de screenshots são, por padrão, a pasta
   `downloaded_media/<system>/screenshots` do ES-DE (auto-descoberta) e,
   opcionalmente, pastas locais adicionais informadas pelo usuário.
3. A associação é determinística, priorizando vínculo manual, pasta por jogo e
   padrão de nome; ambiguidades exigem revisão do usuário.
4. O índice e as miniaturas são locais; a aplicação nunca altera os arquivos de
   screenshot nem usa rede.
5. A especificação completa está em [SCREENSHOTS.md](SCREENSHOTS.md).

### RF-10 — Preferências e privacidade

1. Tema claro, escuro e “seguir sistema” ([INTERFACE.md](INTERFACE.md) §4).
2. Formato de data, primeiro dia da semana e idioma configuráveis.
3. Todo processamento é local. O aplicativo não realiza conexões de rede,
   telemetria, envio de histórico ou integrações externas.
4. O usuário pode apagar o banco local derivado e as personalizações sem tocar
   nas fontes de origem.

### RF-11 a RF-15 — Evoluções desta versão

As evoluções maiores têm requisitos próprios e estão indexadas na **seção 14**
(integração/gravação ES-DE, interface reformulada, painel de filtros, aba de
Atividade e aba de Conquistas).

## 6. Requisitos não funcionais

| ID | Requisito |
| --- | --- |
| RNF-01 | Interface desktop responsiva a janelas de 1.024 px a 2.560 px de largura, sem perda de funcionalidade ao redimensionar. |
| RNF-02 | A primeira importação de até 100 mil sessões deve concluir em até 30 s em hardware de desktop comum; atualizações incrementais em até 3 s, excluído o tempo de acesso ao arquivo. |
| RNF-03 | Listas e gráficos devem continuar responsivos com 100 mil sessões e 10 mil jogos, usando paginação, agregados e/ou virtualização. |
| RNF-04 | Dados e preferências devem permanecer utilizáveis com a rede desativada; a aplicação não deve depender nem tentar acessar recursos de rede. |
| RNF-05 | A aplicação nunca deve escrever nas fontes analisadas (banco de sessões, `gamelist.xml`, mídia do ES-DE ou scripts de terceiros). |
| RNF-06 | Toda operação de importação deve ser idempotente. |
| RNF-07 | Contraste, foco visível, navegação por teclado, texto alternativo e semântica devem atender WCAG 2.1 AA como meta. |
| RNF-08 | Durações, fuso horário e virada de dia devem ser calculados de forma consistente no fuso configurado pelo usuário. |
| RNF-09 | A implementação deve interpretar `start_time` e `end_time` com o offset gravado (`-0300`), sem assumir o fuso atual do computador. |
| RNF-10 | A conexão de origem deve ser SQLite somente leitura; nenhuma tabela, `PRAGMA` persistente, lock de escrita ou arquivo auxiliar pode ser criado na pasta da fonte. |
| RNF-11 | O pacote do aplicativo não deve declarar nem solicitar permissões de rede. Bibliotecas e recursos visuais necessários devem ser distribuídos junto ao aplicativo. |
| RNF-12 | A leitura de mídia e `gamelist.xml` do ES-DE deve ser assíncrona e tolerante a arquivos ausentes, grandes ou malformados, sem bloquear a UI nem derrubar a importação. |
| RNF-13 | As animações da interface devem ser suaves e fluidas, com duração curta (recomendado 120–240 ms) e respeitando a preferência do sistema por redução de movimento, sem comprometer o desempenho. |

## 7. Modelo de dados interno

O armazenamento local separado evita consultas caras às fontes e preserva
correções do usuário.

```text
Source
  id, type, path, schema_version, last_sync_at, last_sync_status

EsdeConfig
  id, esde_home, media_root, gamelists_root, scripts_root, last_scan_at

Game
  id, source_id, external_game_id, title, platform, system, rom_raw,
  cover_path, first_played_at, last_played_at

GameMetadata            # enriquecimento via gamelist.xml do ES-DE (opcional)
  game_id, description, genre, developer, publisher, rating,
  release_date, players, metadata_source_path, matched_at

System
  id, source_id, name, display_name, esde_system_key

Session
  id, source_id, external_id, game_id, started_at, ended_at,
  duration_seconds, wall_clock_seconds, paused_seconds, status,
  close_reason, duration_kind, imported_at

GameOverride
  game_id, title_override, system_override_id, cover_override_path

ImportIssue
  id, source_id, external_id, type, details, created_at, resolved_at

ScreenshotSource
  id, name, root_path, recursive, association_mode, origin, last_scan_at
  # origin: esde_auto | user_folder

ScreenshotAsset
  id, source_id, relative_path, captured_at, width, height, status, thumbnail_key

GameScreenshotLink
  screenshot_asset_id, game_id, association_kind, linked_at

UserSettings
  key, value
```

Restrições importantes:

- `Game(source_id, external_game_id)` é único e corresponde a `games.id` da fonte.
- `Session(source_id, external_id)` é único e corresponde a `sessions.id` da fonte.
- `duration_kind` assume `normal`, `quick_launch` (zero), `invalid_timestamp`,
  `negative_duration` ou `duration_mismatch`.
- `GameMetadata` e `cover_path` são **derivados** do ES-DE: recalculados a cada
  varredura e nunca gravados de volta nas fontes. Ficam vazios quando não há
  correspondência (§4.2).
- `rom_raw` preserva o valor literal da fonte; a forma normalizada é derivada só
  para busca e junção, e não define identidade.
- Durações são armazenadas em segundos; a apresentação escolhe minutos/horas.

## 8. Regras de cálculo

| Métrica | Fórmula |
| --- | --- |
| Tempo jogado | Soma de `duration_seconds` de sessões normais válidas no período, respeitando a interseção da sessão com o período. |
| Sessão | Registro com início e fim parseáveis, duração igual ou compatível com a diferença entre eles e duração maior ou igual a zero. |
| Sessões rápidas | Sessões válidas com `duration_seconds = 0`; entram apenas no contador de sessões, salvo filtro explícito. |
| Jogos jogados | Contagem distinta de `game_id` com ao menos uma sessão normal válida no período. |
| Média de sessão | Tempo jogado ÷ número de sessões normais válidas; mostrar “—” se o divisor for zero. |
| Jogo mais jogado | Jogo com maior tempo acumulado; empate: mais sessões, depois nome em ordem alfabética. |
| Dia mais ativo | Dia local com maior tempo acumulado; empate: dia mais recente. |
| Sequência | Maior conjunto de dias locais consecutivos com pelo menos uma sessão normal válida. |

Sessões que cruzam meia-noite devem ter seu tempo repartido por dia para
gráficos diários e sequência. Para filtros, uma sessão parcialmente contida
contribui apenas com a fração dentro do intervalo. O horário do registro inclui
seu offset; a conversão para o fuso escolhido pelo usuário ocorre antes de
determinar o dia local. A `duration` persistida é a fonte do total, mas
divergência maior que uma tolerância de 1 segundo em relação a
`end_time - start_time` deve ser marcada para integridade.

## 9. Arquitetura proposta

### Aplicação

- **Linguagem e runtime**: Python 3.12 ou superior.
- **Interface nativa**: Qt 6 por meio de **PySide6**. A escolha evita uma
  camada web e permite usar os componentes, diálogos, acessibilidade e impressão
  nativos do Qt. Uma eventual substituição por PyQt6 requer decisão explícita por
  suas implicações de licença.
- **Estrutura da interface**: `QMainWindow` com o shell Playnite/Helium
  ([INTERFACE.md](INTERFACE.md)); páginas Qt independentes para Resumo,
  Estatísticas, Atividade, Conquistas, Retrospectiva, Biblioteca e Configurações.
  Modelos `QAbstractItemModel`/`QSortFilterProxyModel` devem sustentar busca,
  ordenação e listas grandes sem carregar todos os cards de uma vez.
- **Camada de domínio**: módulos Python para importação, normalização,
  agregação e retrospectiva, sem referências a widgets Qt, testáveis com
  `pytest`.
- **Adaptador de fonte**: `GameSessionTrackerSqliteAdapter`, vinculado ao
  esquema confirmado; detecta colunas do protocolo aprimorado por
  `PRAGMA table_info` ([RASTREAMENTO_SESSOES.md](RASTREAMENTO_SESSOES.md)).
- **Integração ES-DE**: `EsdeResolver` localiza, a partir do diretório do ES-DE,
  os caminhos de scripts, mídia e `gamelists`; `GamelistParser` lê os XML em
  streaming; `MediaResolver` resolve capa/screenshots por junção (§4.2). Tudo em
  somente leitura e fora da thread de UI.
- **Banco derivado local**: SQLite acessado pelo módulo padrão `sqlite3`, com
  índices por data, jogo e plataforma. As conexões de origem usam URI `mode=ro`.
- **Mídia local**: serviço de varredura de screenshots e cache de miniaturas,
  isolado da thread de UI e sem qualquer escrita nas pastas de origem.
- **Gráficos**: Qt Charts (`PySide6.QtCharts`) ou widgets Qt equivalentes. Todo
  gráfico deve ter tooltip acessível por teclado e representação textual/tabelada.
- **Empacotamento**: aplicativo desktop autocontido (por exemplo, via
  PyInstaller). Não há servidor embutido, navegador embutido, atualizador
  automático ou dependências baixadas em tempo de execução.

### Fluxo de dados

```text
Diretório do ES-DE (~/ES-DE, somente leitura)
  ├─ scripts/        → instala/detecta game-start, game-end (ESDE.md)
  ├─ downloaded_media/<system>/{covers,screenshots,…}  ─┐
  ├─ gamelists/<system>/gamelist.xml                    │ enriquecimento
  └─ settings/es_settings.xml                           │
                                                        ▼
Banco de sessões (GameSessionTracker, somente leitura)
        ↓
games + sessions (transação de leitura) → validação/normalização → dedupe por sessions.id
        ↓                         ↓                         ↓
Banco derivado local  ←  registro de problemas  ←  junção com mídia/metadados do ES-DE
        ↓
Interface: Resumo, Estatísticas, Atividade, Conquistas, Retrospectiva, Biblioteca
```

### Contrato do adaptador

```python
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

class GameSessionTrackerSource(Protocol):
    def validate(self, path: Path) -> SourceProbeResult: ...
    def list_games(self) -> Iterator[SourceGame]: ...
    def list_sessions_after(self, last_session_id: int) -> Iterator[SourceSession]: ...

class EsdeResource(Protocol):
    def resolve(self, esde_home: Path) -> EsdeLayout: ...
    def media_for(self, system: str, rom_basename: str, kind: str) -> Path | None: ...
    def metadata_for(self, system: str, rom_basename: str) -> GameMetadata | None: ...
```

`SourceSession` é a projeção do `JOIN sessions → games` e inclui `session_id`,
`game_id`, `name`, `platform`, `system`, `rom`, `start_time`, `end_time` e
`duration`. Quando a fonte tiver o protocolo aprimorado, inclui também status,
tempos de relógio/pausa e *snapshots* de metadados. A normalização e a junção
com o ES-DE permanecem fora do adaptador de sessões.

## 10. Experiência e linguagem visual

A direção visual deve ser contemporânea e acolhedora, com foco no conteúdo:
fundo neutro, cards discretos, tipografia legível e capas como elementos de
destaque. O tom é de “diário de jogo”, não de painel corporativo. As interações
usam **animações suaves e fluidas** (RNF-13).

- O **shell** da aplicação (barra superior, navegação em pílulas, painel de
  conteúdo, temas e acento vermelho) está em [INTERFACE.md](INTERFACE.md).
- O layout da **Biblioteca** (grade, cards, lista e estados) está em
  [DESIGN.md](DESIGN.md).
- O **painel de filtros** está em [FILTROS.md](FILTROS.md).

Navegação principal (pílulas): **Resumo · Estatísticas · Atividade · Conquistas
· Retrospectiva**. A **Biblioteca** é alcançada por “Explorar biblioteca”, pela
busca ou pelos Filtros; **Configurações** pela engrenagem. “Atividade” reúne o
feed pessoal e a lista de sessões (antiga Linha do tempo).

Estados obrigatórios:

- onboarding sem diretório do ES-DE / sem fonte configurada;
- importação em andamento, com progresso e possibilidade de continuar usando a
  última versão dos dados;
- biblioteca vazia;
- fonte indisponível, com caminho e ação para tentar novamente;
- dados parciais/inconsistentes, com link para Integridade;
- gráficos sem atividade no período, com sugestão para alterar o filtro.

## 11. Critérios de aceite da V1

1. Dado um diretório do ES-DE válido, o usuário o configura em um único passo e o
   ES-DB detecta scripts, mídia, `gamelist.xml` e banco de sessões sem alterar
   nenhuma fonte.
2. Após a importação, o painel mostra totais corretos para todo o histórico e
   para os períodos predefinidos.
3. Uma nova sessão inserida na fonte aparece após atualização, sem duplicar
   sessões existentes.
4. Um jogo com ROM correspondente no ES-DE exibe capa e metadados (gênero,
   desenvolvedora etc.); sem correspondência, usa placeholder sem erro.
5. Filtrar por plataforma, período, gênero/desenvolvedora (quando houver
   metadados) e intervalo altera de forma coerente biblioteca, painel e
   atividade.
6. A retrospectiva anual apresenta todas as métricas do RF-07 e lida com anos
   sem dados.
7. Sessões zero são visíveis como inícios rápidos, contam em sessões e não
   inflam tempo, sequência ou jogos jogados; sessões inválidas não inflam totais
   e ficam visíveis em Integridade.
8. A sincronização usa `sessions.id` como cursor, atualiza metadados mutáveis de
   `games` e não duplica sessões.
9. O parser aceita timestamps como `2026-09-24T13:09:58-0300` e calcula o dia no
   fuso selecionado.
10. Com o banco de sessões sendo atualizado pelo script, uma leitura bloqueada
    falha sem alterar os dados consolidados e pode ser repetida pelo usuário.
11. A aplicação funciona integralmente com a rede desativada, não efetua
    tentativas de conexão e é utilizável por teclado.
12. A interface se adapta sem perda de funções a janelas desktop de 1.024 px,
    1.440 px e 2.560 px de largura, com animações fluidas.

## 12. Plano de entrega

### Marco 1 — Fundação de dados e ES-DE

Configuração em passo único do diretório do ES-DE, adaptador para
`games`/`sessions`, `EsdeResolver`/`GamelistParser`/`MediaResolver`,
armazenamento derivado, importação incremental por `sessions.id`, integridade e
testes unitários dos timestamps `%z`, sessões zero e junção de mídia/metadados.
Planejar a evolução compatível do protocolo descrita em
[RASTREAMENTO_SESSOES.md](RASTREAMENTO_SESSOES.md).

### Marco 2 — Exploração

Shell Playnite/Helium ([INTERFACE.md](INTERFACE.md)), painel de filtros
([FILTROS.md](FILTROS.md)), biblioteca com capas do ES-DE, busca, página do jogo
com metadados, página da plataforma e aba Atividade. Galeria de screenshots nos
detalhes do jogo ([SCREENSHOTS.md](SCREENSHOTS.md)).

### Marco 3 — Retrospectiva, Conquistas e acabamento

Retrospectiva anual ([RETROSPECTIVA.md](RETROSPECTIVA.md)), aba Conquistas
([CONQUISTAS.md](CONQUISTAS.md)), narrativa baseada em métricas, temas,
acessibilidade, responsividade, estados vazios/erro, animações e impressão.

### Marco 4 — Evoluções opcionais

Capas e artes adicionais do ES-DE (marquees, fanart), exportação dedicada de
retrospectiva, múltiplas fontes e importação local de CSV/JSON.

## 13. Riscos e decisões pendentes

- O esquema e o fluxo do script foram inspecionados em 5 de outubro de 2026. A
  V1 deve validar o esquema a cada configuração e explicar incompatibilidades
  caso o GameSessionTracker evolua.
- No esquema atual, encerramentos inesperados não geram linha em `sessions` e
  duas execuções podem disputar o runtime. O protocolo aprimorado resolve isso
  por sessão ativa persistida, chave de correlação e lock; até sua implantação, a
  aplicação apenas sinaliza a limitação
  ([RASTREAMENTO_SESSOES.md](RASTREAMENTO_SESSOES.md)).
- `games.rom` e `games.system` são regravados a cada início do mesmo
  `(name, platform)`. Histórico de migração de ROM/máquina não pode ser deduzido
  do banco atual.
- A junção com o ES-DE depende de `games.system` casar com a pasta de sistema e
  de o basename da ROM casar com o nome da mídia. ROMs renomeadas após o scrape,
  ou sistemas com nomenclatura divergente, podem não casar; nesses casos o
  usuário pode corrigir localmente (`GameOverride`).
- O armazenamento interno do ES-DB fica em `~/ES-DE-STATS` (banco derivado em
  `derived/`, cache em `cache/`, bancos de sessão em `DATABASE/`), sobreponível
  por `ES_DE_STATS_HOME` ([ESDE.md](ESDE.md) §2).
- A plataforma é aplicativo desktop exclusivamente local. Como o rastreador atual
  usa Bash e está em Linux, Linux é a plataforma inicial recomendada; suporte a
  outros sistemas operacionais deve ser decidido antes do empacotamento.

## 14. Evoluções implementadas nesta versão

Cada evolução tem especificação própria; esta seção é o índice e o resumo dos
requisitos adicionais.

| # | Evolução | Especificação |
| --- | --- | --- |
| RF-11 | **Integração e gravação ES-DE**: configuração em passo único do diretório do ES-DE, descoberta automática de scripts/mídia/metadados, criação e gestão de múltiplos bancos e instalação dos scripts `game-start`/`game-end`; pasta do programa `~/ES-DE-STATS`. | [ESDE.md](ESDE.md) |
| RF-12 | **Interface reformulada** (Playnite/Helium): barra superior, navegação em pílulas, painel de conteúdo, temas e acento vermelho. | [INTERFACE.md](INTERFACE.md) |
| RF-13 | **Painel de filtros** estilo Playnite (plataforma, período, ordenação+direção, opções, metadados do ES-DE e predefinições). | [FILTROS.md](FILTROS.md) |
| RF-14 | **Aba Atividade**: feed pessoal (estilo PlayerActivities) + lista de sessões. | [ATIVIDADE.md](ATIVIDADE.md) |
| RF-15 | **Aba Conquistas**: troféus de RPCS3, Xenia e shadPS4 (estilo PlayniteAchievements). | [CONQUISTAS.md](CONQUISTAS.md) |
| — | **Retrospectiva** reapresentada no estilo “Replay”. | [RETROSPECTIVA.md](RETROSPECTIVA.md) §6 |

### Ajustes de premissas

- A configuração passou a um **único passo**: o diretório do ES-DE, de onde o
  ES-DB descobre scripts, mídia, metadados e banco de sessões (§4.2, RF-01).
- Capas, screenshots e metadados ricos (gênero, desenvolvedora, publisher, nota,
  data) passam a vir do ES-DE quando disponíveis, habilitando filtros antes
  fora de escopo ([FILTROS.md](FILTROS.md)).
- O armazenamento interno migrou para `~/ES-DE-STATS` (banco derivado em
  `derived/`, cache em `cache/`, bancos de sessão em `DATABASE/`).
- A leitura de qualquer fonte analisada permanece **somente leitura** (RNF-05); a
  criação de bancos e a instalação de scripts são escritas locais e opcionais, em
  arquivos que pertencem ao ES-DB ou na pasta de scripts do ES-DE.
- A navegação principal passou a Resumo/Estatísticas/Atividade/Conquistas/
  Retrospectiva, com Biblioteca e Configurações fora das pílulas (§10).
