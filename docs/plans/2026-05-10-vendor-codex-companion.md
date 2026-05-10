---
slug: vendor-codex-companion
created: 2026-05-10
status: in-progress
phases:
  - id: Ф1
    scope: "Завендорить vendor/codex-companion/ из superpowers-strigov-ver (scripts + schemas + prompts + LICENSE/NOTICE/VERSION/.claude-plugin), без тестов; smoke `node companion.mjs --help`"
    status: done
  - id: Ф2
    scope: "Добавить bin/codex-dispatch wrapper, адаптированный под vassal-litigator-cc (resolve marketplace + dev path; CLAUDE_PLUGIN_DATA isolation; без model-pinning)"
    status: in-progress
  - id: Ф3
    scope: "Переписать skills/codex-invocation/SKILL.md под завендоренный companion: 0-tier resolve через bin/codex-dispatch, удалить старый 3-tier по openai-codex, добавить orphan auto-cleanup ноту, переписать stale-lock секцию"
    status: pending
  - id: Ф4
    scope: "Перенести тесты vendor/codex-companion/tests/ + helpers; добавить tests/smoke/test-codex-dispatch.sh; запустить `node tests/index.js` локально"
    status: pending
  - id: Ф5
    scope: "Обновить README.md / ARCHITECTURE.md / CHANGELOG.md / plugin.json (description), удалить упоминания зависимости от openai-codex, добавить раздел про vendored companion"
    status: pending
---

# Vendor codex-companion в vassal-litigator-cc

## Goal

Перенести в `vassal-litigator-cc` собственную копию `codex-companion` (форк OpenAI codex plugin v1.0.4) с уже применёнными orphan-fix патчами из `superpowers-strigov-ver`, чтобы:

1. Снять hard-зависимость от внешнего плагина `openai-codex@>=1.0.3` (на котором вообще нет orphan-fix и который может обновиться breaking-way).
2. Получить стабильное поведение брокера: после `kill -9` Claude Code orphan-процессы `app-server-broker.mjs` + `codex app-server` сами умирают через ~6 сек (heartbeat) и подбираются на старте (`scanOrphanBrokers`).
3. Иметь единую точку входа `bin/codex-dispatch`, которая резолвит companion сама, изолирует state в выделенный `CLAUDE_PLUGIN_DATA` и не зависит от установленной версии `openai-codex`.

## Acceptance criteria

- `vendor/codex-companion/` существует в репозитории и содержит: `scripts/codex-companion.mjs`, `scripts/app-server-broker.mjs`, `scripts/lib/*.mjs` (включая `broker-lifecycle.mjs` с `scanOrphanBrokers`, `parentPid`, без `detached:true`), `schemas/`, `prompts/`, `.claude-plugin/plugin.json`, `LICENSE`, `NOTICE`, `VERSION`.
- `node vendor/codex-companion/scripts/codex-companion.mjs --help` работает (top-level help; `task --help` нельзя — parser трактует `--help` как positional prompt и стартует foreground Codex task).
- `bin/codex-dispatch` исполняемый, резолвит companion и на marketplace install (`~/.claude/plugins/cache/strigov-cc-plugins/vassal-litigator-cc/*/vendor/...`), и на dev-tree (`$(dirname $0)/../vendor/...`).
- `bin/codex-dispatch --help` работает после `chmod +x` (либо `bin/codex-dispatch status --json` возвращает JSON / ECONNREFUSED — оба считаются валидной smoke-проверкой; `task --help` использовать нельзя по той же причине, что и для companion).
- `skills/codex-invocation/SKILL.md` больше не упоминает `openai-codex` нигде (0 совпадений `grep -n openai-codex`), а описывает резолв через `codex-dispatch`. Старая 3-tier-схема удалена полностью (без сохранения в виде deprecated/legacy блока).
- В `SKILL.md` есть нота про автоматическую очистку orphan-брокеров (heartbeat ~6 сек + `scanOrphanBrokers` на старте), а stale-lock секция переписана: `--fresh` остаётся workaround только для in-memory job state, а не для orphan-брокеров.
- `vendor/codex-companion/tests/` лежат в репо; `node vendor/codex-companion/tests/index.js` либо проходит, либо честно скипает integration с пометкой требований среды.
- README/ARCHITECTURE/CHANGELOG/plugin.json обновлены.
- `git grep -n openai-codex` не находит активных продакшн-ссылок (только historical в CHANGELOG допустимо).

