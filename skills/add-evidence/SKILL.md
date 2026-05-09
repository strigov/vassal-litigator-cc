---
name: add-evidence
description: >
  Приём дополнительных доказательств от клиента в **уже ведущееся** дело. Используй этот скилл,
  когда юрист говорит «вот дополнительные документы», «клиент прислал ещё файлы»,
  «добавь доказательства», «новые материалы от клиента», «приобщи к делу».
  НЕ используй для первичного приёма (это `intake`) и для документов оппонента (это `add-opponent`).
---

# add-evidence — Приём дополнительных доказательств

Скилл работает по контракту **plan → review → (revise) → apply → verify**. Всю черновую работу (чтение исходников, OCR, распаковка архивов, классификацию, встраивание в существующую хронологию) делает Codex medium; plan-фаза вызывает `scripts/prepare_intake_workdir.py` и работает с его JSON `files[]`. Claude-main промпты собирает и план показывает — **не читает** исходники клиента, не запускает OCR и не предлагает имена/doc-ID/bundle_id.

## Предусловия

- Дело инициализировано: `.vassal/case.yaml` существует.
- Intake уже выполнен (есть записи в `.vassal/index.yaml`). Если индекс пуст — предложи сначала `/vassal-litigator:intake`.
- Папка `Входящие документы/` существует и в ней хотя бы один новый файл.
- Зависимости установлены (`setup.sh` запущен в сессии).
- Codex companion доступен. Иначе — см. «Блокер при отсутствии Codex».

## Переменные сессии

- `plan_timestamp` = `ГГГГ-ММ-ДД-ЧЧмм`
- `batch_name` = `add-evidence-ГГГГ-ММ-ДД-ЧЧмм` (уникальный per-plan basename)
- `plan_path` = `.vassal/plans/add-evidence-<plan_timestamp>.md`
- `work_dir` = `.vassal/work/add-evidence-<plan_timestamp>/`
- `next_id_hint` = `next_id` из `.vassal/index.yaml`

Создай пустые `.vassal/plans/` и `.vassal/work/`, если их нет. Сам файл плана создаёт Codex plan-фаза.

## Фаза 1 — Plan (Codex medium)

1. Прочитай `skills/codex-invocation/SKILL.md`.
2. Собери промпт: `prompts/_preamble.md` + `prompts/file-executor-add-evidence-plan.md`. Переменные:
   - `role_id`: `file-executor-add-evidence-plan`
   - `task_name`: `add-evidence plan <batch_name>`
   - `case_root`, `plugin_root`
   - `batch_name`, `plan_path`, `work_dir`, `next_id_hint`
   - `revise_feedback`: пусто при первом запуске
   - `report_contract`: из `_preamble.md`
3. `grep -c "{{" <prompt>` → `0`.
4. Диспатч без `--write`: `task --background --effort medium "..."`.
5. Мониторь до `completed` по шаблону из `skills/codex-invocation/SKILL.md` с `sleep 25`.
6. Получи отчёт. Проверь наличие `PLAN_PATH`, `PLAN_YAML`, `WORK_DIR`, `FILES_PLANNED`, `BUNDLES_NEW`, `BUNDLES_ATTACHED`, `ORPHANS_PLANNED`, `FILES_SKIPPED`, файл `{{plan_path}}` непустой, рядом лежащий YAML существует, `plan["batch"] == <plan_basename>`, `work_dir == .vassal/work/<batch>`, `raw_dest == .vassal/raw/<batch>`, а в `{{work_dir}}/00-prep.json` есть JSON от `prepare_intake_workdir.py`.
7. `BLOCKED` / `NEEDS_CONTEXT` → покажи Сюзерену `CONCERNS`, спроси, что делать.

## Фаза 2 — Review Сюзереном

