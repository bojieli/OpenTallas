#!/usr/bin/env python3
"""TOK-FUNC2-S81-LX (10-21): classify the native-compiler GAP list of a layer against the CURRENT die netlist.

dv_layer_compile.py's OPMAP / family gap texts were written against the p4l / bind_p4l3_g8 die; several name units
that the 72-frame G7 die now instantiates (dsdv_idx_rg3 readers with the score engine, dsdv_bk_col, dsdv_eng_rr +
dsdv_eng_tap).  This tool reads the compiler's lowering.json and the die.v the compile ran on and puts every GAP op in
one class:
  HW_GAP      no die unit computes the op (exact op / port / required function named) -> NOTICE to the die owners
  COMPILER    the unit is in die.v (instances counted from the netlist); the lowering / job ABI is owed
  SHARED_L0B  the same endpoint lowering the L0 dense sub-lane (TOK-FUNC2-S81/L0B) owns (vpx / XDIE rows, fold)
    python3 gap_classify.py --die-v die.v[.gz] --lowering DIR/prog_L2_su/lowering.json [...] --out gaps.json
"""
import argparse
import collections
import gzip
import json
import re
from pathlib import Path

# (op regex, class, unit required / present, die masters that must exist for COMPILER, required function / next step)
RULES = [
    (r'attn\.(kv_norm\.(sumsq|rsqrt|scale)|kv_rope_qdq)$', 'HW_GAP', 'KV RMSNorm(D 512) -> RoPE(64) -> FP8 QDQ', (),
     'no unit on G7: vn y feeds only vq, xfin rstd finish is fixed D 5120 (L0B finding). Structural fix exists: '
     'codex/s81-kvq-bind-1021 KV_ENABLE (ot_s81_su_kv kvt/kve/qnh/qnr/kvq at s_3N leaf0 op 15), not in die.v'),
    (r'attn\.cmp\.(k_norm\.(sumsq|rsqrt|scale)|k_rope_qdq|row_qdq|norm\.(sumsq|rsqrt|scale))$', 'HW_GAP',
     'compressor-row RMSNorm(D 512) / RoPE / FP8 QDQ', (),
     'same missing unit class as KV: the su_kv job table must also accept the compressed rows (cmp k_norm/k_rope_qdq/'
     'row_qdq, cmp norm); nothing on G7 computes them'),
    (r'attn\.cmp\.pool$', 'HW_GAP', 'compressor pooling (gate-softmax weighted sum of RATIO rows)', (),
     'no vs/vp op computes the compressor softmax-pool (vs ops SW/QB/RA/RB/QR/MOE/ENG); needs an su op or unit'),
    (r'^eng\.knorm$', 'HW_GAP', 'Engram key RMSNorm', (),
     'no RMSNorm of an Engram key row on G7 (vn is the hc_pre-mixed h norm); same su_kv-class unit or a vs RMS op'),
    (r'attn\.idx\.score$', 'COMPILER', 'index-key scan q.k -> scores', ('dsdv_idx_rg3',),
     'die has the readers (score engine EL 124 a key); owed: reader job header emission (qi) + walker windows in the '
     'svc/controller calendar, bound to the idxrd3 bench (S81-IDXRD-1021 campaign PASS / MUT FAIL)'),
    (r'attn\.idx\.newkey$', 'COMPILER', 'index-key row append to HBM', ('dsdv_svc_rs',),
     'svc_rs job writing the new index key row: job ABI not documented as a compiler ABI'),
    (r'attn\.gather$', 'COMPILER', 'selected-row gather (svc HBM read by index, bk_col frames)', ('dsdv_bk_col', 'dsdv_svc_rs'),
     'bk_col + svc_rs on die; owed: index-list row-read job + bk_col frame emission (TOK.DS.BENCH.4.4)'),
    (r'attn\.idx\.topk_merge$', 'SHARED_L0B', 'TP4 merge of local selections (end-slice lep)', ('ot_s81sl_slice_lepw_mab_mu_72',),
     'cross-die collective rows (same endpoint ABI as the vpx all-gathers, TOK.DS.XDIE)'),
    (r'attn\.(window_load|own_row_write|scores|max|exp|den|sink|pv|normalize)$', 'COMPILER',
     'svc_rs attention over window + compressed/selected rows', ('dsdv_svc_rs',),
     'lower_svc lowers sliding-window layers only; owed: compressed-row selection (index list from the readers) in the '
     'svc job table'),
    (r'(attn\.rows_allgather|eng\.rows_allgather|ffn\.router_allgather|attn\.out_allreduce|substage_hop\d+)$', 'SHARED_L0B',
     'end-slice lep rows / owner fold', ('ot_s81sl_slice_lepw_mab_mu_72',),
     'production row placement of the vpx endpoint ABI + out_allreduce fold: L0B lowers it for L0, reused here'),
    (r'^eng\.gate$', 'COMPILER', 'slice vs op 14 ENG (Engram gate / mix)', ('ot_s81sl_slice',),
     'encoder exists only inside tb_s81sl_slice_eng; owed: vs ENG op words in lower_vs'),
]


def masters(die_v):
    p = Path(die_v)
    txt = (gzip.open(p, 'rt') if p.suffix == '.gz' else p.open()).read()
    c = collections.Counter(m.group(1) for m in re.finditer(r'^\s*([A-Za-z_]\w*)\s+(?:#\s*\(.*?\)\s*)?u_\w+\s*\(', txt, re.M))
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--lowering', nargs='+', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    m = masters(a.die_v)
    res = dict(schema='opentallas.tokfunc_s81.gap_classes.v1', die_v=a.die_v,
               die_masters={k: v for k, v in sorted(m.items()) if not k.startswith(('dsfd_dvrly', 'dsfd_dvland'))},
               layers={})
    for lp in a.lowering:
        d = json.loads(Path(lp).read_text())
        ops, cls = [], collections.Counter()
        for o in d['ops']:
            if o.get('status') != 'GAP':
                continue
            hit = next((r for r in RULES if re.search(r[0], o['op'])), None)
            if hit is None:
                c, unit, need, why = 'UNCLASSIFIED', '-', (), (o.get('gap') or {}).get('missing', '')
            else:
                _, c, unit, need, why = hit
                miss = [x for x in need if not m.get(x)]
                if c == 'COMPILER' and miss:
                    c, why = 'HW_GAP', f'unit masters absent from die.v: {miss}; ' + why
            cls[c] += 1
            ops.append(dict(id=o['id'], op=o['op'], cls=c, unit=unit,
                            die_instances={x: m.get(x, 0) for x in need}, next=why,
                            compiler_gap=o.get('gap')))
        res['layers'][d['layer']] = dict(lowering=lp, status_counts=d.get('status_counts'), classes=dict(cls), gaps=ops)
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    for L, v in res['layers'].items():
        print(L, v['status_counts'], v['classes'])


if __name__ == '__main__':
    main()
