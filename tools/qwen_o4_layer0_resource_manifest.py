#!/usr/bin/env python3
"""Bind Qwen layer-0 ISA, ROM images and TP payloads to finite resource demands.

This is an ordered demand trace, not a cycle schedule. It deliberately does not
assign a token rate before bank ports, queues, routes and physical timing exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import hdc_isa as I

ROOT = Path(__file__).resolve().parents[1]
G, W, IL = 6144, 16, 8
CODE_WORD_BYTES = G * W
SCALE_WORD_BYTES = W * 2
DEFAULT_OUT = ROOT / "results/rtl/qwen_o4_layer0_resources.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_hex(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text().splitlines() if line]


def matrix_demand(row: dict) -> dict:
    rounds = row["rounds"]
    code_words = rounds * row["k_per_split"] * IL
    per_round = G // row["split"]
    scale_span = rounds * per_round * IL
    if code_words != row["code_span_words"] or scale_span != row["scale_span_words"]:
        raise ValueError(f"{row['name']}: matrix spans disagree with executable geometry")
    active_scale_reads = sum(
        r * per_round * W * IL + j * W + g * W * IL < row["rows"]
        for r in range(rounds) for j in range(IL) for g in range(per_round)
    )
    issued = code_words * G * W
    useful = row["rows"] * row["columns"]
    if useful > issued:
        raise ValueError(f"{row['name']}: useful MACs exceed issued lanes")
    return {
        "name": row["name"], "rows": row["rows"], "columns_per_die": row["columns"],
        "weight_source": "INT8_ROM", "scale_source": "BF16_scale_ROM",
        "emitted_code_base_word": row["base"], "emitted_scale_base_word": row["scale_base"],
        "code_words_requested": code_words, "code_words_allocated_in_image": row["allocated_words"],
        "scale_words_address_span": scale_span, "scale_group_reads_active": active_scale_reads,
        "scale_group_reads_without_active_mask": rounds * IL * G,
        "maximum_active_scale_address": row["scale_base"] + scale_span - 1,
        "useful_mac": useful, "issued_lane_mac": issued, "padding_lane_mac": issued - useful,
        "code_bytes_requested": code_words * CODE_WORD_BYTES,
        "code_bytes_allocated_in_image": row["allocated_words"] * CODE_WORD_BYTES,
        "active_scale_bytes_read": active_scale_reads * SCALE_WORD_BYTES,
    }


def trace(manifest: dict, program: list[int], descriptors: list[int]) -> tuple[list[dict], list[dict]]:
    bases = [(word >> 32) & 0xFFFF for word in descriptors]
    segments = []
    for i, word in enumerate(descriptors):
        kind, vw, count = word & 3, (word >> 2) & 0xFF, ((word >> 10) & 0xFF) or (256 if (word & 3) == 1 else 0)
        segments.append({"segment": i, "pc_first": bases[i],
                         "pc_last": (bases[i + 1] if i + 1 < len(bases) else len(program)) - 1,
                         "collective_kind": {0: "END", 1: "ALLREDUCE", 2: "ARGMAX"}.get(kind, "INVALID"),
                         "vm_word_base": vw, "collective_words": count,
                         "collective_payload_bytes_per_die": count * W * 4})
    rows = {r["base"]: r["name"] for r in manifest["matrix_layout"]}
    events = []
    for pc, word in enumerate(program):
        fields = I.decode(word)
        unit = fields["unit"]
        segment = next(s["segment"] for s in segments if s["pc_first"] <= pc <= s["pc_last"])
        event = {"pc": pc, "segment": segment,
                 "unit": {I.UNIT_ME: "ME", I.UNIT_SU: "SU", I.UNIT_END: "END"}.get(unit, str(unit)),
                 "barrier": bool(fields["barrier"])}
        if unit == I.UNIT_ME:
            event.update({"resource": "KV_attention_matvec" if fields["me_wsrc"] else "INT8_matrix_tile",
                          "weight_word_base": fields["me_wbase"],
                          "scale_word_base": fields["me_wcs"] if not fields["me_wsrc"] else None,
                          "matrix": rows.get(fields["me_wbase"]) if not fields["me_wsrc"] else None,
                          "encoded_nout": fields["me_nout"], "encoded_k": fields["me_k"],
                          "encoded_tiles": fields["me_tiles"], "split": 1 << fields["me_split"]})
        elif unit == I.UNIT_SU:
            event.update({"resource": "scalar_vector_SFU_reduction",
                          "encoded_nout": fields["su_nout"], "encoded_nin": fields["su_nin"],
                          "a_base": fields["a_base"], "b_base": fields["b_base"],
                          "c_base": fields["c_base"], "d_base": fields["d_base"],
                          "dst": fields["dst"], "reduction": fields["red"], "sfu": fields["sfu"]})
        events.append(event)
    return segments, events


def build(prefix: Path) -> dict:
    dies = []
    image_pins = {}
    for die in range(2):
        folder = Path(f"{prefix}-d{die}")
        manifest_path = folder / "layer0_rom.json"
        manifest = json.loads(manifest_path.read_text())
        if manifest["status"] != "image_and_isa_emitted" or manifest["die"] != die:
            raise ValueError("unexpected emitter image")
        paths = [manifest_path, *(folder / name for name in (
            "matrix_int8.hex", "matrix_scale_bf16.hex", "crom.hex", "program.hex", "segments.hex"))]
        image_pins[f"die{die}"] = {p.name: sha(p) for p in paths}
        program, descriptors = read_hex(folder / "program.hex"), read_hex(folder / "segments.hex")
        matrices = [matrix_demand(row) for row in manifest["matrix_layout"]]
        segments, events = trace(manifest, program, descriptors)
        requested = sum(x["code_words_requested"] for x in matrices)
        allocated = sum(x["code_words_allocated_in_image"] for x in matrices)
        active_scale = sum(x["scale_group_reads_active"] for x in matrices)
        stale_scale = sum(x["scale_group_reads_without_active_mask"] for x in matrices)
        last_active_scale = max(x["maximum_active_scale_address"] for x in matrices)
        if allocated != manifest["matrix_words"] or len(program) != manifest["program_words"]:
            raise ValueError("image length differs from executable placement")
        if len(descriptors) != manifest["segments"]:
            raise ValueError("descriptor length differs from executable placement")
        dies.append({"die": die, "matrices": matrices, "segments": segments, "events": events,
                     "summary": {
                         "matrix_code_words_requested": requested,
                         "matrix_code_words_emitted": allocated,
                         "matrix_code_padding_words": allocated - requested,
                         "matrix_code_bytes_requested": requested * CODE_WORD_BYTES,
                         "matrix_code_bytes_emitted": allocated * CODE_WORD_BYTES,
                         "matrix_code_padding_bytes": (allocated - requested) * CODE_WORD_BYTES,
                         "matrix_useful_mac": sum(x["useful_mac"] for x in matrices),
                         "matrix_issued_lane_mac": sum(x["issued_lane_mac"] for x in matrices),
                         "scale_group_reads_active": active_scale,
                         "scale_group_reads_without_active_mask": stale_scale,
                         "scale_rom_words_emitted": manifest["scale_rom_words"],
                         "scale_rom_words_needed_for_active_addresses": last_active_scale + 1,
                         "scale_rom_bytes_emitted": manifest["scale_rom_words"] * SCALE_WORD_BYTES,
                         "scale_rom_bytes_active_address_range": (last_active_scale + 1) * SCALE_WORD_BYTES,
                         "constant_rom_bytes": manifest["constant_words"] * 8,
                         "vm_bytes": 177808 * 4,
                         "kv_one_layer_8k_window_bytes": 8388608 * 4,
                         "tp_allreduce_payload_bytes_sent": sum(s["collective_payload_bytes_per_die"]
                                                                for s in segments)}})
    if dies[0]["summary"] != dies[1]["summary"]:
        raise ValueError("TP2 die resource totals differ unexpectedly")
    return {"schema": "opentallas.qwen-o4-layer0-resource-demand.v1",
            "status": "static_exact_image_and_ISA_demand",
            "source_sha256": {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)),
                              "rtl/hdc/ot_hdc_matvec.sv": sha(ROOT / "rtl/hdc/ot_hdc_matvec.sv"),
                              "tools/hdc_qwen_layer0_rom.py": sha(ROOT / "tools/hdc_qwen_layer0_rom.py"),
                              "tools/hdc_qwen_fullshape_program.py": sha(ROOT / "tools/hdc_qwen_fullshape_program.py")},
            "image_sha256": image_pins, "dies": dies,
            "claim_boundary": "Ordered demands from emitted real-checkpoint layer0 ISA and images. "
                              "No finite cycle reservation, bank conflicts, routed bandwidth, "
                              "physical ROM macro packing, full token rate or P&R is measured."}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emitter-prefix", type=Path, default=Path("/tmp/qwen-real-layer0"))
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    result = build(args.emitter_prefix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["dies"][0]["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
