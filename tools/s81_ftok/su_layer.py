#!/usr/bin/env python3
"""The REAL SU slab in the S81 layer vehicle (s81-functional-token r3, 2026-10-14): SU jobs of one layer of the 1M token.

tools/s81_ctrl/die_layer_stim.py --su-snap <snap_LXX.pkl> calls build() to turn the layer program's SU ops (port 1)
into jobs of the production SU slab dsfd_sp_su_h (tb_s81_die_layer +define+TB_SU_REAL), on the golden operands of
that layer captured by tools/dsrom_1m_su.py golden --engram (the layer replay is asserted bit-exact against the w17
shard there).  The job descriptors, operand rows and expected result rows come from tools/s81_suhc/su_gate.py's Run
(the SU gate's own lowering and CPU reference, shapes = the full / production shape), placed in the bench VM from
SU_BASE.  Every expected value is first asserted against the model golden's own intermediate where one exists
(q norm, kv RoPE, q RoPE, softmax e / o, router scores, biased scores, expert activations).

Program op -> SU job (one job per fused chain; the other ops of the chain are ALIASED to it: their consumers wait on
the job, as the HC NORM absorbs attn.quant / ffn.norm.scale / ffn.quant):
  attn.q_quant          QN  (+ attn.q_norm.sumsq)                       q RMSNorm -> FP8
  attn.kv_rope_qdq      KV  (+ attn.kv_norm.sumsq)                      kv RMSNorm -> RoPE -> FP8 QDQ
  attn.q_rope           QR                                              RoPE tails of the die's 16 q heads, in place
  attn.exp              SE  (+ attn.max, attn.den, attn.sink)           softmax e (P) + den with the sink
  attn.normalize        SO                                              P.V / den -> inverse RoPE -> BF16
  attn.z_quant          QB  (FP8)                                       the die's wo_a output z (2,048) -> FP8
  ffn.softplus_sqrt     RA                                              sqrt(softplus) of the die's 96 router rows
  ffn.bias              RB                                              all 384 scores + bias
  ffn.shared_swiglu     SW  w = 1.0 (+ ffn.shared_quant)                shared expert, the die's 576 rows
  ffn.quant2            SW  routed (+ ffn.swiglu, ffn.route_w)          6 experts x the die's 576 rows, weight each
  ffn.weights           RW  (r3, F11)                                   route weights -> the SW job's descriptor words
  boot: <L>.su.gain_q / gain_k  GQ (set 1) / GK (set 2): q_norm / kv_norm weights (layer constants)
  attn.cmp.row_qdq      CN  (+ compressor norm chain)                 norm512 -> RoPE -> FP4/16; also preserves pre-RoPE norm
  attn.cmp.k_rope_qdq   IK  (+ index-key norm chain)                  norm128 -> RoPE -> FP4/32
NOT an SU job kind (stay behavioural at program duration, listed in the result): compressor pooling, attn.idx.newkey,
attn.cand.final, and any op not in the table. All operands here remain fixture inputs, not native producer bindings.

SW lane fit: the slab's SW vector is SW_W = 1,024 lanes with ONE routing weight; an expert's die slice is 576 rows, so
each expert takes one vector padded with zero lanes (silu(0) * 0 = 0: the padded FP8 blocks are zero and the real
blocks are unchanged) -- the expert-to-vector fit costs 1,024 / 576 = 1.78x lanes (reported).
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/s81_suhc"))

F = np.float32
TP, DIE = 4, 0
SU_BASE = 9216                      # bench VM rows SU_BASE.. (H 0.., G 1280.., C 2560.., O 3072.., S 6144.., EH 8192..)
SU_PORT = 1
ROWS_DIE = 2304 // TP               # an expert's intermediate rows on one die

# program op tail -> (job, aliases)
JOBS = {"attn.q_quant": ("QN", ["attn.q_norm.sumsq"]),
        "attn.kv_rope_qdq": ("KV", ["attn.kv_norm.sumsq"]),
        "attn.q_rope": ("QR", []),
        "attn.exp": ("SE", ["attn.max", "attn.den", "attn.sink"]),
        "attn.normalize": ("SO", []),
        "attn.z_quant": ("QB", []),
        "attn.cmp.row_qdq": ("CN", ["attn.cmp.norm.sumsq", "attn.cmp.norm.rsqrt", "attn.cmp.norm.scale"]),
        "attn.cmp.k_rope_qdq": ("IK", ["attn.cmp.k_norm.sumsq", "attn.cmp.k_norm.rsqrt", "attn.cmp.k_norm.scale"]),
        "ffn.softplus_sqrt": ("RA", []),
        "ffn.bias": ("RB", []),
        "ffn.shared_swiglu": ("SWS", ["ffn.shared_quant"]),
        "ffn.quant2": ("SWR", ["ffn.swiglu", "ffn.route_w"])}


def same(a, b):
    a, b = np.asarray(a, F), np.asarray(b, F)
    return a.shape == b.shape and np.array_equal(a.view(np.uint32), b.view(np.uint32))


class SURun:
    """su_gate.Run at the production shape, VM from SU_BASE; records each job's arg by name."""

    def __init__(self):
        import su_gate as SG
        self.SG = SG
        self.r = SG.Run(SG.SHAPES["full"])
        self.r.top = SU_BASE
        self.arg = {}

    def _last_args(self, n):
        return [(p >> 7) & 0xFFFFFF for p in self.r.prog[-n:]]

    def gain(self, name, kind, gsel, w):
        self.r.gain(kind, gsel, w)
        self.arg[name] = self._last_args(1)[0]


