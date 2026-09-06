#!/usr/bin/env python3
"""Derive rung G1b's artifact: layer closure over one complete Qwen3-8B layer.

G1b's statement (configs/gates/redesign_gates.json) is that *one complete
transformer layer* executes end to end in the integrated RTL, bit-exact
against the golden model at **every intermediate**, with no golden value
injected inside the layer.  This tool derives that artifact; it never asserts
it, and it has no way of writing a number the evidence does not carry.

Where each field comes from
---------------------------
**The layer itself is not a list typed in here.**  It is the set of engine
issues the governed decode program makes whose OPERATOR descriptor names a
certified Kernel IR kernel whose ``kernel_id`` lies inside one layer
(``layer.0.``).  The kernel index comes from the descriptor's own
``source_kernel_id``; the Kernel IR is the one the shipped vector set's
``descriptor_derivation`` certifies by path and SHA-256, re-checked here
against the file on disk.  Both Qwen lowerings are resolved independently:
their descriptor IDs differ at every governed PC, so nothing measured on one
is transferred to the other.

**What actually ran** comes from the integrated shipped-prefix campaign
artifact -- the only vehicle in this repository that runs the real compiled
program through the real RTL control plane with the engine array computing.
The campaign is re-validated here before it is allowed to establish anything:
its status must be pass, every source and vector digest it bound must still
match the tree (recomputed, not trusted), the vector set it names must be the
one on disk, and its run log must carry the harness's own MEASURE line.  A
campaign that fails any of those covers no operator at all -- absence of
evidence is a failure, not an unknown.

**Every intermediate, not only the layer output.**  The harness compares every
word the RTL writes into result memory against the golden WRITE STREAM
``p3_writes.hex`` -- address and value, as each write commits -- and then
compares the retained image against ``p3_expect.hex`` per case and once over
the whole run.  The write stream is the half that survives a rewrite: results
are placed by object, so an intermediate a later operator overwrites is no
longer in the image, and an image comparison alone would silently stop
checking it.  So an operator that ran has had *its own* output words compared,
not merely the last operator's.  This tool records the comparison per operator, so
"the layer output matched" can never stand in for "every intermediate
matched" -- the failure that produced this project's 99.17 % MFU claim from
two cancelling unit errors.

**The handoff is computed, not claimed.**  The vehicle places every operand
and every result of every family at its own object's base plus the resolved
element offset.  This tool replays that placement over the operations the
vector set declares and asks, for each operand, whether the OBJECT it names
was last written -- before this operator -- by an operator of this run.  That
is an RTL-to-RTL handoff; anything else is a staged input, and is listed as
one.  The older test compared addresses, and it stops being sound the moment a
buffer is written twice: both writes are at one address, so an operand would
match the wrong one.  This span rewrites three of its buffers.

**Nothing inside is injected** is read from the harness's measured
``injected_results`` count and from which PASS marker the run printed.  If the
log carries neither, the count is reported absent -- never zero.

**The layer's arithmetic is derived too**, from the weight view of each of its
MATMULs, and comes to 192,937,984 multiply-accumulates -- the figure G1b's own
note states.  Agreement is the check that the layer being closed is the layer
that was costed; a test pins it in both directions.

**What is missing is counted, not characterised.**  Every operand of every
operator in the layer is attributed to the engine-placement role the bridge
draws its base from, and the distinct objects per role -- and their union,
because one table serves them all -- are compared with the depth a RUN has
been measured to resolve.  Not with the port list: counting ports is counting
source text, and widening a port list must never move a gate field.  The
measured depth is the largest number of distinct objects a passing campaign
case bound into the table and resolved, on a case whose every result word was
compared against golden by address as well as by value.

What this tool refuses to do
----------------------------
It will not report ``mismatched_words: 0`` over zero comparisons, will not
count an operator the campaign did not run, and will not call the layer
complete because the operators that did run all matched.  ``operator_count``
is the count of the layer's operators that executed in the integrated RTL and
had every result word compared against golden; ``complete`` is true only when
that equals the layer's own operator count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import NO_ID  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import Instruction  # noqa: E402

import importlib.util  # noqa: E402


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_admission = _module("_g1b_adm", "tools/build_a3_operator_admission_vectors.py")
_scatter = _module("_g1b_sc", "tools/build_a3_qwen_kv_scatter_vectors.py")

SCHEMA = "opentallas.rtl.g1b_layer_closure.v1"
WORKLOAD = "TA-QW-EOS-1"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_g1b_layer_closure.json"

DEPLOYMENT_DIR = ROOT / "testdata/compiler/abi3_deployment"
DEPLOYMENT_MANIFEST = DEPLOYMENT_DIR / "abi3_deployment_rtl_vectors.json"
PREFIX_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
PREFIX_VECTORS = PREFIX_DIR / "abi3_shipped_prefix_vectors.json"
INTEGRATED_CAMPAIGN = "results/rtl/abi3_shipped_prefix_campaign.json"
BRIDGE = ROOT / "rtl/abi3/ot_a3_engine_issue_bridge.sv"
INTEGRATED_TOP = ROOT / "rtl/test/a3_shipped_prefix_top.sv"

# The two storage classes G1b requires, and the deployment each one names.
STORAGE_CLASSES = {
    "rom": "qwen3-8b-rom-single-chip",
    "hbm": "qwen3-8b-hbm-single-chip",
}

# The layer this rung closes.  A prefix of a Kernel IR ``kernel_id``, not a
# list of program counters: the PCs are a property of one lowering and this
# has to hold for both.
LAYER_PREFIX = "layer.0."

ISSUE_STRIDE = 3
SLOT_FIELDS = (
    "input_view_0",
    "input_view_1",
    "input_view_2",
    "input_view_3",
    "output_view_0",
    "output_view_1",
)
MEASURE_RE = re.compile(r"^MEASURE (?P<body>.*)$", re.MULTILINE)
ENGINE_MARKER = "PASS: ABI3 shipped-prefix engine integration"
INJECTION_MARKER = "PASS: ABI3 shipped-prefix G1e control-plane injection"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_hex(path: Path) -> list[int]:
    return [int(token, 16) for token in path.read_text().split()]


def _dig(body: Any, dotted: str) -> Any:
    node = body
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


# --------------------------------------------------------------------------
# The layer, walked out of the retained issue stream and the certified IR.
# --------------------------------------------------------------------------
def kernel_index(vector_case: dict[str, Any]) -> dict[str, Any]:
    """The certified Kernel IR this lowering came from, re-checked on disk."""
    derivation = vector_case.get("descriptor_derivation") or {}
    relative = derivation.get("kernel_ir")
    declared = derivation.get("kernel_ir_sha256")
    if not relative or not declared:
        raise SystemExit(
            f"{vector_case.get('name')}: the vector set does not certify a "
            "Kernel IR, so the layer cannot be named from the graph and this "
            "rung has no definition of what one layer is"
        )
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(
            f"{relative} is absent; the certified Kernel IR is what names the "
            "layer, and a layer this tool guessed at would not be a layer"
        )
    observed = sha256_file(path)
    if observed != declared:
        raise SystemExit(
            f"{relative} is {observed}, the vector set certifies {declared}: "
            "the graph has moved under the lowering"
        )
    body = json.loads(path.read_text())
    return {
        "path": relative,
        "sha256": observed,
        "graph_id": body.get("graph_id"),
        "model_id": body.get("model_id"),
        "kernels": {int(k["index"]): str(k["kernel_id"]) for k in body["kernels"]},
        "kinds": {int(k["index"]): str(k.get("kind")) for k in body["kernels"]},
        "contracts": {
            int(k["index"]): str(k.get("numeric_contract")) for k in body["kernels"]
        },
    }


def issued_operators(
    manifest: dict[str, Any],
    images: dict[str, list[int]],
    deployment_key: str,
) -> list[dict[str, Any]]:
    """Every engine issue the decode entrypoint makes, in program order.

    Taken from the retained issue stream -- ``runtime.sim.device.Device``'s own
    trace -- rather than from a re-walk of the program, so this is the stream
    the RTL vehicle was built against.
    """
    case = next(
        c for c in manifest["cases"]
        if c["deployment"] == deployment_key and c["request"] == "decode"
    )
    deployment = next(
        d for d in manifest["deployments"] if d["key"] == deployment_key
    )
    descriptor_base, program_base = _scatter.deployment_bases(manifest)[deployment_key]
    table, _ = _admission.build_table(
        images["descriptor"], descriptor_base, int(deployment["descriptor_count"])
    )
    issues = images["issue"]
    out: list[dict[str, Any]] = []
    for step in range(int(case["issue_count"])):
        at = (int(case["issue_base"]) + step) * ISSUE_STRIDE
        opcode, descriptor_id, instruction_index = issues[at:at + 3]
        operator = table.get(int(descriptor_id), ExtendedDescriptorType.OPERATOR)
        payload = operator.payload
        slots = []
        for field in SLOT_FIELDS:
            view_id = int(payload[field])
            if view_id == NO_ID:
                continue
            view = table.get(view_id, ExtendedDescriptorType.TENSOR_VIEW)
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
        mnemonic = Instruction.decode(
            images["program"][program_base + int(instruction_index)]
            .to_bytes(32, "little")
        ).mnemonic
        out.append(
            {
                "pc": int(instruction_index),
                "mnemonic": mnemonic,
                "family": (int(opcode) >> 8) & 0xFF,
                "sub": int(opcode) & 0xFF,
                "operator_descriptor_id": int(descriptor_id),
                "source_kernel_id": int(payload["source_kernel_id"]),
                "numeric_profile_id": int(payload["numeric_profile_id"]),
                "slots": slots,
            }
        )
    return out


def layer_operators(
    operators: list[dict[str, Any]], kernels: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One invocation of the layer, named by the graph rather than by PC.

    The decode program executes the layer body inside a loop, so the retained
    issue stream carries the layer's operators once per model layer -- the
    same descriptors, with the loop index steering each view's dynamic term at
    the weight for that layer.  One *invocation* of the body is one layer, and
    it is the first occurrence of each of its program counters in program
    order.  The repeat count is returned alongside so the rung records how
    many invocations the program makes rather than silently collapsing them:
    that count is G1c's loop property, not G1b's, and must not be inherited
    here.
    """
    matched = []
    for operator in operators:
        kernel_id = kernels["kernels"].get(operator["source_kernel_id"])
        if kernel_id is None:
            raise SystemExit(
                f"PC {operator['pc']}: operator descriptor "
                f"{operator['operator_descriptor_id']} names kernel index "
                f"{operator['source_kernel_id']}, which the certified Kernel "
                "IR does not contain"
            )
        if not kernel_id.startswith(LAYER_PREFIX):
            continue
        entry = dict(operator)
        entry["kernel_id"] = kernel_id
        entry["kernel_kind"] = kernels["kinds"].get(operator["source_kernel_id"])
        entry["numeric_contract"] = kernels["contracts"].get(
            operator["source_kernel_id"]
        )
        matched.append(entry)
    first: dict[int, dict[str, Any]] = {}
    occurrences: dict[int, int] = {}
    for entry in matched:
        occurrences[entry["pc"]] = occurrences.get(entry["pc"], 0) + 1
        first.setdefault(entry["pc"], entry)
    body = [first[pc] for pc in sorted(first)]
    counts = sorted(set(occurrences.values()))
    if len(counts) != 1:
        raise SystemExit(
            "the layer body's program counters do not all issue the same "
            f"number of times ({occurrences}); one invocation of the body is "
            "not well defined and this rung will not guess at one"
        )
    return body, {
        "operators_per_invocation": len(body),
        "invocations_in_the_program": counts[0],
        "issued_instances_in_the_program": len(matched),
        "note": (
            "the program issues this layer body once per model layer through "
            "one loop; this rung establishes ONE invocation. That the loop "
            "issues the model's layer count of structurally identical "
            "invocations is rung G1c and is not claimed here."
        ),
    }


