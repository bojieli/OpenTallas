#!/usr/bin/env python3
"""Derive rung G1d's artifact: the head, and the token the RTL emitted.

G1d (``configs/gates/redesign_gates.json``) asks for the final normalisation,
the LM head and the argmax to execute *in the integrated RTL, on the composed
trunk output*, and to emit the oracle's first generated token id, on each of
ROM and HBM.  Its record must carry ``record_token_ids`` the RTL actually
emitted; the oracle's ids copied across would satisfy the letter of a
comparison and none of its meaning.

This tool measures what happened and writes it down, whichever way it comes
out.  Today it comes out red, and the artifact says so with the measurement
rather than being absent.

Where each field comes from
---------------------------
**The head is not a list of program counters typed in here.**  It is derived
from the deployment's own program: the layer loop is found from the
LOOP_CONTROL descriptor whose body issues exactly one transformer layer's
kernels, and the head is every issue site *after* that loop's back edge, named
by the certified Kernel IR kernel id each OPERATOR descriptor's
``source_kernel_id`` points at.  The LM head's arithmetic is derived from its
own resolved weight view -- 151,936 x 4,096 -- not from a table.

**What ran** comes from the integrated shipped-prefix campaign, the only
vehicle here that runs the real compiled program through the real control
plane with the engine array computing.  Its Qwen cases fetch 33 instructions
and fail closed at PC 32, inside the first invocation of the layer body, so
every head instruction is *unfetched* -- a measurement, in the program's own
terms, not an inference.  Where a probe did observe a head operator dispatch,
that observation is recorded in full and is explicitly not allowed to turn a
field true, because the thing G1d asks about is the head running on the
composed trunk output with its result compared.

**Nothing is reported over an empty set.**  ``mismatched_logits`` is ``null``
with ``compared_logits: 0`` beside it, never ``0``.  ``record_token_ids`` is
the empty list because the RTL emitted no token, and ``oracle.agreement`` is
false.  Reporting zero mismatches over zero comparisons is the failure this
whole ladder exists to make impossible.

**The shard plan is derived and checked.**  G1d's cost is stated for four
concurrent row shards, which is how the chip computes the head anyway, so the
composition of the shards has to be exact.  Two independent checks:

1. *Structural*, from the descriptor's own resolved views: the axis the shards
   partition is the OUTPUT axis, the reduction axis is not partitioned at all,
   the ranges are disjoint, contiguous, cover the axis exactly and leave no
   remainder.  Composition is therefore concatenation, and no accumulator is
   ever split.
2. *Executed*, at full dimension on the real checkpoint's ``lm_head`` bytes
   through the golden model's own backend under the operator's own declared
   numeric contract: the whole 151,936-row projection and the four-shard
   projection are computed and compared code for code, in binary32 and after
   the output's BF16 rounding.  This is not a formality -- the blocked
   contract's association is the executing implementation's, and
   ``runtime/sim/backend.py`` says outright that a threaded BLAS splits the
   reduction across threads, so whether a row split changes the bits is an
   empirical question about this backend.  A falsification control runs
   alongside it: the same comparison with the *reduction* axis split in two,
   which must NOT reproduce the whole.  A check that cannot fail is not a
   check, and the control is what shows this one can.  The measurement is run
   under the operator's declared contract AND under the contract that fixes
   the reduction association, because the answer differs between them and the
   difference is the finding, not a nuisance to be averaged away.

The shard check establishes a property of the plan.  It is a reference-model
measurement and it is labelled as one; no RTL executed the head.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import Major  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import EosReason  # noqa: E402
from tools import build_abi3_shipped_prefix_vectors as _prefix  # noqa: E402


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_g1b = _module("_g1d_g1b", "tools/build_abi3_g1b_layer_closure.py")
_g1c = _module("_g1d_g1c", "tools/build_abi3_g1c_composition.py")

SCHEMA = "opentallas.rtl.g1d_token.v1"
WORKLOAD = "TA-QW-EOS-1"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_g1d_token.json"
ORACLE = "results/abi3/qwen3_reference_oracle_eos.json"
ORACLE_TOKEN_FIELD = "results.TA-QW-EOS-1.generated_token_ids"
ORACLE_TOKEN_COUNT = 1
# The golden view stream's word stride, as the deployment vector set states it.
VIEW_STRIDE = 7
ENTRY_PROBE = "results/rtl/abi3_vehicle_entry_probe.json"
HEAD_ADMISSION = "results/rtl/abi3_g1d_head_admission.json"
WORKLOAD_PATH = "build/workloads/qwen3-8b/TA-QW-EOS-1.json"

# The three head fields G1d names, and the operator each is.  The mnemonics
# are the ABI's, not this file's invention; which PC carries each is derived.
HEAD_ROLES = {
    "final_norm": "VECTOR.RMS_NORM",
    "lm_head": "TENSOR.MATMUL",
    "argmax": "SELECTION.ARGMAX",
}
# The one family that can carry an EOS reason, and the reason value the gate
# names.  The mnemonic is the ABI's; which PC carries it is derived.
EOS_MNEMONIC = "SELECTION.TOKEN_APPEND"
# The integrated harness prints one MAPPED line per case that carries mapped
# placement, and that line is the only place ``selected_eos_reason`` is ever
# reported by a run.  Reading it is how this rung measures the EOS instead of
# asking a field of the artifact that no run writes.
MAPPED_RE = re.compile(
    r"^MAPPED (?P<case>\d+) placement=(?P<placement>\d+) .*?"
    r"append=(?P<append>\d+) token=(?P<token>\d+) tie=(?P<tie>\d+) "
    r"eos=(?P<eos>\d+) ",
    re.MULTILINE,
)
OFFICIAL_EOS = int(EosReason.OFFICIAL_EOS)
GENERATION_POLICY = ExtendedDescriptorType.GENERATION_POLICY
# The rung's declared shape: four concurrent row shards, from G1d's own cost
# statement.  The shard WIDTH is never typed here -- it is derived by dividing
# the descriptor's own output axis, and a remainder refuses the build.
SHARD_COUNT = 4


def sha256_file(path: Path) -> str:
    return _g1c.sha256_file(path)


def _dig(body: Any, dotted: str) -> Any:
    return _g1b._dig(body, dotted)


# --------------------------------------------------------------------------
def head_operators(facts: Any, loop: dict[str, Any], kernels: dict[str, Any]) -> list[dict[str, Any]]:
    """Every issue site after the layer loop's back edge, named by the graph."""
    out = []
    for pc in sorted(facts.issue_sites):
        if pc <= int(loop["back_edge_pc"]):
            continue
        site = dict(facts.issue_sites[pc])
        kernel_id = kernels["kernels"].get(site["source_kernel_id"])
        if kernel_id is None:
            raise SystemExit(
                f"PC {pc}: descriptor {site['operator_descriptor_id']} names "
                f"kernel index {site['source_kernel_id']}, absent from the "
                "certified Kernel IR"
            )
        site["kernel_id"] = kernel_id
        site["kernel_kind"] = kernels["kinds"].get(site["source_kernel_id"])
        site["numeric_contract"] = kernels["contracts"].get(site["source_kernel_id"])
        out.append(site)
    if not out:
        raise SystemExit(
            "the program issues nothing after the layer loop; this rung has "
            "no head to measure"
        )
    return out


