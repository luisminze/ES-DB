# ES-DB

Aplicativo desktop **exclusivamente local** (sem rede) que transforma o
histórico de sessões gravado por scripts de evento do **ES-DE** em uma interface
moderna: Resumo, Estatísticas, Atividade, Conquistas, Retrospectiva e Biblioteca.

A especificação completa está em [`specs/`](specs/README.md).

## Requisitos

- Python 3.12+
- PySide6 (Qt 6)

## Executar

```bash
python -m venv --system-site-packages .venv   # PySide6 do sistema, ou instale no venv
.venv/bin/pip install -e .
.venv/bin/python -m esdb
```

Na primeira execução, informe em **Configurações** o **diretório do ES-DE**
(padrão `~/ES-DE`). A partir dele o ES-DB descobre automaticamente scripts,
imagens baixadas (`downloaded_media`), metadados (`gamelist.xml`) e o banco de
sessões. Nenhuma fonte analisada é modificada.

## Testes

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest
```

## Funcionalidades

- **Configuração em passo único**: informe o diretório do ES-DE e o app descobre
  scripts, `downloaded_media` (capas/screenshots), `gamelist.xml` (metadados) e o
  banco de sessões.
- **Resumo, Estatísticas, Atividade (feed + sessões), Retrospectiva** (com
  calendário anual e distribuição por hora) e **Biblioteca** com capas do ES-DE.
- **Conquistas** reais: troféus do **RPCS3** (definições `TROPCONF.SFM` + progresso
  binário `TROPUSR.DAT` com datas), **Xenia** (`.gpd`/XDBF) e **shadPS4** (definições).
- **Gravação ES-DE**: criar banco de sessões e instalar/remover os hooks
  `game-start`/`game-end`.
- **Sincronização incremental** por `sessions.id`, **filtros** (inclui gênero/
  desenvolvedora do ES-DE) com **predefinições** salvas, e página de **Integridade**.

## Estrutura

```
src/esdb/
  domain/       # modelos, parsing de tempo, cálculos, retrospectiva (sem Qt, testável)
  data/         # adaptador SQLite somente leitura, classificação, banco derivado, repositório
  esde/         # ES-DE: resolver, gamelist, mídia, ROM, writer (scripts/banco)
  conquistas/   # troféus: rpcs3, xenia, shadPS4, scanner
  ui/           # shell Playnite/Helium e páginas (PySide6)
  config.py     # configuração e pasta do programa (~/ES-DB)
tests/          # pytest: domínio, ES-DE, conquistas, banco derivado, writer
specs/          # especificação do produto
```

Todos os dados do ES-DB vivem em `~/ES-DB` (sobreponível por
`ES_DB_HOME`): `config.json`, banco derivado (`derived/esdb.db`) e cache. As
fontes analisadas (banco de sessões, `gamelist.xml`, mídia, troféus) são sempre
lidas em **somente leitura**.