# --------------------------------------------------------------------------
# Evidence: the integrated campaign, re-validated against the tree as it is.
# --------------------------------------------------------------------------
def _bound_pairs(body: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("path"), str) and isinstance(
                node.get("sha256"), str
            ):
                pairs.append((node["path"], node["sha256"]))
                return
            for key, value in node.items():
                if isinstance(value, str) and len(value) == 64 and "/" in key:
                    pairs.append((key, value))
                elif (
                    isinstance(value, dict)
                    and isinstance(value.get("sha256"), str)
                    and "/" in key
                    and "path" not in value
                ):
                    pairs.append((key, value["sha256"]))
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    # Only sections whose paths are repository paths.  The staged MATMUL
    # weight blob lives in the run's build directory and is never a file of
    # this tree, so treating its path as one would make every campaign look
    # drifted -- a refusal for a reason that is not true.  Its identity is
    # recorded separately instead.
    for section in ("source", "source_sha256", "sources", "vector_set",
                    "vector_sha256"):
        if section in body:
            walk(body[section])
    return pairs


def measure_line(log: str) -> dict[str, Any] | None:
    """The harness's own MEASURE line, parsed into fields."""
    match = MEASURE_RE.search(log or "")
    if match is None:
        return None
    fields: dict[str, Any] = {}
    for token in match.group("body").split():
        if "=" not in token:
            continue
        key, _, value = token.partition("=")
        try:
            fields[key] = int(value)
        except ValueError:
            try:
                fields[key] = float(value)
            except ValueError:
                fields[key] = value
    return fields


