#!/usr/bin/env python3
"""Run and record the dependent-boundary control probe on both simulators.

``docs/CHIP_ARCHITECTURE_DESIGN.md`` section 3.6 says the exposed dependent
chain is unmeasured and names its five terms: "the last result, mesh transfer,
operand readiness, queue admission, and acknowledged completion".  Section 13
item 13 says neither the cycle model's 39 cycles nor the design's historical
120 is a measurement, and §2.1 row 33 has since withdrawn the 120 altogether.

This campaign measures the three terms that have design RTL behind them today,
on the modules themselves and not on a model of them:

  * acknowledged completion -- ``rtl/abi3/ot_a3_issue_record_store.sv``
    retiring a completed producer, and ``rtl/abi3/ot_a3_event_scoreboard.sv``
    signalling its event on that retirement;
  * queue admission -- the store's ``alloc_ready`` under the per-queue depth
    and the per-die outstanding bound, and the scoreboard's twelve-producer
    wait-set evaluation;
  * the mesh crossbar -- ``rtl/abi3/ot_a3_mesh_router.sv``, one to three hops.

It does **not** measure the boundary section 13 item 13 asks for, and the
artifact says so in ``claim_boundary``: the producer tile's own last-result
path and the operand broadcast into the consumer's activation FIFO are not in
it, and the mesh *traversal* is not in it either, because the router's
crossbar is combinational by design ("every cycle of a traversal is spent in
the link channel, not in the router") -- the traversal term lives in
``ot_a3_link_channel`` and ``results/rtl/a3_link_campaign.json`` already
regresses it.

Two independently written checkers drive the same top: ``tb_a3_boundary_control.sv``
under Icarus and ``a3_boundary_control_harness.cpp`` under Verilator.  Unlike
the deployment co-simulation, whose two checkers apply different back-pressure
by design, both checkers here drive a deterministic top with the stimulus
inside it, so the two simulators must report the **same cycles** and the
campaign requires it.
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

SCHEMA = "opentallas.rtl.abi3_boundary_control.v1"
CAMPAIGN = "rtl3_abi3_boundary_control"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_boundary_control.json"
MANIFEST = ROOT / "testdata/rtl/abi3_boundary_control/manifest.json"

RTL_SOURCES = [
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_link_pkg.sv",
    "rtl/abi3/ot_a3_issue_record_store.sv",
    "rtl/abi3/ot_a3_event_scoreboard.sv",
    "rtl/abi3/ot_a3_mesh_router.sv",
    "rtl/test/a3_boundary_control_top.sv",
]
BOUND_SOURCES = RTL_SOURCES + [
    "rtl/test/tb_a3_boundary_control.sv",
    "rtl/test/a3_boundary_control_harness.cpp",
    "tools/build_abi3_boundary_control_vectors.py",
    "tools/rtl_abi3_boundary_control_campaign.py",
]

CASE_RE = re.compile(
    r"^BCASE (?P<index>\d+) tag=(?P<tag>\d+) (?P<verdict>OK|DIVERGE) "
    r"site=(?P<site>\d+) boundary=(?P<boundary>\d+) control=(?P<control>\d+) "
    r"retire=(?P<retire>\d+) mesh=(?P<mesh>\d+) wait=(?P<wait>\d+) "
    r"admit=(?P<admit>\d+) trap=(?P<trap>\d+) ok=(?P<ok>\d+) "
    r"stalled=(?P<stalled>\d+) producers=(?P<producers>\d+) "
    r"hops=(?P<hops>\d+) waits=(?P<waits>\d+) signals=(?P<signals>\d+) "
    r"maxout=(?P<maxout>\d+) local=(?P<local>\d+)$",
    re.MULTILINE,
)
MARKER_RE = re.compile(
    r"^PASS: ABI3 dependent-boundary control probe cases=(?P<cases>\d+) "
    r"checks=(?P<checks>\d+)$", re.MULTILINE,
)

SITE_NAMES = {
    0: "none",
    1: "trap class differs from the case table",
    2: "wait_ok differs from the case table",
    3: "the stall the case builds was not observed",
    4: "the top timed out in a stage",
    5: "issue record store protocol error",
    6: "event scoreboard signal error",
    7: "mesh misroute",
    8: "the scoreboard evaluated other than one wait set",
    9: "the scoreboard signalled other than one event per producer",
    10: "the boundary measured zero cycles",
    11: "the four spans do not sum to the boundary",
    12: "the control figure is not the boundary less the mesh leg",
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
    return {
        "executable": path,
        "executable_sha256": sha256_file(Path(path)),
        "version": (match.group(0) if match else text.splitlines()[0] if text else ""),
    }


def git_identity() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(args, cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {
        "commit": run(["git", "rev-parse", "HEAD"]),
        "worktree_dirty": bool(run(["git", "status", "--porcelain"])),
    }


def canonicalise(text: str, build: Path) -> str:
    return text.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>").replace(
        str(Path.home()), "<HOME>")


def parse(log: str) -> dict[str, Any]:
    cases = [
        {
            "index": int(m.group("index")),
            "tag": int(m.group("tag")),
            "verdict": m.group("verdict"),
            "divergence_site": int(m.group("site")),
            "divergence_site_name": SITE_NAMES.get(int(m.group("site")), "unknown"),
            "boundary_cycles": int(m.group("boundary")),
            "boundary_control_cycles": int(m.group("control")),
            "span_retire_cycles": int(m.group("retire")),
            "span_mesh_cycles": int(m.group("mesh")),
            "span_wait_cycles": int(m.group("wait")),
            "span_admit_cycles": int(m.group("admit")),
            "trap_class": int(m.group("trap")),
            "wait_ok": int(m.group("ok")),
            "stalled": int(m.group("stalled")),
            "producers": int(m.group("producers")),
            "mesh_hops": int(m.group("hops")),
            "wait_evaluations": int(m.group("waits")),
            "events_signalled": int(m.group("signals")),
            "max_outstanding": int(m.group("maxout")),
            "mesh_local_deliveries": int(m.group("local")),
        }
        for m in CASE_RE.finditer(log)
    ]
    marker = MARKER_RE.search(log)
    return {
        "cases": cases,
        "marker_present": marker is not None,
        "checks": int(marker.group("checks")) if marker else None,
        "case_count": int(marker.group("cases")) if marker else None,
    }


def run_iverilog(build: Path) -> dict[str, Any]:
    vvp = build / "bc.vvp"
    compile_cmd = ["iverilog", "-g2012", "-s", "tb_a3_boundary_control", "-o", str(vvp)]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/tb_a3_boundary_control.sv"))
    comp = subprocess.run(compile_cmd, cwd=build, capture_output=True, text=True)
    if comp.returncode != 0:
        raise SystemExit("iverilog compile failed:\n" + comp.stdout + comp.stderr)
    run = subprocess.run(["vvp", str(vvp)], cwd=build, capture_output=True, text=True)
    log = canonicalise(run.stdout, build)
    entry = parse(log)
    entry.update({
        "name": "iverilog",
        "compile_command": canonicalise(" ".join(compile_cmd), build),
        "run_command": canonicalise(f"vvp {vvp}", build),
        "run_returncode": run.returncode,
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
        "run_log": log,
        "status": "pass" if run.returncode == 0 and entry["marker_present"] else "fail",
    })
    return entry


def run_verilator(build: Path, verilator: str) -> dict[str, Any]:
    obj = build / "obj_bc"
    compile_cmd = [
        verilator, "--cc", "--exe", "--build", "-Wall", "-Wno-fatal", "-O2",
        "--top-module", "ot_a3_boundary_control_top", "--Mdir", str(obj), "-o", "Vbc",
    ]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/a3_boundary_control_harness.cpp"))
    comp = subprocess.run(compile_cmd, cwd=build, capture_output=True, text=True)
    if comp.returncode != 0:
        raise SystemExit("verilator build failed:\n" + comp.stdout + comp.stderr)
    run = subprocess.run([str(obj / "Vbc")], cwd=build, capture_output=True, text=True)
    log = canonicalise(run.stdout, build)
    entry = parse(log)
    entry.update({
        "name": "verilator",
        "compile_command": canonicalise(" ".join(compile_cmd), build),
        "run_command": "<BUILD>/obj_bc/Vbc",
        "run_returncode": run.returncode,
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
        "run_log": log,
        "status": "pass" if run.returncode == 0 and entry["marker_present"] else "fail",
    })
    return entry


COMPARED = (
    "index", "tag", "verdict", "divergence_site", "boundary_cycles",
    "boundary_control_cycles", "span_retire_cycles", "span_mesh_cycles",
    "span_wait_cycles", "span_admit_cycles", "trap_class", "wait_ok",
    "stalled", "producers", "mesh_hops", "wait_evaluations",
    "events_signalled", "max_outstanding",
)


def boundary_summary(cases: list[dict[str, Any]],
                     manifest: dict[str, Any]) -> dict[str, Any]:
    """The headline figure, and exactly what it is a figure for."""
    by_name = {c["index"]: c for c in manifest["cases"]}
    unstalled = [
        c for c in cases
        if by_name[c["index"]]["leave_one_pending"] == 0
        and by_name[c["index"]]["unsignalled"] == 0
        and by_name[c["index"]]["admit_release"] == 0
    ]
    values = sorted({c["boundary_control_cycles"] for c in unstalled})
    return {
        "control_boundary_cycles": values[0] if len(values) == 1 else None,
        "control_boundary_cycles_observed": values,
        "invariant_over": (
            "wait-set width 1..12, mesh distance 0..3 hops, NONE / ACQUIRE / "
            "ACQUIRE_RELEASE / SEQUENTIAL ordering, and an issue record store "
            "already holding twelve operations"
        ),
        "decomposition_cycles": {
            "acknowledged_completion": sorted(
                {c["span_retire_cycles"] for c in unstalled}),
            "wait_check": sorted({c["span_wait_cycles"] for c in unstalled}),
            "queue_admission": sorted({c["span_admit_cycles"] for c in unstalled}),
            "mesh_crossbar_and_driver": sorted(
                {c["span_mesh_cycles"] for c in unstalled}),
        },
        "rule": (
            "control_boundary_cycles is boundary_cycles less the mesh leg, over "
            "the cases with no stalled producer, no refused wait and no queue "
            "back-pressure.  It is the span from the cycle the producer's last "
            "completion is acknowledged at the issue record store to the cycle "
            "the consumer is admitted to its engine queue, with a design module "
            "behind every cycle of it"
        ),
        "stalled_cases": [
            {
                "case": by_name[c["index"]]["name"],
                "pending_delay": by_name[c["index"]]["pending_delay"],
                "boundary_control_cycles": c["boundary_control_cycles"],
                "span_wait_cycles": c["span_wait_cycles"],
            }
            for c in cases if by_name[c["index"]]["leave_one_pending"]
        ],
        "queue_back_pressure_cases": [
            {
                "case": by_name[c["index"]]["name"],
                "drains_after_cycles": by_name[c["index"]]["admit_release"],
                "span_admit_cycles": c["span_admit_cycles"],
            }
            for c in cases if by_name[c["index"]]["admit_release"]
        ],
        "refused_cases": [
            {
                "case": by_name[c["index"]]["name"],
                "trap_class": c["trap_class"],
                "wait_ok": c["wait_ok"],
            }
            for c in cases if by_name[c["index"]]["unsignalled"]
        ],
    }


def build_artifact(entries: list[dict[str, Any]],
                   manifest: dict[str, Any]) -> dict[str, Any]:
    projections = [[tuple(c[k] for k in COMPARED) for c in e["cases"]] for e in entries]
    agree = len({tuple(p) for p in projections}) == 1 and bool(projections[0])
    diverged = [c for e in entries for c in e["cases"] if c["verdict"] != "OK"]
    status = (
        "pass" if all(e["status"] == "pass" for e in entries) and agree
        and not diverged else "fail"
    )
    summary = boundary_summary(entries[0]["cases"], manifest)
    per_sim = [
        {"simulator": e["name"], "cycles": summary["control_boundary_cycles"]}
        for e in entries
    ]
    return {
        "schema": SCHEMA,
        "campaign": CAMPAIGN,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": [e["name"] for e in entries],
        "cross_simulator_agreement": {
            "simulators_observed_the_same_cases": agree,
            "compared_fields": list(COMPARED),
            "rule": (
                "both checkers drive the same deterministic top with the "
                "stimulus inside it, so unlike the deployment co-simulation "
                "the CYCLES are inside the projection and the two simulators "
                "are required to agree on them"
            ),
        },
        "boundary": {
            "cycles": summary["control_boundary_cycles"],
            "simulators_agree": agree,
            "per_simulator": per_sim,
            "decomposition": summary["decomposition_cycles"],
            "is_the_section_13_item_13_boundary": False,
            "why_not": (
                "section 13 item 13 asks for a two-tile dependent chain.  This "
                "is its control half: the producer tile's last-result path and "
                "the operand broadcast into the consumer tile's activation "
                "FIFO are not in it, and neither is the mesh traversal"
            ),
        },
        "summary": summary,
        "manifest": {k: v for k, v in manifest.items() if k != "cases"},
        "divergences": diverged,
        "cases": entries,
        "claim_boundary": {
            "establishes": [
                "the cycles from the acknowledgement of a producer's last "
                "completion at rtl/abi3/ot_a3_issue_record_store.sv to the "
                "admission of its consumer into an engine queue, with "
                "rtl/abi3/ot_a3_event_scoreboard.sv's wait-set evaluation "
                "between them, on both simulators and with the same number",
                "that the span does not grow with the width of the wait set: a "
                "twelve-producer set costs what a one-producer set costs, "
                "which is what the three-chunk four-port lookup of section 3.6 "
                "predicts and what nothing had measured",
                "that a producer still outstanding makes the consumer STALL "
                "and then pass, and that a producer that is neither pending "
                "nor signalled traps class 13 -- the two halves of section "
                "3.6's rule, exercised rather than asserted",
                "that admission behind a full engine queue costs the drain, "
                "measured at two different drain delays",
            ],
            "does_not_establish": {
                "the_boundary_of_item_13": (
                    "this is the control half of a dependent boundary.  The "
                    "producer tile's own last-result path (T64 measures its "
                    "per-K-block cycles separately) and the operand broadcast "
                    "into the consumer tile's activation FIFO (no design RTL "
                    "exists; the T64 bench models an H-tree and says so) are "
                    "not in this span, so it is a lower bound on the boundary "
                    "and not the boundary"
                ),
                "mesh_traversal": (
                    "rtl/abi3/ot_a3_mesh_router.sv's crossbar is combinational "
                    "by design -- 'every cycle of a traversal is spent in the "
                    "link channel, not in the router' -- so span_mesh_cycles is "
                    "this top's injection register and its observation cycle, "
                    "not a traversal, and it is excluded from "
                    "boundary_control_cycles.  Wiring two routers back to back "
                    "in both directions closes a combinational loop, which is "
                    "the same statement in another form.  The traversal term is "
                    "measured in results/rtl/a3_link_campaign.json"
                ),
                "physical_realisability": (
                    "simulation says nothing about area, timing or power; no "
                    "routed record of this composition exists"
                ),
                "engine_arithmetic": (
                    "no engine runs here.  The producer's completion is a pulse "
                    "on the issue record store's completion port, which is "
                    "where a real engine's completion enters the front end"
                ),
                "the_shipped_programs": (
                    "the wait sets here are built by the case table, not read "
                    "from a deployment.  What the shipped programs' wait sets "
                    "cost is the deployment co-simulation's business"
                ),
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
            "python": {"executable": sys.executable,
                       "version": sys.version.split()[0]},
        },
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

    from tools.build_abi3_boundary_control_vectors import build_cases, emit
    manifest = emit(build_cases(), build)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    committed = None
    if MANIFEST.exists():
        committed = json.loads(MANIFEST.read_text())
    manifest_matches = committed is not None and (
        committed.get("image_sha256") == manifest["image_sha256"])
    manifest["vector_manifest_matches_committed"] = bool(manifest_matches)

    entries = [run_iverilog(build), run_verilator(build, verilator)]
    body = build_artifact(entries, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(body), encoding="utf-8")
    for entry in entries:
        print(f"{entry['name']}: {entry['status'].upper()} "
              f"cases={entry['case_count']} checks={entry['checks']}")
    b = body["boundary"]
    print(f"control boundary: {b['cycles']} cycles, simulators agree "
          f"{b['simulators_agree']}")
    print(f"abi3 boundary control campaign: {body['status'].upper()} -> {args.output}")
    if tmp is not None:
        tmp.cleanup()
    return 0 if body["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
