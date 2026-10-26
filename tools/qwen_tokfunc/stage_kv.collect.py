#!/usr/bin/env python3
"""TOK-FUNC-QW stage kv collector: a kvattn_rel run dir (summary.txt + record.json from tools/qwen_layerbench/kvattn_rel)
-> RUNROOT/kv/result.json (TOK-FUNC result format).

    stage_kv.collect.py RUNROOT [--out DIR] [--grade G] [--src-note TEXT] [--result PATH]
--out defaults to RUNROOT/kv/out (stage_kv.sh); point it at KV-MU7 job4b's out dir
(ot-epyc5:/srv/opentallas-scratch2/claude/kv-mu6-kvattn4-1020/out_0e597ed1c) to collect that run, with --src-note
recording its source and --result where to write."""
import argparse
import json
import re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('runroot')
ap.add_argument('--out')
ap.add_argument('--grade', default='RTL-functional (source assembly)')
ap.add_argument('--src-note', default='')
ap.add_argument('--result')
a = ap.parse_args()
rr = Path(a.runroot)
out = Path(a.out) if a.out else rr / 'kv' / 'out'
res_p = Path(a.result) if a.result else rr / 'kv' / 'result.json'
src_commit = (rr / 'src' / 'ASM_COMMIT').read_text().strip() if (rr / 'src' / 'ASM_COMMIT').exists() else '?'
rec = json.loads((out / 'record.json').read_text()) if (out / 'record.json').exists() else None
summ = (out / 'summary.txt').read_text() if (out / 'summary.txt').exists() else ''
runs = {}
for l in summ.splitlines():
    m = re.match(r'(\S+) exit=(\S*) ?(.*)', l)
    if m:
        runs[m.group(1)] = m.group(3).strip() or f'exit={m.group(2)} (no KVATTN_REL line)'
MAIN = [f'u{u}_T{T}' for u in (1, 4) for T in (1024, 4096, 8192)] + ['u1_T4096_peaky', 'u1_T8191']
MUTS = ['mut_k_shift', 'mut_v_swap', 'mut_q_swap', 'mut_k_late', 'mut_gmut1', 'mut_gmut2', 'mut_gmut4']
p = lambda n: runs.get(n, '').startswith('KVATTN_REL PASS')
f = lambda n: 'FAIL' in runs.get(n, '')
cycles = {}
if rec:
    for n, m in rec.get('measured', {}).items():
        cycles[f'{n}_start_to_retire'] = m['start_to_retire'] if m['users'] > 1 else m['start_to_retire'][0]
        cycles[f'{n}_work_span'] = m['work_span'] if m['users'] > 1 else m['work_span'][0]
        if m['users'] > 1:
            cycles[f'{n}_cmd_period'] = m['cmd_period']
            cycles[f'{n}_first_cmd_to_last_retire'] = m['first_cmd_to_last_retire']
    if rec.get('context_fit'):
        cycles['context_fit'] = rec['context_fit']
b32 = runs.get('u1_T32768_bound', '')
# 32k bound: the release RTL (14-bit ctx) must refuse = KVATTN_REL FAIL with the tile/calendar fault raised, no timeout
refused = 'KVATTN_REL FAIL' in b32 and ('tile_fault=1' in b32 or 'cal_fault=1' in b32) and 'timeout=0' in b32
ok = rec is not None and all(p(n) for n in MAIN) and all(f(n) for n in MUTS) and refused
out_j = {
    'stage': 'kv',
    'grade': a.grade,
    'src_commit': src_commit,
    'source_note': a.src_note or (out / 'SOURCE_COMMIT.txt').read_text().strip() if (out / 'SOURCE_COMMIT.txt').exists() else a.src_note,
    'verdict': 'PASS' if ok else ('PENDING' if rec is None else 'FAIL'),
    'golden': 'tools/qwen_tp8_attention_native.py vectors (CPU golden, seeds 1..4 normal, seed 5 peaky, seed 6 T8191): every '
              'result record word of every user bit-exact (KVATTN_REL), K/V rows read back; T32768 must be REFUSED (14-bit ctx)',
    'runs': {n: runs.get(n, 'NOT_RUN') for n in MAIN + ['u1_T32768_bound']},
    'cycles': cycles,
    'bound_32k': 'REFUSED as required (tile/cal fault)' if refused else f'NOT REFUSED ({b32 or "NOT_RUN"})',
    'mutants': {n: ('FAIL as required' if f(n) else f'NOT CAUGHT ({runs.get(n, "NOT_RUN")})') for n in MUTS},
    'stand_ins': ['the d2d landing face is driven by the tb (CMD record in, RESULT/STATUS records out on the d2d TX slot); '
                  'compute-die side not simulated (PHY/off-die leg)',
                  'build defines KVD_HEADS=1 KVD_Q_FP32=1 KVD_QK_ONLY=1 (the release vehicle configuration of build.sh)'],
    'logs': [str(x) for x in ('summary.txt', 'record.json', 'build.log', 'run.out', 'fd.txt')],
    'log_dir': str(out),
}
res_p.parent.mkdir(parents=True, exist_ok=True)
res_p.write_text(json.dumps(out_j, indent=1) + '\n')
print(json.dumps({k: out_j[k] for k in ('verdict', 'runs', 'mutants')}, indent=1))
