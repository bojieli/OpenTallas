#!/usr/bin/env python3
"""DIE-HEAD-38 src25s (2026-10-30): LAST HEAD fix-only plan event (OWNER 12.20) on src25r.
Applies EDITS_JSON = {"types": {type: {"set": {dotted.path: value}, "pop": [dotted.path], "cells_add": n}}}
(raw_reset "PICK" in landing_reader_start / landing_writer_start stages = nearest registered non-port raw rrelay),
then the src25q reset fixed point / re-site, START hop and SETTLE gates, and regenerates all type RTL + top.
usage: src25s.py ROOT SRC(src25r) STAGES_JSON EDITS_JSON OUT"""
import copy, hashlib, json, re, shutil, sys
from pathlib import Path
root, src, stj, edj, out = (Path(a).resolve() for a in sys.argv[1:6])
sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
import schema as S, reset_tree as RT, gen_rtl as G, clock_landings as C, landing_contract as LC
from head_start_reset_aliases import patch_rtl
from head_start_sources import complete_top
if out.exists(): sys.exit(f"{out} exists")
raw = json.load(open(src / "source_plan.json")); side = json.load(open(src / "source_sidecar.json"))
stages = json.load(open(stj)); edits = json.load(open(edj))
# Runner-local memoization: tap_grid is deterministic for this immutable Plan instance.
_tap_grid = S.tap_grid
def _cached_tap_grid(P, tn):
    c = P.__dict__.setdefault("_runner_tap_grid", {})
    if tn not in c: c[tn] = tuple(_tap_grid(P, tn))
    return list(c[tn])
S.tap_grid = _cached_tap_grid
# Cache density solver across equivalent Plan instances on its complete materialized geometric inputs.
# We retain all type/die/clock/reset metadata and the actual current sink inventory; reset/START repicks never
# re-use a result whose geometric inputs differ. This is runner-local, not a shared tool or gate change.
import taps as TP
_density_taps = TP.density_taps
_cache_code = hashlib.sha256(b''.join(f.read_bytes() for f in sorted((root/'tools/die_plan').glob('*.py')))).hexdigest()[:16]
_cache_file = Path(__file__).resolve().parent / ('density_cache_' + _cache_code + '.json')
_density_by_inputs = json.loads(_cache_file.read_text()) if _cache_file.exists() else {}
_runner_plan_refs = {}
def _cached_density_taps(P, tn, control=True):
    _runner_plan_refs[id(P)] = P
    effective = bool(control and P.types[tn].get("clock", {}).get("control_sinks"))
    inputs = [tn, P.types[tn], P.die, P.clock, P.reset, P.grid,
              TP.sink_sites(P, tn, effective), S.core_taps(P, tn)]
    if effective: inputs.append(TP.control_pin_sinks(P, tn))
    key = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
    if key not in _density_by_inputs:
        _density_by_inputs[key] = copy.deepcopy(_density_taps(P, tn, control))
        tmp = _cache_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(_density_by_inputs, separators=(',', ':')))
        tmp.replace(_cache_file)
    return copy.deepcopy(_density_by_inputs[key])
TP.density_taps = _cached_density_taps
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
rep = dict(source=str(src), stages=str(stj), edits=str(edj), changes={})

def relays(P, tn):
    t = RT.for_type(P, tn)
    return t, (RT.start_relays(t) if t.get("start") else t["relays"])

def dset(d, path, v):
    ks = path.split("."); 
    for k in ks[:-1]: d = d.setdefault(k, {})
    old = d.get(ks[-1]); d[ks[-1]] = v; return old
def dpop(d, path):
    ks = path.split(".")
    for k in ks[:-1]: d = d[k]
    return d.pop(ks[-1], None)

for tn, e in sorted(edits["types"].items()):
    t = raw["partition_types"][tn]
    for p in e.get("pop", []): rep["changes"][tn + ":pop:" + p] = dpop(t, p) is not None
    for p, v in e.get("set", {}).items(): rep["changes"][tn + ":set:" + p] = dict(old=dset(t, p, copy.deepcopy(v)), new=v)
    if e.get("cells_add"): t["cells"] = int(t.get("cells", 0)) + int(e["cells_add"])
    for fn, k in (e.get("ft_stations") or {}).items():  # pass-through station count (latency +k-old on that link)
        fs = [f for f in t["ft_slots"] if f["name"] == fn]; assert len(fs) == 1, (tn, fn)
        rep["changes"][tn + ":ft_stations:" + fn] = dict(old=fs[0]["stations"], new=k); fs[0]["stations"] = k
    if e.get("ft_order_explicit"):  # lsb_high slots: explicit in/out order (pin geometry unchanged; ring fill +ffr)
        n = 0
        for fs in t.get("ft_slots", []):
            if fs.get("order") == "lsb_high":
                for k in ("in_order", "out_order"):
                    if k not in fs: fs[k] = "lsb_high"; n += 1
        rep["changes"][tn + ":ft_order_explicit"] = n
