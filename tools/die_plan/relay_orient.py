#!/usr/bin/env python3
"""Orient relay-chain macros by their outgoing hop (S81 kv_leaf t2 Fable rev12 X1, generic).

A relay master with an R0 pin convention takes its inputs on two faces and drives its outputs on the two opposite
faces (default: in W + N, out E + S, as dsfd_su_t_kvi / dsfd_su_t_kvx).  Seated R0 everywhere, a relay can only
flow east / south; every hop that goes west or north U-turns its bus over the relay's own body.  This tool picks,
per relay, the orientation that points its output faces along the hop to the next stage (or, for the last stage,
to the chain's sink core, else the previous hop's direction):

  out horizontal face mirrored (MY) when the hop goes against it, out vertical face mirrored (MX) when the hop goes
  against it, both -> R180.  |component| <= tol keeps that axis as is.

Input: a seats JSON with relay_seats (master, engine, stage, origin_um, outline_um) and exit_relay_seats (chain,
block, stage, ...), hard_seats for sinks.  Optional: an ORFS macro_place.tcl of `ot_seat {inst} x y` lines, whose
positions are authoritative and which is rewritten to `ot_seat_o {inst} x y ORIENT` (bbox-normalized: the lower-left
corner stays at x, y whatever the orientation).

  python3 -I tools/die_plan/relay_orient.py --seats seats.json [--out seats_oriented.json]
      [--tcl macro_place.tcl --tcl-out macro_place_oriented.tcl] [--out-faces E,S] [--tol 5]
"""
import argparse, collections, json, re, sys

FLIP_H = {'R0': 'MY', 'MY': 'R0', 'MX': 'R180', 'R180': 'MX'}
SEAT_O_PROC = r'''proc ot_seat_o {name x y o} { global blk dbu miss done
  set i [$blk findInst $name]
  if {$i eq "NULL"} { set i [$blk findInst [string map {\\ {}} $name]] }
  if {$i eq "NULL"} { puts "OT_PROBE_MISSING $name"; incr miss; return }
  $i setOrient $o; $i setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]
  set bb [$i getBBox]; set dx [expr {round($x * $dbu) - [$bb xMin]}]; set dy [expr {round($y * $dbu) - [$bb yMin]}]
  set loc [$i getLocation]; $i setLocation [expr {[lindex $loc 0] + $dx}] [expr {[lindex $loc 1] + $dy}]
  $i setPlacementStatus FIRM; incr done }
'''


def orient_for_hop(dx, dy, out_faces=('E', 'S'), tol=5.0):
    """Orientation that makes the R0 output faces (one of E/W, one of N/S) point along the hop (dx, dy)."""
    oh, ov = out_faces
    if oh not in 'EW' or ov not in 'NS':
        raise ValueError(f'out_faces must be (E|W, N|S), got {out_faces}')
    flip_h = (dx < -tol) if oh == 'E' else (dx > tol)
    flip_v = (dy > tol) if ov == 'S' else (dy < -tol)
    return {(False, False): 'R0', (True, False): 'MY', (False, True): 'MX', (True, True): 'R180'}[(flip_h, flip_v)]


def chain_orients(points, sink=None, out_faces=('E', 'S'), tol=5.0):
    """points: ordered relay centres of one chain; sink: centre of the chain's sink core (or None)."""
    pts = list(points) + ([sink] if sink is not None else [])
    out, last = [], None
    for i in range(len(points)):
        if i + 1 < len(pts):
            last = (pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        out.append(orient_for_hop(*(last if last else (0.0, 0.0)), out_faces=out_faces, tol=tol))
    return out


def _centre(origin, outline):
    return (origin[0] + outline[0] / 2.0, origin[1] + outline[1] / 2.0)


def chains_from_seats(seats):
    """{key: [seat, ...] in stage order} for input relays (per engine) and exit relays (per chain, block)."""
    ch = collections.defaultdict(list)
    for s in seats.get('relay_seats', []):
        ch[('in', s['engine'])].append(s)
    for s in seats.get('exit_relay_seats', []):
        ch[('exit', s.get('chain', 'q'), s['block'])].append(s)
    return {k: sorted(v, key=lambda s: s['stage']) for k, v in ch.items()}


def sink_of(key, seats, sink_re=r'g_kve\[{e}\]\..*u_kve$'):
    if key[0] != 'in':
        return None
    rx = re.compile(sink_re.format(e=key[1]))
    for s in seats.get('hard_seats', []):
        if rx.search(s.get('elaborated_path', '')):
            return s
    return None


def tcl_positions(text):
    pos = {}
    for m in re.finditer(r'^ot_seat(?:_o)? \{(\S+)\} (\S+) (\S+)', text, re.M):
        pos[m.group(1).replace('\\', '')] = (float(m.group(2)), float(m.group(3)))
    return pos


def orient_seats(seats, positions=None, out_faces=('E', 'S'), tol=5.0):
    """Returns {elaborated_path: orient}; positions (tcl, authoritative) override JSON origins."""
    positions = positions or {}
    def ctr(s):
        o = positions.get(s['elaborated_path'], s['origin_um'])
        return _centre(o, s['outline_um'])
    res = {}
    for key, chain in chains_from_seats(seats).items():
        sk = sink_of(key, seats)
        for s, o in zip(chain, chain_orients([ctr(s) for s in chain], ctr(sk) if sk else None, out_faces, tol)):
            res[s['elaborated_path']] = o
    return res


def rewrite_tcl(text, orients):
    def sub(m):
        o = orients.get(m.group(1).replace('\\', ''))
        if not o or o == 'R0':
            return m.group(0)
        return 'ot_seat_o {%s} %s %s %s' % (m.group(1), m.group(2), m.group(3), o)
    t = re.sub(r'^ot_seat \{(\S+)\} (\S+) (\S+)$', sub, text, flags=re.M)
    if 'ot_seat_o {' in t and 'proc ot_seat_o' not in t:
        i = t.find('proc ot_seat {')
        t = (t[:i] + SEAT_O_PROC + t[i:]) if i >= 0 else SEAT_O_PROC + t
    return t


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seats', required=True)
    ap.add_argument('--out')
    ap.add_argument('--tcl')
    ap.add_argument('--tcl-out')
    ap.add_argument('--out-faces', default='E,S')
    ap.add_argument('--tol', type=float, default=5.0)
    a = ap.parse_args(argv)
    seats = json.load(open(a.seats))
    text = open(a.tcl).read() if a.tcl else None
    of = tuple(a.out_faces.split(','))
    orients = orient_seats(seats, tcl_positions(text) if text else None, of, a.tol)
    cnt = collections.Counter(orients.values())
    if a.out:
        for k in ('relay_seats', 'exit_relay_seats'):
            for s in seats.get(k, []):
                if s['elaborated_path'] in orients:
                    s['orient'] = orients[s['elaborated_path']]
        json.dump(seats, open(a.out, 'w'), indent=1)
    if text is not None and a.tcl_out:
        open(a.tcl_out, 'w').write(rewrite_tcl(text, orients))
    print(json.dumps({'relays': len(orients), 'orient': dict(cnt)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
