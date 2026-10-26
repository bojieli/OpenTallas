#!/usr/bin/env python3
"""gen_slice5_lp_spec.py -- QW-SLICE6 10-19 (Q.STA.SLICE.2): the lp.py spec of the hardened one-level slice
(tools/landed_parent/specs/qfd_dv_s5.json + the fallback qfd_dv_s5b.json) from the plan
results/arch/qw_slice5_1019/partition.json (regions / floorplan rectangles) and the generated hardened flat parent
rtl/qwen_dv/s5/qfd_dv_s5_flat.sv.

Regions (one local clock root each, entry beside its register mass):
  r_fw / r_fe          the dn / up face strips (fdn / fup: pin registers, chain merges, pass-throughs)
  r_st0..r_st7         one closed stnrgc each (btab + the rs_s entry frs with r_st0)
  r_stm                stream + tload stand-in (+ the S-face cw_s exit fs)
  r_ctl, r_sc          ctl leaf, scalar leaf
  r_su                 suvm + red + 8 lrly + 8 lane heads + 24 SFU (42 leaf clock pins, judged per linked pair)
  r_tap                the heads' fill tap
  r_hc0..r_hc3         column c: xhead + its 8 x leaves (+ the N-face rs_n entry fn with r_hc1)
Schedule: the slice has cross-region LOOPS (ctl -> SU / station / scalar -> ctl, fdn <-> fup), so no offset schedule
exists.  Every cross-region reader pin is a lag pin: it sees its net exactly E + 1 = 3 edges after the flat parent
(lp.py lag_pins; the lockstep reference is qfd_dv_s5_flat_lagref = the flat parent with those pins delayed 3).  Those
+3 edges per crossing are the compiler's re-schedule (record "compiler" block; NOTICE lanes/QW-GEN3.md).
Main: D 4 / E 2 (+3 a crossing).  Fallback (qfd_dv_s5b): D 8 / E 4 (+5 a crossing: two more flight edges for the
2.2-mm pass-channel / N->S corridor crossings, a structurally different timing envelope).

    python3 tools/qwen_dv/gen_slice5_lp_spec.py [--gen]   (--gen also runs lp.py gen for both; needs tools/landed_parent/lp.py; pure text, runs locally)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/landed_parent"))
import lp  # noqa: E402

PART = ROOT / "results/arch/qw_slice5_1019/partition.json"
CHILD_SOURCES = [
    "rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv",
    "rtl/qwen_dv/qfd_dv_redstn2_regional.sv",
    "rtl/qwen_dv/qfd_dv_head_safe1.sv",
    "rtl/hdc/ot_hdc_vstream_sfu_t.sv",
    "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv",
]


def regions():
    fp = json.loads(PART.read_text())["floorplan"]
    c = lambda k: fp[k]["centre"]
    st = fp["r_st"]["rect"]                      # 2x4 station (stnent geometry): column pitch 216, rows 259.2 / 0
    R = [dict(name="r_fw", insts=["u_fdn"], centre=c("r_fw"), why="dn face strip: pin registers, chain merges, pass-throughs"),
         dict(name="r_fe", insts=["u_fup"], centre=c("r_fe"), why="up face strip: pin registers, SETID forward, pass-throughs")]
    for k in range(8):
        col, row = k // 2, k % 2
        cen = [round(st[0] + 118.8 + 216.0 * col, 3), round(st[1] + (378.0 if row == 0 else 118.8), 3)]
        ins = [f"u_r{k}"] + (["u_btab", "u_frs"] if k == 0 else [])
        R.append(dict(name=f"r_st{k}", insts=ins, centre=cen,
                      why=f"station region {k}: closed stnrgc u_r{k}" + (" + btab (bt round trip local) + rs_s entry" if k == 0 else "")))
    R += [dict(name="r_stm", insts=["u_stm", "u_fs"], centre=c("r_stm"), why="stream + tload STAND-IN, S-face cw_s exit"),
          dict(name="r_ctl", insts=["u_ctl"], centre=c("r_ctl"), why="ctl leaf"),
          dict(name="r_sc", insts=["u_sc"], centre=c("r_sc"), why="scalar leaf"),
          dict(name="r_su", insts=["u_suvm", "u_red", "u_lrly*", "u_head*", "u_exp*", "u_rcp*", "u_rsq*"], centre=c("r_su"),
               why="SU block: suvm + red + 8 lrly + 8 lane heads + 24 SFU (RD relays = reach stages; lane_h ML1/RD2)"),
          dict(name="r_tap", insts=["u_tap"], centre=c("r_tap"), why="heads fill tap")]
    hb = fp["r_hc"]["rect"]
    for k in range(4):
        R.append(dict(name=f"r_hc{k}", insts=[f"u_xh{k}", f"u_xl{k}_*"] + (["u_fn"] if k == 1 else []),
                      centre=[round(hb[0] + 243.0 + 486.0 * k, 3), c("r_hc")[1]],
                      why=f"head column {k}: xhead + 8 x leaves" + (" + N-face rs_n entry" if k == 1 else "")))
    return R


def base_spec(name, D, E):
    return {
        "why": f"QW-SLICE6 10-19 Q.STA.SLICE.2: hardened one-level slice2 (plan claude/qw-slice5-1019 @961b2dafd), "
               f"D {D} / E {E}; every cross-region reader pin lagged E + 1 (cross-region loops: compiler re-schedule)",
        "top": "qfd_dv_s5_flat",
        "top_lp": name + "_lp",
        "sources": ["rtl/qwen_dv/s5/qfd_dv_s5_flat.sv"],
        "child_sources": CHILD_SOURCES,
        "defines": ["OT_S5_HARD"],
        "params": {},
        "out_dir": "rtl/qwen_dv/s5/lp",
        "record_dir": "results/arch/qw_slice6_1019/lp",
        "clock_ports": ["ck"],
        "clock_pins": ["ck", "clk"],
        "reset_port": "rst_n",
        "reset_pins": ["rst_n"],
        "D": D, "E": E,
        "share_rings": True,
        "regions": regions(),
        "mut_child": "u_ctl",
        "bench": {"cycles": 6000, "reset_cycles": 16, "sim": "verilator"},
    }


def lag_pins(S):
    """every (instance, pin) that reads a net driven in another region"""
    S2 = dict(S, schedule="reference", _spec_path="x")
    P = lp.Parent(S2).plan()
    pins = {}
    for L in P["lands"]:
        for rd in L["readers"]:
            inst, pin = rd.split(".", 1)
            pins.setdefault(inst, set()).add(pin)
    return [{"inst": i, "pins": sorted(p), "why": "cross-region reader (slice loops: +E+1 re-schedule)"} for i, p in sorted(pins.items())], P


def main():
    out = ROOT / "tools/landed_parent/specs"
    for name, D, E in (("qfd_dv_s5b", 8, 4), ("qfd_dv_s5", 4, 2)):      # main last: its lagref keeps the shared name
        S = base_spec(name, D, E)
        lg, P = lag_pins(S)
        S["lag_pins"] = lg
        (out / f"{name}.json").write_text(json.dumps(S, indent=1) + "\n")
        bits = sum(L["width"] for L in P["lands"])
        print(f"{name}: {len(P['lands'])} landings ({bits} bits), {sum(len(x['pins']) for x in lg)} lag pins on {len(lg)} instances")
        if "--gen" in sys.argv:
            lp.gen(lp.load(str(out / f"{name}.json")))
            if name != "qfd_dv_s5":     # both specs share the flat top: give each lockstep reference its own name
                d = ROOT / "rtl/qwen_dv/s5/lp"
                src = (d / "qfd_dv_s5_flat_lagref.sv").read_text().replace("module qfd_dv_s5_flat_lagref", f"module {name}_flat_lagref")
                (d / f"{name}_flat_lagref.sv").write_text(src)
                for f in (d / f"tb_{name}_lp.sv", d / f"{name}_lp_bench.sh"):
                    f.write_text(f.read_text().replace("qfd_dv_s5_flat_lagref", f"{name}_flat_lagref"))


if __name__ == "__main__":
    main()
