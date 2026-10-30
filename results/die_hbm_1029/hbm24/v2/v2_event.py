#!/usr/bin/env python3
"""DIE-HBM-24/V2 far-pair variant: feedthrough (ft) slots through root and spb1 (and the row-A/C partitions next to
the hub for SM<->hub), NO partition move.  Die-local overlay event on a re-plan output (VL3d / VL3e); no shared tool
changed (uses tools/die_plan/lane_add.Builder as a library).

    python3 v2_event.py TOOLS PLANDIR FAR_ROWS_JSON OUTDIR [--groups G1,G2,G3,G4] [--first-id 600]

FAR_ROWS_JSON = a replan_report.json (phase2.far) or {"rows":[{src,dst,unplanned_bits|bits}]}.
Groups (rows not in a group stay FAR, reported):
  G1 NW_hub<->NE_hub across root (chain hub|root|hub)
  G2 rows with root as an endpoint, or NE->NW-hub rows that must cross root (generic abutment paths that may cross root)
  G3 hub<->spb0 through spu1|spb2|spb1 (q_spb1 is NW/NE-shared: the NE mirror lane re-uses the NW slot declaration)
  G4 SM<->hub through the row-A/C partition between them (q_sm* are NW/NE-shared endpoints: same mirror rule)
Mirror rule (shared types): NW lane first; its NE mirror (lane id + 'm') takes the exact MY-mirrored windows; on every
NW/NE-shared type the NE lane must produce the identical type-frame declaration, which is then de-duplicated (the NE
ports refer to the NW decl names).  If that fails, BOTH lanes of the pair roll back (no unbound shared declaration).
Writes OUTDIR/die_plan.json + v2_report.json; other files of PLANDIR hard-linked.  Plan arithmetic: UNCHECKED until
G0/G0C/bind."""
import argparse, copy, heapq, json, os, sys, time
from collections import Counter
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("tools"); ap.add_argument("plan"); ap.add_argument("rows"); ap.add_argument("out")
ap.add_argument("--groups", default="G1,G2,G3,G4"); ap.add_argument("--first-id", type=int, default=600)
ap.add_argument("--max-hops", type=int, default=16)
a = ap.parse_args()
sys.path.insert(0, a.tools)
import schema as S  # noqa
import lane_add as LA  # noqa

t0 = time.time()
plan_dir, out = Path(a.plan), Path(a.out)
raw = json.loads((plan_dir / "die_plan.json").read_text())
W = raw["die"]["outline_um"][0]
R = json.loads(Path(a.rows).read_text())
rows = R["phase2"]["far"] if "phase2" in R else R["rows"]
rows = [dict(src=r["src"], dst=r["dst"], bits=int(r.get("bits", r.get("unplanned_bits")))) for r in rows]
GROUPS = set(a.groups.split(","))

B = LA.Builder(raw, near_um=1e9, max_hops=a.max_hops, first_id=a.first_id, require_cycle_match=False)
SHARED = set(B.shared)
B.shared = set()
OPP = LA.OPP
existing_ids = {l["id"] for l in raw["lanes"]}


def mp(n):
    if n.startswith("NW_"):
        return "NE_" + n[3:]
    if n.startswith("NE_"):
        return "NW_" + n[3:]
    return n


def mirror_win(win, face):
    if face in ("E", "W"):
        return [round(win[0], 4), round(win[1], 4)]
    return [round(W - win[1], 4), round(W - win[0], 4)]


def uturn(ch):
    P = B.P
    for k in range(1, len(ch) - 1):
        if LA.shared_edge(P, ch[k], ch[k - 1])[0] == LA.shared_edge(P, ch[k], ch[k + 1])[0]:
            return True
    return False


def path_ex(s, d, ban_nodes=(), max_hops=16):
    """shortest abutment path; root / spb1 MAY be crossed (V2); PHY / io never crossed; no U-turns."""
    P = B.P
    dist, prev, hq = {s: 0.0}, {}, [(0.0, s, 0)]
    while hq:
        d_, u, n = heapq.heappop(hq)
        if u == d:
            break
        if d_ > dist.get(u, 1e18) + 1e-6 or n >= max_hops:
            continue
        for v in B.neighbours(u):
            if v != d and (v.startswith("PHY") or v.endswith("_io") or v in ban_nodes):
                continue
            if u in prev and LA.shared_edge(P, u, prev[u])[0] == LA.shared_edge(P, u, v)[0]:
                continue
            cu, cv = LA.centre(P, u), LA.centre(P, v)
            nd = d_ + abs(cu[0] - cv[0]) + abs(cu[1] - cv[1])
            if nd < dist.get(v, 1e18) - 1e-6:
                dist[v], prev[v] = nd, u
                heapq.heappush(hq, (nd, v, n + 1))
    if d not in prev:
        return None
    o = [d]
    while o[-1] != s:
        o.append(prev[o[-1]])
    return o[::-1]


