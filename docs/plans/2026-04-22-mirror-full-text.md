---
slug: mirror-full-text
created: 2026-04-22
status: in-progress
phases:
  - id: Ф1
    scope: "Единый контракт зеркала: обновить shared/mirror-template.md (убрать правило усечения, зафиксировать полнотекстовость)"
    status: done
  - id: Ф2
    scope: "Apply-фазы файловых скиллов (intake/add-evidence/add-opponent): тело зеркала = полный OCR-файл"
    status: done
  - id: Ф3
    scope: "Plan-фазы файловых скиллов: убрать требование фиксировать первые 20000 символов, перейти к ссылке на полный OCR-артефакт"
    status: in-progress
  - id: Ф4
    scope: "update-index: оба сценария (создание и перегенерация зеркала) используют полный текст"
    status: pending
  - id: Ф5
    scope: "Сверка ARCHITECTURE.md, tests/, scripts/, smoke-сценариев с новым контрактом"
    status: pending
---

## Goal

Привести MD-зеркала документов (`.vassal/mirrors/doc-NNN.md`) к единому контракту «полный извлечённый текст без усечения» во всех файловых скиллах плагина (`intake`, `add-evidence`, `add-opponent`, `update-index`), убрать любые правила усечения по страницам (10/50) и символам (20000) из prompt-контрактов и документации. Назначение зеркала (кэш извлечённого текста, не замена оригинала), путь хранения (`.vassal/mirrors/doc-NNN.md`), схема `index.yaml`, структура `history.md` и pipeline `plan → review → apply → verify` остаются без изменений. Fallback-логика OCR данным ТЗ не затрагивается.

## Files

Ф1 (контракт зеркала):
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/shared/mirror-template.md`

Ф2 (apply-фазы):
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/prompts/file-executor-intake-apply.md`
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/prompts/file-executor-add-evidence-apply.md`
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/prompts/file-executor-add-opponent-apply.md`

Ф3 (plan-фазы):
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/prompts/file-executor-intake-plan.md`
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/prompts/file-executor-add-evidence-plan.md`
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/prompts/file-executor-add-opponent-plan.md`

Ф4 (update-index):
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/prompts/file-executor-update-index.md`

Ф5 (сверка/smoke):
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/ARCHITECTURE.md` (раздел 6.1 уже корректен — проверить, что ничего не противоречит)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/smoke/test-intake.sh` (расширение: большой документ + assert_mirror_full)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/smoke/test-add-evidence.sh` (**новый файл**)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/smoke/test-add-opponent.sh` (**новый файл**)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/smoke/test-update-index.sh` (**новый файл**, покрывает режимы A и C)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/smoke/test-analytical-review.sh` (регрессия — без изменений)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/smoke/test-catalog.sh` (регрессия — без изменений)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/smoke/test-timeline.sh` (регрессия — без изменений)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/fixtures/dummy-case/Входящие документы/большой-договор.pdf` (**новая фикстура**, либо её текстовый источник в `_sources/`)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/tests/fixtures/dummy-case/expected/index-after-intake.yaml` (обновление — новая запись под большой документ)
- `/Users/strigov/Documents/Claude/Projects/Suzerain/plugins/vassal-litigator-cc/scripts/extract_text.py` (только чтение — убедиться, что скрипт пишет полный текст; менять не планируется)

## Contracts

Общая формулировка-эталон, которой заменяются все варианты правила усечения:

> Тело зеркала — полный извлечённый текст документа из `{{work_dir}}/ocr/<имя>.txt` (или соответствующего артефакта OCR для данного скилла). Усечение по страницам или символам запрещено: зеркало должно быть полнотекстовым кэшем оригинала, независимо от размера документа.

Пофайловые изменения (точные замены):

1. `shared/mirror-template.md` — строка 55, пункт 7 правил создания:
   - Убрать пункт `7. Большие документы (>50 страниц) — извлечь первые 10, пометить [... документ содержит N страниц, извлечены первые 10 ...]`.
   - Вместо него добавить пункт `7. Размер документа — не основание для усечения. Зеркало содержит весь извлечённый текст, даже если документ объёмный. Если OCR/парсер извлёк текст частично, в зеркало попадает ровно то, что фактически извлечено, без дополнительного усечения.`
   - В шапке (строка 3) формулировка «полнотекстовое markdown-представление» уже корректна — не трогаем.

