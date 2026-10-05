#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash, S81) at the 1M token: the Engram path of layers 1 and 14 measured in full-shape RTL
on the DS-ROM die's stream unit, on operands rebuilt from the RELEASED checkpoint (owner measurement rule
2026-10-04; minimum component: one die's stream unit, one chain per Engram layer).

The w17 1M golden shard holds only the Engram input (h_in, the 4-copy residual) and its output (L{L}.engram).  The
hashed rows, key and value are rebuilt here from the released weights: the token history of the 1M golden
(golden_ctx1048576_0-39.json), hdc_golden_v41.EngramTables.hashes -> the 24 table rows (FP8 + UE8M0 per 32 columns)
-> linear_q(engram.wkv) -> key [4, 5120] / value [5120]; wgt = q_weight * k_weight.  The rebuilt Engram output must
equal BOTH hdc_golden_v41.Model.engram_layer and the shard's L{L}.engram bit for bit before any RTL runs.

The chain (the as-built ISA lowering of hdc_program_v41.Program.engram, at the released shape 4 x 5120):
  op0  h sum of squares per copy     (L{L}.eng.hh)
  op1  (h * wgt) * key, summed per copy                     (L{L}.eng.dot: h available -> dot result)
  op2  rsqrt(ss / 5120 + eps) of the 8 sums
  op3  rstd_h * rstd_k * dot * dim^-0.5
  op4  Engram gate SFU: sigmoid(signed sqrt)                (L{L}.eng.gate = op2..op4)
  op5  h + gate * value, BF16                               (L{L}.eng.add)
The key's sums of squares are E side (token-addressed, prefetched): VM operands of the h chain, and their own
chain E{L}.engram_key (E{L}.knorm.sumsq, off the h path).
on rtl/hdc/v41x/ot_hdc_v41x_vec.sv N1024 / M256 (MLAT 5 / ALAT 4, the 0.9 GHz serial domain), variants unit
(BCAST 0 / RET 0) and wired (BCAST 22 / RET 15: the plus-hub network stages as RTL register stages), exactly as
tools/dsrom_1m_su.py runs the other SU nodes.

    python3 tools/dsrom_1m_engram.py golden --out DIR        # local (checkpoint host): rebuild + bit-exact checks
    python3 tools/dsrom_1m_engram.py prep   --out DIR        # lower -> DIR/su_cases_engram.pkl
    python3 tools/dsrom_1m_engram.py run    --out DIR --variant unit|wired [--work W]     # compute host
    python3 tools/dsrom_1m_engram.py record --out DIR [--record results/rtl/dsrom_1m_allmeasured_20261004/engram.json]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

