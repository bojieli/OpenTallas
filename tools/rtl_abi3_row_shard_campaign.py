#!/usr/bin/env python3
"""The row-shard campaign: an operator's output rows, run in ranges.

What this campaign is for, in one sentence: the integrated shipped-prefix
vehicle executes three of the governed Qwen decode program's seven
``TENSOR.MATMUL`` operators and cannot execute the other four, and a row shard
is the exact decomposition that reaches three of those four.

Three things are measured here and none of them is asserted.

1. **The decomposition is exact.**  Every shard's own words are compared,
   word for word, against the golden for that shard's rows; the write stream
   is checked by ADDRESS as well as by value, so a shard that wrote the right
   values to the wrong rows fails; and the shards are composed by
   ``tools.abi3_row_shard.compose``, which refuses any gap, overlap or extent
   mismatch by construction.  The composition's digest must equal the whole
   operator's golden, which is walked in a different decomposition again.

2. **The composer really refuses.**  Before any composition is believed, this
   campaign takes the real shard outputs and hands the composer a dropped row,
   a duplicated shard and an off-by-one extent, and requires a refusal for
   each.  A composer that could not refuse would make (1) worthless.

3. **Equivalence, whole against sharded.**  One operator the shipped prefix
   already executes is run whole and in eight shards, and the two results must
   be byte-identical -- and both must equal the shipped-prefix vector set's own
   committed digest for that program counter.

The vehicle is ``rtl/test/tb_a3_row_shard.sv`` around the unmodified
``ot_a3_engine_issue_bridge``.  Simulator cycles and host times here are
verification cost.  Nothing in this campaign is a token commit, a layer, or
TPOT evidence.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.abi3_row_shard import (  # noqa: E402
    ShardCompositionError,
    ShardDescriptor,
    compose,
)
from tools import build_abi3_row_shard_vectors as vectors  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_row_shard_campaign.v1"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_row_shard_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/ot_ta_command_decoder.sv",
    "rtl/ot_ta_rope_bf16_sram_engine.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_mac_lane.sv",
    #: ot_a3_engine_array instantiates BOTH lanes and selects between them,
    #: so a source list with only the legacy one cannot elaborate it.
    "rtl/proto/ot_mac_bf16_fp32_pipe.sv",
    "rtl/abi3/ot_a3_mac_lane_pipe.sv",
    "rtl/abi3/ot_a3_selection_argmax.sv",
    "rtl/abi3/ot_a3_dma_index_mover.sv",
    "rtl/abi3/ot_a3_vector_add.sv",
    "rtl/abi3/ot_a3_vector_convert.sv",
    "rtl/abi3/ot_a3_vector_scale.sv",
    "rtl/abi3/ot_a3_vector_hadamard.sv",
    "rtl/abi3/ot_a3_vector_index_score.sv",
    "rtl/abi3/ot_a3_vector_compress_project.sv",
    "rtl/abi3/ot_a3_vector_mhc_post.sv",
    "rtl/abi3/ot_a3_engine_array.sv",
    "rtl/abi3/ot_a3_vector_rms_norm.sv",
    "rtl/abi3/ot_a3_rope_lane_pipe.sv",
    "rtl/abi3/ot_a3_vector_rope.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/abi3/ot_a3_vector_silu_mul.sv",
    "rtl/abi3/ot_a3_selection_token_append.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "rtl/abi3/ot_a3_route_weight_normalize.sv",
    "rtl/abi3/ot_a3_route_window_index.sv",
    "rtl/abi3/ot_a3_route_biased_topk.sv",
    "rtl/abi3/ot_a3_place_table.sv",
    "rtl/abi3/ot_a3_engine_issue_bridge.sv",
    "rtl/test/tb_a3_row_shard.sv",
    "rtl/test/a3_row_shard_dpi.cpp",
)
BOUND_SOURCES = SOURCES + (
    "tools/abi3_row_shard.py",
    "tools/build_abi3_row_shard_vectors.py",
    "tools/rtl_abi3_row_shard_campaign.py",
    "tests/test_abi3_row_shard_composer.py",
    "runtime/reference/formats.py",
    "runtime/reference/tensor_accelerator_bf16.py",
    "runtime/reference/tensor_accelerator_rmsnorm.py",
    "runtime/tensor_accelerator/bf16.py",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
    "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json",
)

# The plan.  ``rows_per_shard`` 4096 is not a round number: it is the largest
# weight-view row count ot_a3_engine_issue_bridge admits, read out of its own
# predicate, so a 4,096-row shard is the widest exact decomposition the design
# will take.  The ``_refusal`` legs are issued deliberately and must fail
# closed; they are the measured reason a class does or does not move.
PLAN = (
    {"name": "pc11_whole", "pc": 11, "role": "equivalence_whole", "pair": "pc11"},
    {"name": "pc11_shards8", "pc": 11, "shards": 8,
     "role": "equivalence_sharded", "pair": "pc11"},
    {"name": "pc14_whole", "pc": 14, "role": "coverage"},
    {"name": "pc17_whole", "pc": 17, "role": "equivalence_whole", "pair": "pc17"},
    {"name": "pc17_shards8", "pc": 17, "shards": 8,
     "role": "equivalence_sharded", "pair": "pc17"},
    {"name": "pc41_whole", "pc": 41, "role": "coverage"},
    #: pc50, pc53 and pc59 are the MLP projections.  They were refusal legs
    #: because the bridge's weight predicate pinned the reduction length to the
    #: embedding width, which no MLP satisfies -- so the whole 12,288-row forms
    #: and the whole of pc59 (which reduces over 12,288) were refused, and the
    #: refusal was the measurement.  With the predicate generalised they are
    #: admitted, so they become what the goldens were always there for: an
    #: equivalence pair each between the whole operator and its 4,096-row
    #: decomposition.
    {"name": "pc50_rows4096", "pc": 50, "rows_per_shard": 4096,
     "role": "equivalence_sharded", "pair": "pc50"},
    {"name": "pc50_whole", "pc": 50, "role": "equivalence_whole", "pair": "pc50"},
    {"name": "pc53_rows4096", "pc": 53, "rows_per_shard": 4096,
     "role": "equivalence_sharded", "pair": "pc53"},
    {"name": "pc53_whole", "pc": 53, "role": "equivalence_whole", "pair": "pc53"},
    {"name": "pc59_whole", "pc": 59, "role": "equivalence_whole", "pair": "pc59"},
    {"name": "pc59_rows4096", "pc": 59, "rows_per_shard": 4096,
     "role": "equivalence_sharded", "pair": "pc59"},
    {"name": "pc69_rows4096", "pc": 69, "rows_per_shard": 4096, "role": "coverage"},
)

SHARD_RE = re.compile(
    r"SHARD index=(?P<index>\d+) pc=(?P<pc>\d+) shipped_operator=(?P<shipped>\d+) "
    r"shard_operator=(?P<operator>\d+) first_row=(?P<first>\d+) "
    r"row_count=(?P<rows>\d+) declared_extent=(?P<extent>\d+) "
    r"fault=(?P<fault>\d+) trap=(?P<trap>\d+) result=(?P<result>\d+) "
    r"work=(?P<work>\d+) writes=(?P<writes>\d+) compared=(?P<compared>\d+) "
    r"verification_cycles=(?P<cycles>\d+)"
)
WINDOW_RE = re.compile(
    r"WINDOW bytes=(?P<bytes>\d+) page_bytes=(?P<page>\d+) "
    r"resident_cap_bytes=(?P<cap>\d+) reads=(?P<reads>\d+) hits=(?P<hits>\d+) "
    r"faults=(?P<faults>\d+) distinct_pages=(?P<distinct>\d+) "
    r"evicted=(?P<evicted>\d+) peak_resident_bytes=(?P<peak>\d+)"
)
VERILATOR_RE = re.compile(
    r"Verilator: cpu (?P<cpu>[0-9.]+) s on (?P<threads>\d+) threads"
)
PASS_RE = re.compile(
    r"PASS a3_row_shard cases=(?P<cases>\d+) positive=(?P<positive>\d+) "
    r"words=(?P<words>\d+) mismatched=(?P<mismatched>\d+) checks=(?P<checks>\d+) "
    r"stream_writes=(?P<stream>\d+)"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scrub(text: str) -> str:
    """No absolute path reaches the artifact.

    An artifact that names the worktree it was produced in is not portable and
    is not comparable across runs; this repository has fixed that defect once
    already, and the same substitution is applied here.
    """

    return (
        str(text)
        .replace(str(ROOT), "<ROOT>")
        .replace(str(Path.home()), "<HOME>")
        .replace(str(Path(os.environ.get("TMPDIR", "/tmp"))), "<TMP>")
    )


def git_identity() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run(["git", "rev-parse", "HEAD"]),
        "worktree_dirty": bool(run(["git", "status", "--porcelain"])),
    }


def tool_identity() -> dict[str, Any]:
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    if not verilator.is_file():
        raise SystemExit(f"pinned Verilator {PINNED_VERILATOR_VERSION} not found")
    version = subprocess.run(
        [str(verilator), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if PINNED_VERILATOR_VERSION not in version:
        raise SystemExit(f"Verilator is {version}, expected the pinned version")
    return {
        "verilator": {
            "path": scrub(str(verilator)),
            "sha256": sha256_file(verilator),
            "version": version,
        }
    }


def elaborate(build_dir: Path) -> dict[str, Any]:
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    build_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(verilator), "--binary", "--timing", "--top-module", "tb_a3_row_shard",
        "--Mdir", str(build_dir), "-o", "sim", "-Wno-fatal",
        "--x-assign", "0", "--x-initial", "0", "-CFLAGS", "-O3",
        *[str(ROOT / name) for name in SOURCES],
    ]
    started = time.time()
    process = subprocess.run(command, capture_output=True, text=True)
    if process.returncode != 0:
        raise SystemExit(
            "row-shard vehicle failed to elaborate:\n" + process.stdout + process.stderr
        )
    return {
        "command": scrub(" ".join(command)),
        "wall_seconds": round(time.time() - started, 3),
        "binary_sha256": sha256_file(build_dir / "sim"),
    }


def read_hex_words(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text().split() if line]


def run_shard(
    binary: Path, shard_dir: Path, timeout: int, reuse: bool = False
) -> dict[str, Any]:
    """Run one shard, or re-read one this campaign already ran.

    ``reuse`` re-derives a shard's record from the ``run.log`` and
    ``stream.txt`` a previous invocation of THIS campaign left in the shard
    directory, without executing the simulator again.  It exists so the
    analysis can be re-derived over an unchanged set of runs; it is recorded
    in the artifact, so nothing produced this way can be read as a fresh
    measurement.  A shard directory with no retained log is a refusal.
    """

    if reuse:
        log_path = shard_dir / "run.log"
        if not log_path.is_file() or not (shard_dir / "stream.txt").is_file():
            raise SystemExit(
                f"{shard_dir}: --reuse-runs needs a retained run.log and "
                "stream.txt, and this shard has none"
            )
        log = log_path.read_text()
        return _parse_shard_log(log, returncode=0, wall_seconds=None, reused=True)

    command = [
        str(binary),
        "+CASES=cases.hex", "+VIEWS=views.hex", "+DESCRIPTORS=descriptors.hex",
        "+INDEX=index.hex", "+SOURCE=source.hex", "+EXPECTED=expected.hex",
        "+PRELOAD=preload.hex", "+STREAM=stream.txt",
    ]
    started = time.time()
    process = subprocess.run(
        command, cwd=shard_dir, capture_output=True, text=True, timeout=timeout
    )
    log = process.stdout + process.stderr
    (shard_dir / "run.log").write_text(log, encoding="utf-8")
    return _parse_shard_log(
        log,
        returncode=process.returncode,
        wall_seconds=round(time.time() - started, 3),
        reused=False,
    )


def _parse_shard_log(
    log: str, *, returncode: int, wall_seconds: float | None, reused: bool
) -> dict[str, Any]:
    # The simulator's own CPU figure.  A process-tree rusage difference is
    # wrong here by construction: shards run concurrently, so the difference
    # taken around one of them collects every sibling that retired inside its
    # window.  Verilator reports its own, and that is the number recorded.
    cpu = VERILATOR_RE.search(log)
    record: dict[str, Any] = {
        "returncode": returncode,
        "wall_seconds": wall_seconds,
        "cpu_seconds": float(cpu.group("cpu")) if cpu else None,
        "simulator_threads": int(cpu.group("threads")) if cpu else None,
        "log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "reused_a_retained_run": reused,
    }
    shard_match = SHARD_RE.search(log)
    window_match = WINDOW_RE.search(log)
    pass_match = PASS_RE.search(log)
    record["observed"] = (
        {key: int(value) for key, value in shard_match.groupdict().items()}
        if shard_match
        else None
    )
    record["window"] = (
        {key: int(value) for key, value in window_match.groupdict().items()}
        if window_match
        else None
    )
    record["marker"] = (
        {key: int(value) for key, value in pass_match.groupdict().items()}
        if pass_match
        else None
    )
    record["passed"] = bool(
        returncode == 0 and shard_match and pass_match and window_match
    )
    return record


def check_write_stream(
    shard_dir: Path, output_base: int, first_row: int, row_count: int
) -> dict[str, Any]:
    """The write stream, checked by address AND value.

    A shard that computed the right numbers and wrote them at the wrong rows
    is exactly what a sharding harness must not admit, so the address of every
    beat is checked against the shard's own declared region, each address is
    required to be written exactly once, and the words are read back OUT OF
    THE STREAM in row order rather than out of the retained image.
    """

    beats = []
    for line in (shard_dir / "stream.txt").read_text().split("\n"):
        if not line.strip():
            continue
        address, data = line.split()
        beats.append((int(address), int(data)))
    problems: list[str] = []
    seen: dict[int, int] = {}
    for address, data in beats:
        if not (output_base <= address < output_base + row_count):
            problems.append(f"write to {address} outside the shard's own region")
            continue
        if address in seen:
            problems.append(f"address {address} written more than once")
        seen[address] = data
    if len(beats) != row_count:
        problems.append(f"{len(beats)} write beats for {row_count} rows")
    words: list[int] = []
    for row in range(row_count):
        address = output_base + row
        if address not in seen:
            problems.append(f"row {first_row + row} was never written")
            words.append(-1)
        else:
            words.append(seen[address])
    return {
        "beats": len(beats),
        "distinct_addresses": len(seen),
        "problems": problems,
        "words": words,
    }


def falsify_the_composer(
    operator: str, declared_extent: int, parts: list[tuple[ShardDescriptor, list[int]]]
) -> list[dict[str, Any]]:
    """Hand the composer real shard output that is not a partition."""

    def attempt(name: str, mutated: list[tuple[ShardDescriptor, list[int]]],
                extent: int) -> dict[str, Any]:
        try:
            compose(extent, mutated)
        except ShardCompositionError as error:
            return {"probe": name, "refused": True, "reason": error.reason}
        return {"probe": name, "refused": False, "reason": None}

    probes: list[dict[str, Any]] = []
    if len(parts) >= 2:
        dropped = [item for index, item in enumerate(parts) if index != len(parts) // 2]
        probes.append(attempt("a_dropped_shard", dropped, declared_extent))
        duplicated = list(parts)
        duplicated[-1] = (parts[0][0], parts[0][1])
        probes.append(attempt("a_duplicated_shard", duplicated, declared_extent))
    short = list(parts)
    descriptor, words = short[0]
    short[0] = (descriptor, words[:-1])
    probes.append(attempt("a_dropped_row_inside_a_shard", short, declared_extent))
    probes.append(
        attempt("an_off_by_one_declared_extent", list(parts), declared_extent + 1)
    )
    probes.append(
        attempt("an_off_by_one_declared_extent_short", list(parts),
                declared_extent - 1)
    )
    return probes


def prepare_leg(
    leg: dict[str, Any], storage_class: str, scratch: Path
) -> dict[str, Any]:
    """Build one leg's vectors and name the shard directories it will run."""

    name = f"{storage_class}_{leg['name']}"
    vector_dir = scratch / "vectors" / name
    manifest = vectors.build(
        storage_class,
        int(leg["pc"]),
        leg.get("shards"),
        leg.get("rows_per_shard"),
        vector_dir,
    )
    return {
        "name": name,
        "leg": leg,
        "storage_class": storage_class,
        "manifest": manifest,
        "shard_dirs": [
            vector_dir / entry["directory"] for entry in manifest["shards"]
        ],
    }


