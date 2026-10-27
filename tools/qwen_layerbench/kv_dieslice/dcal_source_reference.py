#!/usr/bin/env python3
"""Opt-in KV source-event adapter around the unchanged generic R8 checker.

Raw physical as-built fields and binder member IDs are never rewritten. Only the
checker gets a transient event-reference view, selected by the actual recipe and
guarded by the measured source and exact two-member landing correction.
"""
from __future__ import annotations
import argparse
import copy
import json
import sys
from pathlib import Path

from dcal_boot_contract import prepare

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import r8


def qualified_view(groups: dict, candidate: dict, face: bytes, provider: str):
    contract = candidate.get("source_event_contract")
    if not isinstance(contract, dict) or len(contract.get("changes", [])) != 2:
        raise ValueError("landing table lacks the exact two-member measured source contract")
    baseline = copy.deepcopy(candidate)
    baseline.pop("source_event_contract")
    if "pad_flops" in baseline.get("summary", {}):
        baseline["summary"]["pad_flops"] -= 2
    before = {row["id"]: row["before"] for row in contract["changes"]}
    baseline["members"] = [copy.deepcopy(before.get(row["id"], row)) for row in baseline["members"]]
    raw_reference = copy.deepcopy(groups)
    changes = {row["after"]["sink_port"]: row for row in contract["changes"]}
    selected_sources = {row["before"]["source"] for row in contract["changes"]}
    if any(row.get("source") in selected_sources for row in groups.get("replica", [])):
        raise ValueError("boot strobe has additional replica consumers outside this measured correction")
    for g in raw_reference.get("landing", []):
        for m in g["members"]:
            change = changes.get(m.get("sink_port")) if g.get("sink") == "dcal" else None
            if change and m.get("source") == change["before"]["source"]:
                if m["landed_stages"] not in (change["before"]["landed"], change["after"]["landed"]):
                    raise ValueError("current source group has a different landing cohort")
                m["landed_stages"] = change["before"]["landed"]
    expected, receipt = prepare(baseline, raw_reference, face, provider)
    if expected != candidate or receipt != contract:
        raise ValueError("landing table or source contract differs from the guarded exact correction")
    view = copy.deepcopy(groups)
    landing = {row["id"]: row["landed"] for row in candidate["members"]}
    references = []
    for g in view.get("landing", []):
        for m in g["members"]:
            change = changes.get(m.get("sink_port")) if g.get("sink") == "dcal" else None
            if not change or m.get("source") != change["before"]["source"]:
                continue
            old_key = r8.mkey(g, m)
            if old_key != change["id"]:
                raise ValueError("raw physical member identity changed")
            legacy = m["asbuilt_stages"]
            m["legacy_asbuilt_stages"] = legacy
            m["producer_event_offset"] = 1
            # Library arithmetic only: this is not emitted as a physical bus_groups file.
            m["asbuilt_stages"] = legacy + 1
            event_key = r8.mkey(g, m)
            landing[event_key] = landing[old_key]
            references.append({"raw_id": old_key, "library_event_key": event_key,
                               "legacy_physical_asbuilt": legacy, "producer_event_offset": 1,
                               "effective_event_reference": legacy + 1})
    if len(references) != 2:
        raise ValueError("source-event selection did not identify exactly two members")
    return view, landing, references


def repo_file(root: Path, name: str) -> Path:
    if not isinstance(name, str) or Path(name).is_absolute():
        raise ValueError("source-event recipe paths must be repository-relative")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing/outside-repository source-event input: {name}")
    return path


def check_selected(plan: dict, groups: dict, recipe: dict, root: Path) -> dict:
    selected = recipe.get("qualified_boot_source_event")
    if not isinstance(selected, dict) or selected.get("schema") != "opentallas.kv.boot_source_selection.v1":
        raise ValueError("actual recipe must explicitly select qualified_boot_source_event")
    if selected.get("landing") != recipe.get("land_r8"):
        raise ValueError("source-event selection differs from the binder land_r8 table")
    if selected.get("selected_provider") not in recipe.get("prefer", []):
        raise ValueError("source-event provider is not the actual recipe preferred provider")
    candidate = json.loads(repo_file(root, selected["landing"]).read_text())
    contract = candidate.get("source_event_contract", {})
    if selected.get("contract_sha256") != contract.get("contract_sha256"):
        raise ValueError("recipe selects a different source-event contract")
    protected = {row["id"] for row in contract.get("changes", [])}
    extra_tables = []
    for name in recipe.get("land_r8_extra", []):
        extra = json.loads(repo_file(root, name).read_text())
        replacements = {row["id"]: row for row in extra["members"] if not row["id"].startswith("INNER:")}
        if protected.intersection(replacements):
            raise ValueError("an extra table overwrites the qualified boot strobe correction")
        existing = {row["id"] for row in candidate["members"]}
        candidate["members"] = [replacements.get(row["id"], row) for row in candidate["members"]]
        candidate["members"] += [row for key, row in replacements.items() if key not in existing]
        extra_tables.append(name)
    face = repo_file(root, selected["producer_face"]).read_bytes()
    provider = repo_file(root, selected["selected_provider"]).read_text()
    view, effective_landing, refs = qualified_view(groups, candidate, face, provider)
    options = candidate.get("landed", {})
    r8.configure(candidate.get("exempt", []) + recipe.get("land_r8_exempt", []), options.get("rx", []), options.get("window", 4),
                 options.get("stage_cycles", 0.5), options.get("over_margin", "keep"))
    mode = (candidate.get("replica", "all"), candidate.get("bus", "part"))
    raw_landing = {row["id"]: row["landed"] for row in candidate["members"]}
    old_messages, old_stats = r8.check(groups, plan, raw_landing, *mode)
    messages, stats = r8.check(view, plan, effective_landing, *mode)
    passed = not any(severity == "ERROR" for severity, _ in messages)
    return {"scope": "qualified_current_boot_source_event_R8", "pass": passed,
            "raw_physical_reference_pass": not any(s == "ERROR" for s, _ in old_messages),
            "raw_stats": old_stats, "raw_messages": old_messages,
            "qualified_stats": stats, "qualified_messages": messages,
            "references": refs, "contract_sha256": contract["contract_sha256"],
            "preserved_extra_tables": extra_tables,
            "note": "Raw groups, raw physical stages and binder IDs retained. Generic library labels in qualified_messages describe the transient source-event reference, not amended physical as-built claims. No unrelated R8 finding is waived."}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "groups", "recipe", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--repo", type=Path, default=ROOT)
    a = ap.parse_args()
    if a.out.exists():
        raise ValueError("refusing to overwrite an R8 verdict")
    result = check_selected(json.loads(a.plan.read_text()), json.loads(a.groups.read_text()),
                            json.loads(a.recipe.read_text()), a.repo)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print("QUALIFIED_SOURCE_R8", "PASS" if result["pass"] else "FAIL")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
