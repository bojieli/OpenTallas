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
RELAY = "rtl/lib/ot_rst_relay.sv"
# NATIVE-FIX3/pgs 10-18: committed mutant FAIL witnesses (fleet run of the bench at the fix commit)
WIT = "results/rtl/nf3_pgs_1018/bench"
AUDIT = "results/arch/native_3_1017/native_3_audit.json"


def bench(name, only=None):
    b = {"name": name, "threads": 8, "peak_ram_gb": 48, "needs": ["verilator"]}
    if only is None:
        b.update(cmd=f"OUT={{RUN}}/bench/pos bash {BENCH}", expect="pass", pass_regex="SU_PROGRAMME_PGCOL_GATE PASS",
                 min_count_regex="SU_PROGRAMME_PGCOL PASS edges=(\\d+)")
    else:
        b.update(cmd=f"OUT={{RUN}}/bench/{only} ONLY={only} bash {BENCH}", expect="fail",
                 fail_regex="SU_PROGRAMME_PGCOL FAIL mismatches=[1-9]", fail_witness=f"{WIT}/run_{only}_q0.log")
    return b


BENCHES = [bench("pgcol_equiv_7111_q0123"), bench("pgcol_mut_cfg", "cfg"), bench("pgcol_mut_phase", "phase"),
           bench("pgcol_mut_cfgany", "cfgany"), bench("pgcol_mut_stale", "stale"),
           bench("pgcol_mut_rstrelay", "rstrelay"), bench("pgcol_mut_cpin", "cpin"), bench("pgcol_mut_oreg", "oreg"),
           bench("pgcol_mut_freg", "freg"), bench("pgcol_mut_hrelay", "hrelay")]


def stack(kind, banks, x, orient, y0=LAT):
    return [{"view": VIEW, "count": 1, "inst": f"*u_p.g_m4.{kind}?0?.mem.g?{b}?.mem",
             "at": [round(x, 3), round(y0 + MH * j, 3)], "orient": orient, "exact": True} for j, b in enumerate(banks)]


def ranges(face_len, groups, margin=4.0):
    """contiguous disjoint pin_ranges over the whole face: a <= 16-bit port gets max(1.2, 0.3 n) um, the wide ports share
    the rest in proportion to their bit counts (0.3 um gap after every range)."""
    fixed = {p: max(1.2, 0.3 * n) for p, n in groups if n <= 16}
    tot = sum(n for p, n in groups if p not in fixed)
    span = face_len - 2 * margin - sum(fixed.values())
    assert span > 0 and tot > 0
    out, x = {}, margin
    for p, n in groups:
        w = fixed.get(p, span * n / tot if tot else 0.0)
        out[p] = [round(x, 3), round(x + w - 0.3, 3)]
        x += w
    assert abs(x - (face_len - margin)) < 1e-6, (x, face_len)
    return out