def integrated_evidence(
    path: Path | None = None, vectors_path: Path | None = None
) -> dict[str, Any]:
    """The integrated campaign, and every reason it might not be usable."""
    path = ROOT / INTEGRATED_CAMPAIGN if path is None else Path(path)
    vectors = PREFIX_VECTORS if vectors_path is None else Path(vectors_path)
    record: dict[str, Any] = {"artifact": INTEGRATED_CAMPAIGN}
    if not path.is_file():
        record.update(
            usable=False,
            why_unusable=(
                "the integrated campaign artifact is absent; no RTL is on "
                "record as having executed this program at all"
            ),
        )
        return record
    body = json.loads(path.read_text())
    record["artifact_sha256"] = sha256_file(path)
    record["status"] = body.get("status")
    record["schema"] = body.get("schema")
    record["evidence_class"] = body.get("evidence_class")
    record["integrated_replay_passed"] = body.get("integrated_replay_passed")
    record["integrated_simulators"] = body.get("integrated_simulators")
    record["integrated_simulator_checks"] = body.get("integrated_simulator_checks")
    record["post_fault_write_count"] = body.get("post_fault_write_count")
    record["declared_git"] = body.get("git")

    pairs = _bound_pairs(body)
    drifted = []
    for bound, digest in pairs:
        resolved = ROOT / bound
        if not resolved.is_file():
            drifted.append(f"{bound} [missing]")
        elif sha256_file(resolved) != digest:
            drifted.append(bound)
    record["bound_source_count"] = len(pairs)
    record["drifted_source_count"] = len(drifted)
    record["drifted_sources"] = sorted(drifted)

    vector_declared = _dig(body, "vector_set.sha256")
    vector_observed = sha256_file(vectors) if vectors.is_file() else None
    record["vector_set_path"] = (
        str(vectors.relative_to(ROOT)) if vectors.is_relative_to(ROOT)
        else "(outside the repository)"
    )
    record["vector_set_sha256_declared"] = vector_declared
    record["vector_set_sha256_on_disk"] = vector_observed
    record["vector_set_is_current"] = (
        vector_declared is not None and vector_declared == vector_observed
    )

    logs = [
        case.get("run_log", "") for case in (body.get("cases") or [])
    ]
    measure = None
    marker = None
    for log in logs:
        found = measure_line(log)
        if found is not None:
            measure = found
        if INJECTION_MARKER in (log or ""):
            marker = "injection"
        elif ENGINE_MARKER in (log or "") and marker is None:
            marker = "engine"
    record["measure"] = measure
    # The campaign records its own simulated-cycle count from commit 9aecaac
    # onward.  Prefer the artifact's field over this tool's reading of the
    # log, and require the two to agree when both exist: two numbers for one
    # measurement is how a wrong one survives.
    declared_cycles = body.get("simulated_cycles")
    log_cycles = (measure or {}).get("cycles")
    record["simulated_cycles_declared"] = declared_cycles
    record["simulated_cycles_from_log"] = log_cycles
    record["simulated_cycles"] = (
        declared_cycles if isinstance(declared_cycles, int) and declared_cycles > 0
        else log_cycles
    )
    record["simulated_cycles_agree"] = (
        declared_cycles is None
        or log_cycles is None
        or int(declared_cycles) == int(log_cycles)
    )
    record["operator_admission"] = body.get("operator_admission")
    # The checkpoint bytes the run actually consumed, kept as an identity
    # rather than as a repository path: this file is produced into the run's
    # build directory from the real safetensors shards and is never committed.
    staged = body.get("staged_matmul_weight") or {}
    record["staged_matmul_weight"] = {
        "path": staged.get("path"),
        "bytes": staged.get("bytes"),
        "sha256": staged.get("sha256"),
        "matrix_sha256": [m.get("sha256") for m in staged.get("matrices", [])],
        "note": (
            "not a file of this repository; it is staged into the run's build "
            "directory from the checkpoint shards and its digests are the "
            "identity of the weights the run consumed"
        ),
    }
    record["pass_marker"] = marker
    record["case_status"] = [
        {"name": c.get("name"), "status": c.get("status"), "checks": c.get("checks")}
        for c in (body.get("cases") or [])
    ]
    record["observed_cases"] = (body.get("cases") or [{}])[0].get("observed_cases")
    record["expected_cases"] = body.get("expected_cases")

    reasons = []
    if body.get("status") != "pass":
        reasons.append(f"status is {body.get('status')!r}")
    if body.get("integrated_replay_passed") is not True:
        reasons.append(
            f"integrated_replay_passed is {body.get('integrated_replay_passed')!r}"
        )
    if drifted:
        reasons.append(
            f"{len(drifted)} bound source(s) have drifted since it was recorded"
        )
    if not record["vector_set_is_current"]:
        reasons.append(
            "it binds a vector set that is not the one on disk, so the golden "
            "values it compared against are not the ones this tree declares"
        )
    if _dig(body, "git.worktree_dirty") is not False:
        reasons.append(
            "it does not declare a clean worktree, so it is not source-bound"
        )
    if measure is None:
        reasons.append(
            "its run log carries no MEASURE line, so neither the simulated "
            "cycle count nor the injected-result count was measured"
        )
    if not record["simulated_cycles_agree"]:
        reasons.append(
            f"it declares {declared_cycles} simulated cycles while its own "
            f"log reports {log_cycles}; one measurement, two numbers"
        )
    if not (isinstance(record["simulated_cycles"], int)
            and record["simulated_cycles"] > 0):
        reasons.append(
            "it states no positive simulated cycle count, which the ladder's "
            "provenance spine requires of every rung"
        )
    if marker != "engine":
        reasons.append(
            f"its pass marker is {marker!r}: this rung requires the run in "
            "which the engine array computed, not one in which results were "
            "supplied at the engine boundary"
        )
    record["usable"] = not reasons
    record["why_unusable"] = "; ".join(reasons) if reasons else None
    return record


# --------------------------------------------------------------------------
# The vehicle's placement surface, counted from its own port list.
# --------------------------------------------------------------------------
def placement_capacity(
    vectors: dict[str, Any], campaign: dict[str, Any]
) -> dict[str, Any]:
    """How many distinct objects the vehicle is MEASURED to place at once.

    The bridge places every operand and every result of every family through
    one object table, so "how many objects can this role name" is the same
    question for every role and the answer is the table's depth.

    Two numbers, and they are not interchangeable.  ``declared_entries`` is
    counted from the bridge's own port list -- a declaration, and a count of
    source text, which this programme does not accept as a measurement of
    anything.  ``slots`` is what a run actually did: the largest number of
    distinct objects a passing campaign case bound into that table and
    resolved, on a case whose every result word -- ADDRESS and value -- was
    compared against golden.  With no usable campaign the measured depth is
    zero, and every role is unsatisfiable, because absence of evidence is a
    failure and not an unknown.

    Widening the port list therefore cannot move this number.  Only a run can.
    """
    text = BRIDGE.read_text()
    declared = len(
        set(re.findall(r"input\s+wire\s+\[31:0\]\s+cfg_place_object_(\d+)", text))
    )
    usable = campaign.get("usable") is True
    per_case: list[dict[str, Any]] = []
    for index, case in enumerate(vectors["cases"]):
        mapping = case.get("bank_mapping") or {}
        bound = [int(e["object_id"]) for e in mapping.get("object_placement", [])]
        observed = next(
            (
                c for c in (campaign.get("observed_cases") or [])
                if int(c.get("index", -1)) == index
            ),
            None,
        )
        agrees = (
            observed is not None
            and int(observed.get("words", -1))
            == int(case["expected"]["result_words"])
        )
        per_case.append(
            {
                "case_index": index,
                "case_name": case["name"],
                "objects_bound_and_named": len(bound),
                "objects": sorted(bound),
                "rewritten_objects": mapping.get(
                    "objects_written_more_than_once", []
                ),
                "case_passed_in_the_campaign": bool(usable and agrees),
            }
        )
    measured = max(
        [row["objects_bound_and_named"] for row in per_case
         if row["case_passed_in_the_campaign"]] or [0]
    )
    return {
        "source": "rtl/abi3/ot_a3_engine_issue_bridge.sv",
        "source_sha256": sha256_file(BRIDGE),
        "declared_entries": declared,
        "declared_entries_note": (
            "counted from the bridge's port list. It is a DECLARATION, not a "
            "measurement, and nothing below is credited from it"
        ),
        "measured_simultaneous_objects": measured,
        "measured_from": INTEGRATED_CAMPAIGN,
        "measured_note": (
            "the largest number of distinct ABI objects a passing campaign "
            "case bound into the bridge's table and resolved. Every one of "
            "that case's result words was compared against the golden write "
            "stream, address and value, so an object the bridge placed "
            "anywhere but at its own base would have failed the run"
        ),
        "per_case": per_case,
        "roles": {
            **{
                role: {
                    "object_keyed": True,
                    "slots": measured,
                    "note": (
                        "one shared object table serves every role; the "
                        "per-role capacity is the table's measured depth"
                    ),
                }
                for role in (
                    "matmul_weight", "head_rms_weight", "head_rms_input",
                    "rope_input", "rope_coefficient", "mapped_family_operand",
                    "matmul_input", "rms_input", "rms_weight", "result_object",
                )
            },
            # The three staged REGIONS the vehicle sweeps by launch counter.
            # They are not ABI objects and they do not go through the table,
            # so widening the table does not widen them and they are still
            # one base each.  They were added because their absence was not
            # neutral: a gather's and an embedding lookup's operands fell
            # through to ``unattributed_operands`` and were counted against
            # no capacity at all, which reported an absence as an optimistic
            # result.  Keeping them here keeps that fix.
            "index_base": {
                "object_keyed": False,
                "slots": 1,
                "note": (
                    "cfg_index_base is a single base advanced by the launch "
                    "counter, shared by DMA.GATHER and TENSOR.EMBED_LOOKUP; "
                    "it is not keyed by object"
                ),
            },
            "gather_source": {
                "object_keyed": False,
                "slots": 1,
                "note": (
                    "cfg_source_base is a single base advanced by "
                    "dma_gather_launch_count * cfg_source_launch_stride, not "
                    "keyed by object"
                ),
            },
            "embedding_source": {
                "object_keyed": False,
                "slots": 1,
                "note": (
                    "cfg_embedding_source_base is a single base advanced by "
                    "embedding_launch_count * EMBEDDING_WIDTH, not keyed by "
                    "object"
                ),
            },
        },
    }


