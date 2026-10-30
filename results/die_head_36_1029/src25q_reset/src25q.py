#!/usr/bin/env python3
"""DIE-HEAD-36 src25q (2026-10-29): make the src25p HEAD source self-consistent (HEAD-KITS-U 20:40 ASK, COORD default).
src25p changed clock taps (density) / geometry (lep0N, st_n4 crop) of some types, so reset_tree re-derives their relay trees
and renames relays, but the plan's reset_start_raw_exports rows and the src25p type RTL kept the OLD tree.
Fix (plan data + regenerated source only, no new plan item, no outline/data-pin change, 0 cycles):
  * stale types = those failing the reset_source_prep raw-Q/coordinate fixed point on the src25p plan;
  * each stale (type, port) is re-sited on the actual new raw relay (roles raw/boot/bootstrap_transport, as
    head_start_reset_exports) that minimises the max START stage hop over the stages fed by that port (provider
    start_stages.json reset_ports, unchanged port names/stage wiring), distinct relay per port; existing_port per
    head_start_reset_aliases.reuse_existing rule; the export pin (landing_contract) moves with its relay;
  * full source regenerated as head_start_sources does (L.type_rtl(G.wrapper) + reset alias patch; L.top_rtl(die_top) +
    complete_top), start_stages.sv copied from src25p (DIE-HEAD-31 start_d wire);
  * gates in-script: fixed point PASS on all types, max hop <= 405, raw relative span + 4 <= SETTLE 74.
usage: src25q.py ROOT SRC25P STAGES_JSON OUT"""
import copy, hashlib, json, re, shutil, sys
from pathlib import Path
root, src, stj, out = (Path(a).resolve() for a in sys.argv[1:5])
sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
import schema as S, reset_tree as RT, gen_rtl as G, clock_landings as C
from head_start_reset_aliases import patch_rtl
from head_start_sources import complete_top
if out.exists(): sys.exit(f"{out} exists")
raw = json.load(open(src / "source_plan.json")); side = json.load(open(src / "source_sidecar.json"))
stages = json.load(open(stj)); P = S.Plan(raw, src / "source_plan.json")

def relays(P, tn):
    t = RT.for_type(P, tn)
    return t, (RT.start_relays(t) if t.get("start") else t["relays"])

def fixedpoint(P):
    bad = []; n = 0
    for tn, t in sorted(P.types.items()):
        rows = t.get("reset_start_raw_exports", [])
        if not rows: continue
        _, rl = relays(P, tn); by = {r["name"]: r for r in rl}
        for row in rows:
            a = by.get(row["instance"]); n += 1
            # <= 0.05 um coordinate-only drift with the same relay/Q = the COORD-approved M7 track snap of the export pin
            # (src25p hd_mesh_e rst_start_raw_0/1/3, 0.032 um), not a stale row
            if a is None or a["q"] != row["net"] or max(abs(x - y) for x, y in zip(a["xy"], row["xy_um"])) > .05:
                bad.append((tn, row["port"]))
    return n, bad

n0, bad0 = fixedpoint(P)
stale = sorted({tn for tn, _ in bad0})
print("src25p fixed point:", n0, "rows,", len(bad0), "stale in", stale, flush=True)
offsets = RT.wf_plan(P)
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
users = {}
for sg in stages["stages"]:
    rs = sg.get("reset_source")
    if rs: users.setdefault((rs["type"], rs["port"]), []).append((rs["part"], sg["clock_pin_xy_um"], sg["id"]))
rep = dict(source=str(src), stages=str(stj), stale_types=stale, types={})
L0 = C.Landings(raw, side); ep0 = G.bus_epochs(P)
for tn in stale:
    t = raw["partition_types"][tn]; T, rl = relays(P, tn)
    # which raw Q already drives a type reset output (rst_o_<k>): head_start_reset_aliases.patch_rtl reuse rule
    drives = {q: o for o, q in re.findall(r"\bassign\s+(rst_o_\d+)\s*=\s*(\w+)\s*;", L0.type_rtl(tn, G.wrapper(P, tn, ep0)))}
    cand = [r for r in rl if (not T.get("start")) or r["role"] in ("raw", "boot", "bootstrap_transport")]
    outs = offsets["types"][tn]["outs"]
    pins = t["clock"]["landing_contract"]["pins"]; taken = set(); new_rows = []; trep = []
    for row in t["reset_start_raw_exports"]:
        us = users.get((tn, row["port"]), [])
        def cost(c):
            if us: return (round(max(L1(sxy, P.to_die(pn, c["xy"])) for pn, sxy, _ in us), 4), c["q"] not in drives, c["depth"], c["name"])
            return (round(L1(c["xy"], row["xy_um"]), 4), c["q"] not in drives, c["depth"], c["name"])
        pool = [c for c in cand if c["name"] not in taken]
        # a row that reused an existing type reset output keeps that output (G0C clock_landings counts infrastructure
        # pin use: turning it into a new alias pin leaves an unused landing pin)
        if row.get("existing_port") and any(drives.get(c["q"]) == row["existing_port"] for c in pool):
            pool = [c for c in pool if drives.get(c["q"]) == row["existing_port"]]
        c = min(pool, key=cost); taken.add(c["name"])
        old_hop = max((L1(sxy, P.to_die(pn, row["xy_um"])) for pn, sxy, _ in us), default=None)
        nr = dict(port=row["port"], instance=c["name"], net=c["q"], xy_um=list(c["xy"]))
        if c["q"] in drives: nr["existing_port"] = drives[c["q"]]
        # export pin moves with its relay (declare: alias rows own an M7 ctl pin at the relay site; existing ports none)
        old_pin = [p for p in pins if p["name"] == row["port"]]
        if "existing_port" in nr:
            for p in old_pin: pins.remove(p)
        elif old_pin:
            assert len(old_pin) == 1
            old_pin[0].update(xy_um=nr["xy_um"], source_instance=nr["instance"], source_net=nr["net"], source_registered=True)
        else:
            pins.append(dict(name=nr["port"], dir="out", kind="ctl", layer="M7", xy_um=nr["xy_um"], epoch=False,
                             source_instance=nr["instance"], source_net=nr["net"], source_registered=True))
        new_rows.append(nr)
        trep.append(dict(port=row["port"], old=[row["instance"], row["net"], row["xy_um"], row.get("existing_port")],
                         new=[nr["instance"], nr["net"], [round(v, 4) for v in nr["xy_um"]], nr.get("existing_port"), c["depth"], c.get("role")],
                         stages=len(us), old_hop_um=None if old_hop is None else round(old_hop, 2), new_hop_um=cost(c)[0] if us else None,
                         pin_move_um=round(L1(row["xy_um"], nr["xy_um"]), 3)))
    t["reset_start_raw_exports"] = new_rows; rep["types"][tn] = trep
