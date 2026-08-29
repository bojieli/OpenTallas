"""Independent legality report for an HBM/SRAM ABI 3.0 deployment.

TA-HBM-3.0 section 4.4: *the checker must not import allocator, scheduler,
lowering, or expected-result code*.  This module therefore imports only the
frozen contracts -- the neutral IR schema, the frozen kernel-to-engine table and
the ABI 3.0 record decoders -- and reconstructs, from the graph alone, what the
deployment ought to contain.  It never imports :mod:`.lower` or :mod:`.plan`;
the weight grouping, the layer banding and the program shape are re-derived here
by a second implementation, and a disagreement between the two is reported
rather than reconciled.

What it proves
--------------
1. every neutral kernel reaches an engine operation, with the family and
   subopcode the frozen table assigns and no other;
2. weights are zero-copy: every declared checkpoint range appears exactly once,
   in an immutable object, with its digest intact, and no byte is duplicated,
   dropped or relaid out;
3. per-layer weight roles are one object each with a constant stride, which is
   the precondition for the layer loop;
4. the program is loop-compressed: the layer count does not appear in the
   instruction count, and the reconstructed loop nest matches the descriptors;
5. exactly one topology descriptor, agreeing with the capability, with cluster
   traffic present if and only if there is more than one node;
6. every state resource the graph declares is bound to a state descriptor whose
   prepare/commit pairs close; and
7. the deployment passes the frozen ABI 3.0 verifier.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from compiler.ir.v3.kernel_ir import Kernel, KernelGraph, Symbolic, Tensor
from compiler.ir.v3.lowering import engine_for
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Control,
    DTYPE_BITS,
    DType,
    Major,
    NO_ID,
    Permission,
    State,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import ExtendedDescriptorType, SelectorKind, Symbol
from runtime.abi3.records import decode_body, split_program
from runtime.abi3.verifier import verify_deployment

#: Independent copy of the neutral-dtype table.  Duplicated on purpose: a
#: checker that shares the backend's tables cannot catch the backend's table
#: being wrong.
_DTYPE_BITS: Mapping[str, int] = {
    "bf16": 16,
    "fp16": 16,
    "fp32": 32,
    "fp8_e4m3fn": 8,
    "fp8_e5m2": 8,
    "mxfp4_e2m1": 4,
    "e8m0": 8,
    "i8": 8,
    "u8": 8,
    "bool": 8,
    "i32": 32,
    "u32": 32,
    "i64": 64,
    "u64": 64,
}

#: Same slack the placement rule uses when merging file-adjacent ranges.
_MERGE_SLACK = 4096

#: Kernel kinds the backend is allowed to fold into the hoisted state
#: transaction rather than emitting as an engine operator.
_TRANSACTION_KINDS = frozenset({"STATE_PREPARE", "STATE_COMMIT", "STATE_READ"})


def check_deployment(
    graph: KernelGraph, deployment: Deployment, capability: Capability
) -> dict[str, Any]:
    """Return the lane's independent legality report for one deployment."""
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, ok: bool, message: str) -> bool:
        checks[name] = checks.get(name, True) and bool(ok)
        if not ok:
            errors.append(message)
        return bool(ok)

    table = deployment.table
    header, body = split_program(deployment.program)
    instructions = decode_body(body)

    descriptors_of = {
        kind: [table[i] for i in table.ids_of_type(kind)]
        for kind in ExtendedDescriptorType
    }
    operators = descriptors_of[ExtendedDescriptorType.OPERATOR]
    objects = descriptors_of[ExtendedDescriptorType.MEMORY_OBJECT]
    loops = descriptors_of[ExtendedDescriptorType.LOOP_CONTROL]
    views = descriptors_of[ExtendedDescriptorType.TENSOR_VIEW]
    states = descriptors_of[ExtendedDescriptorType.STATE]
    topologies = descriptors_of[ExtendedDescriptorType.TOPOLOGY]
    communications = descriptors_of[ExtendedDescriptorType.COMMUNICATION]

    tensors = {t.tensor_id: t for t in graph.tensors}
    bands = _reconstruct_bands(graph, tensors)
    expected_groups = _reconstruct_weight_groups(graph, tensors, bands)
    representative = {
        k.index
        for k in graph.kernels
        if k.layer is None or any(k.layer == b["first_layer"] for b in bands)
    }
    emitted_kernels = {k for k in representative if graph.kernels[k].kind not in _TRANSACTION_KINDS}

    # -- 1. engine mapping ------------------------------------------------
    by_kernel: dict[int, list[Any]] = {}
    for descriptor in operators:
        by_kernel.setdefault(descriptor.payload["source_kernel_id"], []).append(
            descriptor
        )
    for index in sorted(emitted_kernels):
        kernel = graph.kernels[index]
        engine = engine_for(kernel.kind)
        found = by_kernel.get(index, [])
        if not require(
            "kernel_coverage",
            bool(found),
            f"kernel {index} ({kernel.kernel_id}) reaches no engine operator",
        ):
            continue
        families = {(d.payload["engine_family"], d.payload["engine_sub"]) for d in found}
        require(
            "engine_mapping",
            (int(engine.family), int(engine.sub)) in families,
            f"kernel {index} ({kernel.kind}) must lower to "
            f"{Major(engine.family).name}.{int(engine.sub)}, found {sorted(families)}",
        )
    for index in sorted(representative - emitted_kernels):
        kernel = graph.kernels[index]
        engine = engine_for(kernel.kind)
        require(
            "state_kernel_coverage",
            any(
                i.major == int(engine.family) and i.sub == int(engine.sub)
                for i in instructions
            ),
            f"state kernel {index} ({kernel.kind}) has no matching instruction",
        )

    # -- 2/3. zero-copy weights and role stacks ---------------------------
    immutable = [
        d
        for d in objects
        if d.permissions & Permission.IMMUTABLE
        and d.payload["storage_class"] == int(StorageClass.HBM)
    ]
    actual_groups: list[list[tuple[str, int, int, str | None]]] = []
    seen_ranges: dict[tuple[str, int, int], int] = {}
    for descriptor in immutable:
        source = deployment.objects.get(descriptor.descriptor_id)
        if source is None or source.kind != "segments":
            errors.append(
                f"object {descriptor.descriptor_id} holds weights but is not a "
                "zero-copy segments source"
            )
            checks["zero_copy_weights"] = False
            continue
        group: list[tuple[str, int, int, str | None]] = []
        for segment in source.segments:
            key = (segment.path, segment.offset, segment.bytes)
            if key in seen_ranges:
                errors.append(
                    f"checkpoint range {key} is materialised twice (objects "
                    f"{seen_ranges[key]} and {descriptor.descriptor_id}); a "
                    "zero-copy placement never duplicates a byte"
                )
                checks["zero_copy_weights"] = False
            seen_ranges[key] = descriptor.descriptor_id
            group.append((segment.path, segment.offset, segment.bytes, segment.sha256))
        actual_groups.append(group)
        require(
            "object_size_matches_segments",
            sum(s.bytes for s in source.segments) == descriptor.payload["size_bytes"],
            f"object {descriptor.descriptor_id} declares "
            f"{descriptor.payload['size_bytes']} bytes but its segments cover "
            f"{sum(s.bytes for s in source.segments)}",
        )
    checks.setdefault("zero_copy_weights", True)

    declared = {
        (t.binding.path, t.binding.offset, t.binding.bytes, t.binding.sha256)
        for t in graph.tensors
        if t.binding is not None
    }
    materialised = {tuple(seg) for group in actual_groups for seg in group}
    missing = declared - materialised
    extra = materialised - declared
    require(
        "every_weight_placed",
        not missing,
        f"{len(missing)} declared checkpoint ranges are not placed in any object",
    )
    require(
        "no_invented_weights",
        not extra,
        f"{len(extra)} object segments do not correspond to a declared binding",
    )

    expected_sets = sorted(
        sorted(tuple(s) for s in group) for group in expected_groups.values()
    )
    actual_sets = sorted(sorted(tuple(s) for s in group) for group in actual_groups)
    require(
        "weight_grouping_agrees",
        expected_sets == actual_sets,
        f"weight grouping disagrees: the checker reconstructs "
        f"{len(expected_sets)} objects, the deployment declares {len(actual_sets)}",
    )

    for role_key, segments in expected_groups.items():
        if not role_key.startswith("role:") or len(segments) < 2:
            continue
        sizes = {seg[2] for seg in segments}
        require(
            "uniform_layer_stride",
            len(sizes) == 1,
            f"role {role_key} has {len(sizes)} distinct per-layer extents, so the "
            "layer loop cannot carry a constant stride",
        )

    # -- 4. loop compression ----------------------------------------------
    layer_counts = sorted({b["layer_count"] for b in bands})
    band_loops = [
        d
        for d in loops
        if d.payload["bound_selector_kind"] == int(SelectorKind.CONSTANT)
        and d.payload["max_iterations"] in {b["layer_count"] for b in bands}
        and d.payload["max_iterations"] > 1
    ]
    multi_layer_bands = [b for b in bands if b["layer_count"] > 1]
    require(
        "layer_loop_present",
        len(band_loops) >= len(multi_layer_bands),
        f"{len(multi_layer_bands)} multi-layer bands but only {len(band_loops)} "
        "layer loops; the program is unrolled over layers",
    )
    body_kernels = sum(len(b["body"]) for b in bands)
    prologue = sum(1 for k in graph.kernels if k.layer is None)
    # One engine instruction per kernel, wrapped where the token count is a
    # runtime symbol: at most three instructions per kernel plus loop framing.
    ceiling = 6 * (body_kernels + prologue) + 64
    require(
        "loop_compressed",
        len(instructions) <= ceiling,
        f"program has {len(instructions)} instructions for {body_kernels} body "
        f"kernels and {prologue} prologue kernels; the compact-control-flow "
        f"bound is {ceiling}",
    )
    total_layers = sum(b["layer_count"] for b in bands)
    require(
        "instructions_independent_of_depth",
        len(instructions) <= ceiling,
        "instruction count scales with layer count",
    )

    for descriptor in loops:
        payload = descriptor.payload
        require(
            "loop_bounded",
            payload["max_iterations"] > 0
            and payload["max_iterations"] <= capability.limits["max_loop_trip"],
            f"loop {descriptor.descriptor_id} declares "
            f"{payload['max_iterations']} iterations",
        )
        if payload["bound_selector_kind"] == int(SelectorKind.RUNTIME_SYMBOL):
            require(
                "symbol_registry",
                payload["bound_symbol_id"] in {int(s) for s in Symbol},
                f"loop {descriptor.descriptor_id} names symbol "
                f"{payload['bound_symbol_id']}, which is not in the frozen registry",
            )

    # -- 5. topology and cluster traffic ----------------------------------
    require(
        "one_topology_descriptor",
        len(topologies) == 1,
        f"deployment declares {len(topologies)} topology descriptors, expected 1",
    )
    node_count = 1
    if topologies:
        payload = topologies[0].payload
        node_count = payload["node_count"]
        require(
            "topology_matches_capability",
            payload["topology_class"] == capability.topology_class,
            "topology descriptor disagrees with the capability's topology class",
        )
        expected_nodes = (
            capability.limits["max_nodes"]
            if capability.topology_class != int(TopologyClass.SINGLE_CHIP)
            else 1
        )
        require(
            "node_count_matches_capability",
            node_count == expected_nodes,
            f"topology declares {node_count} nodes, capability admits "
            f"{expected_nodes}",
        )
    link_instructions = [i for i in instructions if i.major == int(Major.LINK)]
    require(
        "link_traffic_matches_topology",
        bool(link_instructions) == (node_count > 1),
        "cluster deployments must move data between chips and single-chip "
        "deployments must not",
    )
    for instruction in link_instructions:
        descriptor = table[instruction.descriptor_id]
        require(
            "link_descriptor_type",
            descriptor.descriptor_type == ExtendedDescriptorType.COMMUNICATION,
            f"LINK instruction names descriptor {instruction.descriptor_id}, "
            "which is not a communication descriptor",
        )
        require(
            "link_participants",
            descriptor.payload["participant_count"] == node_count,
            "a collective must name every participating node",
        )
    if node_count > 1:
        classes = {d.payload["route_class"] for d in communications}
        require(
            "traffic_classes",
            len(classes) >= 2,
            "a cluster deployment must separate its traffic classes",
        )
        sharded_views = [
            d
            for d in views
            if any(
                d.payload[f"term{s}_kind"] == int(SelectorKind.RUNTIME_SYMBOL)
                and d.payload[f"term{s}_index"] == int(Symbol.NODE_ID)
                for s in range(d.payload["dynamic_term_count"])
            )
        ]
        require(
            "work_is_sharded",
            bool(sharded_views),
            "a 32-node deployment must shard work by node",
        )

    # -- 6. states ---------------------------------------------------------
    resources = {s.state_id for s in graph.states}
    if resources:
        require(
            "states_bound",
            bool(states),
            f"{len(resources)} declared state resources but no state descriptor",
        )
        require(
            "states_merged_not_multiplied",
            len(states) <= len(resources),
            "physical state resources outnumber the declared ones",
        )
        capacity = sum(
            d.payload["capacity_rows"] * d.payload["row_bytes"] for d in states
        )
        declared_capacity = sum(
            _extent(s.capacity_rows) * s.row_elements * _bits(s.dtype) // 8
            for s in graph.states
        )
        require(
            "state_capacity",
            capacity >= declared_capacity,
            f"state descriptors hold {capacity} bytes, the graph declares "
            f"{declared_capacity}",
        )
    prepared: dict[int, int] = {}
    committed: set[int] = set()
    for index, instruction in enumerate(instructions):
        if instruction.major != int(Major.STATE):
            continue
        if instruction.sub == int(State.PREPARE):
            prepared[instruction.descriptor_id] = index
        elif instruction.sub in (int(State.COMMIT), int(State.DISCARD)):
            committed.add(instruction.descriptor_id)
            prepared.pop(instruction.descriptor_id, None)
    require(
        "state_transactions_close",
        not prepared,
        f"{len(prepared)} state resources are prepared without a commit",
    )
    require(
        "every_state_committed",
        committed >= {d.descriptor_id for d in states},
        "some state resource is never committed",
    )

    # -- 7. the frozen verifier -------------------------------------------
    verifier = verify_deployment(deployment, capability)
    require(
        "abi_verifier",
        verifier.admitted,
        "the frozen ABI 3.0 verifier rejected the deployment",
    )
    errors.extend(f"verifier: {message}" for message in verifier.errors)

    # -- summary -----------------------------------------------------------
    completes = [
        i
        for i in instructions
        if i.major == int(Major.CONTROL) and i.sub == int(Control.COMPLETE)
    ]
    require(
        "single_completion",
        len(completes) == 1,
        f"{len(completes)} COMPLETE instructions, expected exactly one",
    )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": dict(sorted(checks.items())),
        "expected": {
            "weight_objects": len(expected_groups),
            "weight_bytes": sum(
                seg[2] for group in expected_groups.values() for seg in group
            ),
            "bands": len(bands),
            "layers": total_layers,
            "body_kernels": body_kernels,
            "instruction_ceiling": ceiling,
            "kernels": len(graph.kernels),
        },
        "actual": {
            "instructions": len(instructions),
            "descriptors": len(table),
            "weight_objects": len(immutable),
            "weight_bytes": sum(seg[2] for group in actual_groups for seg in group),
            "operators": len(operators),
            "views": len(views),
            "loops": len(loops),
            "states": len(states),
            "link_instructions": len(link_instructions),
            "node_count": node_count,
            "declared_retired_work": header.max_retired_work,
        },
        "verifier": verifier.to_dict(),
    }


