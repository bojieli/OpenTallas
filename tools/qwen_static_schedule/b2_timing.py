"""Fold measured B2 hardware deltas into native events before static reservation.

The microcalendar describes ONWARD=1/PINREG=0 events. ``b2_configuration``
selects the actual hardware; head-dependent event ids explicitly identify the
word boundary and its descendants (the upstream request stays at its old edge).
Copy port events carry ``b2_copy_role`` read/write/done/active_rise/active_fall.
Their issue event carries the real cp56_hex. Copy occupancy is reserved on the
assigned copy resource, with relay ages read from a hash-bound actual graph.
Unsupported cross-clock copy transport is refused rather than counted as if all
clocks had the same period. This transformation makes no qualification claim.
"""
import copy
import json
from pathlib import Path

from .calendar import ScheduleError, sha
from . import dvm_head_onward, su_pinreg


def fold(contract, root):
    if 'b2_timing_applied' in contract or any('b2_copy_reservations' in i for i in contract['instructions']):
        raise ScheduleError('derived B2 timing/reservations cannot be supplied as input')
    cfg = contract.get('b2_configuration')
    if cfg is None:
        if any('b2' in i.get('rtl_module', '') or 'b2_head_event_ids' in i or any('b2_copy_role' in e for e in i['events'])
               for i in contract['instructions']):
            raise ScheduleError('B2 native events require explicit hardware configuration')
        return contract
    if cfg.get('base_onward') != 1 or cfg.get('base_pinreg') != 0:
        raise ScheduleError('B2 microcalendar baseline must be ONWARD1/PINREG0')
    root = Path(root)
    out = copy.deepcopy(contract)
    head = dvm_head_onward.load(root, cfg['onward'])
    su = su_pinreg.load(root, cfg['pinreg'])
    for filename in (head['basis'], su['basis']):
        if not (root / filename).is_file():
            # PINREG0 has no delta file, but ONWARD1 always has a real receipt.
            if cfg['pinreg'] == 0 and filename == su['basis']:
                continue
            raise ScheduleError('missing B2 timing receipt: '+filename)
        digest = sha(root / filename)
        if filename not in out['source_sha256'] or out['source_sha256'][filename] != digest:
            raise ScheduleError('B2 timing receipt is not source-pinned: '+filename)
    copies = [e for i in out['instructions'] for e in i['events'] if e.get('kind') == 'copy_issue']
    cp = active = 0
    if copies:
        graph = _artifact(root, cfg['allocator_graph'], out)
        stages = _artifact(root, cfg['allocator_stage_of'], out)
        cp = _route(graph, stages, cfg['copy_command_bus'], 'cp', 'source')
        active = _route(graph, stages, cfg['copy_active_bus'], 'cp_active', 'sink')
        copy_resource = cfg['copy_resource']
        if copy_resource not in out['resources'] or out['resources'][copy_resource]['capacity'] != 1:
            raise ScheduleError('B2 copy engine requires a capacity1 reservation resource')
    if cfg.get('head_clock') not in out['clocks']:
        raise ScheduleError('B2 head delivery requires its assigned source clock')
    head_period = out['clocks'][cfg['head_clock']]['period_fs']
    observed_head = False
    for impl in out['instructions']:
        ids = impl.get('b2_head_event_ids', [])
        if len(ids) != len(set(ids)) or not set(ids) <= {e['id'] for e in impl['events']}:
            raise ScheduleError('B2 head-dependent event ids are missing or duplicated')
        for e in impl['events']:
            if e['id'] in ids:
                if impl['unit'] != 1 or not e.get('rtl_port'):
                    raise ScheduleError('B2 head timing must bind an actual ME port')
                e['offset_fs'] += head['word_shift'] * head_period
                observed_head = True
        issue = [e for e in impl['events'] if e.get('kind') == 'copy_issue']
        roles = [e for e in impl['events'] if e.get('b2_copy_role')]
        if roles and len(issue) != 1:
            raise ScheduleError('B2 copy events require one actual CP56 issue')
        if not issue:
            continue
        if len(issue) != 1:
            raise ScheduleError('B2 copy implementation requires one issue event')
        e = issue[0]
        command = int(e['cp56_hex'], 16)
        beats = command >> 49
        if not 0 <= command < 1 << 56 or not command & 1 or not 1 <= beats <= 64:
            raise ScheduleError('invalid actual CP56 copy command')
        domain_name = out['resources'][copy_resource]['clock']
        # Matching nominal timing is not proof that independently named roots
        # are the same physical clock. No measured alias contract exists here.
        if domain_name != impl['clock'] or domain_name != out['resources'][e['resource']]['clock']:
            raise ScheduleError('B2 copy CDC needs an explicit measured cross-domain calendar')
        period = out['clocks'][domain_name]['period_fs']
        shifts = dict(read=su['reads'], write=su['writes'], done=su['done'],
                      active_rise=su['active_rise'], active_fall=su['active_fall'])
        for port in roles:
            role = port['b2_copy_role']
            if role not in shifts or not port.get('rtl_port'):
                raise ScheduleError('unknown/unbound B2 copy port role')
            if out['resources'][port['resource']]['clock'] != domain_name:
                raise ScheduleError('B2 copy port clock differs from the measured copy domain')
            port['offset_fs'] += shifts[role] * period
        if {p['b2_copy_role'] for p in roles} != set(shifts):
            raise ScheduleError('B2 copy calendar must cover read/write/done/active rise/fall')
        # Reserve every edge from issue through the earliest legal next issue.
        # The solver therefore moves later issues at compile time, and fixed
        # slots that overlap are refused. There is no runtime ready input.
        release = su_pinreg.next_copy_edge(0, beats, su, cp, active)
        impl['b2_copy_reservations'] = [dict(resource=copy_resource, offset_fs=e['offset_fs']+edge*period)
                                         for edge in range(release)]
    if cfg['onward'] == 2 and not observed_head:
        raise ScheduleError('ONWARD2 calendar lacks actual head-dependent ME port events')
    out['b2_timing_applied'] = dict(onward=cfg['onward'], pinreg=cfg['pinreg'], word_shift_edges=head['word_shift'],
                                    copy_done_delta=su['done'], copy_active_fall_delta=su['active_fall'],
                                    copy_command_relay_edges=cp, copy_active_relay_edges=active)
    return out


def _artifact(root, rec, contract):
    p = root / rec['path']
    if not p.is_file() or sha(p) != rec['sha256'] or contract['source_sha256'].get(rec['path']) != rec['sha256']:
        raise ScheduleError('actual B2 allocation artifact missing/changed/unpinned: '+rec['path'])
    return json.loads(p.read_text())


def _route(graph, stages, bid, port, side):
    buses = [b for b in graph['buses'] if b[0] == bid]
    if len(buses) != 1 or bid not in stages:
        raise ScheduleError('actual copy route/stage record missing: '+bid)
    end = buses[0][3][0 if side == 'source' else -1]
    if end[1] != port or type(stages[bid]) is not int or stages[bid] < 1:
        raise ScheduleError('copy route pin/stage identity mismatch: '+bid)
    return stages[bid]-1
