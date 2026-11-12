#!/usr/bin/env python3
"""QC-S28-VISFORM (11-12): the QC visual classes as family forms on the HF-1c plan (one re-appliable delta).

    python3 -I visform.py derive PLAN.json SIDE.json DELTA.json [--repo REPO] [--sc-x 302.4] [--report R.json]
    python3 -I visform.py apply  PLAN.json DELTA.json OUT.json [--report R.json]

derive builds the delta from the frozen base; apply re-applies it on any plan whose touched values still equal the
base values (from-value sha check per op; CONFLICT exit 3, nothing written).  Delta ops:
  {"cls": class, "path": [plan keys...], "from_sha": sha256(canonical old value) | "ABSENT", "to": new | "<DELETE>"}

Classes (types are selected by family regex, never by name):
  SC-ECHAN     (^(sle|slw)_sc_)  u_core moves W to x = --sc-x (move only, same orient/shape): the E sliver
               (23.28 um) becomes a full E channel (66.48 um at 302.4) for the 90 core E pins, the E-face buses and the
               x_su_l1_ctl S->N ft lane that runs at x 594-607.  Derived with the move: the core clock tap xy (= ck pin)
               and collector_tree.core_resets pin_um / xy; every ft station (reg + its bit sites) that the NEW core
               footprint (+2.16 um halo) covers and the old one did not is shifted W by the same dx, so it keeps its
               clearance to the core W edge.  Collector / START / local-reset windows are re-cleared by the generator
               (landing_place._clear_of_hard_cores / _collector_window); reset_tree relays are re-built at bind
               (reset_anchor remap by site); neither is edited here.
  FW-EFACE     (^(sle|slw)_(fw|st_a)_)  budgets.face_flop_ew_types[family] = {cpitch_sites 80, row_stride 3}: the E/W face
               pin registers take a staggered comb band ~20 um deep (face_flops.tcl OT_FF_EW_CPITCH_SITES / OT_FF_EW_ROW_STRIDE)
               instead of the fixed 40-site (2.16 um) column pitch with +-2 rows.
  CTL-RING     (^sle_ctl_)  budgets.cland_strip_density_types[sle_ctl] = 1.0 and cland_strip_rows_types[sle_ctl] = 2
               (the LAND-RING-2 lr2 ring form proven GOOD on sle_ctl__cla4f6f12f and __cl372cea1c) as ONE family key;
               the per-type copies are removed.
  LAND-OVR     (all types)  landing_contract.group_rects_um entries naming a collector node that is on no active
               collector path of the type (landing_place.collector_nodes) are dropped: the stale-copy class of the
               sle_ctl__cl372cea1c gen fail (u_cland_collect_rst_n_t19); GEN-CLASS-1 drops the same set at gen.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

DELETE = "<DELETE>"
ABSENT = "ABSENT"
HALO = 2.16
SC_RE = re.compile(r"^(sle|slw)_sc_")
FW_RE = re.compile(r"^(sle|slw)_(fw|st_a)_")
CTL_RE = re.compile(r"^sle_ctl_")
FW_BASES = ("sle_fw", "slw_fw", "sle_st_a", "slw_st_a")
FW_FORM = {"cpitch_sites": 80, "row_stride": 3}


def sha(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def get(o, path):
    for k in path:
        o = o[k]
    return o


def has(o, path):
    try:
        get(o, path)
        return True
    except (KeyError, IndexError, TypeError):
        return False


def op(ops, cls, plan, path, to):
    old = get(plan, path) if has(plan, path) else None
    ops.append(dict(cls=cls, path=list(path), from_sha=sha(old) if has(plan, path) else ABSENT, to=to))


def rect_of(hc, x=None):
    (ox, oy), (w, h) = hc["origin_um"], hc["outline_um"]
    if hc.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    dx, dy = hc.get("track_offset_um", [0.0, 0.0])
    x0 = (ox if x is None else x) + dx
    return (x0, oy + dy, x0 + w, oy + dy + h)


def inside(pt, r, m=HALO):
    return r[0] - m <= pt[0] <= r[2] + m and r[1] - m <= pt[1] <= r[3] + m


def sc_echan(plan, ops, rep, X):
    grid = plan["die"]["grid_um"]
    if abs(X / grid - round(X / grid)) > 1e-9:
        raise SystemExit(f"--sc-x {X} not on the {grid}-um lattice")
    for tn, t in sorted(plan["partition_types"].items()):
        if not SC_RE.match(tn):
            continue
        P = ["partition_types", tn]
        cores = [i for i, h in enumerate(t.get("hard_cores") or []) if h.get("inst") == "u_core"]
        if len(cores) != 1:
            raise SystemExit(f"{tn}: expected one u_core hard core")
        ci = cores[0]
        hc = t["hard_cores"][ci]
        ox = hc["origin_um"][0]
        d = round(X - ox, 6)
        old, new = rect_of(hc), rect_of(hc, X)
        r = dict(core_x=[ox, X], dx=d, e_gap_um=[round(t["outline_um"][0] - old[2], 3), round(t["outline_um"][0] - new[2], 3)],
                 w_gap_um=[round(old[0], 3), round(new[0], 3)], moved_stations=[], tap=None, core_reset=None)
        op(ops, "SC-ECHAN", plan, P + ["hard_cores", ci, "origin_um"], [X, hc["origin_um"][1]])
        ck = t.get("clock") or {}
        for i, tp in enumerate(ck.get("taps") or []):
            if tp.get("kind") == "core" and tp.get("name", "").startswith("u_core."):
                xy = [round(tp["xy"][0] + d, 6), tp["xy"][1]]
                op(ops, "SC-ECHAN", plan, P + ["clock", "taps", i, "xy"], xy)
                r["tap"] = [tp["xy"], xy]
            elif inside(tp["xy"], new) and tp["xy"][0] < old[0] + HALO:
                # a glue tap the new footprint covers (glue_01 at x 311.04): same dx, its clock route grows by |dx|
                op(ops, "SC-ECHAN", plan, P + ["clock", "taps", i, "xy"], [round(tp["xy"][0] + d, 6), tp["xy"][1]])
                if "from_root_um" in tp:
                    op(ops, "SC-ECHAN", plan, P + ["clock", "taps", i, "from_root_um"], round(tp["from_root_um"] + abs(d), 1))
                r.setdefault("glue_taps", []).append([tp["name"], tp["xy"], [round(tp["xy"][0] + d, 6), tp["xy"][1]]])
        lc = ck.get("landing_contract") or {}
        for k, g in sorted((lc.get("group_rects_um") or {}).items()):
            ov = lambda R: g[0] < R[2] + HALO and g[2] > R[0] - HALO and g[1] < R[3] + HALO and g[3] > R[1] - HALO
            if ov(new) and (g[0] + g[2]) / 2 < old[0] + HALO:
                # an explicit landing-group rectangle at the old core W edge that the new footprint covers: same dx
                # (overrides are not re-cleared at gen)
                op(ops, "SC-ECHAN", plan, P + ["clock", "landing_contract", "group_rects_um", k],
                   [round(g[0] + d, 6), g[1], round(g[2] + d, 6), g[3]])
                r.setdefault("group_rects", []).append([k, g])
        ct = ((ck.get("landing_contract") or {}).get("collector_tree") or {})
        for i, cr in enumerate(ct.get("core_resets") or []):
            if cr.get("inst") != "u_core":
                continue
            base = P + ["clock", "landing_contract", "collector_tree", "core_resets", i]
            op(ops, "SC-ECHAN", plan, base + ["pin_um"], [round(cr["pin_um"][0] + d, 6), cr["pin_um"][1]])
            if inside(cr["xy"], new) and not inside(cr["xy"], old):
                op(ops, "SC-ECHAN", plan, base + ["xy"], [round(cr["xy"][0] + d, 6), cr["xy"][1]])
            r["core_reset"] = dict(pin=[cr["pin_um"][0], cr["pin_um"][0] + d], xy=cr["xy"])
        moves = []
        for si, s in enumerate(t.get("ft_slots") or []):
            regs, bits = s.get("regs_um") or [], s.get("bit_sites_um") or []
            for j in range(1, len(regs)):
                bs = bits[j - 1] if j - 1 < len(bits) else []
                pts = [regs[j]] + bs
                hit = [p for p in pts if inside(p, new)]
                if not hit:
                    continue
                if regs[j][0] >= old[0] + HALO:
                    # an E-side / in-core station is not a W-edge station: report, never drag it across the core
                    r.setdefault("not_moved", []).append(dict(slot=s["name"], station=j, reg=regs[j], covered=len(hit),
                                                              covered_by_old=sum(1 for p in hit if inside(p, old))))
                    continue
                # W-edge station: shift W by the core dx, or more (2.16-um steps) when some of its bits reach further E
                band = [p for p in pts if new[1] - HALO <= p[1] <= new[3] + HALO]
                need = max(p[0] for p in band) - (new[0] - HALO - 0.01) if band else 0.0
                ds = min(d, -2.16 * math.ceil(round(need / 2.16, 6)))
                moves.append((si, j, ds))
        # legalize the shifted bit sites: a shifted bit that lands on a fixed (unmoved) or already re-sited bit cell, or
        # under the new footprint, takes the nearest free lattice site (x step 2.16 W first, y step 0.27)
        moved = {(si, j) for si, j, _ in moves}
        occ = Occ()
        for si, s in enumerate(t.get("ft_slots") or []):
            for jj, bs in enumerate(s.get("bit_sites_um") or []):
                if (si, jj + 1) not in moved:
                    for b in bs:
                        occ.add(b)
        for si, j, ds in moves:
            s = t["ft_slots"][si]
            regs, bs = s["regs_um"], (s.get("bit_sites_um") or [])[j - 1] if j - 1 < len(s.get("bit_sites_um") or []) else []
            out, resited, far = [], 0, 0.0
            for a, b in bs:
                p = [round(a + ds, 6), b]
                if occ.hit(p) or inside(p, new):
                    q = occ.nearest(p, lambda c: not inside(c, new))
                    resited += 1
                    far = max(far, abs(q[0] - p[0]) + abs(q[1] - p[1]))
                    p = q
                occ.add(p)
                out.append(p)
            op(ops, "SC-ECHAN", plan, P + ["ft_slots", si, "regs_um", j], [round(regs[j][0] + ds, 6), regs[j][1]])
            if bs:
                op(ops, "SC-ECHAN", plan, P + ["ft_slots", si, "bit_sites_um", j - 1], out)
            r["moved_stations"].append(dict(slot=s["name"], station=j, dx=round(ds, 3),
                                            reg=[regs[j], [round(regs[j][0] + ds, 3), regs[j][1]]], bits=len(bs),
                                            resited_bits=resited, resite_max_um=round(far, 3),
                                            still_covered=sum(1 for p in out if inside(p, new))))
        rep["SC-ECHAN"][tn] = r


class Occ:
    """bit-site cells (1.404 x 0.27 um at the site point) on a hash grid"""
    CW, CH = 1.404, 0.27

    def __init__(self):
        self.g = {}

    def _k(self, p):
        return (int(p[0] // 2.0), int(p[1] // 1.0))

    def add(self, p):
        self.g.setdefault(self._k(p), []).append((p[0], p[1]))

    def hit(self, p):
        kx, ky = self._k(p)
        for ax in (kx - 1, kx, kx + 1):
            for ay in (ky - 1, ky, ky + 1):
                for x, y in self.g.get((ax, ay), ()):
                    if abs(x - p[0]) < self.CW - 1e-6 and abs(y - p[1]) < self.CH - 1e-6:
                        return True
        return False

    def nearest(self, p, ok, rx=12, ry=24):
        # i > 0 = W of p; equal distance prefers W, then the smaller |dy|
        cand = sorted(((abs(i) * 2.16 + abs(m) * 0.27, -i, abs(m), m, i) for i in range(-rx, rx + 1) for m in range(-ry, ry + 1)))
        for *_, m, i in cand:
            q = [round(p[0] - i * 2.16, 6), round(p[1] + m * 0.27, 6)]
            if ok(q) and not self.hit(q):
                return q
        raise SystemExit(f"no free bit site within {rx * 2.16} x {ry * 0.27} um of {p}")


def fw_eface(plan, ops, rep):
    b = plan["budgets"]
    cur = b.get("face_flop_ew_types")
    to = dict(cur or {})
    for base in FW_BASES:
        to[base] = dict(FW_FORM)
    op(ops, "FW-EFACE", plan, ["budgets", "face_flop_ew_types"], to)
    rep["FW-EFACE"] = dict(key="budgets.face_flop_ew_types", value=to,
                           types=sorted(tn for tn in plan["partition_types"] if FW_RE.match(tn)))


def ctl_ring(plan, ops, rep):
    b = plan["budgets"]
    types = sorted(tn for tn in plan["partition_types"] if CTL_RE.match(tn))
    dens = dict(b.get("cland_strip_density_types") or {})
    rows = dict(b.get("cland_strip_rows_types") or {})
    before = {tn: dict(dens=dens.get(tn, dens.get(tn.split("__")[0], b.get("cland_strip_density"))),
                       rows=rows.get(tn, rows.get(tn.split("__")[0]))) for tn in types}
    for tn in types:
        dens.pop(tn, None)
        rows.pop(tn, None)
    dens["sle_ctl"] = 1.0
    rows["sle_ctl"] = 2
    op(ops, "CTL-RING", plan, ["budgets", "cland_strip_density_types"], dens)
    op(ops, "CTL-RING", plan, ["budgets", "cland_strip_rows_types"], rows)
    rep["CTL-RING"] = dict(types=types, before=before, after={tn: dict(dens=1.0, rows=2) for tn in types})


def land_ovr(plan, side, ops, rep, repo):
    sys.path.insert(0, str(Path(repo) / "tools" / "die_plan"))
    import landing_place as LP
    ct = (side.get("collector") or {}).get("types") or {}
    for tn, t in sorted(plan["partition_types"].items()):
        c = (t.get("clock") or {}).get("landing_contract") or {}
        g = c.get("group_rects_um")
        if not g:
            continue
        ev = LP.collector_event(c)
        try:
            act, xy = LP.collector_nodes(ev)
        except KeyError as e:
            rep["LAND-OVR"][tn] = dict(error=f"plan collector tree: {e}")
            continue
        known = {"u_cland_collect_" + LP.safe(n) for n in act}
        known |= {"u_cland_reset_" + LP.safe(n) for n in act if n != "rst_root_n"}
        known |= {"u_cland_rst_" + s["name"] for s in ev.get("local_sources", [])}
        nodes = {"u_cland_collect_" + LP.safe(r["q"]) for r in (ev.get("tree") or {}).get("relays", [])}
        stale = sorted(k for k in g if k not in known)
        if not stale:
            continue
        # side-car event cross-check (the tree gen may install): stale there too, or the side car has no event
        info = ct.get(tn)
        side_stale = None
        if info and (info.get("mask") or {}).get("active"):
            try:
                sact, _ = LP.collector_nodes(dict(tree=info["tree"], collector_root_node=info.get("collector_root_node", "rst_root_n"),
                                                  local_sources=info["local_sources"], children=info["children"]))
                sk = {"u_cland_collect_" + LP.safe(n) for n in sact} | {"u_cland_reset_" + LP.safe(n) for n in sact}
                sk |= {"u_cland_rst_" + s["name"] for s in info["local_sources"]}
                side_stale = sorted(k for k in g if k not in sk)
            except KeyError:
                side_stale = "side tree incomplete"
        to = {k: v for k, v in g.items() if k not in stale}
        for k in stale:   # one op per dropped key (an empty object is the no-override form)
            op(ops, "LAND-OVR", plan, ["partition_types", tn, "clock", "landing_contract", "group_rects_um", k], DELETE)
        rep["LAND-OVR"][tn] = dict(dropped={k: g[k] for k in stale}, kept=sorted(to),
                                   in_tree_inactive=[k for k in stale if k in nodes], not_in_tree=[k for k in stale if k not in nodes],
                                   side_stale=side_stale)


def derive(a):
    plan = json.loads(Path(a.plan).read_text())
    side = json.loads(Path(a.side).read_text())
    ops, rep = [], {"SC-ECHAN": {}, "LAND-OVR": {}}
    cls = set(a.classes.split(","))
    if "SC-ECHAN" in cls:
        sc_echan(plan, ops, rep, a.sc_x)
    if "FW-EFACE" in cls:
        fw_eface(plan, ops, rep)
    if "CTL-RING" in cls:
        ctl_ring(plan, ops, rep)
    if "LAND-OVR" in cls:
        land_ovr(plan, side, ops, rep, a.repo)
    delta = dict(schema="qc_s28_visform.delta.v1", base_sha=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
                 note="QC-S28-VISFORM 11-12 family forms: " + a.classes, ops=ops)
    Path(a.delta).write_text(json.dumps(delta, indent=1) + "\n")
    counts = {}
    for o in ops:
        counts[o["cls"]] = counts.get(o["cls"], 0) + 1
    rep["ops"] = counts
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(counts))


def apply_ops(plan, delta):
    plan = copy.deepcopy(plan)
    bad = []
    for o in delta["ops"]:
        p = o["path"]
        cur = sha(get(plan, p)) if has(plan, p) else ABSENT
        if cur != o["from_sha"]:
            bad.append(p)
    if bad:
        return None, bad
    for o in delta["ops"]:
        par = get(plan, o["path"][:-1])
        if o["to"] == DELETE:
            del par[o["path"][-1]]
        else:
            par[o["path"][-1]] = copy.deepcopy(o["to"])
    return plan, []


def apply(a):
    plan = json.loads(Path(a.plan).read_text())
    delta = json.loads(Path(a.delta).read_text())
    out, bad = apply_ops(plan, delta)
    rep = dict(plan=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(), ops=len(delta["ops"]), conflicts=bad)
    if bad:
        print("CONFLICT", len(bad), "ops; first", bad[:3])
        if a.report:
            Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
        sys.exit(3)
    if "note" in out:
        out["note"] = "QC-S28-VISFORM 11-12: sc E channel, fw/st_a E-face band, ctl ring family key, stale landing " \
                      "overrides <- " + out["note"]
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    rep["out"] = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print("APPLIED", len(delta["ops"]), "ops ->", rep["out"][:12])


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    d = sp.add_parser("derive")
    d.add_argument("plan"); d.add_argument("side"); d.add_argument("delta")
    d.add_argument("--repo", default=".")
    d.add_argument("--sc-x", type=float, default=302.4)
    d.add_argument("--report")
    d.add_argument("--classes", default="SC-ECHAN,FW-EFACE,CTL-RING,LAND-OVR",
                   help="comma list; SC-ECHAN ships as its own delta until its crossing lanes are re-stationed")
    x = sp.add_parser("apply")
    x.add_argument("plan"); x.add_argument("delta"); x.add_argument("out")
    x.add_argument("--report")
    a = ap.parse_args(argv)
    (derive if a.cmd == "derive" else apply)(a)


if __name__ == "__main__":
    main()
