"""Contract tests for update-index Ф3 prompt/skill/smoke behavior."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_update_index_smoke_records_real_scan_case_state_json_for_preview() -> None:
    script = _read("tests/smoke/test-update-index.sh")

    assert 'python3 "$PLUGIN_ROOT/scripts/scan_case_state.py" "$SMOKE_CASE"' in script
    assert 'EXPECTED_SCAN="/tmp/smoke-vassal-update-index-expected-scan-' in script
    for key in ("index_count", "fs_count", "new_files", "orphans", "stale_mirrors"):
        assert key in script


def test_update_index_preview_contract_uses_scan_json_as_single_source() -> None:
    skill = _read("skills/update-index/SKILL.md")

    assert "Единственный источник diff-preview — JSON от `scan_case_state.py`" in skill
    assert 'python3 "[PLUGIN_ROOT]/scripts/scan_case_state.py" "[CASE_ROOT]"' in skill
    assert "new_files" in skill
    assert "orphans" in skill
    assert "stale_mirrors" in skill
    assert "ручной обход файловой системы" in skill


def test_update_index_apply_prompt_uses_classifier_contract_not_legacy_threshold() -> None:
    prompt = _read("prompts/file-executor-update-index.md")

    assert "scripts/classify_ocr_quality.py" in prompt
    assert 'needs_manual_review` вычисли локально как `ocr_quality != "ok"`' in prompt
    assert "confidence < 0.7" not in prompt
