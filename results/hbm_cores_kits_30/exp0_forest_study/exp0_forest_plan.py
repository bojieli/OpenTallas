#!/usr/bin/env python3
"""HBM-CORES-KITS-30 exp0 (COORD RULING 20:19 (2) option A): plan-built clock FOREST for lane_exp0 -- one ordinary
plan tree per clk_* root (19 roots: clk_bank, clk_insert[0..3], clk_lane[0..7], clk_bank_macro[0..5]); every root's
tree is planned by the shared core_family_slice.plan path (R7 NLDM + 12.8 d1 sizing) from the anchA placed census and
padded with a 12.8c entry trunk so the PLAN MODEL latency of every root sits on one common TT target.
Plan model only; UNCHECKED until built.
usage: exp0_forest_plan.py CENSUS_TSV SITES OUTDIR --libtt F --libff F [--target-tt 250]"""
import argparse, collections, json, sys
from pathlib import Path
REPO = Path(sys.argv[0]).resolve().parents[0]
ap = argparse.ArgumentParser()
ap.add_argument("census"); ap.add_argument("sites"); ap.add_argument("out")
ap.add_argument("--repo", required=True); ap.add_argument("--libtt", required=True); ap.add_argument("--libff", required=True)
ap.add_argument("--core", default="4.32,4.32,410.4,203.04")
ap.add_argument("--macros", required=True, help="MAC lines file (name master x0 y0 x1 y1)")
ap.add_argument("--only", default=None)
ap.add_argument("--entry", default=None, help="x,y common entry (plan centre); default = port xy")
ap.add_argument("--fam", default="{}", help="JSON overrides of the family template")
a = ap.parse_args()
R = Path(a.repo); sys.path.insert(0, str(R / "tools/die_plan"))
import core_family_slice as F
import core_infra_htree as H
import l0r_r7_model as M7
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
ports, sinks = {}, collections.defaultdict(list)
for l in open(a.census):
    f = l.rstrip("\n").split("\t")
    if f[0] == "PORT": ports[f[1]] = (float(f[2]), float(f[3]))
    elif f[0] == "S": sinks[f[1]].append(f)
macs = [l.split() for l in open(a.macros) if l.startswith("MAC ")]
core = a.core.replace(",", " ")
fam = dict(name="exp0f", leaf_target=48, smax=70.0, leaf_limit=35.0, wire="std", reassign=True, reassign_cap=1.5)
fam.update(json.loads(a.fam))
res = {}
for p in sorted(ports):
    if a.only and p != a.only: continue
    ss = sinks[p]; tag = p.replace("[", "_").replace("]", "")
    if any(s[6] == "1" for s in ss):
        res[p] = dict(kind="macro", sinks=len(ss)); continue
    px, py = ports[p] if not a.entry else map(float, a.entry.split(","))
    g = out / ("geo_%s.txt" % tag)
    with open(g, "w") as fh:
        fh.write("CORE %s\nPIN ck %.3f %.3f\n" % (core, px, min(py, 203.0)))
        for m in macs:   # SRAM walls (pin unused by flop roots)
            fh.write("MACRO %s %s %s %s %s %s CLK %s %s\n" % (m[1], m[2], m[3], m[4], m[5], m[6], m[3], m[4]))
        for s in ss:
            inst, pin = s[2].rsplit("/", 1)
            fh.write("SINK %s %s %s %s %s\n" % (s[4], s[5], s[3], inst, pin))
    rec = F.plan(str(g), fam, a.libtt, a.libff, "exp0f_%s" % tag)
    P, libs, r, c, wc = F._PLANS[rec["name"]]
    base = {k: rec[k]["mean"] for k in ("TT", "FF")}
    res[p] = dict(kind="flop", sinks=len(ss), splits=rec["splits"], cells=rec["n_cells"], stages=rec["stages"],
                  TT=rec["TT"], FF=rec["FF"], base=base)
    (out / ("rec_%s.json" % tag)).write_text(json.dumps(rec))
    print(p, len(ss), rec["splits"], rec["n_cells"], rec["stages"], {k: (round(rec[k]["mean"], 1), round(rec[k]["window"], 1)) for k in ("TT", "FF")}, flush=True)
(out / "summary.json").write_text(json.dumps(res, indent=1))
