#!/usr/bin/env python3
"""TOKSIM-S81C/WQBG 10-19: GOLDEN (model-reference) bit-exact check of every attn.wq_b frame-root return word of the
TOK2 fullsix vehicle (sid6 = rank 0, head 6, rank-local rows 3072..3583, K 1280, 6 frames, 15 phases).

Golden (independent of any RTL run and of the P600 baseline):
  * x = ops/attn.q_norm.scale of the released-checkpoint L0 rank-0 fixture (sid6_fixture, DeepSeek-V4.1-Flash
    dba1be0a); W = weights/wq_b (F8_E4M3) + wq_b.scale (UE8M0), rows 3072..3583.
  * per row: three K segments (v41_rom_ksplit_bankmap.segments(1280, 3)); each segment sum = hdc_golden_v41.csum over its
    32-element block products (frame_return_plan.golden_vals, HDC_V41_ARITH=chunk8), FP32 bits.
  * a frame-root word carries the tree node (lo, k, n) of its tag; its golden value is cap_model.golden_sub = the golden
    tree sum of that node (ot_v41_ret_pkg order, padding promoted, fadd = IEEE binary32 RNE, zero canonical).
  * the row's words must partition [0, n); recombined in golden tree order they must equal cap_model.golden_row, and its
    BF16 RNE must equal the fixture's own released-shard wq_b output (ops/attn.wq_b.bin[3072 + d]).
Cross-check: the recomputed segment sums must equal retained_sid6_fixture_contract.json original_segment_sums.

Word layout (classify_diagnostic.py, FRAME_RETURN): tag = w[34:3], data = w[66:35] (FP32), err = w[67], frame_fault = w[69].
usage: wqb_golden_check.py ROOT OUT.json NAME=DIR [NAME=DIR ...]   (DIR holds diagnostic_classification.json)
"""
import hashlib, json, os, sys
from pathlib import Path

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
ROOT = Path(sys.argv[1]).resolve()
for p in ['tools', 'tools/s81_dv', 'tools/s81_slice', 'tools/s81', 'tools/s81_dv/layer_prog', 'tools/s81_dv/layer_prog/qf_producer']:
    sys.path.insert(0, str(ROOT / p))
import numpy as np  # noqa: E402
import hdc_golden_v41 as G  # noqa: E402
from xs_place import Fix, FMat  # noqa: E402
import frame_return_plan as P  # noqa: E402
from cap_model import golden_row, golden_sub  # noqa: E402
from static_return_calendar import _f, _mk, norm, fadd  # noqa: E402
from head_local_contract import storage_offset  # noqa: E402

HEAD, RANKBASE = 6, 6 * 512
INV = {storage_offset(d): d for d in range(512)}


def build_golden():
    fx = Fix(str(ROOT / 'sid6_fixture'))
    x = fx.op('attn.q_norm.scale')
    rows = [RANKBASE + d for d in range(512)]
    m = FMat('wq_b', 'fp8', fx.w('wq_b'), fx.sc('wq_b'), rows, 'attn.wq_b')
    vals = P.golden_vals(m, x, 3)
    shard = fx.op('attn.wq_b').view('uint32')
    gold = {}
    for d in range(512):
        acc, err = golden_row(vals[d])
        bf = int(G.bits(G.to_bf16(G.from_bits(acc))))
        gold[d] = dict(segs=vals[d], acc=acc, err=err, bf16=bf, shard=int(shard[RANKBASE + d]))
    # cross-check vs the committed fixture contract (built per frame/epoch row group)
    c = json.load(open(ROOT / 'retained_sid6_fixture_contract.json'))
    cmp = 0; cmp_bad = []
    for ep in c['phase_contracts']:
        for f in ep['frames']:
            for r in f['rows']:
                d = r['dimension']; cmp += 1
                g = gold[d]
                if (r['original_segment_sums'] != g['segs'] or r['original_accumulator'] != g['acc']
                        or r['original_bf16_gold'] != g['bf16']):
                    cmp_bad.append(d)
    return fx, gold, dict(contract_rows=cmp, contract_mismatch=cmp_bad,
                          shard_bf16_mismatch=[d for d in range(512) if gold[d]['bf16'] != gold[d]['shard'] or gold[d]['err']])


def recombine(words, lo, k, n, segs):
    """golden-tree recombination of the returned node values: use a returned word where it is exactly this node"""
    key = norm(_mk(0, lo, k, n)) & 0x1FFF
    if key in words:
        return words[key], 0, [key]
    if k == 0:
        raise KeyError(('leaf not covered', lo))
    h = 1 << (k - 1)
    l, el, ul = recombine(words, lo, k - 1, n, segs)
    if lo + h >= n:
        return l, el, ul
    r, er, ur = recombine(words, lo + h, k - 1, n, segs)
    s, e = fadd(l, r)
    return s, el | er | e, ul + ur


