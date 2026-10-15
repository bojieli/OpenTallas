#!/usr/bin/env python3
"""Versioned SYS1 MTP component calendar; latency is a measured input.

The default86 is a candidate pending the actual SYS1 arithmetic gate. This
retimes the legacy33-cycle systolic result path by53 real pipeline cycles;
it does not change the weight-prefetch component's1080/1400 price receipts.
"""
from lower_hbm_hc_mtp_static_calendar import lower as legacy_lower, pack


def lower_sys1(kind, *, first_consumer_cycle, sink_divisor, sink_phase,
               row=0, slot=0, eps=0x358637bd, clear=False, npos=8,
               tail_position=0, early=False, sys_latency=86):
    if sys_latency < 33:
        raise ValueError('SYS1 latency cannot precede the legacy33-cycle path')
    if kind == 'row' and npos not in (6, 8):
        raise ValueError('separate SYS1 MTP6/8 profile; canonical P1 not qualified')
    words, meta = legacy_lower(kind, first_consumer_cycle=first_consumer_cycle,
                              sink_divisor=sink_divisor, sink_phase=sink_phase,
                              row=row, slot=slot, eps=eps, clear=clear, npos=npos,
                              tail_position=tail_position, early=early)
    delta = sys_latency - 33
    if kind == 'row':
        events = meta['events_relative_consumer0']
        payload = [pack(norm_eps=eps, row_weight_slot=slot, row_id=row,
                        row_npos=npos) for _ in range(len(words) + delta)]
        payload[0] |= pack(row_launch=1, clear=int(clear))
        ss = [c + delta for c in events['raw_ss']]
        rr = [c + delta for c in events['raw_row']]
        for cycle in ss + rr:
            payload[cycle] |= pack(row_raw_read=1)
        words = [(0xc7a1 << 240) | (pc << 223) | p for pc, p in enumerate(payload)]
        meta['start_limit'] = len(words)
        meta['events_relative_consumer0'] = {
            'launch': 0, 'raw_ss': ss, 'raw_row': rr,
            'results': [c + 5 for c in rr], 'next_row_earliest': len(words)}
    meta.update({'SYS_LAT': sys_latency, 'legacy_SYS_LAT': 33,
                 'additional_pipeline_cycles': delta,
                 'calendar_profile': 'SYS1_MTP6_8_candidate_pending_actual_arithmetic',
                 'canonical_G25_P1_qualified': False,
                 'scope': 'Versioned SYS1 component schedule; measured arithmetic, full native composition and physical phase proof required'})
    return words, meta
