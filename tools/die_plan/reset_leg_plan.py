#!/usr/bin/env python3
"""RESET-RELAY-GEN-1530 (FABLE-CLOSURE-1515 lever 1, die-agnostic): reset / start legs of one bound type as a PLAN DELTA,
from the bound module and a placed geometry dump of the newest kit of that type (geom_dump.tcl, AUTO-GEOM format).

Rule: every reset sink has a position, and the leg into it is a hop (<= --reach, default 300 um, the hop cap).  The
reset tree (reset_tree.py) already bounds relay-to-relay hops; the legs it does not see are:

  form R  a soft sub-instance (or bank) of the bound module takes its reset from the leaf alias `rst_n` (= the one tap
          rst_n_t<c> nearest the outline centre) or from a far tap, so the last leg tap -> its placed flops spans the
          type (QC A4 cbx/cbn/cbf u_rrl_* -> u_u_fab_u_x_*.u_st.g_seg counters, 17-36 buffers; KV pv u_rrl_417 -> banks).
          Fix: reset.inst_taps {tap, sinks, port}: the instance port moves to the existing equal-depth tap with the
          smallest worst leg to that instance's placed reset sinks.  Every tap releases on the same cycle: 0 cycles,
          0 flops (reset_port_relays.apply_inst_taps at bind and kit-rtl).  If no tap is within --reach the instance is
          listed under needs_local_tap with its sink centre (reset.local_taps_um, applied with --local-taps; a new tap
          is a tree terminal of the same depth K, so still 0 release cycles, but it needs a re-bind).
  form L  a module-local relay (ot_rst_relay u_rstr / u_rr, g_rsreg, rst_q ...) is in no tree row and has no site, so GPL
          drops it at either end of its two legs (S81 lepe u_u_land.u_rstr at (1430.9, 8.1), 1,300 um from land; leaf
          u_vp.u_rr).  Fix: (a) its flops are seated FIRM at the L1 centre of their fanout (plan relay_sites, kit_istations
          RELAY_TCL); (b) when it is fed by a signal register (not the tree) and the leg source -> centre is over --reach,
          a sink-side relay_depth row {inst, port, side sink, D = ceil(L / reach) - 1} adds D equal-pitch stages on that
          port (KIT-RD-1, D DECLARED cycles; reset release only: rst_n is held >= 64 clocks, owner 10-29); relay_mid.tcl
          spreads u_y_xd_* stages between their now fixed ends (--stage-sites seats them on the line instead).  A
          replicated relay (REGIONS copies) seats each copy at its own fanout, the synchroniser at the copies' centre.  When the relay is tree fed, form R moves its instance to the tap
          nearest the seated relay instead (0 cycles).
  split   a group whose own fanout radius is over --reach cannot close from one point: listed (REGIONS / split by
          quadrant is the fix, not done here).

  python3 -I reset_leg_plan.py PLAN TYPE BOUND_SV GEOM OUT_PLAN REPORT.json [--reach 300] [--local-taps]
          [--stage-sites [--stage-key FMT]] [--no-sites]

Positions are the PLACED ones of GEOM (the newest placed kit of the type); the bound module is the one that kit was
built from (its rtl/<type>_bound.sv).  The plan delta is opt-in per type and additive; every other plan byte is kept.
Nothing is a gate: the report lists every leg over --reach before and after.  PRECHECK may read report.legs_over.
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import reset_consumers as RC  # noqa: E402
import reset_port_relays as PR  # noqa: E402

REACH_UM = 300.0
MAX_D = 4                         # schema relay_depth.D maximum
LOCAL = re.compile(r"^(?P<g>(?:.*?[./])?(?:u_rstr|u_rr|u_rst_relay\w*|u_rrelay\w*|g_rsreg(?:\[\d+\])?|rst_q))(?=[./\[$]|$)")
TREE_CELL = re.compile(r"^(?:u_rrl_\d+|u_srl_\d+|u_rst_root|u_rst_in|u_rsync_t\d+|u_cland_reset\w*)(?:[./_]|$)")
# kit-rtl stage flop name (kit_relay_depth.apply: wire {base}_s{s}_q, base u_y_xd_<sid>_<port>_k<row>)
STAGE_KEY = "u_y_xd_{sid}_{port}_k{k}_s{s}_q"


class LegError(ValueError):
    pass


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def centre(pts):
    """L1 minimax centre (minimises the worst leg to the points)"""
    us = [p[0] + p[1] for p in pts]
    vs = [p[0] - p[1] for p in pts]
    u, v = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
    return ((u + v) / 2, (u - v) / 2)


def sv_id(s):
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s if s and not s[0].isdigit() else "n" + s


def key(nm):
    """plan relay_sites key of a dump cell name: bound prefix and Yosys cell suffix dropped"""
    return re.sub(r"^u_bound[./]", "", re.sub(r"\$_[A-Za-z0-9_]*$", "", nm.replace("\\", "")))


def top_inst(k):
    return re.split(r"[./]", k, maxsplit=1)[0]


class Geo:
    """placed netlist view: reset fanout / launch tracing through buffers and inverters only"""

    def __init__(self, D):
        self.D = D
        self.name = {c: key(v[6]) for c, v in D.cells.items()}
        self.kind = {c: v[0] for c, v in D.cells.items()}

    def xy(self, c):
        v = self.D.cells[c]
        return ((v[2] + v[4]) / 2, (v[3] + v[5]) / 2)

    def fanout(self, cells):
        """sequential / macro cells (and top pins) whose data or reset input is driven by `cells` through BUF/INV only"""
        out, seen, front = set(), set(cells), list(cells)
        while front:
            nf = []
            for u in front:
                for n in self.D.drives.get(u, []):
                    for s in self.D.nets[n][2]:
                        if s[0] == "p" or s[2]:
                            continue
                        c = s[1]
                        if c in seen:
                            continue
                        seen.add(c)
                        k = self.kind.get(c)
                        if k in ("S", "M"):
                            out.add(c)
                        elif k == "B":
                            nf.append(c)
            front = nf
        return out

    def sources(self, cells):
        """launch cells / pins feeding `cells` from outside the set, through BUF/INV only"""
        out, seen, front = set(), set(cells), list(cells)
        while front:
            nf = []
            for u in front:
                for n, is_clk in self.D.cell_in.get(u, []):
                    if is_clk:
                        continue
                    d = self.D.nets[n][1]
                    if d is None:
                        continue
                    if d[0] == "p":
                        out.add(("p", d[1]))
                        continue
                    c = d[1]
                    if c in seen:
                        continue
                    seen.add(c)
                    k = self.kind.get(c)
                    if k in ("S", "M"):
                        out.add(("i", c))
                    elif k == "B":
                        nf.append(c)
            front = nf
        return out

    def pxy(self, r):
        if r[0] == "p":
            p = self.D.pin_by_k[r[1]]
            return (float(p["x"]), float(p["y"]))
        return self.xy(r[1])


def tap_cells(G, sv):
    """{tap index: dump cell id of the relay flop driving rst_n_t<i>} from the bound module's tree instances"""
    by_name = defaultdict(list)
    for c, nm in G.name.items():
        if G.kind[c] == "S":
            by_name[top_inst(nm)].append(c)
    out = {}
    for inst, c in RC._calls(sv).items():
        q = c["ports"].get("q", (None,))[0]
        m = re.fullmatch(r"rst_n_t(\d+)", q or "")
        if m and by_name.get(inst):
            out[int(m.group(1))] = by_name[inst][0]
    return out


