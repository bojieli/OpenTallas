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
word the RTL writes into result memory against ``p3_expect.hex``, twice: once
per case as the case retires and once over the whole retained image at the
end.  So an operator that ran has had *its own* output words compared, not
merely the last operator's.  This tool records the comparison per operator, so
"the layer output matched" can never stand in for "every intermediate
matched" -- the failure that produced this project's 99.17 % MFU claim from
two cancelling unit errors.

**The handoff is computed, not claimed.**  The vehicle places the appending
families at ``cfg_output_base + result_word_cursor``.  This tool replays that
cursor over the operations the vector set declares, and then checks each
executed operator's declared operand base against the address the operator
that produced that operand actually wrote to.  An operand that equals a
produced address is an RTL-to-RTL handoff; an operand that does not is a
staged input, and is listed as one.

**Nothing inside is injected** is read from the harness's measured
``injected_results`` count and from which PASS marker the run printed.  If the
log carries neither, the count is reported absent -- never zero.

**The layer's arithmetic is derived too**, from the weight view of each of its
MATMULs, and comes to 192,937,984 multiply-accumulates -- the figure G1b's own
note states.  Agreement is the check that the layer being closed is the layer
that was costed; a test pins it in both directions.

**What is missing is counted, not characterised.**  Every operand of every
operator in the layer is attributed to the engine-placement role the bridge
would draw its base from, and the distinct objects per role are compared with
the slots the bridge's own port list declares.  A role whose demand exceeds
its capacity is a reason this vehicle cannot run the layer, stated as two
numbers.

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
def placement_capacity() -> dict[str, Any]:
    """How many distinct objects each engine-placement role can name.

    Counted from the bridge's own declaration, so this cannot drift away from
    the RTL by being written down twice.
    """
    text = BRIDGE.read_text()
    port = r"input\s+wire\s+\[31:0\]\s+cfg_"

    def count(name: str) -> int:
        return len(set(re.findall(port + name + r"_(\d+)", text)))

    return {
        "source": "rtl/abi3/ot_a3_engine_issue_bridge.sv",
        "source_sha256": sha256_file(BRIDGE),
        "roles": {
            "matmul_weight": {
                "object_keyed": True,
                "slots": count("matmul_weight_object"),
            },
            "head_rms_weight": {
                "object_keyed": True,
                "slots": count("head_weight_object"),
            },
            "head_rms_input": {
                "object_keyed": True,
                "slots": count("head_input_object"),
            },
            "rope_input": {
                "object_keyed": True,
                "slots": count("rope_input_object"),
            },
            "rope_coefficient": {
                "object_keyed": True,
                "slots": len(re.findall(r"cfg_rope_coefficient_object\b", text)) and 1,
            },
            "mapped_family_operand": {
                "object_keyed": True,
                "slots": count("map_object"),
            },
            "matmul_input": {
                "object_keyed": False,
                "slots": 1,
                "note": "cfg_matmul_input_base is a single base, not keyed by object",
            },
            "rms_input": {
                "object_keyed": False,
                "slots": 1,
                "note": "cfg_rms_input_base is a single base, not keyed by object",
            },
            "rms_weight": {
                "object_keyed": False,
                "slots": 1,
                "note": "cfg_rms_weight_base is a single base, not keyed by object",
            },
            "appending_output": {
                "object_keyed": False,
                "slots": 1,
                "note": (
                    "the seven appending families write at cfg_output_base + "
                    "result_word_cursor; an object written twice therefore "
                    "occupies two addresses, which the program's own storage "
                    "semantics do not"
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
                    role = "appending_output"
                else:
                    unattributed.append(
                        {"pc": operator["pc"], "mnemonic": operator["mnemonic"],
                         "slot": slot["slot"]}
                    )
                    continue
            demand.setdefault(role, set()).add(int(slot["object_id"]))
    rows = []
    for role, objects in sorted(demand.items()):
        slots = int(capacity["roles"].get(role, {}).get("slots", 0))
        keyed = bool(capacity["roles"].get(role, {}).get("object_keyed"))
        rows.append(
            {
                "role": role,
                "object_keyed": keyed,
                "distinct_objects_the_layer_needs": len(objects),
                "objects": sorted(objects),
                "slots_the_bridge_declares": slots,
                "short_by": max(0, len(objects) - slots),
                "satisfiable": keyed and len(objects) <= slots,
            }
        )
    # An appending cursor cannot express a buffer that is written twice.
    writes: dict[int, list[int]] = {}
    for operator in layer:
        for slot in operator["slots"]:
            if slot["slot"].startswith("output"):
                writes.setdefault(int(slot["object_id"]), []).append(operator["pc"])
    reused = {
        object_id: pcs for object_id, pcs in writes.items() if len(pcs) > 1
    }
    # What would have to change for this vehicle to be able to run the layer
    # at all, expressed as counts against the bridge's own declaration.  It is
    # derived from the same two numbers as the shortfall, so it cannot drift
    # away from the reason the rung is red.
    route = []
    for row in rows:
        if row["satisfiable"]:
            continue
        if row["object_keyed"]:
            route.append(
                "widen {role} from {have} to at least {need} object slots"
                .format(role=row["role"],
                        have=row["slots_the_bridge_declares"],
                        need=row["distinct_objects_the_layer_needs"])
            )
        else:
            route.append(
                "make {role} object-addressed: it is one unkeyed base and the "
                "layer needs {need} distinct objects ({objects})".format(
                    role=row["role"],
                    need=row["distinct_objects_the_layer_needs"],
                    objects=row["objects"],
                )
            )
    if reused:
        route.append(
            "place results by object rather than by the append cursor: "
            f"{len(reused)} of the layer's buffers are written more than once, "
            "so an append cursor gives one object several addresses and no "
            "object-keyed reader can name the right one"
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
                "the layer writes its intermediates into fewer buffers than it "
                "has operators: an appending output cursor gives each write a "
                "fresh address, which is sound only while nothing reads the "
                "earlier contents of a reused object"
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

    The harness compares every word of the case's result region against the
    golden image, so the question this answers is whether each operator's
    output really occupies a distinct, non-empty part of that region.  A layer
    output that matched by luck through two cancelling errors upstream is the
    failure this project has already made once; an operator whose intermediate
    is not separately present in the compared region could hide exactly that.
    """
    base = int(vector_case["bank_mapping"]["output_base"])
    end = base + int(vector_case["expected"]["result_words"])
    spans = sorted(
        (row["result_base_words"],
         row["result_base_words"] + row["result_words_written"])
        for row in executed
    )
    disjoint = all(
        spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)
    )
    covered = sum(stop - start for start, stop in spans)
    inside = all(base <= start and stop <= end for start, stop in spans)
    return {
        "operator_count": len(executed),
        "each_operator_writes_a_non_empty_output": bool(executed) and all(
            row["result_words_written"] > 0 for row in executed
        ),
        "operator_outputs_are_disjoint": disjoint,
        "operator_outputs_lie_in_the_compared_region": inside,
        "words": covered,
        "case_compared_region_words": end - base,
        "holds": bool(executed) and disjoint and inside and all(
            row["result_words_written"] > 0 for row in executed
        ),
    }


def executed_span(
    vector_case: dict[str, Any], layer: list[dict[str, Any]]
) -> dict[str, Any]:
    """Replay the vehicle's append cursor and attribute every operand."""
    mapping = vector_case["bank_mapping"]
    output_base = int(mapping["output_base"])
    cursor = output_base
    produced: dict[int, dict[str, Any]] = {}
    placed: list[dict[str, Any]] = []
    for operation in vector_case["supported_prefix"]:
        words = 1
        for dim in operation["output_view"]["dims"]:
            words *= int(dim)
        entry = {
            "pc": int(operation["pc"]),
            "kind": operation["kind"],
            "result_base_words": cursor,
            "result_words": words,
        }
        placed.append(entry)
        produced[int(operation["pc"])] = entry
        cursor += words
    declared = int(vector_case["expected"]["result_words"])
    if cursor - output_base != declared:
        raise SystemExit(
            f"{vector_case['name']}: the append cursor replays to "
            f"{cursor - output_base} result words, the vector set declares "
            f"{declared}; the placement replay is wrong and nothing derived "
            "from it may be reported"
        )

    # Which addresses each executed operator's operands were read from.
    address_of_role = {
        "rms_input": int(mapping["rms_input_base"]),
        "matmul_input": int(mapping["matmul_input_base"]),
    }
    keyed = {
        "head_rms_input": {
            int(e["object_id"]): int(e["base_words"])
            for e in mapping["head_input_objects"]
        },
        "rope_input": {
            int(e["object_id"]): int(e["base_words"])
            for e in mapping["rope_input_objects"]
        },
    }
    # Present only once a vector set supplies the object-addressed placement
    # the mapped families need.  Absent, those operands resolve to no address
    # at all, which is reported as unresolved rather than assumed to be
    # anything.
    object_placement = {
        int(e["object_id"]): int(e["base_words"])
        for e in mapping.get("mapped_placement", [])
    }
    by_pc = {int(p["pc"]): p for p in placed}
    produced_at = {p["result_base_words"]: p for p in placed}
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
    rows: list[dict[str, Any]] = []
    for operator in layer:
        if operator["pc"] not in executed_pcs:
            continue
        place = by_pc[operator["pc"]]
        operands = []
        for slot in operator["slots"]:
            if slot["slot"].startswith("output"):
                continue
            role = OPERAND_ROLE.get((operator["mnemonic"], slot["slot"]))
            object_id = int(slot["object_id"])
            # Object-addressed placement first, wherever a vector set supplies
            # it: it is the only form that can survive a buffer being written
            # more than once.  Then the role's own object table, then the
            # single unkeyed base the prefix vehicle uses.
            base = object_placement.get(object_id)
            if base is None and role in keyed:
                base = keyed[role].get(object_id)
            if base is None and role in address_of_role:
                base = address_of_role[role]
            reads_result = role in (
                "rms_input", "matmul_input", "head_rms_input", "rope_input"
            ) or (
                role == "mapped_family_operand"
                and (operator["mnemonic"], slot["slot"]) not in MAPPED_INDEX_SLOTS
            )
            source = None
            if reads_result and base is not None and base in produced_at:
                source = produced_at[base]["pc"]
            handoff = (
                "rtl_to_rtl" if source is not None
                else "staged_input" if not reads_result
                else "unresolved"
            )
            is_intermediate = int(slot["object_id"]) in layer_output_objects
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
                "output_object_id": next(
                    (s["object_id"] for s in operator["slots"]
                     if s["slot"].startswith("output")), None
                ),
                "result_base_words": place["result_base_words"],
                "result_words_written": place["result_words"],
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
            "an operand is an RTL-to-RTL handoff when the address the bridge "
            "reads it from is the address an earlier operator of this run "
            "wrote; the replay of the vehicle's own append cursor is what "
            "decides that, not a declaration. A staged operand that names an "
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
    }


# --------------------------------------------------------------------------
def git_state() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout.strip()

    commit = run(["git", "rev-parse", "HEAD"])
    porcelain = run(["git", "status", "--porcelain"])
    dirty_paths = sorted(
        line[3:].strip() for line in porcelain.splitlines() if len(line) > 3
    )
    return {
        "commit": commit or None,
        "worktree_dirty": bool(dirty_paths),
        "dirty_paths": dirty_paths,
    }


def rerun_note(path: Path | None) -> dict[str, Any] | None:
    """A campaign run produced in this session but NOT retained in the tree.

    It establishes nothing.  A rung may only be built from evidence the
    repository holds, because a number derived from a file that is not
    committed cannot be reproduced from the sources this artifact binds.  This
    block exists so a measurement is not lost between one lane and the next,
    and every gate field above is computed without reading it.
    """
    if path is None:
        return None
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"--rerun {path} does not exist")
    body = json.loads(path.read_text())
    logs = [c.get("run_log", "") for c in (body.get("cases") or [])]
    measure = None
    for log in logs:
        found = measure_line(log)
        if found is not None:
            measure = found
    return {
        "establishes": [],
        "why_not_retained": (
            "the vector set this run consumed is uncommitted work of the "
            "descriptor-identity lane, so retaining the run would bind this "
            "repository's evidence to bytes it does not hold. It is recorded "
            "here as a measurement, not as evidence, and no field of this "
            "rung was computed from it."
        ),
        "artifact_sha256": sha256_file(path),
        "status": body.get("status"),
        "integrated_replay_passed": body.get("integrated_replay_passed"),
        "integrated_simulators": body.get("integrated_simulators"),
        "integrated_simulator_checks": body.get("integrated_simulator_checks"),
        "vector_set_sha256": _dig(body, "vector_set.sha256"),
        "git": body.get("git"),
        "observed_cases": (body.get("cases") or [{}])[0].get("observed_cases"),
        "operator_admission": body.get("operator_admission"),
        "measure": measure,
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
    capacity = placement_capacity()
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
        uncovered = []
        for op in layer:
            if op["pc"] in executed_pcs:
                continue
            blocking = []
            for slot in op["slots"]:
                role = OPERAND_ROLE.get((op["mnemonic"], slot["slot"]))
                if role is None and slot["slot"].startswith("output"):
                    role = "appending_output"
                row = role_ok.get(role)
                if row is not None and not row["satisfiable"]:
                    blocking.append(
                        {
                            "slot": slot["slot"],
                            "role": role,
                            "object_id": slot["object_id"],
                            "why": (
                                "role {r} needs {n} distinct objects across "
                                "the layer, the bridge declares {h}"
                            ).format(
                                r=role,
                                n=row["distinct_objects_the_layer_needs"],
                                h=row["slots_the_bridge_declares"],
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
        # wrote against p3_expect.hex, twice, and reported no failure.  With no
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
                    "for this layer and the bridge declares {have}{keyed}"
                    .format(
                        role=row["role"],
                        need=row["distinct_objects_the_layer_needs"],
                        have=row["slots_the_bridge_declares"],
                        keyed=(
                            "" if row["object_keyed"]
                            else ", and that base is not keyed by object at all"
                        ),
                    )
                )
        if usable and not coverage["holds"]:
            why.append(
                "the layer's operators do not each occupy a distinct, "
                "non-empty part of the compared region, so a matching layer "
                "output would not establish that every intermediate matched: "
                + json.dumps(coverage)
            )
        if demand["output_objects"]["objects_written_more_than_once"]:
            why.append(
                "the layer writes {n} intermediates into {d} buffers, so an "
                "appending output cursor gives a reused object two addresses; "
                "objects written more than once: {objs}".format(
                    n=demand["output_objects"]["writes"],
                    d=demand["output_objects"]["distinct_output_objects"],
                    objs=sorted(
                        demand["output_objects"]["objects_written_more_than_once"]
                    ),
                )
            )

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
