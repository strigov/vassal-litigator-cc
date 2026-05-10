---
name: codex-invocation
description: >
  Единый контракт вызова Codex CLI для vassal-litigator-cc. Используй этот скилл, когда
  любой другой скилл плагина должен диспатчить задачу в Codex: файловый apply на medium,
  таймлайн на high, визуализацию через image_gen, контрольное ревью на xhigh. Содержит
  точные команды, monitor-polling, stale-lock workaround, контракт путей [PLUGIN_ROOT] /
  [CASE_ROOT] и резолв generated image path через sessionId.
---

# Codex invocation — единый контракт vassal-litigator-cc

Этот скилл описывает, **как Claude-main вызывает Codex** для ролей плагина vassal-litigator-cc. Он не заменяет профильные скиллы (`intake`, `timeline`, `legal-review` и т.д.), а задаёт общий транспорт, флаги, правила резолвинга путей и отчётности.

## Когда активируется

Используй этот скилл, если задача требует одного из четырёх Codex-ролей плагина:

- `file-executor` — файловый apply-пайплайн, `medium`, с `--write`
- `timeline-builder` — сборка хронологии, `high`, с `--write`
- `imagegen-visualizer` — sidecar-визуализация через `image_gen`, `medium`
- `analytical-reviewer` — контрольное ревью аналитики, `xhigh`, **без** `--write`

## Предусловия

### 1. Однократный логин

Если это первый вызов Codex на машине юриста, сначала нужен логин:

```bash
!codex login
```

Если логин уже делался, повторять не нужно.

### 2. Resolve `$DISPATCH` и legacy `$CODEX_COMPANION`

Основной транспорт — `bin/codex-dispatch`. Wrapper сам резолвит vendored runtime из marketplace install или локального dev-tree, выставляет изолированный `CLAUDE_PLUGIN_DATA` и прокидывает аргументы в companion без model-pinning.

В начале сессии Claude-main **один раз** резолвит `$DISPATCH`:

```bash
DISPATCH=""
[ -n "${PLUGIN_ROOT:-}" ] && [ -x "$PLUGIN_ROOT/bin/codex-dispatch" ] && DISPATCH="$PLUGIN_ROOT/bin/codex-dispatch"
[ -z "$DISPATCH" ] && DISPATCH="$(ls -1d ~/.claude/plugins/cache/strigov-cc-plugins/vassal-litigator-cc/*/bin/codex-dispatch 2>/dev/null | sort -rV | head -1)"
[ -z "$DISPATCH" ] && DISPATCH="$(pwd)/bin/codex-dispatch"

if [ ! -x "$DISPATCH" ]; then
  echo "CODEX_DISPATCH_NOT_FOUND: bin/codex-dispatch не найден или не исполняемый. DISPATCH=$DISPATCH" >&2
  exit 1
fi

echo "DISPATCH=$DISPATCH"
```

Для обратной совместимости профильные скиллы (`intake`, `add-evidence`, `add-opponent`, `visualize`) пока продолжают вызывать `node "$CODEX_COMPANION" ...`. Поэтому в той же сессии Claude-main экспортирует legacy-путь к vendored companion:

```bash
CODEX_COMPANION="$(ls -1d ~/.claude/plugins/cache/strigov-cc-plugins/vassal-litigator-cc/*/vendor/codex-companion/scripts/codex-companion.mjs 2>/dev/null | sort -rV | head -1)"
[ -z "$CODEX_COMPANION" ] && CODEX_COMPANION="$(pwd)/vendor/codex-companion/scripts/codex-companion.mjs"

if [ ! -f "$CODEX_COMPANION" ]; then
  echo "CODEX_COMPANION_NOT_FOUND: vendored codex-companion.mjs не найден. CODEX_COMPANION=$CODEX_COMPANION" >&2
  exit 1
fi

export CODEX_COMPANION
export CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA_OVERRIDE:-$HOME/.claude/plugins/data/vassal-litigator-cc-codex}"

node "$CODEX_COMPANION" --help >/dev/null 2>&1 || {
  echo "CODEX_COMPANION_BROKEN: файл есть, но 'node $CODEX_COMPANION --help' падает" >&2
  exit 1
}

echo "CODEX_COMPANION=$CODEX_COMPANION"
echo "CLAUDE_PLUGIN_DATA=$CLAUDE_PLUGIN_DATA"
```