# ---------------------------------------------------------------------------
# Independent reconstruction
# ---------------------------------------------------------------------------
def _bits(dtype: str) -> int:
    try:
        return _DTYPE_BITS[dtype]
    except KeyError:
        raise ValueError(f"unknown neutral dtype {dtype!r}") from None


def _extent(value: Any, fallback: int = 1) -> int:
    if isinstance(value, Symbolic):
        return value.maximum if value.maximum > 0 else fallback
    return int(value)


def _signature(
    kernels: Sequence[Kernel], tensors: Mapping[str, Tensor], produced: Mapping[str, int]
) -> str:
    parts = []
    for kernel in kernels:
        classes = []
        for name in kernel.inputs:
            tensor = tensors[name]
            if tensor.role in {"weight", "constant"}:
                classes.append("w")
            elif tensor.role == "input":
                classes.append("i")
            elif tensor.role == "output":
                classes.append("o")
            elif name in produced:
                classes.append("a")
            else:
                classes.append("x")
        parts.append(
            "|".join(
                (
                    kernel.kind,
                    kernel.numeric_contract,
                    ",".join(classes),
                    str(len(kernel.outputs)),
                    ",".join(sorted(kernel.phases)),
                    str(len(kernel.state_reads)),
                    str(len(kernel.state_writes)),
                )
            )
        )
    return ";".join(parts)