2. `prompts/file-executor-intake-apply.md:72`:
   - Было: `Тело зеркала — текст из {{work_dir}}/ocr/<имя>.txt (plan-фаза уже прогнала OCR), первые 10 страниц или 20000 символов, что наступит раньше.`
   - Стало: `Тело зеркала — полный текст из {{work_dir}}/ocr/<имя>.txt целиком (plan-фаза уже прогнала OCR). Усечение по страницам или символам запрещено: зеркало полнотекстовое независимо от размера документа.`

3. `prompts/file-executor-add-evidence-apply.md:50`:
   - Было: `Тело — OCR-текст из {{work_dir}}/ocr/<имя>.txt (первые 10 страниц/20000 символов).`
   - Стало: `Тело — полный OCR-текст из {{work_dir}}/ocr/<имя>.txt целиком. Усечение запрещено.`

4. `prompts/file-executor-add-opponent-apply.md:50`:
   - Было: `Тело — OCR из {{work_dir}}/ocr/<имя>.txt (10 страниц / 20000 символов).`
   - Стало: `Тело — полный OCR из {{work_dir}}/ocr/<имя>.txt целиком. Усечение запрещено.`

5. `prompts/file-executor-intake-plan.md:46`:
   - Было: `Зафиксируй extraction_method, confidence, первые 20000 символов — это пригодится apply-фазе для md-зеркал.`
   - Стало: `Зафиксируй extraction_method, confidence и путь к полному OCR-артефакту в {{work_dir}}/ocr/<имя>.txt — apply-фаза использует весь этот файл как тело md-зеркала (полный текст, без усечения).`

6. `prompts/file-executor-add-evidence-plan.md:38`:
   - Было: `Зафиксируй extraction_method, confidence, первые 20000 символов.`
   - Стало: `Зафиксируй extraction_method, confidence и путь к полному OCR-артефакту в {{work_dir}}/ocr/<имя>.txt (apply-фаза берёт его целиком как тело зеркала).`

7. `prompts/file-executor-add-opponent-plan.md:39`:
   - Аналогично п.6.

Важное замечание про update-index: в отличие от `intake`/`add-evidence`/`add-opponent`, скилл `update-index` **не** получает placeholder `{{work_dir}}` (см. `skills/update-index/SKILL.md:45–52`, `prompts/README.md:41–44`) и не имеет lifecycle-контракта «создать/удалить work_dir». Протягивать `work_dir` end-to-end в update-index в рамках этого ТЗ избыточно (меняется контракт скилла и жизненный цикл временных артефактов). Поэтому полнотекстовый OCR-артефакт в update-index создаётся в **self-contained временной директории внутри самого apply-шага** (без нового placeholder): `TMP=$(mktemp -d -t vassal-reindex-XXXXXX)` → `extract_text.py <file> --output-dir "$TMP"` → прочитать `$TMP/<stem>.txt` целиком и вставить в тело зеркала → `rm -rf "$TMP"` в конце шага. Ни `{{work_dir}}`, ни постоянных побочных артефактов не возникает.

8. `prompts/file-executor-update-index.md` — режим A, шаг 2 (строки 23–25), вызов CLI:
   - Было: `python3 [PLUGIN_ROOT]/scripts/extract_text.py --file "путь_к_файлу" --output "путь_к_tmp"` (несуществующие флаги `--file/--output`).
   - Стало: в шаге 2 создай временную директорию `TMP=$(mktemp -d -t vassal-reindex-XXXXXX)`, запусти `python3 [PLUGIN_ROOT]/scripts/extract_text.py "путь_к_файлу" --output-dir "$TMP"` — соответствует реальному CLI (`scripts/extract_text.py:215–239`: позиционный `<файл>` + опциональный `--output-dir <папка>`, скрипт сам складывает полный текст в `<output-dir>/<stem>.txt`). Зафиксируй `extraction_method`, `confidence` и путь `$TMP/<stem>.txt` для использования в шаге формирования тела зеркала. В конце apply-шага (после того как тело зеркала записано) обязательный `rm -rf "$TMP"`.

9. `prompts/file-executor-update-index.md:26` (режим A — создание зеркала, тело):
   - Было: `Тело зеркала — извлечённый текст (первые 20000 символов).`
   - Стало: `Тело зеркала — полный извлечённый текст целиком, без усечения по страницам или символам. Источник полного текста — файл `$TMP/<stem>.txt`, созданный шагом 2 через `extract_text.py --output-dir`. Читай этот файл целиком и вставляй его содержимое в тело зеркала. После записи зеркала `$TMP` удаляется (`rm -rf`), постоянных временных артефактов не остаётся.`

