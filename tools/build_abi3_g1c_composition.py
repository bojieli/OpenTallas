#!/usr/bin/env python3
"""Derive rung G1c's artifact: composition -- the inductive step and the loop.

G1c (``configs/gates/redesign_gates.json``) is two claims, and this tool keeps
them apart because only one of them has a run behind it today.

**The handoff.**  Two consecutive layers execute back to back in the
integrated RTL, with no golden value crossing the layer boundary.  That is
measured from the integrated shipped-prefix campaign -- the only vehicle in
this repository that runs the real compiled program through the real control
plane with the engine array computing.  It fails closed inside the FIRST
invocation of the layer body, so the loop's back edge is never reached and no
layer boundary is ever crossed.  This tool computes how far the run actually
got, in the program's own terms, and refuses to report ``mismatched_words: 0``
over zero compared words: the field is written ``null`` with the count of
comparisons beside it.  Zero mismatches over zero comparisons is not evidence
and the ladder's whole point is that absence is a failure, not a pass.

**The loop property.**  The loop control issues exactly the model's layer count
of structurally identical invocations.  G1c's own note requires this to be
*mechanically checked, not asserted*, and it is: rung G1e already drives every
device transaction of the governed workload through the design's own control
plane and certifies the RTL's issue trace equal to the reference model's
element for element on ``(family, sub, descriptor_id, pc)``.  That trace is
the measurement this rung reads.  It is not taken on trust either:

* the control run's artifact must declare a clean worktree, a named
  simulator, positive simulated cycles, an RTL evidence class, a trace equal
  to golden with a null divergence index, and a control path that is the
  RTL's;
* the deployment digest the control run bound must equal the deployment on
  disk, or the program walked here is not the program that ran;
* the dumped trace file's own ``(family, sub, descriptor_id)`` census must
  reproduce, row for row, the CENSUS the harness printed and the control
  artifact independently recorded.  A trace file that had been edited would
  fail that check.

**Nothing here is a PC typed into this file.**  The layer loop is found by
walking the deployment's own LOOP_CONTROL descriptors and asking which loop's
body issues operators whose certified Kernel IR ``kernel_id`` all lie inside
one transformer layer.  The model's layer count comes from the Kernel IR's own
distinct layer prefixes and is cross-checked against the checkpoint's
``config.json`` ``num_hidden_layers``; a disagreement refuses the build rather
than picking one.  An invocation boundary is the loop's back edge as the trace
shows it -- a program counter that does not advance -- not a stride assumed
here.

**Structural identity is checked on the fields, not asserted.**  Every
invocation's issue sequence is compared element for element, and so is every
operand view the RTL resolver produced for it.  ``element_offset`` is the one
field expected to move, because moving it is what a loop is for: it is
required to be an arithmetic progression across the invocations of one
transaction, and the per-position strides are recorded.  Where a field does
differ between transactions -- the activation extent is 16 in the prefill
transaction and 1 in each decode transaction -- it is reported as a measured
difference with its cause, never averaged away.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import NO_ID, Major, Control  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_g1b = _module("_g1c_g1b", "tools/build_abi3_g1b_layer_closure.py")

SCHEMA = "opentallas.rtl.g1c_composition.v1"
WORKLOAD = "TA-QW-EOS-1"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_g1c_composition.json"
G1E_SCHEMA = "opentallas.rtl.abi3_g1e_control_end_to_end.v1"

# The two storage classes G1c requires and the deployment directory each is.
STORAGE_CLASSES = {
    "rom": ("qwen3-8b-rom-single-chip", "build/abi3/qwen3-8b-rom"),
    "hbm": ("qwen3-8b-hbm-single-chip", "build/abi3/qwen3-8b-hbm-tokens"),
}

SLOT_FIELDS = (
    "input_view_0",
    "input_view_1",
    "input_view_2",
    "input_view_3",
    "output_view_0",
    "output_view_1",
)

# The trace fields G1e certified the RTL equal to the reference model on.
CERTIFIED_ISSUE_FIELDS = ("family", "sub", "descriptor_id", "pc")
# Every view field except the offset, which is what a loop moves.
CERTIFIED_VIEW_SHAPE_FIELDS = ("slot", "descriptor_id", "extent", "extent_axis", "rank")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_state() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout.strip()

    def run_lines(args: list[str]) -> str:
        # ``git status --porcelain`` prefixes every line with a two-column
        # status field and a space, and an unstaged modification's first
        # column is a SPACE.  Stripping the whole output before splitting
        # therefore ate the first line's leading space and ``line[3:]``
        # then ate the first character of the first dirty path: this
        # record named a file that does not exist.  It never moved
        # ``worktree_dirty`` -- that is a bool over a non-empty list -- so
        # no gate verdict turned on it; what it corrupted is the provenance
        # a reader would use to find out WHICH file was dirty.  Only the
        # trailing newline is stripped now.
        return subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout.rstrip("\n")

    porcelain = run_lines(["git", "status", "--porcelain"])
    dirty = sorted(line[3:].strip() for line in porcelain.splitlines() if len(line) > 3)
    return {
        "commit": run(["git", "rev-parse", "HEAD"]) or None,
        "worktree_dirty": bool(dirty),
        "dirty_paths": dirty,
        "scope": (
            "the tree THIS artifact was derived in. It is not a claim about "
            "the tree either run happened in; see execution.control_plane_run "
            "and handoff.integrated_campaign for those."
        ),
    }


# --------------------------------------------------------------------------
# The program, read from the deployment rather than described here.
# --------------------------------------------------------------------------
class ProgramFacts:
    """One lowering's decoded program body, its loops and its issue sites."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.deployment = Deployment.read(directory)
        self.deployment_sha256 = self.deployment.deployment_digest.hex()
        _, body = split_program(self.deployment.program)
        self.instructions = decode_body(body)
        self.loops: list[dict[str, Any]] = []
        self.issue_sites: dict[int, dict[str, Any]] = {}
        for pc, instruction in enumerate(self.instructions):
            major = int(instruction.major)
            sub = int(instruction.sub)
            if major == int(Major.CONTROL) and sub == int(Control.LOOP_SETUP):
                loop_id = int(instruction.control_id)
                payload = self.deployment.table.get(
                    loop_id, ExtendedDescriptorType.LOOP_CONTROL
                ).payload
                self.loops.append(
                    {
                        "loop_control_descriptor_id": loop_id,
                        "setup_pc": pc,
                        "body_start": int(payload["body_start"]),
                        "body_end": int(payload["body_end"]),
                        "max_iterations": int(payload["max_iterations"]),
                        "bound_selector_kind": int(payload["bound_selector_kind"]),
                        "lower_bound": int(payload["lower_bound"]),
                        "upper_bound": int(payload["upper_bound"]),
                        "step": int(payload["step"]),
                    }
                )
                continue
            descriptor_id = int(instruction.descriptor_id)
            if major == int(Major.CONTROL) or descriptor_id == NO_ID:
                continue
            operator = self.deployment.table.get(
                descriptor_id, ExtendedDescriptorType.OPERATOR
            ).payload
            slots = []
            for field in SLOT_FIELDS:
                view_id = int(operator[field])
                if view_id == NO_ID:
                    continue
                view = self.deployment.table.get(
                    view_id, ExtendedDescriptorType.TENSOR_VIEW
                )
                dims = [int(view.payload[f"dim{i}"]) for i in range(6)]
                slots.append(
                    {
                        "slot": field,
                        "view_descriptor_id": view_id,
                        "object_id": int(view.primary_object_id),
                        "dtype": int(view.payload["dtype"]),
                        "rank": int(view.payload["rank"]),
                        "declared_dims": [d for d in dims if d],
                    }
                )
            self.issue_sites[pc] = {
                "pc": pc,
                "mnemonic": instruction.mnemonic,
                "family": major,
                "sub": sub,
                "operator_descriptor_id": descriptor_id,
                "source_kernel_id": int(operator["source_kernel_id"]),
                "slots": slots,
            }

    def back_edge_pc(self, loop: dict[str, Any]) -> int:
        """The LOOP_NEXT that closes ``loop``, found in the program body."""
        loop_id = loop["loop_control_descriptor_id"]
        for pc in range(loop["body_start"], min(loop["body_end"] + 1,
                                                len(self.instructions))):
            instruction = self.instructions[pc]
            if (
                int(instruction.major) == int(Major.CONTROL)
                and int(instruction.sub) == int(Control.LOOP_NEXT)
                and int(instruction.control_id) == loop_id
            ):
                return pc
        raise SystemExit(
            f"{self.directory}: loop {loop_id} declares body "
            f"[{loop['body_start']}, {loop['body_end']}] but the body carries "
            "no LOOP_NEXT naming it; the back edge cannot be located and this "
            "rung will not assume one"
        )


