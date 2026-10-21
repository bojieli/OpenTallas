#!/usr/bin/env python3
"""HBM-OWN/SMH2 r5 (10-21): ref_tile kit specs for the REGIONAL smh_attn halves (landed clusters, multiple_cts_roots).

Inputs: the lp records results/arch/hbm_smh_r5_1021/ot_hbm_smh_rp5<h>_<v>_record.json (tools/hbm_sm_repack_1015/rp5_gen.py
+ tools/landed_parent/lp.py gen).  Geometry, children views, pins and outline are the r4sp kits' (same 8 hard children on
the 43.2 lattice, same outline 691.2 x 1512.0 / 1252.8); only the instance paths (direct children now), the clocking
(one CTS root per region: ck_c core, ck_x, ck_m) and the region clock pins change.  No spine / insertion-aware single
root: each region tree balances only its own sinks.

    python3 tools/hbm_sm_repack_1015/rp5_kit.py [--gen]      -> physical/ref_tile_specs/smh/smh_rp5{n,s}_{m,f}.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/landed_parent"))
import lp  # noqa: E402

REC = "results/arch/hbm_smh_r5_1021"
RTL = "rtl/hbm_accel/sm/repack/h2a5"
BASE = {"n": "physical/ref_tile/smh_rp4ahn_r4sp/spec.json", "s": "physical/ref_tile/smh_rp4ahs_r4sp/spec.json"}
# r3/r4sp instance path -> r5 direct child
INST = {"n": {"u_lf0.g_lr.u_c.u_merge": "u_mg0.u_merge", "u_lf0.g_lr.u_c.u_qk": "u_qk0", "u_lf0.g_lr.u_c.u_bdc": "u_bdc0",
              "u_lf0.g_lr.u_c.u_h0": "u_h00", "u_lf0.g_lr.u_c.u_h1": "u_h10", "u_lf0.g_lr.u_c.u_xs": "u_xs0",
              "u_row0": "u_row0", "u_rowe0": "u_rowe0"},
        "s": {"u_lf1.g_lr.u_c.u_merge": "u_mg1.u_merge", "u_lf1.g_lr.u_c.u_qk": "u_qk1", "u_lf1.g_lr.u_c.u_bdc": "u_bdc1",
              "u_lf1.g_lr.u_c.u_h0": "u_h01", "u_lf1.g_lr.u_c.u_h1": "u_h11", "u_lf1.g_lr.u_c.u_xs": "u_xs1",
              "u_row1": "u_row1", "u_rowe1": "u_rowe1"}}
# region clock pins on the W face beside each region's register mass (y range in um)
CKPIN = {"n": {"c": 560.0, "x": 1080.0, "m": 160.0}, "s": {"c": 560.0, "x": 960.0, "m": 160.0}}


def spec(h, v):
    base = json.loads((ROOT / BASE[h]).read_text())
    lps = json.loads((ROOT / REC / f"lp_spec_{h}_{v}.json").read_text())
    lps["_spec_path"] = f"{REC}/lp_spec_{h}_{v}.json"
    rec_path = f"{REC}/ot_hbm_smh_rp5{h}_{v}_record.json"
    rec = json.loads((ROOT / rec_path).read_text())
    Pm = lp.Parent(lps)
    P = Pm.plan()
    regions = list(rec["regions"])
    cps = [rec["regions"][r]["clock_port"] for r in regions]
    ports = [p for p in Pm.mod["ports"] if p["name"] not in ("clk", "rst_n")]
    dom = {}
    for r in regions:
        name = "core" if r == "c" else r
        dom[name] = dict(ratio=[1, 1], ports=[f"ck_{r}"],
                         inputs=[p["name"] for p in ports if p["dir"] == "in" and p["name"] != "attn" and P["nreg"].get(f"port:{p['name']}") == r]
                         + (["rst_n", "attn"] if r == "c" else []),
                         outputs=[p["name"] for p in ports if p["dir"] == "out" and P["nreg"].get(f"port:{p['name']}") == r])
    kids = []
    for c in base["children"]:
        k = dict(c)
        k["inst"] = INST[h][c["inst"]]
        kids.append(k)
    pins = {f: [p for p in ps if p != "clk"] for f, ps in base["pins"].items()}
    pins["W"] = pins["W"] + cps
    pr = {k: v_ for k, v_ in base["pin_ranges"].items() if k != "clk"}
    for r in regions:
        y = CKPIN[h][r]
        pr[f"ck_{r}"] = [round(y - 0.54, 2), round(y + 0.54, 2)]
    lsrc = f"{RTL}/lp_{h}_{v}/ot_hbm_smh_rp5{h}_{v}.sv"
    bb = [s.replace(".v", "_bb.v") if s.startswith("physical/") and s.endswith(".v") else s for s in lps["child_sources"]]
    srcs = bb + ["rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
                 "rtl/common/landed_parent/ot_pl_land_reset_forest.sv", lsrc]
    ow = base["outline"]
    vname = "MAIN 3 regions x/c/m" if v == "m" else "FALLBACK 2 regions x/c"
    dg = 8 if v == "m" else 5
    nland = len(rec["landings"])
    checklist = {
        "1_pins": "PASS: every data pin registered in RTL (r3 pin stages unchanged: pinrow / pinbeat / straps / u_lands / u_xgi / "
                  "u_xpi / gin u_gi1 in; row_e / beat / u_xbo / u_xgo / u_xpo / u_gs out); each pin belongs to ONE region "
                  "(clock_entry_domains), region clock pins on the W face beside each region; r4sp pin ranges kept.",
        "2_reach": "rl1 / bk1 / straps / gather / xb crossing hops as r3 within a region; every region seam is a landing "
                   "(E=2 multicycle ring -> read, <= ~750 um over 2 cycles); actual route timing decides (no FIRM stations "
                   "in r5 v1: r3 station patterns name the old hierarchy).",
        "3_fanout": "r3 kept copies (xq NIPV 24 / k_oh 16, go k_b/k_p, pub rpp 16) unchanged; landings chunked 24 b (kept "
                    "per-chunk counters / selectors), reset forest leaves <= 32 loads; pre-gate native census decides.",
        "4_depth": "PASS: cut only at existing register stages (xq stage-2 bundles, column / merge outputs); landing read is a "
                   "registered slot mux; no new combinational path.",
        "5_storage": "PASS: unchanged hard SRAM children (x store, PV merge, columns); landing rings D=4 slots of flops.",
        "6_floorplan": f"r4sp outline {ow['w']} x {ow['h']} and child placement unchanged (8 children on the 43.2 lattice); "
                       f"+{rec['flops']['landing']} landing flops (~{rec['flops']['landing'] * 0.3 / 1000:.1f}k um2) in the "
                       "existing W / E / centre channels.",
        "7_clock": f"{len(regions)} regional CTS roots ({', '.join(cps)}): x store region (child refs 453-529 TT) apart from the "
                   "columns (104-188) " + ("and the PV merge (263-313)" if v == "m" else "(PV merge 263-313 shares the column root)")
                   + f"; every region crossing landed (lp audit PASS, {nland} landings), 1-bit reset runs only; judged per region.",
        "8_schedule": f"static; reschedule +3 edges per landed net, absorbed in r3 pads where possible; vs r3 halves: gout +{dg} "
                      f"(all 4 lanes), xo_b +1 (n), xo_g0/gp +{dg - 1} (n), rout/bout 0; reset depths shifted with their data. "
                      f"PRICED: rp4a gout G 10 -> {10 + dg} per tile hop (parent BE_DELAY / GPAD re-solve).",
    }
    s = dict(base)
    for k in ("spine_macro_leaf",):
        s.pop(k, None)
    s.update(
        name=f"smh_rp5{h}_{v}", top=f"ot_hbm_smh_rp5{h}_{v}", sources=srcs, params={},
        defines=lps["defines"] + ["OT_RP4A_HARD"], hard_define="OT_RP4A_HARD",
        clock="multiple_cts_roots", clock_port="ck_c", clock_ports=cps, clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dom, landed_record=rec_path, children=kids, pins=pins, pin_ranges=pr,
        orfs_vars={"OT_IO_REF_CLASS": "1"},
        reset_landing=dict(enable=False, reason=f"the lp RTL lands rst_n (root region c + same-depth reset forest, depth "
                           f"{rec['reset']['depth']}) and ot_rp5_rst kept copies per consumer; priced in the landed record"),
        safe_design_checklist=checklist,
        landed=dict(record=rec_path, landings=nland, landing_flops=rec["flops"]["landing"], reset_depth=rec["reset"]["depth"],
                    lp_spec=f"{REC}/lp_spec_{h}_{v}.json"),
    )
    j = dict(base["job"])
    j.update(owner="Claude:HBM-OWN/SMH2", branch="claude/hbm-own-smh2-r5-1021", tag=f"smh_rp5{h}_{v}",
             purpose=f"H.STA.BLK.14.6 smh_attn {h} half r5 {vname}: regional CTS roots per register mass + landed seams",
             structural_change=("r5: one CTS root per region (x store / columns" + (" / merge+gather" if v == "m" else "")
                                + "), every region crossing a 4-slot fixed-latency landing (lp reschedule), replaces the "
                                "single-root spine (r4sp) and K64 (r3) forms that fail the child-boundary clock rule."),
             extra_paths=["tools/hbm_sm_repack_1015", "tools/landed_parent", "rtl/common/landed_parent", RTL,
                          "rtl/hbm_accel/sm/repack/h2", "rtl/hbm_accel/sm/repack/h2a", "results/arch/hbm_smh_r5_1021",
                          "physical/ref_tile/smh_xs_p192d_bay/views"])
    lpb = f"{RTL}/lp_{h}_{v}/ot_hbm_smh_rp5{h}_{v}_bench.sh"
    vv = 0 if v == "m" else 1
    W5 = "results/arch/hbm_smh_r5_1021/bench"
    benches = [dict(name="r5_lockstep", cmd=f"bash {RTL}/run_rp5_2_one.sh {{RUN}}/r5 {vv} 0", expect="pass",
                    pass_regex=f"^R5_LOCKSTEP PASS VAR={vv} HMUT=0 compared=", pass_witness=f"{W5}/r5_v{vv}_m0.log",
                    threads=4, peak_ram_gb=32)]
    for m in (1, 2, 3, 5, 6):
        benches.append(dict(name=f"r5_mut{m}", cmd=f"bash {RTL}/run_rp5_2_one.sh {{RUN}}/r5m{m} {vv} {m}", expect="fail",
                            fail_regex=f"^R5_LOCKSTEP FAIL VAR={vv} HMUT={m} mismatches=[1-9]",
                            fail_witness=f"{W5}/r5_v{vv}_m{m}.log", threads=4, peak_ram_gb=32))
    for m in (0, 1, 2, 4):
        b = dict(name=f"lp_{h}{v}_mut{m}", cmd=f"MUTS={m} SIM=verilator VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator bash {lpb} {{RUN}}/lp{m}",
                 expect="pass" if m == 0 else "fail", threads=8, peak_ram_gb=32)
        if m == 0:
            b.update(pass_regex="MUT 0: LP_LOCKSTEP PASS", pass_witness=f"{W5}/lp_{h}{v}_m0.log")
        else:
            b.update(fail_regex=f"MUT {m}: LP_LOCKSTEP FAIL", fail_witness=f"{W5}/lp_{h}{v}_m{m}.log")
        benches.append(b)
    j["benches"] = benches
    s["job"] = j
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", action="store_true")
    a = ap.parse_args()
    out = ROOT / "physical/ref_tile_specs/smh"
    for h in ("n", "s"):
        for v in ("m", "f"):
            s = spec(h, v)
            p = out / f"smh_rp5{h}_{v}.json"
            p.write_text(json.dumps(s, indent=1) + "\n")
            print(f"wrote {p.relative_to(ROOT)}: {len(s['clock_ports'])} roots, domains "
                  + ", ".join(f"{d}:{len(x['inputs'])}in/{len(x['outputs'])}out" for d, x in s["clock_entry_domains"].items()))
            if a.gen:
                subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(p)], check=True)


if __name__ == "__main__":
    main()