F = np.float32
CTX = 1048576
GOLD = Path(os.environ.get("OT_DSROM_1M_GOLD", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
LAYERS = (1, 14)
SLOW_HZ = 0.9e9
MLAT, ALAT = 5, 4
VARIANTS = {"unit": (0, 0), "wired": (6 + 16, 15)}
CASES = "su_cases_engram.pkl"
REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/engram.json"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def same(a, b):
    a, b = np.asarray(a, F), np.asarray(b, F)
    return bool(a.shape == b.shape and np.array_equal(a.view(np.uint32), b.view(np.uint32)))


def cmd_golden(a):
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    from hdc_golden_v41 import add, div, mul, rsqrt, reduce_sum_c, sqrt, sigmoid, neg, linear_q, to_bf16
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=True)
    hist = json.loads((GOLD / f"golden_ctx{CTX}_0-39.json").read_text())["history"]
    summary = {}
    for L in LAYERS:
        z = np.load(GOLD / f"ctx{CTX}_L{L:02d}.npz")
        h = z["h_in"].astype(F)
        li = m.engram.layer_ids.index(L)
        ids = m.engram.hashes(hist, li)
        codes, sc = m.emb_codes[L]
        rows = V.decode_engram_rows(codes, sc, ids).reshape(-1)
        kv = linear_q(m.lw(L, "engram.wkv.weight"), rows)
        key = kv[:m.hc * m.dim].reshape(m.hc, m.dim)
        value = kv[m.hc * m.dim:]
        wgt = mul(m.lw(L, "engram.q_weight"), m.lw(L, "engram.k_weight"))
        n = F(m.dim)
        hh, kk, dd, rh, rk, dot, gate, outs = [], [], [], [], [], [], [], []
        for j in range(m.hc):
            hj, kj = h[j], key[j]
            hh.append(reduce_sum_c(mul(hj, hj)))
            kk.append(reduce_sum_c(mul(kj, kj)))
            rh.append(rsqrt(add(div(hh[-1], n), m.eps)))
            rk.append(rsqrt(add(div(kk[-1], n), m.eps)))
            dd.append(reduce_sum_c(mul(mul(hj, wgt[j]), kj)))
            d_ = mul(mul(dd[-1], mul(rh[-1], rk[-1])), m.engram_scale)
            dot.append(d_)
            mag = sqrt(np.maximum(np.abs(d_), F(1e-6)).astype(F))
            g_ = sigmoid(np.where(d_ < 0, neg(mag), mag).astype(F))
            gate.append(g_)
            outs.append(add(hj, mul(g_, value)))
        y = to_bf16(np.stack(outs))
        ref = m.engram_layer(h.copy(), L, hist)
        checks = dict(rebuild_equals_model_engram_layer=same(y, ref), rebuild_equals_shard=same(y, z[f"L{L}.engram"]),
                      h_is_bf16=same(h, to_bf16(h)))
        snap = dict(layer=L, ids=np.asarray(ids, np.int64), h=h, key=np.asarray(key, F), value=np.asarray(value, F),
                    wgt=np.asarray(wgt, F), hh=np.asarray(hh, F), kk=np.asarray(kk, F), dd=np.asarray(dd, F),
                    rstd=np.asarray(rh + rk, F), dot=np.asarray(dot, F).reshape(-1), gate=np.asarray(gate, F).reshape(-1),
                    out=np.asarray(y, F), eps=F(m.eps), scale=F(m.engram_scale), dim=m.dim, hc=m.hc, checks=checks)
        (out / f"engram_L{L:02d}.pkl").write_bytes(pickle.dumps(snap))
        summary[f"L{L}"] = dict(checks=checks, rows=len(ids), row_ids_sha256=hashlib.sha256(np.asarray(ids, np.int64).tobytes()).hexdigest(),
                                kv_rows=int(kv.shape[0]), wkv_k=int(rows.shape[0]),
                                shard=f"ctx{CTX}_L{L:02d}.npz", shard_sha256=sha(GOLD / f"ctx{CTX}_L{L:02d}.npz"))
        print(L, checks, flush=True)
    res = dict(status="pass" if all(all(s["checks"].values()) for s in summary.values()) else "fail", layers=summary,
               history=hist, checkpoint=str(LC.HF), arith=os.environ["HDC_V41_ARITH"], generated_utc=now())
    (out / "engram_golden.json").write_text(json.dumps(res, indent=1) + "\n")
    print("GOLDEN", res["status"])
    return 0 if res["status"] == "pass" else 1


def f32u(x):
    return int(np.asarray(F(x)).view(np.uint32))


def chain_engram(c, I, s):
    """The ISA lowering of Program.engram at 4 x 5120 (see the module doc), h side only: the key sums of squares
    are token-addressed (E side, prefetched long before h arrives), so they are VM operands here and measured as
    their own chain (chain_engram_key)."""
    hc, d = s["hc"], s["dim"]
    H = c.vm(s["h"])
    K = c.vm(s["key"])
    VAL = c.vm(s["value"])
    W = c.crom(s["wgt"])
    SS = c.buf(8)
    c.init.append((SS + 4, np.asarray(s["kk"], F)))                                                          # E side
    c.op(nout=hc, nin=d, abase=H, aso=d, asi=1, red=I.RED_SUM, redsq=1, rbase=SS, rso=1, dst=0)            # 0 hh
    c.check("h sum of squares per copy", SS, s["hh"])
    ED = c.buf(8)
    c.op(nout=hc, nin=d, abase=H, aso=d, asi=1, bsrc=I.SRC_CLO, bbase=W, bso=d, bsi=1, m1=I.M1_AB,
         cbase=K, cso=d, csi=1, m2=I.M2_C, red=I.RED_SUM, rbase=ED, rso=1, dst=0)                            # 1 dot
    c.check("(h * wgt) . key per copy", ED, s["dd"])
    RS = c.buf(8)
    c.op(nout=1, nin=2 * hc, abase=SS, aso=2 * hc, asi=1, m1=I.M1_DIVIMM, imm1=f32u(d), ad=I.AD_IMM,
         imm2=f32u(s["eps"]), sfu=I.SFU_RSQRT, obase=RS, oso=2 * hc, osi=1)                                   # 2
    c.check("rstd h | rstd key", RS, s["rstd"])
    DOT = c.buf(8)
    c.op(nout=1, nin=hc, abase=RS, aso=hc, asi=1, bbase=RS + hc, bso=hc, bsi=1, m1=I.M1_AB, cbase=ED, cso=hc,
         csi=1, m2=I.M2_C, e1=I.E1_MULIMM, imm2=f32u(s["scale"]), obase=DOT, oso=hc, osi=1)                  # 3
    c.check("scaled dot", DOT, s["dot"])
    G = c.buf(8)
    c.op(nout=1, nin=hc, abase=DOT, aso=hc, asi=1, sfu=I.SFU_EGATE, obase=G, oso=hc, osi=1)                   # 4
    c.check("gate", G, s["gate"])
    O = c.buf(hc * d)
    c.op(nout=hc, nin=d, abase=VAL, aso=0, asi=1, bbase=G, bso=1, bsi=0, m1=I.M1_AB, cbase=H, cso=d, csi=1,
         ad=I.AD_C, rnd=1, obase=O, oso=d, osi=1)                                                             # 5
    c.check("h + gate * value (BF16): the Engram output", O, s["out"])
    L = s["layer"]
    return [(f"L{L}.eng.hh", 0, "result"), (f"L{L}.eng.dot", 1, "result"), (f"L{L}.eng.gate", 4, "write"),
            (f"L{L}.eng.add", 5, "write")]


def chain_engram_key(c, I, s):
    """E side: the key's sum of squares per copy (token-addressed, off the h path)."""
    hc, d = s["hc"], s["dim"]
    K = c.vm(s["key"])
    SS = c.buf(8)
    c.op(nout=hc, nin=d, abase=K, aso=d, asi=1, red=I.RED_SUM, redsq=1, rbase=SS, rso=1, dst=0)
    c.check("key sum of squares per copy", SS, s["kk"])
    return [(f"E{s['layer']}.knorm.sumsq", 0, "result")]


def cmd_prep(a):
    import dshbm_baseline_measure as B
    import hdc_golden as G
    import hdc_isa_v41 as I
    import rtl_hdc_v41x_vec_campaign as VC
    out = Path(a.out)
    cases, h = [], hashlib.sha256()
    for L in LAYERS:
        p = out / f"engram_L{L:02d}.pkl"
        h.update(p.read_bytes())
        s = pickle.loads(p.read_bytes())
        assert all(s["checks"].values()), s["checks"]
        for nm, fn in ((f"L{L}.engram", chain_engram), (f"E{L}.engram_key", chain_engram_key)):
            c = B.Chain(nm, VC)
            c.meta = dict(layer=f"L{L}", fn=fn.__name__)
            nodes = fn(c, I, s)
            c.meta["nodes"] = [dict(node=n, op=k, event=ev) for n, k, ev in nodes]
            cases.append(dict(name=c.name, meta=c.meta, init=c.init, cr_lo=c.cr_lo, cr_hi=c.cr_hi, ops=c.ops,
                              checks=[(lab, ad, G.bits(w).astype(np.uint32), "golden") for lab, ad, w, _k in c.checks]))
    (out / CASES).write_bytes(pickle.dumps(dict(cases=cases, snapshots_sha256=h.hexdigest())))
    print("cases", [c["name"] for c in cases])
    return 0


def cmd_check(a):
    import dshbm_baseline_measure as B
    return B.cmd_su_check(argparse.Namespace(out=a.out, cases=CASES))


def cmd_run(a):
    import dshbm_baseline_measure as B
    bc, rt = VARIANTS[a.variant]
    return B.cmd_su_run(argparse.Namespace(out=a.out, cases=CASES, bcast=bc, ret=rt, mlat=MLAT, alat=ALAT, n=a.n,
                                           m=a.m, fp=a.fp, work=a.work))


def _completion(po, ev):
    if ev == "result":
        return po["last_result"]
    return po["last_write"] if po["last_write"] is not None else po["last_result"]


def cmd_record(a):
    out = Path(a.out)
    gold = json.loads((out / "engram_golden.json").read_text())
    runs, nodes, chains = {}, {}, []
    for v, (bc, rt) in VARIANTS.items():
        f = out / f"su_N{a.n}_M{a.m}_b{bc}r{rt}m{MLAT}a{ALAT}_{a.fp}_{Path(CASES).stem}.json"
        r = json.loads(f.read_text())
        runs[v] = dict(file=f.name, status=r["status"], config=r["config"], cases_sha256=r["cases_sha256"],
                       source_sha256=r["source_sha256"])
        for ch in r["chains"]:
            L = ch["layer"]
            t = {nd["node"]: _completion(ch["per_op"][nd["op"]], nd["event"]) for nd in ch["nodes"]}
            if ch.get("fn") == "chain_engram_key":
                cyc = dict(t)
            else:
                hh, dot, gate, add = (f"{L}.eng.{k}" for k in ("hh", "dot", "gate", "add"))
                # chain start = h available (the key sums are VM operands); hh and dot are serial on the unit, so
                # eng.dot carries h -> dot result (pipeline fill included), eng.hh its own completion
                cyc = {hh: t[hh], dot: t[dot], gate: t[gate] - t[dot], add: t[add] - t[gate]}
            chains.append(dict(variant=v, chain=ch["chain"], exact=ch["exact"], checks=ch["checks"],
                               per_op=ch["per_op"], events=t, cycles_end=ch["cycles_end"]))
            for n, c in cyc.items():
                e = nodes.setdefault(n, dict(clock_hz=SLOW_HZ, exact=True))
                e[f"{v}_cycles"] = int(c)
                e[f"{v}_us"] = round(c / SLOW_HZ * 1e6, 5)
                e["exact"] = bool(e["exact"] and ch["exact"])
    for n, e in nodes.items():
        e["us"] = e["wired_us"]
        e["cycles"] = e["wired_cycles"]
        e["source"] = (f"ot_hdc_v41x_vec N{a.n}/M{a.m} MLAT5/ALAT4 at 0.9 GHz, wired BCAST 22 / RET 15 (unit "
                       f"{e['unit_us']} us); Engram chain on operands rebuilt from the released checkpoint, "
                       f"bit-exact vs golden + shard")
    exact = all(c["exact"] for c in chains) and gold["status"] == "pass"
    rec = dict(schema="opentallas.dsrom-1m.engram.v1", generated_utc=now(), source_commit=git_head(),
               context=CTX, position=CTX - 1, exact=exact,
               scope="Engram L1 / L14 at the 1M token, die 0's stream unit (one chain a layer), the ISA lowering of "
                     "Program.engram at the released shape 4 x 5120; node us = wired (BCAST 22 / RET 15) RTL cycles "
                     "at 0.9 GHz.  eng.dot is h available -> dot result (hh and dot are serial on the unit; pipeline fill included); "
                     "E{L}.knorm.sumsq is the key side (token-addressed, prefetchable, off the h path).",
               golden_check=gold, nodes=nodes, runs=runs, chains=chains,
               tool_sha256={"tools/dsrom_1m_engram.py": sha(ROOT / "tools/dsrom_1m_engram.py")})
    Path(a.record).write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print(json.dumps({n: (e["unit_us"], e["wired_us"], e["exact"]) for n, e in nodes.items()}, indent=0))
    return 0 if exact else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("golden", "prep", "check", "run", "record"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", choices=tuple(VARIANTS), default="wired")
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--m", type=int, default=256)
    ap.add_argument("--fp", choices=("rtl", "dpi", "dpi_beh"), default="dpi_beh")
    ap.add_argument("--work", default=None)
    ap.add_argument("--record", default=str(REC))
    a = ap.parse_args()
    return dict(golden=cmd_golden, prep=cmd_prep, check=cmd_check, run=cmd_run, record=cmd_record)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