# The engine-placement role each operand slot of each family draws its base
# from, taken from the bridge's own operand-address assembly.  This is a map
# from (mnemonic, slot) to role, not a set of addresses.
OPERAND_ROLE = {
    ("VECTOR.RMS_NORM", "input_view_0"): "rms_input",
    ("VECTOR.RMS_NORM", "input_view_1"): "rms_weight",
    ("TENSOR.MATMUL", "input_view_0"): "matmul_input",
    ("TENSOR.MATMUL", "input_view_1"): "matmul_weight",
    ("VECTOR.HEAD_RMS_NORM", "input_view_0"): "head_rms_input",
    ("VECTOR.HEAD_RMS_NORM", "input_view_1"): "head_rms_weight",
    ("VECTOR.ROPE", "input_view_0"): "rope_input",
    ("VECTOR.ROPE", "input_view_1"): "rope_coefficient",
    ("DMA.SCATTER", "input_view_0"): "mapped_family_operand",
    ("DMA.SCATTER", "input_view_1"): "mapped_family_operand",
    ("DMA.SCATTER", "output_view_0"): "mapped_family_operand",
    ("ATTENTION.GQA", "input_view_0"): "mapped_family_operand",
    ("ATTENTION.GQA", "input_view_1"): "mapped_family_operand",
    ("ATTENTION.GQA", "input_view_2"): "mapped_family_operand",
    ("ATTENTION.GQA", "input_view_3"): "mapped_family_operand",
    ("ATTENTION.GQA", "output_view_0"): "mapped_family_operand",
    ("VECTOR.ADD", "input_view_0"): "mapped_family_operand",
    ("VECTOR.ADD", "input_view_1"): "mapped_family_operand",
    ("VECTOR.ADD", "output_view_0"): "mapped_family_operand",
    ("VECTOR.SILU_MUL", "input_view_0"): "mapped_family_operand",
    ("VECTOR.SILU_MUL", "input_view_1"): "mapped_family_operand",
    ("VECTOR.SILU_MUL", "output_view_0"): "mapped_family_operand",
    # The bridge's own port comment names six mapped families, and these two
    # were missing from this map, so their operands fell through to
    # ``unattributed_operands`` and the head span's mapped demand was not
    # counted at all.  The reachability derivation attributes the same objects
    # to the same role from the deployment's descriptors, independently.
    ("SELECTION.ARGMAX", "input_view_0"): "mapped_family_operand",
    ("SELECTION.ARGMAX", "output_view_0"): "mapped_family_operand",
    ("SELECTION.TOKEN_APPEND", "input_view_0"): "mapped_family_operand",
    ("SELECTION.TOKEN_APPEND", "output_view_0"): "mapped_family_operand",
    # The two appending families whose operands this map never named.  Read
    # off ``launch_index_base`` and ``launch_source_base`` in the bridge:
    # a gather's index and an embedding lookup's index both come from
    # ``cfg_index_base + real_launch_count``; a gather's source comes from
    # ``cfg_source_base + dma_gather_launch_count * cfg_source_launch_stride``
    # and an embedding lookup's table from ``cfg_embedding_source_base +
    # embedding_launch_count * EMBEDDING_WIDTH``.  Each is one unkeyed base,
    # so each is modelled exactly as ``rms_input`` and ``matmul_input`` are.
    ("DMA.GATHER", "input_view_0"): "index_base",
    ("DMA.GATHER", "input_view_1"): "gather_source",
    ("TENSOR.EMBED_LOOKUP", "input_view_0"): "index_base",
    ("TENSOR.EMBED_LOOKUP", "input_view_1"): "embedding_source",
}

# The two mapped operands that address the INDEX bank rather than a plane of
# the result bank: the scatter's row selector and the attention's position.
# They are inputs to the layer wherever they come from, and separating them
# keeps "this operand came from an earlier RTL operator" a statement about
# activations only.
MAPPED_INDEX_SLOTS = {
    ("DMA.SCATTER", "input_view_0"),
    ("ATTENTION.GQA", "input_view_3"),
}


def layer_arithmetic(layer: list[dict[str, Any]]) -> dict[str, Any]:
    """The layer's multiply-accumulates, from the declared weight shapes.

    Derived so that the layer this rung names can be checked against the cost
    the gate itself states: if the two disagree, the layer being closed is not
    the layer that was costed, and one of them is wrong.
    """
    total = 0
    per_operator = []
    for operator in layer:
        if operator["mnemonic"] != "TENSOR.MATMUL":
            continue
        weight = next(
            (s for s in operator["slots"] if s["slot"] == "input_view_1"), None
        )
        if weight is None or len(weight["declared_dims"]) != 2:
            raise SystemExit(
                f"PC {operator['pc']}: a MATMUL whose weight view is not a "
                "matrix; the layer's arithmetic cannot be derived"
            )
        macs = weight["declared_dims"][0] * weight["declared_dims"][1]
        per_operator.append(
            {"pc": operator["pc"], "kernel_id": operator["kernel_id"],
             "weight_shape": weight["declared_dims"], "mac_count": macs}
        )
        total += macs
    return {
        "mac_count": total,
        "per_matmul": per_operator,
        "note": (
            "multiply-accumulates of the layer's projections, from each "
            "MATMUL's own declared weight view. Attention's own arithmetic is "
            "not in this figure, matching the cost the gate states."
        ),
    }