def layer_loop(facts: ProgramFacts, kernels: dict[str, Any]) -> dict[str, Any]:
    """The loop whose body is one transformer layer, found from the graph.

    Not a PC: the loop is selected by asking which loop's body issues
    operators whose certified Kernel IR kernel ids all lie inside a single
    ``layer.<n>.`` prefix, and covers every operator of that layer that the
    program issues at all.
    """
    layer_sites = {}
    for pc, site in facts.issue_sites.items():
        kernel_id = kernels["kernels"].get(site["source_kernel_id"])
        if kernel_id is None:
            raise SystemExit(
                f"PC {pc}: descriptor {site['operator_descriptor_id']} names "
                f"kernel index {site['source_kernel_id']}, absent from the "
                "certified Kernel IR"
            )
        parts = kernel_id.split(".")
        if len(parts) >= 2 and parts[0] == "layer" and parts[1].isdigit():
            layer_sites[pc] = (kernel_id, f"{parts[0]}.{parts[1]}.")
    if not layer_sites:
        raise SystemExit("no issue site names a layer kernel; the layer loop "
                         "cannot be identified from the graph")
    prefixes = {prefix for _, prefix in layer_sites.values()}
    if len(prefixes) != 1:
        raise SystemExit(
            f"the program issues operators of {sorted(prefixes)}; this rung's "
            "loop property is about a body that is exactly one layer"
        )
    prefix = prefixes.pop()
    candidates = []
    for loop in facts.loops:
        inside = {
            pc for pc in facts.issue_sites
            if loop["body_start"] <= pc <= loop["body_end"]
        }
        if not inside:
            continue
        if inside & set(layer_sites) != inside:
            continue
        if set(layer_sites) - inside:
            continue
        candidates.append(loop)
    if len(candidates) != 1:
        raise SystemExit(
            f"{len(candidates)} loops have a body that is exactly the layer's "
            "issue sites; the layer loop is not uniquely identified and this "
            "rung will not choose one"
        )
    loop = dict(candidates[0])
    loop["layer_prefix"] = prefix
    loop["back_edge_pc"] = facts.back_edge_pc(loop)
    loop["issue_pcs"] = sorted(layer_sites)
    loop["kernel_ids"] = [layer_sites[pc][0] for pc in sorted(layer_sites)]
    loop["identified_by"] = (
        "the loop whose declared body [body_start, body_end] contains exactly "
        "the issue sites whose certified Kernel IR kernel_id begins "
        f"{prefix!r}, taken from each OPERATOR descriptor's own "
        "source_kernel_id"
    )
    return loop


def model_layer_count(kernels: dict[str, Any], checkpoint: Path | None) -> dict[str, Any]:
    """The model's layer count, from the graph and from the checkpoint."""
    prefixes = set()
    for kernel_id in kernels["kernels"].values():
        parts = str(kernel_id).split(".")
        if len(parts) >= 2 and parts[0] == "layer" and parts[1].isdigit():
            prefixes.add(int(parts[1]))
    if not prefixes:
        raise SystemExit("the certified Kernel IR declares no layer kernels")
    from_graph = len(prefixes)
    if sorted(prefixes) != list(range(from_graph)):
        raise SystemExit(
            f"the Kernel IR's layer indices are {sorted(prefixes)[:8]}..., not "
            "a contiguous range from zero"
        )
    record: dict[str, Any] = {
        "layers": from_graph,
        "from_kernel_ir": from_graph,
        "kernel_ir": kernels["path"],
        "kernel_ir_sha256": kernels["sha256"],
    }
    if checkpoint is not None:
        config = Path(checkpoint).expanduser() / "config.json"
        if not config.is_file():
            raise SystemExit(f"{config} is absent; the checkpoint cross-check "
                             "cannot be made and this rung will not skip it")
        body = json.loads(config.read_text())
        declared = int(body["num_hidden_layers"])
        record["from_checkpoint_config"] = declared
        record["checkpoint_config"] = str(config)
        record["checkpoint_config_sha256"] = sha256_file(config)
        if declared != from_graph:
            raise SystemExit(
                f"the Kernel IR declares {from_graph} layers and the "
                f"checkpoint's config.json declares {declared}; two numbers "
                "for one fact, and this rung will not pick one"
            )
        record["sources_agree"] = True
    else:
        record["from_checkpoint_config"] = None
        record["sources_agree"] = None
    return record


# --------------------------------------------------------------------------
# The RTL's own issue trace.
# --------------------------------------------------------------------------
def read_rtl_trace(path: Path) -> list[dict[str, Any]]:
    """Parse the trace the G1e harness wrote under ``OT_A3_TRACE_OUT``."""
    issue_fields: list[str] | None = None
    view_fields: list[str] | None = None
    issues: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "FIELDS":
            if parts[1] == "ISSUE":
                issue_fields = parts[2:]
            elif parts[1] == "VIEW":
                view_fields = parts[2:]
            else:
                raise SystemExit(f"{path}:{number}: unknown FIELDS tag {parts[1]!r}")
            continue
        if parts[0] == "ISSUE":
            if issue_fields is None:
                raise SystemExit(f"{path}:{number}: ISSUE before FIELDS ISSUE")
            if len(parts) - 1 != len(issue_fields):
                raise SystemExit(f"{path}:{number}: ISSUE has the wrong arity")
            issues.append(
                {
                    **{n: int(v) for n, v in zip(issue_fields, parts[1:])},
                    "views": [],
                }
            )
            continue
        if parts[0] == "VIEW":
            if view_fields is None or not issues:
                raise SystemExit(f"{path}:{number}: VIEW outside an issue")
            if len(parts) - 1 != len(view_fields):
                raise SystemExit(f"{path}:{number}: VIEW has the wrong arity")
            issues[-1]["views"].append(
                {n: int(v) for n, v in zip(view_fields, parts[1:])}
            )
            continue
        raise SystemExit(f"{path}:{number}: unknown trace tag {parts[0]!r}")
    if not issues:
        raise SystemExit(f"{path} carries no issue")
    return issues