10. `prompts/file-executor-update-index.md` — режим C, шаг 2 (строки 39–40), и вызов CLI, и тело:
    - Было (CLI): `запусти OCR через python3 [PLUGIN_ROOT]/scripts/extract_text.py` — без обязательного аргумента-пути к файлу и без `--output-dir`.
    - Стало (CLI): создай временную директорию `TMP=$(mktemp -d -t vassal-reindex-XXXXXX)`, затем `python3 [PLUGIN_ROOT]/scripts/extract_text.py "путь_к_исходнику_из_index.file" --output-dir "$TMP"`. Путь к исходнику берётся из поля `file` соответствующей записи `.vassal/index.yaml`. В конце шага — `rm -rf "$TMP"`.
    - Было (тело): `тело = актуальный текст (первые 20000 символов).`
    - Стало (тело): `тело = актуальный полный текст целиком, без усечения. Источник — файл `$TMP/<stem>.txt`, созданный только что в этом же шаге; читается целиком и записывается в тело зеркала. После записи зеркала `$TMP` удаляется.`

Все последующие пункты нумерации сдвигаются соответственно.

12. `ARCHITECTURE.md` — раздел 6.1 (строки 444–452) уже содержит пункт «Полный текст» и НЕ содержит правила усечения. Менять не требуется, но в рамках Ф5 выполняется сверка (grep) на отсутствие формулировок «10 страниц», «20000 символов», «50 страниц» во всём файле.

13. `tests/smoke/*.sh`, `scripts/extract_text.py` — по предварительному grep упоминаний усечения не обнаружено. В Ф5 — финальная сверка и фиксация результата в логе изменений.

Инварианты после доработки (должны выполняться одновременно):
- В репозитории не остаётся контрактных упоминаний усечения зеркала по 10/50 страницам или 20000 символам. Формулировки типа «страниц», «символов» допустимы только в нейтральном контексте (поле `pages` в frontmatter, описание качества OCR и т. п.).
- Для всех файловых скиллов (`intake`, `add-evidence`, `add-opponent`, `update-index`) политика зеркал единообразна.
- Зеркало не превращается в summary: раздел `analysis/` и `positions/` по-прежнему держит аналитику.
- Логика усечения не зависит от размера документа.

## Test strategy

Кодовых тестов в репозитории нет (плагин состоит из Markdown-промптов и вспомогательных Python-скриптов). Проверка — контрактная (grep) + ручной прогон smoke, расширенный под полнотекстовый контракт по всем четырём изменяемым путям (intake, add-evidence, add-opponent, update-index).

1. Контрактный grep (должен возвращать пустой результат после всех фаз):
   ```
   grep -rn -E "(20000|первые 10 страниц|первых 10 страниц|>50 страниц|10 страниц\s*/|страниц\s*/\s*20000)" prompts/ shared/ ARCHITECTURE.md tests/ scripts/
   ```
2. Контрактный grep на присутствие новой формулировки «полный» в ключевых местах:
   ```
   grep -n "полн" prompts/file-executor-intake-apply.md prompts/file-executor-add-evidence-apply.md prompts/file-executor-add-opponent-apply.md prompts/file-executor-update-index.md shared/mirror-template.md
   ```
3. Контрактный grep на корректность CLI вызова `extract_text.py` в update-index:
   ```
   grep -nE "\-\-file|\-\-output[^\-]" prompts/file-executor-update-index.md   # должен быть пустым
   grep -n  "output-dir" prompts/file-executor-update-index.md                  # ровно 2 совпадения (режим A и режим C)
   ```
4. Сверка единообразия: во всех четырёх apply/update-index prompt-ах формулировка про тело зеркала эквивалентна (полный текст из OCR-артефакта, усечение запрещено).

### Large-document fixture

Для доказательства полнотекстовости нужен специальный большой документ, которого сейчас в фикстурах нет. Подготовка:

5. Добавить фикстуру `tests/fixtures/dummy-case/Входящие документы/большой-договор.pdf` — синтетический PDF с текстовым слоем, не менее **50 страниц** и **> 60 000 символов** извлекаемого текста (заведомо больше старого лимита 20 000). Генерация — однократно локально через `reportlab`/`fpdf` (скрипт не коммитится как зависимость плагина, сам PDF кладётся в фикстуру). Допустимая альтернатива, если бинарь в репозитории нежелателен: хранить исходник в `tests/fixtures/dummy-case/_sources/большой-договор.txt` (≥ 60 000 символов) и генерировать PDF во время smoke командой, добавленной в начало `test-intake.sh` (проверка наличия + генерация при отсутствии).
6. Расширить фикстуру ожидаемого состояния (`tests/fixtures/dummy-case/expected/`) новой строкой в `index-after-intake.yaml` под этот документ и пометкой в `history-entry.md`.

