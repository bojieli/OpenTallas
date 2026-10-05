#!/usr/bin/env python3
"""Candidate integer owners and ordered split-layer packets for V4.1 TP-4.

This is an executable *ownership and data-dependency* contract, not a ROM
address map, placed macro image, stage program, or throughput result.  The
representative L1 S0/S1 route deliberately exercises both expert owners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path

import v41_stage_owner_preflight as P

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path("/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/") / (
    "snapshots/dba1be0a40aa45a94ad051997016db3960a90277")
OUT = ROOT / "results/arch/v41_stage_packet_contract.json"
EXPERT = re.compile(r"^layers\.(\d+)\.ffn\.experts\.(\d+)\.(w[123])\.(weight|scale)$")
LAYER = re.compile(r"^layers\.(\d+)\.")
EXPERT_SUFFIXES = tuple(f"{w}.{part}" for w in ("w1", "w2", "w3") for part in ("weight", "scale"))
DIM, HC, TP, N_EXPERT = 5120, 4, 4, 384
FLIT_BYTES = 64


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checkpoint_header_inventory(snapshot: Path) -> tuple[list[list[str]], str]:
    """Read headers only; pin the exact tensor-name inventory, not weight bytes."""
    files = sorted(snapshot.glob("*.safetensors"))
    if not files:
        raise FileNotFoundError(f"no safetensors headers in {snapshot}")
    keys = [[] for _ in range(40)]
    digest = hashlib.sha256()
    for file in files:
        with file.open("rb") as fh:
            size_bytes = fh.read(8)
            if len(size_bytes) != 8:
                raise ValueError(f"short safetensors header: {file}")
            header = fh.read(struct.unpack("<Q", size_bytes)[0])
        digest.update(file.name.encode() + b"\0" + size_bytes + header)
        for name in json.loads(header):
            match = LAYER.match(name)
            if match:
                layer = int(match.group(1))
                if layer >= len(keys):
                    raise ValueError(f"unexpected checkpoint layer {layer}")
                keys[layer].append(name)
    return [sorted(names) for names in keys], digest.hexdigest()


def owner_for_expert(owner: dict, expert_id: int) -> int:
    if not 0 <= expert_id < N_EXPERT:
        raise ValueError(f"expert ID out of range: {expert_id}")
    matches = [part["stage"] for part in owner["routed_expert_candidate_owners"]
               if part["expert_ids"][0] <= expert_id <= part["expert_ids"][1]]
    if len(matches) != 1:
        raise ValueError(f"expert {expert_id} has {len(matches)} stage owners")
    return matches[0]


def layer_tensor_rule(layer: int, owner: dict, source_names: list[str]) -> dict:
    prefix = f"layers.{layer}."
    expert_names = set()
    for expert_id in range(N_EXPERT):
        expert_names.update(f"{prefix}ffn.experts.{expert_id}.{suffix}"
                            for suffix in EXPERT_SUFFIXES)
    if not expert_names <= set(source_names):
        missing = expert_names - set(source_names)
        raise ValueError(f"layer {layer}: {len(missing)} missing expert weight/scale tensors")
    extra_expert = [name for name in source_names if ".ffn.experts." in name and name not in expert_names]
    if extra_expert:
        raise ValueError(f"layer {layer}: unexpected expert tensor {extra_expert[0]}")
    dense = [name for name in source_names if name not in expert_names and
             not name.startswith(prefix + "engram.embed.")]
    engram = [name for name in source_names if name.startswith(prefix + "engram.embed.")]
    home = owner["dense_owner_stage"]
    # These exact names include all non-routed source tensors except the
    # separately striped/spilled Engram table.  Physical addresses remain
    # deliberately null until an image and bank map prove them.
    return dict(layer=layer, home_stage=home,
                dense_source_tensors=dense,
                engram_table_source_tensors=engram,
                engram_table_owner="unbound_table_die_or_spill" if engram else None,
                routed_source_tensor_template=f"{prefix}ffn.experts.{{expert_id}}.{{suffix}}",
                routed_source_suffixes=list(EXPERT_SUFFIXES),
                rank_ownership=[dict(rank=rank, home_die=4 * home + rank,
                                     home_package=(4 * home + rank) // 2,
                                     dense_source_tensor_owner_stage=home,
                                     shared_expert_owner_stage=home,
                                     routed_expert_ranges=[dict(stage=part["stage"],
                                                                die=4 * part["stage"] + rank,
                                                                package=(4 * part["stage"] + rank) // 2,
                                                                expert_ids=part["expert_ids"])
                                                           for part in owner["routed_expert_candidate_owners"]],
                                     physical_rom_bank=None, rom_word_address=None,
                                     source_tensor_tp_slice=None)
                                for rank in range(TP)])


def representative_packets(owner: dict, selected: tuple[int, ...], *, layer: int = 1,
                           user: int = 0, position: int = 199999) -> dict:
    if len(selected) != 6 or tuple(sorted(set(selected))) != selected:
        raise ValueError("representative route requires six distinct ascending expert IDs")
    stages = sorted({owner_for_expert(owner, expert_id) for expert_id in selected})
    if len(owner["routed_expert_candidate_owners"]) != 2 or len(stages) != 2:
        raise ValueError("representative route must select experts on both split stages")
    home, remote = owner["dense_owner_stage"], owner["routed_expert_candidate_owners"][1]["stage"]
    if stages != [home, remote]:
        raise ValueError("representative route does not match its home/remote stages")
    low = [expert_id for expert_id in selected if owner_for_expert(owner, expert_id) == home]
    high = [expert_id for expert_id in selected if owner_for_expert(owner, expert_id) == remote]
    # VM/collective output rows are TP4 output-row split.  XN is the full
    # normalized activation on each logical rank; H/pre has four BF16 copies.
    x_bytes = DIM * 4
    metadata_bytes = 6 * 4 + 6 * 4  # six uint32 IDs and six FP32 normalized gates
    accumulator_bytes = DIM // TP * 4
    continuation_bytes = HC * DIM * 2 + 16
    nodes, packets = [], []
    for rank in range(TP):
        stem = f"u{user}.p{position}.L{layer}.r{rank}"
        def node(name: str, stage: int, depends: list[str], work: str) -> str:
            uid = f"{stem}.{name}"
            nodes.append(dict(id=uid, stage=stage, rank=rank, depends_on=depends, work=work,
                              earliest_cycle=None, service_cycles=None, physical_resource=None))
            return uid

        def packet(name: str, src: int, dst: int, depends: list[str], payload: list[dict]) -> str:
            uid = f"{stem}.{name}"
            useful = sum(part["bytes"] for part in payload)
            packets.append(dict(id=uid, from_stage=src, to_stage=dst, from_die=4 * src + rank,
                                to_die=4 * dst + rank, rank=rank, user=user, position=position,
                                layer=layer, phase=name, depends_on=depends, payload=payload,
                                useful_bytes=useful, minimum_payload_flits=math.ceil(useful / FLIT_BYTES),
                                header_bytes=None, physical_link_route=None,
                                start_cycle=None, completion_cycle=None))
            return uid

        router = node("router_ready", home, [], "XN and six selected IDs/normalized gates ready")
        activation = packet("activation_forward", home, remote, [router], [
            dict(name="XN", format="FP32", elements=DIM, bytes=x_bytes),
            dict(name="expert_ids", format="uint32", elements=6, bytes=24),
            dict(name="normalized_gates", format="FP32", elements=6, bytes=24)])
        local = node("low_experts_done", home, [router],
                     f"BF16 per-expert w2 outputs and FP32 additions in ID order {low}")
        shared_output = node("shared_output_ready", home, [router],
                             "compute shared expert output independently; defer its FP32 add")
        partial = packet("partial_forward", home, remote, [local], [
            dict(name="ordered_accumulator", format="FP32", elements=DIM // TP,
                 bytes=accumulator_bytes, after_expert_ids=low)])
        high_outputs = node("high_expert_outputs_ready", remote, [activation],
                            f"BF16 per-expert w2 outputs in ID order {high}; no accumulation yet")
        remote_sum = node("remote_ordered_sum_done", remote, [partial, high_outputs],
                          f"start from transmitted FP32 partial; add {high} in order, FP32 RNE")
        returned = packet("accumulator_return", remote, home, [remote_sum], [
            dict(name="ordered_accumulator", format="FP32", elements=DIM // TP,
                 bytes=accumulator_bytes, after_expert_ids=list(selected))])
        shared = node("shared_last_done", home, [returned, shared_output],
                      "add shared expert after all routed experts, then BF16 round")
        hc = node("hc_post_done", home, [shared], "HC post and next-layer H/pre committed")
        packet("continuation_forward", home, remote, [hc], [
            dict(name="H", format="BF16", elements=HC * DIM, bytes=HC * DIM * 2),
            dict(name="pre_and_scalars", format="opaque_model_payload", elements=None, bytes=16)])
    return dict(kind="representative_synthetic_route", layer=layer, home_stage=home,
                remote_stage=remote, user=user, position=position,
                selected_expert_ids=list(selected), local_expert_ids=low, remote_expert_ids=high,
                golden_order_rule="ascending expert ID FP32 add, shared expert last, then BF16 round",
                rank_count=TP, nodes=nodes, packets=packets,
                claim_boundary="Packet dependencies and useful bytes only; no real L1 selected IDs, physical "
                               "addresses, link arbitration, program, timing or token verdict.")


def derive(snapshot: Path = SNAPSHOT) -> dict:
    candidate = P.derive()
    source_names, header_hash = checkpoint_header_inventory(snapshot)
    if len(source_names) != 40 or any(not names for names in source_names):
        raise ValueError("checkpoint does not contain 40 populated layers")
    owners = candidate["layer_owners"]
    layers = [layer_tensor_rule(layer, owner, source_names[layer])
              for layer, owner in enumerate(owners)]
    route = representative_packets(owners[1], (0, 1, 151, 152, 200, 383))
    source = {str(P.CONFIG.relative_to(ROOT)): sha(P.CONFIG),
              str(P.PLACEMENT.relative_to(ROOT)): sha(P.PLACEMENT),
              "tools/v41_stage_owner_preflight.py": sha(Path(P.__file__)),
              "tools/v41_stage_packet_contract.py": sha(Path(__file__)),
              "tools/hdc_golden_v41.py": sha(ROOT / "tools/hdc_golden_v41.py")}
    return dict(schema="opentallas.v41.stage_packet_contract.v1",
                status="candidate_packet_dependency_not_executable",
                source_sha256=source,
                checkpoint_header_sha256=header_hash,
                checkpoint_snapshot_revision=snapshot.name,
                candidate_preflight_min_per_die_headroom_after_spill_bytes=(
                    candidate["min_per_die_headroom_after_rounding_and_engram_spill_bytes"]),
                layer_count=40, stage_count=28, tensor_parallel_ranks=TP,
                layer_tensor_ownership=layers,
                representative_split=route,
                missing_gates=["physical ROM bank/word addresses and TP slices for all tensor sources",
                               "Engram table/spill source-row owner and executable multicast",
                               "stage-specific programs for all 40 layers and every selected route",
                               "real packet transport, credits, buffers, arbitration and exact token gate",
                               "capacity with padding/ECC/metadata and achieved routed frequency"],
                claim_boundary="Checkpoint header inventory, coarse integer owner candidate and synthetic "
                               "arithmetic-order packet contract. No physical fit or chip-rate claim.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    record = derive(args.snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
