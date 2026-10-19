#!/usr/bin/env python3
"""VEH-FMT-SM (10-18): the HBM weight operands of the DeepSeek-V4.1 SM.MATVEC records of one layer, as the bit-exact
native programme (tools/hgi_sim/ds_native.py) hands them to the matrix engine.

ds_layer_fixtures.py records HBM operands as (address, bytes, sha256) but the DS weights are not die.hbm regions
(ds_native's sm handler reads them from the released checkpoint through the image manifest: man.find + wrows), so
the fixtures carry 'HBM access ... outside every region' for every SM B operand.  This tool runs the same layer the
same way and captures, for every SM.MATVEC record on the chosen ranks, the weight operand at the engine call:
  BF16 records (V_.mv)       -> uint16 BF16 bits [m, K] (asserted exactly BF16: low 16 bits of the FP32 zero);
  FP8 / FP4 records (V_.linear_q, Q8) -> q (FP32 values on the E4M3 / E2M1 grid) [m, K] + e (int32 block exponents).
Output: OUT/<L>/weights.npz (keys r<rank>.k<k>.{W | Wq, We}) + weights.json (per record: k_layer, tag, occ, fmt, shape,
sha256 of each array, the priced record matched by (op, tag, occurrence) as ds_layer_fixtures does).

    HDC_V41_ARITH=chunk8 OT_V41_FLASH_SNAPSHOT=CKPT python3 tools/hbm_layer_vehicle/ds_sm_weights.py \
        --layer 0 --ranks 0 --refs REFS --out OUT          (fleet: run_ds_fixtures.sh host / inputs)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from hgi_sim import ds_native as DN  # noqa: E402


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layer", required=True, help="0..42 or head")
    ap.add_argument("--ranks", default="0")
    ap.add_argument("--refs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ranks = {int(x) for x in a.ranks.split(",")}
    lay = a.layer
    out = a.out / (lay if lay == "head" else f"L{int(lay):02d}")
    out.mkdir(parents=True, exist_ok=True)
    V = DN.V_
    arrays, rows, seen = {}, [], Counter()
    per_rank_k = Counter()
    state = dict(rec=None, dies=None, n=0)

    def rec_engine(name, orig):
        def f(w, x, *args, **kw):
            r, dies = state["rec"], state["dies"]
            if r is not None:
                die = dies[state["n"]]
                state["n"] += 1
                if die.rank in ranks:
                    key = f"r{die.rank}.k{state['k'][die.rank]}"
                    if isinstance(w, V.Q8):
                        arrays[key + ".Wq"] = np.asarray(w.q, np.float32)
                        arrays[key + ".We"] = np.asarray(w.e, np.int32)
                        ent = dict(kind="Q8", shape=list(np.shape(w.q)), sha_q=sha(arrays[key + ".Wq"]),
                                   sha_e=sha(arrays[key + ".We"]))
                    else:
                        wf = np.ascontiguousarray(np.asarray(w, np.float32))
                        bits = wf.view(np.uint32)
                        assert not (bits & 0xFFFF).any(), "BF16 weight operand with non-zero low half"
                        arrays[key + ".W"] = (bits >> 16).astype(np.uint16)
                        ent = dict(kind="BF16", shape=list(wf.shape), sha=sha(arrays[key + ".W"]))
                    state["caps"].append(dict(rank=die.rank, engine=name, **ent))
            return orig(w, x, *args, **kw)
        return f

    orig_units = DN.ds_units

    def units(*x, **k):
        u = orig_units(*x, **k)
        out_u = {}
        for key, fn in u.items():
            def w(M, r, L, _fn=fn, _key=key):
                dies = [d for d in M.dies]
                layer = DN.CUR_LAYER[0]
                if _key == ("SM", "MATVEC"):
                    state.update(rec=r, dies=dies, n=0, caps=[], k={d.rank: per_rank_k[(layer, d.rank)] for d in dies})
                try:
                    res = _fn(M, r, L)
                finally:
                    if _key == ("SM", "MATVEC"):
                        for c in state["caps"]:
                            occ = seen[(layer, c["rank"], r.tag)]
                            rows.append(dict(layer=layer, k=state["k"][c["rank"]], tag=r.tag, occ=occ,
                                             fmt=int(r.param) & 3, **c))
                        for d in dies:
                            seen[(layer, d.rank, r.tag)] += 1
                        state.update(rec=None)
                for d in dies:
                    per_rank_k[(layer, d.rank)] += 1
                return res
            out_u[key] = w
        return out_u

    V.mv = rec_engine("mv", V.mv)
    V.linear_q = rec_engine("linear_q", V.linear_q)
    DN.ds_units = units
    argv = ["ds_native", "--refs", str(a.refs), "--out", str(out / "ds_native.json")]
    last = max(int(p.stem.split("_L")[1]) for p in a.refs.glob("ctx*_L*.npz"))
    argv += (["--layers", str(last), "--head"] if lay == "head" else ["--layers", str(int(lay))])
    sys.argv = argv
    rc = DN.main()
    tgt = max(r["layer"] for r in rows) if (lay == "head" and rows) else (None if lay == "head" else int(lay))
    keep = [r for r in rows if r["layer"] == tgt]
    # k = layer-local dispatch index per rank (per_rank_k is keyed by (layer, rank)) = ds_layer_fixtures k_layer
    keys = {f"r{r['rank']}.k{r['k']}" for r in keep}
    np.savez(out / "weights.npz", **{k: v for k, v in arrays.items() if k.rsplit(".", 1)[0] in keys})
    doc = dict(schema="opentallas.hbm_ds_sm_weights.v1", layer=lay, ranks=sorted(ranks), records=keep,
               note="k = dispatch index of the record within its layer on that rank (= ds_layer_fixtures k_layer); "
                    "match fixtures by (tag, occ)")
    (out / "weights.json").write_text(json.dumps(doc, indent=1) + "\n")
    v = json.loads((out / "ds_native.json").read_text())
    ok = all(x.get("verdict") == "pass" for x in v.get("results", []))
    print(f"DS_SM_WEIGHTS {'PASS' if ok and keep else 'FAIL'} layer={lay} records={len(keep)} -> {out}")
    return 0 if ok and keep and not rc else 1


if __name__ == "__main__":
    raise SystemExit(main())
