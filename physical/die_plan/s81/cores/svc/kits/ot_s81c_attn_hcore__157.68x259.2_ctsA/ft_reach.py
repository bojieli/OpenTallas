"""FT reach from actual corresponding pin bits, including mirrored output orders.

resize(raw, reach_um=405, margin=.98, types=None, macrofree_only=True)
updates station counts in place and returns one record per changed slot. It never
reduces a count. Call gen.py latency after this to account every added cycle.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S
from gen_phys import type_pins


def resize(raw, reach_um=405.0, margin=.98, types=None, macrofree_only=True):
    if not 0 < margin <= 1 or reach_um <= 0:
        raise ValueError('reach must be positive and margin in (0, 1]')
    model = S.Plan(raw)
    selected = None if types is None else set(types)
    changed = []
    for tn, ty in model.types.items():
        if (selected is not None and tn not in selected) or (macrofree_only and ty.get('hard_cores')):
            continue
        if not ty.get('ft_slots'):
            continue
        pins = {(bus, bit): (x, y) for bus, bit, _, x, y, _ in type_pins(model, tn)}
        for slot in ty['ft_slots']:
            lengths = []
            for bit in range(slot['width'] + 1):
                a = pins.get((slot['name'] + '_i', bit))
                b = pins.get((slot['name'] + '_o', bit))
                if a is not None and b is not None:
                    lengths.append(abs(a[0] - b[0]) + abs(a[1] - b[1]))
            if not lengths:
                continue
            worst = max(lengths)
            need = max(slot['stations'], int(math.ceil(worst / (reach_um * margin))))
            if need > slot['stations']:
                changed.append(dict(type=tn, slot=slot['name'], stations=[slot['stations'], need],
                                    worst_bit_route_um=round(worst, 4), reach_um=reach_um, margin=margin))
                slot['stations'] = need
    return changed
