"""DIE-QC-36 A0: author the slice core_tree of an A0 tile (qfd_tile_nl_a0c / qfd_tile_nk_a0c) for the opt-in
core_infra.py delta (stage_basis total + cts_stages, form-C macro gates with early_tap_ps, install_stage pre_cts).

Inputs are plan/census data only (no timing measurement): the kit master_slice.json, the read-only clock census of the
GEOM PASS-COND 3_place (cts36/census/n?.tsv.gz: every sink of the clock port and of each hop ICG, placed xy), and the
macro signed Liberty views (min/max_clock_tree_path of the macro clock pin, TT and FF) from the kit macros/ dir.
Tree (T = total stages, plan stage model = clk_aocv_table_g021 class B mu_stage_ps TT 36.154 / FF 27.549):
  port -> R (1) -> t2 .. t(T-4) trunk;  register hop ICGs (CTS-open domains, cts_stages 3) on t(T-4) -> total T;
  root registers: equal-count planned leaves (<= 24 sinks) at depth T below t(T-4) (3 bisection levels);
  macro hop ICGs = planned-domain gates (form C): romleaf (k = 8) on R -> leaf at 3, LSL / node (k = 7) on t2 -> leaf
  at 4, each leaf.early_tap_ps = the macro view insertion -> total T = 11 (the minimum the romleaf view allows).
    python3 -I gen_a0_tree.py --kit KIT --census nl.tsv.gz --out slice.json [--report report.json]
"""
import argparse, gzip, json, math, re
from pathlib import Path

STAGE = {"TT": 36.154, "FF": 27.549,
         "source": "tools/die_plan/clk_aocv_table_g021.json clock_aocv.classes.B.{TT,FF}.mu_stage_ps (core tree stage)"}
FANOUT = 24
CTS_STAGES = 3
T = 11


def lib_insertion(path):
    """(min, max) over rise/fall of the clock pin's min_clock_tree_path / max_clock_tree_path in a macro Liberty."""
    txt = Path(path).read_text()
    out = {}
    for kind in ("min", "max"):
        m = re.search(kind + r"_clock_tree_path;\s*cell_rise\(scalar\)\s*\{\s*values\(\"([0-9.]+)\"\);\s*\}\s*"
                      r"cell_fall\(scalar\)\s*\{\s*values\(\"([0-9.]+)\"\);", txt)
        if not m:
            raise SystemExit(f"{path}: no {kind}_clock_tree_path")
        a, b = float(m[1]), float(m[2])
        out[kind] = min(a, b) if kind == "min" else max(a, b)
    return out


def split(pts, counts):
    """Recursive bisection of pts (list of (x, y, item)) into len(counts) groups of exactly counts[i] items."""
    if len(counts) == 1:
        return [pts]
    h = len(counts) // 2
    n1 = sum(counts[:h])
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    axis = 0 if max(xs) - min(xs) >= max(ys) - min(ys) else 1
    pts = sorted(pts, key=lambda p: (p[axis], p[1 - axis]))
    return split(pts[:n1], counts[:h]) + split(pts[n1:], counts[h:])