def check_run(name, d, gold):
    cl = json.load(open(Path(d) / 'diagnostic_classification.json'))
    W = cl['frame_return_words']
    bad = []; byrow = {}; nw = 0
    for x in W:
        w = int(x['word'], 16); nw += 1
        tag = (w >> 3) & 0xFFFFFFFF; data = (w >> 35) & 0xFFFFFFFF; err = (w >> 67) & 1; ff = (w >> 69) & 1
        row16 = (tag >> 13) & 0xFFFF; row14 = row16 & 0x3FFF
        off = row14 - HEAD * 1024
        dim = INV.get(off)
        rec = dict(t=x['t'], lane=x['lane'], row16=row16, word=x['word'])
        if dim is None or x.get('semantic_row') != RANKBASE + dim:
            bad.append(dict(rec, why='row identity', dim=dim, semantic_row=x.get('semantic_row'))); continue
        _, lo, k, n = _f(tag)
        if n != 3:
            bad.append(dict(rec, why='n!=3', n=n)); continue
        exp, eerr = golden_sub(gold[dim]['segs'], tag)
        if data != exp or err or ff or eerr:
            bad.append(dict(rec, why='value', dim=dim, lo=lo, k=k, got=f'{data:08x}', golden=f'{exp:08x}', err=err, ff=ff))
            continue
        key = tag & 0x1FFF
        byrow.setdefault(dim, {})
        if key in byrow[dim]:
            bad.append(dict(rec, why='duplicate node', dim=dim, lo=lo, k=k)); continue
        byrow[dim][key] = data
    rows_ok = 0; row_bad = []
    for dim in range(512):
        if dim not in byrow:
            row_bad.append(dict(dim=dim, why='missing')); continue
        try:
            acc, e, used = recombine(byrow[dim], 0, 2, 3, None)
        except KeyError as ex:
            row_bad.append(dict(dim=dim, why=str(ex))); continue
        g = gold[dim]
        bf = int(G.bits(G.to_bf16(G.from_bits(acc))))
        if sorted(used) != sorted(byrow[dim]) or acc != g['acc'] or e or bf != g['shard']:
            row_bad.append(dict(dim=dim, why='row recombination', acc=f'{acc:08x}', golden_acc=f'{g["acc"]:08x}',
                                bf16=f'{bf:04x}', shard=f'{g["shard"]:04x}', extra_nodes=len(byrow[dim]) - len(used)))
            continue
        rows_ok += 1
    nodes = {}
    for dim, ws in byrow.items():
        k = tuple(sorted((_f(t)[1], _f(t)[2]) for t in ws)); nodes[str(k)] = nodes.get(str(k), 0) + 1
    return dict(run=name, dir=str(d), words=nw, words_golden_equal=nw - len(bad), word_mismatches=bad[:50],
                n_word_mismatch=len(bad), rows_full_golden=rows_ok, row_failures=row_bad[:50], n_row_fail=len(row_bad),
                node_patterns=nodes,
                bit_exact=(len(bad) == 0 and rows_ok == 512 and nw == len(W)),
                classification_sha256=hashlib.sha256((Path(d) / 'diagnostic_classification.json').read_bytes()).hexdigest())


def main():
    out = Path(sys.argv[2])
    fx, gold, xc = build_golden()
    runs = [check_run(*a.split('=', 1), gold) for a in sys.argv[3:]]
    res = dict(schema='opentallas.toksim_s81c.wqb_golden_check.v1',
               golden='cap_model.golden_row/golden_sub over frame_return_plan.golden_vals (hdc_golden_v41 csum chunk8, 3 K '
                      'segments, ot_v41_ret_pkg tree order, IEEE fp32 RNE fadd) on the released-checkpoint L0 rank-0 '
                      'fixture sid6 (rows 3072..3583, K 1280); row BF16 RNE == fixture ops/attn.wq_b (released shard)',
               fixture_meta_sha256=hashlib.sha256((ROOT / 'sid6_fixture/meta.json').read_bytes()).hexdigest(),
               checkpoint=fx.meta.get('checkpoint'), shard=fx.meta.get('shard'),
               golden_self_check=xc, golden_self_check_PASS=(xc['contract_rows'] == 512 and not xc['contract_mismatch']
                                                              and not xc['shard_bf16_mismatch']),
               runs=runs)
    out.write_text(json.dumps(res, indent=1) + '\n')
    print('WQBG golden_self_check_PASS', res['golden_self_check_PASS'], xc['contract_rows'], len(xc['contract_mismatch']),
          len(xc['shard_bf16_mismatch']))
    for r in runs:
        print('WQBG', r['run'], 'words', r['words'], 'golden_equal', r['words_golden_equal'], 'rows_full_golden',
              r['rows_full_golden'], 'bit_exact', r['bit_exact'], 'nodes', r['node_patterns'])


if __name__ == '__main__':
    main()