### Сценарии smoke — по одному на каждый изменяемый entrypoint

Каждый сценарий запускается вручную, но содержит **автоматически проверяемые ассерты** (через `wc -c`, `grep -c`, `python3 -c`), которые перечислены в разделе ПРОВЕРКА соответствующего smoke-скрипта.

Важные ограничения, которые влияют на форму ассертов:
- Инвариант имени зеркала — только `doc-NNN.md` (трёхзначный порядковый номер), см. `shared/mirror-template.md:36`, `ARCHITECTURE.md:410`, `tests/smoke/test-intake.sh:87`. Конкретное `NNN` заранее неизвестно, поэтому путь к зеркалу большого документа в ассертах определяется **не по имени файла**, а через lookup в `.vassal/index.yaml` по `origin.name` (или другому устойчивому полю `name`/`file`/`mirror`, соответствующему исходному PDF).
- Apply-фазы `intake`/`add-evidence`/`add-opponent` удаляют `{{work_dir}}` в конце (`prompts/file-executor-intake-apply.md:134–139`, `prompts/file-executor-add-evidence-apply.md:108–113`, `prompts/file-executor-add-opponent-apply.md:101–106`). После стандартного apply→cleanup OCR-артефакта в `.vassal/work/.../ocr/` уже нет — ссылаться на `.vassal/work/.../ocr/...` после apply запрещено. Контракт apply→cleanup не меняем.
- Однако **исходник документа** сохраняется по дизайну в `.vassal/raw/` (для intake — батч `intake-*`, для add-evidence/add-opponent/update-index — соответствующие постоянные локации, см. `ARCHITECTURE.md` о `.vassal/raw/`). Этот исходник — ground truth, на котором можно заново прогнать OCR и получить эталонную длину.

Стратегия сильной проверки полнотекстовости: в верификации smoke-сценария **заново прогоняем `scripts/extract_text.py` на сохранённом исходнике** во временной директории и сравниваем длину тела зеркала с длиной fresh OCR-вывода. Это доказывает именно то, что требует ТЗ — «зеркало не обрезано» — и не зависит от удалённого `work_dir`.

Общая MIRROR-lookup функция (используется во всех четырёх smoke-сценариях):

```
# Находит путь к зеркалу для документа по index.yaml
# Аргумент: имя исходного файла (напр., "большой-договор.pdf")
mirror_of() {
  python3 - "$1" "$SMOKE_CASE/.vassal/index.yaml" <<'PY'
import sys, yaml, pathlib
name, idx = sys.argv[1], sys.argv[2]
data = yaml.safe_load(pathlib.Path(idx).read_text(encoding="utf-8"))
for entry in data.get("documents", []):
    origin = entry.get("origin", {}) or {}
    if origin.get("name") == name or entry.get("file", "").endswith(name):
        print(entry["mirror"]); break
PY
}

# Читает поле `file` из записи index.yaml по имени исходника (origin.name либо
# суффикс поля `file`). Поле `file` — это и есть путь к сохранённому исходнику
# (обычно внутри .vassal/raw/, но возможны и другие локации для add-evidence/
# add-opponent/update-index); никаких предположений о конкретной подпапке тут нет.
source_of() {
  python3 - "$1" "$SMOKE_CASE/.vassal/index.yaml" <<'PY'
import sys, yaml, pathlib
name, idx = sys.argv[1], sys.argv[2]
data = yaml.safe_load(pathlib.Path(idx).read_text(encoding="utf-8"))
for entry in data.get("documents", []):
    origin = entry.get("origin", {}) or {}
    if origin.get("name") == name or entry.get("file", "").endswith(name):
        print(entry["file"]); break
PY
}

# Читает поле `file` из записи index.yaml по конкретному doc-ID (строка вида
# `doc-NNN`, ровно как в поле `id` записи index.yaml). Используется в
# сценариях, где lookup по имени неприменим (напр., update-index режим C —
# перегенерация существующей записи, чей origin.name/file не совпадает с
# именем входной фикстуры).
source_of_id() {
  python3 - "$1" "$SMOKE_CASE/.vassal/index.yaml" <<'PY'
import sys, yaml, pathlib
doc_id, idx = sys.argv[1], sys.argv[2]
data = yaml.safe_load(pathlib.Path(idx).read_text(encoding="utf-8"))
for entry in data.get("documents", []):
    if entry.get("id") == doc_id:
        print(entry["file"]); break
PY
}

# Читает поле `mirror` из записи index.yaml по doc-ID (см. source_of_id).
mirror_of_id() {
  python3 - "$1" "$SMOKE_CASE/.vassal/index.yaml" <<'PY'
import sys, yaml, pathlib
doc_id, idx = sys.argv[1], sys.argv[2]
data = yaml.safe_load(pathlib.Path(idx).read_text(encoding="utf-8"))
for entry in data.get("documents", []):
    if entry.get("id") == doc_id:
        print(entry["mirror"]); break
PY
}
```

