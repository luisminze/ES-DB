# ES-DB — Especificação de Rastreamento de Sessões

## 1. Objetivo e limites

Esta especificação evolui o **GameSessionTracker**, o script que produz `~/GameSessionTracker/database/games.db`. O ES-DB continua somente leitor da fonte: ele não inicia, encerra, edita ou recupera sessões no banco de origem.

O desenho é inspirado no [GameActivity para Playnite](https://github.com/Lacro59/playnite-gameactivity-plugin): registros por sessão, regras para sessões curtas, tratamento de pausa, cópias de segurança e verificação de inconsistências. A implementação será própria, local e sem monitoramento de hardware, rede, serviços Windows ou dependências de Playnite.

## 2. Situação atual e meta

Hoje, `game-end.sh` insere uma linha em `sessions`; interrupções deixam `runtime/current_session`, mas nenhum histórico consultável. A versão aprimorada deve dar a cada execução uma chave de correlação, persistir início e atividade periodicamente, impedir que um término antigo feche uma execução nova, registrar pausas somente por eventos reais e recuperar interrupções sem fingir que a duração é exata.

Sessões cruas nunca são apagadas por regras de qualidade. A aplicação pode classificá-las e criar decisões locais reversíveis, sem editar a fonte.

## 3. Protocolo da sessão

### Estados

```text
                pause                    resume
running ─────────────────→ paused ─────────────────→ running
   │                       │                            │
   ├── end normal ─────────┴──────────────→ completed   │
   ├── falha conhecida ───────────────────→ interrupted │
   └── timeout de heartbeat ──────────────→ recovered   │
```

`completed` é o único estado automaticamente elegível às métricas. `interrupted` e `recovered` ficam em Integridade e só entram nas métricas após revisão explícita. `paused` não é um estado final.

### Chave e concorrência

- `session_key` é um UUID gerado em `game-start.sh` e transportado por todos os scripts do ciclo de vida.
- `game-end.sh`, pausa, retomada e *heartbeat* só alteram a sessão cuja chave corresponda à sessão ativa.
- Escritas usam `flock` em `runtime/tracker.lock` e transação SQLite. Um novo início primeiro reconcilia uma sessão anterior; nunca a sobrescreve.
- Término com chave ausente ou antiga é evento órfão: entra no log, sem fechar nenhuma sessão.

### Eventos

| Evento | Origem | Efeito |
| --- | --- | --- |
| `started` | `game-start.sh` | Cria a sessão ativa e *snapshot* de jogo. |
| `heartbeat` | processo local a cada 60 s | Atualiza `last_heartbeat_at`. |
| `paused` / `resumed` | hooks opcionais | Acumula apenas pausas confirmadas. |
| `ended` | `game-end.sh` | Fecha como `completed`. |
| `interrupted` | falha/sinal conhecido | Fecha com tempo estimado até o último heartbeat. |
| `recovered` | reconciliação local | Fecha sessão expirada, preservando auditoria. |

Não é permitido inferir pausa por falta de eventos. Sem hook de pausa, `paused_seconds = 0`. Se o ambiente não puder manter *heartbeat*, ele grava `heartbeat_supported = 0` e não deve estimar duração de recuperação além do último evento conhecido.

## 4. Evolução compatível do banco

`games` continua sem mudança. `sessions` permanece a tabela de sessões concluídas, recebendo apenas colunas aditivas; o esquema atual segue legível durante a migração.

```sql
ALTER TABLE sessions ADD COLUMN session_key TEXT;
ALTER TABLE sessions ADD COLUMN wall_clock_seconds INTEGER;
ALTER TABLE sessions ADD COLUMN paused_seconds INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'completed';
ALTER TABLE sessions ADD COLUMN close_reason TEXT;
ALTER TABLE sessions ADD COLUMN recovered_at TEXT;
ALTER TABLE sessions ADD COLUMN game_name_snapshot TEXT;
ALTER TABLE sessions ADD COLUMN platform_snapshot TEXT;
ALTER TABLE sessions ADD COLUMN system_snapshot TEXT;
ALTER TABLE sessions ADD COLUMN rom_snapshot TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_session_key
  ON sessions(session_key) WHERE session_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS active_sessions (
  session_key TEXT PRIMARY KEY,
  game_id INTEGER NOT NULL,
  started_at TEXT NOT NULL,
  last_heartbeat_at TEXT NOT NULL,
  paused_at TEXT,
  paused_seconds INTEGER NOT NULL DEFAULT 0,
  heartbeat_supported INTEGER NOT NULL DEFAULT 1,
  game_name_snapshot TEXT NOT NULL,
  platform_snapshot TEXT NOT NULL,
  system_snapshot TEXT,
  rom_snapshot TEXT,
  tracker_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_key TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  event_type TEXT NOT NULL,
  details_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_session_events_key ON session_events(session_key, occurred_at);
```

`duration` continua sendo tempo efetivamente jogado: `max(0, wall_clock_seconds - paused_seconds)`. Os *snapshots* tornam o histórico estável quando `games.system` ou `games.rom` forem atualizados. Sessões legadas ficam `completed`, `paused_seconds = 0`, `session_key = NULL` e jamais são regravadas para inventar dados ausentes.

## 5. Fluxo de escrita

### Início

1. Validar argumentos e adquirir o lock.
2. Reconciliar eventual sessão ativa anterior.
3. Atualizar/inserir `games`, obter `game_id` e gerar `session_key`.
4. Em uma transação, inserir `active_sessions` e evento `started` com o mesmo relógio.
5. Gravar `runtime/current_session` atomicamente (temporário + `mv`), com chave e PID do *heartbeat*.
6. Após *commit*, iniciar o *heartbeat*.

Falha antes do *commit* não cria sessão. Falha depois do *commit* deixa sessão ativa recuperável, nunca descartada silenciosamente.

### Término e recuperação

- `game-end.sh` encerra o *heartbeat*, fecha pausa pendente e calcula os dois tempos. Em uma transação: insere `sessions`, registra `ended`, remove `active_sessions`; só então remove `current_session`.
- `reconcile-sessions.sh` identifica sessão sem *heartbeat* além do limite local (padrão: 10 min). Cria sessão `recovered` com `close_reason = 'heartbeat_timeout'`, limitada ao último *heartbeat*, e adiciona evento de auditoria.
- O usuário decide incluir/excluir recuperadas somente no banco derivado do ES-DB. A fonte não é modificada.

## 6. Classificação no ES-DB

| Classe | Regra | Métricas padrão |
| --- | --- | --- |
| `valid` | `completed`, horários e duração coerentes | Incluída |
| `quick_launch` | duração zero | Só contador de sessões |
| `short` | duração positiva abaixo do limite configurável | Incluída, ocultável |
| `recovered` | `recovered` ou `interrupted` na fonte | Excluída até revisão |
| `overlap` | conflita com sessão confirmada | Excluída e sinalizada |
| `invalid` | data inválida, duração negativa ou divergência | Excluída |

O limite de sessão curta é preferência local (60 s recomendado), não regra destrutiva. Integridade deve mostrar razão, eventos e uma decisão local, versionada e reversível.

## 7. Adaptador, testes e aceite

O adaptador detecta colunas novas por `PRAGMA table_info` em conexão somente leitura, aceita banco legado/aprimorado, usa `sessions.id` como cursor e prefere os *snapshots* quando disponíveis. `active_sessions` aparece apenas como “em andamento”, fora das métricas.

1. Dois inícios concorrentes não criam duas sessões ativas.
2. Um término com chave antiga não encerra a sessão atual.
3. Interrupção preserva início/eventos e pode ser reconciliada sem apagar evidências.
4. Pausas reduzem duração só com pares válidos de eventos.
5. `duration = max(0, wall_clock_seconds - paused_seconds)`.
6. O ES-DB importa fontes legadas e aprimoradas sem escrever nelas.
7. Recuperadas/interrompidas não influenciam totais sem decisão explícita do usuário.
