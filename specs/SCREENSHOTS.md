# ES-DB — Especificação do Visualizador de Screenshots

## 1. Objetivo e referência

O Visualizador de Screenshots permite que o usuário selecione diretórios locais de capturas e veja, em cada página de jogo, somente as imagens associadas àquele jogo. É um recurso de leitura: jamais move, renomeia, converte ou exclui arquivos de screenshot.

A referência de experiência é o [ScreenshotsVisualizer para Playnite](https://github.com/Lacro59/playnite-screenshotsvisualizer-plugin), que organiza capturas por jogo e aceita múltiplas pastas. A V1 do ES-DB restringe-se a imagens locais: vídeo, nuvem, conversão por ferramenta externa e operações sobre arquivos estão fora do escopo.

## 2. Requisitos funcionais

### RF-SC-01 — Fontes locais

1. O ES-DB registra automaticamente, como fonte de origem `esde_auto`, a pasta
   `downloaded_media/<system>/screenshots` do ES-DE, quando o diretório do ES-DE
   está configurado ([ESDE.md](ESDE.md) §6). Em Configurações, o usuário pode
   adicionar fontes próprias (origem `user_folder`) pelo seletor nativo do Qt.
   Nenhuma outra pasta é descoberta automaticamente.
2. Cada fonte possui nome, caminho absoluto, **origem** (`esde_auto` ou
   `user_folder`), estado, data da última varredura, opção de incluir subpastas e
   regra de associação. A fonte `esde_auto` já associa por sistema + basename da
   ROM (§RF-SC-02), aproveitando a convenção de nomes do ES-DE.
3. A varredura aceita PNG, JPEG/JPG, WEBP e BMP quando suportados pelo Qt da plataforma. Outros formatos podem ser adicionados depois.
4. Links simbólicos não são seguidos por padrão. Se habilitados no futuro, ciclos e saída da raiz escolhida devem ser bloqueados.
5. A fonte é lida em segundo plano, não exige rede e não sofre nenhuma escrita pelo aplicativo.

### RF-SC-02 — Associação ao jogo

Cada imagem segue esta prioridade determinística:

1. **Associação manual** do arquivo ou pasta a `Game.external_game_id`.
2. **Pasta por jogo**: nome da pasta relativa corresponde ao título normalizado ou alias local do jogo. Este é o modo recomendado.
3. **Padrão de nome** configurado pelo usuário, por exemplo `{game}*` ou `{system}_{game}_*`; ele é aplicado somente ao nome de arquivo.

Normalização: Unicode normalizado, diacríticos removidos, `casefold`, pontuação/separadores substituídos por espaço e espaços colapsados. Números de versão, edição e região não são removidos sem alias explícito. Não haverá associação aproximada (*fuzzy matching*) na V1: uma captura do jogo errado é pior que uma captura pendente.

Sem correspondência única, o arquivo entra na fila **Não associados**. O usuário pode associá-lo, ignorá-lo ou criar alias para o jogo. Se existir mais de uma correspondência, o arquivo é ambíguo e nunca é associado automaticamente.

### RF-SC-03 — Galeria por jogo

1. A página de detalhes do jogo contém a seção **Screenshots**, com contador de imagens associadas.
2. Miniaturas em grade são ordenadas por data de captura decrescente; o usuário pode escolher crescente ou por nome.
3. Clique abre visualizador local com imagem ajustada; setas, `Page Up`/`Page Down`, Home e End navegam; `+`, `-`, `0` e roda do mouse controlam zoom.
4. O visualizador mostra nome, caminho relativo à fonte, dimensões, tamanho e data. A data preferida é `EXIF DateTimeOriginal`; na ausência, usa modificação do arquivo e informa sua origem.
5. Imagens ausentes, corrompidas ou sem permissão mostram erro e podem ser removidas **somente do índice local**.
6. Jogo sem capturas mostra estado vazio com “Configurar pasta de screenshots”.

### RF-SC-04 — Varredura e índice

1. **Atualizar screenshots** inicia a varredura; a primeira varredura é oferecida ao salvar uma fonte.
2. A operação exibe encontrados, indexados, associados, não associados, ignorados e erros; é cancelável.
3. A identidade de arquivo é `source_id + caminho relativo normalizado`. Mudança de tamanho ou data de modificação invalida metadados e miniatura.
4. Arquivo removido fica `missing` no índice e pode reaparecer; a limpeza do índice local é ação separada.
5. A varredura incremental é padrão; **Reindexar fonte** realiza reconciliação completa.

## 3. Dados locais

```text
ScreenshotSource
  id, name, root_path, recursive, association_mode, origin,
  filename_pattern, last_scan_at, last_scan_status
  # origin: esde_auto | user_folder

ScreenshotAsset
  id, source_id, relative_path, normalized_relative_path,
  file_size, modified_at, captured_at, captured_at_source,
  width, height, status, thumbnail_key, indexed_at

GameScreenshotLink
  screenshot_asset_id, game_id, association_kind, linked_at
  # manual | folder | filename_pattern

GameScreenshotAlias
  id, game_id, alias_normalized, created_at

ScreenshotScanIssue
  id, source_id, relative_path, type, details, created_at, resolved_at
```

`GameScreenshotLink(screenshot_asset_id)` é único na V1: uma captura pertence a no máximo um jogo. Para transferi-la, o usuário remove a associação atual. Miniaturas são cache derivado; a chave inclui caminho normalizado, tamanho, `modified_at` e versão do gerador protegidos por hash. Limpar cache não altera arquivos nem associações.

## 4. Desempenho, segurança e privacidade

- Varredura, EXIF, geração de miniatura e decodificação usam `QThreadPool`/`QRunnable` ou equivalente, fora da thread de UI.
- `QImageReader` deve fazer leitura escalonada; miniaturas têm 320 px no maior lado. A imagem completa só é aberta no visualizador.
- Arquivos acima de 50 MB ou dimensões além do limite seguro configurado são sinalizados, não decodificados automaticamente.
- Uma falha de miniatura fica registrada até o arquivo mudar ou o usuário pedir nova tentativa.
- Nenhum caminho, imagem, miniatura ou EXIF deixa o computador. A aplicação não cria, move, renomeia, edita ou remove conteúdo nas fontes selecionadas.

## 5. Interface Qt

Em Configurações, `QFileDialog.getExistingDirectory` adiciona fontes. Uma tabela lista origem e estado, com ações: adicionar, editar, varrer, reindexar, cancelar e remover índice/cache local após confirmação.

Galeria usa grade virtualizada com delegate de miniatura; os cards mostram imagem, data e indicador de erro. O visualizador usa `QGraphicsView`/`QGraphicsScene` ou equivalente para pan/zoom e respeita rotação EXIF. Todo item possui foco visível e texto acessível com nome, data e dimensões; o aplicativo não tenta descrever conteúdo da imagem automaticamente.

A Biblioteca pode exibir contador discreto de screenshots no card do jogo, mas a galeria completa fica apenas nos detalhes do jogo.

## 6. Estados e critérios de aceite

| Estado | Comportamento |
| --- | --- |
| Sem fonte | Explica o recurso e oferece seletor de pasta. |
| Varredura | Mostra progresso e Cancelar; mantém resultados anteriores. |
| Sem captura | Estado vazio local, sem buscar na internet. |
| Não associados | Lista revisável por arquivo/pasta, associação manual e alias. |
| Fonte indisponível | Preserva índice, informa o caminho e permite nova tentativa. |
| Arquivo ausente/corrompido | Exibe erro no item sem bloquear a galeria. |

1. Uma pasta `screenshots/<nome-do-jogo>/` associa corretamente suas imagens no modo Pasta por jogo sem rede.
2. Nome ambíguo não é associado automaticamente.
3. Associação manual persiste após nova varredura, salvo remoção do arquivo.
4. Imagens novas, alteradas e removidas são refletidas por varredura incremental.
5. Galeria e visualizador permanecem responsivos com 5 mil imagens indexadas.
6. Nenhum arquivo sob as fontes selecionadas é alterado pelo aplicativo.