1. Прочитай `{{plan_path}}` целиком.
2. Покажи Сюзерену весь план как есть (markdown-таблицы, секции «Новые комплекты», «Присоединения к существующим», «Сироты», «Конверсии», «Не обработанные архивы», «Уже обработанные (пропуск)»). Сопроводительный комментарий 2-3 строки с числами допустим.
3. Особое внимание обрати Сюзерена на секцию «Присоединения к существующим комплектам»: там Codex решил доложить новые приложения в уже существующие физические папки. Это критичная точка ревью, ошибка здесь ломает ранее собранную раскладку.
4. Спроси: «Подтверждаешь? Или нужны правки?»
5. Варианты: подтверждение → Фаза 3; правки → Фаза 2b; отмена → остановиться.

### Фаза 2b — Revise

1. Собери промпт plan с заполненным `revise_feedback` (буквальный текст правок).
2. Те же `plan_path` и `work_dir` — Codex перезапишет план и при необходимости обновит рабочую область.
3. Вернись к Фазе 2.

## Фаза 3 — Apply (Codex medium `--write`)

1. Собери промпт: `prompts/_preamble.md` + `prompts/file-executor-add-evidence-apply.md`. Переменные:
   - `role_id`: `file-executor-add-evidence-apply`
   - `task_name`: `add-evidence apply <batch_name>`
   - `case_root`, `plugin_root`
   - `batch_name`, `plan_path`, `work_dir`, `plan_timestamp`
   - `report_contract`
2. `grep -c "{{" <prompt>` → `0`.
3. Диспатч: `task --background --write --effort medium "..."`.
4. Мониторь до завершения.
5. Получи отчёт.

## Фаза 4 — Verify

1. Прочитай отчёт Codex. Проверь:
   - статус `DONE` или `DONE_WITH_CONCERNS`
   - `FILES_INGESTED` совпадает с новыми (непропущенными) из плана
   - `BUNDLES_NEW` и `BUNDLES_ATTACHED` соответствуют разбору backup YAML в `.vassal/codex-logs/<plan_basename>.yaml`, а не `bundle_count` из stdout скрипта
   - `INDEX_VALIDATION` — YAML валиден
   - `PLAN_ARCHIVED` указывает реальный путь в `.vassal/codex-logs/`
   - `{{plan_path}}` и парный `.yaml` удалены из `.vassal/plans/`
   - в `.vassal/codex-logs/` есть `<plan_basename>.md` и `<plan_basename>.yaml`; `plan["batch"] == <plan_basename>`
2. Прочитай `.vassal/index.yaml`: новые записи имеют `source: client`, корректные `bundle_id`/`role_in_bundle`/`parent_id`.
   Для каждой новой записи проверь наличие `ocr_quality` и `ocr_quality_reason`; их пишет `apply_intake_plan.py` через `classify_ocr_quality.py`, а `needs_manual_review` должен соответствовать правилу `ocr_quality != "ok"`. В mirror frontmatter этих полей нет.
3. Если в `Входящие документы/` остались файлы из плана — аномалия, покажи Сюзерену.
4. Сохрани лог сессии `.vassal/codex-logs/<plan_timestamp>-add-evidence-session.md`: промпт plan + отчёт plan + промпт apply + отчёт apply.
5. Финальное резюме Сюзерену: `N новых записей, M новых комплектов, J присоединений, S сирот, K изображений → PDF, D пропущено. needs_manual_review: X`.

## Идемпотентность

План-фаза сама детектирует уже обработанные файлы по `origin.name` + `origin.archive_src` в `index.yaml` и помечает их в markdown-плане как пропуск. В machine-plan skipped-файлы не должны попадать в `cleanup_set`, если для них нет безопасной raw-preserving ветки (`raw_only`, `source_path` или `grouped_inputs`).

Это защищает от двойного приобщения, когда клиент присылает тот же пакет повторно.

## Блокер при отсутствии Codex

Если Codex companion не найден (`CODEX_COMPANION_NOT_FOUND`) или вернул `ECONNREFUSED`/ошибку запуска:

- Сообщи Сюзерену: `Codex companion недоступен, add-evidence невозможен. Установи/перезапусти плагин openai-codex и повтори.`
- Не переходи к самостоятельному исполнению. Вся черновая работа — за Codex medium.
- Остановись.
