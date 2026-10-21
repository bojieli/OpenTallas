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


def expand_channel(source, receiver, extra, baseline_w, baseline_h, west=0., max_width=33000.):
    """Add physical receiver-column land area without compressing another seam.

    Unlike the initial missing-channel repair, this grows an existing channel
    with an explicit array translation and outline budget. The western service
    column stays fixed. No relay/stage is invented; GEN places split classes in
    the added real footprint and retains its strict native-pin reach limit.
    """
    if west < 0 or abs(west / 43.2 - round(west / 43.2)) > 1e-6:
        raise ValueError('array translation must be nonnegative multiples of 43.2 um')
    if baseline_w + extra - west > max_width + 1e-6:
        raise ValueError('proposed die exceeds the reticle width')
    if extra <= 0 or abs(extra / 43.2 - round(extra / 43.2)) > 1e-6:
        raise ValueError('channel expansion must be positive multiples of 43.2 um')
    out = copy.deepcopy(source)
    slices = {i['n']: i for i in out['insts'] if i['n'].startswith('dvs_')}
    boundary = slices[receiver]['x']
    left = max(i['x'] + i['w'] for n, i in slices.items()
               if n != receiver and i['x'] < boundary)
    old_gap = round(boundary - left, 3)
    if old_gap < 0:
        raise ValueError('receiver overlaps its western slice')
    moved = []
    for i in out['insts']:
        if i['n'].startswith(('c16_', 'dvs_')):
            i['x'] = round(i['x'] - west + (extra if i['x'] >= boundary - 1e-3 else 0), 3)
            if i['x'] < 0:
                raise ValueError('array translation crosses western die edge')
            moved.append(i['n'])
    prior = out.get('receiver_channel_plan')
    history = out.setdefault('receiver_channel_history', [])
    if prior:
        history.append(prior)
    out['receiver_channel_plan'] = dict(
        receiver=receiver, prior_gap_um=old_gap, added_gap_um=extra,
        gap_um=round(old_gap + extra, 3), array_west_um=west,
        baseline_die_um=[baseline_w, baseline_h],
        proposed_die_um=[round(baseline_w + extra - west, 3), baseline_h],
        die_area_delta_mm2=round((extra-west) * baseline_h / 1e6, 9),
        moved_array_instances=len(moved), moved_instances=moved,
        reservation=dict(split_lanes=2, class_frame_um=[104, 106],
                         independent_frames=True, row_endcap_pitch_um=12.96,
                         required_width_um=2*104+3*12.96),
        explicit_pipeline_stages_added=0, token_age_delta=None,
        rebuilt_lane_ages='derive from actual GEN relay topology; calendar recompilation required',
        scope='physical channel/outline expansion; actual GEN decides placement; calendar remains HOLD')
    out['source'] = out.get('source', '') + f' | expand {receiver} channel by {extra} um, array west {west} um, outline +{extra-west} um'
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
