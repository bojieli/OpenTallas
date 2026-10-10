#!/usr/bin/env python3
"""DeepSeek-V4.1-Flash DSpark MTP on the generic HBM die: the compiler's KERNEL bodies (G23 entries, G26 per-layer
bodies) in native HGI-1 unit ops, their execution on the hgi_sim machine (96 dies) under the shipped DSpark launch
expansion (tools/gpu_sys/v41_dspark.py expand), and the golden of one verify step.

THE KERNELS (DYN at a KERNEL doorbell: TOKEN = the launch's token, POS = its pos; the CP translator owns L'):
  swapin  (kind 0, token = slot c, pos = L)   slot c of the column store (HBM COLB + c * CSTR, dyn_sel TOKEN) ->
          the layer working buffers: h (4 x 5,120 FP32 residual copies), PRE (the pre mix), SELIDX (the index
          selection, 2,048 U32), CANDM (the layer-20 candidate table, 2 x 2,048): four DMA.LOAD
  swapout (kind 1, token = slot c, pos = n + c)   the same four buffers back to slot c: four DMA.STORE
  embed   (kind 2, token = t, pos = n + c)    h <- the BF16 embedding row of t in every residual copy (DMA.LOAD with
          dyn_sel TOKEN over the BF16 table, converted at the load), PRE <- (1, 0, 0, 0) from the table ONE4
  layer   (kind 3, per layer L at kent[3] + L * kstride)   ds_native's lowering of layer L made POSITION-GENERIC:
          RoPE row = ROPEB + POS * 256 (dyn_sel POS), window ring n = DYN 16 (WIN = min(pos + 1, 128), the spec's
          first DS selector; ring slot (POS1 - WIN) mod 128) on ATT.QK / ATT.PV B and on every score-row operand
          (SC / E / EB / MB), KV append slot POS mod 128 (DMA.KVWB_DS, already POS-driven).  Built for the sliding
          layers without Engram (L0, the bench's real layer); others: see LIMITS.
  head    (kind 4, token 0, pos = n + c, after swapin(c, 63))   final hc_pre + norm, the LM head (SM, 1,347-row
          shards) streamed into ARGMAX.LOCAL, COLL.ARGMAX_MERGE, CTL.END reads the merged id (TOK + 4).
  seed / demb / dsa / dsb / dhead / markov (kinds 5..10)   NOT LOWERED (LIMITS): END-only bodies.

Bench variants of the image (--stub-head): other layers END-only, head = END reading the golden argmax table
HT[POS] (dyn_sel POS) that the export plants in VM -- the die bench's head stub.

ROLLBACK (commit n <- n + 1 + a is the only action; v41_dspark notes):
  * position-indexed and safe: window ring (slot POS mod 128, rows of rejected positions are rewritten before the
    ring can read them: a read at pos p takes slots of positions p - 127 .. p, all < n after commit + rewritten by
    the next pass first); RoPE rows (read-only); DSpark rows (by position); the head table (stub, read-only).
  * column slots: written by swapout of the pass, read by swapin of the same pass only: no cross-pass state.
  * compressor (KV-source layers 2/8/14/20): the open group is POSITION-INDEXED only with SLOT_RING (v41_dspark
    H.SLOT_RING); ds_native today keeps it as a host table (SLOTKV / SLOTSC, compiled per position) and APPENDS the
    compressed row at group n_prev (compile-time) -- a rejected position that closes a group would leave a row the
    next pass must overwrite at the same group index: safe only if the append address is POS-derived
    (group = POS div r), which the position-generic lowering of those layers must do (open item G27).
  * indexer key store (IKSTORE, the compressed rows' index keys): same append rule as the compressor.
  * Engram (layers 1, 14): ids hashed from the token HISTORY; the history ring is position-indexed in the
    controller (tw_pos = n + j), so a rejected draft's token is overwritten at its position before any read; the
    die's hash engine must read the ring at POS, not keep a running history (spec 10.x Engram row says it restores
    on accept): hazard if it keeps state -- open item.

LIMITS (stubbed units, owner hgi-1010/h): layer bodies L >= 1 (Engram ids host-provided per token, compressor /
indexer addresses compile-time per position), the DSpark kinds 5..10 (no full-shape lowering of mtp.0-2: main_proj,
the stage blocks, the Markov head).

    NPY_DISABLE_CPU_FEATURES=... HDC_V41_ARITH=chunk8 python3 -m hgi_sim.ds_mtp_kernels golden --out DIR
    ... python3 -m hgi_sim.ds_mtp_kernels sim --golden DIR --out DIR [--export DIR]
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

F = np.float32
KINDS = ("swapin", "swapout", "embed", "layer", "head", "seed", "demb", "dsa", "dsb", "dhead", "markov")
PER_LAYER = {3: 40, 7: 3, 8: 3}       # G26: kinds with one body per layer / draft stage
L_NONE = 63
PMAX, BLK = 8, 5
NCOLSLOT = PMAX + BLK
DYN_WIN = 16                          # spec 6.8: the first DS selector = WIN = min(pos + 1, 128) (ot_hgi_seq dsq[16])


def npy_check():
    feats = getattr(np, "_core", np.core)._multiarray_umath.__cpu_features__
    if feats.get("AVX512F"):
        raise SystemExit("set NPY_DISABLE_CPU_FEATURES (numpy AVX512 float64 trig differs from the reference)")


# =================================================================================================================
# golden: one DSpark verify step of the released model from position 0 (forced drafter)
# =================================================================================================================
def golden(a):
    """Prefill p0 at position 0 -> y; forced drafts d_1..d_c = the AR continuation, d_{c+1} = t_c + 1 (corrupted),
    later drafts = the DSpark noise token; verify columns at positions 1 .. g+1 with tokens [y, d_1 .. d_g].
    Positions run one at a time (AR order); --layer-major re-runs the verify set as ONE layer-major pass
    (Model.forward_positions' order) from the post-prefill state and requires bit equality (the golden's identity)."""
    npy_check()
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ck = LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=True)
    vocab = int(m.c["vocab_size"])
    log = open(out / "golden.log", "a")

    def say(s):
        print(s, flush=True)
        log.write(s + "\n")
        log.flush()
    say(f"model built {time.time() - t0:.0f} s")

    def emb(t):
        return np.repeat(ck.rows("embed.weight", [t]), m.hc, axis=0).astype(F)

    def drop_experts(L=None):
        """bounded memory: a layer's weights are read once per position (golden_token's rule)"""
        for k_ in [k_ for k_ in m.w if ".ffn.experts." in k_ or (L is not None and k_.startswith(f"layers.{L}."))]:
            del m.w[k_]

    def head(ctx):
        xf = V.rmsnorm_fold(m.hc_pre(ctx["h"], ctx["pre"]), m.w["norm.weight"], m.eps)
        return V.mv(m.w["head.weight"], xf)

    def new_ctx(t, p, state):
        return {"pos": p, "hist": list(state["tokens"]), "h": emb(t), "pre": np.array([1, 0, 0, 0], dtype=F)[:m.hc]}

    def run_ar(t, p, state, rec):
        state["tokens"].append(int(t))
        ctx = new_ctx(t, p, state)
        tr = {}
        for L in range(m.L):
            tl = time.time()
            if L == 0:
                rec["h_in"] = ctx["h"].copy()
            m.layer(L, ctx, state, tr if L == 0 else None)
            drop_experts(L)
            if L == 0:
                rec["h0"], rec["pre0"] = ctx["h"].copy(), ctx["pre"].copy()
                rec["experts0"] = list(map(int, tr.get("L0.experts", [])))
            if L % 10 == 0:
                say(f"  pos {p} L{L:02d} {time.time() - tl:.1f} s")
        lg = head(ctx)
        rec.update(pos=p, token=int(t), argmax=int(np.argmax(lg)), margin=float(V.margin(lg)),
                   logits_sha256=LC.digest(lg))
        return lg

    gamma, c = a.gamma, a.corrupt
    state = m.new_state()
    recs = []
    r = {}
    lg = run_ar(a.p0, 0, state, r)
    recs.append(r)
    y = r["argmax"]
    say(f"pos 0 token {a.p0} -> y {y} ({time.time() - t0:.0f} s)")
    post_prefill = copy.deepcopy(state)
    toks, drafts, targets = [y], [], []
    for j in range(gamma + 1):                   # verify column j at position 1 + j
        r = {}
        run_ar(toks[j], 1 + j, state, r)
        recs.append(r)
        targets.append(r["argmax"])
        if j < gamma:
            if j < c:
                d = r["argmax"]                  # the AR continuation
            elif j == c:
                d = (r["argmax"] + 1) % vocab    # corrupted: accept stops here
            else:
                d = m.noise_id
            drafts.append(d)
            toks.append(d)
        say(f"pos {1 + j} token {toks[j]} -> {r['argmax']} margin {r['margin']:.3f} ({time.time() - t0:.0f} s)")
    acc = 0
    while acc < len(drafts) and drafts[acc] == targets[acc]:
        acc += 1
    emitted = [y] + targets[:acc + 1]
    np.savez_compressed(out / "golden_l0.npz", **{f"{k}{i}": np.asarray(v) for i, rr in enumerate(recs)
                                                    for k, v in rr.items() if k in ("h_in", "h0", "pre0")})
    summ = dict(schema="opentallas.hgi_sim.ds_mtp_golden.v1", model="DeepSeek-V4.1-Flash (released checkpoint, "
                "hdc_golden_v41 HDC_V41_ARITH=chunk8 via rtl_v41_fullshape_layer_campaign.build_model)",
                p0=a.p0, gamma=gamma, corrupt=c, noise=m.noise_id, prompt=[a.p0], y=y, verify_tokens=toks,
                drafts=drafts, targets=targets, accepted=acc, emitted=emitted,
                positions=[dict({k: v for k, v in rr.items() if k not in ("h_in", "h0", "pre0")},
                                h0_sha256=LC.digest(rr["h0"]), pre0_sha256=LC.digest(rr["pre0"])) for rr in recs],
                order="AR (one position at a time)", init_sha=init_sha, golden=LC.golden_pin(),
                wall_s=round(time.time() - t0, 1))
    (out / "golden.json").write_text(json.dumps(summ, indent=1) + "\n")
    say(f"AR done: y {y} drafts {drafts} targets {targets} accept {acc} emitted {emitted}")
    if a.layer_major:
        st = post_prefill
        st["tokens"].extend(int(t) for t in toks)
        ctxs = []
        for j, t in enumerate(toks):
            cx = {"pos": 1 + j, "hist": st["tokens"][:2 + j], "h": emb(t),
                  "pre": np.array([1, 0, 0, 0], dtype=F)[:m.hc]}
            ctxs.append(cx)
        l0 = []
        for L in range(m.L):
            for cx in ctxs:
                m.layer(L, cx, st)
            drop_experts(L)
            if L == 0:
                l0 = [(cx["h"].copy(), cx["pre"].copy()) for cx in ctxs]
            say(f"  layer-major L{L:02d} ({time.time() - t0:.0f} s)")
        lm = [int(np.argmax(head(cx))) for cx in ctxs]
        same_l0 = all(np.array_equal(h_.view(np.uint32), recs[1 + j]["h0"].view(np.uint32)) and
                      np.array_equal(p_.view(np.uint32), recs[1 + j]["pre0"].view(np.uint32))
                      for j, (h_, p_) in enumerate(l0))
        summ["layer_major"] = dict(argmax=lm, argmax_equal_ar=lm == targets, l0_bit_equal_ar=bool(same_l0),
                                   wall_s=round(time.time() - t0, 1))
        (out / "golden.json").write_text(json.dumps(summ, indent=1) + "\n")
        say(f"layer-major: argmax {lm} equal {lm == targets} L0 bit-equal {same_l0}")
    return 0



# =================================================================================================================
# the kernels
# =================================================================================================================
EMBB = 1 << 32                       # BF16 embedding rows: EMBB + token * 10,240 (dyn_sel TOKEN)
MTB = 0x170000000                    # MTP constants (ONE4 = 1, 0, 0, 0)
COLB = 0x180000000                   # column slot store: COLB + slot * CSTR (dyn_sel TOKEN)
ROPEB = 1 << 31                      # plain RoPE rows: ROPEB + pos * 256 (cos 32 | sin 32, dyn_sel POS)
ZT, HT = 261120, 261184              # VM: the END token word of non-head kernels (0); the head stub's table HT[pos]
SLOT = (("h", 0, 20480), ("PRE", 81920, 4), ("SELIDX", 81952, 2048), ("CANDM", 90144, 4096))
CSTR = 1 << 17
ATT_TAGS = ("attend.qk", "attend.max", "attend.exp_sum", "attend.bf16_p", "attend.pv")


class Kernels:
    """Per-rank kernel bodies (record lists, every body ends with CTL.END) and rank r's G23 / G26 image."""

    def __init__(self, m, stub_head=True, layers_real=(0,)):
        from hgi_sim import ds_native as DN
        from hgi_sim.records import MDesc, Rec
        from hgi_sim.qwen_compiler import Builder
        import w19_hbm_tp96_isa as W
        self.DN, self.W, self.MDesc, self.Rec, self.Builder = DN, W, MDesc, Rec, Builder
        self.m, self.TP = m, DN.TP
        self.lay, self.man = DN.Layout(), DN.Manifest()
        assert self.lay.end <= ZT and HT + 64 <= DN.MC.VM_WORDS
        self.low = DN.Lower(m, 1, self.lay, self.man)
        self.ops = {}
        self.body = {r: {} for r in range(self.TP)}       # (kind, L') -> [Rec]
        for k in range(len(KINDS)):
            for Lp in range(PER_LAYER.get(k, 1)):
                for r in range(self.TP):
                    self.body[r][(k, Lp)] = [self.end()]
        for r in range(self.TP):
            self.body[r][(0, 0)] = self.swap(True)
            self.body[r][(1, 0)] = self.swap(False)
            self.body[r][(2, 0)] = self.embed()
            if stub_head:
                self.body[r][(4, 0)] = [self.end(HT, POS=True)]
        for L in layers_real:
            for r, recs in enumerate(self.layer(L)):
                self.body[r][(3, L)] = recs + [self.end()]

    # ---- records
    def end(self, base=ZT, POS=False):
        A = self.MDesc(space="VM", fmt="U32", base=base, n=1, dyn_sel=1 if POS else 0, dyn_mul=1 if POS else 0)
        return self.Rec("CTL", "END", wait=0xFFFE, desc=dict(A=A), tag="end" + (".head_stub" if POS else ""))

    def swap(self, into):
        b = self.Builder(None)
        for nm, off, n in SLOT:
            hb = self.MDesc(space="HBM", fmt="FP32", base=COLB + off, n=n, dyn_sel=3, dyn_mul=CSTR)
            vm = self.MDesc(space="VM", fmt="FP32", base=self.lay.vm[nm], n=n)
            if into:
                b.add(self.Rec("DMA", "LOAD", desc=dict(A=hb, O=vm), tag=f"swapin.{nm}", family="swap"), [], [nm])
            else:
                b.add(self.Rec("DMA", "STORE", desc=dict(A=vm, O=hb), tag=f"swapout.{nm}", family="swap"),
                      [nm], [f"COL.{nm}"])
        return b.recs + [self.end()]

    def embed(self):
        b = self.Builder(None)
        for j in range(4):
            b.add(self.Rec("DMA", "LOAD", desc=dict(
                A=self.MDesc(space="HBM", fmt="BF16", base=EMBB, n=5120, dyn_sel=3, dyn_mul=10240),
                O=self.MDesc(space="VM", fmt="FP32", base=self.lay.vm["h"] + 5120 * j, n=5120)),
                tag=f"embed.h{j}", family="embed"), [], [f"h{j}"])
        b.add(self.Rec("DMA", "LOAD", desc=dict(A=self.MDesc(space="HBM", fmt="FP32", base=MTB, n=4),
                                                 O=self.MDesc(space="VM", fmt="FP32", base=self.lay.vm["PRE"], n=4)),
                       tag="embed.pre", family="embed"), [], ["PRE"])
        return b.recs + [self.end()]

    def layer(self, L):
        """ds_native's layer L for every rank, made position-generic (sliding layers without Engram)."""
        DN, m = self.DN, self.m
        assert m.ratio[L] == 0 and L not in m.engram.layer_ids, "position-generic lowering: sliding, no Engram"
        ops = self.W.Compiler(m, 1, DN.VARIANT).compile_layer(L, first=True)
        for op_ in ops:
            self.ops[f"{L}:{op_.get('id')}"] = op_
        rank_recs = [self.low.layer(L, ops, r) for r in range(self.TP)]
        DN.POS_DEFAULT[0] = 1
        rank_recs, _ = DN.schedule_layer(rank_recs, ops, L)
        rope_old = DN.TBASE + DN.TABLE_OFF["ROPE"]
        for recs in rank_recs:
            for r in recs:
                for k_, d in list(r.desc.items()):
                    if d.space == "HBM" and d.base == rope_old:
                        r.desc[k_] = dataclasses.replace(d, base=ROPEB, dyn_sel=1, dyn_mul=256)
                    elif r.tag in ATT_TAGS and d.n == 128:
                        r.desc[k_] = dataclasses.replace(d, n_sel=DYN_WIN)
        return rank_recs

    # ---- the image of rank r (G23 entries, G26 stride), 16-byte units from the image start
    def image(self, r):
        from hgi_sim.records import encode_program
        out = bytearray(16)                                # unit 0 unused: a kernel entry of 0 = absent
        ar = len(out) // 16
        out += encode_program([self.end()])
        kent = [0] * len(KINDS)
        ks = max(len(encode_program(self.body[r][(3, L)])) for L in range(PER_LAYER[3])) // 16
        ks = max(ks, max(len(encode_program(self.body[r][(k, Lp)])) // 16 for k, n in PER_LAYER.items()
                         for Lp in range(n)))
        where = {}
        for k in range(len(KINDS)):
            kent[k] = len(out) // 16
            for Lp in range(PER_LAYER.get(k, 1)):
                blob = encode_program(self.body[r][(k, Lp)])
                where[(k, Lp)] = (len(out), len(blob))
                out += blob
                if k in PER_LAYER:
                    out += bytes(ks * 16 - len(blob))
        return bytes(out), ar, kent, ks, where


