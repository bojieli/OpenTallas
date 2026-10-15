#!/usr/bin/env python3
"""Continuous-run glue of tools/s81_ftok (s81-functional-token r3, 2026-10-14): the checks between RTL stages.

  head  --hout <L39 hop flits>        the final hop output -> h (4 x 5120) == shard h_out of L39; the head's
                                      hc_pre + final norm (golden function: the head die's HC NORM is not in a bench)
                                      == shard xf, the input the head-terminal bench's roots were built from
  mtp0  --mtp DIR --out DIR           DSpark stage-0 inputs: 4 copies of embed[y], embed[noise] x 4 rows, HIDDEN flits
  mtpo  --hout <M2R<i> hop flits> --mtp DIR --row i
                                      the last DSpark stage's hop output of row i == golden stage-2 output, and its
                                      hc_pre + norm == the draft-head bench's xf of row i
"""
import argparse, os, pickle, sys, json, hashlib
from pathlib import Path
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "tools/s81_suhc"))
F = np.float32
GOLD = Path(os.environ.get("OT_DSROM_1M_GOLD", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))


def rows_to_h(path):
    """hop flits (header + 640 rows) -> h [4, 5120] (inverse of hc_gate.Run.h_rows)"""
    ln = [l for l in Path(path).read_text().split("\n") if l.strip()]
    assert len(ln) == 641, (path, len(ln))
    hb = np.zeros((4, 5120), np.uint32)
    for q, l in enumerate(ln[1:]):
        v = int(l, 16)
        for j in range(32):
            e, k = 8 * q + j // 4, j % 4
            hb[k][e] = (v >> (16 * j)) & 0xFFFF
    return (hb << 16).astype(np.uint32).view(F)


def h_to_flits(h, path):
    import hc_gate as HG
    with open(path, "w") as f:
        f.write(f"{0:0128x}\n")
        for r in HG.Run(256).h_rows(np.asarray(h, F)):
            f.write(f"{r:0128x}\n")


def same(a, b):
    return np.array_equal(np.asarray(a, F).view(np.uint32), np.asarray(b, F).view(np.uint32))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=("head", "mtp0", "mtpo"))
    ap.add_argument("--hout")
    ap.add_argument("--mtp")
    ap.add_argument("--out")
    ap.add_argument("--row", type=int, default=0)
    ap.add_argument("--native-prep", type=Path, help="actual RTL head preparation output directory (xf.npy and source provenance)")
    a = ap.parse_args()
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    def native_xf():
        if a.native_prep is None:
            return None
        w = a.native_prep
        m = json.loads((w / "xf.provenance.json").read_text())
        digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        assert m["gate"] == "PASS" and m["arithmetic"] == "RTL only; no DPI", "unqualified head prep"
        assert m["actual_output_sha256"] == digest(w / "xf.mem"), "head prep output changed"
        assert m["inputs"]["hout"]["sha256"] == digest(a.hout), "wrong upstream hop handoff"
        xf = np.load(w / "xf.npy")
        words = np.array([int(x,16) for x in (w / "xf.mem").read_text().split()], np.uint32)
        assert same(xf, (words << 16).view(F)), "xf.npy differs from actual RTL dump"
        assert xf.shape == (5120,), "head output shape"
        return xf
    if a.step == "head":
        h = rows_to_h(a.hout)
        z = np.load(GOLD / "ctx1048576_L39.npz"); zh = np.load(GOLD / "ctx1048576_head.npz")
        assert same(h, z["h_out"]), "L39 hop output != shard h_out"
        xf = native_xf()
        if xf is None:
            ck = LC.Checkpoint(); m, _ = LC.build_model(ck, engram=False)
            xf = V.rmsnorm_fold(m.hc_pre(h, z["pre_out"]), m.w["norm.weight"], m.eps)
            print("HISTORICAL_REFERENCE_GLUE: HC_PRE+RMSNorm supplied by Python; not native qualification")
        assert same(xf, zh["xf"]), "head xf from the RTL rows != shard xf"
        print("HEAD_GLUE PASS: L39 hop output == h_out; hc_pre + norm == xf (the head bench's input)")
    elif a.step == "mtp0":
        ck = LC.Checkpoint(); m, _ = LC.build_model(ck, engram=False)
        ids = [21946] + [m.noise_id] * (m.dspark_block - 1)
        for i, t in enumerate(ids):
            row = np.asarray(ck.rows("embed.weight", [t])[0], F)
            fx = pickle.loads((Path(a.mtp) / f"hc_chain_M0R{i}.pkl").read_bytes())
            h = np.repeat(row[None, :], 4, axis=0)
            assert same(h, fx["chain"]["h_in"]), f"embed[{t}] x 4 != DSpark stage-0 row {i} input"
            h_to_flits(h, Path(a.out) / f"hin_M0R{i}.mem")
        print("MTP0_GLUE PASS: 5 DSpark stage-0 inputs (embed[y], embed[noise] x 4) == golden, flits written")
    else:
        h = rows_to_h(a.hout)
        fx = pickle.loads((Path(a.mtp) / f"hc_chain_M2R{a.row}.pkl").read_bytes())
        assert same(h, fx["chain"]["h_out"]), f"M2R{a.row} hop output != golden stage-2 output"
        z = np.load(Path(a.mtp) / "draft_head.npz")
        xn = native_xf()
        if xn is None:
            ck = LC.Checkpoint(); m, _ = LC.build_model(ck, engram=False)
            Lf = m.L + m.n_mtp - 1
            xn = V.rmsnorm_bf16(V.to_bf16(m.hc_pre(h, fx["chain"]["pre_out"])), m.lw(Lf, "norm.weight"), m.eps)
            print("HISTORICAL_REFERENCE_GLUE: HC_PRE+RMSNorm supplied by Python; not native qualification")
        assert same(xn, z["xf"][a.row]), f"draft row {a.row}: xf from the RTL rows != golden"
        print(f"MTPO_GLUE PASS row {a.row}: stage-2 hop output == golden; hc_pre + norm == draft-head xf")


if __name__ == "__main__":
    main()
