"""PW image for the actual qfd_seq_su collective command calendar.

Events must name their real producer and actual collective core command edge (after its new pin register).
Tags store segment6 only; the actual receiver joins accepted token18/position8.
No observation traces or readiness values choose issue times.
"""
from .calendar import ScheduleError
BASE = 944
DEPTH = 8


def pw_image(events, stage_start_cycle, relay_edges, stop_cycle, program_words, command_pin_edges=1):
    if not 0 < program_words < 60:
        raise ScheduleError('native instructions overlap reserved PW944 collective window')
    if stage_start_cycle < 0 or relay_edges < 0 or stop_cycle < 2 or command_pin_edges != 1:
        raise ScheduleError('invalid actual stage/relay/stop calendar')
    if not 0 <= len(events) < DEPTH:
        raise ScheduleError('collective calendar requires at most seven actual commands plus END')
    out = []
    previous = 1
    for k, event in enumerate(events):
        if not event.get('rtl_instance') or not event.get('rtl_module'):
            raise ScheduleError('collective command lacks actual producer attribution')
        cycle = event['core_cmd_cycle'] - stage_start_cycle - relay_edges - 1 - command_pin_edges
        words, mode, tag = event['words'], event['mode'], event['tag']
        if not previous < cycle < stop_cycle or not 0 < words < 65536 or mode not in (0, 1) or not 0 <= tag < 3:
            raise ScheduleError('collective command exceeds counter/descriptor/ordering bounds')
        out.extend([dict(address=BASE+2*k, data_hex=f'{cycle | words<<32 | mode<<48:016x}'),
                    dict(address=BASE+2*k+1, data_hex=f'{tag:016x}')])
        previous = cycle
    k = len(events)
    out.extend([dict(address=BASE+2*k, data_hex=f'{stop_cycle | 1<<49:016x}'),
                dict(address=BASE+2*k+1, data_hex='0000000000000000'),
                dict(address=BASE+2*DEPTH, data_hex=f'{0x434c<<48 | (k+1)<<32 | stop_cycle:016x}')])
    return out