def build(snap_path, layer, check_layer=True):
    """-> dict(arg={op name: SU job arg}, alias={op name: target op name}, behavioural=[op tails],
    vm={row: int}, exp={row: int}, jexp={op name: (first row, count)}, checks={label: bool}, sw_fit=...)"""
    import hdc_golden_v41 as V
    import dsrom_su_norm as NM
    import dsrom_su_softmax as SM
    import dsrom_su_swiglu as SWG
    s = pickle.loads(Path(snap_path).read_bytes())
    if check_layer:                    # backbone snapshot (tools/dsrom_1m_su.py): its layer and its replay checks
        assert s["layer"] == int(layer.lstrip("L")), (s["layer"], layer)
        assert all(s["checks"].values()), ("snapshot replay not exact", s["checks"])
    else:                              # DSpark row snapshot (tools/s81_ftok/mtp_golden.py, checked there)
        assert s.get("ftok_name") == layer, (s.get("ftok_name"), layer)
    L = layer
    su = SURun()
    r = su.r
    chk = {}
    eps = F(s["eps"])
    # ---- gains (boot)
    wq, wk = np.asarray(s["q_norm"]["w"], F), np.asarray(s["kv_norm"]["w"], F)
    su.gain(f"{L}.su.gain_q", "GQ", 1, wq)
    su.gain(f"{L}.su.gain_k", "GK", 2, wk)
    jexp = {}
    footprints = {}
    from su_footprints import footprint

    def job(name, fn, *args, n=1, **kw):
        k0 = len(r.prog)
        out = fn(*args, **kw)
        assert len(r.prog) == k0 + n
        for j, a in enumerate(su._last_args(n)):
            nm = name if n == 1 else name[j]
            su.arg[nm] = a
            kind = next(kind for kind, code in su.SG.K.items() if code == (a >> 20))
            owned = {}
            if k0+j in r.jexp:
                first, count_out = r.jexp[k0+j]
                # QR outputs are strided. Resolve its exact output addresses from
                # the descriptor in footprint; other jobs use the expected span.
                owned = {row:value for row,value in r.exp.items() if first <= row < first+count_out}
            footprints[nm] = footprint(kind, a, r.vm, r.sh, owned)
            if k0 + j in r.jexp:
                jexp[nm] = r.jexp[k0 + j]
        return out
    # ---- QN
    xq = np.asarray(s["q_norm"]["x"], F)
    y, _ = NM.golden_row("q", xq, np.zeros(4, F), wq, eps)
    chk["QN q norm == golden q_norm out"] = same(y, s["q_norm"]["out"])
    job(f"{L}.attn.q_quant", r.qn, xq, wq, eps, 1)
    # ---- KV
    cos, sin = (np.asarray(v, F) for v in s["kv_rope"]["cs"])
    xk = np.asarray(s["kv_norm"]["x"], F)
    yk, ro = NM.golden_row("kv", xk, np.zeros(4, F), wk, eps, (cos, sin))
    chk["KV norm == golden kv_norm out"] = same(yk, s["kv_norm"]["out"])
    chk["KV rope == golden kv_rope out"] = same(ro, s["kv_rope"]["out"])
    job(f"{L}.attn.kv_rope_qdq", r.kv, xk, wk, eps, cos, sin, 2)
    # ---- QR
    qc, qs = (np.asarray(v, F) for v in s["q_rope"]["cs"])
    qx = np.asarray(s["q_rope"]["x"], F)
    chk["QR rope == golden q_rope out"] = same(V.rope_tail(qx, (qc, qs)), s["q_rope"]["out"])
    job(f"{L}.attn.q_rope", r.qr, qx, qc, qs)
    # Compressor outputs must retain both raw FP4 formats and the pre-RoPE
    # normalized row consumed by the real cmp.wk field operation.
    compressor_outputs = {}
    if s.get("cmp"):
        cm = s["cmp"]
        for key, rope_key, tail, gain_name, method in (
                ("norm", "row_rope", "row_qdq", "gain_c", r.cn),
                ("k_norm", "k_rope", "k_rope_qdq", "gain_i", r.ik)):
            x = np.asarray(cm[key]["x"], F).reshape(-1)
            w = np.asarray(cm[key]["w"], F).reshape(-1)
            cc, ss = (np.asarray(v, F) for v in cm[rope_key]["cs"])
            norm = V.rmsnorm_bf16(x, w, eps)
            chk[f"{key} native norm reference == snapshot"] = same(norm, np.asarray(cm[key]["out"], F).reshape(-1))
            chk[f"{key} native rope reference == snapshot"] = same(V.rope_tail(norm, (cc, ss)), np.asarray(cm[rope_key]["out"], F).reshape(-1))
            compressor_outputs[tail] = job([f"{L}.su.{gain_name}", f"{L}.attn.cmp.{tail}"],
                                           method, x, w, eps, cc, ss, n=2)
    # ---- SE + SO
    at = s["hc"]["attend"]
    T = int(at["T"])
    sh = r.sh
    nv = (T + sh["SM_LPH"] - 1) // sh["SM_LPH"]
    fits = T > 0 and nv <= sh["SM_NVMAX"]
    sm_ok = False
    if fits:
        ac, asn = (np.asarray(v, F) for v in at["cs"])
        ref = SM.reference(at["s_raw"], at["attn_scale"], at["sink"], at["pv"], ac, asn)
        chk["SE e == golden e"] = same(ref["e"], at["e"])
        chk["SE den == golden den"] = same(ref["den"], at["den"])
        chk["SO o == golden o"] = same(ref["o"], at["o"])
        job([f"{L}.attn.exp", f"{L}.attn.normalize"], r.softmax, np.asarray(at["s_raw"], F), F(at["attn_scale"]),
            np.asarray(at["sink"], F), np.asarray(at["pv"], F), ac, asn, n=2)
        sm_ok = True
    # ---- QB (z: the die's quarter of the wo_a output)
    z = np.asarray(at["z"], F).reshape(-1)
    nz = len(z) // TP
    zd = z[DIE * nz:(DIE + 1) * nz]
    qb_ok = nz % (32 * sh["QB_NB"]) == 0
    if qb_ok:
        job(f"{L}.attn.z_quant", r.qb, zd, 0)
    # ---- RA / RB
    rt = s["router"]
    n = len(rt["raw"]) // TP
    xr = np.asarray(rt["raw"], F)[DIE * n:(DIE + 1) * n]
    chk["RA sqrt(softplus) == golden scores"] = same(V.sqrt(V.softplus(xr)), np.asarray(rt["scores"], F)[DIE * n:(DIE + 1) * n])
    chk["RB scores + bias == golden biased"] = same(V.add(rt["scores"], rt["bias"]), rt["biased"])
    router_fits = n % 16 == 0 and len(rt["raw"]) % 16 == 0     # RA / RB move whole 16-word rows (DSpark: 4 experts)
    if router_fits:
        job(f"{L}.ffn.softplus_sqrt", r.ra, xr)
        job(f"{L}.ffn.bias", r.rb, np.asarray(rt["scores"], F), np.asarray(rt["bias"], F))
    # ---- SW (shared, routed): one padded vector per expert
    W = sh["SW_W"]
    lim = F(s["limit"])
    lo, hi = DIE * ROWS_DIE, (DIE + 1) * ROWS_DIE

    def sw(name, ex, routed, from_rw=False):
        g = np.zeros(len(ex) * W, F)
        u = np.zeros(len(ex) * W, F)
        for v, e in enumerate(ex):
            g[v * W:v * W + ROWS_DIE] = np.asarray(e["g"], F)[lo:hi]
            u[v * W:v * W + ROWS_DIE] = np.asarray(e["u"], F)[lo:hi]
        wv = np.asarray([e["weight"] if routed else 1.0 for e in ex], F)
        act = SWG.golden_swiglu(g, u, np.repeat(wv, W).astype(F), lim)
        chk[f"{name} act == golden expert a"] = all(
            same(act[v * W:v * W + ROWS_DIE], np.asarray(e["a"], F)[lo:hi]) for v, e in enumerate(ex))
        job(name, r.sw, g, u, wv, lim, weights_from_rw=from_rw)
    ex_r = [e for e in s["experts"] if e["weight"] is not None]
    ex_s = [e for e in s["experts"] if e["weight"] is None]
    assert len(ex_r) >= 1 and len(ex_s) == 1, (len(ex_r), len(ex_s))      # 6 routed (backbone) / 3 (DSpark)
    sw(f"{L}.ffn.shared_swiglu", ex_s, False)
    # routed: its routing weights come from the RW job (ffn.weights, F11) written into its descriptor at run time
    rw_fits = router_fits and len(ex_r) <= 8
    sw(f"{L}.ffn.quant2", ex_r, True, from_rw=rw_fits)
    if rw_fits:
        w_rw = job(f"{L}.ffn.weights", r.rw, np.asarray(rt["scores"], F), list(rt["ids"]), F(s["route_scale"]), r.sw_desc)
        chk["RW weights == golden route weights"] = same(w_rw, np.asarray(rt["weights"], F))
    for name, arg in su.arg.items():
        if name not in footprints:
            kind = next(kind for kind, code in su.SG.K.items() if code == (arg >> 20))
            footprints[name] = footprint(kind, arg, r.vm, r.sh, {})
    assert all(chk.values()), {k: v for k, v in chk.items() if not v}
    alias = {}
    for tail, (_k, al) in JOBS.items():
        if f"{L}.{tail}" in su.arg:
            for x in al:
                alias[f"{L}.{x}"] = f"{L}.{tail}"
    return dict(run=r, arg=su.arg, alias=alias, footprints=footprints, compressor_outputs=compressor_outputs,
                vm=dict(r.vm), exp=dict(r.exp), jexp=jexp, checks=chk, T=T,
                softmax_fits=sm_ok, qb_fits=qb_ok, router_fits=router_fits, rw=rw_fits, top=r.top,
                sw_fit=dict(lanes=W, rows_per_expert=ROWS_DIE, lane_ratio=round(W / ROWS_DIE, 3)))