Набор ассертов `assert_mirror_full <source_name>` (одинаковый во всех четырёх сценариях). Поддерживается также форма `assert_mirror_full --id <STALE_ID>` — для update-index режима C, где lookup по имени неприменим (входная фикстура `большой-договор.pdf` подменяет исходник существующей записи, но `origin.name`/`file` этой записи ≠ имени фикстуры).

```
assert_mirror_full() {
  local MIRROR_REL SOURCE_REL MIRROR SOURCE TMP OCR_FILE MIRROR_CHARS OCR_CHARS
  if [ "$1" = "--id" ]; then
    local DOC_ID="$2"
    MIRROR_REL=$(mirror_of_id "$DOC_ID")
    SOURCE_REL=$(source_of_id "$DOC_ID")
  else
    local SRC_NAME="$1"
    MIRROR_REL=$(mirror_of "$SRC_NAME")
    SOURCE_REL=$(source_of "$SRC_NAME")
  fi
  MIRROR="$SMOKE_CASE/$MIRROR_REL"
  SOURCE="$SMOKE_CASE/$SOURCE_REL"
  [ -f "$MIRROR" ] || fail "mirror not found: $MIRROR"
  [ -f "$SOURCE" ] || fail "source not found in .vassal/raw: $SOURCE"

  # 1. Маркеры усечения отсутствуют (дешёвая контрактная проверка).
  ! grep -q "извлечены первые 10" "$MIRROR" || fail "truncation marker '10 pages' in mirror"
  ! grep -qE "\[\.\.\. документ содержит [0-9]+ страниц" "$MIRROR" \
    || fail "truncation marker 'N pages' in mirror"

  # 2. Сильная проверка: заново прогоняем OCR на сохранённом исходнике
  #    и сравниваем длину тела зеркала с длиной fresh OCR-вывода.
  TMP=$(mktemp -d -t vassal-assert-XXXXXX)
  python3 "$PLUGIN_ROOT/scripts/extract_text.py" "$SOURCE" --output-dir "$TMP" \
    || { rm -rf "$TMP"; fail "re-OCR failed for $SOURCE"; }
  OCR_FILE=$(ls "$TMP"/*.txt | head -1)
  [ -s "$OCR_FILE" ] || { rm -rf "$TMP"; fail "empty fresh OCR output"; }

  # Тело зеркала = всё, кроме YAML-фронтматтера (между двумя "---").
  MIRROR_CHARS=$(awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2{print}' "$MIRROR" | wc -m)
  OCR_CHARS=$(wc -m < "$OCR_FILE")
  rm -rf "$TMP"

  # Допуск: -100 символов на нормализацию пробелов/переводов строк при вставке в md.
  [ "$MIRROR_CHARS" -ge "$((OCR_CHARS - 100))" ] \
    || fail "Mirror truncated: body=$MIRROR_CHARS chars < fresh OCR=$OCR_CHARS chars"
}
```

Ключевые свойства этого ассерта:
- Не обращается к удалённому `work_dir` — контракт apply→cleanup не нарушается.
- Использует исходник из `.vassal/raw/` (сохраняется по дизайну плагина).
- Fresh-OCR служит эталонной длиной; сравнение зеркала с эталоном доказывает отсутствие усечения, а не просто «больше 20 000».
- Ошибочное зеркало, обрезанное на 25k/40k/любом другом пороге, провалит ассерт, если полный OCR длиннее.
- Маркеры усечения («первые 10», «документ содержит N страниц») проверяются отдельно как дополнительная контрактная страховка.

Требование к фикстуре: `большой-договор.pdf` должен давать fresh OCR длиной заведомо больше любого подозрительного порога усечения (60 000+ символов), чтобы сравнение `MIRROR_CHARS ≥ OCR_CHARS − 100` имело смысл. См. раздел Large-document fixture выше.

