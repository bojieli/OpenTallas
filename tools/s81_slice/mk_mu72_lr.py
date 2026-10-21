#!/usr/bin/env python3
"""S81-SLICE/ENDP 10-21: lp specs + landed RTL of the four selected72 MU end parents (LANDED REGIONS, see mu72_lr_geom.py).

    mk_mu72_lr.py [flavor ...]      writes tools/landed_parent/specs/mu72_<f>_lr{a,b}.json, runs lp.py gen + audit

Flat source = rtl/dsrom_sys/s81_dv/slice/mu72/lr/ot_s81sl_slice_<f>_x.sv (tools/s81_slice/mk_mu72_xtop.py from the G8 _72 top).
Landed top  = ot_s81sl_slice_<f>_lr{a,b}_lp in rtl/dsrom_sys/s81_dv/slice/mu72/lr/.  a = E 2 (MAIN), b = E 3 (FALLBACK).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mu72_lr_geom import geom, SID, HOST   # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FLAVORS = ("lepw_mab_mu", "lepw_mu", "lepe_mu", "lepe_nh_mu")
STAGES = 10
OREG = 3


def spec(f, v):
    g = geom(f, v)
    asm = json.load(open(ROOT / f"physical/ref_tile/s81_mu72_assembly/{f}.json"))
    lanes = [f"u_ln{i}" for i in range(4 if f == "lepw_mab_mu" else 2)]
    pr = {p: "K" for i in range(len(lanes)) for p in (f"rx{i}", f"tx{i}")}
    # inputs land at the face in P (ring P->K / P->ML); outputs leave K through OREG relay stages (lp lands no output
    # port): 3 registered hops spread over the ~1.3-1.6 mm face run (<= ~400 um each), +3 edges, priced.
    outs = ["mu_rt", "fault"] + (["f_host", "f_lf", "f_ks"] if f == "lepe_mu" else [])
    pr.update({"ch_b": "K", "mu_c": "P", "mu_rc": "P", **{p: "K" for p in outs}})
    if f == "lepe_mu":
        pr.update({"t_host": "P", "t_kd": "P"})
    return {
        "top": f"ot_s81sl_slice_{f}_x",
        "top_lp": f"ot_s81sl_slice_{f}_lr{v}_lp",
        "sources": [f"rtl/dsrom_sys/s81_dv/slice/mu72/lr/ot_s81sl_slice_{f}_x.sv"],
        "child_sources": [s for s in asm["sources"] if "/mu72/ot_s81sl_slice_" not in s],
        "defines": asm["defines"],
        "out_dir": "rtl/dsrom_sys/s81_dv/slice/mu72/lr",
        "record_dir": "results/rtl/s81_endp_1021/lp",
        "clock_ports": ["clk"], "clock_pins": ["clk", "ck", "ck_C"],
        "reset_port": "rst_n", "reset_pins": ["rst_n", "rs"],
        "regions": [{"name": "S", "insts": ["u_sl"], "centre": g["centre"]["S"]},
                    {"name": "K", "insts": ["u_lep"] + lanes, "centre": g["centre"]["K"]},
                    {"name": "ML", "insts": ["u_land"], "centre": g["centre"]["ML"]},
                    {"name": "P", "insts": [], "centre": g["centre"]["P"]}],
        # hard children are param-baked views: their #() is simulation-only (`ifndef SYNTHESIS), as lp supports
        "synthesis_hard_instances": ["u_sl", "u_lep", "u_land"],
        "static": ["sid", "ch_b"], "tb_static": {"sid": SID[f], "ch_b": "1'b1"},
        "D": 4, "E": g["E"], "reschedule": True,
        "bench": {"cycles": 14000, "reset_cycles": 16, "sim": "verilator"},
        "port_regions": pr,
        "out_regs": {p: OREG for p in outs},
        "landing_chunk_bits": 8, "landing_reset_forest": True, "landing_kept_enable": True,
        "regional_reset_ports": {"stages": STAGES, "why": (
            "S81-SLICE/ENDP 10-21 landed regions: d1a/d1b/d3a one reset root u_lpr_root across the 2.8x6.8 mm slot "
            "(in->reg -19.6/-48.6 ns, undeclared S->K reset crossing); one reset port per region beside its own pin, die "
            "releases rst_n_S/K/ML/P on one edge; 10 = 8 registered prefix hops (fenced <= ~405 um along streets that avoid the macros, up to ~2.3 mm) + branch + leaf")},
        "_note": (f"S81-SLICE/ENDP 10-21: landed-regions parent of {asm['top']} (G8 die source, u_sl = c1x_k8_cap5r_lp with its "
                  "10 real roots): regions S (u_sl) / K (u_lep + abutting lanes) / ML (u_land) / P (port entry, no child: "
                  "control/host ports land at the face, ring bank wire carries the face->endpoint run). "
                  f"{'MAIN E 2' if v == 'a' else 'FALLBACK E 3 (+1 edge on every ring: 3 T bank reach)'}."),
    }


def main(fl):
    for f in fl:
        for v in ("a", "b"):
            s = spec(f, v)
            p = ROOT / f"tools/landed_parent/specs/mu72_{f}_lr{v}.json"
            p.write_text(json.dumps(s, indent=1) + "\n")
            subprocess.run([sys.executable, "tools/landed_parent/lp.py", "gen", str(p.relative_to(ROOT))], cwd=ROOT, check=True)
            r = subprocess.run([sys.executable, "tools/landed_parent/lp.py", "audit", str(p.relative_to(ROOT))], cwd=ROOT,
                               capture_output=True, text=True)
            print(f, v, r.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    main(sys.argv[1:] or FLAVORS)
