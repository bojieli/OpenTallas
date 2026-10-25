#!/usr/bin/env python3
"""OWNER RESET RULE (BRIEFING "OWNER DECISIONS" 2026-10-24 #2, = KV-G3 option (b)): pipeline reset like data.

Per partition (die region) there is exactly ONE root 2-flop (or 3-flop) reset synchroniser, u_rst_root, next to the
arst_n pin.  Its async input is the only reset false path.  From it the synchronised reset travels as a SYNCHRONOUS
signal through relay flops (ot_dp_rrelay u_rrl_<k>) with every hop <= REACH_UM (405, the data reach rule), and with
EQUAL depth D to every clock tap.  So every tap's delivered reset rst_n_t<i> releases (and asserts) on the same known
cycle: N + D clocks after arst_n.  Local flops take rst_n_t<i> of their nearest tap (reset_taps.tcl) with normal
timed recovery/removal from that local relay.  There are no recovery waivers.

Tree: a shortest-hop tree from the root over the type's clock taps.  An edge u -> v costs max(1, ceil(manhattan /
REACH_UM)) relays; edges over one hop get intermediate relays on the x-then-y L path.  Ties go to fewer intermediate
relays, then to the shorter total wire.  Each tap's tree relay sits at the tap and feeds its children.  Taps shallower than D get local pad relays at
the tap up to depth D; the last relay at tap i drives rst_n_t<i>.

Shared by kit_rsync.py (bound kits), gen_rtl.py (generated kits) and gen_phys.py (reset_tree.tcl: FIRM placement of
the root and the relays, sourced by face_flops.tcl before reset_taps.tcl).
usage: reset_tree.py PLAN.json TYPE      -> prints the tree summary (depth, relays, boot cycles)"""
import heapq
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

REACH_UM = 405.0

def relay_sv():
    """the ot_dp_rrelay module text (held in gen_rtl.CELLS, the one copy of the kit cells)."""
    import gen_rtl
    import re
    return re.search(r"(//[^\n]*ot_dp_rrelay.*?\nendmodule\n)", gen_rtl.CELLS, re.S).group(1)


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _hops(a, b, reach):
    return max(1, math.ceil(_man(a, b) / reach - 1e-9))


def _lpath(a, b, n):
    """n interior points at equal spacing on the x-then-y L path a -> b."""
    L = _man(a, b)
    pts = []
    for j in range(1, n + 1):
        s = L * j / (n + 1)
        dx = abs(b[0] - a[0])
        if s <= dx:
            pts.append((a[0] + math.copysign(s, b[0] - a[0]), a[1]))
        else:
            pts.append((b[0], a[1] + math.copysign(s - dx, b[1] - a[1])))
    return pts


def build(taps, root_xy, reach=REACH_UM):
    """taps [(port, x, y)] (tap index = list index); root_xy = the arst_n pin.  Returns the tree:
    relays [{name, xy, d (input net), q (output net), depth, tap, kind}], depth D, per-tap tree depth."""
    root = (float(root_xy[0]), float(root_xy[1]))
    pts = [(float(x), float(y)) for _, x, y in taps]
    n = len(pts)
    dist = {-1: (0, 0, 0.0)}     # (hops, intermediate wire relays, wire um): ties -> fewer relays, then shorter wire
    par = {}
    pq = [(0, 0, 0.0, -1)]
    done = set()
    while pq:
        h, nw, w, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        pu = root if u < 0 else pts[u]
        for v in range(n):
            if v in done:
                continue
            e = _hops(pu, pts[v], reach)
            c = (h + e, nw + e - 1, w + _man(pu, pts[v]))
            if v not in dist or c < dist[v]:
                dist[v] = c
                par[v] = u
                heapq.heappush(pq, c + (v,))
    D = max(dist[v][0] for v in range(n))
    relays = []
    tree_q = {-1: "rst_root_n"}
    order = sorted(range(n), key=lambda v: dist[v])
    k = 0
    tdepth = {}
    for v in order:
        u = par[v]
        pu = root if u < 0 else pts[u]
        src = tree_q[u]
        nh = _hops(pu, pts[v], reach)
        dep = dist[u][0]
        for p in _lpath(pu, pts[v], nh - 1):
            dep += 1
            relays.append(dict(name=f"u_rrl_{k}", xy=p, d=src, q=f"rst_rl_{k}", depth=dep, tap=v, kind="wire"))
            src = f"rst_rl_{k}"
            k += 1
        dep += 1
        tdepth[v] = dep
        q = f"rst_n_t{v}" if dep == D else f"rst_rl_{k}"
        relays.append(dict(name=f"u_rrl_{k}", xy=pts[v], d=src, q=q, depth=dep, tap=v, kind="tap"))
        tree_q[v] = q
        k += 1
        src = q
        while dep < D:
            dep += 1
            q = f"rst_n_t{v}" if dep == D else f"rst_rl_{k}"
            relays.append(dict(name=f"u_rrl_{k}", xy=pts[v], d=src, q=q, depth=dep, tap=v, kind="pad"))
            src = q
            k += 1
    maxhop = 0.0
    xy = {r["q"]: r["xy"] for r in relays}
    xy["rst_root_n"] = root
    for r in relays:
        maxhop = max(maxhop, _man(xy[r["d"]], r["xy"]))
    return dict(root=root, depth=D, relays=relays, tap_depth=tdepth, reach_um=reach, max_hop_um=round(maxhop, 1),
                n_tree=sum(r["kind"] != "pad" for r in relays), n_pad=sum(r["kind"] == "pad" for r in relays))


