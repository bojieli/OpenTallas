"""Size a generated KV START/reset relay graph before physical implementation.

This infrastructure-only candidate does not qualify calendars or token latency.
The emitted stage manifest includes reset-wave registers in each stage's flops.
"""
from collections import Counter


def model(stages, bound, baseline=None):
    ss = stages['stages']
    indexed = {s['region']: s for s in ss}
    pairs = []
    for dst in ss:
        src = indexed.get(dst['parent'])
        if src is not None:
            distance = sum(abs(a-b) for a, b in zip(src['rect_um'][:2], dst['rect_um'][:2]))
            pairs.append(distance)
    flops = sum(s['flops'] for s in ss)
    resets = sum(s.get('reset_flops', 0) for s in ss)
    ff_area_floor = flops * stages['flop_w_um'] * 0.27
    delta = Counter()
    if baseline is not None:
        old = baseline.get('count_aligned', baseline)['ports']
        assert set(bound['ports']) == set(old), 'Selected crossing identities changed'
        for name, row in bound['ports'].items():
            assert row['depth'] == old[name]['depth'], (name, 'depth changed')
            assert row.get('freg', 0) == old[name].get('freg', 0), (name, 'FREG changed')
            delta[row['sched_lat'] - old[name]['sched_lat']] += 1
    return dict(
        schema='opentallas.uarch.kv-start-relay.v1', build_ready=not any(d > 405 for d in pairs),
        scope='Infrastructure candidate; boundary placement, mapped timing and calendar consumer qualification pending',
        macs_per_cycle=0, compute_intensity=0, memory_bytes_per_cycle=0,
        stage_replicas=len(ss), flops=flops, reset_flops=resets, mission_flops=flops-resets,
        stage_boundary_bits_per_cycle=dict(start=1, reset=1),
        internal_boundaries=len(pairs), data_tracks_per_boundary=2,
        clock_tracks='Use the existing measured tree; additional fanout must be measured with real mapped cells',
        ff_area_floor_um2=round(ff_area_floor, 6),
        floorplan_slot_fit='Emitted legal SiteMap homes; mapped combinational cells and PDN pending',
        mux_demux='No data mux/demux; parent result fans out to its named child stages',
        max_stage_fanout=max((len(s.get('children', [])) for s in ss), default=0),
        wire_anchor_sum_um=sum(pairs), max_stage_hop_um=max(pairs, default=0),
        stage_hops_over405=sum(d > 405 for d in pairs),
        startup_max_origin_cycles=bound['report']['max_origin_cycles'],
        selected_crossings=len(bound['ports']), schedule_delta_histogram=dict(delta),
        token_latency='Must compose changed scheduler dates and START origins in the consumer before adoption',
        physical_timing='NOT RUN', consumer_qualified=False,
    )
