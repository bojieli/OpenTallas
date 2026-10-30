#!/usr/bin/env python3
"""DIE-HBM-29 plan event on d28c (die-local, no shared tool change):
 (A) HBM-055 scorer contents: 3-way slot rotation of equal-size (218.592 x 187.488) scorer hard cores
     r1c0_k0h0: b101 -> b102 (into the r1c2_k0h0 slot), r1c2_k0h0: b102 -> b103 (into the tail0 slot),
     tail0: b103 -> b101 (into the r1c0_k0h0 slot); every variant of q_b101/q_b102/q_b103.
     Slot geometry (origin/orient/outline) stays, the moving core brings its module/pins/clock entry.
     core_conns follow the coarse in-type cross product (every hcol <-> every other hcol, tail = clk only);
     internal stations: b102 = rename (same module, same slot); b101 = drop the leaving hcol's entries;
     b103 = transplant the entries of the nearest same-module sibling (shifted by the slot offset), regs re-chained
     on the W channel (x = 4.32) when a hop would exceed the reach.
 (B) map: copy of the bind map with the moved scorer leaves + row-0 E glue + score register -> b101 (NW/NE).
 (C) type clock taps + clock_entries.json follow the moved cores (G0C reads them); the legacy clock_taps_die.json sidecar
     is read by no tool and stays byte-same (a recomputed copy is written next to it for reference).
usage: hbm055_event.py SRC_PLAN_DIR OUT_PLAN_DIR SRC_MAP OUT_MAP
"""
import copy, json, math, shutil, sys
from pathlib import Path

SRC, OUT, SMAP, OMAP = map(Path, sys.argv[1:5])
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT, symlinks=True)
P = json.loads((OUT / "die_plan.json").read_text())
CC = json.loads((OUT / "core_conns.json").read_text())
CE = json.loads((OUT / "clock_entries.json").read_text())
T = P["partition_types"]
PRE = "u_hb_idx__s_Q_"
H0, TAIL = "ot_hbm_idx_score_hcol_h0", "ot_hbm_idx_tail_native"
SMAX = 360.0
rep = {"event": "DIE-HBM-29 HBM-055", "types": {}}

def fam(t):
    return [k for k in T if k == t or k.startswith(t + "__") or k == t + "_nw"]

def hc(t, inst):
    return next(h for h in T[t]["hard_cores"] if h["inst"] == inst)

def tap(t, name):
    return next(x for x in T[t]["clock"]["taps"] if x["name"] == name)

def tapname(inst, module):
    return inst if module == TAIL else inst + ".clk_pair"

def cekey(t):
    return t if t in CE else t.split("__")[0].replace("_nw", "")

# canonical source records (taken before any edit)
src = {}
for t, x in (("q_b101", "r1c0_k0h0"), ("q_b102", "r1c2_k0h0"), ("q_b103", "tail0")):
    h = copy.deepcopy(hc(t, PRE + x))
    src[x] = dict(hc=h, tap=copy.deepcopy(tap(t, tapname(h["inst"], h["module"]))),
                  ce=copy.deepcopy(CE[cekey(t)][h["inst"]]), cc=copy.deepcopy(CC[t].get(h["inst"])))

def place(t, old, new_src, new_inst):
    """old slot inst -> new core (module/pins/clock from new_src), slot geometry kept."""
    v = T[t]
    o = hc(t, old)
    n = copy.deepcopy(new_src["hc"])
    for k in ("origin_um", "orient", "outline_um", "track_offset_um", "obs_max"):
        if k in o:
            n[k] = o[k]
        elif k in n:
            del n[k]
    n["inst"] = new_inst
    n["note"] = n.get("note", "") + f" | DIE-HBM-29 HBM-055: moved into {t} slot of {old} (slot geometry kept)"
    v["hard_cores"][v["hard_cores"].index(o)] = n
    ot = tap(t, tapname(old, o["module"]))
    nt = copy.deepcopy(new_src["tap"])
    nt["xy"] = ot["xy"]                       # same core-local entry (107.976, 95.04) on every scorer core
    nt["note"] = nt.get("note", "") + " | DIE-HBM-29 HBM-055 slot move"
    v["clock"]["taps"][v["clock"]["taps"].index(ot)] = nt
    ck = cekey(t)
    if ck == t or t == ck:
        CE[ck].pop(old, None)
        CE[ck][new_inst] = copy.deepcopy(new_src["ce"])
    return o, n

