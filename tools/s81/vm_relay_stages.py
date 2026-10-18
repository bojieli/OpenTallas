"""Bind VM path legs to a selected die table; never infer absent buses or cycles.

The owner supplies alternatives for each write/read_request/read_return/commit
leg. Each alternative lists consecutive die buses; tile-internal ages are excluded.
Independent leg maxima give a conservative relay-only cost. This is a source-bound
cost input, not native execution/port-coverage or physical qualification.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_relay_stages as DRS

SCHEMA = 'opentallas.s81.vm-relay-paths.v1'
LEGS = ('write', 'read_request', 'read_return', 'commit')


def bind(plan, paths):
    errors = DRS.validate(plan)
    if errors:
        raise DRS.RelayStagesError('; '.join(errors))
    if plan['design'] != 's81' or plan['role'] != 'die_plan':
        raise DRS.RelayStagesError('expected S81 die_plan table')
    if plan['coverage'] != 'complete' or plan.get('problem_count', 0) or plan.get('problems'):
        raise DRS.RelayStagesError('complete unambiguous table required')
    if not plan['plan'].get('commit'):
        raise DRS.RelayStagesError('die source commit absent')
    if paths.get('schema') != SCHEMA or paths.get('plan_digest') != plan['digest']:
        raise DRS.RelayStagesError('VM path schema or selected plan digest differs')
    if paths.get('plan') != plan['plan']:
        raise DRS.RelayStagesError('VM path source identity differs')
    # No conversion between domains can be inferred from a cycle count. The VM
    # token-path price is in stream cycles at 1.2 GHz.
    if not math.isclose(plan['clock_period_ps'], 1e6 / 1200, abs_tol=.001):
        raise DRS.RelayStagesError('VM relay price requires stream_1p2 clock')
    legs = paths.get('legs', {})
    if set(legs) != set(LEGS):
        raise DRS.RelayStagesError('all four VM path legs required')
    table = DRS.Table(plan)
    used, out = {}, {}
    for leg in LEGS:
        alternatives = legs[leg]
        if not isinstance(alternatives, list) or not alternatives:
            raise DRS.RelayStagesError(f'VM {leg}: alternatives absent')
        rows = []
        for alternative in alternatives:
            if not isinstance(alternative, list) or not alternative or len(set(alternative)) != len(alternative):
                raise DRS.RelayStagesError(f'VM {leg}: empty or repeated bus path')
            buses = [table.bus(bid) for bid in alternative]
            if any(b['domain'] != 'stream_1p2' for b in buses):
                raise DRS.RelayStagesError(f'VM {leg}: unknown or non-stream bus domain')
            for previous, current in zip(buses, buses[1:]):
                if previous['dst']['inst'] != current['src']['inst']:
                    raise DRS.RelayStagesError(f'VM {leg}: disconnected consecutive buses')
            for b in buses:
                if b.get('eq_age_group') and table.group_age(b['eq_age_group']) != b['stages']:
                    raise DRS.RelayStagesError(f'VM {leg}: unpadded equal-age bus {b["id"]}')
                used.setdefault(b['id'], []).append('vm.' + leg)
            rows.append(dict(buses=alternative, stages=sum(b['stages'] for b in buses)))
        out[leg] = dict(alternatives=rows, stages=max(r['stages'] for r in rows))
    write = out['write']['stages']
    read = out['read_request']['stages'] + out['read_return']['stages']
    return dict(schema='opentallas.s81.vm-relay-cost-input.v1', plan=plan['plan'],
                digest=plan['digest'], legs=out, write=write, read=read,
                write_plus_read=write + read, commit=out['commit']['stages'],
                scope='owner-declared path alternatives; independent leg maxima; relay-only cost',
                exhaustive_native_path_coverage_proven=False, native_qualified=False), DRS.compiled(
                    plan, 'tools/s81/mtp_ledger_1016.py', used_by=used)