# Size new control-clock demand BEFORE solving reset geometry.
# R/W stages each have1FF; a ready/fault collector has2FF. Reset groups reserve up to one copy per consumer,
# a conservative bound on later same-depth group splits. This is planned demand, not an actual placed census.
from collections import Counter
for tn, e in sorted(edits['types'].items()):
    ck = raw['partition_types'][tn]['clock']; demand = Counter(); actual = 0; reserve = 0
    def count_xy(xy, n):
        demand[(round(xy[0],3), round(xy[1],3))] += n
    for fld in ('landing_reader_start','landing_writer_start'):
        for br in (ck.get(fld) or {}).get('branches',{}).values():
            for st in br['stages']:count_xy(st['xy_um'],1);actual+=1
    for tg in (ck.get('landing_status_input_stages') or {}).values():
        for status_chain in tg.values():
            for st in status_chain:count_xy(st['xy_um'],2);actual+=2
    for st in ck.get('landing_local_resets') or []:
        n=max(1,len(st['consumers']));count_xy(st['xy_um'],n);reserve+=n;actual+=1
    for xy in (ck.get('landing_status_anchors') or {}).values():count_xy(xy,2)
    if not demand:continue
    have=Counter()
    for row in ck.get('sink_sites_um',[]):have[(round(row[0],3),round(row[1],3))] += row[2] if len(row)>2 else 1
    explicit_manual='clock.sink_sites_um' in e.get('set',{})
    for xy,n in demand.items():
        have[xy]=max(have[xy],n) if explicit_manual else have[xy]+n
    ck['sink_sites_um']=[[x,y,n] for (x,y),n in sorted(have.items())]
    rep['changes'][tn+':weighted_control_clock_demand']=dict(form_flops_before_reset_splits=actual,
        reset_copy_capacity_reserved=reserve,control_demand_weight=sum(demand.values()),manual_census=explicit_manual,
        basis='planned conservative control clock demand; actual root-specific placement census still required')

P0 = S.Plan(raw, src / "source_plan.json")

# ---- reset tree fixed point (src25q rule) and re-site of stale export rows
def fixedpoint(P):
    bad = []; n = 0
    for tn, t in sorted(P.types.items()):
        rows = t.get("reset_start_raw_exports", [])
        if not rows: continue
        _, rl = relays(P, tn); by = {r["name"]: r for r in rl}
        for row in rows:
            a = by.get(row["instance"]); n += 1
            if a is None or a["q"] != row["net"] or max(abs(x - y) for x, y in zip(a["xy"], row["xy_um"])) > .05:
                bad.append((tn, row["port"]))
    return n, bad

P = S.Plan(raw, src / "source_plan.json")
n0, bad0 = fixedpoint(P)
rep["fixed_point_before_resite"] = dict(rows=n0, stale=bad0)
print("fixed point after pin move:", n0, "rows,", len(bad0), "stale", bad0, flush=True)
users = {}
for sg in stages["stages"]:
    rs = sg.get("reset_source")
    if rs: users.setdefault((rs["type"], rs["port"]), []).append((rs["part"], sg["clock_pin_xy_um"], sg["id"]))
_pr = copy.deepcopy(raw)  # START fields still holding a raw_reset "PICK" are left out of the probe RTL
for _t in _pr["partition_types"].values():
    _t.get("clock", {}).pop("landing_local_resets", None)
    _t.get("clock", {}).pop("landing_reader_start", None)
    _t.get("clock", {}).pop("landing_writer_start", None)
