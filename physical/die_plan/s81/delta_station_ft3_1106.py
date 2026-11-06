#!/usr/bin/env python3
"""S81 t51 FT3 storage gets room east of the NW crossing; no RTL or cycle change."""
import argparse
import copy
import json
import re
from pathlib import Path


def apply(plan):
    out = copy.deepcopy(plan)
    typ = out['partition_types']['slice_station__t51']
    band = typ['clock']['landing_contract']['bands']['ft3_i']
    before = [227.88, 1099.44, 253.8, 1209.228]
    after = [302.4, 1144.8, 388.8, 1209.228]
    assert band['rect_um'] == before, band['rect_um']
    band['rect_um'] = after
    # Full declared input window against every band corner is conservative for
    # every concrete snapped payload/epoch pin emitted inside that window.
    slot = next(f for f in typ['ft_slots'] if f['name'] == 'ft3')
    pin_x0, pin_x1 = slot['in_window_um']
    height = typ['outline_um'][1]
    hop = round(max(abs(x - px) + height - y
                    for x in (after[0], after[2]) for y in (after[1], after[3])
                    for px in (pin_x0, pin_x1)), 6)
    assert hop <= 402.84
    band['max_pin_to_band_hop_um'] = hop
    # Same 576-bit ring/ports/depth. Only the available placement region changes.
    assert (after[2] - after[0]) * (after[3] - after[1]) >= 1.5 * band['area_reserve_um2']
    for name, other in typ['clock']['landing_contract']['bands'].items():
        if name == 'ft3_i':
            continue
        b = other['rect_um']
        assert not (min(after[2], b[2]) > max(after[0], b[0])
                    and min(after[3], b[3]) > max(after[1], b[1])), name
    allowed = copy.deepcopy(plan)
    allowed['partition_types']['slice_station__t51']['clock']['landing_contract']['bands']['ft3_i']['rect_um'] = after
    allowed['partition_types']['slice_station__t51']['clock']['landing_contract']['bands']['ft3_i']['max_pin_to_band_hop_um'] = hop
    assert allowed == out
    return out, {'type': 'slice_station__t51', 'bus': 'ft3_i', 'before_um': before,
                 'after_um': after, 'old_area_um2': 2845.70496,
                 'new_area_um2': round((after[2]-after[0])*(after[3]-after[1]), 6),
                 'area_reserve_um2': band['area_reserve_um2'], 'pin_cycles': 0,
                 'max_pin_to_any_band_corner_um': hop,
                 'scope': 'one ring placement band, fixed outline/pins/RTL/clock/reset/latency'}


def source_delta(raw, plan):
    """Keep the plan's existing serialization; replace exactly two field values."""
    tstart = raw.index('"slice_station__t51":')
    bstart = raw.index('"ft3_i":', tstart)
    target = plan['partition_types']['slice_station__t51']['clock']['landing_contract']['bands']['ft3_i']
    start = raw.index('"rect_um":', bstart)
    a = raw.index('[', start)
    b = raw.index(']', a) + 1
    values = iter(str(v) for v in target['rect_um'])
    replacement = re.sub(r'-?\d+(?:\.\d+)?', lambda m: next(values), raw[a:b])
    raw = raw[:a] + replacement + raw[b:]
    start = raw.index('"max_pin_to_band_hop_um":', bstart)
    m = re.search(r'-?\d+(?:\.\d+)?', raw[start + len('"max_pin_to_band_hop_um":'):])
    a = start + len('"max_pin_to_band_hop_um":') + m.start()
    b = start + len('"max_pin_to_band_hop_um":') + m.end()
    raw = raw[:a] + str(target['max_pin_to_band_hop_um']) + raw[b:]
    assert json.loads(raw) == plan
    return raw


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('plan', type=Path)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--evidence', type=Path)
    args = a.parse_args()
    raw = args.plan.read_text()
    plan = json.loads(raw)
    out, evidence = apply(plan)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(source_delta(raw, out))
    if args.evidence:
        args.evidence.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence))
