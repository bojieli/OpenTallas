#!/usr/bin/env python3
"""HBM-KITS 2026-10-25: census of the B2n hard cores (die_plan.json partition_types[*].hard_cores) -> distinct designs.
Inputs: B2n die_plan.json, views_b2n.json (claude/hbm-kits-1025), canonical_ports_split.json, over_cap_split/*.split.json,
OWNERS.tsv (autopilot), fleet kit probe TSV (host, kit, module, pins_sha12, plan_sha12, outline, stage, fails, signoff, mtime).
Distinct design key = (RTL top + params, straps, outline, pin geometry incl. names).  'unify' key drops straps and pin
geometry: pieces that share it are the same logic up to strap constants / plan pin placement and can share ONE hardened core
once straps become ID pins tied at the parent and the plan gives them one pin table (replicas hardened once)."""
import json, sys, re, hashlib, collections, argparse
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True); ap.add_argument("--views", required=True)
ap.add_argument("--owners", required=True); ap.add_argument("--probe", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
R = Path(a.root); B = R / "physical/die_plan/hbm_arch/B2n"
plan = json.load(open(B / "die_plan.json")); psha = hashlib.sha256(open(B / "die_plan.json", "rb").read()).hexdigest()
V = json.load(open(a.views)); assert V["plan_sha256"] == psha, "views_b2n.json is not for this plan"
CT = json.load(open(R / "physical/die_plan/hbm/cores/harden/canonical_ports_split.json"))["types"]
canon_of = {}
for cname, ct in CT.items():
    for tid, ti in ct["type_ids"].items():
        canon_of[re.sub(r"__[\d.]+x[\d.]+$", "", tid)] = (cname, ct["top"], ti.get("straps", {}), ti.get("tied_at_parent", {}))
SPL = {}
for f in (R / "physical/die_plan/hbm/over_cap_split").glob("*.split.json"):
    s = json.load(open(f))
    for c in s.get("cores", []):
        SPL[(s["master"], c.get("core_label"))] = (f.name, c)
# instances per module
inst = collections.defaultdict(list); hc_note = {}
pcount = collections.Counter(p["type"] for p in plan["partitions"])
for tn, t in plan["partition_types"].items():
    for h in t.get("hard_cores", []):
        inst[h["module"]].append((tn, h["inst"], tuple(h["outline_um"]), h["pins_file"]))
        hc_note[h["module"]] = h.get("note", "")
owners = {}
for ln in open(a.owners):
    f = ln.rstrip("\n").split("\t")
    if len(f) > 5 and f[0] == "hbm" and f[2] == "core":
        owners[f[1]] = (f[3], f[4])
probe = collections.defaultdict(list)
for ln in open(a.probe):
    f = ln.rstrip("\n").split("\t")
    if len(f) >= 10 and psha.startswith(f[4]):
        probe[(f[2], f[3])].append(f)
ORDER = ["", "1_synth", "1_2_yosys", "3_place", "4_cts", "5_route", "6_final"]
def pinsig(pf, names=True):
    P = json.load(open(B / pf))
    key = sorted((p["name"] if names else "", p["layer"], round(p["x"], 3), round(p["y"], 3)) for p in P)
    return hashlib.sha256(json.dumps(key).encode()).hexdigest()[:10], len(P)
rows = []
for v in V["view_list"]:
    m = v["module"]; outl = "x".join(f"{x:g}" for x in v["outline_um"])
    note = hc_note.get(m, ""); mm = re.match(r"split piece (\S+) of (\S+) \((\S+)\); (\d+) cells", note)
    piece, parent, splitf, cells = (mm.groups() if mm else ("", m, "", (re.search(r"(\d+) cells", note) or [None, ""])[1]))
    cn = canon_of.get(m)
    sc = None
    if mm:
        master = json.load(open(R / "physical/die_plan/hbm/over_cap_split" / splitf))["master"]
        sc = SPL.get((master, piece))
    rtl = cn[1] if cn else (sc[1]["module"] if sc else (v["recipe_keys"][0].split("@")[-1] if v["recipe_keys"] else m))
    if cn and cn[0].endswith(("_h1",)): rtl += "#(HALF 1)"
    if cn and cn[0].endswith(("_h0",)): rtl += "#(HALF 0)"
    straps = json.dumps(cn[2], sort_keys=True) if cn else "{}"
    srams = sc[1].get("srams", "") if sc else ""
    gsig, npins = pinsig(v["pins_file"]); gsig_nn, _ = pinsig(v["pins_file"], names=False)
    ins = [i for i in inst[m] if "x".join(f"{x:g}" for x in i[2]) == outl and i[3] == v["pins_file"]] or \
          [i for i in inst[m] if "x".join(f"{x:g}" for x in i[2]) == outl]
    placed = sum(pcount[i[0]] for i in ins)
    kits = probe.get((m, v["pins_sha256"][:12]), [])
    best = max((k[6] for k in kits), key=lambda s: ORDER.index(s) if s in ORDER else 0, default="")
    fails = sorted({k[7].split(":")[0] + (":" + k[7].split(":", 1)[1].split()[0] if ":" in k[7] else "") for k in kits if k[7]})
    signed = sorted({k[8] for k in kits if k[8]})
    own = owners.get(m, ("", ""))
    rows.append(dict(module=m, view=v["view"], family=v.get("family", ""), parent=parent, piece=piece, split_json=splitf,
                     canonical_type=cn[0] if cn else "", rtl_top=rtl, straps=straps, cells=cells, srams=srams, outline=outl,
                     pins_file=v["pins_file"], pins=npins, pin_geom=gsig, pin_xy=gsig_nn,
                     ptypes=";".join(sorted({i[0] for i in ins})), insts=";".join(sorted({i[1] for i in ins})), placed=placed,
                     view_blockers=";".join(map(str, v.get("blockers", []))), owner_state=own[0], owner=own[1],
                     kits_cur_plan=len(kits), best_stage=best, kit_fails="|".join(fails), signoff="|".join(signed),
                     kit_hosts=";".join(sorted({k[0] + ":" + k[1] for k in kits}))[:400]))
# design keys
dkey = lambda r: (r["rtl_top"], r["straps"], r["outline"], r["pin_geom"])
ukey = lambda r: (r["rtl_top"], r["outline"])
D = {}; U = {}
for r in rows:
    D.setdefault(dkey(r), f"D{len(D)+1:03d}"); U.setdefault(ukey(r), f"U{len(U)+1:03d}")
    r["design"] = D[dkey(r)]; r["unify"] = U[ukey(r)]
cols = ["design", "unify", "module", "view", "family", "parent", "piece", "split_json", "canonical_type", "rtl_top", "straps",
        "cells", "srams", "outline", "pins_file", "pins", "pin_geom", "pin_xy", "ptypes", "insts", "placed", "view_blockers",
        "owner_state", "owner", "kits_cur_plan", "best_stage", "kit_fails", "signoff", "kit_hosts"]
with open(a.out, "w") as f:
    f.write(f"# HBM-KITS census B2n die_plan sha {psha[:12]} views_b2n {len(rows)} views; design = rtl+straps+outline+pins, unify = rtl+outline\n")
    f.write("\t".join(cols) + "\n")
    for r in sorted(rows, key=lambda r: (r["family"], r["parent"], r["design"], r["module"])):
        f.write("\t".join(str(r[c]) for c in cols) + "\n")
print("views", len(rows), "modules", len({r['module'] for r in rows}), "designs", len(D), "unify", len(U))
# COORD 06:5x (TYPE-REDUCE claude/type-reduce-1025@befcf3f66): key by RTL MASTER (rtl_top + params) -> census_masters.tsv
# one row per master: kit ONE core per (master, pin template); designs/tables listed only to show the template delta owed.
M = collections.OrderedDict()
for r in sorted(rows, key=lambda r: (r["family"], r["parent"], r["rtl_top"])):
    m = M.setdefault(r["rtl_top"], dict(family=r["family"], parent=r["parent"], canonical_type=r["canonical_type"], cells=r["cells"],
                                         srams=r["srams"], modules=set(), views=0, placed=0, outlines=set(), tables=set(),
                                         straps=set(), designs=set(), blockers=set(), owner_states=set()))
    m["modules"].add(r["module"]); m["views"] += 1; m["placed"] += int(r["placed"]); m["outlines"].add(r["outline"])
    m["tables"].add(r["pin_xy"]); m["straps"].add(r["straps"]); m["designs"].add(r["design"])
    m["owner_states"].add(r["owner_state"])
    if r["view_blockers"]: m["blockers"].add(r["view_blockers"].split(":")[0])
mo = Path(a.out).with_name("census_masters.tsv")
with open(mo, "w") as f:
    f.write(f"# HBM-KITS census by RTL master (B2n sha {psha[:12]}): {len(M)} masters / {len(rows)} views / {len(D)} designs\n")
    f.write("master\tfamily\tparent\tcanonical_type\tcells\tsrams\tmodules\tviews\tplaced\toutlines\tpin_xy_tables\tstrap_variants\tdesigns\tblockers\towner_states\n")
    for k, m in M.items():
        f.write("\t".join(map(str, [k, m["family"], m["parent"], m["canonical_type"], m["cells"], m["srams"], len(m["modules"]), m["views"],
                                     m["placed"], ";".join(sorted(m["outlines"])), len(m["tables"]), len(m["straps"]) if m["straps"] != {"{}"} else 0,
                                     len(m["designs"]), ";".join(sorted(m["blockers"])), ";".join(sorted(m["owner_states"]))])) + "\n")
print("masters", len(M))