L0 = C.Landings(_pr, side); ep0 = G.bus_epochs(P)
for tn in sorted({tn for tn, _ in bad0}):
    print("RESITE", tn, flush=True)
    t = raw["partition_types"][tn]; T, rl = relays(P, tn)
    drives = {q: o for o, q in re.findall(r"\bassign\s+(rst_o_\d+)\s*=\s*(\w+)\s*;", L0.type_rtl(tn, G.wrapper(S.Plan(_pr, src / "source_plan.json"), tn, ep0)))}
    cand = [r for r in rl if (not T.get("start")) or r["role"] in ("raw", "boot", "bootstrap_transport")]
    pins = t["clock"]["landing_contract"]["pins"]; taken = set(); new_rows = []; trep = []
    for row in t["reset_start_raw_exports"]:
        us = users.get((tn, row["port"]), [])
        def cost(c):
            if us: return (round(max(L1(sxy, P.to_die(pn, c["xy"])) for pn, sxy, _ in us), 4), c["q"] not in drives, c["depth"], c["name"])
            return (round(L1(c["xy"], row["xy_um"]), 4), c["q"] not in drives, c["depth"], c["name"])
        pool = [c for c in cand if c["name"] not in taken]
        if row.get("existing_port") and any(drives.get(c["q"]) == row["existing_port"] for c in pool):
            pool = [c for c in pool if drives.get(c["q"]) == row["existing_port"]]
        c = min(pool, key=cost); taken.add(c["name"])
        nr = dict(port=row["port"], instance=c["name"], net=c["q"], xy_um=list(c["xy"]))
        if c["q"] in drives: nr["existing_port"] = drives[c["q"]]
        old_pin = [p for p in pins if p["name"] == row["port"]]
        if "existing_port" in nr:
            for p in old_pin: pins.remove(p)
        elif old_pin:
            old_pin[0].update(xy_um=nr["xy_um"], source_instance=nr["instance"], source_net=nr["net"], source_registered=True)
        else:
            pins.append(dict(name=nr["port"], dir="out", kind="ctl", layer="M7", xy_um=nr["xy_um"], epoch=False,
                             source_instance=nr["instance"], source_net=nr["net"], source_registered=True))
        new_rows.append(nr)
        trep.append(dict(port=row["port"], old=[row["instance"], row["net"], row["xy_um"]], new=[c["name"], c["q"], c["xy"]],
                         new_hop_um=cost(c)[0] if us else None))
    t["reset_start_raw_exports"] = new_rows; rep.setdefault("resited", {})[tn] = trep

(Path(__file__).resolve().parent / ('resited_' + out.name + '.json')).write_text(json.dumps(raw, indent=1)+'\n')

# ---- START stage raw pick (reader + writer): never a relay that drives a type reset output port
P = S.Plan(raw, src / "source_plan.json"); ep = G.bus_epochs(P)
for tn in sorted(raw["partition_types"]):
    ck = raw["partition_types"][tn].get("clock", {})
    for fld in ("landing_reader_start", "landing_writer_start"):
        cfg = ck.get(fld)
        if not cfg: continue
        print("START_PICK", tn, fld, flush=True)
        T, rl = relays(P, tn)
        probe = copy.deepcopy(raw)
        for remove in ('landing_reader_start', 'landing_writer_start', 'landing_local_resets'):
            probe['partition_types'][tn]['clock'].pop(remove, None)
        text = C.Landings(probe, side).type_rtl(tn, G.wrapper(S.Plan(probe, src / "source_plan.json"), tn, ep))
        drives = {q: o for o, q in re.findall(r"\bassign\s+(rst_o_\d+)\s*=\s*(\w+)\s*;", text)}
        rrelay = set(re.findall(r"\bot_dp_rrelay\s+\w+\s*\([^;]*?\.q\(\s*(\w+)\s*\)", text, re.S))
        ok = [r for r in rl if r["q"] in rrelay and (fld == "landing_reader_start" or r["q"] not in drives) and r.get("role") == "raw"]
        by = {r["q"]: r for r in rl}; trep = []
        for bus, br in sorted(cfg["branches"].items()):
            for i, st in enumerate(br["stages"]):
                cur = st["raw_reset"]
                if cur != "PICK" and cur in by and (fld == "landing_reader_start" or cur not in drives) and cur in rrelay and L1(by[cur]["xy"], st["xy_um"]) <= 405:
                    h = L1(by[cur]["xy"], st["xy_um"]); assert h <= 405, (tn, fld, bus, i, cur, h)
                    trep.append(dict(bus=bus, stage=i, raw=cur, kept=True, hop_um=round(h, 2))); continue
                c = min(ok, key=lambda r: (round(L1(r["xy"], st["xy_um"]), 3), r["depth"], r["name"]))
                h = L1(c["xy"], st["xy_um"]); assert h <= 405, (tn, fld, bus, i, c["name"], h)
                trep.append(dict(bus=bus, stage=i, old=cur, raw=c["q"], instance=c["name"], hop_um=round(h, 2)))
                st["raw_reset"] = c["q"]
            hops = [L1(a["xy_um"], b["xy_um"]) for a, b in zip(br["stages"], br["stages"][1:])]
            trep.append(dict(bus=bus, stage_to_stage_um=[round(h, 2) for h in hops]))
        rep["changes"][tn + "." + fld + ".pick"] = trep
