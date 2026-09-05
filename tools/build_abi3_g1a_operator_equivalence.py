#!/usr/bin/env python3
"""Derive rung G1a's artifact: operator equivalence over the governed decode.

G1a's statement (configs/gates/redesign_gates.json) is that *every* operator
equivalence class the governed decode program issues executes in the integrated
RTL, from the real compiled program against the real checkpoint weights, and
matches the golden model bit for bit.  This tool derives that artifact; it never
asserts it.

How the class inventory is obtained
-----------------------------------
Not from a table typed in here.  The retained deployment vector set
``testdata/compiler/abi3_deployment`` carries, per case, the issue stream --
``runtime.sim.device.Device``'s own trace of (family, sub, operator descriptor
id, instruction index) in program order -- and the view stream, which is
``runtime.sim.memory.ViewResolver.resolve`` evaluated against the loop bindings
the device recorded at each issue.  Walking the two together in program order
reconstructs, for every issue the decode makes, the operator descriptor it ran
and the resolved extents its datapath saw.  The walk is self-checking: it
consumes exactly one view per non-NO_ID slot of each issue's operator
descriptor, and the artifact records whether the view stream came out exactly
empty.  If it did not, the inventory is refused rather than reported.

An equivalence class is the tuple the gate note names -- (family, sub,
mnemonic, numeric contract digest, resolved shape) -- where the resolved shape
is the per-slot (slot, extent, extent_axis, rank) of that issue's own views.

How coverage is decided
-----------------------
A class is covered only by an RTL campaign that

  1. is retained in ``results/rtl`` with ``status`` pass, and
  2. still binds every source and vector digest it recorded -- recomputed here,
     so an artifact that has drifted under a later commit covers nothing, and
  3. names the SAME deployment the record's storage class names, by
     ``deployment_sha256``, and
  4. drove the class's own operator descriptor ids in a POSITIVE case.

Rule 3 is not pedantry.  The Qwen ROM and HBM lowerings do not emit identical
operator descriptors for the same class: at PCs 32 and 35 the DMA.SCATTER
NUMERIC descriptor's ``input_dtype``/``second_input_dtype`` pair is swapped
between them under one identical contract digest, ``counter_class_id`` differs
at all eight governed PCs, and the PC-72 output view is structurally different.
Bit-exactness measured on one lowering is therefore not measured on the other,
and this tool will not transfer it.

Nothing here widens a check or rounds a count.  Uncovered classes are reported
as uncovered and the rung stays red.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import NO_ID  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import Instruction  # noqa: E402

import importlib.util  # noqa: E402


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_admission = _module("_g1a_adm", "tools/build_a3_operator_admission_vectors.py")
_scatter = _module("_g1a_sc", "tools/build_a3_qwen_kv_scatter_vectors.py")

SCHEMA = "opentallas.rtl.g1a_operator_equivalence.v1"
DEPLOYMENT_DIR = ROOT / "testdata/compiler/abi3_deployment"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_g1a_operator_equivalence.json"
WORKLOAD = "TA-QW-EOS-1"
ISSUE_STRIDE = 3
VIEW_STRIDE = 7
SLOT_FIELDS = (
    "input_view_0",
    "input_view_1",
    "input_view_2",
    "input_view_3",
    "output_view_0",
)

# The two storage classes G1a requires, and the deployment each one names.
STORAGE_CLASSES = {
    "rom": "qwen3-8b-rom-single-chip",
    "hbm": "qwen3-8b-hbm-single-chip",
}

# The retained RTL campaigns that may carry operator-equivalence evidence.
# Each is re-validated here before it is allowed to cover anything.
EVIDENCE_CAMPAIGNS = (
    "results/rtl/a3_operator_admission_campaign.json",
    "results/rtl/a3_qwen_gqa_campaign.json",
    "results/rtl/abi3_shipped_prefix_campaign.json",
)

# The vector index that says which operator descriptors a campaign actually
# drove, and in which direction.  A campaign with no such index covers nothing:
# "it passed" is not "it drove this class".
CAMPAIGN_VECTOR_INDEX = {
    "results/rtl/a3_operator_admission_campaign.json":
        "testdata/rtl/a3_operator_admission/index.json",
}


def _dig(body: Any, dotted: str) -> Any:
    node = body
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_hex(path: Path) -> list[int]:
    return [int(token, 16) for token in path.read_text().split()]


# --------------------------------------------------------------------------
# The class inventory, walked out of the retained streams.
# --------------------------------------------------------------------------
def inventory(manifest: dict[str, Any], images: dict[str, list[int]],
              deployment_key: str) -> dict[str, Any]:
    case = next(
        c for c in manifest["cases"]
        if c["deployment"] == deployment_key and c["request"] == "decode"
    )
    deployment = next(
        d for d in manifest["deployments"] if d["key"] == deployment_key
    )
    descriptor_base, program_base = _scatter.deployment_bases(manifest)[deployment_key]
    table, _ = _admission.build_table(
        images["descriptor"], descriptor_base, int(deployment["descriptor_count"])
    )

    issue_base, issue_count = case["issue_base"], case["issue_count"]
    view_base, view_count = case["view_base"], case["view_count"]
    issues = images["issue"]
    views = images["view"]

    cursor = 0
    classes: dict[tuple, dict[str, Any]] = {}
    problems: list[str] = []
    for step in range(issue_count):
        at = (issue_base + step) * ISSUE_STRIDE
        opcode, descriptor_id, instruction_index = issues[at:at + 3]
        family, sub = (opcode >> 8) & 0xFF, opcode & 0xFF
        try:
            operator = table.get(int(descriptor_id), ExtendedDescriptorType.OPERATOR)
        except Exception as exc:  # pragma: no cover - refused, not smoothed over
            problems.append(
                f"issue {step} at instruction {instruction_index}: "
                f"operator descriptor {descriptor_id}: {exc}"
            )
            continue
        slots = [int(operator.payload[f]) for f in SLOT_FIELDS]
        bound = [s for s in slots if s != NO_ID]
        group = [
            views[(view_base + cursor + i) * VIEW_STRIDE:
                  (view_base + cursor + i) * VIEW_STRIDE + VIEW_STRIDE]
            for i in range(len(bound))
        ]
        cursor += len(bound)
        shape = tuple(
            (int(v[1]), int(v[2]), int(v[6]), int(v[5])) for v in group
        )
        numeric_id = int(operator.payload["numeric_profile_id"])
        contract = None
        if numeric_id != NO_ID:
            numeric = table.get(numeric_id, ExtendedDescriptorType.NUMERIC)
            raw = numeric.payload.get("contract_digest")
            contract = raw.hex() if isinstance(raw, (bytes, bytearray)) else str(raw)
        mnemonic = Instruction.decode(
            images["program"][program_base + int(instruction_index)].to_bytes(32, "little")
        ).mnemonic
        key = (family, sub, mnemonic, contract, shape)
        entry = classes.setdefault(
            key, {"issues": 0, "pcs": set(), "operators": set()}
        )
        entry["issues"] += 1
        entry["pcs"].add(int(instruction_index))
        entry["operators"].add(int(descriptor_id))

    if cursor != view_count:
        problems.append(
            f"the walk consumed {cursor} resolved views of {view_count}: the "
            "issue and view streams do not correspond and the inventory is "
            "not trustworthy"
        )

    ordered = [
        {
            "family": key[0],
            "sub": key[1],
            "mnemonic": key[2],
            "numeric_contract_sha256": key[3],
            "resolved_shape": [list(s) for s in key[4]],
            "shape_fields": ["slot", "extent", "extent_axis", "rank"],
            "issues": value["issues"],
            "program_counters": sorted(value["pcs"]),
            "operator_descriptor_ids": sorted(value["operators"]),
        }
        for key, value in sorted(
            classes.items(),
            key=lambda kv: (kv[0][0], kv[0][1], str(kv[0][3]), str(kv[0][4])),
        )
    ]
    return {
        "deployment": deployment_key,
        "deployment_sha256": deployment["deployment_sha256"],
        "program_sha256": deployment["program_sha256"],
        "descriptor_table_sha256": deployment["descriptor_table_sha256"],
        "instruction_count": int(deployment["instruction_count"]),
        "entrypoint": "decode",
        "issued_instance_count": issue_count,
        "resolved_view_count": view_count,
        "resolved_views_consumed": cursor,
        "streams_correspond": cursor == view_count and not problems,
        "problems": problems,
        "classes": ordered,
    }


# --------------------------------------------------------------------------
# Evidence: retained campaigns, re-validated against the tree as it is now.
# --------------------------------------------------------------------------
def _bound_pairs(body: dict[str, Any]) -> list[tuple[str, str]]:
    """Every (repository path, sha256) a campaign artifact binds."""
    pairs: list[tuple[str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("path"), str) and isinstance(node.get("sha256"), str):
                pairs.append((node["path"], node["sha256"]))
                return
            for key, value in node.items():
                if isinstance(value, str) and len(value) == 64 and "/" in key:
                    pairs.append((key, value))
                elif isinstance(value, dict) and isinstance(value.get("sha256"), str) \
                        and "/" in key and "path" not in value:
                    pairs.append((key, value["sha256"]))
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for section in ("source", "source_sha256", "sources", "vector_set", "vector_sha256"):
        if section in body:
            walk(body[section])
    return pairs


def _resolve(relative: str) -> Path | None:
    for candidate in (ROOT / relative, ROOT / "testdata/rtl" / relative):
        if candidate.is_file():
            return candidate
    return None


def evidence() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for relative in EVIDENCE_CAMPAIGNS:
        path = ROOT / relative
        if not path.is_file():
            out.append({"artifact": relative, "usable": False,
                        "why": "artifact absent"})
            continue
        body = json.loads(path.read_text())
        drifted = []
        for bound, digest in _bound_pairs(body):
            resolved = _resolve(bound)
            if resolved is None:
                drifted.append(f"{bound} [missing]")
            elif sha256_file(resolved) != digest:
                drifted.append(bound)
        record: dict[str, Any] = {
            "artifact": relative,
            "artifact_sha256": sha256_file(path),
            "status": body.get("status"),
            "bound_source_count": len(_bound_pairs(body)),
            "drifted_source_count": len(drifted),
            "drifted_sources": sorted(drifted),
        }
        index_rel = CAMPAIGN_VECTOR_INDEX.get(relative)
        if index_rel and (ROOT / index_rel).is_file():
            index = json.loads((ROOT / index_rel).read_text())
            record["vector_index"] = index_rel
            record["target"] = index.get("target")
            record["target_deployment_sha256"] = index.get("deployment_sha256")
            # A positive case is one the vector set itself declares
            # non-faulting.  Taken from the record, never inferred from a name.
            positive = [
                c for c in index.get("cases", [])
                if not (c.get("expected") or {}).get("fault")
            ]
            record["positive_case_count"] = len(positive)
            record["positive_operator_descriptor_ids"] = sorted(
                {int(c["operator_descriptor_id"]) for c in positive
                 if c.get("operator_descriptor_id") is not None}
            )
            record["positive_program_counters"] = sorted(
                {int(c["pc"]) for c in positive if c.get("pc") is not None}
            )
            record["positive_family_subs"] = sorted(
                {(int(c["family"]), int(c["sub"])) for c in positive
                 if c.get("family") is not None}
            )
            declared = index.get("expected_pass") or {}
            if int(declared.get("positive", -1)) != len(positive):
                raise SystemExit(
                    f"{index_rel}: the vector index declares "
                    f"{declared.get('positive')} positive cases but "
                    f"{len(positive)} were identified; the coverage map would "
                    "rest on a guess about which cases are positive"
                )
            record["compared_words"] = int(
                (body.get("aggregate") or {}).get("admission_words_compared", 0)
            )
            record["simulated_cycles"] = sum(
                int(case.get("verification_cycles", 0))
                for bench in (body.get("normalized") or {}).values()
                for case in (bench.get("cases", []) if isinstance(bench, dict) else [])
            )
            # The simulators that actually produced a log, not the tool
            # inventory: yosys elaborated and vvp is Icarus's runtime, and
            # neither is a simulator that ran these cases.
            simulators = set()
            for key in (body.get("log_sha256") or {}):
                for name in ("iverilog", "verilator"):
                    if key.endswith("_" + name):
                        simulators.add({"iverilog": "icarus"}.get(name, name))
            record["simulators"] = sorted(simulators)
            record["simulator_versions"] = {
                name: (body.get("tools") or {}).get(name, {}).get("version")
                for name in ("iverilog", "verilator")
                if name in (body.get("tools") or {})
            }
            record["simulators_agree"] = body.get("simulators_agree")
        # Which program counters this campaign names, per case, and which
        # deployment digest it ran them against.  For an artifact whose bound
        # sources have drifted this is not coverage; it is the record that the
        # class was once measured, under a lowering that has been superseded.
        named: dict[str, dict[str, Any]] = {}
        for section in ("checkpoint_rows", "checkpoint_gains",
                        "checkpoint_head_gains", "checkpoint_matrices",
                        "rope_operations", "fault_sites"):
            for item in (body.get(section) or []):
                case = str(item.get("case", ""))
                if not case or item.get("operator_pc") is None:
                    continue
                slot = named.setdefault(
                    case,
                    {"deployment_sha256": item.get("deployment_sha256"),
                     "program_counters": set()},
                )
                slot["program_counters"].add(int(item["operator_pc"]))
        if named:
            record["named_program_counters_by_case"] = {
                case: {
                    "deployment_sha256": slot["deployment_sha256"],
                    "program_counters": sorted(slot["program_counters"]),
                }
                for case, slot in sorted(named.items())
            }

        # Did the campaign itself declare the tree it ran in?  Most of these
        # bind source digests instead of a git block, which is a weaker claim
        # and is reported as one rather than inherited silently by this rung.
        record["declares_own_git_state"] = "git" in body
        record["declared_worktree_dirty"] = _dig(body, "git.worktree_dirty")

        record["usable"] = (
            body.get("status") == "pass" and not drifted and "target" in record
        )
        if not record["usable"]:
            reasons = []
            if body.get("status") != "pass":
                reasons.append(f"status is {body.get('status')!r}")
            if drifted:
                reasons.append(
                    f"{len(drifted)} bound source(s) have drifted since it was recorded"
                )
            if "target" not in record:
                reasons.append(
                    "no retained vector index names the operator descriptors it drove, "
                    "so it cannot be said to cover any particular class"
                )
            record["why_unusable"] = "; ".join(reasons)
        out.append(record)
    return out



# --------------------------------------------------------------------------
# Why ROM evidence is not HBM evidence, computed rather than argued.
# --------------------------------------------------------------------------
def cross_lowering_transfer(manifest: dict[str, Any], images: dict[str, list[int]],
                            program_counters: list[int]) -> dict[str, Any]:
    """Diff the two lowerings' descriptors at the PCs a campaign covered.

    If they were identical apart from descriptor ids, evidence measured on one
    would carry to the other and the artifact should say so.  They are not, and
    the exact fields that differ are listed here so the claim is checkable.
    """
    per_target: dict[str, dict[int, Any]] = {}
    for storage_class, key in STORAGE_CLASSES.items():
        deployment = next(d for d in manifest["deployments"] if d["key"] == key)
        descriptor_base, program_base = _scatter.deployment_bases(manifest)[key]
        table, _ = _admission.build_table(
            images["descriptor"], descriptor_base, int(deployment["descriptor_count"])
        )
        entries: dict[int, Any] = {}
        for pc in program_counters:
            instruction = Instruction.decode(
                images["program"][program_base + pc].to_bytes(32, "little")
            )
            operator = table.get(int(instruction.descriptor_id),
                                 ExtendedDescriptorType.OPERATOR)

            def plain(payload: dict[str, Any]) -> dict[str, Any]:
                return {
                    k: (v.hex() if isinstance(v, (bytes, bytearray)) else v)
                    for k, v in payload.items()
                }

            numeric_id = int(operator.payload["numeric_profile_id"])
            numeric = (
                plain(table.get(numeric_id, ExtendedDescriptorType.NUMERIC).payload)
                if numeric_id != NO_ID else None
            )
            views = {}
            for slot, field in enumerate(SLOT_FIELDS):
                view_id = int(operator.payload[field])
                if view_id == NO_ID:
                    continue
                views[slot] = plain(
                    table.get(view_id, ExtendedDescriptorType.TENSOR_VIEW).payload
                )
            entries[pc] = {
                "mnemonic": instruction.mnemonic,
                "operator_descriptor_id": int(instruction.descriptor_id),
                "operator": plain(operator.payload),
                "numeric": numeric,
                "views": views,
            }
        per_target[storage_class] = entries

    reference_fields = set(SLOT_FIELDS) | {"numeric_profile_id", "schedule_id"}
    differences = []
    for pc in program_counters:
        rom, hbm = per_target["rom"][pc], per_target["hbm"][pc]
        fields: list[str] = []
        for name in sorted(set(rom["operator"]) | set(hbm["operator"])):
            if name in reference_fields:
                continue
            if rom["operator"].get(name) != hbm["operator"].get(name):
                fields.append(f"operator.{name}")
        for name in sorted(set(rom["numeric"] or {}) | set(hbm["numeric"] or {})):
            if (rom["numeric"] or {}).get(name) != (hbm["numeric"] or {}).get(name):
                fields.append(f"numeric.{name}")
        for slot in sorted(set(rom["views"]) | set(hbm["views"])):
            a, b = rom["views"].get(slot, {}), hbm["views"].get(slot, {})
            for name in sorted(set(a) | set(b)):
                if a.get(name) != b.get(name):
                    fields.append(f"view[{slot}].{name}")
        differences.append({
            "program_counter": pc,
            "mnemonic": rom["mnemonic"],
            "rom_operator_descriptor_id": rom["operator_descriptor_id"],
            "hbm_operator_descriptor_id": hbm["operator_descriptor_id"],
            "differing_fields": fields,
            "identical": not fields,
        })
    return {
        "note": (
            "The two Qwen lowerings do not emit identical descriptors for the "
            "same equivalence class, so bit-exactness measured on one is not "
            "measured on the other and this artifact does not transfer it. "
            "The fields listed here are the difference, computed from the "
            "retained descriptor image; object ids and view/numeric descriptor "
            "REFERENCES are excluded, since a differing reference to an "
            "identical descriptor would not change what the datapath sees."
        ),
        "program_counters": list(program_counters),
        "identical_program_counter_count": sum(
            1 for d in differences if d["identical"]
        ),
        "differing_program_counter_count": sum(
            1 for d in differences if not d["identical"]
        ),
        "per_program_counter": differences,
    }


# --------------------------------------------------------------------------
def build(output: Path) -> dict[str, Any]:
    manifest = json.loads((DEPLOYMENT_DIR / "abi3_deployment_rtl_vectors.json").read_text())
    images = {
        "descriptor": read_hex(DEPLOYMENT_DIR / "a3_descriptor.hex"),
        "program": read_hex(DEPLOYMENT_DIR / "a3_program.hex"),
        "issue": read_hex(DEPLOYMENT_DIR / "a3_deployment_issue.hex"),
        "view": read_hex(DEPLOYMENT_DIR / "a3_deployment_view.hex"),
    }
    campaigns = evidence()
    usable = [c for c in campaigns if c.get("usable")]

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    dirty = bool(porcelain)

    records = []
    for storage_class, deployment_key in STORAGE_CLASSES.items():
        inv = inventory(manifest, images, deployment_key)
        covering = [
            c for c in usable
            if c.get("target_deployment_sha256") == inv["deployment_sha256"]
        ]
        classes = []
        for entry in inv["classes"]:
            hit = None
            for campaign in covering:
                wanted = set(entry["operator_descriptor_ids"])
                if (entry["family"], entry["sub"]) in {
                    tuple(p) for p in campaign["positive_family_subs"]
                } and wanted <= set(campaign["positive_operator_descriptor_ids"]):
                    hit = campaign
                    break
            item = dict(entry)
            item["covered"] = hit is not None
            if hit is not None:
                item["covered_by"] = hit["artifact"]
                item["covered_by_sha256"] = hit["artifact_sha256"]
            else:
                item["why_not_covered"] = (
                    "no source-current retained RTL campaign drove operator "
                    f"descriptor(s) {entry['operator_descriptor_ids']} of this "
                    f"deployment ({inv['deployment_sha256'][:12]}) in a positive case"
                )
                stale = []
                for campaign in campaigns:
                    if campaign.get("usable"):
                        continue
                    for case, slot in (
                        campaign.get("named_program_counters_by_case") or {}
                    ).items():
                        if not case.startswith(inv["deployment"] + "/"):
                            continue
                        hit_pcs = sorted(
                            set(entry["program_counters"])
                            & set(slot["program_counters"])
                        )
                        if hit_pcs:
                            stale.append({
                                "artifact": campaign["artifact"],
                                "case": case,
                                "program_counters": hit_pcs,
                                "against_deployment_sha256": slot["deployment_sha256"],
                                "is_the_deployment_this_record_names": (
                                    str(slot["deployment_sha256"]) ==
                                    inv["deployment_sha256"]
                                ),
                            })
                if stale:
                    item["measured_once_under_a_superseded_lowering"] = stale
                    item["why_not_covered"] += (
                        "; it was measured under a superseded lowering, whose "
                        "campaign artifact no longer binds the tree"
                    )
            classes.append(item)

        covered = [c for c in classes if c["covered"]]
        uncovered = [c for c in classes if not c["covered"]]
        cycles = sum(c.get("simulated_cycles", 0) for c in covering)
        compared = sum(c.get("compared_words", 0) for c in covering)
        simulators = sorted({s for c in covering for s in c.get("simulators", [])})

        # Every class that consumes a real checkpoint tensor.  If any of them is
        # uncovered, the rung has not run against the real checkpoint weights,
        # whatever the covered classes did.
        weighted = {
            "TENSOR.MATMUL", "TENSOR.EMBED_LOOKUP", "VECTOR.RMS_NORM",
            "VECTOR.HEAD_RMS_NORM", "VECTOR.ROPE",
        }
        weighted_classes = [c for c in classes if c["mnemonic"] in weighted]
        weighted_covered = [c for c in weighted_classes if c["covered"]]

        record: dict[str, Any] = {
            "storage_class": storage_class,
            "workload_id": WORKLOAD,
            "deployment": {
                "key": inv["deployment"],
                "deployment_sha256": inv["deployment_sha256"],
                "program_sha256": inv["program_sha256"],
                "descriptor_table_sha256": inv["descriptor_table_sha256"],
                "instruction_count": inv["instruction_count"],
                "entrypoint": inv["entrypoint"],
            },
            "execution": {
                "simulator": (", ".join(simulators) if simulators else None),
                "simulators": simulators,
                "simulated_cycles": cycles,
                "evidence_class": (
                    "public_open_tool_rtl_simulation_dual_simulator"
                    if simulators
                    else "absent: no simulation of this lowering exists"
                ),
                "campaigns": [c["artifact"] for c in covering],
                "underlying_campaign_provenance": [
                    {
                        "artifact": c["artifact"],
                        "declares_own_git_state": c.get("declares_own_git_state"),
                        "declared_worktree_dirty": c.get("declared_worktree_dirty"),
                        "binds_every_source_digest_and_they_all_match": (
                            c.get("drifted_source_count") == 0
                        ),
                        "bound_source_count": c.get("bound_source_count"),
                        "note": (
                            "this campaign does not declare the worktree it ran "
                            "in; what binds it to committed bytes is that every "
                            "source and vector digest it recorded still matches "
                            "the tree, recomputed here"
                        ) if not c.get("declares_own_git_state") else None,
                    }
                    for c in covering
                ],
                "campaigns_considered_and_refused": [
                    {"artifact": c["artifact"], "why": c.get("why_unusable")}
                    for c in campaigns if not c.get("usable")
                ],
            },
            "git": {
                "commit": commit,
                "worktree_dirty": dirty,
                "scope": (
                    "the tree THIS artifact was derived in. It is not a claim "
                    "about the tree each underlying RTL campaign ran in; see "
                    "execution.underlying_campaign_provenance."
                ),
            },
            "coverage": {
                "issued_class_count": len(classes),
                "covered_class_count": len(covered),
                "uncovered_class_count": len(uncovered),
                "every_issued_class_covered": bool(classes) and not uncovered,
                "issued_instance_count": inv["issued_instance_count"],
                "covered_instance_count": sum(c["issues"] for c in covered),
                "uncovered_instance_count": sum(c["issues"] for c in uncovered),
                "resolved_view_count": inv["resolved_view_count"],
                "resolved_views_consumed": inv["resolved_views_consumed"],
                "inventory_streams_correspond": inv["streams_correspond"],
                "inventory_problems": inv["problems"],
                "classes": classes,
            },
            "equivalence": {
                "compared_words": compared,
                "mismatched_words": 0 if compared else None,
                "mismatched_words_note": (
                    None if compared else
                    "no words were compared under this lowering; a mismatch "
                    "count over zero comparisons is not a zero mismatch count, "
                    "and is reported as absent rather than as zero"
                ),
                "weights_are_real_checkpoint": bool(weighted_classes)
                and len(weighted_covered) == len(weighted_classes),
                "checkpoint_weighted_class_count": len(weighted_classes),
                "checkpoint_weighted_covered_class_count": len(weighted_covered),
                "weights_note": (
                    "Every class that consumes a real checkpoint tensor -- "
                    "TENSOR.MATMUL, TENSOR.EMBED_LOOKUP, VECTOR.RMS_NORM, "
                    "VECTOR.HEAD_RMS_NORM, VECTOR.ROPE -- must be covered "
                    "before this is true. The covered set is otherwise the "
                    "weightless operators, whose operands in the retained "
                    "campaign are a seeded deterministic BF16 spread and "
                    "authentic retained RTL activations, not checkpoint weights."
                ),
            },
        }
        records.append(record)

    # capability_trapped_family_count, in its PESSIMISTIC form.  Two vehicles
    # give two answers and post-mortem R13 forbids publishing the optimistic
    # one: the operator-admission vehicle admits all six families (measured,
    # capability_trapped_family_count 0), and the vehicle that runs the real
    # compiled program end to end, rtl/test/a3_shipped_prefix_top.sv, answers
    # separately.  The integrated vehicle's answer is the one published here,
    # and it is read from that vehicle's own campaign artifact: which of the
    # six the bridge LAUNCHED, per family, in a case whose result words were
    # compared against golden.  A family the integrated campaign did not
    # launch is trapped here, and so is every family when that campaign is
    # absent, failed, drifted, or predates the measurement -- absence of
    # evidence is a FAIL, never "not evaluable".
    integrated_relative = "results/rtl/abi3_shipped_prefix_campaign.json"
    integrated_path = ROOT / integrated_relative
    integrated_record = next(
        (c for c in campaigns if c["artifact"] == integrated_relative), None
    )
    integrated_body = (
        json.loads(integrated_path.read_text()) if integrated_path.is_file() else {}
    )
    # The integrated vehicle's answer is taken from what it MEASURED, never
    # from whether its source text mentions the bridge's placement pins.  A
    # port connection is not a launch: the previous form of this block grepped
    # rtl/test/a3_shipped_prefix_top.sv for ".cfg_extended_placement_valid("
    # and would have reported zero trapped families the moment the pin was
    # connected, before a single family had run.  The measurement is the
    # harness's ADMISSION line, per family, and it counts a family only when
    # the bridge launched it in a case whose result words were compared
    # against golden.
    integrated_admission = integrated_body.get("operator_admission") or {}
    integrated_fresh = bool(
        integrated_record
        and integrated_record.get("status") == "pass"
        and integrated_record.get("drifted_source_count") == 0
    )
    integrated_reached = (
        list(integrated_admission.get("reached_families") or [])
        if (integrated_fresh and integrated_admission.get("measured"))
        else []
    )
    admission_body = json.loads(
        (ROOT / "results/rtl/a3_operator_admission_campaign.json").read_text()
    ) if (ROOT / "results/rtl/a3_operator_admission_campaign.json").is_file() else {}
    admitted = (admission_body.get("admission") or {}).get(
        "previously_capability_trapped_families", []
    )
    integrated_trapped = [f for f in admitted if f not in integrated_reached]
    trapped = len(integrated_trapped)
    why_not_measured = []
    if not integrated_path.is_file():
        why_not_measured.append(f"{integrated_relative} is absent")
    elif integrated_record is None:
        why_not_measured.append(
            f"{integrated_relative} is not in this tool's evidence list"
        )
    else:
        if integrated_record.get("status") != "pass":
            why_not_measured.append(
                f"{integrated_relative} status is "
                f"{integrated_record.get('status')!r}"
            )
        if integrated_record.get("drifted_source_count"):
            why_not_measured.append(
                f"{integrated_record['drifted_source_count']} of its bound "
                "sources have drifted since it was recorded"
            )
        if not integrated_admission:
            why_not_measured.append(
                "it records no operator_admission block, so it predates the "
                "measurement and cannot be read as one"
            )
        elif not integrated_admission.get("measured"):
            why_not_measured.append(
                str(integrated_admission.get("why_not_measured")
                    or "its run emitted no ADMISSION line")
            )
    for record in records:
        record["capability_trapped_family_count"] = trapped
        record["capability"] = {
            "reported_form": "pessimistic",
            "why_pessimistic": (
                "post-mortem R13: a metric reported under two models is not "
                "evidence in its optimistic form. The two models here are the "
                "operator-admission vehicle and the integrated shipped-prefix "
                "vehicle, and this is the integrated vehicle's answer."
            ),
            "source_of_this_count": (
                "measured launches in the integrated vehicle's own campaign "
                "artifact, not the presence of a port connection in its source"
            ),
            "integrated_vehicle": "rtl/test/a3_shipped_prefix_top.sv",
            "integrated_vehicle_campaign": integrated_relative,
            "integrated_vehicle_campaign_usable": integrated_fresh,
            "integrated_vehicle_measured": bool(
                integrated_fresh and integrated_admission.get("measured")
            ),
            "integrated_vehicle_launches": integrated_admission.get("launches"),
            "integrated_vehicle_reached_families": integrated_reached,
            "integrated_vehicle_trapped_families": integrated_trapped,
            "why_not_measured": why_not_measured,
            "operator_admission_vehicle_trapped_family_count": (
                admission_body.get("admission") or {}
            ).get("capability_trapped_family_count"),
            "operator_admission_vehicle_admitted_family_count": (
                admission_body.get("admission") or {}
            ).get("admitted_family_count"),
        }

    artifact = {
        "schema": SCHEMA,
        "gate": "G1a",
        "workload_id": WORKLOAD,
        "generated_by": "tools/build_abi3_g1a_operator_equivalence.py",
        "generated_by_sha256": sha256_file(Path(__file__)),
        "derived_mechanically": True,
        "class_definition": (
            "(family, sub, mnemonic, numeric contract digest, resolved shape), "
            "where the resolved shape is the per-slot "
            "(slot, extent, extent_axis, rank) of the issue's own resolved views"
        ),
        "inventory_source": {
            "path": "testdata/compiler/abi3_deployment",
            "issue_stream": manifest["issue_reference"],
            "view_stream": manifest["view_reference"],
            "files": {
                name: sha256_file(DEPLOYMENT_DIR / name)
                for name in (
                    "abi3_deployment_rtl_vectors.json",
                    "a3_descriptor.hex",
                    "a3_program.hex",
                    "a3_deployment_issue.hex",
                    "a3_deployment_view.hex",
                )
            },
        },
        "evidence_campaigns": campaigns,
        "cross_lowering_transfer": cross_lowering_transfer(
            manifest,
            images,
            sorted({
                pc
                for campaign in usable
                for pc in campaign.get("positive_program_counters", [])
            }),
        ),
        "summary": [
            (
                f"{r['storage_class']}: {r['coverage']['covered_class_count']} of "
                f"{r['coverage']['issued_class_count']} issued equivalence classes "
                f"covered bit-exactly ({r['coverage']['covered_instance_count']} of "
                f"{r['coverage']['issued_instance_count']} issued instances); "
                f"{r['coverage']['uncovered_class_count']} uncovered; "
                f"{r['equivalence']['compared_words']} words compared, "
                f"{r['equivalence']['mismatched_words']} mismatched; "
                f"real checkpoint weights: "
                f"{r['equivalence']['weights_are_real_checkpoint']}; "
                f"capability-trapped families (pessimistic form): "
                f"{r['capability_trapped_family_count']}"
            )
            for r in records
        ],
        "status": "fail" if any(
            r["coverage"]["uncovered_class_count"] or r["capability_trapped_family_count"]
            or not r["equivalence"]["weights_are_real_checkpoint"]
            for r in records
        ) else "pass",
        "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    artifact = build(args.output)
    print(f"G1a operator-equivalence artifact status={artifact['status']}")
    for record in artifact["records"]:
        coverage = record["coverage"]
        print(
            f"  {record['storage_class']:<4} "
            f"covered {coverage['covered_class_count']}/"
            f"{coverage['issued_class_count']} classes, "
            f"uncovered {coverage['uncovered_class_count']}, "
            f"instances {coverage['covered_instance_count']}/"
            f"{coverage['issued_instance_count']}, "
            f"cycles {record['execution']['simulated_cycles']}, "
            f"capability-trapped {record['capability_trapped_family_count']}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
