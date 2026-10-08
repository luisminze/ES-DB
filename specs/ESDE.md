# ES-DB — Integração com o ES-DE e Gravação de Sessões

> Esta especificação cobre a **integração central com o ES-DE** e uma **evolução
> de escopo**: além de *ler* um banco de sessões, o ES-DB descobre
> automaticamente os recursos do ES-DE a partir de um único diretório, pode
> **criar** o próprio banco, **gerenciar vários bancos** e **gerar/instalar os
> scripts de evento do ES-DE** que gravam as sessões. Tudo é local e opcional; a
> leitura analítica permanece em somente leitura ([MAIN.md](MAIN.md) §4, RNF-05).

## 1. Objetivo

Simplificar toda a configuração do ES-DB a **um único passo**: o usuário informa
o **diretório de configuração do ES-DE** e o aplicativo identifica e utiliza
automaticamente scripts, imagens baixadas, metadados, banco de sessões e demais
arquivos necessários — sem configurações manuais adicionais e mantendo
compatibilidade com a estrutura padrão do ES-DE.

Quando ainda não houver registro de sessões, o ES-DB também cria um banco no
formato GameSessionTracker e instala no ES-DE os hooks `game-start`/`game-end`
que o preenchem. O usuário pode manter quantos bancos quiser (por perfil, por
coleção) e escolher qual é analisado e qual recebe as gravações.

## 2. Duas pastas, dois papéis

O ES-DB lida com duas raízes distintas e nunca as confunde:

### 2.1 Diretório do ES-DE (fonte, somente leitura)

Por padrão `~/ES-DE` (espelhado pelo diretório de dados do próprio ES-DE). É
**analisado**, nunca modificado — exceto a pasta `scripts/`, onde o ES-DB pode,
com confirmação, instalar/remover apenas os seus próprios hooks. Estrutura
reconhecida:

```text
~/ES-DE/
  scripts/
    game-start/            # hooks disparados ao abrir um jogo
    game-end/              # hooks disparados ao fechar um jogo
  downloaded_media/
    <system>/              # ex.: ps2, snes, xbox360
      covers/  screenshots/  marquees/  miximages/  3dboxes/
      backcovers/  fanart/  physicalmedia/  titlescreens/  videos/  manuals/
  gamelists/
    <system>/gamelist.xml  # metadados por jogo
  settings/
    es_settings.xml        # configuração do ES-DE (p. ex. caminhos de ROM/mídia)
  collections/  themes/  custom_systems/  logs/  …   # ignorados pelo ES-DB
```

### 2.2 Pasta do ES-DB (dados próprios)

Todos os dados que o ES-DB cria vivem sob uma única pasta, por padrão
`~/ES-DB`, sobreponível pela variável de ambiente `ES_DB_HOME`:

```text
~/ES-DB/
  database/            # bancos de sessão criados/geridos pelo usuário
    <nome>.db          # ex.: Strokyze.db
    .gametracker       # marcador de runtime/propriedade do ES-DB
  derived/derived.db   # banco derivado interno (cache analítico)
  cache/thumbnails/    # miniaturas de screenshots
```

- Um banco novo é criado como `~/ES-DB/database/<nome>.db`, onde `<nome>`
  é o nome escolhido, sem separadores de caminho e sem prefixo imposto.
- O caminho pode ser alterado no diálogo de criação.

## 3. Descoberta automática (RF-GE-00)

A partir do diretório do ES-DE informado em passo único, o `EsdeResolver`
([MAIN.md](MAIN.md) §9) resolve e valida:

| Recurso | Caminho resolvido | Uso |
| --- | --- | --- |
| Scripts | `<ES-DE>/scripts/{game-start,game-end}/` | Detectar/instalar hooks (§5). |
| Mídia | `<ES-DE>/downloaded_media/<system>/<tipo>/` | Capas e screenshots (§6). |
| Metadados | `<ES-DE>/gamelists/<system>/gamelist.xml` | Enriquecimento (§6). |
| Configuração | `<ES-DE>/settings/es_settings.xml` | Caminhos personalizados de ROM/mídia. |
| Banco de sessões | sugerido entre `~/ES-DB/database/*.db` e `~/GameSessionTracker/database/games.db` | Fonte das sessões. |

Regras:

1. Cada recurso ausente é tratado como opcional: a interface indica o que foi
   encontrado e o que falta, sem bloquear o uso do restante.
2. Se `es_settings.xml` apontar diretórios de mídia/ROM personalizados, eles têm
   precedência sobre os padrões.
3. Nenhuma varredura de mídia/metadados escreve em `~/ES-DE`; resultados vão para
   o banco derivado e o cache em `~/ES-DB`.

## 4. Junção de jogos com recursos do ES-DE (RF-GE-01)

A associação entre um jogo rastreado e seus recursos no ES-DE é determinística e
local ([MAIN.md](MAIN.md) §4.2):

1. `games.system` casa com o **nome da pasta de sistema** (`ps2`, `snes`…).
2. O **basename da ROM sem extensão** casa com o nome-base dos arquivos de mídia
   e com o `<path>` do `<game>` no `gamelist.xml`.
   - Ex.: ROM `Black (USA) (PlayStation 2).chd` →
     capa `downloaded_media/ps2/covers/Black (USA) (PlayStation 2).png` e
     metadados do `<game>` cujo `<path>` é `./Black (USA) (PlayStation 2).chd`.
3. Sem correspondência única, o jogo usa placeholder e metadados vazios; nunca se
   associa recurso de outro jogo por aproximação.

Campos lidos do `gamelist.xml`: `name`, `desc`, `genre`, `developer`,
`publisher`, `rating` (0.0–1.0), `releasedate` (`AAAAMMDDT000000`) e `players`.

