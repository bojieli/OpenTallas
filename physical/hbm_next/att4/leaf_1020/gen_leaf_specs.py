#!/usr/bin/env python3
"""HNEXT.ATT4 cluster-leaf successor (claude/hnx-att4-leaf-1020): writes the two leaf kit specs per floorplan variant.
  A (primary, safe):  432 x 302.4, 3 x 3 SRAMs, row pitch 86.4 (43.2 std band between every macro row): the macro W
                      faces (rd_out 256 + wd_in 137 + ctl = 393 live pins on 43.2 um) see <= 4.6 live pins / um of
                      channel height, every pin face escapes into a full-width band <= 21.6 um away.
  B (compact, area-neutral fallback): 432 x 216, the same 3 x 3 SRAMs abutted (row pitch 43.2) between a S and a N band:
                      parent 432 x 475.2 = the _nf area + one 43.2 seam band; macro channel faces stay at ~9.1 / um.
Leaves: n = ot_hnx_att4_sleaf_n (parent N face, words 0..7), s = ot_hnx_att4_sleaf_s (parent S face, words 8..15).
Seam ranges are identical on the N leaf's S face and the S leaf's N face (both R0 at x = 0), so every seam bit runs
straight across the parent's 43.2 um seam band.  usage: gen_leaf_specs.py  (from the repo root)"""
import json
from pathlib import Path

SRC = ["rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
       "rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv", "rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v",
       "rtl/hbm_next/att/ot_hnx_att4_smerge_h.sv",
       "rtl/hbm_next/att/ot_hnx_att4_sleaf.sv",
       "physical/hbm_next/att4/macros/hnx_sram_1r1w_128x256_r43/hnx_sram_1r1w_128x256_r43_bb.v"]
MV = "physical/hbm_next/att4/macros/hnx_sram_1r1w_128x256_r43"
X = [43.2, 172.8, 302.4]                     # column = lane
VAR = {"a": dict(h=302.4, y=[43.2, 129.6, 216.0]), "b": dict(h=216.0, y=[43.2, 86.4, 129.6])}
SEAM = {  # face position (um from the W end) of every seam port; same on both leaves
    "f_sum": [8, 204], "clk": [212, 220], "xs": [228, 328], "f_pd": [332, 356], "f_tag": [358, 382], "xt": [384, 396],
    "f_ev": [398, 402], "f_ps": [403, 405], "f_pl": [406, 409], "f_psl": [410, 414], "f_flt": [416, 418],
    "f_rst": [420, 423]}
NFACE = {"sum_lo": [8, 380], "tag_lo": [382, 406], "ev": [408, 412], "pub_start": [413, 415], "pub_lane": [416, 419],
         "pub_slot": [420, 424], "rst_n": [426, 429]}
SFACE = {"sum_hi": [8, 300], "tag_hi": [302, 326], "pub_data": [328, 376], "pub_word": [378, 384],
         "pub_out_slot": [386, 391], "pub_out_lane": [392, 396], "pub_tag": [398, 418], "pub_v": [420, 422],
         "fault": [424, 427]}
BENCH = "tools/hbm_next/att4_scl_matrix.sh"


