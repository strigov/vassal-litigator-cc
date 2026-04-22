#!/usr/bin/env bash

set -euo pipefail

print_usage() {
    cat <<'EOF'
USAGE: bash tests/smoke/test-intake.sh /path/to/vassal-litigator-cc

Запускать из директории внутри /tmp/.
Скрипт готовит smoke-окружение и выводит шаги для ручной проверки intake
по контракту v1.0.0: plan → review → apply → verify.
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

SMOKE_CASE="/tmp/smoke-vassal-intake-$(date +%s)"

mkdir -p "$SMOKE_CASE"
cp -R "$PLUGIN_ROOT/tests/fixtures/dummy-case/Входящие документы" "$SMOKE_CASE/"
cp "$PLUGIN_ROOT/tests/fixtures/dummy-case/case-initial.yaml" "$SMOKE_CASE/.vassal-case-initial.yaml"

cat <<EOF
=== SMOKE: intake (v1.0.0 — plan → review → apply → verify) ===

РАБОЧАЯ ДИРЕКТОРИЯ:
$SMOKE_CASE

ПРЕДУСЛОВИЯ:
- openai-codex установлен, codex login выполнен
- setup.sh прогонится автоматически внутри init-case (либо один раз запусти вручную)

ШАГИ:
1. Перейди в smoke-директорию:
   cd "$SMOKE_CASE"
2. Запусти Claude Code в этой папке.
3. Выполни: /vassal-litigator:init-case
4. Заполни карточку (если init-case запросит):
   - Клиент: ООО "Ромашка" (истец)
   - Оппонент: ООО "Лютик" (ответчик)
   - Дело: А41-1234/2025
   - Суд: Арбитражный суд Московской области
   - Суть: взыскание задолженности по договору поставки
5. init-case сам запустит intake на файлах из "Входящие документы/":
   - договор.pdf, претензия.pdf, скан.jpg, архив.zip (внутри: акт.pdf, платёжка.pdf)
6. Фаза plan: Codex medium без --write. Дождись, пока Claude покажет markdown-план.
7. Проверь план:
   - scan: таблица файлов с новыми именами, целевыми папками, doc-ID
   - скан.jpg помечен для конверсии в PDF
   - архив.zip помечен как "archive_failed: false", его содержимое (акт.pdf, платёжка.pdf)
     попало в таблицу как отдельные файлы с origin.archive_src = "архив"
   - секции "Комплекты", "Сироты без даты", "Конверсии изображений → PDF",
     "Не обработанные архивы", "Проверки плана"
8. Если план ок — подтверди ("apply"/"go"/"да"). Если нет — дай правки, дождись revise-плана.
9. Фаза apply: Codex medium --write. Дождись завершения.

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
- .vassal/raw/intake-ГГГГ-ММ-ДД/ содержит копии всех 4 исходников + содержимое архива:
  договор.pdf, претензия.pdf, скан.jpg, архив.zip, архив__акт.pdf, архив__платёжка.pdf
- .vassal/mirrors/ содержит doc-001.md ... doc-NNN.md (по числу проиндексированных)
- .vassal/index.yaml валиден, source: client, у каждой записи заполнены
  id/title/date/file/mirror/origin/extraction_method/confidence/mirror_stale
- Комплекты (если Codex их выделил) имеют bundle_id, role_in_bundle, parent_id, attachment_order
- Материалы от клиента/ содержит хронологическую раскладку:
  * одиночные файлы — без папки (например "2025-06-01 Ромашка Договор поставки.pdf")
  * комплекты — папки вида "ГГГГ-ММ-ДД Отправитель Описание/" с "Приложение NN — ...расш"
  * сироты (если есть) — в "Без даты — <Тема>/"
- Скриншот скан.jpg превращён в PDF; .jpg-оригинал остался ТОЛЬКО в .vassal/raw/
- архив.zip НЕ попал в "Материалы от клиента/" и НЕ индексируется в index.yaml
  (в raw остаётся, в index.yaml есть только его содержимое)
- Входящие документы/ пустая (все 4 файла удалены через rm после архивации в .vassal/raw/)
- .vassal/plans/intake-*.md удалён после архивации
- .vassal/codex-logs/ГГГГ-ММ-ДД-ЧЧмм-intake-plan.md — архивная копия плана
- .vassal/work/intake-*/ удалена целиком
- .vassal/history.md содержит две строки: "intake plan: ..." и "intake apply: ..."

ПРОВЕРКА:
- ls -la "\$SMOKE_CASE/Входящие документы/"                      # должна быть пустой
- find "\$SMOKE_CASE/.vassal/raw" -type f | wc -l                # >= 6 (4 исходника + 2 из архива)
- find "\$SMOKE_CASE/.vassal/mirrors" -name 'doc-*.md' | wc -l    # == число записей в index.yaml
- find "\$SMOKE_CASE/Материалы от клиента" -type f              # хронологическая раскладка
- find "\$SMOKE_CASE/.vassal/codex-logs" -name '*-intake-plan.md' -type f   # архив плана
- ls "\$SMOKE_CASE/.vassal/plans/" 2>/dev/null; ls "\$SMOKE_CASE/.vassal/work/" 2>/dev/null  # пусто (всё удалено)
- python3 -c "import yaml, pathlib; p=pathlib.Path('\$SMOKE_CASE/.vassal/index.yaml'); d=yaml.safe_load(p.read_text(encoding='utf-8')); docs=d.get('documents', []); print('docs=', len(docs), 'next_id=', d.get('next_id')); print([d2.get('source') for d2 in docs])"
- grep -E '^(### )?.*intake (plan|apply):' "\$SMOKE_CASE/.vassal/history.md"

СВЕРКА С ФИКСТУРОЙ:
- cat "\$PLUGIN_ROOT/tests/fixtures/dummy-case/expected/index-after-intake.yaml"
- cat "\$PLUGIN_ROOT/tests/fixtures/dummy-case/expected/history-entry.md"

ОЧИСТКА:
rm -rf "$SMOKE_CASE"
EOF