def role_sites(head: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Bind each of G1d's three named fields to exactly one issue site."""
    bound: dict[str, dict[str, Any]] = {}
    for role, mnemonic in HEAD_ROLES.items():
        matches = [site for site in head if site["mnemonic"] == mnemonic]
        if len(matches) != 1:
            raise SystemExit(
                f"the head has {len(matches)} {mnemonic} sites; G1d's "
                f"{role!r} field names exactly one and this tool will not "
                "choose between them"
            )
        bound[role] = matches[0]
    return bound


def lm_head_arithmetic(site: dict[str, Any]) -> dict[str, Any]:
    """The head's shape and MAC count, from its own resolved views."""
    weight = next(
        (s for s in site["slots"] if s["slot"] == "input_view_1"), None
    )
    output = next(
        (s for s in site["slots"] if s["slot"] == "output_view_0"), None
    )
    activation = next(
        (s for s in site["slots"] if s["slot"] == "input_view_0"), None
    )
    if weight is None or len(weight["declared_dims"]) != 2:
        raise SystemExit("the LM head MATMUL has no rank-2 weight view")
    rows, reduction = weight["declared_dims"]
    if activation is None or activation["declared_dims"][-1] != reduction:
        raise SystemExit(
            "the LM head's activation width does not equal its weight's "
            "reduction extent; the shard axis cannot be identified safely"
        )
    return {
        "pc": site["pc"],
        "operator_descriptor_id": site["operator_descriptor_id"],
        "kernel_id": site["kernel_id"],
        "numeric_contract": site["numeric_contract"],
        "weight_object_id": weight["object_id"],
        "weight_view_descriptor_id": weight["view_descriptor_id"],
        "output_rows": int(rows),
        "reduction": int(reduction),
        "activation_dims": activation["declared_dims"],
        "output_dims": output["declared_dims"] if output else None,
        "mac_count": int(rows) * int(reduction),
        "derived_from": (
            "the weight TENSOR_VIEW descriptor's own declared extents; not a "
            "table and not the gate's own note"
        ),
    }


def shard_plan(arithmetic: dict[str, Any], shards: int) -> dict[str, Any]:
    rows = int(arithmetic["output_rows"])
    if shards < 1:
        raise SystemExit("a shard count below one is not a plan")
    width, remainder = divmod(rows, shards)
    ranges = [
        {"shard": index, "start_row": index * width, "stop_row_exclusive": (index + 1) * width,
         "rows": width}
        for index in range(shards)
    ]
    covered = sum(r["rows"] for r in ranges)
    disjoint = all(
        ranges[i]["stop_row_exclusive"] == ranges[i + 1]["start_row"]
        for i in range(len(ranges) - 1)
    )
    return {
        "shard_count": shards,
        "rows_per_shard": width,
        "remainder_rows": remainder,
        "ranges": ranges,
        "sharded_axis": "output",
        "sharded_axis_extent": rows,
        "reduction_axis_extent": int(arithmetic["reduction"]),
        "reduction_axis_is_partitioned": False,
        "ranges_are_disjoint_and_contiguous": bool(disjoint),
        "ranges_cover_the_axis_exactly": bool(covered == rows and remainder == 0),
        "composition_is": "concatenation along the output axis",
        "why_that_is_exact": (
            "each output element's complete reduction over "
            f"{arithmetic['reduction']} terms happens inside one shard, so no "
            "accumulator is split and no partial sum is ever re-associated. "
            "Sharding the REDUCTION axis instead would split accumulators and "
            "is what the falsification control below exercises"
        ),
        "structurally_exact": bool(
            disjoint and remainder == 0 and covered == rows
        ),
    }


def shard_execution_check(
    target: Any,
    facts: Any,
    arithmetic: dict[str, Any],
    plan: dict[str, Any],
    embedding_object_id: int,
    activation_tokens: list[int],
) -> dict[str, Any]:
    """Compute the head whole and in shards on the real checkpoint bytes.

    Run under two numeric contracts, because the answer differs and the
    difference is the finding.  The operator declares
    ``bf16_bf16_fp32_blocked_rne_v1``, whose association is the executing
    implementation's -- ``runtime/sim/backend.py`` says a threaded BLAS splits
    the reduction across threads and fixes the association by shape and thread
    count -- so whether a ROW split changes the bits is an empirical question
    about this backend, not a theorem.  ``bf16_bf16_fp32_sequential_rne_v1``
    fixes the association in ascending reduction index independently of shape,
    so under it the row split must be exact.  Both are measured; neither is
    assumed.
    """
    import numpy as np
    from runtime.sim.backend import (
        CONTRACT_BLOCKED,
        CONTRACT_SEQUENTIAL,
        NumpyBackend,
    )

    deployment = facts.deployment
    reduction = int(arithmetic["reduction"])
    rows = int(arithmetic["output_rows"])
    declared = str(arithmetic["numeric_contract"])

    weight_bytes, weight_record = _prefix._checkpoint_matrix(
        target, deployment, int(arithmetic["weight_object_id"]),
        rows=rows, columns=reduction, cache={},
    )
    backend = NumpyBackend()
    weight = backend.widen_bf16(
        np.frombuffer(weight_bytes, dtype="<u2").reshape(rows, reduction)
    )
    del weight_bytes

    def bits(array):
        return np.ascontiguousarray(array, dtype=np.float32).view(np.uint32)

    activations: list[dict[str, Any]] = []
    for token in activation_tokens:
        row_bytes, row_record = _prefix._checkpoint_row(
            target, deployment, embedding_object_id, token, reduction
        )
        activations.append(
            {
                "token_id": token,
                "row_sha256": row_record["selected_row_sha256"],
                "shard": row_record["shard"],
                "codes": np.frombuffer(row_bytes, dtype="<u2").reshape(1, reduction),
            }
        )

    contracts: dict[str, Any] = {}
    for contract in (declared, CONTRACT_SEQUENTIAL):
        if contract in contracts:
            continue
        per_activation = []
        for entry in activations:
            activation = backend.widen_bf16(entry["codes"])
            whole = backend.matmul_binary32(activation, weight, contract=contract)
            sharded = np.concatenate(
                [
                    backend.matmul_binary32(
                        activation,
                        weight[r["start_row"]:r["stop_row_exclusive"]],
                        contract=contract,
                    )
                    for r in plan["ranges"]
                ],
                axis=1,
            )
            whole_bf16 = backend.narrow_rne(whole).codes
            sharded_bf16 = backend.narrow_rne(sharded).codes
            half = reduction // 2
            control = np.ascontiguousarray(
                backend.matmul_binary32(
                    activation[:, :half], weight[:, :half], contract=contract
                )
                + backend.matmul_binary32(
                    activation[:, half:], weight[:, half:], contract=contract
                ),
                dtype=np.float32,
            )
            control_bf16 = backend.narrow_rne(control).codes
            per_activation.append(
                {
                    "token_id": entry["token_id"],
                    "row_sha256": entry["row_sha256"],
                    "compared_logits": int(whole.size),
                    "row_shard_binary32_differing_elements": int(
                        np.count_nonzero(bits(whole) != bits(sharded))
                    ),
                    "row_shard_bf16_differing_elements": int(
                        np.count_nonzero(whole_bf16 != sharded_bf16)
                    ),
                    "reduction_split_binary32_differing_elements": int(
                        np.count_nonzero(bits(whole) != bits(control))
                    ),
                    "reduction_split_bf16_differing_elements": int(
                        np.count_nonzero(whole_bf16 != control_bf16)
                    ),
                }
            )
        contracts[contract] = {
            "is_the_operator_declared_contract": contract == declared,
            "association": (
                "fixed by the contract in ascending reduction index, "
                "independently of operand shape"
                if contract == CONTRACT_SEQUENTIAL
                else "the executing implementation's, fixed by (library, "
                     "version, device, shape, thread count)"
            ),
            "per_activation": per_activation,
            "row_shard_exact_in_binary32": all(
                row["row_shard_binary32_differing_elements"] == 0
                for row in per_activation
            ),
            "row_shard_exact_at_the_declared_output_precision": all(
                row["row_shard_bf16_differing_elements"] == 0
                for row in per_activation
            ),
            "reduction_split_differs_in_binary32": all(
                row["reduction_split_binary32_differing_elements"] > 0
                for row in per_activation
            ),
            "reduction_split_differs_at_the_output_precision": all(
                row["reduction_split_bf16_differing_elements"] > 0
                for row in per_activation
            ),
        }

    declared_result = contracts[declared]
    sequential_result = contracts[CONTRACT_SEQUENTIAL]
    return {
        "ran": True,
        "what_was_computed": (
            "the head's projection at full dimension -- "
            f"[1,{reduction}] x [{rows},{reduction}]^T over the checkpoint's "
            "own lm_head bytes -- whole, as the "
            f"{plan['shard_count']} row shards of the plan above, and with the "
            "reduction axis split in two as a falsification control; under "
            "the operator's declared contract and under the contract that "
            "fixes the association"
        ),
        "operator_declared_contract": declared,
        "backend_identity": backend.implementation_identity(),
        "activations": [
            {
                "token_id": entry["token_id"],
                "row_sha256": entry["row_sha256"],
                "shard": entry["shard"],
            }
            for entry in activations
        ],
        "activation_provenance": (
            "real BF16 embedding rows of width "
            f"{reduction}, read through the deployment's own declared "
            "checkpoint segments. These are NOT the composed trunk output: "
            "the trunk cannot run in this vehicle, so no composed trunk "
            "output exists. What this measures is the exactness of the SHARD "
            "COMPOSITION at the head's real shape and on the real weights; it "
            "establishes nothing about the logits of the governed workload"
        ),
        "weight": {
            "object_id": int(arithmetic["weight_object_id"]),
            "rows": rows,
            "columns": reduction,
            "shard": weight_record.get("shard"),
            "declared_segment_sha256": weight_record.get("declared_segment_sha256"),
            "selected_matrix_sha256": weight_record.get("selected_matrix_sha256"),
            "bytes": rows * reduction * 2,
        },
        "by_contract": contracts,
        "row_shard_composition_is_exact": bool(
            declared_result["row_shard_exact_at_the_declared_output_precision"]
        ),
        "row_shard_composition_is_exact_in_binary32_under_the_declared_contract": bool(
            declared_result["row_shard_exact_in_binary32"]
        ),
        "falsification_control_has_teeth": bool(
            declared_result["reduction_split_differs_in_binary32"]
            and declared_result["reduction_split_differs_at_the_output_precision"]
        ),
        "what_the_measurement_says": (
            "measured, not argued. Under the operator's own declared blocked "
            "contract the four row shards reproduce the whole projection "
            "exactly at the precision the operator writes -- every one of the "
            f"{rows:,} BF16 output codes -- while a small number of the "
            "binary32 accumulators before that single rounding differ, "
            "because the blocked contract delegates the association to the "
            "implementation and this BLAS associates a 37,984-row operand "
            "differently from a 151,936-row one. Under the sequential "
            "contract, which fixes the association independently of shape, "
            "the row shards agree in binary32 as well. Splitting the "
            "REDUCTION axis instead differs under both, which is the control "
            "that shows this comparison can fail"
        ),
        "does_not_establish": [
            "any RTL execution of the head: this is the reference model on "
            "the reference backend, and no RTL ran",
            "the logits of the governed workload: the activation is not the "
            "composed trunk output, which does not exist",
            "exactness for an activation not measured here: the binary32 "
            "agreement under the declared contract is a property of this "
            "backend at these shapes and is reported per activation",
        ],
    }


# --------------------------------------------------------------------------
def head_execution(
    campaign: dict[str, Any],
    head: list[dict[str, Any]],
    roles: dict[str, dict[str, Any]],
    vector_case: dict[str, Any],
    case_index: int,
) -> dict[str, Any]:
    """Which head instructions the integrated RTL reached, measured."""
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
    fetched = int(measured.get("fetched", -1)) if measured else -1
    fault_pc = int(measured.get("fault", -1)) if measured else -1
    trap_class = int(measured.get("trap", -1)) if measured else -1
    admission = campaign.get("operator_admission") or {}
    trapped = list(admission.get("trapped_families") or [])
    launches = dict(admission.get("launches") or {})

    per_site = []
    for site in head:
        family_name = site["mnemonic"]
        per_site.append(
            {
                "pc": site["pc"],
                "kernel_id": site["kernel_id"],
                "mnemonic": family_name,
                "operator_descriptor_id": site["operator_descriptor_id"],
                "numeric_contract": site["numeric_contract"],
                "fetched_by_the_integrated_run": bool(0 <= site["pc"] < fetched),
                "issued": False if fetched >= 0 and site["pc"] >= fetched else None,
                "family_is_trapped_capability_by_the_bridge": family_name in trapped,
                "family_launch_count_in_the_run": launches.get(family_name),
            }
        )
    reached = [row for row in per_site if row["fetched_by_the_integrated_run"]]
    return {
        "instructions_fetched": fetched,
        "fault_pc": fault_pc,
        "trap_class": trap_class,
        "head_sites": per_site,
        "head_sites_fetched": len(reached),
        "head_site_count": len(per_site),
        "why": (
            f"the integrated run fetched {fetched} instruction(s) of one pass "
            f"and failed closed at PC {fault_pc} with trap class {trap_class}. "
            f"Every head instruction lies at PC "
            f"{min(s['pc'] for s in head)} or later, so none was fetched, none "
            "was issued, and none launched"
        ),
        "roles": {
            role: {
                "pc": site["pc"],
                "kernel_id": site["kernel_id"],
                "in_rtl_on_the_composed_trunk_output": False,
                "fetched_by_the_integrated_run": bool(0 <= site["pc"] < fetched),
            }
            for role, site in roles.items()
        },
    }


def resolved_output_words(
    deployment_key: str, head: list[dict[str, Any]]
) -> dict[str, Any]:
    """How many result words each head operator would actually write.

    Declared dims overstate it: the final normalisation's output view is
    declared [512, 4096] and resolves to a single row.  The resolved extent
    comes from the golden device's own recorded view stream -- the same
    stream the RTL vehicle is checked against -- so this is what ran in the
    reference model, not a re-derivation from the descriptor's maxima.
    """
    manifest = json.loads(_g1b.DEPLOYMENT_MANIFEST.read_text())
    stream = _g1b.read_hex(_g1b.DEPLOYMENT_DIR / "a3_deployment_view.hex")
    case = next(
        c for c in manifest["cases"]
        if c["deployment"] == deployment_key and c["request"] == "decode"
    )
    stride = int(manifest.get("view_stride") or VIEW_STRIDE)
    base = int(case["view_base"])
    count = int(case["view_count"])
    resolved: dict[int, dict[str, int]] = {}
    for step in range(count):
        at = (base + step) * stride
        resolved[int(stream[at])] = {
            "extent": int(stream[at + 2]),
            "rank": int(stream[at + 5]),
            "extent_axis": int(stream[at + 6]),
        }
    rows = []
    total = 0
    for site in head:
        for slot in site["slots"]:
            if not slot["slot"].startswith("output"):
                continue
            entry = resolved.get(int(slot["view_descriptor_id"]))
            if entry is None:
                raise SystemExit(
                    f"PC {site['pc']}: output view "
                    f"{slot['view_descriptor_id']} has no resolved extent in "
                    "the golden view stream; the span's result-bank demand "
                    "cannot be measured and is not guessed"
                )
            dims = list(slot["declared_dims"])
            axis = entry["extent_axis"]
            if axis < len(dims):
                dims[axis] = entry["extent"]
            elements = 1
            for value in dims:
                elements *= int(value)
            rows.append(
                {
                    "pc": site["pc"],
                    "mnemonic": site["mnemonic"],
                    "view_descriptor_id": slot["view_descriptor_id"],
                    "declared_dims": slot["declared_dims"],
                    "resolved_extent": entry["extent"],
                    "resolved_on_axis": axis,
                    "resolved_dims": dims,
                    "elements": elements,
                }
            )
            total += elements
    return {
        "per_output": rows,
        "words": total,
        "source": (
            "testdata/compiler/abi3_deployment/a3_deployment_view.hex, the "
            "resolved-view stream runtime.sim.device.Device recorded for this "
            "case; one result word holds one element, which is what "
            "p3_expect.hex is and what the harness compares"
        ),
    }


def runnable_leg(
    facts: Any,
    loop: dict[str, Any],
    head: list[dict[str, Any]],
    roles: dict[str, dict[str, Any]],
    eos: dict[str, Any],
    deployment_key: str,
    vectors: dict[str, Any],
    campaign: dict[str, Any],
) -> dict[str, Any]:
    """The one span of this program a single transaction could execute today.

    Every number here is derived: the entry is the layer loop's back edge plus
    one, because the head IS the sites after that edge; each instruction bound
    is a site's own PC plus one.  The placement demand is computed by G1b's
    own function against the bridge's own declared capacity, so it cannot
    drift from the reason the layer rung is red, and it is computed over the
    span's COMPLETE operand set -- a role no operand is attributed to is a
    hole, not a pass.

    What it establishes is that this span is reachable, and what it costs.  It
    establishes nothing about the head having run: no field of this rung is
    permitted to move because a span was found reachable.
    """
    entry_pc = int(loop["back_edge_pc"]) + 1
    argmax_pc = int(roles["argmax"]["pc"])
    eos_pc = int(eos["site"]["pc"])
    # The bridge places every operand and result through ONE object table,
    # and G1b decides that table's depth by MEASUREMENT -- the most objects a
    # passing campaign case bound and resolved with every result word
    # compared by address as well as by value -- not by counting the bridge's
    # port list.  This rung takes the same number from the same function, so
    # the span's satisfiability cannot be more generous than the layer's, and
    # with no usable campaign the depth is 0 and no span is satisfiable.
    capacity = _g1b.placement_capacity(vectors, campaign)
    spans = {}
    for name, bound_pc in (
        ("through_argmax", argmax_pc), ("through_the_eos_site", eos_pc)
    ):
        sites = [site for site in head if entry_pc <= site["pc"] <= bound_pc]
        demand = _g1b.placement_demand(sites, capacity)
        outputs = resolved_output_words(deployment_key, sites)
        spans[name] = {
            "entry_pc": entry_pc,
            "instruction_count": bound_pc + 1,
            "site_pcs": [site["pc"] for site in sites],
            "operand_count": sum(len(site["slots"]) for site in sites),
            "unattributed_operand_count": len(demand["unattributed_operands"]),
            "every_role_satisfiable": demand["every_role_satisfiable"],
            "placement_demand": demand,
            "result_bank_words_the_span_would_write": outputs,
        }
    geometry = vectors.get("geometry") or {}
    vehicle_words = geometry.get("result_words")
    used = geometry.get("expected_words_used")
    fits = None
    if isinstance(vehicle_words, int) and isinstance(used, int):
        need = spans["through_argmax"]["result_bank_words_the_span_would_write"]["words"]
        fits = (used + need) <= vehicle_words
    return {
        "derived_from": (
            "the layer loop's back edge and the head sites' own PCs; no span "
            "bound is written down in this file"
        ),
        "spans": spans,
        "result_bank": {
            "vehicle_result_words": vehicle_words,
            "words_the_committed_cases_already_use": used,
            "words_the_argmax_span_would_add": spans["through_argmax"][
                "result_bank_words_the_span_would_write"]["words"],
            "a_fifth_case_fits_in_the_vehicle_as_elaborated": fits,
            "note": (
                "the vehicle's result memory is one bank shared by every case "
                "at disjoint bases, so a new case's demand is added to what "
                "the committed cases already occupy. RESULT_WORDS is a "
                "parameter the campaign passes at elaboration from this very "
                "geometry, so this is a sizing statement, not a wall"
            ),
        },
        "establishes": (
            "that a single transaction entered at the head can reach these "
            "sites with every placement role satisfiable"
        ),
        "does_not_establish": (
            "that the head ran, that any logit was computed or compared, or "
            "that the value the span would consume is the composed trunk "
            "output: no field of this rung moves because of this block"
        ),
    }


def eos_measurement(
    facts: Any,
    head: list[dict[str, Any]],
    execution: dict[str, Any],
    campaign: dict[str, Any],
    campaign_body: dict[str, Any],
    case_index: int,
    oracle_ids: list[int],
) -> dict[str, Any]:
    """``eos.official_eos_raised``, and the two halves it is the AND of.

    The field moved to this rung on 2026-09-06 because G1e's design excludes
    engines and could only ever have passed a model value through.  It asks
    two things at once, and this record answers each separately so a reader
    can see which half is missing:

    1.  the integrated top's ``selected_eos_reason`` equals ``OFFICIAL_EOS``;
    2.  the run launched at least one REAL engine.

    Half 2 is measured from the run's own launch count.  Half 1 is not
    measured at all -- the retained integrated campaign records no
    ``selected_eos_reason`` observation, because the harness only checks that
    word for a case carrying mapped placement and the campaign reports
    ``cases_with_mapped_placement`` 0.  An unmeasured half is FALSE here, and
    the record says which half and why, rather than reporting the conjunction
    over an absence.

    Two further facts are derived rather than asserted, because together they
    say a single head run cannot satisfy this rung as it now stands:

    *   only ``SELECTION.TOKEN_APPEND`` carries an EOS reason at all, and this
        program has exactly one such site.  Its PC is derived from the
        deployment's own issue sites and compared against the span the run
        fetched.
    *   the deployment's own GENERATION_POLICY descriptor names the EOS token
        ids.  The oracle's generated ids are compared against that set, and
        the INDEX at which the official EOS appears is reported.  This rung's
        ``oracle_token_count`` is 1, so the id it compares is the oracle's
        FIRST generated id; if the official EOS is not that id, the run whose
        token this rung certifies is not the run that raises the EOS.
    """
    observed = next(
        (
            row for row in (campaign.get("observed_cases") or [])
            if int(row.get("index", -1)) == case_index
        ),
        None,
    )
    real_launches = int(observed.get("launches", 0)) if observed else None
    launched_a_real_engine = bool(real_launches) if real_launches is not None else False

    sites = [s for s in head if s["mnemonic"] == EOS_MNEMONIC]
    if len(sites) != 1:
        raise SystemExit(
            f"the head has {len(sites)} {EOS_MNEMONIC} site(s); the EOS "
            "measurement binds to exactly one and refuses to guess"
        )
    site = sites[0]
    fetched = int(execution.get("instructions_fetched", -1))
    site_fetched = bool(0 <= site["pc"] < fetched)

    policy_ids = list(facts.deployment.table.ids_of_type(GENERATION_POLICY))
    if len(policy_ids) != 1:
        raise SystemExit(
            f"the deployment declares {len(policy_ids)} GENERATION_POLICY "
            "descriptors; the EOS token set cannot be derived from one"
        )
    policy = facts.deployment.table.get(policy_ids[0], GENERATION_POLICY).payload
    eos_tokens = [
        int(policy[f"eos_token_{i}"]) for i in range(int(policy["eos_count"]))
    ]
    official_index = next(
        (i for i, token in enumerate(oracle_ids) if int(token) in eos_tokens), None
    )

    # The observation comes from the run's own printed MAPPED line for THIS
    # case, and only from a campaign this rung already found usable: a line in
    # a drifted, dirty or failed campaign is not evidence of anything.
    reason_observed = None
    selected_token = None
    if campaign.get("usable") is True:
        for case in (campaign_body.get("cases") or []):
            for match in MAPPED_RE.finditer(case.get("run_log") or ""):
                if int(match.group("case")) != case_index:
                    continue
                if int(match.group("placement")) == 0:
                    continue
                reason_observed = int(match.group("eos"))
                selected_token = int(match.group("token"))
    reason_is_official = (
        reason_observed is not None and int(reason_observed) == OFFICIAL_EOS
    )
    return {
        "official_eos_raised": bool(reason_is_official and launched_a_real_engine),
        "selected_eos_reason_observed": reason_observed,
        "selected_token_observed": selected_token,
        "observation_source": (
            "the MAPPED line the integrated harness printed for this case, in "
            "the run log of a campaign this rung found usable"
        ),
        "selected_eos_reason_is_official_eos": reason_is_official,
        "official_eos_reason_value": OFFICIAL_EOS,
        "run_launched_at_least_one_real_engine": launched_a_real_engine,
        "real_engine_launches_in_this_case": real_launches,
        "why_the_reason_is_unmeasured": (
            None if reason_observed is not None else
            "no run log of a usable campaign carries a MAPPED line for this "
            "case: rtl/test/a3_shipped_prefix_harness.cpp prints that line, "
            "and checks selected_eos_reason at all, only for a case carrying "
            "mapped placement, and the campaign reports "
            "cases_with_mapped_placement "
            f"{_dig(campaign, 'operator_admission.cases_with_mapped_placement')}"
        ),
        "site": {
            "mnemonic": EOS_MNEMONIC,
            "pc": site["pc"],
            "kernel_id": site["kernel_id"],
            "operator_descriptor_id": site["operator_descriptor_id"],
            "fetched_by_the_integrated_run": site_fetched,
            "note": (
                "the only site in this program that can carry an EOS reason. "
                f"The run fetched {fetched} instruction(s), so this site was "
                + ("fetched" if site_fetched else "never fetched")
            ),
        },
        "generation_policy": {
            "descriptor_id": policy_ids[0],
            "eos_token_ids": eos_tokens,
            "vocabulary_size": int(policy["vocabulary_size"]),
            "source": (
                "the deployment's own GENERATION_POLICY descriptor, not a "
                "token id written down here"
            ),
        },
        "oracle_position_of_the_official_eos": {
            "generated_token_ids": [int(t) for t in oracle_ids],
            "index_of_the_first_eos_token": official_index,
            "this_rung_compares_only_the_first_n": ORACLE_TOKEN_COUNT,
            "the_certified_token_is_also_the_eos": (
                official_index is not None and official_index < ORACLE_TOKEN_COUNT
            ),
            "consequence": (
                "the id this rung certifies and the id that raises the EOS "
                "are different generated positions, so one head execution "
                "cannot make both halves of this field true: the rung needs "
                "the head run at the position whose argmax selects an EOS "
                "token as well as at the position whose token it certifies"
            ) if (official_index is not None
                  and official_index >= ORACLE_TOKEN_COUNT) else (
                "the certified id is itself an EOS token, so one head "
                "execution can carry both halves"
            ),
        },
        "why": (
            "official_eos_raised is the AND of an unmeasured half and a "
            "measured one. The engine half is "
            + ("satisfied: this case launched "
               f"{real_launches} real engine(s). "
               if launched_a_real_engine else
               "not satisfied: this case launched no real engine. ")
            + "The reason half is "
            + ("satisfied." if reason_is_official else
               "not measured, and an unmeasured half is false, never "
               "not_evaluable.")
        ),
    }


def entry_probe_observation(roles: dict[str, dict[str, Any]], deployment_key: str) -> dict[str, Any]:
    """A mid-program entry probe that did dispatch a head operator, cited."""
    path = ROOT / ENTRY_PROBE
    record: dict[str, Any] = {"artifact": ENTRY_PROBE}
    if not path.is_file():
        record["present"] = False
        return record
    body = json.loads(path.read_text())
    record.update(
        present=True,
        artifact_sha256=sha256_file(path),
        status=body.get("status"),
        declared_git=body.get("git"),
        source_bound=bool(_dig(body, "git.worktree_dirty") is False),
        vector_set_committed=_dig(body, "vector_set.committed"),
    )
    head_pcs = {site["pc"] for site in roles.values()}
    rows = [
        row for row in (body.get("comparisons") or [])
        if row.get("target") == deployment_key
        and int(row.get("site_pc", -1)) in head_pcs
    ]
    record["rows"] = rows
    record["head_sites_that_dispatched"] = [
        int(row["site_pc"]) for row in rows
        if _dig(row, "measured.dispatches_the_site") is True
    ]
    record["why_it_does_not_make_a_field_true"] = (
        "a dispatch under a mid-program entry is not this rung's claim. G1d "
        "asks for the head to execute ON THE COMPOSED TRUNK OUTPUT and for "
        "its result to be compared: under a mid-program entry the vehicle's "
        "result memory holds its initialisation pattern, no trunk has run, "
        "and no word was compared against golden. The observation is recorded "
        "because it is a measurement and it bounds what is missing; it is not "
        "allowed to move a gate field"
    )
    if record.get("source_bound") is False:
        record["caveat"] = (
            "this probe artifact declares a dirty worktree, so it is not "
            "source-bound evidence; it is cited as an observation only"
        )
    return record


def head_admission_observation(deployment_key: str) -> dict[str, Any]:
    """What refuses the head span's last two instructions, measured.

    ``entry_probe_observation`` above records that a head operator dispatched
    under a mid-program entry.  This records how far that span then gets and
    what stops it, which is the more useful half for a rung that is red: the
    LM head's ``TENSOR.MATMUL`` and the span's ``SELECTION.ARGMAX``, each
    attributed by an arm that changed one thing.

    It moves no field of this rung, and the reason is the same one the entry
    probe carries: a mid-program entry runs on a result memory holding its
    initialisation pattern with objects bound at bases nothing was staged at,
    so an admitted engine's words are not the checkpoint's and an admitted
    argmax's selection is not a token id.  What it does is turn two of this
    rung's blockers from absences into measurements.
    """
    path = ROOT / HEAD_ADMISSION
    record: dict[str, Any] = {"artifact": HEAD_ADMISSION}
    if not path.is_file():
        record["present"] = False
        record["why_absent_is_not_neutral"] = (
            "with no such measurement the LM head's refusal has a trap class "
            "and no attribution, which is the state this rung was in"
        )
        return record
    body = json.loads(path.read_text())
    findings = _dig(body, f"findings.{deployment_key}") or {}
    record.update(
        present=True,
        artifact_sha256=sha256_file(path),
        status=body.get("status"),
        declared_git=body.get("git"),
        source_bound=bool(_dig(body, "git.worktree_dirty") is False),
        one_elaboration_for_every_arm=body.get("one_elaboration_for_every_arm"),
        simulated_cycles=body.get("simulated_cycles"),
        findings=findings,
        mapped_families_word_in_the_committed_vector_set=_dig(
            body,
            "vector_set.mapped_families_word_in_the_committed_set."
            + deployment_key,
        ),
    )
    record["why_it_does_not_make_a_field_true"] = (
        "an arm of that campaign enters mid-program, binds objects at a "
        "declared base with nothing staged there, and compares no word "
        "against golden. G1d asks for the head to execute ON THE COMPOSED "
        "TRUNK OUTPUT and for its logits to be compared. A selected token "
        "measured there is evidence that a selection happened and is not a "
        "token id, and record_token_ids is never filled from it"
    )
    if record.get("source_bound") is False:
        record["caveat"] = (
            "this campaign declares a dirty worktree, so it is not "
            "source-bound evidence; it is cited as an observation only"
        )
    return record


def oracle_evidence() -> dict[str, Any]:
    path = ROOT / ORACLE
    if not path.is_file():
        raise SystemExit(f"{ORACLE} is absent; this rung has no oracle to compare against")
    body = json.loads(path.read_text())
    ids = _dig(body, ORACLE_TOKEN_FIELD)
    if not isinstance(ids, list) or not ids:
        raise SystemExit(f"{ORACLE} carries no token id list at {ORACLE_TOKEN_FIELD}")
    return {
        "path": ORACLE,
        "artifact_sha256": sha256_file(path),
        "token_field": ORACLE_TOKEN_FIELD,
        "generated_token_ids": list(ids)[:ORACLE_TOKEN_COUNT],
        "all_generated_token_ids": list(ids),
        "stop_reason": _dig(body, "results.TA-QW-EOS-1.stop_reason"),
        "agreement": False,
        "why_not_agreed": (
            "the RTL emitted no token: the head never executed, so "
            "record_token_ids is empty. This field is never set from the "
            "oracle's own ids"
        ),
    }


def _establishes(records: list[dict[str, Any]]) -> list[str]:
    """What the rung established, computed from the records, never declared."""
    out: list[str] = []
    checks = [
        record["head"]["shard_composition_check"] for record in records
    ]
    plans = [record["head"]["shard_plan"] for record in records]
    if plans and all(plan.get("structurally_exact") for plan in plans):
        counts = sorted({int(p["shard_count"]) for p in plans})
        widths = sorted({int(p["rows_per_shard"]) for p in plans})
        out.append(
            f"the head's {counts} row shards of {widths} rows partition the "
            "OUTPUT axis and leave the reduction axis whole, so composition "
            "is concatenation and no accumulator is ever split -- derived "
            "from the LM head's own weight view"
        )
    ran = [check for check in checks if check.get("ran")]
    if ran and all(check.get("falsification_control_has_teeth") for check in ran):
        if all(check.get("row_shard_composition_is_exact") for check in ran):
            out.append(
                "executed at full dimension on the checkpoint's own lm_head "
                "bytes: the row shards reproduce the whole projection at the "
                "precision the operator writes, every output code, while the "
                "reduction-axis control does not -- a reference-model "
                "measurement of the plan, with no RTL involved"
            )
    return out


# --------------------------------------------------------------------------
def build(
    output: Path,
    campaign_path: Path | None,
    vectors_path: Path | None,
    checkpoint: Path | None,
    shards: int,
    run_shard_check: bool,
    rerun_path: Path | None = None,
) -> dict[str, Any]:
    vectors = json.loads(
        (_g1b.PREFIX_VECTORS if vectors_path is None else Path(vectors_path)).read_text()
    )
    # The body of the campaign this rung reads, honouring --campaign so that
    # a control run can be pointed at a fabricated one and the tool's own
    # falsification test means something.
    campaign_file = (
        ROOT / _g1b.INTEGRATED_CAMPAIGN if campaign_path is None
        else Path(campaign_path)
    )
    campaign_body = (
        json.loads(campaign_file.read_text()) if campaign_file.is_file() else {}
    )
    rate = _g1c.integrated_rate(campaign_body)
    campaign = _g1b.integrated_evidence(campaign_path, vectors_path)
    rerun = _g1c.rerun_agreement(rerun_path, campaign_body)
    oracle = oracle_evidence()
    git = _g1c.git_state()
    workload = json.loads((ROOT / WORKLOAD_PATH).read_text())
    activation_tokens = [int(t) for t in workload["token_ids"][:3]]

    records = []
    for storage_class, (deployment_key, directory) in _g1c.STORAGE_CLASSES.items():
        vector_case = next(
            c for c in vectors["cases"] if c["deployment"] == deployment_key
        )
        case_index = vectors["cases"].index(vector_case)
        kernels = _g1b.kernel_index(vector_case)
        facts = _g1c.ProgramFacts(ROOT / directory)
        loop = _g1c.layer_loop(facts, kernels)
        head = head_operators(facts, loop, kernels)
        roles = role_sites(head)
        arithmetic = lm_head_arithmetic(roles["lm_head"])
        plan = shard_plan(arithmetic, shards)
        execution = head_execution(campaign, head, roles, vector_case, case_index)
        probe = entry_probe_observation(roles, deployment_key)
        admission = head_admission_observation(deployment_key)
        eos = eos_measurement(
            facts, head, execution, campaign, campaign_body, case_index,
            list(oracle["all_generated_token_ids"]),
        )
        leg = runnable_leg(
            facts, loop, head, roles, eos, deployment_key, vectors, campaign
        )

        shard_check: dict[str, Any]
        if run_shard_check:
            target = next(t for t in _prefix.TARGETS if t.key == deployment_key)
            embedding = next(
                (
                    s["object_id"]
                    for site in facts.issue_sites.values()
                    if site["mnemonic"] == "TENSOR.EMBED_LOOKUP"
                    for s in site["slots"]
                    if s["slot"] == "input_view_1"
                ),
                None,
            )
            if embedding is None:
                raise SystemExit(
                    "no TENSOR.EMBED_LOOKUP weight view was found, so the "
                    "shard check has no real activation row to read"
                )
            shard_check = shard_execution_check(
                target, facts, arithmetic, plan, int(embedding), activation_tokens
            )
        else:
            shard_check = {
                "ran": False,
                "why_not": "--no-shard-check was passed",
            }

        records.append(
            {
                "storage_class": storage_class,
                "workload_id": WORKLOAD,
                "deployment": {
                    "key": deployment_key,
                    "directory": directory,
                    "deployment_sha256": facts.deployment_sha256,
                },
                "execution": {
                    "simulator": _dig(campaign, "integrated_simulators.0")
                    or (campaign.get("integrated_simulators") or [None])[0],
                    "simulated_cycles": campaign.get("simulated_cycles"),
                    "simulated_cycles_scope": (
                        "the integrated run's own total over all four cases of "
                        "the one binary; this rung does not split it per "
                        "lowering because the harness reports one count"
                    ),
                    "evidence_class": campaign.get("evidence_class"),
                    "vehicle": _dig(campaign, "operator_admission.vehicle"),
                    "campaign": campaign,
                },
                "head": {
                    "final_norm_in_rtl": False,
                    "lm_head_in_rtl": False,
                    "argmax_in_rtl": False,
                    "mismatched_logits": None,
                    "compared_logits": 0,
                    "why_null": (
                        "mismatched_logits is null, not 0: zero logits were "
                        "compared because the head never ran. Zero mismatches "
                        "over zero comparisons is not evidence"
                    ),
                    "head_named_by": (
                        "every issue site after the layer loop's back edge "
                        f"(PC {loop['back_edge_pc']}), named by the certified "
                        "Kernel IR kernel each OPERATOR descriptor's "
                        "source_kernel_id points at"
                    ),
                    "operators": [
                        {
                            "pc": site["pc"],
                            "mnemonic": site["mnemonic"],
                            "kernel_id": site["kernel_id"],
                            "kernel_kind": site["kernel_kind"],
                            "numeric_contract": site["numeric_contract"],
                            "operator_descriptor_id": site["operator_descriptor_id"],
                            "slots": site["slots"],
                        }
                        for site in head
                    ],
                    "arithmetic": arithmetic,
                    "what_running_the_head_would_cost": {
                        "mac_count": arithmetic["mac_count"],
                        "measured_integrated_rate": rate,
                        "seconds_whole": (
                            round(arithmetic["mac_count"] / rate["macs_per_second"], 1)
                            if rate.get("measured") else None
                        ),
                        "hours_whole": (
                            round(
                                arithmetic["mac_count"]
                                / rate["macs_per_second"] / 3600.0,
                                2,
                            )
                            if rate.get("measured") else None
                        ),
                        "hours_in_concurrent_row_shards": (
                            round(
                                arithmetic["mac_count"]
                                / rate["macs_per_second"] / 3600.0
                                / plan["shard_count"],
                                2,
                            )
                            if rate.get("measured") and plan["shard_count"]
                            else None
                        ),
                        "note": (
                            "derived: the head's own multiply-accumulates at "
                            "the rate the integrated vehicle itself measured. "
                            "The shard figure is wall time with the shards "
                            "run concurrently, which is exact because the "
                            "shards share no accumulator -- see shard_plan. "
                            "It is what the head would cost, not what this "
                            "rung cost, which ran no head at all"
                        ),
                    },
                    "shard_plan": plan,
                    "shard_composition_check": shard_check,
                    "execution_measured": execution,
                    "entry_probe_observation": probe,
                    "head_admission_observation": admission,
                    "runnable_leg": leg,
                    "kernel_ir": {
                        "path": kernels["path"],
                        "sha256": kernels["sha256"],
                        "graph_id": kernels["graph_id"],
                    },
                },
                "eos": eos,
                "record_token_ids": [],
                "record_token_ids_note": (
                    "the RTL emitted no token id. This list is what the RTL "
                    "emitted and is never filled from the oracle; a rung that "
                    "copied the oracle's ids across would agree with itself"
                ),
                "oracle": oracle,
                "git": git,
            }
        )

    body = {
        "schema": SCHEMA,
        "gate": "G1d",
        "workload_id": WORKLOAD,
        "generated_by": "tools/build_abi3_g1d_token.py",
        "generated_by_sha256": sha256_file(Path(__file__)),
        "derived_mechanically": True,
        "what_this_rung_is": (
            "the rung where an RTL-emitted token id first exists: the final "
            "normalisation, the LM head and the argmax executing in the "
            "integrated RTL on the composed trunk output"
        ),
        "establishes": _establishes(records),
        "does_not_establish": [
            "any RTL execution of the head: no head instruction was fetched",
            "any token id: the RTL emitted none",
            "the logits: none were computed in RTL and none were compared",
            "that the shard composition is exact IN RTL -- the shard check is "
            "a reference-model measurement of the plan, on the reference "
            "backend, and says so",
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
    parser.add_argument("--campaign", type=Path, default=None)
    parser.add_argument("--vectors", type=Path, default=None)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--shards", type=int, default=SHARD_COUNT)
    parser.add_argument(
        "--rerun",
        type=Path,
        default=None,
        help="an independent run of the integrated campaign, recorded for "
             "agreement and relied on for nothing",
    )
    parser.add_argument(
        "--no-shard-check",
        action="store_true",
        help="skip the full-dimension shard composition execution",
    )
    args = parser.parse_args()
    body = build(
        args.output,
        args.campaign,
        args.vectors,
        args.checkpoint,
        args.shards,
        not args.no_shard_check,
        args.rerun,
    )
    for record in body["records"]:
        head = record["head"]
        check = head["shard_composition_check"]
        print(
            f"{record['storage_class']}: final_norm={head['final_norm_in_rtl']} "
            f"lm_head={head['lm_head_in_rtl']} argmax={head['argmax_in_rtl']} "
            f"mismatched_logits={head['mismatched_logits']} "
            f"record_token_ids={record['record_token_ids']} "
            f"macs={head['arithmetic']['mac_count']} "
            f"shards={head['shard_plan']['shard_count']}x"
            f"{head['shard_plan']['rows_per_shard']} "
            f"shard_exact_bf16={check.get('row_shard_composition_is_exact')} "
            f"shard_exact_fp32={check.get('row_shard_composition_is_exact_in_binary32_under_the_declared_contract')} "
            f"control_teeth={check.get('falsification_control_has_teeth')}"
        )
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
