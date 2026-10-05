#!/usr/bin/env python3
"""Run the dual-simulator VECTOR.ENGRAM_GATE campaign over four geometries.

Eight simulator legs: Icarus and the PINNED Verilator 5.050, each over the four
(VECTOR_WIDTH, LANES, ACC_EXP_MAX) geometries the vector builder emits, plus one
pinned-Yosys elaboration of the block.  Every expected word comes from
``runtime/reference/engram.py``; nothing in this file computes an expected value.

The Verilator legs use ``--binary`` with the SystemVerilog testbench, so plusargs
reach the model through the generated main and no local ``VerilatedContext`` is
constructed.  A C++ harness would have to call ``commandArgs`` on the context
that owns the model; this campaign avoids the question by not having one.

Reported cycles and wall times are verification cost.  They are not
architectural latency, not a frequency claim, and not a TPOT.
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
import tempfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VECTOR_DIR = ROOT / "testdata/rtl/a3_v41_engram_gate"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_v41_engram_gate_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

TOP_MODULE = "ot_a3_vector_engram_gate"
TESTBENCH = "tb_a3_v41_engram_gate"

#: Everything the elaborated block needs, in dependency order.
SYNTH_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv",
    "rtl/abi3/ot_a3_engram_exact_dot_tree.sv",
    "rtl/abi3/ot_a3_vector_engram_gate.sv",
)
RTL_SOURCES = SYNTH_SOURCES + ("rtl/test/tb_a3_v41_engram_gate.sv",)
ORACLE_SOURCES = (
    "runtime/reference/formats.py",
    "runtime/reference/hyper_connection.py",
    "runtime/reference/engram.py",
    "tools/build_a3_v41_engram_gate_vectors.py",
    "tools/run_a3_v41_engram_gate_rtl_campaign.py",
)
VECTOR_FILES = (
    "meta.hex",
    "cases.hex",
    "input.hex",
    "expect_g0.hex",
    "expect_g1.hex",
    "expect_g2.hex",
    "expect_g3.hex",
    "index.json",
)

SUMMARY_RE = re.compile(r"^ENGRAM_GATE_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(
    r"^PASS a3_v41_engram_gate cases=(?P<cases>\d+) checks=(?P<checks>\d+)$"
)
PAIR_RE = re.compile(r"(?P<key>[a-z_0-9]+)=(?P<value>-?\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
YOSYS_RE = re.compile(r"Yosys (?P<major>\d+)\.(?P<minor>\d+)")

#: Counters the summary reports that the manifest does not predict, because they
#: are verification cost rather than a property of the contract.
COST_KEYS = frozenset({"max_cycles"})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub(value: str, temporary_root: Path | None = None) -> str:
    if temporary_root is not None:
        value = value.replace(str(temporary_root), "<TMP>")
    return value.replace(str(ROOT), "<ROOT>").replace(str(Path.home()), "<HOME>")


def run(command: list[str], *, timeout: int) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"command timed out after {timeout}s") from exc
    return process, time.monotonic() - started


def tool_identity(
    executable: Path,
    arguments: list[str],
    pattern: re.Pattern[str],
    expected: tuple[int, int] | None,
    label: str,
) -> dict[str, str]:
    process, _ = run([str(executable), *arguments], timeout=60)
    output = (process.stdout + process.stderr).strip()
    match = pattern.search(output)
    if process.returncode or match is None:
        raise RuntimeError(f"cannot identify {label}: {output}")
    observed = (int(match.group("major")), int(match.group("minor")))
    if expected is not None and observed != expected:
        raise RuntimeError(f"{label} version {observed} is not pinned {expected}")
    resolved = executable.resolve()
    return {
        "path": scrub(str(resolved)),
        "sha256": sha256(resolved),
        "version": output.splitlines()[0],
    }


def resolve_tools() -> tuple[Path, Path, Path, Path]:
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    yosys = TOOLS_ROOT / f"yosys-{PINNED_YOSYS_VERSION}/bin/yosys"
    if not iverilog or not vvp:
        raise RuntimeError("iverilog and vvp must be on PATH")
    if not verilator.is_file():
        raise RuntimeError(f"pinned Verilator {PINNED_VERILATOR_VERSION} is absent")
    if not yosys.is_file():
        raise RuntimeError(f"pinned Yosys {PINNED_YOSYS_VERSION} is absent")
    return Path(iverilog), Path(vvp), verilator, yosys


def plusargs(geometry_name: str) -> list[str]:
    return [
        f"+META={VECTOR_DIR / 'meta.hex'}",
        f"+REQUESTS={VECTOR_DIR / 'cases.hex'}",
        f"+INPUTS={VECTOR_DIR / 'input.hex'}",
        f"+EXPECTED={VECTOR_DIR / f'expect_{geometry_name}.hex'}",
    ]


def parse_log(log: str) -> tuple[dict[str, int], dict[str, int]]:
    summary: dict[str, int] | None = None
    passed: dict[str, int] | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = SUMMARY_RE.match(line)
        if match:
            summary = {
                item.group("key"): int(item.group("value"))
                for item in PAIR_RE.finditer(match.group("body"))
            }
        match = PASS_RE.match(line)
        if match:
            passed = {key: int(value) for key, value in match.groupdict().items()}
    if summary is None or passed is None:
        raise RuntimeError("simulator did not emit the exact summary and PASS markers")
    return summary, passed


def validate_leg(
    summary: dict[str, int],
    passed: dict[str, int],
    manifest: dict[str, Any],
    geometry_name: str,
) -> None:
    """Compare a leg against the manifest's own derived expectation."""

    expected = manifest["per_geometry_aggregate"][geometry_name]
    observed = {key: value for key, value in summary.items() if key not in COST_KEYS}
    predicted = {key: value for key, value in expected.items() if key != "checks"}
    if observed != predicted:
        difference = {
            key: (observed.get(key), predicted.get(key))
            for key in set(observed) | set(predicted)
            if observed.get(key) != predicted.get(key)
        }
        raise RuntimeError(f"{geometry_name} summary differs from the reference: {difference}")
    if passed["cases"] != expected["cases"] or passed["checks"] != expected["checks"]:
        raise RuntimeError(
            f"{geometry_name} PASS marker differs: {passed} != "
            f"{{'cases': {expected['cases']}, 'checks': {expected['checks']}}}"
        )