def consumers(sv):
    """{(inst, port): tree net} for every emitted non-tree instance input on a generated-tree reset net"""
    out = {}
    for inst, c in RC._calls(sv).items():
        if c["module"].startswith(PR.TREE_CELLS):
            continue
        for port, (expr, _lo, _hi) in c["ports"].items():
            if port in ("q", "rst_o") or not PR.TREE_NET.match(expr):
                continue
            out[(inst, port)] = expr
    return out


def local_groups(G):
    """{group key: [cell ids]} of module-local relay flops (not the kit tree)"""
    gs = defaultdict(list)
    for c, nm in G.name.items():
        if G.kind[c] != "S" or TREE_CELL.match(nm):
            continue
        m = LOCAL.match(nm)
        if m and re.search(r"[./]", m.group("g")):
            gs[m.group("g")].append(c)
    return dict(gs)


def port_into(sv, inst, G, src_cells):
    """the port of bound instance `inst` that carries the group's input: the one whose connection wire drives toward the
    source, else the only reset-named port that is not a tree net"""
    c = RC._calls(sv).get(inst)
    if c is None:
        return None
    cand = [p for p, (e, _a, _b) in c["ports"].items() if re.search(r"rst|reset", p) and not PR.TREE_NET.match(e)]
    if len(cand) == 1:
        return cand[0]
    nets = {G.D.nets[n][0].replace("\\", "") for s in src_cells for n in G.D.drives.get(s, [])}
    hit = [p for p in cand if any(re.sub(r"^u_bound[./]", "", n) == c["ports"][p][0].replace(" ", "") for n in nets)]
    return hit[0] if len(hit) == 1 else None


