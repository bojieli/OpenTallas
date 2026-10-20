#!/usr/bin/env python3
"""HBM-ELEMOWN3/COLLQ3 (10-19): ref_tile specs of the hard leaves the SAFE COLL quadrant parents (ot_hfd_coll_{q2,q3}_lp_ars)
need (rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_safe_leaves.sv).  Every leaf: ONE scalar clock pin, no instance
parameters (the view name is the module name the parent instantiates), SRAMs inside the leaf on the 43.2 lattice.

  hcoll_fj3_r128w     ot_hgi_coll_fj_n2s1_r128  = hcoll_v5_fj3_r128 (gate WARN 03:28, util 51%, GRT 0, spread 11.6) re-topped
  hcoll_fj2_r128w     ot_hgi_coll_fj_q2_r128    = hcoll_v5_fj2_r128 (gate WARN 03:28, util 52%, GRT 0, spread 12.5) re-topped
  hcoll_link_e1       ot_hgi_coll_link_e1       NEW: link_e rail (registered controller faces, 4 x 64x512 retry-store SRAMs
                                                2 x 2 on the lattice with 44.7 / 51.8-um channels, full-width std bands S and N)
  hcoll_reduce_lane   ot_hgi_coll_reduce_lane   NEW: one of 16 reduce lanes (16 x 32 b tagged state + LAT-8 FP32 add)

  python3 tools/hbm_coll_static/gen_coll_safe_leaf_kits.py   -> tools/ref_tile/specs_hbm_d4g/<name>.json
  then: python3 tools/ref_tile/ref_tile.py gen <spec>  (kit physical/ref_tile/<name>/)

Not generated: the ROWS-128 issuer leaf (ot_hgi_coll_issuer_m_r128).  ot_hgi_coll_static_issuer_v6 #(ROWS 128) keeps its loop
tables as runtime-indexed FLOP arrays (meta 128 x 64 b, rowloops 128 x 32 b, rowcm1 128 x 32 b = 16 kb, read at start_pc /
cur_target / cur_next in one cycle): SAFE-DESIGN item 5 (> 2 kb -> SRAM) fails, so it is NOT gated as-is (owner 10-19: no
squeezing).  It needs the issuer v7 table rebuild (tables in SRAM, replicated read copies, next-row pre-fetch) -> COORD queue.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools/ref_tile/specs_hbm_d4g"
SAFE = "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_safe_leaves.sv"
SRAM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2"
OWNER = "Claude:HBM-ELEMOWN3/COLLQ3"
BRANCH = "claude/collq3-safe-1019"
EXTRA = ["rtl/hbm_accel/generic/collective", "rtl/lib/ot_rst_relay.sv", "rtl/hdc", "rtl/qwen_sys/split_20261014",
         "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2", "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2",
         "results/arch/landed_parent_1018/collq"]
ROUTE = {"pd": 0.5, "period_ps": 833.333, "threads": 8, "hold_margin_ns": 0.03, "macro_halo_um": 5.4,
         "io_hold_margin_ns": 0.03, "pin_balance": {"group_max": 32}}
COMMON = {"kind": "tile", "clock_port": "clk", "reset_ports": ["rst_n"], "layer_cap": "M5", "children": [], "params": {},
          "inter": [], "io_flop_at_pins": {"cols": 4, "allow_none": True}, "inhold": True, "outhold": True,
          "keep_pin_regs": True, "pin_reg_split": True, "hold_pad": {"cell": "HB2xp67_ASAP7_75t_R"},
          "reset_landing": {"enable": True, "stages": 2}}
RS_BENCH = [  # the reduce split lockstep (reduce_static vs control + 16 lanes) and its mutants (run_coll_lp_ars_all.sh rs)
    {"name": "rsplit_eq", "cmd": "LP_ROOT=. bash rtl/hbm_accel/generic/collective/p2p/landed/run_coll_lp_ars_all.sh q3 {RUN}/bench/rs rs",
     "expect": "pass", "pass_regex": "RS PASS", "min_count_regex": "RSPLIT_EQ PASS cycles=(\\d+)", "threads": 16,
     "peak_ram_gb": 32, "needs": ["verilator"]},
]
EQ_BENCH = [  # the whole SAFE parent lockstep (v8x #(AR_ITER 1, ROWS 128) == lpf_ars) incl. the leaf
    {"name": "q3_lpf_ars_eq", "cmd": "LP_ROOT=. bash rtl/hbm_accel/generic/collective/p2p/landed/run_coll_lp_ars_all.sh q3 {RUN}/bench/eq eq",
     "expect": "pass", "pass_regex": "EQ PASS", "min_count_regex": "LPF_EQ PASS compared=(\\d+)", "threads": 16,
     "peak_ram_gb": 96, "needs": ["verilator"]},
]


def rewrap(src_kit, name, top, purpose):
    s = json.loads((ROOT / f"physical/ref_tile/{src_kit}/spec.json").read_text())
    s = copy.deepcopy(s)
    s["name"], s["top"], s["params"] = name, top, {}
    if SAFE not in s["sources"]:
        s["sources"] = s["sources"] + [SAFE]
    s["job"] = dict(s["job"], owner=OWNER, branch=BRANCH, tag="safe", purpose=purpose,
                    views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}")
    s["route"] = dict(s["route"], io_hold_margin_ns=0.03)
    s["structural_change"] = (f"COLLQ3 10-19: {src_kit} geometry / pins / RTL, re-topped as the parameter-free wrapper {top} "
                              f"(the parent instantiates it by this exact name; a #(ROWS 128) instance of the base module "
                              f"is renamed $paramod by yosys and binds no view)")
    return s


def link_e1():
    s = dict(copy.deepcopy(COMMON), name="hcoll_link_e1", top="ot_hgi_coll_link_e1",
             sources=["rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_hard_v5.sv", SAFE,
                      "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_link_capture.sv",
                      "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_capture_ctl.sv",
                      "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_pinreg_ctl.sv",
                      "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_pinreg_store.sv",
                      "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_seq_ctl.sv",
                      "rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv", "rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv",
                      "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"])
    # 475.2 x 345.6: SRAM 2 x 2 (171.288 x 77.784) at x 43.2 / 259.2 (channel 44.7), y 86.4 / 216 (channels 51.8, N edge 51.8); the
    # S band y 0..86.4 (full width) holds the PHY-face pin flops (tx/rx_pin 1,224 b on S, 2.6 pins/um), the switch-side
    # flits enter W (wr_flit 545) / leave E (rx_flit 545), 1.6 pins/um.
    s["outline"] = {"w": 475.2, "h": 345.6}
    s["macros"] = [{"view": SRAM, "count": 1, "inst": f"u.g_bank[{b}].u_store.u_native.u_sram",
                    "at": [[43.2, 259.2][b % 2], [86.4, 216.0][b // 2]], "at_exact": True} for b in range(4)]
    s["pins"] = {"S": ["phy_up", "tx_pin_v", "tx_pin_flit", "clk", "rst_n", "rx_pin_v", "rx_pin_flit", "retry_requested"],
                 "W": ["epoch_begin", "epoch_new", "held_epoch", "wr_v", "wr_observed_v", "wr_seq", "wr_flit", "rd_v", "rd_seq",
                       "rx_expect_v", "rx_expect_seq"],
                 "E": ["rx_v", "rx_flit", "epoch_abort", "fault_cause"], "N": []}
    s["recipe"] = 3
    s["route"] = dict(ROUTE, peak_ram_gb=48)
    s["pin_regs"] = {"enable": False, "reason": "ot_hgi_coll_static_pinreg_ctl registers every published pin (controller "
                     "register Q) and lands every input on a controller face flop before any check (rail header); a "
                     "synthesis pin stage would add an unbenched edge to the static link calendar"}
    s["structural_change"] = ("COLLQ3 10-19 NEW hard leaf: the q2/q3 COLL parents' soft link_e x2 (13.3k soft flops + 8 raw "
                              "SRAMs on the sw root; 5-bit {5{ck_sw}} clock pin read as 'no region' by the gate link graph) "
                              "-> ot_hgi_coll_link_e1 (one clock pin, its 4 retry-store SRAMs inside)")
    s["job"] = {"owner": OWNER, "branch": BRANCH, "tag": "safe", "purpose": "HBM COLL rail leaf for the SAFE q2/q3 COLL "
                "quadrant parents (lp_ars); gate first, route after checklist review", "extra_paths": EXTRA,
                "benches": EQ_BENCH, "views_to": "physical/ref_tile/hcoll_link_e1/views",
                "record_to": "results/rtl/ref_tile/hcoll_link_e1"}
    return s


def reduce_lane():
    s = dict(copy.deepcopy(COMMON), name="hcoll_reduce_lane", top="ot_hgi_coll_reduce_lane",
             sources=["rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_reduce_static.sv", SAFE,
                      "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static.sv",
                      "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv"])
    # ~1.3k flops (512 state + 128 read regs + the LAT-8 add lane ~650): 64.8 x 64.8 for ~45-55 % std fill; 124 pins.
    s["outline"] = {"w": 64.8, "h": 64.8}
    s["macros"] = []
    s["pins"] = {"N": ["load_v", "load_tag", "in_data"],
                 "W": ["clk", "rst_n", "wb", "wb_tag", "add_read", "read_tag", "add_issue"],
                 "E": ["pub_read", "pub_tag_a", "pub_tag_b", "add_valid"],
                 "S": ["pub_a", "pub_b"]}
    s["recipe"] = 3
    s["route"] = dict(ROUTE, peak_ram_gb=16)
    s["pin_regs"] = {"enable": False, "reason": "every lane input lands on a lane flop within <= 3 levels (state[t] write "
                     "enable decode of load_tag / wb_tag, acc / operand / pub read registers, add-lane ap/bp/vp pin "
                     "registers) and every output is flop Q (pub_a / pub_b registers, add valid pipe); a synthesis pin stage "
                     "would shift the lane against the control's 8-edge writeback pipe (unbenched)"}
    s["structural_change"] = ("COLLQ3 10-19 NEW hard leaf: the q2/q3 COLL parents' soft ot_hgi_coll_reduce_static (21.2k soft "
                              "flops on the sw root) split exactly into the soft control ot_hgi_coll_reduce_static_ctl + 16 of "
                              "this lane (tb_hgi_coll_reduce_split_eq); state 512 b per lane (< 2 kb: flops)")
    s["job"] = {"owner": OWNER, "branch": BRANCH, "tag": "safe", "purpose": "HBM COLL reduce lane (x16) for the SAFE q2/q3 "
                "COLL quadrant parents (lp_ars); gate first, route after checklist review", "extra_paths": EXTRA,
                "benches": RS_BENCH, "views_to": "physical/ref_tile/hcoll_reduce_lane/views",
                "record_to": "results/rtl/ref_tile/hcoll_reduce_lane"}
    return s


def main():
    specs = [
        rewrap("hcoll_v5_fj3_r128", "hcoll_fj3_r128w", "ot_hgi_coll_fj_n2s1_r128",
               "COLLQ3 SAFE q3 parent hard child u_fj (ROWS 128 programme target, parameter-free top)"),
        rewrap("hcoll_v5_fj2_r128", "hcoll_fj2_r128w", "ot_hgi_coll_fj_q2_r128",
               "COLLQ3 SAFE q2 parent hard child u_fj (ROWS 128 programme target, parameter-free top)"),
        link_e1(), reduce_lane()]
    for s in specs:
        (OUT / f"{s['name']}.json").write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", OUT / f"{s['name']}.json")


if __name__ == "__main__":
    main()