7. **intake (`tests/smoke/test-intake.sh`)** — расширить существующий скрипт:
   - Добавить `большой-договор.pdf` в копируемый набор «Входящие документы».
   - После apply: `assert_mirror_full "большой-договор.pdf"` (функция сама делает lookup зеркала и исходника по `index.yaml`, заново прогоняет OCR на `.vassal/raw/...` и сравнивает длины).
8. **add-evidence** — добавить новый smoke `tests/smoke/test-add-evidence.sh`: после прогона `/vassal-litigator:add-evidence` с `большой-договор.pdf` — `assert_mirror_full "большой-договор.pdf"` (тот же re-run-OCR-сценарий; исходник хранится в `.vassal/raw/` согласно контракту add-evidence).
9. **add-opponent** — новый smoke `tests/smoke/test-add-opponent.sh`: после `/vassal-litigator:add-opponent` с большим документом — `assert_mirror_full "большой-договор.pdf"` (то же самое; исходник в `.vassal/raw/` стороны opponent).
10. **update-index** — новый smoke `tests/smoke/test-update-index.sh`, покрывающий оба режима A и C:
    - Режим A: положить `большой-договор.pdf` рядом с существующим `index.yaml` (сценарий, где update-index находит «бесхозный» файл), запустить `/vassal-litigator:update-index`, затем `assert_mirror_full "большой-договор.pdf"` (функция подтянет `file:` из новой записи `index.yaml` — путь к исходнику в `.vassal/raw/` или туда, куда update-index его поместил, — и заново прогонит OCR).
    - Режим C: сценарий **привязывается к конкретному `doc-NNN`-идентификатору**, а не к имени входной фикстуры (имя входной фикстуры `большой-договор.pdf` ≠ `origin.name`/`file` существующей записи, поэтому lookup по имени здесь неприменим).
      1. В сетапе теста выбрать конкретный `STALE_ID` (строка вида `doc-NNN`, например `STALE_ID="doc-001"`, ровно как в поле `id` записи `index.yaml`) — либо уже имеющий `mirror_stale: true` в `.vassal/index.yaml`, либо искусственно выставить флаг `mirror_stale: true` для выбранной записи `doc-NNN` (минимальной правкой `index.yaml` через `python3 -c "import yaml; ..."`). Запомнить `STALE_ID` в переменной сценария как строку `doc-NNN`.
      2. Подменить исходник этой записи: записать содержимое `большой-договор.pdf` по пути, который указан в поле `file` записи `STALE_ID` (этот путь — `.vassal/raw/...` или иная постоянная локация по дизайну плагина); `origin.name` и `file` записи при этом **не меняются** — меняется только содержимое файла по этому пути.
      3. Запустить `/vassal-litigator:update-index`.
      4. Проверить:
         - `assert_mirror_full --id "$STALE_ID"` — функция по `STALE_ID` достанет актуальный `mirror` и `file` из обновлённого `index.yaml`, заново прогонит `extract_text.py` на подменённом исходнике и сравнит длину тела зеркала с длиной свежего OCR-вывода.
         - Дополнительно: для записи `STALE_ID` поле `mirror_stale: false` и `last_verified` обновлён на текущую дату.
    - Дополнительный ассерт CLI-совместимости: `assert_mirror_full` вызывает `extract_text.py <source> --output-dir <tmp>` с реальными аргументами, что и проверяет CLI-контракт de facto (если CLI сломан — ассерт падает с `re-OCR failed`, а не с мнимой пометкой про `--help`).
11. Регрессия: `test-analytical-review.sh`, `test-catalog.sh`, `test-timeline.sh` продолжают проходить (они читают зеркала — увеличение тела не должно ломать их, разве что увеличит расход токенов, что допустимо по ТЗ).

## Risks / unknowns / assumptions

Риски:
- R1. Рост расхода токенов у downstream-скиллов (`catalog`, `timeline`, `prepare-hearing`), которые читают зеркала. ТЗ явно это принимает («без усечения на всякий случай»); downstream-скиллы сами решают, сколько грузить (в `init-case.md:181` уже есть собственное ограничение «первые ~2000 символов» — его не трогаем, оно про чтение, а не про создание зеркала).
- R2. Очень большие документы (сотни страниц) могут создавать md-файлы в десятки МБ. Смягчение: ТЗ явно требует не вводить усечение; поведение остаётся на ответственности OCR-слоя (`scripts/extract_text.py`). Текущий скрипт не меняем.
- R3. Расхождение между plan-фазой (фиксирует только ссылку на OCR-артефакт) и apply-фазой (читает весь файл). Смягчение: в plan-фазе явно пишем путь к артефакту, apply-фаза читает `{{work_dir}}/ocr/<имя>.txt` целиком — контракт фиксирует это одинаково в обоих промптах.