def placement_demand(
    layer: list[dict[str, Any]], capacity: dict[str, Any]
) -> dict[str, Any]:
    """What the whole layer would ask of each placement role, versus capacity.

    Every operand of every operator in the layer is attributed to the role the
    bridge would draw its base from, and the distinct objects per role are
    counted.  A role whose demand exceeds its capacity is a reason this vehicle
    cannot run the layer, stated as a count rather than as an opinion.
    """
    demand: dict[str, set[int]] = {}
    unattributed: list[dict[str, Any]] = []
    for operator in layer:
        for slot in operator["slots"]:
            role = OPERAND_ROLE.get((operator["mnemonic"], slot["slot"]))
            if role is None:
                if slot["slot"].startswith("output"):
                    role = "result_object"
                else:
                    unattributed.append(
                        {"pc": operator["pc"], "mnemonic": operator["mnemonic"],
                         "slot": slot["slot"]}
                    )
                    continue
            demand.setdefault(role, set()).add(int(slot["object_id"]))
    # An appending cursor cannot express a buffer that is written twice, so
    # the reuse set is what decides the output role and has to be known first.
    writes: dict[int, list[int]] = {}
    for operator in layer:
        for slot in operator["slots"]:
            if slot["slot"].startswith("output"):
                writes.setdefault(int(slot["object_id"]), []).append(operator["pc"])
    reused = {
        object_id: pcs for object_id, pcs in writes.items() if len(pcs) > 1
    }
    rows = []
    for role, objects in sorted(demand.items()):
        entry = capacity["roles"].get(role, {})
        slots = int(entry.get("slots", 0))
        keyed = bool(entry.get("object_keyed"))
        rows.append(
            {
                "role": role,
                "object_keyed": keyed,
                "distinct_objects_the_layer_needs": len(objects),
                "objects": sorted(objects),
                "slots_the_bridge_declares": slots,
                "short_by": max(0, len(objects) - slots),
                # An object-keyed role draws its base from the one object
                # table, so the question is whether that table is measured to
                # hold the objects this role names.  An unkeyed role is ONE
                # staged base, so it places exactly one object -- not zero.
                # A REWRITE is no longer a reason
                # for a role to be unsatisfiable: a result lands at its
                # object's base, so the second write to a buffer lands where
                # the first one did and a later read of that object reads
                # what is there.  The append cursor that could not express
                # that is gone.
                "satisfiable": len(objects) <= slots,
            }
        )
    # The binding constraint of ONE table is the UNION, not the largest role.
    # Ten roles that each fit in the table can still name more objects between
    # them than the table holds, and reporting only the per-role rows would
    # miss exactly that.  This row is stricter than every row above it.
    # Only the object-keyed roles draw from the table; the three staged
    # regions do not, so their objects are not part of what it has to hold.
    union = sorted({
        object_id
        for role, objects in demand.items()
        if capacity["roles"].get(role, {}).get("object_keyed")
        for object_id in objects
    })
    table = int(capacity.get("measured_simultaneous_objects", 0))
    union_row = {
        "role": "__the whole span, through one table__",
        "object_keyed": True,
        "distinct_objects_the_layer_needs": len(union),
        "objects": union,
        "slots_the_bridge_declares": table,
        "short_by": max(0, len(union) - table),
        "satisfiable": len(union) <= table,
        "note": (
            "the roles above share one object table, so the span is placeable "
            "only if the table is measured to hold their union"
        ),
    }
    rows.append(union_row)
    route = []
    for row in rows:
        if row["satisfiable"]:
            continue
        route.append(
            "place {need} distinct objects at once: the deepest table a run "
            "has resolved holds {have} (role {role}); the bridge declares "
            "{declared} entries, which is a declaration and not a "
            "measurement".format(
                role=row["role"],
                need=row["distinct_objects_the_layer_needs"],
                have=row["slots_the_bridge_declares"],
                declared=capacity.get("declared_entries"),
            )
        )
    return {
        "per_role": rows,
        "route_to_completion": route,
        "route_note": (
            "derived from the same demand-versus-capacity counts as the "
            "shortfall above; it is what this vehicle lacks, not a design"
        ),
        "unattributed_operands": unattributed,
        "output_objects": {
            "distinct_output_objects": len(writes),
            "writes": sum(len(v) for v in writes.values()),
            "objects_written_more_than_once": {
                str(k): sorted(v) for k, v in sorted(reused.items())
            },
            "note": (
                "the layer writes its intermediates into fewer buffers than "
                "it has operators. Under object-addressed results that is not "
                "a placement problem: the second write to a buffer lands at "
                "that buffer's own base, which is where a later read of it "
                "looks. It IS a verification problem, and the campaign "
                "answers it by comparing the engines' write STREAM rather "
                "than the retained image, so an intermediate a later operator "
                "overwrites is still compared"
            ),
        },
        "every_role_satisfiable": all(row["satisfiable"] for row in rows),
    }


# --------------------------------------------------------------------------
# What the integrated vehicle executed, and where each operand came from.
# --------------------------------------------------------------------------
def intermediate_coverage(
    executed: list[dict[str, Any]], vector_case: dict[str, Any]
) -> dict[str, Any]:
    """Whether each executed operator's OWN output words were compared.

    A layer output that matched by luck through two cancelling errors upstream
    is the failure this project has already made once, so it is not enough
    that the last operator's words matched: each operator's own output has to
    have been compared separately.

    The test used to be that the operators' output spans are DISJOINT inside
    the case's compared image region.  Under object-addressed results that
    test is wrong in both directions.  Two operators that write one buffer
    share a span on purpose, so disjointness would call a correct layer
    broken; and the retained image holds only the last of those two writes, so
    an image comparison would no longer see the first one at all.  What the
    campaign compares now is the engines' write STREAM -- every word, at the
    address it was written to, in launch order -- so each operator's own words
    are compared as they are produced whether or not a later operator
    overwrites them.  What is checked here is that every operator writes a
    non-empty output, that each one lies inside the region the case allocated,
    and that operators writing DIFFERENT objects do not overlap; an overlap
    between different objects would mean one operator's words were destroyed
    by another's and never separately compared.
    """
    base = int(vector_case["bank_mapping"]["result_region_base"])
    end = base + int(vector_case["bank_mapping"]["result_region_span"])
    by_object: dict[int, tuple[int, int]] = {}
    overlaps: list[dict[str, Any]] = []
    for row in executed:
        object_id = int(row["output_object_id"])
        span = (
            int(row["result_base_words"]),
            int(row["result_base_words"]) + int(row["result_words_written"]),
        )
        previous = by_object.get(object_id)
        if previous is not None and previous != span:
            overlaps.append(
                {"object_id": object_id, "spans": [list(previous), list(span)]}
            )
        by_object[object_id] = span
    spans = sorted(by_object.items(), key=lambda item: item[1])
    for index in range(len(spans) - 1):
        (left_object, left), (right_object, right) = spans[index], spans[index + 1]
        if left[1] > right[0]:
            overlaps.append(
                {
                    "objects": [left_object, right_object],
                    "spans": [list(left), list(right)],
                }
            )
    covered = sum(stop - start for _, (start, stop) in by_object.items())
    inside = all(base <= start and stop <= end for _, (start, stop) in spans)
    rewritten = sorted(
        {
            int(row["output_object_id"]) for row in executed
            if row.get("rewrites_object")
        }
    )
    return {
        "operator_count": len(executed),
        "each_operator_writes_a_non_empty_output": bool(executed) and all(
            row["result_words_written"] > 0 for row in executed
        ),
        "distinct_objects_do_not_overlap": not overlaps,
        "overlaps": overlaps,
        "operator_outputs_lie_in_the_compared_region": inside,
        "objects_rewritten_in_the_span": rewritten,
        "words": covered,
        "case_compared_region_words": end - base,
        "compared_against": (
            "the golden write stream, address and value, for every word the "
            "engines write; the retained image is compared as well and holds "
            "each object's last value"
        ),
        "holds": bool(executed) and not overlaps and inside and all(
            row["result_words_written"] > 0 for row in executed
        ),
    }