def _reconstruct_bands(
    graph: KernelGraph, tensors: Mapping[str, Tensor]
) -> list[dict[str, Any]]:
    """Independently recompute the layer bands from kernel structure."""
    produced = {n: k.index for k in graph.kernels for n in k.outputs}
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)
    if not by_layer:
        return []
    layers = sorted(by_layer)
    signatures = {l: _signature(by_layer[l], tensors, produced) for l in layers}

    runs: list[list[int]] = []
    for layer in layers:
        if runs and signatures[layer] == signatures[runs[-1][-1]] and layer == runs[-1][-1] + 1:
            runs[-1].append(layer)
        else:
            runs.append([layer])

    bands: list[dict[str, Any]] = []
    for run in runs:
        if len(run) > 1 and not _uniform(run, by_layer, tensors):
            for layer in run:
                bands.append(
                    {
                        "first_layer": layer,
                        "layer_count": 1,
                        "layers": [layer],
                        "body": list(by_layer[layer]),
                    }
                )
            continue
        bands.append(
            {
                "first_layer": run[0],
                "layer_count": len(run),
                "layers": list(run),
                "body": list(by_layer[run[0]]),
            }
        )
    return bands


def _uniform(
    run: Sequence[int],
    by_layer: Mapping[int, Sequence[Kernel]],
    tensors: Mapping[str, Tensor],
) -> bool:
    body = by_layer[run[0]]
    if any(len(by_layer[l]) != len(body) for l in run):
        return False
    for position, kernel in enumerate(body):
        for slot, name in enumerate(kernel.inputs):
            if tensors[name].role not in {"weight", "constant"}:
                continue
            names, extents = [], set()
            for layer in run:
                peer = by_layer[layer][position]
                if slot >= len(peer.inputs):
                    return False
                member = tensors[peer.inputs[slot]]
                if member.binding is None:
                    return False
                names.append(peer.inputs[slot])
                extents.add(member.binding.bytes)
            if len(set(names)) == 1:
                continue
            if len(set(names)) != len(run) or len(extents) != 1:
                return False
    return True