# Resolve R1 groups against the actual original reset graph; keep each consumer's release edge.
for tn in sorted(raw['partition_types']):
    ck = raw['partition_types'][tn].get('clock', {})
    cfg = ck.get('landing_local_resets')
    if not cfg: continue
    print('R1_RESOLVE', tn, flush=True)
    probe = copy.deepcopy(raw); probe['partition_types'][tn]['clock'].pop('landing_local_resets')
    PP = S.Plan(probe, src / 'source_plan.json')
    text = C.Landings(probe, side).type_rtl(tn, G.wrapper(PP, tn, G.bus_epochs(PP)))
    TT, rr = relays(PP, tn)
    ports = {q for _, q in re.findall(r'\bassign\s+(rst_o_\d+)\s*=\s*(\w+)\s*;', text)}
    actual_raw = set(re.findall(r'\bot_dp_rrelay\s+\w+\s*\([^;]*?\.q\(\s*(\w+)\s*\)', text, re.S))
    memo = {}
    def dep(net, seen=()):
        if net in memo: return memo[net]
        assert net not in seen, (tn, 'reset loop', net)
        m = re.search(r'\bot_dp_r(?:relay|gate)\s+\w+\s*\(([^;]*?)\.q\(\s*' + re.escape(net) + r'\s*\)\s*\);[ \t]*(?://[^\n]*?\bdepth (\d+)\b)?', text, re.S)
        if m and m.group(2): d = int(m.group(2))
        elif m:
            pm = re.search(r'\.d\(\s*(\w+)\s*\)', m.group(1)); assert pm, (tn, net)
            d = dep(pm.group(1), seen+(net,)) + 1
        else:
            z = re.search(r'\bassign\s+'+re.escape(net)+r'\s*=\s*(\w+)\s*;', text)
            assert z, (tn, 'no reset depth', net)
            d = dep(z.group(1), seen+(net,))
        memo[net] = d; return d
    repaired = []; updates=[]
    for row in cfg:
        groups = {}
        for con in row['consumers']:
            ms = list(re.finditer(r'\b'+re.escape(con)+r'\s*\(([^;]+)\);', text, re.S))
            assert len(ms)==1, (tn, 'nonexistent consumer', con)
            cp = re.search(r'\.(?:rst_n|rst_raw_n)\(\s*(\w+)\s*\)', ms[0].group(1))
            assert cp, (tn, 'consumer lacks reset', con)
            groups.setdefault(dep(cp.group(1)), []).append(con)
        for depth,cons in sorted(groups.items()):
            pool=[q for q in rr if q['q'] in actual_raw and q['q'] not in ports and q['depth']==depth-1]
            assert pool, (tn, row['name'], 'no raw at needed depth', depth-1)
            cand=min(pool,key=lambda q:(round(L1(q['xy'],row['xy_um']),4),q['name']))
            hop=L1(cand['xy'],row['xy_um']);assert hop<=405,(tn,row['name'],hop)
            nr=copy.deepcopy(row);nr.update(raw=cand['q'],consumers=cons)
            if len(groups)>1:nr['name'] += '_d'+str(depth)
            repaired.append(nr);updates.append(dict(name=nr['name'],old_raw=row['raw'],raw=cand['q'],copy_depth=depth,hop_um=round(hop,3),consumers=len(cons),added_cycles=0))
    ck['landing_local_resets']=repaired
    rep['changes'][tn+'.R1_actual_depth_resolution']=updates

