#!/usr/bin/env python3
"""Build an immutable-ROM ABI 3.0 deployment from Tensor Kernel IR v3.

One CLI, two products, one backend family:

    python3 tools/build_rom_deployment.py qwen3-8b \\
        --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \\
        --output build/abi3/qwen3-8b-rom

    python3 tools/build_rom_deployment.py deepseek-v4-flash \\
        --ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \\
        --output build/abi3/deepseek-v4-flash-rom

DeepSeek-V4-Pro-0813 exists ONLY as a 32-node array product, and only from a
short-context IR:

    python3 tools/build_deepseek_v4_kernel_ir_v3.py \\
        --model deepseek-v4-pro-0813 --context-tokens 8192 \\
        --verify-bindings 0 --output <ir>/kernel_ir.v3.json
    python3 tools/build_rom_deployment.py deepseek-v4-pro-array \\
        --ir <ir>/kernel_ir.v3.json --output build/abi3/deepseek-v4-pro-rom-array-32

Two facts travel with that, and neither is a knob:

*   There is no Pro wafer or single-chip ROM product and there cannot be one.
    An unsharded routed expert region needs a per-layer element stride of
    384 x 3072 x 7168 = 8,455,716,864 elements, 1.97x over the 32-bit
    dynamic-term stride field of ABI 3.0 tensor views; only the array's 32-way
    node ownership divides it inside.
*   At the shipped 262,144-position IR the array build is refused --
    ``hbm_and_state objects need 259,278,995,592 bytes but the capability
    declares 180,000,000,000`` -- and at 8,192 it admits.  Context length is
    the lever; the token-block knob is not.  The matched ``--storage-class hbm``
    twin is refused at ANY context (864,068,475,024 bytes per node), so a Pro
    ROM deployment has no comparable HBM counterpart from this backend.

The build is zero copy: no ROM image file is written.  Regions reference
authenticated checkpoint byte ranges, and ``--checkpoint-root`` tells the
inverse proof where to read them from.  ``--verify`` runs the independent ABI
verifier, ``--inverse`` runs the independent reconstruction proof, and
``--determinism`` rebuilds from scratch and requires the two artifacts to be
byte-identical.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from compiler.backends.rom.common.image import DefectRecord, RomCoordinate  # noqa: E402
from compiler.backends.rom.common.inverse import check_rom_inverse  # noqa: E402
from compiler.backends.rom.deepseek_v4 import (  # noqa: E402
    build_deepseek_v4_rom_deployment,
    deepseek_v4_rom_capability,
)
from compiler.backends.rom.deepseek_v4_array import (  # noqa: E402
    PRO_BANK_BYTES,
    PRO_DENSE_BANKS,
    PRO_EXPERT_BANKS,
    PRO_TARGET_ID,
    build_deepseek_v4_array_rom_deployment,
    deepseek_v4_array_rom_capability,
    deepseek_v4_pro_array_rom_capability,
)
from compiler.backends.rom.deepseek_v41_array import (  # noqa: E402
    TARGET_ID as V41_ARRAY_TARGET_ID,
    build_deepseek_v41_array_rom_deployment,
    deepseek_v41_array_rom_capability,
)
from compiler.backends.rom.deepseek_v41 import (  # noqa: E402
    TARGET_ID as V41_WAFER_TARGET_ID,
    build_deepseek_v41_rom_deployment,
    deepseek_v41_rom_capability,
)
from compiler.backends.rom.qwen3 import (  # noqa: E402
    build_qwen3_rom_deployment,
    qwen3_rom_capability,
)
from compiler.backends.rom.qwen3_array import (  # noqa: E402
    NODE_COUNT as QWEN3_ARRAY_NODE_COUNT,
    TARGET_ID as QWEN3_ARRAY_TARGET_ID,
    build_qwen3_array_rom_deployment,
    qwen3_array_rom_capability,
)
from compiler.ir.v3.kernel_ir import KernelGraph, require_neutral  # noqa: E402
from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.constants import StorageClass  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402

PRODUCTS = (
    "qwen3-8b",
    "deepseek-v4-flash",
    "deepseek-v4-flash-array",
    # DeepSeek-V4-Pro-0813 on the same 32-node ROM array.  Pro has NO wafer and
    # NO single-chip ROM product and cannot have one: an unsharded routed
    # expert region needs a per-layer element stride of 8,455,716,864, 1.97x
    # over the 32-bit dynamic-term stride field of ABI 3.0 tensor views, and
    # only 32-way node ownership brings it inside.  See
    # ``deepseek_v4_pro_array_rom_capability`` for the geometry and for the
    # iso-area caveat that travels with it.
    "deepseek-v4-pro-array",
    # DeepSeek-V4.1-Flash on the reticle-class ROM array, plan WP-F.  The node
    # count is derived from the released expert count and the declared NVLink
    # domain size rather than typed: see ``expert_parallel_node_count``.
    "deepseek-v4.1-flash-array",
    # Qwen3-8B on an N-node pipelined ROM array.  The analytical sweep's own
    # design point (``ROM-N5-native-SRAMKV-array-pipeline-x8-romfill``) had no
    # deployment target until this backend: its published capability records
    # collapse the devices into one logical device and say so.  ``--nodes``
    # selects the point; the layer partition is derived from the graph.
    "qwen3-8b-array",
    # DeepSeek-V4.1-Flash on two wafer-scale logical devices, plan WP-E.  There
    # is no V4.1 single-chip product and no one-wafer one: 307.5 GB of weights
    # against a 192 GiB wafer ROM.  The layer partition, the pipeline depth and
    # the cross-wafer payload are all derived from the graph and the capability
    # (``deepseek_v41_stage_plan``), so this CLI passes no geometry.
    "deepseek-v4.1-flash",
)


# ---------------------------------------------------------------------------
# Reading a Tensor Kernel IR v3 document
# ---------------------------------------------------------------------------
def load_kernel_graph(path: Path) -> KernelGraph:
    """Read a neutral Tensor Kernel IR v3 document written by a front end.

    The schema owns its own reader, so a backend that hand-decoded it would be a
    second place for the format to drift.
    """
    graph = KernelGraph.read(Path(path))
    require_neutral(graph)
    return graph


def parse_defects(path: Path | None) -> tuple[DefectRecord, ...]:
    """Read a BIST/DFT defect list, the input to spare activation."""
    if path is None:
        return ()
    body = json.loads(Path(path).read_text())
    records = body["defects"] if isinstance(body, Mapping) else body
    return tuple(
        DefectRecord(
            coordinate=RomCoordinate(
                node_id=int(record.get("node_id", 0)),
                reticle=int(record.get("reticle", 0)),
                tile=int(record.get("tile", 0)),
                bank=int(record.get("bank", 0)),
            ),
            kind=str(record["kind"]),
            index=int(record.get("index", 0)),
            source=str(record.get("source", "bist")),
        )
        for record in records
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def summarise(deployment: Deployment, plan, capability) -> dict[str, Any]:
    header, body = split_program(deployment.program)
    instructions = decode_body(body)
    counts: dict[str, int] = {}
    for descriptor in deployment.table.descriptors():
        name = ExtendedDescriptorType(descriptor.descriptor_type).name
        counts[name] = counts.get(name, 0) + 1
    mutable = sum(
        descriptor.payload["size_bytes"]
        for descriptor in deployment.table.descriptors()
        if descriptor.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
        and descriptor.payload["storage_class"] != int(StorageClass.ROM)
    )
    # Mask-programmed derived constants -- a rotary table, a position range --
    # are immutable ROM bytes with no checkpoint range, so they sit outside the
    # region plan and are reported separately rather than silently missing.
    generated = sum(
        descriptor.payload["size_bytes"]
        for descriptor in deployment.table.descriptors()
        if descriptor.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
        and descriptor.payload["storage_class"] == int(StorageClass.ROM)
        and deployment.objects[descriptor.descriptor_id].kind == "generated"
    )
    topology = next(
        (
            d.payload
            for d in deployment.table.descriptors()
            if d.descriptor_type == ExtendedDescriptorType.TOPOLOGY
        ),
        {},
    )
    return {
        "backend": deployment.backend,
        "capability_digest": capability.digest,
        "deployment_sha256": deployment.deployment_digest.hex(),
        "descriptor_count": len(deployment.table),
        "descriptors_by_type": dict(sorted(counts.items())),
        "instruction_count": len(instructions),
        "largest_region_bytes": plan.largest_region_bytes,
        "loop_count": sum(
            1 for i in instructions if i.major == 0x00 and i.sub == 0x02
        ),
        "max_retired_work": header.max_retired_work,
        "model_id": deployment.model_id,
        "mutable_state_bytes": mutable,
        "notes": {
            key: deployment.notes[key]
            for key in sorted(deployment.notes)
            if key != "rom_plan"
        },
        "plan_id": plan.to_dict()["plan_id"],
        "product": plan.product,
        "quarantined_resources": len(plan.repair_map.quarantine),
        "region_count": plan.region_count,
        "rom_generated_bytes": generated,
        "rom_padding_bytes": plan.padding_bytes,
        "rom_payload_bytes": plan.payload_bytes,
        "rom_resource_count": plan.resource_count,
        "rom_total_bytes": plan.rom_bytes,
        "source_kernel_count": deployment.notes.get("rom_lowering", {}).get(
            "source_kernel_count"
        ),
        "spare_rows_activated": plan.repair_map.to_dict()["spare_rows_used"],
        "target_id": deployment.target_id,
        "topology": {
            "class": topology.get("topology_class"),
            "epoch": topology.get("epoch"),
            "link_count": topology.get("link_count"),
            "node_count": topology.get("node_count"),
            "reticle_count": topology.get("reticle_count"),
            "tiles_per_reticle": topology.get("tiles_per_reticle"),
        },
    }


def override_capability(args) -> Any:
    """Read a ``--capability`` record, or return None when none was given.

    The record is read through ``Capability.from_dict`` rather than compared
    field by field: the digest the deployment stamps is a function of the
    parsed object, and a hand-rolled reader would be a second place for the
    capability format to drift.
    """
    path = getattr(args, "capability", None)
    if path is None:
        return None
    return Capability.from_dict(json.loads(Path(path).read_text()))


def build(product: str, graph: KernelGraph, args) -> tuple[Deployment, Any, Any]:
    defects = parse_defects(args.defects)
    storage = StorageClass.HBM if args.storage_class == "hbm" else StorageClass.ROM
    supplied = override_capability(args)
    if product == "qwen3-8b":
        capability = supplied or qwen3_rom_capability()
        deployment, plan = build_qwen3_rom_deployment(
            graph,
            **({"target_id": args.target_id} if args.target_id else {}),
            capability=capability,
            defects=defects,
            weight_storage_class=storage,
        )
    elif product == "qwen3-8b-array":
        nodes = int(getattr(args, "nodes", None) or QWEN3_ARRAY_NODE_COUNT)
        capability = supplied or qwen3_array_rom_capability(node_count=nodes)
        deployment, plan = build_qwen3_array_rom_deployment(
            graph,
            capability=capability,
            node_count=int(capability.limits.get("max_nodes", nodes)),
            defects=defects,
            weight_storage_class=storage,
            epoch=args.epoch,
            target_id=args.target_id or QWEN3_ARRAY_TARGET_ID,
        )
    elif product == "deepseek-v4-flash-array":
        capability = supplied or deepseek_v4_array_rom_capability()
        deployment, plan = build_deepseek_v4_array_rom_deployment(
            graph,
            capability=capability,
            defects=defects,
            weight_storage_class=storage,
            epoch=args.epoch,
        )
    elif product == "deepseek-v4.1-flash-array":
        capability = supplied or deepseek_v41_array_rom_capability()
        deployment, plan = build_deepseek_v41_array_rom_deployment(
            graph,
            capability=capability,
            defects=defects,
            weight_storage_class=storage,
            epoch=args.epoch,
            target_id=args.target_id or V41_ARRAY_TARGET_ID,
        )
    elif product == "deepseek-v4.1-flash":
        capability = supplied or deepseek_v41_rom_capability()
        deployment, plan = build_deepseek_v41_rom_deployment(
            graph,
            capability=capability,
            defects=defects,
            weight_storage_class=storage,
            epoch=args.epoch,
            target_id=args.target_id or V41_WAFER_TARGET_ID,
        )
    elif product == "deepseek-v4-pro-array":
        capability = supplied or deepseek_v4_pro_array_rom_capability()
        deployment, plan = build_deepseek_v4_array_rom_deployment(
            graph,
            capability=capability,
            defects=defects,
            weight_storage_class=storage,
            epoch=args.epoch,
            bank_bytes=PRO_BANK_BYTES,
            expert_banks=PRO_EXPERT_BANKS,
            dense_banks=PRO_DENSE_BANKS,
            target_id=PRO_TARGET_ID,
        )
    else:
        capability = supplied or deepseek_v4_rom_capability()
        deployment, plan = build_deepseek_v4_rom_deployment(
            graph,
            capability=capability,
            defects=defects,
            weight_storage_class=storage,
            epoch=args.epoch,
        )
    return deployment, plan, capability


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product", choices=PRODUCTS)
    parser.add_argument("--ir", type=Path, required=True, help="Tensor Kernel IR v3")
    parser.add_argument("--output", type=Path, help="deployment bundle directory")
    parser.add_argument(
        "--checkpoint-root",
        type=Path,
        help="directory the checkpoint bindings' paths are relative to",
    )
    parser.add_argument("--defects", type=Path, help="BIST/DFT defect list (JSON)")
    parser.add_argument("--epoch", type=int, default=1, help="wafer health epoch")
    parser.add_argument(
        "--storage-class",
        choices=("rom", "hbm"),
        default="rom",
        help="weight storage class; 'hbm' builds the comparison deployment from "
        "the identical program and is only for the ROM-versus-HBM protocol",
    )
    parser.add_argument(
        "--capability",
        type=Path,
        help=(
            "compile against this capability record instead of the product's "
            "own.  The deployment's stamped capability_digest is what "
            "run_abi3_cycle.py admits against, so a cycle run on a DERIVED "
            "machine (tools/derive_cycle_machine.py) needs the deployment "
            "rebuilt against that machine's capability.  The record must still "
            "admit the product's program: this overrides the machine, never "
            "the lowering."
        ),
    )
    parser.add_argument(
        "--nodes",
        type=int,
        help=(
            "node count for a product whose node count is a design point rather "
            "than a fixed geometry (qwen3-8b-array). Ignored by every other "
            "product, whose node count is derived or frozen"
        ),
    )
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--inverse", action="store_true")
    parser.add_argument("--determinism", action="store_true")
    parser.add_argument(
        "--target-id",
        default=None,
        help=(
            "override the backend's target id. The reduced regression "
            "configuration lowers through the same backend as the shipped one and "
            "must be distinguishable from it: the RTL vector builder keys a target "
            "by this id and refuses two deployments claiming the same one."
        ),
    )
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    args = parser.parse_args(argv)

    graph = load_kernel_graph(args.ir)
    deployment, plan, capability = build(args.product, graph, args)
    report = summarise(deployment, plan, capability)

    if args.output:
        deployment.write(args.output)
        report["output"] = str(args.output)

    if args.verify:
        verification = verify_deployment(deployment, capability)
        report["verification"] = verification.to_dict()
        if not verification.admitted:
            print(json.dumps(report, indent=2, sort_keys=True))
            return 2

    if args.inverse:
        root = args.checkpoint_root or args.ir.parent
        report["inverse"] = check_rom_inverse(deployment, root=root)

    if args.determinism:
        again, again_plan, _ = build(args.product, graph, args)
        report["determinism"] = {
            "descriptor_table_identical": again.table.encode()
            == deployment.table.encode(),
            "manifest_identical": canonical_json(again.manifest())
            == canonical_json(deployment.manifest()),
            "plan_identical": again_plan.to_dict() == plan.to_dict(),
            "program_identical": again.program == deployment.program,
        }
        if not all(report["determinism"].values()):
            print(json.dumps(report, indent=2, sort_keys=True))
            return 3

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0


def _print_human(report: Mapping[str, Any]) -> None:
    print(f"product            {report['product']}")
    print(f"target             {report['target_id']} ({report['backend']})")
    print(f"model              {report['model_id']}")
    print(f"instructions       {report['instruction_count']}")
    print(f"  from kernels     {report['source_kernel_count']}")
    print(f"  loops            {report['loop_count']}")
    print(f"descriptors        {report['descriptor_count']}")
    for name, count in report["descriptors_by_type"].items():
        print(f"  {name.lower():<24} {count}")
    print(f"ROM regions        {report['region_count']}")
    print(f"ROM payload bytes  {report['rom_payload_bytes']}")
    print(f"ROM padding bytes  {report['rom_padding_bytes']}")
    print(f"ROM generated      {report['rom_generated_bytes']}")
    print(f"ROM total bytes    {report['rom_total_bytes'] + report['rom_generated_bytes']}")
    print(f"ROM resources      {report['rom_resource_count']}")
    print(f"largest region     {report['largest_region_bytes']}")
    print(f"mutable state      {report['mutable_state_bytes']}")
    print(f"repair activated   {report['spare_rows_activated']} spare rows")
    print(f"quarantined        {report['quarantined_resources']}")
    topology = report["topology"]
    print(
        "topology           class={class} nodes={node_count} "
        "reticles={reticle_count} tiles/reticle={tiles_per_reticle} "
        "links={link_count} epoch={epoch}".format(**topology)
    )
    if "verification" in report:
        print(f"verifier           admitted={report['verification']['admitted']}")
    if "inverse" in report:
        print(
            f"inverse proof      {report['inverse']['status']} "
            f"({report['inverse']['placed_tensor_count']} tensors, "
            f"padding zero={report['inverse']['all_padding_zero']})"
        )
    if "determinism" in report:
        print(f"determinism        {all(report['determinism'].values())}")
    print(f"deployment sha256  {report['deployment_sha256']}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