def hcols(t):
    return [h["inst"] for h in T[t]["hard_cores"] if h["module"].startswith("ot_hbm_idx_score_hcol")]

def rebuild_cc(t, template_inst):
    """coarse cross product: every hcol port lists every other hcol of the type (core_conns form)."""
    c = CC[t]
    hs = hcols(t)
    tmpl = c[template_inst]
    for h in hs:
        if h not in c:
            c[h] = {}
        for port, lst in tmpl.items():
            if port == "clk_pair":
                c[h][port] = [f"tap:{h}.clk_pair"]
            else:
                c[h][port] = [f"core:{o}" for o in hs if o != h]
    for k in list(c):
        if k.startswith(PRE) and k not in hs and not k.startswith(PRE + "tail"):
            del c[k]
    for k in [k for k in c if k.startswith(PRE + "tail")]:
        c[k] = {"clk": [f"tap:{k}"]}

def hops_ok(a, regs, b, smax):
    pts = [a] + regs + [b]
    return all(abs(p[0] - q[0]) + abs(p[1] - q[1]) <= smax + 1e-6 for p, q in zip(pts, pts[1:]))

def chain(a, b, smax=SMAX, xch=4.32):
    """W-channel chain a -> (xch, a.y) -> (xch, b.y) -> b with regs every <= smax."""
    path = [a, [xch, a[1]], [xch, b[1]], b]
    L = sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(path, path[1:]))
    n = max(0, math.ceil(L / smax) - 1)
    regs = []
    for i in range(1, n + 1):
        s = L * i / (n + 1)
        for p, q in zip(path, path[1:]):
            seg = abs(p[0] - q[0]) + abs(p[1] - q[1])
            if s <= seg + 1e-9:
                f = s / seg if seg else 0
                regs.append([round(p[0] + (q[0] - p[0]) * f, 3), round(p[1] + (q[1] - p[1]) * f, 3)])
                break
            s -= seg
    return regs

def ren(e, a, b):
    e = copy.deepcopy(e)
    for k in ("conn", "launch", "capture"):
        if k in e:
            e[k] = e[k].replace(a + ".", b + ".").replace(a + "|", b + "|")
            if e[k] == a:
                e[k] = b
            if e[k].endswith("|" + a):
                e[k] = e[k][: -len(a)] + b
    return e

def core_of(s):
    return (s or "").split(".")[0]

for t in fam("q_b101") + fam("q_b102") + fam("q_b103"):
    pass
