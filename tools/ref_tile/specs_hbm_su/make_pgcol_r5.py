#!/usr/bin/env python3
"""HBM-SU r5 2026-10-17: kit specs for the three leaf masters of the per-quarter SU programme cluster
ot_hbm_su_programme_pslice_c5 (rtl/.../ot_hbm_su_programme_pgcol.sv).

Why: the flat per-quarter tile failed the measured clock rule twice (r3 8058137fc: TT insertion 851..1280 ps, spread 429;
r4 294f94bbd: 830..1148 ps, spread 318; both GRT > 3.5 h): one root over 98 SRAMs on 940 x 760 um.
Leaves (each its own clock root, <= ~3.5k flops):
  * hbm_su_pgcol_s_r5 (ot_hbm_su_programme_pgcol_s, x7 per quarter): 4 packed index + 3 dictionary SRAMs.
    302.4 x 259.2 um; index stack MY at x 43.2 (pins E), dictionary stack R0 at x 172.8 (pins W) -> both rd_out/wd_in
    faces on one 34.8 um channel; S band (y 0..43.2) = 256 command registers; clk on S in the channel.
  * hbm_su_pgcol_l_r5 (ot_hbm_su_programme_pgcol_l, x3 per quarter): 4 packed index + 13 dictionary SRAMs.
    302.4 x 453.6 um; MY stack: dictionary 0..4 (bottom) + index 0..3 (top); R0 stack: dictionary 5..12.
  * hbm_su_pghead_r5 (ot_hbm_su_programme_pghead, x1 per quarter): cfg pin stage + column decode + fault OR.
    86.4 x 86.4 um; inputs W, outputs E (top-down: faces are placeholders for the cluster pin assignment).
Macros on the 43.2 um lattice (x 43.2 / 172.8, stack base y 43.2, abutted 41.04 um pitch as r3/r4).
Usage: python3 tools/ref_tile/specs_hbm_su/make_pgcol_r5.py   (from the repo root), then ref_tile.py gen on each spec.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R4 = ROOT / "physical/ref_tile/hbm_su_pslice_r4_1017/spec.json"
OUT = ROOT / "tools/ref_tile/specs_hbm_su"
VIEW = "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2"
SRC = "rtl/hbm_accel/generic/adapters/static_su/programme/"
MH, LAT = 41.04, 43.2
BENCH = "tools/hbm_static/su_programme_pgcol_run.sh"


def bench(name, only=None):
    b = {"name": name, "threads": 8, "peak_ram_gb": 48, "needs": ["verilator"]}
    if only is None:
        b.update(cmd=f"OUT={{RUN}}/bench/pos bash {BENCH}", expect="pass", pass_regex="SU_PROGRAMME_PGCOL_GATE PASS",
                 min_count_regex="SU_PROGRAMME_PGCOL PASS edges=(\\d+)")
    else:
        b.update(cmd=f"OUT={{RUN}}/bench/{only} ONLY={only} bash {BENCH}", expect="fail",
                 fail_regex="SU_PROGRAMME_PGCOL FAIL mismatches=[1-9]")
    return b


BENCHES = [bench("pgcol_equiv_7111_q0123"), bench("pgcol_mut_cfg", "cfg"), bench("pgcol_mut_phase", "phase"),
           bench("pgcol_mut_cfgany", "cfgany"), bench("pgcol_mut_stale", "stale")]


def stack(kind, banks, x, orient, y0=LAT):
    return [{"view": VIEW, "count": 1, "inst": f"*u_p.g_m4.{kind}?0?.mem.g?{b}?.mem",
             "at": [round(x, 3), round(y0 + MH * j, 3)], "orient": orient, "exact": True} for j, b in enumerate(banks)]


def ranges(face_len, groups, margin=4.0):
    """contiguous pin_ranges over the whole face, proportional to bit count."""
    tot = sum(n for _, n in groups)
    span = face_len - 2 * margin
    out, x = {}, margin
    for p, n in groups:
        w = span * n / tot
        out[p] = [round(x, 3), round(x + w - 0.3, 3)]
        x += w
    return out


def leaf(s4, name, top, w, h, macros, why):
    s = json.loads(json.dumps(s4))
    s["name"] = name
    s["top"] = top
    s["sources"] = [SRC + "ot_hbm_su_programme.sv", SRC + "ot_hbm_su_programme_pgcol.sv",
                    VIEW + "/ot_sram_1r1w_128x256_m1_r2c2_bb.v"]
    s["outline"] = {"w": w, "h": h, "exact": True}
    s["macros"] = macros
    s.pop("io_tcl", None)
    s["pins"] = {"N": ["cfg_data", "cfg_bank", "cfg_row", "cfg_we", "cfg_any", "rst_n", "start", "length"],
                 "S": ["command", "busy", "valid", "done", "fault", "edge_index", "clk"]}
    pr = ranges(w, [("cfg_data", 256), ("cfg_bank", 5), ("cfg_row", 7), ("cfg_we", 1), ("cfg_any", 1), ("rst_n", 1),
                    ("start", 1), ("length", 16)])
    # S: command W of the macro channel (1.8 pins/um), clk in the channel (x 138.0..172.8, beside the register mass),
    # status bits E of it
    pr.update({"command": [4.0, 148.0], "clk": [150.8, 151.4], "busy": [154.0, 156.0], "valid": [156.5, 158.5],
               "done": [159.0, 161.0], "fault": [161.5, 163.5], "edge_index": [164.0, round(w - 4.0, 3)]})
    s["pin_ranges"] = pr
    s["route"] = dict(s["route"], threads=8, peak_ram_gb=24)
    s["pin_regs"] = {"enable": False, "reason": (
        "ot_hbm_su_programme_pgcol registers start/length at the pin (the pslice STAGES 1 stage); cfg_* arrive from the "
        "head leaf's registered configuration stage (= the pslice c_* stage) and land on the PIPE 2 per-bank write "
        "enable / config copy registers; every output is a register (command, busy_q, valid, done, edge_index, "
        "fault_d). A kit flop stage would add an edge the start-advance contract (DEPTH+4) does not price.")}
    s["structural_change"] = why
    s["job"] = dict(s["job"], tag="r5", purpose=f"SU programme cluster leaf {top} (HBM-SU r5 per-column split)",
                    views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
                    benches=BENCHES)
    return s


WHY = ("SUCCESSOR of the flat per-quarter SU programme tile (hbm_su_pslice_r3_1017 gate FAIL 8058137fc: TT clock "
       "insertion 851..1280 ps, spread 429, GRT 4 h timeout; hbm_su_pslice_r4_1017 294f94bbd: TT 830..1148 ps, spread "
       "318, GRT > 3.5 h with clock NDRs dropped, killed): one root over 98 SRAMs + 14k flops on 940 x 760 um. r5 = "
       "cluster ot_hbm_su_programme_pslice_c5: one leaf per command column (own packed 16-edge/row index, own "
       "dictionary, own 256 command flops, controller replica) + a head leaf (cfg stage + column decode + fault OR). "
       "Lockstep bench vs r4 on all 4 quarters PASS, mutants cfg/phase/cfgany/stale FAIL (db03bbcbd, "
       "results/rtl/hbm_su_lane_1017/r5_pgcol). Start advance unchanged DEPTH+4. ")


def main():
    s4 = json.loads(R4.read_text())
    ms = stack("ix", range(4), LAT, "MY") + stack("dt", range(3), 4 * LAT, "R0")
    s = leaf(s4, "hbm_su_pgcol_s_r5", "ot_hbm_su_programme_pgcol_s", 302.4, 259.2, ms, WHY + (
        "THIS leaf: S master (7 per quarter): 4 index + 3 dictionary SRAMs, 302.4 x 259.2, index stack MY x 43.2 and "
        "dictionary stack R0 x 172.8 facing one 34.8 um channel, S band = 256 command flops, ~1.3k flops one root."))
    (OUT / "hbm_su_pgcol_s_r5.json").write_text(json.dumps(s, indent=1) + "\n")
    ml = (stack("dt", range(5), LAT, "MY") + stack("ix", range(4), LAT, "MY", LAT + 5 * MH)
          + stack("dt", range(5, 13), 4 * LAT, "R0"))
    s = leaf(s4, "hbm_su_pgcol_l_r5", "ot_hbm_su_programme_pgcol_l", 302.4, 453.6, ml, WHY + (
        "THIS leaf: L master (3 per quarter): 4 index + 13 dictionary SRAMs, 302.4 x 453.6, MY stack dictionary 0..4 + "
        "index 0..3, R0 stack dictionary 5..12, one 34.8 um channel, N cfg band 41 um, S band = 256 command flops, ~3.3k flops one root."))
    (OUT / "hbm_su_pgcol_l_r5.json").write_text(json.dumps(s, indent=1) + "\n")
    h = leaf(s4, "hbm_su_pghead_r5", "ot_hbm_su_programme_pghead", 86.4, 86.4, [], WHY + (
        "THIS leaf: head (1 per quarter): cfg pin stage + column decode (bank[15:5] = column) + sticky fault OR of the "
        "10 leaves + leaf-valid lockstep check; pin-bound register tile, inputs W / outputs E (placeholder faces)."))
    h["sources"] = [SRC + "ot_hbm_su_programme_pgcol.sv"]
    h["pins"] = {"W": ["clk", "rst_n", "cfg_we", "cfg_bank", "cfg_row", "cfg_data", "l_fault", "l_valid"],
                 "E": ["o_we", "o_any", "o_bank", "o_row", "o_data", "fault"]}
    h["pin_ranges"] = dict(ranges(86.4, [("cfg_data", 256), ("cfg_bank", 16), ("cfg_row", 7), ("cfg_we", 1),
                                         ("rst_n", 1), ("l_fault", 10), ("l_valid", 10)], 2.0),
                           **ranges(86.4, [("o_data", 256), ("o_row", 7), ("o_bank", 5), ("o_any", 1), ("o_we", 10),
                                           ("fault", 1)], 2.0))
    # clk in the W face middle of cfg_data
    h["pin_ranges"]["clk"] = [42.0, 42.6]
    h["pin_ranges"]["cfg_data"] = [2.0, 41.7]
    h["pin_ranges"]["cfg_bank"] = [42.9, h["pin_ranges"]["cfg_bank"][1]]
    h["route"] = dict(h["route"], threads=8, peak_ram_gb=16)
    h.pop("macro_halo_um", None)
    h["pin_regs"] = {"enable": False, "reason": (
        "ot_hbm_su_programme_pghead is itself the configuration pin stage of the cluster (= the pslice c_* stage): "
        "cfg inputs land on c_we/c_bank/o_row/o_data registers, l_fault on the fault OR register, l_valid on the sticky "
        "check; outputs are register outputs except o_we/o_any/o_bank (one 11-bit compare after c_bank/c_we). A kit flop "
        "stage would add an edge the leaf timing contract does not price.")}
    (OUT / "hbm_su_pghead_r5.json").write_text(json.dumps(h, indent=1) + "\n")
    for n in ("s", "l"):
        print(n, len(json.loads((OUT / f"hbm_su_pgcol_{n}_r5.json").read_text())["macros"]), "macros")


if __name__ == "__main__":
    main()
