#!/usr/bin/env python3
"""TOK-FUNC-S81/MURATE (10-21): results/token_pass/tokfunc_s81_1021/mu.json from the fleet outputs of run_mu_calendar.sh
(per-case bench verdicts + mu_stats per-user / per-message splits + calibration), the sampled stage-hop set
(mu_hop_plan.py index) and the full-stage admission check (dv_mu_calendar_phys --check on all 241 stages, MODEL grade).
Cases without a DONE marker are listed as pending (never as PASS)."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
from pathlib import Path

GRADE_OK = 'RTL-functional (source assembly)'


def rd(p):
    p = Path(p)
    return json.loads(calendar_bytes(p)) if p.exists() else None


def calendar_bytes(p):
    raw = Path(p).read_bytes()
    return gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--plans', required=True)
    ap.add_argument('--sources', required=True)
    ap.add_argument('--json', required=True)
    ap.add_argument('--cal-check-log', default='results/token_pass/tokfunc_s81_1021/mu/cal241_check.log')
    ap.add_argument('--calendar-ar', help='Exact AR calendar JSON checked with same-user collisions enabled')
    ap.add_argument('--calendar-mtp', help='Exact corrected MTP calendar JSON; the superseded x6 schedule is invalid')
    a = ap.parse_args()
    o = Path(a.out_dir)
    cal = rd(o / 'cal.json')
    index = rd(Path(a.plans) / 'index.json') or []
    cases = {}
    for t in sorted(o.glob('*.txt')):
        n = t.stem
        if n.startswith(('build_', 'cal')) and n not in ('cal_su', 'cal_mu1'):
            continue
        txt = t.read_text(errors='replace')
        st = rd(o / n / 'stats.json')
        done = (o / f'DONE_{n}').exists()
        c = dict(done=done, bench_pass=bool(re.search(r'^BENCH_PASS', txt, re.M)),
                 lines=[ln for ln in txt.splitlines() if ln.startswith(('XDIE', 'PASS', 'FAIL', 'BENCH', 'LATE', 'MISMATCH',
                                                                       'STATS', 'GEN_FAILED', 'EXIT'))][:12])
        golden = rd(o / n / 'golden.json') or {}
        c['traffic_calendar_sha256'] = golden.get('mu', {}).get('cal_sha256')
        if st:
            pu = st['per_user']
            c.update(beats=st['beats'], users=st['users'], late=sum(d['late'] for d in pu.values()),
                     max_late=max((d['max_late'] for d in pu.values() if d['max_late'] is not None), default=None),
                     cross_H_S_N_minmax=[min(d['cross_min'] for d in pu.values()), max(d['cross_max'] for d in pu.values())],
                     last_cycle=max(d['last_land'] for d in pu.values()),
                     per_user={u: dict(beats=d['beats'], late=d['late'], span_cycles=d['span_cycles'],
                                       cross_max=d['cross_max']) for u, d in pu.items()})
            if 'messages' in st:
                c['messages'] = st['messages']
        cases[n] = c
    ok = lambda n: n in cases and cases[n]['done'] and cases[n]['bench_pass'] and cases[n].get('late', 1) == 0
    # per-user verdicts: a user passes when every finished run that carries it passed; source = the runs that carry it
    users = {}
    for mode, U, full, parts in (('ar', 50, 'ar50r', [f'ar50r_c{k}' for k in range(10)]),
                                 ('mtp', 10, 'mtp10r', [f'mtp10r_u{k}' for k in range(10)])):
        for u in range(U):
            runs = [n for n in [full] + parts if n in cases and cases[n]['done'] and str(u) in cases[n].get('per_user', {})]
            hops = [x['name'] for x in index if x['mode'] == mode]
            hop_runs = [f'hop_{h}' for h in hops if f'hop_{h}' in cases and cases[f'hop_{h}']['done']
                        and str(u) in cases[f'hop_{h}'].get('per_user', {})]
            allr = runs + hop_runs
            users[f'{mode}{u}'] = dict(
                verdict=('PASS' if allr and all(ok(n) for n in allr) else 'FAIL' if any(not ok(n) for n in allr) else 'PENDING'),
                runs=allr, span_cycles={n: cases[n]['per_user'][str(u)]['span_cycles'] for n in allr},
                full_run=full in runs)
    hops = []
    for x in index:
        n = f"hop_{x['name']}"
        c = cases.get(n, {})
        pl = rd(Path(a.plans) / f"{x['name']}.json")
        hops.append(dict(name=x['name'], mode=x['mode'], hop=x['hop'], resource=x['resource'], why=x['why'], users=x['users'],
                         messages=x['messages'], verdict=('PASS' if ok(n) and c.get('messages', {}).get('all_within_HOP')
                                                         else 'PENDING' if not c.get('done') else 'FAIL'),
                         msg_latency_max=c.get('messages', {}).get('latency_max'),
                         within_HOP_821=c.get('messages', {}).get('all_within_HOP'),
                         gap_compress=pl['gap_compress'] if pl else None,
                         same_user_serial_delays=pl['same_user_serial_delays'] if pl else None))
    chk = Path(a.cal_check_log)
    chk_txt = chk.read_text() if chk.exists() else ''
    calendars = {}
    for mode in ('ar', 'mtp'):
        name = getattr(a, 'calendar_' + mode)
        path = Path(name) if name else None
        record = rd(path) if path else None
        # A legacy PASS string cannot establish that the corrected checker ran.
        proof = record.get('checker', {}) if record else {}
        corrected = proof.get('same_user_checked') is True and all(
            re.fullmatch(r'[0-9a-f]{64}', str(proof.get(k, '')))
            for k in (('source_sha256', 'position_graph_sha256') if mode == 'mtp' else ('source_sha256',)))
        good = corrected and proof.get('result') == 'PASS' and record.get('users', 0) > 0
        calendars[mode] = dict(path=name,
            sha256=hashlib.sha256(calendar_bytes(path)).hexdigest() if path and path.exists() else None,
            artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path and path.exists() else None,
            checker=proof, corrected_checker=corrected,
            verdict='PASS_MODEL' if good else 'FAIL' if record and proof.get('result') == 'FAULT' else 'PENDING',
            users=record.get('users') if record else None,
            period=record.get('period') if record else None,
            per_user_tok_s=record.get('per_user_tok_s') if good else None,
            aggregate_tok_s=record.get('aggregate_tok_s') if good else None)
    schedule_pass = all(c['verdict'] == 'PASS_MODEL' for c in calendars.values())
    traffic_calendar_bound = all(
        cases.get(case, {}).get('traffic_calendar_sha256') == calendars[mode]['sha256']
        and calendars[mode]['sha256'] is not None
        for mode, case in [('ar', 'ar50r'), ('mtp', 'mtp10r')])
    rate1 = dict(tool='tools/s81_dv/dv_mu_calendar_phys.py (same-user checker required)',
                 result='PASS_MODEL' if schedule_pass else 'UNQUALIFIED', grade='MODEL',
                 calendars=calendars,
                 legacy_log=dict(path=str(chk), lines=chk_txt.splitlines()[:4],
                     qualification='Historical only: the original checker missed 200 MTP same-user collisions'))
    all_cases = [n for n in cases if n not in ('cal_su', 'cal_mu1')]
    pend = [n for n in all_cases if not cases[n]['done']]
    fail = [n for n in all_cases if cases[n]['done'] and not ok(n)]
    hop_fail = [h['name'] for h in hops if h['verdict'] == 'FAIL']
    try:
        head = subprocess.run(['git', 'rev-parse', '--short=9', 'HEAD'], capture_output=True, text=True).stdout.strip()
    except Exception:
        head = None
    rec = dict(
        schema='opentallas.tokfunc_s81.mu.v1', lane='TOK-FUNC-S81/MURATE (tree TOK.DS.RATE.1, MU.TOK, MU.TOK.DS3, TOK.DS.LAYER.MU)',
        grade=(GRADE_OK if not pend and not fail and not hop_fail and all_cases and schedule_pass and traffic_calendar_bound
               and all(u['verdict'] == 'PASS' for u in users.values()) else
               'OPEN: ' + ('; '.join(([f'FAIL {fail + hop_fail}'] if fail or hop_fail else []) + ([f'{len(pend)} pending'] if pend else [])))),
        calendar=dict(attn='G4', selected=calendars, schedule_model_pass=schedule_pass,
                      traffic_calendar_bound=traffic_calendar_bound,
                      superseded_mtp='6f8bbf5c4: invalid same-user overlap424 on200/240 hops; rates withdrawn'),
        full_token_pass=False,
        component_runs_only=True,
        rtl=dict(bench='tb_xdie_s81_2 XL5 (claude/s81-link5-xdie-1021 @edc851400 rdm config: MU 2 release-die endpoints)',
                 wn_leaf='ot_s81sl_lep_mu_ab #(RX_SRAM 1, IN_PIPE 1, NATIVE32 1) as G7 binds s_0N (claude/s81-die72-g7-1021 '
                         '99750c015; lep file blob a6775e6f9f7d)', sources=a.sources,
                 sources_count=len(Path(a.sources).read_text().splitlines()) if Path(a.sources).exists() else None,
                 simulator='Verilator 5.050', tools_head=head),
        modelled_legs='off-die channel only (xdie2_chan 2 x PMA 8 + D): direct cabling hop_latency.json @4b528ad2b tp_mesh 251 '
                      '(D_CH 243), stage_hop 266 (D_ST 258); all on-die logic between the PHY pads is RTL',
        calibration=cal, cases=cases, users=users,
        users_summary={m: {v: sum(1 for k, x in users.items() if k.startswith(m) and x['verdict'] == v)
                           for v in ('PASS', 'FAIL', 'PENDING')} for m in ('ar', 'mtp')},
        sampled_stage_hops=dict(
            why='a full 241-stage RTL token is too slow; stage hops sampled by class: first (DENSE2 L0 A->B), mid DENSE2 (L1, '
                'Engram L1 B), L2-class idx (into / out of the copy-B L2 B stage = the AR binding resource), L14 Engram '
                '(in / out of copy-B), L20 (in / out of copy-B, the 52-user window), last stage hop R239->R240. Each run = '
                'one calendar link resource: every user of it with every calendar message (x / partial / combined / DENSE2 '
                'x + a_proj partial; MTP x6 verify positions) at its calendar cycle; idle gaps > 2,000 cycles compressed',
            not_sampled='head handoff R240 -> head die (head_hop 257 leg: a different D; the head plane is the head lane), '
                        'per-layer compute (the parent ports the per-layer slice benches)',
            runs=hops),
        rate1_full_stage_admission=rate1,
        findings=[
            'Historical 6f8bbf5c4 MTP x6 schedule is invalid: 200/240 same-user circuit collisions, max424 cycles. '
            'The corrected checker includes same-user windows; current hop-plan generation refuses hidden serialization. '
            'Explicit corrected calendar inputs and their checker provenance are required; missing inputs cannot inherit rates.',
            'DENSE2 A->B message is 652 + 8 cycles (x + a_proj partial); the bench h carries the 40,960 B x vector '
            '(lep NB 80 x 4 windows), the 8-cycle a_proj partial tail is not carried'],
        pending=pend, failed=fail + hop_fail)
    Path(a.json).write_text(json.dumps(rec, indent=1) + '\n')
    print(f"mu.json: grade {rec['grade']}; users {rec['users_summary']}; cases {len(all_cases)} pending {len(pend)} fail {len(fail + hop_fail)}")


if __name__ == '__main__':
    main()