def control_run_evidence(
    artifact: Path, trace_root: Path, storage_class: str
) -> dict[str, Any]:
    """The G1e control run whose certified trace this rung reads, re-checked."""
    body = json.loads(artifact.read_text())
    record: dict[str, Any] = {
        "artifact": str(artifact),
        "artifact_sha256": sha256_file(artifact),
        "schema": body.get("schema"),
        "declared_git": body.get("git"),
    }
    reasons: list[str] = []
    if body.get("schema") != G1E_SCHEMA:
        reasons.append(f"schema is {body.get('schema')!r}, not {G1E_SCHEMA!r}")
    rec = next(
        (r for r in (body.get("records") or [])
         if r.get("storage_class") == storage_class),
        None,
    )
    if rec is None:
        reasons.append(f"it carries no record for storage class {storage_class!r}")
        record.update(usable=False, why_unusable="; ".join(reasons))
        return record
    record["workload_id"] = rec.get("workload_id")
    record["rung"] = body.get("rung")
    record["simulator"] = _g1b._dig(rec, "execution.simulator")
    record["simulator_version"] = _g1b._dig(rec, "execution.simulator_version")
    record["simulated_cycles"] = _g1b._dig(rec, "execution.simulated_cycles")
    record["evidence_class"] = _g1b._dig(rec, "execution.evidence_class")
    record["vehicle"] = _g1b._dig(rec, "execution.vehicle")
    record["control_plane"] = _g1b._dig(rec, "execution.control_plane")
    record["parameters"] = _g1b._dig(rec, "execution.parameters")
    record["trace"] = {
        "equals_golden": _g1b._dig(rec, "trace.equals_golden"),
        "divergence_index": _g1b._dig(rec, "trace.divergence_index"),
        "compared_issue_count": _g1b._dig(rec, "trace.compared_issue_count"),
        "compared_elements": _g1b._dig(rec, "trace.compared_elements"),
        "compared_issue_fields": _g1b._dig(rec, "trace.compared_issue_fields"),
        "compared_view_fields": _g1b._dig(rec, "trace.compared_view_fields"),
        "golden_source": _g1b._dig(rec, "trace.golden_source.module"),
    }
    record["passes"] = {
        "executed": _g1b._dig(rec, "passes.executed"),
        "unit": _g1b._dig(rec, "passes.unit"),
        "workload_token_positions": _g1b._dig(rec, "passes.workload_token_positions"),
        "per_pass": _g1b._dig(rec, "passes.per_pass"),
    }
    record["injection"] = {
        "boundary": _g1b._dig(rec, "injection.boundary"),
        "control_path_is_rtl": _g1b._dig(rec, "injection.control_path_is_rtl"),
        "engine_launches": _g1b._dig(rec, "injection.measured_at_run_time.engine_launches"),
    }
    record["deployment_sha256"] = _g1b._dig(rec, "deployment.deployment_sha256")
    record["issue_census"] = _g1b._dig(rec, "issue_census.rows")

    if _g1b._dig(body, "git.worktree_dirty") is not False:
        reasons.append("it does not declare a clean worktree, so it is not source-bound")
    if not record["simulator"]:
        reasons.append("it names no simulator")
    cycles = record["simulated_cycles"]
    if not isinstance(cycles, int) or cycles <= 0:
        reasons.append(f"its simulated_cycles is {cycles!r}")
    if "rtl" not in str(record["evidence_class"]).lower():
        reasons.append(f"its evidence_class {record['evidence_class']!r} does not name RTL")
    if record["trace"]["equals_golden"] is not True:
        reasons.append("its issue trace is not equal to the reference model's")
    if record["trace"]["divergence_index"] is not None:
        reasons.append(
            f"its trace diverges at index {record['trace']['divergence_index']}"
        )
    if record["injection"]["control_path_is_rtl"] is not True:
        reasons.append("its control path is not declared to be the RTL's")
    for field in CERTIFIED_ISSUE_FIELDS:
        if field not in (record["trace"]["compared_issue_fields"] or []):
            reasons.append(
                f"its compared issue fields do not include {field!r}, which "
                "this rung's loop property is derived from"
            )

    # Every source the control run bound, re-hashed against the tree as it is
    # now.  The run may have happened at an earlier commit; what matters is
    # that nothing it depended on has moved since, and that is checked rather
    # than argued from the commit id.
    bound = body.get("source_sha256") or {}
    drifted = []
    for relative, digest in sorted(bound.items()):
        resolved = ROOT / relative
        if not resolved.is_file():
            drifted.append(f"{relative} [missing]")
        elif sha256_file(resolved) != digest:
            drifted.append(relative)
    record["bound_source_count"] = len(bound)
    record["drifted_source_count"] = len(drifted)
    record["drifted_sources"] = drifted
    if not bound:
        reasons.append("it binds no source digests, so it cannot be re-checked")
    elif drifted:
        reasons.append(
            f"{len(drifted)} source(s) it bound have drifted since it ran: "
            + ", ".join(drifted[:4])
        )

    trace_path = Path(trace_root) / f"build-{storage_class}" / "rtl_issue_trace.txt"
    record["trace_file"] = str(trace_path)
    if not trace_path.is_file():
        reasons.append(f"the RTL issue trace {trace_path} is absent")
        record.update(usable=False, why_unusable="; ".join(reasons))
        return record
    record["trace_file_sha256"] = sha256_file(trace_path)
    issues = read_rtl_trace(trace_path)
    record["trace_file_issue_count"] = len(issues)
    if len(issues) != record["trace"]["compared_issue_count"]:
        reasons.append(
            f"the trace file carries {len(issues)} issues and the run "
            f"reports {record['trace']['compared_issue_count']} compared"
        )
    # Bind the dumped file to the run's own independently recorded census.
    census: dict[tuple[int, int, int], int] = {}
    for issue in issues:
        key = (issue["family"], issue["sub"], issue["descriptor_id"])
        census[key] = census.get(key, 0) + 1
    declared = {
        (int(r["family"]), int(r["sub"]), int(r["descriptor_id"])): int(r["instances"])
        for r in (record["issue_census"] or [])
    }
    record["census_rows_from_the_trace_file"] = len(census)
    record["census_agrees_with_the_run"] = census == declared
    if not declared:
        reasons.append("the run records no issue census to bind the trace file to")
    elif census != declared:
        reasons.append(
            "the trace file's own (family, sub, descriptor id) census does "
            "not reproduce the census the run printed"
        )
    record["usable"] = not reasons
    record["why_unusable"] = "; ".join(reasons) if reasons else None
    record["issues"] = issues
    return record


# --------------------------------------------------------------------------
# The loop property, measured from the certified trace.
# --------------------------------------------------------------------------
def _issue_key(issue: dict[str, Any]) -> tuple[int, ...]:
    return tuple(int(issue[f]) for f in CERTIFIED_ISSUE_FIELDS)


def _view_shape(issue: dict[str, Any]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(int(view[f]) for f in CERTIFIED_VIEW_SHAPE_FIELDS)
        for view in issue["views"]
    )


