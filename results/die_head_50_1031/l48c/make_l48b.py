#!/usr/bin/env python3
"""DIE-HEAD-48 plan event l47u = l47t + hd_st_turn clock_reach one-block fix (GEOM-86/88 item 2, NE reset relays 704.85 um
from every clock tap).  Root cause: the type's reset tree has reset.local_taps_um terminals in the NE quadrant (no data
sinks there; two of them, rst_n_t32/t37, have no consumer at all) whose relay chains (u_rrl/u_srl, clocked) sit 600-700 um
from the 24 density clock taps, which do not see reset relays as sinks.  Fix (taps.explicit_taps contract, 'materialising
a density-derived table breaks control-relay/tap coordinate feedback'):
  - hd_st_turn clock.tap_mode density -> explicit; taps = the 24 density taps frozen (same names, same xy);
  - SPEC: reset.local_taps_um points listed in 'convert' become clock taps clk_t24.. at the SAME xy (removed from
    local_taps_um), points in 'drop' are removed, 'taps' adds new clock taps;
  - clock.sink_sites_um += SPEC 'sinks' (the plan reset relays these taps clock), so explicit_taps validates them;
  - clock.landing_local_resets raw names are remapped onto the regenerated reset tree: same ancestry chain (xy+depth
    from the root) when it exists, else the nearest relay of the SAME depth (same release edge) to the entry xy_um.
  make_l47u.py TOOLS_DIE_PLAN SRC_DIR(head_source_l47t) SPEC_JSON OUT_DIR
"""
import json, copy, shutil, sys, collections
from pathlib import Path
tools, src, specf, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, tools)
import schema as S, taps as TP, reset_tree as RT
tn = __import__("os").environ.get("TN", "hd_st_turn"); spec = json.loads(specf.read_text())
def clear():
    for m in (TP, RT):
        for c in ("_CACHE", "_TAPS"):
            if isinstance(getattr(m, c, None), dict): getattr(m, c).clear()
def reach(xy, tl): return min(abs(float(xy[0]) - x) + abs(float(xy[1]) - y) for _, x, y in tl)
def chain(rs, r):
    by = {x["q"]: x for x in rs}; o = []
    while r is not None:
        o.append((tuple(r["xy"]), r["depth"])); r = by.get(r["d"])
    return o
src_raw = json.loads((src / "source_plan.json").read_text())
P0 = S.Plan(src_raw); f0 = [(n, x, y) for n, x, y, _, _ in TP.density_taps(P0, tn)]; rel0 = RT.for_type(P0, tn)["relays"]
raw = copy.deepcopy(src_raw); t = raw["partition_types"][tn]; ck = t["clock"]; lt = t["reset"]["local_taps_um"]
conv = [lt[i] for i in spec.get("convert", [])]
t["reset"]["local_taps_um"] = [p for i, p in enumerate(lt) if i not in set(spec.get("convert", [])) | set(spec.get("drop", []))]
new = [list(map(float, p)) for p in conv + spec.get("taps", [])]
tab = [dict(name=n, xy=[x, y]) for n, x, y in f0] + [dict(name=f"clk_t{len(f0) + i}", xy=p) for i, p in enumerate(new)]
ck.update(tap_mode="explicit", taps=tab, sink_sites_um=ck["sink_sites_um"] + [list(map(float, r)) for r in spec["sinks"]])
clear(); P = S.Plan(raw); rel = RT.for_type(P, tn)["relays"]
qa = {r["q"]: r for r in rel0}; remap = {}
for e in ck["landing_local_resets"]:
    a = qa[e["raw"]]
    same = [b["q"] for b in rel if b["q"].startswith("rst_rl_") and chain(rel, b) == chain(rel0, a)]
    if same:
        remap[e["raw"]] = (same[0], "same chain")
    else:
        c = [b for b in rel if b["q"].startswith("rst_rl_") and b["depth"] == a["depth"]]
        b = min(c, key=lambda b: abs(b["xy"][0] - e["xy_um"][0]) + abs(b["xy"][1] - e["xy_um"][1]))
        remap[e["raw"]] = (b["q"], f"nearest depth-{a['depth']} relay {b['name']} @ {b['xy']}, "
                                   f"{abs(b['xy'][0] - e['xy_um'][0]) + abs(b['xy'][1] - e['xy_um'][1]):.1f} um from the copy (was "
                                   f"{abs(a['xy'][0] - e['xy_um'][0]) + abs(a['xy'][1] - e['xy_um'][1]):.1f})")
for e in ck["landing_local_resets"]:
    e["raw"] = remap[e["raw"]][0]
# every other rst_rl_N reference in the type (START raw exports/landings, source nets): same-chain map, else fail
import re
lrs = ck.pop("landing_local_resets"); txt = json.dumps(t); full = {}; moved = {}
for q in sorted(set(re.findall(r"rst_rl_\d+", txt)), key=lambda x: int(x[7:])):
    same = [b["q"] for b in rel if b["q"].startswith("rst_rl_") and chain(rel, b) == chain(rel0, qa[q])]
    if not same:
        # owner GO (reset tree regenerated): nearest relay of the SAME depth = same release edge; recorded in the report
        a = qa[q]; c = [b for b in rel if b["q"].startswith("rst_rl_") and b["depth"] == a["depth"]]
        b = min(c, key=lambda b: abs(b["xy"][0] - a["xy"][0]) + abs(b["xy"][1] - a["xy"][1]))
        same = [b["q"]]; moved[q] = (b["q"], a["depth"], list(a["xy"]), list(b["xy"]))
    full[q] = same[0]