class Machine2:
    """the hgi_sim Machine with the DS selector DYN 16 (WIN) set at the doorbell (spec 6.8; ot_hgi_seq dsq[16])"""

    @staticmethod
    def make(MC, dies, units):
        class M(MC.Machine):
            def doorbell(self, token, pos, slot_count=1):
                super().doorbell(token, pos, slot_count)
                for d in self.dies:
                    d.dyn[DYN_WIN] = min(pos + 1, 128)
        return M(dies, units)


def patch_timing_dyn():
    from hgi_sim import timing as T
    if getattr(T.Dyn, "_mtp", False):
        return

    class Dyn(T.Dyn):
        _mtp = True

        def __init__(self, pos, token=0, rank=0):
            super().__init__(pos, token, rank)
            self.v[15], self.v[DYN_WIN] = pos + 1, min(pos + 1, 128)
    T.Dyn = Dyn


class Engine:
    """The CP translator + KERNEL doorbells on the simulator: a DSpark command -> v41_dspark.expand launches; L' of a
    per-layer kind = the position field of the column's preceding swapin (G26)."""

    def __init__(self, K, Mach, units, timing=True):
        self.K, self.M, self.units = K, Mach, units
        self.Lp = 0
        self.launches, self.trace = [], []
        self.timing = timing
        self.on_launch = None

    def launch(self, kind, tok, pos):
        DN = self.K.DN
        k = KINDS.index(kind)
        if k == 0:
            self.Lp = pos if pos < 40 else (pos - 40 if pos != L_NONE else 0)
        Lp = self.Lp if k in PER_LAYER else 0
        progs = [self.K.body[d.rank][(k, Lp)] for d in self.M.dies]
        t0 = time.time()
        DN.run_per_die(self.M, progs, self.units, pos, tok)
        end = progs[0][-1]
        res = int(self.M.dies[0].vm[end.desc["A"].base + (pos if end.desc["A"].dyn_sel == 1 else 0)])
        self.launches.append(dict(kind=kind, k=k, Lp=Lp, token=int(tok), pos=int(pos), result=res,
                                  records=sum(1 for r in progs[0] if r.unit != "CTL"), wall_s=round(time.time() - t0, 2)))
        if self.on_launch:
            self.on_launch(self.launches[-1])
        return res

    # the v41_dspark Engine interface (ctl_loop drives it)
    def run(self, cmd, want_logits=False):
        import v41_dspark as V41D
        res = []
        for kind, tok, pos in V41D.expand(cmd):
            r = self.launch(kind, tok, pos)
            if kind in ("head", "markov"):
                res.append(r)
        return res, [None] * len(res)


