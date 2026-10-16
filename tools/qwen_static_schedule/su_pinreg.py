"""SU (qfd_sp_su64_sfu) PINREG=1 schedule contract for the static compiler (Q-B2r 2026-10-16).

Source of truth: the SU owner's measured differential bench, recorded as
results/rtl/qwen_su64_pinreg_1016/schedule_delta.json (schema opentallas.qwen.schedule-delta.v1, master
qfd_sp_su64_sfu; branch claude/qelem-suc-1016).  This module never hard-codes a delta: a missing / foreign file is an
error, never a silent zero.  It turns the per-contract deltas into the fixed windows the compiler must reserve.

Copy unit (rtl/qwen_split/qfd_su_static_copy.sv, READ_EDGES = 15 at PINREG=0), edges counted from the SU-pin edge E
that samples the copy command cp (all at the SU die pins, SU clock edges):
    va read beats      E+1+r .. E+B+r              (B = cp beats, r = reads delta)
    va / xsw writes    E+R+2+w .. E+R+B+1+w        (R = 15, w = writes delta)
    cp_done            E+R+B+2+d
    cp_active high     E+a_rise .. E+R+B+1+a_fall  (inclusive; low again from edge E+R+B+2+a_fall)
At PINREG=1 the measured deltas are reads +2, writes +3, cp_done +2, cp_active rise +1 / fall +2 (copy start +1).
The decomposition is checked: reads = start + 1 (va pin register), writes = reads + 1 (READ_EDGES 15 -> 16),
cp_done = start + 1 (pin register), cp_active rise = start, fall = start + 1.

Controller back-to-back copy rule (ot_qfd_tt_ctlm_split_static: cp_available = !cp_active_q, cp_active_q is one
register on the controller root): a copy issued at controller edge c reaches the SU after cp_relay edges; the next copy
may issue at controller edge c2 only when cp_active_q is already low:
    c2 >= c + cp_relay + (R + B + 1 + a_fall) + 1 + cp_active_relay + 1
Relay edges are the die allocator's ages (allocator_stage_of), passed in, never assumed.

Other contracts: embedding requests external_a_re/addr reach seq_su one edge EARLIER (-1; answers keep their latency
relative to the request); status sd is +1 edge (status only, never a schedule input); SU op latency 0.
"""
import json
from pathlib import Path

from .calendar import ScheduleError

ROOT = Path(__file__).resolve().parents[2]
DELTA = 'results/rtl/qwen_su64_pinreg_1016/schedule_delta.json'
SCHEMA = 'opentallas.qwen.schedule-delta.v1'
READ_EDGES = 15  # qfd_su_static_copy default at PINREG=0 (rtl/qwen_split/qfd_sp_su64_sfu.sv u_copy)

_KEYS = {
    'start': 'copy command cp -> copy start',
    'reads': 'copy VM read beats at va (from cp)',
    'writes': 'copy VM write beats at va / xsw copy beats (from cp)',
    'done': 'cp_done (from cp)',
    'active': 'cp_active',
    'embed': 'embedding requests (external_a_re/addr)',
    'status': 'status sd (fault, rows, progress, kv_we copy, idle, ready, inflight, active)',
}


def load(root=ROOT, pinreg=1):
    """deltas of the SU PINREG configuration the die instance uses (pinreg 0 -> all zero by construction)"""
    if pinreg not in (0, 1):
        raise ScheduleError('SU PINREG must be 0 or 1')
    if pinreg == 0:
        return dict(pinreg=0, start=0, reads=0, writes=0, done=0, active_rise=0, active_fall=0, embed=0, status=0,
                    su_op=0, basis='PINREG=0: source default, no pin registers')
    f = Path(root) / DELTA
    if not f.is_file():
        raise ScheduleError(f'SU PINREG=1 schedule delta missing: {DELTA} (claude/qelem-suc-1016)')
    d = json.loads(f.read_text())
    if d.get('schema') != SCHEMA or d.get('master') != 'qfd_sp_su64_sfu':
        raise ScheduleError(f'{DELTA}: unknown schema / master')
    by = {c.get('contract'): c for c in d.get('contracts', [])}
    out = dict(pinreg=1, basis=DELTA)
    for k, name in _KEYS.items():
        c = by.get(name)
        if c is None or type(c.get('delta')) is not int:
            raise ScheduleError(f'{DELTA}: contract {name!r} missing or not an integer delta')
        out[k] = c['delta']
    note = by[_KEYS['active']].get('note', '')
    # "rises +1, falls +2": the fall moves one edge more than the rise (one edge longer copy pipe)
    import re
    m = re.search(r'rises \+(\d+), falls \+(\d+)', note)
    if not m:
        raise ScheduleError(f'{DELTA}: cp_active rise/fall edges not recorded')
    out['active_rise'], out['active_fall'] = int(m[1]), int(m[2])
    del out['active']
    if type(d.get('su_op_latency_delta')) is not int:
        raise ScheduleError(f'{DELTA}: su_op_latency_delta missing')
    out['su_op'] = d['su_op_latency_delta']
    s = out['start']
    if not (out['reads'] == s + 1 and out['writes'] == out['reads'] + 1 and out['done'] == s + 1
            and out['active_rise'] == s and out['active_fall'] == s + 1):
        raise ScheduleError(f'{DELTA}: deltas do not decompose into cp pin register + va pin register + READ_EDGES+1')
    return out


def copy_windows(beats, delta):
    """SU-pin edge offsets (from the edge that samples cp) of one copy of `beats` 64-lane beats"""
    if type(beats) is not int or not 1 <= beats <= 64:
        raise ScheduleError('copy beats must be 1..64 (CP56 [55:49])')
    R, B = READ_EDGES, beats
    return dict(reads=(1 + delta['reads'], B + delta['reads']),
                writes=(R + 2 + delta['writes'], R + B + 1 + delta['writes']),
                done=R + B + 2 + delta['done'],
                active=(delta['active_rise'], R + B + 1 + delta['active_fall']))


def next_copy_edge(issue_edge, beats, delta, cp_relay, cp_active_relay):
    """earliest controller edge for the next copy after one issued at issue_edge (cp_available = !cp_active_q)"""
    for n, v in (('cp_relay', cp_relay), ('cp_active_relay', cp_active_relay)):
        if type(v) is not int or v < 0:
            raise ScheduleError(f'{n}: die-assigned relay edges must be a non-negative integer')
    w = copy_windows(beats, delta)
    return issue_edge + cp_relay + w['active'][1] + 1 + cp_active_relay + 1


def check_copies(copies, delta, cp_relay, cp_active_relay):
    """copies: [(controller_edge, beats)] in issue order -> raise on a copy issued while the unit is still reserved"""
    prev = None
    for edge, beats in sorted(copies):
        if prev is not None:
            need = next_copy_edge(prev[0], prev[1], delta, cp_relay, cp_active_relay)
            if edge < need:
                raise ScheduleError(f'copy at controller edge {edge} overlaps the SU copy reservation of the copy at '
                                    f'{prev[0]} ({prev[1]} beats): earliest {need} (PINREG={delta["pinreg"]})')
        prev = (edge, beats)
    return True
