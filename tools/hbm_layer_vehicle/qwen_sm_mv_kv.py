#!/usr/bin/env python3
"""SMB-INT8 (10-19): the SM.MATVEC operands of the Qwen3-8B D4G8 layer programmes (sibling of qwen_att_kv.py).

Runs the committed D4G8 stage (tools/hbm_qwen_layer/qwen_d4g_proof.py run_stage, gold from golden(), position 8191) and
captures, on the chosen ranks (one die a rank), at every SM.MATVEC unit call (all fmt 3 INT8 in qwen_compiler):
  A  = the activation the unit reads (BF16-exact: the SM x path is BF16)
  W  = the die's INT8 weight codes [m, K] exactly as the unit reads them (machine.hbm_rows_raw)
  O  = the raw FP32 sums the unit wrote (row scales are applied after the reduction by the SU consumer)
Every capture is re-checked: hgi_sim.lib.sm_int8(W, A) == O bit for bit, and the stage must still PASS the proof.

    python3 tools/hbm_layer_vehicle/qwen_sm_mv_kv.py --snapshot SNAP --cache IMG --stage L0 --ranks 0 --out OUT
Output: OUT/<stage>/sm_mv.npz (keys d<rank>.L<L>.<tag>.{A,W,O}) + sm_mv.json (shapes, sha256, the priced d4g8 record
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


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


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
    key = ("SM", "MATVEC")
    orig = MC.UNITS[key]

    def wrap(M, r, L):
        pre = {}
        if (r.param & 3) == 3 and ((r.param >> 2) & 7) == 0:
            for d in M.dies:
                if d.rank in ranks:
                    pre[d.rank] = dict(A=np.asarray(M.read(r.desc["A"], d, L), F).copy(),
                                       W=np.ascontiguousarray(M.hbm_rows_raw(r.desc["B"], d, L)).view(np.int8).copy())
        res = orig(M, r, L)
        for d in M.dies:
            if d.rank not in pre:
                continue
            e = pre[d.rank]
            e["O"] = np.asarray(M.read(r.desc["O"], d, L), F).reshape(-1).copy()
            ref = A.sm_int8(e["W"], e["A"])
            if not np.array_equal(np.asarray(ref, F).view(np.uint32), e["O"].view(np.uint32)):
                raise SystemExit(f"d{d.rank} L{L} {r.tag}: captured operands do not reproduce O")
            # the unit rounds A to BF16 itself (lib.sm_int8: to_bf16(x)); the SM's x store holds that BF16 image
            a_bf16_exact = not bool((e["A"].view(np.uint32) & 0xFFFF).any())
            base = f"d{d.rank}.L{L}.{r.tag}"
            meta = dict(rank=d.rank, L=int(L), op="SM.MATVEC", fmt=3, tag=r.tag, m=int(e["W"].shape[0]),
                        K=int(e["W"].shape[1]), A_bf16_exact=a_bf16_exact, arrays={})
            for nm, arr in e.items():
                arrays[f"{base}.{nm}"] = arr
                meta["arrays"][nm] = dict(key=f"{base}.{nm}", shape=list(arr.shape), dtype=str(arr.dtype),
                                          sha256=sha(arr))
            rows.append(meta)
        return res

    MC.UNITS[key] = wrap
    t0 = time.time()
    model = R.QwenR25(a.snapshot, a.cache)
    cfg = model.ck.cfg
    gold = QP.golden(model, a.stage, a.position)
    res = QP.run_stage(model, cfg, a.stage, a.position, gold=gold)
    MC.UNITS[key] = orig
    np.savez_compressed(out / "sm_mv.npz", **arrays)
    sched = json.loads((ROOT / "results/rtl/hbm_qwen_layer_tput_1018/static_schedule.json").read_text())
    priced = sched["schedule"]["base"]["d4g8"][a.stage]
    for m in rows:
        m["priced_d4g8"] = [dict(i=p["i"], start=p["start"], end=p["end"], cost=p["cost"], base_cost=p["base_cost"])
                            for p in priced if p["tag"] == m["tag"] and p["L"] == m["L"]]
    doc = dict(schema="opentallas.hbm_qwen_sm_mv_kv.v1", lane="SMB-INT8", stage=a.stage, position=a.position,
               ranks=sorted(ranks), records=rows, proof_pass=bool(res["pass_"]),
               proof_failures=res.get("failures"), image_sha256=res.get("image_sha256"),
               npz_sha256=hashlib.sha256((out / "sm_mv.npz").read_bytes()).hexdigest(),
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                   "hgi_sim/machine.py", "hgi_sim/qwen_compiler.py", "hgi_sim/lib.py",
                   "hbm_qwen_layer/qwen_d4g_proof.py", "qwen_r25_golden.py", "hbm_layer_vehicle/qwen_sm_mv_kv.py")},
               wall_s=round(time.time() - t0, 1),
               note="captured at the SM.MATVEC unit call of the D4G8 programme (qwen_d4g_proof.run_stage); every "
                    "capture reproduces the unit's raw FP32 O bit for bit (hgi_sim.lib.sm_int8)")
    (out / "sm_mv.json").write_text(json.dumps(doc, indent=1, default=int) + "\n")
    ok = bool(res["pass_"]) and len(rows) > 0
    print(f"QWEN_SM_MV_KV {'PASS' if ok else 'FAIL'} stage={a.stage} records={len(rows)} proof_pass={res['pass_']} "
          f"tags={[m['tag'] for m in rows]} -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
