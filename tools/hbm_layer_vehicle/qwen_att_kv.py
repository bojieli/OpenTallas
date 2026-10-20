#!/usr/bin/env python3
"""VEH-ATT3 (10-19): the attention operands of the Qwen3-8B D4G8 layer programmes (the Qwen analogue of ds_att_kv.py).

The committed Qwen D4G8 fixture generator (tools/hbm_qwen_layer/qwen_d4g_proof.py: hgi_sim.qwen_compiler Geometry(tp=8)
on the HGI-1 functional model, bit-exact against the qwen_r25 golden, position 8191) records only expected VM values and
the HBM regions; the SM attention vehicle needs the rows the unit consumes.  This tool runs the SAME stage the same way
(run_stage, gold from golden()) and captures, on the chosen dies, at the ATT unit call:
  ATT.QK   A = q (lanes x 128, BF16-exact: round_q), K = att_rows (P x 128 FP32 = decoded FP8 E4M3, the order the unit
           consumes) + Kc = the E4M3 codes of those rows (uint8; decode(Kc) == K bit for bit, canonical zero), O = scores.
  ATT.PV   A = p (lanes x P, BF16-exact: softmax.bf16_p), V rows (+ codes), O = PV (lanes x 128).
Every capture is re-checked against the unit output it produced (att_qk(q, K) == O / att_pv(p, V) == O, every lane) and
the stage must still PASS the proof's checks (the capture does not perturb the programme).  Stages: L0 (one layer) and
chain (2-layer LOOP; L = 1 is the steady-state chained layer).

    python3 tools/hbm_layer_vehicle/qwen_att_kv.py --snapshot SNAP --cache IMG --stage L0 --ranks 0 --out OUT
Output: OUT/<stage>/att_kv.npz (keys d<rank>.L<L>.<op>.<name>) + att_kv.json (shapes, sha256, the priced d4g8 record
matched by (tag, L) from results/rtl/hbm_qwen_layer_tput_1018/static_schedule.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_qwen_layer"))
import qwen_d4g_proof as QP  # noqa: E402
import qwen_r25_golden as R  # noqa: E402
from hgi_sim import lib as A  # noqa: E402
from hgi_sim import machine as MC  # noqa: E402

F = np.float32


def _e4m3_table():
    t = np.zeros(256, dtype=np.float64)
    for c in range(256):
        e, m = (c >> 3) & 15, c & 7
        v = (m / 8.0) * 2.0 ** -6 if e == 0 else (1 + m / 8.0) * 2.0 ** (e - 7)
        t[c] = -v if c & 0x80 else v
    return t


E4M3 = _e4m3_table()
_ENC = {}
for _c in range(256):
    if (_c & 0x7F) == 0x7F or (E4M3[_c] == 0 and _c != 0):
        continue
    _ENC.setdefault(float(E4M3[_c]), _c)


def e4m3_codes(K):
    """E4M3 codes of decoded FP8 rows; decode(codes) must equal K bit for bit (zero canonical +0)."""
    K = np.asarray(K, dtype=F)
    flat = K.reshape(-1).astype(np.float64)
    try:
        codes = np.array([_ENC[float(v)] if v != 0 else 0 for v in flat], dtype=np.uint8)
    except KeyError as e:
        raise SystemExit(f"KV value {e} is not an E4M3 value")
    dec = E4M3[codes].astype(F)
    z = lambda a: np.where(a == 0, F(0), a).view(np.uint32)  # noqa: E731
    if not np.array_equal(z(dec), z(flat.astype(F))):
        raise SystemExit("E4M3 re-encode does not decode to the captured rows")
    return codes.reshape(K.shape)


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def bf16_exact(a):
    return not (np.asarray(a, dtype=F).view(np.uint32) & 0xFFFF).any()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--stage", default="L0", choices=("L0", "chain"))
    ap.add_argument("--position", type=int, default=8191)
    ap.add_argument("--ranks", default="0")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    ranks = {int(x) for x in a.ranks.split(",")}
    out = a.out / a.stage
    out.mkdir(parents=True, exist_ok=True)
    arrays, rows = {}, []
    orig = {k: MC.UNITS[k] for k in (("ATT", "QK"), ("ATT", "PV"))}

    def wrap(key, fn):
        def w(M, r, L):
            pre = {}
            for d in M.dies:
                if d.rank not in ranks:
                    continue
                lanes = (r.param & 0xF) or 16
                if key[1] == "QK":
                    _, hd, _, _, _ = M.eff(r.desc["A"], d, L)
                    x = M.vm_read(r.desc["A"], d, L, lanes, hd).reshape(lanes, hd).astype(F)
                else:
                    _, hd, _, _, _ = M.eff(r.desc["O"], d, L)
                    _, P, _, _, _ = M.eff(r.desc["A"], d, L)
                    x = M.vm_read(r.desc["A"], d, L, lanes, P).reshape(lanes, P).astype(F)
                Kr = np.asarray(MC.att_rows(M, r, d, L, hd), dtype=F)
                b = r.desc["B"]
                _, bn, bm, _, _ = M.eff(b, d, L)
                pre[d.rank] = dict(lanes=lanes, A=x, K=Kr, Kc=e4m3_codes(Kr),
                                   ring=dict(n=int(bn), m=int(bm), on=bool((r.param >> 8) & 1)))
            res = fn(M, r, L)
            for d in M.dies:
                if d.rank not in ranks:
                    continue
                e = pre[d.rank]
                o = r.desc["O"]
                _, on_, _, _, _ = M.eff(o, d, L)
                e["O"] = M.vm_read(o, d, L, e["lanes"], on_).reshape(e["lanes"], on_).astype(F)
                for h in range(e["lanes"]):
                    ref = A.att_qk(e["A"][h], e["K"]) if key[1] == "QK" else A.att_pv(e["A"][h], e["K"])
                    if not np.array_equal(np.asarray(ref, F).view(np.uint32), e["O"][h].view(np.uint32)):
                        raise SystemExit(f"d{d.rank} L{L} {r.tag}: captured operands do not reproduce O (lane {h})")
                if not bf16_exact(e["A"]):
                    raise SystemExit(f"d{d.rank} L{L} {r.tag}: A operand not BF16-exact (SM x path is BF16)")
                base = f"d{d.rank}.L{L}.{key[0]}.{key[1]}"
                meta = dict(rank=d.rank, L=int(L), op=f"{key[0]}.{key[1]}", tag=r.tag, lanes=e.pop("lanes"),
                            ring=e.pop("ring"), arrays={})
                for nm, arr in e.items():
                    arrays[f"{base}.{nm}"] = arr
                    meta["arrays"][nm] = dict(key=f"{base}.{nm}", shape=list(arr.shape), dtype=str(arr.dtype),
                                              sha256=sha(arr))
                rows.append(meta)
            return res
        return w

    for k, fn in orig.items():
        MC.UNITS[k] = wrap(k, fn)
    t0 = time.time()
    model = R.QwenR25(a.snapshot, a.cache)
    cfg = model.ck.cfg
    gold = QP.golden(model, a.stage, a.position)
    res = QP.run_stage(model, cfg, a.stage, a.position, gold=gold)
    for k, fn in orig.items():
        MC.UNITS[k] = fn
    np.savez_compressed(out / "att_kv.npz", **arrays)
    sched = json.loads((ROOT / "results/rtl/hbm_qwen_layer_tput_1018/static_schedule.json").read_text())
    priced = sched["schedule"]["base"]["d4g8"][a.stage]
    for m in rows:
        m["priced_d4g8"] = [dict(i=p["i"], start=p["start"], end=p["end"], cost=p["cost"], base_cost=p["base_cost"])
                            for p in priced if p["tag"] == m["tag"] and p["L"] == m["L"]]
    doc = dict(schema="opentallas.hbm_qwen_att_kv.v1", lane="VEH-ATT3", stage=a.stage, position=a.position,
               ranks=sorted(ranks), records=rows, proof_pass=bool(res["pass_"]),
               proof_families=res.get("families"), proof_failures=res.get("failures"),
               image_sha256=res.get("image_sha256"),
               npz_sha256=hashlib.sha256((out / "att_kv.npz").read_bytes()).hexdigest(),
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                   "hgi_sim/machine.py", "hgi_sim/qwen_compiler.py", "hgi_sim/lib.py",
                   "hbm_qwen_layer/qwen_d4g_proof.py", "qwen_r25_golden.py", "hbm_layer_vehicle/qwen_att_kv.py")},
               wall_s=round(time.time() - t0, 1),
               note="captured at the ATT unit call of the D4G8 programme (qwen_d4g_proof.run_stage); every capture "
                    "reproduces the unit's O bit for bit; K/V codes re-encoded from the decoded rows (decode-checked)")
    (out / "att_kv.json").write_text(json.dumps(doc, indent=1, default=int) + "\n")
    ok = res["pass_"] and len(rows) == 2 * len(ranks) * (1 if a.stage == "L0" else 2)
    print(f"QWEN_ATT_KV {'PASS' if ok else 'FAIL'} stage={a.stage} records={len(rows)} proof_pass={res['pass_']} -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
