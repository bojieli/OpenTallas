#!/usr/bin/env python3
"""HBM-NEXT-UNITS-SUDMA2 2026-10-19: FUSED.QDQ_* N-row records on the d4g static QDQ engine (ot_hgi_qdq_program_static:
fixed beat calendar, the released decoder, eight real VM bank pipelines; RTL unchanged), bench tb_hgi_qdq_static (d4g).

    hnx_qdq_rows_vectors.py OUT --n N [--op QDQ_FP8|QDQ_FP4_E4M3] [--e 512] [--seed 0] [--mut-stride]

One N-row record (verify positions r = 0 .. N-1) of e elements a row (DS kv_row_qdq: QDQ_FP8, e = 512, block 32;
cmp.ckv_qdq: QDQ_FP4_E4M3, e = 512, block 16), rows at A = A0 + r rs_A, O = O0 + r rs_O (rs = e words: the verify rows'
KV vectors are contiguous). The engine issues one 32-element beat (4 contiguous VM sectors) a cycle; an N-row record
is the N rows' beats back to back in ONE programme range (row r's beats carry src / dst + r rs / 8 sectors, the last
beat of a row its record-last bit) -- compiler-only: no RTL change. Price (isa_rows.py FUSED.QDQ_*): n / 32 a row.
The bench's throughput bound is the row price: recs cost = ceil(e / 32) + 8 for row 0 (the d4g record price, fixed
pipeline once) and e / 32 for every further row; it asserts last commit <= 1.1 x the sum.
Golden: hdc_golden_v41.qdq_fp8 / qdq_fp4_e4m3 (released, NumPy), independent of the DUT.
--mut-stride: the PROGRAMME drops the row stride (every row's beats read row 0's A; the golden stays per row) -> the
bench must FAIL (gold mismatch): the witness that the row addresses come from the programme words.
Outputs (tb_hgi_qdq_static format): recs.txt, in_k.hex / out_k.hex (k = row), program.hex (one 256-b word a beat:
c7a1 magic [255:240], PC [233:224], {last, dst16, src16, block8, op6, v} [47:0]), meta.json.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_golden_v41 as G  # noqa: E402

OPS = {"QDQ_FP8": (4, 32, G.qdq_fp8), "QDQ_FP4_E4M3": (6, 16, G.qdq_fp4_e4m3)}
A0, O0 = 51776, 51776 + 8 * 512           # production kv_row base; O after the last row's A (rows <= 8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--n", type=int, required=True); ap.add_argument("--e", type=int, default=512)
    ap.add_argument("--op", choices=tuple(OPS), default="QDQ_FP8"); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mut-stride", action="store_true")
    a = ap.parse_args()
    N, E = a.n, a.e
    assert 1 <= N <= 8 and E % 32 == 0 and N * E // 32 <= 1024
    code, block, gold = OPS[a.op]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    lines, prog, meta = [], [], []
    nb = E // 32
    for r in range(N):
        x = (rng.standard_normal(E) * rng.uniform(0.05, 4.0)).astype(np.float32)
        with np.errstate(over="ignore", under="ignore", invalid="raise"):
            y = np.asarray(gold(x.copy(), block=block), dtype=np.float32)
        xb, yb = x.view(np.uint32), y.view(np.uint32)
        assert not (yb & 0xFFFF).any()
        ab, ob = A0 + E * r, O0 + E * r
        (out / f"in_{r}.hex").write_text("".join("".join(f"{int(w):08x}" for w in reversed(xb[s:s + 8])) + "\n"
                                                for s in range(0, E, 8)))
        (out / f"out_{r}.hex").write_text("".join("".join(f"{int(w):08x}" for w in reversed(yb[s:s + 8])) + "\n"
                                                 for s in range(0, E, 8)))
        cost = nb + 8 if r == 0 else nb
        lines.append(f"{code} {E} {ab} {ob} {cost} {block}")
        sab = A0 if a.mut_stride else ab
        for s in range(nb):
            pc = len(prog)
            pay = (int(s == nb - 1) << 47) | ((ob // 8 + 4 * s) << 31) | ((sab // 8 + 4 * s) << 15) | (block << 7) | (code << 1) | 1
            prog.append((0xC7A1 << 240) | (pc << 224) | pay)
        meta.append(dict(row=r, a_base=ab, o_base=ob, beats=nb, cost=cost))
    (out / "recs.txt").write_text(f"{N}\n" + "\n".join(lines) + "\n")
    # the d4g bench checks every word's payload against the PRODUCTION record (row-strided); the stride mutant
    # writes a different programme and so is caught there at configuration ("compiler programme command differs")
    # unless --mut-stride also patches the record line -- keep the record (golden) per row and let the bench decide.
    (out / "program.hex").write_text("".join(f"{w:064x}\n" for w in prog))
    total = sum(m["cost"] for m in meta)
    (out / "meta.json").write_text(json.dumps(dict(schema="opentallas.hbm_next.qdq_rows.v1", n=N, e=E, op=a.op,
        block=block, beats=len(prog), price_row=nb, price_c1=nb + 8, cost_total=total, mut_stride=a.mut_stride,
        rows=meta, golden="hdc_golden_v41 " + gold.__name__), indent=1) + "\n")
    print(f"N={N} beats={len(prog)} cost={total}")


if __name__ == "__main__":
    main()
