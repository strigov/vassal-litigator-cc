#!/usr/bin/env bash

set -euo pipefail

print_usage() {
    cat <<'EOF'
USAGE: bash tests/smoke/test-update-index.sh /path/to/vassal-litigator-cc

Запускать из директории внутри /tmp/.
Скрипт готовит smoke-окружение и выводит шаги для ручной проверки update-index
в режимах добавления нового файла и пересоздания устаревшего зеркала.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    print_usage
    exit 0
fi

PLUGIN_ROOT="${1:-}"
if [[ -z "$PLUGIN_ROOT" ]]; then
    print_usage
    exit 1
fi

case "$PWD" in
    /tmp|/tmp/*) ;;
    *)
        echo "WARNING: smoke-скрипт можно запускать только из /tmp/. Текущий CWD: $PWD"
        exit 1
        ;;
esac

if [[ ! -d "$PLUGIN_ROOT" ]]; then
    echo "ERROR: PLUGIN_ROOT не существует: $PLUGIN_ROOT"
    exit 1
fi

if [[ ! -d "$PLUGIN_ROOT/tests/fixtures/dummy-case" ]]; then
    echo "ERROR: не найдена фикстура $PLUGIN_ROOT/tests/fixtures/dummy-case"
    exit 1
fi

source "$PLUGIN_ROOT/tests/smoke/_fulltext_common.sh"

SMOKE_CASE="/tmp/smoke-vassal-update-index-$(date +%s)"
PAYLOAD_DIR="$SMOKE_CASE/.smoke-payloads"

mkdir -p "$SMOKE_CASE" "$PAYLOAD_DIR"
cp -R "$PLUGIN_ROOT/tests/fixtures/dummy-case/Входящие документы" "$SMOKE_CASE/"
cp "$PLUGIN_ROOT/tests/fixtures/dummy-case/case-initial.yaml" "$SMOKE_CASE/.vassal-case-initial.yaml"
generate_large_fixture_pdf \
    "$PLUGIN_ROOT/tests/fixtures/dummy-case/_sources/большой-договор.txt" \
    "$PAYLOAD_DIR/большой-договор-update-index.pdf"
write_fulltext_helper "$SMOKE_CASE" "$PLUGIN_ROOT"

cat <<EOF
=== SMOKE: update-index ===

РАБОЧАЯ ДИРЕКТОРИЯ:
$SMOKE_CASE

ШАГИ:
1. Перейди в smoke-директорию:
   cd "$SMOKE_CASE"
2. Запусти Claude Code в этой папке.
3. Выполни /vassal-litigator:init-case и дождись завершения базового intake.
4. Подготовь новый файл для режима добавления:
   cp "$PAYLOAD_DIR/большой-договор-update-index.pdf" "$SMOKE_CASE/Материалы от клиента/2026-04-22 Большой документ для update-index.pdf"
5. Подготовь устаревшее зеркало для режима пересоздания:
   export SMOKE_CASE="$SMOKE_CASE"; export PLUGIN_ROOT="$PLUGIN_ROOT"
   source "\$SMOKE_CASE/.smoke-fulltext.sh"
   export STALE_ID=\$(python3 - "\$SMOKE_CASE/.vassal/index.yaml" <<'PY'
import pathlib
import sys
import yaml

idx = pathlib.Path(sys.argv[1])
data = yaml.safe_load(idx.read_text(encoding="utf-8"))
for entry in data.get("documents", []):
    if entry.get("source") == "client":
        print(entry["id"])
        break
PY
)
   export STALE_FILE=\$(source_of_id "\$STALE_ID")
   cp "$PAYLOAD_DIR/большой-договор-update-index.pdf" "$SMOKE_CASE/\$STALE_FILE"
   touch -m "$SMOKE_CASE/\$STALE_FILE"
6. Выполни: /vassal-litigator:update-index
7. Проверь preview:
   - новый файл `2026-04-22 Большой документ для update-index.pdf` попал в режим добавления
   - `\$STALE_ID` попал в список устаревших зеркал
8. Подтверди apply.

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
- новый файл появился в `.vassal/index.yaml` с новым doc-ID и зеркалом
- для `\$STALE_ID` зеркало пересоздано и `mirror_stale: false`
- оба зеркала содержат полный текст без усечения
- `.vassal/codex-logs/` содержит лог update-index

ПРОВЕРКА:
- export SMOKE_CASE="$SMOKE_CASE"; export PLUGIN_ROOT="$PLUGIN_ROOT"
- source "\$SMOKE_CASE/.smoke-fulltext.sh"
- python3 -c "import os, pathlib, yaml; p=pathlib.Path('\$SMOKE_CASE/.vassal/index.yaml'); d=yaml.safe_load(p.read_text(encoding='utf-8')); docs=d.get('documents', []); hits=[x for x in docs if x.get('file', '').endswith('2026-04-22 Большой документ для update-index.pdf')]; stale=next((x for x in docs if x.get('id') == os.environ.get('STALE_ID')), None); print('new_hits=', len(hits)); print('new_ids=', [x.get('id') for x in hits]); print('stale_found=', bool(stale)); print('stale_mirror_stale=', None if stale is None else stale.get('mirror_stale'))"
- assert_mirror_full "2026-04-22 Большой документ для update-index.pdf"
- assert_mirror_full --id "\$STALE_ID"
- find "\$SMOKE_CASE/.vassal/codex-logs" -name '*update-index*.md' -type f

ОЧИСТКА:
rm -rf "$SMOKE_CASE"
EOF
