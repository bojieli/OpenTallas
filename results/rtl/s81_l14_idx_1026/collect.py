#!/usr/bin/env python3
"""TOK-DS-4: collect run_idx_l14.sh logs into check.json + committed witnesses.  usage: collect.py <run out dir> <this dir>"""
import json
import re
import shutil
import sys
from pathlib import Path

O, D = Path(sys.argv[1]), Path(sys.argv[2])
REL = 'results/rtl/s81_l14_idx_1026'


def line(f, pat):
    t = (O / f).read_text() if (O / f).exists() else ''
    m = [x for x in t.splitlines() if re.match(pat, x)]
    return m[-1] if m else None


def svc(n):
    ln = line(f'svc_{n}.log', r'^SVCIK ')
    return dict(line=ln, verdict=(re.search(r'verdict=(\w+)', ln or '') or [None, None])[1])


def rg3(n):
    v = line(f'rg3_{n}.log', r'^TB_IDXRD (PASS|FAIL)$')
    st = line(f'rg3_{n}.log', r'^TB_IDXRD_STATS ')
    im = line(f'rg3_{n}.log', r'^TB_IDXRD_IMG ')
    return dict(verdict=v and v.split()[1], stats=st, img=im)


res = dict(svc={n: svc(n) for n in ('base', 'mut4', 'mut5', 'ik_kb')}, rg3={n: rg3(n) for n in ('base', 'chain_mut4', 'mut3')})
img = json.loads((O / 'img/image.json').read_text())
for n, f in (('svc_base', 'svc_base.log'), ('rg3_base', 'rg3_base.log')):
    shutil.copy(O / f, D / f)
muts = []
for n, what, f, r in (
        ('svc_mut4', 'dsdv_svc_att MUT 4: IK_ROW region hash without j[15:12] (wrong owner slice for p >= 2^16)', 'svc_mut4.log', res['svc']['mut4']),
        ('svc_mut5', 'dsdv_svc_att MUT 5: IK_ROW scale bytes of key c ^ 1', 'svc_mut5.log', res['svc']['mut5']),
        ('svc_ik_kb', 'compiler: IK_ROW KB without the rank offset (KB = IKB): the key lands outside the rg3 scan layout', 'svc_ik_kb.log', res['svc']['ik_kb']),
        ('rg3_chain_mut4', 'chain: rg3 HBM delta = the svc MUT 4 dump (new key written by slice 0 instead of 7) -> its score is wrong', 'rg3_chain_mut4.log', res['rg3']['chain_mut4']),
        ('rg3_mut3', 'dsdv_idx_rg3 MUT 3: scale sector of the neighbouring cell', 'rg3_mut3.log', res['rg3']['mut3'])):
    failed = r.get('verdict') == 'FAIL'
    if (O / f).exists():
        t = (O / f).read_text().splitlines()
        (D / f'mut_{n}_fail_witness.log').write_text('\n'.join([x for x in t if re.match(r'^(SVCIK|TB_IDXRD)', x)][-60:]) + '\n')
    muts.append(dict(name=n, what=what, failed=failed, witness=f'{REL}/mut_{n}_fail_witness.log', line=r.get('line') or r.get('stats')))
ok = res['svc']['base']['verdict'] == 'PASS' and res['rg3']['base']['verdict'] == 'PASS' and all(m['failed'] for m in muts)
m = re.search(r'hdr_to_last (\d+) end_to_last (\d+)', res['rg3']['base']['stats'] or '')
chk = dict(schema='opentallas.s81_dv.compiler_bench.v1', family='idx', layer='L14', rank=img['quarter']['rank'],
           ops_proven=['attn.idx.newkey (IK_ROW frame of the rank-3 svc job, dsdv_svc_att x 16 sids)',
                       'attn.idx.score (IDX_S job of the rank-3 quarter, 131,072 keys, 8 dsdv_idx_rg3 + 16 dsfd_ctrl_rg3)'],
           vehicle=('svc: one dsdv_svc_att run per sid 0..15 on the compiled IK_ROW q words (tb_dsdv_svc_att_ik +img); rg3: '
                    'tb_dsdv_idx_rg3 +IMG (W/E reader groups, relay stations 3/8/13/18, XD 21, refresh-aware HBM model) with '
                    'HBM = the rank-3 state key quarter at the layout + the svc bench\'s observed IK_ROW writes'),
           golden='fixture L14 rank 3 (dv_layer_fixtures --layer L14 --rank 3, all checks equal shard): attn.idx.newkey key '
                  'bytes (layout writes) and attn.idx.score[393216:524288] (BF16 bits, every lane word bit-exact)',
           quarter=img['quarter'], words=img['words'], cycles_model=img['scan_cycles'],
           cycles_measured=dict(hdr_to_last=int(m.group(1)), end_to_last=int(m.group(2))) if m else None,
           not_proven=['the slice iq send of the IDX_S frame (s_3S_C -> iqf: xs field programme) and u_irg_07 = rg3_nq on 877',
                       'the rank-3 svc attention job on the DIE_ID 3 protect-lib slices (bench_cmp is rank 0 / DIE 0)',
                       'attn.cmp.k_rope_qdq (the new key producer, no die unit: GAP_KV_UNIT); the frame payload is the fixture key'],
           pass_=ok, results=res, mutants=muts)
chk['pass'] = chk.pop('pass_')
(D / 'check.json').write_text(json.dumps(chk, indent=1) + '\n')
print(json.dumps(dict(pass_=ok, cyc=chk['cycles_measured'], model=chk['cycles_model'],
                      muts={x['name']: x['failed'] for x in muts})))
