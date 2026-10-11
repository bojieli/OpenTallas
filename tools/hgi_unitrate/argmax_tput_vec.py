#!/usr/bin/env python3
"""hgi-1010/tput1-argmax (2026-10-10): PRODUCTION-SHAPE throughput vectors for ARGMAX.LOCAL
(ot_hgi_argmax_record + ot_hgi_argmax18_m GENERIC18, tb_hgi_argmax_tput).

The records are the REAL dispatches (sequencer contract effective descriptors, tools/hgi_seq_vectors.Ref):
  qwen: hbm-sim Qwen3-8B TP4 P8,191 rank 0 token program, ARGMAX.LOCAL A = STREAM n 37,984 (the head logits from
        SU head_scale -> STREAM 1), O = VM 2 words, imm_a 37,984;
  ds:   ds_native DeepSeek-V4.1 TP96 P1,048,575 rank-0 head program (results/arch/hgi_sim_20261010/g25_proof), ARGMAX.LOCAL
        A = STREAM n 1,347 (the LM head matvec output), O = VM 2 words, imm_a 1,347.
The record bits are used verbatim; only cfg_rank varies (the global id = local + RANK * imm_a).  Logit values: FP32
gauss rows with planted structure -- the max on the LAST element (a last-beat drop fails), ties straddling the two halves
of one beat (a lane-order / tie-break error fails), a first-NaN row, +-0 rows.  Golden = numpy argmax on FP32 (lowest
index of the max, -0 == +0, the first NaN wins), hgi_sim u_argmax_local semantics.

  --model qwen|ds --out DIR      writes at_case.mem {rank 8, nan 4, value 32, id 32, first word 32, n 32, rec 684},
                                 at_str.mem (one FP32 word a line), at_sizes.svh, at_cases.json (price per record)
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'hgi_adapters'))
import common as C  # noqa: E402
from argmax_bench import am_ref, rec_bus  # noqa: E402
from hgi_sim import timing as T  # noqa: E402

DS_PROG = ROOT / 'results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json'
# the DS price the token is charged (budget.json ds_hbm ARGMAX.LOCAL): hgi_sim.ds_native_timing.NativeCost -> the walk's
# 'su:argmax_local' node, 142.668 cycles (computed on DS_PROG at main 445ca2a45)
DS_PRICE = 142.668


def ds_dispatch():
    from hgi_sim.records import decode_one
    dd = json.loads(DS_PROG.read_text())
    lay = dd['layers'][-1]
    assert lay['layer'] == 'head'
    words = []
    for x in lay['records']:
        b = bytes.fromhex(x['hex'])
        words += [int.from_bytes(b[q:q + 16], 'little') for q in range(0, len(b), 16)]
    words += C.SV.record(C.SV.header('CTL', 'END'), descs={'A': C.SV.mdesc(space=1, fmt=5, base=(1 << 18) - 16, n=1, m=1)})
    tr, _ = C.SV.Ref(words, 0, 0, (1 << 20) - 1, 0, 129280, 1 << 20, {}).run()
    return tr


def f2w(x):
    return struct.unpack('<I', struct.pack('<f', float(x)))[0]


def rows(n, rng, lps=16):
    """(name, words) production-length rows with planted structure"""
    out = []
    g = lambda: [f2w(x) for x in rng.normal(0, 4, n).astype(np.float32)]
    w = g(); w[n - 1] = f2w(64.0); out.append(('max_last', w))                 # a dropped last beat loses the max
    w = g(); b = (n // 2) // lps * lps                                         # a tie straddling the halves of one beat
    w[b + lps // 2 + 1] = w[b + 1] = f2w(50.0); out.append(('tie_halves', w))
    w = g(); w[3] = w[n - 2] = f2w(40.0); out.append(('tie_far', w))
    w = g(); w[n // 3] = 0x7FC00001; w[n // 2] = 0x7FC00002; out.append(('nan_first', w))
    w = [0x80000000 if i % 3 else 0 for i in range(n)]; w[n - 1] = 0x80000000; out.append(('zeros', w))
    out.append(('gauss', g()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True, choices=['qwen', 'ds'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=20261010)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.model == 'qwen':
        tr, _ = C.qwen_dispatch()
        ranks = (0, 3)
    else:
        tr = ds_dispatch()
        ranks = (0, 95)
    d = [x for x in tr if C.unit_of(x) == 7]
    assert len(d) == 1, len(d)
    d = d[0]
    A = d['eff'][0]
    assert C.fld(A, 'space') == 2, 'ARGMAX.LOCAL A must be the STREAM'
    n, imm = d['n'][0], C.fld(d['hdr'], 'imm_a', C.UOP)
    O = d['eff'][4]
    if a.model == 'qwen':
        recs, words, recs_py = None, None, None
        _, recs_py, _, _ = C.SV.qwen_program()
        r = [r for r in recs_py if r.unit == 'ARGMAX'][0]
        price, grade, how = T.cost(r, T.Dyn(8191, 0), 0)
    else:
        price, grade, how = DS_PRICE, 'measured', 'walk su:argmax_local (ds_native_timing.NativeCost)'
    rng = np.random.default_rng(a.seed)
    cases, strm, man = [], [], []
    for rank in ranks:
        for name, w in rows(n, rng):
            val, gid, nan = am_ref(w, rank, imm)
            cases.append(f'{rank:02X}{int(nan):01X}{val:08X}{gid & 0xFFFFFFFF:08X}{len(strm):08X}{n:08X}' +
                         C.hexw(rec_bus(d), 684))
            man.append(dict(k=len(man), tag=f'{a.model}.argmax_local.{name}.r{rank}', rank=rank, n=n, imm_a=imm,
                            value=f'{val:08x}', id=gid, nan=nan, cost=round(float(price), 3)))
            strm.extend(w)
    (out / 'at_case.mem').write_text('\n'.join(cases) + '\n')
    (out / 'at_str.mem').write_text(''.join(f'{x:08X}\n' for x in strm))
    (out / 'at_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NSTR = {len(strm)};\n')
    (out / 'at_cases.json').write_text(json.dumps(dict(
        model=a.model, n=n, imm_a=imm, o_base=C.fld(O, 'base'), o_istride=C.fld(O, 'istride'), price=price,
        price_grade=grade, price_how=how, cases=man), indent=1))
    print(f'{a.model}: {len(cases)} records n {n} imm_a {imm} price {price:.1f} ({how}); O base {C.fld(O, "base")}')


if __name__ == '__main__':
    main()