def segment_invocations(
    issues: list[dict[str, Any]], loop: dict[str, Any]
) -> list[list[dict[str, Any]]]:
    """Split the trace into invocations of the loop body.

    An invocation ends where the trace's program counter stops advancing --
    the loop's back edge as the RTL took it.  Nothing about the body's length
    or its stride is assumed; consecutive invocations are contiguous in the
    trace precisely because the back edge issues nothing.
    """
    start, end = loop["body_start"], loop["body_end"]
    invocations: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] | None = None
    previous = -1
    for issue in issues:
        pc = int(issue["pc"])
        if start <= pc <= end:
            if current is None or pc <= previous:
                current = []
                invocations.append(current)
            current.append(issue)
            previous = pc
        else:
            current = None
            previous = -1
    return invocations


def loop_property(
    issues: list[dict[str, Any]],
    loop: dict[str, Any],
    layers: dict[str, Any],
    transactions: int,
    per_pass: list[dict[str, Any]] | None = None,
    facts: "ProgramFacts | None" = None,
) -> dict[str, Any]:
    invocations = segment_invocations(issues, loop)
    lengths = sorted({len(inv) for inv in invocations})
    issue_keys = {tuple(_issue_key(i) for i in inv) for inv in invocations}
    view_shapes = {tuple(_view_shape(i) for i in inv) for inv in invocations}

    per_transaction: list[dict[str, Any]] = []
    identical_within = True
    offsets_arithmetic = True
    strides: dict[str, int] = {}
    if transactions and len(invocations) % transactions == 0:
        stride = len(invocations) // transactions
        for index in range(transactions):
            block = invocations[index * stride:(index + 1) * stride]
            keys = {tuple(_issue_key(i) for i in inv) for inv in block}
            shapes = {tuple(_view_shape(i) for i in inv) for inv in block}
            block_arithmetic = True
            block_strides: dict[str, list[int]] = {}
            if len({len(inv) for inv in block}) == 1 and block:
                for position in range(len(block[0])):
                    for slot in range(len(block[0][position]["views"])):
                        series = [
                            int(inv[position]["views"][slot]["element_offset"])
                            for inv in block
                        ]
                        deltas = {b - a for a, b in zip(series, series[1:])}
                        if len(deltas) > 1:
                            block_arithmetic = False
                        else:
                            name = (
                                f"pc{block[0][position]['pc']}"
                                f".slot{block[0][position]['views'][slot]['slot']}"
                            )
                            block_strides[name] = sorted(deltas)
            else:
                block_arithmetic = False
            identical_within = identical_within and len(keys) == 1 and len(shapes) == 1
            offsets_arithmetic = offsets_arithmetic and block_arithmetic
            for name, values in block_strides.items():
                if len(values) == 1:
                    strides.setdefault(name, values[0])
            per_transaction.append(
                {
                    "transaction_index": index,
                    "invocations": len(block),
                    "distinct_issue_structures": len(keys),
                    "distinct_view_shape_structures": len(shapes),
                    "element_offsets_are_arithmetic_progressions": block_arithmetic,
                }
            )
    else:
        identical_within = False
        offsets_arithmetic = False

    # Where the transactions differ from one another, say what differs.
    across: list[dict[str, Any]] = []
    if len(view_shapes) > 1 and invocations:
        reference = _view_shape_map(invocations[0])
        for inv in invocations:
            candidate = _view_shape_map(inv)
            for key, value in candidate.items():
                if reference.get(key) != value and not any(
                    row["pc"] == key[0] and row["slot"] == key[1] for row in across
                ):
                    across.append(
                        {
                            "pc": key[0],
                            "slot": key[1],
                            "field_values_seen": sorted(
                                {
                                    tuple(_view_shape_map(x)[key])
                                    for x in invocations
                                    if key in _view_shape_map(x)
                                }
                            ),
                        }
                    )

    # Where a view field differs between transactions, say which field and
    # whether the difference tracks the entrypoint the transaction entered at
    # rather than the loop.  A prefill transaction spans every prompt position
    # at once and a decode transaction spans one; that is a property of the
    # request, not of the loop's invocations.
    across_summary: dict[str, Any] = {}
    if across and transactions and len(invocations) % transactions == 0:
        stride = len(invocations) // transactions
        entrypoints = [
            int(row.get("entrypoint_id", -1))
            for row in (per_pass or [])
        ]
        fields_differing: set[str] = set()
        tracks = bool(entrypoints) and len(entrypoints) == transactions
        for row in across:
            key = (row["pc"], row["slot"])
            by_transaction = []
            for index in range(transactions):
                block = invocations[index * stride:(index + 1) * stride]
                values = {
                    _view_shape_map(inv).get(key) for inv in block
                }
                by_transaction.append(
                    next(iter(values)) if len(values) == 1 else None
                )
            row["value_by_transaction"] = by_transaction
            for left, right in zip(by_transaction, by_transaction[1:]):
                if left is None or right is None:
                    tracks = False
                    continue
                for name, a, b in zip(CERTIFIED_VIEW_SHAPE_FIELDS, left, right):
                    if a != b:
                        fields_differing.add(name)
            if tracks:
                for i in range(transactions):
                    for j in range(i + 1, transactions):
                        same_entry = entrypoints[i] == entrypoints[j]
                        same_value = by_transaction[i] == by_transaction[j]
                        if same_entry != same_value:
                            tracks = False
        across_summary = {
            "view_fields_that_differ": sorted(fields_differing),
            "entrypoint_id_per_transaction": entrypoints,
            "the_difference_tracks_the_entrypoint_not_the_loop": tracks,
            "why": (
                "transactions that entered at the same entrypoint resolve the "
                "same extents and transactions that entered at different ones "
                "do not, so what differs is the token span of the request -- a "
                "16-position prefill against a one-position decode -- and not "
                "the loop's invocations, which are identical within each"
                if tracks else
                "the difference does not line up with the entrypoint each "
                "transaction entered at, so it is not explained here and is "
                "left as a measured difference"
            ),
        }

    # An independent count of the same loop, from a counter the issue trace
    # does not produce: the RTL's own per-pass loop-iteration total.  The
    # program's loop setups inside and outside the body predict it exactly
    # when every inner loop runs one trip, so agreement between the two is
    # evidence for that and a disagreement would be a finding.
    iteration_check: dict[str, Any] = {"checked": False}
    if facts is not None and per_pass and per_transaction_counts_ok(per_transaction):
        inner = [
            row for row in facts.loops
            if loop["body_start"] <= row["setup_pc"] <= loop["body_end"]
            and row["setup_pc"] != loop["setup_pc"]
        ]
        outside = [
            row for row in facts.loops
            if not (loop["body_start"] <= row["setup_pc"] <= loop["body_end"])
            and row["setup_pc"] != loop["setup_pc"]
        ]
        measured_counts = sorted(
            {int(row["loop_iterations"]) for row in per_pass
             if isinstance(row.get("loop_iterations"), int)}
        )
        invocations_each = per_transaction[0]["invocations"]
        predicted = invocations_each + invocations_each * len(inner) + len(outside)
        iteration_check = {
            "checked": True,
            "loop_setups_inside_the_body": len(inner),
            "loop_setups_outside_the_body": len(outside),
            "invocations_measured_per_transaction": invocations_each,
            "predicted_loop_iterations_per_transaction": predicted,
            "measured_loop_iterations_per_transaction": measured_counts,
            "agrees": measured_counts == [predicted],
            "assumption": (
                "every loop other than the layer loop runs exactly one trip in "
                "these transactions. The agreement of the two counters is the "
                "evidence for it; a disagreement would be reported here rather "
                "than absorbed"
            ),
            "why_it_matters": (
                "the invocation count above is read from the issue trace. This "
                "reads the same loop from the sequencer's own loop-iteration "
                "counter, which the trace does not produce, so the two are "
                "independent measurements of one thing"
            ),
        }

    per_transaction_counts = sorted({row["invocations"] for row in per_transaction})
    matches = (
        len(per_transaction_counts) == 1
        and per_transaction_counts[0] == layers["layers"]
        and loop["max_iterations"] == layers["layers"]
    )
    return {
        "invocations_measured": len(invocations),
        "transactions_measured": transactions,
        "invocations_per_transaction": per_transaction_counts,
        "operators_per_invocation": lengths,
        "model_layers": layers["layers"],
        "model_layers_source": layers,
        "loop_declared_max_iterations": loop["max_iterations"],
        "invocation_count_matches_model_layers": bool(matches),
        "structurally_identical": bool(
            identical_within
            and offsets_arithmetic
            and len(issue_keys) == 1
            and len(lengths) == 1
        ),
        "distinct_issue_structures_over_all_invocations": len(issue_keys),
        "distinct_view_shape_structures_over_all_invocations": len(view_shapes),
        "per_transaction": per_transaction,
        "element_offset_strides_per_layer": dict(sorted(strides.items())),
        "loop_iteration_cross_check": iteration_check,
        "view_shape_fields_that_differ_between_transactions": across,
        "view_shape_differences_between_transactions": across_summary,
        "what_structural_identity_means_here": (
            "every invocation issues the same sequence of "
            "(family, subopcode, descriptor id, program counter), and the RTL "
            "resolver produces the same "
            "(slot, descriptor id, extent, extent axis, rank) for every "
            "operand of every one of them, within each device transaction. "
            "element_offset is the field a loop is for: it is required to "
            "advance by a constant per-invocation stride and the strides are "
            "recorded above rather than described"
        ),
        "measured_from": (
            "the RTL's own issue trace, dumped by rtl/test/"
            "a3_g1e_control_harness.cpp under OT_A3_TRACE_OUT during the G1e "
            "control run, and bound to that run by its own census"
        ),
    }


