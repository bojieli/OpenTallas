#!/usr/bin/env python3
"""Lower declared native reducer exports into distinct COLL and RF reservations.

Edges are sampled edges, not post-edge updates. A qcore command E produces
scalar pins after E+11; cxport and the first RF relay sample those pins E+12.
This join emits control only. It neither supplies arithmetic results nor proves
the upstream reducer operands or the downstream collective programme.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = 'rtl/hbm_accel/generic/adapters/static_su/'
SOURCES = [S+'top/ot_hbm_su_static_qcore.sv',
           S+'collport/ot_hbm_su_static_cxport.sv',
           S+'top/ot_hbm_su_static_top.sv',
           S+'reduction/ot_hbm_su_reduce_static.sv']


class CalendarError(ValueError):
    pass


def lower(plan):
    """Plan: exports {quarter, command_edge, source_addr, source_ready_serial, carry_word,
    emit?, collective_tag?, return_destination?, lp_sample_stream?, rf_addr?};
    returns {quarter, tag, coll_update_stream, relay_stages?}.
    carry_word None means RF-only. Every emitted packet must contain 8 native
    scalar exports since the previous EMIT. RF writes broadcast to all quarters.
    """
    if plan.get('rf_relay') != 36:
        raise CalendarError('current RF route requires exactly 36 serial stages')
    resources = {}
    events = []
    pending = {}
    words = {q: set() for q in range(4)}
    def reserve(unit, edge, ident):
        key = (unit, edge)
        if key in resources:
            raise CalendarError(f'collision {unit} edge {edge}: {resources[key]} / {ident}')
        resources[key] = ident
    # Merge both event kinds by actual serial processing edge, allowing a
    # returned tag to be reused at that same edge as the RTL explicitly does.
    work = []
    for i, x in enumerate(plan['exports']):
        work.append((x['command_edge']+13, 1, i, x))
    for i, x in enumerate(plan.get('returns', [])):
        a = x['coll_update_stream']+1+x.get('relay_stages', 0)
        if a % 4 == 2:
            raise CalendarError('return lands on forbidden stream phase 2')
        work.append(((3*a+6)//4, 0, i, x))
    for edge, kind, i, x in sorted(work, key=lambda v: v[:3]):
        q = x['quarter']
        if not 0 <= q < 4:
            raise CalendarError('quarter outside native four quarters')
        if kind == 0:
            tag = x['tag']
            if (q, tag) not in pending:
                raise CalendarError('return has no outstanding native carry tag')
            dest, lp = pending.pop((q, tag))
            if x['coll_update_stream'] < lp:
                raise CalendarError('return precedes collective sampling of native carry')
            # cxport rr_wv at n; qcore samples n+1; RF commits n+2.
            for bank in range(8*(dest & 7), 8*(dest & 7)+8):
                reserve(f'q{q}.rf.bank{bank}.write_pins', edge+1, f'rr{i}')
            events.append(dict(kind='return', quarter=q, tag=tag,
                               rr_register_serial=edge, rf_commit_serial=edge+2))
            continue
        e, addr = x['command_edge'], x['source_addr']
        if e < 0 or not 0 <= addr < 1024:
            raise CalendarError('invalid reducer command edge/address')
        if 'source_ready_serial' not in x or x['source_ready_serial'] > e:
            raise CalendarError('missing/late upstream native reducer readiness reservation')
        reserve(f'q{q}.reducer.command', e, f'export{i}')
        tag = 0
        rf_addr = x.get('rf_addr')
        if rf_addr is not None:
            if not 0 <= rf_addr < 256:
                raise CalendarError('RF address outside 256 native words')
            tag |= 0x100 | rf_addr
            # scalar is sampled by first relay at E+12; RF pins E+48;
            # internal RF input register then commits E+49.
            for destq in range(4):
                reserve(f'q{destq}.rf.bank{rf_addr & 63}.write_pins', e+48,
                        f'export{i}')
        w = x.get('carry_word')
        if w is not None:
            if not 0 <= w < 8 or w in words[q]:
                raise CalendarError('invalid/repeated word in native carry packet')
            words[q].add(w)
            tag |= (1 << 9) | (w << 10)
        event = dict(kind='export', quarter=q, command_serial=e,
                     scalar_capture_serial=e+12,
                     rf_commit_serial=e+49 if rf_addr is not None else None)
        if x.get('emit', False):
            if words[q] != set(range(8)):
                raise CalendarError('EMIT requires all eight native carry words')
            words[q].clear()
            ct = x['collective_tag']
            if not 0 <= ct < 8:
                raise CalendarError('collective tag outside native eight tags')
            # cxport processes at m=E+13; base rc register update is ceil((4m+3)/3).
            base = (4*edge+5)//3
            lp = x['lp_sample_stream']
            late = lp-1-x.get('carry_relay_stages', 0)-base
            if late not in (0, 1):
                raise CalendarError('collective lp slot cannot be reached by native LATE bit')
            rc = base+late
            reserve(f'q{q}.cxport.rc_register', rc, f'export{i}')
            reserve(f'q{q}.coll.lp_sample', lp, f'export{i}')
            tag |= (1 << 13) | (ct << 14) | (late << 17)
            if 'return_destination' in x:
                dest = x['return_destination']
                if not 0 <= dest < 32 or (q, ct) in pending:
                    raise CalendarError('invalid destination or outstanding native tag reused')
                pending[q, ct] = (dest, lp)
                tag |= (1 << 23) | (dest << 18)
            event.update(rc_update_stream=rc, lp_sample_stream=lp,
                         late=late, collective_tag=ct)
        elif 'return_destination' in x:
            raise CalendarError('return destination requires EMIT')
        event.update(tag=tag, red_cmd_hex=f'{(1<<73)|(4<<70)|(addr<<60)|(tag<<8):019x}')
        events.append(event)
    if any(words.values()) or pending:
        raise CalendarError('unfinished native carry packet or outstanding return')
    return dict(schema='opentallas.hbm.su.red_carry_calendar.v1',
                events=events, reservations=[dict(unit=k[0], edge=k[1], identity=v)
                                             for k,v in sorted(resources.items())],
                source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()
                               for s in SOURCES},
                scope='control lowering and resource reservations; no arithmetic substitution',
                whole_layer_native_qualified=False, physical_qualified=False,
                production_rate_qualified=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    result = lower(json.loads(args.plan.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