## Non-goals / deferred

- Не меняем upstream-логику `codex-companion.mjs` (никаких vassal-specific патчей в companion-коде).
- Не публикуем codex-companion как отдельный плагин в маркетплейсе.
- Не пинуем модель в `bin/codex-dispatch` (в superpowers это `gpt-5.5`, у юриста vassal-litigator-cc контрактно `medium/high/xhigh effort` и upstream-default модель). Этот пункт отдельно — если понадобится, делаем post-merge.
- Не трогаем профильные скиллы (`intake`, `add-evidence`, `add-opponent`, `update-index`, `legal-review` …) — они продолжают вызывать «companion» через `$CODEX_COMPANION` (значение которого теперь будет указывать на vendored путь). Замена `$CODEX_COMPANION` → `$DISPATCH` во всех профильных скиллах — отдельный future plan.
- Не меняем существующий путь `~/.codex/` (логин юриста) и `CODEX_HOME` для генерации картинок.

## Files

### Новые

- `vendor/codex-companion/` — полное дерево из `superpowers-strigov-ver/vendor/codex-companion/` (без `tests/` в Ф1; с `tests/` в Ф4).
- `bin/codex-dispatch` — bash-wrapper, адаптированный (см. Contracts).
- `tests/smoke/test-codex-dispatch.sh` — простой smoke (`bin/codex-dispatch --help` exit 0, либо `bin/codex-dispatch status --json` возвращает JSON/ECONNREFUSED).

### Изменяемые

- `skills/codex-invocation/SKILL.md` — переписать секцию Resolve `$CODEX_COMPANION` → Resolve `$DISPATCH`/`$CODEX_COMPANION` через bin-wrapper; добавить orphan-cleanup ноту; обновить «stale-lock и `--fresh`» секцию; обновить «Что нельзя делать» (убрать запрет hardcoded `~/.claude/plugins/cache/openai-codex/...` в пользу нового запрета: «не вызывать `codex-companion.mjs` напрямую вне vendored пути»).
- `README.md` — раздел установки: убрать обязательную предустановку `openai-codex`, добавить упоминание vendored companion и `bin/codex-dispatch`.
- `ARCHITECTURE.md` — обновить блок про Codex transport.
- `CHANGELOG.md` — Unreleased: добавить vendored companion с orphan-fix.
- `.claude-plugin/plugin.json` — переписать `description` (убрать «Использует openai-codex companion …», заменить на «Использует vendored codex-companion runtime …»).
- `shared/conventions.md` — выправить строки про `openai-codex`/companion path.
- `tests/README.md` — упомянуть smoke для codex-dispatch.

### Не трогаем

- `skills/intake|add-evidence|add-opponent|visualize|*/SKILL.md` (кроме `codex-invocation`) — уже работают через `$CODEX_COMPANION`. После Ф3 переменная будет ссылаться на vendored путь.
- `commands/init-case.md` — без изменений в этом плане.

## Contracts

### bin/codex-dispatch

Адаптируем wrapper из superpowers под vassal-litigator-cc:

1. **resolve_companion** — порядок:
   - marketplace glob: `~/.claude/plugins/cache/strigov-cc-plugins/vassal-litigator-cc/*/vendor/codex-companion/scripts/codex-companion.mjs` (sort -rV, newest);
   - dev fallback: `$(dirname $0)/../vendor/codex-companion/scripts/codex-companion.mjs`;
   - empty → exit 1 с понятной ошибкой.
