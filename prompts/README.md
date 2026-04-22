# Prompts — карта Ф1

В этой директории лежат **каркасы** промптов Codex для vassal-litigator. Ф1 создаёт только инфраструктуру и единый контракт; профильная логика будет дозаполняться в Ф2-Ф6.

## Общая схема

Каждый ролевой шаблон начинается с:

```md
{{include _preamble.md}}
```

<!-- prompt-assembly step expands this include; see skills/codex-invocation/SKILL.md §Как Claude-main собирает prompt -->

Оркестратор обязан **до диспатча**:

1. получить абсолютные `[CASE_ROOT]` и `[PLUGIN_ROOT]`
2. expand `{{include _preamble.md}}` буквальной подстановкой содержимого `prompts/_preamble.md`
3. подставить пути и остальные placeholders конкретной команды
4. проверить, что в собранном prompt не осталось `{{include ...}}` и других `{{...}}`
5. передать в Codex уже готовый текст

## Общие placeholders

- `{{task_name}}` — имя конкретной задачи
- `{{role_id}}` — `file-executor` | `timeline-builder` | `imagegen-visualizer` | `analytical-reviewer`
- `{{case_root}}` — абсолютный путь к делу
- `{{plugin_root}}` — абсолютный путь к установленному плагину
- `{{report_contract}}` — при необходимости локальное уточнение формата отчёта
- `{{extra_constraints}}` — дополнительные ограничения конкретного вызова

## Карта файлов

Пары `plan → apply` файлового пайплайна (v1.0.0, контракт `plan → review → (revise) → apply → verify`):

- `file-executor-intake-plan.md` — plan-шаблон intake; ключевые placeholders: `{{batch_name}}`, `{{plan_path}}`, `{{work_dir}}`, `{{revise_feedback}}`, `{{next_id_hint}}`
- `file-executor-intake-apply.md` — apply-шаблон intake; placeholders: `{{batch_name}}`, `{{plan_path}}`, `{{work_dir}}`, `{{plan_timestamp}}`
- `file-executor-add-evidence-plan.md` + `-apply.md` — такая же пара для add-evidence
- `file-executor-add-opponent-plan.md` + `-apply.md` — пара для add-opponent, плюс дополнительный placeholder `{{opponent_hint}}` в plan

Одностадийные файловые роли (без plan-фазы, детерминированный алгоритм):

- `file-executor-update-index.md` — apply-шаблон update-index; ключевые placeholders: `{{plan_body}}`, `{{scan_scope}}`
- `file-executor-catalog.md` — apply-шаблон catalog; placeholders: `{{plan_body}}`, `{{output_table_path}}`

Остальные роли:

- `timeline-builder.md` — high-effort шаблон хронологии; placeholders: `{{timeline_goal}}`, `{{existing_timeline_policy}}`
- `imagegen-visualizer.md` — каркас sidecar-визуализатора; placeholders: `{{visual_type}}`, `{{visual_context}}`
- `analytical-reviewer.md` — xhigh review-каркас; placeholders: `{{output_path}}`, `{{original_input}}`

## Инварианты

- шаблоны не содержат относительных `scripts/...` и `shared/...` (только `[PLUGIN_ROOT]/...`)
- plan-шаблоны пишут **только** в whitelist: `{{plan_path}}`, `{{work_dir}}/`, `.vassal/history.md`
- apply-шаблоны исполняют план буквально, в конце архивируют план в `.vassal/codex-logs/` и обнуляют активный план и work-дир
- для визуализатора путь к итоговому PNG не описывается как `GENERATED_IMAGE:`-контракт; фактический резолв делается оркестратором через `sessionId`
