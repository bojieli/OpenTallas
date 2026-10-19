#!/usr/bin/env python3
"""QW-ODSCALE collector: copy every runs/<name>/bench.out from ot-epyc5 R=/srv/opentallas-scratch/claude/qw-odscale into
runs/<name>/bench.out here (mutant outputs = the committed fail witnesses) and write record.json (realstg record schema).
usage (from the worktree root): python3 results/rtl/qlb_c4b_1018/odscale/collect.py [--unit UNIT]"""
import argparse
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = '/srv/opentallas-scratch/claude/qw-odscale'
ap = argparse.ArgumentParser()
ap.add_argument('--unit', default='')
a = ap.parse_args()
names = subprocess.run(['ssh', 'ot-epyc5', f'ls {R}/runs'], capture_output=True, text=True, check=True).stdout.split()
stages = {}
for n in names:
    d = HERE / 'runs' / n
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(['scp', '-q', f'ot-epyc5:{R}/runs/{n}/bench.out', str(d / 'bench.out')], check=True)
    txt = (d / 'bench.out').read_text()
    first = txt.splitlines()[0] if txt else ''
    m = re.match(r'DV_LOWER_MAT (\w+) (PASS|FAIL|REFUSED) (\d+/\d+)?', first)
    rc = re.search(r'rc=(\d+)', txt)
    info = {}
    j = first.find('{')
    if j >= 0:
        try:
            info = json.loads(first[j:])
        except ValueError:
            pass
    stages[n] = dict(verdict=m.group(2) if m else 'UNKNOWN', checks=m.group(3) if m else None,
                     expected='FAIL' if n.startswith('MUT_') else 'PASS', span_cycles=info.get('span_cycles'),
                     delivery_span_cycles=info.get('delivery_span_cycles'), isa_gold=info.get('isa_gold'),
                     rc=int(rc.group(1)) if rc else None, first_line=first[:400])
ok = all(v['verdict'] == v['expected'] for v in stages.values())
rec = dict(schema='opentallas.qwen.dv-realstg.v1', lane='QW-ODSCALE', date='2026-10-19', position=8191, layers=[0, 1],
           tp8_die=0, run_host='ot-epyc5 (ot-run unit %s)' % a.unit, run_script='results/rtl/qlb_c4b_1018/odscale/run.sh',
           vehicle='tb_qfd_dv2 N12 fresh Verilator 5.050 build of this branch (origin/main merged, MU_NU 1 default)',
           change='dv_lower_mat.station_row_scales: BTAB row scale BF16 1.0 for o / down (the ISA all-reduces RAW partials; '
                  'the post-TP scale is the residual pscale); bench takes matrix scales, expectation = compiler station scale',
           operands='L<n>_mat_od_tp8.npz = dv_layer_fixture.py tp8od on the TP8 ISA gold (qwen_tp8_layer_gold P8191, '
                    'production TP8 fold): o x = die-0 ATTN, down x = die-0 ACT, gold = collective0/1_partial '
                    '(fixtures/L<n>_tp8od.json: hdc G.matvec split 256 == gold 4096/4096 both). L<n>_mat_od / qkv / gu = '
                    'the QW-REALSTG tp4 fixtures (regression).',
           exactness='od_tp8 PASS = RTL AR words (tag/last/data) bit-exact vs the bench expectation AND that expectation '
                     'bit-exact vs the TP8 ISA gold partials (isa_gold tp8_isa_gold_words)',
           mutants=dict(rawscale='the pre-fix lowering (o / down BTAB = matrix scales)', nostagger='as-built AR delivery'),
           verdict='PASS' if ok else 'FAIL', stages=stages)
(HERE / 'record.json').write_text(json.dumps(rec, indent=1) + '\n')
print(rec['verdict'], {k: (v['verdict'], v['checks'], v['span_cycles']) for k, v in stages.items()})
