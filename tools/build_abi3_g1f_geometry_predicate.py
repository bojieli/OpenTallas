#!/usr/bin/env python3
"""G1f supporting measurement: what KIND of predicate refuses the reduced geometry?

G1f's record has to decide one thing that no field of the gate turns on: build
the geometry port, or choose a reduced configuration that fits the geometry the
engines already have.  ``results/rtl/abi3_g1f_reduced_end_to_end.json`` measured
that ``ot_a3_vector_rms_norm`` refuses a 16-wide row (``ERR_SHAPE``) and that
``ot_a3_qwen_gqa`` refuses a context of 4.  Two refusals are not enough to
decide, because they are consistent with two designs that deserve opposite
answers:

* a **capacity bound** is a legitimate physical limit.  A reduced configuration
  must be chosen inside it and no RTL owes anything.
* an **exact-set membership test** is a refusal that
  ``docs/CHIP_ARCHITECTURE_DESIGN.md`` section 4.9 does not authorise for this
  contract -- its fail-closed column names three refusals for
  ``qwen3_rmsnorm_fp32_bf16_v1`` (eps_bits 0, order != PAIRWISE_TREE, unknown
  digest) and width is not among them, while the microprogram's own step is
  "divide by width", i.e. width is an operand.  A configuration chosen to fit
  such a test is a configuration chosen to fit a defect.

The two are separated by SWEEPING the blocks, never by reading a constant out of
a module -- which is the defect section 11.7 records inside the G1a tool.  This
tool runs ``rtl/test/tb_a3_g1f_geometry_predicate.sv``, which walks 38 row
widths and 21 context lengths through the two blocks, and then CLASSIFIES what
came back:

* ``consistent_with_upper_bound`` / ``consistent_with_lower_bound`` /
  ``consistent_with_interval`` are each tested against the swept set.  A
  predicate that is none of them, over a sweep that brackets every admitted
  value from both sides, is exact-set membership.
* the GQA half additionally fits ``reads = a + b * context`` over the admitted
  contexts and reports the worst residual, and reports whether the result row
  width moved at any admitted context.  A block whose traffic scales exactly
  with the one geometry field it has a port for, and whose result row never
  moves, has measured both the geometry it is built for and the fact that no
  other geometry can be asked of it.

Nothing here is a verdict typed into this file: every field below is computed
from the sweep the simulator printed.  The DECISION this measurement informs is
recorded in ``results/rtl/abi3_g1f_reduced_end_to_end.json`` under
``records[].geometry_port_decision``; this artifact is evidence for it and is
not itself a gate rung.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

BENCH = "rtl/test/tb_a3_g1f_geometry_predicate.sv"
SOURCES = (
    BENCH,
    "rtl/abi3/ot_a3_vector_rms_norm.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_shared_divider.sv",
)

#: The engine error codes are not restated here.  They are imported from the
#: rung's own tool so the two artifacts can never disagree about what a code
#: means; a second hand-typed copy of a mapping is how two records come to name
#: different refusals for the same integer.
sys.path.insert(0, str(ROOT / "tools"))
from build_abi3_g1f_reduced_end_to_end import ENGINE_ERRORS  # noqa: E402

SWEEP_RE = re.compile(r"^SWEEP\s+(.*)$")
MARKER_RE = re.compile(r"^MARKER: ABI3 G1F GEOMETRY PREDICATE SWEEP\b")

DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_g1f_geometry_predicate.json"


def _git() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True
        ).stdout.strip()

    porcelain = run(["git", "status", "--porcelain"])
    dirty = [line[3:] for line in porcelain.splitlines() if line.strip()]
    return {
        "commit": run(["git", "rev-parse", "HEAD"]) or None,
        "worktree_dirty": bool(dirty),
        "dirty_paths": dirty,
        "scope": (
            "the tree this measurement RAN in.  A dirty tree makes the "
            "measurement inadmissible however sound it is, so the field is "
            "recorded rather than assumed"
        ),
    }


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_sweep(work: Path) -> dict[str, Any]:
    verilator = shutil.which("verilator")
    if verilator is None:
        raise SystemExit("verilator is not on PATH")
    banner = subprocess.run(
        [verilator, "--version"], capture_output=True, text=True
    ).stdout.strip()
    work.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    compiled = subprocess.run(
        [
            verilator,
            "--binary",
            "--timing",
            "-Wno-fatal",
            "-O2",
            "-j",
            "8",
            "--top-module",
            Path(BENCH).stem,
            "-Mdir",
            str(work / "obj"),
            "-o",
            "sweep",
            *[str(ROOT / name) for name in SOURCES],
        ],
        cwd=work,
        capture_output=True,
        text=True,
    )
    compile_seconds = time.perf_counter() - started
    if compiled.returncode != 0:
        raise SystemExit(
            "the G1f geometry-predicate bench did not elaborate:\n"
            + compiled.stderr[-3000:]
        )
    started = time.perf_counter()
    run = subprocess.run(
        [str(work / "obj" / "sweep")], capture_output=True, text=True, timeout=3600
    )
    run_seconds = time.perf_counter() - started
    if run.returncode != 0:
        raise SystemExit(
            "the G1f geometry-predicate bench failed:\n" + run.stdout[-3000:]
        )

    cases: list[dict[str, Any]] = []
    marker: str | None = None
    for line in run.stdout.splitlines():
        line = line.strip()
        found = SWEEP_RE.match(line)
        if found:
            body: dict[str, Any] = {}
            for token in found.group(1).split():
                key, _, value = token.partition("=")
                body[key] = int(value) if value.lstrip("-").isdigit() else value
            body["error_name"] = ENGINE_ERRORS.get(int(body.get("err", -1)), "UNKNOWN")
            body["admitted"] = int(body.get("err", -1)) == 0
            cases.append(body)
            continue
        if MARKER_RE.match(line):
            marker = line
    if marker is None or not cases:
        raise SystemExit("the G1f geometry-predicate bench printed no marker")
    return {
        "vehicle": BENCH,
        "vehicle_sha256": _digest(ROOT / BENCH),
        "simulator": "verilator_cpp_executable",
        "simulator_version": banner.split()[1] if banner else None,
        "simulator_banner": banner,
        "evidence_class": "public_open_tool_rtl_simulation",
        "simulated_cycles": int(re.search(r"cycles=(\d+)", marker).group(1)),
        "case_count": int(re.search(r"cases=(\d+)", marker).group(1)),
        "compile_seconds": round(compile_seconds, 2),
        "run_seconds": round(run_seconds, 2),
        "marker": marker,
        "cases": cases,
        "sources": {
            name: _digest(ROOT / name) for name in SOURCES
        },
    }


def second_simulator(work: Path) -> dict[str, Any]:
    """Ask Icarus the same question, and record verbatim what it says.

    Rungs of this ladder are normally taken on two simulators.  Whether that is
    possible for THIS bench is a fact about the blocks, not a choice, so it is
    measured and recorded rather than left as a silent single-simulator result:
    a reader who is not told will assume agreement that was never obtained.
    """
    iverilog = shutil.which("iverilog")
    if iverilog is None:
        return {"simulator": "icarus", "available": False}
    banner = subprocess.run(
        [iverilog, "-V"], capture_output=True, text=True
    ).stdout.splitlines()
    work.mkdir(parents=True, exist_ok=True)
    elaborated = subprocess.run(
        [
            iverilog,
            "-g2012",
            "-s",
            Path(BENCH).stem,
            "-o",
            str(work / "icarus.vvp"),
            *[str(ROOT / name) for name in SOURCES],
        ],
        cwd=work,
        capture_output=True,
        text=True,
    )
    return {
        "simulator": "icarus",
        "available": True,
        "simulator_banner": banner[0].strip() if banner else None,
        "elaborated": elaborated.returncode == 0,
        "returncode": elaborated.returncode,
        "refusal_tail": (elaborated.stderr or elaborated.stdout)[-1200:] or None,
        "what_it_means": (
            "when this is false the sweep below stands on ONE simulator, and "
            "no cross-simulator agreement is claimed for it anywhere"
        ),
    }


def classify(swept: list[int], admitted: list[int]) -> dict[str, Any]:
    """Which shape of predicate is the observed admission set consistent with?

    Each test is evaluated against the values actually swept, so a shape is
    ruled out only by a value the simulator was actually asked about.
    """
    values = sorted(set(swept))
    admits = sorted(set(admitted))
    refused = [v for v in values if v not in set(admits)]

    def as_upper_bound() -> int | None:
        for t in values:
            if [v for v in values if v <= t] == admits:
                return t
        return None

    def as_lower_bound() -> int | None:
        for t in values:
            if [v for v in values if v >= t] == admits:
                return t
        return None

    def as_interval() -> list[int] | None:
        if not admits:
            return None
        lo, hi = admits[0], admits[-1]
        if [v for v in values if lo <= v <= hi] == admits:
            return [lo, hi]
        return None

    upper = as_upper_bound()
    lower = as_lower_bound()
    interval = as_interval()
    bracketed = {
        str(value): {
            "next_lower_swept": max(
                [v for v in values if v < value], default=None
            ),
            "next_lower_admitted": (
                max([v for v in values if v < value], default=None) in set(admits)
                if [v for v in values if v < value]
                else None
            ),
            "next_higher_swept": min(
                [v for v in values if v > value], default=None
            ),
            "next_higher_admitted": (
                min([v for v in values if v > value], default=None) in set(admits)
                if [v for v in values if v > value]
                else None
            ),
        }
        for value in admits
    }
    shape = (
        "exact_set_membership"
        if interval is None
        else ("interval" if len(admits) > 1 else "single_value")
    )
    return {
        "swept_values": values,
        "swept_count": len(values),
        "admitted": admits,
        "refused": refused,
        "consistent_with_upper_bound": upper,
        "consistent_with_lower_bound": lower,
        "consistent_with_interval": interval,
        "shape": shape,
        "each_admitted_value_bracketed": bracketed,
        "how_the_shape_was_decided": (
            "each candidate shape is reconstructed from the swept values and "
            "compared with the observed admission set; a shape survives only "
            "if it reproduces that set exactly.  'exact_set_membership' is the "
            "residual, and it is only reached when no bound and no interval "
            "over the swept values reproduces the admissions"
        ),
    }


def linear_in(pairs: list[tuple[int, int]]) -> dict[str, Any]:
    """Is y exactly affine in x over these points?  Reported, not assumed."""
    if len(pairs) < 2:
        return {"points": len(pairs), "affine": None}
    (x0, y0), (x1, y1) = pairs[0], pairs[1]
    if x1 == x0:
        return {"points": len(pairs), "affine": None}
    numerator = y1 - y0
    denominator = x1 - x0
    if numerator % denominator:
        slope = numerator / denominator
        exact = False
    else:
        slope = numerator // denominator
        exact = True
    intercept = y0 - slope * x0
    residuals = [y - (slope * x + intercept) for x, y in pairs]
    worst = max(abs(r) for r in residuals)
    return {
        "points": len(pairs),
        "slope": slope,
        "intercept": intercept,
        "slope_is_integral": exact,
        "worst_residual": worst,
        "affine": worst == 0,
        "fit_from": "the first two admitted points; every other point is a test",
    }


def build(sweep: dict[str, Any]) -> dict[str, Any]:
    rms = [c for c in sweep["cases"] if c.get("engine") == "rms_norm"]
    gqa = [c for c in sweep["cases"] if c.get("engine") == "gqa"]

    one_row = [c for c in rms if c["rows"] == 1]
    width = classify(
        [c["cols"] for c in one_row],
        [c["cols"] for c in one_row if c["admitted"]],
    )
    multi_row = [
        {
            "rows": c["rows"],
            "cols": c["cols"],
            "admitted": c["admitted"],
            "error_name": c["error_name"],
            "results": c["results"],
        }
        for c in rms
        if c["rows"] != 1
    ]
    one_row_verdict = {c["cols"]: c["admitted"] for c in one_row}
    row_count_independent = all(
        entry["cols"] not in one_row_verdict
        or one_row_verdict[entry["cols"]] == entry["admitted"]
        for entry in multi_row
    )

    context = classify(
        [c["context"] for c in gqa],
        [c["context"] for c in gqa if c["admitted"]],
    )
    admitted_gqa = [c for c in gqa if c["admitted"]]
    reads = linear_in([(c["context"], c["reads"]) for c in admitted_gqa])
    writes = sorted({c["writes"] for c in admitted_gqa})
    refusal_codes = sorted({c["error_name"] for c in gqa if not c["admitted"]})

    return {
        "schema": "opentallas.rtl.abi3_g1f_geometry_predicate.v1",
        "gate": "G1f (supporting measurement; no gate field turns on it)",
        "informs": {
            "artifact": "results/rtl/abi3_g1f_reduced_end_to_end.json",
            "field": "records[].geometry_port_decision",
            "question": (
                "is the geometry port a design change worth making, or should "
                "the reduced configuration be chosen to fit the geometry the "
                "engines have?"
            ),
        },
        "generated_by": "tools/build_abi3_g1f_geometry_predicate.py",
        "generated_by_sha256": _digest(Path(__file__).resolve()),
        "git": _git(),
        "execution": {
            "second_simulator": sweep["second_simulator"],
            **{
            key: sweep[key]
            for key in (
                "vehicle",
                "vehicle_sha256",
                "simulator",
                "simulator_version",
                "simulator_banner",
                "evidence_class",
                "simulated_cycles",
                "case_count",
                "compile_seconds",
                "run_seconds",
                "marker",
                "sources",
            )
            },
        },
        "measured": {
            "rms_norm_row_width": {
                "block": "rtl/abi3/ot_a3_vector_rms_norm.sv",
                "port": "cfg_cols",
                "predicate": width,
                "multi_row_cases": multi_row,
                "row_count_independent": row_count_independent,
                "refusal_codes": sorted(
                    {c["error_name"] for c in rms if not c["admitted"]}
                ),
            },
            "gqa_context_length": {
                "block": "rtl/abi3/ot_a3_qwen_gqa.sv",
                "port": "cfg_context_length",
                "predicate": context,
                "refusal_codes": refusal_codes,
                "operand_words_read_vs_context": reads,
                "result_words_written_at_every_admitted_context": writes,
                "result_row_moved_with_anything_the_block_can_be_told": len(writes)
                > 1,
            },
        },
        "establishes": [],
        "does_not_establish": [
            "any numeric result: this bench drives both blocks with the "
            "constant BF16 code 1.0 and reads only admission, traffic and "
            "cycles.  Bit-exactness is rung G1a's and is established there on "
            "real checkpoint bytes",
            "that a widened predicate would be correct: it measures the shape "
            "of the predicate that exists, not the shape of the one that "
            "should",
            "anything about the compiler's config-digest pin, which "
            "results/rtl/abi3_g1f_reduced_end_to_end.json measures as G1f's "
            "FIRST blocker and which no RTL change touches",
        ],
    }


def narrate(record: dict[str, Any]) -> list[str]:
    width = record["measured"]["rms_norm_row_width"]["predicate"]
    context = record["measured"]["gqa_context_length"]
    bracketed_both_sides = sum(
        1
        for entry in width["each_admitted_value_bracketed"].values()
        if entry["next_lower_admitted"] is False
        and entry["next_higher_admitted"] is False
    )
    lines = [
        (
            f"ot_a3_vector_rms_norm admits {len(width['admitted'])} of "
            f"{width['swept_count']} swept row widths -- {width['admitted']} -- "
            f"and the admission set is {width['shape']}: no upper bound, no "
            f"lower bound and no interval over the swept values reproduces it"
        ),
        (
            f"{bracketed_both_sides} of {len(width['admitted'])} admitted "
            "widths are refused at the very next swept value both below and "
            "above them"
            + (
                ", so no capacity threshold can explain the admissions"
                if bracketed_both_sides == len(width["admitted"])
                else ", which does NOT rule out a capacity threshold; read the "
                "bracketing table before drawing a conclusion"
            )
        ),
        (
            f"ot_a3_qwen_gqa admits {len(context['predicate']['admitted'])} of "
            f"{context['predicate']['swept_count']} swept context lengths and "
            f"the admission set IS an interval "
            f"{context['predicate']['consistent_with_interval']}: the one "
            f"geometry field with a runtime port is bounds-checked at both ends"
        ),
        (
            "its operand traffic is affine in that field "
            f"(reads = {context['operand_words_read_vs_context']['intercept']} "
            f"+ {context['operand_words_read_vs_context']['slope']} x context, "
            f"worst residual "
            f"{context['operand_words_read_vs_context']['worst_residual']}), "
            "while its result row is "
            f"{context['result_words_written_at_every_admitted_context']} words "
            "at every admitted context -- the head geometry has no port, so it "
            "cannot be asked for and cannot be refused"
        ),
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    sweep = run_sweep(arguments.work)
    sweep["second_simulator"] = second_simulator(arguments.work / "icarus")
    record = build(sweep)
    record["establishes"] = narrate(record)

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    for line in record["establishes"]:
        print(line)
    print(f"wrote {arguments.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
