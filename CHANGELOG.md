## [vassal-litigator-cc] v1.0.0 -- 2026-04-22

Первый релиз cc-edition — форк `vassal-litigator` v0.5.4 (Cowork edition), адаптированный под нативную установку в Claude Code через маркетплейс `strigov-cc-plugins`.

### Сохранено

- Контракт файловых скиллов `plan → review → (revise)? → apply → verify` (intake, add-evidence, add-opponent, update-index).
- Диспатч Codex CLI из Claude-main через `codex-companion.mjs` — роли `file-executor-*-plan` (medium, whitelist writes), `file-executor-*-apply` (medium, `--write`), `timeline-builder` (high, `--write`), `analytical-reviewer` (xhigh, read-only), `imagegen-visualizer` (medium).
- Хронологическая раскладка `Материалы от клиента/` (одиночные файлы, комплекты `ГГГГ-ММ-ДД Отправитель Описание/` с `Приложение NN — ...`, сироты `Без даты — <Тема>/`).
- Распаковка архивов (`zip`, `rar`, `7z`, `tar`), конверсия скриншотов в PDF через `scripts/image_to_pdf.py`, OCR через `scripts/extract_text.py`.
- Контрольное ревью Codex xhigh в 6 аналитических скиллах (`legal-review`, `build-position`, `prepare-hearing`, `analyze-hearing`, `draft-judgment`, `appeal`, `cassation`).
- Формат индекса `.vassal/index.yaml`, case.yaml, зеркал, схема timeline.

### Изменено относительно v0.5.4

- **Удаление обработанных файлов.** Вместо Cowork-паттерна «копия в `На удаление/` + обнуление источника через `: >`» apply-фаза использует обычный `rm`. Оригиналы остаются в `.vassal/raw/<batch>/` (неизменяемые исходники). Папка `На удаление/` из скелета дела удалена.
- **Упрощён резолвер `$CODEX_COMPANION`**: было 5-tier (env → канонический `$HOME/...` → remote-plugin siblings в `/sessions/<name>/mnt/.remote-plugins/` для Cowork → `installed_plugins.json` + широкий скан → вопрос юристу); стало 3-tier (env → канонический `$HOME/...` → `installed_plugins.json`). Все Cowork-specific пробы (`/sessions/*/mnt/.remote-plugins/*`, переменная-хинт `VASSAL_PLUGIN_ROOT_HINT`) удалены.
- **Очистка плана и work-dir.** `cp plan → .vassal/codex-logs/ + rm plan` вместо `cp + : >`; `rm -rf .vassal/work/<skill>-<timestamp>/` вместо построчного `: >` каждого файла.
- **Установка.** README описывает установку через `/plugin marketplace add strigov/strigov-cc-plugins` + `/plugin install vassal-litigator-cc@strigov-cc-plugins`.
- **Обновлены упоминания.** Во всех текстах «Cowork»/«сессия Cowork»/«Claude Cowork» заменены на «Claude Code»/«машина»/«сессия».

### Удалено

- Папка `На удаление/` из скелета init-case и из whitelist apply-промптов.
- Tier 3 (remote-plugin siblings) и Tier 4 (широкий sandbox-скан) из резолвера `$CODEX_COMPANION`.
- Переменная `VASSAL_PLUGIN_ROOT_HINT` (использовалась только в Cowork).
- Cowork-специфичные советы про Python-интерпретатор sandbox в `skills/codex-invocation/SKILL.md`.
- Историческая директория `docs/` (planning artefacts от v0.5.x разработки Cowork edition).

### Происхождение

История версий до v0.5.4 см. в апстрим-репозитории `vassal-litigator`. В `vassal-litigator-cc` история плагина начинается с v1.0.0 как единого initial release.
