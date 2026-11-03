#!/usr/bin/env python3
"""DISABLED model-only T48 CB station proposal; never writes a canonical plan.

No synthesis, bind, P&R or STA is launched. Existing FT banks/taps stay fixed.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools/die_plan'), str(ROOT)]
import schema as S
import gen
import reset_tree as RT
import taps
from tools.die_trial.legal_sites import RowAllocator

TN = 'slice_station__t48'
LANE = 'cb__s_0N_LP__bk_sel'


def prepare(raw):
    before = S.Plan(raw)
    original = before.types[TN]
    slot = next(s for s in original['ft_slots'] if s['name'] == 'ft1')
    assert slot['stations'] == 6 and len(slot['bit_sites_um']) == 5
    assert slot['width'] == 276
    baseline_clock = taps.report(before, TN)
    reset = RT.for_type(before, TN)
    cw, ch = slot['bit_site_cell_um']
    width, height = original['outline_um']
    macros = list(S.placed_macro_boxes(original, halo=4.32).values())
    occupied = [(x-cw/2, y-ch/2, x+cw/2, y+ch/2)
                for x, y, kind in taps.planned_sinks(before, TN, bit_sites=True)]
    # Preserve planned reset/START relays and clock-driver entry footprints.
    controls = [tuple(reset['root'])] + [tuple(r['xy']) for r in reset['relays']]
    controls += [(x, y) for name, x, y in taps.control_pin_sinks(before, TN)]
    blocked = macros + [(x-4.32, y-4.32, x+4.32, y+4.32) for x, y in controls]
    blocked += [(p['xy'][0]-4.32, p['xy'][1]-4.32,
                 p['xy'][0]+4.32, p['xy'][1]+4.32) for p in original['clock']['taps']]
    previous, following = slot['bit_sites_um'][:2]
    attempts = []
    for toward_previous in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80):
        allocator = RowAllocator((4.32, 4.32, width-4.32, height-4.32), blocked=blocked,
                                 cell_size=(cw, ch), column_pitch=2.16, row_pitch=.27,
                                 origin=(4.32, 4.32))
        for rectangle in occupied:
            allocator.reserve_rectangle(rectangle)
        bank = []
        for a, b in zip(previous, following):
            target = [toward_previous*a[i] + (1-toward_previous)*b[i] + (cw/2 if i == 0 else ch/2)
                      for i in range(2)]
            points, _ = allocator.allocate(target, 1, max_radius_um=15)
            bank.append([round(float(points[0, 0]-cw/2), 6), round(float(points[0, 1]-ch/2), 6)])
        candidate = copy.deepcopy(raw)
        target = next(s for s in candidate['partition_types'][TN]['ft_slots'] if s['name'] == 'ft1')
        target['stations'] = 7
        target['bit_sites_um'].insert(1, bank)
        centre = [round(sum(p[i]+(cw/2 if i == 0 else ch/2) for p in bank)/len(bank), 6) for i in range(2)]
        target['regs_um'].insert(2, centre)
        after = S.Plan(candidate)
        new_hops = [abs(a[0]-q[0])+abs(a[1]-q[1]) for a, q, b in zip(previous, bank, following)]
        new_hops += [abs(q[0]-b[0])+abs(q[1]-b[1]) for a, q, b in zip(previous, bank, following)]
        try:
            clock = taps.report(after, TN)
        except ValueError as exc:
            attempts.append(dict(weight=toward_previous, verdict='FAIL_CLOCK_REACH', reason=str(exc)))
            continue
        if max(new_hops) > 405:
            attempts.append(dict(weight=toward_previous, verdict='FAIL_DATA_REACH', max_hop_um=max(new_hops)))
            continue
        attempts.append(dict(weight=toward_previous, verdict='PASS_MODEL'))
        break
    else:
        raise ValueError('no new bank fits frozen clock reach and existing obstacles')
    old_table, new_table = gen.latency_table(before), gen.latency_table(after)
    deltas = {lid: new_table[lid]['cycles']-old_table[lid]['cycles'] for lid in old_table
              if new_table[lid]['cycles'] != old_table[lid]['cycles']}
    assert deltas == {LANE: 1}
    assert [p['xy'] for p in original['clock']['taps']] == [p['xy'] for p in after.types[TN]['clock']['taps']]
    candidate['latency'] = dict(lanes=new_table)
    new_reset = RT.for_type(after, TN)
    assert reset['root'] == new_reset['root'] and reset['relays'] == new_reset['relays']
    return candidate, dict(status='DISABLED_MODEL_CANDIDATE', production_enabled=False,
        base_plan_digest=gen.plan_digest(raw), candidate_plan_digest=gen.plan_digest(candidate),
        part='s_4N_x06', type=TN, slot='ft1', old_stations=6, candidate_stations=7,
        inserted_internal_stage=2, added_payload_flops=276, added_epoch_flops=1,
        added_clock_sinks=277, added_epoch_reset_loads=1, added_clock_ports=0,
        added_async_reset_control_pins=1, added_async_reset_sources=0,
        packet_valid_is_inside_276_bit_bus=True, external_epoch_bit_index=276,
        old_clock=baseline_clock, candidate_clock=clock, reset_topology_unchanged=True,
        max_new_neighbor_hop_um=max(new_hops), new_bank_centre_um=centre,
        new_bit_sites_um=bank, attempts=attempts,
        lane_cycle_deltas=deltas, old_cb_cycles=old_table[LANE]['cycles'], new_cb_cycles=new_table[LANE]['cycles'],
        ca_cycles=new_table['ca__s_0N_LP__bk_sel']['cycles'], old_max_lane_cycles=max(v['cycles'] for v in old_table.values()),
        new_max_lane_cycles=max(v['cycles'] for v in new_table.values()),
        station0_and_other_existing_banks_moved=False, source_release_epochs_changed=False,
        cb_payload_and_epoch_delivery_delta_cycles=1, boot_cb_epoch_fill_delta_cycles=1,
        actual_bind_or_physical_qualification=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.resolve().is_relative_to((ROOT/'physical').resolve()):
        raise ValueError('DISABLED candidate output must be outside canonical physical/')
    if a.out.exists():
        raise FileExistsError(a.out)
    raw = json.loads(a.plan.read_text())
    candidate, report = prepare(raw)
    a.out.mkdir(parents=True)
    (a.out/'candidate_plan.json').write_text(json.dumps(candidate, separators=(',', ':'))+'\n')
    (a.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'], report['lane_cycle_deltas'], report['new_bank_centre_um'])


if __name__ == '__main__':
    main()
