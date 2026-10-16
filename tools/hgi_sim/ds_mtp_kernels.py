#!/usr/bin/env python3
"""DeepSeek-V4.1-Flash DSpark MTP on the generic HBM die: the compiler's KERNEL bodies (G23 entries, G26 per-layer
bodies) in native HGI-1 unit ops, their execution on the hgi_sim machine (96 dies) under the shipped DSpark launch
expansion (tools/gpu_sys/v41_dspark.py expand), and the golden of one verify step.

THE KERNELS (DYN at a KERNEL doorbell: TOKEN = the launch's token, POS = its pos; the CP translator owns L'):
  swapin  (kind 0, token = slot c, pos = L)   slot c of the column store (HBM COLB + c * CSTR, dyn_sel TOKEN) ->
          the layer working buffers: h (4 x 5,120 FP32 residual copies), PRE (the pre mix): two DMA.LOAD
  swapout (kind 1, token = slot c, pos = n + c)   the same two buffers back to slot c: two DMA.STORE + FENCE
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


def f32u(x):
    return int(np.asarray(np.float32(x)).view(np.uint32))


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



def golden_spec(a):
    """The DSpark golden of one REAL-drafter step at full shape (Model.generate_spec semantics, prompt [p0], anchor 0):
    prefill p0 at position 0 (main hidden parts of layers 37..39 -> the seed: every stage's DSpark window row 0),
    y = argmax; draft(y, 0) (3 stages over the block [y, noise x 4], DLOG rows, the Markov argmax chain);
    verify [y, d_1 .. d_g] at positions 1 .. g+1 (one position at a time = the golden's own identity, checked by the
    AR run above), targets, accept, the verify columns' seeds.  Per position and layer the residual / pre after the
    layer (the die bench's labelled replay of layers 1..39) and the main hidden parts."""
    npy_check()
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ck = LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=True)
    log = open(out / "golden_spec.log", "a")

    def say(s_):
        print(s_, flush=True)
        log.write(s_ + "\n")
        log.flush()

    def drop(L=None):
        for k_ in [k_ for k_ in m.w if ".ffn.experts." in k_ or (L is not None and k_.startswith(m.P(L)))]:
            del m.w[k_]

    def emb(t):
        return np.repeat(ck.rows("embed.weight", [t]), m.hc, axis=0).astype(F)
    arrs = {}
    state = m.new_state(mtp=True)

    def run_pos(t, p):
        state["tokens"].append(int(t))
        ctx = {"pos": p, "hist": list(state["tokens"]), "h": emb(t), "pre": np.array([1, 0, 0, 0], dtype=F), "mh": []}
        for L in range(m.L):
            m.layer(L, ctx, state)
            arrs[f"h_{p}_{L}"] = ctx["h"].copy()
            arrs[f"pre_{p}_{L}"] = ctx["pre"].copy()
            drop(L)
        xf = V.rmsnorm_fold(m.hc_pre(ctx["h"], ctx["pre"]), m.w["norm.weight"], m.eps)
        lg = V.mv(m.w["head.weight"], xf)
        tr = {}
        m.dspark_seed(np.concatenate(ctx["mh"]), p, state, tr)
        arrs[f"mh_{p}"] = np.asarray(tr["main_hidden"], F)
        arrs[f"mainx_{p}"] = np.asarray(tr["main_x"], F)
        for st in range(m.n_mtp):
            arrs[f"dsk_{st}_{p}"] = np.asarray(state["dsk"][st][p], F)
        tok = int(np.argmax(lg))
        say(f"pos {p} token {t} -> {tok} ({time.time() - t0:.0f} s)")
        return tok
    y = run_pos(a.p0, 0)
    # the draft at anchor 0 (Model.draft, unrolled to keep every stage's rows)
    B, q = m.dspark_block, 0
    ids = [y] + [m.noise_id] * (B - 1)
    hs = [emb(t) for t in ids]
    pres = [np.array([1, 0, 0, 0], dtype=F) for _ in ids]
    for st in range(m.n_mtp):
        hs, pres = m.dspark_stage(m.L + st, hs, pres, q, state)
        for i in range(B):
            arrs[f"dh_{st}_{i}"], arrs[f"dpre_{st}_{i}"] = hs[i].copy(), pres[i].copy()
        drop(m.L + st)
        say(f"draft stage {st} ({time.time() - t0:.0f} s)")
    Lf = m.L + m.n_mtp - 1
    xh = [V.to_bf16(m.hc_pre(h, p_)) for h, p_ in zip(hs, pres)]
    logits = [V.mv(m.w["head.weight"], V.rmsnorm_bf16(x, m.lw(Lf, "norm.weight"), m.eps)) for x in xh]
    for i in range(B):
        arrs[f"dlog_{i}"] = np.asarray(logits[i], F)
    embm, mhead = m.lw(Lf, "markov_head.embed.weight"), m.lw(Lf, "markov_head.head.weight")
    d = [y]
    for i in range(B):
        lg = V.add(logits[i], V.mv(mhead, embm[d[i]]))
        d.append(int(np.argmax(lg)))
    drafts_all = d[1:]
    g = a.gamma
    drafts = drafts_all[:g]
    say(f"draft: {drafts_all} ({time.time() - t0:.0f} s)")
    toks = [y] + drafts
    targets = [run_pos(t, 1 + j) for j, t in enumerate(toks)]
    acc = 0
    while acc < g and drafts[acc] == targets[acc]:
        acc += 1
    emitted = [y] + targets[:acc + 1]
    np.savez_compressed(out / "golden_spec.npz", **arrs)
    summ = dict(schema="opentallas.hgi_sim.ds_mtp_golden_spec.v1", p0=a.p0, gamma=g, y=y, noise=m.noise_id,
                drafts_block=drafts_all, drafts=drafts, verify_tokens=toks, targets=targets, accepted=acc,
                emitted=emitted, prompt=[a.p0], drafter="dspark (real)",
                positions=[dict(pos=p, argmax=(y if p == 0 else targets[p - 1])) for p in range(1 + len(toks))],
                golden=LC.golden_pin(), init_sha=init_sha, wall_s=round(time.time() - t0, 1))
    (out / "golden_spec.json").write_text(json.dumps(summ, indent=1) + "\n")
    say(f"SPEC: y {y} drafts {drafts} targets {targets} accept {acc} emitted {emitted}")
    return 0


# =================================================================================================================
# the kernels
# =================================================================================================================
EMBB = 1 << 32                       # BF16 embedding rows: EMBB + token * 10,240 (dyn_sel TOKEN)
MTB = 0x170000000                    # MTP constants (ONE4 = 1, 0, 0, 0)
# Column slot store: STACK-LOCAL COLB + slot * CSTR (dyn_sel TOKEN) on ALL FOUR stacks (h rides the swap on stacks
# 0..3, PRE on stack 0), so the window must be free in every stack AND inside a stack's physical bytes.  It sits in
# ds_native's reserved DATA WINDOW (stack-local 20 GiB + 512 MiB on every stack; the weight manifest skips it), above
# the 256 MiB kept there for the HC stripe rows.
# It was 0x180000000 (stack-local 6 GiB): on stack 2 that is flat 70 GiB, INSIDE the weight manifest's address map
# (layers.0.ffn.experts.w2, expert 44, rows 4,098..4,881: measured 2026-10-13 with the vehicle's manifest) -- on the
# dies that own those rows every swap-out of rows o = 2 mod 4 wrote over weight rows.  The simulator could not see it
# (weights come from the checkpoint, the STRIPE4 code bit kept the address out of the manifest lookup) and neither
# could the e2e bench (SM is a stub there).  Kernels.check_colslot_window() proves the window against the manifest,
# the HC stripe rows and the stack capacity.  (A first move to stack-local 31 GiB faulted every RTL engine: above
# STACK_BYTES, suite s5.)
COLB = (20 << 30) + (256 << 20)
ROPEB = 1 << 31                      # plain RoPE rows: ROPEB + pos * 256 (cos 32 | sin 32, dyn_sel POS)
# VM tail above ds_native's buffer map (derived from DN.Layout().end at bind time, never hard-coded: the map grows --
# EGID 144 moved it to 261,440, rule (A)'s bank-phase-0 HC buffers to 261,696): ZT = the END token word of non-head
# kernels (0, 64-word slot); HT = the head stub's table HT[pos] (HT_N positions); QV = the WTAB row of the launch's
# position (16 words).  bind_vm_tail() sets them before any kernel / export uses them.
ZT = HT = QV = None
HT_N = 64


def bind_vm_tail():
    """Place ZT / HT / QV 64-word aligned right above the ds_native map end; refuse a map that leaves no room."""
    global ZT, HT, QV
    from hgi_sim import ds_native as DN
    end = DN.Layout().end
    ZT = -(-end // 64) * 64
    HT = ZT + 64
    QV = HT + HT_N
    assert QV + 16 <= DN.MC.VM_WORDS, (end, ZT, HT, QV, DN.MC.VM_WORDS)
    return ZT, HT, QV


# PRE rides the swap as one whole 32 B sector (8 words: the 4 pre-mix words + 4 words of the 64-word-aligned VM PRE
# slot): an HBM write is whole sectors (the DMA write paths have no byte enables; the mover refuses a partial sector)
SLOT = (("h", 0, 20480), ("PRE", 81920, 8))
# h rides the swap STRIPE4-coded (stack-interleaved in 256 B rows): every 32 consecutive VM sectors of h land on the four
# stacks, 8 each, so the swap streams at the DMA BACK / FRONT rate (4 stacks x 8 lanes x 32 B) instead of one stack's 8 lanes;
# per stack the rows are packed (row o at stack-local COLB + slot x CSTR + o x 64: stack s holds rows s, s + 4, ... 256 B apart)
SW, HSTRIPE = 64, 320
# The index selection (SELIDX) and the layer-20 candidate table (CANDM) are per-POSITION transients written by the
# index-source layers and read by later layers of the same position: they move to position-indexed rows (SELB / CANDB +
# (POS mod 16) * stride, written by the writer layer's body, loaded by the readers' bodies -- rollback-safe like the
# window ring) instead of riding every swap (they changed at 4 of 40 layers; 6,144 of 26,628 swapped words).  L0 reads
# neither.  VM residency of the columns: today's VM map ends at 261,056 of 262,144 words, so 0 columns of 20,484 words
# fit; the VM-512 macros (2 MiB physical, hgi-1010/f) would hold 12.
CSTR = 1 << 17
ATT_TAGS = ("attend.qk", "attend.max", "attend.exp_sum", "attend.bf16_p", "attend.pv")


TSTR = 1 << 24                       # per-layer table regions: TBASE + slot * TSTR (slot: L0 0, stages 1..3, seed 4)
TSLOT = {0: 0, 40: 1, 41: 2, 42: 3, "seed": 4}
DSKX = 0x190000000                   # per die, per stage (+ st * 1 MiB): rows by slot (2,048 B): the DSpark window ring
                                     # (slots 0..127, slot p mod 128) and this step's block rows at n_win + i
ROWQ = 0x1A0000000                   # per die: the block rows' q (head die's 512 words) by row i (TOKEN)
ROWMIX = 0x1A0010000                 # per die: the block rows' attention mixes (24 words) by row i
DLOG = 0x1B0000000                   # per die: the block rows' LM-head logits (this die's <= 1,352 rows) by row i
WTAB = 0x1C0000000                   # per position p (64 B): [n_win(p-j)+j for j<5 | n_win(p-j)+5 for j<5 | p mod 16]
GOLDB = 19 << 30                  # LABELLED REPLAY: golden h / pre after layer L at position p (layers 1..39)
GSTR, GPOS = 81952, 16
MHB = 0x280000000                    # main hidden parts (layers 37..39 inputs), ring of 16 positions x 61,440 B
MEMB = 0x290000000                   # Markov-head embedding rows (BF16 x 256) by token: MEMB + token * 512
WROW = 2048
VOCAB, EMB_ROW, MEMB_ROW = 129280, 10240, 512


def full_table(raw, row_bytes, vocab=VOCAB):
    """A whole per-token HBM table (vocab rows of row_bytes) as ONE read-only byte region: no per-token subset, so
    every token the program can compute has its row; refuses a checkpoint tensor of any other size."""
    t = np.asarray(raw).view(np.uint8).reshape(-1)
    if t.size != vocab * row_bytes:
        raise ValueError(f"table holds {t.size} B, not {vocab} rows x {row_bytes} B")
    if t.flags.writeable:
        t = t.view()
        t.flags.writeable = False
    return t


# ---- the HC aperture row plan of the MTP program (slot 0 = the attn mix row, slot 1 = the ffn mix row)
# A body's attn HC_MIX_ROWS loads its own ffn row under itself (slot 1: written and read inside one body, or by all dsa
# of a stage before all its dsb), so only slot 0 crosses bodies.  Its row must come from a body that precedes the
# reader in EVERY launch order v41_dspark.expand / ctl_loop can produce:
#   enter: kind -> (layer, which) the body loads before its END.  embed precedes every L0 body (prefill, every verify
#          column, the first token); demb precedes every dsa of stage 0.
#   next:  layer -> the layer whose attn row its FFN mix record prefetches (None = no cross-body prefetch).  The dsb
#          bodies of stage st run after ALL dsa of st and before all dsa of st + 1, so they prefetch mtp.(st + 1);
#          L0 and stage 2 have no fixed successor (L0: its next column, the head or a draft; stage 2: a verify).
# HC_PLAN_BACKBONE_CHAIN is the single-column backbone rule ((L + 1) % 40, no entering load) the MTP program was
# first lowered with; it is kept ONLY as the checker's negative case (the reader trace and the simulator fault on it).
HC_PLAN = dict(name="mtp", enter={2: (0, "attn"), 6: (40, "attn")}, next={0: None, 40: 41, 41: 42, 42: None})
HC_PLAN_BACKBONE_CHAIN = dict(name="backbone_chain", enter={}, next=None)


def kernel_lp(k, pos, lp):
    """L' after a launch of kind k at pos (G26: a swapin's position field names the layer of the column's bodies)"""
    return (pos if pos < 40 else (pos - 40 if pos != L_NONE else 0)) if k == 0 else lp


def hc_reader_trace(body, launches, ranks=None):
    """STATIC reader trace of the HC aperture over a launch list [(kind, token, pos)] in program order: for every
    aperture HC_MIX_ROWS, the row it needs (rec.hc_row) against the row the LAST aperture LOAD before it left in its
    slot, and that LOAD's launch.  Returns (rows, bad, dead): rows = one dict a reader; bad = the readers whose slot
    was never loaded or holds another row; dead = loads overwritten or left at the end without a reader."""
    from hgi_sim import machine as MC
    from hgi_sim import ds_native as DN
    rows, bad, dead = [], [], []
    for rank in (sorted(body) if ranks is None else ranks):
        held, lp = {}, 0
        for i, (kind, tok, pos) in enumerate(launches):
            k = KINDS.index(kind)
            lp = kernel_lp(k, pos, lp)
            key = (k, lp if k in PER_LAYER else 0)
            for r in body[rank][key]:
                if r.unit == "DMA" and r.op == "LOAD" and r.desc["O"].space == "VM" and r.desc["O"].base >= MC.VM_WORDS:
                    slot = (r.desc["O"].base - MC.VM_WORDS) // DN.HC_SLOT
                    old = held.get(slot)
                    if old is not None and not old["readers"] and old["row"] != tuple(r.hc_row):
                        dead.append(dict(old, rank=rank, why="overwritten unread", by=i))
                    # (the same row again = a refresh by the next column's copy of the body: not a dead load)
                    held[slot] = dict(row=tuple(r.hc_row), launch=i, kind=kind, lp=key[1], readers=0)
                elif r.unit == "HC" and r.op == "HC_MIX_ROWS" and r.desc["B"].space == "VM":
                    slot = (r.desc["B"].base - MC.VM_WORDS) // DN.HC_SLOT
                    h = held.get(slot)
                    row = dict(rank=rank, launch=i, kind=kind, lp=key[1], token=tok, pos=pos, slot=slot,
                               needs=tuple(r.hc_row), holds=h and h["row"], loaded_by=h and (h["launch"], h["kind"], h["lp"]),
                               ok=bool(h and h["row"] == tuple(r.hc_row)))
                    if h:
                        h["readers"] += 1
                    rows.append(row)
                    if not row["ok"]:
                        bad.append(row)
        dead += [dict(h, rank=rank, why="never read") for h in held.values() if not h["readers"]]
    return rows, bad, dead


def mtp_launches(prompt_len=1, steps=1, gamma=None, accept=0, nl=40):
    """The launch list of a DSpark job as the shipped control loop issues it (v41_dspark.ctl_loop over expand): the
    prefill of prompt_len positions, then `steps` draft / verify steps accepting `accept` drafts each."""
    sys.path.insert(0, str(TOOLS / "gpu_sys"))
    import v41_dspark as V41D
    from types import SimpleNamespace
    out = []
    gamma = V41D.GAMMA if gamma is None else gamma

    class Eng:
        prog = SimpleNamespace(m=SimpleNamespace(L=nl))

        def run(self, cmd, want_logits=False):
            ls = V41D.expand(cmd)
            out.extend(ls)
            if cmd["op"] == "MARKOV":                   # draft i = 1000 + i; the verify agrees with the first `accept`
                return [1000 + cmd["idx"]], [None]
            n = sum(1 for x in ls if x[0] == "head")
            return [1000 + c if c < accept else 7 for c in range(n)], [None] * n
    noise, V41D.NOISE = V41D.NOISE, (V41D.NOISE if V41D.NOISE is not None else 3)
    try:
        ngen = 1 + steps * (1 + accept)
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            V41D.ctl_loop(Eng(), [1] * prompt_len, ngen, gamma, maxpos=1 << 20)
    finally:
        V41D.NOISE = noise
    return out


def wtab_row(p):
    nw = [min(p - j, 128) for j in range(5)]
    return [nw[j] + j for j in range(5)] + [nw[j] + 5 for j in range(5)] + [p % 16] + [0] * 5


class Kernels:
    """Per-rank kernel bodies (record lists, every body ends with CTL.END) and rank r's G23 / G26 image.
    spec=True: the DSpark kinds (seed / demb / dsa / dsb / dhead / markov) and the verify head are real; layers 1..39 are
    LABELLED REPLAY bodies (load the golden h / pre after the layer; layers 37..39 first store their input's main hidden
    part with real SU records)."""

    def __init__(self, m, spec=False, b2_swap=None, hc_plan=None):
        """b2_swap (opt-in, default None = the legacy swap bodies, unchanged):
        "native" = the native B2 swap in LOGICAL VM addresses (swap_native: the four-cluster h group + the PRE
        singleton as GRP-marked linear DMA records; what the HGI simulator runs and the B2 pass places);
        a callable rank -> (h_allocations, pre_allocation) read from the live B2 record-liveness allocator
        (hgi_b2.mtp_swap.allocations_from_placement) = swap_b2's dispatch groups in resolved slice addresses (what
        the cluster engines receive; not runnable on the simulator's one logical VM)."""
        self.swap_layout = "native" if b2_swap is not None else "stripe4"
        self.hc_plan = HC_PLAN if hc_plan is None else hc_plan
        from hgi_sim import ds_native as DN
        from hgi_sim.records import MDesc, Rec
        from hgi_sim.qwen_compiler import Builder, sut
        import hdc_isa_v41 as I
        import w19_hbm_tp96_isa as W
        from types import SimpleNamespace
        self.DN, self.W, self.MDesc, self.Rec, self.Builder, self.sut, self.I = DN, W, MDesc, Rec, Builder, sut, I
        self.m, self.TP, self.spec = m, DN.TP, spec
        self.lay, self.man = DN.Layout(), DN.Manifest()
        bind_vm_tail()
        assert self.lay.end <= ZT and QV + 16 <= DN.MC.VM_WORDS
        self.low = DN.Lower(m, 1, self.lay, self.man)
        self.low.hc_next_attn = self.hc_next()
        self.ops = {}
        self.tabs = {}                                  # slot -> [per-rank table buffer]
        self.st0 = SimpleNamespace(win={L: np.zeros((m.window - 1, m.hd), F) for L in (0, 40, 41, 42)}, slots={})
        self.body = {r: {} for r in range(self.TP)}       # (kind, L') -> [Rec]
        for k in range(len(KINDS)):
            for Lp in range(PER_LAYER.get(k, 1)):
                for r in range(self.TP):
                    self.body[r][(k, Lp)] = [self.end()]
        for r in range(self.TP):
            self.body[r][(0, 0)], self.body[r][(1, 0)] = self.swap_bodies(r, b2_swap)
            self.body[r][(2, 0)] = self.embed(r, 2)
            self.body[r][(6, 0)] = self.embed(r, 6)       # demb = the embedding kernel (token y or the noise id)
            if not spec:
                self.body[r][(4, 0)] = [self.end(HT, POS=True)]
        self.tables_for(0)
        for r, recs in enumerate(self.layer(0)):
            self.body[r][(3, 0)] = recs + [self.fence(), self.end()]
        if spec:
            heads = self.head()                          # (L0's tables: norm.weight)
            for r in range(self.TP):
                self.body[r][(4, 0)] = heads[r]
            for L in range(1, 40):
                for r in range(self.TP):
                    self.body[r][(3, L)] = self.replay(L)
            for st in range(3):
                a_, b_ = self.stage(40 + st)
                for r in range(self.TP):
                    self.body[r][(7, st)], self.body[r][(8, st)] = a_[r], b_[r]
            seeds = self.seed()
            for r in range(self.TP):
                self.body[r][(5, 0)] = seeds[r]
                self.body[r][(9, 0)] = self.dhead(r)
                self.body[r][(10, 0)] = self.markov(r)

        self.check_colslot_window()

    def check_colslot_window(self):
        """The column slot windows [stack s local COLB, + NCOLSLOT x CSTR), s = 0..3, hold nothing else: they lie in
        the reserved data window and inside the stack's physical bytes, and no weight manifest extent and no HC stripe
        row (its whole 81,920 B span) overlaps them.  (Registered data regions are refused by Hbm.add in the run.)"""
        DN = self.DN
        span = NCOLSLOT * CSTR
        assert COLB % 32 == 0 and DN.DATA_WIN + (256 << 20) <= COLB and COLB + span <= DN.DATA_WIN + DN.DATA_WIN_BYTES, \
            "column slots outside the reserved data window"
        assert COLB + span <= DN.STACK_BYTES, "column slots beyond the stack's physical bytes"
        for s_ in range(4):
            lo = (s_ << 35) | COLB
            for e in self.man.ent:
                a_, b_ = e["base"], e["base"] + e["estride"] * e["experts"]
                assert not (a_ < lo + span and lo < b_), \
                    f"column slot window of stack {s_} [{lo:#x}, +{span}) overlaps weight extent {e['key']} [{a_:#x}, {b_:#x})"
        for loc in DN.HC_STRIPE:
            assert not (loc < COLB + span and COLB < loc + 8 * DN.HC_RS * 8 * 4), \
                f"column slot window overlaps the HC stripe row at stack-local {loc:#x}"

    # ---- tables (one region per layer slot, relocated)
    def table_region(self, L):
        """the HBM base of slot L's table region (L: 0, 40..42 or "seed")"""
        return self.DN.TBASE + TSLOT[L] * TSTR

    def tables_for(self, L):
        """Build slot L's tables FOR THEIR OWN REGION: the bytes and their layouts (ds_native.set_table_layouts: which
        gains are GPK) are recorded at table_region(L), the address every reader -- lowering check, simulator unit,
        export -- resolves them by.  The seed set's mtp.2.norm gain is the B of the DHEAD FUSED.HC_PRE_NORM (d = 5,120:
        the lane-local engine on an HLL target), so it is stored by the same rule as every other such gain
        (ds_native.gain_image); the other seed gains are read by SU records and stay linear."""
        DN = self.DN
        assert TSTR == DN.TABLE_SPAN
        region = self.table_region(L)
        self.low.table_region = region
        if L == "seed":
            items = [("mtp.0.main_norm.weight", self.m.w["mtp.0.main_norm.weight"])]
            items += [(f"mtp.{st}.attn.kv_norm.weight", self.m.lw(40 + st, "attn.kv_norm.weight")) for st in range(3)]
            items += [("mtp.2.norm.weight", self.m.lw(42, "norm.weight")), ("ROPE", np.zeros(64, F))]
            off, blobs, layouts = 0, [], {}
            for name, arr in items:
                a = np.asarray(arr, dtype=F).reshape(-1)
                off = -(-off // 32) * 32
                fmt = "BF16" if name.endswith("norm.weight") else "FP32"     # (ds_native.build_tables' rule)
                if fmt == "BF16":
                    assert np.array_equal(DN.MC.A.to_bf16(a).view(np.uint32), a.view(np.uint32)), name
                    if name == "mtp.2.norm.weight":
                        a, lay_ = DN.gain_image(name, a)
                        if lay_:
                            layouts[off] = lay_
                    raw = DN.MC.encode_fmt(a, "BF16")
                else:
                    raw = a.view(np.uint8)
                DN.TABLE_OFF[name], DN.TABLE_N[name], DN.TABLE_FMT[name] = off, a.size, fmt
                blobs.append((off, raw))
                off += raw.size
            buf = np.zeros(-(-off // 32) * 32, dtype=np.uint8)
            for o, raw in blobs:
                buf[o:o + raw.size] = raw
            DN.set_table_layouts(region, layouts)
            self.tabs["seed"] = [buf] * self.TP
            self.dnorm_off = DN.TABLE_OFF["mtp.2.norm.weight"]
            return
        self.tabs[L] = [DN.build_tables(self.m, self.st0, L, 0, r, region=region) for r in range(self.TP)]

    def relocate(self, recs, slot):
        """table bases -> slot's region; the RoPE row -> ROPEB by POS"""
        DN = self.DN
        rope_old = DN.TBASE + DN.TABLE_OFF["ROPE"]
        hi = DN.TBASE + TSTR
        for r in recs:
            for k_, d in list(r.desc.items()):
                if d.space != "HBM":
                    continue
                if d.base == rope_old:
                    r.desc[k_] = dataclasses.replace(d, base=ROPEB, dyn_sel=1, dyn_mul=256)
                elif DN.TBASE <= d.base < hi and slot:
                    r.desc[k_] = dataclasses.replace(d, base=d.base + slot * TSTR)
        return recs

    # ---- records
    def end(self, base=None, POS=False):
        base = ZT if base is None else base
        A = self.MDesc(space="VM", fmt="U32", base=base, n=1, dyn_sel=1 if POS else 0, dyn_mul=1 if POS else 0)
        return self.Rec("CTL", "END", wait=0xFFFE, desc=dict(A=A), tag="end" + (".head_stub" if POS else ""))

    def fence(self):
        """CTL.FENCE: every unit drained and every POSTED HBM write visible (spec CTL.FENCE / wr_quiet) -- a body that
        stores to HBM ends with it, so the next launch's reads (the slot's swapin, the next column's window-ring rows)
        see the writes; END's wait mask alone does not cover posted DMA writes"""
        return self.Rec("CTL", "FENCE", wait=0xFFFE, tag="fence")

    def V(self, name, n, off=0, fmt="FP32", **kw):
        return self.MDesc(space="VM", fmt=fmt, base=self.lay.vm[name] + off, n=n, **kw)

    def H(self, base, n, fmt="FP32", **kw):
        return self.MDesc(space="HBM", fmt=fmt, base=base, n=n, **kw)

    def qvload(self, b):
        b.add(self.Rec("DMA", "LOAD", desc=dict(A=self.H(WTAB, 16, fmt="U32", dyn_sel=1, dyn_mul=64),
                                                O=self.MDesc(space="VM", fmt="U32", base=QV, n=16)),
                       tag="wtab", family="mtp"), [], ["QV"])

    def qvi(self):
        """I operand: VM QV + TOKEN (indexed id = QV[i] = the block row's slot; N_FROM_VM = QV[5 + i] = its row count)"""
        return self.MDesc(space="VM", fmt="U32", base=QV, n=1, stride=5, dyn_sel=3, dyn_mul=1)

    def swap(self, into):
        b = self.Builder(None)
        for nm, off, n in SLOT:
            hb = self.H(COLB + off, n, dyn_sel=3, dyn_mul=CSTR)
            vm = self.V(nm, n)
            if nm == "h":                # STRIPE4 (spec 6.4): 320 rows of 256 B, row o on stack o mod 4 at COLB + o x 64
                hb = self.H((1 << 37) | COLB, SW, m=HSTRIPE, stride=64, dyn_sel=3, dyn_mul=CSTR)
                vm = self.V(nm, SW, m=HSTRIPE, stride=SW)
            if into:
                b.add(self.Rec("DMA", "LOAD", desc=dict(A=hb, O=vm), tag=f"swapin.{nm}", family="swap"), [], [nm])
            else:
                b.add(self.Rec("DMA", "STORE", desc=dict(A=vm, O=hb), tag=f"swapout.{nm}", family="swap"),
                      [nm], [f"COL.{nm}"])
        return b.recs + ([] if into else [self.fence()]) + [self.end()]

    def swap_bodies(self, rank, b2_swap=None):
        """(swapin, swapout) bodies of one rank: the legacy records unless the caller opted in with b2_swap."""
        if b2_swap is None:
            return self.swap(True), self.swap(False)
        if isinstance(b2_swap, str):
            assert b2_swap == "native", b2_swap
            return self.swap_native(True), self.swap_native(False)
        h_allocations, pre_allocation = b2_swap(rank)
        return (self.swap_b2(True, h_allocations, pre_allocation),
                self.swap_b2(False, h_allocations, pre_allocation))

    def swap_native(self, into):
        """The native B2 swap as the program carries it (hgi_b2.mtp_swap NATIVE LAYOUT): four linear own-stack DMA
        records, cluster q moving its quarter of h (logical rows 80q .. 80q + 79) to / from stack q's 80 slot rows,
        marked GRP (the last GLAST) so the DMA unit releases them on one edge, then PRE as a GRP | GLAST singleton on
        stack 0.  Same sectors and stacks as the STRIPE4 record, rows permuted by owner; the slot image is NOT the
        legacy one, so swapin and swapout always come from this one builder."""
        from hgi_b2.mtp_swap import logical_h, lower_pre
        legacy = self.swap(into)
        h, pre = legacy[:2]
        return [e.record for e in logical_h(h).records] + [lower_pre(pre, 0).records[0].record] + legacy[2:]

    def swap_b2(self, into, h_allocations, pre_allocation):
        """Native B2 swap groups for the allocator's CURRENT record lifetime.

        h_allocations maps cluster -> resolved LOCAL/MIRROR descriptor for
        its quarter (logical rows 80q .. 80q + 79; they land on slot rows
        q + 4j). pre_allocation is PRE's resolved stack-zero descriptor.
        The cmdproc must dispatch every group's records in one beat. This
        explicit entry point keeps the legacy vehicle unchanged until its
        caller supplies the native B2 allocator and local-slice engines.
        """
        from hgi_b2.mtp_swap import lower_h, lower_pre
        legacy = self.swap(into)
        h, pre = legacy[:2]
        return [lower_h(h, h_allocations), lower_pre(pre, 0, pre_allocation), *legacy[2:]]

    def hc_next(self):
        """Lower.hc_next_attn of the plan (None = the backbone chain rule)"""
        nxt = self.hc_plan["next"]
        return None if nxt is None else (lambda L: nxt[L])

    def hc_enter(self, b, kind, rank):
        """the plan's entering HC row of a kernel kind: the row its successor's attn HC_MIX_ROWS reads from aperture
        slot 0, loaded under this body (the reader FENCEs the slot; END drains the DMA).  A rank that owns no mix row
        carries a NOP so every die's image keeps one structure."""
        if not self.DN.HC_DB[0] or kind not in self.hc_plan["enter"]:
            return
        L, w = self.hc_plan["enter"][kind]
        ld = self.low.hc_row_load(L, w, rank)
        b.add(ld or self.Rec("CTL", "NOP", tag=f"hc_{w}.weight_row_prefetch (layer {L})", family="hc_mixes"), [],
              [f"HCW{0 if w == 'attn' else 1}"] if ld else [])

    def embed(self, rank=0, kind=2):
        b = self.Builder(None)
        self.hc_enter(b, kind, rank)
        for j in range(4):
            b.add(self.Rec("DMA", "LOAD", desc=dict(A=self.H(EMBB, 5120, fmt="BF16", dyn_sel=3, dyn_mul=10240),
                                                     O=self.V("h", 5120, off=5120 * j)),
                           tag=f"embed.h{j}", family="embed"), [], [f"h{j}"])
        b.add(self.Rec("DMA", "LOAD", desc=dict(A=self.H(MTB, 4), O=self.V("PRE", 4)), tag="embed.pre", family="embed"),
              [], ["PRE"])
        return b.recs + [self.end()]

    def su(self, b, tag, desc, rd, wr, **t):
        """an SU template record (a plain HBM -> VM table copy becomes a DMA.LOAD, ds_native FUSION 1)"""
        if set(desc) == {"A", "O"} and desc["A"].space == "HBM" and \
                all(v == 0 for k_, v in self.sut(**t).items() if k_ not in ("dst", "a_src", "b_src", "c_src", "d_src")):
            b.add(self.Rec("DMA", "LOAD", desc=dict(A=desc["A"], O=desc["O"]), tag=tag, family="mtp"), rd, wr)
            return
        b.add(self.Rec("SU", "VOP", sut=self.sut(**t), desc=desc, tag=tag, family="mtp"), rd, wr)

    def mv(self, b, rank, key, rows_all, k, fmt, x, out, out_fmt, local=False, tag=""):
        """SM.MATVEC of this rank's rows (even split, or the 1,347-row head shards when rows_all = 'head')"""
        DN = self.DN
        if rows_all == "head":
            r0, r1 = DN.head_rows(rank)
            n = 129280
        else:
            r0, r1 = self.W.even(rows_all)[rank]
            n = rows_all
        e = self.low.W(key, n, k, fmt)
        bd = self.H(e["base"] + r0 * e["rowbytes"], k, fmt=DN.HFMT[fmt], m=max(r1 - r0, 1), stride=e["rowbytes"])
        o = self.V(out, max(r1 - r0, 1), off=0 if local else r0, fmt=out_fmt)
        if r1 > r0:
            b.add(self.Rec("SM", "MATVEC", param={"bf16": 0, "fp8": 1, "fp4": 2}[fmt], desc=dict(A=x, B=bd, O=o),
                           tag=tag, family="mtp"), [], [out])
        else:
            b.add(self.Rec("CTL", "NOP", tag=tag, family="mtp"), [], [])
        return r0, r1

    def gather(self, b, buf, n, tag):
        b.add(self.Rec("COLL", "ALL_GATHER", desc=dict(A=self.V(buf, n), O=self.V(buf, n)), tag=tag, family="mtp"),
              [buf], [buf])

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
        for recs in rank_recs:
            self.relocate(recs, 0)
            for r in recs:
                for k_, d in list(r.desc.items()):
                    if r.tag in ATT_TAGS and d.n == 128:
                        r.desc[k_] = dataclasses.replace(d, n_sel=DYN_WIN)
        return rank_recs

    def head(self):
        """the verify-row head (kind 4): ds_native's final norm + LM head (STREAM) + ARGMAX.LOCAL + ARGMAX_MERGE, END
        reads the merged id (L0's table region holds norm.weight)"""
        DN, m = self.DN, self.m
        ops = self.W.Compiler(m, 1, DN.VARIANT).compile_head()
        for op_ in ops:
            self.ops[f"{m.L}:{op_.get('id')}"] = op_
        out = []
        for r in range(self.TP):
            recs = self.relocate(self.low.layer(m.L, ops, r), 0)
            out.append(recs + [self.end(self.lay.vm["TOK"] + 4)])
        return out

    def replay(self, L):
        """LABELLED REPLAY of layer L (1..39; not lowered): h / pre <- the golden after layer L at POS.  Layers 37..39
        first store their INPUT's main hidden part (real SU: ((h0 + h1) + h2) + h3, x 0.25, BF16) into the MH ring
        (DMA.KVWB_DS: slot POS mod 16)."""
        b = self.Builder(None)
        I = self.I
        hb = None
        if L in self.m.dspark_targets:
            D = 5120
            self.su(b, "mh.add1", dict(A=self.V("h", D), C=self.V("h", D, off=D), O=self.V("y", D)), ["h"], ["y"],
                    ad=I.AD_C, dst=I.DST_VM)
            for j in (2, 3):
                self.su(b, f"mh.add{j}", dict(A=self.V("y", D), C=self.V("h", D, off=j * D), O=self.V("y", D)),
                        ["h", "y"], ["y"], ad=I.AD_C, dst=I.DST_VM)
            self.su(b, "mh.mean_bf16", dict(A=self.V("y", D), O=self.V("y", D)), ["y"], ["y"], m1=I.M1_AIMM,
                    imm1=f32u(0.25), rnd=1, dst=I.DST_VM)
            part = self.m.dspark_targets.index(L)
            b.add(self.Rec("DMA", "KVWB_DS", desc=dict(A=self.V("y", D), O=self.H(MHB + part * D * 4, D, m=16,
                                                                                     stride=61440)),
                           tag="mh.store", family="mtp"), ["y"], ["MH"])
        base = GOLDB + L * GPOS * GSTR
        b.add(self.Rec("DMA", "LOAD", desc=dict(A=self.H(base, 20480, dyn_sel=1, dyn_mul=GSTR), O=self.V("h", 20480)),
                       tag=f"replay{L}.h", family="replay"), ["MH"], ["h"])
        b.add(self.Rec("DMA", "LOAD", desc=dict(A=self.H(base + 81920, 4, dyn_sel=1, dyn_mul=GSTR), O=self.V("PRE", 4)),
                       tag=f"replay{L}.pre", family="replay"), [], ["PRE"])
        return b.recs + ([self.fence()] if L in self.m.dspark_targets else []) + [self.end()]

    def stage(self, L):
        """DSpark stage L = 40 + st as the sliding-layer lowering (128 experts, top 3) split at the attention: dsa =
        hc mixes .. q RoPE (+ the block row's FP8 KV row into DSKX at n_win + i, q and the mixes saved by row);
        dsb = attention over DSKX rows 0 .. n_win + 4 (the window in ring-slot order + the block rows, no mask) ..
        the FFN hc_post."""
        DN, m, I = self.DN, self.m, self.I
        st = L - 40
        save = (m.ratio, m.n_exp, m.k_exp)
        m.ratio = list(m.ratio_all)
        m.n_exp, m.k_exp = m.dspark_n_exp, m.dspark_k_exp
        try:
            self.tables_for(L)
            ops = self.W.Compiler(m, 1, DN.VARIANT).compile_layer(L, first=True)
            for op_ in ops:
                self.ops[f"{L}:{op_.get('id')}"] = op_
            split = next(o["id"] for o in ops if o.get("fn") == "attend")
            rank_recs = [self.relocate(self.low.layer(L, ops, r), TSLOT[L]) for r in range(self.TP)]
        finally:
            m.ratio, m.n_exp, m.k_exp = save
        dskx = DSKX + st * (1 << 20)
        A_, B_ = [], []
        for recs in rank_recs:
            a_ = self.Builder(None)
            self.qvload(a_)
            pa, pb = self.split_stage(recs, split)
            res_copy = None
            for r in pa:
                if r.tag == "attn.res_copy":
                    res_copy = r
                if r.op == "KVWB_DS":
                    r = self.Rec("DMA", "STORE", wait=0xFFFE, desc=dict(
                        A=r.desc["A"], O=self.H(dskx, 512, indexed=1, dyn_mul=WROW), I=self.qvi()),
                        tag="block_row_kv", family="mtp")
                a_.recs.append(r)
            for buf, n, base, stride in (("q_own", 512, ROWQ, 2048), ("MIXa", 24, ROWMIX, 128)):
                a_.recs.append(self.Rec("DMA", "STORE", wait=0xFFFE, desc=dict(
                    A=self.V(buf, n), O=self.H(base, n, dyn_sel=3, dyn_mul=stride)), tag=f"save.{buf}", family="mtp"))
            A_.append(a_.recs + [self.fence(), self.end()])
            b_ = self.Builder(None)
            self.qvload(b_)
            for buf, n, base, stride in (("q_own", 512, ROWQ, 2048), ("MIXa", 24, ROWMIX, 128)):
                b_.add(self.Rec("DMA", "LOAD", desc=dict(A=self.H(base, n, dyn_sel=3, dyn_mul=stride),
                                                         O=self.V(buf, n)), tag=f"load.{buf}", family="mtp"), [], [buf])
            rc = copy.copy(res_copy)
            rc.wait = 0xFFFE
            # tables the lowering loads once a layer (ds_native FUSION 1 dedup) that dsa loaded and dsb reads: the RoPE
            # row of POS (the inverse RoPE of the attention output) -- reloaded here, the VM holds the LAST dsa's
            tl = [copy.copy(r) for r in pa if r.unit == "DMA" and r.op == "LOAD" and "A" in r.desc
                  and r.desc["A"].space == "HBM" and r.desc["A"].base == ROPEB]
            assert len(tl) == 1, len(tl)
            out = list(b_.recs) + [rc] + tl
            first = True
            for r in pb:
                r = copy.copy(r)
                r.desc = dict(r.desc)
                if first:
                    r.wait = 0xFFFE
                    first = False
                if r.tag in ("attend.qk", "attend.pv"):
                    r.param = r.param & ~(1 << 8)
                    r.desc["B"] = self.H(dskx, 512, m=1, stride=WROW, n_sel=63)
                    r.desc["I"] = self.qvi()
                    r.wait = 0xFFFE
                if r.tag in ATT_TAGS:
                    for k_, d in list(r.desc.items()):
                        if k_ not in ("B", "I") and d.n == 128:
                            r.desc[k_] = dataclasses.replace(d, n_sel=63)
                    r.desc["I"] = self.qvi()
                out.append(r)
            B_.append(out + [self.end()])
        return A_, B_

    @staticmethod
    def split_stage(recs, split):
        """a stage's records at the attention op: (dsa part, dsb part)"""
        return ([r for r in recs if r.src and r.src[1] < split], [r for r in recs if r.src and r.src[1] >= split])

    def seed(self):
        """SEED (kind 5, token = column, pos p): main_x = main_norm(main_proj(MH of p)); each stage's DSpark window row
        (kv_norm(wkv(main_x)), RoPE at p, FP8) into DSKX ring slot p mod 128."""
        DN, I = self.DN, self.I
        self.tables_for("seed")
        D = 5120
        out = []
        for rank in range(self.TP):
            b = self.Builder(None)
            self.qvload(b)
            b.add(self.Rec("DMA", "LOAD", desc=dict(
                A=self.H(MHB, 3 * D, indexed=1, dyn_mul=61440), O=self.V("eg_kv", 3 * D),
                I=self.MDesc(space="VM", fmt="U32", base=QV + 10, n=1)), tag="seed.mh", family="mtp"), ["QV"], ["MHV"])
            self.mv(b, rank, "mtp.0.main_proj.weight", D, 3 * D, "fp8", self.V("eg_kv", 3 * D), "y", "BF16",
                    tag="seed.main_proj")
            self.gather(b, "y", D, "seed.main_proj.gather")
            self.low.rmsnorm(lambda *x, **t: self.su(b, x[0], x[2], x[3], x[4], **{k_: v for k_, v in t.items()
                                                                                    if k_ != "run"}),
                             "seed.main_norm", "y", D, "yf", "x", "mtp.0.main_norm.weight")
            for st in range(3):
                self.mv(b, rank, f"mtp.{st}.attn.wkv.weight", 512, D, "fp8", self.V("x", D), "kvraw", "BF16",
                        tag=f"seed.wkv{st}")
                self.gather(b, "kvraw", 512, f"seed.wkv{st}.gather")
                sufn = (lambda *x, **t: self.su(b, x[0], x[2], x[3], x[4], **{k_: v for k_, v in t.items()
                                                                                if k_ != "run"}))
                self.low.rmsnorm(sufn, f"seed.kv_norm{st}", "kvraw", 512, "GKV", "kvr",
                                 f"mtp.{st}.attn.kv_norm.weight")
                self.low.rope_tail(sufn, f"seed.rope{st}", "kvr", 512, "kvr", inverse=False)
                b.add(self.Rec("FUSED", "QDQ_FP8", desc=dict(A=self.V("kvr", 512), O=self.V("win_new", 512)),
                               tag=f"seed.qdq{st}", family="mtp"), ["kvr"], ["win_new"])
                b.add(self.Rec("DMA", "KVWB_DS", desc=dict(A=self.V("win_new", 512), O=self.H(
                    DSKX + st * (1 << 20), 512, m=128, stride=WROW)), tag=f"seed.dsk{st}", family="mtp"),
                    ["win_new"], [f"DSK{st}"])
            out.append(self.relocate(b.recs, TSLOT["seed"]) + [self.fence(), self.end()])
        return out

    def dhead_norm(self):
        """DHEAD's FUSED.HC_PRE_NORM (h, PRE, the seed region's mtp.2.norm gain -> x), under the same refusal as every
        lowered HC_PRE_NORM: bank phases (rule A) and a GPK gain image at B (rule B)."""
        DN = self.DN
        dn = self.Rec("FUSED", "HC_PRE_NORM", imm_a=f32u(self.m.eps), desc=dict(
            A=self.V("h", 20480), B=self.H(self.table_region("seed") + self.dnorm_off, 5120, fmt="BF16"),
            C=self.V("PRE", 4), O=self.V("x", 5120, fmt="BF16")), tag="dhead.norm", family="mtp")
        DN.assert_fused_fast_path(dn, gain_layout=DN.table_layout_at(dn.desc["B"].base))
        return dn

    def dhead(self, rank):
        """DHEAD (kind 9, token = block row i): rmsnorm(hc_pre(h), mtp.2.norm) -> the LM head (this die's rows) ->
        DLOG row i."""
        b = self.Builder(None)
        b.add(self.dhead_norm(), ["h", "PRE"], ["x"])
        r0, r1 = self.mv(b, rank, "head.weight", "head", 5120, "bf16", self.V("x", 5120), "logits", "FP32",
                         local=True, tag="dhead.lm_head")
        n8 = -(-(r1 - r0) // 8) * 8                  # whole sectors (logits is 1,352 words: the pad stays in the row)
        b.add(self.Rec("DMA", "STORE", desc=dict(A=self.V("logits", n8), O=self.H(DLOG, n8, dyn_sel=3,
                                                                                    dyn_mul=1352 * 4)),
                       tag="dhead.store", family="mtp"), ["logits"], ["DLOG"])
        return b.recs + [self.fence(), self.end()]

    def markov(self, rank):
        """MARKOV (kind 10, token d_i, pos i): DLOG row i + markov_head(embed(d_i)) -> ARGMAX.LOCAL ->
        COLL.ARGMAX_MERGE; END returns d_{i+1}."""
        DN, I = self.DN, self.I
        b = self.Builder(None)
        b.add(self.Rec("DMA", "LOAD", desc=dict(A=self.H(MEMB, 256, fmt="BF16", dyn_sel=3, dyn_mul=512),
                                                 O=self.V("qr", 256)), tag="markov.embed", family="mtp"), [], ["qr"])
        r0, r1 = self.mv(b, rank, "mtp.2.markov_head.head.weight", "head", 256, "bf16", self.V("qr", 256), "logits",
                         "FP32", local=True, tag="markov.head")
        n = r1 - r0
        b.add(self.Rec("DMA", "LOAD", desc=dict(A=self.H(DLOG, n, dyn_sel=1, dyn_mul=1352 * 4), O=self.V("zpart", n)),
                       tag="markov.dlog", family="mtp"), [], ["zpart"])
        self.su(b, "markov.add", dict(A=self.V("zpart", n), C=self.V("logits", n), O=self.V("logits", n)),
                ["zpart", "logits"], ["logits"], ad=I.AD_C, dst=I.DST_VM)
        b.add(self.Rec("ARGMAX", "LOCAL", imm_a=DN.HEAD_ROWS, desc=dict(A=self.V("logits", n), O=self.V("TOK", 2)),
                       tag="markov.argmax_local", family="mtp"), ["logits"], ["TOK"])
        b.add(self.Rec("COLL", "ARGMAX_MERGE", desc=dict(A=self.V("TOK", 2), O=self.MDesc(
            space="VM", fmt="U32", base=self.lay.vm["TOK"] + 4, n=1)), tag="markov.argmax_merge", family="mtp"),
            ["TOK"], ["TOKM"])
        return b.recs + [self.end(self.lay.vm["TOK"] + 4)]

    # ---- the image of rank r (G23 entries, G26 stride), 16-byte units from the image start
    def image(self, r):
        from hgi_sim.records import encode_program
        out = bytearray(16)                                # unit 0 unused: a kernel entry of 0 = absent
        ar = len(out) // 16
        out += encode_program([self.end()])
        kent = [0] * len(KINDS)
        ks = max(len(encode_program(self.body[r][(k, Lp)])) // 16 + 1 for k, n in PER_LAYER.items()
                 for Lp in range(n))
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
            self.Lp = kernel_lp(k, pos, self.Lp)
        Lp = self.Lp if k in PER_LAYER else 0
        progs = [self.K.body[d.rank][(k, Lp)] for d in self.M.dies]
        t0 = time.time()
        try:
            DN.run_per_die(self.M, progs, self.units, pos, tok)
        except Exception as ex:                       # noqa: BLE001
            cur = getattr(self.M, "cur", None)
            raise RuntimeError(f"launch {kind} L'{Lp} tok {tok} pos {pos}: record {getattr(cur, 'tag', None)} "
                               f"{getattr(cur, 'unit', None)}.{getattr(cur, 'op', None)}: {ex}") from ex
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


def rows_replay(Mach, progs, units, rows, mutant=None):
    """H-MTP2 P-ROW PROOF: run one layer body ONCE as P-row records over `rows` = [(token, pos, vm_images_per_die)]:
    record-major (record k runs its P rows, then record k + 1), row r with its own VM image (the per-position VM copy
    of the P-row form) and its own doorbell DYN (POS = its position, WIN), the HBM shared by all rows (so every
    attention row sees ALL P positions' KV appends of the layer: the causal superset of the batched verify).  Returns
    the per-row final VM images.  mutant 'pos0': every row runs at row 0's POS (must FAIL)."""
    dies = Mach.dies
    keep = [d.vm for d in dies]
    imgs = [[im.copy() for im in r[2]] for r in rows]
    nrec = len(progs[0])
    if any(p[k].unit == "CTL" and p[k].op in ("LOOP", "ENDLOOP") for p in progs for k in range(nrec)):
        raise RuntimeError("rows_replay: loops in the body (not a sliding layer)")
    try:
        for k in range(nrec):
            r0 = next((p[k] for p in progs if p[k].unit != "CTL"), None)
            if r0 is None:
                continue
            if r0.unit == "COLL":
                assert all(p[k].unit == "COLL" for p in progs), f"rows_replay: COLL record {k} not on every die"
            for j, (tok, pos, _) in enumerate(rows):
                for i, d in enumerate(dies):
                    d.vm = imgs[j][i]
                Mach.doorbell(tok, rows[0][1] if mutant == "pos0" else pos)
                for d in dies:
                    d.dyn[4] = 0
                if r0.unit == "COLL":
                    Mach.die_recs = {d.rank: progs[i][k] for i, d in enumerate(dies)}
                    Mach.cur = r0
                    try:
                        units[(r0.unit, r0.op)](Mach, r0, 0)
                    finally:
                        Mach.die_recs = None
                else:
                    for i, die in enumerate(dies):
                        r = progs[i][k]
                        if r.unit == "CTL":          # a die-local NOP (ds_native pads non-owner dies with CTL.NOP)
                            assert r.op in ("NOP", "FENCE"), r.op
                            continue
                        Mach.dies = [die]
                        Mach.cur = r
                        try:
                            units[(r.unit, r.op)](Mach, r, 0)
                        finally:
                            Mach.dies = dies
    finally:
        for d, v in zip(dies, keep):
            d.vm = v
    return imgs


def sim(a):
    """Build the kernels, run one DSpark job (prefill p0 + one draft / verify step) on 96 simulated dies through the
    shipped control loop (v41_dspark.ctl_loop), check every column's L0 output, (spec) every DSpark window row, every
    draft stage's rows, the drafts / targets / accepted stream against the golden; optionally export the die bench.
    Golden dir with golden_spec.json: the REAL DSpark drafter (draft kinds lowered, layers 1..39 labelled replay);
    else golden.json: the forced drafter (draft kinds END stubs, head stub)."""
    npy_check()
    sys.path.insert(0, str(TOOLS / "gpu_sys"))
    if a.export:
        # The die-bench vehicle's FUSED slot (hgi_e2e_slots.sv hgi_e2e_fused_slot) is ot_hgi_fused_record UNIT 1: the
        # micro-op lowering, which reads the d = 5,120 gain LINEAR -- so the exported image is built by the rule of
        # THAT reader (tools/hgi_e2e/export.py export_ds does the same), unless the caller says the harness builds
        # the slot with the lane-local engine (HGI_FUSED_HLL=1).  A run without --export prices and checks the die
        # target (HLL 1: GPK gains, bank phase 0).  ds_native reads the variable once, at import.
        os.environ.setdefault("HGI_FUSED_HLL", "0")
        assert "hgi_sim.ds_native" not in sys.modules, "ds_native imported before the export target was chosen"
    import v41_dspark as V41D
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    from types import SimpleNamespace
    from hgi_sim import ds_native as DN
    from hgi_sim import machine as MC
    import w19_hbm_tp96_isa as W
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    spec = (Path(a.golden) / "golden_spec.json").exists()
    if spec:
        gd = json.loads((Path(a.golden) / "golden_spec.json").read_text())
        gz = np.load(Path(a.golden) / "golden_spec.npz")
        h0 = lambda p: (gz[f"h_{p}_0"], gz[f"pre_{p}_0"])          # noqa: E731
    else:
        gd = json.loads((Path(a.golden) / "golden.json").read_text())
        gz = np.load(Path(a.golden) / "golden_l0.npz")
        h0 = lambda p: (gz[f"h0{p}"], gz[f"pre0{p}"])              # noqa: E731
    t0 = time.time()
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    V41D.NOISE = m.noise_id
    TP = DN.TP
    if getattr(a, "hc_hbm", False):
        DN.HC_DB[0] = False
    plan = {p_["name"]: p_ for p_ in (HC_PLAN, HC_PLAN_BACKBONE_CHAIN)}[getattr(a, "hc_plan", "mtp")]
    from hgi_b2.mtp_swap import native_row
    native = getattr(a, "swap", "stripe4") == "native"
    assert not (native and a.export), "--swap native has no die-bench export: the e2e harness has one central VM and " \
        "no group adapter (the group is measured by tb_hgi_b2_swap_rec / tb_hgi_b2_swapin)"
    K = Kernels(m, spec=spec, hc_plan=plan, b2_swap="native" if native else None)
    if spec and DN.HC_DB[0]:
        # the HC aperture reader trace of this job's launch order, before anything runs (the simulator's provenance
        # check faults on the first bad reader; this is the whole table)
        tr, bad, dead = hc_reader_trace(K.body, mtp_launches(len(gd["prompt"]), 1, gd["gamma"], gd["accepted"]))
        (out / "hc_reader_trace.json").write_text(json.dumps(dict(
            plan=plan["name"], readers=len(tr), bad=len(bad), dead_loads=len(dead),
            rank3=[x for x in tr if x["rank"] == 3], bad_first=bad[:8], dead_first=dead[:8]), indent=0, default=str) + "\n")
        print(f"HC aperture reader trace ({plan['name']}): {len(tr)} readers, {len(bad)} bad, {len(dead)} dead loads",
              flush=True)
        if getattr(a, "hc_trace_only", False):
            return 1 if bad else 0
    npos = 1 + len(gd["verify_tokens"])
    rope = np.zeros((GPOS, 64), F)
    for p in range(GPOS):
        cs, sn = V.rope_cs(m.freqs_plain, p)
        rope[p] = np.concatenate([cs, sn])
    # The image holds the WHOLE embedding tables, as the die's HBM does (one read-only region each, shared by the 96
    # dies): the token of an embed / Markov-embed LOAD is computed by the program (dyn_sel TOKEN), so an image that
    # held only the golden's tokens turned every wrong token into "HBM access outside every region" before the draft /
    # golden comparison could report it (regen r5: Markov row of token 2,616, a draft the unfixed HC rows produced).
    emb_tab = full_table(ck.raw("embed.weight")[0], EMB_ROW)
    assert EMBB + emb_tab.size <= MTB, (emb_tab.size, MTB)
    shared = {}
    if spec:
        shared["memb"] = full_table(ck.raw("mtp.2.markov_head.embed.weight")[0], MEMB_ROW)
        gold = np.zeros((40 * GPOS, GSTR // 4), F)
        for p in range(npos):
            for L in range(1, 40):
                gold[L * GPOS + p, :20480] = gz[f"h_{p}_{L}"].reshape(-1)
                gold[L * GPOS + p, 20480:20484] = gz[f"pre_{p}_{L}"]
        shared["gold"] = gold.view(np.uint8).reshape(-1)
        shared["wtab"] = np.array([wtab_row(p) for p in range(GPOS)], np.uint32).view(np.uint8).reshape(-1)
    dies = [MC.Die(r, MC.Hbm()) for r in range(TP)]
    for d in dies:
        d.rk = W.Rank(d.rank)
        for slot_key, tb in K.tabs.items():
            d.hbm.add(DN.TBASE + TSLOT[slot_key] * TSTR, tb[d.rank] if slot_key != "seed" else tb[d.rank].copy(),
                      f"TABLES{slot_key}")
        d.hbm.add(ROPEB, rope.view(np.uint8).reshape(-1).copy(), "ROPE_ROWS")
        d.hbm.add(MTB, np.array([1, 0, 0, 0], F).view(np.uint8).copy(), "MTP_CONST")
        d.hbm.add(COLB, np.zeros(NCOLSLOT * CSTR, np.uint8), "COLSLOTS")
        for st_ in (1, 2, 3):        # the STRIPE4 h rows of stacks 1..3 (same stack-local window as stack 0)
            d.hbm.add((st_ << 35) | COLB, np.zeros(NCOLSLOT * CSTR, np.uint8), f"COLSLOTS{st_}")
        d.hbm.add(EMBB, emb_tab, "EMBED_TABLE")
        if spec:
            for st in range(3):
                d.hbm.add(DSKX + st * (1 << 20), np.zeros(136 * WROW, np.uint8), f"DSKX{st}")
            d.hbm.add(ROWQ, np.zeros(BLK * 2048, np.uint8), "ROWQ")
            d.hbm.add(ROWMIX, np.zeros(BLK * 128, np.uint8), "ROWMIX")
            d.hbm.add(DLOG, np.zeros(BLK * 1352 * 4, np.uint8), "DLOG")
            d.hbm.add(WTAB, shared["wtab"], "WTAB")
            d.hbm.add(GOLDB, shared["gold"], "GOLD_REPLAY")
            d.hbm.add(MHB, np.zeros(16 * 61440, np.uint8), "MHRING")
            d.hbm.add(MEMB, shared["memb"], "MARKOV_EMBED_TABLE")
        d.vm[ZT] = 0
        if not spec:
            assert npos <= HT_N, npos
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
    col_out, stage_out = {}, {}

    def col_read(d, c):
        """slot c as the linear column (h 20,480 words from its slot rows, then PRE 4 words).  Logical row o sits on
        stack o mod 4 at row o (STRIPE4) or, in the native layout, on its owner cluster's stack at slot row
        q + 4j (o = 80q + j): hgi_b2.mtp_swap.native_row -- the reader is independent of the swap records"""
        lb = COLB + c * CSTR
        rows = [native_row(o) if native else (o & 3, o) for o in range(HSTRIPE)]
        h = [d.hbm.view((s_ << 35) | (lb + ro * 64), SW * 4).view(np.uint32) for s_, ro in rows]
        return np.concatenate(h + [d.hbm.view(lb + 81920, 16).view(np.uint32)]).copy()

    rows_pre, rows_post, rows_res = {}, {}, {}

    def rows_proof():
        """the batched layer-0 verify: the six verify columns' layer-0 body as ONE pass of P-row records (rows_replay)
        from each column's pre-layer VM image; every row's final VM (all 96 dies, whole VM incl. the HC aperture)
        must equal that column's column-serial post-layer VM, whose h / PRE are checked against the golden (A)"""
        vp = sorted(rows_pre)
        progs = [K.body[d.rank][(3, 0)] for d in dies]
        rows = [(rows_pre[p][0], p, rows_pre[p][1]) for p in vp]
        for mut in (None, "pos0"):
            t1 = time.time()
            imgs = rows_replay(Mach, progs, units, rows, mutant=mut)
            bad = {}
            for j, p in enumerate(vp):
                nd = [int(np.count_nonzero(imgs[j][i] != rows_post[p][i])) for i in range(len(dies))]
                if any(nd):
                    bad[p] = dict(dies_differing=sum(1 for x in nd if x), words_differing_max=max(nd))
            rows_res["mutant_pos0" if mut else "p_row"] = dict(rows=len(vp), positions=vp, bad=bad,
                                                              equal=not bad, wall_s=round(time.time() - t1, 1))
            print(f"P-ROW PROOF{' (mutant ' + mut + ')' if mut else ''}: {len(vp)} rows, layer-0 body "
                  f"{sum(1 for r in progs[0] if r.unit != 'CTL')} records, 96 dies: "
                  f"{'ALL ROWS EQUAL the column-serial VM' if not bad else 'DIFFER ' + str(bad)}", flush=True)
        rows_pre.clear()

    def on_launch(e):
        if rows_on and K_cur["L"] == 0 and e["kind"] == "embed" and e["pos"] >= plen:
            rows_pre[e["pos"]] = (e["token"], [d.vm.copy() for d in dies])
        if rows_on and K_cur["L"] == 0 and e["kind"] == "layer" and e["pos"] in rows_pre:
            rows_post[e["pos"]] = [d.vm.copy() for d in dies]
            if len(rows_post) == len(gd["verify_tokens"]) and len(rows_pre) == len(rows_post):
                rows_proof()
        if e["kind"] == "swapout" and K_cur["L"] == 0:
            c = e["token"]
            col_out[e["pos"]] = [col_read(d, c) for d in dies]
        if e["kind"] == "swapout" and K_cur["L"] >= 40 and K_cur["phase_b"]:
            c = e["token"]
            stage_out[(K_cur["L"] - 40, c - PMAX)] = [col_read(d, c) for d in dies]
        if e["kind"] == "swapin":
            K_cur["L"] = e["pos"]
            # swap round trip: the working h after a swap-in is the slot's h in the HBM image (rank 0)
            hv = K.V("h", HSTRIPE * SW)
            got_h = dies[0].vm[hv.base:hv.base + HSTRIPE * SW]
            nbad = int(np.count_nonzero(got_h != col_read(dies[0], e["token"])[:HSTRIPE * SW]))
            swapchk["n"] += 1
            if nbad:
                swapchk["bad"] += 1
                if len(swapchk["first"]) < 8:
                    swapchk["first"].append(dict(launch=len(eng.launches) - 1, slot=e["token"], Lp=e["pos"],
                                                 words_differing=nbad))
        if spec and e["kind"] in ("dsa", "dsb") and not K_cur.get("dbg_" + e["kind"] + str(e["token"])) and K_cur["L"] == 40:
            K_cur["dbg_" + e["kind"] + str(e["token"])] = 1
            d0 = dies[0]
            dbg[f"{e['kind']}{e['token']}_dskx"] = d0.hbm.view(DSKX, 6 * WROW).view(np.uint32).copy()
            dbg[f"{e['kind']}{e['token']}_rowq"] = d0.hbm.view(ROWQ, BLK * 2048).view(np.uint32).copy()
            dbg[f"{e['kind']}{e['token']}_rowmix"] = d0.hbm.view(ROWMIX, BLK * 128).view(np.uint32).copy()
            dbg[f"{e['kind']}{e['token']}_qv"] = d0.vm[QV:QV + 16].copy()
        if e["kind"] in ("dsa", "dsb"):
            K_cur["phase_b"] = e["kind"] == "dsb"
    K_cur = {"L": -1, "phase_b": False}
    swapchk = dict(n=0, bad=0, first=[])
    dbg = {}
    eng.on_launch = on_launch
    plen = len(gd["prompt"])
    rows_on = bool(getattr(a, "rows_proof", False))
    forced = None
    if not spec:
        forced_d = gd["drafts"]

        def forced(step, y, q, g):
            assert step == 0 and g == len(forced_d)
            return list(forced_d)
    eng.prog = SimpleNamespace(m=SimpleNamespace(L=m.L))
    ngen = len(gd["emitted"])
    # A step whose drafts / targets differ from the golden's ends the job there (FAIL): the golden holds rows only for
    # its own path, and a later step would overwrite the position-indexed rows (DSK, stage rows, columns) the first
    # mismatch has to be named from.
    watch = dict(heads=[], markov=[], vheads=0)
    run0 = eng.run

    class StepDiverged(Exception):
        pass

    def run_watch(cmd, want=False):
        res, lgs = run0(cmd, want)
        if cmd["op"] == "VHEAD":
            watch["vheads"] += 1
            watch["heads"].append(list(res))
        elif cmd["op"] == "MARKOV":
            watch["markov"] += res
        elif spec and cmd["op"] == "SEED" and watch["vheads"] == plen + 1:
            d_, t_ = watch["markov"], watch["heads"][-1]
            if d_ != gd["drafts"] or t_ != gd["targets"] or watch["heads"][0] != [gd["positions"][plen - 1]["argmax"]]:
                raise StepDiverged
        return res, lgs
    eng.run = run_watch
    diverged = None
    try:
        tok, _, steps = V41D.ctl_loop(eng, gd["prompt"], ngen, gd["gamma"], forced, maxpos=1 << 20)
    except StepDiverged:
        d_, t_ = watch["markov"], watch["heads"][-1]
        a_ = 0
        while a_ < len(d_) and d_[a_] == t_[a_]:
            a_ += 1
        steps = [dict(anchor=plen - 1, drafts=d_, targets=t_, accepted=a_)]
        tok = (watch["heads"][0] + t_[:a_ + 1])[:ngen]
        diverged = dict(prefill_y=watch["heads"][0], golden_y=gd["positions"][plen - 1]["argmax"], drafts=d_,
                        golden_drafts=gd["drafts"], targets=t_, golden_targets=gd["targets"])
        print(f"STEP 1 DIVERGED from the golden (job stopped after its verify): {diverged}", flush=True)
    # (A) every column's L0 output (slot after swapout) == the golden's L0 output at that position, every rank
    colres = []
    for p in sorted(col_out):
        try:
            hh, pp = h0(p)
        except KeyError:                  # a position the golden never ran (only reachable on a diverged path)
            colres.append(dict(pos=p, kind="prefill" if p < plen else "verify", bit_exact_all_ranks=False,
                               no_golden_row=True))
            continue
        want = np.concatenate([hh.reshape(-1).view(np.uint32), pp.view(np.uint32)])
        got = col_out[p]
        ok = all(np.array_equal(g_[:20484], want) for g_ in got)
        colres.append(dict(pos=p, kind="prefill" if p < plen else "verify", bit_exact_all_ranks=bool(ok),
                           rank0_words_differing=int(np.count_nonzero(got[0][:20484] != want))))
    accept_ok = tok == gd["emitted"] and steps and steps[0]["drafts"] == gd["drafts"] and \
        steps[0]["targets"] == gd["targets"] and steps[0]["accepted"] == gd["accepted"]
    draft_checks = {}
    if spec:
        dsk_ok = {}
        for st in range(3):
            for p in range(npos):
                want = gz[f"dsk_{st}_{p}"].view(np.uint32)
                got = [d.hbm.view(DSKX + st * (1 << 20) + (p % 128) * WROW, 2048).view(np.uint32) for d in dies]
                dsk_ok[f"st{st}_p{p}"] = bool(all(np.array_equal(g_, want) for g_ in got))
        stg_ok, draft_detail = {}, {}
        np.savez(out / "dbg_stage0.npz", **dbg)
        np.savez(out / "stage_rows_rank0.npz", **{f"st{st}_row{i}": got[0][:20484] for (st, i), got in stage_out.items()})
        for (st, i), got in sorted(stage_out.items()):
            want = np.concatenate([gz[f"dh_{st}_{i}"].reshape(-1).view(np.uint32), gz[f"dpre_{st}_{i}"].view(np.uint32)])
            stg_ok[f"st{st}_row{i}"] = bool(all(np.array_equal(g_[:20484], want) for g_ in got))
            if not stg_ok[f"st{st}_row{i}"]:
                dif = np.nonzero(got[0][:20484] != want)[0]
                stg_detail = draft_detail.setdefault(f"st{st}_row{i}", {})
                stg_detail.update(n=int(len(dif)), first=[int(x) for x in dif[:6]],
                                  got=[hex(int(got[0][x])) for x in dif[:6]], want=[hex(int(want[x])) for x in dif[:6]],
                                  ranks_equal=bool(all(np.array_equal(g_[:20484], got[0][:20484]) for g_ in got)))
        draft_checks = dict(dsk_rows_bit_exact=dsk_ok, stage_rows_bit_exact=stg_ok, stage_mismatch_detail=draft_detail,
                            drafts=steps[0]["drafts"] if steps else None, golden_drafts=gd["drafts"],
                            all_ok=bool(all(dsk_ok.values()) and all(stg_ok.values()) and len(stg_ok) == 15))
    # (C) timing: the simulator's S2 cycles of every launch body (rank 0), and per record
    patch_timing_dyn()
    from hgi_sim import timing as T
    from hgi_sim.ds_native_timing import NativeCost
    price_pos = getattr(a, "price_pos", None)       # None: each launch at its own position (the functional run's)
    att_b = None
    if getattr(a, "att_b", None):
        att_b = json.loads(Path(a.att_b).read_text())[getattr(a, "att_b_var", "exposed")]["per_record"]
    costs, t_launch = [], 0.0
    per_launch = []
    cache = {}
    for e in eng.launches:
        body = K.body[0][(e["k"], e["Lp"])]
        ppos = e["pos"] if price_pos is None else price_pos
        key = (e["k"], e["Lp"], ppos, e["token"])
        if key not in cache:
            for r in body:
                if not hasattr(r, "src_key0"):        # (NativeCost.walk replaces r.src by its own record)
                    sr = getattr(r, "src", None)
                    r.src_key0 = None if not sr or not isinstance(sr, tuple) else f"{sr[0]}:{sr[1]}"
                r.src_key = r.src_key0 if r.src_key0 in K.ops else None
                r.src_extra = []
                r.layer = e["Lp"]
            nc = NativeCost(K.ops, body)

            def cf(r, dyn, L, nc=nc):
                """NativeCost; the MTP kernels' own collectives (no w19 op) priced by the TU collective model"""
                def model():
                    from hgi_sim.perf import coll_cycles
                    n = r.desc["A"].n if "A" in r.desc else 1
                    nb = 8 * 96 if r.op == "ARGMAX_MERGE" else 4 * n
                    c, _, _ = coll_cycles("ALL_GATHER", nb, 96)
                    return c, "measured_tu_budget", f"{r.op} {nb} B over 96 (TU collective model; no measured class)"
                if r.unit == "COLL" and r.src_key is None:
                    return model()
                if r.unit == "ATT" and att_b:
                    # option B (attention on the SM engines, the current die): the measured SM attention component
                    # span a record (b_measured_model.json per_record, by selection size 640 / 128; DSpark rows 128)
                    T_ = r.desc["O"].n if r.op == "QK" else r.desc["A"].n
                    cls = "640" if T_ > 128 + 64 else "128"
                    return float(att_b[cls][r.op.lower()]), "measured_component+model", f"SM attention option B T{cls}"
                try:
                    return nc(r, dyn, L)
                except KeyError:
                    if r.unit == "COLL":          # a size the measured table lacks (the DSpark stages' gathers)
                        return model()
                    raise
            sch = T.schedule(body, ppos, "S2", token=e["token"], cost_fn=cf)
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
    # rank 0 owns no HC mix row (its HC_MIX_ROWS and row LOADs are NOPs): the same pricing of a row-owning die's
    # bodies (rank 3 = mix row 0), per kernel and per kind, so the HC row loads are in a reported number
    hc_rank, own, own_kern = 3, {k_: 0.0 for k_ in KINDS}, {}
    for e in eng.launches:
        body = K.body[hc_rank][(e["k"], e["Lp"])]
        ppos = e["pos"] if price_pos is None else price_pos
        key = (hc_rank, e["k"], e["Lp"], ppos, e["token"])
        if key not in cache:
            for r in body:
                if not hasattr(r, "src_key0"):
                    sr = getattr(r, "src", None)
                    r.src_key0 = None if not sr or not isinstance(sr, tuple) else f"{sr[0]}:{sr[1]}"
                r.src_key = r.src_key0 if r.src_key0 in K.ops else None
                r.src_extra = []
                r.layer = e["Lp"]
            nc = NativeCost(K.ops, body)
            cache[key] = T.schedule(body, ppos, "S2", token=e["token"], cost_fn=lambda r, dyn, L, nc=nc: cf(r, dyn, L, nc))
        own[e["kind"]] += cache[key]["total_cycles"]
        own_kern.setdefault(f"{e['kind']}{'' if e['Lp'] == 0 else e['Lp']}", round(cache[key]["total_cycles"], 1))
    r0_kern = {}
    for x in per_launch:
        r0_kern.setdefault(f"{x['kind']}{'' if x['Lp'] == 0 else x['Lp']}", x["s2_cycles"])
    print(f"swap-in round trip (rank 0, working h == slot h): {swapchk['n']} swap-ins, {swapchk['bad']} bad, first "
          f"{swapchk['first']}", flush=True)
    # the column-slot HBM image this job left (rank 0, the four stacks' slot windows): the golden image of the swap
    # layout in use (STRIPE4 and native hold the same sectors with h's rows permuted by owner)
    cs = [dies[0].hbm.view((s_ << 35) | COLB, NCOLSLOT * CSTR) for s_ in range(4)]
    colimg = dict(layout=K.swap_layout, rank=0, slots=NCOLSLOT, slot_bytes=CSTR,
                  stack_sha256=[hashlib.sha256(x.tobytes()).hexdigest() for x in cs], file="colslots_rank0.npz")
    np.savez_compressed(out / "colslots_rank0.npz", **{f"stack{s_}": x for s_, x in enumerate(cs)})
    ok_all = bool(swapchk["bad"] == 0 and accept_ok and all(c["bit_exact_all_ranks"] for c in colres) and (not spec or draft_checks["all_ok"]))
    if rows_on:
        ok_all = ok_all and bool(rows_res.get("p_row", {}).get("equal")) and \
            not rows_res.get("mutant_pos0", {}).get("equal", True)
    rec = dict(schema="opentallas.hgi_sim.ds_mtp_sim.v2", golden=str(a.golden),
               drafter="dspark (real, lowered)" if spec else "FORCED (golden drafts; draft kinds END stubs)",
               golden_summary={k_: gd[k_] for k_ in ("prompt", "y", "verify_tokens", "drafts", "targets", "accepted",
                                                      "emitted")},
               machine_tokens=tok, steps=steps, accept_stream_equals_golden=bool(accept_ok),
               l0_columns=colres, l0_all_bit_exact=all(c["bit_exact_all_ranks"] for c in colres),
               draft_checks=draft_checks, verdict="PASS" if ok_all else "FAIL", step1_diverged=diverged,
               swapin_round_trip=swapchk, swap_layout=K.swap_layout, colslot_image=colimg,
               launches=len(eng.launches), s2_job_cycles=round(t_launch, 1),
               price_pos=price_pos, att_pricing=("option B: measured SM attention spans, " + str(a.att_b) + " "
                                                 + getattr(a, "att_b_var", "exposed")) if att_b else "ATT table (option A)",
               s2_l0_cycles=[x["s2_cycles"] for x in l0],
               s2_by_kind={k_: round(sum(x["s2_cycles"] for x in per_launch if x["kind"] == k_), 1)
                           for k_ in KINDS},
               kernel_records={f"{KINDS[k_]}{'' if Lp == 0 else Lp}": len([r for r in K.body[0][(k_, Lp)] if r.unit != "CTL"])
                               for (k_, Lp) in K.body[0] if (k_ not in (3,) or Lp in (0, 1, 37))},
               hc_plan=plan["name"], fused_hll=int(DN.FUSED_HLL), rows_proof=rows_res or None,
               s2_first_launch_cycles={k_: v for k_, v in r0_kern.items() if not k_.startswith("layer") or k_ in (
                   "layer", "layer1", "layer37")},
               hc_row_rank=dict(rank=hc_rank, s2_job_cycles=round(sum(own.values()), 1),
                                s2_by_kind={k_: round(v, 1) for k_, v in own.items()},
                                s2_first_launch_cycles={k_: v for k_, v in own_kern.items() if not k_.startswith(
                                    "layer") or k_ in ("layer", "layer1", "layer37")},
                                kernel_records={f"{KINDS[k_]}{'' if Lp == 0 else Lp}": len(
                                    [r for r in K.body[hc_rank][(k_, Lp)] if r.unit != "CTL"])
                                    for (k_, Lp) in K.body[hc_rank] if (k_ not in (3,) or Lp in (0, 1, 37))}),
               stubbed=(["layer bodies L1..L39: LABELLED REPLAY of the golden h / pre after the layer "
                         "(L37..39 store their input's main hidden part with real SU records)"] if spec else
                        ["layer bodies L1..L39 (END only)", "head (END reads golden argmax HT[POS])",
                         "seed / demb / dsa / dsb / dhead / markov (END only; forced drafter)"]),
               wall_s=round(time.time() - t0, 1),
               source_sha256={p_: hashlib.sha256((TOOLS / p_).read_bytes()).hexdigest() for p_ in (
                   "hgi_sim/ds_mtp_kernels.py", "hgi_sim/ds_native.py", "hgi_sim/machine.py", "hgi_sim/records.py",
                   "gpu_sys/v41_dspark.py", "hdc_golden_v41.py")})
    (out / "sim.json").write_text(json.dumps(rec, indent=1, default=int) + "\n")
    (out / "launches.json").write_text(json.dumps(per_launch, indent=0, default=int) + "\n")
    print(f"{rec['verdict']}: accept stream {'== golden' if accept_ok else 'DIFFERS'} {tok}; L0 columns "
          f"{[(c['pos'], c['bit_exact_all_ranks']) for c in colres]}; draft {draft_checks.get('all_ok')} "
          f"drafts {draft_checks.get('drafts')} vs {draft_checks.get('golden_drafts')}; launches {len(eng.launches)} "
          f"S2 {t_launch:.0f}")
    if spec and not draft_checks["all_ok"]:
        print("  dsk", {k_: v for k_, v in draft_checks["dsk_rows_bit_exact"].items() if not v},
              "stage", {k_: v for k_, v in draft_checks["stage_rows_bit_exact"].items() if not v})
    if cap is not None:
        export_bench(a, K, cap, dies[0], regions0, snap0, vm0, costs, gd, rec)
    return 0 if ok_all else 1


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
              image_pages=-(-len(img) // 4096) + 1, mtp_kstride=ks, mtp_noise=K.m.noise_id, **{f"mtp_kernel_{k}": kent[k] for k in range(11)})
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
                                                         s2_l0_cycles=simrec["s2_l0_cycles"]), needs_end=False,
                fused_hll=int(K.DN.FUSED_HLL))        # the FUSED gain layout the image was built for (0 = micro-op slot)
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
    host[64:72] = [len(g["prompt"]), g["gamma"], len(em), 0, 0 if g.get("drafter", "").startswith("dspark") else 1, 1 << 20, len(em),
                   1 + g["accepted"] + 1 + len(g["prompt"]) - 1]
    for i, t in enumerate(g["prompt"][:8]):
        host[72 + i] = t
    for i, t in enumerate(g["drafts"][:8]):
        host[80 + i] = t
    for i, t in enumerate(em[:8]):
        host[88 + i] = t
    (out / "host.mem").write_text("\n".join(f"{x & 0xFFFFFFFF:08x}" for x in host) + "\n")
    from hgi_e2e.scratch import bind_mtp_directory
    bind_mtp_directory(out)
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
    gs = sp.add_parser("golden-spec")
    gs.add_argument("--out", required=True)
    gs.add_argument("--p0", type=int, default=0)
    gs.add_argument("--gamma", type=int, default=4)
    q = sp.add_parser("sim")
    q.add_argument("--golden", required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--export")
    q.add_argument("--hc-plan", default="mtp", choices=("mtp", "backbone_chain"),
                   help="HC aperture row plan; backbone_chain = the checker's negative case (the first lowering)")
    q.add_argument("--hc-hbm", action="store_true",
                   help="HC mix rows read from HBM directly (ds_native HC_DB off: no aperture slots; a bisection aid)")
    q.add_argument("--swap", default="stripe4", choices=("stripe4", "native"),
                   help="column swap: stripe4 = the legacy one-record STRIPE4 swap (the e2e die bench); native = the B2 "
                        "four-cluster own-stack group (cluster q's quarter of h on stack q; another slot image)")
    q.add_argument("--hc-trace-only", action="store_true", help="build the kernels, write the reader trace, stop")
    q.add_argument("--price-pos", type=int, help="price every launch body at this position (e.g. 1048575: the 1M step; "
                   "the functional run and its checks are unchanged)")
    q.add_argument("--att-b", help="b_measured_model.json: price ATT records by the measured SM attention spans (option B)")
    q.add_argument("--att-b-var", default="exposed", choices=("exposed", "prefetch"))
    q.add_argument("--rows-proof", action="store_true",
                   help="H-MTP2: re-run the verify's layer 0 as ONE pass of P-row records (rows_replay) and require "
                        "every row's VM == the column-serial VM (all dies); mutant pos0 must differ")
    a = ap.parse_args()
    if a.cmd == "golden":
        return golden(a)
    if a.cmd == "golden-spec":
        return golden_spec(a)
    if a.cmd == "sim":
        return sim(a)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
