# ES-DB — Aba Conquistas (RPCS3 · Xenia · shadPS4)

> **Atualização 1:** pontuação/níveis (Sony) e Gamerscore (Xbox), anéis de
> resumo e conquistas no feed de Atividade — ver [ATUALIZACAO1.md](ATUALIZACAO1.md).
> **Atualização 2:** anéis no rodapé e pontuação compacta no canto superior
> direito — ver [ATUALIZACAO2.md](ATUALIZACAO2.md).

> Inspirado no plugin **PlayniteAchievements**, restrito a três emuladores:
> **RPCS3**, **Xenia** e **shadPS4**. Local e somente leitura dos dados do
> emulador; sem rede.

## 1. Objetivo

Exibir troféus/conquistas dos jogos de console emulados, lendo os arquivos do
próprio emulador nas pastas indicadas pelo usuário.

## 2. Configuração das pastas (RF-CQ-01)

Em **Configurações → Conquistas (emuladores)**, o usuário aponta a pasta de cada
emulador:

| Emulador | Pasta (exemplo) | Arquivos lidos |
| --- | --- | --- |
| RPCS3 | `…/dev_hdd0/home/00000001/trophy` | `TROPCONF.SFM` (definições), `TROPUSR.DAT` (progresso) |
| Xenia | `…/Xenia/content` | `*.gpd` (formato XDBF) |
| shadPS4 | `…/shadPS4/user/trophy` | `*.SFM` (definições PS4) |

Qualquer pasta pode ficar vazia; o emulador correspondente é simplesmente ignorado.

## 3. Leitura (RF-CQ-02)

### Definições (confiável)

Nome, descrição, grau (bronze/prata/ouro/platina ou gamerscore) e flag de "oculto"
vêm de XML (`TROPCONF.SFM`/`TROP.SFM`) ou do GPD (Xenia), lidos de forma confiável.

### Progresso de desbloqueio (melhor-esforço)

O estado de desbloqueio vive em binários específicos de cada emulador:

- **RPCS3** — `TROPUSR.DAT`: parsing binário defensivo; quando o formato não puder
  ser interpretado com segurança, os troféus aparecem como bloqueados e o jogo é
  marcado com progresso indisponível.
- **Xenia** — flags e data (FILETIME) extraídas do GPD/XDBF.
- **shadPS4** — por ora apenas definições (sem desbloqueio).

> **Estado:** o parser do **RPCS3** (`TROPUSR.DAT`, incl. data de desbloqueio via
> `CellRtcTick`) foi validado contra arquivos reais. O do **Xenia** (`.gpd`/XDBF)
> segue o formato documentado e é validado por teste sintético. Em todos os casos,
> os parsers degradam com elegância (nunca travam) e nunca marcam desbloqueio
> incerto como certo; se a leitura binária falhar, o jogo exibe apenas as
> definições com "progresso indisponível".

## 4. Modelo

```text
Achievement { key, name, description, grade, hidden, unlocked, unlocked_at, icon_path }
GameAchievements { emulator, title, comm_id, source_path, achievements[], progress_available }
```

## 5. Apresentação

- Lista de jogos (emulador + título + progresso N/total) e, ao selecionar, a lista
  de conquistas: ícone, nome, descrição, grau, estado (✓ desbloqueado com data /
  bloqueado) e barra de progresso.
- Troféus **ocultos** e ainda bloqueados escondem nome/detalhe ("Troféu oculto").
- Quando o progresso é indisponível, um aviso explica que apenas as definições são
  exibidas.

## 6. Garantias

- O ES-DB **nunca** modifica arquivos do emulador.
- Nenhum acesso à rede.
- Falha ao ler um arquivo isola-se àquele item, sem derrubar a varredura.

## 7. Critérios de aceite

1. Apontar a pasta de um emulador lista seus jogos e troféus.
2. As definições (nome, descrição, grau, ocultos) são exibidas corretamente.
3. Quando o progresso é legível, troféus desbloqueados mostram data; os demais,
   bloqueados.
4. Quando o progresso não é legível, o jogo indica "progresso indisponível" sem
   erro.
5. Apenas RPCS3, Xenia e shadPS4 são suportados.
6. Nenhum arquivo de emulador é alterado e não há tráfego de rede.