Обязательный инвариант: любой documented-вызов `node "$CODEX_COMPANION" ...` должен идти **после** `export CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA_OVERRIDE:-$HOME/.claude/plugins/data/vassal-litigator-cc-codex}"`. Прямой legacy-вызов обходит `bin/codex-dispatch`; без этого export broker/state попадут в чужой data-dir, а orphan-scan потеряет изоляцию.

Если `$DISPATCH` или `$CODEX_COMPANION` не резолвятся, Claude-main обязан вернуть `NEEDS_CONTEXT` и попросить Сюзерена указать корректный plugin root или запустить из корня установленного `vassal-litigator-cc`.

Orphan-брокеры от аварийно убитых Claude Code сессий чистятся автоматически: broker self-terminates примерно за 6 секунд после смерти родителя через heartbeat в `app-server-broker.mjs`, а `ensureBrokerSession` на старте подбирает оставшиеся orphan state через `scanOrphanBrokers`.

### 3. Feature-flag для визуализатора

Для основного Branch A у роли `imagegen-visualizer` юрист должен один раз включить feature:

```bash
codex features enable image_generation
```

Это включает `features.image_generation = true` в `~/.codex/config.toml`. Если юрист не хочет включать feature глобально, используй Branch B из раздела про визуализатор.

## Роли и точные команды

Во всех командах ниже:

- `[CASE_ROOT]` — абсолютный путь к папке дела
- `<PROMPT>` — уже отрендеренный промпт, где Claude-main **заменил** `[PLUGIN_ROOT]` и `[CASE_ROOT]` на абсолютные пути
- `$DISPATCH` — основной wrapper `bin/codex-dispatch`, резолвленный разделом «Предусловия / Resolve `$DISPATCH` и legacy `$CODEX_COMPANION`»
- `$CODEX_COMPANION` — legacy-путь к vendored `codex-companion.mjs`, экспортированный вместе с изолированным `$CLAUDE_PLUGIN_DATA`

### 1. `file-executor` — medium, apply, `--write`

```bash
node "$CODEX_COMPANION" task \
  --background \
  --write \
  --effort medium \
  "<PROMPT>"
```

Используется для:

- `file-executor-intake-apply`, `file-executor-intake-plan`* (plan-фаза без `--write`)
- `file-executor-add-evidence-apply`, `file-executor-add-evidence-plan`* (plan-фаза без `--write`)
- `file-executor-add-opponent-apply`, `file-executor-add-opponent-plan`* (plan-фаза без `--write`)
- `file-executor-update-index`
- `file-executor-catalog`

\* plan-фаза вызывается **без** `--write`; whitelist writes в `.vassal/plans/` и `.vassal/work/` контролируется самим промптом, не флагом companion.

### 2. `timeline-builder` — high, apply, `--write`

```bash
node "$CODEX_COMPANION" task \
  --background \
  --write \
  --effort high \
  "<PROMPT>"
```

### 3. `analytical-reviewer` — xhigh, read-only

```bash
node "$CODEX_COMPANION" task \
  --background \
  --effort xhigh \
  "<PROMPT>"
```

Для ревьюера `--write` не передаётся.

### 4. `imagegen-visualizer` — два branch-варианта

#### Branch A — основной: companion + глобально включённый feature-flag

```bash
node "$CODEX_COMPANION" task \
  --background \
  --write \
  --effort medium \
  "<PROMPT с вызовом image_gen>"
```

Когда использовать:

