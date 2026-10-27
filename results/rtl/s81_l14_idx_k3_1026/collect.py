#!/usr/bin/env python3
"""TOK-DS-6: collect run_idx_k3.sh logs into check.json + committed witnesses.  usage: collect.py <run out dir> <this dir>"""
import json
import re
import shutil
import sys
from pathlib import Path

O, D = Path(sys.argv[1]), Path(sys.argv[2])
REL = 'results/rtl/s81_l14_idx_k3_1026'


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


def cyc(st):
    m = re.search(r'hdr_to_last (\d+) end_to_last (\d+)', st or '')
    return dict(hdr_to_last=int(m.group(1)), end_to_last=int(m.group(2))) if m else None


res = dict(svc={n: svc(n) for n in ('base', 'mut4', 'mut5', 'ik_kb')},
           rg3={n: rg3(n) for n in ('base_d2', 'base_d0', 'chain_mut4', 'mut3', 'shard_k1')})
img = {d: json.loads((O / f'img_d{d}/image.json').read_text()) for d in (0, 2)}
for f in ('svc_base.log', 'rg3_base_d2.log', 'rg3_base_d0.log'):
    shutil.copy(O / f, D / f)
muts = []
for n, what, f, r in (
        ('svc_mut4', 'dsdv_svc_att MUT 4: IK_ROW region hash without j[15:12] (wrong owner slice for p >= 2^16)', 'svc_mut4.log', res['svc']['mut4']),
        ('svc_mut5', 'dsdv_svc_att MUT 5: IK_ROW scale bytes of key c ^ 1', 'svc_mut5.log', res['svc']['mut5']),
        ('svc_ik_kb', 'compiler: IK_ROW KB without the shard offset (KB = IKB): the key lands outside the rg3 scan layout', 'svc_ik_kb.log', res['svc']['ik_kb']),
        ('rg3_chain_mut4', 'chain: rg3 HBM delta = the svc MUT 4 dump (new key written by the wrong slice) -> its score is wrong', 'rg3_chain_mut4.log', res['rg3']['chain_mut4']),
        ('rg3_mut3', 'dsdv_idx_rg3 MUT 3: scale sector of the neighbouring cell', 'rg3_mut3.log', res['rg3']['mut3']),
        ('rg3_shard_k1', 'compiler: the TOK-DS-4 k = 1 IDX_S spec (B 393216 N 131072, whole rank quarter) on the shard-2 die image', 'rg3_shard_k1.log', res['rg3']['shard_k1'])):
    failed = r.get('verdict') == 'FAIL'
    if (O / f).exists():
        t = (O / f).read_text().splitlines()
        (D / f'mut_{n}_fail_witness.log').write_text('\n'.join([x for x in t if re.match(r'^(SVCIK|TB_IDXRD)', x)][-60:]) + '\n')
    muts.append(dict(name=n, what=what, failed=failed, witness=f'{REL}/mut_{n}_fail_witness.log', line=r.get('line') or r.get('stats')))
ok = (res['svc']['base']['verdict'] == 'PASS' and res['rg3']['base_d2']['verdict'] == 'PASS' and
      res['rg3']['base_d0']['verdict'] == 'PASS' and all(m['failed'] for m in muts))
chk = dict(schema='opentallas.s81_dv.compiler_bench.v1', family='idx', layer='L14', rank=img[2]['quarter']['rank'],
           shard_k=img[2]['quarter']['k'],
           ops_proven=['attn.idx.newkey (IK_ROW frame of the rank-3 shard-die-2 svc job, dsdv_svc_att x 16 sids)',
                       'attn.idx.score (IDX_S job of each SHARD_K=3 shard: die 2 [480598, 524288) 43,690 keys incl. the '
                       'new key, die 0 [393216, 436907) 43,691 keys; 8 dsdv_idx_rg3 + 16 dsfd_ctrl_rg3)'],
           vehicle=('svc: one dsdv_svc_att run per sid 0..15 on the compiled IK_ROW q words (tb_dsdv_svc_att_ik +img); rg3: '
                    'tb_dsdv_idx_rg3 +IMG (W/E reader groups, relay stations 3/8/13/18, XD 21, refresh-aware HBM model) with '
                    'HBM = the shard\'s state keys at the layout (+ the svc bench\'s observed IK_ROW writes on die 2)'),
           golden='fixture L14 rank 3 (dv_layer_fixtures --layer L14 --rank 3): attn.idx.newkey key bytes (layout writes) and '
                  'attn.idx.score of each shard (BF16 bits, every lane word bit-exact)',
           shards={str(d): img[d]['quarter'] for d in (0, 2)}, words={str(d): img[d]['words'] for d in (0, 2)},
           cycles_model={str(d): img[d]['scan_cycles'] for d in (0, 2)},
           cycles_law_3N16_511={str(d): -(-3 * img[d]['quarter']['N'] // 16) + 511 for d in (0, 2)},
           cycles_measured={'2': cyc(res['rg3']['base_d2']['stats']), '0': cyc(res['rg3']['base_d0']['stats'])},
           not_proven=['the slice iq send of the IDX_S frame (s_3S_C -> iqf: xs field programme) and u_irg_07 = rg3_nq on 877',
                       'the query fan-out to the 3 shard dies (die-link legs) and the rank-tree merge (lower_bk job_rank_tree_rd: '
                       'compiler plan only here)',
                       'attn.cmp.k_rope_qdq (the new key producer, no die unit: GAP_KV_UNIT); the frame payload is the fixture key',
                       'shard die 1 (same law, not run)'],
           pass_=ok, results=res, mutants=muts)
chk['pass'] = chk.pop('pass_')
(D / 'check.json').write_text(json.dumps(chk, indent=1) + '\n')
print(json.dumps(dict(pass_=ok, cyc=chk['cycles_measured'], model=chk['cycles_model'], law=chk['cycles_law_3N16_511'],
                      muts={x['name']: x['failed'] for x in muts})))