def per_transaction_counts_ok(per_transaction: list[dict[str, Any]]) -> bool:
    """True when every transaction ran the same number of invocations."""
    counts = {row["invocations"] for row in per_transaction}
    return len(counts) == 1


def _view_shape_map(inv: list[dict[str, Any]]) -> dict[tuple[int, int], tuple[int, ...]]:
    out: dict[tuple[int, int], tuple[int, ...]] = {}
    for issue in inv:
        for view in issue["views"]:
            out[(int(issue["pc"]), int(view["slot"]))] = tuple(
                int(view[f]) for f in CERTIFIED_VIEW_SHAPE_FIELDS
            )
    return out


def boundary_address_identity(
    issues: list[dict[str, Any]],
    loop: dict[str, Any],
    facts: "ProgramFacts",
    transactions: int,
) -> dict[str, Any]:
    """Does the RTL resolve invocation N+1's operand to what N wrote?

    Measured from the same certified trace: for every layer boundary, the
    address the RTL's own resolver produced for the consumer's operand is
    compared with the address it produced for the producer's output, over the
    object the two share.  This is *address* identity and nothing more.  In
    that run every engine result was injected at the engine boundary, so no
    value flowed; what this establishes is that the loop's view resolution
    composes across the back edge, which is a different and weaker claim than
    the RTL-to-RTL data handoff G1c asks for -- and it is recorded under its
    own name so it can never stand in for it.
    """
    invocations = segment_invocations(issues, loop)
    producer_pc = loop["issue_pcs"][-1]
    consumer_pc = loop["issue_pcs"][0]
    object_of = {
        slot["view_descriptor_id"]: slot["object_id"]
        for site in facts.issue_sites.values()
        for slot in site["slots"]
    }
    produced = {
        slot["object_id"]
        for slot in facts.issue_sites[producer_pc]["slots"]
        if slot["slot"].startswith("output")
    }
    consumed = {
        slot["object_id"]
        for slot in facts.issue_sites[consumer_pc]["slots"]
        if slot["slot"].startswith("input")
    }
    shared = produced & consumed

    def addresses(issue: dict[str, Any]) -> list[tuple[int, ...]]:
        return sorted(
            (
                int(object_of.get(int(view["descriptor_id"]), -1)),
                int(view["element_offset"]),
                int(view["extent"]),
                int(view["extent_axis"]),
                int(view["rank"]),
            )
            for view in issue["views"]
            if object_of.get(int(view["descriptor_id"])) in shared
        )

    checked = 0
    matched = 0
    examples: list[dict[str, Any]] = []
    if transactions and invocations and len(invocations) % transactions == 0:
        stride = len(invocations) // transactions
        for index in range(transactions):
            block = invocations[index * stride:(index + 1) * stride]
            for position in range(len(block) - 1):
                producer = next(
                    (i for i in block[position] if int(i["pc"]) == producer_pc), None
                )
                consumer = next(
                    (i for i in block[position + 1] if int(i["pc"]) == consumer_pc),
                    None,
                )
                if producer is None or consumer is None:
                    continue
                checked += 1
                left, right = addresses(producer), addresses(consumer)
                if left and left == right:
                    matched += 1
                elif len(examples) < 3:
                    examples.append(
                        {
                            "transaction_index": index,
                            "from_invocation": position,
                            "producer_addresses": left,
                            "consumer_addresses": right,
                        }
                    )
    return {
        "shared_objects": sorted(shared),
        "producer_pc": producer_pc,
        "consumer_pc": consumer_pc,
        "boundaries_checked": checked,
        "boundaries_where_the_address_matched": matched,
        "holds": bool(checked > 0 and matched == checked and shared),
        "disagreements": examples,
        "what_it_is": (
            "the RTL resolver's own (object, element offset, extent, extent "
            "axis, rank) for the consumer of each layer boundary, compared "
            "with the same for the producer of the invocation before it"
        ),
        "what_it_is_not": (
            "an RTL-to-RTL data handoff. The run this is measured in supplies "
            "every engine result at the engine boundary, so no value produced "
            "by one layer was consumed by the next. G1c's handoff fields are "
            "not derived from this and cannot be"
        ),
    }


