#!/usr/bin/env python3
"""Build an immutable-ROM ABI 3.0 deployment from Tensor Kernel IR v3.

One CLI, two products, one backend family:

    python3 tools/build_rom_deployment.py qwen3-8b \\
        --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \\
        --output build/abi3/qwen3-8b-rom

    python3 tools/build_rom_deployment.py deepseek-v4-flash \\
        --ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \\
        --output build/abi3/deepseek-v4-flash-rom

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
from compiler.backends.rom.qwen3 import (  # noqa: E402
    build_qwen3_rom_deployment,
    qwen3_rom_capability,
)
from compiler.ir.v3.kernel_ir import (  # noqa: E402
    CheckpointBinding,
    Entrypoint,
    Kernel,
    KernelGraph,
    RuntimeSymbol,
    StateResource,
    Symbolic,
    Tensor,
    require_neutral,
)
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.constants import StorageClass  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402

PRODUCTS = ("qwen3-8b", "deepseek-v4-flash")


# ---------------------------------------------------------------------------
# Reading a Tensor Kernel IR v3 document
# ---------------------------------------------------------------------------
def _extent(value: Any) -> Any:
    if isinstance(value, Mapping):
        return Symbolic(
            symbol=str(value["symbol"]),
            multiplier=int(value.get("multiplier", 1)),
            maximum=int(value.get("maximum", 0)),
        )
    return int(value)


def load_kernel_graph(path: Path) -> KernelGraph:
    """Read a neutral Tensor Kernel IR v3 document written by a front end."""
    body = json.loads(Path(path).read_text())
    schema = body.get("schema")
    if schema != "opentallas.tensor_kernel_ir.v3":
        raise SystemExit(f"{path}: unexpected IR schema {schema!r}")
    tensors = []
    for record in body["tensors"]:
        binding = record.get("binding")
        tensors.append(
            Tensor(
                tensor_id=record["tensor_id"],
                dtype=record["dtype"],
                shape=tuple(_extent(d) for d in record["shape"]),
                role=record["role"],
                binding=CheckpointBinding(
                    source_name=binding["source_name"],
                    path=binding["path"],
                    offset=int(binding["offset"]),
                    bytes=int(binding["bytes"]),
                    sha256=binding["sha256"],
                    transform=binding.get("transform", "identity"),
                )
                if binding
                else None,
                scale_tensor_id=record.get("scale_tensor_id"),
                scale_block_elements=int(record.get("scale_block_elements", 0)),
            )
        )
    states = tuple(
        StateResource(
            state_id=record["state_id"],
            state_class=record["state_class"],
            dtype=record["dtype"],
            row_elements=int(record["row_elements"]),
            capacity_rows=_extent(record["capacity_rows"]),
            initialization=record.get("initialization", "zero"),
        )
        for record in body["states"]
    )
    kernels = tuple(
        Kernel(
            index=int(record["index"]),
            kernel_id=record["kernel_id"],
            kind=record["kind"],
            inputs=tuple(record["inputs"]),
            outputs=tuple(record["outputs"]),
            numeric_contract=record["numeric_contract"],
            iteration_domain={
                k: _extent(v) for k, v in record.get("iteration_domain", {}).items()
            },
            attributes=dict(record.get("attributes", {})),
            phases=tuple(record.get("phases", ("prefill", "decode"))),
            state_reads=tuple(record.get("state_reads", ())),
            state_writes=tuple(record.get("state_writes", ())),
            counter_class=record.get("counter_class", ""),
            source_operation_id=record.get("source_operation_id", ""),
            layer=record.get("layer"),
        )
        for record in body["kernels"]
    )
    graph = KernelGraph(
        model_id=body["model_id"],
        source=dict(body.get("source", {})),
        symbols=tuple(
            RuntimeSymbol(
                name=record["name"],
                minimum=int(record["minimum"]),
                maximum=int(record["maximum"]),
                multiple_of=int(record.get("multiple_of", 1)),
                binding=record.get("binding", "request"),
            )
            for record in body.get("symbols", ())
        ),
        tensors=tuple(tensors),
        states=states,
        kernels=kernels,
        entrypoints=tuple(
            Entrypoint(
                phase=record["phase"],
                inputs=tuple(record["inputs"]),
                outputs=tuple(record["outputs"]),
                states=tuple(record["states"]),
                generation_policy=record.get("generation_policy", ""),
            )
            for record in body["entrypoints"]
        ),
        numeric_profile=body.get("numeric_profile", "target_precision_v1"),
        generation_policy=dict(body.get("generation_policy", {})),
    )
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


def build(product: str, graph: KernelGraph, args) -> tuple[Deployment, Any, Any]:
    defects = parse_defects(args.defects)
    storage = StorageClass.HBM if args.storage_class == "hbm" else StorageClass.ROM
    if product == "qwen3-8b":
        capability = qwen3_rom_capability()
        deployment, plan = build_qwen3_rom_deployment(
            graph,
            capability=capability,
            defects=defects,
            weight_storage_class=storage,
        )
    else:
        capability = deepseek_v4_rom_capability()
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
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--inverse", action="store_true")
    parser.add_argument("--determinism", action="store_true")
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
    print(f"ROM total bytes    {report['rom_total_bytes']}")
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