done = set()
for base in ("q_b101", "q_b102", "q_b103"):
    for t in fam(base):
        if t in done:
            continue
        done.add(t)
        v = T[t]
        ist = v["internal_stations"]
        r = {"stations_before": len(ist)}
        if base == "q_b101":
            old = PRE + "r1c0_k0h0"
            place(t, old, src["tail0"], PRE + "tail0")
            v["internal_stations"] = [e for e in ist if old not in (core_of(e.get("launch")), core_of(e.get("capture")))]
            rebuild_cc(t, PRE + "r0c2_k0h0")
        elif base == "q_b102":
            old, new = PRE + "r1c2_k0h0", PRE + "r1c0_k0h0"
            place(t, old, src["r1c0_k0h0"], new)
            v["internal_stations"] = [ren(e, old, new) for e in ist]
            rebuild_cc(t, PRE + "r1c0_k0h1")
        else:
            old, new = PRE + "tail0", PRE + "r1c2_k0h0"
            o, n = place(t, old, src["r1c2_k0h0"], new)
            # top-row slot: the hcol N-face ports must face the partners below -> MX like the other top-row hcols
            n["orient"] = "MX"
            nt = tap(t, new + ".clk_pair")
            nt["xy"] = [n["origin_um"][0] + 107.976, round(n["origin_um"][1] + 187.488 - 95.04, 3)]
            # nearest same-module sibling in the same column (x) -> transplant its stations
            sibs = [h for h in v["hard_cores"] if h["module"] == H0 and h["inst"] != new
                    and abs(h["origin_um"][0] - n["origin_um"][0]) < 1]
            sib = min(sibs, key=lambda h: abs(h["origin_um"][1] - n["origin_um"][1]))
            dy = n["origin_um"][1] - sib["origin_um"][1]
            dx = n["origin_um"][0] - sib["origin_um"][0]
            add, rechained = [], 0
            for e in ist:
                lc, cc_ = core_of(e.get("launch")), core_of(e.get("capture"))
                if sib["inst"] not in (lc, cc_) or new in (lc, cc_):
                    continue
                f = ren(e, sib["inst"], new)
                if lc == sib["inst"]:
                    f["from_um"] = [round(f["from_um"][0] + dx, 3), round(f["from_um"][1] + dy, 3)]
                else:
                    f["to_um"] = [round(f["to_um"][0] + dx, 3), round(f["to_um"][1] + dy, 3)]
                if not hops_ok(f["from_um"], f["regs_um"], f["to_um"], SMAX):
                    f["regs_um"] = chain(f["from_um"], f["to_um"])
                    rechained += 1
                f["note"] = f"DIE-HBM-29 HBM-055: transplanted from {sib['inst']} (dx {dx:+.2f}, dy {dy:+.2f})"
                add.append(f)
            # the sibling <-> new pair itself
            for a_, b_ in ((sib["inst"], new), (new, sib["inst"])):
                for e in ist:
                    if core_of(e.get("launch")) == sib["inst"] and core_of(e.get("capture")) != new:
                        port = e["launch"].split(".", 1)[1]
                        if any(x.get("launch") == f"{a_}.{port}" and core_of(x.get("capture")) == b_ for x in add):
                            continue
                        ha = hc(t, a_); hb = hc(t, b_)
                        fa = [ha["origin_um"][0] + 3.48, ha["origin_um"][1] + 187.488 / 2]
                        tb = list(hb["origin_um"])
                        d = abs(fa[0] - tb[0]) + abs(fa[1] - tb[1])
                        if d > SMAX:
                            g = dict(conn=f"{a_}.{port}|{b_}", from_um=fa, to_um=tb, regs_um=chain(fa, tb),
                                     bits=e["bits"], launch=f"{a_}.{port}", capture=b_,
                                     note="DIE-HBM-29 HBM-055: new sibling pair, W-channel chain")
                            for k in ("bits_parallel", "serial_k"):
                                if k in e:
                                    g[k] = e[k]
                            add.append(g)
            v["internal_stations"] = [e for e in ist if old not in (core_of(e.get("launch")), core_of(e.get("capture")))] + add
            r.update(sibling=sib["inst"], dy=dy, transplanted=len(add), rechained=rechained)
            rebuild_cc(t, PRE + "r1c2_k1h0")
        v["note"] = v.get("note", "") + " | DIE-HBM-29 HBM-055 scorer contents (slot rotation r1c0_k0h0->b102, r1c2_k0h0->b103, tail0->b101)"
        r["stations_after"] = len(v["internal_stations"])
        r["hard_cores"] = sorted(h["inst"][len(PRE):] for h in v["hard_cores"] if h["inst"].startswith(PRE))
        rep["types"][t] = r

# (C) clock_taps_die.json: recompute every entry from the plan
parts = {p_["name"]: p_ for p_ in P["partitions"]}
ctd = json.loads((OUT / "clock_taps_die.json").read_text())
moved = []
newctd = []
seen = set()
def xf(part, xy):
    t = T[part["type"]]; W, H = t["outline_um"]; x, y = xy; o = part.get("orient", "R0")
    if o == "MY": x = W - x
    elif o == "MX": y = H - y
    elif o == "R180": x, y = W - x, H - y
    return [round(part["origin_um"][0] + x, 3), round(part["origin_um"][1] + y, 3)]
ren_tap = {PRE + "r1c0_k0h0.clk_pair": {"b101": PRE + "tail0", "b102": None},
           }