# --------------------------------------------------------------------------
# The handoff, measured from the integrated campaign.
# --------------------------------------------------------------------------
def handoff_evidence(
    campaign: dict[str, Any],
    facts: ProgramFacts,
    loop: dict[str, Any],
    vector_case: dict[str, Any],
    case_index: int,
    rerun: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """How many layer boundaries the integrated RTL actually crossed."""
    observed = next(
        (
            row for row in (campaign.get("observed_cases") or [])
            if int(row.get("index", -1)) == case_index
        ),
        None,
    )
    expected = next(
        (
            row for row in (campaign.get("expected_cases") or [])
            if int(row.get("index", -1)) == case_index
        ),
        None,
    )
    measured = observed if observed is not None else expected
    source = (
        "the campaign's observed case counters"
        if observed is not None
        else "the campaign's expected case counters, which the run's own "
             "checker requires the observed counters to equal"
    )
    fetched = int(measured.get("fetched", -1)) if measured else -1
    fault_pc = int(measured.get("fault", -1)) if measured else -1
    trap_class = int(measured.get("trap", -1)) if measured else -1
    back_edge = int(loop["back_edge_pc"])

    # How many invocations of the body completed.  Each completion retires the
    # loop's back edge, so a harness that counts back-edge retirals answers
    # this directly; that counter is read when the run carries it.  Without it
    # the answer is derivable only in one direction: a run whose fetch never
    # reached the back edge completed none, definitively.  Anything else is
    # undetermined by this evidence and is written null rather than guessed.
    declared_retirals = measured.get("back_edge_retirals") if measured else None
    if isinstance(declared_retirals, int):
        completed = int(declared_retirals)
        completed_source = "the run's own back-edge retiral counter"
    elif 0 <= fetched <= back_edge:
        completed = 0
        completed_source = (
            "derived: the run's fetch never reached the back edge, so no "
            "invocation of the body completed"
        )
    else:
        completed = None
        completed_source = (
            "not derivable from this run: it fetched past the back edge and "
            "the harness prints no back-edge retiral counter, so how many "
            "invocations completed is unknown -- which is written null, not "
            "assumed"
        )
    boundary_crossings = None if completed is None else max(0, completed - 1)

    # Words compared across the boundary, and the mismatches among them.  Both
    # come from counters the run would have to print; neither is inferred.
    compared_words = measured.get("boundary_compared_words") if measured else None
    if not isinstance(compared_words, int):
        compared_words = 0 if boundary_crossings == 0 else None
    mismatched = measured.get("boundary_mismatched_words") if measured else None
    if not isinstance(mismatched, int) or not isinstance(compared_words, int) \
            or compared_words <= 0:
        mismatched = None
    injected = measured.get("boundary_injected_operands") if measured else None
    if not isinstance(injected, int) or not boundary_crossings:
        golden_injected = None
    else:
        golden_injected = bool(injected)

    rtl_to_rtl = bool(
        isinstance(boundary_crossings, int)
        and boundary_crossings >= 1
        and isinstance(compared_words, int)
        and compared_words > 0
        and mismatched == 0
        and golden_injected is False
    )

    # The object the boundary would hand over, from the program itself.
    first_pc = loop["issue_pcs"][0]
    last_pc = loop["issue_pcs"][-1]
    produced = [
        s["object_id"] for s in facts.issue_sites[last_pc]["slots"]
        if s["slot"].startswith("output")
    ]
    consumed = [
        s["object_id"] for s in facts.issue_sites[first_pc]["slots"]
        if s["slot"].startswith("input")
    ]
    shared = sorted(set(produced) & set(consumed))

    blocked_at = None
    if fault_pc in facts.issue_sites:
        site = facts.issue_sites[fault_pc]
        blocked_at = {
            "pc": fault_pc,
            "mnemonic": site["mnemonic"],
            "operator_descriptor_id": site["operator_descriptor_id"],
            "trap_class": trap_class,
            "is_inside_the_layer_body": bool(
                loop["body_start"] <= fault_pc <= loop["body_end"]
            ),
            "invocation_it_stopped_in": (
                None if completed is None else completed + 1
            ),
        }

    return {
        "rtl_to_rtl": rtl_to_rtl,
        "golden_injected_between_layers": golden_injected,
        "mismatched_words": mismatched,
        "compared_words_across_the_layer_boundary": compared_words,
        "layer_boundary_crossings_observed": boundary_crossings,
        "completed_layer_invocations": completed,
        "completed_layer_invocations_source": completed_source,
        "consecutive_layers_executed": (
            None if completed is None else min(completed, 2)
        ),
        "consecutive_layers_required": 2,
        "what_would_turn_this_green": [
            "a run whose back edge retires at least twice, so a second "
            "invocation of the body consumes what the first produced",
            "a boundary_compared_words counter above zero and a "
            "boundary_mismatched_words of zero among them",
            "a boundary_injected_operands of zero, so nothing crossing the "
            "boundary came from the golden model",
        ],
        "measured": {
            "source": source,
            "instructions_fetched": fetched,
            "fault_pc": fault_pc,
            "trap_class": trap_class,
            "loop_back_edge_pc": back_edge,
            "why": (
                f"the integrated run fetched {fetched} instruction(s) of one "
                f"pass and faulted at PC {fault_pc}; the layer loop's back "
                f"edge is PC {back_edge}. "
            ) + completed_source,
        },
        "blocked_at": blocked_at,
        "boundary_object_the_program_declares": {
            "producer_pc": last_pc,
            "producer_mnemonic": facts.issue_sites[last_pc]["mnemonic"],
            "producer_output_objects": sorted(set(produced)),
            "consumer_pc": first_pc,
            "consumer_mnemonic": facts.issue_sites[first_pc]["mnemonic"],
            "consumer_input_objects": sorted(set(consumed)),
            "objects_in_common": shared,
            "derived_not_measured": True,
            "note": (
                "read from the two operators' own TENSOR_VIEW descriptors: "
                "invocation N's last operator writes these objects and "
                "invocation N+1's first operator reads them, so the handoff "
                "the loop would make is through device memory. Nothing here "
                "says the RTL performed it -- it did not"
            ),
        },
        "why_null": (
            "mismatched_words and golden_injected_between_layers are reported "
            "null, not 0 and not false, because zero words were compared "
            "across zero layer boundaries. A count of zero mismatches over "
            "zero comparisons, or 'no golden value crossed' over no crossing, "
            "is a vacuous truth over an empty set; this ladder's first rule "
            "is that absence of evidence is a failure and never a pass"
        ),
        "evidence_currency": {
            "retained_campaign_is_usable": bool(campaign.get("usable")),
            "why_not": campaign.get("why_unusable"),
            "fields_the_handoff_reads": [
                "expected_cases/observed_cases: fetched, fault and trap class "
                "for this lowering's case",
                "operator_admission: which families the bridge trapped",
            ],
            "an_independent_run_at_this_commit_agrees": (
                None if rerun is None
                else bool(rerun.get("agrees_on_every_compared_field"))
            ),
            "what_that_means": (
                "the retained integrated campaign is what this repository "
                "holds, and it is no longer source-current: sources it bound "
                "have moved since it ran. That is a second reason this half "
                "of the rung is red, independent of the boundary at which the "
                "vehicle fails closed. An independent execution at this "
                "commit, in a pinned clean worktree, is recorded under "
                "rerun_not_retained; where it agrees on every compared field "
                "the drift did not move the measurement, and where it did not "
                "that disagreement would itself be the finding"
                if not campaign.get("usable") else
                "the retained integrated campaign is source-current and every "
                "field the handoff reads comes from it"
            ),
        },
        "integrated_campaign": {
            key: campaign.get(key)
            for key in (
                "artifact",
                "artifact_sha256",
                "status",
                "evidence_class",
                "declared_git",
                "bound_source_count",
                "drifted_source_count",
                "drifted_sources",
                "vector_set_path",
                "vector_set_sha256_declared",
                "vector_set_sha256_on_disk",
                "vector_set_is_current",
                "simulated_cycles",
                "integrated_simulator_checks",
                "operator_admission",
                "pass_marker",
                "usable",
                "why_unusable",
                "staged_matmul_weight",
            )
        },
        "case": {
            "index": case_index,
            "name": vector_case.get("name"),
            "declared_boundary_pc": int(
                (vector_case.get("first_unsupported") or {}).get("pc", -1)
            ),
            "observed": measured,
        },
    }


def integrated_rate(campaign_body: dict[str, Any]) -> dict[str, Any]:
    """The integrated vehicle's measured MAC rate, from its own two numbers.

    Not a constant and not the plan's figure: the multiply-accumulates the run
    executed, divided by the seconds its own MEASURE line says the simulation
    took.  Both come from the same run, so the quotient is a measurement of
    that run and nothing else.
    """
    macs = campaign_body.get("matmul_mac_count")
    seconds = None
    for case in campaign_body.get("cases") or []:
        found = _g1b.measure_line(case.get("run_log", ""))
        if found and found.get("sim_wall_s"):
            seconds = float(found["sim_wall_s"])
    if not isinstance(macs, int) or macs <= 0 or not seconds:
        return {
            "measured": False,
            "why_not": (
                "the integrated campaign states no positive MAC count or no "
                "simulation wall time, so no rate can be measured from it"
            ),
        }
    return {
        "measured": True,
        "mac_count": int(macs),
        "simulation_wall_seconds": seconds,
        # NOT rounded.  This field is checked against the quotient of the
        # run's own two numbers at rel=1e-6, and at this magnitude rounding
        # to one decimal can miss that band by more than it allows -- the
        # check passed only when the rounding happened to fall the right
        # way.  The artifact carries the quotient; presentation rounds.
        "macs_per_second": macs / seconds,
        "source": (
            "results/rtl/abi3_shipped_prefix_campaign.json: its own "
            "matmul_mac_count and the sim_wall_s of its MEASURE line"
        ),
        "caveat": (
            "this is the rate THAT run measured, on a machine other work was "
            "sharing. Another run of the same vehicle on a quieter box "
            "measures a higher one; the figure is reported with the run it "
            "came from rather than as a property of the design"
        ),
    }


def layer_arithmetic(facts: "ProgramFacts", loop: dict[str, Any]) -> dict[str, Any]:
    """The layer body's multiply-accumulates, from each MATMUL's weight view."""
    per_matmul = []
    total = 0
    for pc in loop["issue_pcs"]:
        site = facts.issue_sites[pc]
        if site["mnemonic"] != "TENSOR.MATMUL":
            continue
        weight = next(
            (s for s in site["slots"] if s["slot"] == "input_view_1"), None
        )
        if weight is None or len(weight["declared_dims"]) != 2:
            raise SystemExit(f"MATMUL at PC {pc} has no rank-2 weight view")
        macs = weight["declared_dims"][0] * weight["declared_dims"][1]
        total += macs
        per_matmul.append(
            {"pc": pc, "weight_shape": weight["declared_dims"], "mac_count": macs}
        )
    return {
        "mac_count": total,
        "per_matmul": per_matmul,
        "note": (
            "the projections of one invocation of the layer body, each from "
            "its own resolved weight view. Attention's own arithmetic is not "
            "in this figure, matching the cost the plan states for a layer"
        ),
    }


def _establishes(records: list[dict[str, Any]]) -> list[str]:
    """What the rung established, computed from the records, never declared."""
    out: list[str] = []
    loops = [record["loop"] for record in records]
    if loops and all(row.get("invocation_count_matches_model_layers") for row in loops):
        layers = sorted({int(row["model_layers"]) for row in loops})
        counts = sorted({int(row["invocations_measured"]) for row in loops})
        out.append(
            f"the design's own loop control issues exactly {layers} "
            "invocations of the layer body per device transaction -- the "
            "model's layer count from the certified Kernel IR and the "
            f"checkpoint's config.json -- measured as {counts} invocations in "
            "the RTL's own certified issue trace, on each declared storage "
            "class"
        )
    if loops and all(row.get("structurally_identical") for row in loops):
        out.append(
            "every one of those invocations is structurally identical: the "
            "same sequence of (family, subopcode, descriptor id, program "
            "counter), the same resolved (slot, descriptor id, extent, extent "
            "axis, rank) for every operand, and an element offset that "
            "advances by a constant per-invocation stride"
        )
    identities = [
        record["handoff"]["address_identity_across_the_layer_boundary"]
        for record in records
    ]
    if identities and all(row.get("holds") for row in identities):
        checked = sorted({int(row["boundaries_checked"]) for row in identities})
        out.append(
            f"at all {checked} layer boundaries the RTL resolver produced, for "
            "invocation N+1's consumer, the same object, element offset and "
            "extent it produced for invocation N's producer -- address "
            "identity, not a data handoff"
        )
    return out


def rerun_agreement(path: Path | None, campaign: dict[str, Any]) -> dict[str, Any] | None:
    """An independent run of the same integrated campaign, recorded not relied on.

    It establishes nothing on its own: every field of the rung is computed
    from the campaign artifact the repository holds, because a number taken
    from a file the tree does not carry cannot be reproduced from the sources
    this artifact binds.  What it is good for is agreement.  The retained
    campaign was recorded before three of the sources it binds moved, so a
    reader cannot otherwise tell whether that drift changed the measurement;
    an independent run at this commit that lands on the same counters says it
    did not, and a disagreement would be the finding.
    """
    if path is None:
        return None
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"--rerun {path} does not exist")
    body = json.loads(path.read_text())

    def compare(field: str) -> dict[str, Any]:
        rerun = body.get(field)
        retained = campaign.get(field)
        return {"rerun": rerun, "retained": retained, "agree": rerun == retained}

    fields = {
        "status": compare("status"),
        "simulated_cycles": compare("simulated_cycles"),
        "result_word_count": compare("result_word_count"),
        "real_engine_launch_count": compare("real_engine_launch_count"),
        "capability_fault_count": compare("capability_fault_count"),
        "expected_cases": {
            "rerun": body.get("expected_cases"),
            "retained": campaign.get("expected_cases"),
            "agree": body.get("expected_cases") == campaign.get("expected_cases"),
        },
        "operator_admission": {
            "rerun": body.get("operator_admission"),
            "retained": campaign.get("operator_admission"),
            "agree": body.get("operator_admission") == campaign.get("operator_admission"),
        },
    }
    return {
        "what_it_is": (
            "an independent execution of the same integrated campaign, run "
            "for this rung at this commit in a separately pinned worktree"
        ),
        "why_not_retained": (
            "it is not a file of this repository, so nothing in this rung is "
            "computed from it; it is recorded as agreement with the campaign "
            "the tree does hold"
        ),
        "artifact_sha256": sha256_file(path),
        "git": body.get("git"),
        "vector_set_sha256": _g1b._dig(body, "vector_set.sha256"),
        "agreement": fields,
        "agrees_on_every_compared_field": all(row["agree"] for row in fields.values()),
    }