def executed_span(
    vector_case: dict[str, Any], layer: list[dict[str, Any]]
) -> dict[str, Any]:
    """Where every operand and result of the executed span actually went.

    Results are object-addressed, so this is no longer a cursor replay: a
    result's address is its own object's base plus the resolved element
    offset, and the vector set publishes the object table the run drove the
    bridge with.  The handoff test changes with it, and gets stricter.  It
    used to be "the address this operand reads is an address some earlier
    operator wrote"; under a buffer that is written twice, that test would
    match the WRONG write, because both writes are at one address.  It is now
    "the object this operand names was last written, before this operator, by
    an operator of this run" -- which is the property the ABI's own dependence
    ranges describe.
    """
    mapping = vector_case["bank_mapping"]
    output_base = int(mapping["result_region_base"])
    placement = {
        int(e["object_id"]): int(e["base_words"])
        for e in mapping["object_placement"]
    }
    produced: dict[int, dict[str, Any]] = {}
    placed: list[dict[str, Any]] = []
    written = 0
    last_writer: dict[int, int] = {}
    for operation in vector_case["supported_prefix"]:
        words = 1
        for dim in operation["output_view"]["dims"]:
            words *= int(dim)
        object_id = int(operation["output_view"]["object_id"])
        if object_id not in placement:
            raise SystemExit(
                f"{vector_case['name']}: PC {operation['pc']} writes object "
                f"{object_id}, which the vector set's own placement table "
                "does not name; nothing derived from this replay may ship"
            )
        entry = {
            "pc": int(operation["pc"]),
            "kind": operation["kind"],
            "output_object_id": object_id,
            "result_base_words": placement[object_id],
            "result_words": words,
            "rewrites_object": object_id in last_writer,
            "previous_writer_pc": last_writer.get(object_id),
        }
        placed.append(entry)
        produced[int(operation["pc"])] = entry
        last_writer[object_id] = int(operation["pc"])
        written += words
    declared = int(vector_case["expected"]["result_words"])
    if written != declared:
        raise SystemExit(
            f"{vector_case['name']}: the placement replay covers {written} "
            f"result words, the vector set declares {declared}; the placement "
            "replay is wrong and nothing derived from it may be reported"
        )
    span = int(mapping["result_region_span"])
    allocated = sum(
        entry["result_words"] for entry in placed if not entry["rewrites_object"]
    )
    if allocated != span:
        raise SystemExit(
            f"{vector_case['name']}: the placement replay allocates "
            f"{allocated} words, the vector set declares a region of {span}; "
            "the placement replay is wrong"
        )

    by_pc = {int(p["pc"]): p for p in placed}
    executed_pcs = set(by_pc)
    # Every object the layer itself writes.  An operand that names one of
    # these and did NOT come from the RTL operator that wrote it is a golden
    # value supplied inside the layer -- an injected intermediate.  An operand
    # that names anything else (a checkpoint gain, a projection matrix, the
    # generated RoPE coefficients) is an INPUT to the layer, and the
    # difference is what keeps this rung's third field honest.
    layer_output_objects = {
        int(slot["object_id"])
        for operator in layer
        for slot in operator["slots"]
        if slot["slot"].startswith("output")
    }
    order = [int(operation["pc"]) for operation in vector_case["supported_prefix"]]
    rows: list[dict[str, Any]] = []
    for operator in layer:
        if operator["pc"] not in executed_pcs:
            continue
        place = by_pc[operator["pc"]]
        position = order.index(operator["pc"])
        # Who last wrote each object BEFORE this operator ran.
        writer_before: dict[int, int] = {}
        for earlier in order[:position]:
            writer_before[by_pc[earlier]["output_object_id"]] = earlier
        operands = []
        for slot in operator["slots"]:
            if slot["slot"].startswith("output"):
                continue
            role = OPERAND_ROLE.get((operator["mnemonic"], slot["slot"]))
            object_id = int(slot["object_id"])
            base = placement.get(object_id)
            reads_result = role in (
                "rms_input", "matmul_input", "head_rms_input", "rope_input"
            ) or (
                role == "mapped_family_operand"
                and (operator["mnemonic"], slot["slot"]) not in MAPPED_INDEX_SLOTS
            )
            source = writer_before.get(object_id) if reads_result else None
            handoff = (
                "rtl_to_rtl" if source is not None
                else "staged_input" if not reads_result
                else "unresolved"
            )
            is_intermediate = object_id in layer_output_objects
            operands.append(
                {
                    "slot": slot["slot"],
                    "role": role,
                    "object_id": slot["object_id"],
                    "reads_result_bank": reads_result,
                    "base_words": base,
                    "produced_by_pc": source,
                    "handoff": handoff,
                    "names_a_layer_intermediate": is_intermediate,
                    "golden_injected": bool(
                        is_intermediate and handoff != "rtl_to_rtl"
                    ),
                }
            )
        rows.append(
            {
                "pc": operator["pc"],
                "kernel_id": operator["kernel_id"],
                "mnemonic": operator["mnemonic"],
                "numeric_contract": operator["numeric_contract"],
                "operator_descriptor_id": operator["operator_descriptor_id"],
                "output_object_id": place["output_object_id"],
                "result_base_words": place["result_base_words"],
                "result_words_written": place["result_words"],
                "rewrites_object": place["rewrites_object"],
                "previous_writer_pc": place["previous_writer_pc"],
                "operands": operands,
            }
        )
    operands = [o for row in rows for o in row["operands"]]
    handoff = {
        "operand_count": len(operands),
        "rtl_to_rtl_operand_count": sum(
            1 for o in operands if o["handoff"] == "rtl_to_rtl"
        ),
        "staged_input_operand_count": sum(
            1 for o in operands if o["handoff"] == "staged_input"
        ),
        "unresolved_operand_count": sum(
            1 for o in operands if o["handoff"] == "unresolved"
        ),
        "golden_injected_operand_count": sum(
            1 for o in operands if o["golden_injected"]
        ),
        "every_activation_operand_came_from_the_rtl": all(
            o["handoff"] == "rtl_to_rtl"
            for o in operands if o["names_a_layer_intermediate"]
        ),
        "staged_operands": sorted(
            {
                (o["role"], int(o["object_id"]))
                for o in operands if o["handoff"] != "rtl_to_rtl"
            }
        ),
        "note": (
            "an operand is an RTL-to-RTL handoff when the OBJECT it names "
            "was last written, before this operator, by an operator of this "
            "run; the replay of the vehicle's own object placement is what "
            "decides that, not a declaration. Address equality was the old "
            "test and it is not sound under a buffer written twice, because "
            "both writes are at one address. A staged operand that names an "
            "object this layer writes would be a golden intermediate and is "
            "counted as one; a staged operand that names a checkpoint tensor "
            "or a generated coefficient is an input to the layer."
        ),
    }
    return {
        "placement": placed,
        "layer_intermediates": rows,
        "handoff": handoff,
        "case_result_words": declared,
        "case_result_region_span": span,
        "objects_rewritten_in_the_span": sorted(
            {int(entry["output_object_id"]) for entry in placed
             if entry["rewrites_object"]}
        ),
    }


# --------------------------------------------------------------------------
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

    commit = run(["git", "rev-parse", "HEAD"])
    porcelain = run_lines(["git", "status", "--porcelain"])
    dirty_paths = sorted(
        line[3:].strip() for line in porcelain.splitlines() if len(line) > 3
    )
    return {
        "commit": commit or None,
        "worktree_dirty": bool(dirty_paths),
        "dirty_paths": dirty_paths,
    }


def rerun_note(path: Path | None) -> dict[str, Any] | None:
    """An independent run of the same campaign, recorded but not relied on.

    It establishes nothing: every field of the rung above is computed from
    the campaign the repository holds, because a number taken from a file the
    tree does not carry cannot be reproduced from the sources this artifact
    binds.  What it is good for is agreement -- an independent execution of
    the same vehicle that lands on the same counts is a check on the retained
    one, and a disagreement would be a finding.  Both are reported; neither is
    averaged.
    """
    if path is None:
        return None
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"--rerun {path} does not exist")
    body = json.loads(path.read_text())
    measure = None
    for case in (body.get("cases") or []):
        found = measure_line(case.get("run_log", ""))
        if found is not None:
            measure = found
    retained_path = ROOT / INTEGRATED_CAMPAIGN
    retained = (
        json.loads(retained_path.read_text()) if retained_path.is_file() else {}
    )

    def compare(field: str) -> dict[str, Any]:
        mine, theirs = body.get(field), retained.get(field)
        return {"rerun": mine, "retained": theirs, "agree": mine == theirs}

    agreement = {
        field: compare(field)
        for field in (
            "status",
            "integrated_replay_passed",
            "integrated_simulator_checks",
            "simulated_cycles",
            "operator_admission",
        )
    }
    agreement["observed_cases"] = {
        "rerun": (body.get("cases") or [{}])[0].get("observed_cases"),
        "retained": (retained.get("cases") or [{}])[0].get("observed_cases"),
        "agree": (body.get("cases") or [{}])[0].get("observed_cases")
        == (retained.get("cases") or [{}])[0].get("observed_cases"),
    }
    return {
        "establishes": [],
        "what_it_is": (
            "an independent execution of the same integrated campaign, run "
            "for this rung in a separately pinned worktree. No field of this "
            "rung is computed from it."
        ),
        "why_not_retained": (
            "it declares worktree_dirty "
            f"{_dig(body, 'git.worktree_dirty')!r} at commit "
            f"{str(_dig(body, 'git.commit'))[:12]}, and the repository "
            f"already holds {INTEGRATED_CAMPAIGN} from a clean tree; "
            "replacing a clean run with a dirtier one would weaken the "
            "evidence, not strengthen it"
        ),
        "artifact_sha256": sha256_file(path),
        "vector_set_sha256": _dig(body, "vector_set.sha256"),
        "git": body.get("git"),
        "measure": measure,
        "agreement_with_the_retained_campaign": agreement,
        "agrees_on_every_compared_field": all(
            entry["agree"] for entry in agreement.values()
        ),
    }


