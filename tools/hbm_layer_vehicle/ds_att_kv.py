#!/usr/bin/env python3
"""VEH-ATT (10-19): the KV / key operands of the DeepSeek-V4.1 attention records of one layer, as the bit-exact native
programme (tools/hgi_sim/ds_native.py, released checkpoint, 1M context, W17 reference shards) hands them to the units.

ds_layer_fixtures.py records HBM operands as (address, bytes, sha256) only (and the ATT C operand's effective m is 1 there,
the dynamic selected-row count lives in n); the attention vehicle needs the rows themselves.  This tool runs the same layer
the same way and captures, on the chosen ranks, at the unit call:
  ATT.QK / ATT.PV   K = machine.att_rows(...) [T, 512] FP32 (ring rows oldest first, then the selected compressed rows,
                    the exact order the unit consumes), the ring slot list, the C (selected) row count, the A operand
                    (q for QK [lanes, 512]; p for PV [lanes, T]) and the unit's output O (scores [T] / PV [512]).
  IDX.INDEX         the query A, head weights B, the owned key ids idx and their key rows (machine.index_keys: FP4 grid),
                    and the scores v (die.index_last) the frame computes.
Output: OUT/<L>/att_kv.npz (keys r<rank>.<op>.<occ>.<name>) + att_kv.json (shapes, sha256, eff descriptors, the priced
record matched by (op, tag, occurrence) exactly as ds_layer_fixtures does).  Every captured array is cross-checked
against the unit output it produced (QK: att_qk(q, K) == O, PV: att_pv(p, K) == O) before it is written.

    HDC_V41_ARITH=chunk8 OT_V41_FLASH_SNAPSHOT=CKPT python3 tools/hbm_layer_vehicle/ds_att_kv.py \
        --layer 2 --ranks 0 --refs REFS --out OUT          (fleet: run_ds_fixtures.sh host / inputs)
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
from hgi_sim import machine as MC  # noqa: E402

F = np.float32
OPS = {("ATT", "QK"), ("ATT", "PV"), ("IDX", "INDEX")}


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layer", required=True, help="0..42")
    ap.add_argument("--ranks", default="0")
    ap.add_argument("--refs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ranks = {int(x) for x in a.ranks.split(",")}
    out = a.out / f"L{int(a.layer):02d}"
    out.mkdir(parents=True, exist_ok=True)
    arrays, rows, seen = {}, [], Counter()
    orig_units = DN.ds_units

    def units(*x, **k):
        u = orig_units(*x, **k)
        wrapped = {}
        for key, fn in u.items():
            if key not in OPS:
                wrapped[key] = fn
                continue

            def w(M, r, L, _fn=fn, _key=key):
                layer = DN.CUR_LAYER[0]
                dies = [d for d in M.dies if d.rank in ranks]
                pre = {}
                cur = M.cur
                M.cur = r
                try:
                    for d in dies:
                        rd = M.rec_of(d, r)
                        ent = dict(eff=DN._eff_trace(M, d, rd, L))
                        if _key[0] == "ATT":
                            lanes = (rd.param & 0xF) or 16
                            ent["lanes"] = lanes
                            if _key[1] == "QK":
                                _, hd, _, _, _ = M.eff(rd.desc["A"], d, L)
                                ent["A"] = M.vm_read(rd.desc["A"], d, L, lanes, hd).reshape(lanes, hd).astype(F)
                            else:
                                _, hd, _, _, _ = M.eff(rd.desc["O"], d, L)
                                _, P, _, _, _ = M.eff(rd.desc["A"], d, L)
                                ent["A"] = M.vm_read(rd.desc["A"], d, L, lanes, P).reshape(lanes, P).astype(F)
                            ent["K"] = np.asarray(MC.att_rows(M, rd, d, L, hd), dtype=F)
                            b = rd.desc["B"]
                            _, bn, bm, _, _ = M.eff(b, d, L)
                            ent["ring"] = dict(n=int(bn), m=int(bm), on=bool((rd.param >> 8) & 1),
                                               first=int((d.dyn[2] - bn) % bm) if (rd.param >> 8) & 1 else 0)
                            c = rd.desc.get("C")
                            ent["c_rows"] = int(M.eff(c, d, L)[1]) if c is not None else 0
                        else:
                            ih = rd.desc["B"].n
                            ent["A"] = M.read(rd.desc["A"], d, L).astype(F).reshape(ih, -1)
                            ent["B"] = M.read(rd.desc["B"], d, L).astype(F)
                            idx, blocks = MC.index_owned(d.rank % M.cfg["coll_group_size"], rd.imm_a,
                                                         M.cfg["coll_group_size"])
                            ent["idx"] = np.asarray(idx, dtype=np.int64)
                        pre[d.rank] = ent
                finally:
                    M.cur = cur
                res = _fn(M, r, L)
                M.cur = r
                try:
                    for d in dies:
                        ent = pre[d.rank]
                        rd = M.rec_of(d, r)
                        name = f"{_key[0]}.{_key[1]}"
                        occ = seen[(layer, d.rank, name, rd.tag)]
                        seen[(layer, d.rank, name, rd.tag)] += 1
                        base = f"r{d.rank}.{name}.{occ}"
                        o = rd.desc["O"]
                        _, on_, om, _, _ = M.eff(o, d, L)
                        if _key[0] == "ATT":
                            lanes = ent["lanes"]
                            ent["O"] = M.vm_read(o, d, L, lanes, on_).reshape(lanes, on_).astype(F)
                            for h in range(lanes):          # the captured operands reproduce the unit output
                                ref = (MC.A.att_qk(ent["A"][h], ent["K"]) if _key[1] == "QK"
                                       else MC.A.att_pv(ent["A"][h], ent["K"]))
                                if not np.array_equal(np.asarray(ref, F).view(np.uint32), ent["O"][h].view(np.uint32)):
                                    raise SystemExit(f"{base}: captured operands do not reproduce O (lane {h})")
                        else:
                            idx_, v = d.index_last
                            # the key store accessor is attached by ds_native's index_frame handler at the call
                            ent["keys"] = np.asarray(M.index_keys(d, rd.imm_b, ent["idx"]), dtype=F)
                            ent["v"] = np.asarray(v, dtype=np.float64)
                            ent["O"] = M.read(o, d, L).view(np.uint32).copy()
                        meta = dict(layer=layer, rank=d.rank, op=name, tag=rd.tag, occ=occ,
                                    eff={k: [int(x) if isinstance(x, (int, np.integer)) else x for x in v]
                                         for k, v in ent.pop("eff").items()}, arrays={})
                        for nm in ("ring", "c_rows", "lanes"):
                            if nm in ent:
                                meta[nm] = ent.pop(nm)
                        for nm, arr in ent.items():
                            arrays[f"{base}.{nm}"] = arr
                            meta["arrays"][nm] = dict(key=f"{base}.{nm}", shape=list(arr.shape), dtype=str(arr.dtype),
                                                      sha256=sha(arr))
                        rows.append(meta)
                finally:
                    M.cur = cur
                return res
            wrapped[key] = w
        return wrapped

    DN.ds_units = units
    sys.argv = ["ds_native", "--refs", str(a.refs), "--out", str(out / "ds_native.json"), "--layers", str(int(a.layer))]
    rc = DN.main()
    keep = [r for r in rows if r["layer"] == int(a.layer)]
    # priced record match (same rule as ds_layer_fixtures.match_priced: (orig_op, tag, occurrence))
    pl = json.loads((TOOLS.parent / "results/rtl/hbm_ds_layer_tput_1018/priced_layers.json").read_text())
    seg = pl["segments"].get(str(int(a.layer)), {"records": []})
    occ = Counter()
    for rec in seg["records"]:
        key = (rec["orig_op"], rec["tag"])
        o = occ[key]
        occ[key] += 1
        for e in keep:
            if (e["op"], e["tag"], e["occ"]) == (rec["orig_op"], rec["tag"], o):
                e.setdefault("priced", []).append(dict(i=rec["i"], start=rec["start"], end=rec["end"],
                                                       base_cost=rec["base_cost"]))
    keys = {v["key"] for e in keep for v in e["arrays"].values()}
    np.savez(out / "att_kv.npz", **{k: v for k, v in arrays.items() if k in keys})
    doc = dict(schema="opentallas.hbm_ds_att_kv.v1", layer=int(a.layer), ranks=sorted(ranks), records=keep,
               npz_sha256=hashlib.sha256((out / "att_kv.npz").read_bytes()).hexdigest(),
               note="captured at the unit call of the bit-exact native programme; every ATT capture reproduces the "
                    "unit's O bit for bit (checked before writing)")
    (out / "att_kv.json").write_text(json.dumps(doc, indent=1) + "\n")
    v = json.loads((out / "ds_native.json").read_text())
    ok = all(x.get("verdict") == "pass" for x in v.get("results", []))
    print(f"DS_ATT_KV {'PASS' if ok and keep else 'FAIL'} layer={a.layer} records={len(keep)} -> {out}")
    return 0 if ok and keep and not rc else 1


if __name__ == "__main__":
    raise SystemExit(main())
