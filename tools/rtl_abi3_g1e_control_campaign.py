#!/usr/bin/env python3
"""Rung G1e: the governed workload's whole control path, measured.

Builds the golden control vectors from ``runtime.sim.device.Device`` (through
``tools/build_abi3_g1e_control_vectors.py``, which reads no RTL), elaborates
``rtl/test/a3_shipped_prefix_top.sv`` with ``ENABLE_RESULT_INJECTION=1``, runs
every pass of ``TA-QW-EOS-1`` through the design's own control plane with the
engine results supplied at the engine result boundary, and compares the RTL
issue trace to the golden's element for element -- on each of ROM and HBM.

Three things this file refuses to take on trust:

**That the injection reaches only the engine boundary.**  ``audit_injection``
re-derives it from ``rtl/test/a3_shipped_prefix_top.sv`` itself: it finds every
statement in which an injected input appears, follows the signals those
statements drive, and requires the transitive fanout to land inside a declared
sink set -- the engine port's completion handshake and the result memory's
write port.  A signal outside that set is a FAIL with the line that reached it.
The audit is falsifiable by construction: ``--audit-self-test`` runs it against
a copy of the source with one extra edge spliced in and requires it to refuse.

**That the run measured what it claims.**  Every record carries the provenance
spine the ladder requires -- a named simulator, positive simulated cycles, an
RTL evidence class and a clean worktree -- plus the checker's own zero-launch,
zero-engine-work and zero-weight-read observations, which are what say the
control plane and not the datapath is what ran.

**That the explanation of a red field is true.**  The rung measures three
passes against the number G1e's specification names, and until now the gap was
explained in prose.  ``tools/build_abi3_g1e_pass_decomposition.py`` executes
the governed workload on the reference model under several submission
sequences and reports which reproduce the oracle's gold, so the pass count is
bounded by an experiment rather than by an argument.  The gate's own number is
read out of ``configs/gates/redesign_gates.json``; nothing here types it and
nothing here edits it.

**That an absent measurement is not a pass.**  A field this vehicle cannot
measure is written with the value it actually has and the reason it has it.
G1e asks for two things this deployment's control plane never does -- raise
OFFICIAL_EOS and refuse a post-EOS instruction -- because in the promoted
lowering the EOS decision is an engine result and the post-EOS refusal is a
host session-state refusal, taken before an instruction is fetched.  Both are
reported false with the measurement that shows where they actually live.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import Major, Selection  # noqa: E402
from runtime.abi3.records import EosReason  # noqa: E402
from tools.build_abi3_g1e_pass_decomposition import (  # noqa: E402
    gate_required_passes,
)
from tools.rtl_abi3_shipped_prefix_campaign import (  # noqa: E402
    PINNED_VERILATOR_VERSION,
    RTL_SOURCES,
    TOOLS_ROOT,
    canonical,
    git_identity,
    require_versions,
    resolve,
    sha256_file,
    tool_record,
)

SCHEMA = "opentallas.rtl.abi3_g1e_control_end_to_end.v1"
ARTIFACT = ROOT / "results/rtl/abi3_g1e_control_end_to_end.json"
TOP = "rtl/test/a3_shipped_prefix_top.sv"
HARNESS = "rtl/test/a3_g1e_control_harness.cpp"
BUILDER = "tools/build_abi3_g1e_control_vectors.py"
DECOMPOSITION = "tools/build_abi3_g1e_pass_decomposition.py"
WORKLOAD_ID = "TA-QW-EOS-1"

TEST_SOURCES = (
    "rtl/test/a3_engine_completion_adapter.sv",
    TOP,
    HARNESS,
)
TOOL_SOURCES = (
    BUILDER,
    DECOMPOSITION,
    "tools/build_abi3_deployment_rtl_vectors.py",
    "tools/rtl_abi3_g1e_control_campaign.py",
)
CONTRACT_SOURCES = (
    "runtime/sim/device.py",
    "runtime/sim/memory.py",
    "runtime/driver.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/records.py",
    "runtime/abi3/verifier.py",
    "docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md",
)

# The vehicle's elaboration.  RESULT/SOURCE/INDEX words are the vehicle's
# operand banks; under injection no engine reads them, and the derivation in
# the vector builder shows the control plane reads a result word only through
# a PREDICATE.  They are recorded in the artifact so the geometry a record was
# taken at is never in doubt.
PARAMETERS = {
    "ENABLE_RESULT_INJECTION": 1,
    "MATMUL_WEIGHT_BYTES": 0,
    "RESULT_WORDS": 4096,
    "SOURCE_WORDS": 256,
    "INDEX_WORDS": 64,
}

STORES = ("rom", "hbm")


# ---------------------------------------------------------------------------
# The injection-site audit
# ---------------------------------------------------------------------------
# The three inputs that carry a model value into the design, and the only two
# places the top is permitted to take them.  The sink names are the top's own
# signals; the audit follows the fanout and refuses anything else.
INJECTED_INPUTS = (
    "inj_result_valid",
    "inj_result_fault",
    "inj_result_trap_class",
    "inj_write_en",
    "inj_write_addr",
    "inj_write_data",
)
MEMORY = "result_mem"
# The engine port's completion handshake: the boundary itself.  A real
# engine's ready/fault/trap_class drives exactly these signals.
COMPLETION_HANDSHAKE = {
    "injected_ready",
    "engine_ready",
    "engine_fault",
    "engine_trap_class",
    "issue_ready",
    "issue_fault",
    "issue_trap_class",
}
# The result memory's write port, and the memory it writes.
RESULT_MEMORY_WRITE_PORT = {"res_we", "res_addr", "res_data", MEMORY}
# Signals the completion legitimately reaches that are observation only: the
# checker's response port, the injected-completion counters, the write and
# fault counters, and the exact-multicast adapter's sequencing, which this
# vehicle elaborates with ENABLE_EXACT_MULTICAST=0 so `exact_multicast_issue`
# is constantly false and the adapter never starts (the checker measures
# multicast_launch_count == 0 per pass).  None of them is an input to fetch,
# decode, view resolution, predicates, the loop stack, the wait set or issue,
# and the instance-port scan below is what establishes that rather than this
# list.
OBSERVATION_ONLY = {
    "response_valid",
    "response_fault",
    "response_trap_class",
    "inj_completion_count",
    "inj_last_response_index",
    "last_response_index",
    "output_write_count",
    "writes_after_fault",
    "fault_seen",
}
ALLOWED_SINKS = COMPLETION_HANDSHAKE | RESULT_MEMORY_WRITE_PORT | OBSERVATION_ONLY
MULTICAST_PREFIX = "multicast_"
# The only design inputs an injected value is permitted to reach through a
# module instantiation: the completion adapter's engine-side completion.
ALLOWED_INSTANCE_PORTS = {
    "eng_issue_ready",
    "eng_issue_fault",
    "eng_issue_trap_class",
}
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _statements(source: str) -> list[tuple[int, str]]:
    """(line number, statement text), comments removed.

    A crude but total split on ';' is deliberate: the audit must not depend on
    a parser that could silently skip a construct it did not understand.  Any
    statement it cannot attribute is reported, not ignored.
    """
    out: list[tuple[int, str]] = []
    line_number = 1
    current: list[str] = []
    start = 1
    in_block = False
    i = 0
    while i < len(source):
        char = source[i]
        if source.startswith("/*", i):
            in_block = True
            i += 2
            continue
        if in_block:
            if source.startswith("*/", i):
                in_block = False
                i += 2
                continue
            if char == "\n":
                line_number += 1
            i += 1
            continue
        if source.startswith("//", i):
            while i < len(source) and source[i] != "\n":
                i += 1
            continue
        if char == "\n":
            line_number += 1
            current.append(" ")
            i += 1
            continue
        if char == ";":
            text = "".join(current).strip()
            if text:
                out.append((start, text))
            current = []
            start = line_number
            i += 1
            continue
        if not current:
            start = line_number
        current.append(char)
        i += 1
    text = "".join(current).strip()
    if text:
        out.append((start, text))
    return out


VERILOG_KEYWORDS = frozenset(
    """
    assign wire reg logic integer localparam parameter input output inout
    if else begin end always posedge negedge for while case casez casex
    endcase default module endmodule genvar generate endgenerate initial
    signed unsigned int longint bit byte real time automatic static
    """.split()
)


def _driven_names(statement: str) -> list[str]:
    """The signal a statement drives.

    The left-hand side is everything before the statement's first assignment
    operator; bit selects and ranges are removed, declaration keywords are
    dropped, and what remains is the target.  ``result_mem[res_addr] <= data``
    therefore drives ``result_mem`` and not ``res_addr``, and
    ``wire [32:0] x = ...`` drives ``x``.
    """
    text = statement.strip()
    cut = None
    for index in range(len(text) - 1):
        pair = text[index : index + 2]
        if pair == "<=":
            cut = index
            break
        if text[index] == "=" and pair != "==" and (
            index == 0 or text[index - 1] not in "=!<>"
        ):
            cut = index
            break
    if cut is None:
        return []
    left = re.sub(r"\[[^\]]*\]", " ", text[:cut])
    names = [
        name for name in IDENTIFIER.findall(left) if name not in VERILOG_KEYWORDS
    ]
    return names[-1:]


def _closure(
    statements: list[tuple[int, str]], seeds: set[str], stop_at: set[str]
) -> tuple[set[str], list[dict[str, Any]]]:
    """Transitive fanout of ``seeds``, not propagating out of ``stop_at``."""
    tainted = set(seeds)
    edges: list[dict[str, Any]] = []
    changed = True
    rounds = 0
    while changed and rounds < 64:
        changed = False
        rounds += 1
        for line, statement in statements:
            if "module " in statement:
                continue  # the port list and parameter defaults drive nothing
            names = set(IDENTIFIER.findall(statement))
            source = names & tainted
            if not source or source <= stop_at:
                continue
            driven = _driven_names(statement)
            if not driven or driven[0] in tainted:
                continue
            tainted.add(driven[0])
            edges.append(
                {
                    "line": line,
                    "drives": driven[0],
                    "from": sorted(source),
                    "statement": " ".join(statement.split())[-180:],
                }
            )
            changed = True
    return tainted, edges


def _instance_ports(source_text: str, tainted: set[str]) -> list[dict[str, Any]]:
    """Every module-instance port connection an injected value reaches.

    The signal-level closure above stops at module boundaries, so this is the
    half that says which DESIGN INPUTS the injection can drive.  A completion
    that reaches only the completion adapter's engine-side completion is the
    engine result boundary; a completion that reached, say, the sequencer's
    start or the symbol file would not be.
    """
    out: list[dict[str, Any]] = []
    line = 1
    for match in re.finditer(r"\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)", source_text):
        line += source_text.count("\n", 0, match.start()) if False else 0
        expression = match.group(2)
        names = set(IDENTIFIER.findall(expression))
        if not (names & tainted):
            continue
        out.append(
            {
                "line": source_text.count("\n", 0, match.start()) + 1,
                "port": match.group(1),
                "expression": " ".join(expression.split()),
                "from": sorted(names & tainted),
            }
        )
    return out


def audit_injection(source_text: str) -> dict[str, Any]:
    """Where an injected value can reach in the top, derived from the source.

    Two tiers, because they are two different claims.  The DIRECT tier is the
    fanout of the injected inputs with the result memory treated as terminal:
    it must land inside the engine port's completion handshake and the result
    memory's write port, and nothing else.  The THROUGH-MEMORY tier then asks
    what reads that memory, and reports it rather than hiding it: the engine
    operand ports (which no engine reads here, because none is issued to) and
    the sequencer's predicate-read window, which is the one place in either
    machine where a word in memory decides control flow.  Whether that window
    can carry anything is not argued here -- the vector builder derives the
    set of words a PREDICATE names, and this program names none.
    """
    statements = _statements(source_text)
    direct, edges = _closure(statements, set(INJECTED_INPUTS), {MEMORY})
    reached = sorted(direct - set(INJECTED_INPUTS))
    outside = sorted(
        name
        for name in reached
        if name not in ALLOWED_SINKS and not name.startswith(MULTICAST_PREFIX)
    )
    ports = _instance_ports(source_text, direct)
    for entry in ports:
        if entry["port"] in ALLOWED_INSTANCE_PORTS:
            entry["class"] = "engine_completion_boundary"
        elif all(name.startswith(MULTICAST_PREFIX) for name in entry["from"]):
            # The exact-multicast adapter.  This vehicle elaborates it with
            # ENABLE_EXACT_MULTICAST=0, so `exact_multicast_issue` is
            # constantly false, the adapter is never started, and the checker
            # measures multicast_launch_count == 0 on every pass.  It is
            # classified, not excused: were the parameter ever 1 here, this
            # entry would have to move to the allowed set or the vehicle would
            # have to change.
            entry["class"] = "inert_exact_multicast_adapter"
        else:
            entry["class"] = "outside"
    outside_ports = sorted(
        entry["port"] for entry in ports if entry["class"] == "outside"
    )
    through, memory_edges = _closure(statements, {MEMORY}, set())
    readers = sorted(through - {MEMORY})
    return {
        "injected_inputs": list(INJECTED_INPUTS),
        "allowed_sinks": sorted(ALLOWED_SINKS),
        "reached": reached,
        "outside_allowed_sinks": outside,
        "edges": edges,
        "instance_ports_reached": ports,
        "instance_ports_outside_allowed": outside_ports,
        "instance_port_classes": sorted(
            {entry["class"] for entry in ports}
        ),
        "exact_multicast_elaborated": PARAMETERS.get("ENABLE_EXACT_MULTICAST", 0),
        "allowed_instance_ports": sorted(ALLOWED_INSTANCE_PORTS),
        "clean": not outside and not outside_ports,
        "through_memory": {
            "memory": MEMORY,
            "readers": readers,
            "edges": memory_edges,
            "control_path_window": "predicate_read_value",
            "note": (
                "the only reader of the result memory that any control "
                "decision depends on is the sequencer's predicate-read port; "
                "the engine operand ports are read by engines, and under "
                "result injection no engine is issued to"
            ),
        },
        "method": (
            "every statement of the top that mentions a tainted signal is "
            "found, the signal it drives is added, and the closure is taken; "
            "a tainted signal outside the declared sink set refuses the audit"
        ),
    }


def audit_self_test(source_text: str) -> dict[str, Any]:
    """The audit must refuse a source in which injection reaches further.

    An audit that cannot fail is not an audit.  One extra assignment is
    spliced into a copy of the top -- an injected value driving a signal that
    is plainly in the control path -- and the audit is required to catch it.
    """
    spliced = source_text.replace(
        "    assign inj_issue_family = issue_family;",
        "    assign inj_issue_family = issue_family;\n"
        "    wire audit_probe_pc = inj_result_valid;",
        1,
    )
    if spliced == source_text:
        return {
            "ran": False,
            "refused_the_spliced_edge": False,
            "why": "the splice anchor is no longer in the top; the self test "
            "did not run and the audit above is therefore unverified",
        }
    result = audit_injection(spliced)
    return {
        "ran": True,
        "refused_the_spliced_edge": bool(
            "audit_probe_pc" in result["outside_allowed_sinks"]
        ),
        "spliced_edge": "wire audit_probe_pc = inj_result_valid;",
        "outside_allowed_sinks_when_spliced": result["outside_allowed_sinks"],
    }


# ---------------------------------------------------------------------------
# Build and run
# ---------------------------------------------------------------------------
MARKER = re.compile(
    r"PASS: ABI3 G1e control end to end passes=(\d+) issues=(\d+) views=(\d+) "
    r"elements=(\d+) injected=(\d+) checks=(\d+)"
)
TRACE_LINE = re.compile(
    r"TRACE compared=(\d+) equal=(\d+) divergence_index=(-?\d+) "
    r"queue_compared=(\d+) queue_equal=(\d+) queue_divergence_index=(-?\d+)"
)
INJECT_LINE = re.compile(
    r"INJECTION results=(\d+) words=(\d+) engine_launches=(\d+) "
    r"engine_work=(\d+) weight_halfwords=(\d+)"
)
COST_LINE = re.compile(
    r"COST passes=(\d+) cycles=(\d+) seconds=([0-9.]+) host_writes=(\d+)"
)
CENSUS_LINE = re.compile(r"CENSUS classes=(\d+) instances=(\d+)")
CENSUS_ROW = re.compile(r"CENSUS-ROW (\d+) (\d+) (\d+) (\d+)")
EOS_LINE = re.compile(
    r"EOS selected_token=(\d+) selected_tie_multiplicity=(\d+) "
    r"selected_eos_reason=(\d+) engine_launches=(\d+)"
)
POSTEOS_LINE = re.compile(
    r"POSTEOS ran=(\d+) admitted=(\d+) trapped=(\d+) trap_class=(\d+) "
    r"issues=(\d+) cycles=(\d+)"
)
PASS_RECORD = re.compile(
    r"PASS-RECORD index=(\d+) entrypoint=(\d+) generation=(\d+) context=(\d+) "
    r"issues=(\d+) views=(\d+) fetched=(\d+) retired=(\d+) loops=(\d+) "
    r"waits=(\d+) cycles=(\d+)"
)


def build_vectors(store: str, out: Path, checkpoint: Path | None) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / BUILDER),
        "--store",
        store,
        "--output",
        str(out),
    ]
    if checkpoint is not None:
        command += ["--checkpoint", str(checkpoint)]
    started = time.perf_counter()
    result = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    seconds = time.perf_counter() - started
    if result.returncode != 0:
        raise SystemExit(
            f"golden vector build for {store} failed:\n{result.stdout[-4000:]}"
        )
    manifest = json.loads((out / "g1e_vectors.json").read_text(encoding="utf-8"))
    manifest["build_seconds"] = round(seconds, 2)
    manifest["build_marker"] = result.stdout.strip().splitlines()[-1]
    return manifest


def derive_official_eos_raised(
    eos_observation: dict[str, Any], engine_launches: int
) -> bool:
    """Did the RTL raise OFFICIAL_EOS?  Two observations, both from the run.

    The EOS reason alone is not enough and never was: under result injection
    the selection engines are not issued to, so a reason appearing on that
    output could only be a model value routed through the top.  Requiring a
    real engine launch beside it is what makes the field impossible to set by
    wiring an output up -- the failure this ladder found in its own G1a tool,
    where a gate field was decided by the presence of a port name.
    """
    reason = eos_observation.get("selected_eos_reason")
    return bool(
        reason is not None
        and int(reason) == int(EosReason.OFFICIAL_EOS)
        and int(engine_launches) > 0
    )


def derive_post_eos_refused(probe: dict[str, Any]) -> bool:
    """Did the RTL refuse the instruction after the official EOS?

    A probe that did not run refuses nothing, and a pass the design completed
    without trapping was admitted, not refused.  Both readings come off the
    DUT's own done / complete / trapped outputs.
    """
    if not bool(probe.get("ran")):
        return False
    return bool(probe.get("rtl_trapped")) or not bool(
        probe.get("rtl_admitted_the_pass")
    )


def eos_field_self_test() -> dict[str, Any]:
    """Both derived fields must be falsifiable in both directions.

    A field that cannot become true is not a measurement, and a field that
    cannot become false is not one either.  This exercises each derivation
    against fabricated observations and requires the value to follow them, so
    a later change that nails either field to a constant fails here rather
    than in the artifact.
    """
    official = {
        "false_because_no_engine_ran": derive_official_eos_raised(
            {"selected_eos_reason": int(EosReason.OFFICIAL_EOS)}, 0
        ),
        "false_because_the_reason_is_not_official": derive_official_eos_raised(
            {"selected_eos_reason": int(EosReason.NONE)}, 7
        ),
        "true_when_a_real_engine_raised_it": derive_official_eos_raised(
            {"selected_eos_reason": int(EosReason.OFFICIAL_EOS)}, 7
        ),
    }
    refused = {
        "false_when_the_probe_did_not_run": derive_post_eos_refused(
            {"ran": False, "rtl_admitted_the_pass": False, "rtl_trapped": True}
        ),
        "false_when_the_design_completed_the_pass": derive_post_eos_refused(
            {"ran": True, "rtl_admitted_the_pass": True, "rtl_trapped": False}
        ),
        "true_when_the_design_trapped_it": derive_post_eos_refused(
            {"ran": True, "rtl_admitted_the_pass": False, "rtl_trapped": True}
        ),
        "true_when_the_design_did_not_complete_it": derive_post_eos_refused(
            {"ran": True, "rtl_admitted_the_pass": False, "rtl_trapped": False}
        ),
    }
    passed = (
        official == {
            "false_because_no_engine_ran": False,
            "false_because_the_reason_is_not_official": False,
            "true_when_a_real_engine_raised_it": True,
        }
        and refused == {
            "false_when_the_probe_did_not_run": False,
            "false_when_the_design_completed_the_pass": False,
            "true_when_the_design_trapped_it": True,
            "true_when_the_design_did_not_complete_it": True,
        }
    )
    return {
        "ran": True,
        "passed": passed,
        "official_eos_raised": official,
        "post_eos_refused": refused,
        "why": (
            "each derived EOS field is exercised against fabricated "
            "observations in both directions; a field pinned to a constant "
            "fails this and the campaign refuses to publish"
        ),
    }


def run_decomposition(store: str, out: Path, checkpoint: Path | None) -> dict[str, Any]:
    """Measure which host decompositions of this workload the design admits.

    G1e's pass count is the one field on this rung whose red value used to be
    explained rather than measured.  ``tools/build_abi3_g1e_pass_decomposition``
    runs the governed workload on the reference model under several submission
    sequences and reports which of them reproduce the oracle's gold; the
    maximum pass count over those is what the rung can honestly report against
    the gate's number.  A study that will not run is a FAIL of this campaign,
    not a missing section: an unmeasured explanation is exactly what it
    replaces.
    """
    command = [
        sys.executable,
        str(ROOT / DECOMPOSITION),
        "--store",
        store,
        "--output",
        str(out),
    ]
    if checkpoint is not None:
        command += ["--checkpoint", str(checkpoint)]
    started = time.perf_counter()
    result = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    seconds = time.perf_counter() - started
    if result.returncode != 0:
        raise SystemExit(
            f"the pass-decomposition study for {store} failed:\n"
            f"{result.stdout[-4000:]}"
        )
    study = json.loads(out.read_text(encoding="utf-8"))
    study["campaign_wall_seconds"] = round(seconds, 2)
    study["marker"] = result.stdout.strip().splitlines()[-1]
    return study


def run_store(
    store: str,
    manifest: dict[str, Any],
    vectors: Path,
    build: Path,
    verilator: Path,
) -> dict[str, Any]:
    build.mkdir(parents=True, exist_ok=True)
    for name in sorted(manifest["emitted"]):
        shutil.copy2(vectors / name, build / name)
    # The top $readmemh's its operand banks at time zero.  Under injection no
    # engine reads them; they are supplied at the elaborated size so the DUT
    # never reads an uninitialised word.
    (build / "p3_index.hex").write_text(
        "\n".join(["00000000"] * PARAMETERS["INDEX_WORDS"]) + "\n", encoding="ascii"
    )
    (build / "p3_source.hex").write_text(
        "\n".join(["00000000"] * PARAMETERS["SOURCE_WORDS"]) + "\n", encoding="ascii"
    )

    compile_command = [
        str(verilator),
        "--cc",
        "--exe",
        "--build",
        "-Wall",
        "-Wno-fatal",
        "-Wno-DECLFILENAME",
        "--top-module",
        "ot_a3_shipped_prefix_top",
        *[f"-G{name}={value}" for name, value in sorted(PARAMETERS.items())],
        "--Mdir",
        "obj_g1e",
        *[str(ROOT / path) for path in RTL_SOURCES],
        *[str(ROOT / path) for path in TEST_SOURCES],
        "-CFLAGS",
        "-std=c++17",
    ]
    started = time.perf_counter()
    compile_result = subprocess.run(
        compile_command, cwd=build, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    compile_seconds = time.perf_counter() - started
    if compile_result.returncode != 0:
        return {
            "storage_class": store,
            "status": "fail",
            "why": "elaboration failed",
            "compile_log_tail": canonical(compile_result.stdout[-4000:], build),
        }

    started = time.perf_counter()
    run_result = subprocess.run(
        ["./obj_g1e/Vot_a3_shipped_prefix_top"],
        cwd=build,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env={**os.environ, "OT_A3_G1E_DIR": str(build)},
    )
    run_seconds = time.perf_counter() - started
    stdout = run_result.stdout

    marker = MARKER.search(stdout)
    trace = TRACE_LINE.search(stdout)
    injection = INJECT_LINE.search(stdout)
    cost = COST_LINE.search(stdout)
    posteos = POSTEOS_LINE.search(stdout)
    eos = EOS_LINE.search(stdout)
    census = CENSUS_LINE.search(stdout)
    census_rows = [
        {
            "family": int(m.group(1)),
            "sub": int(m.group(2)),
            "descriptor_id": int(m.group(3)),
            "instances": int(m.group(4)),
        }
        for m in CENSUS_ROW.finditer(stdout)
    ]
    passes = [
        {
            "index": int(m.group(1)),
            "entrypoint_id": int(m.group(2)),
            "generation_index": int(m.group(3)),
            "context_length": int(m.group(4)),
            "issues": int(m.group(5)),
            "views": int(m.group(6)),
            "instructions_fetched": int(m.group(7)),
            "instructions_retired": int(m.group(8)),
            "loop_iterations": int(m.group(9)),
            "wait_events": int(m.group(10)),
            "simulated_cycles": int(m.group(11)),
        }
        for m in PASS_RECORD.finditer(stdout)
    ]
    return {
        "storage_class": store,
        "returncode": run_result.returncode,
        "marker_present": marker is not None,
        "marker": marker.group(0) if marker else None,
        "checks": int(marker.group(6)) if marker else 0,
        "trace": {
            "compared_elements": int(trace.group(1)) if trace else 0,
            "equal": bool(trace and trace.group(2) == "1"),
            "divergence_index": int(trace.group(3)) if trace else None,
            "queue_compared_elements": int(trace.group(4)) if trace else 0,
            "queue_equal": bool(trace and trace.group(5) == "1"),
            "queue_divergence_index": int(trace.group(6)) if trace else None,
        },
        "injection": {
            "results_consumed": int(injection.group(1)) if injection else 0,
            "result_words_written": int(injection.group(2)) if injection else 0,
            "engine_launches": int(injection.group(3)) if injection else -1,
            "engine_work": int(injection.group(4)) if injection else -1,
            "weight_halfword_reads": int(injection.group(5)) if injection else -1,
        },
        "cost": {
            "passes": int(cost.group(1)) if cost else 0,
            "simulated_cycles": int(cost.group(2)) if cost else 0,
            "simulate_seconds": float(cost.group(3)) if cost else 0.0,
            "host_writes": int(cost.group(4)) if cost else 0,
            "elaborate_and_compile_seconds": round(compile_seconds, 2),
            "run_seconds": round(run_seconds, 2),
            "golden_model_seconds": manifest["golden_model"]["wall_seconds"],
        },
        "issue_census": {
            "classes": int(census.group(1)) if census else 0,
            "instances": int(census.group(2)) if census else 0,
            "rows": census_rows,
            "source": "the RTL's own issue trace over every pass",
        },
        "eos_observation": {
            "selected_token": int(eos.group(1)) if eos else None,
            "selected_tie_multiplicity": int(eos.group(2)) if eos else None,
            "selected_eos_reason": int(eos.group(3)) if eos else None,
            "engine_launches": int(eos.group(4)) if eos else None,
        },
        "post_eos_probe": {
            "ran": bool(posteos and posteos.group(1) == "1"),
            "rtl_admitted_the_pass": bool(posteos and posteos.group(2) == "1"),
            "rtl_trapped": bool(posteos and posteos.group(3) == "1"),
            "trap_class": int(posteos.group(4)) if posteos else None,
            "issues": int(posteos.group(5)) if posteos else 0,
            "simulated_cycles": int(posteos.group(6)) if posteos else 0,
        },
        "passes": passes,
        "compile_command": canonical(" ".join(compile_command), build),
        "log_tail": canonical(stdout[-4000:], build),
    }


def compose_record(
    store: str,
    manifest: dict[str, Any],
    run: dict[str, Any],
    audit: dict[str, Any],
    study: dict[str, Any],
) -> dict[str, Any]:
    """One rung record, with every field the gate reads and nothing rounded."""
    counts = manifest["counts"]
    workload_positions = (
        manifest["workload"]["prompt_token_count"]
        + len(manifest["oracle"]["generated_token_ids"])
    )
    device_transactions = counts["passes"]
    # Every position whose forward pass the control plane actually ran: the
    # prefill transaction's own span, plus one per decode transaction.  The
    # final generated token is never fed back, so it is a position of the
    # sequence and not a pass of the model.
    forward_passes = 0
    positions_covered: list[dict[str, int]] = []
    for entry in manifest["passes"]:
        symbols = entry["symbols"]
        span = int(symbols.get("0", symbols.get(0, 1)))
        start = int(symbols.get("1", symbols.get(1, 0)))
        forward_passes += span
        positions_covered.append(
            {
                "pass_index": int(entry["pass_index"]),
                "entrypoint_id": int(entry["entrypoint_id"]),
                "position_start": start,
                "span_tokens": span,
                "positions": list(range(start, start + span)),
            }
        )
    trace = run.get("trace", {})
    equal = bool(trace.get("equal")) and run.get("marker_present", False)
    divergence = trace.get("divergence_index")
    gate_requires = int(study["gate_requires_passes"])
    # How far the control plane got towards the EOS decision, counted from the
    # RTL's own issue census rather than from anybody's reading of the program.
    # SELECTION.TOKEN_APPEND is the instruction rtl/abi3/
    # ot_a3_selection_token_append.sv answers, and it is the one that raises
    # OFFICIAL_EOS; if the RTL never issued it the two red EOS fields would
    # mean something quite different from what they mean here.
    census_rows = run.get("issue_census", {}).get("rows", [])
    def _selection(sub: int) -> int:
        return sum(
            int(row["instances"])
            for row in census_rows
            if int(row["family"]) == int(Major.SELECTION)
            and int(row["sub"]) == int(sub)
        )
    argmax_issues = _selection(int(Selection.ARGMAX))
    append_issues = _selection(int(Selection.TOKEN_APPEND))
    eos_reach = {
        "selection_argmax_issues": argmax_issues,
        "selection_token_append_issues": append_issues,
        "passes": device_transactions,
        "issued_in_every_pass": (
            device_transactions > 0
            and append_issues == device_transactions
            and argmax_issues == device_transactions
        ),
        "source": "the RTL's own issue census over every pass of this run",
        "meaning": (
            "the control plane fetched, decoded, resolved the operand views "
            "of and issued SELECTION.ARGMAX and SELECTION.TOKEN_APPEND -- the "
            "instruction pair that ends a generation -- in every pass. What "
            "did not happen is the engine behind it running: under "
            "ENABLE_RESULT_INJECTION the top ties the bridge's issue_valid "
            "low, so ot_a3_selection_token_append.sv was never started and "
            "raised nothing. official_eos_raised is false as a measurement of "
            "the engine, not as an absence of the instruction"
        ),
    }
    # The two EOS fields are DERIVED from what the run observed, never
    # written as constants.  A constant cannot be falsified by a better run,
    # and a field that a wiring change could flip without anything executing
    # is the defect this programme exists to prevent -- so each is a
    # conjunction of RTL observations, and each stays false here because the
    # observations say so.
    eos_observation = run.get("eos_observation", {})
    eos_reason_observed = eos_observation.get("selected_eos_reason")
    engine_launches = int(run.get("injection", {}).get("engine_launches", -1))
    official_eos_raised = derive_official_eos_raised(
        eos_observation, engine_launches
    )
    probe = run.get("post_eos_probe", {})
    probe_ran = bool(probe.get("ran"))
    probe_admitted = bool(probe.get("rtl_admitted_the_pass"))
    probe_trapped = bool(probe.get("rtl_trapped"))
    post_eos_refused = derive_post_eos_refused(probe)
    correct = [c for c in study["cases"] if c["reproduces_gold"]]
    wrong = [c for c in study["cases"] if not c["reproduces_gold"]]
    decomposition_summary = (
        f"{len(study['cases'])} submission sequences were executed on the "
        f"reference model, of which {len(correct)} reproduced the oracle's "
        f"gold ({', '.join(c['decomposition'] for c in correct) or 'none'}) "
        f"and {len(wrong)} did not "
        f"({', '.join(c['decomposition'] for c in wrong) or 'none'}). The "
        "largest pass count over the sequences that reproduce the gold is "
        f"{study['measured']['maximum_device_transactions_over_correct_decompositions']}"
        f", against the gate's {gate_requires}; "
        f"{study['measured']['maximum_forward_passed_positions_over_correct_decompositions']}"
        f" of the workload's {workload_positions} token positions are "
        "forward-passed, and the last generated token -- the official EOS -- "
        "is never fed back, so it is a position of the sequence and not a "
        "pass of the model"
    )
    record = {
        "storage_class": store,
        "workload_id": WORKLOAD_ID,
        "rung": "G1e",
        "execution": {
            "simulator": "verilator_cpp_executable",
            "simulator_version": PINNED_VERILATOR_VERSION,
            "simulated_cycles": int(run.get("cost", {}).get("simulated_cycles", 0)),
            "evidence_class": "public_open_tool_rtl_simulation",
            "vehicle": TOP,
            "control_plane": "rtl/abi3/ot_a3_device_top.sv",
            "parameters": PARAMETERS,
            "dual_simulator": False,
            "why_single_simulator": (
                "the vehicle declares `parameter longint unsigned "
                "MATMUL_WEIGHT_BYTES` and imports a DPI function returning "
                "`longint unsigned`; Icarus 11 cannot parse either, measured "
                "at this commit and before it. G1's own scope already records "
                "this vehicle as Verilator-only"
            ),
        },
        "git": git_identity(),
        "trace": {
            "equals_golden": equal,
            "divergence_index": None if divergence in (-1, None) else divergence,
            "compared_issue_count": int(counts["issues"]),
            "compared_view_count": int(counts["views"]),
            "compared_elements": int(trace.get("compared_elements", 0)),
            "compared_issue_fields": ["family", "sub", "descriptor_id", "pc"],
            "compared_view_fields": [
                "slot",
                "descriptor_id",
                "extent",
                "extent_axis",
                "element_offset",
                "rank",
            ],
            "uncompared_issue_fields": ["serial", "irs_slot"],
            "why_uncompared": (
                "the issue serial and the issue-record-store slot are RTL "
                "allocations the reference model does not compute; a golden "
                "that carried them would be comparing the RTL against the "
                "vector builder rather than against the model. The serial is "
                "still required to advance within each pass and the slot to "
                "be a real queue index"
            ),
            "extended_comparison": {
                "adds": ["queue"],
                "equal": bool(trace.get("queue_equal")),
                "compared_elements": int(trace.get("queue_compared_elements", 0)),
                "divergence_index": (
                    None
                    if trace.get("queue_divergence_index") in (-1, None)
                    else trace.get("queue_divergence_index")
                ),
                "meaning": (
                    "the schedule the SCHEDULE record selects is a pure "
                    "function of the operator's descriptor, so the model "
                    "computes it and the RTL's choice can be compared; "
                    "reported beside the gate-compared set, not folded into it"
                ),
            },
            "golden_source": manifest["golden_model"],
        },
        "passes": {
            "executed": device_transactions,
            "unit": "device transaction through the RTL control plane",
            "device_transactions": device_transactions,
            "model_forward_passes": forward_passes,
            "workload_token_positions": workload_positions,
            "positions_never_forward_passed": (
                workload_positions - forward_passes
            ),
            "positions_covered_per_pass": positions_covered,
            "positions_covered_note": (
                "SPAN_TOKENS and POSITION_START are the request symbols the "
                "RTL's symbol file was loaded with for each pass, so this is "
                "which of the workload's token positions the control plane "
                "actually drove, not a count of transactions"
            ),
            "per_pass": run.get("passes", []),
            "gate_requires": gate_requires,
            "gate_requires_read_from": "configs/gates/redesign_gates.json",
            "why_not_the_gate_number": (
                f"measured, not argued. The RTL ran {device_transactions} "
                "device transactions because that is what the workload's own "
                "submission sequence is: one prefill transaction whose "
                f"SPAN_TOKENS is "
                f"{manifest['workload']['prompt_token_count']} and covers "
                "every prompt position at once, then one decode transaction "
                "per further token. Whether the same workload could be cut "
                f"into {gate_requires} transactions was not reasoned about, it "
                f"was tried: {decomposition_summary}"
            ),
            "decomposition_study": {
                "artifact_schema": study.get("schema"),
                "tool": DECOMPOSITION,
                "reads_no_rtl": True,
                "gate_requires_passes": study["gate_requires_passes"],
                "measured": study["measured"],
                "finding": study["finding"],
                "does_not_establish": study["does_not_establish"],
                "wall_seconds": study.get("wall_seconds"),
                "deployment_sha256": study["deployment_sha256"],
                "workload_digest": study["workload_digest"],
                "oracle": study["oracle"],
                "source_sha256": study["source_sha256"],
                "cases": [
                    {
                        key: case[key]
                        for key in (
                            "decomposition",
                            "statement",
                            "device_transactions",
                            "completed_transactions",
                            "forward_passed_positions",
                            "generated_token_ids",
                            "reproduces_gold",
                            "note",
                            "wall_seconds",
                            "transactions",
                        )
                    }
                    for case in study["cases"]
                ],
                "marker": study.get("marker"),
            },
        },
        "eos": {
            "official_eos_raised": official_eos_raised,
            "post_eos_refused": post_eos_refused,
            "how_both_fields_are_decided": {
                "official_eos_raised": (
                    "the integrated top's selected_eos_reason output equals "
                    f"OFFICIAL_EOS ({int(EosReason.OFFICIAL_EOS)}, read from "
                    "runtime.abi3.records.EosReason) AND the run launched at "
                    "least one real engine. The second half is not "
                    "decoration: under result injection the EOS reason could "
                    "only be a model value passed through, and a field that "
                    "could be set by wiring an output with nothing having run "
                    "is the exact defect this ladder was built to catch. Both "
                    "halves come off the RTL run"
                ),
                "post_eos_refused": (
                    "the post-EOS probe ran AND the RTL either refused to "
                    "complete it or trapped it. Both come off the DUT's own "
                    "done/complete/trapped outputs on the pass driven after "
                    "the one that produced the official EOS"
                ),
                "measured_inputs": {
                    "selected_eos_reason": eos_reason_observed,
                    "official_eos_encoding": int(EosReason.OFFICIAL_EOS),
                    "real_engine_launches": engine_launches,
                    "post_eos_probe_ran": probe_ran,
                    "post_eos_probe_admitted": probe_admitted,
                    "post_eos_probe_trapped": probe_trapped,
                },
                "self_test": eos_field_self_test(),
            },
            "model_stop_reason": manifest["model_run"]["stop_reason"],
            "model_generated_token_ids": manifest["model_run"]["generated_token_ids"],
            "post_eos_attempt": manifest["post_eos"],
            "rtl_eos_observation": {
                **run.get("eos_observation", {}),
                "eos_reason_encoding": {"0": "EOS_NONE", "1": "OFFICIAL_EOS",
                                        "2": "MAX_NEW_TOKENS"},
                "meaning": (
                    "measured at the end of the run: the integrated top's "
                    "selection outputs, which rtl/abi3/"
                    "ot_a3_selection_token_append.sv drives. Under result "
                    "injection the bridge's issue_valid is tied low, so that "
                    "engine is never issued to and the outputs hold their "
                    "reset values. An OFFICIAL_EOS reported by this rung "
                    "would have been the model's, passed through"
                ),
            },
            "post_eos_probe_measured_in_rtl": {
                **run.get("post_eos_probe", {}),
                "meaning": (
                    "one further pass was driven into the RTL after the pass "
                    "that produced the official EOS, configured exactly as the "
                    "last decode pass. The reference model refuses such a "
                    "transaction before fetching an instruction; what the RTL "
                    "control plane does with it is measured here rather than "
                    "argued. Its issues are not part of the compared trace"
                ),
            },
            "control_plane_reached_the_eos_instruction": eos_reach,
            "why_not_measured_in_rtl": (
                "in the promoted lowering the EOS decision is an ENGINE result "
                "-- rtl/abi3/ot_a3_selection_token_append.sv raises "
                "OFFICIAL_EOS from the policy's EOS set -- and under result "
                "injection no engine is issued to, so an EOS raised here would "
                "be the model's value passed through. The post-EOS refusal is "
                "a host session-state refusal in "
                "runtime/sim/device.py:run_transaction, taken before an "
                "instruction is fetched; this deployment's program carries no "
                "STATE instruction and no EOS_MEMBER predicate, so its RTL "
                "control plane has nothing to refuse. Neither field is written "
                "as a constant: each is the conjunction of RTL observations "
                "recorded in how_both_fields_are_decided, and each is false "
                "because those observations are"
            ),
            "what_would_measure_them": [
                "OFFICIAL_EOS: issue SELECTION.TOKEN_APPEND to the real engine "
                "with the injected ARGMAX token, which needs the top to select "
                "injection per issue rather than by parameter",
                "post-EOS refusal: a program that predicates its continuation "
                "on EOS_MEMBER, or a device-side session the RTL owns",
            ],
        },
        "injection": {
            "control_path_is_rtl": bool(
                audit["clean"]
                and run.get("injection", {}).get("engine_launches") == 0
                and run.get("injection", {}).get("engine_work") == 0
                and run.get("injection", {}).get("weight_halfword_reads") == 0
            ),
            "boundary": "engine_result",
            "sites": audit,
            "measured_at_run_time": run.get("injection", {}),
            "derivation": manifest["injection_derivation"],
            "what_the_control_plane_did_itself": [
                "instruction fetch and decode from the loaded program store",
                "symbol-file binding of the request's sixteen symbols",
                "loop setup, iteration and teardown on the loop stack",
                "operand view resolution, including every element offset",
                "wait-set evaluation against the event scoreboard",
                "dependence-table hazard checking",
                "queue acceptance and issue in program order",
                "retirement and the completion of every issue",
            ],
        },
        "issue_census": {
            **run.get("issue_census", {}),
            "for": (
                "G1's composition certificate, which its own acceptance "
                "requires to be derived mechanically from this rung's issue "
                "trace rather than asserted: these are the (family, subopcode, "
                "descriptor id) instances the governed workload issued, "
                "counted from the RTL's trace and not from the golden's"
            ),
        },
        "oracle": manifest["oracle"],
        "deployment": manifest["deployment"],
        "workload": manifest["workload"],
        "golden_vectors": {
            "counts": counts,
            "files": manifest["emitted"],
            "manifest_schema": manifest["schema"],
        },
        "cost": run.get("cost", {}),
        "checks": run.get("checks", 0),
        "marker": run.get("marker"),
        "checker_returncode": run.get("returncode"),
    }
    return record


def cost_measurement(records: list[dict[str, Any]]) -> dict[str, Any]:
    """What the rung cost, and the estimate that measurement replaces.

    The ladder table in docs/OPENTALLAS_REDESIGN_PLAN.md and section 11.5 of
    docs/CHIP_ARCHITECTURE_DESIGN.md both carry ~3 h per store for this rung.
    That figure is not adjusted anywhere by this tool; it is reported beside
    the measurement, with the arithmetic that most likely produced it, because
    an estimate replaced without saying what it was is a number nobody can
    check.
    """
    per_store = {}
    for record in records:
        cost = record["cost"]
        cycles = int(record["execution"]["simulated_cycles"])
        seconds = float(cost.get("simulate_seconds") or 0.0) or 1e-9
        rate = cycles / seconds
        words = int(
            record["injection"]["derivation"][
                "golden_output_words_if_every_word_were_supplied"
            ]
        )
        study_seconds = float(
            record["passes"]["decomposition_study"].get("wall_seconds") or 0.0
        )
        per_store[record["storage_class"]] = {
            "golden_model_seconds": cost.get("golden_model_seconds"),
            "pass_decomposition_study_seconds": round(study_seconds, 2),
            "elaborate_and_compile_seconds": cost.get(
                "elaborate_and_compile_seconds"
            ),
            "simulate_seconds": cost.get("simulate_seconds"),
            "run_seconds": cost.get("run_seconds"),
            "end_to_end_seconds": round(
                float(cost.get("golden_model_seconds") or 0)
                + float(cost.get("elaborate_and_compile_seconds") or 0)
                + float(cost.get("run_seconds") or 0)
                + study_seconds,
                2,
            ),
            "simulated_cycles": cycles,
            "simulated_cycles_per_second": round(rate),
            "hypothetical_seconds_if_every_output_word_were_injected": round(
                words / rate
            ),
            "hypothetical_note": (
                "a lower bound: one result-memory write cycle per word, "
                f"{words:,} words, at this run's own measured rate. It is "
                "reported because it is the arithmetic that most plausibly "
                "produced the ~3 h estimate, not because this rung needs it -- "
                "the RTL control plane can observe a result word only through "
                "a PREDICATE, and this program declares none"
            ),
        }
    total = round(sum(v["end_to_end_seconds"] for v in per_store.values()), 2)
    return {
        "measured_per_store": per_store,
        "measured_all_stores_seconds": total,
        "replaces": {
            "figure": "~3 h per store",
            "recorded_in": [
                "docs/OPENTALLAS_REDESIGN_PLAN.md, the ladder table's G1e row",
                "docs/CHIP_ARCHITECTURE_DESIGN.md section 11.5",
                "configs/gates/redesign_gates.json, G1e's evaluator note",
            ],
            "also_reported_as": (
                "3.10 h per store by the lane that built the injection "
                "vehicle, which reported that conservative figure over an "
                "optimistic 0.35 h form under R13"
            ),
            "measured_instead": total,
            "not_edited_here": (
                "no document or gate figure is changed by this tool; the "
                "measurement is published beside the estimate"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ARTIFACT)
    parser.add_argument("--build-root", type=Path, default=None)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument(
        "--stores", nargs="*", choices=STORES, default=list(STORES)
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="run the injection-site audit and its self test, and stop",
    )
    args = parser.parse_args()

    top_text = (ROOT / TOP).read_text(encoding="utf-8")
    audit = audit_injection(top_text)
    audit["self_test"] = audit_self_test(top_text)
    fields = eos_field_self_test()
    if not fields["passed"]:
        raise SystemExit(
            "the EOS field self test failed: at least one of "
            "official_eos_raised and post_eos_refused no longer follows the "
            "run's observations. A rung whose fields cannot move is not "
            "evidence, and nothing is published:\n"
            + json.dumps(fields, indent=2)
        )
    if args.audit_only:
        print(json.dumps({"injection": audit, "eos_fields": fields}, indent=2))
        return (
            0
            if audit["clean"]
            and audit["self_test"]["refused_the_spliced_edge"]
            and fields["passed"]
            else 1
        )

    verilator = resolve(
        "verilator", TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    )
    tools = {
        "verilator": tool_record(verilator, ["--version"]),
        "cxx": tool_record(resolve("g++", None), ["--version"]),
    }
    require_versions(tools)

    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="opentallas-g1e-") as raw:
        root = Path(args.build_root) if args.build_root else Path(raw)
        root.mkdir(parents=True, exist_ok=True)
        for store in args.stores:
            vectors = root / f"vectors-{store}"
            manifest = build_vectors(store, vectors, args.checkpoint)
            study = run_decomposition(
                store, root / f"decomposition-{store}.json", args.checkpoint
            )
            run = run_store(
                store, manifest, vectors, root / f"build-{store}", verilator
            )
            records.append(compose_record(store, manifest, run, audit, study))

    source_paths = (*RTL_SOURCES, *TEST_SOURCES, *TOOL_SOURCES, *CONTRACT_SOURCES)
    body = {
        "schema": SCHEMA,
        "campaign": "abi3_g1e_control_end_to_end",
        "rung": "G1e",
        "gate": "G1e (configs/gates/redesign_gates.json)",
        "workload_id": WORKLOAD_ID,
        "status": "pass"
        if all(
            record["trace"]["equals_golden"]
            and record["injection"]["control_path_is_rtl"]
            and record["passes"]["executed"] == gate_required_passes()
            and record["eos"]["official_eos_raised"]
            and record["eos"]["post_eos_refused"]
            for record in records
        )
        and len(records) == len(STORES)
        else "fail",
        "what_ran": {
            "reference": "runtime.sim.device.Device, run by the workload's own "
            "GenerationDriver; no RTL is read by the golden builder",
            "vehicle": TOP + " with ENABLE_RESULT_INJECTION=1",
            "compared": [
                "every engine issue in program order: family, subopcode, "
                "descriptor id and program counter",
                "every operand view the RTL resolver produced for it: slot, "
                "descriptor id, extent, extent axis, 64-bit element offset "
                "and rank",
                "per pass: instructions fetched, retired, predicated off and "
                "issued, loop iterations, wait events and views resolved",
                "per issue: that the injected result answers the issue the RTL "
                "actually made, by opcode, descriptor id and program counter",
            ],
            "not_compared": [
                "any engine arithmetic: no engine is issued to and none can be",
                "the token ids: this rung emits none -- the selected token is "
                "an injected engine result, and an RTL-emitted token is G1d's "
                "claim, not this one",
            ],
        },
        "claim_boundary": {
            "establishes": [
                "the ABI 3.0 control plane RTL issues the same sequence the "
                "reference model does, over every pass of the governed "
                "workload, on each of ROM and HBM, compared element for "
                "element with the first divergence recorded",
                "the injected values reach only the engine completion "
                "handshake and the result memory write port, re-derived from "
                "the RTL source by an audit that is required to refuse a "
                "spliced counter-example",
                "no engine ran: zero launches, zero engine work and zero "
                "weight reads, measured per pass",
                "which host decompositions of the governed workload this "
                "deployment admits at all, executed rather than reasoned "
                "about, with the ones that do not reproduce the oracle's gold "
                "recorded with the tokens they produced instead",
            ],
            "does_not_establish": [
                "that the gate's pass count is wrong about the model: the "
                "decomposition study measures the SHIPPED program, and a "
                "different lowering of the same model could cut the workload "
                "differently",
                "any engine result: every one was supplied",
                "an RTL-emitted token, or an RTL-raised OFFICIAL_EOS",
                "dual-simulator agreement: Icarus 11 cannot parse this "
                "vehicle's 64-bit weight window declarations",
                "any rate or cycle-accurate timing claim",
            ],
        },
        "cost_measurement": cost_measurement(records),
        "records": records,
        "tools": tools,
        "git": git_identity(),
        "source_sha256": {
            path: sha256_file(ROOT / path)
            for path in source_paths
            if (ROOT / path).is_file()
        },
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for record in records:
        print(
            f"{record['storage_class']}: trace equal="
            f"{record['trace']['equals_golden']} divergence="
            f"{record['trace']['divergence_index']} issues="
            f"{record['trace']['compared_issue_count']} elements="
            f"{record['trace']['compared_elements']} passes="
            f"{record['passes']['executed']} cycles="
            f"{record['execution']['simulated_cycles']} "
            f"control_path_is_rtl={record['injection']['control_path_is_rtl']}"
        )
    print(f"status={body['status']} -> {args.output}")
    return 0 if body["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