2. **CLAUDE_PLUGIN_DATA isolation** — `export CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA_OVERRIDE:-$HOME/.claude/plugins/data/vassal-litigator-cc-codex}"`. Это даст изолированный state/broker.sock от любого другого codex install (в том числе superpowers-strigov-ver, чтобы две сессии не конкурировали за один broker). Паттерн через `CLAUDE_PLUGIN_DATA_OVERRIDE` (а не `${CLAUDE_PLUGIN_DATA:-...}`) гарантирует, что override сработает даже если родительский env уже задал `CLAUDE_PLUGIN_DATA`.
3. **Без model-pinning** — exec `node "$COMPANION" "$@"` без вмешательства в флаги. Юрист vassal-litigator-cc явно указывает `--effort` и не использует ролевой `--model gpt-5.5`.
4. **set -eu**, exit codes из upstream.

### Резолв `$CODEX_COMPANION` в SKILL.md (новый контракт)

Главный путь — через `codex-dispatch`:

```bash
DISPATCH="$(command -v codex-dispatch || true)"
[ -z "$DISPATCH" ] && DISPATCH="$(ls -1d ~/.claude/plugins/cache/strigov-cc-plugins/vassal-litigator-cc/*/bin/codex-dispatch 2>/dev/null | sort -rV | head -1)"
[ -z "$DISPATCH" ] && DISPATCH="$(pwd)/bin/codex-dispatch"
```

И **дополнительно** прежний `$CODEX_COMPANION` (для обратной совместимости с существующими профильными скиллами, которые используют `node "$CODEX_COMPANION" task ...`):

```bash
CODEX_COMPANION="$(...same resolve as DISPATCH but pointing to vendor/codex-companion/scripts/codex-companion.mjs ...)"
```

**Isolation contract для legacy-пути**: прямой вызов `node "$CODEX_COMPANION" ..." обходит `bin/codex-dispatch` и, как следствие, не получает `CLAUDE_PLUGIN_DATA=$HOME/.claude/plugins/data/vassal-litigator-cc-codex` — broker/state свалится в дефолтный shared путь и нарушит orphan-scan/state isolation. Поэтому в SKILL.md (Ф3) перед любым `node "$CODEX_COMPANION" ..." вызовом обязателен экспорт:

```bash
export CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA_OVERRIDE:-$HOME/.claude/plugins/data/vassal-litigator-cc-codex}"
```

(одно и то же значение, что и в `bin/codex-dispatch`). Это превращает legacy-путь в functionally-equivalent `$DISPATCH`-вызову с точки зрения isolation. Альтернатива — перевести все documented invocations в SKILL.md на `$DISPATCH`; этот вариант мы НЕ выбираем из-за обратной совместимости с профильными скиллами.

**Корректный паттерн export** (применяется и в `bin/codex-dispatch`, и в SKILL.md для legacy-пути):

```bash
export CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA_OVERRIDE:-$HOME/.claude/plugins/data/vassal-litigator-cc-codex}"
```

Паттерн `${CLAUDE_PLUGIN_DATA:-default}` НЕ годится: если родительский env уже задал `CLAUDE_PLUGIN_DATA` (например, через другой codex-плагин), override не сработает и broker свалится в shared путь. Пользовательский override делается через явную переменную `CLAUDE_PLUGIN_DATA_OVERRIDE`.

Решение: в Ф3 описываем оба, помечаем `$DISPATCH` как preferred, и фиксируем обязательный `CLAUDE_PLUGIN_DATA` export для legacy-пути.

### Orphan-fix контракт (наследуется из vendored кода)

- `spawnBrokerProcess` без `detached:true` (только `child.unref()`) → broker остаётся в process group родителя.
- `app-server-broker.mjs` heartbeat: каждые 3 сек `if process.ppid === 1 → shutdown(); process.exit(0)`.
- `ensureBrokerSession` на старте вызывает `scanOrphanBrokers()` — пробегает по `~/.claude/plugins/data/vassal-litigator-cc-codex/state/*/broker.json`, kill -0 проверяет `parentPid`; мёртвый parent → kill broker + cleanup state.
- `broker.json` пишется с `parentPid: process.pid`.

