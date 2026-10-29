"""Private HBM adapter: continuous paired-bit paths for adjacent-face FT turns.

The shared L-corner helper uses off_in before the centroid corner and off_out
after it. For a >403um-wide E/N ribbon that switches a bit's offset abruptly
from Y to X, creating an impossible jump independent of register count. Use the
same continuous per-bit-path mechanism as the qualified Z-ribbon helper, with
each bit's actual own shortest Manhattan corner. Every allocated pair is still
checked against the unchanged physical hop budget by the shared allocator.

No shared tool or default behavior is changed. Fail on a mismatching upstream
implementation instead of applying a partial patch.
"""
import inspect

def install(module):
    # The HBM cores consume M1-M5. Only M7 supplies vertical over-core
    # transport; reserve its <=0.6 track fraction instead of M5+M7 capacity.
    pitch = next(layer['pitch_um'] for layer in module.S.ASAP7_LAYERS if layer['name'] == 'M7')
    module.LANE_UM_PER_BIT = max(module.LANE_UM_PER_BIT, pitch / .6)
    original_jogs = module.jog_lanes
    def checked_jogs(ty, pins, w, h, fixed=None):
        lanes = original_jogs(ty, pins, w, h, fixed)
        by_axis = {0: [], 1: []}
        slots = {s['name']: s for s in ty.get('ft_slots', [])}
        for name, (centre, width) in lanes.items():
            axis = 1 if slots[name]['in_face'] in 'NS' else 0
            extent = h if axis == 1 else w
            lo, hi = centre-width/2, centre+width/2
            if lo < 4.32 or hi > extent-4.32:
                raise ValueError(f'{name}: M7-only jog band [{lo:.3f},{hi:.3f}] outside physical outline')
            by_axis[axis].append((lo, hi, name))
        for axis, rows in by_axis.items():
            rows.sort()
            for left, right in zip(rows, rows[1:]):
                if right[0] < left[1]-1e-6:
                    raise ValueError(f'{right[2]}: M7-only jog band overlaps {left[2]}')
        return lanes
    module.jog_lanes = checked_jogs
    fn = inspect.getsource(module._place_slot)
    substitutions = [
        ('    def bit_points(s):\n', '''    adjacent_bits = fin != fout and S.OPP.get(fin) != fout
    if adjacent_bits:
        P = np.stack([a, a.copy(), b], axis=1)
        if fin in "EW":
            P[:, 1, 0] = b[:, 0]
        else:
            P[:, 1, 1] = b[:, 1]
        Pseg = np.abs(np.diff(P, axis=1)).sum(axis=2)
        Pcum = np.concatenate([np.zeros((nb, 1)), np.cumsum(Pseg, axis=1)], axis=1)

    def bit_points(s):
'''),
        ('        j = np.clip((u >= Pcum[:, 1]).astype(int) + (u >= Pcum[:, 2]), 0, 2)\n',
         '        j = np.minimum((u[:, None] >= Pcum[:, 1:-1]).sum(axis=1), P.shape[1] - 2).astype(int)\n'),
        ('        if zjog:\n            return bit_points(s)\n',
         '        if zjog or adjacent_bits:\n            return bit_points(s)\n'),
    ]
    for before, after in substitutions:
        if fn.count(before) != 1:
            raise RuntimeError('ft_corridor implementation mismatch: ' + before.strip())
        fn = fn.replace(before, after)
    scope = dict(module.__dict__)
    exec(compile(fn, __file__ + ':paired_corner', 'exec'), scope)
    module._place_slot = scope['_place_slot']