def sim(a):
    """Build the kernels, run one DSpark job (prefill p0 + one verify step) on 96 simulated dies through the shipped
    control loop (v41_dspark.ctl_loop, forced drafter = the golden's drafts), check every column's L0 output against
    the golden and the accepted stream against the golden's; optionally export the die-bench vehicle."""
    npy_check()
    sys.path.insert(0, str(TOOLS / "gpu_sys"))
    import v41_dspark as V41D
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    from types import SimpleNamespace
    from hgi_sim import ds_native as DN
    from hgi_sim import machine as MC
    import w19_hbm_tp96_isa as W
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    gd = json.loads((Path(a.golden) / "golden.json").read_text())
    gz = np.load(Path(a.golden) / "golden_l0.npz")
    t0 = time.time()
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    TP = DN.TP
    # per-die HBM: L0 tables (empty window ring), RoPE rows, embedding rows of the job's tokens, constants, slots
    st0 = SimpleNamespace(win={0: np.zeros((m.window - 1, m.hd), F)}, slots={})
    tabs = [DN.build_tables(m, st0, 0, 0, r) for r in range(TP)]        # (sets TABLE_OFF before the lowering)
    K = Kernels(m)
    npos = 1 + len(gd["verify_tokens"])
    rope = np.zeros((npos, 64), F)
    for p in range(npos):
        cs, sn = V.rope_cs(m.freqs_plain, p)
        rope[p] = np.concatenate([cs, sn])
    toks = sorted(set([gd["p0"]] + gd["verify_tokens"]))
    raw = {t: np.asarray(ck.raw("embed.weight")[0]).reshape(129280, 10240)[t].copy() for t in toks}
    dies = [MC.Die(r, MC.Hbm()) for r in range(TP)]
    for d in dies:
        d.rk = W.Rank(d.rank)
        d.hbm.add(DN.TBASE, tabs[d.rank], "TABLES")
        d.hbm.add(ROPEB, rope.view(np.uint8).reshape(-1).copy(), "ROPE_ROWS")
        d.hbm.add(MTB, np.array([1, 0, 0, 0], F).view(np.uint8).copy(), "MTP_CONST")
        d.hbm.add(COLB, np.zeros(NCOLSLOT * CSTR, np.uint8), "COLSLOTS")
        for t in toks:
            d.hbm.add(EMBB + t * 10240, raw[t].copy(), f"EMB{t}")
        d.vm[ZT] = 0
        d.vm[HT:HT + npos] = [gd["positions"][p]["argmax"] for p in range(npos)]
    golib = W.Executor(m, None, 1, [], DN.VARIANT)
    units = DN.ds_units(m, K.man, golib)
    Mach = Machine2.make(MC, dies, units)
    cap = None
    if a.export:
        from hgi_e2e import export as EX
        cap = EX.Capture(Mach, dies[0])
        regions0 = list(dies[0].hbm.regions)
        snap0 = {id(dat): dat.copy() for b_, dat, nm in regions0}
        vm0 = dies[0].vm.copy()
        units = {k_: cap.wrap(k_, fn) for k_, fn in units.items()}
    eng = Engine(K, Mach, units)
    col_out = {}

    def on_launch(e):
        if e["kind"] == "swapout" and K_cur["L"] == 0:
            c = e["token"]
            hs = []
            for d in dies:
                v = d.hbm.view(COLB + c * CSTR, 81952).view(np.uint32)
                hs.append(v.copy())
            col_out[e["pos"]] = hs
        if e["kind"] == "swapin":
            K_cur["L"] = e["pos"]
    K_cur = {"L": -1}
    eng.on_launch = on_launch
    plen = len(gd["prompt"])
    forced_d = gd["drafts"]

    def forced(step, y, q, g):
        assert step == 0 and g == len(forced_d)
        return list(forced_d)
    eng.prog = SimpleNamespace(m=SimpleNamespace(L=m.L))
    ngen = len(gd["emitted"])
    tok, _, steps = V41D.ctl_loop(eng, gd["prompt"], ngen, gd["gamma"], forced, maxpos=1 << 20)
    # (A) every column's L0 output (slot after swapout) == the golden's L0 output at that position, every rank
    colres = []
    for p in sorted(col_out):
        want = np.concatenate([gz[f"h0{p}"].reshape(-1).view(np.uint32), gz[f"pre0{p}"].view(np.uint32)])
        got = col_out[p]
        ok = all(np.array_equal(g_[:20480], want[:20480]) and np.array_equal(g_[20480:20484], want[20480:]) for g_ in got)
        nbad = int(np.count_nonzero(got[0][:20484] != want))
        colres.append(dict(pos=p, kind="prefill" if p < plen else "verify", bit_exact_all_ranks=bool(ok),
                           rank0_words_differing=nbad))
    accept_ok = tok == gd["emitted"] and steps and steps[0]["drafts"] == gd["drafts"] and \
        steps[0]["targets"] == gd["targets"] and steps[0]["accepted"] == gd["accepted"]
    # (C) timing: the simulator's S2 cycles of every launch body (rank 0), and per L0 record
    patch_timing_dyn()
    from hgi_sim import timing as T
    from hgi_sim.ds_native_timing import NativeCost
    costs, t_launch = [], 0.0
    per_launch = []
    cache = {}
    for e in eng.launches:
        body = K.body[0][(e["k"], e["Lp"])]
        key = (e["k"], e["Lp"], e["pos"], e["token"])
        if key not in cache:
            for r in body:
                if not hasattr(r, "src_key0"):        # (NativeCost.walk replaces r.src by its own record)
                    sr = getattr(r, "src", None)
                    r.src_key0 = None if not sr else f"{sr[0]}:{sr[1]}"
                r.src_key = r.src_key0
                r.src_extra = []
                r.layer = e["Lp"]
            sch = T.schedule(body, e["pos"], "S2", token=e["token"], cost_fn=NativeCost(K.ops, body))
            cache[key] = sch
        sch = cache[key]
        for i, (k_, L_, L1_) in enumerate(sch["ex"]):
            if body[k_].unit == "CTL":
                continue
            costs.append(dict(cost=round(float(sch["costs"][i][0]), 1), cost_how=sch["costs"][i][2],
                              s2_disp=round(t_launch + sch["disp"][i], 1), s2_start=round(t_launch + sch["start"][i], 1),
                              s2_end=round(t_launch + sch["end"][i], 1)))
        per_launch.append(dict(e, s2_cycles=round(sch["total_cycles"], 1), s2_start=round(t_launch, 1)))
        t_launch += sch["total_cycles"]
    l0 = [x for x in per_launch if x["kind"] == "layer" and x["Lp"] == 0]
    rec = dict(schema="opentallas.hgi_sim.ds_mtp_sim.v1", golden=str(a.golden), golden_summary={
                   k_: gd[k_] for k_ in ("prompt", "y", "verify_tokens", "drafts", "targets", "accepted", "emitted")},
               machine_tokens=tok, steps=steps, accept_stream_equals_golden=bool(accept_ok),
               l0_columns=colres, l0_all_bit_exact=all(c["bit_exact_all_ranks"] for c in colres),
               launches=len(eng.launches), s2_job_cycles=round(t_launch, 1),
               s2_l0_cycles=[x["s2_cycles"] for x in l0], l0_records=K and len([r for r in K.body[0][(3, 0)] if r.unit != "CTL"]),
               kernel_records={KINDS[k_]: len(K.body[0][(k_, 0)]) for k_ in range(len(KINDS))},
               stubbed=["layer bodies L1..L39 (END only)", "head (END reads golden argmax HT[POS])",
                        "seed / demb / dsa / dsb / dhead / markov (END only; forced drafter)"],
               wall_s=round(time.time() - t0, 1),
               source_sha256={p_: hashlib.sha256((TOOLS / p_).read_bytes()).hexdigest() for p_ in (
                   "hgi_sim/ds_mtp_kernels.py", "hgi_sim/ds_native.py", "hgi_sim/machine.py", "hgi_sim/records.py",
                   "gpu_sys/v41_dspark.py", "hdc_golden_v41.py")})
    (out / "sim.json").write_text(json.dumps(rec, indent=1, default=int) + "\n")
    (out / "launches.json").write_text(json.dumps(per_launch, indent=0, default=int) + "\n")
    print(f"accept stream {'== golden' if accept_ok else 'DIFFERS'} {tok}; L0 columns "
          f"{[(c['pos'], c['bit_exact_all_ranks']) for c in colres]}; launches {len(eng.launches)} S2 {t_launch:.0f}")
    if cap is not None:
        export_bench(a, K, cap, dies[0], regions0, snap0, vm0, costs, gd, rec)
    return 0 if accept_ok and rec["l0_all_bit_exact"] else 1