def leaf(s4, name, top, w, h, macros, why):
    s = json.loads(json.dumps(s4))
    s["name"] = name
    s["top"] = top
    s["sources"] = [RELAY, SRC + "ot_hbm_su_programme.sv", SRC + "ot_hbm_su_programme_pgcol.sv",
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
    # gate e8c5e2cf6: PPL packed each port into a fraction of its range (S 293 pins on 38 um, head cfg_data on ~25 um):
    # the balanced placer spreads every port uniformly over its own range
    s["route"] = dict(s["route"], threads=8, peak_ram_gb=24, pin_group_max=1,
                      pin_balance={"group_max": 1, "h": "M4", "v": "M3 M5"})
    s["pin_regs"] = {"enable": False, "reason": (
        "ot_hbm_su_programme_pgcol registers every input in RTL: start/length at the pin (the pslice STAGES 1 stage), "
        "cfg_we/cfg_any/cfg_bank on the CPIN 1 pin stage (NATIVE-FIX3 10-18, +1 configuration edge), cfg_row/cfg_data on the per-bank config copy registers (the head presents them one edge after the control), "
        "rst_n only into ot_rst_relay; every output is a register (command, busy_q, valid, done, edge_index, fault_d). "
        "A kit flop stage would add an edge the start-advance contract (DEPTH+4) does not price.")}
    s["structural_change"] = why
    s["job"] = dict(s["job"], tag="r5", branch="claude/nf3-pgs-1018", owner="Claude:NATIVE-FIX3/pgs", purpose=f"SU programme cluster leaf {top} (HBM-SU r5 per-column split)",
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


NF3 = (" NATIVE-FIX3/pgs 10-18 (NATIVE-3 audit, claude/native-3-1017 73adc87ea, lanes/NATIVE-3.md): pin registers in "
       "RTL -- leaf: ot_rst_relay at rst_n (release +3 edges) and a pin stage on cfg_we/cfg_any/cfg_bank (CPIN 1; cfg_row/cfg_data stay on the config copy registers, presented by the head one edge later: gate g1 with all cfg inputs pin-flopped had TT pin-flop spread 101 ps); head: export "
       "registers on every output (o_we decoded into one flop per column, OREG 1), l_fault pin registers (FREG 1, "
       "leaves report fault FADV 2 edges early so the cluster fault edge is unchanged) and ot_rst_relay at rst_n (HRLY 1, "
       "gate g1 rst_n capture 238 ps). Cluster configuration latency "
       "+2 edges (compile-scheduled: the host configures while idle, 2 edges earlier; a write on pin edge e pairs with a "
       "start on edge e+2 for the reject rule); start advance DEPTH+4, command/valid/done/busy/fault edges unchanged. "
       "Bench: lockstep vs r4 on all 4 quarters PASS with the cluster writes driven 2 edges ahead + reset-release check "
       "(3 edges, leaves and head); mutants cfg/phase/cfgany/stale/rstrelay/cpin/oreg/freg/hrelay FAIL (results/rtl/nf3_pgs_1018).")


def main():
    s4 = json.loads(R4.read_text())
    ms = stack("ix", range(4), LAT, "MY") + stack("dt", range(3), 4 * LAT, "R0")
    s = leaf(s4, "hbm_su_pgcol_s_r5", "ot_hbm_su_programme_pgcol_s", 302.4, 259.2, ms, WHY + (
        "THIS leaf: S master (7 per quarter): 4 index + 3 dictionary SRAMs, 302.4 x 259.2, index stack MY x 43.2 and "
        "dictionary stack R0 x 172.8 facing one 34.8 um channel, S band = 256 command flops, ~1.3k flops one root.") + NF3)
    s["reroute_reason"] = {
        "kind": "pin_register", "source": AUDIT, "cell": "ot_hbm_su_programme_pgcol_s", "capture_ps": 414.2,
        "launch_ps": 109.2, "closed_job": "hbm_su_pgcol_s_r5-r5-9e33ce295",
        "why": ("NATIVE-3 audit (claude/native-3-1017 73adc87ea, lanes/NATIVE-3.md): capture rst_n 414.2, cfg_we 390.6, "
                "cfg_any 388.4, cfg_bank[0..4] 284.4..303.9 ps > 190 (R 271.4; spread TT 50.3 / FF 46.7 OK) -> "
                "ot_rst_relay at rst_n + pin registers on cfg_we/cfg_any/cfg_bank (native_capture class; "
                "RTL changed, so kind pin_register)"),
        "fix": ("RTL pin registers: rst_n drives only ot_rst_relay (2 sync + 1 relay, 2 regions); every cfg "
                "control input (cfg_we/cfg_any/cfg_bank) lands on a pin flop (CPIN 1, +1 configuration edge, compile-"
                "scheduled); head export stage +1, row/data +1 more (DLAT 1)")}
    (OUT / "hbm_su_pgcol_s_r5.json").write_text(json.dumps(s, indent=1) + "\n")
    ml = (stack("dt", range(5), LAT, "MY") + stack("ix", range(4), LAT, "MY", LAT + 5 * MH)
          + stack("dt", range(5, 13), 4 * LAT, "R0"))
    s = leaf(s4, "hbm_su_pgcol_l_r5", "ot_hbm_su_programme_pgcol_l", 302.4, 453.6, ml, WHY + (
        "THIS leaf: L master (3 per quarter): 4 index + 13 dictionary SRAMs, 302.4 x 453.6, MY stack dictionary 0..4 + "
        "index 0..3, R0 stack dictionary 5..12, one 34.8 um channel, N cfg band 41 um, S band = 256 command flops, ~3.3k flops one root.") + NF3)
    # gate e8c5e2cf6: GPL-0305 RePlAce diverged (3.2k flops in 41k um2 placeable at PD 0.5) -> lower target density
    s["route"]["pd"] = 0.3
    (OUT / "hbm_su_pgcol_l_r5.json").write_text(json.dumps(s, indent=1) + "\n")
    h = leaf(s4, "hbm_su_pghead_r5", "ot_hbm_su_programme_pghead", 86.4, 86.4, [], WHY + (
        "THIS leaf: head (1 per quarter): cfg pin stage + column decode (bank[15:5] = column) + sticky fault OR of the "
        "10 leaves + leaf-valid lockstep check; pin-bound register tile, inputs W / outputs E (placeholder faces).") + NF3)
    h["reroute_reason"] = {
        "kind": "pin_register", "source": AUDIT, "cell": "ot_hbm_su_programme_pghead", "launch_ps": 225.6,
        "capture_ps": 204.5, "closed_job": "hbm_su_pghead_r5-r5-114508f65",
        "why": ("NATIVE-3 audit (claude/native-3-1017 73adc87ea, lanes/NATIVE-3.md): launch o_we[0..9] 221.1..225.6 ps > "
                "220 and capture l_fault[1,4,5,6] 199.3..204.5 ps > 190 (R 101.8); relative re-audit vs pgcol_s / lgtap "
                "fails (launch and capture together) -> o_we from export flops, l_fault into pin flops (native_launch "
                "class; RTL changed, so kind pin_register)"),
        "fix": ("RTL: every output leaves from an export register (o_we decoded into one flop per column, OREG 1; "
                "+1 configuration edge); l_fault lands on pin registers (FREG 1; leaves FADV 2 keep the cluster fault "
                "edge); head out-of-range fault delayed CLAT 2; rst_n drives only ot_rst_relay (HRLY 1)")}
    h["sources"] = [RELAY, SRC + "ot_hbm_su_programme_pgcol.sv"]
    h["pins"] = {"W": ["clk", "rst_n", "cfg_we", "cfg_bank", "cfg_row", "cfg_data", "l_fault", "l_valid"],
                 "E": ["o_we", "o_any", "o_bank", "o_row", "o_data", "fault"]}
    h["pin_ranges"] = dict(ranges(86.4, [("cfg_data", 256), ("clk", 1), ("cfg_bank", 16), ("cfg_row", 7),
                                         ("cfg_we", 1), ("rst_n", 1), ("l_fault", 10), ("l_valid", 10)], 2.0),
                           **ranges(86.4, [("o_data", 256), ("o_row", 7), ("o_bank", 5), ("o_any", 1), ("o_we", 10),
                                           ("fault", 1)], 2.0))
    h["route"] = dict(h["route"], threads=8, peak_ram_gb=16)
    h.pop("macro_halo_um", None)
    h["pin_regs"] = {"enable": False, "reason": (
        "ot_hbm_su_programme_pghead is itself the configuration pin stage of the cluster (= the pslice c_* stage): "
        "cfg inputs land on c_we/c_bank/c_row/c_data registers, l_fault on FREG 1 pin registers, l_valid on the sticky "
        "check; every output leaves from an OREG 1 export register (o_we decoded into one flop per column) or the "
        "fault register; rst_n drives only ot_rst_relay (NATIVE-FIX3 10-18). A kit flop stage would add an edge the leaf timing contract does not price.")}
    (OUT / "hbm_su_pghead_r5.json").write_text(json.dumps(h, indent=1) + "\n")
    for n in ("s", "l"):
        print(n, len(json.loads((OUT / f"hbm_su_pgcol_{n}_r5.json").read_text())["macros"]), "macros")


if __name__ == "__main__":
    main()