# local reset copies: raw must sit one level above each consumer's reset (release edge unchanged); a raw named on
# the pre-event tree that no longer has that depth is re-picked: nearest non-port raw rrelay of the required depth
LRX = re.compile(r"landing_local_resets\.(\w+): consumer \S+ reset \S+ depth (\d+) != copy depth")
for tn in sorted(raw["partition_types"]):
    ck = raw["partition_types"][tn].get("clock", {})
    if not ck.get("landing_local_resets"): continue
    trep = []
    for it in range(2 * len(ck["landing_local_resets"]) + 1):
        P = S.Plan(raw, src / "source_plan.json"); T, rl = relays(P, tn)
        try:
            text = C.Landings(raw, side).type_rtl(tn, G.wrapper(P, tn, G.bus_epochs(P))); break
        except C.LandingError as ex:
            m = LRX.search(str(ex))
            if not m: raise
            name, need = m.group(1), int(m.group(2)) - 1
            ent = [r for r in ck["landing_local_resets"] if r["name"] == name][0]
            probe = copy.deepcopy(raw); probe["partition_types"][tn]["clock"].pop("landing_local_resets")
            pt = C.Landings(probe, side).type_rtl(tn, G.wrapper(S.Plan(probe, src / "source_plan.json"), tn, G.bus_epochs(P)))
            drives = {q for o, q in re.findall(r"\bassign\s+(rst_o_\d+)\s*=\s*(\w+)\s*;", pt)}
            rr = set(re.findall(r"\bot_dp_rrelay\s+\w+\s*\([^;]*?\.q\(\s*(\w+)\s*\)", pt, re.S))
            ok = [r for r in rl if r["q"] in rr and r["q"] not in drives and r["depth"] == need and r["q"] != ent["raw"]]
            assert ok, (tn, name, need)
            c = min(ok, key=lambda r: (round(L1(r["xy"], ent["xy_um"]), 3), r["name"]))
            trep.append(dict(name=name, old=ent["raw"], new=c["q"], depth=need, hop_um=round(L1(c["xy"], ent["xy_um"]), 2)))
            assert L1(c["xy"], ent["xy_um"]) <= 405, trep[-1]
            ent["raw"] = c["q"]
    else: sys.exit(f"{tn}: local reset repick did not converge")
    rep["changes"][tn + ".landing_local_resets.repick"] = trep
# Refresh stale published lane metadata from the existing implemented plan formula (no RTL edit).
PL = S.Plan(raw, src / "source_plan.json")
oldlat = copy.deepcopy(raw.get("latency", {}).get("lanes", {}))
newlat = {lid: PL.lane_latency(lid) for lid in sorted(PL.lanes)}
raw.setdefault("latency", {})["lanes"] = newlat
rep["latency_metadata_refresh"] = {lid: dict(old=oldlat.get(lid), new=row) for lid, row in newlat.items() if oldlat.get(lid) != row}
errs = S.validate(raw); assert not errs, errs[:5]

# ---- write + regenerate (src25q / head_start_sources form)
out.mkdir(parents=True)
for f in src.iterdir():
    if f.is_dir(): shutil.copytree(f, out / f.name)
plan_path = out / "source_plan.json"; plan_path.write_text(json.dumps(raw, indent=1) + "\n")
P1 = S.Plan(raw, plan_path)
n1, bad1 = fixedpoint(P1)
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
    if sg["reset_port"] in st2.get("reset_ports", {}): st2["reset_ports"][sg["reset_port"]].update({k: rs[k] for k in rs})
rootid = next(s["id"] for s in st2["stages"] if s["root"])
span = max(v - rel[rootid] for v in rel.values())
settle = next(s["settle"] for s in stages["stages"] if s["root"])
rep["gates"] = dict(fixed_point_rows=n1, fixed_point_mismatch=len(bad1), max_reset_hop_um=max(hops)[0],
                    over_405=[h for h in hops if h[0] > 405], raw_relative_span=span, settle=settle, settle_ok=span + 4 <= settle)
(out / "start_stages_src25q.json").write_text(json.dumps(st2, indent=1) + "\n")
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
rep["files_vs_src25r"] = diff; rep["unused_uniform_exports"] = len(spares)
r0 = json.load(open(src / "report.json")); r0["unused_uniform_exports"] = spares
r0["src25r"] = "DIE-HEAD-38: R2 reader START x4 types + turn_a tstart pin; see src25s_report.json"
(out / "report.json").write_text(json.dumps(r0, indent=1) + "\n")
rep["sha256"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.glob("*.sv")) + [plan_path]}
(out / "src25s_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps(rep["gates"])); print(json.dumps(rep["changes"], indent=0)); print(json.dumps(diff))
print("source_plan.json sha256", rep["sha256"]["source_plan.json"])
if bad1 or rep["gates"]["over_405"] or not rep["gates"]["settle_ok"]: sys.exit("GATE FAIL")
