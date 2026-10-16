"""Opt-in qbank S hard-frame geometry; default source geometry is untouched.

The actual S25.92um/N8.64um leaves need S19.44um/N2.16um beyond
the nominal 6.48um reservations. Only q slots grow, with canonical frame tops
fixed. Every element and its N bank translate together; cfg7 ROM/sequencer rows
move below the enlarged S bank. This is source geometry, never adoption proof.
"""
from __future__ import annotations
import copy
import hashlib
from collections import Counter

OLD_BANK_H = 6.48
HARD_BANK_H = 25.92
N_BANK_H = 8.64
EXTRA = round(HARD_BANK_H - OLD_BANK_H, 6)
N_EXTRA = round(N_BANK_H - OLD_BANK_H, 6)
SLOT_EXTRA = round(EXTRA + N_EXTRA, 6)


def slot_extra(kind, enabled):
    return SLOT_EXTRA if enabled and kind == 'q' else 0.0


def canonical(d, *, cfifo_h, pq_root_h=0.0):
    """Return a new source layout, keeping frame tops and all population IDs.

    The first/between street allocations are recomputed from real coordinates.
    A smaller allocation is legal only if the actual FIFO/root stack and the
    existing roadmap's 79.8um x-entry row still fit. Full neighbour/incident proof
    remains separate; this function does not waive a physical checker.
    """
    assert 'qbank_hard_frame' not in d, 'qbank frame transform already applied'
    out = copy.deepcopy(d)
    transforms = []
    for f in out['placements']:
        old = copy.deepcopy(f)
        qslots = {int(e[2]) for e in f['packed_elements'] if e[1] == 'q'}
        kinds = {}
        for e in f['packed_elements']:
            s, k = int(e[2]), e[1]
            assert s not in kinds or kinds[s] == k, ('mixed-kind slot', f['root'], s)
            kinds[s] = k
        delta = round(len(qslots) * SLOT_EXTRA, 6)
        assert abs(sum(f['slot_heights_um']) - f['height_um']) < .001
        f['origin_um'][1] = round(f['origin_um'][1] - delta, 6)
        y = 0.0
        for s, h in enumerate(old['slot_heights_um']):
            f['slot_offsets_um'][s] = round(y, 6)
            f['slot_heights_um'][s] = round(h + (SLOT_EXTRA if s in qslots else 0), 6)
            y += f['slot_heights_um'][s]
        f['height_um'] = round(y, 6)
        f['outline_um'][1] = f['height_um']
        assert abs(f['origin_um'][1] + f['height_um'] - old['origin_um'][1] - old['height_um']) < .001
        transforms.append(dict(root=f['root'], old_origin=old['origin_um'], new_origin=f['origin_um'],
                               old_height=old['height_um'], new_height=f['height_um'],
                               q_slots=sorted(qslots), extra_um=delta,
                               old_offsets=old['slot_offsets_um'], new_offsets=f['slot_offsets_um']))
    minimum = max(float(cfifo_h) + float(pq_root_h) + 4.32, 79.8 + 4.32)
    streets = []
    for col in out['columns']:
        previous = float(col['y0_um'])
        fs = sorted((f for f in out['placements'] if abs(f['origin_um'][0] - col['x_um']) < .001),
                    key=lambda f: f['origin_um'][1])
        for f in fs:
            available = round(f['origin_um'][1] - previous, 6)
            assert available >= minimum - .001, ('qbank frame street cannot fit actual stack', f['root'], available, minimum)
            streets.append(dict(root=f['root'], y0=previous, y1=f['origin_um'][1], available_um=available, required_um=minimum))
            previous = f['origin_um'][1] + f['height_um']
        assert previous <= col['y1_um'] + .001, ('qbank frame outside column', col['x_um'], previous, col['y1_um'])
    # canonical_layout.geometry historically asserts its allocation's first
    # channel as a minimum. Replace that accounting value with the measured
    # candidate allocation, after the actual-stack check above.
    out['interframe_channels_um'] = dict(out['interframe_channels_um'], first=min(s['available_um'] for s in streets))
    out['frames'] = {f['root']: f for f in out['placements']}
    out['fields_reserved_area_mm2'] = sum(f['outline_um'][0] * f['height_um'] for f in out['placements']) / 1e6
    histogram = Counter((f['pair_count'], f['bf'], f['packed_slots'], f['height_um']) for f in out['placements'])
    out['frame_histogram'] = [dict(pair_count=p, bf=b, slots=s, height_um=h, roots=n)
                              for (p,b,s,h),n in sorted(histogram.items())]
    out['status'] = 'SOURCE_CANDIDATE_REQUIRES_FULL_REPLAN'
    out['scope'] = 'Qbank actual-size source candidate; coarse frame/pin checks only, NOT full GEN/native routing/latency qualification.'
    out['qbank_hard_frame'] = dict(scope='SOURCE_CANDIDATE_NOT_INTEGRATED', bank_nominal_height_um=dict(S=HARD_BANK_H, N=N_BANK_H),
                                  extra_per_q_slot_um=SLOT_EXTRA, frame_tops_preserved=True,
                                  old_reserved_area_mm2=d['fields_reserved_area_mm2'],
                                  new_reserved_area_mm2=out['fields_reserved_area_mm2'],
                                  old_status=d.get('status'),
                                  normal_data_cycles_added=0, transforms=transforms, streets=streets,
                                  obligations=['actual per-bit LEF endpoint mapping/chirality', 'all neighbours and other-face cuts',
                                               'source-current full GEN clock/reset/hop replan', 'native/TT-setup/FF-hold/DRC0 integration'])
    return out


def require_replan(*, hop_fix, hop_iter, col_reset_tree, rly_face_pins, reset_leaf):
    """A frame candidate cannot reuse old relay/reset placement or old RTL."""
    assert hop_fix and hop_iter >= 2, 'qbank frame requires fresh iterative hop/relay replan (--hop-fix --hop-iter >=2)'
    assert col_reset_tree > 0, 'qbank frame requires fresh final column reset tree'
    assert rly_face_pins, 'qbank frame requires final actual incident relay-face assignment'
    assert reset_leaf, 'qbank frame requires --qbank-s-rstreg matching qualified nr1 RTL'


PINNED_VIEWS = {
    'dsfd_qbank_S': ('s81fill2_qbank_s_t-nr1-a0a4982dd', 60.48, 25.92, '05f344c239556e4ca1be92cdc69d835fd6e93a5ca3dc1fd88cac4d3e78377f03'),
    'dsfd_qbank_N': ('s81fill2_qbank_n-g1-7b1c80004', 60.48, 8.64, 'f0d203bb65221c658d9d80cade7b73d0505b7f906679c027ee3839220f7c4c2b'),
}

def require_bank_views(views):
    """This opt-in profile is pinned to actual reviewed leaves, not an old alias."""
    for master,(job,w,h,digest) in PINNED_VIEWS.items():
        assert master in views, ('qbank hard frame missing actual view', master)
        v=views[master]
        assert v.get('job')==job, ('qbank hard frame stale/different view job', master, v.get('job'), job)
        assert abs(v['w']-w)<1e-7 and abs(v['h']-h)<1e-7, ('qbank hard frame incorrect actual SIZE',master)
        assert hashlib.sha256(v['text'].encode()).hexdigest()==digest, ('qbank hard frame actual LEF differs',master)
