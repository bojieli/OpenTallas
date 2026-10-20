#!/usr/bin/env python3
"""S81-TILES-E (10-20, LEAD9-S81 decision 14:30): kit s81sl_xg5 = the slice gather sub-leaf re-merged (ot_s81sl_xg5 =
ot_s81sl_rs + ot_s81sl_xs4 + issuer relay) so the 3 x 1,031-b gather port stays inside one tile.

Why: the split rs4 leaf was PIN-BOUND (13,750 signal pins in 864 x 518.4, util 2.6%; at <= 6 pins/um its minimum outline
gives ~3.7%) and its placement TT was -313.8 ps; owner 10-20 09:09 REPARTITION rule for pin-bound tiles.
Outline = the original xg slot 648 x 561.6 (base spec base_s81sl_xg_spec_xg1019.json, claude/s81-xg-1019): estimated
std ~30k um2 (rs4 synth 12.3k + xs4 synth 16.5k + XG5 copies) + 37 macros 115.8k um2 = 146k -> util ~40%; pins
11,914 on full faces <= 5.8/um (W/E 4.5, N 5.8, S 4.7).
Macro map (SRAM / ROM / exp-SRAM pins are on the L/R faces only -> deliberate N-S abutted stacks, gap 0.024 um, bare
touching faces; channels only between columns; stack origins on the 43.2 / 21.6 grid, as the original xg kit):
  x 43.2   bank 1 (W ring source) 8 x 128x256 SRAM, y 108 + 41.088 k   | x 216.0 bank 0 (own) | x 432.0 bank 2 (E source)
  x 345.6  7 x ROM 4096x72, y 64.8 + 62.976 k
  x 561.6  6 x exponent SRAM 128x64 (source 0/1/2 x beat bit 2), y 108 + 27.6 k
Channels: 34.8-78 um between macro columns, W edge 43.2, E edge 52.7, S strip 108 / N strip 108 for the face pin cells.
"""
import copy, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SRAM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"
ROM = "physical/asap7_memory_macros_v2/ot_rom_4096x72_m8"
EXP = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1"