- feature `image_generation` уже включён у юриста
- нужен стандартный background-flow с Monitor polling

#### Branch B — fallback: прямой `codex exec`

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox workspace-write \
  --enable image_generation \
  -C "[CASE_ROOT]" \
  -c model_reasoning_effort=medium \
  "<PROMPT с вызовом image_gen>"
```

Когда использовать:

- юрист не включил `image_generation` глобально
- нужен явный `--enable image_generation`
- допустим синхронный вызов без Monitor polling

## Monitor polling — шаблон для background-задач

Для `file-executor`, `timeline-builder`, `analytical-reviewer` и Branch A визуализатора используй один и тот же шаблон. `case`-guard обязателен: без него poll-loop заспамит вывод.

```bash
TASK=task-XXXX
until
  st=$(node "$CODEX_COMPANION" status "$TASK" --json 2>/dev/null \
       | python3 -c "import json,sys; print(json.load(sys.stdin)['job']['status'])")
  case "$st" in
    completed|failed|cancelled) echo "codex task terminal: $st"; true ;;
    *) false ;;
  esac
do
  sleep 25
done
```

После терминального статуса:

```bash
node "$CODEX_COMPANION" result "$TASK"
```

Если нужен `sessionId`, бери JSON:

```bash
node "$CODEX_COMPANION" status "$TASK" --json
```

## `--resume-last`, stale-lock и `--fresh`

Обычный паттерн follow-up:

```bash
node "$CODEX_COMPANION" task \
  --background \
  --write \
  --effort medium \
  --resume-last \
  "<PROMPT>"
```

Если предыдущий запуск был прерван, но текущий broker всё ещё жив, у него может остаться in-memory job state `status=running` даже после исчезновения OS-процесса задачи. В этом случае `--resume-last` может упереться в stale-lock:

```text
Task task-XXXX is still running. Use /codex:status before continuing it.
```

Правка JSON на диске в `~/.claude/plugins/data/vassal-litigator-cc-codex/state/<workspace-slug>/jobs/<task>.json` не помогает: живой broker держит состояние в памяти через `broker.sock`.

Workaround для такого in-memory stale-lock — стартовать новую сессию через `--fresh`:

```bash
node "$CODEX_COMPANION" task \
  --background \
  --write \
  --effort medium \
  --fresh \
  "<PROMPT>"
```

Правило:

- follow-up по той же роли и тому же делу: сначала `--resume-last`
- stale-lock внутри живого broker: `--fresh`

Важно: `--fresh` больше не нужен для orphan-брокеров от прошлых `kill -9` / crash-сессий Claude Code. Эти процессы чистятся runtime-ом автоматически: heartbeat завершает broker примерно за 6 секунд после смерти parent process, а `ensureBrokerSession` на startup добирает оставшиеся orphan state через `scanOrphanBrokers`.

## Контракт путей: `[PLUGIN_ROOT]` и `[CASE_ROOT]`

Это критичный инвариант v0.5.0.

- `[CASE_ROOT]` — абсолютный путь к папке дела; это `cwd` Codex-процесса
- `[PLUGIN_ROOT]` — абсолютный путь к установленному плагину vassal-litigator

Из-за того, что `cwd = [CASE_ROOT]`, относительные пути `scripts/...` и `shared/...` **запрещены**. Все обращения к файлам плагина делаются только так:

- `[PLUGIN_ROOT]/scripts/extract_text.py`
- `[PLUGIN_ROOT]/scripts/generate_table.py`
- `[PLUGIN_ROOT]/scripts/setup.sh`
- `[PLUGIN_ROOT]/shared/conventions.md`
- `[PLUGIN_ROOT]/shared/case-schema.yaml`
- `[PLUGIN_ROOT]/shared/index-schema.yaml`
- `[PLUGIN_ROOT]/shared/mirror-template.md`

### Как Claude-main получает `[CASE_ROOT]`

Базовый вариант:

```bash
CASE_ROOT="$(pwd)"
```

Это должен быть корень конкретного дела, а не корень плагина.

### Как Claude-main получает `[PLUGIN_ROOT]` — 3-tier fallback

`CLAUDE_PLUGIN_ROOT` в main-session обычно **не существует**, поэтому нужен жёстко задокументированный fallback.

#### Tier 1 — env `CLAUDE_PLUGIN_ROOT`, если уже выставлена

```bash
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT" ]; then
  PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
