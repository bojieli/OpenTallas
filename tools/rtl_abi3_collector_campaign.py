#!/usr/bin/env python3
"""Run and record the PC64 partial-collector campaign on both simulators.

``rtl/abi3/ot_a3_partial_collector.sv`` is one of the two blocks
``results/rtl/abi3_boundary_chain.json`` established were MISSING from the
dependent chain of section 13 item 13: nothing drove
``ot_a3_tree_endpoint_fp32``'s ``in_valid`` / ``in_leaf`` / ``in_leaf_count`` /
``in_tag`` from ``ot_a3_tile64``'s partial port.  This campaign qualifies it the
way every other block in this programme is qualified -- two independently
written checkers over one deterministic top, on Icarus Verilog and Verilator,
required to agree case for case -- with the roots checked against the exact
AM-E1 reference (``tools/am_e1_lane_reference.py::re8_chain``) through a real
``ot_a3_tree_endpoint_fp32`` sitting on the collector's leaf port.

It does NOT measure a boundary.  The two-tile chain measurement is
``tools/rtl_abi3_boundary_chain_datapath_campaign.py``.
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

SCHEMA = "opentallas.rtl.abi3_partial_collector.v1"
CAMPAIGN = "rtl3_abi3_partial_collector"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_partial_collector.json"
MANIFEST = ROOT / "testdata/rtl/abi3_partial_collector/manifest.json"

RTL_SOURCES = [
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/abi3/ot_a3_partial_collector.sv",
    "rtl/abi3/ot_a3_tree_endpoint_fp32.sv",
    "rtl/test/a3_collector_top.sv",
]
BOUND_SOURCES = RTL_SOURCES + [
    "rtl/test/tb_a3_collector.sv",
    "rtl/test/a3_collector_harness.cpp",
    "tools/build_abi3_collector_vectors.py",
    "tools/rtl_abi3_collector_campaign.py",
]
VECTOR_FILES = ("pc_part.hex", "pc_case.hex", "pc_expect.hex", "pc_meta.hex")

CASE_RE = re.compile(
    r"^CCASE (?P<index>\d+) (?P<verdict>OK|DIVERGE) site=(?P<site>\d+) "
    r"vectors=(?P<vectors>\d+) roots=(?P<roots>\d+) captured=(?P<captured>\d+) "
    r"code=(?P<code>\d+) detail=(?P<detail>\d+) lane=(?P<lane>\d+) "
    r"slot=(?P<slot>\d+) blocks=(?P<blocks>\d+) elems=(?P<elems>\d+) "
    r"mode=(?P<mode>\d+) inject=(?P<inject>\d+)$", re.MULTILINE)
CHECKS_RE = re.compile(r"^CHECKS: (\d+)$", re.MULTILINE)
MARKER_RE = re.compile(
    r"^PASS: ABI3 partial collector cases=(?P<cases>\d+) "
    r"vectors=(?P<vectors>\d+) roots=(?P<roots>\d+)$", re.MULTILINE)

SITE_NAMES = {
    0: "none", 1: "error class", 2: "error detail", 3: "error lane", 4: "error slot",
    5: "vectors emitted", 6: "partials captured", 7: "roots retired",
    8: "the block's own vector counter", 9: "tags not dense and ascending",
    10: "the top timed out", 11: "done did not pulse exactly once",
    12: "the endpoint faulted", 13: "the collector is still busy",
    14: "a leaf differs from the partial image",
    15: "a vector's tag", 16: "a vector's leaf count",
    17: "a root differs from the AM-E1 reference", 18: "a root's tag",
    19: "the case did not finish",
}


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
    return {"executable": path, "executable_sha256": sha256_file(Path(path)),
            "version": (match.group(0) if match else
                        text.splitlines()[0] if text else "")}


def git_identity() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(args, cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run(["git", "rev-parse", "HEAD"]),
            "worktree_dirty": bool(run(["git", "status", "--porcelain"]))}


def canonicalise(text: str, build: Path) -> str:
    return text.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>").replace(
        str(Path.home()), "<HOME>")


def parse(log: str) -> dict[str, Any]:
    cases = [{k: (m.group(k) if k == "verdict" else int(m.group(k)))
              for k in ("index", "verdict", "site", "vectors", "roots", "captured",
                        "code", "detail", "lane", "slot", "blocks", "elems",
                        "mode", "inject")}
             for m in CASE_RE.finditer(log)]
    for case in cases:
        case["site_name"] = SITE_NAMES.get(case["site"], "unknown")
    marker = MARKER_RE.search(log)
    checks = CHECKS_RE.search(log)
    return {"cases": cases, "marker_present": marker is not None,
            "checks": int(checks.group(1)) if checks else None,
            "case_count": int(marker.group("cases")) if marker else None,
            "vectors": int(marker.group("vectors")) if marker else None,
            "roots": int(marker.group("roots")) if marker else None}


def run_stage(name: str, command: list[str], cwd: Path, build: Path,
              timeout: int) -> dict[str, Any]:
    out = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                         timeout=timeout)
    log = canonicalise((out.stdout or "") + (out.stderr or ""), build)
    return {"name": name, "command": canonicalise(" ".join(command), build),
            "returncode": out.returncode, "log": log}


def run_iverilog(build: Path) -> dict[str, Any]:
    vvp = build / "pc.vvp"
    compile_cmd = ["iverilog", "-g2012", "-s", "tb_a3_collector", "-o", str(vvp)]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/tb_a3_collector.sv"))
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
    obj = build / "obj_pc"
    compile_cmd = [verilator, "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
                   "-Wno-DECLFILENAME", "-O2", "--top-module", "ot_a3_collector_top",
                   "--Mdir", str(obj), "-o", "Vpc"]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/a3_collector_harness.cpp"))
    compile_cmd += ["-CFLAGS", "-std=c++17 -O2", "-j", "8"]
    comp = run_stage("verilator.compile", compile_cmd, build, build, 3600)
    if comp["returncode"] != 0:
        raise SystemExit("verilator build failed:\n" + comp["log"])
    run = run_stage("verilator.run", [str(obj / "Vpc")], build, build, 7200)
    entry = parse(run["log"])
    entry.update({"name": "verilator", "compile_command": comp["command"],
                  "run_command": "<BUILD>/obj_pc/Vpc", "run_returncode": run["returncode"],
                  "log_sha256": hashlib.sha256(run["log"].encode()).hexdigest(),
                  "run_log": run["log"],
                  "status": "pass" if run["returncode"] == 0 and entry["marker_present"]
                            else "fail"})
    return entry


COMPARED = ("index", "verdict", "site", "vectors", "roots", "captured", "code",
            "detail", "lane", "slot")


def build_artifact(entries: list[dict[str, Any]],
                   manifest: dict[str, Any]) -> dict[str, Any]:
    projections = [[tuple(c[k] for k in COMPARED) for c in e["cases"]] for e in entries]
    agree = len({tuple(p) for p in projections}) == 1 and bool(projections[0])
    checks_agree = len({e["checks"] for e in entries}) == 1
    diverged = [c for e in entries for c in e["cases"] if c["verdict"] != "OK"]
    status = ("pass" if all(e["status"] == "pass" for e in entries) and agree
              and checks_agree and not diverged else "fail")
    by_name = {c["id"]: c for c in manifest["cases"]}
    faults = sorted({(by_name[c["index"]]["expect_error_detail"],
                      by_name[c["index"]]["expect_error_detail_name"])
                     for c in entries[0]["cases"]
                     if by_name[c["index"]]["expect_error_code"]})
    return {
        "schema": SCHEMA,
        "campaign": CAMPAIGN,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": [e["name"] for e in entries],
        "cross_simulator_agreement": {
            "simulators_observed_the_same_cases": agree,
            "check_counts_agree": checks_agree,
            "compared_fields": list(COMPARED),
        },
        "block": {
            "rtl": "rtl/abi3/ot_a3_partial_collector.sv",
            "why_it_exists": (
                "results/rtl/abi3_boundary_chain.json established by elaboration "
                "that nothing in the design drove ot_a3_tree_endpoint_fp32's leaf "
                "port from ot_a3_tile64's partial port.  This is that block"),
            "leaf_buffer_bytes": (manifest["geometry"]["tile_lanes"] *
                                  manifest["geometry"]["slot_elems"] *
                                  manifest["geometry"]["leaves"] * 4),
            "leaf_buffer_basis": (
                "section 4.4 allocates two RE8 endpoints per eight-tile cluster, "
                "each with 4 KiB buffering; TILE_LANES x SLOT_ELEMS x LEAVES x 4 B "
                "is that buffer and the vehicle's is exactly 4,096 B"),
            "distinct_fault_modes": [{"detail": d, "name": n} for d, n in faults],
        },
        "totals": {
            "cases": entries[0]["case_count"],
            "leaf_vectors": entries[0]["vectors"],
            "roots": entries[0]["roots"],
            "checks_per_simulator": entries[0]["checks"],
        },
        "manifest": {k: v for k, v in manifest.items() if k != "cases"},
        "cases_declared": manifest["cases"],
        "divergences": diverged,
        "simulators": entries,
        "claim_boundary": {
            "establishes": [
                "that the collector presents ot_a3_tile64's partial port to "
                "ot_a3_tree_endpoint_fp32 in the tree's leaf order -- leaf k is "
                "K-block k of one output element -- with dense ascending tags, "
                "and that every root the endpoint then retires equals the exact "
                "AM-E1 reference re8_chain over those partials",
                "that the transposition holds whether the producer presents all "
                "64 lanes on one cycle (the tile's lockstep) or one lane per "
                "cycle, and at B = 1, 2, 3, 4, 5 and 8 leaves",
                "that the 4 KiB leaf buffer is a sized resource: a window wider "
                "than it holds is refused, not wrapped",
                "six distinct fail-closed modes, each reported with the lowest "
                "faulting lane and the slot",
            ],
            "does_not_establish": {
                "any_boundary_latency": (
                    "no dependent-boundary cycle count is measured here.  The "
                    "two-tile chain measurement is a separate campaign"),
                "the_chained_upper_tree": (
                    "B above LEAVES is refused rather than chained; composing "
                    "stage-2 endpoints is the engine controller's business and "
                    "no RTL for it exists"),
                "physical_realisability": (
                    "simulation says nothing about area, timing or power; no "
                    "routed record of this block exists"),
                "the_general_window_permutation": (
                    "the collector emits slots in ascending (lane, element) "
                    "order.  Which activation element of a CONSUMER a slot "
                    "becomes is the operand H-tree's address rule, which "
                    "section 4.4 leaves unwritten"),
            },
        },
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
                 ".local/opentallas-tools/verilator-5.050/bin/verilator")), "--version"],
                r"Verilator [\d.]+"),
            "cxx": tool_identity("g++", ["g++", "--version"], r"g\+\+ .*"),
            "python": {"executable": sys.executable, "version": sys.version.split()[0]},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260908)
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

    from tools.build_abi3_collector_vectors import build_cases, emit
    manifest = emit(build_cases(), build, args.seed)
    for name in VECTOR_FILES:
        if sha256_file(build / name) != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    committed = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else None
    manifest["vector_manifest_matches_committed"] = bool(
        committed is not None and committed.get("image_sha256") == manifest["image_sha256"])

    entries = [run_iverilog(build), run_verilator(build, verilator)]
    body = build_artifact(entries, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(body), encoding="utf-8")
    for entry in entries:
        print(f"{entry['name']}: {entry['status'].upper()} "
              f"cases={entry['case_count']} checks={entry['checks']} "
              f"vectors={entry['vectors']} roots={entry['roots']}")
    print(f"abi3 partial collector campaign: {body['status'].upper()} -> {args.output}")
    if tmp is not None:
        tmp.cleanup()
    return 0 if body["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