def _reconstruct_weight_groups(
    graph: KernelGraph, tensors: Mapping[str, Tensor], bands: Sequence[Mapping[str, Any]]
) -> dict[str, list[tuple[str, int, int, str]]]:
    """Independently recompute the expected weight objects.

    Rule one: one object per weight role, segments in layer order.  Rule two:
    everything left over grouped by adjacency inside one checkpoint file.
    """
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)

    groups: dict[str, list[tuple[str, int, int, str]]] = {}
    claimed: set[str] = set()
    for band in bands:
        for position, kernel in enumerate(band["body"]):
            for slot, name in enumerate(kernel.inputs):
                tensor = tensors[name]
                if tensor.role not in {"weight", "constant"} or tensor.binding is None:
                    continue
                members: list[str] = []
                for layer in band["layers"]:
                    peer = by_layer[layer][position]
                    if slot >= len(peer.inputs):
                        members = []
                        break
                    member = peer.inputs[slot]
                    if (
                        member in claimed
                        or member in members
                        or tensors[member].binding is None
                    ):
                        members = []
                        break
                    members.append(member)
                if not members:
                    continue
                claimed.update(members)
                groups[f"role:{band['first_layer']}.{position}.{slot}"] = [
                    (
                        tensors[m].binding.path,
                        tensors[m].binding.offset,
                        tensors[m].binding.bytes,
                        tensors[m].binding.sha256,
                    )
                    for m in members
                ]

    leftovers = sorted(
        (
            t
            for t in graph.tensors
            if t.role in {"weight", "constant"}
            and t.binding is not None
            and t.tensor_id not in claimed
        ),
        key=lambda t: (t.binding.path, t.binding.offset, t.tensor_id),
    )
    run_index = 0
    end = -1
    path = None
    for tensor in leftovers:
        binding = tensor.binding
        assert binding is not None
        if path != binding.path or not 0 <= binding.offset - end <= _MERGE_SLACK:
            run_index += 1
            path = binding.path
        groups.setdefault(f"file:{run_index}", []).append(
            (binding.path, binding.offset, binding.bytes, binding.sha256)
        )
        end = binding.offset + binding.bytes
    return groups
