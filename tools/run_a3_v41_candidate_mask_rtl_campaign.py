#!/usr/bin/env python3
"""Run and record the ROUTE.CANDIDATE_MASK campaign on both simulators.

``rtl/abi3/ot_a3_route_candidate_mask.sv`` is the AM-E10 block that expands
chosen candidate-block ids into the per-position admission mask
``ROUTE.INDEX_TOPK`` takes in slot 3 (plan section 5 row 3).  It is qualified the
way every other block in this programme is qualified -- two independently
written checkers over one deterministic top, on Icarus Verilog and on the PINNED
Verilator 5.050, required to agree case for case and cycle for cycle -- with the
masks checked against ``runtime/reference/candidate_pool.py`` and re-derived a
third and fourth time inside the checkers themselves.

It does NOT place or route the block, and it does not run it from a descriptor
through ``ot_a3_engine_array``: see ``claim_boundary``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "opentallas.rtl.a3_v41_candidate_mask_campaign.v1"
CAMPAIGN = "rtl3_a3_v41_route_candidate_mask"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_v41_candidate_mask_campaign.json"

RTL_SOURCES = [
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_route_candidate_mask.sv",
    "rtl/test/a3_candidate_mask_top.sv",
]
BOUND_SOURCES = RTL_SOURCES + [
    "rtl/test/tb_a3_candidate_mask.sv",
    "rtl/test/a3_candidate_mask_harness.cpp",
    "runtime/reference/candidate_pool.py",
    "runtime/abi3/constants.py",
    "tools/build_a3_v41_candidate_mask_vectors.py",
    "tools/run_a3_v41_candidate_mask_rtl_campaign.py",
]
VECTOR_FILES = ("cm_case.hex", "cm_ids.hex", "cm_expect.hex", "cm_meta.hex")

CASE_RE = re.compile(
    r"^CMCASE +(?P<index>\d+) +(?P<verdict>OK|DIVERGE) site=(?P<site>\d+) "
    r"geom=(?P<geom>\d+) block=(?P<block>\d+) width=(?P<width>\d+) "
    r"ids=(?P<ids>\d+) words=(?P<words>\d+) pop=(?P<pop>\d+) "
    r"blocks=(?P<blocks>\d+) code=(?P<code>\d+) detail=(?P<detail>\d+) "
    r"slot=(?P<slot>\d+) value=(?P<value>\d+) pulses=(?P<pulses>\d+) "
    r"span=(?P<span>\d+) gap=(?P<gap>\d+) cycles=(?P<cycles>\d+) "
    r"consumed=(?P<consumed>\d+)$", re.MULTILINE)
CHECKS_RE = re.compile(r"^CHECKS: (\d+)$", re.MULTILINE)
MARKER_RE = re.compile(
    r"^PASS: A3 V41 candidate mask cases=(?P<cases>\d+) "
    r"words=(?P<words>\d+) population=(?P<population>\d+)$", re.MULTILINE)

#: The numbered check sites both checkers report, so a divergence is a place and
#: not just a verdict.
SITE_NAMES = {
    0: "none",
    1: "the top timed out",
    2: "done did not pulse exactly once",
    3: "error code",
    4: "error detail, the trap site",
    5: "error slot, the offending id",
    6: "error value",
    7: "mask words the block reported writing",
    8: "admitted population",
    9: "distinct admitted blocks",
    10: "out_we pulses the top counted",
    11: "out_addr was not out_base + word index",
    12: "a write outside the capture window",
    13: "elaborated BLOCK",
    14: "elaborated MAX_WIDTH",
    15: "elaborated MAX_IDS",
    16: "elaborated WORD_BITS",
    17: "elaborated PIN_LAST_BLOCK",
    18: "initiation interval: n words did not span n-1 cycles",
    19: "the largest gap between output words was not 1",
    20: "a mask word differs from the reference image",
    21: "a mask word differs from the checker's own derivation",
    22: "the reference image differs from the checker's own derivation",
    23: "the checker's population differs from the reference's",
    24: "the checker's block count differs from the reference's",
    25: "ids retired by the ingest",
    26: "the block is still busy after done",
    27: "operand-port reads the block issued",
    28: "a case declared within its bound derived above it",
    29: "the top's geometry count",
    30: "the top's case stride",
    31: "the campaign's mask-word total",
    32: "the campaign's population total",
}

#: Fields every case line must agree on between the two simulators.  Cycles are
#: included on purpose: the stimulus is inside the top and is a deterministic
#: function of the case table, so a cycle difference is a real disagreement.
COMPARED = ("index", "verdict", "site", "geom", "block", "width", "ids", "words",
            "pop", "blocks", "code", "detail", "slot", "value", "pulses", "span",
            "gap", "cycles", "consumed")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(body: Any) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True) + "\n"


def tool_identity(name: str, argv: list[str], pattern: str) -> dict[str, Any]:
    path = shutil.which(argv[0]) or argv[0]
    if not Path(path).exists():
        raise SystemExit(f"required tool is unavailable: {name} ({argv[0]})")
    out = subprocess.run(argv, capture_output=True, text=True, check=False)
    text = (out.stdout or "") + (out.stderr or "")
    match = re.search(pattern, text)
    return {"executable": str(path).replace(str(Path.home()), "<HOME>"),
            "executable_sha256": sha256_file(Path(path)),
            "version": (match.group(0) if match else
                        text.splitlines()[0] if text else "")}


def git_identity() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(args, cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run(["git", "rev-parse", "HEAD"]),
            "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
            "worktree_dirty": bool(run(["git", "status", "--porcelain"]))}


def canonicalise(text: str, build: Path) -> str:
    return (text.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>")
                .replace(str(Path.home()), "<HOME>"))


def parse(log: str) -> dict[str, Any]:
    cases = [{k: (m.group(k) if k == "verdict" else int(m.group(k)))
              for k in COMPARED}
             for m in CASE_RE.finditer(log)]
    for case in cases:
        case["site_name"] = SITE_NAMES.get(case["site"], "unknown")
    marker = MARKER_RE.search(log)
    checks = CHECKS_RE.search(log)
    return {"cases": cases, "marker_present": marker is not None,
            "checks": int(checks.group(1)) if checks else None,
            "case_count": int(marker.group("cases")) if marker else None,
            "mask_words": int(marker.group("words")) if marker else None,
            "population": int(marker.group("population")) if marker else None}


def run_stage(name: str, command: list[str], cwd: Path, build: Path,
              timeout: int) -> dict[str, Any]:
    out = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                         timeout=timeout)
    log = canonicalise((out.stdout or "") + (out.stderr or ""), build)
    return {"name": name, "command": canonicalise(" ".join(command), build),
            "returncode": out.returncode, "log": log}


def run_iverilog(build: Path) -> dict[str, Any]:
    vvp = build / "cm.vvp"
    compile_cmd = ["iverilog", "-g2012", "-s", "tb_a3_candidate_mask", "-o", str(vvp)]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/tb_a3_candidate_mask.sv"))
    comp = run_stage("iverilog.compile", compile_cmd, build, build, 3600)
    if comp["returncode"] != 0:
        raise SystemExit("iverilog compile failed:\n" + comp["log"])
    run = run_stage("iverilog.run", ["vvp", str(vvp)], build, build, 7200)
    entry = parse(run["log"])
    entry.update({"name": "iverilog", "compile_command": comp["command"],
                  "run_command": run["command"], "run_returncode": run["returncode"],
                  "log_sha256": hashlib.sha256(run["log"].encode()).hexdigest(),
                  "run_log": run["log"],
                  "status": "pass" if run["returncode"] == 0 and entry["marker_present"]
                            else "fail"})
    return entry


def run_verilator(build: Path, verilator: str) -> dict[str, Any]:
    obj = build / "obj_cm"
    compile_cmd = [verilator, "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
                   "-Wno-DECLFILENAME", "-O2", "--top-module",
                   "ot_a3_candidate_mask_top", "--Mdir", str(obj), "-o", "Vcm"]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/a3_candidate_mask_harness.cpp"))
    compile_cmd += ["-CFLAGS", "-std=c++17 -O2", "-j", "8"]
    comp = run_stage("verilator.compile", compile_cmd, build, build, 3600)
    if comp["returncode"] != 0:
        raise SystemExit("verilator build failed:\n" + comp["log"])
    run = run_stage("verilator.run", [str(obj / "Vcm")], build, build, 7200)
    entry = parse(run["log"])
    entry.update({"name": "verilator", "compile_command": comp["command"],
                  "run_command": "<BUILD>/obj_cm/Vcm",
                  "run_returncode": run["returncode"],
                  "log_sha256": hashlib.sha256(run["log"].encode()).hexdigest(),
                  "run_log": run["log"],
                  "status": "pass" if run["returncode"] == 0 and entry["marker_present"]
                            else "fail"})
    return entry


def registry_agreement() -> dict[str, Any]:
    """The RTL package, the Python registry and the IR must name one sub-opcode."""
    from runtime.abi3.constants import Major, Route
    from compiler.ir.v3.lowering import KERNEL_TO_ENGINE
    pkg = (ROOT / "rtl/abi3/ot_a3_pkg.sv").read_text(encoding="utf-8")
    match = re.search(r"A3_ROUTE_CANDIDATE_MASK\s*=\s*8'h([0-9a-fA-F]+)", pkg)
    rtl_value = int(match.group(1), 16) if match else None
    entry = KERNEL_TO_ENGINE.get("CANDIDATE_MASK")
    return {
        "runtime_abi3_constants_route_candidate_mask": int(Route.CANDIDATE_MASK),
        "rtl_ot_a3_pkg_a3_route_candidate_mask": rtl_value,
        "ir_kernel_to_engine_family": int(entry.family) if entry else None,
        "ir_kernel_to_engine_subopcode": int(entry.sub) if entry else None,
        "ir_kernel_to_engine_inputs": int(entry.inputs) if entry else None,
        "ir_kernel_to_engine_outputs": int(entry.outputs) if entry else None,
        "ir_major_route": int(Major.ROUTE),
        "agree": bool(
            rtl_value is not None and entry is not None
            and rtl_value == int(Route.CANDIDATE_MASK)
            and int(entry.sub) == int(Route.CANDIDATE_MASK)
            and int(entry.family) == int(Major.ROUTE)),
    }


def build_artifact(entries: list[dict[str, Any]],
                   manifest: dict[str, Any]) -> dict[str, Any]:
    projections = [[tuple(c[k] for k in COMPARED) for c in e["cases"]] for e in entries]
    agree = len({tuple(p) for p in projections}) == 1 and bool(projections[0])
    totals_agree = len({(e["case_count"], e["mask_words"], e["population"])
                        for e in entries}) == 1
    diverged = [c for e in entries for c in e["cases"] if c["verdict"] != "OK"]
    registry = registry_agreement()
    declared = {c["id"]: c for c in manifest["cases"]}
    status = ("pass" if all(e["status"] == "pass" for e in entries) and agree
              and totals_agree and not diverged and registry["agree"]
              and manifest["vector_manifest_reproducible"] else "fail")
    observed = entries[0]["cases"]
    ii_cases = [c for c in observed if c["words"] > 1]
    return {
        "schema": SCHEMA,
        "campaign": CAMPAIGN,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "block": {
            "rtl": "rtl/abi3/ot_a3_route_candidate_mask.sv",
            "engine": "ROUTE.CANDIDATE_MASK",
            "subopcode": registry["runtime_abi3_constants_route_candidate_mask"],
            "ir_kind": "CANDIDATE_MASK(block_ids, block, width) -> mask",
            "numeric_contract": manifest["contract"],
            "polarity": manifest["polarity"],
            "polarity_basis": (
                "a set bit ADMITS its position.  SRC-DSV41-FLASH-MODEL: the "
                "Indexer masks scores TO the candidate pool, so the pool is what "
                "survives; and the plan's candidate_pool_bound checker bounds the "
                "mask POPULATION by 16,384, which is 2,048 chosen blocks x 8 "
                "positions -- the admitted count, not the excluded one, which "
                "would be width - 16,384 and would grow with the context.  Plan "
                "section 5 row 3's phrase 'masks scores to -inf inside the "
                "candidate blocks' reads as the opposite polarity and contradicts "
                "its own checker; the -inf goes OUTSIDE the candidate blocks"),
            "pinned_last_block_rule": (
                "block ceil(width/BLOCK) - 1 is admitted whether or not an id "
                "named it: its block maximum was taken over a partly filled block "
                "whose absent tail is -inf padding, and the Hierarchical Sparse "
                "Indexer is applied identically in training and inference, where "
                "the current block is always visible.  Geometry 4 elaborates the "
                "same block with the rule off and case unpinned_one_id shows what "
                "it is worth: 8 admitted positions instead of 12"),
            "pipeline": {
                "ingest_stages": 4,
                "ingest_initiation_interval_ids_per_cycle": 1,
                "emit_stages": 2,
                "emit_initiation_interval_words_per_cycle": 1,
                "measured_largest_gap_between_output_words": sorted(
                    {c["gap"] for c in ii_cases}),
                "measured_span_equals_words_minus_one": all(
                    c["span"] == c["words"] - 1 for c in ii_cases),
                "widest_combinational_path_in_the_emit_loop": (
                    "a BLOCK-to-1 mux of WORD_BITS bits over a wiring-only "
                    "replication network, then one AND with the tail mask.  No "
                    "reduction, no variable shift and no dependence on the "
                    "previous bit or the previous word"),
                "division_and_multiplication": (
                    "by the elaboration parameters BLOCK and WORD_BITS only, and "
                    "confined to the three setup cycles outside every II=1 loop"),
            },
            "geometry_is_parameterised": {
                "parameters": ["BLOCK", "MAX_WIDTH", "MAX_IDS", "WORD_BITS",
                               "PIN_LAST_BLOCK"],
                "defaults_are_the_v41_values": True,
                "elaborations_exercised": manifest["geometries"],
                "runtime_fields": ["cfg_width", "cfg_id_count", "cfg_block",
                                   "cfg_max_pop", "cfg_ids_base", "cfg_out_base"],
                "every_admission_bound_derived_from": (
                    "a parameter (MAX_WIDTH, MAX_IDS, BLOCK) or an operand field "
                    "(cfg_width, cfg_id_count, cfg_max_pop); the block count comes "
                    "from cfg_width and never from an assumed 2,048"),
                "checked_not_assumed": (
                    "each instance drives its elaborated BLOCK, MAX_WIDTH, "
                    "MAX_IDS, WORD_BITS and PIN_LAST_BLOCK back out and every "
                    "case compares them (sites 13 to 17)"),
            },
        },
        "simulators_counted": [e["name"] for e in entries],
        "simulators_agree": agree and totals_agree,
        "cross_simulator_agreement": {
            "simulators_observed_the_same_cases": agree,
            "campaign_totals_agree": totals_agree,
            "compared_fields": list(COMPARED),
            "cycles_are_compared": True,
            "check_counts": {e["name"]: e["checks"] for e in entries},
            "check_counts_are_not_required_to_match": (
                "the two checkers are written independently and do not make the "
                "same set of comparisons: the Verilog checker owns sites 29 to 32 "
                "and the C++ checker owns site 28 and its own image-consistency "
                "checks.  What must match is every field of every case line, "
                "cycle counts included"),
        },
        "totals": {
            "cases": entries[0]["case_count"],
            "mask_words_written": entries[0]["mask_words"],
            "admitted_positions": entries[0]["population"],
            "refusals": manifest["totals"]["refusals"],
            "geometries": len(manifest["geometries"]),
            "checks_per_simulator": {e["name"]: e["checks"] for e in entries},
        },
        "reference": manifest["reference"],
        "reference_agreement": {
            "reference": ("runtime/reference/candidate_pool.py::"
                          "select_candidate_mask"),
            "derived_from": ("the semantics in docs/DEEPSEEK_V41_FLASH_ROM_"
                             "IMPLEMENTATION_PLAN.md sections 5 and 7 and the "
                             "pinned vendor behaviour SRC-DSV41-FLASH-MODEL, "
                             "-CONFIG and -REPORT record in docs/SOURCES.md; not "
                             "transcribed from the RTL"),
            "independent_rederivations": 2,
            "how": ("the Verilog checker decides every position from its block "
                    "index; the C++ checker walks only the blocks that overlap "
                    "each output word and fills the overlapping range.  Sites 20, "
                    "21 and 22 require the block, the reference image and the "
                    "checker's own derivation to agree word for word"),
            "mask_words_compared": entries[0]["mask_words"],
        },
        "registry_agreement": registry,
        "vector_manifest": {k: v for k, v in manifest.items() if k != "cases"},
        "cases_declared": manifest["cases"],
        "cases_observed": observed,
        "divergences": diverged,
        "simulators": entries,
        "site_names": {str(k): v for k, v in SITE_NAMES.items()},
        "claim_boundary": {
            "establishes": [
                "that for 35 cases over five elaborations the block's mask words "
                "equal runtime/reference/candidate_pool.py::select_candidate_mask "
                "word for word, and equal two further derivations written "
                "independently in Verilog and C++, on both simulators",
                "that a set bit admits its position and the population is the "
                "admitted count: the 2,048-block pool of a 16,384-position axis "
                "has population exactly 16,384 (case pool_exactly_at_the_bound)",
                "that the pinned last block is admitted with no id at all, that "
                "it is counted once when an id also names it, and that the same "
                "block elaborated without the rule admits 8 positions where the "
                "pinned one admits 12",
                "that the -inf padded tail is honoured: a width that is not a "
                "multiple of BLOCK or of WORD_BITS admits [last*BLOCK, width) "
                "only and zeroes the high bits of the final word",
                "that the emit loop sustains one output word per cycle: every "
                "case that wrote n > 1 words wrote them in exactly n-1 cycles "
                "with a largest inter-word gap of 1, including the 32,768-word "
                "case at the V4.1 context of 1,048,576 positions",
                "that ids are a set: duplicates, unsorted order and A3_NO_ID "
                "slots all give the same mask as the sorted distinct set",
                "that seven fail-closed trap sites each report their own detail, "
                "and that a refused run writes no output word at all",
                "that the geometry is elaborated, not frozen: BLOCK 1, 3, 8 and "
                "16, four MAX_WIDTHs and four MAX_IDS, each checked against what "
                "the instance says it elaborated",
                "that the sub-opcode in the RTL package, in runtime/abi3/"
                "constants.py and in the IR's KERNEL_TO_ENGINE are one value",
            ],
            "does_not_establish": {
                "physical_realisability": (
                    "no frequency, area or power number comes from this run.  The "
                    "pipeline claim is structural -- registered stages, II = 1 "
                    "measured in cycles, no combinational reduction -- and the "
                    "500 MHz class figure quoted for ot_a3_mac_lane_pipe and "
                    "ot_mac_bf16_fp32_pipe on ASAP7 is THEIR measurement, not "
                    "this block's.  results/physical_abi3/*/a3_candidate_mask/ "
                    "does not exist yet (plan WP-M)"),
                "integration_with_the_engine_array": (
                    "the block is driven by rtl/test/a3_candidate_mask_top.sv, "
                    "not by a ROUTE descriptor through ot_a3_engine_issue_bridge "
                    "and ot_a3_engine_array.  Nothing here shows the bridge "
                    "admits sub-opcode 0x09, nor which descriptor fields carry "
                    "cfg_width, cfg_id_count, cfg_block and cfg_max_pop"),
                "the_slot_3_consumer": (
                    "no ROUTE.INDEX_TOPK in this repository reads a mask operand "
                    "yet.  This run establishes the producer's words, not that a "
                    "top-k masks scores to -inf with them, and therefore not the "
                    "end-to-end candidate-pool mechanism WP-H's evidence document "
                    "has to show is applied"),
                "the_block_score_path": (
                    "ROUTE.BLOCK_MAX, the block top-k and the tie rule that "
                    "chooses WHICH block ids arrive are another unit's work.  The "
                    "ids here are a synthetic operand image"),
                "the_candidate_pool_bound_as_a_compiler_check": (
                    "cfg_max_pop is enforced by this block when a descriptor "
                    "carries it.  check.py's candidate_pool_bound is a separate "
                    "clause over a lowered program and is not run here"),
                "runtime_variable_block_size": (
                    "BLOCK is an elaboration parameter: the expander is wiring "
                    "whose every index is constant-folded, and a descriptor that "
                    "carries a different block size is REFUSED (detail 5) rather "
                    "than reinterpreted.  Changing it is one parameter override "
                    "and no source edit, and the campaign runs four values, but "
                    "one elaboration does not serve two block sizes at once"),
                "the_pool_bound_and_the_pin_together": (
                    "case refuse_population_above_bound is a finding about the "
                    "plan, not about the block: 2,048 chosen blocks plus a pinned "
                    "block none of them named is 16,392 admitted positions, above "
                    "the 16,384 that candidate_pool_bound states.  Either the "
                    "top-k budgets 2,047 ids (case bound_met_with_the_pin_counted "
                    "shows that lands exactly on 16,384) or the bound is 16,392.  "
                    "Which one the reference model does is a question for WP-H's "
                    "oracle, and this campaign does not answer it"),
                "fp4_and_engram_neighbours": (
                    "the other four AM-E10 blocks are separate units with "
                    "separate campaigns"),
            },
        },
        "limitations": [
            "The operand port is modelled as a synchronous read with one cycle of "
            "latency behind a registered address, which is what the top provides. "
            "A real operand H-tree with a longer or variable latency would need "
            "the ingest to carry a ready/valid handshake; the emit side would not "
            "change, because it reads the block's own bitmap.",
            "The bitmap is a register-array memory in simulation. Whether it "
            "maps to an SRAM macro or to flops at the elaborated SET_WORDS "
            "(4,096 words of 32 bits at the V4.1 geometry) is a physical question "
            "this run does not answer.",
            "The clear phase costs ceil(blocks/WORD_BITS) cycles before ingest, "
            "so the block is not free to restart every cycle. It is a per-run "
            "setup cost, not part of the II = 1 emit loop, and the measured cycle "
            "counts in cases_observed include it.",
            "The population counter is 32 bits wide, as are the width and the "
            "mask-word index. A position axis above 2^32 would need wider "
            "counters; MAX_WIDTH is checked against the parameter, so such an "
            "axis is refused rather than wrapped.",
            "Case ids are synthetic images chosen to exercise the geometry and "
            "the hazards. They are not the block ids a real V4.1 Reindex layer "
            "would choose, which is what the reference oracle of plan section 7 "
            "is for.",
        ],
        "source_sha256": {s: sha256_file(ROOT / s) for s in BOUND_SOURCES},
        "git": git_identity(),
        "tools": {
            "iverilog": tool_identity("iverilog", ["iverilog", "-V"],
                                      r"Icarus Verilog version [\d.]+"),
            "vvp": tool_identity("vvp", ["vvp", "-V"],
                                 r"Icarus Verilog runtime version [\d.]+"),
            "verilator": tool_identity(
                "verilator",
                [os.environ.get("VERILATOR", str(Path.home() /
                 ".local/opentallas-tools/verilator-5.050/bin/verilator")),
                 "--version"],
                r"Verilator [\d.]+"),
            "cxx": tool_identity("g++", ["g++", "--version"], r"g\+\+ .*"),
            "python": {"executable": sys.executable,
                       "version": sys.version.split()[0]},
        },
        "verilator_pin": (
            "the repository pins Verilator 5.050 under "
            "<HOME>/.local/opentallas-tools; the 4.038 on PATH is not used"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 2

    verilator = os.environ.get(
        "VERILATOR",
        str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    tmp = None
    if args.build_dir is None:
        tmp = tempfile.TemporaryDirectory()
        build = Path(tmp.name)
    else:
        build = args.build_dir
        build.mkdir(parents=True, exist_ok=True)

    from tools.build_a3_v41_candidate_mask_vectors import build_cases, emit
    manifest = emit(build_cases(), build)
    for name in VECTOR_FILES:
        if sha256_file(build / name) != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    # The images must be a function of the source alone: build them a second
    # time into a scratch directory and require the same digests.
    second = build / "reproduce"
    again = emit(build_cases(), second)
    manifest["vector_manifest_reproducible"] = (
        again["image_sha256"] == manifest["image_sha256"])
    for name in VECTOR_FILES:
        (second / name).unlink()
    second.rmdir()

    entries = [run_iverilog(build), run_verilator(build, verilator)]
    body = build_artifact(entries, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(body), encoding="utf-8")
    for entry in entries:
        print(f"{entry['name']}: {entry['status'].upper()} "
              f"cases={entry['case_count']} checks={entry['checks']} "
              f"words={entry['mask_words']} population={entry['population']}")
    print(f"a3 v41 candidate mask campaign: {body['status'].upper()} "
          f"simulators_agree={body['simulators_agree']} -> {args.output}")
    if tmp is not None:
        tmp.cleanup()
    return 0 if body["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
