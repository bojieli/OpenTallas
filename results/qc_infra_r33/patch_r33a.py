import sys,re
p=sys.argv[1]; s=open(p).read()
def rep(a,b,cnt=1):
    global s
    assert s.count(a)==cnt,(a[:80],s.count(a)); s=s.replace(a,b)
# 1. side helper (same rule as legalize lane_sign: column-tree lane on the wider channel side)
rep('''def band_trees(B, st, a):
    """R26: the balanced band trees for every band / W-edge driver (see the section comment)."""
''','''def col_lane_side(cores, x):
    """legalize() lane_sign: the column-tree lane sits on the wider channel side of column x (+1 east / -1 west).
    W/E mirrored types get mirrored signs (the core geometry is mirrored), so offsets in these units are type-frame
    identical (12.2a1)."""
    L = max([c[2] for c in cores if c[2] <= x + 1e-6] or [-1e9])
    R = min([c[0] for c in cores if c[0] >= x - 1e-6] or [1e9])
    return 1.0 if R - x >= x - L else -1.0


def band_trees(B, st, a):
    """R26: the balanced band trees for every band / W-edge driver (see the section comment)."""
''')
rep('''        if not wedge and getattr(a, "a0_band_col_dx", None):
            xc = xc + float(a.a0_band_col_dx)
''','''        if not wedge and getattr(a, "a0_band_col_dx", None):
            xc = xc + float(a.a0_band_col_dx)
        # R33 (opt-in --a0-band-col-side N; COORD ruling INFRA-FIRST-QC-R32 (b)): the band y-tree takes its OWN island
        # column N island x-pitches from the feed column on the column-tree side (signed: + = past the column-tree lane
        # side, - = the far side); side from the core geometry, so W/E mirror types keep identical slots
        if not wedge and getattr(a, "a0_band_col_side", None) is not None:
            xc = r3(xc + col_lane_side(B["cores"], xc) * float(a.a0_band_col_side) * float(a.island_pitch_x))
''')
# 2. col tap side preference: snap point shifted N pitches toward (+) / away (-) from the column-tree lane
rep('''        masters = masters if masters is not None else ["BUFx24"] * int(units)
        cells.append(dict(kind=kind, xy0=(r3(xy[0]), r3(xy[1])), site=[xy[0] + dx, xy[1] + dy], units=len(masters), lane=lane,
                          ref=ref, masters=masters))
''','''        masters = masters if masters is not None else ["BUFx24"] * int(units)
        cells.append(dict(kind=kind, xy0=(r3(xy[0]), r3(xy[1])), site=[xy[0] + dx, xy[1] + dy], units=len(masters), lane=lane,
                          ref=ref, masters=masters))
        if kind == "col_tap" and COLTAP_SIDE[0] is not None:
            # R33 (opt-in --col-tap-side N): the merged top-leaf / column-tap cell snaps from a plan point N island
            # x-pitches toward (+) / away from (-) the column-tree lane, so tap, column tree and band y-tree hold
            # disjoint island columns at the feed column (side from core geometry -> W/E mirror identical)
            cells[-1]["snap0"] = (r3(xy[0] + lane_sign(xy[0]) * COLTAP_SIDE[0]), r3(xy[1]))
''')
rep('''DX_LANE = 8.64      # column / trunk tree lane''','''COLTAP_SIDE = [None]     # R33 --col-tap-side (um, signed, set by build from island pitches)
DX_LANE = 8.64      # column / trunk tree lane''')
# assign_periodic uses snap0 when present
rep('''        n = host(*c["xy0"])
        if n is None:
            raise RuntimeError(f"top cell outside partitions {c['xy0']}")
        fx, fy = frame(n, *c["xy0"])''','''        p0 = c.get("snap0") or c["xy0"]
        n = host(*p0)
        if n is None:
            raise RuntimeError(f"top cell outside partitions {c['xy0']}")
        fx, fy = frame(n, *p0)''')
rep('''    p.add_argument("--a0-band-up", type=int, default=4,''','''    p.add_argument("--a0-band-col-side", type=float, default=None,
                   help="R33 opt-in: band y-tree column = feed column + N island x-pitches toward the column-tree lane side (signed)")
    p.add_argument("--col-tap-side", type=float, default=None,
                   help="R33 opt-in: column-tap (merged top leaf) slot snaps N island x-pitches toward the column-tree lane side (signed)")
    p.add_argument("--a0-band-up", type=int, default=4,''')
open(p,"w").write(s)
print("ok")
