#!/usr/bin/env python3
"""Production Q readiness evidence. Transport ages alone never admit SAFE2 prefetch."""
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qwen_split'))
import lane_latency_audit as LA
import lane_groups as LG

PATHS = (
    ('dvw_dd_wo', 'dvs_W5', 'dd_wo', 'native59', 'dd_i'),
    ('sf_q_slot', 'sys_face', 'q_slot', 'native59', 'q_slot'),
    ('sf_q_slot_beat', 'sys_face', 'q_slot_beat', 'native59', 'q_slot_beat'),
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect(die_v, lanes, source_commit):
    """Bind the three real pin chains, cross-checking GEN frames and landing straps.

    This is deliberately a BLOCKED certificate: the current layer compiler does not
    emit the production compute program, 512 Q writes or the 32 QSLOT events. No
    user-supplied synthetic ready array can change its verdict.
    """
    text = Path(die_v).read_text()
    inst = {}
    for line in text.splitlines():
        m = re.match(r'\s*\w+\s+(\w+)\s*\((.*)\);\s*$', line)
        if m:
            inst[m[1]] = dict(LA.CONN.findall(m[2]))
    rows = {r['bid']: r for r in json.loads(Path(lanes).read_text())['lanes']}
    net = LA.parse(die_v)
    pins = {}
    for bid, src, sp, dst, dp in PATHS:
        r, n = rows.get(bid), net.get(bid)
        if not r or not n or not n['contiguous'] or n['kind'] != ['fwd']:
            raise ValueError(f'Q readiness: missing or invalid forwarded lane {bid}')
        if (r.get('src'), r.get('dst'), r.get('n'), r.get('K')) != (src, dst, n['n'], n['K']):
            raise ValueError(f'Q readiness: GEN/netlist identity mismatch {bid}')
        if type(r.get('E')) is not int or n['K'] != (r['E'] + r.get('cal', 0)) % 8:
            raise ValueError(f'Q readiness: GEN/netlist landing age mismatch {bid}')
        sn, dn = inst.get(src, {}).get(sp), inst.get(dst, {}).get(dp)
        if not sn or not dn:
            raise ValueError(f'Q readiness: missing endpoint pins {src}.{sp}->{dst}.{dp}')
        at = sn
        for i in range(n['n']):
            hop = inst.get(f'rly_{bid}_{i}', {})
            if hop.get('a') != at or not hop.get('b'):
                raise ValueError(f'Q readiness: broken pin chain {bid} frame{i}')
            at = hop['b']
        if at != dn:
            raise ValueError(f'Q readiness: wrong consumer pin {bid}')
        pins[bid] = dict(source=f'{src}.{sp}', consumer=f'{dst}.{dp}',
                         source_net=sn, consumer_net=dn, frames=n['n'],
                         E=r['E'], K=n['K'], age_edges=LG.lane_cycles(r),
                         age_basis='GEN planned E+1; frame/strap connectivity checked, physical phase unqualified')
    if pins['sf_q_slot']['age_edges'] != pins['sf_q_slot_beat']['age_edges']:
        raise ValueError('Q readiness: torn Q request slot/beat')
    return dict(schema='opentallas.qwen_layerbench.q_readiness.v1', verdict='BLOCKED',
                production_bound=False, advance_admitted=False, phase_qualified=False, source_commit=source_commit,
                inputs=dict(die_v_sha256=digest(die_v), fwd_lanes_sha256=digest(lanes)),
                pins=pins, request_edges=pins['sf_q_slot']['age_edges'],
                ready_reference='native59_qdd_pin', producer_ready=None, request_ages=None,
                required_coverage=dict(beats=32, seats_per_beat=16, total_seats=512),
                blockers=['production PW1024/DW8 compute program is not emitted (bench_program is filler)',
                          'no production W5 Q write edges/seat coverage or all32 QSLOT events',
                          'SAFE2 source/kit must be bound by a new GEN; existing die is not its production proof',
                          'GEN E+1 is planned, not measured: bind final die source/forwarded/receiver clock phases'],
                rule='For each beat b: old_qslot[b] - 1 + request_edges >= '
                     'max(W5_Qwrite[b,seat] + Qdata_age for seat in 0..15); '
                     'SAFE2 same-edge forwarding permits equality; all512 seats and all32 requests required')


def require_advance(certificate, advance):
    if advance and not certificate.get('advance_admitted', False):
        raise ValueError('Q prefetch advance1 rejected: ' + '; '.join(certificate['blockers']))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--lanes', required=True)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--advance', type=int, choices=(0, 1), default=0)
    a = ap.parse_args()
    cert = inspect(a.die_v, a.lanes, a.source_commit)
    Path(a.out).write_text(json.dumps(cert, indent=1) + '\n')
    try:
        require_advance(cert, a.advance)
    except ValueError as e:
        sys.exit(str(e))
    print('Q_READINESS BLOCKED: GEN planned ages checked; production programme and clock phase unqualified')
