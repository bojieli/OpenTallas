#!/usr/bin/env python3
"""DRIVE-S81-GUPROP (10-20) bench vectors: the SW consumer beat leaf G of the GU_PROP gate/up gather (tb_vs_guprop.sv).

Producer side (compiler of record, no RTL here): the capture placement of every gate / up row (gu_gather.py --out MAP:
`producer` = cap_emit amap, i.e. cap_model.decode of the frame tag under the slice's cap cfg_d -- the decode the
ot_s81sl_cap conformance record pins) holds BF16 RNE(fixture gu) (cap fmt 2 rounding, cap_model.decode).
Gather: the compiler's RD records for this consumer leaf (MAP `records`, dst = (sid, leaf)) -- each copies the SOURCE
capture row pair (src_row, src_row + 1) of the producer image into the leaf's row pair dst_row, one pair a cycle in
dst_row order from bench edge RD0 (the xr RD unpacker rate), as kind 6 beats.  Then the routed weights rows (target 5,
gunit router rows, W_GUARD before the command) and ONE SW command (lower_vs.plan's command word: n 16, wr, wsel = slot,
uq -> vq) at the last RD edge + 1 (or --issue ovl: one edge BEFORE the first RD pair -- the overlapped issue, a measurement, not the verdict).
Expected = the layer fixture: BF16(route_w) (routed) / BF16(shared.swiglu) rows at SW_OUT and the quant2 /
shared_quant XQ beat (index G), as gen_vs_bench.py.  Nothing of the expected side is derived from the gather records.

    gen_guprop_bench.py --fixtures D --map MAP.json --G G --out OUT [--mutant srcoff|gswap] [--issue last|ovl]
mutants (gather map, not RTL): srcoff = every record reads the NEXT source row pair; gswap = gate / up rows of every
record swapped.  RTL negative control: tb_vs_guprop -GVS_MUT=1 (ot_s81sl_vs SW drops w).
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('gen_vs_bench', HERE / 'gen_vs_bench.py')
GB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(GB)
LV, V, u32, rows4 = GB.LV, GB.V, GB.u32, GB.rows4
ROOT = GB.ROOT
sys.path.insert(0, str(ROOT / 'tools/s81_slice'))
from cap_model import decode  # noqa: E402
RD0 = 640


def bf16w(x):
    """cap fmt 2 (BF16 RNE in an FP32 word), cap_model.decode's rounding"""
    cfg = dict(rbase=0, rcnt=1, np=0, fmt=2, obase=0, ops=0, rsplit=0, lo32=0, hi32=0)
    return decode(0, int(x), cfg)[4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--map', required=True)
    ap.add_argument('--G', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mutant', default=None, choices=(None, 'srcoff', 'gswap'))
    ap.add_argument('--issue', default='last', choices=('last', 'ovl'))
    a = ap.parse_args()
    M = json.loads(Path(a.map).read_text())
    assert M['PASS'], 'gather map refused'
    meta = json.loads((Path(a.fixtures) / 'meta.json').read_text())
    assert meta['rank'] == 0
    V.set_arith(meta.get('arith', 'chunk8'))
    b = GB.Bench(a.fixtures)
    b.xqi = []
    G = a.G
    sid, k = divmod(G, 5)
    slot, jj = divmod(G, 9)
    lo = 64 * jj
    ids = [int(e) for e in meta['experts']]
    ex = 'shared' if slot == 6 else f'exp{ids[slot]}'
    pre = 'ops/ffn.shared' if slot == 6 else f'ops/ffn.experts.{ids[slot]}'
    j0 = meta['tp_split']['shared_ff_rows' if slot == 6 else 'expert_ff_rows'][0][0]
    gu = b.f(f'{pre}.gu.bin')
    nff_all = len(gu) // 2
    # ---- producer image: every (slice, leaf, word) of the capture placement (amap), BF16 RNE(fixture)
    img = {}
    for p in M['producer']:
        if p['expert'] != ex:
            continue
        v = gu[(nff_all if p['kind'] == 'up' else 0) + j0 + p['j']]
        img[(p['sid'], p['leaf'], p['word'])] = bf16w(u32([v])[0])
    # ---- the gather records of this consumer leaf, in destination row order
    recs = sorted((r for r in M['records'] if r['G'] == G), key=lambda r: r['dst_row'])
    assert len(recs) == 16 and all(r['dst_sid'] == sid and r['dst_leaf'] == k and r['expert'] == ex for r in recs), \
        ('consumer leaf needs 16 groups', G, len(recs))
    rd, beats = [], []
    for i, r in enumerate(recs):
        srow = r['src_row'] + (2 if a.mutant == 'srcoff' else 0)
        ws = [img.get((r['src_sid'], r['src_leaf'], 4 * srow + w), 0) for w in range(8)]
        if a.mutant == 'gswap':
            ws = ws[4:] + ws[:4]
        rd.append(sum(w << (32 * n) for n, w in enumerate(ws)))
        beats.append(dict(op='gu.gather', issue=RD0 + i, kind=6, body=r['dst_row'] | i << 16, dur=0,
                          what=f"RD pair src s{r['src_sid']} l{r['src_leaf']} row {srow} -> row {r['dst_row']} (j {r['j']})"))
    t_sw = (RD0 + len(recs)) if a.issue == 'last' else RD0 - 1
    R = LV.VS_ROWS
    if slot < 6:
        spec_g = importlib.util.spec_from_file_location('lower_gu', ROOT / 'tools/s81_dv/layer_prog/lower_gu.py')
        GU = importlib.util.module_from_spec(spec_g)
        spec_g.loader.exec_module(GU)
        wrow = GU.GU_ROWS['router'] + 1
        c = LV.vp_cmd(LV.OP['SW'], a0=R['SW_IN'], a1=wrow, n=16,
                      imm=LV.vs_imm(ob=R['SW_OUT'], wb=1, uq=1, umq=1, umi=G, lim=LV.LIM, w0=LV.POISON, w1=LV.POISON,
                                    wr=1, wsel=slot))
        dur = LV.VS_DUR['SW'](16, 1)
        wts = [int(v) for v in u32(b.f('ops/ffn.weights.bin')[:6])]
        for i, ws in enumerate((wts[0:4], wts[4:6] + [0, 0])):
            body = (wrow + i) | (0xF if i == 0 else 0x3) << 10 | sum(w << (32 * j) for j, w in enumerate(ws)) << 14
            beats.append(dict(op='ffn.weights', issue=RD0 - 24 + i, kind=3, body=body, dur=0,
                              what=f'gunit router weights row {wrow + i}'))
        wfx = 'route_w'
    else:
        c = LV.vp_cmd(LV.OP['SW'], a0=R['SW_IN'], n=16, imm=LV.vs_imm(ob=R['SW_OUT'], wb=1, uq=1, umq=1, umi=G,
                                                                       lim=LV.LIM, w0=LV.ONE, w1=LV.ONE))
        dur = LV.VS_DUR['SW'](16)
        wfx = 'swiglu'
    beats.append(dict(op='ffn.swiglu' if slot < 6 else 'ffn.shared_swiglu', issue=t_sw, kind=1, body=c, dur=dur,
                      what=f'SW n 16 slot {slot} G {G}'))
    # ---- expected (fixture only)
    a_fx = b.f(f'{pre}.{wfx}.bin')[j0 + lo:j0 + lo + 64]
    ab = V.to_bf16(a_fx)
    q2 = b.f(f'{pre}.quant2.bin', np.float64)
    nm = 'ffn.swiglu' if slot < 6 else 'ffn.shared_swiglu'
    b.expect_rows(nm, R['SW_OUT'], rows4(u32(ab)))
    b.expect_xq(q2[j0 + lo:j0 + lo + 64], q2[2304 + (j0 + lo) // 32: 2304 + (j0 + lo) // 32 + 2], G, golden_in=ab)
    # ---- files (gen_vs_bench formats + rd.mem)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    prog = []
    for x in sorted(beats, key=lambda x: (x['issue'], x['kind'] != 3)):
        op = x['body'] & 0xF if x['kind'] == 1 else 0
        prog.append(x['kind'] << 252 | x['issue'] << 228 | op << 224 | (x['dur'] & 0xFFFF) << 186 | x['body'])
    assert len({x['issue'] for x in beats}) == len(beats), 'two beats on one edge'
    exp, expm = [], []
    names = sorted({cc[0] for cc in b.chk})
    for op, base, rows, ms in b.chk:
        idx = len(exp)
        for i in range(0, len(rows), 2):
            exp.append(sum(w << (32 * j) for j, w in enumerate(rows[i] + rows[i + 1])))
            expm.append(ms[i] | ms[i + 1] << 4)
        prog.append(2 << 252 | names.index(op) << 224 | idx << 210 | (len(rows) // 2) << 202 | base)
    prog.append(0)
    with open(out / 'img.mem', 'w') as f, open(out / 'imgv.mem', 'w') as g:
        for _ in range(1024):
            f.write('%032x\n' % 0)
            g.write('0\n')
    (out / 'prog.mem').write_text(''.join('%064x\n' % p for p in prog))
    (out / 'rd.mem').write_text(''.join('%064x\n' % p for p in rd))
    (out / 'exp.mem').write_text(''.join('%064x\n' % e for e in exp))
    (out / 'expm.mem').write_text(''.join('%02x\n' % m for m in expm))
    (out / 'xq.mem').write_text(''.join('%0133x\n' % e for e in b.xq))
    (out / 'xqi.mem').write_text(''.join('%02x\n' % e for e in b.xqi))
    last = max(x['issue'] for x in beats)
    (out / 'params.txt').write_text(f'+sid={sid} +k={k} +nxq={len(b.xq)} +last={last}\n')
    srcs = sorted({r['src_sid'] for r in recs})
    man = dict(G=G, sid=sid, leaf=k, slot=slot, expert=ex, ff=[j0 + lo, j0 + lo + 64], mutant=a.mutant, issue=a.issue,
               source_slices=srcs, local=sum(r['src_sid'] == sid for r in recs), rd0=RD0, sw_issue=t_sw,
               model_dur=dur, map=str(a.map), map_topo=M['topo'], map_slice_share=M['slice_share'],
               beats=[dict(x, body=f"{x['body']:040x}") for x in sorted(beats, key=lambda x: x['issue'])])
    (out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'GUPROP_GEN G={G} slot={slot} {ex} sources={srcs} mutant={a.mutant} issue={a.issue} sw={t_sw}')


if __name__ == '__main__':
    main()