def type_delta(tn, t, sv, D, reach=REACH_UM, local_taps=False, sites=True, stage_key=STAGE_KEY, stage_sites=False):
    """mutates plan type dict t; -> report"""
    G = Geo(D)
    rep = dict(type=tn, reach_um=reach, inst_taps=[], local=[], relay_depth=[], needs_local_tap=[], split=[],
               legs_over_before=0, legs_over_after=0)
    seated = {}                                      # cell id -> new xy (form L seats)
    rs_sites = {}
    rd_rows = list(t.get("relay_depth") or [])
    # ---- form L: module-local relays.  Each relay flop that drives sinks outside the group (a REGIONS copy, or the one
    # last stage) is seated at the L1 centre of ITS OWN fanout; the inner stages (synchroniser) at the centre of the
    # copies they feed.  A flop whose own leg is already <= reach keeps its placement.
    for g, cells in sorted(local_groups(G).items()):
        cs = set(cells)
        own = {c: G.fanout([c]) - cs for c in cells}
        fan = set().union(*own.values())
        if not fan:
            continue
        fp = [G.xy(c) for c in fan]
        C = centre(fp)
        here = centre([G.xy(c) for c in cells])
        srcs = G.sources(cells)
        tree_fed = any(r[0] == "i" and TREE_CELL.match(G.name[r[1]]) for r in srcs)
        sp = [G.pxy(r) for r in srcs]
        S = centre(sp) if sp else None
        leg = {c: max(l1(G.xy(c), G.xy(f)) for f in own[c]) for c in cells if own[c]}
        out_now = max(leg.values())
        inner = [c for c in cells if not own[c]]
        in_now = max((l1(G.xy(c), p) for c in (inner or cells) for p in sp), default=0.0)
        new, rad = {}, {}
        for c, L in leg.items():
            fc = [G.xy(f) for f in own[c]]
            cc = centre(fc)
            rad[c] = max(l1(cc, p) for p in fc)
            if L > reach:
                new[c] = cc
        # a single-copy relay moves whole (its synchroniser goes with the last stage, the input leg is then staged); a
        # replicated relay (REGIONS / tree copies) moves only its copies: its inner stages are a tree of their own
        single = len(leg) == 1
        if single and inner and (new or in_now > reach):
            Ci = centre([new.get(c, G.xy(c)) for c in leg])
            for c in inner:
                new[c] = Ci
        radius = max(rad.values())
        e = dict(group=g, flops=len(cells), copies=len(leg), fanout=len(fan), at=[round(v, 1) for v in here],
                 centre=[round(v, 1) for v in C], copy_radius_um=round(radius, 1), out_leg_um=round(out_now, 1),
                 in_leg_um=round(in_now, 1), tree_fed=tree_fed, source=[round(v, 1) for v in S] if S else None)
        rep["legs_over_before"] += (out_now > reach) + (in_now > reach)
        if radius > reach:
            rep["split"].append(dict(group=g, copy_radius_um=round(radius, 1), copies=len(leg), fanout=len(fan)))
        if not new:
            continue
        for c, xy in new.items():
            seated[c] = xy
            if sites:
                rs_sites[G.name[c]] = [round(xy[0], 3), round(xy[1], 3)]
        entry = [new.get(c, G.xy(c)) for c in (inner or list(leg))]
        in_after = max((l1(q, p) for q in entry for p in sp), default=0.0)
        if single and not tree_fed and S is not None and in_after > reach:
            inst = top_inst(g)
            port = port_into(sv, inst, G, [r[1] for r in srcs if r[0] == "i"])
            Dn = math.ceil(in_after / reach - 1e-9) - 1
            if port is None:
                e["relay_depth"] = "unresolved port"
            else:
                k = len(rd_rows)
                row = dict(inst=inst, port=port, side="sink", D=min(Dn, MAX_D), path_um=round(in_after, 1),
                           note=f"RESET-RELAY-GEN-1530 form L: {g} fed from {e['source']}, seated at its fanout")
                rd_rows.append(row)
                rep["relay_depth"].append(dict(row, over_cap=Dn > MAX_D))
                if stage_sites:
                    T = centre(entry)
                    for s_ in range(row["D"]):
                        f = (s_ + 1) / (row["D"] + 1)
                        p = (S[0] + (T[0] - S[0]) * f, S[1] + (T[1] - S[1]) * f)
                        rs_sites[stage_key.format(sid=sv_id(inst), port=port, k=k, s=s_)] = [round(p[0], 3), round(p[1], 3)]
                in_after = in_after / (row["D"] + 1)
        out_after = max(l1(new.get(c, G.xy(c)), G.xy(f)) for c in leg for f in own[c])
        e.update(seated=len(new), in_leg_after_um=round(in_after, 1), out_leg_after_um=round(out_after, 1))
        rep["legs_over_after"] += (out_after > reach) + (in_after > reach and not tree_fed)
        e["form"] = "single" if single else "replicated (copies only)"
        rep["local"].append(e)
    # ---- form R: tree-fed instances / banks
    taps = tap_cells(G, sv)
    txy = {i: G.xy(c) for i, c in taps.items()}
    leaf = PR.LEAF.findall(sv)
    cons = consumers(sv)
    if txy and len(leaf) == 1 and cons:
        by_inst = defaultdict(list)
        for (inst, port), net in cons.items():
            by_inst[inst].append((port, net))
        sinks_of = defaultdict(set)                  # inst -> placed reset sink cells reached from any tap
        on_tap = {}                                  # sink cell -> the tap that drives it in the PLACED netlist
        for i, c in sorted(taps.items()):
            for s in G.fanout([c]):
                ti = top_inst(G.name[s])
                if ti in by_inst:
                    sinks_of[ti].add(s)
                    on_tap.setdefault(s, i)
        rows = defaultdict(list)
        lt = list((t.get("reset") or {}).get("local_taps_um") or [])
        for inst in sorted(by_inst):
            ss = sorted(sinks_of.get(inst, ()))
            pts = [seated.get(s) or G.xy(s) for s in ss]
            if not pts:
                continue
            for port, net in by_inst[inst]:
                m = PR.TREE_NET.match(net)
                cur = int(m.group(1)) if m.group(1) is not None else int(leaf[0])
                if cur not in txy:
                    continue
                # the leg as placed: from the tap each sink really hangs on (reset_taps.tcl re-points FIRM flops itself)
                now = max(l1(txy[on_tap.get(s, cur)], p) for s, p in zip(ss, pts))
                if now <= reach:
                    continue
                rep["legs_over_before"] += 1
                best = min(txy, key=lambda i: (max(l1(txy[i], p) for p in pts), i))
                after = max(l1(txy[best], p) for p in pts)
                e = dict(inst=inst, port=port, sinks=len(pts), tap_rtl=cur,
                         tap_was=sorted({on_tap.get(s, cur) for s in ss}), leg_was_um=round(now, 1), tap=best,
                         leg_um=round(after, 1))
                if after > reach:
                    C = centre(pts)
                    e["centre"] = [round(C[0], 1), round(C[1], 1)]
                    rep["needs_local_tap"].append(e)
                    if local_taps and [round(C[0], 3), round(C[1], 3)] not in lt:
                        lt.append([round(C[0], 3), round(C[1], 3)])
                if best != cur and after < now:
                    rows[(best, port)].append(inst)
                    rep["inst_taps"].append(e)
                rep["legs_over_after"] += min(after, now) > reach
        if rows:
            have = list((t.get("reset") or {}).get("inst_taps") or [])
            taken = {(s, r.get("port", "rst_n")) for r in have for s in r["sinks"]}
            for (tap, port), ss in sorted(rows.items()):
                ss = [s for s in ss if (s, port) not in taken]
                if ss:
                    r = dict(tap=tap, sinks=ss)
                    if port != "rst_n":
                        r["port"] = port
                    have.append(r)
            t.setdefault("reset", {})["inst_taps"] = have
        if local_taps and lt != list((t.get("reset") or {}).get("local_taps_um") or []):
            t.setdefault("reset", {})["local_taps_um"] = lt
    elif cons:
        rep["form_r_skipped"] = "no generated reset-tree leaf alias / no placed tap relay found"
    if rd_rows != list(t.get("relay_depth") or []):
        t["relay_depth"] = rd_rows
    if rs_sites:
        merged = dict(t.get("relay_sites") or {})
        merged.update(rs_sites)
        t["relay_sites"] = dict(sorted(merged.items()))
    rep["relay_sites"] = len(rs_sites)
    rep["added_reset_cycles"] = max((r["D"] for r in rep["relay_depth"]), default=0)
    return rep