def equal_counts(n, k):
    return [n // k + (1 if i < n % k else 0) for i in range(k)]


def centroid(pts):
    return [round(sum(p[0] for p in pts) / len(pts), 3), round(sum(p[1] for p in pts) / len(pts), 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", required=True); ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--report")
    ap.add_argument("--dpl-max", type=float, default=60.0)
    ap.add_argument("--spread", action="store_true")
    ap.add_argument("--stages", type=int, default=11)
    a = ap.parse_args()
    global T
    T = a.stages
    kd = Path(a.kit)
    sl = json.loads((kd / "master_slice.json").read_text())
    port, root, dom, gates = None, [], {}, {}
    for line in gzip.open(a.census, "rt"):
        f = line.rstrip("\n").split("\t")
        if line.startswith("port "):
            _, _, x, y = line.split(); port = [float(x), float(y)]
            continue
        if f[0] != "S":
            continue
        path, depth, inst, pin, master, x, y = f[1], int(f[2]), f[3], f[4], f[5], float(f[6]), float(f[7])
        if depth == 0:
            if master.startswith("ICG"):
                gates[inst] = dict(master=master, xy=[x, y])
            else:
                root.append((x, y, f"{inst}/{pin}"))
        elif depth == 1:
            g = path.split(">", 1)[1]
            dom.setdefault(g, []).append(dict(inst=inst, pin=pin, master=master, xy=[x, y]))
    views = {}
    for g, sinks in dom.items():
        if len(sinks) == 1 and sinks[0]["master"].startswith("ot_qwen_tile_"):
            m = sinks[0]["master"]
            if m not in views:
                ff, tt = kd / "macros" / f"{m}_ff.lib", kd / "macros" / f"{m}_tt.lib"
                import hashlib
                views[m] = dict(FF=lib_insertion(ff), TT=lib_insertion(tt),
                                view=f"macros/{m}_{{tt,ff}}.lib sha256 tt:{hashlib.sha256(tt.read_bytes()).hexdigest()[:16]} "
                                     f"ff:{hashlib.sha256(ff.read_bytes()).hexdigest()[:16]} (min/max_clock_tree_path)")
    reg_gates = sorted(g for g, s in dom.items() if not (len(s) == 1 and s[0]["master"] in views))
    mac_gates = sorted(g for g in dom if g not in reg_gates)
    assert set(gates) == set(dom), (set(gates) ^ set(dom))
    cx, cy = centroid([(*gates[g]["xy"], g) for g in reg_gates])
    nodes, leaves, glist = [], [], []
    # trunk R .. t(T-4) from the port toward the register-ICG centroid
    trunk = []
    for k in range(1, T - 3):
        f = (k - 1) / max(1, T - 5)
        name = "mp_a0_R" if k == 1 else f"mp_a0_t{k}"
        nodes.append(dict(name=name, master="BUFx24_ASAP7_75t_R",
                          xy_um=[round(port[0] + f * (cx - port[0]), 3), round(port[1] + 2.0 + f * (cy - port[1]), 3)],
                          parent="port:ck" if k == 1 else trunk[-1]))
        trunk.append(name)
    top = trunk[-1]                       # depth T-4
    for g in reg_gates:
        glist.append(dict(inst=g, master=gates[g]["master"], parent=top, xy_um=gates[g]["xy"]))
        leaves.append(dict(node=g, load_class="gated_domain", domain_sinks=len(dom[g]), cts_stages=CTS_STAGES))
    # root registers: L equal-count leaves at depth T under top (levels T-3, T-2, T-1, T)
    L = math.ceil(len(root) / FANOUT)
    groups = split(root, equal_counts(len(root), L))
    lv = [dict(pts=g) for g in groups]
    for k, g in enumerate(lv):
        g["name"] = f"mp_a0_l{k}"
    levels = [lv]
    for lev in range(3):                  # parents at depth T-1, T-2, T-3
        cur = levels[-1]
        n_par = max(1, math.ceil(len(cur) / 4)) if lev < 2 else max(1, math.ceil(len(cur) / 4))
        pts = [(*centroid(c["pts"]), c) for c in cur]
        par = []
        for k, grp in enumerate(split(pts, equal_counts(len(cur), n_par))):
            allp = [q for (_, _, c) in grp for q in c["pts"]]
            par.append(dict(name=f"mp_a0_p{T - 1 - lev}_{k}", pts=allp, kids=[c for (_, _, c) in grp]))
        levels.append(par)
    for lev in reversed(range(len(levels))):
        for nd in levels[lev]:
            parent = top if lev == len(levels) - 1 else nd["_parent"]
            master = "BUFx8_ASAP7_75t_R" if lev == 0 else "BUFx12f_ASAP7_75t_R"
            nodes.append(dict(name=nd["name"], master=master, xy_um=centroid(nd["pts"]), parent=parent))
            for c in nd.get("kids", []):
                c["_parent"] = nd["name"]
    for nd in levels[0]:
        leaves.append(dict(node=nd["name"], sinks=[p[2] for p in nd["pts"]]))
    # macro hop ICGs: form C planned gates with early-tap leaves
    early = []
    for g in mac_gates:
        s = dom[g][0]
        v = views[s["master"]]
        ins = {c: {"min": v[c]["min"], "max": v[c]["max"]} for c in ("TT", "FF")}
        k = int(math.floor(((ins["FF"]["min"] + ins["FF"]["max"]) / 2) / STAGE["FF"] + 0.5))
        gate_parent = trunk[T - k - 3] if T - k - 3 >= 0 else None   # gate depth = T - k - 1
        if gate_parent is None:
            raise SystemExit(f"{g}: early tap k={k} needs a gate above the root")
        glist.append(dict(inst=g, master=gates[g]["master"], parent=gate_parent, xy_um=gates[g]["xy"], domain="planned"))
        gx, gy = gates[g]["xy"]
        leaf = f"mp_a0_m_{g.split('.')[-1].split('/')[0]}"
        nodes.append(dict(name=leaf, master="BUFx24_ASAP7_75t_R", xy_um=[round(gx, 3), round(gy + 1.5, 3)], parent=g))
        leaves.append(dict(node=leaf, sinks=[f"{s['inst']}/{s['pin']}"], load_class="macro", early_tap_ps=ins,
                           early_tap_view=v["view"]))
        early.append(dict(gate=g, macro=s["master"], k=k, leaf_depth=T - k))
    if a.spread:
        # Spread all clock loads, including early macro gates, from the port.
        # Depth is preserved exactly; no clock/data/reset cycle is added.
        fr = json.loads((kd / "freeze.json").read_text())
        boxes=[]
        for hc in fr.get("hard_children", []):
            txt=(kd/"macros"/(hc["master"]+".lef")).read_text()
            mm=re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)",txt)
            x,y=hc["at"]; w,h=map(float,mm.groups()); boxes.append((x-5.8,y-4.6,x+w+5.8,y+h+4.6))
        def legal(pt):
            x=max(6.,min(451.9,pt[0]));y=max(4.8,min(1152.9,pt[1]))
            pending=[(x,y)];seen=set();ok=[]
            while pending:
                x,y=pending.pop();key=(round(x,3),round(y,3))
                if key in seen:continue
                seen.add(key)
                hit=next((b for b in boxes if b[0]<x<b[2] and b[1]<y<b[3]),None)
                if hit:
                    aa,bb,cc,dd=hit
                    for q in ((aa,y),(cc,y),(x,bb),(x,dd)):
                        if 6<=q[0]<=451.9 and 4.8<=q[1]<=1152.9:pending.append(q)
                else:ok.append((x,y))
            if not ok:raise ValueError("no legal planned buffer site")
            return list(min(ok,key=lambda q:abs(q[0]-pt[0])+abs(q[1]-pt[1])))
        olddepth={"port:ck":0}
        for nd in nodes:
            if nd["name"] in trunk:olddepth[nd["name"]]=olddepth[nd["parent"]]+1
        targets=[]
        for gg in glist:
            targets.append(dict(record=gg,xy=gg["xy_um"],goal=olddepth[gg["parent"]],name=gg["inst"]))
        for nd in nodes:
            if nd["name"].startswith("mp_a0_p") and nd["parent"]==top:
                targets.append(dict(record=nd,xy=nd["xy_um"],goal=T-4,name=nd["name"]))
        rootnd=next(n for n in nodes if n["name"]==trunk[0]);rootnd["xy_um"]=legal(rootnd["xy_um"])
        nodes=[n for n in nodes if n["name"] not in trunk[1:]]
        serial=[0]
        def feed(parent,xy,depth,items):
            ready=[q for q in items if q["goal"]==depth];later=[q for q in items if q["goal"]>depth]
            if len(ready)>4 or (len(ready)==4 and later):raise ValueError(f"depth {depth}: {len(ready)} fixed-depth loads cannot have fanout<=4")
            for q in ready:q["record"]["parent"]=parent
            if not later:return
            branches=min(4-len(ready),len(later));pts=[(*q["xy"],q) for q in later]
            for grp in split(pts,equal_counts(len(pts),branches)):
                kids=[q for x,y,q in grp];cx,cy=centroid(grp);rem=min(q["goal"] for q in kids)-depth
                pos=legal([xy[0]+(cx-xy[0])/rem,xy[1]+(cy-xy[1])/rem])
                serial[0]+=1;name=f"mp_a0_sp{serial[0]}"
                nodes.append(dict(name=name,master="BUFx24_ASAP7_75t_R",xy_um=[round(v,3) for v in pos],parent=parent))
                feed(name,pos,depth+1,kids)
        feed(rootnd["name"],rootnd["xy_um"],1,targets)
        xy_by_name={"port:ck":port,**{n["name"]:n["xy_um"] for n in nodes},**{g["inst"]:g["xy_um"] for g in glist}}
        arcs=[];fan={}
        for nd in nodes+[{"name":g["inst"],"parent":g["parent"],"xy_um":g["xy_um"]} for g in glist]:
            aa=xy_by_name[nd["parent"]];bb=nd["xy_um"];length=abs(aa[0]-bb[0])+abs(aa[1]-bb[1]);fan[nd["parent"]]=fan.get(nd["parent"],0)+1;arcs.append((length,nd["parent"],nd["name"]))
        print("SPREAD_GEOMETRY",json.dumps(dict(max_fanout=max(fan.values()),max_leg_um=max(x[0] for x in arcs),long_legs=[x for x in arcs if x[0]>150],targets=len(targets))),flush=True)
    sl["core_tree"] = dict(clock_port=sl.get("core_clock_port", "ck"), stage_basis="total", install_stage="pre_cts",
                           late_dpl_max_um=a.dpl_max, early_tap_stage_ps=STAGE, nodes=nodes, gates=glist,
                           leaves=leaves,
                           note="DIE-QC-36 A0 plan-built tile tree (gen_a0_tree.py): census of the GEOM PASS-COND "
                                "3_place, macro early taps from the macro Liberty views; no timing measurement")
    Path(a.out).write_text(json.dumps(sl, indent=1) + "\n")
    rep = dict(T=T, port=port, reg_gates=len(reg_gates), mac_gates=len(mac_gates), root_registers=len(root),
               root_leaves=L, leaf_counts=sorted({len(g) for g in groups}), nodes=len(nodes), early=early,
               domains={g: len(dom[g]) for g in reg_gates}, views={m: {c: v[c] for c in ("TT", "FF")}
                                                                    for m, v in views.items()})
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("T", "reg_gates", "mac_gates", "root_registers", "root_leaves",
                                          "leaf_counts", "nodes")}), [(e["macro"], e["k"]) for e in early][:3])


if __name__ == "__main__":
    main()
