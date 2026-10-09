#!/usr/bin/env python3
"""hbm-forks (2026-10-09): Qwen softmax on the UNCHANGED fused engine ot_dsrom_su_softmax (REVIEW_20261009 D3: no
sink-off bit; the sink is data) + the X2 stage-cycle measurement.

Qwen data: sink = -2^100 for every head (exp(sink - max) underflows to +0 in the engine's exp, so den = es + (+0) =
es), inverse-RoPE tail cos = 1, sin = 0 (re = bf16(a*1 + b*0) = bf16(a): the tail passes).  The expected files are
written from the QWEN r25 reference (no sink term, no rotation: e = exp(s*scale - max), Z = csum chunk8, o = bf16(pv / Z)),
NOT from the DS reference, so a PASS proves the engine reproduces the Qwen golden bit for bit with today's RTL.
Negative: the same cases with sink = 0 (a finite sink) against the Qwen reference must FAIL.
X2: the SMX event cycles of each run (max, exp, den, normalise) at T = 640 / 128 / 16 per pass; the 8K multipass
composition (13 x 640-row chunks) is computed from them in the record.

  python3 tools/hbm_forks_sfx_qwen.py prep --work W      # case dirs W/lph16/<case>, mutant W/lph16m/<case>
  (build: python3 tools/dsrom_su_softmax.py build --work W --lph 16 ; run: this script's `run`)
  python3 tools/hbm_forks_sfx_qwen.py run --work W       # runs, verdict, record JSON W/qwen_sink_data.json
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_su_softmax as S  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402

F = np.float32
H, TAIL, ROW = S.H, S.TAIL, S.ROW


def qwen_ref(s_raw, scale, pv):
    s = V.mul(s_raw, F(scale))
    mb = np.max(s, axis=1)
    e = V.exp(V.add(s, V.neg(mb)[:, None]))
    es = V.reduce_rows(e)
    o = V.to_bf16(V.div(pv, es[:, None]))
    return dict(s=s, max=mb, e=e, es=es, den=es, o=o)


def cases(seed=20261009):
    rng = np.random.default_rng(seed)
    out = []
    for k, T in enumerate((640, 640, 128, 16, 640, 128)):
        kind = k % 3
        if kind == 0:
            s_raw = rng.normal(0, 4, (H, T)).astype(F)
        elif kind == 1:
            s_raw = (rng.normal(0, 1, (H, T)) * rng.choice([1, 30, 300], (H, T))).astype(F)
            s_raw[:, 3] = s_raw.max(axis=1)
        else:
            s_raw = np.clip(rng.standard_cauchy((H, T)) * 3, -1e4, 1e4).astype(F)
        scale = F(0.08838834764831845)                     # Qwen head_dim 128: FP32(128 ** -0.5)
        pv = (rng.normal(0, 1, (H, ROW)) * rng.choice([1e-3, 1, 50], (H, ROW))).astype(F)
        out.append(dict(name=f"qwen{k}_T{T}", T=T, s_raw=s_raw, scale=scale, pv=pv))
    return out


def cmd_prep(a):
    w = Path(a.work)
    meta = []
    for c in cases():
        ref = qwen_ref(c["s_raw"], c["scale"], c["pv"])
        cos, sin = np.ones(TAIL // 2, F), np.zeros(TAIL // 2, F)
        for tag, sink in (("", F(-2.0 ** 100)), ("m", F(0.0))):
            d = dict(name=c["name"], layer=None, T=c["T"], s_raw=c["s_raw"], scale=c["scale"],
                     sink=np.full(H, sink, F), pv=c["pv"], cos=cos, sin=sin, ref=ref)
            S.write_case(w / f"lph16{tag}" / c["name"], d, 16)
        # the DS reference with these data equals the Qwen reference (the identity the D3 decision rests on)
        dsr = S.reference(c["s_raw"], c["scale"], np.full(H, F(-2.0 ** 100), F), c["pv"], cos, sin)
        same = all(np.array_equal(np.asarray(dsr[k], F).view(np.uint32), np.asarray(ref[k], F).view(np.uint32))
                   for k in ("e", "es", "den", "o"))
        meta.append(dict(name=c["name"], layer=None, T=c["T"], source="hbm-forks Qwen sink-as-data", ds_ref_equals_qwen=same))
    for tag in ("", "m"):
        (w / f"lph16{tag}" / "cases.json").write_text(json.dumps(dict(cases=meta), indent=1) + "\n")
    print("prepared", [(m["name"], m["ds_ref_equals_qwen"]) for m in meta])
    return 0 if all(m["ds_ref_equals_qwen"] for m in meta) else 1


def run_dir(exe, d):
    r = subprocess.run([str(exe)], cwd=d, capture_output=True, text=True)
    g = re.search(r"SMX (.*)", r.stdout)
    if not g:
        return None
    return {k: int(v) for k, v in (x.split("=") for x in g.group(1).split())}


def cmd_run(a):
    w = Path(a.work)
    exe = w / "obj_lph16" / "Vtb_dsrom_su_softmax"
    meta = json.loads((w / "lph16" / "cases.json").read_text())["cases"]
    rows, neg = [], []
    for m in meta:
        kv = run_dir(exe, w / "lph16" / m["name"])
        ok = kv is not None and all(kv[k] == 0 for k in ("err_max", "err_es", "err_den", "err_e", "err_o")) and \
            kv["n_e"] == H * m["T"] and kv["n_o"] == H * ROW and kv["fault"] == 0
        nodes = None if kv is None else {"max": kv["t_mx"], "exp": kv["t_elast"] - kv["t_mx"],
                                         "den": kv["t_den"] - kv["t_elast"], "normalise": kv["t_olast"] - kv["t_pv0"],
                                         "row_total": kv["t_olast"]}
        rows.append(dict(m, exact=ok, smx=kv, cycles=nodes))
        km = run_dir(exe, w / "lph16m" / m["name"])
        caught = km is None or any(km[k] != 0 for k in ("err_den", "err_o"))
        neg.append(dict(name=m["name"], caught=caught))
        print(m["name"], "exact" if ok else "MISMATCH", nodes, "mutant caught" if caught else "MUTANT PASSED", flush=True)
    t640 = [r for r in rows if r["T"] == 640 and r["cycles"]]
    comp = None
    if t640:
        c = t640[0]["cycles"]
        # 8K multipass composition from the measured 640-row pass: pass 1 = running max over 13 chunks (overlapped with
        # the QK stream; exposed = one chunk's max tail), pass 2 = 13 chunks of exp + sum streamed back to back (the
        # carry-in add per chunk), pass 3 = one normalise.  Upper bound if nothing overlaps: 13 x (max + exp) + den +
        # normalise.
        comp = dict(chunks=13, measured_640=c,
                    exposed_estimate=c["max"] + c["den"] + c["normalise"] + 13 * 40,
                    no_overlap_bound=13 * (c["max"] + c["exp"]) + c["den"] + c["normalise"])
    verdict = "PASS" if rows and all(r["exact"] for r in rows) and all(n["caught"] for n in neg) else "FAIL"
    rec = dict(schema="opentallas.hbm_forks.sfx_qwen.v1", verdict=verdict, sink=-2.0 ** 100, cos=1, sin=0,
               rows=rows, mutant_sink0=neg, multipass_8k=comp)
    (w / "qwen_sink_data.json").write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print("SFX_QWEN", verdict, json.dumps(comp))
    return 0 if verdict == "PASS" else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("prep", "run"))
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    return dict(prep=cmd_prep, run=cmd_run)[a.step](a)


if __name__ == "__main__":
    raise SystemExit(main())