Неизвестное:
- U1. Есть ли неявные потребители «первых 20000 символов» в plan → apply передаче. Предварительный grep показывает, что ограничение живёт только в самих prompt-текстах; структура work_dir (`{{work_dir}}/ocr/*.txt`) уже содержит полный текст. Проверим в Ф3 ещё раз.

Допущения:
- A1. `scripts/extract_text.py` уже сохраняет полный извлечённый текст в `work_dir/ocr/<имя>.txt` без усечения. Изменения скрипта в данном ТЗ не нужны (не меняем Python-код, не добавляем зависимостей).
- A2. Pipeline `plan → review → apply → verify` не завязан на длину тела зеркала — review читает план, а не содержимое зеркала.
- A3. `index.yaml`, `history.md`, `.vassal/raw/` не меняют назначение и схему.

## Phases

### Ф1 — Контракт зеркала в shared/mirror-template.md

Шаги:
1. Открыть `shared/mirror-template.md`.
2. Заменить пункт 7 в разделе «Правила создания» (строка 55):
   - Удалить формулировку про `>50 страниц` и `первые 10`.
   - Вставить новый пункт 7: «Размер документа — не основание для усечения. Зеркало содержит весь извлечённый текст целиком. Если OCR/парсер извлёк текст частично, в зеркало попадает ровно то, что фактически извлечено».
3. Проверить, что шапка (строка 3) и пункт 1 (строка 49, «Полный текст — весь текст переносится...») согласованы с новой политикой. Пункт 1 уже корректен — не трогаем.
4. Финальный grep по файлу: `grep -n "20000\|10 страниц\|50 страниц" shared/mirror-template.md` — должен быть пустым.

Критерий завершения: шаблон однозначно фиксирует полнотекстовость, ни одного упоминания усечения нет.

### Ф2 — Apply-фазы (intake, add-evidence, add-opponent)

Шаги:
1. `prompts/file-executor-intake-apply.md`: заменить строку 72 (см. Contracts п.2).
2. `prompts/file-executor-add-evidence-apply.md`: заменить строку 50 (см. Contracts п.3).
3. `prompts/file-executor-add-opponent-apply.md`: заменить строку 50 (см. Contracts п.4).
4. Убедиться, что во всех трёх файлах формулировка тела зеркала эквивалентна (полный OCR, усечение запрещено).
5. Grep-проверка: `grep -n "20000\|10 страниц" prompts/file-executor-*-apply.md` — пусто.

Критерий завершения: единая формулировка «полный OCR из {{work_dir}}/ocr/<имя>.txt» во всех apply-промптах.

### Ф3 — Plan-фазы (intake, add-evidence, add-opponent)

Шаги:
1. `prompts/file-executor-intake-plan.md:46`: заменить «первые 20000 символов» на указание пути к полному OCR-артефакту (см. Contracts п.5).
2. `prompts/file-executor-add-evidence-plan.md:38`: то же (п.6).
3. `prompts/file-executor-add-opponent-plan.md:39`: то же (п.7).
4. Проверить, что plan-фазы передают apply-фазе ссылку на `{{work_dir}}/ocr/<имя>.txt`, а не «первые 20000 символов».
5. Grep-проверка: `grep -n "20000\|первые 10" prompts/file-executor-*-plan.md` — пусто.

Критерий завершения: plan-фазы не требуют фиксации «первых N символов», а ссылаются на полный OCR-артефакт.

### Ф4 — update-index

Замечание про жизненный цикл временных артефактов. Скилл `update-index` не использует placeholder `{{work_dir}}` (см. `skills/update-index/SKILL.md:45–52`, `prompts/README.md:41–44`) и не имеет lifecycle-контракта temp-dir. В рамках этого ТЗ контракт скилла и placeholder-схема не расширяются: полнотекстовый OCR-артефакт создаётся и удаляется **внутри самого apply-шага** в self-contained временной директории (`mktemp -d`), без нового placeholder и без постоянных побочных артефактов.

Шаги:
1. `prompts/file-executor-update-index.md`, режим A, шаг 2 (строки 23–25): заменить вызов CLI с несуществующих флагов `--file/--output` на реальный CLI (Contracts п.8):
   - Создать временную директорию: `TMP=$(mktemp -d -t vassal-reindex-XXXXXX)`.
   - Вызвать: `python3 [PLUGIN_ROOT]/scripts/extract_text.py "путь_к_файлу" --output-dir "$TMP"`.
   - Скрипт (`scripts/extract_text.py:215–239`) принимает позиционный путь к файлу и при `--output-dir` сам записывает полный извлечённый текст в `$TMP/<stem>.txt`.
   - Зафиксировать `extraction_method`, `confidence` и путь `$TMP/<stem>.txt` для шага формирования тела зеркала.
   - После формирования тела зеркала — `rm -rf "$TMP"` (обязательный cleanup в том же шаге).
