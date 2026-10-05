#!/usr/bin/env python3
"""Six owner-selected slab closure vehicles. Full native-parent admission stays separate."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import qwen_slab_share as share
import qwen_slab_share_splitface as faces

ROOT = Path(__file__).resolve().parents[1]
HEIGHTS = {456: 455.76, 570: 570.24, 685: 684.72}
KINDS = ("twoface", "capture")
LOAD = 5.55848


def recipe(kind, nominal):
    if kind not in KINDS or nominal not in HEIGHTS:
        raise ValueError("only the six named owner recipes are permitted")
    h = HEIGHTS[nominal]
    args = faces.args(h)
    if kind == "capture":
        at = args.index("^res_in=top")
        splits = []
        for c in range(4):
            lo = 40 + c * (share.W - share.EDGE - 40) / 4
            hi = 40 + (c+1) * (share.W - share.EDGE - 40) / 4
            pattern = "^res_in\\[(" + "|".join(str(b) for b in range(128*c,128*(c+1))) + ")\\]$"
            if c: splits.append("--pin-region")
            splits.append(f"{pattern}=top:{lo:g}-{hi:g}")
        args[at:at+1] = splits
    name = f"qss_fanout_{kind}_{nominal}_l7"
    tcl = f"physical/qwen_slab_fanout/{kind}_{nominal}.tcl"
    capture_bottom = max(share.snap(h - 30.24), round(math.ceil((share.rows(h)[-1] + share.ROM_H + share.EDGE) / share.LAT_Y) * share.LAT_Y, 3))
    capture_top = h - share.EDGE
    if kind == "capture" and share.rows(h)[-1] + share.ROM_H + share.EDGE > capture_bottom:
        raise ValueError("capture region collides with north macro row/halo")
    model = faces.model(h)
    model.update(schema="opentallas.qwen_slab_fanout.r1", variant=name,
        kind=kind, height_um=h, mul_lat=7,
        additional_cycles_vs_inherited_lat6=217,
        postscale_cycles_vs_lat5_per_token=434,
        added_token_latency_ns_vs_lat6=217/1.2,
        source_top=("ot_qwen_slab_port_group_capture" if kind=="capture" else "ot_qwen_slab_port_group"),
        rtl=("rtl/physical/ot_qwen_slab_port_group_capture.sv" if kind=="capture" else "rtl/physical/ot_qwen_slab_port_group.sv"),
        selection=dict(MUL_LAT=7,BW_FIFO=1,**({"COLUMN_CAPTURE":1} if kind=="capture" else {})),
        macro_placement_tcl=tcl, physical_args=args,
        capture=dict(existing_ff=512,new_ff=0,new_clock_reset_pins=0,new_muxes=0,new_cycles=0,
                     existing_ff_area_um2=512*.2916, groups=(4 if kind=="capture" else 0),
                     fence_y_um=([capture_bottom,capture_top] if kind=="capture" else None)),
        finite_service=dict(word_bits=512, bytes_per_clock_per_word_port=64, scale_bytes_per_cycle_per_macro=32,
            scale_port_count=16, group_scale_bytes_per_cycle_max=512,
            fp32_multiplies_per_cycle=16, MACs_per_cycle=0, argmax_comparators=15, argmax_levels=4,
            fifo_depth=8, output_credits=1, total_credits=9, II_min_cycles=1,
            accepted_write="bw_v && bw_rdy",accepted_read="tw_v && tw_rdy",
            publication="held FIFO output until accepted_read; reverse credit on accepted_read only",
            startup="reset copies + HOLD8 + SETTLE8 + peer sync3/stable1; actual parent startup ACK unbound",
            stall_reset_gate="capture_recipe_r1/binary_gate_terminal/terminal.json four phases; no repeat",
            native_parent_tag_epoch_ready_join_installed=False),
        port_capacity=dict(top_res_bits=512,top_capture_bits_per_region=(128 if kind=="capture" else 512),
            top_M5_pitch_um=.048,top_gross_tracks=math.floor((share.W-2*share.EDGE)/.048),
            right_tw_bits=514,right_M4_pitch_um=.048,
            right_tw_gross_tracks=math.floor((share.snap(h/2-35)-share.LAT_Y-share.EDGE)/.048),
            macro_obstructions_and_local_traffic_credit=False,
            gross_capacity_is_not_GRT_or_legal_route_proof=True),
        physical_boundary=dict(inherited_root_relative_input_output_ps=166.667,
            output_load_ff=LOAD,load_evidence="inputs/ss_seq_load.json",
            load_is_SS_sequential_pin_envelope_not_installed_tree_load=True,
            ideal_zero_load=False, propagated_native_parent_clock_bounds=None,
            source_producer="ot_qwen_w12_matvec_part.g_lvl[LG].lq -> raw_res",
            source_receiver="t_in -> lvl[LV0] -> g_lvl[LV0+1].g_add/u_hold",
            source_parent_instantiates_slab=False,source_parent_t_in_has_ready_valid=False,
            no_external_path_declared_internal_failure=True),
        physical_launch_scope="Owner-directed finite-boundary slab closure measurement; not full parent admission",
        full_native_parent_admission=False, hardware_admission=False,die_fit_or_timing_claim=False,
        new_physical_timeout_seconds=dict(synth=None,flow=None), num_cores=16, make_jobs_max=16)
    return model


def capture_tcl(nominal):
    r=recipe("capture",nominal)
    text=(ROOT/"physical/qwen_slab_share/capture_columns_r1.tcl").read_text()
    h=r["height_um"];lo,hi=r["capture"]["fence_y_um"]
    return text.replace("macro_place_h570.24.tcl",f"macro_place_h{h:g}.tcl").replace("540.0*",f"{lo:g}*").replace("568.08*",f"{hi:g}*")


def generate():
    directory=ROOT/"physical/qwen_slab_fanout";directory.mkdir(exist_ok=True)
    for kind in KINDS:
        for nominal in HEIGHTS:
            r=recipe(kind,nominal)
            text=(capture_tcl(nominal) if kind=="capture" else f"source /src/physical/qwen_slab_share/macro_place_h{r['height_um']:g}.tcl\n")
            (ROOT/r["macro_placement_tcl"]).write_text(text)
    baseline=(ROOT/"physical/qwen_slab_m5/port_group.sdc").read_text()
    (directory/"finite_boundary.sdc").write_text(baseline+f"\n# Explicit finite SS sequential-pin envelope; parent arrival contract remains unqualified.\nset_load {LOAD} [all_outputs]\n")


def model():
    cases=[recipe(k,n) for k in KINDS for n in HEIGHTS]
    sources=["tools/qwen_slab_fanout.py", "tools/qwen_slab_fanout_run.py", "tools/run_abi3_physical.py",
        "tools/run_abi3_physical_persistent.py", "tools/uarch_model.py",
        "rtl/physical/ot_qwen_slab_port_group.sv", "rtl/physical/ot_qwen_slab_port_group_capture.sv",
        "rtl/common/ot_meso_fifo.sv", "rtl/hdc/ot_qwen_w12_matvec.sv",
        "results/rtl/qwen_slab_share_20261005/capture_recipe_r1/binary_gate_terminal/terminal.json",
        "results/rtl/qwen_slab_share_20261005/l7_physical_terminal/terminal.json",
        "physical/qwen_slab_fanout/finite_boundary.sdc",
        "results/rtl/qwen_slab_share_20261005/fanout_r1/inputs/ss_seq_load.json"]
    sources += [r["macro_placement_tcl"] for r in cases]
    sources += [f"physical/qwen_slab_share/macro_place_h{h:g}.tcl" for h in HEIGHTS.values()]
    return dict(schema="opentallas.qwen_slab_fanout.all.r1",cases=cases,
        owner_directive="CODEX_DIRECTIVE_20261005_parallel_fanout.md",replication_count=96,
        no_new_RTL=True, prior_failure_records_preserved=True,
        sourcepins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources})


def main():
    p=argparse.ArgumentParser();p.add_argument("--generate",action="store_true");p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.generate:generate()
    s=json.dumps(model(),indent=2,sort_keys=True)+"\n"
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(s)
    else:print(s,end="")
if __name__=="__main__":main()
