#!/usr/bin/env python3
"""SU softmax path for attention on the SM engines (HBM attention option B, adopted 10-15): the SU <-> SM interface.

Option B replaces ATT.QK / ATT.PV by SM.MATVEC (QK: raw FP32 dot products, the 1/sqrt(d) scale stays in the SU
softmax immediate, as today) and an SM PV-accumulate mode (reads the BF16-rounded P, writes FP32 PV).  The SU records
(softmax.max -> exp_sum -> bf16_p -> pv_normalize; DS attend.max/exp_sum/bf16_p/den/norm) are unchanged, so the SU
calendar and its measured cost are unchanged; what changes is WHO writes the scores and reads P / writes PV.  This tool
derives, from the SU per-quarter address map (su_f2_spread.py --map), the exact layout every attention tensor has in the
static SU and therefore the obligations of the SM producer / consumer:

  * which VM slice (quarter q = SID q) holds each score / P / PV position, as a closed-form rule checked word by word;
  * whether any word is replicated (a cross-quarter read the SM would have to serve twice);
  * GQA co-location (Qwen: the 4 query heads of a KV head see the same position in the same quarter, so one streamed
    KV line serves all 4 x vectors of a quadrant's SM);
  * the SM row balance the rule implies for the context lengths the programs run (DS T128 / T640, Qwen T8192).

The canonical trace under-counts the ATT obligations (its ATT descriptors are dynamic-length, n_sel = POS1, and the
trace resolves them as one word); the counts here come from the SU roles, i.e. the full tensors.

    python3 tools/hbm_static/su_attention_sm_interface.py [--out results/arch/hbm_su_f2_static_1014/spread/attention_sm_interface.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPREAD = ROOT / 'results/arch/hbm_su_f2_static_1014/spread'
LANES_PER_Q, ISSUE = 128, 512
SMS_PER_QUADRANT = 8                       # 32 SM engines, 8 per quadrant (r25 HBM die)

TENSORS = {
    'qwen': dict(map='address_map_qwen.json', ctx=[8192], heads=8, gqa=4, tensors=[
        ('SC', 'softmax.max.A', 'SM.MATVEC QK writes raw FP32 q.k (was ATT:attention_qk)', 'write', 'FP32'),
        ('P', 'softmax.bf16_p.O', 'SM PV-accumulate reads P (BF16-rounded value in a 32-bit word, low 16 bits 0; was ATT:attention_pv)', 'read', 'BF16 in FP32 word'),
        ('PV', 'pv_normalize.A', 'reduced PV (sum over all SM partials) written here (was ATT:attention_pv)', 'write', 'FP32'),
    ]),
    'deepseek_g25': dict(map='address_map_deepseek_g25.json', ctx=[128, 640], heads=1, gqa=1, tensors=[
        ('SC', 'attend.max.A', 'SM.MATVEC QK writes raw FP32 q.k (was ATT:attend.qk)', 'write', 'FP32'),
        ('P', 'attend.bf16_p.O', 'SM PV-accumulate reads P (was ATT:attend.pv)', 'read', 'BF16 in FP32 word'),
        ('PV', 'attend.norm.A', 'reduced PV written here (was ATT:attend.pv)', 'write', 'FP32'),
    ]),
}


def rule(i):
    """quarter of position i of a tensor in the static SU: lane identity, issue = 512 positions, quarter = 128 lanes"""
    return (i % ISSUE) // LANES_PER_Q


def balance(t):
    """rows per quadrant for one T-position vector under the SU rule, vs the balanced split"""
    per_q = Counter(rule(p) for p in range(t))
    rows = [per_q.get(q, 0) for q in range(4)]
    bal = -(-t // 4)
    return dict(T=t, rows_per_quadrant=rows, balanced_rows=bal, max_over_balanced=round(max(rows) / bal, 3),
                rows_per_sm_max=-(-max(rows) // SMS_PER_QUADRANT), rows_per_sm_balanced=-(-bal // SMS_PER_QUADRANT))


def tensor(m, role):
    words = {}
    for r in m['runs']:
        if role in r['su_roles']:
            for w in range(r['logical_word_begin'], r['logical_word_end']):
                words.setdefault(w, []).append((r['quarter'], r['global_word_begin'] + w - r['logical_word_begin']))
    if not words:
        raise SystemExit(f'role {role} not in the map')
    base = min(words)
    bad = [w for w, h in words.items() if [q for q, _ in h] != [rule(w - base)]]
    per_q = Counter(h[0][0] for h in words.values())
    first = {q: min(g for hs in words.values() for qq, g in hs if qq == q) for q in per_q}
    return dict(logical_base=base, words=len(words), span=max(words) - base + 1,
                replicated_words=sum(len(h) > 1 for h in words.values()), rule_mismatch_words=len(bad),
                words_per_quarter=[per_q.get(q, 0) for q in range(4)],
                first_global_word_per_quarter={f'q{q}': first[q] for q in sorted(first)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=SPREAD / 'attention_sm_interface.json')
    a = ap.parse_args()
    out = dict(schema='opentallas.hbm.su_attention_sm_interface.v1', tool='tools/hbm_static/su_attention_sm_interface.py',
               qualification=False, owner='H-ELEM-B (SU side); SM side H-SM-ATT / SM owner; PV reduction H-COLL',
               rule='position i of SC / P / PV lives ONLY in slice q = (i mod 512) // 128 (static SU lane identity: '
                    'issue = 512 positions, quarter q = lanes 128q..128q+127); no replica; heads stride P = context '
                    'padded to 512, so every head uses the same rule',
               su_cost='unchanged: same SU records, same calendar (spread receipt rev_1015_sfu_ledger: Qwen 1.114 '
                       'LAT4 / DS 0.640 LAT4)',
               designs={})
    for d, spec in TENSORS.items():
        p = SPREAD / spec['map']
        m = json.loads(p.read_text())
        ts = {}
        for name, role, what, direction, fmt in spec['tensors']:
            ts[name] = dict(su_role=role, sm_side=what, sm_direction=direction, format=fmt, **tensor(m, role))
        gqa = None
        if spec['gqa'] > 1:
            sc = ts['SC']
            stride = sc['words'] // spec['heads']
            gqa = dict(query_heads_per_kv=spec['gqa'], head_stride_words=stride,
                       stride_multiple_of_issue=stride % ISSUE == 0,
                       colocated='every position p of the 4 heads of one KV head is in the same quarter'
                       if stride % ISSUE == 0 else 'NO: heads of one KV head split across quarters')
        out['designs'][d] = dict(address_map=str(p.relative_to(ROOT)),
                                 address_map_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                                 tensors=ts, gqa=gqa, sm_row_balance=[balance(t) for t in spec['ctx']])
    ok = all(t['rule_mismatch_words'] == 0 and t['replicated_words'] == 0
             for dd in out['designs'].values() for t in dd['tensors'].values())
    out['rule_holds_word_by_word'] = ok
    out['sm_obligations'] = [
        'QK: SMs of quadrant q compute exactly the KV rows i with (i mod 512)//128 == q and write the raw FP32 '
        'score of every query head of that row into slice q at the address the map gives (KV rows striped to the '
        'quadrants in 128-row chunks; with 8 SMs/quadrant, 16 rows per SM per 512-row block)',
        'PV: the same SMs read P of their own rows from slice q only (no cross-quarter read); GQA: one streamed V '
        'line x 4 local P values',
        'PV reduction: per-SM FP32 partials over disjoint row sets must be summed to one PV vector and written so '
        'that PV word j lands in slice (j mod 512)//128 -> a 4-quadrant REDUCE-SCATTER (on-die COLL 2x2 ring or '
        'SM-side), fixed-slot; the FP32 summation order must equal the reference attention order (bit-exact) or '
        'the golden must be re-derived and quality-checked',
        'DS T640 (38 of 40 layers): the rule puts rows 512..639 all on quadrant 0 (256/128/128/128 rows, 1.6x SM '
        'rows on quadrant 0). Balanced 160/quadrant needs the SU tail issue split 32 lanes x 4 quarters (per-quarter '
        'base + count in the compiler; the SFU sub-issue already walks 32 lanes/quarter). SU-side change proposed, '
        'not yet built: decide with the SM owner (the SM-side alternative is a balanced row map + a cross-quarter '
        'score move, which the static SU does not have)',
    ]
    out['open'] = ['T640 SU records are not in the layer-0 fixture (T128); the balanced-tail lowering needs a T640 '
                   'fixture and a vehicle run', 'compiler: ATT.QK/PV -> SM.MATVEC / SM.ACC records + KV prefetch '
                   '(H-SM-ATT)', 'SM PV-accumulate RTL + mixed-precision x (SM owner)']
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    for d, dd in out['designs'].items():
        for n, t in dd['tensors'].items():
            print(d, n, t['su_role'], 'words', t['words'], 'per quarter', t['words_per_quarter'],
                  'mismatch', t['rule_mismatch_words'], 'replica', t['replicated_words'])
        print(d, 'gqa', dd['gqa'], 'balance', dd['sm_row_balance'])
    print('rule holds word by word:', ok, '->', a.out)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
