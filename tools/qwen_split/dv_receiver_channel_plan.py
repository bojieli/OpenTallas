"""Reserve a missing receiver-column relay channel in an existing DV plan.

Move only the replicated compute array west to keep the die within its reticle;
retain all W-column service/PHY origins. Actual GEN placement and reach gates
must validate the resulting plan before routing.
"""
import argparse
import copy
import json
from pathlib import Path


def plan(source, receiver, gap, west, baseline_w, baseline_h, max_width=33000.):
    for value in (gap, west):
        if value < 0 or abs(value / 43.2 - round(value / 43.2)) > 1e-6:
            raise ValueError('channel and array shift must be nonnegative multiples of 43.2 um')
    if not gap:
        raise ValueError('a new channel requires positive width')
    out = copy.deepcopy(source)
    slices = {i['n']: i for i in out['insts'] if i['n'].startswith('dvs_')}
    boundary = slices[receiver]['x']
    if not any(abs(i['x'] + i['w'] - boundary) < .1 for n, i in slices.items() if n != receiver):
        raise ValueError('receiver has no abutting slice boundary; do not add a duplicate channel')
    if baseline_w + gap - west > max_width + 1e-6:
        raise ValueError('proposed die exceeds the reticle width')
    count = 0
    for i in out['insts']:
        if i['n'].startswith(('c16_', 'dvs_')):
            i['x'] = round(i['x'] - west + (gap if i['x'] >= boundary - 1e-3 else 0), 3)
            if i['x'] < 0:
                raise ValueError('array shift crosses the die boundary')
            count += 1
    record = dict(receiver=receiver, gap_um=gap, array_west_um=west,
                  baseline_die_um=[baseline_w, baseline_h],
                  proposed_die_um=[round(baseline_w + gap - west, 3), baseline_h],
                  die_area_delta_mm2=round((gap - west) * baseline_h / 1e6, 9),
                  moved_array_instances=count,
                  scope='planned channel only; actual GEN collision/pin reach/clock/calendar/bind remain required')
    out['receiver_channel_plan'] = record
    out['source'] = out.get('source', '') + f' | receiver {receiver} channel {gap} um, array west {west} um'
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--receiver', default='dvs_E1')
    ap.add_argument('--gap', type=float, required=True)
    ap.add_argument('--array-west', type=float, required=True)
    ap.add_argument('--baseline-w', type=float, required=True)
    ap.add_argument('--baseline-h', type=float, required=True)
    a = ap.parse_args()
    out = plan(json.loads(a.plan.read_text()), a.receiver, a.gap, a.array_west, a.baseline_w, a.baseline_h)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['receiver_channel_plan']))
