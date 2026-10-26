#!/usr/bin/env python3
"""Bind the diagnosed SU31 calendar cost to its exact historical compiler schedule.

No current B1 rate or measured token claim is made. Unchanged records retain
their model costs; only exact same-tag SU records get this scoped sensitivity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    root = a.root.resolve()
    sys.path.insert(0, str(root / 'tools'))
    from hgi_sim import d4g_quadrant_1017 as Q
    from hgi_sim import plan_study_price_1017 as PS
    from hgi_sim import ds_die_split as S
    from hgi_sim import ds_relay_latency as RL
    from hgi_sim import ds_mtp_verify as V
    from hgi_sim import timing as T
    stages = root / 'results/arch/hbm_plan_study_1017/stages.json'
    st = json.loads(stages.read_text())
    st['plan_b_bd'] = Q.bd_stages(st)
    # load_ledger otherwise silently falls back to {}, dropping measured adders.
    if not Q.LEDGER.is_file():
        raise FileNotFoundError(2, 'No such file or directory', str(Q.LEDGER))
    led = Q.load_ledger()
    if not led.get('entries'):
        raise ValueError('measured latency ledger must be present')
    kn = dict(Q.knob(Q.ADDERS, st, ledger=led), rings=2, ag_qbg=True)
    Q._D4G.clear()
    Q._D4G.update(kn)
    S.set_variant(PS.VARIANTS['b'], st)
    prog = RL.compile_case('AR')
    end = [r for r in prog if r.unit == 'CTL' and r.op == 'END'][:1]
    segments = [(key, V.rebuild(seg + end)) for key, seg in V.segments(prog)]
    first = next(seg for key, seg in segments if key == 0)
    target = first[31]
    if target.unit != 'SU':
        raise ValueError(f'historical segment0 record31 must be SU, got {target.unit}.{target.op} {target.tag}')
    def selected(r):
        return r.unit == target.unit and r.op == target.op and r.tag == target.tag
    costs = V.cost_fn(None)
    cases = {}
    T.footprint = V._footprint
    try:
        for label, delta in [('baseline', 0), ('historical_serial_3to4', 52 * 4 / 3),
                             ('common833_unqualified_sensitivity', 52)]:
            total, rows, hits = 0.0, {}, 0
            def cf(r, dyn, L):
                c, grade, how = costs(r, dyn, L)
                return c + (delta if selected(r) else 0), grade, how
            for key, seg in segments:
                nh = sum(selected(r) for r in seg)
                result = T.schedule(seg, V.DT.POS, 'S2', cost_fn=cf)
                hits += nh
                total += result['total_cycles']
                rows[str(key)] = dict(cycles=result['total_cycles'], matched_records=nh,
                    records=[dict(index=i, tag=r.tag, start=result['start'][i],
                                  end=result['end'][i], added_work_stream_cycles=delta)
                             for i,r in enumerate(seg) if selected(r)])
            cases[label] = dict(cycles=total, tok_s=Q.CLK / total,
                                extra_stream_cycles_per_matched_record=delta,
                                matched_records=hits, segments=rows)
    finally:
        T.footprint = V._FP
    base = cases['baseline']['cycles']
    for case in cases.values():
        case['added_token_cycles'] = case['cycles'] - base
        case['loss_pct'] = 100 * (1 - base / case['cycles'])
    report = dict(schema='opentallas.su31_calendar_bound_price.v1',
        status='PROPOSED_DIAGNOSTIC_NOT_ADOPTED', target=dict(segment=0, index=31,
        unit=target.unit, op=target.op, tag=target.tag, orig_op=target.orig_op),
        source_model='d4g_2ring_qbg historical priced_layers compiler',
        raw_calendar_delta=dict(issue_wait_serial_edges=48, pin_reg_drain_serial_edges=4,
            total_serial_edges=52, programme_edges_before=134, programme_edges_after=186,
            config_writes_before=481, config_writes_after=538),
        historical_clock='serial3:4 of 1.2GHz; +52 serial edges = +69.333333 stream cycles',
        current_b1='NOT QUALIFIED: common833 row is a sensitivity only; no B1 rate adoption',
        stages_sha256=hashlib.sha256(stages.read_bytes()).hexdigest(), cases=cases)
    report['latency_ledger_sha256'] = hashlib.sha256(Q.LEDGER.read_bytes()).hexdigest()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(target=report['target'], cases={k: {n: v[n] for n in
        ['cycles', 'tok_s', 'added_token_cycles', 'loss_pct', 'matched_records']} for k,v in cases.items()})))


if __name__ == '__main__':
    main()
