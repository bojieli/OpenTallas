"""INFRA-FIRST-QC-R28 (COORD ruling 2026-10-27 11:08, OPTION A): cut the die VSS M8/M9 stripes under every
clock-mesh strap, keep the PG phase (offset 4.32), and check that the cut grid stays one connected VSS net.

Why: the QC continuous mesh (qc_clk_mesh3 / R22 convention) puts every M8/M9 strap ON a VSS lane (y or x = 0 mod
8.64); at offset 4.32 all 3,299 strap segments short to the VSS stripe under them (R27 census).  The strap's drawn
shields are VSS, so the strap lane is still a VSS-shielded lane after the cut.

Rule (exact, die frame; written to die.pg.grid[layer].net_holes_um[VSS]):
  * one hole per merged collinear strap run on the strap's own layer (M8 strap -> M8 VSS row, M9 -> M9 column);
  * across: the clock metal band (centre +- width/2) bloated by the NDR space: it meets only the VSS stripe the strap
    sits on (pitch 8.64, VDD 4.32 away is untouched);
  * along: the strap metal end (+ width/2), its drawn shield extension (shield_geom ext) and the NDR space, so the
    kept VSS stripe neither touches the clock metal nor merges with the shield ends into a wide VSS shape.
Keep-out = strap width + min spacing, as the ruling states, extended over the shield ends (same net, but a merge
would create a >= 0.49975 um shape, R8 wide-merge rule).

Checks (fail closed, report JSON):
  * shorts / spacing of mesh clock metal + shields vs the cut PG (qc_mesh_pg_phase.inventory form) = 0;
  * VSS continuity: every kept M8/M9 VSS piece meets >= 1 perpendicular VSS piece (VIA89), every piece that ends at
    a cut has a via within one perpendicular pitch of that end (strapped at both ends), and the VSS M8/M9 pieces
    form ONE connected component (union-find over the via89 crossings);
  * removed length per layer vs the uncut VSS (R27 arithmetic ~5.5 %).
"""
import argparse
import bisect
import copy
import json
from collections import defaultdict
from pathlib import Path

import die_clock_128 as C
import die_clock_mesh as D
import die_infra as I
import schema


def merge_runs(segs):
    """{coord: [(a0, a1)]} merged overlapping/touching intervals"""
    by = defaultdict(list)
    for c, a0, a1 in segs:
        by[round(c, 4)].append((min(a0, a1), max(a0, a1)))
    out = {}
    for c, iv in by.items():
        iv.sort()
        m = [list(iv[0])]
        for a, b in iv[1:]:
            if a <= m[-1][1] + 1e-9:
                m[-1][1] = max(m[-1][1], b)
            else:
                m.append([a, b])
        out[c] = [tuple(x) for x in m]
    return out


def mesh_holes(mesh, nd):
    """{layer: [rect]} VSS cut-outs for the mesh straps (see module doc)"""
    hw, _off, ext = C.shield_geom(nd)
    sp = nd["space"]
    across = hw + sp
    along = max(hw, ext) + sp
    runs = {"M8": merge_runs([(s["y"], s["x0"], s["x1"]) for s in mesh["M8"]]),
            "M9": merge_runs([(s["x"], s["y0"], s["y1"]) for s in mesh["M9"]])}
    out = {"M8": [], "M9": []}
    for c, ivs in sorted(runs["M8"].items()):
        for a0, a1 in ivs:
            out["M8"].append([round(a0 - along, 4), round(c - across, 4), round(a1 + along, 4), round(c + across, 4)])
    for c, ivs in sorted(runs["M9"].items()):
        for a0, a1 in ivs:
            out["M9"].append([round(c - across, 4), round(a0 - along, 4), round(c + across, 4), round(a1 + along, 4)])
    return out, dict(across_half_um=round(across, 4), along_ext_um=round(along, 4),
                     runs=dict(M8=sum(len(v) for v in runs["M8"].values()), M9=sum(len(v) for v in runs["M9"].values())))