## 5. Criação e gestão de bancos (RF-GE-02)

1. O ES-DB cria um SQLite vazio com o **mesmo esquema** do GameSessionTracker
   (tabelas `games` e `sessions` e índices; ver [MAIN.md](MAIN.md) §4).
2. A criação **nunca sobrescreve** um arquivo existente sem confirmação explícita.
3. Um banco recém-criado é válido para leitura imediata (0 jogos, 0 sessões) e
   passa a ser preenchido quando o ES-DE dispara os scripts.
4. O ES-DB mantém um **catálogo** de bancos (tabela `managed_source` no banco
   derivado: `id, name, path, created_at`). Cada banco pode ser:
   - **ativo**: é o que a interface analisa (importado para o banco derivado);
   - **de gravação**: é onde os scripts do ES-DE escrevem.
   O ativo e o de gravação podem ser o mesmo ou diferentes.
5. Operações: **criar** (novo arquivo), **adicionar existente**, **renomear**,
   **remover do catálogo** (sem apagar o arquivo), **definir como ativo** e
   **instalar scripts** apontando para ele.
6. Definir um banco como ativo importa seu conteúdo (RF-02) e atualiza toda a
   interface.

## 6. Mídia e metadados do ES-DE (RF-GE-03)

1. **Capas**: a imagem de `downloaded_media/<system>/covers/<rom-base>.*` é a
   capa principal da Biblioteca e da página do jogo. A varredura é assíncrona,
   com cache de miniaturas em `~/ES-DB/cache/` ([DESIGN.md](DESIGN.md),
   [SCREENSHOTS.md](SCREENSHOTS.md)).
2. **Screenshots**: `downloaded_media/<system>/screenshots/` é adicionada
   automaticamente como fonte de screenshots (origem `esde_auto`), somando-se às
   pastas que o usuário informar ([SCREENSHOTS.md](SCREENSHOTS.md)).
3. **Metadados**: `gamelist.xml` enriquece a página do jogo e habilita filtros
   de gênero, desenvolvedora e publisher ([FILTROS.md](FILTROS.md)).
4. Toda leitura é somente leitura e tolerante a arquivos ausentes, grandes ou
   malformados (RNF-12); uma falha isola-se ao item.

## 7. Scripts de evento do ES-DE (RF-GE-04)

### Local e ativação

- Os scripts são instalados em `<ES-DE>/scripts/<evento>/`, usando os eventos
  `game-start` e `game-end`.
- O usuário deve ativar no ES-DE: **Menu → Other Settings → Enable Custom Event
  Scripts**.

### Contrato de argumentos

O ES-DE passa quatro argumentos para `game-start` e `game-end`:

| Posição | Conteúdo |
| --- | --- |
| `$1` | caminho absoluto da ROM |
| `$2` | nome do arquivo sem extensão |
| `$3` | nome do jogo |
| `$4` | nome do sistema (curto, ex.: `ps2`) |

### Comportamento

1. `game-start` grava início (timestamp `%Y-%m-%dT%H:%M:%S%z`), nome, sistema e
   ROM em um arquivo de runtime ao lado do banco (`.gametracker/current_session`).
2. `game-end` lê o runtime, calcula a duração em segundos, faz *upsert* do jogo
   (`INSERT ... ON CONFLICT(name, platform) DO UPDATE`) e insere a sessão.
3. O nome legível da **plataforma** é derivado do sistema por um mapeamento
   embutido (ex.: `ps2` → `Sony PlayStation 2`, `xbox360` → `Microsoft Xbox 360`,
   `snes` → `Nintendo SNES (Super Nintendo)`); sistemas desconhecidos usam o
   próprio nome curto. O mapeamento deve casar com os nomes já usados nos dados
   existentes do usuário para que os registros se fundam.
4. Aspas simples em nome/ROM/plataforma são escapadas antes de compor o SQL.
5. Duração negativa é normalizada para zero; encerramentos sem runtime não geram
   sessão (coerente com [MAIN.md](MAIN.md) §4).

### Dependências e segurança

- Os scripts dependem de `sqlite3` e `date` (GNU) no sistema; são `bash`.
- Cada script carrega um marcador de origem; a **remoção** só apaga scripts
  gerados pelo ES-DB, preservando outros scripts do usuário.
- Nenhuma operação acessa a rede. A criação de esquema escreve apenas sobre o
  banco que pertence ao ES-DB; a fonte analisada continua aberta em `mode=ro`
  (RNF-05, RNF-10).

## 8. Critérios de aceite

1. Informar o diretório do ES-DE em passo único faz o ES-DB detectar scripts,
   `downloaded_media`, `gamelists` e um banco de sessões, listando o que
   encontrou e o que falta.
2. Um jogo com ROM correspondente mostra capa e metadados do ES-DE; sem
   correspondência, usa placeholder e metadados vazios, sem erro.
3. Criar um banco gera `~/ES-DB/database/<nome>.db` válido e vazio, sem
   sobrescrever arquivos existentes.
4. É possível manter vários bancos, alternar o ativo (reanalisando) e escolher o
   de gravação independentemente.
5. Instalar os scripts cria `game-start`/`game-end` executáveis apontando para o
   banco escolhido; removê-los preserva outros scripts do ES-DE.
6. Com os scripts ativos no ES-DE, abrir e fechar um jogo registra uma sessão com
   início, fim, duração, nome, plataforma legível e sistema corretos, inclusive
   para nomes com apóstrofo.
7. Sistemas sem mapeamento gravam a plataforma com o nome curto do sistema.
8. Toda a operação funciona sem rede e sem escrever em qualquer fonte externa
   além dos próprios scripts do ES-DB na pasta `scripts/` do ES-DE.
