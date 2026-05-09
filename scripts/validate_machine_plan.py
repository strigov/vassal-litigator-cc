#!/usr/bin/env python3
"""Validate plugin-local machine-plan invariants before deterministic apply."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

import apply_intake_plan as aip

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".heic"}


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _real(path: Path) -> Path:
    return Path(os.path.realpath(str(path)))


def _contains(root: Path, target: Path, *, allow_equal: bool = True) -> bool:
    root = _real(root)
    target = _real(target)
    try:
        common = Path(os.path.commonpath([str(root), str(target)]))
    except ValueError:
        return False
    if common != root:
        return False
    return allow_equal or target != root


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise aip.ApplyError("plan yaml must be mapping")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _doc_id_int(doc_id: str) -> int:
    match = aip.DOC_ID_RE.fullmatch(str(doc_id))
    if not match:
        raise aip.ApplyError(f"invalid doc_id: {doc_id}")
    return int(match.group(1))


def _path(raw: Any, case_root: Path) -> Path:
    path = Path(str(raw))
    if not path.is_absolute():
        path = case_root / path
    return path


def _check_doc_ids(plan: dict[str, Any]) -> None:
    items = plan.get("items") or []
    actual = sorted(_doc_id_int(item.get("doc_id")) for item in items if isinstance(item, dict))
    start = int(plan.get("next_id_start"))
    expected = list(range(start, start + len(items)))
    if actual != expected:
        raise aip.ApplyError(f"doc_id range must be contiguous from next_id_start: expected {expected}, got {actual}")


def _cleanup_sources(plan: dict[str, Any], case_root: Path) -> tuple[set[Path], set[Path], set[Path]]:
    copied: set[Path] = set()
    raw_only: set[Path] = set()
    skipped: set[Path] = set()
    for entry in plan.get("raw_only") or []:
        src = _real(_path(entry.get("archive_src"), case_root))
        copied.add(src)
        raw_only.add(src)
    for item in plan.get("items") or []:
        if item.get("source_path") is not None:
            copied.add(_real(_path(item.get("source_path"), case_root)))
        for grouped in item.get("grouped_inputs") or []:
            copied.add(_real(_path(grouped, case_root)))
    for entry in plan.get("skipped") or []:
        skipped.add(_real(_path(entry.get("path"), case_root)))
    return copied, raw_only, skipped


def _check_cleanup(plan: dict[str, Any], case_root: Path) -> None:
    copied, raw_only, skipped = _cleanup_sources(plan, case_root)
    work_dir = _real(_path(plan["work_dir"], case_root))
    raw_only_names = {
        Path(str(entry.get("archive_src"))).name
        for entry in plan.get("raw_only") or []
        if isinstance(entry, dict)
    }
    for idx, item in enumerate(plan.get("items") or []):
        source = item.get("source_path")
        origin = item.get("origin") or {}
        origin_name = origin.get("name") if isinstance(origin, dict) else None
        if source is None or not isinstance(origin_name, str):
            continue
        source_path = _real(_path(source, case_root))
        if _contains(work_dir, source_path, allow_equal=False) and source_path.suffix.lower() == ".pdf" and Path(origin_name).suffix.lower() in IMAGE_SUFFIXES:
            if Path(origin_name).name not in raw_only_names:
                raise aip.ApplyError(f"pre-converted image requires raw_only copy: items[{idx}].origin.name={origin_name}")
    for raw in plan.get("cleanup_set") or []:
        path = _real(_path(raw, case_root))
        if path in skipped:
            raise aip.ApplyError(f"cleanup_set contains skipped path: {path}")
        if path not in copied:
            if path.suffix.lower() in IMAGE_SUFFIXES:
                raise aip.ApplyError(f"pre-converted image in cleanup_set requires raw_only copy: {path}")
            raise aip.ApplyError(f"cleanup_set path has no raw-preserving source_path/grouped_inputs/raw_only copy: {path}")
        if path.suffix.lower() in {".zip", ".rar", ".7z", ".tar", ".gz"} and path not in raw_only:
            raise aip.ApplyError(f"archive in cleanup_set requires raw_only bit copy: {path}")


def _check_grouped_inputs(plan: dict[str, Any], case_root: Path) -> None:
    for idx, item in enumerate(plan.get("items") or []):
        grouped = item.get("grouped_inputs") or []
        if not grouped:
            continue
        resolved = [_real(_path(raw, case_root)) for raw in grouped]
        if len(set(resolved)) != len(resolved):
            raise aip.ApplyError(f"items[{idx}].grouped_inputs must contain distinct real paths")


def _raw_pairs(plan: dict[str, Any], case_root: Path) -> list[tuple[Path, Path]]:
    inbox = _real(_path(plan["source_inbox"], case_root))
    work = _real(_path(plan["work_dir"], case_root))
    raw_dest = _real(_path(plan["raw_dest"], case_root))
    pairs: list[tuple[Path, Path]] = []
    for entry in plan.get("raw_only") or []:
        source = _real(_path(entry["archive_src"], case_root))
        pairs.append((_real(raw_dest / str(entry["raw_dest_name"])), source))
    for item in plan.get("items") or []:
        sources = item.get("grouped_inputs") or [item.get("source_path")]
        for raw in sources:
            source = _real(_path(raw, case_root))
            root = inbox if _contains(inbox, source, allow_equal=False) else work
            try:
                rel = source.relative_to(root)
            except ValueError as exc:
                raise aip.ApplyError(f"source path cannot be mapped to raw_dest: {source}") from exc
            pairs.append((_real(raw_dest / rel), source))
    return pairs


def _check_raw_collisions(plan: dict[str, Any], case_root: Path) -> None:
    by_dest: dict[Path, set[Path]] = {}
    for dest, source in _raw_pairs(plan, case_root):
        by_dest.setdefault(dest, set()).add(source)
    for dest, sources in by_dest.items():
        if len(sources) > 1:
            joined = ", ".join(str(path) for path in sorted(sources))
            raise aip.ApplyError(f"raw destination collision: {dest} <- {{{joined}}}")


def _state_status(case_root: Path, plan_yaml: Path, plan: dict[str, Any]) -> bool:
    state_path = case_root / ".vassal" / "plans" / f"{plan['batch']}-apply-state.json"
    if not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise aip.ApplyError(f"invalid apply state json: {state_path}") from exc
    if not isinstance(state, dict):
        raise aip.ApplyError(f"invalid apply state json: {state_path}")
    current_hash = _sha256(plan_yaml)
    state_hash = state.get("plan_sha256")
    if state.get("plan_yaml") != str(plan_yaml.resolve()) or state.get("batch") != plan["batch"]:
        raise aip.ApplyError("apply state belongs to another plan")
    if not state_hash or state_hash != current_hash:
        raise aip.ApplyError(f"resume drift: plan content changed since previous apply (state sha256={state_hash}, current sha256={current_hash})")
    backup = case_root / ".vassal" / "codex-logs" / plan_yaml.name
    if backup.exists() and _sha256(backup) != current_hash:
        raise aip.ApplyError("resume drift: plan content differs from codex-log backup")
    return True


def _has_matching_apply_state(case_root: Path, plan_yaml: Path, plan: dict[str, Any]) -> bool:
    batch = plan.get("batch")
    if not isinstance(batch, str) or Path(batch).name != batch or "/" in batch or batch in {".", ".."}:
        return False
    state_path = case_root / ".vassal" / "plans" / f"{batch}-apply-state.json"
    if not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(state, dict):
        return False
    return (
        state.get("batch") == batch
        and state.get("plan_yaml") == str(plan_yaml)
        and state.get("plan_sha256") == _sha256(plan_yaml)
    )


def _check_batch_identity(case_root: Path, plan_yaml: Path, plan: dict[str, Any], mode: str) -> None:
    batch = str(plan.get("batch"))
    if plan_yaml.stem != batch:
        raise aip.ApplyError("batch identity mismatch: plan filename stem must equal plan.batch")
    expected_work = _real(case_root / ".vassal" / "work" / batch)
    expected_raw = _real(case_root / ".vassal" / "raw" / batch)
    if _real(_path(plan.get("work_dir"), case_root)) != expected_work:
        raise aip.ApplyError("batch identity mismatch: work_dir must be .vassal/work/<batch>")
    if _real(_path(plan.get("raw_dest"), case_root)) != expected_raw:
        raise aip.ApplyError("batch identity mismatch: raw_dest must be .vassal/raw/<batch>")
    state_path = case_root / ".vassal" / "plans" / f"{batch}-apply-state.json"
    raw_nonempty = expected_raw.exists() and any(expected_raw.iterdir())
    if mode == "plan":
        if state_path.exists():
            raise aip.ApplyError("state_file already exists for batch")
        if raw_nonempty:
            raise aip.ApplyError("raw_dest already exists and is not empty")
        return
    valid_state = _state_status(case_root, plan_yaml, plan) if state_path.exists() else False
    if raw_nonempty and not valid_state:
        raise aip.ApplyError("raw_dest is not empty without valid resume state")


def validate(case_root: Path, plan_yaml: Path, mode: str) -> None:
    raw_plan = _load_yaml(plan_yaml)
    index = aip._load_index_payload(case_root)
    allow_existing_target_files = mode == "apply" and _has_matching_apply_state(case_root, plan_yaml, raw_plan)
    aip._validate_plan(case_root, raw_plan, index, allow_existing_target_files=allow_existing_target_files)
    _check_doc_ids(raw_plan)
    _check_cleanup(raw_plan, case_root)
    _check_grouped_inputs(raw_plan, case_root)
    _check_raw_collisions(raw_plan, case_root)
    _check_batch_identity(case_root, plan_yaml, raw_plan, mode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate vassal machine plan invariants")
    parser.add_argument("case_root")
    parser.add_argument("--plan-yaml", required=True)
    parser.add_argument("--mode", required=True, choices=["plan", "apply"])
    args = parser.parse_args()
    try:
        validate(Path(args.case_root).resolve(), Path(args.plan_yaml).resolve(strict=True), args.mode)
        return 0
    except (aip.ApplyError, OSError, ValueError, KeyError, TypeError) as exc:
        return _fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