fi
```

#### Tier 2 — парсинг `~/.claude/plugins/installed_plugins.json`

Это основной путь для production-установки.

```bash
if [ -z "${PLUGIN_ROOT:-}" ]; then
  PLUGIN_ROOT="$(python3 - <<'PY'
import json
import os
import sys

path = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
try:
    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
except FileNotFoundError:
    sys.exit(0)

plugins = data.get('plugins', {})
for key, entries in plugins.items():
    if not key.startswith('vassal-litigator@'):
        continue
    for entry in entries:
        install_path = entry.get('installPath')
        if install_path:
            install_path = os.path.expanduser(install_path)
            if os.path.isdir(install_path):
                print(install_path)
                raise SystemExit(0)
PY
)"
fi
```

#### Tier 3 — спросить у юриста и закешировать на текущую сессию

Если ни env, ни `installed_plugins.json` не дали путь, **первый вызов в сессии** должен остановиться с вопросом:

```text
укажи абсолютный путь к плагину vassal-litigator
```

После ответа:

- проверь, что путь абсолютный
- проверь, что внутри есть `skills/`, `shared/`, `scripts/`
- сохрани значение в session-cache и больше в этой сессии не переспрашивай

Пример простого session-cache в shell:

```bash
if [ -n "${VASSAL_PLUGIN_ROOT_CACHE:-}" ] && [ -d "$VASSAL_PLUGIN_ROOT_CACHE" ]; then
  PLUGIN_ROOT="$VASSAL_PLUGIN_ROOT_CACHE"
