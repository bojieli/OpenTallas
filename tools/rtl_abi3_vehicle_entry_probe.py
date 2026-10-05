#!/usr/bin/env python3
"""Measure what the integrated vehicle's control plane does at each entry PC.

``tools/build_abi3_vehicle_reachability.py`` derives, from each deployment's
own program and descriptors, whether a transaction entered at a given PC can
execute a given operator.  A derivation is a prediction.  This campaign runs
the prediction against the RTL: it elaborates the integrated shipped-prefix
top, replays the derived probe plan through the design's own configuration
port, and requires the sequencer's measured verdict -- trap class, trapped PC,
and whether anything issued -- to equal the derivation's, probe by probe.

Two probe kinds carry the argument, and the campaign fails if either is
missing:

``own_pc_entry``   the shape the standing plan proposed -- "one case per
                   family entering at that family's own PC".  These cost zero
                   MACs because they refuse before dispatch.
``positive_control`` a mid-program entry, strictly past the deployed
                   entrypoint, at an engine instruction that carries no wait
                   set.  It must dispatch.  Without it, a uniform refusal
                   could be read as "this vehicle refuses any entry but the
                   entrypoint", which is a different and weaker claim.

A probe whose measured verdict differs from the derived one is a failure of
this campaign, not a correction to the derivation: two independent accounts of
the same machine disagreeing is the finding.
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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import rtl_abi3_shipped_prefix_campaign as prefix  # noqa: E402
from tools import build_abi3_vehicle_reachability as reach  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_vehicle_entry_probe.v1"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_vehicle_entry_probe.json"
MARKER = "PASS: ABI3 vehicle entry probe"
PROBE_RE = re.compile(
    r"^PROBE case=(?P<case>\d+) entry=(?P<entry>\d+) ic=(?P<ic>\d+) "
    r"trap=(?P<trap>\d+) fault=(?P<fault>\d+) launches=(?P<launches>\d+) "
    r"issued=(?P<issued>\d+) fetched=(?P<fetched>\d+) retired=(?P<retired>\d+) "
    r"capability=(?P<capability>\d+) cycles=(?P<cycles>\d+)$",
    re.MULTILINE,
)
# The vehicle's four cases are the four shipped decode transactions, in the
# order the vector set carries them; the map is derived from the vector set's
# own case names rather than written down.
TRAP_INTERNAL = 13
TRAP_ILLEGAL = 5
TRAP_CAPABILITY = 4


def sha256_file(path: Path) -> str:
    return prefix.sha256_file(path)


def run(
    build_root: Path | None = None, vector_dir: Path | None = None
) -> dict[str, Any]:
    # The vector set supplies the four case configurations the probe drives
    # the design with -- program base, descriptor base and the request's
    # sixteen symbols -- so the campaign has to say WHICH vector set it used.
    # ``--vectors`` points it at one built outside testdata, which is how it
    # runs while the committed set is being rebuilt against a re-lowered
    # bundle; the directory and the manifest digest go into the artifact.
    if vector_dir is not None:
        prefix.VECTOR_DIR = vector_dir
        prefix.VECTOR_JSON = vector_dir / "abi3_shipped_prefix_vectors.json"
    vectors = prefix.load_vectors()
    case_index = {
        case["name"].split("/")[0]: index
        for index, case in enumerate(vectors["cases"])
    }
    with tempfile.TemporaryDirectory(prefix="opentallas-a3-entry-probe-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        derivation_path = build / "abi3_vehicle_reachability.json"
        plan_path = build / "abi3_vehicle_reachability_probe_plan.json"
        reach.build(
            ["--output", str(derivation_path), "--probe-plan", str(plan_path)]
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        probes = [
            probe
            for probe in plan["probes"]
            if probe["kind"] in ("own_pc_entry", "positive_control")
        ]
        if not probes:
            raise SystemExit("the derivation produced no probes to measure")
        lines = []
        for probe in probes:
            index = case_index.get(probe["target"])
            if index is None:
                raise SystemExit(
                    f"the vehicle has no case for target {probe['target']}"
                )
            probe["case_index"] = index
            lines.append(
                f"{index} {probe['entry_pc']} {probe['instruction_count']}"
            )
        (build / "probe_plan.txt").write_text("\n".join(lines) + "\n")

        for name in prefix.DEPLOYMENT_IMAGES:
            shutil.copy2(prefix.DEPLOYMENT_VECTOR_DIR / name, build / name)
        for name in prefix.VECTOR_FILES:
            shutil.copy2(prefix.VECTOR_DIR / name, build / name)
        if not (build / "p3_matmul_weight.bin").exists():
            prefix.stage_matmul_weight(vectors, build / "p3_matmul_weight.bin")

        executables = {
            "verilator": prefix.resolve(
                "verilator",
                prefix.TOOLS_ROOT
                / f"verilator-{prefix.PINNED_VERILATOR_VERSION}/bin/verilator",
            ),
            "cxx": prefix.resolve("g++", None),
        }
        tools = {
            name: prefix.tool_record(path, ["--version"])
            for name, path in executables.items()
        }
        prefix.require_versions(tools)
        compile_command = [
            str(executables["verilator"]),
            "--cc",
            "--exe",
            "--build",
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
        compiled = prefix.run_stage("probe.compile", compile_command, build, 3600)
        executed = None
        if compiled["returncode"] == 0:
            environment = dict(os.environ)
            environment["OT_A3_ENTRY_PROBE"] = "probe_plan.txt"
            result = subprocess.run(
                ["./obj_probe/Vot_a3_shipped_prefix_top"],
                cwd=build,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=environment,
                timeout=7200,
            )
            executed = {
                "name": "probe.run",
                "command": "OT_A3_ENTRY_PROBE=probe_plan.txt "
                "./obj_probe/Vot_a3_shipped_prefix_top",
                "returncode": result.returncode,
                "log": prefix.canonical(result.stdout, build),
            }
        log = executed["log"] if executed else ""
        measured = [
            {key: int(value) for key, value in match.groupdict().items()}
            for match in PROBE_RE.finditer(log)
        ]
        derivation = json.loads(derivation_path.read_text(encoding="utf-8"))

    comparisons: list[dict[str, Any]] = []
    if len(measured) == len(probes):
        for probe, observation in zip(probes, measured):
            dispatched = observation["trap"] != TRAP_INTERNAL
            echoed = (
                observation["case"] == probe["case_index"]
                and observation["entry"] == probe["entry_pc"]
                and observation["ic"] == probe["instruction_count"]
            )
            if probe["predicted_dispatches_the_site"]:
                # The derivation models the sequencer, not the engine bridge:
                # once an instruction dispatches, the trap class that follows
                # is the bridge's answer and is a different measurement.  So
                # a predicted dispatch is checked as a dispatch -- the
                # instruction issued and the wait set did not refuse it.
                agrees = echoed and dispatched and observation["issued"] >= 1
            else:
                # A predicted refusal is checked exactly: the class, the PC it
                # names, and that nothing issued.
                agrees = (
                    echoed
                    and observation["trap"] == probe["predicted_trap_class"]
                    and observation["fault"] == probe["predicted_trap_pc"]
                    and observation["issued"] == 0
                )
            comparisons.append(
                {
                    "kind": probe["kind"],
                    "target": probe["target"],
                    "family": probe["family"],
                    "site_pc": probe["site_pc"],
                    "entry_pc": probe["entry_pc"],
                    "instruction_count": probe["instruction_count"],
                    "predicted": {
                        "dispatches_the_site": probe[
                            "predicted_dispatches_the_site"
                        ],
                        "trap_class": probe["predicted_trap_class"],
                        "trap_pc": probe["predicted_trap_pc"],
                    },
                    "measured": {
                        "dispatches_the_site": dispatched,
                        "trap_class": observation["trap"],
                        "trap_pc": observation["fault"],
                        "issued": observation["issued"],
                        "engine_launches": observation["launches"],
                        "capability_faults": observation["capability"],
                        "simulated_cycles": observation["cycles"],
                    },
                    "agrees": agrees,
                }
            )
    disagreements = [entry for entry in comparisons if not entry["agrees"]]
    underived = [
        {
            "target": target["target"],
            "family": family["family"],
            "pc": site["pc"],
            "reason": site["underivable_reason"],
        }
        for target in derivation["targets"]
        for family in target["families"]
        for site in family["issue_sites"]
        if not site["derivable"]
    ]
    controls = [
        entry for entry in comparisons if entry["kind"] == "positive_control"
    ]
    own_pc = [entry for entry in comparisons if entry["kind"] == "own_pc_entry"]
    passed = (
        compiled["returncode"] == 0
        and executed is not None
        and executed["returncode"] == 0
        and MARKER in log
        and len(measured) == len(probes)
        and not disagreements
        and bool(controls)
        and all(entry["measured"]["dispatches_the_site"] for entry in controls)
    )
    source_paths = (
        *prefix.RTL_SOURCES,
        "rtl/test/a3_engine_completion_adapter.sv",
        "rtl/test/a3_shipped_prefix_top.sv",
        "rtl/test/a3_shipped_prefix_harness.cpp",
        "tools/build_abi3_vehicle_reachability.py",
        "tools/rtl_abi3_vehicle_entry_probe.py",
        "tools/build_abi3_shipped_prefix_vectors.py",
    )
    return {
        "schema": SCHEMA,
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_rtl_simulation",
        "simulator": "verilator_cpp_executable",
        "claim": (
            "the integrated vehicle's control plane refuses to execute an "
            "operator whose wait-set producers the transaction did not issue, "
            "so entering a case at the operator's own PC cannot reach it"
        ),
        "does_not_establish": [
            "that an operator reachable from a legal entry is bit-exact: this "
            "campaign measures the control plane's verdict, not any result "
            "word",
            "that the engine bridge admits a family it dispatches: a "
            "dispatched instruction may still be refused TRAP_CAPABILITY at "
            "the bridge, which is a different measurement",
        ],
        "vector_set": {
            "directory": prefix.canonical(str(prefix.VECTOR_DIR), ROOT),
            "manifest_sha256": sha256_file(prefix.VECTOR_JSON),
            # False means the vector set is not the committed one, so this
            # record has to be re-run against the committed set before it can
            # stand as source-bound evidence.  It is stated here rather than
            # left to a reader to infer from a path.
            "committed": prefix.VECTOR_DIR
            == ROOT / "testdata/compiler/abi3_shipped_prefix",
        },
        "probe_count": len(probes),
        "measured_probe_count": len(measured),
        "own_pc_entry_probe_count": len(own_pc),
        "own_pc_entries_that_dispatched": sum(
            1 for entry in own_pc if entry["measured"]["dispatches_the_site"]
        ),
        "positive_control_count": len(controls),
        "disagreement_count": len(disagreements),
        "underived_site_count": len(underived),
        "underived_sites": underived,
        "simulated_cycles": sum(
            entry["measured"]["simulated_cycles"] for entry in comparisons
        ),
        "required_marker": MARKER,
        "marker_present": MARKER in log,
        "tools": tools,
        "derivation": derivation,
        "comparisons": comparisons,
        "compile_returncode": compiled["returncode"],
        "compile_log": compiled["log"],
        "run_returncode": executed["returncode"] if executed else None,
        "run_log": log,
        "git": prefix.git_identity(),
        "source_sha256": {
            path: sha256_file(ROOT / path) for path in source_paths
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-root", type=Path, default=None)
    parser.add_argument(
        "--vectors",
        type=Path,
        default=None,
        help="use a shipped-prefix vector set outside testdata; its path and "
        "manifest digest are recorded in the artifact",
    )
    args = parser.parse_args(argv)
    record = run(args.build_root, args.vectors)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(
        f"abi3 vehicle entry probe: {record['status']} "
        f"probes={record['measured_probe_count']}/{record['probe_count']} "
        f"own_pc_dispatched={record['own_pc_entries_that_dispatched']} "
        f"controls={record['positive_control_count']} "
        f"disagreements={record['disagreement_count']} "
        f"underived={record['underived_site_count']} "
        f"cycles={record['simulated_cycles']}"
    )
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