errs = S.validate(raw); assert not errs, errs[:5]
out.mkdir(parents=True)
for f in src.iterdir():
    if f.is_dir(): shutil.copytree(f, out / f.name)
plan_path = out / "source_plan.json"; plan_path.write_text(json.dumps(raw, indent=1) + "\n")
P1 = S.Plan(raw, plan_path)
n1, bad1 = fixedpoint(P1)
# stage hops + raw release span on the new plan (same rule as head_start_reset_exports / reset_source_prep)
off1 = RT.wf_plan(P1); hops = []; rel = {}
st2 = copy.deepcopy(stages)
for sg in st2["stages"]:
    rs = sg.get("reset_source")
    if not rs: continue
    tn = rs["type"]; T, rl = relays(P1, tn); by = {r["name"]: r for r in rl}
    row = [r for r in raw["partition_types"][tn]["reset_start_raw_exports"] if r["port"] == rs["port"]]
    assert len(row) == 1, (tn, rs["port"]); row = row[0]; c = by[row["instance"]]
    xy = P1.to_die(rs["part"], c["xy"])
    rs.update(instance=c["name"], net=c["q"], xy_um=list(xy), local_xy_um=list(c["xy"]),
              raw_release=off1["parts"][rs["part"]]["release"] - RT.release_clocks(T) + RT.entry_stages(T) + c["depth"])
    sg["reset_hop_um"] = round(L1(sg["clock_pin_xy_um"], xy), 4); hops.append((sg["reset_hop_um"], sg["id"], tn))
    rel[sg["id"]] = rs["raw_release"]
    if sg["reset_port"] in st2["reset_ports"]: st2["reset_ports"][sg["reset_port"]].update({k: rs[k] for k in rs})
rootid = next(s["id"] for s in st2["stages"] if s["root"])
span = max(v - rel[rootid] for v in rel.values())
settle = stages["stages"][[s["root"] for s in stages["stages"]].index(True)]["settle"]
rep["gates"] = dict(fixed_point_rows=n1, fixed_point_mismatch=len(bad1), max_hop_um=max(hops), over_405=[h for h in hops if h[0] > 405],
                    raw_relative_span=span, settle=settle, settle_ok=span + 4 <= settle,
                    span_src25p_stages=stages["root_settle_guard"]["raw_relative_span"])
(out / "start_stages_src25q.json").write_text(json.dumps(st2, indent=1) + "\n")
# regenerate the source exactly as head_start_sources (plan already declared; observer already in plan/sidecar)
L = C.Landings(raw, side); ep = G.bus_epochs(P1)
(out / "ot_dp_cells.sv").write_text(G.CELLS)
for tn, t in sorted(P1.types.items()):
    if t.get("hard"): continue
    text = patch_rtl(L.type_rtl(tn, G.wrapper(P1, tn, ep)), t.get("reset_start_raw_exports", []))
    (out / (t["module"] + ".sv")).write_text(text)
top = L.top_rtl(G.die_top(P1, ep), {tn: t["module"] for tn, t in P1.types.items()})
top, spares = complete_top(top, raw, stages); (out / (G.sv_id(P1.name) + "_top.sv")).write_text(top)
shutil.copy(src / "start_stages.sv", out / "start_stages.sv")
(out / "source_sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
diff = {}
for f in sorted(out.glob("*.sv")):
    o = src / f.name
    diff[f.name] = "NEW" if not o.exists() else ("SAME" if o.read_bytes() == f.read_bytes() else "DIFF")
rep["files_vs_src25p"] = diff; rep["unused_uniform_exports"] = len(spares)
r0 = json.load(open(src / "report.json")); r0["unused_uniform_exports"] = spares
r0["src25q"] = "DIE-HEAD-36: stale reset_start_raw_exports re-sited on the actual relays; see src25q_report.json"
(out / "report.json").write_text(json.dumps(r0, indent=1) + "\n")
rep["sha256"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.glob("*.sv")) + [plan_path]}
(out / "src25q_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps(rep["gates"])); print(json.dumps(diff))
print("source_plan.json sha256", rep["sha256"]["source_plan.json"])
if bad1 or rep["gates"]["over_405"] or not rep["gates"]["settle_ok"]: sys.exit("GATE FAIL")
