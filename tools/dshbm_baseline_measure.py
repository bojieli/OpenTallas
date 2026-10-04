#!/usr/bin/env python3
"""First MEASURED per-user rate of the DeepSeek-V4.1 HBM BASELINE (the GPU-organised ablation: static schedule,
hardware barrier, NVLS switch), from one die's share of each distinct layer type at full shape, 1M context, position
1,048,575 (minimum-component rule: one die is the vehicle at TP-96; collectives are composed from the measured W15
switch path).

    HDC_V41_ARITH=chunk8 python3 tools/dshbm_baseline_measure.py execute --out DIR   # golden-checked TP-96 run,
                                                                                    # rank-0 operands of L0/L2/head
    python3 tools/dshbm_baseline_measure.py sm --out DIR                            # SM element RTL, every matvec
    python3 tools/dshbm_baseline_measure.py su --out DIR                            # stream-unit RTL, local chains
    python3 tools/dshbm_baseline_measure.py compose --out DIR --record results/rtl/dshbm_baseline_measured_20261004/measured.json

Representative layers (the 2,262 tok/s model's per-layer table, results/uarch/w19_hbm_token_ar_fused_wsel256.json):
  L0    the regular MoE layer (sliding-window attention; 29 of 40 layers price identically in the model);
  L2    the index-source layer (compressor + indexer + top-512 selection + gathered compressed KV; 2 and 8 identical,
        24/28/32/36 differ only by skipping the compressor, 14 adds Engram, 20 adds layer-20 candidates);
  head  final hc_pre + norm, the LM head, local argmax and the argmax merge.

What is measured in RTL on the real full-shape operands (die 0 = rank 0, the busiest SM of 32, bit-exact):
  SM    every matvec of L0 / L2 / head on W13's ot_gpu_sm_v (tools/w19_sm_real_ops.py, the executor's operands);
  SU    the stream-unit local chains (ot_hdc_v41x_vec, N = 1,024 light lanes, M = 256 SFU lanes, the W11 element the
        model's local steps are priced on) at the TP-96 die's widths: hc_pre + RMSNorm, hc_post, q/kv RMSNorm,
        RoPE, sqrt(softplus) on the die's router rows, route weights, SwiGLU, the expert sum, the final norm, the
        local argmax.  Each chain runs on the real operands captured from the executor and its outputs are compared
        word for word with the executor's (golden-checked) values and with the unit reference.
Cited RTL measurements (not re-run here; source records named in the output): attention tile job cycles, index
score slice, router top-6, 96 x 512 select, W15 NVLS gather/all-reduce fits, the measured barrier, the routed
expert first access.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

F = np.float32
LAYERS = (0, 2)              # representative layer types; "head" = -1
HEAD = -1
SNAP_FNS = {"hc_pre_norm", "hc_post", "q_norm_kv_row", "q_rope", "router_act", "route", "swiglu", "moe_sum",
            "final_norm", "argmax_local", "index_q", "attend"}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


# ======================================================================================================================
# execute: the golden-checked TP-96 executor, all 40 layers + head, with rank 0's operands of the chosen layers
# ======================================================================================================================
EXT_FNS = {"index_scores", "topk_local", "cand_local", "cand_mask", "engram_fetch", "engram_mix"}


def cmd_execute_ext(a):
    """Default-off (--exec-layers L,L,...): each listed layer executed ALONE by the golden-checked TP-96 executor
    (entering from the W17 golden shard of the layer before it, as w19_hbm_tp96_isa.run does for a first layer > 0),
    snapshotting rank 0's operands of SNAP_FNS + EXT_FNS (the DU steps the model prices: index q / scores / local
    top-k / candidates / Engram), plus rank 0's own index keys for index_scores.  Writes local_snaps_ext.pkl and
    execute_ext.json; the default execute path is unchanged."""
    import w19_hbm_tp96_isa as X
    if os.environ.get("OT_ENGRAM_TOKEN_MAP"):       # default-off: a host without `tokenizers` loads the precomputed
        import hdc_golden_v41 as Vg                  # compressed token map (hdc_golden_v41.compressed_token_map output)
        z = np.load(os.environ["OT_ENGRAM_TOKEN_MAP"])
        Vg.compressed_token_map = lambda path, size: (z["token_map"], int(z["cv"]))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    layers = [int(x) for x in a.exec_layers.split(",")]
    fns = SNAP_FNS | EXT_FNS
    snaps, results = {}, []
    orig_run = X.Executor.run

    def run(self, ops):
        for op in ops:
            take = op["kind"] == "local" and op["fn"] in fns
            if take:
                r0 = self.ranks[0]
                before = {k: v.copy() for k, v in r0.mem.items()}
            orig_run(self, [op])
            if take:
                after = {k: v.copy() for k, v in r0.mem.items() if k not in before or
                         before[k].shape != v.shape or not np.array_equal(before[k], v, equal_nan=True)}
                L = op["layer"]
                key = f"L{L}.op{op['id']}.{op['fn']}" + (f".{op['which']}" if "which" in op else "") + \
                      (f".s{op['slot']}" if "slot" in op else "")
                extra = {}
                if op["fn"] == "index_scores":
                    idx = self.owned(r0, op["n"])
                    extra = dict(keys=np.asarray(self.st.ik[op["src"]][idx], dtype=F).copy(), key_idx=idx.copy())
                if op["fn"] in ("cand_mask",) and r0.cand is not None:
                    extra = dict(cand_keep={int(b): bool(v) for b, v in r0.cand.items()})
                if op["fn"] == "engram_fetch":
                    m = self.m
                    li = m.engram.layer_ids.index(L)
                    extra = dict(ids=np.asarray(m.engram.hashes(self.hist, li)).reshape(-1).copy())
                if op["fn"] == "engram_mix":                 # the step's constants (no checkpoint needed to lower it)
                    import hdc_golden as Gd
                    m = self.m
                    extra = dict(wgt=np.asarray(Gd.mul(m.lw(L, "engram.q_weight"), m.lw(L, "engram.k_weight")), F),
                                 engram_scale=F(m.engram_scale), eps=F(m.eps), hc=int(m.hc), dim=int(m.dim))
                if op["fn"] == "index_q":
                    import hdc_golden_v41 as Vg
                    m = self.m
                    extra = dict(cs=Vg.rope_cs(m.freqs_yarn, self.pos), index_w_scale=F(m.index_w_scale),
                                 ih=int(m.ih), ihd=int(m.ihd))
                snaps[key] = dict(op=op, before=before, after=after, **extra)
    X.Executor.run = run
    try:
        for L in layers:
            t0 = time.time()
            res = X.run([L], False, "oreduce")
            lr = res["layers"][0]
            results.append(dict(layer=L, kind=lr["kind"], verdict=lr["verdict"], defect=lr["defect"],
                                regions=len(lr["regions"]), bit_exact_regions=sum(1 for x in lr["regions"]
                                                                                  if x["bit_exact"]),
                                region_names=[x["region"] for x in lr["regions"]], wall_s=round(time.time() - t0, 1)))
            print("EXEC_EXT", results[-1], flush=True)
            (out / "local_snaps_ext.pkl").write_bytes(pickle.dumps(snaps))
    finally:
        X.Executor.run = orig_run
    summ = dict(status="pass" if results and all(r["verdict"] == "pass" for r in results) else "fail",
                layers=results, snapshots=sorted(snaps), source_sha256={s: sha(ROOT / s) for s in X.SOURCES})
    (out / "execute_ext.json").write_text(json.dumps(summ, indent=1, default=int) + "\n")
    return 0 if summ["status"] == "pass" else 1


def cmd_execute(a):
    if getattr(a, "exec_layers", None):
        return cmd_execute_ext(a)
    import w19_hbm_tp96_isa as X
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    X.DUMP["path"], X.DUMP["layers"] = out / "sm_dump.pkl", set(LAYERS) | {HEAD}
    snaps = {}
    orig_run = X.Executor.run

    def run(self, ops):
        for op in ops:
            L = op.get("layer")
            take = op["kind"] == "local" and op["fn"] in SNAP_FNS and L in (set(LAYERS) | {HEAD})
            if take:
                r0 = self.ranks[0]
                before = {k: v.copy() for k, v in r0.mem.items()}
            orig_run(self, [op])
            if take:
                after = {k: v.copy() for k, v in r0.mem.items() if k not in before or
                         before[k].shape != v.shape or not np.array_equal(before[k], v, equal_nan=True)}
                key = f"L{L}.op{op['id']}.{op['fn']}" + (f".{op['which']}" if "which" in op else "") + \
                      (f".s{op['slot']}" if "slot" in op else "")
                extra = {}
                if op["fn"] == "attend":                      # the rows the die's head attends over (rank 0)
                    rows = r0.win[L]
                    if op["yarn"]:
                        rows = np.concatenate([rows, r0.sel_rows[self.m.kv_of[L]]])
                    extra = dict(rows=np.asarray(rows, dtype=F).copy(),
                                 sink=np.asarray(self.m.lw(L, "attn.attn_sink")[0:1], dtype=F).copy(),
                                 cs=self.cs(L), attn_scale=F(self.m.attn_scale))
                snaps[key] = dict(op=op, before={k: v for k, v in before.items()}, after=after,
                                  route_ids=list(getattr(self, "route_ids", []) or []), **extra)
    X.Executor.run = run
    t0 = time.time()
    res = X.run(list(range(40)), True, "oreduce", program_out=out / "program.json")
    res["wall_s"] = round(time.time() - t0, 1)
    X.Executor.run = orig_run
    # trim the snapshots to the buffers the stream-unit chains read (h, pre, mixes, slices); keep everything small
    (out / "local_snaps.pkl").write_bytes(pickle.dumps(snaps))
    passed = all(r["verdict"] == "pass" for r in res["layers"]) and len(res["layers"]) == 40 and \
        res["head"] is not None and res["head"]["verdict"] == "pass"
    summ = dict(status="pass" if passed else "fail", wall_s=res["wall_s"], position=res["position"],
                context=res["context"], variant=res["variant"], state_check=res["state_check"],
                head=res["head"], layers=[dict(layer=r["layer"], kind=r["kind"], verdict=r["verdict"],
                                                regions=len(r["regions"]),
                                                bit_exact_regions=sum(1 for x in r["regions"] if x["bit_exact"]),
                                                collectives=r["collectives"], ops=r["ops"]) for r in res["layers"]],
                source_sha256={s: sha(ROOT / s) for s in X.SOURCES})
    (out / "execute.json").write_text(json.dumps(summ, indent=1, default=int) + "\n")
    print("EXECUTE", summ["status"], "head", res["head"])
    return 0 if passed else 1


# ======================================================================================================================
# sm: the SM element on every matvec of the representative layers (W13 ot_gpu_sm_v, w19_sm_real_ops.py)
# ======================================================================================================================
def cmd_sm(a):
    """tools/w19_sm_real_ops.py on the dump, in process: its pinned source list predates the LAT-parameterised FP32
    add (799afc7bc), whose prefix adders (ot_hdc_ksadd_k) live in rtl/hdc/ot_hdc_prefix.sv, so that file is added
    to the compile list here (no pinned file edited)."""
    if a.sm_accelerator:
        # Same retained executor operands and W19 codecs; explicit candidate
        # selection never replaces the baseline record consumed by compose.
        import hbm_accel_sm_v_gate as gate
        out = Path(a.out).resolve()
        record = out / "sm_accel_real_ops.json"
        if record.exists():
            raise FileExistsError("Preserve the prior SM candidate verdict: " + str(record))
        return gate.main(["real", "--dump", str(out / "sm_dump.pkl"),
                          "--out", str(record),
                          "--workdir", str(Path(a.work).resolve() if a.work else out / "sm_accel_work"),
                          "--jobs", str(a.jobs), "--simulator", a.sm_simulator,
                          "--verilator", a.sm_verilator, "--build-jobs", str(a.sm_build_jobs)])
    import rtl_gpu_sm_exact as S
    import w19_sm_real_ops as SM
    if "rtl/hdc/ot_hdc_prefix.sv" not in S.SMV_SRC:
        S.SMV_SRC.insert(0, "rtl/hdc/ot_hdc_prefix.sv")
    out = Path(a.out)
    sys.argv = ["w19_sm_real_ops.py", "--dump", str(out / "sm_dump.pkl"), "--record", str(out / "sm_real_ops.json"),
                "--workdir", str(Path(a.work) if a.work else out / "sm_work"), "--jobs", str(a.jobs)]
    return SM.main()


# ======================================================================================================================
# su: the stream-unit local chains in RTL (ot_hdc_v41x_vec, N 1,024 / M 256), on the captured real operands
# ======================================================================================================================
SU_N, SU_M = 1024, 256
D, HC = 5120, 4


class Chain:
    """One local step lowered to stream-unit ops over a vector memory laid out by an allocator."""

    def __init__(self, name, VC):
        self.name, self.VC = name, VC
        self.al = VC.Alloc(64, (1 << VC.VMA) - 64)
        self.cr_lo = np.zeros(1 << VC.CRA, dtype=np.uint32)
        self.cr_hi = np.zeros(1 << VC.CRA, dtype=np.uint32)
        self.crp = 0
        self.init = []           # (address, float32 values)
        self.ops = []
        self.checks = []         # (label, address, expected float32 array, kind)
        self.memo = {}           # read-only operands shared by the positions of a multi-position chain

    def vm(self, vals, align=8):
        vals = np.asarray(vals, dtype=F).reshape(-1)
        key = ("vm", len(vals), hashlib.sha256(vals.tobytes()).hexdigest())     # read-only inputs only
        if key in self.memo:
            return self.memo[key][0]
        src = vals
        a = self.al.get(len(vals), align)
        self.init.append((a, vals))
        self.memo[key] = (a, src)
        return a

    def vm_u32(self, vals, align=8):
        vals = np.asarray(vals, dtype=np.uint32).reshape(-1)
        a = self.al.get(len(vals), align)
        self.init.append((a, vals.view(F)))
        return a

    def buf(self, n, align=8):
        return self.al.get(n, align)

    def crom(self, lo, hi=None):
        lo = np.asarray(lo, dtype=F).reshape(-1)
        key = ("cr", hashlib.sha256(lo.tobytes()).hexdigest(),
               None if hi is None else hashlib.sha256(np.asarray(hi, dtype=F).tobytes()).hexdigest())
        if key in self.memo:
            return self.memo[key][0]
        src = (lo, hi)
        a = self.crp
        self.memo[key] = (a, src)
        self.cr_lo[a:a + len(lo)] = lo.view(np.uint32)
        if hi is not None:
            self.cr_hi[a:a + len(lo)] = np.asarray(hi, dtype=F).reshape(-1).view(np.uint32)
        self.crp += -(-len(lo) // 8) * 8
        return a

    def op(self, **kw):
        f = self.VC.op_defaults()
        f.update(dst=1)
        f.update(kw)
        self.ops.append(f)

    def check(self, label, addr, want, kind="executor"):
        self.checks.append((label, addr, np.asarray(want, dtype=F).reshape(-1), kind))

    def mem0(self):
        VC = self.VC
        vm = np.zeros(1 << VC.VMA, dtype=np.uint32)
        for a, v in self.init:
            vm[a:a + len(v)] = v.view(np.uint32)
        kv = np.zeros(1 << VC.KVA, dtype=np.uint32)
        cr = np.stack([self.cr_lo, self.cr_hi], axis=1)
        wr = np.zeros(1 << VC.WRA, dtype=np.uint16)
        return VC.Mem(vm, kv, cr, wr)


def f32u(x):
    return int(np.asarray(F(x)).view(np.uint32))


def lower_rmsnorm(c, I, xa, n, w, eps, ss=None):
    """RMSNorm of the n values at xa (BF16 values), gain w (CROM): out = bf16(w * (x * rsqrt(csum(x^2)/n + eps))).
    ss: the sum of squares is already at ss (the producer's chained reduction)."""
    if ss is None:
        ss = c.buf(8)
        seg = 8 if n % 64 == 0 else 1
        c.op(nout=seg, nin=n // seg, abase=xa, aso=n // seg, asi=1, red=I.RED_SUM, redsq=1, redtree=1 if seg > 1 else 0,
             redwhole=0 if seg > 1 else 1, rbase=ss, dst=0)
    rs = c.buf(8)
    c.op(nout=1, nin=1, abase=ss, m1=I.M1_DIVIMM, imm1=f32u(n), ad=I.AD_IMM, imm2=f32u(eps), sfu=I.SFU_RSQRT,
         obase=rs)
    wb = c.crom(w)
    y = c.buf(n)
    c.op(nout=1, nin=n, abase=xa, aso=n, asi=1, bbase=rs, m1=I.M1_AB, csrc=I.SRC_CLO, cbase=wb, cso=n, csi=1,
         e1=I.E1_MULC, rnd=1, obase=y, oso=n, osi=1)
    return y


def lower_hc_pre_norm(c, I, h, pre, w, eps):
    H = c.vm(h)
    P = c.vm(pre)
    T = c.buf(D)
    X = c.buf(D)
    SS = c.buf(8)
    c.op(nout=1, nin=D, abase=H, aso=D, asi=1, bbase=P, m1=I.M1_AB, cbase=H + D, cso=D, csi=1, dbase=P + 1,
         qm=I.QM_POS, ad=I.AD_Q, obase=T, oso=D, osi=1)
    c.op(nout=1, nin=D, abase=H + 2 * D, aso=D, asi=1, bbase=P + 2, m1=I.M1_AB, cbase=T, cso=D, csi=1, ad=I.AD_C,
         obase=T, oso=D, osi=1)
    seg = 8
    c.op(nout=seg, nin=D // seg, abase=H + 3 * D, aso=D // seg, asi=1, bbase=P + 3, m1=I.M1_AB, cbase=T,
         cso=D // seg, csi=1, ad=I.AD_C, rnd=1, obase=X, oso=D // seg, osi=1, red=I.RED_SUM, redsq=1, redtree=1,
         rbase=SS)
    return lower_rmsnorm(c, I, X, D, w, eps, ss=SS)


def lower_hc_post(c, I, y, res, post, comb):
    H = c.vm(res)
    Y = c.vm(y)
    CB = c.vm(comb)
    PO = c.vm(post)
    T = c.buf(HC * D)
    O = T                    # the last op accumulates in place (as the first three do), so 6 positions fit in VM
    SSX = c.buf(8)
    c.op(nout=HC, nin=D, abase=H, aso=0, asi=1, bbase=CB, bso=1, m1=I.M1_AB, cbase=H + D, cso=0, csi=1,
         dbase=CB + 4, dso=1, qm=I.QM_POS, ad=I.AD_Q, obase=T, oso=D, osi=1)
    for j in (2, 3):
        c.op(nout=HC, nin=D, abase=H + j * D, aso=0, asi=1, bbase=CB + 4 * j, bso=1, m1=I.M1_AB, cbase=T, cso=D,
             csi=1, ad=I.AD_C, obase=T, oso=D, osi=1)
    c.op(nout=HC, nin=D, abase=Y, aso=0, asi=1, bbase=PO, bso=1, m1=I.M1_AB, cbase=T, cso=D, csi=1, ad=I.AD_C,
         rnd=1, obase=O, oso=D, osi=1, red=I.RED_SUM, redsq=1, redtree=1, rbase=SSX)
    return O


def lower_rope(c, I, xa, n, cs):
    """In-place adjacent-pair RoPE of the last 2*len(cos) elements of the n values at xa (BF16 out)."""
    cos, sin = cs
    rd = 2 * len(cos)
    tb = c.crom(cos, sin)
    t0 = xa + n - rd
    assert t0 % 2 == 0
    out = c.buf(n)
    # copy the untouched head, then rotate the tail into the output
    if n > rd:
        c.op(nout=1, nin=n - rd, abase=xa, aso=n - rd, asi=1, obase=out, oso=n - rd, osi=1)
    c.op(nout=1, nin=rd, abase=t0, aso=rd, asi=1, cpair=1, bsrc=I.SRC_CLO, bbase=tb, bso=rd // 2, bsi=1, bhalf=1,
         dsrc=I.SRC_CHI, dbase=tb, dso=rd // 2, dsi=1, m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q, rnd=1,
         obase=out + n - rd, oso=rd, osi=1)
    return out


def build_chains(snaps, m, pos, VC, I, V, G, reps=1, op_major=False):
    """Every lowered local step of the representative layers, from the captured rank-0 operands."""
    chains = []
    lw = m.lw
    for key, s in snaps.items():
        op, b, a = s["op"], s["before"], s["after"]
        fn, L = op["fn"], op["layer"]
        lname = "head" if L == HEAD else f"L{L}"
        c = Chain(f"{lname}.{fn}" + (f".{op['which']}" if "which" in op else "") +
                  (f".s{op['slot']}" if "slot" in op else ""), VC)
        c.meta = dict(layer=lname, fn=fn, op_id=op["id"], tag=op["tag"], reps=reps, op_major=bool(op_major))
        ok = True
        for rep in range(reps):          # reps > 1: the same step for `reps` positions, back to back (own buffers)
            if fn in ("hc_pre_norm", "final_norm"):
                if fn == "final_norm":
                    pre, w = b["pre"], m.w["norm.weight"]
                elif op["which"] == "attn":
                    pre, w = b["pre"], lw(L, "attn_norm.weight")
                else:
                    pre, w = b["attn_pre"], lw(L, "ffn_norm.weight")
                y = lower_hc_pre_norm(c, I, b["h"], pre, np.asarray(w, dtype=F), m.eps)
                c.check("x", y, a["x"])
            elif fn == "hc_post":
                w = op["which"]
                yv = b["y" if w == "attn" else "yf"]
                o = lower_hc_post(c, I, yv, b[f"{w}_res"], b[f"{w}_post"], b[f"{w}_comb"])
                c.check("h", o, a["h"])
            elif fn == "q_norm_kv_row":
                qr = lower_rmsnorm(c, I, c.vm(b["qa"]), len(b["qa"]), np.asarray(lw(L, "attn.q_norm.weight"), F), m.eps)
                c.check("qr", qr, a["qr"])
                kvn = lower_rmsnorm(c, I, c.vm(b["kvraw"]), len(b["kvraw"]), np.asarray(lw(L, "attn.kv_norm.weight"), F),
                                    m.eps)
                cs = V.rope_cs(m.freqs_yarn if m.ratio[L] > 0 else m.freqs_plain, pos)
                kvr = lower_rope(c, I, kvn, len(b["kvraw"]), cs)
                kv_ref = V.rope_tail(V.rmsnorm_bf16(b["kvraw"], lw(L, "attn.kv_norm.weight"), m.eps), cs)
                c.check("kv_rope (golden function; FP8 QDQ of the window row is the QE unit, not lowered)", kvr, kv_ref,
                        "golden_fn")
                c.check("win_new after QDQ = qdq_fp8(kv_rope) (consistency of the reference)", kvr, kv_ref, "golden_fn")
                c.checks.pop()
                c.meta["also_bitexact_window_row"] = bool(np.array_equal(G.bits(V.qdq_fp8(kv_ref)), G.bits(a["win_new"])))
            elif fn == "q_rope":
                h = 0
                q = b["q"][h * 512:(h + 1) * 512]
                cs = V.rope_cs(m.freqs_yarn if m.ratio[L] > 0 else m.freqs_plain, pos)
                o = lower_rope(c, I, c.vm(q), 512, cs)
                c.check("q_own", o, a["q_own"])
            elif fn == "router_act":
                g = b["gsc"][0:4]
                ga = c.vm(g)
                o = c.buf(8)
                c.op(nout=1, nin=4, abase=ga, aso=4, asi=1, sfu=I.SFU_SPSQRT, obase=o, oso=4, osi=1)
                c.check("gsc[0:4]", o, a["gsc"][0:4])
            elif fn == "route":
                sc = b["gsc"]
                S_ = c.vm(sc)
                bias = c.crom(np.asarray(lw(L, "ffn.gate.bias"), F))
                BI = c.buf(384)
                c.op(nout=1, nin=384, abase=S_, aso=384, asi=1, csrc=I.SRC_CLO, cbase=bias, cso=384, csi=1, ad=I.AD_C,
                     obase=BI, oso=384, osi=1)
                c.check("router (scores + bias)", BI, a["router"])
                ids = np.asarray(a["route_ids"], dtype=np.uint32)          # top-6 itself: the router top-k RTL (cited)
                IX = c.vm_u32(ids)
                TOT = c.buf(8)
                c.op(nout=1, nin=6, abase=S_, asi=1, aso=6, aind=I.IND_I, aibase=IX, red=I.RED_SUM, redwhole=1,
                     rbase=TOT, dst=0)
                DEN = c.buf(8)
                c.op(nout=1, nin=1, abase=TOT, ad=I.AD_IMM, imm2=f32u(1e-20), obase=DEN)
                W = c.buf(8)
                c.op(nout=1, nin=6, abase=S_, asi=1, aso=6, aind=I.IND_I, aibase=IX, bbase=DEN, m1=I.M1_DIVB,
                     e1=I.E1_MULIMM, imm2=f32u(m.route_scale), obase=W, oso=6, osi=1)
                c.check("route_w", W, a["route_w"])
            elif fn == "swiglu":
                e = op["slot"]
                r0, r1 = 0, 24
                g = b[f"e{e}.g"][r0:r1]
                u = b[f"e{e}.u"][r0:r1]
                ga, ua = c.vm(g), c.vm(u)
                o = c.buf(24)
                lim = f32u(m.limit)
                kw = dict(nout=1, nin=24, abase=ga, aso=24, asi=1, amin=1, imm3=lim, sfu=I.SFU_SILU, cbase=ua, cso=24,
                          csi=1, cclip=1, e1=I.E1_MULC, rnd=1, obase=o, oso=24, osi=1)
                if e < m.k_exp:
                    rw = c.vm(b["route_w"][e:e + 1])
                    kw.update(bbase=rw, e2=I.E2_MULB)
                c.op(**kw)
                c.check(f"ea slot {e}", o, a["ea"][e * 2304 + r0:e * 2304 + r1])
            elif fn == "moe_sum":
                r1 = 54
                parts = np.stack([b[f"e{e}.d"][0:r1] for e in range(m.k_exp + 1)], axis=1)   # [54][7]
                Pa = c.vm(parts)
                o = c.buf(64)
                c.op(nout=r1, nin=m.k_exp + 1, abase=Pa, aso=m.k_exp + 1, asi=1, red=I.RED_SUM, redrnd=1, rbase=o, rso=1,
                     dst=0)
                c.check("yf rows 0:54", o, a["yf"][0:r1])
            elif fn == "attend":
                # scores and P.V are the attention tile's work (cited RTL record); the softmax, the denominator with
                # the sink, the normalisation and the inverse RoPE are the stream unit's, lowered here
                q = b["q_own"].reshape(1, 512)
                rows = s["rows"]
                T = len(rows)
                sc = G.mul(V.dots(q, rows), s["attn_scale"]).reshape(-1)
                mb = np.max(sc)
                ev = G.exp(G.add(sc, G.neg(mb)))
                pv = V.dots(G.to_bf16(ev.reshape(1, -1)), rows.T).reshape(-1)
                S_ = c.vm(sc)
                MB = c.buf(8)
                c.op(nout=1, nin=T, abase=S_, aso=T, asi=1, red=I.RED_MAX, redwhole=1, rbase=MB, dst=0)
                E = c.buf(T)
                SE = c.buf(8)
                c.op(nout=1, nin=T, abase=S_, aso=T, asi=1, bbase=MB, ad=I.AD_NEGB, sfu=I.SFU_EXP, obase=E, oso=T,
                     osi=1, red=I.RED_SUM, redwhole=1, rbase=SE)
                c.check("exp(s - max) (P before BF16, the tile's PV input)", E, ev, "golden_fn")
                SK = c.vm(s["sink"])
                ES = c.buf(8)
                c.op(nout=1, nin=1, abase=SK, bbase=MB, ad=I.AD_NEGB, sfu=I.SFU_EXP, obase=ES)
                DEN = c.buf(8)
                c.op(nout=1, nin=1, abase=SE, cbase=ES, ad=I.AD_C, obase=DEN)
                PV = c.vm(pv)
                O = c.buf(512)
                c.op(nout=1, nin=512, abase=PV, aso=512, asi=1, bbase=DEN, m1=I.M1_DIVB, rnd=1, obase=O, oso=512, osi=1)
                cos, sin = s["cs"]
                rd = 2 * len(cos)
                tb = c.crom(cos, sin)
                c.op(nout=1, nin=rd, abase=O + 512 - rd, aso=rd, asi=1, cpair=1, bsrc=I.SRC_CLO, bbase=tb, bso=rd // 2,
                     bsi=1, bhalf=1, dsrc=I.SRC_CHI, dbase=tb, dso=rd // 2, dsi=1, m1=I.M1_AB, qm=I.QM_ALT_PN, ad=I.AD_Q,
                     rnd=1, obase=O + 512 - rd, oso=rd, osi=1)
                c.check("o_own", O, a["o_own"])
                c.meta["T"] = int(T)
            elif fn == "argmax_local":
                lg = b["logits"][0:1347]
                la = c.vm(lg)
                o = c.buf(8)
                c.op(nout=1, nin=1347, abase=la, aso=1347, asi=1, red=I.RED_MAX, redwhole=1, rbase=o, dst=0)
                c.check("argmax value", o, a["argmax_v"])
            else:
                ok = False
                break
        if not ok:
            continue
        if reps > 1 and op_major:        # issue op j of every position before op j + 1 (a position's ops keep order)
            k = len(c.ops) // reps
            assert k * reps == len(c.ops)
            c.ops = [c.ops[r * k + j] for j in range(k) for r in range(reps)]
        chains.append(c)
    return chains


def cmd_su_prep(a):
    """Lower every captured local step to stream-unit cases (needs the checkpoint for gains / tables); no RTL."""
    import hdc_golden as G
    import hdc_golden_v41 as V
    import hdc_isa_v41 as I
    import rtl_hdc_v41x_vec_campaign as VC
    import rtl_v41_fullshape_layer_campaign as LC
    out = Path(a.out)
    snaps = pickle.loads((out / "local_snaps.pkl").read_bytes())
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    chains = build_chains(snaps, m, 1048575, VC, I, V, G, reps=a.reps, op_major=a.op_major)
    cases = [dict(name=c.name, meta=c.meta, init=c.init, cr_lo=c.cr_lo, cr_hi=c.cr_hi, ops=c.ops,
                  checks=[(lab, ad, G.bits(w).astype(np.uint32), kind) for lab, ad, w, kind in c.checks])
             for c in chains]
    (out / a.cases).write_bytes(pickle.dumps(dict(cases=cases, snapshots_sha256=sha(out / "local_snaps.pkl"))))
    print("SU cases", len(cases), [c["name"] for c in cases])
    return 0


def cmd_su_check(a):
    """The prepared cases through the unit's bit-level reference only (no RTL): the lowering is right iff every
    executor check matches here; the RTL run then checks the unit against this reference."""
    import rtl_hdc_v41x_vec_campaign as VC
    out = Path(a.out)
    blob = pickle.loads((out / a.cases).read_bytes())
    bad = 0
    for cs in blob["cases"]:
        vm = np.zeros(1 << VC.VMA, dtype=np.uint32)
        for ad, v in cs["init"]:
            vm[ad:ad + len(v)] = np.asarray(v, dtype=F).view(np.uint32)
        mem0 = VC.Mem(vm, np.zeros(1 << VC.KVA, dtype=np.uint32), np.stack([cs["cr_lo"], cs["cr_hi"]], axis=1),
                      np.zeros(1 << VC.WRA, dtype=np.uint16))
        mref, sops, lays, ok = VC.schedule(cs["ops"], mem0, SU_N, SU_M)
        res = []
        for label, addr, want, kind in cs["checks"]:
            got = mref.vm[addr:addr + len(want)]
            n = int(np.sum(got != want))
            res.append((label[:30], n))
            bad += n > 0
        print(f"{cs['name']:28s} ref_ok {ok} bad_layout {[i for i, l in enumerate(lays) if l['bad']]} "
              f"vectors {sum(l['nv'] for l in lays)} mismatches {res}")
    print("SU-CHECK", "PASS" if bad == 0 else "FAIL")
    return 0 if bad == 0 else 1


def cmd_su_run(a):
    """Build the stream-unit bench and run every prepared case (no checkpoint needed: runs on the compute host)."""
    import rtl_hdc_v41x_vec_campaign as VC
    out = Path(a.out)
    blob = pickle.loads((out / a.cases).read_bytes())
    VC.BCAST, VC.RET = a.bcast, a.ret
    VC.set_mlat(a.mlat, a.alat)
    N, M = a.n, a.m
    if a.fp in ("dpi", "dpi_beh"):
        VC.LIB = fp_dpi_lib(VC.LIB, beh_prefix=a.fp == "dpi_beh")
    btag = f"N{N}_M{M}_b{a.bcast}r{a.ret}m{a.mlat}a{a.alat}_{a.fp}"
    tag = btag + ("" if a.cases == "su_cases.pkl" else "_" + Path(a.cases).stem)
    obj = Path(a.work or (out / "su_work")) / f"obj_{btag}"      # OT_REUSE_BUILD=1 reuses it across case sets
    t0 = time.time()
    exe, bs = VC.build(N, M, obj)
    print(f"built {tag} in {time.time() - t0:.0f} s", flush=True)
    rows = []
    for cs in blob["cases"]:
        vm = np.zeros(1 << VC.VMA, dtype=np.uint32)
        for ad, v in cs["init"]:
            vm[ad:ad + len(v)] = np.asarray(v, dtype=F).view(np.uint32)
        mem0 = VC.Mem(vm, np.zeros(1 << VC.KVA, dtype=np.uint32), np.stack([cs["cr_lo"], cs["cr_hi"]], axis=1),
                      np.zeros(1 << VC.WRA, dtype=np.uint16))
        d = Path(a.work or (out / "su_work")) / tag / cs["name"]
        bad = [i for i, l in enumerate(VC.schedule(cs["ops"], mem0, N, M)[2]) if l["bad"]]
        if bad:                  # the lowering targets N 1,024: a segmented op may not lay out on a narrower unit
            rows.append(dict(chain=cs["name"], **cs["meta"], skipped=f"ops {bad} do not lay out at N {N} / M {M}",
                             exact=None))
            print(f"{cs['name']:28s} SKIPPED (layout at N {N}: ops {bad})", flush=True)
            continue
        cc, tr, sops, lays = VC.run_program(exe, d, mem0, cs["ops"], N, M)
        per = []
        for k, (f, lay) in enumerate(zip(sops, lays)):
            em, rt, rs = VC.op_trace(tr, k)
            per.append(dict(first_emit=em[0] if em else None, last_emit=em[-1] if em else None,
                            last_write=rt[-1] if rt else None, last_result=rs[-1] if rs else None, vectors=len(em),
                            nout=f["nout"], nin=f["nin"], depth_model=lay["dP"]))
        firsts = [p["first_emit"] for p in per if p["first_emit"] is not None]
        lasts = [x for p in per for x in (p["last_write"], p["last_result"]) if x is not None]
        ex_checks = []
        got_vm = tr["vm"]
        for label, addr, want, kind in cs["checks"]:
            got = got_vm[addr:addr + len(want)] if got_vm is not None else None
            ok = got is not None and np.array_equal(got, want)
            ex_checks.append(dict(label=label, kind=kind, n=int(len(want)), bit_exact=bool(ok),
                                  mismatches=None if got is None else int(np.sum(got != want))))
        row = dict(chain=cs["name"], **cs["meta"], ops=len(sops), unit_reference=cc, checks=ex_checks,
                   vm_out_sha256=None if got_vm is None else hashlib.sha256(np.asarray(got_vm, np.uint32).tobytes()).hexdigest(),
                   cycles_end=cc["cycles"],
                   first_emit_to_last_write=(max(lasts) - min(firsts) + 1) if firsts and lasts else None,
                   per_op=per, exact=bool(cc["pass_"] and all(x["bit_exact"] for x in ex_checks)))
        rows.append(row)
        print(f"{cs['name']:28s} ops {len(sops):2d} end {cc['cycles']} span {row['first_emit_to_last_write']} "
              f"unit {'PASS' if cc['pass_'] else 'FAIL'} executor {[x['bit_exact'] for x in ex_checks]}", flush=True)
    rec = dict(schema="opentallas.rtl.dshbm_baseline_su_chains.v1", generated_utc=now(), source_commit=git_head(),
               config=dict(N=N, M=M, BCAST=a.bcast, RET=a.ret, MLAT=a.mlat, ALAT=a.alat, build_s=round(bs, 1), fp=a.fp,
                           fp_note=FP_NOTE[a.fp]),
               status="pass" if rows and all(r["exact"] for r in rows if r["exact"] is not None) else "fail",
               skipped=[r["chain"] for r in rows if r["exact"] is None], chains=rows,
               source_sha256={p: sha(ROOT / p) for p in [
                   "tools/dshbm_baseline_measure.py", "tools/rtl_hdc_v41x_vec_campaign.py",
                   *[str(x.relative_to(ROOT)) for x in VC.RTL + VC.LIB], str(VC.TB.relative_to(ROOT))]},
               cases_sha256=sha(out / a.cases), cases=a.cases, snapshots_sha256=blob["snapshots_sha256"])
    (out / f"su_{tag}.json").write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print("SU", rec["status"])
    return 0 if rec["status"] == "pass" else 1


FP_NOTE = dict(rtl="every FP unit is the bit-level RTL", dpi=(
    "FP add / multiply units are the simulation-only DPI stand-ins (rtl/test/sim_hdc_v41x_fastfp_dpi.sv, "
    "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv, rtl/test/sim_hdc_fp32_lat_tops.sv): same ports, same LAT stages, II 1, "
    "same function; every other module is the RTL.  Equivalence on these cases: su-equiv (N 64 both ways)."),
    dpi_beh=("as dpi, and the keep-prefix integer adders (rtl/hdc/ot_hdc_prefix.sv) are the behavioural `+` "
             "(rtl/test/sim_hdc_prefix_beh.sv, combinational, same function); equivalence: su-equiv at N 64."))


def fp_dpi_lib(lib, beh_prefix=False):
    """The stream unit's source list with the bit-level FP units replaced by their DPI stand-ins (cycle-identical);
    beh_prefix: also the keep-prefix integer adders by their behavioural `+` (rtl/test/sim_hdc_prefix_beh.sv)."""
    rep = {"rtl/hdc/ot_hdc_fastfp.sv": ["rtl/test/sim_hdc_v41x_fastfp_dpi.sv", "rtl/test/sim_hdc_v41x_fastfp_wrap.sv",
                                        "rtl/test/sim_hdc_v41x_fastfp_dpi.cpp"],
           "rtl/hdc/ot_hdc_fp32_add_lat.sv": ["rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv",
                                              "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp",
                                              "rtl/test/sim_hdc_fp32_lat_tops.sv"],
           "rtl/hdc/ot_hdc_fp32_mul_lat.sv": []}
    if beh_prefix:
        rep["rtl/hdc/ot_hdc_prefix.sv"] = ["rtl/test/sim_hdc_prefix_beh.sv"]
    out = []
    for p in lib:
        r = str(Path(p).relative_to(ROOT))
        out += [ROOT / x for x in rep[r]] if r in rep else [p]
    return out


def cmd_su_equiv(a):
    """The RTL-FP and DPI-FP runs of the same cases (N 64 / M 16) must agree in every output word and every op's
    emit / write / result cycle."""
    r0, r1 = (json.loads(Path(x).read_text()) for x in a.su.split(","))
    assert r0["config"]["fp"] == "rtl" and r1["config"]["fp"].startswith("dpi") and \
        r0["cases_sha256"] == r1["cases_sha256"]
    rows, ok = [], True
    for x, y in zip(r0["chains"], r1["chains"]):
        if x["exact"] is None or y["exact"] is None:
            assert x["exact"] is None and y["exact"] is None
            continue
        same = x["chain"] == y["chain"] and x["vm_out_sha256"] == y["vm_out_sha256"] and x["per_op"] == y["per_op"] \
            and x["cycles_end"] == y["cycles_end"]
        ok &= same
        rows.append(dict(chain=x["chain"], identical=same, cycles_end=[x["cycles_end"], y["cycles_end"]],
                         vm_out_sha256=x["vm_out_sha256"]))
    rec = dict(schema="opentallas.rtl.dshbm_baseline_su_fp_equiv.v1", generated_utc=now(), source_commit=git_head(),
               status="pass" if ok and rows and len(r0["chains"]) == len(r1["chains"]) else "fail",
               skipped_no_layout=r0.get("skipped", []),
               config=dict(rtl=r0["config"], dpi=r1["config"]), chains=rows,
               inputs={Path(p).name: sha(Path(p)) for p in a.su.split(",")})
    Path(a.record).write_text(json.dumps(rec, indent=1) + "\n")
    print("SU-EQUIV", rec["status"], sum(r["identical"] for r in rows), "/", len(rows))
    return 0 if rec["status"] == "pass" else 1


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ======================================================================================================================
# compose: walk the executed 40-layer + head program, pricing every op from a measured element (or flagging it)
# ======================================================================================================================
F_FAST, F_SER = 1.2e9, 0.9e9
BARRIER_CYC, SERVICE_CYC = 78, 4                 # measured boundary (gpu_supply_barrier); honest ACK/fence/owner
W15_LEG_PHY_NS = 4 * 0.9340659340659341 + 56.86813186813187 + 59 * 0.9340659340659341   # W15 board_112g enc+chan+dec
FETCH_POSTPONED_NS, FETCH_LIVE_NS, FETCH_CDC_NS, FETCH_STALL_NS = 133.2, 469.5, 6.4, 0.1
QUANT_NS = 40.6                                  # model node price of an FP8 activation quantiser (not lowered)
# SM-domain clocks.  The measured element (rtl/gpu/ot_gpu_sm_v.sv) holds ot_gpu_issue, ot_gpu_bulk_copy, ot_gpu_stack,
# the tree and the columns; its as-built loop-carried paths (risk_clock_loops_20261003 screens, 0.833 ns, pre-route):
# bulk copy DS 589.7 MHz (binding), issue DS 751.8 MHz, stack 1,252 MHz.  The same baseline bulk copy inside the
# HBM-accel wrapper with ENABLE=0 screens 541.1 MHz (hbm_clock_loops_20261004 r1).  The 1.2 GHz issue closure and the
# 693.9 MHz bulk-copy screen at main are the HA3/HA6 levers (ENABLE=1), not the baseline: sensitivity only.
SM_CLOCKS = {"target_1p2GHz": 1.2e9, "as_built_bulk_copy_0p590GHz": 0.5897e9,
             "as_built_wrapper_e0_0p541GHz": 0.5411e9, "lever_bulk_copy_fix_screen_0p694GHz": 0.6939e9}
SWITCH = [("tomahawk_ultra_protocol", "board"), None, ("low", "board"), ("central", "board"), ("high", "board"),
          ("central", "kp4")]
HEADLINE_SWITCH = "tomahawk_ultra_protocol_board"   # owner rule 2026-10-04: publish with the TU-protocol collectives
# attention tile: one job (16 query rows x T KV rows, scores + softmax handoff + P.V), start to done, measured
# (results/rtl/v41_full_attention_numeric/result.json: tail129 T=128 225 cycles, mixed640 T=640 609 cycles)
ATT_TILE = {128: 225, 640: 609}
TILE_JOBS = lambda P: P             # noqa: E731  (sensitivity: 1 = the positions share one 16-row job)


def su_exact(r):
    """Skipped rows (no layout at this width) are never measured.  A chain counts as measured when the RTL's output words equal the executor's (golden-checked) values.  The
    unit reference's own refusal predicate is stricter than the unit for sqrt(softplus(x)), x < 0 (it refuses the
    negative ARGUMENT although softplus(x) > 0), so for router_act the executor checks decide."""
    if r["exact"] is None:
        return False
    if r["exact"]:
        return True
    return r["fn"] == "router_act" and all(x["bit_exact"] for x in r["checks"]) and \
        r["unit_reference"].get("faults") == 0 and r["unit_reference"].get("vm_mismatch_words") == 0


def su_table(su_rec, su2_rec=None, P=1):
    """Measured chain cycles by (layer-independent) key; the chains are data-independent in time.  P > 1: the P
    positions' chain = the 1-position run + (P - 1) x the measured marginal of the 2-position run (in-order unit,
    each position's ops issue behind the previous position's; own buffers, no shared hazard)."""
    if P > 1:
        t1, t2 = su_table(su_rec), su_table(su2_rec)
        return {k: t1[k] + (P - 1) * (t2[k] - t1[k]) for k in t1 if k in t2}
    t = {}
    for r in su_rec["chains"]:
        if not su_exact(r):
            continue
        fn = r["fn"]
        key = fn
        if fn in ("hc_pre_norm", "hc_post"):
            key = f"{fn}.{r['chain'].split('.')[-1]}"
        if fn == "attend":
            key = f"attend.T{r['T']}"
        if fn == "swiglu":
            key = "swiglu.routed" if not r["chain"].endswith(".s6") else "swiglu.shared"
        t.setdefault(key, []).append(r["cycles_end"])
    return {k: max(v) for k, v in t.items()}


def price_local(op, su, f_ser, flags, WC, m, P=1):
    """(us on the chain, how) of one local step for P positions: su is the measured chain table at P positions; the
    model-priced pieces repeat their issue as the W19 composer does (LOCAL_REPEAT); the attention tile runs one job
    per position (each position selects its own 512 compressed rows, so the 16-row job cannot share them)."""
    fn = op["fn"]
    R = WC.LOCAL_REPEAT(P)
    if fn in WC.OFF_PATH:
        return 0.0, "off-path (model)"
    if fn in ("hc_pre_norm", "final_norm"):
        k = "hc_pre_norm." + op.get("which", "attn") if fn == "hc_pre_norm" else "final_norm"
        k = k if k in su else "hc_pre_norm.attn"
        flags.add("FP8 activation quantiser after the norm: model node price 40.6 ns (QE, not lowered)")
        return su[k] / f_ser * 1e6 + R * QUANT_NS * F_FAST / F_SER / 1e3, "SU measured + quant(model)"
    if fn == "hc_post":
        return su["hc_post." + op["which"]] / f_ser * 1e6, "SU measured"
    if fn == "q_norm_kv_row":
        flags.add("FP8 QDQ of the window row / q: model node price 40.6 ns (QE, not lowered)")
        return su["q_norm_kv_row"] / f_ser * 1e6 + R * QUANT_NS * F_FAST / F_SER / 1e3, "SU measured + quant(model)"
    if fn in ("q_rope", "router_act", "moe_sum", "argmax_local"):
        if fn in su:
            return su[fn] / f_ser * 1e6, "SU measured"
    if fn == "route":
        flags.add("router top-6 select: model node price (ot_gpu_router_topk is RTL-measured inside w19_expert_fetch)")
        sel = (31.9 + 25.1) * F_FAST / F_SER / 1e3
        return su["route"] / f_ser * 1e6 + R * sel, "SU measured + top6(model)"
    if fn == "swiglu":
        return su["swiglu.routed"] / f_ser * 1e6, "SU measured (once a layer)"
    if fn == "attend":
        T = 640 if op.get("yarn") else 128
        k = f"attend.T{T}"
        if k in su and T in ATT_TILE:
            tile = TILE_JOBS(P) * ATT_TILE[T] / F_FAST * 1e6
            return su[k] / f_ser * 1e6 + tile, f"SU measured + tile(cited RTL, T={T})"
    ns, _ = WC.local_cycles(op, m)
    flags.add(f"local {fn}: model element price (not re-measured here)")
    return R * ns / 1e3, "model"


def switch_us(op, coll, switch):
    """A sourced switch scenario's fixed hardware-path latency in place of the W15 RTL switch's fixed term (the W15
    slopes keep carrying the bytes): tools/uarch_model.hbm_switch_collective_us, the AUTHORITATIVE scenarios
    (results/uarch/hbm_switch_latency_authoritative_20261004; low / central / high = push_optimistic / nvls_measured /
    gpu_fenced; the ablation's default is nvls_measured on board reach), small-message fixed term."""
    import uarch_model as U
    scen, fec = switch
    kind = "ar" if op["kind"] == "all_reduce" else "ag"
    fixed = coll[kind]["fixed_cycles"] / coll["hz"] * 1e6
    return U.hbm_switch_collective_us(scen, kind, fec) - fixed


def compose_program(prog, sm, coll, su, WC, f_sm, f_ser=F_SER, fetch_ns=FETCH_POSTPONED_NS, service=False,
                    leg_delta_ns=0.0, sm_mode="lines_drain", switch=None, P=1):
    """P > 1: the verify pass of P positions.  SM: the measured 1-column cycles (the element's columns carry the
    positions; 5-column = 1-column measured, results/rtl/dshbm_dspark_draft_20261004) -- the routed experts' union
    and its fetch are NOT in this walk (added by the caller from the model, flagged); collectives at P x bytes."""
    flags = set()
    m = dict(n_keys=0)
    out, tot = [], dict(sm=0.0, barrier=0.0, collective=0.0, local=0.0, fetch=0.0)
    by_fn = {}
    bcyc = BARRIER_CYC + (SERVICE_CYC if service else 0)
    for lay in prog["layers"]:
        t = dict(sm=0.0, barrier=0.0, collective=0.0, local=0.0, fetch=0.0)
        pend, swi, ncoll, how = None, False, 0, {}

        def flush():
            nonlocal pend
            if pend:
                t["sm"] += pend["cyc"] / f_sm * 1e6
                t["barrier"] += bcyc / f_sm * 1e6
            pend = None
        for op in lay["ops"]:
            k = op["kind"]
            if k == "mv":
                rows_die = max(r1 - r0 for r0, r1 in op["rows"])
                R = math.ceil(rows_die / WC.N_SM)
                lines, drain, hw = sm.op(op["fmt"], op["k"], R)
                if hw != "measured":
                    flags.add(f"SM shape {op['fmt']} K={op['k']} R={R}: line rate of the measured table (scaled)")
                startup = 0
                if sm_mode == "start_to_done":
                    key = ({"fp8": "v41_fp8", "fp4": "v41_fp4", "bf16": "v41_bf16"}[op["fmt"]], op["k"], R)
                    v = sm.rows.get(key)
                    startup = (v["start_to_done"] - v["lines"] - v["drain"]) if v else 0
                batch = op["tag"].startswith("expert slot")
                if pend and batch and pend["batch"]:
                    pend["cyc"] += lines
                    pend["drain"] = max(pend["drain"], drain)
                    pend["cyc"] += 0
                else:
                    flush()
                    pend = dict(cyc=lines + drain + startup, drain=drain, batch=batch)
                continue
            if k == "local" and op["fn"] == "swiglu":
                if not swi:
                    us, hw = price_local(op, su, f_ser, flags, WC, m, P)
                    t["local"] += us
                    by_fn[f"swiglu|{hw}"] = by_fn.get(f"swiglu|{hw}", 0.0) + us
                    swi = True
                continue
            flush()
            if k in ("all_gather", "all_reduce", "topk_merge", "kv_gather"):
                if op["tag"].startswith(WC.OFF_PATH_COLL):
                    continue
                us, hw = WC.prod_us(op, coll, P)
                sel = 0.0                       # the top-k merges' select (compute, not transport)
                if op["kind"] == "topk_merge" and op.get("what") in ("sel", "cand"):
                    est = 9 * (WC.TP * op["k"] / 64) * P / coll["hz"] * 1e6
                    us -= est
                    # the measured exact wide select (96 x 512, l20_index_topk, 419 cycles) replaces the W15b
                    # estimate for "sel", as in the W19 composition the model is (71b3ffc5 prod_us)
                    sel = P * coll["select_cycles"] / coll["hz"] * 1e6 if (op.get("what") == "sel" and
                                                                        coll.get("select_cycles")) else est
                if switch and switch[0] in ("tomahawk_ultra_protocol", "tomahawk_ultra_inc"):
                    import uarch_model as U       # every op at its actual bytes (uarch_model.w19_transport_us)
                    us = U.tu_transport_us(op["kind"], P * op["bytes"], switch[0])
                elif switch:
                    us += switch_us(op, coll, switch)
                us += sel
                t["collective"] += us + 2 * leg_delta_ns / 1e3
                ncoll += 1
            elif k == "expert_fetch":
                t["fetch"] += (fetch_ns + ((FETCH_CDC_NS + FETCH_STALL_NS) if service else 0)) / 1e3
            elif k == "local":
                if op["fn"] == "index_scores":
                    m["n_keys"] = op["n"]
                us, hw = price_local(op, su, f_ser, flags, WC, m, P)
                t["local"] += us
                by_fn[f"{op['fn']}|{hw}"] = by_fn.get(f"{op['fn']}|{hw}", 0.0) + us
                how[op["fn"]] = hw
        flush()
        out.append(dict(layer=lay["layer"], collectives=ncoll, us={k: round(v, 3) for k, v in t.items()},
                        total_us=round(sum(t.values()), 3), local_pricing=how))
        for kk in tot:
            tot[kk] += t[kk]
    T = sum(tot.values())
    return dict(total_us=round(T, 2), tokens_s=round(1e6 / T, 1), parts_us={k: round(v, 2) for k, v in tot.items()},
                layers=out, flags=sorted(flags), local_by_fn_us={k: round(v, 3) for k, v in sorted(by_fn.items())})


DRAFT_REC = "results/rtl/dshbm_dspark_draft_20261004/composition.json"     # MEASURED HBM draft (main 9d1046521)
HBM_DIE_PEAK_TBS, HBM_DIE_SUSTAINED_TBS = 4.0, 3.6     # 4 HBM3E stacks a die, 1.0 TB/s each (0.9 sustained)
FMT_BYTES = {"fp4": 0.5 + 1 / 32, "fp8": 1.0 + 1 / (128 * 128), "bf16": 2.0}   # + block scales (ue8m0 / 32; FP8 128x128)
KV_ROW_BYTES = 448 + 64 * 2      # FP8 nope part + BF16 RoPE part of a 512-wide compressed / window KV row
IDX_KEY_BYTES = 128 // 2 + 128 // 32                                    # FP4 index key + its ue8m0 scales


def hbm_traffic(prog, tok_s, sm_us):
    """Bytes one die reads from its HBM for the token (die 0's row slices of every matvec in the executed program,
    its share of the index keys, its window rows and its share of the gathered compressed-KV rows) and the achieved
    rate over the token and over the SM-busy time, against the die's 4.0 TB/s peak."""
    w = idx = kv = 0.0
    for lay in prog["layers"]:
        for op in lay["ops"]:
            if op["kind"] == "mv":
                r0, r1 = op["rows"][0]
                w += (r1 - r0) * op["k"] * FMT_BYTES[op["fmt"]]
            elif op["kind"] == "local" and op["fn"] == "index_scores":
                idx += math.ceil(op["n"] / prog["tp"]) * IDX_KEY_BYTES
            elif op["kind"] == "local" and op["fn"] == "attend":
                kv += 128 * KV_ROW_BYTES                                  # the die's replicated window rows
            elif op["kind"] == "kv_gather":
                kv += op["bytes"] / prog["tp"]                            # sources' reads, one die's share
    tot = w + idx + kv
    T = 1 / tok_s
    return dict(bytes_per_die=dict(weights=round(w), index_keys=round(idx), kv_rows=round(kv), total=round(tot)),
                achieved_tbs_over_token=round(tot / T / 1e12, 4),
                achieved_tbs_over_sm_busy=round(w / (sm_us * 1e-6) / 1e12, 4),
                fraction_of_peak_over_token=round(tot / T / 1e12 / HBM_DIE_PEAK_TBS, 4),
                fraction_of_peak_over_sm_busy=round(w / (sm_us * 1e-6) / 1e12 / HBM_DIE_PEAK_TBS, 4),
                peak_tbs=HBM_DIE_PEAK_TBS, sustained_tbs=HBM_DIE_SUSTAINED_TBS,
                note="the SM bench's bulk copy is behavioural (LAT/JIT), so the SM-busy rate is the rate the measured "
                     "SM schedule DEMANDS of the HBM, not a DRAM-model measurement; weights are prefetchable under "
                     "the chain (the W19 weight sweep), so the token is latency-bound, not bandwidth-bound")


def mtp_and_accelerator(prog, base, su1, su2):
    """MEASURED baseline AR and MTP (TU-protocol collectives, 1.2 GHz) against the model's ablation and accelerator
    rows.  MTP step = verify(P = 6) + measured draft + seed_commit, tau from the draft record (third-party published, gamma 5)."""
    import uarch_model as U
    from hbm_accelerator_model import _load_study
    mstudy, _, _, _ = _load_study(ROOT)
    V1, V6 = mstudy.VERIFY_PARTS[1], mstudy.VERIFY_PARTS[6]
    sw = ("tomahawk_ultra_protocol", "board")
    dr = json.loads((ROOT / DRAFT_REC).read_text())
    row = {r["design"]: r for r in dr["rows"] if r["ctx"] == "1M" and r["scenario"] == sw[0]}
    tau = dr["tau"]
    b = dict(base)
    b["su"] = su_table(su1)
    ar = compose_program(**b, f_sm=F_FAST, switch=sw)
    reps = su2["chains"][0].get("reps", 2)
    b["su"] = su_table(su2) if reps == 6 else su_table(su1, su2, 6)     # 6 positions measured, or extrapolated
    v6 = compose_program(**b, f_sm=F_FAST, switch=sw, P=6)
    b2 = dict(b)
    v6_onejob = None
    global TILE_JOBS
    saved = TILE_JOBS
    try:
        TILE_JOBS = lambda P: 1      # noqa: E731
        v6_onejob = compose_program(**b2, f_sm=F_FAST, switch=sw, P=6)
    finally:
        TILE_JOBS = saved
    union = dict(sm=round(V6["sm"] - V1["sm"], 3), fetch=round(V6["fetch"] - V1["fetch"], 3))
    ab = row["ablation_w19"]
    draft, seed = ab["as_built"]["draft_us"], ab["seed_commit_us"]

    def mtp(v):
        verify = v["total_us"] + union["sm"] + union["fetch"]
        step = verify + draft + seed
        return dict(verify_p6_us=round(verify, 2), step_us=round(step, 2), mtp_tok_s=round(tau * 1e6 / step, 1),
                    verify_parts_us={**v["parts_us"], "sm": round(v["parts_us"]["sm"] + union["sm"], 2),
                                     "fetch": round(v["parts_us"]["fetch"] + union["fetch"], 2)})
    m6, m6b = mtp(v6), mtp(v6_onejob)
    T = mstudy.T
    rungs1 = {r: x for r, x, _ in mstudy.ds_rungs(1, include_conditional=False)}
    rungs6 = {r: x for r, x, _ in mstudy.ds_rungs(6, include_conditional=False)}
    keep = [r for r in rungs1 if r not in ("R2", "R3a")]
    ab_ar_parts = {**V1, "collective": round(V1["collective"] + U.w19_transport_us(1, sw[0]) -
                                             U.w19_transport_us(1, "w15", "kp4"), 2)}
    ab_v6_parts = {**V6, "collective": round(V6["collective"] + U.w19_transport_us(6, sw[0]) -
                                             U.w19_transport_us(6, "w15", "kp4"), 2)}
    acc = row["accelerator_firm_switch"]
    comp = json.loads((ROOT / "results/rtl/hbm_accel_composition_20261004/measured_composition.json").read_text())
    crow = comp["revisions"][-1]["rows"]
    adopted = [r for r in crow if r["measured_gain_us"] and "ADOPT" in r["verdict"].upper()
               and "NOT ADOPTED" not in r["verdict"].upper() and not r["verdict"].startswith("REJECT")]
    return dict(
        rule="publish only measured compositions: the measured baseline IS the measured accelerator until a rung is "
             "measured AND adopted; no rung is adopted (composition record r%d)" % comp["revisions"][-1]["revision"],
        measured=dict(ar_us=ar["total_us"], ar_tok_s=ar["tokens_s"], ar_parts_us=ar["parts_us"],
                      mtp=m6, mtp_tok_s=m6["mtp_tok_s"], draft_us=draft, seed_commit_us=seed, tau=tau,
                      sensitivity_tile_one_job_for_6_positions=m6b,
                      adopted_measured_rungs=[r["rung"] for r in adopted]),
        model=dict(ablation_tu=dict(ar_tok_s=ab["ar_tok_s"], ar_us=round(T(V1) + U.w19_transport_us(1, sw[0]) -
                                                                          U.w19_transport_us(1, "w15", "kp4"), 2),
                                    ar_parts_us=ab_ar_parts, verify_p6_us=ab["verify_p6_us"], verify_parts_us=ab_v6_parts,
                                    draft_us=draft, mtp_tok_s=ab["as_built"]["mtp_tok_s"]),
                   accelerator_firm=dict(ar_tok_s=acc["ar_tok_s"], verify_p6_us=acc["verify_p6_us"],
                                         draft_us=acc["as_built"]["draft_us"], seed_commit_us=acc["seed_commit_us"],
                                         mtp_tok_s=acc["as_built"]["mtp_tok_s"],
                                         rungs_kept=keep, rung_gain_us_p1={r: round(rungs1[r], 3) for r in keep},
                                         rung_gain_us_p6={r: round(rungs6[r], 3) for r in keep},
                                         rung_sum_us_p1=round(sum(rungs1[r] for r in keep), 3),
                                         rung_sum_us_p6=round(sum(rungs6[r] for r in keep), 3),
                                         status="UNVALIDATED hypothesis (frozen HA ladder)"),
                   accelerator_measured_composition=row["accelerator_measured_composition"]["ar_tok_s"]),
        delta_vs_ablation_model_us=dict(
            ar={k: round(ar["parts_us"][k] - ab_ar_parts[k], 2) for k in ab_ar_parts},
            verify_p6={k: round(m6["verify_parts_us"][k] - ab_v6_parts[k], 2) for k in ab_v6_parts}),
        ratios=dict(ar_measured_over_accel_model=round(ar["tokens_s"] / acc["ar_tok_s"], 4),
                    mtp_measured_over_accel_model=round(m6["mtp_tok_s"] / acc["as_built"]["mtp_tok_s"], 4),
                    ar_measured_over_ablation_model=round(ar["tokens_s"] / ab["ar_tok_s"], 4),
                    mtp_measured_over_ablation_model=round(m6["mtp_tok_s"] / ab["as_built"]["mtp_tok_s"], 4)),
        unvalidated_terms=[
            "verify(P=6) routed-expert UNION: SM lines and fetch exposure increments (+%.2f / +%.2f us) are the "
            "W19 composer's (measured union counts, line-rate pricing), not re-measured here" % (union["sm"],
                                                                                              union["fetch"]),
            "verify(P=6): model-priced local steps (index q/scores/top-k, Engram, cand, FP8 quantiser, router "
            "top-6 select) repeat by the W19 LOCAL_REPEAT issue fraction",
            "seed_commit (%.3f us) from the draft record" % seed] + sorted(set(ar["flags"]) | set(v6["flags"])),
        verify_p6_walk=dict(total_us=v6["total_us"], parts_us=v6["parts_us"], flags=v6["flags"]))


def cmd_compose(a):
    import w19_hbm_token_compose as WC
    out = Path(a.out)
    prog = json.loads((out / "program.json").read_text())
    sm_new = json.loads((out / "sm_real_ops.json").read_text())
    sm_old = json.loads((ROOT / "results/rtl/w19_sm_real_ops.json").read_text())
    sm = WC.SMTable([sm_old, sm_new], "ar")          # the new run's rows override the old for the same shape
    sm_only_new = WC.SMTable([sm_new], "ar")
    su_rec = json.loads(Path(a.su).read_text())
    su = su_table(su_rec)
    w15 = json.loads((ROOT / "results/rtl/w15_hbm_nvls.json").read_text())
    coll = WC.w15_prod(w15, "hbm_p48_ss")
    coll["select_cycles"] = 419
    model = json.loads((ROOT / "results/uarch/h3_complete_native_calendar_20261002/authority_reconciliation_r4/inputs/"
                        "w19_hbm_token_ar_fused_wsel256.json").read_text())["result"]
    scen = {}
    base = dict(prog=prog, sm=sm, coll=coll, su=su, WC=WC)
    scen["measured_target_clock"] = compose_program(**base, f_sm=F_FAST)
    scen["measured_target_clock_honest_service"] = compose_program(**base, f_sm=F_FAST, fetch_ns=FETCH_LIVE_NS,
                                                                   service=True)
    scen["measured_target_clock_sm_start_to_done"] = compose_program(**base, f_sm=F_FAST, sm_mode="start_to_done")
    for name, f in SM_CLOCKS.items():
        if name.startswith("target"):
            continue
        scen[f"measured_{name}_sm_domain"] = compose_program(**base, f_sm=f)
        scen[f"measured_{name}_sm_domain_honest_service"] = compose_program(**base, f_sm=f, fetch_ns=FETCH_LIVE_NS,
                                                                            service=True)
    grid = {}
    for cname, f in SM_CLOCKS.items():
        for sw in SWITCH:
            key = f"{cname}|{'w15_rtl_switch' if sw is None else sw[0] + '_' + sw[1]}"
            r = compose_program(**base, f_sm=f, switch=sw)
            grid[key] = dict(tokens_s=r["tokens_s"], total_us=r["total_us"], parts_us=r["parts_us"])
    # the model under each switch scenario: the same fixed-term replacement over the same on-path collectives
    w0 = grid["target_1p2GHz|w15_rtl_switch"]["parts_us"]["collective"]
    model_by_switch = {}
    for sw in SWITCH:
        k = "w15_rtl_switch" if sw is None else sw[0] + "_" + sw[1]
        dc = grid[f"target_1p2GHz|{k}"]["parts_us"]["collective"] - w0
        tot = model["total_us"] + dc
        model_by_switch[k] = dict(total_us=round(tot, 2), tokens_s=round(1e6 / tot, 1),
                                  collective_us=round(model["parts_us"]["collective"] + dc, 2))
    scen["sensitivity_light_fec_130ns_legs"] = compose_program(**base, f_sm=F_FAST, leg_delta_ns=130 - W15_LEG_PHY_NS)
    scen["sensitivity_kp4_209ns_legs"] = compose_program(**base, f_sm=F_FAST, leg_delta_ns=209 - W15_LEG_PHY_NS)
    # the per-term difference against the model, representative layers and token
    rep = {}
    mlay = {str(l["layer"]): l for l in model["layers"]}
    mlay["head"] = mlay.get("head")
    for L in ("0", "2", "head"):
        meas = next(x for x in scen["measured_target_clock"]["layers"] if str(x["layer"]) in (L, "-1" if L == "head"
                                                                                          else L))
        mm = mlay[L]
        rep[L] = dict(model=mm["us"], model_total=mm["total_us"], measured=meas["us"], measured_total=meas["total_us"],
                      delta={k: round(meas["us"][k] - mm["us"][k], 3) for k in mm["us"]},
                      local_pricing=meas["local_pricing"])
    mt = scen["measured_target_clock"]
    token_delta = {k: round(mt["parts_us"][k] - model["parts_us"][k], 2) for k in model["parts_us"]}
    rec = dict(schema="opentallas.rtl.dshbm_baseline_measured.v1", generated_utc=now(), source_commit=git_head(),
               design="DeepSeek-V4.1-Flash HBM BASELINE (GPU-organised ablation): TP-96, 32 SMs/die, static schedule, "
                      "hardware barrier, W15 NVLS switch; 1M context, position 1,048,575, AR, batch 1",
               model=dict(tokens_s=model["tokens_s"], total_us=model["total_us"], parts_us=model["parts_us"],
                          source="results/uarch/w19_hbm_token_ar_fused_wsel256.json (W19 composition, 2,261.7)"),
               published=dict(
                   rule="owner 2026-10-04: 1M context (position 1,048,575, full synthetic format-valid KV/index history), "
                        "TU-protocol collectives (uarch_model tomahawk_ultra_protocol, board)",
                   switch=HEADLINE_SWITCH,
                   tokens_s_1p2GHz=grid[f"target_1p2GHz|{HEADLINE_SWITCH}"]["tokens_s"],
                   parts_us_1p2GHz=grid[f"target_1p2GHz|{HEADLINE_SWITCH}"]["parts_us"],
                   tokens_s_as_built=grid[f"as_built_bulk_copy_0p590GHz|{HEADLINE_SWITCH}"]["tokens_s"],
                   parts_us_as_built=grid[f"as_built_bulk_copy_0p590GHz|{HEADLINE_SWITCH}"]["parts_us"],
                   model_tokens_s=model_by_switch[HEADLINE_SWITCH]["tokens_s"],
                   model_parts_us={**model["parts_us"],
                                   "collective": model_by_switch[HEADLINE_SWITCH]["collective_us"]},
                   delta_us_by_term_1p2GHz={k: round(grid[f"target_1p2GHz|{HEADLINE_SWITCH}"]["parts_us"][k] - (
                       model_by_switch[HEADLINE_SWITCH]["collective_us"] if k == "collective" else model["parts_us"][k]),
                       2) for k in model["parts_us"]}),
               headline=dict(measured_tokens_s=mt["tokens_s"], measured_total_us=mt["total_us"],
                             model_tokens_s=model["tokens_s"], token_delta_us_by_term=token_delta,
                             honest_service_tokens_s=scen["measured_target_clock_honest_service"]["tokens_s"]),
               switch_clock_grid=grid, model_by_switch=model_by_switch, representative_layers=rep, scenarios={k: {kk: vv for kk, vv in v.items()} for k, v in scen.items()},
               inputs={"program": sha(out / "program.json"), "sm_real_ops": sha(out / "sm_real_ops.json"),
                       "su": sha(Path(a.su)), "execute": sha(out / "execute.json"),
                       "w15_hbm_nvls": sha(ROOT / "results/rtl/w15_hbm_nvls.json"),
                       "w19_sm_real_ops(older shapes)": sha(ROOT / "results/rtl/w19_sm_real_ops.json")},
               constants=dict(barrier_cycles=BARRIER_CYC, service_cycles=SERVICE_CYC, w15_leg_phy_ns=W15_LEG_PHY_NS,
                              fetch_ns=dict(postponed=FETCH_POSTPONED_NS, refresh_live=FETCH_LIVE_NS,
                                            cdc=FETCH_CDC_NS, stall=FETCH_STALL_NS),
                              attention_tile_cycles=ATT_TILE, sm_clocks=SM_CLOCKS, serial_clock=F_SER,
                              su_chain_cycles=su))
    if a.su2:
        rec["mtp_and_accelerator"] = mtp_and_accelerator(prog, base, su_rec, json.loads(Path(a.su2).read_text()))
        rec["inputs"]["su_p2"] = sha(Path(a.su2))
    rec["hbm"] = hbm_traffic(prog, rec["published"]["tokens_s_1p2GHz"], rec["published"]["parts_us_1p2GHz"]["sm"])
    Path(a.record).parent.mkdir(parents=True, exist_ok=True)
    Path(a.record).write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print(json.dumps(rec["published"], indent=1))
    print(json.dumps(rec["model_by_switch"], indent=1))
    for k, v in grid.items():
        print(f"GRID {k:58s} {v['tokens_s']:8.1f} tok/s {v['total_us']:8.2f} us {v['parts_us']}")
    for k, v in scen.items():
        print(f"{k:58s} {v['tokens_s']:8.1f} tok/s {v['total_us']:8.2f} us {v['parts_us']}")
    return 0


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in ("execute", "sm", "su-prep", "su-check", "su-run", "su-equiv", "compose"):
    ap = argparse.ArgumentParser()
    ap.add_argument("step")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--sm-accelerator", action="store_true",
                    help="SM step only: explicit ENABLE0/1 accelerator comparison on the retained dump; separate record")
    ap.add_argument("--sm-simulator", choices=("iverilog", "verilator"), default="iverilog")
    ap.add_argument("--sm-verilator", default="verilator")
    ap.add_argument("--sm-build-jobs", type=int, default=1)
    ap.add_argument("--bcast", type=int, default=0)
    ap.add_argument("--ret", type=int, default=0)
    ap.add_argument("--mlat", type=int, default=3)
    ap.add_argument("--alat", type=int, default=3)
    ap.add_argument("--work", default=None)
    ap.add_argument("--su", default=None)
    ap.add_argument("--su2", default=None, help="the multi-position SU record (6 positions op-major, or 2 positions; "
                    "MTP verify composition)")
    ap.add_argument("--record", default=None)
    ap.add_argument("--n", type=int, default=SU_N)
    ap.add_argument("--m", type=int, default=SU_M)
    ap.add_argument("--fp", choices=("rtl", "dpi", "dpi_beh"), default="rtl")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--op-major", action="store_true", help="with --reps: interleave the positions op by op")
    ap.add_argument("--cases", default="su_cases.pkl")
    ap.add_argument("--exec-layers", default=None, help="execute only: default-off; run these layers alone and "
                    "snapshot the DU steps (cmd_execute_ext)")
    a = ap.parse_args()
    raise SystemExit({"execute": cmd_execute, "sm": cmd_sm, "su-prep": cmd_su_prep, "su-check": cmd_su_check, "su-run": cmd_su_run, "su-equiv": cmd_su_equiv, "compose": cmd_compose}[a.step](a))
