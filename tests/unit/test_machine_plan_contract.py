"""End-to-end contract checks for machine plan validation and apply."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


ALLOWED_TOP_LEVEL = {
    "batch",
    "source_inbox",
    "work_dir",
    "raw_dest",
    "next_id_start",
    "next_bundle_id_start",
    "raw_only",
    "skipped",
    "cleanup_set",
    "bundles",
    "items",
}


def _write(path: Path, text: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _build_plan(tmp_path: Path, batch: str, fixture_name: str) -> tuple[Path, Path]:
    case_root = tmp_path / batch
    inbox = case_root / "Входящие документы"
    work = case_root / ".vassal" / "work" / batch
    raw = case_root / ".vassal" / "raw" / batch
    plans = case_root / ".vassal" / "plans"
    for path in [inbox, work, raw.parent, plans]:
        path.mkdir(parents=True, exist_ok=True)
    _yaml(case_root / ".vassal" / "index.yaml", {"version": 2, "last_updated": "2026-05-05", "documents": [], "bundles": [], "next_id": 1, "next_bundle_id": 1})
    source = inbox / "contract.pdf"
    text = work / "contract.txt"
    _write(source, "source")
    _write(text, "Полный текст договора")
    template = (Path(__file__).parent / "fixtures" / fixture_name).read_text(encoding="utf-8")
    rendered = (
        template.replace("__BATCH__", batch)
        .replace("__SOURCE_INBOX__", str(inbox))
        .replace("__WORK_DIR__", str(work))
        .replace("__RAW_DEST__", str(raw))
        .replace("__SOURCE_FILE__", str(source))
        .replace("__TEXT_FILE__", str(text))
        .replace("__TARGET_FILE__", str(case_root / "Материалы от клиента" / "2026-05-05 Договор.pdf"))
    )
    plan = yaml.safe_load(rendered)
    plan_path = plans / f"{batch}.yaml"
    _yaml(plan_path, plan)
    assert set(plan) == ALLOWED_TOP_LEVEL
    return case_root, plan_path


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)


def test_apply_intake_plan_contract_for_supported_batches(tmp_path: Path) -> None:
    cases = [
        ("intake-2026-05-05-1430", "intake.yaml"),
        ("add-evidence-2026-05-05-1431", "add-evidence.yaml"),
        ("add-opponent-2026-05-05-1432", "add-opponent.yaml"),
    ]
    for batch, fixture_name in cases:
        case_root, plan_path = _build_plan(tmp_path, batch, fixture_name)

        validate = _run([sys.executable, "scripts/validate_machine_plan.py", str(case_root), "--plan-yaml", str(plan_path), "--mode", "plan"])
        assert validate.returncode == 0, validate.stderr

        dry = _run([sys.executable, "scripts/apply_intake_plan.py", str(case_root), "--plan-yaml", str(plan_path), "--dry-run"])
        assert dry.returncode == 0, dry.stderr
        dry_payload = json.loads(dry.stdout)
        assert dry_payload["applied"] is False
        assert dry_payload["history_line"].find(f"{batch.split('-2026')[0]} apply: batch={batch}") != -1

        apply = _run([sys.executable, "scripts/apply_intake_plan.py", str(case_root), "--plan-yaml", str(plan_path)])
        assert apply.returncode == 0, apply.stderr
        payload = json.loads(apply.stdout)
        assert payload["applied"] is True
        assert payload["added_doc_ids"] == ["doc-001"]
        assert not plan_path.exists()
        assert not plan_path.with_suffix(".md").exists()
        assert (case_root / "Материалы от клиенте").exists() is False

        index = yaml.safe_load((case_root / ".vassal" / "index.yaml").read_text(encoding="utf-8"))
        assert index["next_id"] == 2
        assert index["documents"][0]["ocr_quality"] == "ok"
        assert index["documents"][0]["needs_manual_review"] is False
        assert (case_root / ".vassal" / "raw" / batch / "contract.pdf").exists()
        assert not (case_root / "Входящие документы" / "contract.pdf").exists()
