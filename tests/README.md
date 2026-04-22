# Smoke-тесты vassal-litigator

Smoke-тесты — это руководства для ручной проверки скиллов. Они не запускают Claude/Codex автоматически: скрипты подготавливают тестовое окружение и выводят пошаговые инструкции.

## Предварительные требования

- Установлен плагин `vassal-litigator-cc` в Claude Code
- Установлен `openai-codex` companion и выполнен `codex login`
  (при отсутствии Codex скиллы `intake`/`add-evidence`/`add-opponent` блокируются — это by design)
- Python `>= 3.9`
- Для ручных проверок `catalog` полезны пакеты `yaml` и `openpyxl`
- Smoke-скрипты запускаются только из директории внутри `/tmp/`

## Контракт файловых скиллов (v1.0.0)

`intake`, `add-evidence`, `add-opponent` работают по контракту `plan → review → (revise)? → apply → verify`:

- **plan** — Codex medium без `--write`, читает исходники, пишет markdown-план в `.vassal/plans/<skill>-<timestamp>.md`, добавляет строку в `.vassal/history.md`
- **review** — Сюзерен ревьюит план (секции «Комплекты», «Сироты без даты», «Конверсии изображений → PDF», «Не обработанные архивы», «Проверки плана»)
- **revise** (опц.) — при правках Claude собирает свод и запускает revise plan у Codex
- **apply** — Codex medium `--write`, разносит файлы, строит раскладку, индексирует, чистит `Входящие документы/` через `rm`, удаляет `.vassal/plans/<plan>.md` после архивации в `.vassal/codex-logs/` и `.vassal/work/<skill>-*/` через `rm -rf`
- **verify** — Claude проверяет отчёт Codex и инварианты

Smoke-тест `intake` охватывает:
- архивацию плана в `.vassal/codex-logs/ГГГГ-ММ-ДД-ЧЧмм-intake-plan.md`
- удаление `.vassal/plans/intake-*.md` после архивации
- удаление рабочей области `.vassal/work/intake-*/`
- хронологическую раскладку «Материалы от клиента/» (одиночные файлы без папки, комплекты в папках `ГГГГ-ММ-ДД Отправитель Описание/`, сироты в `Без даты — <Тема>/`)
- распаковку архивов (`архив.zip` не в индексе, его содержимое проиндексировано с `origin.archive_src`)
- конверсию изображений в PDF (`скан.jpg` → PDF, оригинал только в `.vassal/raw/`)

## Структура

```text
tests/
├── fixtures/
│   └── dummy-case/
│       ├── Входящие документы/
│       │   ├── договор.pdf
│       │   ├── претензия.pdf
│       │   ├── скан.jpg
│       │   └── архив.zip
│       ├── case-initial.yaml
│       └── expected/
│           ├── index-after-intake.yaml   # _check-контракт структуры
│           └── history-entry.md          # ожидаемые строки в history.md
└── smoke/
    ├── test-intake.sh
    ├── test-catalog.sh
    ├── test-timeline.sh
    └── test-analytical-review.sh
```

Новые подпапки в скелете дела, которые создаёт `init-case` (v1.0.0):

- `.vassal/plans/` — рабочие markdown-планы Codex (удаляются после apply, с архивом в `codex-logs/`)
- `.vassal/work/<skill>-<timestamp>/` — рабочие артефакты Codex (черновики, промежуточные расчёты); удаляются после apply
- `.vassal/codex-logs/` — архивные копии планов и summary Codex-сессий

## Запуск

```bash
cd /tmp

PLUGIN_ROOT=/path/to/vassal-litigator-cc

bash "$PLUGIN_ROOT/tests/smoke/test-intake.sh" "$PLUGIN_ROOT"
bash "$PLUGIN_ROOT/tests/smoke/test-catalog.sh" "$PLUGIN_ROOT"
bash "$PLUGIN_ROOT/tests/smoke/test-timeline.sh" "$PLUGIN_ROOT"
bash "$PLUGIN_ROOT/tests/smoke/test-analytical-review.sh" "$PLUGIN_ROOT"
```

Каждый скрипт печатает блоки `ШАГИ`, `ОЖИДАЕМЫЙ РЕЗУЛЬТАТ`, `ПРОВЕРКА`, `ОЧИСТКА`. Выполняй шаги вручную в Claude Code, запущенном в указанной smoke-директории.

## Тестовое дело

Дело: `А41-1234/2025`  
Стороны: `ООО "Ромашка"` (истец) vs `ООО "Лютик"` (ответчик)  
Суд: `Арбитражный суд Московской области`  
Суть: `Взыскание задолженности по договору поставки №47 от 2025-06-01`

Документы в fixture:

- `договор.pdf` — stub-PDF договора поставки
- `претензия.pdf` — stub-PDF претензии
- `скан.jpg` — stub-JPEG для OCR-проверки (apply-фаза конвертирует в PDF)
- `архив.zip` — архив с `акт.pdf` и `платёжка.pdf` (apply-фаза распаковывает, содержимое индексирует с `origin.archive_src = "архив"`)

## Сверка ожидаемого результата

`expected/index-after-intake.yaml` — не эталонный index, а **контракт на структуру**: список инвариантов (`_check:`), которые проверяются в smoke-скрипте:

- `version: 2`, `next_id >= 6`
- `source: client`, `origin.batch` начинается с `intake-`
- `архив.zip` НЕ присутствует в `documents` (только его содержимое)
- `скан.*` имеет `file`, оканчивающийся на `.pdf`
- для `role_in_bundle == "attachment"` обязательны `parent_id` и `attachment_order`
- для `needs_manual_review == true` путь файла начинается с `Материалы от клиента/Без даты — `

`expected/history-entry.md` — описание трёх строк, которые должны появиться в `.vassal/history.md` после `init-case` (стартовая init-case + intake plan + intake apply + финальная init-case).

## Безопасность

Скрипты работают только с временными каталогами вида `/tmp/smoke-vassal-*/` и откажутся запускаться, если текущая рабочая директория не находится внутри `/tmp/`.