def group(r):
    s, d = r["src"], r["dst"]
    if {s, d} == {"NW_hub", "NE_hub"}:
        return "G1"
    if "root" in (s, d) or (s.startswith("NE_") and d.startswith("NW_")) or (s.startswith("NW_") and d.startswith("NE_")):
        return "G2"
    if {s[3:], d[3:]} == {"hub", "spb0"}:
        return "G3"
    if d[3:] == "hub" and s[3:5] == "sm" or s[3:] == "hub" and d[3:5] == "sm":
        return "G4"
    return None


def cand_chains(r, g):
    s, d = r["src"], r["dst"]
    out = []
    side = s[:3] if s[:3] in ("NW_", "NE_") else d[:3]
    if g == "G1":
        out.append([s, "root", d])
    if g == "G3":
        c = [side + x for x in ("hub", "spu1", "spb2", "spb1", "spb0")]
        out.append(c if s.endswith("hub") else c[::-1])
    if g == "G4":
        sm = s if "sm" in s else d
        via = {"sm0": ["su01"], "sm1": ["su10", "su11"], "sm2": ["su21", "spu1"], "sm3": ["su30", "b100", "b110", "su31"]}[sm[3:]]
        for v_ in via:
            c = [sm, side + v_, side + "hub"]
            out.append(c if s == sm else c[::-1])
    p1 = path_ex(s, d)
    if p1:
        out.append(p1)
        for x in p1[1:-1]:
            p2 = path_ex(s, d, ban_nodes={x})
            if p2:
                out.append(p2)
    seen, res = set(), []
    for c in out:
        if tuple(c) in seen or uturn(c) or not all(LA.shared_edge(B.P, u, v) for u, v in zip(c, c[1:])):
            continue
        seen.add(tuple(c)); res.append(c)
    return res


# mirror-window hinting: B.alloc tries the exact mirrored NW window first
_orig_alloc = B.alloc
HINT = []


def alloc_h(u, v, width, prefer=None):
    if HINT:
        nwin = HINT.pop(0)
        e = LA.shared_edge(B.P, u, v)
        if e is not None:
            df, lo, hi = e
            mw = mirror_win(nwin, df)
            occ = LA.face_intervals(B.P, u, df) + LA.face_intervals(B.P, v, OPP[df]) + B.taken[(u, df)]
            if mw[0] >= lo + B.guard and mw[1] <= hi - B.guard and all(mw[1] + B.guard <= x0 or mw[0] - B.guard >= x1
                                                                      for x0, x1 in occ):
                B.taken[(u, df)].append(tuple(mw)); B.taken[(v, OPP[df])].append(tuple(mw))
                return df, mw, LA.face_layers(B.P, u, df)
            prefer = (mw[0] + mw[1]) / 2
    return _orig_alloc(u, v, width, prefer=prefer)


B.alloc = alloc_h
LA.copy = type("C", (), {"deepcopy": staticmethod(lambda x: x)})   # build_one's internal snapshots: we snapshot here


def snap():
    return copy.deepcopy(B.raw), copy.deepcopy(B.taken), dict(B.ids), B.next_id


def restore(sn):
    r_, t_, i_, n_ = sn
    B.raw.clear(); B.raw.update(copy.deepcopy(r_))
    B.taken = copy.deepcopy(t_); B.ids, B.next_id = dict(i_), n_
    B.P = S.Plan(B.raw)