def spec(leaf, v):
    g = VAR[v]
    name = f"hnx_rp3a3_sl{leaf}_{v}"
    seam = {("xs_in" if leaf == "n" else "xs_out") if k == "xs" else ("xt_in" if leaf == "n" else "xt_out") if k == "xt"
            else k: r for k, r in SEAM.items()}
    if leaf == "n":
        top, rst, faces = "ot_hnx_att4_sleaf_n", "rst_n", {"N": NFACE, "S": seam}
    else:
        top, rst, faces = "ot_hnx_att4_sleaf_s", "f_rst", {"N": seam, "S": SFACE}
    pins = {f: list(r) for f, r in faces.items()}
    rng = {p: r for f in faces.values() for p, r in f.items()}
    macros = [{"view": MV, "count": 1, "at": [X[l], g["y"][q]], "inst": f"*u_h.g_lane?{l}?.g_lv?{q}?.u_ring"}
              for l in range(3) for q in range(3)]
    half = "words 0..7 (N face of the parent)" if leaf == "n" else "words 8..15 (S face of the parent)"
    return name, {
        "name": name, "top": top, "kind": "tile", "sources": SRC, "clock_port": "clk", "reset_ports": [rst],
        "macros": macros, "pins": pins, "pin_ranges": rng,
        "route": {"pd": 0.5, "threads": 8, "peak_ram_gb": 32, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
                  "macro_halo_um": 0.0, "macro_halo_x_um": 5.4,
                  "pin_balance": {"group_max": 32, "h": "M4", "v": "M3 M5"}},
        "job": {
            "owner": "Claude:HNX-SM4/ATT4", "branch": "claude/hnx-att4-leaf-1020", "tag": f"leaf{leaf}{v}",
            "purpose": (f"HNEXT.ATT4 cluster-leaf successor of hnx_rp3a3_spvm_safe_nf (TT/FF pin-flop spread 127/114 on "
                        f"one 18.5k-sink root; GRT killed by the 4 h stall watchdog, rc 137): leaf {leaf.upper()} = {half}, "
                        f"9 SRAMs + 8 adders + an identical control replica, own clock root, every pin registered; "
                        f"floorplan variant {v.upper()} ({'safe 86.4 macro-row pitch' if v == 'a' else 'compact abutted rows'})."
                        " Below release (next-release HBM die P=3)."),
            "extra_paths": ["physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2",
                            "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2", "rtl/gpu", "rtl/hbm_next/att",
                            "rtl/proto", "tools/hbm_next", "tools/hgi_sim", "tools/hdc_golden.py",
                            "tools/hdc_golden_v41.py", MV, "physical/hbm_next/att4/leaf_1020",
                            "tools/orfs_allcorner_spef.py", "tools/prepare_fp32_fan32_models.py",
                            "results/rtl/fp32_add_native_clone_1020/final_packet/cells.v.gz", "physical/common_flow/ot_keep_regs.tcl",
                            "physical/common_flow/ot_rst_copies.tcl", "physical/common_flow/ot_rst_copies.py"],
            "benches": [
                {"name": "att4_scl_lockstep_exact",
                 "cmd": "HNX_ATT_SAFE_RESET=1 python3 tools/hbm_next/att4_pub_bench.py run --nl 3 --top scl --work {RUN}/bench/scl --out {RUN}/bench/scl.json --mut 0",
                 "expect": "pass", "pass_regex": "^PASS HNX_ATT4_PUB", "threads": 16, "peak_ram_gb": 24,
                 "needs": ["verilator"]},
                {"name": "att4_scl_seam_mut8",
                 "cmd": "HNX_ATT_SAFE_RESET=1 python3 tools/hbm_next/att4_pub_bench.py run --nl 3 --top scl --work {RUN}/bench/scl8 --out {RUN}/bench/scl8.json --mut 8",
                 "expect": "fail", "fail_regex": "^FAIL HNX_ATT4_PUB",
                 "fail_witness": "results/arch/hbm_next_1019/att4/leaf_1020/witness/scl_m8.log", "threads": 16,
                 "peak_ram_gb": 24, "needs": ["verilator"]},
                {"name": "att4_scl_pubhalf_mut9",
                 "cmd": "HNX_ATT_SAFE_RESET=1 python3 tools/hbm_next/att4_pub_bench.py run --nl 3 --top scl --work {RUN}/bench/scl9 --out {RUN}/bench/scl9.json --mut 9",
                 "expect": "fail", "fail_regex": "^FAIL HNX_ATT4_PUB",
                 "fail_witness": "results/arch/hbm_next_1019/att4/leaf_1020/witness/scl_m9.log", "threads": 16,
                 "peak_ram_gb": 24, "needs": ["verilator"]}],
            "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/arch/hbm_next_1019/att4/leaf_1020/{name}",
            "hold_merge": True},
        "pin_regs": {"enable": False, "reason": (
            "the RTL registers every pin: inputs land in one pin register (N leaf ev_a/sum_a/tag_a/ps_a/pl_a/psl_a + seam "
            "xs_g/xt_g; S leaf seam *_g + S-face sum_hb/tag_hb), every output is a flop (feed-throughs driven straight "
            "from the pin registers, f_pd/f_flt, S-face pub_*/fault); a kit flop would add an unscheduled edge")},
        "std_area_um2": 7500.0, "util": 0.5, "outline": {"w": 432.0, "h": g["h"]}, "params": {"NL": 3},
        "recipe": 4,
        "reset_landing": {"enable": False, "reason": (
            "RTL lands the reset at the face in single flops (N: rst_n -> r1 -> r2; S: f_rst -> g1, g1 = the N leaf's r1 "
            "+ the seam register) then one kept split stage (r3v / g2v, 8 copies, <= 32 loads a copy) feeds the core")},
        "io_flop_at_pins": {"enable": True}, "defines": ["OT_HNX_ATT_SAFE_RESET", "OT_FP_DATA_NORST"],
        "reset_relay_split": {"max_loads": 32}, "children": [], "inter": [], "hold_budget": "die",
        "inhold": False, "outhold": False, "keep_pin_regs": True,
        **({"fill_reason": {"pin_bound": (
            "SRAM macro-face pin bound (safe-design item 6): each hnx_sram_1r1w_128x256_r43 carries 393 live pins "
            "(rd_out 256 + wd_in 137 + ctl) on its 43.2 um W face and 119 live wd_in on its E face (9.1 / um); abutted "
            "3-stacks (the _nf / variant B rows) give the column channels > 6 live pins / um and drove the _nf GRT into "
            "the stall; the 86.4 um row pitch keeps <= 4.6 / um of channel height with a full-width band <= 21.6 um from "
            "every pin. Leaf faces: N leaf N 1,065 pins / 432 um, seam 859 / 432 um (<= 2.8 / um per bus range)")}}
           if v == "a" else {})}


if __name__ == "__main__":
    for v in VAR:
        for leaf in "ns":
            n, s = spec(leaf, v)
            d = Path("physical/ref_tile") / n
            d.mkdir(parents=True, exist_ok=True)
            (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
            print(d / "spec.json")
