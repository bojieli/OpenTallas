#!/usr/bin/env python3
"""Qwen A0 consumer-owned register hardening; structural plan, not qualification."""
import json

def model():
    return dict(schema="opentallas.qwen.region_glue.model.v1", adopted=False,
      operand=dict(master="ot_qwen_tile_operand", replicas_per_tile=8, replicas_per_die=6144,
        lanes=8, groups=4, lanes_per_group=2, wrom_bytes_per_cycle=16,
        input_bits_per_cycle=133, output_bits_per_cycle=128, ff_count=261,
        outline_um=[12.96,86.4], area_um2=1119.744,
        reference_stages=["mq_wrom + s1b_gm/wsrc", "s2_w high16 per lane"],
        latency_edges=2, added_latency_edges=0, macs_per_cycle=0,
        clock="consumer's ck_tx[g] entry; related neighbour clock, measured phi-R required",
        valid_modes="ROM-only KV_LOCAL=0, WCONV=1, HIER=2; KV sourced weights return zero exactly",
        ctrl_copies_delta_ff=40, parent_ck_removed_ff=2048,
        pins_per_face_um=133/86.4, tracks_per_long_face_m4=86.4/.048),
      rqr=dict(master="ot_qwen_tile_rqr_half", replicas_per_tile=4, replicas_per_die=3072,
        input_bits_per_cycle=512, output_bits_per_cycle=512, ff_count=512,
        outline_um=[12.96,129.6], area_um2=1679.616,
        latency_edges=1, added_latency_edges=0, macs_per_cycle=0,
        ff_delta=0, clock_entries=["ck_rs", "ck_rn", "ck_rse", "ck_rne"],
        ownership=["south-W", "north-W", "south-E", "north-E"],
        pins_per_face_um=512/129.6, tracks_per_long_face_m4=129.6/.048),
      parent=dict(rom_mac_lanes=64, raw_rom_macros=10, added_latency_edges=0,
        total_added_ff=40, new_clock_entries=2,
        expected_remaining_ck_ff=4396-2048,
        footprint_status="not granted: new hard-child guards require A0 slot replan before binding",
        invariants=["same INT8->BF16 values and reduction order", "no reset waiver", "no stage added", "registered physical inputs and outputs"]),
      qualification=dict(required=["exact legacy-vs-leaf bench and rejected mutants", "full actual ROM A0 composed bench", "native launch<=220/capture<=190/spread<=80", "real placement/CTS/clock neighbours<=80", "GRT0 and TT/FF>=0"], status="unmeasured"))

if __name__ == "__main__":
    print(json.dumps(model(), indent=2))