def build(
    output: Path,
    campaign_path: Path | None = None,
    vectors_path: Path | None = None,
    rerun_path: Path | None = None,
) -> dict[str, Any]:
    manifest = json.loads(DEPLOYMENT_MANIFEST.read_text())
    images = {
        "descriptor": read_hex(DEPLOYMENT_DIR / "a3_descriptor.hex"),
        "program": read_hex(DEPLOYMENT_DIR / "a3_program.hex"),
        "issue": read_hex(DEPLOYMENT_DIR / "a3_deployment_issue.hex"),
    }
    vectors = json.loads(
        (PREFIX_VECTORS if vectors_path is None else Path(vectors_path)).read_text()
    )
    campaign = integrated_evidence(campaign_path, vectors_path)
    capacity = placement_capacity(vectors, campaign)
    git = git_state()

    records = []
    for storage_class, deployment_key in STORAGE_CLASSES.items():
        vector_case = next(
            c for c in vectors["cases"] if c["deployment"] == deployment_key
        )
        kernels = kernel_index(vector_case)
        operators = issued_operators(manifest, images, deployment_key)
        layer, invocations = layer_operators(operators, kernels)
        demand = placement_demand(layer, capacity)
        arithmetic = layer_arithmetic(layer)
        span = executed_span(vector_case, layer)
        coverage = intermediate_coverage(span["layer_intermediates"], vector_case)

        executed = span["layer_intermediates"]
        executed_pcs = {row["pc"] for row in executed}
        role_ok = {row["role"]: row for row in demand["per_role"]}
        span_row = next(
            (row for row in demand["per_role"] if row["role"].startswith("__")),
            None,
        )
        uncovered = []
        for op in layer:
            if op["pc"] in executed_pcs:
                continue
            blocking = []
            for slot in op["slots"]:
                role = OPERAND_ROLE.get((op["mnemonic"], slot["slot"]))
                if role is None and slot["slot"].startswith("output"):
                    role = "result_object"
                row = role_ok.get(role)
                if row is not None and not row["satisfiable"]:
                    blocking.append(
                        {
                            "slot": slot["slot"],
                            "role": role,
                            "object_id": slot["object_id"],
                            "why": (
                                "role {r} needs {n} distinct objects across "
                                "the layer and the deepest object table a run "
                                "has resolved holds {h}"
                            ).format(
                                r=role,
                                n=row["distinct_objects_the_layer_needs"],
                                h=row["slots_the_bridge_declares"],
                            ),
                        }
                    )
            # The roles share ONE table, so an operand can be blocked without
            # any single role being short: the span's objects together can
            # exceed the table even when no role does.  Attributing that to
            # the operands whose objects are in the union is what stops this
            # rung reporting an operator as "blocked only by the boundary"
            # while the vehicle cannot place its operands at all -- the field
            # that carried the correction section 11.7 records, reported in
            # its optimistic form.
            if span_row is not None and not span_row["satisfiable"]:
                for slot in op["slots"]:
                    role = OPERAND_ROLE.get((op["mnemonic"], slot["slot"]))
                    if role is None and slot["slot"].startswith("output"):
                        role = "result_object"
                    row = role_ok.get(role)
                    if row is None or not row["object_keyed"]:
                        continue
                    if int(slot["object_id"]) not in span_row["objects"]:
                        continue
                    blocking.append(
                        {
                            "slot": slot["slot"],
                            "role": role,
                            "object_id": slot["object_id"],
                            "why": (
                                "the span names {n} distinct objects through "
                                "one table and the deepest table a run has "
                                "resolved holds {h}"
                            ).format(
                                n=span_row["distinct_objects_the_layer_needs"],
                                h=span_row["slots_the_bridge_declares"],
                            ),
                        }
                    )
            uncovered.append(
                {
                    "pc": op["pc"],
                    "kernel_id": op["kernel_id"],
                    "mnemonic": op["mnemonic"],
                    "operator_descriptor_id": op["operator_descriptor_id"],
                    "blocking_operands": blocking,
                    "blocked_only_by_the_boundary": not blocking,
                }
            )

        measure = campaign.get("measure") or {}
        # The run is one binary over several cases.  A pass over the run is
        # not a measurement of THIS lowering until the case that carries it is
        # identified and its own observed counts agree with what the vector
        # set declares for it.
        case_index = vectors["cases"].index(vector_case)
        observed = next(
            (
                c for c in (campaign.get("observed_cases") or [])
                if int(c.get("index", -1)) == case_index
            ),
            None,
        )
        expected_words = int(vector_case["expected"]["result_words"])
        boundary_pc = int((vector_case.get("first_unsupported") or {}).get("pc", -1))
        case_agrees = (
            observed is not None
            and int(observed.get("words", -1)) == expected_words
            and int(observed.get("fault", -2)) == boundary_pc
        )
        case_evidence = {
            "case_index": case_index,
            "case_name": vector_case["name"],
            "observed": observed,
            "declared_result_words": expected_words,
            "declared_boundary_pc": boundary_pc,
            "observed_agrees_with_the_vector_set": case_agrees,
        }
        usable = campaign.get("usable") is True and case_agrees
        compared = (
            sum(row["result_words_written"] for row in executed) if usable else None
        )
        # A campaign whose every case passed compared every result word it
        # wrote against the golden write stream, address and value, and its
        # retained image against p3_expect.hex, and reported no failure.  With no
        # usable campaign there are no comparisons, and a mismatch count over
        # zero comparisons is not a zero mismatch count.
        mismatched = 0 if (usable and compared) else None
        measured_injection = measure.get("injected_results") if usable else None
        staged_intermediates = span["handoff"]["golden_injected_operand_count"]
        injected = (
            None if measured_injection is None
            else int(measured_injection) + int(staged_intermediates)
        )
        cycles = campaign.get("simulated_cycles") if usable else None

        # The structural property (each operator's output is a distinct,
        # non-empty part of the compared region) is not the same claim as
        # "the comparison happened".  Both are required, and they are kept
        # apart so a layout that would support the claim cannot be read as
        # the claim itself.
        coverage["comparison_actually_happened"] = usable
        operator_count = len(executed) if usable else 0
        complete = bool(
            usable
            and operator_count == len(layer)
            and mismatched == 0
            and injected == 0
            # Every operator's own output must be separately present in the
            # region that was compared. Without this, a layer whose final
            # output matched through two cancelling errors upstream would
            # still be called complete -- the exact failure that produced this
            # project's 99.17 % MFU claim.
            and coverage["holds"]
        )

        why: list[str] = []
        if campaign.get("usable") is not True:
            why.append(
                "the integrated campaign is not usable as evidence: "
                + str(campaign.get("why_unusable"))
            )
        elif not case_agrees:
            why.append(
                "the integrated campaign passed, but the case that carries "
                f"this lowering ({vector_case['name']}) is not on record "
                "with the result-word count and fail-closed boundary the "
                "vector set declares, so the run measures nothing about it: "
                f"observed {observed!r}"
            )
        if uncovered:
            why.append(
                f"{len(uncovered)} of the layer's {len(layer)} operators did "
                "not execute in the integrated RTL: "
                + ", ".join(
                    f"PC {u['pc']} {u['mnemonic']} ({u['kernel_id']})"
                    for u in uncovered
                )
            )
        boundary = dict(vector_case.get("first_unsupported") or {})
        if boundary:
            first_uncovered = min(
                (u["pc"] for u in uncovered), default=None
            )
            boundary["is_the_first_uncovered_operator_of_the_layer"] = (
                first_uncovered is not None
                and int(boundary.get("pc", -1)) == int(first_uncovered)
            )
            why.append(
                "the vehicle fails closed at PC {pc} {opcode} descriptor "
                "{descriptor_id} with trap class {trap_class}; {claim}".format(
                    claim=(
                        "that is the first operator of the layer it does not "
                        "run"
                        if boundary["is_the_first_uncovered_operator_of_the_layer"]
                        else "the first operator of the layer it does not run "
                             f"is PC {first_uncovered}, so the boundary and "
                             "the coverage gap are not the same place"
                    ),
                    **{k: boundary.get(k) for k in
                       ("pc", "opcode", "descriptor_id", "trap_class")},
                )
            )
        for row in demand["per_role"]:
            if not row["satisfiable"]:
                why.append(
                    "placement role {role} must name {need} distinct objects "
                    "for this layer and the deepest object table a run has "
                    "been measured to resolve holds {have} (the bridge "
                    "DECLARES {declared} entries, which is a count of source "
                    "text and is credited to nothing)".format(
                        role=row["role"],
                        need=row["distinct_objects_the_layer_needs"],
                        have=row["slots_the_bridge_declares"],
                        declared=capacity.get("declared_entries"),
                    )
                )
        if usable and not coverage["holds"]:
            why.append(
                "the layer's operators do not each occupy a distinct, "
                "non-empty part of the compared region, so a matching layer "
                "output would not establish that every intermediate matched: "
                + json.dumps(coverage)
            )
        # The layer rewriting buffers is no longer a reason it cannot be
        # placed -- results are object-addressed, so a rewrite lands where the
        # first write did.  It is recorded because it is what makes the write
        # STREAM, rather than the retained image, the thing the campaign has
        # to compare.

        records.append(
            {
                "storage_class": storage_class,
                "workload_id": WORKLOAD,
                "deployment": {
                    "key": deployment_key,
                    "deployment_sha256": vector_case["deployment_sha256"],
                },
                "layer": {
                    "layer_id": LAYER_PREFIX.rstrip("."),
                    "layer_named_by": (
                        "the certified Kernel IR kernel each OPERATOR "
                        "descriptor's source_kernel_id points at; every issue "
                        "whose kernel_id begins " + repr(LAYER_PREFIX)
                    ),
                    "kernel_ir": {
                        "path": kernels["path"],
                        "sha256": kernels["sha256"],
                        "graph_id": kernels["graph_id"],
                    },
                    "operators_in_layer": len(layer),
                    "loop": invocations,
                    "arithmetic": arithmetic,
                    "operator_count": operator_count,
                    "operator_count_meaning": (
                        "operators of this layer that executed in the "
                        "integrated RTL and had every result word they wrote "
                        "compared against the golden image"
                    ),
                    "complete": complete,
                    "compared_words": compared,
                    "mismatched_words": mismatched,
                    "mismatched_words_note": (
                        None if mismatched == 0 else
                        "no words of this layer were compared under this "
                        "lowering; a mismatch count over zero comparisons is "
                        "not a zero mismatch count and is reported absent"
                    ),
                    "golden_injected_intermediate_count": injected,
                    "golden_injected_breakdown": {
                        "engine_results_injected_at_the_engine_boundary":
                            measured_injection,
                        "activation_operands_staged_instead_of_produced":
                            staged_intermediates,
                        "note": (
                            "the first is the harness's own injected_results "
                            "counter; the second is every operand of an "
                            "executed operator that names an object this "
                            "layer writes and was not read from the address "
                            "the producing operator wrote"
                        ),
                    },
                    "handoff": span["handoff"],
                    "golden_injected_note": (
                        "measured from the harness's own injected_results "
                        "counter and the PASS marker the run printed; the run "
                        "that establishes this rung is the one in which the "
                        "engine array computed"
                        if injected is not None else
                        "absent: no measured injection count exists, and this "
                        "field is never defaulted to zero"
                    ),
                    "intermediate_coverage": coverage,
                    "every_intermediate_compared": bool(
                        coverage["holds"] and usable
                    ),
                    "intermediates": executed,
                    "uncovered_operators": uncovered,
                    "fail_closed_boundary": boundary,
                    "why_not_complete": why,
                    "placement_demand": demand,
                },
                "execution": {
                    "simulator": (
                        ", ".join(campaign.get("integrated_simulators") or [])
                        if usable else None
                    ),
                    "simulated_cycles": cycles,
                    "simulated_cycles_scope": (
                        "the integrated run's own total, over all four cases "
                        "of the one binary; the harness reports one cycle "
                        "count for the run and this rung does not split it "
                        "per lowering, so the same number appears in both "
                        "records and must not be added across them"
                        if cycles else None
                    ),
                    "evidence_class": (
                        campaign.get("evidence_class") if usable else
                        "absent: no usable integrated RTL simulation of this "
                        "lowering exists"
                    ),
                    "campaign": campaign,
                    "case_evidence": case_evidence,
                    "vehicle": {
                        "top": "rtl/test/a3_shipped_prefix_top.sv",
                        "top_sha256": sha256_file(INTEGRATED_TOP),
                        "bridge": capacity["source"],
                        "bridge_sha256": capacity["source_sha256"],
                        "placement_capacity": capacity,
                    },
                },
                "git": {
                    "commit": git["commit"],
                    "worktree_dirty": git["worktree_dirty"],
                    "dirty_paths": git["dirty_paths"],
                    "scope": (
                        "the tree THIS artifact was derived in. It is not a "
                        "claim about the tree the integrated campaign ran in; "
                        "see execution.campaign.declared_git."
                    ),
                },
            }
        )

    summary = {
        "schema": SCHEMA,
        "gate": "G1b",
        "generated_by": "tools/build_abi3_g1b_layer_closure.py",
        "generated_by_sha256": sha256_file(Path(__file__).resolve()),
        "derived_mechanically": True,
        "workload_id": WORKLOAD,
        "layer_definition": (
            "one complete transformer layer, named by the certified Kernel "
            "IR: every engine issue the governed decode program makes whose "
            "OPERATOR descriptor's source_kernel_id points at a kernel whose "
            "kernel_id begins " + repr(LAYER_PREFIX) + ". The two lowerings "
            "are resolved independently; their descriptor IDs differ at every "
            "governed program counter and nothing measured on one is "
            "transferred to the other."
        ),
        "does_not_establish": [
            "any layer other than the one named above, and any position other "
            "than the governed decode position",
            "the KV history the layer's attention would read: those rows are "
            "produced by the prefill passes, are an INPUT to this layer, and "
            "are not established by this rung",
            "dual-simulator agreement: the integrated vehicle is Verilator "
            "only, because Icarus 11 cannot parse the paged weight window's "
            "64-bit declarations",
            "any rate; that is gate G3",
        ],
        # Published because the distinction inside it is the whole point:
        # ``declared_entries`` is a count of the bridge's port list and is
        # credited to nothing, ``measured_simultaneous_objects`` is what a
        # passing run actually placed, and every satisfiability verdict below
        # is computed from the second.
        "placement_capacity": capacity,
        "records": records,
        "rerun_not_retained": rerun_note(rerun_path),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--campaign",
        type=Path,
        default=None,
        help=(
            "the integrated campaign artifact to read the measurement from; "
            "defaults to " + INTEGRATED_CAMPAIGN
        ),
    )
    parser.add_argument(
        "--rerun",
        type=Path,
        default=None,
        help=(
            "an integrated campaign run produced outside the repository, "
            "recorded as a measurement only; it establishes nothing and no "
            "field of the rung is computed from it"
        ),
    )
    parser.add_argument(
        "--vectors",
        type=Path,
        default=None,
        help=(
            "the shipped-prefix vector set whose executed span and bank "
            "mapping are replayed; defaults to the retained one"
        ),
    )
    args = parser.parse_args()
    summary = build(args.output, args.campaign, args.vectors, args.rerun)
    for record in summary["records"]:
        layer = record["layer"]
        print(
            f"{record['storage_class']} layer {layer['layer_id']}: "
            f"{layer['operator_count']}/{layer['operators_in_layer']} operators, "
            f"complete={layer['complete']}, "
            f"compared_words={layer['compared_words']}, "
            f"mismatched={layer['mismatched_words']}, "
            f"golden_injected={layer['golden_injected_intermediate_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
