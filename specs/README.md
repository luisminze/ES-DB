# ES-DB — Índice de Especificações

Documentação do **ES-DB**, organizada por tema. Comece pela especificação de
produto e técnica; as demais detalham áreas específicas. Todos os documentos se
referenciam entre si pelos nomes de arquivo abaixo.

O ES-DB é um aplicativo desktop exclusivamente local que lê o histórico de
sessões gravado por scripts de evento do **ES-DE** e o apresenta como
biblioteca, estatísticas, atividade, conquistas e retrospectiva.

## Núcleo

| Documento | Conteúdo |
| --- | --- |
| [MAIN.md](MAIN.md) | Produto e técnica: visão geral, fonte GameSessionTracker, integração ES-DE, requisitos, modelo de dados, regras de cálculo, arquitetura e critérios. A **seção 14** indexa as evoluções desta versão. |
| [DESIGN.md](DESIGN.md) | Design da **Biblioteca**: grade, cards, visualização em lista e estados. (O shell está na spec de Interface.) |

## Integração e evoluções desta versão

| Documento | Conteúdo |
| --- | --- |
| [ESDE.md](ESDE.md) | Integração com o ES-DE: configuração em passo único, descoberta automática de scripts/mídia/metadados, criação e gestão de múltiplos bancos e instalação dos scripts de evento. |
| [INTERFACE.md](INTERFACE.md) | Shell da aplicação (Playnite/Helium): barra superior, navegação em pílulas, painel de conteúdo, temas e acento. |
| [FILTROS.md](FILTROS.md) | Painel de filtros estilo Playnite (plataforma, período, ordenação, opções, metadados do ES-DE e predefinições). |
| [ATIVIDADE.md](ATIVIDADE.md) | Aba Atividade: feed pessoal + lista de sessões. |
| [CONQUISTAS.md](CONQUISTAS.md) | Aba Conquistas: RPCS3, Xenia e shadPS4. |

## Áreas específicas

| Documento | Conteúdo |
| --- | --- |
| [RETROSPECTIVA.md](RETROSPECTIVA.md) | Retrospectiva anual: cálculos, cobertura, narrativa e layout estilo "Replay". |
| [SCREENSHOTS.md](SCREENSHOTS.md) | Visualizador de screenshots: fontes (ES-DE + pastas do usuário), associação, índice e desempenho. |
| [RASTREAMENTO_SESSOES.md](RASTREAMENTO_SESSOES.md) | Evolução compatível do protocolo de rastreamento de sessões. |

## Convenções

- **ES-DB** é o aplicativo; **GameSessionTracker** é o esquema/script que grava
  as sessões; **ES-DE** é o front-end de emulação que dispara os eventos.
- Tudo é **local** e **sem rede**. A leitura de qualquer fonte analisada é sempre
  em somente leitura; criação de bancos e instalação de scripts são escritas
  locais e opcionais.
- A configuração é feita em **passo único**, pelo diretório do ES-DE, de onde o
  ES-DB descobre scripts, mídia, metadados e banco de sessões ([ESDE.md](ESDE.md)).
- Sessões de duração zero são **inícios rápidos**: contam em sessões, nunca em
  tempo, jogos jogados, sequência ou destaques.
- Timestamps respeitam o offset gravado; quebras temporais usam o fuso do usuário.
