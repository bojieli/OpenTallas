#!/usr/bin/env python3
"""Measure how far the G1d head span executes in the integrated vehicle, and what refuses it.

``docs/CHIP_ARCHITECTURE_DESIGN.md`` section 11.7 records one runnable leg of
the ladder -- the head span, entry 65, PCs 66/68/69/70, ending in
``SELECTION.ARGMAX`` -- and records that a re-run of the vehicle entry probe
found its positive control returning ``TRAP_DESCRIPTOR`` at PC 66 with zero
engine launches where it used to launch an engine and run 33,047 cycles.  That
observation is a trap class and a PC.  It does not say WHICH of the refusals
the design can produce fired, and a trap class is not an attribution: the same
class is raised by the placement table, by every operand view predicate and by
every result view predicate in ``rtl/abi3/ot_a3_engine_issue_bridge.sv``.

This campaign attributes it, by measurement rather than by reading the
predicate.  One binary is elaborated from committed source and is NOT rebuilt
between arms.  The only thing that changes from arm to arm is the object
placement table the design is configured with **through its own configuration
port** -- the surface the vector set drives, one entry per ABI object, an
object id and the base its data sits at.  A refusal that moves when one
object's entry moves, and that does not move when an object the refused
instruction also names is added, is attributable to that object and to nothing
else in the vehicle.

Three things this campaign does NOT establish, stated here so no reader has to
infer them:

* **No numeric claim.**  An arm binds an added object at a declared base with
  nothing staged there, so the words an admitted engine writes are not the
  words the checkpoint implies.  No arm compares a word against golden and
  none is reported.  What is measured is admission and control: which
  instruction the design dispatches, which it refuses, with what class, at
  what PC, and how many engines it launched.
* **It is not gate G1d.**  G1d asks for the head to execute on the COMPOSED
  TRUNK OUTPUT with its logits compared.  A mid-program entry runs on the
  vehicle's initialised result memory; no trunk has run.
* **The added table entries are not a proposal for the shipped vector set.**
  They are a probe.  What they measure is what the shipped vector set would
  have to bind, and what binding it would still not be enough for.

The span, its entry and its objects are all derived from the deployment's own
program body and descriptor table.  Nothing about the span is written down
here: the site is the program's own ``SELECTION.ARGMAX``, the entry is the
greatest PC from which the abstract machine of
``tools/build_abi3_vehicle_reachability.py`` -- whose transitions are the
sequencer's -- reaches the fetch bound one past the site, and an instruction's
objects are the ``primary_object_id`` of each operand and result view its
operator descriptor names, which is the field
``ot_a3_engine_issue_bridge.sv`` resolves through the table.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import Major, Selection, Tensor  # noqa: E402
from tools import rtl_abi3_shipped_prefix_campaign as prefix  # noqa: E402
from tools import build_abi3_vehicle_reachability as reach  # noqa: E402
from tools.build_abi3_shipped_prefix_vectors import (  # noqa: E402
    CASE_STRIDE,
    TARGETS,
    _deployment_vectors,
)

SCHEMA = "opentallas.rtl.abi3_g1d_head_span_probe.v1"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_g1d_head_span_probe.json"
MARKER = "PASS: ABI3 vehicle entry probe"
NO_ID = 0xFFFF_FFFF
# Case-record word offsets, valid at the 139-word placed generation only.
# They are the harness's own constants (rtl/test/a3_shipped_prefix_harness.cpp
# kPlaceValidWord / kPlaceTableWord / kPlaceTableEntries) and the campaign
# refuses a vector set of any other generation rather than reinterpreting one.
PLACE_VALID_WORD = 58
PLACE_TABLE_WORD = 60
PLACE_TABLE_ENTRIES = 32
# Where an arm binds an object the shipped table does not name.  Declared, not
# chosen per arm, because a base that varied between arms would make a moved
# refusal ambiguous between the object and its address.  Nothing is staged
# there; see the module docstring on why no arm makes a numeric claim.
PROBE_BASE = 0
# The most a bracket span may cost.  At the measured integrated rate this is
# about ten minutes of one core; a bracket that cost a layer would be the
# whole campaign again for a number the ladder already brackets from above.
MAX_BRACKET_MACS = 20_000_000
TRAP_DESCRIPTOR = 3
TRAP_ILLEGAL = 5
TRAP_INTERNAL = 13
PROBE_RE = re.compile(
    r"^PROBE case=(?P<case>\d+) entry=(?P<entry>\d+) ic=(?P<ic>\d+) "
    r"trap=(?P<trap>\d+) fault=(?P<fault>\d+) launches=(?P<launches>\d+) "
    r"issued=(?P<issued>\d+) fetched=(?P<fetched>\d+) retired=(?P<retired>\d+) "
    r"capability=(?P<capability>\d+) cycles=(?P<cycles>\d+)$",
    re.MULTILINE,
)
VIEW_ROLES = (
    "input_view_0",
    "input_view_1",
    "input_view_2",
    "input_view_3",
    "output_view_0",
    "output_view_1",
)


def _git_state() -> dict[str, Any]:
    """The tree THIS artifact was derived in, and whether it was clean."""

    def one(args: list[str]) -> str:
        return subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout.strip()

    porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.rstrip("\n")
    dirty = sorted(
        line[3:].strip() for line in porcelain.splitlines() if len(line) > 3
    )
    return {
        "commit": one(["git", "rev-parse", "HEAD"]) or None,
        "worktree_dirty": bool(dirty),
        "dirty_paths": dirty,
        "scope": "the tree this campaign elaborated and ran from",
    }


def _read_hex(path: Path) -> list[int]:
    return [int(word, 16) for word in path.read_text(encoding="utf-8").split()]


def _write_hex(path: Path, words: list[int]) -> None:
    path.write_text("".join(f"{word:08x}\n" for word in words), encoding="utf-8")


def _views_of(program: reach.Program, pc: int) -> list[dict[str, Any]]:
    """Every operand and result view the instruction at ``pc`` names, in role order."""
    instruction = program.instructions[pc]
    descriptor_id = int(instruction.descriptor_id)
    if descriptor_id == NO_ID:
        return []
    payload = program.table.get(descriptor_id).payload
    out: list[dict[str, Any]] = []
    for role in VIEW_ROLES:
        view_id = int(payload.get(role, NO_ID))
        if view_id == NO_ID:
            continue
        view = program.table.get(view_id)
        body = view.payload
        out.append(
            {
                "role": role,
                "view_descriptor_id": view_id,
                "object_id": int(view.primary_object_id),
                "dtype": int(body["dtype"]),
                "rank": int(body["rank"]),
                "dims": [int(body[f"dim{axis}"]) for axis in range(6)],
                "strides": [int(body[f"stride{axis}"]) for axis in range(6)],
            }
        )
    return out


def _span(program: reach.Program) -> dict[str, Any]:
    """The head span, derived: its site, its entry and the instructions between."""
    sites = [
        pc
        for pc, instruction in enumerate(program.instructions)
        if int(instruction.major) == int(Major.SELECTION)
        and int(instruction.sub) == int(Selection.ARGMAX)
    ]
    if len(sites) != 1:
        raise SystemExit(
            f"{program.target.key}: expected exactly one SELECTION.ARGMAX, "
            f"found {len(sites)}"
        )
    site = sites[0]
    entry = None
    for candidate in range(site, -1, -1):
        run = reach.simulate(program, candidate, site + 1)
        if (
            run["outcome"] == "trap"
            and run["trap_class"] == TRAP_ILLEGAL
            and run["trap_pc"] == site + 1
        ):
            entry = candidate
            break
    if entry is None:
        raise SystemExit(
            f"{program.target.key}: no straight-line entry reaches PC {site}"
        )
    run = reach.simulate(program, entry, site + 1)
    return {
        "site_pc": site,
        "entry_pc": entry,
        "instruction_count": site + 1,
        "derived_by": (
            "the greatest entry from which the abstract machine of "
            "tools/build_abi3_vehicle_reachability.py reaches the fetch bound "
            "one past the site without a wait-set or loop-stack refusal"
        ),
        "issued_pcs": [int(record["pc"]) for record in run["issued"]],
        "macs": int(run["macs"]),
    }


class Bench:
    """One elaborated binary, driven with a different placement table per arm."""

    def __init__(self, build: Path, vectors: dict[str, Any]) -> None:
        self.build = build
        self.vectors = vectors
        self.base_case_words = _read_hex(build / "p3_case.hex")
        meta = _read_hex(build / "p3_meta.hex")
        stride = meta[4] if len(meta) > 4 else 0
        if stride != CASE_STRIDE:
            raise SystemExit(
                "this campaign is qualified against the placed case-record "
                f"generation ({CASE_STRIDE} words); the vector set states "
                f"{stride}"
            )
        self.stride = stride

    def committed_table(self, case_index: int) -> list[tuple[int, int]]:
        record = self.base_case_words[
            case_index * self.stride : (case_index + 1) * self.stride
        ]
        if record[PLACE_VALID_WORD] == 0:
            return []
        entries = [
            (
                record[PLACE_TABLE_WORD + 2 * slot],
                record[PLACE_TABLE_WORD + 2 * slot + 1],
            )
            for slot in range(PLACE_TABLE_ENTRIES)
        ]
        return [entry for entry in entries if entry[0] != NO_ID]

    def run(
        self, tables: dict[int, list[tuple[int, int]]], plan: list[tuple[int, int, int]]
    ) -> dict[str, Any]:
        words = list(self.base_case_words)
        for case_index, entries in tables.items():
            if len(entries) > PLACE_TABLE_ENTRIES:
                raise SystemExit(
                    f"case {case_index}: {len(entries)} entries exceed the "
                    f"{PLACE_TABLE_ENTRIES}-entry table the record carries"
                )
            objects = [entry[0] for entry in entries]
            if len(set(objects)) != len(objects):
                raise SystemExit(
                    f"case {case_index}: an object is bound twice, which the "
                    "bridge refuses before anything is fetched"
                )
            padded = list(entries) + [(NO_ID, 0)] * (
                PLACE_TABLE_ENTRIES - len(entries)
            )
            offset = case_index * self.stride + PLACE_TABLE_WORD
            for slot, (object_id, base) in enumerate(padded):
                words[offset + 2 * slot] = object_id
                words[offset + 2 * slot + 1] = base
        _write_hex(self.build / "p3_case.hex", words)
        (self.build / "arm_plan.txt").write_text(
            "".join(f"{case} {entry} {bound}\n" for case, entry, bound in plan),
            encoding="utf-8",
        )
        environment = dict(os.environ)
        environment["OT_A3_ENTRY_PROBE"] = "arm_plan.txt"
        started = time.time()
        result = subprocess.run(
            ["./obj_probe/Vot_a3_shipped_prefix_top"],
            cwd=self.build,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=environment,
            timeout=21600,
        )
        _write_hex(self.build / "p3_case.hex", self.base_case_words)
        rows = [
            {key: int(value) for key, value in match.groupdict().items()}
            for match in PROBE_RE.finditer(result.stdout)
        ]
        return {
            "returncode": result.returncode,
            "marker_present": MARKER in result.stdout,
            "wall_seconds": round(time.time() - started, 3),
            "rows": rows,
            "log_tail": prefix.canonical(result.stdout[-2000:], self.build),
        }


def _elaborate(build: Path, vector_dir: Path) -> dict[str, Any]:
    for name in prefix.DEPLOYMENT_IMAGES:
        shutil.copy2(prefix.DEPLOYMENT_VECTOR_DIR / name, build / name)
    for name in prefix.VECTOR_FILES:
        shutil.copy2(vector_dir / name, build / name)
    vectors = prefix.load_vectors()
    if not (build / "p3_matmul_weight.bin").exists():
        prefix.stage_matmul_weight(vectors, build / "p3_matmul_weight.bin")
    verilator = prefix.resolve(
        "verilator",
        prefix.TOOLS_ROOT
        / f"verilator-{prefix.PINNED_VERILATOR_VERSION}/bin/verilator",
    )
    tools = {
        "verilator": prefix.tool_record(verilator, ["--version"]),
        "cxx": prefix.tool_record(prefix.resolve("g++", None), ["--version"]),
    }
    prefix.require_versions(tools)
    command = [
        str(verilator),
        "--cc",
        "--exe",
        "--build",
        "-j",
        "8",
        "-Wall",
        "-Wno-fatal",
        "-Wno-DECLFILENAME",
        "--top-module",
        "ot_a3_shipped_prefix_top",
        "--Mdir",
        "obj_probe",
        *[str(ROOT / path) for path in prefix.RTL_SOURCES],
        str(ROOT / "rtl/test/a3_engine_completion_adapter.sv"),
        str(ROOT / "rtl/test/a3_shipped_prefix_top.sv"),
        str(ROOT / "rtl/test/a3_shipped_prefix_harness.cpp"),
        "-CFLAGS",
        "-std=c++17 -O2",
    ]
    compiled = prefix.run_stage("headspan.compile", command, build, 7200)
    return {"tools": tools, "compile": compiled, "vectors": vectors}


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-root", type=Path, default=None)
    args = parser.parse_args(argv)

    deployment_vectors, _ = _deployment_vectors()
    shipped = {case["name"]: case for case in deployment_vectors["cases"]}
    qwen = [target for target in TARGETS if target.key.startswith("qwen3-8b-")]

    with tempfile.TemporaryDirectory(prefix="opentallas-a3-head-span-") as raw:
        build_dir = Path(args.build_root) if args.build_root else Path(raw)
        build_dir.mkdir(parents=True, exist_ok=True)
        elaboration = _elaborate(build_dir, prefix.VECTOR_DIR)
        vectors = elaboration["vectors"]
        case_index = {
            case["name"].split("/")[0]: index
            for index, case in enumerate(vectors["cases"])
        }
        bench = Bench(build_dir, vectors)

        programs: dict[str, reach.Program] = {}
        spans: dict[str, dict[str, Any]] = {}
        for target in qwen:
            case = shipped.get(f"{target.key}/decode")
            if case is None:
                raise SystemExit(f"no shipped decode case for {target.key}")
            symbols = {int(k): int(v) for k, v in case["symbols"].items()}
            program = reach.Program(target, symbols)
            programs[target.key] = program
            spans[target.key] = _span(program)

        entry_span = {
            target.key: spans[target.key]["entry_pc"] for target in qwen
        }
        bound_span = {
            target.key: spans[target.key]["instruction_count"] for target in qwen
        }

        # -- the ladder ------------------------------------------------------
        # Each arm runs the WHOLE span on both stores.  After each arm the
        # refused instruction's own objects that the table does not yet name
        # are added, and nothing else is.  The ladder stops when the refusal
        # stops moving, which is the arm that separates placement from
        # geometry.
        tables = {
            target.key: list(bench.committed_table(case_index[target.key]))
            for target in qwen
        }
        arms: list[dict[str, Any]] = []
        previous_fault: dict[str, int | None] = {t.key: None for t in qwen}
        for step in range(8):
            plan = [
                (case_index[t.key], entry_span[t.key], bound_span[t.key])
                for t in qwen
            ]
            measured = bench.run(
                {case_index[t.key]: tables[t.key] for t in qwen}, plan
            )
            per_target = {}
            additions: dict[str, list[dict[str, Any]]] = {}
            moved = False
            for index, target in enumerate(qwen):
                row = measured["rows"][index] if index < len(measured["rows"]) else None
                per_target[target.key] = {
                    "placement_table": [
                        {"object_id": o, "base_words": b}
                        for o, b in tables[target.key]
                    ],
                    "placement_table_entry_count": len(tables[target.key]),
                    "measured": row,
                }
                if row is None:
                    continue
                if previous_fault[target.key] != row["fault"]:
                    moved = True
                previous_fault[target.key] = row["fault"]
                program = programs[target.key]
                bound_objects = {o for o, _ in tables[target.key]}
                unplaced = []
                if row["trap"] == TRAP_DESCRIPTOR and row["fault"] < len(
                    program.instructions
                ):
                    for view in _views_of(program, row["fault"]):
                        if view["object_id"] not in bound_objects and not any(
                            entry["object_id"] == view["object_id"]
                            for entry in unplaced
                        ):
                            unplaced.append(view)
                per_target[target.key]["refused_instruction_views"] = (
                    _views_of(program, row["fault"])
                    if row["fault"] < len(program.instructions)
                    else []
                )
                per_target[target.key]["unplaced_objects_of_the_refusal"] = [
                    entry["object_id"] for entry in unplaced
                ]
                additions[target.key] = unplaced
            arms.append(
                {
                    "step": step,
                    "kind": "baseline" if step == 0 else "add_the_refusal's_own_unplaced_objects",
                    "entry_and_bound": {
                        t.key: [entry_span[t.key], bound_span[t.key]] for t in qwen
                    },
                    "returncode": measured["returncode"],
                    "marker_present": measured["marker_present"],
                    "wall_seconds": measured["wall_seconds"],
                    "targets": per_target,
                }
            )
            if step > 0 and not moved:
                break
            if not any(additions.get(t.key) for t in qwen):
                break
            for target in qwen:
                for view in additions.get(target.key, []):
                    tables[target.key].append((view["object_id"], PROBE_BASE))

        # -- the bound the entry probe's own positive control used ----------
        # Section 11.7 records that control returning TRAP_DESCRIPTOR at the
        # first engine instruction of this span with zero launches and 240
        # cycles.  That control stops one instruction past the site it probes,
        # not at the end of the span, so it is a different fetch bound from
        # the ladder's.  It is re-run here on the committed table so this
        # record carries the document's own number and shows it is the same
        # refusal at a different bound rather than a different measurement.
        historical: dict[str, Any] = {
            "kind": "the_entry_probe's_own_positive_control_bound",
            "targets": {},
        }
        historical_plan = []
        for target in qwen:
            program = programs[target.key]
            first_engine = next(
                pc
                for pc in spans[target.key]["issued_pcs"]
            )
            historical_plan.append(
                (
                    case_index[target.key],
                    entry_span[target.key],
                    first_engine + 1,
                )
            )
        historical_measured = bench.run(
            {
                case_index[t.key]: list(bench.committed_table(case_index[t.key]))
                for t in qwen
            },
            historical_plan,
        )
        for index, target in enumerate(qwen):
            historical["targets"][target.key] = {
                "entry_pc": historical_plan[index][1],
                "instruction_count": historical_plan[index][2],
                "measured": historical_measured["rows"][index]
                if index < len(historical_measured["rows"])
                else None,
            }

        # -- the attribution control ----------------------------------------
        # The ladder added entries and the refusal walked forward.  That is
        # consistent with the design reading the table, and it is also
        # consistent with the refusal walking forward for some other reason
        # while the table was ignored.  The control separates them by running
        # the ladder backwards: from the table the ladder ended with, each
        # object it ADDED is dropped on its own and the span is re-run.  An
        # object the design consults moves the refusal back to the
        # instruction that names it; an object it does not consult leaves the
        # measurement byte-identical.  Both outcomes are recorded, because
        # WHICH entries the design consults for this span is itself the
        # finding -- an operand still served by an unkeyed configuration base
        # shows up here as an added entry whose removal changes nothing.
        control: dict[str, Any] = {
            "kind": "drop_each_added_object_in_turn",
            "why": (
                "a refusal that walks forward as entries are added is only "
                "attributable to the table if removing an entry walks it "
                "back; this runs that direction"
            ),
            "targets": {},
        }
        committed_counts = {
            t.key: len(bench.committed_table(case_index[t.key])) for t in qwen
        }
        added_objects = {
            t.key: [
                entry[0] for entry in tables[t.key][committed_counts[t.key] :]
            ]
            for t in qwen
        }
        for target in qwen:
            control["targets"][target.key] = {
                "added_objects": added_objects[target.key],
                "drops": [],
            }
        widest = max(len(added_objects[t.key]) for t in qwen)
        for slot in range(widest):
            drop_tables = {}
            dropped_now: dict[str, int | None] = {}
            plan = []
            for target in qwen:
                objects = added_objects[target.key]
                choice = objects[slot] if slot < len(objects) else None
                dropped_now[target.key] = choice
                drop_tables[case_index[target.key]] = [
                    entry for entry in tables[target.key] if entry[0] != choice
                ]
                plan.append(
                    (
                        case_index[target.key],
                        entry_span[target.key],
                        bound_span[target.key],
                    )
                )
            measured = bench.run(drop_tables, plan)
            for index, target in enumerate(qwen):
                if dropped_now[target.key] is None:
                    continue
                row = (
                    measured["rows"][index]
                    if index < len(measured["rows"])
                    else None
                )
                final = arms[-1]["targets"][target.key]["measured"]
                control["targets"][target.key]["drops"].append(
                    {
                        "dropped_object_id": dropped_now[target.key],
                        "measured": row,
                        "refusal_moved_back": bool(
                            row is not None
                            and final is not None
                            and row["fault"] < final["fault"]
                        ),
                        "measurement_unchanged": bool(
                            row is not None
                            and final is not None
                            and row["fault"] == final["fault"]
                            and row["cycles"] == final["cycles"]
                            and row["launches"] == final["launches"]
                        ),
                        "wall_seconds": measured["wall_seconds"],
                    }
                )
        for target in qwen:
            drops = control["targets"][target.key]["drops"]
            control["targets"][target.key]["objects_the_design_consults"] = [
                drop["dropped_object_id"]
                for drop in drops
                if drop["refusal_moved_back"]
            ]
            control["targets"][target.key][
                "objects_added_that_the_design_never_read"
            ] = [
                drop["dropped_object_id"]
                for drop in drops
                if drop["measurement_unchanged"]
            ]
            control["targets"][target.key]["at_least_one_moved_back"] = any(
                drop["refusal_moved_back"] for drop in drops
            )

        # -- the admitted weight-view first dimension, measured --------------
        # The head's own MATMUL is refused.  What the design DOES admit is
        # measured in the same binary on the same span rule: the shipped
        # program's own earlier MATMULs, entered at the greatest PC from
        # which straight-line execution reaches them.  The largest first
        # dimension that launched is the bound every row-shard arithmetic
        # below is taken against, and it is a launch that happened rather
        # than a constant read out of the bridge.
        weight_admission: list[dict[str, Any]] = []
        for target in qwen:
            program = programs[target.key]
            for pc, instruction in enumerate(program.instructions):
                if int(instruction.major) != int(Major.TENSOR) or int(
                    instruction.sub
                ) != int(Tensor.MATMUL):
                    continue
                views = _views_of(program, pc)
                weight = next(
                    (v for v in views if v["role"] == "input_view_1"), None
                )
                if weight is None or weight["rank"] != 2:
                    continue
                weight_admission.append(
                    {
                        "target": target.key,
                        "pc": pc,
                        "weight_view_descriptor_id": weight["view_descriptor_id"],
                        "weight_object_id": weight["object_id"],
                        "weight_dims": weight["dims"][:2],
                    }
                )
        # Run only the two cheapest admitted candidates plus the head's own,
        # each on the ROM store, so the bracket costs one projection rather
        # than the whole layer.
        rom = qwen[0]
        rom_program = programs[rom.key]
        candidates = sorted(
            {
                entry["pc"]
                for entry in weight_admission
                if entry["target"] == rom.key
            }
        )
        bracket: list[dict[str, Any]] = []
        for pc in candidates:
            views = _views_of(rom_program, pc)
            weight = next((v for v in views if v["role"] == "input_view_1"), None)
            if weight is None or weight["rank"] != 2:
                continue
            first_dim = weight["dims"][0]
            if pc in spans[rom.key]["issued_pcs"]:
                # the head's own MATMUL is measured by the ladder above
                continue
            entry = None
            for candidate in range(pc, -1, -1):
                run = reach.simulate(rom_program, candidate, pc + 1)
                if (
                    run["outcome"] == "trap"
                    and run["trap_class"] == TRAP_ILLEGAL
                    and run["trap_pc"] == pc + 1
                ):
                    entry = candidate
                    break
            if entry is None:
                continue
            run = reach.simulate(rom_program, entry, pc + 1)
            if run["macs"] > MAX_BRACKET_MACS:
                # one projection, not the whole prefix: the bracket exists to
                # put a NUMBER on what launches, not to re-run the campaign
                continue
            measured = bench.run(
                {case_index[rom.key]: list(bench.committed_table(case_index[rom.key]))},
                [(case_index[rom.key], entry, pc + 1)],
            )
            row = measured["rows"][0] if measured["rows"] else None
            bracket.append(
                {
                    "target": rom.key,
                    "site_pc": pc,
                    "entry_pc": entry,
                    "instruction_count": pc + 1,
                    "issued_pcs": [int(r["pc"]) for r in run["issued"]],
                    "weight_view_first_dimension": first_dim,
                    "weight_view_dims": weight["dims"][:2],
                    "derived_macs_of_the_span": int(run["macs"]),
                    "measured": row,
                    "launched": bool(row is not None and row["launches"] > 0),
                    "wall_seconds": measured["wall_seconds"],
                }
            )

    admitted_first_dims = sorted(
        {entry["weight_view_first_dimension"] for entry in bracket if entry["launched"]}
    )
    largest_admitted = admitted_first_dims[-1] if admitted_first_dims else None
    head = {}
    for target in qwen:
        program = programs[target.key]
        span = spans[target.key]
        matmul_pc = next(
            (
                pc
                for pc in span["issued_pcs"]
                if int(program.instructions[pc].major) == int(Major.TENSOR)
            ),
            None,
        )
        if matmul_pc is None:
            continue
        weight = next(
            v
            for v in _views_of(program, matmul_pc)
            if v["role"] == "input_view_1"
        )
        rows = weight["dims"][0]
        shards = None
        if largest_admitted:
            count = 1
            while count <= rows:
                if rows % count == 0 and rows // count <= largest_admitted:
                    shards = count
                    break
                count += 1
        head[target.key] = {
            "matmul_pc": matmul_pc,
            "weight_view_dims": weight["dims"][:2],
            "output_rows": rows,
            "reduction": weight["dims"][1],
            "macs": rows * weight["dims"][1],
            "coarsest_exact_row_partition": (
                None
                if shards is None
                else {
                    "shards": shards,
                    "rows_per_shard": rows // shards,
                    "shards_times_rows_equals_output_rows": shards
                    * (rows // shards)
                    == rows,
                    "largest_first_dimension_measured_to_launch": largest_admitted,
                    "why": (
                        "the coarsest partition of the head's output rows into "
                        "equal shards each of which is no wider than the largest "
                        "weight-view first dimension this campaign MEASURED the "
                        "bridge to launch.  Equal shards make the partition "
                        "exact by construction: the shard count divides the row "
                        "count, so the extents sum to the whole with no gap and "
                        "no overlap"
                    ),
                }
            ),
        }

    ladder_end = arms[-1]
    attribution = {
        "first_refusal": {
            target.key: arms[0]["targets"][target.key]["measured"]
            for target in qwen
        },
        "final_refusal": {
            target.key: ladder_end["targets"][target.key]["measured"]
            for target in qwen
        },
        "objects_the_ladder_had_to_bind": {
            target.key: [
                entry["object_id"]
                for entry in ladder_end["targets"][target.key]["placement_table"]
            ][len(bench.committed_table(case_index[target.key])) :]
            for target in qwen
        },
        "the_final_refusal_is_not_placement": {
            target.key: bool(
                ladder_end["targets"][target.key].get(
                    "unplaced_objects_of_the_refusal"
                )
                == []
            )
            for target in qwen
        },
    }
    passed = (
        elaboration["compile"]["returncode"] == 0
        and all(arm["marker_present"] for arm in arms)
        and all(arm["returncode"] == 0 for arm in arms)
        and all(
            row["at_least_one_moved_back"] for row in control["targets"].values()
        )
        and all(
            arms[0]["targets"][t.key]["measured"] is not None for t in qwen
        )
    )
    def _sum(rows: list[dict[str, Any] | None]) -> int:
        return sum(row["cycles"] for row in rows if row is not None)

    _cycles = {
        "ladder": _sum(
            [
                entry["measured"]
                for arm in arms
                for entry in arm["targets"].values()
            ]
        ),
        "positive_control_at_the_entry_probe_bound": _sum(
            [entry["measured"] for entry in historical["targets"].values()]
        ),
        "attribution_control": _sum(
            [
                drop["measured"]
                for entry in control["targets"].values()
                for drop in entry["drops"]
            ]
        ),
        "weight_view_admission_bracket": _sum(
            [entry["measured"] for entry in bracket]
        ),
    }
    _cycles["total"] = sum(_cycles.values())

    record = {
        "schema": SCHEMA,
        "status": "pass" if passed else "fail",
        "gate": "G1d (configs/gates/redesign_gates.json)",
        "what_this_measures": (
            "how far the head span executes in the integrated shipped-prefix "
            "vehicle and what refuses it, with placement separated from "
            "geometry by a ladder of arms that differ only in the object "
            "placement table"
        ),
        "does_not_establish": [
            "gate G1d: no arm runs the head on the composed trunk output and "
            "no arm compares a logit against golden",
            "any numeric result: an added table entry binds an object at a "
            "declared base with nothing staged there",
            "that the shipped vector set should bind these objects: the arms "
            "are a probe, and what they measure is what such a binding would "
            "and would not buy",
        ],
        "evidence_class": "public_open_tool_rtl_simulation",
        "simulator": "verilator_cpp_executable",
        "vehicle": "rtl/test/a3_shipped_prefix_top.sv",
        "one_elaboration_for_every_arm": True,
        "probe_base_words": PROBE_BASE,
        "vector_set": {
            "directory": str(prefix.VECTOR_DIR.relative_to(ROOT)),
            "manifest_sha256": prefix.sha256_file(prefix.VECTOR_JSON),
            "committed": prefix.VECTOR_DIR
            == ROOT / "testdata/compiler/abi3_shipped_prefix",
            "case_record_stride": bench.stride,
        },
        "spans": spans,
        "arms": arms,
        "positive_control_at_the_entry_probe_bound": historical,
        "attribution_control": control,
        "attribution": attribution,
        "weight_view_admission_bracket": bracket,
        "weight_views_in_the_program": weight_admission,
        "head_matmul": head,
        "tools": elaboration["tools"],
        "compile_returncode": elaboration["compile"]["returncode"],
        "simulated_cycles": _cycles["total"],
        "simulated_cycles_by_stage": _cycles,
        "git": _git_state(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"{record['status']}: {args.output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(build())