def build(r, chains, lid, hint=None):
    """try chains in order, splitting the width over up to 3 equal-cycle lanes; returns list of r1 or None."""
    for chain in chains:
        if not hint and set(chain) & SHARED:
            continue          # a non-mirrored lane must not touch a NW/NE-shared type
        for k in (1, 2, 3):
            sn = snap() if k > 1 else None
            widths = [r["bits"] // k + (1 if i < r["bits"] % k else 0) for i in range(k)]
            got = []
            for j, w in enumerate(widths):
                my = lid if j == 0 else f"{lid}s{j}"
                B.new_id = (lambda x: (lambda a_, b_, part=0: x))(my)
                HINT[:] = list(hint[j]) if hint and j < len(hint) else []
                r1 = B.build_one(r["src"], r["dst"], w, chain, "path", None, record=False)
                HINT[:] = []
                if r1 is None or (got and r1["cycles"] != got[0]["cycles"]):
                    r1 = None
                    break
                got.append(r1)
            if len(got) == k:
                return got
            if sn is not None:
                restore(sn)
    return None


def dedupe_shared(nw_got, ne_got):
    """NE decls on shared types -> the NW decl (identical type-frame geometry required)."""
    T = B.raw["partition_types"]
    pt = {p["name"]: p["type"] for p in B.raw["partitions"]}
    ren = {}
    for r_nw, r_ne in zip(nw_got, ne_got):
        lw, le = r_nw["lane"], r_ne["lane"]
        cw, ce = r_nw["chain"], r_ne["chain"]
        if [mp(x) for x in cw] != ce:
            return f"chain not mirrored {cw} vs {ce}"
        n = len(ce) - 1
        for i, part in enumerate(ce):
            if part not in SHARED:
                continue
            if i == 0:
                pairs = [("buses", f"{lw}_o", f"{le}_o")]
            elif i == n:
                pairs = [("buses", f"{lw}_i", f"{le}_i")]
            else:
                pairs = [("ft_slots", f"{lw}x{i}", f"{le}x{i}")]
            tn = pt[part]
            for key, nwn, nen in pairs:
                dn = [x for x in T[tn].get(key, []) if x["name"] == nwn]
                de = [x for x in T[tn].get(key, []) if x["name"] == nen]
                if len(dn) != 1 or len(de) != 1:
                    return f"{tn}.{key} {nwn}/{nen} missing"
                A_ = {k: v for k, v in dn[0].items() if k not in ("name", "regs_um")}
                B_ = {k: v for k, v in de[0].items() if k not in ("name", "regs_um")}
                if A_ != B_:
                    return f"{tn}.{key} {nen} != {nwn}: " + json.dumps({k: (A_.get(k), B_.get(k)) for k in A_ if A_.get(k) != B_.get(k)})[:300]
                T[tn][key] = [x for x in T[tn][key] if x["name"] != nen]
                if key == "buses":
                    ren[(part, nen)] = nwn
                else:
                    ren[(part, nen + "_i")] = nwn + "_i"; ren[(part, nen + "_o")] = nwn + "_o"
    for p in B.raw["ports"]:
        for side in ("src", "dst"):
            k_ = (p[side]["part"], p[side]["bus"])
            if k_ in ren:
                p[side]["bus"] = ren[k_]
    B.P = S.Plan(B.raw)
    for r1 in ne_got:
        nat = B.P.lane_natural(r1["lane"])
        B.raw["latency"]["lanes"][r1["lane"]] = dict(nat, natural=nat["cycles"], pad=0, param="LAT_" + r1["lane"].upper())
        r1["cycles"] = nat["cycles"]
    return None


rep = dict(schema="die_hbm_24.v2_event.v1", base=str(plan_dir), base_sha=LA.sha12(plan_dir / "die_plan.json"),
           groups=sorted(GROUPS), built=[], failed=[], far=[], estimate=[])
for r in rows:
    r["group"] = group(r)
def is_ne_row(r):
    return (r["src"].startswith("NE_") or r["dst"].startswith("NE_")) and not ({r["src"], r["dst"]} & {"NW_hub"})


nw_first = sorted(rows, key=lambda r: (is_ne_row(r), -r["bits"]))
idmap, nid = {}, a.first_id
done_rows = {}
for r in nw_first:
    g = r["group"]
    if g not in GROUPS:
        rep["far"].append(r); continue
    is_ne = is_ne_row(r)
    key = (mp(r["src"]), mp(r["dst"]))
    chains = cand_chains(r, g)
    if is_ne and key in done_rows and done_rows[key] is not None:
        nw_got = done_rows[key]
        lid = nw_got[0]["lane"] + "m"
        chain = [mp(x) for x in nw_got[0]["chain"]]
        hint = [[w["window_um"] for w in x["windows"]] for x in nw_got]
        sn = snap()
        got = None
        # same split count as NW
        k = len(nw_got)
        widths = [x["bits"] for x in nw_got]
        got = []
        for j, w in enumerate(widths):
            my = lid if j == 0 else f"{lid}s{j}"
            if my.endswith("m") is False:
                pass
            B.new_id = (lambda x: (lambda a_, b_, part=0: x))(nw_got[j]["lane"] + "m")
            HINT[:] = list(hint[j])
            r1 = B.build_one(r["src"], r["dst"], w, chain, "path", None, record=False)
            HINT[:] = []
            if r1 is None:
                got = None; break
            got.append(r1)
        why = None if got else f"NE mirror build failed: {B._why}"
        if got and set(chain) & SHARED:
            why = dedupe_shared(nw_got, got)
        elif got and [g_["cycles"] for g_ in got] != [g_["cycles"] for g_ in nw_got]:
            why = None   # non-shared NE mirror: own geometry allowed; cycles reported
        if why:
            restore(sn)
            # roll back the NW lane too if it put a declaration on a shared type
            if set(nw_got[0]["chain"]) & SHARED:
                ids_ = {x["lane"] for x in nw_got}
                T = B.raw["partition_types"]
                pt = {p["name"]: p["type"] for p in B.raw["partitions"]}
                for x in nw_got:
                    for part in x["chain"]:
                        t = T[pt[part]]
                        t["buses"] = [b_ for b_ in t.get("buses", []) if b_["name"] not in (x["lane"] + "_o", x["lane"] + "_i")]
                        t["ft_slots"] = [s_ for s_ in t.get("ft_slots", []) if not s_["name"].startswith(x["lane"] + "x")]
                lp = {q for l in B.raw["lanes"] if l["id"] in ids_ for q in l["ports"]}
                B.raw["ports"] = [p for p in B.raw["ports"] if p["id"] not in lp]
                B.raw["lanes"] = [l for l in B.raw["lanes"] if l["id"] not in ids_]
                for i_ in ids_:
                    B.raw["latency"]["lanes"].pop(i_, None)
                B.P = S.Plan(B.raw)
                rep["built"] = [x for x in rep["built"] if x["lane"] not in ids_]
                rep["failed"].append(dict(r=dict(src=key[0], dst=key[1]), why="rolled back with its NE mirror: " + why))
            rep["failed"].append(dict(r=r, why=why))
            continue
        for x in got:
            x["group"] = g
        rep["built"].extend(got)
        continue
    lid = f"L{nid}"; nid += 1
    while lid in existing_ids:
        lid = f"L{nid}"; nid += 1
    got = build(r, chains, lid)
    if got is None:
        rep["failed"].append(dict(r=r, why=B._why, chains=chains[:4]))
        done_rows[(r["src"], r["dst"])] = None
        continue
    for x in got:
        x["group"] = g
    rep["built"].extend(got)
    done_rows[(r["src"], r["dst"])] = got
    print(f"  built {r['src']}->{r['dst']} {r['bits']}b {g} lanes {[x['lane'] for x in got]} cyc {got[0]['cycles']} "
          f"chain {got[0]['chain']} {time.time()-t0:.0f}s", flush=True)

LA.copy = copy
out.mkdir(parents=True, exist_ok=True)
for f in plan_dir.iterdir():
    dst = out / f.name
    if f.name in ("die_plan.json", "v2_report.json") or dst.exists():
        continue
    try:
        os.link(f, dst) if f.is_file() else os.symlink(f.resolve(), dst)
    except OSError:
        pass
raw = B.raw
raw["die"]["label"] = "DIE-HBM-24 V2 root/spb1 ft | " + raw["die"].get("label", "")
raw["note"] = raw.get("note", "") + " | DIE-HBM-24 V2: far pairs laned through root/spb1/row ft slots (no partition move)"
(out / "die_plan.json").write_text(json.dumps(raw, indent=1))
rep["out_sha"] = LA.sha12(out / "die_plan.json")
bl = rep["built"]
rep["totals"] = dict(rows=len(rows), built_rows=len({(x["src"], x["dst"]) for x in bl}), built_lanes=len(bl),
                     built_bits=sum(x["bits"] for x in bl), failed=len(rep["failed"]), far_left=len(rep["far"]),
                     far_left_bits=sum(x["bits"] for x in rep["far"]),
                     by_group={g: sum(1 for x in bl if x["group"] == g) for g in sorted(GROUPS)})
rep["built_list"] = [dict(lane=x["lane"], src=x["src"], dst=x["dst"], bits=x["bits"], group=x["group"], cycles=x["cycles"],
                          stations=x["stations"], chain=x["chain"], macro_hits=x["macro_hits"]) for x in bl]
(out / "v2_report.json").write_text(json.dumps(rep, indent=1, default=str))
print(json.dumps(rep["totals"]), "OUT", rep["out_sha"], f"{time.time()-t0:.0f}s")
for x in rep["failed"]:
    print("FAILED", json.dumps(x, default=str)[:400])
