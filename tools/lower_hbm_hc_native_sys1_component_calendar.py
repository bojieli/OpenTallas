#!/usr/bin/env python3
"""One preinstalled SYS1 MTP row/tail image with explicit pipeline cost."""
from lower_hbm_hc_sys1_mtp_static_calendar import lower_sys1
from lower_hbm_hc_tail_loop_calendar import lower_tail_loop


def lower_native_sys1(*, npos, first_row_consumer_cycle,
                      first_tail_consumer_cycle, sink_divisor=7,
                      sink_phase=0, sys_latency=86):
    if npos not in (6, 8):
        raise ValueError('SYS1 MTP supports6/8 positions only')
    row, rm = lower_sys1('row', first_consumer_cycle=first_row_consumer_cycle,
                         sink_divisor=sink_divisor, sink_phase=sink_phase,
                         npos=npos, early=True, clear=True,
                         sys_latency=sys_latency)
    if first_tail_consumer_cycle < first_row_consumer_cycle + 24 * len(row):
        raise ValueError('tail overlaps projection programme')
    tail, tm = lower_tail_loop(first_consumer_cycle=first_tail_consumer_cycle,
                               sink_divisor=sink_divisor,
                               sink_phase=sink_phase, npos=npos)
    base = len(row)
    tail = [(w & ((1 << 223) - 1)) | (0xc7a1 << 240) | ((base + i) << 223)
            for i, w in enumerate(tail)]
    words = row + tail
    if len(words) > 2048:
        raise ValueError('actual two-page programme capacity')
    return words, {
        'positions': npos, 'rows': 24, 'configuration_words': len(words),
        'programme_pages': 2, 'SYS_LAT': sys_latency,
        'additional_pipeline_cycles': sys_latency - 33,
        'row': {'start_base': 0, 'start_limit': base, 'start_loops': 24,
                'ROW_LOOP': 1, 'body_cycles': base,
                'events_relative_consumer0': rm['events_relative_consumer0']},
        'tail': {'start_base': base, 'start_limit': len(words),
                 'start_loops': npos, 'TAIL_LOOP': 1, 'body_cycles': len(tail),
                 'events_relative_consumer0': tm['events_relative_consumer0']},
        'first_row_consumer_cycle': first_row_consumer_cycle,
        'first_tail_consumer_cycle': first_tail_consumer_cycle,
        'sink_divisor': sink_divisor, 'sink_phase': sink_phase,
        'reconfigure_between_components': False,
        'canonical_G25_P1_qualified': False,
        'scope': 'Prepared SYS1 MTP component image; requires actual engine and native joined verdict, separate physical qualification'}