def apply_holes(grid, holes, net="VSS"):
    g = copy.deepcopy(grid)
    for row in g:
        if row["layer"] in holes and holes[row["layer"]]:
            row.setdefault("net_holes_um", {})[net] = holes[row["layer"]]
            row["net_holes_note"] = ("INFRA-FIRST-QC-R28 pg_mesh_cut.py: %s cut under every clock-mesh strap on %s "
                                     "(COORD 10-27 11:08 OPTION A)" % (net, row["layer"]))
    return g


def shorts(P, grid, mesh, nd):
    """mesh clock metal + drawn VSS shields vs the PG shapes (qc_mesh_pg_phase.inventory form)"""
    pg = C.pg_shapes(I.pg_rects(P, grid))
    ix = C.MetalIndex(nd["space"])
    for s in pg:
        ix.add(s)
    segs = [("M8", s["x0"], s["y"], s["x1"], s["y"], "ck_mesh_explicit", "mesh") for s in mesh["M8"]]
    segs += [("M9", s["x"], s["y0"], s["x"], s["y1"], "ck_mesh_explicit", "mesh") for s in mesh["M9"]]
    n = defaultdict(int)
    ex = []
    for s in C.clock_shapes(segs, nd, "VSS"):
        for j, what in ix.hits(s):
            n[f"{s[0]}:{s[2]}:{what}:{ix.shapes[j][1]}"] += 1
            if len(ex) < 8:
                ex.append(dict(kind=what, mesh=list(s), pg=list(ix.shapes[j])))
    # wide merge: a drawn shield touching a same-net VSS stripe
    wide = 0
    for s in C.clock_shapes(segs, nd, "VSS"):
        if s[2] == "shield" and C.merged_width(ix, s, "VSS") >= C.WIDE_MERGE_UM - 1e-9:
            wide += 1
    return dict(segments=len(segs), conflicts=sum(n.values()), by_kind=dict(n), shield_wide_merge=wide, examples=ex)