def analyse_leg(
    prepared: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    name = prepared["name"]
    leg = prepared["leg"]
    storage_class = prepared["storage_class"]
    manifest = prepared["manifest"]
    shard_dirs = prepared["shard_dirs"]

    problems: list[str] = []
    compared_words = 0
    mismatched_words = 0
    simulated_cycles = 0
    cpu_seconds = 0.0
    parts: list[tuple[ShardDescriptor, list[int]]] = []
    shard_records: list[dict[str, Any]] = []

    for entry, shard_dir, result in zip(manifest["shards"], shard_dirs, results):
        expected_admitted = bool(entry["admitted_by_the_bridge_predicate"])
        observed = result.get("observed") or {}
        record: dict[str, Any] = {
            "index": entry["index"],
            "first_output_row": entry["first_output_row"],
            "row_count": entry["row_count"],
            "multiply_accumulates": entry["multiply_accumulates"],
            "admitted_by_the_bridge_predicate": expected_admitted,
            "expected_fault": entry["expected_fault"],
            "expected_trap_class": entry["expected_trap_class"],
            "drives_the_shipped_descriptor": entry[
                "drives_the_shipped_descriptor"
            ],
            "golden_sha256": entry["golden_sha256"],
            "run": {
                key: result.get(key)
                for key in ("returncode", "wall_seconds", "cpu_seconds",
                            "simulator_threads", "log_sha256", "passed",
                            "reused_a_retained_run")
            },
            "observed": observed or None,
            "window": result.get("window"),
            "marker": result.get("marker"),
        }
        cpu_seconds += float(result.get("cpu_seconds") or 0.0)
        if not result.get("passed"):
            problems.append(f"{name} shard {entry['index']}: the vehicle did not pass")
            shard_records.append(record)
            continue
        simulated_cycles += int(observed.get("cycles", 0))
        if int(observed.get("fault", -1)) != int(entry["expected_fault"]):
            problems.append(
                f"{name} shard {entry['index']}: fault "
                f"{observed.get('fault')} for expected {entry['expected_fault']}"
            )
        if int(observed.get("trap", -1)) != int(entry["expected_trap_class"]):
            problems.append(
                f"{name} shard {entry['index']}: trap class "
                f"{observed.get('trap')} for expected {entry['expected_trap_class']}"
            )
        marker = result.get("marker") or {}
        record["compared_words"] = int(marker.get("words", 0))
        record["mismatched_words"] = int(marker.get("mismatched", 0))
        compared_words += record["compared_words"]
        mismatched_words += record["mismatched_words"]

        if not expected_admitted:
            stream = (shard_dir / "stream.txt").read_text().strip()
            record["write_stream"] = {
                "beats": 0 if not stream else len(stream.split("\n")),
                "problems": [] if not stream else ["a refused shard wrote"],
            }
            if stream:
                problems.append(f"{name} shard {entry['index']}: a refusal wrote")
            shard_records.append(record)
            continue

        stream = check_write_stream(
            shard_dir,
            int(manifest["geometry"]["bank_output_base"]),
            entry["first_output_row"],
            entry["row_count"],
        )
        record["write_stream"] = {
            "beats": stream["beats"],
            "distinct_addresses": stream["distinct_addresses"],
            "problems": stream["problems"],
        }
        problems.extend(f"{name} shard {entry['index']}: {p}" for p in stream["problems"])
        golden = read_hex_words(shard_dir / "expected.hex")[: entry["row_count"]]
        stream_mismatch = sum(
            1 for produced, want in zip(stream["words"], golden) if produced != want
        )
        record["write_stream"]["mismatched_against_golden"] = stream_mismatch
        if stream_mismatch:
            problems.append(
                f"{name} shard {entry['index']}: {stream_mismatch} stream words "
                "differ from golden"
            )
        parts.append(
            (
                ShardDescriptor(
                    manifest["operator_key"],
                    entry["first_output_row"],
                    entry["row_count"],
                ),
                stream["words"],
            )
        )
        shard_records.append(record)

    leg_record: dict[str, Any] = {
        "name": name,
        "role": leg["role"],
        "leg_pair": leg.get("pair"),
        "storage_class": storage_class,
        "target": manifest["target"],
        "deployment_sha256": manifest["deployment_sha256"],
        "program_counter": manifest["program_counter"],
        "shipped_operator_descriptor_id": manifest["operator_descriptor_id"],
        "operator_key": manifest["operator_key"],
        "numeric_contract_sha256": manifest["numeric_contract_sha256"],
        "declared_output_rows": manifest["declared_output_rows"],
        "reduction": manifest["reduction"],
        "multiply_accumulates": manifest["multiply_accumulates"],
        "whole_operator_admitted_by_the_bridge_predicate": manifest[
            "whole_operator_admitted_by_the_bridge_predicate"
        ],
        "activation": manifest["activation"],
        "weight_source": manifest["weight_source"],
        "differential_rows_recomputed_by_the_scalar_oracle": manifest[
            "differential_rows_recomputed_by_the_scalar_oracle"
        ],
        "whole_operator_golden_sha256": manifest["whole_operator_golden_sha256"],
        "shard_count": len(manifest["shards"]),
        "shards": shard_records,
        "compared_words": compared_words,
        "mismatched_words": mismatched_words,
        "simulated_cycles": simulated_cycles,
        "cpu_seconds": round(cpu_seconds, 3),
        "rewritten_fields": manifest["shards"][0]["rewritten_fields"],
        "drives_the_shipped_descriptor": bool(
            manifest["shards"][0]["drives_the_shipped_descriptor"]
        ),
    }

    if parts:
        try:
            composed = compose(manifest["declared_output_rows"], parts)
        except ShardCompositionError as error:
            leg_record["composition"] = {
                "composed": False,
                "reason": error.reason,
                "detail": error.detail,
            }
            problems.append(f"{name}: composition refused -- {error.reason}")
        else:
            leg_record["composition"] = {
                "composed": True,
                "sha256": composed.sha256,
                "shard_count": composed.shard_count,
                "partition_proof": composed.partition_proof,
                "equals_whole_operator_golden": (
                    composed.sha256 == manifest["whole_operator_golden_sha256"]
                ),
                "rows_covered": composed.declared_extent,
            }
            if composed.sha256 != manifest["whole_operator_golden_sha256"]:
                problems.append(
                    f"{name}: the composition does not equal the whole "
                    "operator's golden"
                )
            leg_record["composer_falsification"] = falsify_the_composer(
                manifest["operator_key"], manifest["declared_output_rows"], parts
            )
            for probe in leg_record["composer_falsification"]:
                if not probe["refused"]:
                    problems.append(
                        f"{name}: the composer admitted {probe['probe']}"
                    )
    else:
        leg_record["composition"] = {
            "composed": False,
            "reason": "every shard of this leg was refused by the design",
            "detail": (
                "the bridge's admitted MATMUL predicate refused this shape; the "
                "refusal is the measurement"
            ),
        }
    leg_record["problems"] = problems
    leg_record["status"] = "pass" if not problems else "fail"
    return leg_record


G1A_ARTIFACT = ROOT / "results/rtl/abi3_g1a_operator_equivalence.json"


def g1a_impact(legs: list[dict[str, Any]]) -> dict[str, Any]:
    """What this campaign does and does not do to rung G1a's coverage.

    G1a's own rule, unchanged and not weakened here: a class is covered when a
    source-current RTL campaign drove EVERY operator descriptor of that class
    positively, as the program issues it.  So only a leg that fetched the
    SHIPPED descriptor -- which is a leg whose shard is the whole operator --
    can move a class under that rule, and a sharded leg cannot, however
    complete its partition is.  Both numbers are reported, and the sharded one
    is never presented as the covered count: rule R13 says a metric reported
    under two models is not evidence in its optimistic form.

    A missing, unreadable or pre-measurement G1a artifact is recorded as such
    and yields no counts, never an assumption.
    """

    try:
        retained = json.loads(G1A_ARTIFACT.read_text())
    except (OSError, ValueError) as error:
        return {
            "readable": False,
            "why": f"{G1A_ARTIFACT.name}: {error}",
            "note": "no before/after count is stated from an artifact that "
                    "could not be read",
        }

    by_class: list[dict[str, Any]] = []
    per_store: dict[str, Any] = {}
    for record in retained.get("records", []):
        storage_class = record["storage_class"]
        store_legs = [leg for leg in legs if leg["storage_class"] == storage_class]
        # Descriptors this campaign issued positively AS THE PROGRAM ISSUES
        # THEM: the whole operator, the shipped descriptor id, no fault, every
        # word compared, nothing mismatched.
        issued_whole = {
            leg["shipped_operator_descriptor_id"]
            for leg in store_legs
            if leg["drives_the_shipped_descriptor"]
            and leg["status"] == "pass"
            and leg["mismatched_words"] == 0
            and leg["compared_words"] > 0
            and all(
                (shard.get("observed") or {}).get("fault") == 0
                for shard in leg["shards"]
            )
        }
        # Descriptors whose every output row ran, in an exact partition whose
        # composition equals the whole operator's golden.  This is a real and
        # checkable statement and it is NOT the statement above.
        rows_all_executed = {
            leg["shipped_operator_descriptor_id"]: {
                "shard_count": leg["shard_count"],
                "declared_output_rows": leg["declared_output_rows"],
                "composition_equals_whole_operator_golden": (
                    leg["composition"].get("equals_whole_operator_golden", False)
                ),
                "compared_words": leg["compared_words"],
                "mismatched_words": leg["mismatched_words"],
                "multiply_accumulates": leg["multiply_accumulates"],
            }
            for leg in store_legs
            if leg["status"] == "pass"
            and leg["composition"].get("equals_whole_operator_golden")
            and leg["mismatched_words"] == 0
        }
        refused = {
            leg["shipped_operator_descriptor_id"]: {
                "leg": leg["name"],
                "trap_class": (leg["shards"][0].get("observed") or {}).get("trap"),
                "declared_output_rows": leg["declared_output_rows"],
                "reduction": leg["reduction"],
            }
            for leg in store_legs
            if leg["role"] == "refusal" and leg["status"] == "pass"
        }

        before_covered = sum(
            1 for item in record["coverage"]["classes"] if item["covered"]
        )
        after_covered = 0
        for item in record["coverage"]["classes"]:
            wanted = set(item["operator_descriptor_ids"])
            covered_after = bool(item["covered"]) or wanted <= issued_whole
            after_covered += 1 if covered_after else 0
            if item["covered"] and not (wanted & (issued_whole | set(rows_all_executed))):
                continue
            by_class.append(
                {
                    "storage_class": storage_class,
                    "mnemonic": item["mnemonic"],
                    "operator_descriptor_ids": item["operator_descriptor_ids"],
                    "program_counters": item["program_counters"],
                    "covered_before": bool(item["covered"]),
                    "covered_after_under_g1a_unchanged_rule": covered_after,
                    "descriptors_this_campaign_issued_whole": sorted(
                        wanted & issued_whole
                    ),
                    "descriptors_whose_every_row_this_campaign_executed": {
                        str(key): value
                        for key, value in rows_all_executed.items()
                        if key in wanted
                    },
                    "descriptors_this_campaign_measured_refused": {
                        str(key): value
                        for key, value in refused.items()
                        if key in wanted
                    },
                    "still_missing": sorted(
                        wanted - issued_whole - set(rows_all_executed)
                    ),
                }
            )
        per_store[storage_class] = {
            "issued_class_count": record["coverage"]["issued_class_count"],
            "covered_class_count_before": before_covered,
            "covered_class_count_after_under_g1a_unchanged_rule": after_covered,
            "shipped_operator_descriptors_issued_whole": sorted(issued_whole),
            "shipped_operator_descriptors_with_every_row_executed": sorted(
                rows_all_executed
            ),
            "shipped_operator_descriptors_refused": {
                str(key): value for key, value in refused.items()
            },
        }

    return {
        "readable": True,
        "artifact": str(G1A_ARTIFACT.relative_to(ROOT)),
        "artifact_sha256": hashlib.sha256(G1A_ARTIFACT.read_bytes()).hexdigest(),
        "rule": (
            "G1a's own rule is unchanged: a class is covered when every one of "
            "its operator descriptors was driven positively as the program "
            "issues it.  A row-sharded leg rewrites the weight view's row count "
            "and so does not issue that descriptor; it is reported separately "
            "and is never counted as coverage."
        ),
        "per_storage_class": per_store,
        "classes": by_class,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="run only the named legs (repeatable); default is the whole plan",
    )
    parser.add_argument(
        "--reuse-runs",
        action="store_true",
        help=(
            "re-derive the artifact from the run logs and write streams a "
            "previous invocation of this campaign left in the scratch "
            "directory, without executing the simulator again.  Recorded in "
            "the artifact."
        ),
    )
    parser.add_argument(
        "--storage-class", action="append", default=None,
        choices=sorted(vectors.STORAGE_CLASSES),
    )
    args = parser.parse_args(argv)

    scratch = args.scratch
    scratch.mkdir(parents=True, exist_ok=True)
    tools = tool_identity()
    elaboration = elaborate(scratch / "obj_row_shard")
    binary = scratch / "obj_row_shard" / "sim"

    storage_classes = args.storage_class or sorted(vectors.STORAGE_CLASSES)
    plan = [leg for leg in PLAN if args.only is None or leg["name"] in set(args.only)]
    if not plan:
        raise SystemExit("the selection matched no leg of the plan")

    started = time.time()
    # Every shard of every leg goes into ONE pool.  Legs are not equal in
    # size -- one is 38 shards and another is 1 -- so running them leg by leg
    # would leave most of the cores idle for most of the campaign.
    prepared = [
        prepare_leg(leg, storage_class, scratch)
        for storage_class in storage_classes
        for leg in plan
    ]
    queue = [
        (item, index, shard_dir)
        for item in prepared
        for index, shard_dir in enumerate(item["shard_dirs"])
    ]
    # Longest first, so the tail of the campaign is not one 4,096-row shard
    # running alone behind eleven idle cores.
    queue.sort(
        key=lambda entry: entry[0]["manifest"]["shards"][entry[1]][
            "multiply_accumulates"
        ],
        reverse=True,
    )
    results: dict[tuple[str, int], dict[str, Any]] = {}
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(
                run_shard, binary, shard_dir, args.timeout, args.reuse_runs
            ): (item["name"], index)
            for item, index, shard_dir in queue
        }
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            results[key] = future.result()
            done += 1
            print(
                f"[{done}/{len(queue)}] {key[0]} shard {key[1]}: "
                f"cycles={(results[key].get('observed') or {}).get('cycles')} "
                f"cpu={results[key].get('cpu_seconds')}",
                flush=True,
            )

    legs: list[dict[str, Any]] = []
    for item in prepared:
        record = analyse_leg(
            item,
            [
                results[(item["name"], index)]
                for index in range(len(item["shard_dirs"]))
            ],
        )
        legs.append(record)
        print(
            f"{record['name']}: {record['status']} "
            f"shards={record['shard_count']} "
            f"words={record['compared_words']} "
            f"mismatched={record['mismatched_words']} "
            f"cycles={record['simulated_cycles']}",
            flush=True,
        )

    # The equivalence statement, stated as its own field rather than left for
    # a reader to infer from two legs.
    equivalence: list[dict[str, Any]] = []
    pairs = sorted({leg.get("pair") for leg in plan if leg.get("pair")})
    for storage_class in storage_classes:
      for pair in pairs:
        whole = next(
            (
                leg for leg in legs
                if leg["storage_class"] == storage_class
                and leg["role"] == "equivalence_whole"
                and leg["leg_pair"] == pair
            ),
            None,
        )
        sharded = next(
            (
                leg for leg in legs
                if leg["storage_class"] == storage_class
                and leg["role"] == "equivalence_sharded"
                and leg["leg_pair"] == pair
            ),
            None,
        )
        if whole is None or sharded is None:
            continue
        whole_sha = (whole.get("composition") or {}).get("sha256")
        shard_sha = (sharded.get("composition") or {}).get("sha256")
        equivalence.append(
            {
                "storage_class": storage_class,
                "pair": pair,
                "program_counter": whole["program_counter"],
                "operator_key": whole["operator_key"],
                "declared_output_rows": whole["declared_output_rows"],
                "whole_run_shard_count": whole["shard_count"],
                "sharded_run_shard_count": sharded["shard_count"],
                "whole_run_sha256": whole_sha,
                "sharded_run_sha256": shard_sha,
                "byte_identical": bool(
                    whole_sha is not None and whole_sha == shard_sha
                ),
                "both_equal_the_golden": bool(
                    whole_sha == whole["whole_operator_golden_sha256"]
                    and shard_sha == sharded["whole_operator_golden_sha256"]
                ),
            }
        )

    problems = [problem for leg in legs for problem in leg["problems"]]
    for item in equivalence:
        if not item["byte_identical"]:
            problems.append(
                f"{item['storage_class']} {item['pair']}: the whole run and "
                "the sharded run are not byte-identical"
            )
        if not item["both_equal_the_golden"]:
            problems.append(
                f"{item['storage_class']} {item['pair']}: a run does not "
                "equal the golden"
            )

    artifact = {
        "schema": SCHEMA,
        "scope": (
            "one TENSOR.MATMUL operator per leg, run over a contiguous range "
            "of its output rows on the unmodified ot_a3_engine_issue_bridge, "
            "then composed.  Verification cost only: not a token, not a layer, "
            "not a rate."
        ),
        "evidence_class": "rtl_simulation",
        "simulators": ["verilator"],
        "simulator_note": (
            "one simulator, for the reason the integrated shipped-prefix "
            "vehicle has one: the weight window is DPI-C, which Icarus 11 "
            "does not serve here"
        ),
        "tools": tools,
        "git": git_identity(),
        "elaboration": elaboration,
        "runs_reused_from_retained_logs": bool(args.reuse_runs),
        "runs_reused_note": (
            "the simulator was not executed in this invocation; every shard's "
            "record was re-derived from the run.log and stream.txt this same "
            "campaign wrote, each bound here by its own log_sha256"
            if args.reuse_runs
            else "every shard was executed in this invocation"
        ),
        "bound_sources": {
            name: sha256_file(ROOT / name) for name in sorted(BOUND_SOURCES)
        },
        "plan": [dict(leg) for leg in plan],
        "storage_classes": storage_classes,
        "legs": legs,
        "equivalence": equivalence,
        "g1a_impact": g1a_impact(legs),
        "totals": {
            "legs": len(legs),
            "shards": sum(leg["shard_count"] for leg in legs),
            "compared_words": sum(leg["compared_words"] for leg in legs),
            "mismatched_words": sum(leg["mismatched_words"] for leg in legs),
            "simulated_cycles": sum(leg["simulated_cycles"] for leg in legs),
            "simulator_cpu_seconds": round(
                sum(leg["cpu_seconds"] for leg in legs), 3
            ),
            "wall_seconds_of_this_invocation": round(time.time() - started, 3),
            "wall_seconds_note": (
                "the wall figure is this invocation's own.  Under --reuse-runs "
                "it is the re-analysis pass and not the simulation, which is "
                "why the CPU figure beside it -- each simulator's own, summed "
                "-- is the cost of the campaign and the wall figure is not"
            ),
            "multiply_accumulates_executed": sum(
                shard["multiply_accumulates"]
                for leg in legs
                for shard in leg["shards"]
                if shard["admitted_by_the_bridge_predicate"]
                and (shard.get("observed") or {}).get("fault") == 0
            ),
        },
        "problems": problems,
        "status": "pass" if not problems else "fail",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"row-shard campaign: {artifact['status']} "
        f"legs={artifact['totals']['legs']} "
        f"shards={artifact['totals']['shards']} "
        f"words={artifact['totals']['compared_words']} "
        f"mismatched={artifact['totals']['mismatched_words']} "
        f"macs={artifact['totals']['multiply_accumulates_executed']} "
        f"-> {args.output}"
    )
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