def dumper(rb, raw):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, indent=1), lambda p: json.dumps(p, indent=2),
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(raw).encode() == rb:
            return f
    return lambda p: json.dumps(p, indent=1, ensure_ascii=False) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("plan", "type", "bound_sv", "geom", "out_plan", "report"):
        ap.add_argument(a)
    ap.add_argument("--reach", type=float, default=REACH_UM)
    ap.add_argument("--local-taps", action="store_true", help="also write reset.local_taps_um for instances no tap reaches")
    ap.add_argument("--no-sites", action="store_true", help="no relay_sites rows (rows only)")
    ap.add_argument("--stage-key", default=STAGE_KEY)
    ap.add_argument("--stage-sites", action="store_true",
                    help="also site the relay_depth stages on the source -> relay line (default: relay_mid.tcl spreads u_y_xd_* "
                         "stages between their fixed ends)")
    a = ap.parse_args(argv)
    import geom_rules
    rb = Path(a.plan).read_bytes()
    raw = json.loads(rb)
    t = raw["partition_types"][a.type]
    rep = type_delta(a.type, t, Path(a.bound_sv).read_text(), geom_rules.Design(a.geom), a.reach, a.local_taps,
                     not a.no_sites, a.stage_key, a.stage_sites)
    Path(a.out_plan).write_text(dumper(rb, raw)(raw))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"{a.type}: legs over {a.reach:g} um {rep['legs_over_before']} -> {rep['legs_over_after']}; inst_taps "
          f"{len(rep['inst_taps'])}, local relays seated {len(rep['local'])}, relay_depth rows {len(rep['relay_depth'])} "
          f"(+{rep['added_reset_cycles']} reset cycles), needs_local_tap {len(rep['needs_local_tap'])}, split {len(rep['split'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