def regenerate_and_compare(temporary: Path) -> dict[str, Any]:
    generated = temporary / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_v41_engram_gate_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=600,
    )
    if process.returncode:
        raise RuntimeError(
            f"vector generation failed:\n{process.stdout}\n{process.stderr}"
        )
    for filename in VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")
    return json.loads((generated / "index.json").read_text())


def function_sha256(module_path: Path, name: str) -> str:
    """Digest the named function's own source text.

    ``runtime/reference/engram.py`` is shared with the NGRAM_HASH unit, which
    appends to it, so the whole-file digest moves when that unit lands.  The
    digest of this unit's own function does not, and it is the digest that says
    whether the semantics this campaign ran against have changed.
    """

    import ast

    source = module_path.read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is None:  # pragma: no cover - ast always returns a segment
                raise RuntimeError(f"cannot extract {name}")
            return hashlib.sha256(segment.encode()).hexdigest()
    raise RuntimeError(f"{module_path} does not define {name}")


def campaign(output: Path) -> dict[str, Any]:
    iverilog, vvp, verilator, yosys = resolve_tools()
    tools = {
        "iverilog": tool_identity(iverilog, ["-V"], IVERILOG_RE, None, "Icarus"),
        "vvp": {"path": scrub(str(vvp.resolve())), "sha256": sha256(vvp.resolve())},
        "verilator": tool_identity(
            verilator, ["--version"], VERILATOR_RE, (5, 50), "Verilator"
        ),
        "yosys": tool_identity(yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"),
    }

    legs: list[dict[str, Any]] = []
    wall: dict[str, float] = {}
    logs: dict[str, str] = {}
    simulators_agree = True

    with tempfile.TemporaryDirectory(prefix="a3-v41-engram-gate-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)
        geometries = manifest["geometries"]

        for geometry in geometries:
            label = geometry["name"]
            overrides = {
                "GATE_VECTOR_WIDTH": geometry["vector_width"],
                "GATE_LANES": geometry["lanes"],
                "GATE_ACC_EXP_MIN": manifest["exactness_window"]["acc_exp_min"],
                "GATE_ACC_EXP_MAX": geometry["acc_exp_max"],
            }

            icarus_binary = temporary / f"tb_{label}.vvp"
            process, compile_seconds = run(
                [
                    str(iverilog),
                    "-g2012",
                    *[
                        f"-P{TESTBENCH}.{key}={value}"
                        for key, value in overrides.items()
                    ],
                    "-s",
                    TESTBENCH,
                    "-o",
                    str(icarus_binary),
                    *[str(ROOT / source) for source in RTL_SOURCES],
                ],
                timeout=600,
            )
            if process.returncode:
                raise RuntimeError(
                    f"Icarus compile failed for {label}:\n{process.stdout}\n{process.stderr}"
                )
            process, icarus_seconds = run(
                [str(vvp), str(icarus_binary), *plusargs(label)], timeout=1800
            )
            icarus_log = process.stdout + process.stderr
            if process.returncode:
                raise RuntimeError(f"Icarus simulation failed for {label}:\n{icarus_log}")
            icarus_summary, icarus_pass = parse_log(icarus_log)
            validate_leg(icarus_summary, icarus_pass, manifest, label)

            verilator_dir = temporary / f"verilator_{label}"
            process, verilator_compile_seconds = run(
                [
                    str(verilator),
                    "--binary",
                    "--timing",
                    "--top-module",
                    TESTBENCH,
                    *[f"-G{key}={value}" for key, value in overrides.items()],
                    "--Mdir",
                    str(verilator_dir),
                    "-o",
                    "sim",
                    "-Wno-fatal",
                    *[str(ROOT / source) for source in RTL_SOURCES],
                ],
                timeout=1800,
            )
            verilator_compile_log = process.stdout + process.stderr
            if process.returncode:
                raise RuntimeError(
                    f"Verilator compile failed for {label}:\n{verilator_compile_log}"
                )
            process, verilator_seconds = run(
                [str(verilator_dir / "sim"), *plusargs(label)], timeout=1800
            )
            verilator_log = process.stdout + process.stderr
            if process.returncode:
                raise RuntimeError(
                    f"Verilator simulation failed for {label}:\n{verilator_log}"
                )
            verilator_summary, verilator_pass = parse_log(verilator_log)
            validate_leg(verilator_summary, verilator_pass, manifest, label)

            agree = (
                icarus_summary == verilator_summary and icarus_pass == verilator_pass
            )
            simulators_agree = simulators_agree and agree
            legs.append(
                {
                    "geometry": label,
                    "vector_width": geometry["vector_width"],
                    "lanes": geometry["lanes"],
                    "acc_exp_max": geometry["acc_exp_max"],
                    "icarus_summary": icarus_summary,
                    "verilator_summary": verilator_summary,
                    "icarus_checks": icarus_pass["checks"],
                    "verilator_checks": verilator_pass["checks"],
                    "simulators_agree": agree,
                }
            )
            wall[f"{label}_iverilog_compile"] = compile_seconds
            wall[f"{label}_iverilog_simulation"] = icarus_seconds
            wall[f"{label}_verilator_compile"] = verilator_compile_seconds
            wall[f"{label}_verilator_simulation"] = verilator_seconds
            logs[f"{label}_iverilog"] = icarus_log
            logs[f"{label}_verilator_compile"] = verilator_compile_log
            logs[f"{label}_verilator"] = verilator_log

        if not simulators_agree:
            raise RuntimeError("Icarus and Verilator results differ")

        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + f"; hierarchy -check -top {TOP_MODULE}; proc; opt; check; stat"
        )
        process, yosys_seconds = run([str(yosys), "-Q", "-p", yosys_script], timeout=900)
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration failed:\n{yosys_log}")
        wall["yosys_elaboration"] = yosys_seconds
        logs["yosys"] = yosys_log

    #: The geometry-independence claim, restated from the legs rather than from
    #: the manifest: every geometry ran the same case list, and the computed
    #: codes the manifest emitted for g0 and g1 were already proved identical by
    #: the builder, which refuses to emit them otherwise.
    lane_independent = all(
        leg["icarus_summary"]["cases"] == legs[0]["icarus_summary"]["cases"]
        for leg in legs
    )

    source_paths = [ROOT / path for path in (*RTL_SOURCES, *ORACLE_SOURCES)]
    result: dict[str, Any] = {
        "schema": "opentallas.rtl.a3_v41_engram_gate_campaign.v1",
        "status": "pass",
        "abi": {"major": 3, "minor": 0},
        "unit": {
            "engine": "VECTOR",
            "sub_opcode": "0x0d",
            "sub_opcode_name": "A3_VECTOR_ENGRAM_GATE",
            "ir_kind": "ENGRAM_GATE",
            "ir_signature": "ENGRAM_GATE(h, key, value, q, k) -> h_out",
            "numeric_contract": manifest["numeric_contract"],
            "top_module": TOP_MODULE,
            "amendment": "AM-E10",
            "work_package": "WP-K",
        },
        "pipeline": {
            "reduction_phase_stages": "4 + clog2(LANES); six at LANES=4",
            "reduction_phase_initiation_interval_groups_per_cycle": 1,
            "reduction_phase_initiation_interval_elements_per_cycle": "LANES",
            "combine_phase_stages": 5,
            "combine_phase_initiation_interval_groups_per_cycle": 1,
            "square_root_stages": "FRAC_SHIFT + 15; thirty at FRAC_SHIFT=15",
            "square_root_initiation_interval": 1,
            "square_root_evaluations_per_transaction": 3,
            "registered_reduction_tree": True,
            #: MEASURED, not asserted: for every retiring case the scoreboard
            #: checks that each streaming phase issued ceil(count/LANES) groups
            #: in exactly that many CONSECUTIVE cycles, and that the write port
            #: retired over the same span.  A one-cycle stall widens a span
            #: without changing a count; a skipped group changes a count without
            #: widening a span.
            "initiation_interval_measured": True,
            "initiation_interval_measurement": (
                "issue count and issue span of both streaming phases, and the "
                "write-port span, per retiring case"
            ),
            "serial_accumulator_over_one_float_adder": False,
            "combinational_path_spanning_a_whole_vector": False,
            "multi_cycle_reused_blocks": [
                "ot_a3_fp32_div_rne",
                "ot_a3_fp32_transcendental_cr_rne",
            ],
        },
        "geometry": {
            "parameterised": [
                "VECTOR_WIDTH",
                "LANES",
                "ACC_EXP_MIN",
                "ACC_EXP_MAX",
                "GATE_EPSILON_CODE",
                "SQRT_FRAC_SHIFT",
            ],
            "row_length_source": "cfg_count operand field, not a parameter",
            "legs": [
                {
                    "geometry": leg["geometry"],
                    "vector_width": leg["vector_width"],
                    "lanes": leg["lanes"],
                    "acc_exp_max": leg["acc_exp_max"],
                }
                for leg in legs
            ],
            "same_case_list_on_every_geometry": lane_independent,
            "lane_count_changes_no_computed_code": manifest[
                "geometry_independence"
            ]["computed_codes_identical_across_lanes"],
            "rows_longer_than_the_v41_width_accepted_when_built_for_them": True,
        },
        "reference": {
            "module": "runtime/reference/engram.py",
            "function": "engram_gate",
            "function_sha256": function_sha256(
                ROOT / "runtime/reference/engram.py", "engram_gate"
            ),
            "shared_with_other_unit": True,
            "shared_file_digest_moves_when_ngram_hash_lands": True,
            "derivation": (
                "written from the mechanism semantics of the V4.1 plan section 5 "
                "row 6 and the exact binary32 primitives of "
                "runtime/reference/formats.py; no RTL was transcribed"
            ),
            "independent_square_root": (
                "math.isqrt candidate plus an exact midpoint-square comparison, "
                "which is neither the RTL digit recurrence nor the code-space "
                "bisection in runtime/reference/sqrt_softplus.py"
            ),
        },
        "aggregate": {
            "geometries": len(legs),
            "simulator_legs": 2 * len(legs),
            "cases_per_leg": manifest["case_count"],
            "checks_per_leg": {
                leg["geometry"]: leg["icarus_checks"] for leg in legs
            },
            "checks_per_simulator": sum(leg["icarus_checks"] for leg in legs),
            "total_word_comparisons": sum(
                leg["icarus_checks"] + leg["verilator_checks"] for leg in legs
            ),
            "output_words_compared_per_simulator": sum(
                leg["icarus_summary"]["output_word_checks"] for leg in legs
            ),
            "sentinel_words_checked_per_simulator": sum(
                leg["icarus_summary"]["sentinel_checks"] for leg in legs
            ),
            "scalar_words_compared_per_simulator": sum(
                leg["icarus_summary"]["scalar_checks"] for leg in legs
            ),
            "elements_reduced_per_simulator": sum(
                leg["icarus_summary"]["elements_reduced"] for leg in legs
            ),
            "initiation_interval_checks_per_simulator": sum(
                leg["icarus_summary"]["initiation_interval_checks"]
                for leg in legs
            ),
            "refusal_sites_covered": manifest["refusal_sites_covered"],
            "refusal_sites_unreachable": sorted(
                manifest["refusal_sites_unreachable"]
            ),
        },
        "refusal_sites_unreachable_reasons": manifest["refusal_sites_unreachable"],
        "legs": legs,
        "simulators_agree": simulators_agree,
        "claim_boundary": {
            "bit_exact_against_an_independent_python_reference": True,
            "dual_simulator": True,
            "synthesizable_elaboration": True,
            "geometry_swept_over_four_parameter_sets": True,
            "establishes_vendor_engram_forward_equivalence": False,
            "vendor_inference_engram_py_present_in_this_checkout": False,
            "establishes_the_operand_role_mapping_of_the_vendor_module": False,
            "establishes_target_frequency_or_timing_closure": False,
            "is_placed_or_routed": False,
            "establishes_area_or_power": False,
            "establishes_a_token_a_layer_or_a_tpot": False,
            "integrates_the_engine_issue_bridge_or_a_descriptor_decode": False,
            "executes_the_engram_row_gather_or_the_ngram_hash": False,
            "establishes_the_fp8_engram_key_value_projection": False,
            "covers_refusal_sites_6_to_10": False,
            "covers_a_normalised_dot_whose_magnitude_exceeds_one": False,
            "exhausts_the_binary32_input_space": False,
            "establishes_rounding_tie_coverage_of_the_residual_add": False,
            "initiation_interval_of_one_measured_at_both_ports": True,
            "reported_cycles_are_verification_cost_only": True,
        },
        "claim_boundary_notes": {
            "vendor_equivalence": (
                "inference/engram.py at revision "
                "dba1be0a40aa45a94ad051997016db3960a90277 is not in this "
                "checkout.  The contract implemented here is the mechanism the "
                "plan states, written as an explicit deterministic target "
                "adaptation.  Confirming the operand roles and the reduction "
                "convention against the vendor source is WP-H work and is open."
            ),
            "reduction_convention": (
                "engram_gate_fp32_v1 specifies the three reductions as EXACT "
                "sums rounded once, which makes them order independent.  A "
                "vendor implementation that rounds per addition would differ in "
                "the last bits; that difference is unmeasured here."
            ),
            "frequency": (
                "each combine-phase stage is one qualified binary32 operation "
                "from ot_fp32_rne_pkg, a block class rtl/proto measures at "
                "174 MHz standalone.  No frequency is established by simulation; "
                "the >500 MHz question is WP-M physical work."
            ),
            "refusal_sites_6_to_10": (
                "structurally unreachable rather than untested: each is bounded "
                "by the exactness-window parameters, and the bounds are recorded "
                "in refusal_sites_unreachable_reasons."
            ),
            "normalised_dot_magnitude": (
                "Cauchy-Schwarz bounds the unclamped normalised dot by one and "
                "the clamp only shrinks it, so no case in this campaign presents "
                "the signed square root with an argument above one."
            ),
        },
        "vector_manifest": {
            "schema": manifest["schema"],
            "case_count": manifest["case_count"],
            "vector_limit": manifest["vector_limit"],
            "epsilon_binary32": manifest["epsilon_binary32"],
            "exactness_window": manifest["exactness_window"],
            "geometry_independence": manifest["geometry_independence"],
        },
        "synthesis_frontend": {
            "top": TOP_MODULE,
            "check_problems": 0,
            "note": (
                "generic synthesizable elaboration only; no library mapping, "
                "no PPA, no token latency and no TPOT claim"
            ),
        },
        "verification_wall_seconds": wall,
        "tools": tools,
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path) for path in source_paths
        },
        "vector_sha256": {
            filename: sha256(VECTOR_DIR / filename) for filename in VECTOR_FILES
        },
        "log_sha256": {
            key: hashlib.sha256(value.encode()).hexdigest()
            for key, value in logs.items()
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def validate_retained(path: Path = DEFAULT_OUTPUT) -> list[str]:
    """Check the retained record against the tree it claims to describe."""

    if not path.is_file():
        return [f"missing retained campaign: {path}"]
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read retained campaign: {exc}"]
    problems: list[str] = []
    if value.get("status") != "pass":
        problems.append("campaign status differs")
    if not value.get("simulators_agree"):
        problems.append("the two simulators did not agree")
    if len(value.get("legs", ())) != 4:
        problems.append("geometry leg count differs")
    for source, expected in value.get("source_sha256", {}).items():
        candidate = ROOT / source
        #: runtime/reference/engram.py is shared with the NGRAM_HASH unit, whose
        #: append moves the file digest without touching this unit's semantics.
        #: The function digest is the binding one, so the file is reported as
        #: shared drift rather than as a failure.
        if not candidate.is_file():
            problems.append(f"missing source: {source}")
        elif sha256(candidate) != expected:
            if source == "runtime/reference/engram.py":
                function = value.get("reference", {}).get("function_sha256")
                if function_sha256(candidate, "engram_gate") != function:
                    problems.append("engram_gate semantics drifted")
            else:
                problems.append(f"source drift: {source}")
    for filename, expected in value.get("vector_sha256", {}).items():
        candidate = VECTOR_DIR / filename
        if not candidate.is_file() or sha256(candidate) != expected:
            problems.append(f"vector drift: {filename}")
    return problems


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument(
        "--validate-retained",
        action="store_true",
        help="check the retained record instead of running the campaign",
    )
    return result


def main() -> int:
    arguments = parser().parse_args()
    if arguments.validate_retained:
        problems = validate_retained(arguments.output)
        for problem in problems:
            print(f"PROBLEM {problem}")
        print(f"validate_retained problems={len(problems)}")
        return 1 if problems else 0
    result = campaign(arguments.output)
    print(
        "a3_v41_engram_gate RTL campaign "
        f"status={result['status']} "
        f"geometries={result['aggregate']['geometries']} "
        f"legs={result['aggregate']['simulator_legs']} "
        f"comparisons={result['aggregate']['total_word_comparisons']} "
        f"agree={result['simulators_agree']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