2. `prompts/file-executor-update-index.md:26` (режим A, тело зеркала): заменить формулировку на полнотекстовую и явно указать, что тело берётся целиком из файла `$TMP/<stem>.txt`, созданного шагом 2 (Contracts п.9). После записи зеркала `$TMP` удаляется.
3. `prompts/file-executor-update-index.md`, режим C, шаг 2 (строки 39–40):
   - (а) Привести вызов CLI к реальной сигнатуре с обязательным позиционным путём (берётся из поля `file` записи `.vassal/index.yaml`) и `--output-dir "$TMP"` (где `TMP=$(mktemp -d -t vassal-reindex-XXXXXX)` создаётся в начале шага).
   - (б) Заменить формулировку тела зеркала на полный текст из только что созданного `$TMP/<stem>.txt` (Contracts п.10).
   - (в) В конце шага — `rm -rf "$TMP"`.
4. Убедиться, что оба сценария (режим A — новый документ, режим C — перегенерация при `mirror_stale`) используют одинаковую цепочку: `mktemp -d` → `extract_text.py <file> --output-dir $TMP` → чтение `$TMP/<stem>.txt` целиком → запись в тело зеркала → `rm -rf $TMP`.
5. Инвариант контракта скилла: в `skills/update-index/SKILL.md` и `prompts/README.md` placeholder-карта **не меняется** — никакого нового `{{work_dir}}` для update-index не появляется. Это явно отмечается в логе изменений Ф4.
6. Grep-проверки по файлу:
   - `grep -n "20000" prompts/file-executor-update-index.md` — пусто.
   - `grep -nE "\-\-file|\-\-output[^\-]" prompts/file-executor-update-index.md` — пусто (никаких несуществующих флагов).
   - `grep -n "output-dir" prompts/file-executor-update-index.md` — ровно два совпадения (режимы A и C).
   - `grep -n "{{work_dir}}" prompts/file-executor-update-index.md` — пусто (placeholder в update-index не вводится).
   - `grep -nE "mktemp -d|rm -rf \"\$TMP\"" prompts/file-executor-update-index.md` — по два совпадения каждого (режимы A и C), что подтверждает симметричный lifecycle temp-dir.

Критерий завершения: update-index использует полнотекстовую политику в обоих сценариях; OCR-артефакт создаётся и удаляется внутри apply-шага через `mktemp -d`/`rm -rf` без расширения placeholder-контракта скилла; вызовы `extract_text.py` соответствуют реальному CLI.

### Ф5 — Сверка ARCHITECTURE.md, tests/, scripts/ и финальная контрактная проверка

Шаги:
1. `ARCHITECTURE.md`: выполнить grep `grep -nE "(20000|10 страниц|50 страниц|первых? 10)" ARCHITECTURE.md`. Предварительно таких совпадений нет. Если всплывут — заменить по тем же правилам.
2. `tests/smoke/*.sh`: grep то же выражение. Если совпадений нет — зафиксировать в отчёте; если есть — привести к новому контракту.
3. `scripts/extract_text.py`: проверить чтением, что скрипт пишет полный текст в `work_dir/ocr/<имя>.txt`. Если пишет — изменений не требуется. Если вдруг есть ограничение — эскалировать (это выходит за рамки ТЗ: «не менять Python, не добавлять зависимости»; в таком случае зафиксировать как отложенный риск).
4. Финальный контрактный grep по всему репозиторию:
   ```
   grep -rn -E "(20000|первые 10 страниц|первых 10 страниц|>50 страниц|страниц\s*/\s*20000|10 страниц\s*/)" prompts/ shared/ ARCHITECTURE.md tests/ scripts/ skills/ commands/
   ```
   Результат должен быть пустым (допустимы упоминания «страниц» / «символов» в нейтральных контекстах — поле frontmatter `pages`, описание качества OCR и т. п., но не как правило усечения зеркала).
5. Статусы всех фаз перевести в `done`, статус плана — в `done`.

Критерий завершения: во всём репозитории не осталось контрактных упоминаний усечения зеркала; ARCHITECTURE.md, smoke-тесты и скрипты согласованы с новым контрактом.