def for_type(P, tn, reach=REACH_UM):
    """The tree of a plan type: its clock taps (schema.tap_grid) and its reset tap (gen_phys.tap_points[1])."""
    import gen_phys
    return build(S.tap_grid(P, tn), gen_phys.tap_points(P, tn)[1], reach)


def rtl_lines(tree, ns, ind="    "):
    """SystemVerilog body lines: root synchroniser + relays.  Declares rst_n_t<i> for every tap."""
    if ns not in (2, 3):
        raise ValueError(f"reset_tree: sync_stages {ns} (root synchronisers exist for 2 or 3)")
    taps = sorted({r["tap"] for r in tree["relays"]})
    out = [f"{ind}// OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): ONE root synchroniser + synchronous relay "
           f"tree, depth {tree['depth']} to all {len(taps)} taps, hops <= {tree['reach_um']:g} um; "
           f"release N+D = {ns}+{tree['depth']} clocks",
           f"{ind}wire rst_root_n;",
           f"{ind}ot_dp_rsync_s{ns} u_rst_root (.clk(clk), .async_rst_n(arst_n), .sync_rst_n(rst_root_n));"]
    out += [f"{ind}wire rst_n_t{i};" for i in taps]
    for r in tree["relays"]:
        if r["q"].startswith("rst_rl_"):
            out.append(f"{ind}wire {r['q']};")
        out.append(f"{ind}ot_dp_rrelay {r['name']} (.clk(clk), .d({r['d']}), .q({r['q']}));  "
                   f"// {r['kind']} tap {r['tap']} depth {r['depth']} @ ({r['xy'][0]:.1f}, {r['xy'][1]:.1f})")
    return out


TCL_HEAD = """# GENERATED by tools/die_plan/reset_tree.py (OWNER RESET RULE 10-24): FIRM sites of the root reset synchroniser
# (at the arst_n pin) and of the synchronous reset relays (u_rrl_<k>, hops <= REACH).  Sourced inside face_flops.tcl
# (PRE_GLOBAL_PLACE) before reset_taps.tcl; uses its ff_put_near / ff_blk / ff_dbu.  Listed in ot_face_flops.txt so
# face_flops_release.tcl hands them to DPL like the face flops.
set rtr_n 0; set rtr_miss {}
set rtr_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
proc rtr_place {pat x y tag} {
  global ff_blk ff_dbu rtr_n rtr_miss rtr_fh
  set hit 0
  foreach i [$ff_blk getInsts] {
    set nm [$i getName]
    if {![string match $pat $nm]} continue
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    set got [ff_put_near $i [expr {round($x * $ff_dbu)}] [expr {round($y * $ff_dbu)}]]
    if {$got eq ""} { lappend rtr_miss $nm; continue }
    puts $rtr_fh "$nm\\t$tag\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-"
    incr rtr_n; incr hit
  }
  if {!$hit} { lappend rtr_miss $pat }
}
"""


def tcl_text(tree):
    t = [TCL_HEAD, f"rtr_place {{*u_rst_root[./]*}} {tree['root'][0]:g} {tree['root'][1]:g} rroot"]
    for r in tree["relays"]:
        t.append(f"rtr_place {{*{r['name']}[./]*}} {r['xy'][0]:.3f} {r['xy'][1]:.3f} rrl:{r['kind']}{r['depth']}")
    t.append("close $rtr_fh")
    t.append(f"puts \"OT_RESET_TREE depth {tree['depth']} ({tree['n_tree']} tree + {tree['n_pad']} pad relays, "
             f"max hop {tree['max_hop_um']} um): placed $rtr_n flops FIRM (missing: [llength $rtr_miss] $rtr_miss)\"")
    return "\n".join(t) + "\n"


def summary(tree, ns):
    return dict(depth=tree["depth"], relays=len(tree["relays"]), tree_relays=tree["n_tree"], pad_relays=tree["n_pad"],
                max_hop_um=tree["max_hop_um"], reach_um=tree["reach_um"], root_um=[round(v, 3) for v in tree["root"]],
                sync_stages=ns, release_clocks=ns + tree["depth"],
                boot_cycles_added=tree["depth"],
                note="OWNER RESET RULE 10-24: one root synchroniser + equal-depth synchronous relay tree")


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__)
    P = S.Plan(json.load(open(argv[0])))
    ns = int(P.types[argv[1]].get("reset", {}).get("sync_stages", 2))
    print(json.dumps(dict(type=argv[1], **summary(for_type(P, argv[1]), ns))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