fi
```

Если кеш пуст:

```bash
VASSAL_PLUGIN_ROOT_CACHE="$PLUGIN_ROOT"
export VASSAL_PLUGIN_ROOT_CACHE
```

### Валидация резолвинга

Перед первым dispatch в сессии проверь:

```bash
test -n "${DISPATCH:-}" && test -x "$DISPATCH"
test -n "${CODEX_COMPANION:-}" && test -f "$CODEX_COMPANION"
test "${CLAUDE_PLUGIN_DATA:-}" = "${CLAUDE_PLUGIN_DATA_OVERRIDE:-$HOME/.claude/plugins/data/vassal-litigator-cc-codex}"
test -f "$PLUGIN_ROOT/scripts/extract_text.py"
test -f "$PLUGIN_ROOT/shared/conventions.md"
test -d "$CASE_ROOT"
```

Если любой тест падает, не запускай Codex. Сначала `NEEDS_CONTEXT`.

## Как Claude-main собирает prompt

Оркестратор делает **prompt-assembly step** до диспатча, а не рассчитывает, что Codex сам что-то резолвит.

Формальный алгоритм:

1. Получи абсолютные `PLUGIN_ROOT` и `CASE_ROOT`.
2. Прочитай целевой шаблон prompt-файла.
3. Если первая строка шаблона содержит `{{include _preamble.md}}`, **expand include** буквальной подстановкой содержимого `prompts/_preamble.md` на место этой директивы.
4. После expand include подставь все переменные шаблона: `[PLUGIN_ROOT]`, `[CASE_ROOT]`, `{{case_root}}`, `{{plugin_root}}` и остальные `{{...}}` placeholders конкретной роли.
5. Проверь, что в собранном prompt не осталось нераскрытых `{{include ...}}` и прочих `{{...}}`.
6. Только после этого передай финальный prompt в Codex как последний аргумент `companion.mjs task` или `codex exec`.

Минимальный пример:

```bash
PROMPT_TEMPLATE="$PLUGIN_ROOT/prompts/timeline-builder.md"
PROMPT="$(cat "$PROMPT_TEMPLATE")"
PREAMBLE="$(cat "$PLUGIN_ROOT/prompts/_preamble.md")"
PROMPT="${PROMPT/\{\{include _preamble.md\}\}/$PREAMBLE}"
PROMPT="${PROMPT//\{\{case_root\}\}/$CASE_ROOT}"
PROMPT="${PROMPT//\{\{plugin_root\}\}/$PLUGIN_ROOT}"
```

Гарантийный check перед dispatch:

```bash
ASSEMBLED_PROMPT_FILE="/tmp/vassal-codex-prompt.txt"
printf '%s\n' "$PROMPT" > "$ASSEMBLED_PROMPT_FILE"
grep -n '{{' "$ASSEMBLED_PROMPT_FILE" && echo "UNRESOLVED_TEMPLATE_TOKENS"
grep -n '\[PLUGIN_ROOT\]\|\[CASE_ROOT\]' "$ASSEMBLED_PROMPT_FILE" && echo "UNRESOLVED_PATH_TOKENS"
```

Ожидание:

- `grep -n '{{' <assembled-prompt>` возвращает `0` совпадений
- `grep -n '\[PLUGIN_ROOT\]\|\[CASE_ROOT\]' <assembled-prompt>` возвращает `0` совпадений

Жёсткое правило:

- Codex не должен видеть «нераскрытые» `{{include _preamble.md}}`, `[PLUGIN_ROOT]`, `[CASE_ROOT]`, `{{case_root}}`, `{{plugin_root}}` и любые другие `{{...}}`
- если путь не удалось получить, правильный исход — `NEEDS_CONTEXT`, а не «попробую с относительным путём»

## Session paths для debug

- Wrapper: `[PLUGIN_ROOT]/bin/codex-dispatch`
- Vendored companion: `[PLUGIN_ROOT]/vendor/codex-companion/scripts/codex-companion.mjs`
- Vendored companion version: `[PLUGIN_ROOT]/vendor/codex-companion/VERSION`
- Isolated data dir: `~/.claude/plugins/data/vassal-litigator-cc-codex`
- State + jobs + broker.sock: `~/.claude/plugins/data/vassal-litigator-cc-codex/state/<workspace-slug>/`
- Job log: `~/.claude/plugins/data/vassal-litigator-cc-codex/state/<workspace-slug>/jobs/task-XXXX.log`

`ECONNREFUSED` на socket до первой реальной `task`-задачи означает, что broker ещё не стартовал.

## Save Codex report

После каждого значимого Codex-dispatch Claude-main сохраняет итоговый отчёт в:

```text
[CASE_ROOT]/.vassal/codex-logs/{ГГГГ-ММ-ДД-ЧЧмм}-{role}.md
```

Это делается для финального результата конкретного dispatch, а не для каждого промежуточного poll.

Минимальный состав лога:

- `task_id`
- `role`
- `effort`
- `prompt_size_bytes`
- `stdout`
- `stderr`
- `taken_ms`
- `final_status`

Если dispatch не стартовал вовсе, лог всё равно желательно сохранить как локальный failure-report с причиной.

## Fallback без Codex

Если Codex недоступен (`network down`, `OpenAI rate limit`, companion broker не отвечает, `status=failed`, timeout, `NEEDS_CONTEXT` до старта), Claude-main не должен молча зависать.

Правило по ролям:

- файловые скиллы (`file-executor-*`) — откат на Claude-native исполнение по логике `v0.4.0`, с явным предупреждением Сюзерену, что Codex-path временно недоступен
- `timeline-builder` — skip по умолчанию; если позже отдельный skill явно задокументирует Claude-native fallback, использовать его, иначе честно вернуть, что таймлайн не собран
- `imagegen-visualizer` — skip: визуализация не создаётся, дело продолжается без sidecar-картинки
- `analytical-reviewer` — skip: показать Сюзерену, что контрольное ревью Codex не проведено

Во всех случаях:

- показать Сюзерену причину сбоя
- сохранить failure-report в `.vassal/codex-logs/`
- не подменять недоступный Codex фиктивным «успехом»

## Визуализатор: как получить путь к PNG на самом деле

Это место **обновлено по Q1 AMENDED**. Нельзя опираться на строку `GENERATED_IMAGE: <abs_path>` в stdout, потому что эмпирически Codex её не печатает стабильно.

### Реальный механизм

1. Определи `sessionId`.
2. Определи `CODEX_HOME` как `${CODEX_HOME:-$HOME/.codex}`.
3. Ищи PNG по паттерну:

```text
$CODEX_HOME/generated_images/<sessionId>/ig_*.png
```

4. Если файлов несколько, бери последний по `mtime`.
5. Claude-main **копирует** найденный PNG в `[CASE_ROOT]/.vassal/visuals/...`; исходник в `$CODEX_HOME/generated_images/...` не трогает.

### Branch A — как получить `sessionId`

Через companion status/result JSON:

```bash
node "$CODEX_COMPANION" status "$TASK" --json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['job']['sessionId'])"
```

### Branch B — как получить `sessionId`

Прямой `codex exec` печатает `session id: <UUID>` в stderr/stdout. Парсинг делается оркестратором по этой строке.

### Поиск PNG

```bash
CODEX_HOME_RESOLVED="${CODEX_HOME:-$HOME/.codex}"
SESSION_ID="<полученный sessionId>"
IMAGE_PATH="$(find "$CODEX_HOME_RESOLVED/generated_images/$SESSION_ID" -maxdepth 1 -type f -name 'ig_*.png' -print \
  | xargs ls -t 2>/dev/null | head -n 1)"