Эти инварианты валидируются тестами в Ф4.

## Test strategy

- **Ф1 smoke**: `node vendor/codex-companion/scripts/codex-companion.mjs --help` exit 0 (top-level help; не `task --help` — parser стартует foreground Codex task на unknown `--help` как positional); ручная проверка `git ls-files vendor/codex-companion | wc -l` против оригинала.
- **Ф2 smoke**: `bin/codex-dispatch --help` exit 0 и/или `bin/codex-dispatch status --json` возвращает JSON (либо ECONNREFUSED — допустимо до первого `task`); `printenv CLAUDE_PLUGIN_DATA` показывает vassal-litigator-cc-codex.
- **Ф3 smoke**: `grep -n openai-codex skills/codex-invocation/SKILL.md` — 0 совпадений (без исключений; historical/legacy блок не сохраняется в файле). Manual-чтение: новый раздел Resolve через codex-dispatch присутствует, orphan-cleanup нота присутствует.
- **Ф4**:
  - `node vendor/codex-companion/tests/index.js` (graceful-shutdown.test, heartbeat.test, scan-orphans.test, integration-kill9.test). Integration-kill9 требует реальный fork/kill — если в среде CI/dev падает по правам, помечаем skip.
  - `tests/smoke/test-codex-dispatch.sh` — exit 0.
- **Ф5**: ручной review README/ARCHITECTURE/CHANGELOG; `git grep -n openai-codex` показывает только historical refs в CHANGELOG.

Никаких новых unit/integration тестов поверх vendored — мы доверяем upstream-тестам superpowers, которые перенесены 1-в-1.

## Risks / unknowns

1. **Конкуренция за broker.sock**, если на машине одновременно работают `superpowers-strigov-ver` и `vassal-litigator-cc`. Митигация: разные `CLAUDE_PLUGIN_DATA` (`superpowers-strigov-ver-codex` vs `vassal-litigator-cc-codex`), брокеры изолированы. Тестов на это нет — только архитектурный инвариант через wrapper.
2. **Размер репо**: vendored код добавляет ~2-3к строк JS. Допустимо для плагина.
3. **Дрифт от upstream**: superpowers может обновить companion (например, до v1.0.5 OpenAI), и vassal отстанет. Митигация: `vendor/codex-companion/VERSION` фиксирует upstream-tag и дату vendor-операции. Будущее обновление — отдельный sync-plan.
4. **Профильные скиллы продолжают использовать `$CODEX_COMPANION`**. Ф3 обязан гарантировать, что новый Resolve ставит эту переменную на vendored путь, иначе intake/add-evidence сломаются. Тестируется ручным прогоном `tests/smoke/test-intake.sh` после Ф3 (опционально).
5. **`bin/` may not be in PATH at marketplace install**. Митигация: `command -v` fallback на marketplace glob; SKILL.md явно описывает оба пути.
6. **Лицензия**: upstream OpenAI codex-plugin под Apache 2 (NOTICE есть). vassal-litigator-cc — GPL-3.0. Apache 2 совместим с GPL-3 при включении NOTICE/LICENSE — что мы и делаем (копируем `LICENSE` + `NOTICE` из vendored). Никаких лицензионных модификаций не требуется.

## Phases

### Ф1: завендорить codex-companion (без тестов)

**Scope**: скопировать `vendor/codex-companion/` целиком из `superpowers-strigov-ver`, исключая `tests/`.

**Шаги**:

1. `mkdir -p vendor/codex-companion`.
2. `cp -R` следующих путей из `/Users/strigov/Documents/Claude/projects-сode/superpowers-strigov-ver/vendor/codex-companion/`:
   - `scripts/` (включая `lib/`)
   - `schemas/`
   - `prompts/`
   - `.claude-plugin/`
   - `LICENSE`, `NOTICE`, `VERSION`