def continuity(rects, net="VSS", cut_pitch=None, orig=None):
    """VSS M8/M9 piece graph over the VIA89 crossings.  orig = the uncut rects: a piece end that is not an end of
    its uncut stripe is a CUT end and must have a via within cut_pitch (strapped at both ends); other ends (die edge)
    are reported as edge_stub_max_um only."""
    oe = defaultdict(set)
    for r in (orig or rects):
        if r[0] == net and r[1] in ("M8", "M9"):
            V = r[1] == "M9"
            c = round(((r[2] + r[4]) if V else (r[3] + r[5])) / 2, 4)
            oe[(r[1], c)].update((round(r[3], 4), round(r[5], 4)) if V else (round(r[2], 4), round(r[4], 4)))
    stub = [0.0]

    def bad_end(L, c, lo, hi, first, last):
        ends = oe.get((L, round(c, 4)), set())
        b = False
        for e, d in ((lo, first - lo), (hi, hi - last)):
            if round(e, 4) in ends:
                stub[0] = max(stub[0], d)
            elif d > cut_pitch + 1e-6:
                b = True
        return b
    h = [(r[3], r[5], r[2], r[4]) for r in rects if r[0] == net and r[1] == "M8"]   # (y0, y1, x0, x1)
    v = [(r[2], r[4], r[3], r[5]) for r in rects if r[0] == net and r[1] == "M9"]   # (x0, x1, y0, y1)
    cols = defaultdict(list)                       # column centre x -> [(y0, y1, idx)]
    for k, (x0, x1, y0, y1) in enumerate(v):
        cols[round((x0 + x1) / 2, 4)].append((y0, y1, k))
    cx = sorted(cols)
    for c in cx:
        cols[c].sort()
    par = list(range(len(h) + len(v)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    vcount = [0] * len(v)
    vys = defaultdict(list)
    hfloat, hend, vias = [], [], 0
    for i, (y0, y1, x0, x1) in enumerate(h):
        y = (y0 + y1) / 2
        lo, hi = bisect.bisect_left(cx, x0), bisect.bisect_right(cx, x1)
        xs = []
        for c in cx[lo:hi]:
            for (a, b, k) in cols[c]:
                if a <= y <= b:
                    vias += 1
                    xs.append(c)
                    vcount[k] += 1
                    vys[k].append(y)
                    ra, rb = find(i), find(len(h) + k)
                    if ra != rb:
                        par[ra] = rb
                    break
        if not xs:
            hfloat.append(i)
        elif cut_pitch is not None and bad_end("M8", y, x0, x1, xs[0], xs[-1]):
            hend.append(i)
    vfloat = [k for k in range(len(v)) if not vcount[k]]
    vend = []
    if cut_pitch is not None:
        for k, (x0, x1, y0, y1) in enumerate(v):
            if vys[k] and bad_end("M9", (x0 + x1) / 2, y0, y1, min(vys[k]), max(vys[k])):
                vend.append(k)
    comps = len({find(a) for a in range(len(par))})
    return dict(m8_pieces=len(h), m9_pieces=len(v), via89=vias, floating_m8=len(hfloat), floating_m9=len(vfloat),
                dangling_end_m8=len(hend), dangling_end_m9=len(vend), components=comps,
                edge_stub_max_um=round(stub[0], 4),
                examples=dict(floating_m8=[list(h[i]) for i in hfloat[:5]], floating_m9=[list(v[k]) for k in vfloat[:5]],
                              dangling_m8=[list(h[i]) for i in hend[:5]], dangling_m9=[list(v[k]) for k in vend[:5]]))


def continuity_floating(rects, net, layer):
    """(x0, y0, x1, y1) of `layer` net pieces with no perpendicular same-net crossing"""
    me = [r for r in rects if r[0] == net and r[1] == layer]
    ot = [r for r in rects if r[0] == net and r[1] == ("M9" if layer == "M8" else "M8")]
    cols = defaultdict(list)
    for r in ot:
        c = round(((r[2] + r[4]) if layer == "M8" else (r[3] + r[5])) / 2, 4)
        cols[c].append((r[3], r[5]) if layer == "M8" else (r[2], r[4]))
    cx = sorted(cols)
    out = []
    for r in me:
        c = ((r[3] + r[5]) if layer == "M8" else (r[2] + r[4])) / 2
        a0, a1 = (r[2], r[4]) if layer == "M8" else (r[3], r[5])
        lo, hi = bisect.bisect_left(cx, a0), bisect.bisect_right(cx, a1)
        if not any(p <= c <= q for x in cx[lo:hi] for p, q in cols[x]):
            out.append(r[2:])
    return out


def length(rects, net, layer):
    return sum((r[4] - r[2]) if layer == "M8" else (r[5] - r[3]) for r in rects if r[0] == net and r[1] == layer)


def cut_tcl(grid, net="VSS"):
    """POST_PDN_TCL: cut the pdngen `net` M8/M9 stripe sboxes (and the vias on them) inside every net_holes_um rect,
    keeping the pieces outside.  Same rect set as the model (die_infra.pg_rects)."""
    rows = [(g["layer"], h) for g in grid for h in (g.get("net_holes_um") or {}).get(net, ())]
    t = ["# GENERATED by tools/die_plan/pg_mesh_cut.py (INFRA-FIRST-QC-R28): cut %s under the clock-mesh straps" % net,
         "set b [ord::get_db_block]", "set dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
         "set n [$b findNet %s]" % net, "set ot_holes {"]
    t += ["  {%s %.4f %.4f %.4f %.4f}" % (L, *h) for L, h in rows]
    t += ["}", r'''
proc ot_iv_cut {lo hi cuts} {
  set out {}; set a $lo
  foreach c [lsort -real -index 0 $cuts] { lassign $c h0 h1
    if {$h1 <= $a || $h0 >= $hi} continue
    if {$h0 > $a} { lappend out [list $a $h0] }
    if {$h1 > $a} { set a $h1 } }
  if {$a < $hi} { lappend out [list $a $hi] }
  return $out }
set ot_cut 0; set ot_via 0
foreach sw [$n getSWires] {
  set mk {}
  foreach sb [$sw getWires] {
    set ly [$sb getTechLayer]
    if {$ly eq "NULL"} {
      # a via: drop it when its centre lies in a hole of either layer it joins
      set x [expr {([$sb xMin]+[$sb xMax])/2.0/$dbu}]; set y [expr {([$sb yMin]+[$sb yMax])/2.0/$dbu}]
      foreach h $ot_holes { lassign $h L x0 y0 x1 y1
        if {$x > $x0 && $x < $x1 && $y > $y0 && $y < $y1} { lappend mk [list via $sb]; break } }
      continue }
    set L [$ly getName]; if {$L ne "M8" && $L ne "M9"} continue
    set bx [list [$sb xMin] [$sb yMin] [$sb xMax] [$sb yMax]]
    lassign [lmap q $bx {expr {$q/double($dbu)}}] x0 y0 x1 y1
    set V [expr {($x1-$x0) < ($y1-$y0)}]
    set cuts {}
    foreach h $ot_holes { lassign $h HL hx0 hy0 hx1 hy1
      if {$HL ne $L} continue
      if {$V} { if {$hx0 < $x1 && $x0 < $hx1 && $hy0 < $y1 && $y0 < $hy1} { lappend cuts [list $hy0 $hy1] } } else {
                if {$hy0 < $y1 && $y0 < $hy1 && $hx0 < $x1 && $x0 < $hx1} { lappend cuts [list $hx0 $hx1] } } }
    if {[llength $cuts]} { lappend mk [list wire $sb $L $V $x0 $y0 $x1 $y1 $cuts [$sb getWireShapeType]] } }
  foreach m $mk {
    if {[lindex $m 0] eq "via"} { odb::dbSBox_destroy [lindex $m 1]; incr ot_via; continue }
    lassign $m _ sb L V x0 y0 x1 y1 cuts st
    set ly [[ord::get_db_tech] findLayer $L]
    odb::dbSBox_destroy $sb; incr ot_cut
    foreach p [ot_iv_cut [expr {$V ? $y0 : $x0}] [expr {$V ? $y1 : $x1}] $cuts] { lassign $p a c
      if {$V} { odb::dbSBox_create $sw $ly [expr {round($x0*$dbu)}] [expr {round($a*$dbu)}] [expr {round($x1*$dbu)}] [expr {round($c*$dbu)}] $st
      } else { odb::dbSBox_create $sw $ly [expr {round($a*$dbu)}] [expr {round($y0*$dbu)}] [expr {round($c*$dbu)}] [expr {round($y1*$dbu)}] $st } } } }
puts "OT_PG_MESH_CUT stripes_cut $ot_cut vias_removed $ot_via"
'''.strip()]
    return "\n".join(t) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("spec", help="clock_spec.json (its 'mesh') or a bare mesh json")
    ap.add_argument("out", help="output dir: plan.json (cut grid), pg_mesh_cut.json, post_pdn_cut.tcl")
    ap.add_argument("--net", default="VSS")
    a = ap.parse_args()
    P = schema.Plan(schema.load(a.plan), Path(a.plan))
    sp = json.loads(Path(a.spec).read_text())
    mesh = sp.get("mesh", sp)
    nd = D.NDR[mesh.get("ndr", "8w")]
    grid0 = C.pg_grid(P)
    holes, hmeta = mesh_holes(mesh, nd)
    grid1 = apply_holes(P.die["pg"]["grid"], holes, a.net)
    # a kept piece that meets no perpendicular VSS stripe (e.g. the 8-um M8 tail east of a strap whose end column is
    # cut too) carries no current: it is cut as well (no floating VSS metal), then the check below re-runs
    raw0 = json.loads(Path(a.plan).read_text())
    tmp = copy.deepcopy(raw0)
    tmp["die"]["pg"]["grid"] = grid1
    Pt = schema.Plan(tmp, Path(a.plan))
    rt = I.pg_rects(Pt, C.pg_grid(Pt))
    extra = {"M8": [], "M9": []}
    for L in ("M8", "M9"):
        for x0, y0, x1, y1 in continuity_floating(rt, a.net, L):
            e = 1e-3     # cover the piece along its axis (exact across)
            extra[L].append([round(x0 - e, 4), y0, round(x1 + e, 4), y1] if L == "M8"
                            else [x0, round(y0 - e, 4), x1, round(y1 + e, 4)])
    if extra["M8"] or extra["M9"]:
        holes = {L: holes[L] + extra[L] for L in holes}
        grid1 = apply_holes(P.die["pg"]["grid"], holes, a.net)
    hmeta["floating_tail_holes"] = dict(M8=len(extra["M8"]), M9=len(extra["M9"]))
    raw = json.loads(Path(a.plan).read_text())
    raw["die"]["pg"]["grid"] = grid1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(raw, indent=1) + "\n")
    P1 = schema.Plan(schema.load(out / "plan.json"), out / "plan.json")
    r0, r1 = I.pg_rects(P, grid0), I.pg_rects(P1, C.pg_grid(P1))
    pitch = {g["layer"]: g["pitch_um"] for g in grid1}
    rem = {L: dict(uncut_mm=round(length(r0, a.net, L) / 1e3, 1), cut_mm=round(length(r1, a.net, L) / 1e3, 1))
           for L in ("M8", "M9")}
    for L, d in rem.items():
        d["removed_mm"] = round(d["uncut_mm"] - d["cut_mm"], 1)
        d["removed_pct"] = round(100 * d["removed_mm"] / d["uncut_mm"], 2) if d["uncut_mm"] else 0.0
    other = {n: [length(r0, n, L) - length(r1, n, L) for L in ("M8", "M9")] for n in {r[0] for r in r0} if n != a.net}
    s0, s1 = shorts(P, grid0, mesh, nd), shorts(P1, C.pg_grid(P1), mesh, nd)
    cont = continuity(r1, a.net, cut_pitch=max(pitch.values()), orig=r0)
    cont0 = continuity(r0, a.net, cut_pitch=max(pitch.values()))
    ok = (s1["conflicts"] == 0 and s1["shield_wide_merge"] == 0 and cont["floating_m8"] == 0 and cont["floating_m9"] == 0
          and cont["dangling_end_m8"] == 0 and cont["dangling_end_m9"] == 0 and cont["components"] == 1
          and all(abs(v) < 1e-6 for vs in other.values() for v in vs))
    rep = dict(schema="opentallas.pg_mesh_cut.v1", plan=a.plan, spec=a.spec, net=a.net, ndr=mesh.get("ndr", "8w"),
               rule=hmeta, holes=dict(M8=len(holes["M8"]), M9=len(holes["M9"])), removed=rem,
               other_nets_removed_um={n: [round(x, 4) for x in v] for n, v in other.items()},
               mesh_vs_pg_uncut={k: v for k, v in s0.items() if k != "examples"}, mesh_vs_pg_cut=s1,
               vss_continuity_uncut={k: v for k, v in cont0.items() if k != "examples"}, vss_continuity_cut=cont,
               verdict="PASS" if ok else "FAIL",
               scope="plan PG model (die_infra.pg_rects) + pdngen POST_PDN cut; IR needs a PDNSim re-solve on this grid")
    (out / "pg_mesh_cut.json").write_text(json.dumps(rep, indent=1) + "\n")
    (out / "post_pdn_cut.tcl").write_text(cut_tcl(grid1, a.net))
    print(json.dumps({k: rep[k] for k in ("holes", "removed", "verdict")}))
    print(json.dumps(dict(uncut=rep["mesh_vs_pg_uncut"]["conflicts"], cut=s1["conflicts"], wide=s1["shield_wide_merge"],
                          cont={k: v for k, v in cont.items() if k != "examples"})))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
