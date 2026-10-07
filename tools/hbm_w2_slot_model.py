#!/usr/bin/env python3
"""Price an independent W2 reservation; never claim an unbound slot is routed."""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_accel_die_fp as H


def report():
    base = H.build(H.R24F)
    candidate = H.build(H.R24W)
    slot = next(i for i in candidate['insts'] if i.name == 'hb_w2_sender')
    area = slot.w * slot.h
    bits = 2 * 64 * 544
    pitch = H.Q.TRK['M6'][1]
    # Two signal tracks per bit; reserve both directions plus feedback on the face.
    signal_bits = 2 * 1090
    capacity = int(slot.h / (2 * pitch))
    baseline = {i.name: i.box() for i in base['insts']}
    changed = [i.name for i in candidate['insts'] if i.name in baseline and i.box() != baseline[i.name]]
    actual_sm = (3075.84, 1131.84)
    old = base['geo']
    # Three columns / three rows retain eight actual SMs in each group, with
    # the ninth site empty. This is a sizing alternative, not a wired netlist.
    group_w = 3 * (actual_sm[0] + H.SHAVE) + 4 * H.CH
    group_h = 3 * (actual_sm[1] + H.SHAVE) + 3 * H.CH
    retile_w = old['W'] + 2 * (group_w - old['grp_w'])
    retile_h = old['H'] + 2 * (group_h - old['grp_h'])
    return dict(status='candidate-unbound-reservation', selected=False,
        source_sha256=hashlib.sha256(Path(H.__file__).read_bytes()).hexdigest(),
        slot=dict(instance=slot.name, box_um=slot.box(), area_um2=area,
                  target_utilization=.55, cell_budget_um2=.55*area,
                  storage_bits=bits, storage_flop_lower_bound_um2=21896,
                  capture_successor_flop_mux_subtotal_um2=63594.22752,
                  remaining_decode_clock_repair_budget_um2=.55*area-63594.22752,
                  cell_budget_after_storage_um2=.55*area-21896,
                  domain='stream_1p2', MACs_per_cycle=0,
                  input_bits_per_cycle=1090, output_bits_per_cycle=1090,
                  fifo_write_bytes_per_cycle=136, fifo_read_bytes_per_cycle=136,
                  capture_added_cycles=1, additional_latency='relay hops pending placed boundary contract'),
        tracks=dict(north_arrival_bits=1090, south_send_bits=1090,
                    north_south_layer='M5', north_south_pitch_um=H.Q.TRK['M5'][1],
                    north_south_capacity_bits_per_face=int(slot.w/(2*H.Q.TRK['M5'][1])),
                    north_south_signal_window_um=1090*2*H.Q.TRK['M5'][1],
                    reducer_box_um=next(i.box() for i in candidate['insts'] if i.name=='hb_su_red'),
                    intervening_divider_box_um=next(i.box() for i in candidate['insts'] if i.name=='hb_su_full'),
                    route_requirement='sender to reducer must detour around occupied divider; no straight-line latency credit',
                    layer='M6', pitch_um=pitch, tracks_per_bit=2,
                    face_capacity_bits=capacity, payload_bits_both_directions=signal_bits,
                    feedback_spare_bits=capacity-signal_bits,
                    scope='local face capacity only; shared die corridor occupancy unproven'),
        legality=H.legality(candidate), changed_existing_instances=changed,
        die_area_delta_um2=0,
        actual_sm=dict(width_um=actual_sm[0], height_um=actual_sm[1],
            rejected_4x2_outline_um=[37578.384,20863.44],
            legal_outline_limit_um=[33000,26000],
            candidate_3x3_group_um=[group_w,group_h],
            candidate_3x3_outline_um=[retile_w,retile_h],
            active_sms_per_group=8, empty_sites_per_group=1, total_sms=32,
            candidate_outline_fits=retile_w<=33000 and retile_h<=26000,
            additional_dies_for_capacity=0,
            scope='sizing only; HBM PHY clearance, complete legal placement, network remapping and latency remain required'),
        remaining_gates=['full sender cell inventory including mux/control/capture and physical repair',
          'actual wrapper pins, clock/reset and credit boundary mapped to die nets',
          'shared corridor capacity and hop/round-trip/token composition',
          'source-pinned exactness/negative gates and admitted SS/FF route with DRC0',
          'SM 3x3 physical remapping preserves all eight SM identities and actual ports'])

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True)
    a=ap.parse_args();p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    r=report();p.write_text(json.dumps(r,indent=2)+'\n')
    assert r['legality']['overlaps']==r['legality']['outside']==0
    assert not r['changed_existing_instances']
    assert r['tracks']['feedback_spare_bits']>0
    print(json.dumps(r,indent=2))