def main():
    s = json.loads((HERE / "base_s81sl_xg_spec_xg1019.json").read_text())
    s["name"] = "s81sl_xg5"
    s["top"] = "ot_s81sl_xg5"
    s["sources"] = ["rtl/v41rom/ot_v41_kreg.sv", "rtl/common/ot_prefix.sv",
                    "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rs.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv",
                    "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg5.sv",
                    f"{SRAM}/ot_sram_1r1w_128x256_m1_r2c2_bb.v", f"{ROM}/ot_rom_4096x72_m8_bb.v",
                    f"{EXP}/ot_sram_1r1w2c_128x64_m1_bb.v"]
    s["defines"] = []
    m = []
    for bank, x in ((1, 43.2), (0, 216.0), (2, 432.0)):
        for k in range(8):
            m.append({"view": SRAM, "count": 1, "inst": f"*u_s.g_bank?{bank}?.g_mac?{k}?.u_mem",
                      "at": [x, round(108.0 + 41.088 * k, 4)], "orient": "R0", "at_exact": True})
    for k, n in enumerate(["u_phase0", "u_cal_action", "u_cal_time", "u_stream0", "u_stream1", "u_stream2", "u_stream3"]):
        m.append({"view": ROM, "count": 1, "inst": f"*u_s.{n}", "at": [345.6, round(64.8 + 62.976 * k, 4)], "orient": "R0",
                  "at_exact": True})
    k = 0
    for bank in range(3):
        for e in range(2):
            m.append({"view": EXP, "count": 1, "inst": f"*u_s.g_bank?{bank}?.g_ex?{e}?.u_em",
                      "at": [561.6, round(108.0 + 27.6 * k, 4)], "orient": "R0", "at_exact": True})
            k += 1
    s["macros"] = m
    s["std_area_um2"] = 30000.0
    s["route"] = dict(s["route"], synth_keep_modules=["ot_s81sl_xs4_pdec", "ot_s81sl_xs4_due", "ot_s81sl_xs4_fetch"])
    s["orfs_vars"] = {"OT_CKKM_K": "16"}
    s["pre_cts_extra"] = ["physical/common_flow/clock_split_km.tcl"]
    s["fill_reason"] = {"pin_bound": "11,914 signal pins on full faces <= 5.8/um (N 5.8, S 4.7, W/E 4.5) at 648 x 561.6; "
                                     "37 macros 115.8k um2 + std ~30k (synthesis rs4 12.3k + xs4 16.5k) = ~40% util"}
    s["structural_change"] = __doc__.strip()
    s["pin_regs"] = rs_pin_regs()
    W = "results/rtl/s81_slice_1019"
    benches = []
    def b(name, cmd, expect, wit, fail_regex=None, pass_regex=None, ram=16):
        d = {"name": name, "cmd": cmd, "expect": expect, "threads": 8, "peak_ram_gb": ram, "needs": ["verilator"],
             "pass_regex": pass_regex}
        if expect == "pass":
            d["pass_witness"] = wit
        else:
            d["fail_regex"] = fail_regex; d["fail_witness"] = wit
        benches.append(d)
    b("xg5_bench", "bash tools/s81_slice/xg5_bench.sh {RUN}/xg5", "pass", f"{W}/xg5/xg5_bench.log",
      pass_regex="^XG5_BENCH PASS", ram=32)
    # rs / xs4 equivalence benches + mutants exactly as their leaf kits (s81sl_rs4 @claude/s81-xg4-1020, s81sl_xs4a);
    # xs4 witnesses re-run on the XG5 source (census fixes) and committed under xg5/
    for k, wdir in (("s81sl_rs4", None), ("s81sl_xs4a", f"{W}/xg5")):
        for bb in json.loads((ROOT / f"physical/ref_tile/{k}/spec.json").read_text())["job"]["benches"]:
            bb = copy.deepcopy(bb)
            if wdir and bb.get("fail_witness"):
                bb["fail_witness"] = bb["fail_witness"].replace(f"{W}/xg4xs", wdir)
            benches.append(bb)
    j = s["job"]
    j["benches"] = benches
    j["extra_paths"] = ["rtl/dsrom_sys", "rtl/lib", "rtl/v41rom", "rtl/common", "tools/s81_slice", "tools/s81_static_control",
                        "tools/s81/pq_static_calendar_abi.json", "physical/s81_pq_hier/pinned", SRAM, ROM, EXP,
                        "results/rtl/dsrom_recovery_20261004/immutable_fullcatalog/stage0",
                        "results/rtl/dsrom_recovery_20261004/immutable_fullcatalog/stage3", f"{W}/xg4", f"{W}/xg5"]
    j.update(owner="Claude:S81-TILES-E", branch="claude/s81-xg5-1020", tag="xg5",
             views_to="physical/ref_tile/s81sl_xg5/views", record_to="results/rtl/ref_tile/s81sl_xg5",
             purpose="S81.STA.LEAF.5 s81sl_xg5: rs + xs4 re-merged (gather port inside; owner REPARTITION rule) at the "
                     "original xg slot 648 x 561.6, util ~40%; xs4 native census fixes. SAFE checklist in kit README.")
    d = ROOT / "physical/ref_tile/s81sl_xg5"
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json")


def rs_pin_regs():
    return {"enable": False, "reason": "Source-registered merged leaf: every rs input lands in a pin flop (iw / ie / iv / xf_q / "
            "neo_q / nwo_q / ci_q / sid_c and the capture copies) and every rs output leaves a relay flop (ro_* / vo / dl_* / "
            "nx_*); the x streamer's issuer input lands in the xg5 issuer relay then xs4 capture flops, xw_v / xw_d / fault "
            "leave flops. A recipe pin_regs stage would add an unpriced ring-hop edge (~8 cycles per traversal)."}


if __name__ == "__main__":
    main()
