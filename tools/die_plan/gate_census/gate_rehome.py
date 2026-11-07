#!/usr/bin/env python3
"""Plan a closed-set re-home of combinational gates that global placement left far outside their own connectivity.

Measured on NK vR4 3_place (DIE-QC-89 11-07): rq_l[257] at (254,152) -> gs[769] at (253,233), 81 um apart, routes through
an AND3 at (19,860) (1400 um round trip) in one cycle.  No cells added or removed, no netlist or clock change: only
positions of a gate and of the single-fanout buffers on its input and output chains.
Read-only by itself: it writes a plan, nothing touches a DB until the Tcl is sourced and legalized.  --report-only prints
the census of gates outside the box of their real fanin + fanout (buffers walked through) and writes no plan.

usage: run.sh ODB OUTDIR            census of any placed DB, 2 minutes, docker memory cap, read-only
       gate_rehome.py CENSUS.tsv --report-only
       gate_rehome.py CENSUS.tsv --tcl OUT.tcl --json OUT.json [--far-um 20]
To apply in a form: source the Tcl in the PRE_CTS hook, then detailed_placement -max_displacement {150 150}; check_placement.
"""
import argparse, collections, json

SKIP_PREFIX = ('ot_b3', 'clk', 'delay', 'ot_face_lift', 'ot_fcap')