def export_bench(a, K, cap, die0, regions0, snap0, vm0, costs, gd, simrec):
    """The die-bench vehicle (tools/hgi_e2e/run.py layout): rank 0's image with the G23 / G26 kernel table, the
    global dispatch order of the whole job (every launch's records), per record its golden writes and S2 cost."""
    from hgi_e2e import export as EX
    import hbm_generic_iface as HGI
    out = Path(a.export)
    out.mkdir(parents=True, exist_ok=True)
    img, ar, kent, ks, where = K.image(0)
    assert len(costs) == len(cap.recs), (len(costs), len(cap.recs))
    for e, c in zip(cap.recs, costs):
        e.update(c)
    md = dict(magic=HGI.MAGIC, ver_minor=HGI.D_VERSION[1], ver_major=HGI.D_VERSION[0], n_words=HGI.NWORDS,
              cp_vocab=129280, cp_ctx_max=1 << 20, coll_group_size=96, entry_ar=ar, image_base=EX.IMAGE_PAGE,
              image_pages=-(-len(img) // 4096) + 1, mtp_kstride=ks, **{f"mtp_kernel_{k}": kent[k] for k in range(11)})
    words = HGI.d_pack(md)
    assert HGI.d_hw_check(words) == 0
    (out / "image.bin").write_bytes(img)
    (out / "image_e2e.bin").write_bytes(img)
    (out / "vm0.bin").write_bytes(vm0.astype("<u4").tobytes())
    (out / "vmw.bin").write_bytes(bytes(cap.vmw))
    (out / "hbmw.bin").write_bytes(bytes(cap.hbmw))
    (out / "vm_final.bin").write_bytes(die0.vm.astype("<u4").tobytes())
    for k_, parts in cap.coll.items():
        (out / f"coll_{k_}.bin").write_bytes(b"".join(p.astype("<u4").tobytes() for p in parts))
    with open(out / "hbm.bin", "wb") as f:
        for lo, hi in EX.merge(cap.touch):
            f.write(EX.struct.pack("<QQ", lo, hi - lo) + EX.region_bytes(regions0, snap0, lo, hi - lo))
    meta = dict(schema="opentallas.hgi_e2e.export_mtp.v1", model="DeepSeek-V4.1-Flash", vehicle="ds_mtp_L0_verify",
                rank=0, group=96, md_words=words, records=cap.recs, image_bytes=len(img), kent=kent, kstride=ks,
                entry_ar=ar, image_base_bytes=EX.IMAGE_PAGE * 4096, image_sha256=hashlib.sha256(img).hexdigest(),
                golden=simrec["golden_summary"], sim=dict(s2_job_cycles=simrec["s2_job_cycles"],
                                                         s2_l0_cycles=simrec["s2_l0_cycles"]), needs_end=False)
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=int) + "\n")
    # recs.txt / prep.txt / host.mem for tb_hgi_e2e MTP=1 (run.py prep's format; host words below the md words)
    sys.argv = ["x"]
    from hgi_e2e import run as RUN
    lines = []
    from hgi_sim.records import OPS
    import re
    for r in cap.recs:
        h = int(r["hdr"], 16)
        hw = [(h >> (32 * i)) & 0xFFFFFFFF for i in (3, 2, 1, 0)]
        ops = []
        for nm in RUN.OPND:
            e = r["eff"].get(nm)
            ops.append(f"1 {e[0] & ((1 << 40) - 1):x} {e[1] & ((1 << 21) - 1)}" if e else "0 0 0")
        tag = re.sub(r"[^A-Za-z0-9_.+:-]", "_", r["tag"] or "-")[:120]
        lines.append(f"{r['k']} {RUN.UNITS.index(r['unit'])} {OPS[r['unit']].index(r['op'])} " +
                     " ".join(f"{x:08x}" for x in hw) + " " + " ".join(ops) +
                     f" {r.get('cost', 1)} {r['vm_off']} {r['vm_n']} {r['hbm_off']} {r['hbm_n']} "
                     f"{r.get('s2_disp', 0)} {r.get('s2_start', 0)} {r.get('s2_end', 0)} {tag}")
    (out / "recs.txt").write_text("\n".join(lines) + "\n")
    (out / "prep.txt").write_text(f"{EX.IMAGE_PAGE * 4096} image_e2e.bin\n0\n")
    g = gd
    host = list(words) + [0] * 64
    em = g["emitted"]
    host[64:72] = [len(g["prompt"]), g["gamma"], len(em), 0, 1 + len(g["verify_tokens"]), 1 << 20, len(em),
                   1 + g["accepted"] + 1 + len(g["prompt"]) - 1]
    for i, t in enumerate(g["prompt"][:8]):
        host[72 + i] = t
    for i, t in enumerate(g["drafts"][:8]):
        host[80 + i] = t
    for i, t in enumerate(em[:8]):
        host[88 + i] = t
    (out / "host.mem").write_text("\n".join(f"{x & 0xFFFFFFFF:08x}" for x in host) + "\n")
    print(f"export {out}: {len(lines)} dispatched records, image {len(img)} B (kstride {ks}, kent {kent})")

# =================================================================================================================
# main
# =================================================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("golden")
    g.add_argument("--out", required=True)
    g.add_argument("--p0", type=int, default=0)
    g.add_argument("--gamma", type=int, default=4)
    g.add_argument("--corrupt", type=int, default=2)
    g.add_argument("--layer-major", action="store_true")
    q = sp.add_parser("sim")
    q.add_argument("--golden", required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--export")
    a = ap.parse_args()
    if a.cmd == "golden":
        return golden(a)
    if a.cmd == "sim":
        return sim(a)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
