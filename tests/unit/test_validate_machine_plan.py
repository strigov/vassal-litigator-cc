"""Behavior tests for plugin-local machine plan guard."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _write_file(path: Path, text: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _case(tmp_path: Path, *, batch: str = "intake-2026-05-05-1430", next_id: int = 47) -> tuple[Path, dict]:
    case_root = tmp_path / "case"
    inbox = case_root / "Входящие документы"
    work = case_root / ".vassal" / "work" / batch
    raw = case_root / ".vassal" / "raw" / batch
    for path in [inbox, work, raw.parent, case_root / ".vassal" / "plans", case_root / ".vassal" / "codex-logs"]:
        path.mkdir(parents=True, exist_ok=True)
    _write_yaml(
        case_root / ".vassal" / "index.yaml",
        {"version": 2, "last_updated": "2026-05-05", "documents": [], "bundles": [], "next_id": next_id, "next_bundle_id": 1},
    )
    return case_root, {"batch": batch, "inbox": inbox, "work": work, "raw": raw, "next_id": next_id}


def _item(paths: dict, *, doc_id: str = "doc-047", source: Path | None = None, grouped: list[Path] | None = None) -> dict:
    batch = paths["batch"]
    if source is None and grouped is None:
        source = paths["inbox"] / "doc.pdf"
        _write_file(source, "pdf")
    text = paths["work"] / f"{doc_id}.txt"
    _write_file(text, f"text {doc_id}")
    if grouped is not None:
        for idx, path in enumerate(grouped):
            _write_file(path, f"image {idx}")
    elif source is not None:
        _write_file(source, "source")
    artifacts = [
        {"path": str(text), "extraction_method": "pdf-text", "confidence": "high", "pages": 1, "total_chars": 10}
        for _ in (grouped or [source])
    ]
    return {
        "source_path": str(source) if grouped is None else None,
        "grouped_inputs": [str(p) for p in grouped] if grouped is not None else None,
        "archive_src": None,
        "target_file": str(paths["inbox"].parent / "Материалы от клиента" / f"{doc_id}.pdf"),
        "convert_image_to_pdf": grouped is not None,
        "ocr_artifacts": artifacts,
        "combined_text_path": str(text),
        "doc_id": doc_id,
        "title": f"Документ {doc_id}",
        "type": "договор",
        "date": "2026-05-05",
        "source": "client",
        "origin": {"name": f"{doc_id}.pdf", "date": "2026-05-05", "received": "2026-05-05", "batch": batch, "archive_src": None},
        "bundle_id": None,
        "role_in_bundle": None,
        "parent_id": None,
        "attachment_order": None,
    }


def _plan(case_root: Path, paths: dict, *, items: list[dict] | None = None, **overrides: object) -> Path:
    batch = str(overrides.pop("batch", paths["batch"]))
    payload = {
        "batch": batch,
        "source_inbox": str(overrides.pop("source_inbox", paths["inbox"])),
        "work_dir": str(overrides.pop("work_dir", paths["work"])),
        "raw_dest": str(overrides.pop("raw_dest", paths["raw"])),
        "next_id_start": overrides.pop("next_id_start", paths["next_id"]),
        "next_bundle_id_start": overrides.pop("next_bundle_id_start", 1),
        "raw_only": overrides.pop("raw_only", []),
        "skipped": overrides.pop("skipped", []),
        "cleanup_set": overrides.pop("cleanup_set", []),
        "bundles": overrides.pop("bundles", []),
        "items": items if items is not None else [_item(paths)],
    }
    payload.update(overrides)
    path = case_root / ".vassal" / "plans" / f"{batch}.yaml"
    _write_yaml(path, payload)
    return path


def _run(case_root: Path, plan: Path, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/validate_machine_plan.py", str(case_root), "--plan-yaml", str(plan), "--mode", mode],
        text=True,
        capture_output=True,
        check=False,
    )


def test_doc_id_contiguity(tmp_path: Path) -> None:
    case_root, paths = _case(tmp_path)
    ok = _plan(case_root, paths, items=[_item(paths, doc_id="doc-047"), _item(paths, doc_id="doc-048")])
    assert _run(case_root, ok, "plan").returncode == 0

    gap = _plan(case_root, paths, items=[_item(paths, doc_id="doc-047"), _item(paths, doc_id="doc-049")])
    proc = _run(case_root, gap, "plan")
    assert proc.returncode != 0
    assert "doc_id range" in proc.stderr

    wrong_start = _plan(case_root, paths, items=[_item(paths, doc_id="doc-999")])
    proc = _run(case_root, wrong_start, "plan")
    assert proc.returncode != 0
    assert "doc_id range" in proc.stderr


def test_cleanup_set_safety(tmp_path: Path) -> None:
    case_root, paths = _case(tmp_path)
    source = paths["inbox"] / "safe.pdf"
    item = _item(paths, source=source)
    assert _run(case_root, _plan(case_root, paths, items=[item], cleanup_set=[str(source)]), "plan").returncode == 0

    skipped = paths["inbox"] / "skipped.pdf"
    _write_file(skipped)
    proc = _run(
        case_root,
        _plan(case_root, paths, skipped=[{"path": str(skipped), "reason": "manual"}], cleanup_set=[str(skipped)]),
        "plan",
    )
    assert proc.returncode != 0
    assert "skipped" in proc.stderr

    archive = paths["inbox"] / "pack.zip"
    extracted = paths["work"] / "archives" / "pack" / "inside.pdf"
    _write_file(archive, "zip")
    archive_item = _item(paths, source=extracted)
    archive_item["archive_src"] = str(archive)
    archive_item["origin"]["archive_src"] = archive.name
    proc = _run(case_root, _plan(case_root, paths, items=[archive_item], cleanup_set=[str(archive)]), "plan")
    assert proc.returncode != 0
    assert "raw_only" in proc.stderr

    ok = _plan(
        case_root,
        paths,
        items=[archive_item],
        raw_only=[{"archive_src": str(archive), "raw_dest_name": "pack.zip"}],
        cleanup_set=[str(archive)],
    )
    assert _run(case_root, ok, "plan").returncode == 0


def test_single_image_and_distinct_grouped_inputs(tmp_path: Path) -> None:
    case_root, paths = _case(tmp_path)
    img = paths["inbox"] / "photo.jpg"
    converted = paths["work"] / "photo.pdf"
    _write_file(img, "image")
    item = _item(paths, source=converted)
    proc = _run(case_root, _plan(case_root, paths, items=[item], cleanup_set=[str(img)]), "plan")
    assert proc.returncode != 0
    assert "pre-converted image" in proc.stderr

    item_without_cleanup = _item(paths, source=converted)
    item_without_cleanup["origin"]["name"] = "photo.jpg"
    proc = _run(case_root, _plan(case_root, paths, items=[item_without_cleanup], cleanup_set=[]), "plan")
    assert proc.returncode != 0
    assert "pre-converted image" in proc.stderr

    ok = _plan(
        case_root,
        paths,
        items=[item],
        raw_only=[{"archive_src": str(img), "raw_dest_name": "photo.jpg"}],
        cleanup_set=[str(img)],
    )
    assert _run(case_root, ok, "plan").returncode == 0

    duplicate_group = _plan(case_root, paths, items=[_item(paths, grouped=[img, img])])
    proc = _run(case_root, duplicate_group, "plan")
    assert proc.returncode != 0
    assert "grouped_inputs" in proc.stderr

    img2 = paths["inbox"] / "photo2.jpg"
    grouped_ok = _plan(case_root, paths, items=[_item(paths, grouped=[img, img2])], cleanup_set=[str(img), str(img2)])
    assert _run(case_root, grouped_ok, "plan").returncode == 0


def test_raw_dest_collision(tmp_path: Path) -> None:
    case_root, paths = _case(tmp_path)
    first = paths["inbox"] / "first.zip"
    second = paths["inbox"] / "second.zip"
    _write_file(first)
    _write_file(second)
    proc = _run(
        case_root,
        _plan(
            case_root,
            paths,
            raw_only=[
                {"archive_src": str(first), "raw_dest_name": "archive.zip"},
                {"archive_src": str(second), "raw_dest_name": "archive.zip"},
            ],
        ),
        "plan",
    )
    assert proc.returncode != 0
    assert "raw destination collision" in proc.stderr

    nested = paths["inbox"] / "sub" / "contract.pdf"
    ok = _plan(
        case_root,
        paths,
        items=[_item(paths, source=nested)],
        raw_only=[{"archive_src": str(first), "raw_dest_name": "contract.pdf"}],
    )
    assert _run(case_root, ok, "plan").returncode == 0


def test_batch_identity_modes(tmp_path: Path) -> None:
    case_root, paths = _case(tmp_path)
    ok = _plan(case_root, paths)
    assert _run(case_root, ok, "plan").returncode == 0
    assert _run(case_root, ok, "apply").returncode == 0

    mismatch_path = case_root / ".vassal" / "plans" / "intake-2026-05-05-9999.yaml"
    mismatch_path.write_text(ok.read_text(encoding="utf-8"), encoding="utf-8")
    assert _run(case_root, mismatch_path, "plan").returncode != 0

    bad_work = _plan(case_root, paths, work_dir=str(case_root / ".vassal" / "work" / "other"))
    assert _run(case_root, bad_work, "plan").returncode != 0

    bad_raw = _plan(case_root, paths, raw_dest=str(case_root / ".vassal" / "raw" / "other"))
    assert _run(case_root, bad_raw, "apply").returncode != 0

    ok = _plan(case_root, paths)
    _write_file(paths["raw"] / "old.pdf")
    proc = _run(case_root, ok, "plan")
    assert proc.returncode != 0
    assert "raw_dest" in proc.stderr

    state = case_root / ".vassal" / "plans" / f"{paths['batch']}-apply-state.json"
    state.write_text(
        json.dumps({"status": "promoting", "batch": paths["batch"], "plan_yaml": str(ok.resolve()), "plan_sha256": hashlib.sha256(ok.read_bytes()).hexdigest()}),
        encoding="utf-8",
    )
    assert _run(case_root, ok, "plan").returncode != 0
    assert _run(case_root, ok, "apply").returncode == 0

    state.write_text("{bad-json", encoding="utf-8")
    assert _run(case_root, ok, "apply").returncode != 0


def test_resume_drift_blocked(tmp_path: Path) -> None:
    case_root, paths = _case(tmp_path)
    plan = _plan(case_root, paths)
    backup = case_root / ".vassal" / "codex-logs" / plan.name
    backup.write_bytes(plan.read_bytes())
    state = case_root / ".vassal" / "plans" / f"{paths['batch']}-apply-state.json"
    state.write_text(
        json.dumps({"status": "promoting", "batch": paths["batch"], "plan_yaml": str(plan.resolve()), "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest()}),
        encoding="utf-8",
    )
    _write_file(paths["raw"] / "staged.pdf")
    assert _run(case_root, plan, "apply").returncode == 0

    payload = yaml.safe_load(plan.read_text(encoding="utf-8"))
    payload["items"][0]["title"] = "Изменённый документ"
    _write_yaml(plan, payload)
    proc = _run(case_root, plan, "apply")
    assert proc.returncode != 0
    assert "resume drift" in proc.stderr


def test_apply_resume_allows_existing_target_file_with_valid_state(tmp_path: Path) -> None:
    case_root, paths = _case(tmp_path)
    item = _item(paths)
    plan = _plan(case_root, paths, items=[item])
    _write_file(Path(item["target_file"]), "promoted")
    _write_file(paths["raw"] / "doc.pdf", "raw")
    state = case_root / ".vassal" / "plans" / f"{paths['batch']}-apply-state.json"
    state.write_text(
        json.dumps({"status": "promoting", "batch": paths["batch"], "plan_yaml": str(plan.resolve()), "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest()}),
        encoding="utf-8",
    )

    assert _run(case_root, plan, "apply").returncode == 0