def load(path):
    I, P, drv, snk, core = {}, {}, {}, collections.defaultdict(list), None
    for line in open(path):
        r = line.rstrip('\n').split('\t')
        if r[0] == 'I':
            ins = r[8].split(',') if r[8] else []
            outs = r[9].split(',') if r[9] else []
            I[r[1]] = dict(m=r[2], k=r[3], x0=int(r[4]), y0=int(r[5]), x1=int(r[6]), y1=int(r[7]), ins=ins, outs=outs,
                           st=r[10], dnt=r[11] in ('1', 'true'))
            for n in ins:
                snk[n].append(r[1])
            for n in outs:
                drv[n] = r[1]
        elif r[0] == 'P':
            P[r[2]] = (int(r[4]), int(r[5]), r[3])
        elif r[0] == 'C':
            core = tuple(int(v) for v in r[1:5])
    return I, P, drv, snk, core


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('census')
    ap.add_argument('--tcl')
    ap.add_argument('--json')
    ap.add_argument('--report-only', action='store_true')
    ap.add_argument('--far-um', type=float, default=20.0)
    a = ap.parse_args()
    if not a.report_only and not (a.tcl and a.json):
        ap.error('--tcl and --json, or --report-only')
    I, P, drv, snk, core = load(a.census)
    macros = [(i['x0'], i['y0'], i['x1'], i['y1']) for i in I.values() if i['k'] == 'M']

    def movable(n):
        i = I[n]
        return i['st'] in ('PLACED', 'LOCKED_NOT') and not i['dnt'] and not n.startswith(SKIP_PREFIX)

    def centre(i):
        return ((i['x0'] + i['x1']) // 2, (i['y0'] + i['y1']) // 2)

    def back(net):
        """real source (non-buffer driver or port) of net, and the single-fanout buffers walked, nearest source last"""
        chain = []
        while True:
            d = drv.get(net)
            if d is None:
                return (P[net][:2] if net in P else None), chain
            i = I[d]
            if i['k'] == 'B' and i['ins']:
                if len(snk[net]) == 1 and net not in P and movable(d):
                    chain.append(d)
                net = i['ins'][0]
                continue
            return centre(i), chain

    def fwd(net, chain, top=True):
        """real sinks of net; buffers joined only through single-fanout stages from the gate are movable"""
        pts = []
        if net in P and P[net][2] == 'OUTPUT':
            pts.append(P[net][:2])
        sinks = snk.get(net, [])
        single = len(sinks) == 1 and net not in P
        for s in sinks:
            i = I[s]
            if i['k'] == 'B' and i['outs']:
                if top and single and movable(s):
                    chain.append(s)
                    pts += fwd(i['outs'][0], chain, True)
                else:
                    pts += fwd(i['outs'][0], chain, False)
            else:
                pts.append(centre(i))
        return pts

    def in_macro(x, y):
        return next((m for m in macros if m[0] <= x <= m[2] and m[1] <= y <= m[3]), None)

    def snap(x, y):
        m = in_macro(x, y)
        if not m:
            return x, y
        margin = 2000
        opts = [(m[0] - margin, y), (m[2] + margin, y), (x, m[1] - margin), (x, m[3] + margin)]
        opts = [o for o in opts if core[0] <= o[0] <= core[2] and core[1] <= o[1] <= core[3] and not in_macro(*o)]
        return min(opts, key=lambda o: abs(o[0] - x) + abs(o[1] - y))

    moves, gates, before = {}, [], 0
    outside = []
    order = sorted((n for n, i in I.items() if i['k'] == 'G' and movable(n)))
    for n in order:
        i = I[n]
        srcs, in_chains = [], []
        for net in i['ins']:
            s, ch = back(net)
            if s:
                srcs.append(s)
                in_chains.append((s, ch))
        ochain = []
        pts = []
        for net in i['outs']:
            pts += fwd(net, ochain)
        allp = srcs + pts
        if not allp:
            continue
        x0, x1 = min(p[0] for p in allp), max(p[0] for p in allp)
        y0, y1 = min(p[1] for p in allp), max(p[1] for p in allp)
        cx, cy = centre(i)
        d = max(0, x0 - cx, cx - x1) + max(0, y0 - cy, cy - y1)
        outside.append((d / 1000, n, i['m'], cx / 1000, cy / 1000))
        if d <= a.far_um * 1000:
            continue
        tx, ty = snap(min(max(cx, x0), x1), min(max(cy, y0), y1))
        moves[n] = (tx, ty)
        gates.append(dict(gate=n, master=i['m'], outside_um=d / 1000, frm=[cx, cy], to=[tx, ty], fanin=len(srcs), fanout=len(pts)))
        before += d

        def spread(chain, a_pt, b_pt):
            # chain ordered from a_pt to b_pt
            k = len(chain)
            for j, c in enumerate(chain):
                f = (j + 1) / (k + 1)
                moves.setdefault(c, snap(int(a_pt[0] + (b_pt[0] - a_pt[0]) * f), int(a_pt[1] + (b_pt[1] - a_pt[1]) * f)))
        for s, ch in in_chains:
            spread(ch[::-1], s, (tx, ty))
        if ochain and pts:
            c = (sum(p[0] for p in pts) // len(pts), sum(p[1] for p in pts) // len(pts))
            spread(ochain, (tx, ty), c)

    print('gates', len(outside), 'outside own box by >X um:', {t: sum(1 for o in outside if o[0] > t) for t in (20, 50, 100, 200, 400)})
    for o in sorted(outside, reverse=True)[:12]:
        print('  %.0f um %s %s at (%.0f,%.0f)' % (o[0], o[1], o[2], o[3], o[4]))
    if a.report_only:
        return
    with open(a.tcl, 'w') as f:
        f.write('# generated by gate_rehome.py: positions only\n')
        f.write('proc ot_rh {n x y} { set i [[ord::get_db_block] findInst $n]; if {$i eq "NULL"} { error "gate_rehome: missing $n" }; $i setLocation $x $y }\n')
        for n, (x, y) in sorted(moves.items()):
            f.write('ot_rh {%s} %d %d\n' % (n, x, y))
    json.dump(dict(gates=len(gates), cells_moved=len(moves), far_um=a.far_um, outside_um_sum=before / 1000,
                   worst=sorted(gates, key=lambda g: -g['outside_um'])[:40]), open(a.json, 'w'), indent=1)
    print('gates', len(gates), 'cells moved', len(moves), 'outside_um_sum %.0f' % (before / 1000))


if __name__ == '__main__':
    main()
