#!/usr/bin/env python3
"""TOKSIM-S81B/SMX (2026-10-19): case files for tb_toksim_smx (the release softmax share ot_s81_su_sms) at production
shape.  Golden cases = the 1M token's attend chains of su_cases_v2_ildr.pkl (L0 T 128 sliding window, L2 T 640 =
window 128 + 512 selected; ONE real head per case, scores already scaled: the chain has no scale op, so scale = 1.0),
the real head placed in every one of the 16 head slots; the reference (tools/dsrom_su_softmax.reference = the
hdc_golden_v41 attend softmax + normalise + inverse RoPE) is asserted equal to the chain's own checks (e, o_own) before
any file is written.  Plus random 16-head stress cases (dsrom_su_softmax.stress_cases).  File format: write_case.

    python3 tools/s81_su_sm/toksim_smx_prep.py --cases tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl --work W [--stress 4]
"""
import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_su_softmax as SM  # noqa: E402

F = np.float32


def golden(pkl):
    d = pickle.loads(Path(pkl).read_bytes())
    out = []
    for c in d["cases"]:
        if c["meta"].get("fn") != "attend":
            continue
        T = c["meta"]["T"]
        init = dict(c["init"])
        ops = c["ops"]
        s1 = np.asarray(init[ops[0]["abase"]], F).reshape(1, T)
        sk1 = np.asarray(init[ops[2]["abase"]], F).reshape(1)
        pv1 = np.asarray(init[ops[4]["abase"]], F).reshape(1, SM.ROW)
        cos = np.asarray(c["cr_lo"][:SM.TAIL // 2]).astype(np.uint32).view(F)
        sin = np.asarray(c["cr_hi"][:SM.TAIL // 2]).astype(np.uint32).view(F)
        scale = F(1.0)
        chk = {lab: np.asarray(w, np.uint32) for lab, _a, w, _k in c["checks"]}
        r1 = SM.reference(s1, scale, sk1, pv1, cos, sin)
        agree = {"e": bool(np.array_equal(SM.u32(r1["e"]), chk[[k for k in chk if k.startswith("exp")][0]])),
                 "o": bool(np.array_equal(SM.u32(r1["o"]), chk["o_own"]))}
        assert all(agree.values()), (c["name"], agree)
        H = SM.H
        s, sk, pv = np.repeat(s1, H, 0), np.repeat(sk1, H), np.repeat(pv1, H, 0)
        ref = SM.reference(s, scale, sk, pv, cos, sin)
        out.append(dict(name=c["name"].replace(".", "_") + f"_T{T}", layer=c["meta"]["layer"], T=T, s_raw=s, scale=scale,
                        sink=sk, pv=pv, cos=cos, sin=sin, ref=ref, source="golden 1M token (real head x16 slots)",
                        reference_equals_chain_checks=agree))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--stress", type=int, default=4)
    a = ap.parse_args()
    cs = golden(a.cases) + SM.stress_cases(a.stress)
    meta = []
    for c in cs:
        SM.write_case(Path(a.work) / c["name"], c, 16)
        meta.append(dict(name=c["name"], layer=c["layer"], T=c["T"], source=c["source"],
                         reference_equals_chain_checks=c.get("reference_equals_chain_checks")))
    (Path(a.work) / "cases.json").write_text(json.dumps(dict(cases=meta, cases_pkl_sha256=SM.sha(a.cases)), indent=1) + "\n")
    print("prepared", [m["name"] for m in meta])


if __name__ == "__main__":
    main()