```

Если `IMAGE_PATH` пустой, это `BLOCKED`: не пытайся выдумывать путь, не проси Codex «сохранить ещё раз по нужному месту», не пиши в `.vassal/visuals/` напрямую из imagegen-подзадачи.

## Что нельзя делать

- Не запускать файловые роли без `--background`
- Не опираться на относительные `scripts/...` и `shared/...`
- Не использовать `--write` для `analytical-reviewer`
- Не ожидать, что `$imagegen` сам сохранит файл по пути из промпта
- Не считать `GENERATED_IMAGE:` гарантированным интерфейсом
- Не пропускать `--fresh`, если stale-lock живого broker уже проявился
- Не вызывать `codex-companion.mjs` напрямую из произвольного места; legacy `$CODEX_COMPANION` должен указывать только на vendored runtime этого плагина
- Не вызывать `codex exec` напрямую, кроме явно описанного Branch B у `imagegen-visualizer`
- Не делать documented `node "$CODEX_COMPANION" ...` без предварительного `export CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA_OVERRIDE:-$HOME/.claude/plugins/data/vassal-litigator-cc-codex}"`
- Не хардкодить marketplace cache path в командах; всегда работай через `$DISPATCH` и legacy `$CODEX_COMPANION`, резолвленные один раз в начале сессии

## Результат, который ожидает Claude-main

Этот скилл не задаёт содержание профильного ответа роли, но задаёт транспортный контракт:

- роль выбирается строго из четырёх перечисленных выше
- пути всегда переданы как абсолютные
- cwd всегда равен `[CASE_ROOT]`
- `$DISPATCH` резолвится один раз на сессию как primary transport через `bin/codex-dispatch`
- `$CODEX_COMPANION` сохраняется как legacy export на vendored companion path для профильных скиллов
- `CLAUDE_PLUGIN_DATA` всегда выставлен через `CLAUDE_PLUGIN_DATA_OVERRIDE` pattern до legacy companion-вызовов
- для визуализатора путь к PNG резолвится через `sessionId` + `$CODEX_HOME/generated_images/...`
