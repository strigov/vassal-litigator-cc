#!/usr/bin/env bash

set -euo pipefail

print_usage() {
    cat <<'EOF'
USAGE: bash tests/smoke/test-add-evidence.sh /path/to/vassal-litigator-cc

Запускать из директории внутри /tmp/.
Скрипт готовит smoke-окружение и выводит шаги для ручной проверки add-evidence
с полнотекстовой проверкой md-зеркала.
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

SMOKE_CASE="/tmp/smoke-vassal-add-evidence-$(date +%s)"
PAYLOAD_DIR="$SMOKE_CASE/.smoke-payloads"

mkdir -p "$SMOKE_CASE" "$PAYLOAD_DIR"
cp -R "$PLUGIN_ROOT/tests/fixtures/dummy-case/Входящие документы" "$SMOKE_CASE/"
cp "$PLUGIN_ROOT/tests/fixtures/dummy-case/case-initial.yaml" "$SMOKE_CASE/.vassal-case-initial.yaml"
generate_large_fixture_pdf \
    "$PLUGIN_ROOT/tests/fixtures/dummy-case/_sources/большой-договор.txt" \
    "$PAYLOAD_DIR/большой-договор-evidence.pdf"
write_fulltext_helper "$SMOKE_CASE" "$PLUGIN_ROOT"

cat <<EOF
=== SMOKE: add-evidence ===

РАБОЧАЯ ДИРЕКТОРИЯ:
$SMOKE_CASE

ШАГИ:
1. Перейди в smoke-директорию:
   cd "$SMOKE_CASE"
2. Запусти Claude Code в этой папке.
3. Выполни /vassal-litigator:init-case и дождись завершения базового intake на стартовой fixture-поставке.
4. Добавь новый полнотекстовый документ для догрузки:
   cp "$PAYLOAD_DIR/большой-договор-evidence.pdf" "$SMOKE_CASE/Входящие документы/большой-договор-evidence.pdf"
5. Выполни: /vassal-litigator:add-evidence
6. Проверь preview:
   - в плане есть новый документ "большой-договор-evidence.pdf"
   - для него назначен новый doc-ID
   - нет попытки перепривязать уже существующие документы
7. Подтверди apply.

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
 - создан raw-батч `.vassal/raw/evidence-ГГГГ-ММ-ДД/` с копией `большой-договор-evidence.pdf`
- в `.vassal/index.yaml` появилась новая запись с `source: client` и `origin.batch: evidence-...`
- для новой записи создано `.vassal/mirrors/doc-NNN.md` с полным текстом
- `.vassal/codex-logs/` содержит архив плана add-evidence
- `.vassal/plans/add-evidence-*.md` и `.vassal/work/add-evidence-*/` удалены
- `Входящие документы/` снова пустая

ПРОВЕРКА:
- export SMOKE_CASE="$SMOKE_CASE"; export PLUGIN_ROOT="$PLUGIN_ROOT"
- source "\$SMOKE_CASE/.smoke-fulltext.sh"
- find "\$SMOKE_CASE/.vassal/raw" -path '*evidence-*' -type f
- python3 -c "import pathlib, yaml; p=pathlib.Path('\$SMOKE_CASE/.vassal/index.yaml'); d=yaml.safe_load(p.read_text(encoding='utf-8')); docs=d.get('documents', []); hits=[x for x in docs if (x.get('origin', {}) or {}).get('name') == 'большой-договор-evidence.pdf']; print('hits=', len(hits)); print('sources=', [x.get('source') for x in hits]); print('batches=', [(x.get('origin', {}) or {}).get('batch') for x in hits])"
- assert_mirror_full "большой-договор-evidence.pdf"
- find "\$SMOKE_CASE/.vassal/codex-logs" -name '*add-evidence-plan.md' -type f
- ls "\$SMOKE_CASE/.vassal/plans/" 2>/dev/null; ls "\$SMOKE_CASE/.vassal/work/" 2>/dev/null

ОЧИСТКА:
rm -rf "$SMOKE_CASE"
EOF