for e in ctd:
    part = parts.get(e["part"])
    if part is None:
        newctd.append(e); continue
    tt = T[part["type"]]
    names = {x["name"]: x for x in tt["clock"]["taps"]}
    nm = e["tap"]
    if nm not in names:
        # renamed by HBM-055 in this partition: map by slot (same xy before)
        cand = [x for x in tt["clock"]["taps"] if xf(part, x["xy"]) == [round(c, 3) for c in e["xy_die_um"]]]
        if len(cand) == 1:
            nm = cand[0]["name"]
        else:
            moved.append(dict(part=e["part"], tap=e["tap"], status="dropped (no tap in plan)")); continue
    if (e["part"], nm) in seen:
        continue
    seen.add((e["part"], nm))
    f = dict(e, type=part["type"], tap=nm, xy_die_um=xf(part, names[nm]["xy"]))
    if f["xy_die_um"] != e["xy_die_um"] or nm != e["tap"]:
        moved.append(dict(part=e["part"], tap=e["tap"], new_tap=nm, before=e["xy_die_um"], after=f["xy_die_um"],
                          dist=round(abs(f["xy_die_um"][0] - e["xy_die_um"][0]) + abs(f["xy_die_um"][1] - e["xy_die_um"][1]), 1)))
    newctd.append(f)
# taps in the plan that the sidecar lacks
have = {(e["part"], e["tap"]) for e in newctd}
for pn, part in parts.items():
    if part["type"] not in T or "clock" not in T[part["type"]]:
        continue
    for x in T[part["type"]]["clock"].get("taps", []):
        if (pn, x["name"]) not in have and any(e["part"] == pn for e in ctd):
            newctd.append(dict(part=pn, type=part["type"], tap=x["name"], insertion_ps=x.get("insertion_ps", 250.0),
                               insertion_ff_ps=x.get("insertion_ff_ps", 202.5), xy_die_um=xf(part, x["xy"])))
            moved.append(dict(part=pn, tap=x["name"], status="added", after=newctd[-1]["xy_die_um"]))
(OUT / "clock_taps_die.recomputed.json").write_text(json.dumps(newctd, indent=1))   # the legacy sidecar is read by no tool (grep tools/): kept byte-same, recomputed copy for reference
rep["clock_taps_die"] = dict(entries_before=len(ctd), entries_after=len(newctd), changed=len(moved),
                             moved_over_1um=sorted({m["part"] for m in moved if m.get("dist", 0) > 1}))
(OUT / "hbm055_clock_taps_moves.json").write_text(json.dumps(moved, indent=1))

(OUT / "die_plan.json").write_text(json.dumps(P, indent=1))
(OUT / "core_conns.json").write_text(json.dumps(CC, indent=1))
(OUT / "clock_entries.json").write_text(json.dumps(CE, indent=1))

# (B) map
M = json.loads(SMAP.read_text())
pm = M["parts"]
mv = []
for h in ("NW", "NE"):
    s = f"hb_idx__s_{h}.scorer."
    leaf = lambda r, c, k, hh: f"{s}ge[{r}].gc[{c}].leaf.core.g_col[{k}].g_half[{hh}].u_hc"
    upd = {leaf(1, 0, 0, 0): [f"{h}_b102", PRE + "r1c0_k0h0"],
           leaf(1, 2, 0, 0): [f"{h}_b103", PRE + "r1c2_k0h0"],
           s + "ge[0].u_t": [f"{h}_b101", PRE + "tail0"]}
    for g in ("ge[0].keep_pipe", "ge[0].md", "score_fault_check", "$procdff$71730", "$procdff$71751", "$procdff$71756"):
        upd[s + g] = f"{h}_b101"
    for k, val in upd.items():
        if k not in pm:
            raise SystemExit(f"map key missing: {k}")
        mv.append(dict(key=k, before=pm[k], after=val)); pm[k] = val
M["note"] = "DIE-HBM-29 HBM-055: scorer slot rotation + row-0 E glue/score register -> b101 | " + M["note"]
OMAP.write_text(json.dumps(M))
rep["map_moves"] = mv
(OUT / "hbm055_event_report.json").write_text(json.dumps(rep, indent=1))
print(json.dumps({k: (v if k != "map_moves" else len(v)) for k, v in rep.items()}, indent=1))