3. **Не копировать**: `tests/` (это Ф4).
4. Smoke: `node vendor/codex-companion/scripts/codex-companion.mjs --help` (top-level; `task --help` запрещён — parser трактует `--help` как positional prompt и стартует foreground task).
5. Git add vendor/, отдельный коммит `feat(Ф1): vendor codex-companion v1.0.4 + orphan-fix from superpowers-strigov-ver`.

**DoD**: smoke passes; `vendor/codex-companion/scripts/lib/broker-lifecycle.mjs` содержит `scanOrphanBrokers` (быстрая проверка `grep -n scanOrphanBrokers`); `vendor/codex-companion/scripts/app-server-broker.mjs` содержит heartbeat (`grep -n "process.ppid === 1"`).

### Ф2: bin/codex-dispatch wrapper

**Scope**: добавить bash-wrapper в `bin/codex-dispatch`, адаптированный под vassal-litigator-cc.

**Шаги**:

1. `mkdir -p bin`.
2. Создать `bin/codex-dispatch` (см. Contracts: marketplace glob под `vassal-litigator-cc`, dev-fallback, `CLAUDE_PLUGIN_DATA=$HOME/.claude/plugins/data/vassal-litigator-cc-codex`, без model-pinning, `exec node "$COMPANION" "$@"`).
3. `chmod +x bin/codex-dispatch`.
4. Smoke: `bin/codex-dispatch --help` exit 0; `bin/codex-dispatch status --json` (допустимо ECONNREFUSED до первого task). `task --help` использовать нельзя.
5. Коммит `feat(Ф2): bin/codex-dispatch wrapper для vendored companion с CLAUDE_PLUGIN_DATA isolation`.

**DoD**: оба smoke ok; `bin/codex-dispatch` исполняемый; `grep -n CLAUDE_PLUGIN_DATA bin/codex-dispatch` показывает корректное имя.

### Ф3: переписать skills/codex-invocation/SKILL.md

**Scope**: обновить контракт резолвинга и stale-lock.

**Шаги**:

1. В разделе «Предусловия / Resolve `$CODEX_COMPANION`»:
   - Удалить 3-tier по `openai-codex`.
   - Добавить новый главный блок: Resolve `$DISPATCH` (как в superpowers SKILL.md, адаптировано под `strigov-cc-plugins/vassal-litigator-cc`).
   - Сохранить экспорт `$CODEX_COMPANION` (через тот же resolver, но указывающий на `vendor/codex-companion/scripts/codex-companion.mjs`) — для обратной совместимости с профильными скиллами.
   - **Обязательный шаг для legacy-пути**: рядом с экспортом `$CODEX_COMPANION` явно прописать `export CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA_OVERRIDE:-$HOME/.claude/plugins/data/vassal-litigator-cc-codex}"` и зафиксировать в SKILL.md, что любой documented `node "$CODEX_COMPANION" ..." вызов должен идти после этого export (иначе ломается isolation/orphan-scan, см. Contracts → Isolation contract для legacy-пути). Альтернатива — перевести все documented invocations на `$DISPATCH` — отвергнута из-за совместимости с профильными скиллами.
   - Smoke-check заменить с `node "$CODEX_COMPANION" task --help` на `node "$CODEX_COMPANION" --help` (top-level help; `task --help` стартует foreground task — см. R1-B1).
2. Добавить orphan-cleanup ноту (заимствовать формулировку из superpowers SKILL.md, адаптировать имя data-dir).
3. Переписать секцию «`--resume-last`, stale-lock и `--fresh`»:
   - Уточнить, что `--fresh` — workaround только для **in-memory job state в живом брокере**.
   - Orphan-брокеры от прошлых kill-9 теперь чистятся автоматически (heartbeat ~6 сек + scanOrphanBrokers на startup), `--fresh` для этого больше не нужен.
4. Обновить раздел «Что нельзя делать»:
   - Убрать `Не использовать hardcoded ~/.claude/plugins/cache/openai-codex/...`.
   - Добавить `Не вызывать codex напрямую через codex exec` (из superpowers; кроме явного Branch B визуализатора, как у нас и есть).
5. Обновить «Session paths (for debugging)» — добавить новые пути (vendored companion path, isolated CLAUDE_PLUGIN_DATA).
6. Коммит `refactor(Ф3): SKILL.md под vendored companion + orphan auto-cleanup`.

**DoD**: `grep -n openai-codex skills/codex-invocation/SKILL.md` — 0 совпадений (без исключений — историческое упоминание в файле не сохраняется); файл синтаксически валидный YAML frontmatter; ручное чтение подтверждает наличие orphan-cleanup ноты и переписанной stale-lock секции.

### Ф4: тесты vendor/codex-companion

**Scope**: перенести тесты + smoke для wrapper.

**Шаги**:

1. `cp -R` из `superpowers/vendor/codex-companion/tests/` → `vendor/codex-companion/tests/` (включая `helpers/`, `index.js`, `package.json`).
2. Создать `tests/smoke/test-codex-dispatch.sh` (по образцу существующих `tests/smoke/test-intake.sh`):
   - `bin/codex-dispatch --help` exit 0 (top-level help; `task --help` запрещён — см. примечание в acceptance criteria), плюс `bin/codex-dispatch status --json` возвращает JSON или ECONNREFUSED.
   - Проверка, что выбранный COMPANION путь под `vendor/codex-companion/`.
3. Запустить `node vendor/codex-companion/tests/index.js`. Если integration-kill9 падает по env-причинам, задокументировать в `tests/README.md`.
4. Запустить `tests/smoke/test-codex-dispatch.sh`.
5. Коммит `test(Ф4): vendored tests heartbeat/scan-orphans/graceful-shutdown/integration-kill9 + smoke wrapper`.

**DoD**: 4 vendored unit-теста pass; smoke wrapper pass.

### Ф5: документация

**Scope**: README, ARCHITECTURE, CHANGELOG, plugin.json, conventions.md.

**Шаги**:

1. `.claude-plugin/plugin.json`: переписать `description` (vendored codex-companion вместо openai-codex).
2. `README.md`:
   - Раздел «Установка»: убрать обязательное `/plugin install codex@openai-codex` и любые другие упоминания `openai-codex` (включая «опционально» / «больше не требуется») — DoD требует `git grep -n openai-codex -- ':!CHANGELOG.md'` == 0, поэтому в README в принципе не должно остаться этой строки. Login юриста описать через `!codex login` без отсылки к плагину: «требует `npm i -g @openai/codex` — это standalone CLI, не плагин Claude Code».
   - Добавить короткий блок «Codex transport»: vendored runtime + `bin/codex-dispatch`, ссылка на `skills/codex-invocation/SKILL.md`.
3. `ARCHITECTURE.md`: обновить раздел про Codex (vendored runtime, bin/codex-dispatch, isolated CLAUDE_PLUGIN_DATA, orphan-cleanup).
4. `CHANGELOG.md` Unreleased:
   - feat: vendored `vendor/codex-companion/` (форк OpenAI codex-plugin v1.0.4) с orphan-fix (heartbeat + scanOrphanBrokers, no detached).
   - feat: `bin/codex-dispatch` wrapper.
   - refactor: skills/codex-invocation/SKILL.md под vendored runtime.
   - removed: hard-зависимость от плагина `openai-codex`.
5. `shared/conventions.md`: обновить упоминания.
6. `tests/README.md`: упомянуть smoke для codex-dispatch + vendored tests.
7. Коммит `docs(Ф5): README/ARCHITECTURE/CHANGELOG/plugin.json про vendored companion`.

**DoD**: `git grep -n openai-codex -- ':!CHANGELOG.md'` — 0 продакшн-упоминаний (упоминания в CHANGELOG.md historical допустимы).
