#!/usr/bin/env python3
"""el1011-hbm-smt 2026-10-12: ref_tile CLUSTER specs for the SM tile (ot_hbm_accel_smh_tile_eg / _wg).

One hardened cluster per SM tile: the 12 closed ref_tile sub-tiles (pt_w, pt_e, 2 x {xs, bdc, tcl, tcl, tct}) + the tile
glue (ot_cg_tile ICG + enable regs, reset relay, leaf i-stages, G1 select / gather relays), hardened once and stepped x16.

Floorplan re-derived from the CLOSED child LEFs on the 43.2-um child lattice with >= 20 um channels and >= 20 um from
every pin face (ref_tile floorplan_checks):
  W column  : bdc1 / xs1 / pt_w / xs0 / bdc0  (xs <-> pt_w landing channels 58-60 um: 2,900 landing wires with lateral
              shifts, cut demand 1,821 at x 115 vs ~3,100 H tracks at 60 um -> 0.59; at 43.2 um it would be 0.82)
  E column  : tct1 / tcl pair1 / pt_e / tct0 / tcl pair0 (tcc stays R0 in both leaves: tcl sum_o S -> tct sum_i N)
  leaf 1's xs and bdc are MX images (landing / input faces turn towards pt_w / xs).  A mirrored child must carry no M6
  face pins (M4 48/12 and M6 64/16 tracks have no common mirror residue): xs is the exact-io_tcl re-route p50x.
The 587.52 x 1080 hand slot does not fit on the lattice (bdc above xs needs 1,245 um of column height; the tcl pair needs a
216-um column beside pt_e): outline 630.72 x 1252.8 (children 381.6k um2 = 48 % + glue).
Pin plan: rin/bin at the y of pt_w's own rin/bin pins and rout/bout at the SAME y on the opposite face (abutment-ready for
the next tile; pt_e's rout/bout sit at those y within 0.5 um, cut demand 30), gin + straps + clk/rst/cg on N, gout on S.
wg = MY mirror: pt_w on the E side, rin/bin on E, rout/bout on W, children MY (R0 ones) / R180 (MX ones).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
L = 43.2
W, H = 630.72, 1252.8
V = "physical/ref_tile/{}/views/{}"
VIEWS = {"pt_w": V.format("smh_pt_w_ref_p45h", "ot_hbm_accel_smh_pt_w"),
         "pt_e": V.format("smh_pt_e_ref_p40s", "ot_hbm_accel_smh_pt_e"),
         "xs": V.format("smh_xs_ref_p50x", "ot_hbm_accel_smh_xs"),
         "bdc": V.format("smh_bdc_ref_p50", "ot_hbm_accel_smh_bdc"),
         "tcl": V.format("smh_tcl_ref_p45", "ot_hbm_accel_smh_tcl"),
         "tct": V.format("smh_tct_ref_p45", "ot_hbm_accel_smh_tct")}
DIM = {"pt_w": (302.4, 371.52), "pt_e": (194.4, 371.52), "xs": (302.4, 157.68), "bdc": (112.32, 142.56),
       "tcl": (86.4, 120.96), "tct": (194.4, 71.28)}
# eg (R0 leaf 0 above the band, MX leaf 1 below): (kind, instance glob, x, y, orient)
EG = [("pt_w", "*u_ptw", 43.2, 432.0, "R0"), ("pt_e", "*u_pte", 388.8, 432.0, "R0"),
      ("xs", "*g_lf?0?.u_lh.u_xs", 43.2, 864.0, "R0"), ("bdc", "*g_lf?0?.u_lh.u_bdc", 129.6, 1080.0, "R0"),
      ("tct", "*g_lf?0?.u_lh.u_tcc.u_tr", 388.8, 864.0, "R0"),
      ("tcl", "*g_lf?0?.u_lh.u_tcc.u_h0", 388.8, 993.6, "R0"), ("tcl", "*g_lf?0?.u_lh.u_tcc.u_h1", 518.4, 993.6, "R0"),
      ("xs", "*g_lf?1?.u_lh.u_xs", 43.2, 216.0, "MX"), ("bdc", "*g_lf?1?.u_lh.u_bdc", 129.6, 43.2, "MX"),
      ("tct", "*g_lf?1?.u_lh.u_tcc.u_tr", 388.8, 129.6, "R0"),
      ("tcl", "*g_lf?1?.u_lh.u_tcc.u_h0", 388.8, 259.2, "R0"), ("tcl", "*g_lf?1?.u_lh.u_tcc.u_h1", 518.4, 259.2, "R0")]
MYO = {"R0": "MY", "MX": "R180"}
DEFINES = ["OT_SMH_CG_ENREG", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY", "OT_SMH_HIER",
           "OT_SMH_PTW_OHDLY"]
BDEF = " ".join(f"--define {d}" for d in DEFINES)
BENCH = ("W=$(mktemp -d /tmp/smtb.XXXXXX); python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 4 --smh --cg " + BDEF +
         " {mut}--cg-gap 300 --build-jobs 8 --workdir $W --out {{RUN}}/b_{n}.json > {{RUN}}/b_{n}.log 2>&1; rc=$?; "
         "cat {{RUN}}/b_{n}.log | tail -5; grep -h CG_LOCKSTEP $W/*/runtime.log; {tail}")
BENCHES = [
    {"name": "lockstep_enreg_xlk", "expect": "pass", "pass_regex": "SMT_LOCKSTEP_PASS", "threads": 8, "peak_ram_gb": 24,
     "cmd": BENCH.format(n="lockstep_enreg_xlk", mut="", tail=(
         "test $rc -eq 0 && grep -q 'CG_LOCKSTEP mismatches 0 ' $W/*/runtime.log && grep -q '\"total_cycles\": 8270' "
         "{RUN}/b_lockstep_enreg_xlk.json && echo SMT_LOCKSTEP_PASS"))},
    {"name": "mut_late32", "expect": "fail", "fail_regex": "CG_LOCKSTEP mismatches [1-9]", "threads": 8, "peak_ram_gb": 24,
     "cmd": BENCH.format(n="mut_late32", mut="--cg-mut-late ", tail=(
         "test $rc -eq 0 && ! grep -q 'CG_LOCKSTEP mismatches [1-9]' $W/*/runtime.log"))},
    {"name": "mut_hold0", "expect": "fail", "fail_regex": "CG_LOCKSTEP mismatches [1-9]", "threads": 8, "peak_ram_gb": 24,
     "cmd": BENCH.format(n="mut_hold0", mut="--cg-mut-hold0 ", tail=(
         "test $rc -eq 0 && ! grep -q 'CG_LOCKSTEP mismatches [1-9]' $W/*/runtime.log"))}]


def ptw_pins():
    """pt_w face pins (name -> (layer, x, y)) from its LEF (the closed view, or its placeholder before closure)"""
    t = (ROOT / VIEWS["pt_w"] / "ot_hbm_accel_smh_pt_w.lef").read_text()
    out = {}
    for m in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1", t, re.S):
        r = re.search(r"LAYER\s+(\S+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", m.group(2))
        if r:
            out[m.group(1).replace("\\", "")] = (r.group(1), round((float(r.group(2)) + float(r.group(4))) / 2, 3),
                                                 round((float(r.group(3)) + float(r.group(5))) / 2, 3))
    return out


def bits(n, k):
    return [f"{n}[{i}]" for i in range(k)]


def io_tcl(variant):
    pw = ptw_pins()
    xin, xout = (0.0, W) if variant == "eg" else (W, 0.0)
    y0 = 432.0
    out = ["# generated by physical/ref_tile_specs/smh/mk_smh_tile_cluster.py: SM tile cluster pin plan (" + variant + ")",
           "# rin/bin at pt_w's own pin y (straight into the child), rout/bout at the same y on the far face (next tile)"]
    def pp(n, layer, x, y):
        sz = "0.192 0.024" if layer == "M4" else "0.024 0.192"
        out.append(f"place_pin -pin_name {{{n}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{sz}}} "
                   "-force_to_die_boundary")
    for src, dst, k in (("rin", "rout", 1636), ("bin", "bout", 2069)):
        for i in range(k):
            lay, _, y = pw[f"{src}[{i}]"]
            assert lay == "M4"
            pp(f"{src}[{i}]", "M4", xin, round(y0 + y, 3))
            pp(f"{dst}[{i}]", "M4", xout, round(y0 + y, 3))
    # N face: gin lanes (2 x 50) + straps / clock / reset / wake; S face: gout lanes (4 x 50); 0.48 um pitch, M5 tracks
    def row(names, x0, y, pitch=0.48):
        for i, n in enumerate(names):
            pp(n, "M5", round(x0 + i * pitch, 3), y)
    gx0 = 0.012 + 48 * round((W / 2 - 100 * 0.48) / 0.048 / 48)   # centred, on the M5 track (0.012 + k * 0.048)
    row(bits("gout", 200), round(gx0, 3), 0.0)
    nn = (bits("gin", 100) + bits("xs_a1", 18) + bits("xs_g1", 10) + bits("xs_a2", 14) + bits("xs_g2", 10)
          + ["rst_n", "cgi", "cgo"])
    nx0 = 0.012 + 0.048 * round((W / 2 - len(nn) * 0.24) / 0.048)
    row(nn, round(nx0, 3), H)
    pp("clk", "M5", round(nx0 + len(nn) * 0.48 + 4.8, 3), H)
    return "\n".join(out) + "\n"


def spec(variant):
    name = f"smh_tile_{variant}_ref"
    kids = []
    for kind, inst, x, y, o in EG:
        if variant == "wg":
            w = DIM[kind][0]
            x = round(round((W - x - w) / L) * L, 3)
            o = MYO[o]
        kids.append({"view": VIEWS[kind], "count": 1, "at": [x, y], "orient": o, "inst": inst})
    io = f"physical/ref_tile_specs/smh/{name}_pins.tcl"
    (ROOT / io).write_text(io_tcl(variant))
    fin, fout = ("W", "E") if variant == "eg" else ("E", "W")
    src = json.loads((OUT / "smh_pt_w_ref_p45h.json").read_text())["sources"]
    src = src + [f for f in ("rtl/hdc/ot_hdc_cg.sv", "rtl/hbm_accel/cg/ot_cg_tile.sv") if f not in src]
    return {
        "name": name, "top": f"ot_hbm_accel_smh_tile_{variant}", "kind": "cluster",
        "sources": src, "params": {}, "defines": DEFINES, "clock_port": "clk", "reset_ports": ["rst_n"],
        "spine_through_icg": True,
        "outline": {"w": W, "h": H},
        "children": kids,
        "pins": {fin: ["rin", "bin"], fout: ["rout", "bout"], "S": ["gout"],
                 "N": ["gin", "xs_a1", "xs_g1", "xs_a2", "xs_g2", "clk", "rst_n", "cgi", "cgo"]},
        "io_tcl": io,
        "refglob": "*",
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 96},
        "job": {"owner": "Claude:el1011-hbm-smmv-b", "branch": "claude/el1011-hbm-smt", "tag": "r1",
                "purpose": (f"[smmv-b/smt] ot_hbm_accel_smh_tile_{variant}: SM tile as ONE ref_tile cluster (owner "
                            "contract: harden once, step x16; wg = MY mirror) over the 12 closed ref_tile sub-tiles "
                            "(pt_w p45h, pt_e p40s, xs p50, bdc p50, tcl p45, tct p45), floorplan re-derived from their "
                            "LEFs on the 43.2-um lattice (630.72 x 1252.8, landing channels 58-60 um, cut 0.59), clock "
                            "spine through the tile ICG, exact abutment pin plan. Benches: lockstep_enreg_xlk (exact, "
                            "8270 cycles with the gather relays) + mut_late32 / mut_hold0 must fail."),
                "benches": BENCHES},
    }


def main():
    for v in sys.argv[1:] or ["eg", "wg"]:
        s = spec(v)
        p = OUT / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print(p.relative_to(ROOT))


if __name__ == "__main__":
    main()