txt = re.sub(r"rst_rl_\d+\b", lambda m: full[m.group(0)], txt)
# relay instance names (u_rrl_N / u_srl_N) follow their q net through the same-chain map
q2n = {b["q"]: b["name"] for b in rel}; n2q = {a["name"]: a["q"] for a in rel0}
def inst(m):
    o = m.group(0); k = "u_rrl_" + o[6:]
    if k not in n2q: raise SystemExit(f"{o}: no such relay")
    if n2q[k] not in full:
        a = qa[n2q[k]]; same = [b["q"] for b in rel if chain(rel, b) == chain(rel0, a)]
        if not same:
            c = [b for b in rel if b["depth"] == a["depth"]]
            b = min(c, key=lambda b: abs(b["xy"][0] - a["xy"][0]) + abs(b["xy"][1] - a["xy"][1]))
            same = [b["q"]]; moved["inst:" + o] = (b["q"], a["depth"], list(a["xy"]), list(b["xy"]))
        full[n2q[k]] = same[0]
    return o[:6] + q2n[full[n2q[k]]][6:]
txt = re.sub(r"\bu_[rs]rl_\d+\b", inst, txt)
t.clear(); t.update(json.loads(txt)); t["clock"]["landing_local_resets"] = lrs; ck = t["clock"]
remap_all = full
# a moved relay moves its raw START export pin with it (the export sits on the relay)
byq = {b["q"]: b for b in rel}; xy = {}
inv = {v: k for k, v in full.items()}; used = set()
for r in t.get("reset_start_raw_exports", []):
    if r["net"] in used:
        # two moved raws landed on one relay: an export needs its own source relay (head_start_raw_private), so the
        # later export takes the nearest unused relay of the same depth to its ORIGINAL relay
        a = qa[[k for k, v in full.items() if v == r["net"]][-1]]
        c = [b for b in rel if b["q"].startswith("rst_rl_") and b["depth"] == a["depth"] and b["q"] not in used and b["q"] != r["net"]]
        b = min(c, key=lambda b: abs(b["xy"][0] - a["xy"][0]) + abs(b["xy"][1] - a["xy"][1]))
        moved["export:" + r["port"]] = (b["q"], a["depth"], list(a["xy"]), list(b["xy"]))
        r["net"] = b["q"]; r["instance"] = b["name"]
    if r["net"] not in byq:
        nq = {b["name"]: b["q"] for b in rel}[r["instance"]]; moved["exportnet:" + r["port"]] = (nq, r["net"]); r["net"] = nq
    used.add(r["net"])
    b = byq[r["net"]]
    if list(r["xy_um"]) != list(b["xy"]): r["xy_um"] = list(b["xy"]); xy[r["port"]] = list(b["xy"])
for p in ck.get("landing_contract", {}).get("pins", []):
    if p["name"] in xy: p["xy_um"] = xy[p["name"]]
    for r in t.get("reset_start_raw_exports", []):
        if p["name"] == r["port"] and "source_instance" in p: p["source_instance"] = r["instance"]; p["source_net"] = r["net"]
t["note"] = (t.get("note", "") + " [DIE-HEAD-49 l48b: clock_reach one-block fix; density taps frozen as explicit (24 same "
             f"names/xy) + local reset taps {spec.get('convert', [])} -> clock taps, dropped {spec.get('drop', [])}, new "
             f"{spec.get('taps', [])}; landing_local_resets raws remapped onto the regenerated reset tree]").strip()
clear(); P = S.Plan(raw)
fin = TP.explicit_taps(P, tn); rel = RT.for_type(P, tn)["relays"]
ft = [(n, x, y) for n, x, y, _, _ in fin]
rep = dict(taps_before=len(f0), taps_after=len(fin), new_taps=[(n, x, y, k, r) for n, x, y, k, r in fin[len(f0):]],
           kept_identical=[(n, x, y) for n, x, y, _, _ in fin[:len(f0)]] == f0, relays=[len(rel0), len(rel)],
           relay_reach_before=round(max(reach(r["xy"], f0) for r in rel0), 1), relay_reach_after=round(max(reach(r["xy"], ft) for r in rel), 1),
           relay_worst_after=sorted(((round(reach(r["xy"], ft), 1), r["name"], r["xy"]) for r in rel), reverse=True)[:6],
           remap={k: v for k, v in remap.items()}, remap_all=remap_all, moved=moved, export_pins_moved=xy, depth=RT.for_type(P, tn).get("depth"))
if out.exists(): shutil.rmtree(out)
shutil.copytree(src, out)
(out / "source_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
(out / "l47u_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps(rep, indent=1))
