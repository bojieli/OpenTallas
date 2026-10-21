"""Build real forwarded delay frames for measured early-write ring overruns.

Input is an existing failed die STA land plan. This is hardware planning, not
a new verdict or a replacement for STA on the changed source and geometry.
"""
import hashlib
import json
import math
from pathlib import Path


def reserve(model, buses, plans, pads, path, depth=4):
    source = Path(path)
    plan = json.loads(source.read_text())
    period = float(plan['T_ps'])
    current = {bid: (idx, eps) for idx, (bid, cls, bits, eps) in buses}
    rows, absent = [], []
    for row in plan['links']:
        if row.get('window_ok') is not False or not row.get('h0'):
            continue
        bid = row['bid']
        if bid not in current:
            absent.append(bid)
            continue
        idx, eps = current[bid]
        if len(eps) != 2:
            raise ValueError(f'forward phase transport {bid}: requires one real producer and receiver')
        residual = int(row['E'])
        deficit = max(0.0, max(-float(h) - (depth-residual)*period for h in row['h0'].values()))
        if deficit <= 0:
            continue
        # Every pair of half-cycle stations is a real whole-period delay.
        # Provision one extra period for the n=1 -> multi-frame topology and
        # the default E_sta=2 vs the old clamped E=1 residual. This is priced
        # hardware, not a relaxed timing margin or a larger ring.
        cycles = math.ceil(deficit/period) + 1
        frames = 2*cycles
        setup_remaining = {corner: float(s)-cycles*period for corner,s in row.get('s1',{}).items()}
        if setup_remaining and min(setup_remaining.values()) < 0:
            raise ValueError(f'forward phase transport {bid}: no recorded setup room for {cycles} real delay periods')
        before = len(plans.get(idx, {}).get('frames', [])) + int(pads.get(bid,0))
        pads[bid] = int(pads.get(bid,0)) + frames
        rows.append(dict(bid=bid, source=list(eps[0]), receiver=list(eps[1]),
                         previous_frames=before, added_half_cycle_frames=frames,
                         physical_delay_periods=cycles, ring_depth=depth,
                         old_h0_ps=row['h0'], old_s1_ps=row.get('s1',{}),
                         old_residual_E=residual, old_deficit_ps=round(deficit,3),
                         new_source_qualified=False))
    record = dict(schema='opentallas.qwen.forward-phase-transport.v1',
                  source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  recorded_period_ps=period, fixed_native_ring_depth=depth,
                  requests=rows, absent_from_changed_source=absent,
                  added_frames=sum(r['added_half_cycle_frames'] for r in rows),
                  implementation='existing occupied-site-aware tree-pad allocator; forwarded-clock station hardware',
                  calendar='GEN actual fwd E and bundle equalization plus final reset K straps; compiler recomposition owed',
                  qualification='SOURCE_CHANGED: old STA is planning input only; intended new GEN/GRT/STA required')
    model['fwd_phase_transport'] = record
    return record