# --------------------------------------------------------------------------
def build(
    output: Path,
    control_artifact: Path,
    trace_root: Path,
    campaign_path: Path | None,
    vectors_path: Path | None,
    checkpoint: Path | None,
    rerun_path: Path | None = None,
) -> dict[str, Any]:
    vectors = json.loads(
        (_g1b.PREFIX_VECTORS if vectors_path is None else Path(vectors_path)).read_text()
    )
    campaign_body = json.loads(
        (ROOT / _g1b.INTEGRATED_CAMPAIGN).read_text()
    ) if (ROOT / _g1b.INTEGRATED_CAMPAIGN).is_file() else {}
    campaign = _g1b.integrated_evidence(campaign_path, vectors_path)
    rate = integrated_rate(campaign_body)
    rerun = rerun_agreement(rerun_path, json.loads(
        (ROOT / _g1b.INTEGRATED_CAMPAIGN).read_text()
    ) if (ROOT / _g1b.INTEGRATED_CAMPAIGN).is_file() else {})
    git = git_state()

    records = []
    for storage_class, (deployment_key, directory) in STORAGE_CLASSES.items():
        vector_case = next(
            c for c in vectors["cases"] if c["deployment"] == deployment_key
        )
        case_index = vectors["cases"].index(vector_case)
        kernels = _g1b.kernel_index(vector_case)
        facts = ProgramFacts(ROOT / directory)
        loop = layer_loop(facts, kernels)
        layers = model_layer_count(kernels, checkpoint)
        control = control_run_evidence(control_artifact, trace_root, storage_class)
        if control.get("deployment_sha256") not in (None, facts.deployment_sha256):
            control["usable"] = False
            control["why_unusable"] = (
                (control.get("why_unusable") or "")
                + f"; it bound deployment {control['deployment_sha256']} and the "
                f"deployment on disk is {facts.deployment_sha256}"
            ).lstrip("; ")

        address_identity: dict[str, Any] | None = None
        if control.get("usable"):
            transactions = int(control["passes"]["executed"])
            loop_record = loop_property(
                control["issues"],
                loop,
                layers,
                transactions,
                control["passes"].get("per_pass"),
                facts,
            )
            address_identity = boundary_address_identity(
                control["issues"], loop, facts, transactions
            )
        else:
            loop_record = {
                "invocations_measured": None,
                "transactions_measured": None,
                "model_layers": layers["layers"],
                "model_layers_source": layers,
                "loop_declared_max_iterations": loop["max_iterations"],
                "invocation_count_matches_model_layers": False,
                "structurally_identical": False,
                "why_not_measured": control.get("why_unusable"),
                "measured_from": None,
            }
        control.pop("issues", None)

        handoff = handoff_evidence(
            campaign, facts, loop, vector_case, case_index, rerun
        )
        arithmetic = layer_arithmetic(facts, loop)
        outstanding = int(arithmetic["mac_count"]) * 2
        handoff["what_the_missing_half_would_cost"] = {
            "consecutive_layers_required": 2,
            "mac_count_per_invocation": arithmetic["mac_count"],
            "mac_count_for_two_consecutive_invocations": outstanding,
            "per_matmul": arithmetic["per_matmul"],
            "measured_integrated_rate": rate,
            "seconds": (
                round(outstanding / rate["macs_per_second"], 1)
                if rate.get("measured") else None
            ),
            "hours": (
                round(outstanding / rate["macs_per_second"] / 3600.0, 2)
                if rate.get("measured") else None
            ),
            "note": (
                "derived: the layer body's own multiply-accumulates, twice, "
                "at the rate the integrated vehicle itself measured. It is "
                "what the handoff half costs once the eleven operators the "
                "bridge traps can be issued; it is not what this rung cost, "
                "which is the control run above"
            ),
        }
        handoff["address_identity_across_the_layer_boundary"] = (
            address_identity
            if address_identity is not None
            else {
                "holds": False,
                "why_not_measured": control.get("why_unusable"),
            }
        )

        records.append(
            {
                "storage_class": storage_class,
                "workload_id": WORKLOAD,
                "deployment": {
                    "key": deployment_key,
                    "directory": directory,
                    "deployment_sha256": facts.deployment_sha256,
                    "instruction_count": len(facts.instructions),
                },
                "execution": {
                    "simulator": control.get("simulator"),
                    "simulator_version": control.get("simulator_version"),
                    "simulated_cycles": control.get("simulated_cycles"),
                    "simulated_cycles_scope": (
                        "the control-plane run in which this rung's loop "
                        "property was measured -- every device transaction of "
                        "the governed workload through the design's own "
                        "control plane. The integrated run that establishes "
                        "(or here, fails to establish) the handoff reports its "
                        "own cycles under handoff.integrated_campaign"
                    ),
                    "evidence_class": control.get("evidence_class"),
                    "vehicle": control.get("vehicle"),
                    "control_plane": control.get("control_plane"),
                    "control_plane_run": control,
                },
                "loop": loop_record,
                "layer_loop": {
                    key: loop[key]
                    for key in (
                        "loop_control_descriptor_id",
                        "setup_pc",
                        "body_start",
                        "body_end",
                        "back_edge_pc",
                        "max_iterations",
                        "bound_selector_kind",
                        "layer_prefix",
                        "issue_pcs",
                        "kernel_ids",
                        "identified_by",
                    )
                },
                "handoff": handoff,
                "git": git,
            }
        )

    body = {
        "schema": SCHEMA,
        "gate": "G1c",
        "workload_id": WORKLOAD,
        "generated_by": "tools/build_abi3_g1c_composition.py",
        "generated_by_sha256": sha256_file(Path(__file__)),
        "derived_mechanically": True,
        "what_this_rung_is": (
            "the inductive step of the ladder. G1b is the base case -- one "
            "layer. This rung is layer N to layer N+1 with an RTL-to-RTL "
            "handoff, plus the loop property that closes the induction over "
            "every layer of the model"
        ),
        "establishes": _establishes(records),
        "does_not_establish": [
            "the handoff: see handoff.rtl_to_rtl and its measurement. Nothing "
            "in this artifact says a value produced by one layer was consumed "
            "by the next in RTL unless that field is true",
            "any engine arithmetic: the run the loop property is measured "
            "from supplies every engine result at the engine boundary, which "
            "is rung G1e's scope, not this one's",
            "that a structurally identical invocation computes the right "
            "words -- that is G1a per operator and G1b per layer",
        ],
        "records": records,
        "rerun_not_retained": rerun,
        "git": git,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--control-run",
        type=Path,
        required=True,
        help="the G1e control-end-to-end artifact of the run that dumped the "
             "RTL issue trace",
    )
    parser.add_argument(
        "--trace-root",
        type=Path,
        required=True,
        help="that run's --build-root, holding build-<store>/rtl_issue_trace.txt",
    )
    parser.add_argument("--campaign", type=Path, default=None)
    parser.add_argument("--vectors", type=Path, default=None)
    parser.add_argument(
        "--rerun",
        type=Path,
        default=None,
        help="an independent run of the integrated campaign, recorded for "
             "agreement and relied on for nothing",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="the checkpoint snapshot whose config.json cross-checks the "
             "model's layer count",
    )
    args = parser.parse_args()
    body = build(
        args.output,
        args.control_run,
        args.trace_root,
        args.campaign,
        args.vectors,
        args.checkpoint,
        args.rerun,
    )
    for record in body["records"]:
        loop = record["loop"]
        handoff = record["handoff"]
        print(
            f"{record['storage_class']}: loop invocations="
            f"{loop['invocations_measured']} layers={loop['model_layers']} "
            f"count_matches={loop['invocation_count_matches_model_layers']} "
            f"structurally_identical={loop['structurally_identical']} | "
            f"handoff rtl_to_rtl={handoff['rtl_to_rtl']} "
            f"crossings={handoff['layer_boundary_crossings_observed']} "
            f"mismatched_words={handoff['mismatched_words']}"
        )
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
