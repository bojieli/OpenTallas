#!/usr/bin/env python3
"""TOKSIM-KVATTN collector: run dir of tools/qwen_layerbench/kvattn_rel/run.sh -> record.json (+ per-run JSON).

start  = the CMD record presented at the KV-die attention tile face (d2d landing input)
retire = the last (beat 31) RESULT record leaving the tile on the d2d TX slot
work   = CMD -> final join out_valid (the last data-path event; everything after it is calendar padding to the fixed slots)
Context-dependent share: least-squares fit work(T) = a + b T over T = 1024/4096/8192; share = b T / retire.
Usage: collect.py OUT_DIR RECORD_JSON
"""
import json, re, sys
from pathlib import Path

out, rec = Path(sys.argv[1]), Path(sys.argv[2])
runs = {}
for d in sorted((out / 'runs').iterdir()):
    log = (d / 'sim.log').read_text(errors='replace') if (d / 'sim.log').exists() else ''
    users = [json.loads(l) for l in log.splitlines() if l.startswith('{"user"')]
    v = next((l for l in log.splitlines() if l.startswith('KVATTN_REL')), None)
    fin0 = [l for l in log.splitlines() if l.startswith('FIN0')]
    mm = [l for l in log.splitlines() if l.startswith('MISMATCH')][:3]
    runs[d.name] = dict(verdict=v, users=users, fin0=fin0, mismatch_sample=mm,
                        exit=(d / 'exit').read_text().strip() if (d / 'exit').exists() else None,
                        time=(d / 'time').read_text().strip() if (d / 'time').exists() else None)
def ok(n):
    v = runs.get(n, {}).get('verdict') or ''
    return v.startswith('KVATTN_REL PASS')
meas = {}
for T in (1024, 4096, 8191, 8192):
    for nu in (1, 4):
        n = f'u{nu}_T{T}'
        r = runs.get(n)
        if not r or not r['users']:
            continue
        us = r['users']
        meas[n] = dict(pass_=ok(n), ctx=T, users=nu,
                       start_to_retire=[u['start_to_retire'] for u in us],
                       start_to_status=[u['start_to_status'] for u in us],
                       work_span=[u['work_span'] for u in us],
                       cmd_period=(us[-1]['cyc_cmd'] - us[0]['cyc_cmd']) / (nu - 1) if nu > 1 else None,
                       first_cmd_to_last_retire=us[-1]['cyc_result31'] - us[0]['cyc_cmd'],
                       first_cmd_to_last_status=us[-1]['cyc_status'] - us[0]['cyc_cmd'],
                       exact=[u['exact'] for u in us], k_rows=[u['k_rows'] for u in us], v_rows=[u['v_rows'] for u in us])
fit = None
pts = [(meas[f'u1_T{T}']['ctx'], meas[f'u1_T{T}']['work_span'][0]) for T in (1024, 4096, 8192) if f'u1_T{T}' in meas]
if len(pts) >= 2:
    n = len(pts); mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts); a = my - b * mx
    fit = dict(work_fixed=round(a, 1), work_per_row=round(b, 5),
               share={str(T): round(b * T / meas[f'u1_T{T}']['start_to_retire'][0], 4) for T in (1024, 4096, 8192)
                      if f'u1_T{T}' in meas})
mut = {n: dict(verdict=r['verdict'], must='FAIL', caught=bool(r['verdict']) and 'FAIL' in r['verdict'])
       for n, r in runs.items() if n.startswith('mut_')}
record = dict(schema='opentallas.toksim.kvattn.v1', lane='TOKSIM-KVATTN',
              fd=(out / 'fd.txt').read_text().strip() if (out / 'fd.txt').exists() else None,
              measured=meas, context_fit=fit, mutants=mut,
              bound_32k=runs.get('u1_T32768_bound', {}).get('verdict'),
              peaky=runs.get('u1_T4096_peaky', {}).get('verdict'), runs=runs)
rec.parent.mkdir(parents=True, exist_ok=True)
rec.write_text(json.dumps(record, indent=1) + '\n')
print(json.dumps(dict(measured={k: dict(p=v['pass_'], r=v['start_to_retire'], s=v['start_to_status'], w=v['work_span'],
                                       per=v['cmd_period']) for k, v in meas.items()},
                      fit=fit, mutants={k: v['caught'] for k, v in mut.items()}, b32k=record['bound_32k'])))
