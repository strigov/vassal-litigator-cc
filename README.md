> **ВАЖНО: Конфиденциальность.** Плагин отправляет материалы дела (тексты документов, зеркала, метаданные) в OpenAI через Codex CLI для выполнения файлового пайплайна, построения таймлайна, визуализаций и контрольного ревью аналитики. Устанавливая плагин, вы подтверждаете согласие на такую передачу. Если это недопустимо для вашей юрисдикции или клиентского договора — не устанавливайте плагин.

# vassal-litigator-cc

Вассал — плагин для **Claude Code**, помогающий юристу вести судебные дела от первичного приёма материалов клиента до кассационной жалобы. Форк [vassal-litigator](https://github.com/strigov/vassal-litigator) v0.5.4, адаптированный под Claude Code (без Cowork-специфики).

## Возможности

**Приём и систематизация документов** — OCR сканов и фотографий, переименование файлов по содержимому, создание текстовых зеркал, автоматическое ведение реестра документов дела.

**Правовой анализ** — квалификация спора, проверка сроков исковой давности, определение подсудности, оценка полноты доказательственной базы, формирование правовой позиции с оценкой рисков.

**Подготовка к заседаниям** — стресс-тест позиции (red team / blue team), генерация процессуальных документов (отзывы, ходатайства, пояснения).

**Анализ заседаний** — разбор транскрипций: речевые паттерны судьи, уклончивые ответы оппонента, рекомендации по тактике.

**Обжалование** — подготовка апелляционных и кассационных жалоб с систематическим поиском оснований по АПК/ГПК РФ, проект судебного решения с учётом стиля конкретного судьи.

## Скиллы (15)

| Фаза | Скилл | Описание |
|------|-------|----------|
| Фундамент | `intake` | Приём и обработка материалов клиента |
| | `catalog` | Генерация xlsx-таблицы документов |
| | `update-index` | Верификация и синхронизация реестра |
| | `codex-invocation` | Единый контракт вызова Codex CLI (читается другими скиллами) |
| | `timeline` | Построение юридической хронологии дела (Codex high) |
| | `visualize` | Sidecar-визуализации через `image_gen` (вызывается из других скиллов) |
| Анализ | `legal-review` | Комплексный правовой анализ |
| | `build-position` | Формирование правовой позиции |
| Ведение дела | `add-evidence` | Приём доп. доказательств от клиента |
| | `add-opponent` | Приём и анализ документов оппонента |
| | `prepare-hearing` | Подготовка к заседанию |
| | `analyze-hearing` | Анализ транскрипции заседания |
| Обжалование | `draft-judgment` | Проект судебного решения |
| | `appeal` | Апелляционная жалоба |
| | `cassation` | Кассационная жалоба |

## Требования

- [Claude Code](https://claude.com/claude-code) (CLI, desktop или IDE-расширение)
- Плагин [`openai-codex`](https://github.com/openai/codex-plugin-cc) ≥ 1.0.3
- Выполненный `codex login`
- Для визуализаций: `codex features enable image_generation`
- Локальные зависимости (устанавливаются скриптом): `tesseract-ocr`, Python-пакеты `python-docx`, `openpyxl`, `pymupdf`

Без `openai-codex` плагин работает в деградированном режиме: Claude Code выполняет файловые операции самостоятельно, но без таймлайна, визуализаций и контрольного ревью.

## Установка

### 1. Добавьте маркетплейс и установите плагин

В Claude Code:

```
/plugin marketplace add strigov/strigov-cc-plugins
/plugin install vassal-litigator-cc@strigov-cc-plugins
```

Либо через settings (project или user):

```json
{
  "extraKnownMarketplaces": {
    "strigov-cc": {
      "source": { "source": "github", "repo": "strigov/strigov-cc-plugins" }
    }
  },
  "enabledPlugins": {
    "vassal-litigator-cc@strigov-cc": true
  }
}
```

### 2. Установите зависимости

Из папки установленного плагина (Claude Code: `~/.claude/plugins/cache/strigov-cc-plugins/plugins/vassal-litigator-cc/`):

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Скрипт установит: `tesseract-ocr` (для OCR), Python-пакеты `python-docx`, `openpyxl`, `pymupdf`, а также `ocrmypdf` и архиваторы (`unzip`, `7z`, `tar`, `unrar`).

Можно также вызвать `setup.sh` автоматически при первом запуске `init-case` — скилл `intake` это делает сам.

### 3. Установите плагин openai-codex и войдите в аккаунт

```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
```

Затем однократно:

```bash
codex login
codex features enable image_generation   # для визуализаций, опционально
```

## Быстрый старт

1. Создайте папку будущего дела, положите туда «сырые» материалы клиента (pdf, docx, сканы, zip — всё россыпью в корне).
2. Откройте эту папку в Claude Code и выполните:
   ```
   /vassal-litigator-cc:init-case
   ```
3. Плагин сам создаст скелет, сгребёт файлы во «Входящие документы/», запустит intake (OCR + переименование + md-зеркала + раскладка) и опросит вас только по недостающим полям карточки дела.
4. Далее по ситуации:
   - `/vassal-litigator-cc:catalog` — xlsx-таблица документов для приобщения
   - `/vassal-litigator-cc:legal-review` — правовой анализ
   - `/vassal-litigator-cc:build-position` — правовая позиция с оценкой рисков
   - `/vassal-litigator-cc:prepare-hearing` — подготовка к заседанию
   - `/vassal-litigator-cc:timeline` — хронология дела
   - `/vassal-litigator-cc:add-evidence` / `add-opponent` — добавление новых материалов по ходу дела
   - `/vassal-litigator-cc:analyze-hearing` — разбор транскрипции
   - `/vassal-litigator-cc:appeal` / `cassation` — жалобы

## Маршрутизация моделей

| Задача | Модель |
|--------|--------|
| Файловые операции (OCR, зеркала, индексация) | Codex medium (`--write`) |
| Таймлайн | Codex high (`--write`) |
| Визуализации sidecar (PNG) | Codex medium → gpt-image-1.5 |
| Контрольное ревью аналитики | Codex xhigh (read-only) |
| Оркестрация, preview, git | Sonnet (Claude Code) |
| Правовой анализ, позиции, документы | Opus (Claude Code) |

## Структура плагина

```
vassal-litigator-cc/
├── .claude-plugin/
│   └── plugin.json          # Манифест плагина
├── commands/                 # Slash-команды
├── skills/                   # Скиллы (15)
├── shared/                   # Общие схемы и конвенции (conventions.md, case-schema.yaml, index-schema.yaml, mirror-template.md)
├── scripts/                  # Утилиты (setup.sh, extract_text.py, generate_table.py, image_to_pdf.py)
├── prompts/                  # Шаблоны промптов Codex CLI
├── tests/                    # Smoke-тесты (ручные, с инструкциями)
├── ARCHITECTURE.md           # Архитектура
├── CHANGELOG.md
└── README.md
```

## Отличия от vassal-litigator (Cowork edition)

- Установка через `/plugin marketplace add` + `/plugin install`, а не через загрузку zip в Cowork.
- Операция удаления файлов — нормальный `rm` (в Cowork не работал, там был workaround через папку «На удаление/» + обнуление исходника `: >`).
- Резолвер `$CODEX_COMPANION` упрощён с 5-tier до 3-tier fallback: env → `$HOME/.claude/plugins/cache/openai-codex/codex/<ver>/scripts/codex-companion.mjs` → парсинг `installed_plugins.json` → fail. Выкинуты Cowork-специфичные тиры `/sessions/<name>/mnt/.remote-plugins/...` и hint `VASSAL_PLUGIN_ROOT_HINT`.
- Бизнес-логика скиллов (`intake`, `timeline`, `legal-review`, `build-position` и т.д.), вся Codex-интеграция, prompts, schemas — **идентичны** vassal-litigator v0.5.4.

## Лицензия

GPL-3.0. См. [LICENSE](LICENSE).

## Автор

Ian Strigov ([@strigov](https://github.com/strigov))
