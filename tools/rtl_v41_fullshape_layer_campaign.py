#!/usr/bin/env python3
"""Layer-sharded FULL-SHAPE DeepSeek-V4.1-Flash decode campaign: golden shards, RTL feasibility, assembly.

    python3 tools/rtl_v41_fullshape_layer_campaign.py --steps blockers,golden,model,assemble \
        [--contexts 1048576,200000] [--layers 0-39] [--scratch DIR]

WHY LAYER SHARDS.  A whole full-shape token of the 188-die array cannot be simulated in one process, so the token
is cut at layer boundaries.  A shard is one backbone layer of one decode token at one context position:

  input   the golden's exact layer input: the 4-copy hyper-connection residual h [4, 5120] (BF16 values), the
          pending pre-mix `pre` [4] of the previous FFN sublayer, the position, the token history (Engram), and
          the per-position transients the layer reads (the index selection its index source made, the candidate
          blocks of layer 20), plus the layer's KV / index state (below);
  output  the golden's layer output (h, pre) and the transients it made (index selection, experts, the rows it
          appended to the compressed-KV / index-key state);
  RTL     one layer die (rtl/chip/ot_chip_v41x_die.sv, the adopted core) runs the layer's program on those inputs
          and is checked bit for bit against the output; its cycles are the shard's cycles.

The shards of one token are produced by ONE sequential golden pass (layer L's output is layer L+1's input), so
every shard's input is exactly what the preceding layers compute; the RTL shards are then independent and run in
parallel across the fleet (/tmp/claude-1000/remote_gate.sh).

TENSOR GROUP.  The design point splits a layer over a tensor group of 4 dies (tools/hdc_replay_v41.py SHIPPED,
tp = 4: output-split a-projections, heads / o-groups / expert intermediate / router experts, index keys; the
hyper-connection residual work replicated).  The RTL shard is ONE die with a bit-exact collective model: the
die's partial sums of the other three ranks come from the golden (the full-width golden product restricted to
their slices, combined in the one-shot collective's fixed rank order, which R-ARITH makes a level of the chunked
tree).  Simulating the 4-die group per layer would multiply the per-shard memory by 4 for no additional
arithmetic coverage.

STATE AT 1M / 200K.  A real 1M-token prefill is infeasible here (the golden decodes one position at a time).  The
KV / index state entering the token is SYNTHETIC BUT GOLDEN-CONSISTENT: every row is produced by the golden's own
quantisers in the format the golden stores (window rows FP8 QDQ of a gained RMS-normalised vector, compressed KV
rows FP4 (E4M3 scale, block 16) QDQ, index keys FP4 (UE8M0, block 32) QDQ), deterministic from a seed, with the
row counts of the context (window 128; compressed rows (pos + 1) // ratio per KV source; the compressor's open
group).  The token itself is then computed exactly by the golden on that state.

GOLDEN AT FULL SHAPE.  tools/hdc_golden_v41.py's Model is shape-generic but loads a single checkpoint file whole.
This tool builds the same Model object (attributes set exactly as Model.__init__ does; the __init__ source is
pinned by hash and the tool refuses to run if it changes) over the RELEASED checkpoint
(~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash, 48 shards), reading each tensor lazily through
a memory map, so a layer costs only its own weights and the experts its router picks.  Arithmetic contract:
HDC_V41_ARITH = chunk8 (R-ARITH, all classes: the adopted all-unit core's contract).

Writes results/rtl/hdc_v41x_fullshape_layers.json (source-pinned) and per-layer shard files under --scratch.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import resource
import struct
import subprocess
import sys
import time

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402
from hdc_golden import F, from_bits, to_bf16  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41x_fullshape_layers.json"
SCHEMA = "opentallas.rtl.hdc_v41x_fullshape_layers.v1"
HF = Path(os.environ.get("OT_V41_FLASH_SNAPSHOT", Path.home() / ".cache/huggingface/hub/models--deepseek-ai--"
                         "DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277"))
CONFIG = ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json"
# Model.__init__ of tools/hdc_golden_v41.py as mirrored by build_model(); a change there must be mirrored here
INIT_SHA = "e7cb833da456d0b6486b347c822d2ca12f2dac1670daf5faa86c35102e9a6552"
SEED = 20260928


# -- the released checkpoint, lazily ---------------------------------------------------------------------------
class Checkpoint:
    """Tensor reader over the released shards: header offsets, a memory map per shard, the dtype decoding of
    hdc_golden_v41.load_checkpoint applied to one tensor at a time."""

    def __init__(self, snap: Path = HF):
        self.snap = snap
        self.map = json.loads((snap / "model.safetensors.index.json").read_text())["weight_map"]
        self._hdr, self._mm = {}, {}

    def _header(self, f):
        if f not in self._hdr:
            with open(self.snap / f, "rb") as fh:
                n = struct.unpack("<Q", fh.read(8))[0]
                self._hdr[f] = (json.loads(fh.read(n)), 8 + n)
            self._mm[f] = np.memmap(self.snap / f, dtype=np.uint8, mode="r")
        return self._hdr[f]

    def __contains__(self, name):
        return name in self.map

    def meta(self, name):
        f = self.map[name]
        h, base = self._header(f)
        return h[name], base, f

    def raw(self, name):
        """The tensor's bytes as a read-only uint8 memory map, its dtype and shape."""
        m, base, f = self.meta(name)
        s, e = m["data_offsets"]
        return self._mm[f][base + s:base + e], m["dtype"], m["shape"]

    def get(self, name):
        """hdc_golden_v41.load_checkpoint's decoding of one tensor."""
        buf, dt, shape = self.raw(name)
        if dt == "F32":
            return np.frombuffer(buf, dtype=np.float32).reshape(shape).copy()
        if dt == "BF16":
            return from_bits(np.frombuffer(buf, dtype=np.uint16).astype(np.uint32) << 16).reshape(shape)
        if dt == "F8_E4M3":
            return np.frombuffer(buf, dtype=np.uint8).reshape(shape)
        if dt == "F8_E8M0":
            return np.frombuffer(buf, dtype=np.uint8).astype(np.int32).reshape(shape) - 127
        if dt == "I8":
            b = np.frombuffer(buf, dtype=np.uint8).reshape(shape)
            return np.stack([V.E2M1[b & 15], V.E2M1[b >> 4]], axis=-1).reshape(shape[0], shape[1] * 2)
        raise ValueError(f"{name}: unsupported dtype {dt}")

    def rows(self, name, ids):
        """Selected rows of a 2-D tensor without decoding the rest (the embedding, the Engram tables)."""
        buf, dt, shape = self.raw(name)
        width = {"BF16": 2, "F32": 4, "F8_E4M3": 1, "F8_E8M0": 1}[dt]
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(shape[0], shape[1] * width)
        sel = np.asarray(arr[np.asarray(ids)])
        if dt == "BF16":
            return from_bits(sel.view(np.uint16).astype(np.uint32) << 16)
        if dt == "F8_E8M0":
            return sel.astype(np.int32) - 127
        if dt == "F32":
            return sel.view(np.float32)
        return sel


class LazyWeights(dict):
    """Model.w, loaded on first use with Model.__init__'s conversions: a .weight with a .scale sibling becomes a
    Q8 (_blocked), except the Engram table; wo_a is dequantised to BF16 (the release's convert.py)."""

    def __init__(self, ck: Checkpoint):
        super().__init__()
        self.ck = ck
        self.loaded_bytes = 0

    def __missing__(self, name):
        ck = self.ck
        if name == "embed.weight":
            raise KeyError("embed.weight is read by row (Checkpoint.rows), never whole")
        v = ck.get(name)
        sc = name[:-len(".weight")] + ".scale" if name.endswith(".weight") else None
        if sc in ck and not name.endswith("engram.embed.weight"):
            v = V._blocked(v, ck.get(sc), name)
            if name.endswith("attn.wo_a.weight"):
                v = to_bf16(v.dense())
        self.loaded_bytes += ck.raw(name)[0].size
        self[name] = v
        return v


class EngramScales:
    """The Engram table's per-32-column UE8M0 exponents, decoded only for the rows a hash selects."""

    def __init__(self, ck, name):
        self.ck, self.name = ck, name
        self.shape = tuple(ck.raw(name)[2])

    def __getitem__(self, ids):
        return self.ck.rows(self.name, np.asarray(ids).reshape(-1)).reshape(np.shape(ids) + (self.shape[1],))


class EngramCodes(EngramScales):
    pass


def build_model(ck: Checkpoint, config: Path = CONFIG, engram=True):
    """A hdc_golden_v41.Model at the released shape over the lazy checkpoint: every attribute Model.__init__
    sets, set the same way (its source is pinned: INIT_SHA)."""
    src = inspect.getsource(V.Model.__init__)
    got = hashlib.sha256(src.encode()).hexdigest()
    if got != INIT_SHA:
        raise SystemExit(f"hdc_golden_v41.Model.__init__ changed ({got}); mirror it in build_model and re-pin")
    m = V.Model.__new__(V.Model)
    m.vendor_decode_from = None
    c = m.c = json.loads(Path(config).read_text())
    m.L = c["n_layers"]
    m.has_mtp = any(k.startswith("mtp.") for k in ck.map)
    m.dim, m.hc = c["dim"], c["hc_mult"]
    m.heads, m.hd, m.rd = c["n_heads"], c["head_dim"], c["rope_head_dim"]
    m.eps, m.hc_eps = F(c["norm_eps"]), F(c["hc_eps"])
    m.ratio = c["compress_ratios"][:m.L]
    m.kv_src = list(c["kv_source_layers"])
    m.idx_src = list(c["index_source_layers"])
    m.cand_src = c["candidate_source_layer"]
    m.topk, m.cand_k, m.cand_b = c["index_topk"], c["candidate_topk_blocks"], c["candidate_block_size"]
    m.ih, m.ihd = c["index_n_heads"], c["index_head_dim"]
    m.groups, m.o_rank = c["o_groups"], c["o_lora_rank"]
    m.n_exp, m.k_exp = c["n_routed_experts"], c["n_activated_experts"]
    m.route_scale, m.limit = F(c["route_scale"]), F(c["swiglu_limit"])
    m.window = c["window_size"]
    m.attn_scale = F(m.hd ** -0.5)
    m.index_w_scale = F(m.ihd ** -0.5 * m.ih ** -0.5)
    m.engram_scale = F(m.dim ** -0.5)
    m.sinkhorn_iters = c["hc_sinkhorn_iters"]
    m.n_mtp = c.get("n_mtp_layers", 0) if c.get("dspark_block_size", 0) else 0
    m.dspark_block = c.get("dspark_block_size", 0)
    m.dspark_targets = list(c.get("dspark_target_layer_ids", ()))
    m.dspark_n_exp = c.get("dspark_n_routed_experts", 0) or m.n_exp
    m.dspark_k_exp = c.get("dspark_n_activated_experts", 0) or m.k_exp
    m.noise_id = int(c.get("dspark_noise_token_id", 0)) % int(c["vocab_size"])
    m.ratio_all = list(c["compress_ratios"])
    m.freqs_plain = V.rope_freqs(m.rd, 0, c["rope_theta"], c["rope_factor"], c["beta_fast"], c["beta_slow"])
    m.freqs_yarn = V.rope_freqs(m.rd, c["original_seq_len"], c["compress_rope_theta"], c["rope_factor"],
                                c["beta_fast"], c["beta_slow"])
    m.w = LazyWeights(ck)
    m.emb_codes = {L: (EngramCodes(ck, f"layers.{L}.engram.embed.weight"),
                       EngramScales(ck, f"layers.{L}.engram.embed.scale")) for L in c["engram_layer_ids"]}
    if engram:
        tok = V.TOKENIZER
        V.TOKENIZER = HF / "tokenizer.json"
        try:
            m.engram = V.EngramTables(c, c["vocab_size"])
        finally:
            V.TOKENIZER = tok
    else:
        m.engram = type("NoEngram", (), {"layer_ids": list(c["engram_layer_ids"])})()
    m.kv_of = {L: max(s for s in m.kv_src if s <= L) for L in range(m.L) if m.ratio[L]}
    m.idx_of = {L: max(s for s in m.idx_src if s <= L) for L in range(m.L) if m.ratio[L]}
    return m, got


# -- synthetic, golden-consistent state at a context ------------------------------------------------------------
def _gained(rng, n, width, gain, chunk=1 << 16):
    """n rows of a unit-RMS normal vector times the layer's own norm gain, BF16 (the scale the golden's RMSNorm
    outputs have), generated in chunks."""
    for i in range(0, n, chunk):
        k = min(chunk, n - i)
        x = rng.standard_normal((k, width)).astype(F)
        yield to_bf16(x * gain[None, :])


def synthetic_state(m, ctx, seed=SEED, layers=None):
    """The decode state entering position pos = ctx - 1 (so the token is the ctx-th): per layer 128 window rows
    (FP8 QDQ), per KV source its compressed rows (FP4 E4M3-scale block-16 QDQ) and index keys (FP4 UE8M0 block-32
    QDQ) for the groups before this position's, and the compressor's open group (FP32 slot pairs).  Returns the
    state and a description with the row counts and a digest of every array."""
    pos = ctx - 1
    st = m.new_state()
    desc = {"position": pos, "seed": [seed, ctx], "rows": {}, "sha256": {},
            "streams": "one generator per component: default_rng([seed, ctx, kind, layer]), kind 0 window, "
                       "1 compressed KV, 2 index keys, 3 open group; a shard's state does not depend on which "
                       "other layers were generated"}
    h = hashlib.sha256()

    def rng_of(kind, L):
        return np.random.default_rng([seed, ctx, kind, L])
    need = set(range(m.L)) if layers is None else set(layers)
    for L in range(m.L):
        if L not in need:
            continue
        g = m.lw(L, "attn.kv_norm.weight")
        rows = np.concatenate(list(_gained(rng_of(0, L), m.window - 1, m.hd, g)))
        rows = V.qdq_fp8(rows.reshape(-1)).reshape(m.window - 1, m.hd)
        st["win"][L] = list(rows)
        h.update(rows.tobytes())
        desc["sha256"][f"win{L}"] = hashlib.sha256(rows.tobytes()).hexdigest()
    for s in m.kv_src:
        if not any(m.kv_of.get(L) == s for L in need):
            continue
        r = m.ratio[s]
        n_prev = pos // r if r > 1 else pos          # groups closed before this position's
        gk = m.lw(s, "attn.compressor.norm.weight")
        gi = m.lw(s, "attn.indexer.k_norm.weight")
        ckv = np.empty((n_prev, m.hd), dtype=F)
        ik = np.empty((n_prev, m.ihd), dtype=F)
        i = 0
        for blk in _gained(rng_of(1, s), n_prev, m.hd, gk):
            ckv[i:i + len(blk)] = V.qdq_fp4_e4m3(blk.reshape(-1), 16).reshape(blk.shape)
            i += len(blk)
        i = 0
        for blk in _gained(rng_of(2, s), n_prev, m.ihd, gi):
            ik[i:i + len(blk)] = V.qdq_fp4_e8m0(blk.reshape(-1)).reshape(blk.shape)
            i += len(blk)
        st["ckv"][s], st["ik"][s] = list(ckv), list(ik)
        h.update(ckv.tobytes()); h.update(ik.tobytes())
        desc["sha256"][f"ckv{s}"] = hashlib.sha256(ckv.tobytes()).hexdigest()
        desc["sha256"][f"ik{s}"] = hashlib.sha256(ik.tobytes()).hexdigest()
        rng = rng_of(3, s)
        if r > 1 and pos % r:                     # the open group holds the positions pos - pos % r .. pos - 1
            slots = []
            for p in range(pos - pos % r, pos):
                kv = rng.standard_normal(m.hd).astype(F)
                sc = rng.standard_normal(m.hd).astype(F)
                slots.append((kv, sc))
                st["slotrec"][s][p] = (kv, sc)
                h.update(kv.tobytes()); h.update(sc.tobytes())
            st["slots"][s] = slots
        desc["rows"][str(s)] = {"ratio": r, "compressed_rows": n_prev, "index_keys": n_prev,
                                "open_group_slots": len(st["slots"][s])}
    desc["window_rows_per_layer"] = m.window - 1
    desc["state_sha256"] = h.hexdigest()
    return st, desc


def token_history(ctx, seed=SEED, n=8):
    """The last n token ids before and at the position (synthetic, deterministic; the Engram hash reads 4)."""
    rng = np.random.default_rng(seed * 7 + ctx)
    return [int(t) for t in rng.integers(3, 128000, size=n)]


def digest(*arrs):
    h = hashlib.sha256()
    for a in arrs:
        h.update(np.ascontiguousarray(np.asarray(a, dtype=F)).tobytes())
    return h.hexdigest()


def golden_pin():
    """The golden this run used: git blob hash and sha256 of tools/hdc_golden_v41.py and tools/hdc_golden.py."""
    out = {}
    for f in ("tools/hdc_golden_v41.py", "tools/hdc_golden.py"):
        b = (ROOT / f).read_bytes()
        out[f] = {"git_blob": hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest(),
                  "sha256": hashlib.sha256(b).hexdigest()}
    return out


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576


def golden_token(ctx, layers, out_dir: Path, head=True, log=print):
    """One decode token at position ctx - 1 through `layers` (consecutive from 0 unless a shard input is given),
    layer by layer, saving every shard's input and output."""
    t0 = time.time()
    ck = Checkpoint()
    m, init_sha = build_model(ck, engram=any(L in (1, 14) for L in layers))
    t_build = time.time() - t0
    t0 = time.time()
    st, sdesc = synthetic_state(m, ctx, layers=layers)
    t_state = time.time() - t0
    log(f"ctx {ctx}: model {t_build:.1f} s, state {t_state:.1f} s, rss {rss_gb():.1f} GB")
    hist = token_history(ctx)
    st["tokens"] = list(hist)
    tok = hist[-1]
    first = layers[0]
    if first == 0:
        h = np.repeat(ck.rows("embed.weight", [tok]), m.hc, axis=0).astype(F)
        pre = np.array([1, 0, 0, 0], dtype=F)[:m.hc]
    else:
        prev = np.load(out_dir / f"ctx{ctx}_L{first - 1:02d}.npz")
        h, pre = prev["h_out"], prev["pre_out"]
    cx = {"pos": ctx - 1, "hist": hist, "h": h, "pre": pre}
    if first > 0:
        carry = json.loads((out_dir / f"ctx{ctx}_L{first - 1:02d}.json").read_text())["ctx_out"]
        if "sel" in carry:
            cx["sel"] = carry["sel"]
        if "cand_file" in carry:
            cx["cand"] = np.load(out_dir / carry["cand_file"])["cand"]
    shards = []
    pin = golden_pin()
    for L in layers:
        rec = {"layer": L, "context": ctx, "position": ctx - 1, "golden": pin, "arith": V.ARITH,
               "kind": ("engram+" if L in m.engram.layer_ids else "") + (
                   "sliding" if not m.ratio[L] else f"ratio{m.ratio[L]}" + (
                       "+compressor" if L in m.kv_src else "") + ("+indexer" if L in m.idx_src else "") + (
                       "+candidates" if L == m.cand_src else ""))}
        h_in, pre_in = cx["h"].copy(), cx["pre"].copy()
        rec["input_sha256"] = digest(h_in, pre_in)
        rec["ctx_in"] = {"sel": list(map(int, cx["sel"])) if "sel" in cx else None,
                         "cand_sha256": digest(cx["cand"]) if "cand" in cx else None}
        grew = {s: len(st["ckv"][s]) for s in m.kv_src}
        tr = {}
        t1 = time.time()
        loaded0 = m.w.loaded_bytes
        m.layer(L, cx, st, tr)
        rec["golden_wall_s"] = round(time.time() - t1, 2)
        rec["weights_read_bytes"] = m.w.loaded_bytes - loaded0
        rec["output_sha256"] = digest(cx["h"], cx["pre"])
        rec["experts"] = list(map(int, tr.get(f"L{L}.experts", [])))
        if f"L{L}.index_select" in tr:
            rec["index_select_n"] = len(tr[f"L{L}.index_select"])
            rec["index_select_sha256"] = hashlib.sha256(np.asarray(tr[f"L{L}.index_select"],
                                                                   np.int64).tobytes()).hexdigest()
        rec["appended_rows"] = {str(s): len(st["ckv"][s]) - grew[s] for s in m.kv_src if len(st["ckv"][s]) != grew[s]}
        new_rows = {f"ckv{s}": st["ckv"][s][-1] for s in m.kv_src if len(st["ckv"][s]) != grew[s]}
        new_rows.update({f"ik{s}": st["ik"][s][-1] for s in m.kv_src if len(st["ckv"][s]) != grew[s]})
        new_rows[f"win{L}"] = st["win"][L][-1]
        ctx_out = {}
        if "sel" in cx:
            ctx_out["sel"] = list(map(int, cx["sel"]))
        extra = {}
        if "cand" in cx:
            extra["cand"] = cx["cand"]
            ctx_out["cand_file"] = f"ctx{ctx}_cand.npz"
            np.savez_compressed(out_dir / ctx_out["cand_file"], cand=cx["cand"])
        rec["ctx_out"] = ctx_out
        rec["trace_sha256"] = {k: digest(v) for k, v in tr.items() if not isinstance(v, list)}
        np.savez_compressed(out_dir / f"ctx{ctx}_L{L:02d}.npz", h_in=h_in, pre_in=pre_in, h_out=cx["h"],
                            pre_out=cx["pre"], **new_rows, **{k: v for k, v in tr.items() if not isinstance(v, list)})
        for k in [k for k in m.w if k.startswith(f"layers.{L}.")]:     # a layer's weights are read once a token
            del m.w[k]
        rec["rss_gb_after"] = round(rss_gb(), 2)
        (out_dir / f"ctx{ctx}_L{L:02d}.json").write_text(json.dumps(rec, indent=1) + "\n")
        shards.append(rec)
        log(f"ctx {ctx} L{L:02d} {rec['kind']}: {rec['golden_wall_s']} s, experts {rec['experts']}, "
            f"rss {rec['rss_gb_after']} GB")
    out = {"context": ctx, "position": ctx - 1, "token": tok, "history": hist, "state": sdesc,
           "model_build_s": round(t_build, 1), "state_build_s": round(t_state, 1), "layers": shards,
           "golden_init_source_sha256": init_sha, "golden": pin, "arith": V.ARITH, "fuse": sorted(V.FUSE)}
    if head and layers[-1] == m.L - 1:
        t1 = time.time()
        xf = V.rmsnorm_fold(m.hc_pre(cx["h"], cx["pre"]), m.w["norm.weight"], m.eps)
        logits = V.mv(m.w["head.weight"], xf)
        nxt = int(np.argmax(logits))
        out["head"] = {"next_token": nxt, "logits_sha256": digest(logits), "wall_s": round(time.time() - t1, 1),
                       "margin": float(V.margin(logits))}
        np.savez_compressed(out_dir / f"ctx{ctx}_head.npz", logits=logits, xf=xf)
    out["peak_rss_gb"] = round(rss_gb(), 2)
    return out


# -- what blocks a full-shape layer on the adopted die (re-derived on every run) -----------------------------------
CORE = ROOT / "rtl/hdc/v41x/ot_hdc_core_v41x.sv"
TILE = ROOT / "rtl/chip/ot_chip_v41x_tile.sv"
DIE = ROOT / "rtl/chip/ot_chip_v41x_die.sv"


def _line(path: Path, pattern: str):
    """file:line of the first match (the evidence of a blocker), or None if the pattern no longer occurs."""
    rx = re.compile(pattern)
    for i, ln in enumerate(path.read_text().splitlines(), 1):
        if rx.search(ln):
            return f"{path.relative_to(ROOT)}:{i}: {ln.strip()[:160]}"
    return None


def _param(path: Path, name: str):
    m = re.search(rf"parameter\s+integer\s+{name}\s*=\s*([^,\s)]+)", path.read_text())
    if not m:
        m = re.search(rf"\b{name}\s*=\s*(\d+)", path.read_text())
    return int(m.group(1).replace("_", "")) if m and m.group(1).replace("_", "").isdigit() else None


def blockers(contexts=(1048576, 200000)) -> dict:
    """Full-shape requirement of one die's share of each layer (tensor group 4) against what the adopted core, its
    ISA and its program generator can express.  Every row re-derives its numbers: the per-die program is
    tools/hdc_replay_v41.py's shipped-shape emitter (SHIPPED, tp = 4, the design point's split), its fields are
    checked against tools/hdc_isa_v41.py's widths, its DYN counts are resolved at each context, and the RTL
    evidence is located by pattern (a row whose pattern disappears is reported as possibly fixed)."""
    import hdc_isa_v41 as I
    import hdc_replay_v41 as R
    lay = I.LAYOUT
    prog = R.build(R.SHIPPED)
    over = {}
    for ins in prog:
        for k, v in ins.items():
            if k.startswith("_") or k not in lay or not isinstance(v, int):
                continue
            if not 0 <= v < (1 << lay[k][1]):
                o = over.setdefault(k, {"width_bits": lay[k][1], "max_value": 0, "instructions": 0, "example_tag": None})
                o["instructions"] += 1
                if v > o["max_value"]:
                    o["max_value"], o["example_tag"] = v, ins.get("_tag")
    for o in over.values():
        o["bits_needed"] = int(o["max_value"]).bit_length()
    dyn = {}
    for ctx in contexts:
        dv = R.dyn_values(R.SHIPPED, ctx - 1)
        dyn[str(ctx)] = {k: v for k, v in dv.items() if v >= (1 << I.N)}
    nw = _param(TILE, "NW") or 16
    shp = R.SHIPPED
    rows = []

    def row(key, owner, need, have, evidence, change, blocking=True):
        rows.append({"id": key, "owner": owner, "full_shape_needs": need, "as_built": have,
                     "evidence": evidence, "proposed_change": change,
                     "blocking": bool(blocking and all(e is not None for e in (evidence if isinstance(evidence, list)
                                                                                  else [evidence])))})

    row("isa_field_widths", "Codex (tools/hdc_isa_v41.py, rtl/hdc/v41/ot_hdc_isa_v41.svh, core decode)",
        {k: f"{v['max_value']} ({v['bits_needed']} bits, e.g. {v['example_tag']})" for k, v in over.items()},
        {k: f"{v['width_bits']} bits" for k, v in over.items()},
        f"tools/hdc_isa_v41.py FIELDS: A = {I.A}, N = {I.N}, xu_k = {lay['xu_k'][1]}, D = {I.D}; the per-die "
        f"shipped program (hdc_replay_v41.build(SHIPPED), {len(prog)} instructions) overflows {len(over)} fields",
        "widen xu_k to 12 bits (top-512 selection, 2,048 candidate blocks); give the compressed-KV / index-key "
        "regions their own base space (they live in HBM behind KV_HBM / the pooled indexer, so the vector-memory "
        "A = 24 only needs the resident regions), or widen A to 32 where a field addresses them")
    row("dyn_count_width", "Codex (ISA N, core DYN table)",
        {c: v for c, v in dyn.items()}, f"N = {I.N} bits (max 65,535)",
        _line(CORE, r"dyn\[db \+ 5\] <= p1"),
        "N >= 21 for counts derived from the position (NC1 = pos + 1 up to 1,048,576; per-die scan SC1 = 262,144 "
        "at 1M), or express the scan counts in tiles (rnds) so a 16-bit count covers them")
    row("token_and_position_width", "Codex (ot_hdc_core_v41x ports, ot_chip_v41x_tile NW)",
        {"token": f"vocab {129280} needs 17 bits", "position": "1,048,575 needs 20 bits"},
        f"NW = {nw} (token, pos, next_token, counts share it)",
        [_line(CORE, r"input\s+wire \[NW-1:0\]\s+pos"), _line(TILE, r"NW = 16")],
        "separate the position width (PW = 21) and the token width (TW = 17) from the count width NW")
    row("dyn_table_is_the_reduced_shape", "Codex (core DYN table = hdc_isa_v41.dyn_values)",
        "DYN values of the shipped shape at one die of tp = 4: head dim 512 strides, per-ratio group counts, "
        "top-512 clamps, per-die scan selectors SC1 / SC2 / SCR / NSL1 / NSL2 / NSLR (hdc_replay_v41.dyn_values)",
        "b_tok * DIM, b_pos * 32 (head dim 32), n2 = p1 >> 1, ns = min(., TOPK = 16); no per-die scan selectors",
        [_line(CORE, r"dyn\[db \+ 16\] <= b_pos \* 32"), _line(CORE, r"parameter integer TOPK = 16")],
        "parameterise the DYN table by the shape (HD, TOPK, ratios, tp) and add the six per-die scan selectors")
    row("attention_adapter_geometry", "Codex (ot_hdc_core_v41x g_att_x instance, ot_hdc_v41x_att_adapt)",
        {"head_dim": shp["hd"], "rows_per_job": f"window 128 + top-{shp['topk']} = {shp['t_max']}",
         "heads_per_die": shp["heads"] // shp["tp"]},
        "H = 16, D = 32, TD = 32, TROWS = 160, NHMAX = 32 (literals)",
        _line(CORE, r"\.H\(16\), \.D\(32\)"),
        "lift the adapter's H / D / TROWS / NHMAX to core parameters (D = 512, TROWS >= 640, NHMAX >= 16) and "
        "size its staging for a 640 x 512 job")
    row("isa_shape_constants", "Codex (tools/hdc_isa_v41.py, tools/hdc_program_v41.py)",
        {"T_MAX": shp["t_max"], "POS_MAX / RoPE rows": "1,048,576 (RoPE computed, not tabled, or a 2^20 table)",
         "head dim": shp["hd"]},
        {"T_MAX": I.T_MAX, "POS_MAX": I.POS_MAX, "ROPE_POS": I.ROPE_POS, "KV_WORDS": I.KV_WORDS,
         "VM_ELEMS": I.VM_ELEMS, "hdc_program_v41.HD": 32},
        [_line(ROOT / "tools/hdc_isa_v41.py", r"^T_MAX = 144"), _line(ROOT / "tools/hdc_program_v41.py", r"^HD = 32")],
        "make the ISA constants functions of the shape dict hdc_replay_v41 already defines")
    row("program_generator_is_reduced_only", "Codex (tools/hdc_program_v41.py Builder, Layout, images)",
        "the real Builder (weights, images, addresses) at the shipped shape and ONE die's tp = 4 share, with the "
        "collective steps of the split",
        "Builder reads the reduced model and hard-codes its dimensions; the shipped-shape emitter "
        "(tools/hdc_replay_v41.py ShapeBuilder) emits timing-only programs: symbolic DYN names, a flat 2^40 "
        "allocator, no images, no collective ops",
        [_line(ROOT / "tools/hdc_replay_v41.py", r"hard-codes its$|hard-codes its dimensions"),
         _line(ROOT / "tools/hdc_program_v41.py", r"^HD = 32")],
        "promote ShapeBuilder into the real Builder (its composite ops already carry every shape parameter): "
        "real placement over the die's ROM banks, image writers at the shipped layout, and a COLL instruction "
        "(or a sequencer wait on the die's collective engine) at each split's reduction")
    rom_words = int(2.714e9 / 128)
    row("rom_and_address_depth", "Claude (die / tile ROM parameters) + Codex (core AW = ISA A)",
        {"per_die_rom_bytes": 2.714e9, "128_byte_words": rom_words, "address_bits": rom_words.bit_length()},
        {"WROM_AW": _param(DIE, "WROM_AW"), "core AW": _param(TILE, "AW") or 24},
        _line(DIE, r"parameter integer WROM_AW"),
        "the die's ROM parameters can be raised here once the core's AW (the ISA's A) can address 2^25 words; "
        "for simulation only the rows a token touches need image content (sparse images)")
    row("collective_in_the_program", "Codex (ISA) + Claude (die collective engine wiring)",
        "about 5 collectives a layer on the critical path (tp = 4: attention output, wo_b, shared + routed "
        "experts, lm_head); the die must stall its sequencer on the one-shot collective's result",
        "the die's u_coll (ot_rom_oneshot_die_px) is elaborated but no instruction drives it; the smoke runs in "
        "host mode with the collective unexercised",
        _line(DIE, r"not exercised by the smoke"),
        "a COLL unit in the ISA (or a mailbox op) + the die wiring from the core to u_cdma; until then the shard "
        "harness injects the golden's other-rank partial sums at the reduction points (the bit-exact collective "
        "model of this campaign)")
    return {"per_die_program": {"shape": shp["name"], "tp": shp["tp"], "instructions": len(prog)},
            "field_overflow": over, "dyn_over_count_width": dyn, "rows": rows,
            "blocking": [r["id"] for r in rows if r["blocking"]],
            "verdict": ("a full-shape layer cannot be expressed on the adopted die: " +
                        ", ".join(r["id"] for r in rows if r["blocking"])) if any(r["blocking"] for r in rows)
            else "no blocker located"}


def model_cycles(contexts=(1048576, 200000)) -> dict:
    """Per layer kind, the design point's model cycles for one die's share (tools/hdc_timing_v41x.per_layer at the
    spec widths, 1,024 SU lanes) and the as-built-width estimate of the same program (hdc_replay_v41.simulate,
    Cfg() = configuration C), the latter sizing the RTL shard's simulated cycles."""
    import hdc_replay_v41 as R
    import hdc_timing_v41x as X
    sp = X.Spec()
    out = {"clock_hz": sp.clock_hz, "spec": "tools/hdc_timing_v41x.Spec() (spec widths)",
           "layer_kinds": {lab: L for lab, L in R.layer_types()}, "by_context": {}}
    for ctx in contexts:
        pl = X.per_layer(sp, ctx)
        rows = {}
        for lab, L in R.layer_types():
            prog = R.build(R.SHIPPED, layers=[L], embed=False, head=False)
            rows[lab] = {"design_point_cycles": pl[lab]["cycles"], "design_point_instructions": pl[lab]["instructions"],
                         "as_built_width_cycles_estimate": R.simulate(prog, ctx - 1, R.SHIPPED, R.Cfg())}
        tok = X.token(sp, ctx)
        out["by_context"][str(ctx)] = {"per_layer_kind": rows, "design_point_token_compute_cycles": tok["compute_cycles"],
                                       "design_point_us_per_token": tok["us_per_token"],
                                       "design_point_comm_us": X.comm_us()}
    return out


def layer_kind(L, R=None):
    """The hdc_replay_v41.layer_types() label whose program is layer L's (same ratio / source / index / Engram)."""
    import hdc_replay_v41 as R
    ratio, kv, idx, eng = R.RATIO[L], L in R.KV_SRC, L in R.IDX_SRC, L in R.ENGRAM
    for lab, Lr in R.layer_types():
        if (R.RATIO[Lr] > 0) == (ratio > 0) and (Lr == R.CAND_SRC) == (L == R.CAND_SRC) and \
                (Lr in R.KV_SRC) == kv and (Lr in R.IDX_SRC) == idx and (Lr in R.ENGRAM) == eng and \
                (not ratio or R.RATIO[Lr] == ratio):
            return lab
    return None


# -- full-shape images of one die-layer, independent of the program generator --------------------------------------
# The canonical per-die content of a layer shard: the die's weight slices in the checkpoint's own storage formats
# (raw bytes: FP8 E4M3 codes, UE8M0 scale bytes, packed E2M1 nibbles, BF16, FP32), the KV / index state packed as it
# sits in HBM (window rows FP8 + UE8M0 per 32, compressed rows FP4 E2M1 + E4M3 per 16, index keys FP4 E2M1 + UE8M0
# per 32), the golden's layer input / output, and a manifest.  A bank-layout pass (the ISA owner's image writer)
# maps these onto the die's ROM banks and HBM regions; nothing here depends on hdc_program_v41.
E2M1_POS = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])


def _pow2_encode(x, block, grid_max, mant_bits, min_exp):
    """Exact re-encoding of already-quantised values with a power-of-two scale per block: e = ceil(log2(amax /
    grid_max)) (the golden's rule, from the stored values); every value / 2^e is on the grid (a value on the grid at
    the original, larger exponent stays on it at a smaller one).  Returns (codes as float64 grid values, e)."""
    x = np.asarray(x, dtype=np.float64).reshape(-1, block)
    amax = np.max(np.abs(x), axis=1)
    e = np.where(amax > 0, np.ceil(np.log2(np.where(amax > 0, amax, 1.0) / grid_max)), 0).astype(np.int64)
    v = x * np.exp2(-e)[:, None]
    assert np.all(np.abs(v) <= grid_max), "scale range"
    assert np.array_equal(V._round_grid(v, min_exp, mant_bits), v), "value off the grid: not an exact encoding"
    return v, e


def pack_fp8_ue8m0(rows):
    """Window KV rows (FP8 QDQ values) -> E4M3 codes [n, hd] uint8 + UE8M0 bytes [n, hd / 32] (bias 127)."""
    n, w = rows.shape
    v, e = _pow2_encode(rows, 32, 448.0, 3, -6)
    codes = np.array([np.nonzero(V.E4M3 == t)[0][0] if t != 0 else (128 if np.signbit(t) else 0)
                      for t in np.unique(v)], dtype=np.uint8)
    lut = dict(zip(np.unique(v).tolist(), codes.tolist()))
    c = np.vectorize(lut.get, otypes=[np.uint8])(v).reshape(n, w)
    out = (c, (e + 127).astype(np.uint8).reshape(n, w // 32))
    dec = (V.E4M3[out[0]].reshape(-1, 32) * np.exp2(out[1].reshape(-1).astype(np.int64) - 127)[:, None]).astype(F)
    assert np.array_equal(dec.reshape(n, w).view(np.uint32), np.asarray(rows, F).view(np.uint32)), "fp8 round trip"
    return out


def _e2m1_codes(v):
    a = np.abs(v)
    idx = np.searchsorted(E2M1_POS, a)
    assert np.array_equal(E2M1_POS[idx], a), "not an E2M1 value"
    return (idx | (np.signbit(v).astype(np.int64) << 3)).astype(np.uint8)


def _nibbles(c):
    c = c.reshape(c.shape[0], -1, 2)
    return (c[..., 0] | (c[..., 1] << 4)).astype(np.uint8)


def pack_fp4_ue8m0(rows):
    """Index keys (FP4 QDQ, UE8M0 per 32) -> packed E2M1 nibbles [n, w/2] + UE8M0 bytes [n, w/32]."""
    n, w = rows.shape
    v, e = _pow2_encode(rows, 32, 6.0, 1, 0)
    codes = _e2m1_codes(v).reshape(n, w)
    dec = (np.concatenate([E2M1_POS, -E2M1_POS])[codes].reshape(-1, 32) * np.exp2(e)[:, None]).astype(F)
    assert np.array_equal(dec.reshape(n, w).view(np.uint32), np.asarray(rows, F).view(np.uint32)), "fp4 round trip"
    return _nibbles(codes), (e + 127).astype(np.uint8).reshape(n, w // 32)


E4M3_POS = np.unique(np.abs(V.E4M3[np.isfinite(V.E4M3)]))


def pack_fp4_e4m3(rows, chunk=1 << 16):
    """Compressed KV rows (FP4 QDQ with an E4M3 scale per 16) -> packed E2M1 nibbles [n, w/2] + E4M3 scale codes
    [n, w/16].  The scale is recovered as amax / c for the largest code c that leaves every value on the grid and the
    scale an E4M3 value (the stored rows came from some such scale, so one exists); asserted by a round trip."""
    n, w = rows.shape
    nib = np.empty((n, w // 2), np.uint8)
    sc = np.empty((n, w // 16), np.uint8)
    e4 = {float(v): i for i, v in enumerate(V.E4M3) if np.isfinite(v) and not (v == 0 and i)}
    for i in range(0, n, chunk):
        x = np.asarray(rows[i:i + chunk], np.float64).reshape(-1, 16)
        amax = np.max(np.abs(x), axis=1)
        s = np.zeros(len(x))
        ok = np.zeros(len(x), bool)
        for cmax in (6.0, 4.0, 3.0, 2.0, 1.5, 1.0, 0.5):
            cand = np.where(amax > 0, amax / cmax, V.FP4_AMAX_FLOOR_E4M3 / 6.0)
            on = np.isin(cand, E4M3_POS)
            q = x / np.where(cand > 0, cand, 1)[:, None]
            good = on & np.all(np.isin(np.abs(q), E2M1_POS), axis=1) & ~ok
            s = np.where(good, cand, s)
            ok |= good
        zero = amax == 0
        s = np.where(zero & ~ok, E4M3_POS[1], s)
        ok |= zero
        assert ok.all(), "no exact E4M3-scaled encoding"
        codes = _e2m1_codes(x / s[:, None])
        dec = (np.concatenate([E2M1_POS, -E2M1_POS])[codes] * s[:, None]).astype(F)
        assert np.array_equal(dec.view(np.uint32), np.asarray(rows[i:i + chunk], F).reshape(-1, 16).view(np.uint32))
        k = len(x) // (w // 16)
        nib[i:i + k] = _nibbles(codes.reshape(k, w))
        sc[i:i + k] = np.array([e4[float(v)] for v in s], np.uint8).reshape(k, w // 16)
    return nib, sc


def _raw(ck, name, rows=None, cols=None):
    """The checkpoint bytes of a tensor slice [rows, cols] in its own storage (cols in elements; packed FP4 has two
    elements a byte)."""
    buf, dt, shape = ck.raw(name)
    width = {"BF16": 2, "F32": 4, "F8_E4M3": 1, "F8_E8M0": 1, "I8": 1}[dt]
    if len(shape) == 1:                          # vectors (norm gains, biases, sinks): rows = elements
        arr = np.frombuffer(buf, np.uint8).reshape(shape[0], width)
        return np.ascontiguousarray(arr if rows is None else arr[slice(*rows)]), dt
    arr = np.frombuffer(buf, np.uint8).reshape(shape[0], shape[1] * width)
    r = slice(None) if rows is None else slice(*rows)
    if cols is None:
        return np.ascontiguousarray(arr[r]), dt
    per = {"I8": 0.5}.get(dt, width)
    return np.ascontiguousarray(arr[r, int(cols[0] * per):int(cols[1] * per)]), dt


def die_slices(L, rank, s, experts, eng):
    """(file name, tensor, row range, column range) of every weight slice rank `rank` of the tp group holds for layer
    L: the split of /tmp/claude-1000/v41_fullshape_tp_plan.md section 1 (w2 by OUTPUT rows)."""
    tp, D, hd = s["tp"], s["dim"], s["hd"]
    P = f"layers.{L}."
    rr = lambda n: (rank * n // tp, (rank + 1) * n // tp)            # noqa: E731
    sb = lambda n: (rank * n // tp // 32, (rank + 1) * n // tp // 32)  # scale rows of a 32 x 32 block scale  # noqa
    out = [("hc_attn_fn", P + "hc_attn_fn", None, None), ("hc_ffn_fn", P + "hc_ffn_fn", None, None),
           ("hc_attn_scale", P + "hc_attn_scale", None, None), ("hc_attn_base", P + "hc_attn_base", None, None),
           ("hc_ffn_scale", P + "hc_ffn_scale", None, None), ("hc_ffn_base", P + "hc_ffn_base", None, None),
           ("attn_norm", P + "attn_norm.weight", None, None), ("ffn_norm", P + "ffn_norm.weight", None, None),
           ("q_norm", P + "attn.q_norm.weight", None, None), ("kv_norm", P + "attn.kv_norm.weight", None, None),
           ("attn_sink", P + "attn.attn_sink", None, None),
           ("wq_a", P + "attn.wq_a.weight", rr(s["q_rank"]), None), ("wq_a.scale", P + "attn.wq_a.scale", sb(s["q_rank"]), None),
           ("wkv", P + "attn.wkv.weight", rr(hd), None), ("wkv.scale", P + "attn.wkv.scale", sb(hd), None),
           ("wq_b", P + "attn.wq_b.weight", rr(s["heads"] * hd), None),
           ("wq_b.scale", P + "attn.wq_b.scale", sb(s["heads"] * hd), None),
           ("wo_a", P + "attn.wo_a.weight", rr(s["o_groups"] * s["o_rank"]), None),
           ("wo_a.scale", P + "attn.wo_a.scale", sb(s["o_groups"] * s["o_rank"]), None),
           ("wo_b", P + "attn.wo_b.weight", None, rr(s["o_groups"] * s["o_rank"])),
           ("wo_b.scale", P + "attn.wo_b.scale", None, sb(s["o_groups"] * s["o_rank"])),
           ("gate", P + "ffn.gate.weight", rr(s["n_exp"]), None), ("gate.bias", P + "ffn.gate.bias", None, None),
           ("shared.w1", P + "ffn.shared_experts.w1.weight", rr(s["moe_ff"]), None),
           ("shared.w1.scale", P + "ffn.shared_experts.w1.scale", sb(s["moe_ff"]), None),
           ("shared.w3", P + "ffn.shared_experts.w3.weight", rr(s["moe_ff"]), None),
           ("shared.w3.scale", P + "ffn.shared_experts.w3.scale", sb(s["moe_ff"]), None),
           ("shared.w2", P + "ffn.shared_experts.w2.weight", rr(D), None),
           ("shared.w2.scale", P + "ffn.shared_experts.w2.scale", sb(D), None)]
    for e in experts:
        q = f"{P}ffn.experts.{e}."
        out += [(f"exp{e}.w1", q + "w1.weight", rr(s["moe_ff"]), None), (f"exp{e}.w1.scale", q + "w1.scale", rr(s["moe_ff"]), None),
                (f"exp{e}.w3", q + "w3.weight", rr(s["moe_ff"]), None), (f"exp{e}.w3.scale", q + "w3.scale", rr(s["moe_ff"]), None),
                (f"exp{e}.w2", q + "w2.weight", rr(D), None), (f"exp{e}.w2.scale", q + "w2.scale", rr(D), None)]
    if L in R_KV_SRC():
        ratio = s["ratio"][L]
        n = (2 if ratio == 2 else 1) * hd
        out += [("compressor.wkv", P + "attn.compressor.wkv.weight", rr(hd), None),
                ("compressor.norm", P + "attn.compressor.norm.weight", None, None),
                ("indexer.wk", P + "attn.indexer.wk.weight", None, None),
                ("indexer.k_norm", P + "attn.indexer.k_norm.weight", None, None)]
        if ratio == 2:
            out += [("compressor.wgate", P + "attn.compressor.wgate.weight", rr(hd), None)]
    if L in R_IDX_SRC():
        out += [("indexer.wq_b", P + "attn.indexer.wq_b.weight", None, None),
                ("indexer.wq_b.scale", P + "attn.indexer.wq_b.scale", None, None),
                ("indexer.weights_proj", P + "attn.indexer.weights_proj.weight", rr(s["ih"]), None)]
    if eng:
        n = (s["hc"] + 1) * D
        out += [("engram.wkv", P + "engram.wkv.weight", rr(n), None), ("engram.wkv.scale", P + "engram.wkv.scale", sb(n), None),
                ("engram.q_weight", P + "engram.q_weight", None, None), ("engram.k_weight", P + "engram.k_weight", None, None)]
    return out


def R_KV_SRC():
    import hdc_replay_v41 as R
    return R.KV_SRC


def R_IDX_SRC():
    import hdc_replay_v41 as R
    return R.IDX_SRC


def images(ctx, L, rank, scratch: Path, out_dir: Path, all_experts=False, log=print):
    """The full-shape image set of die `rank` of layer L's tensor group for the token at position ctx - 1."""
    import hdc_replay_v41 as R
    t0 = time.time()
    shard = json.loads((scratch / f"ctx{ctx}_L{L:02d}.json").read_text())
    z = np.load(scratch / f"ctx{ctx}_L{L:02d}.npz")
    ck = Checkpoint()
    eng = L in (1, 14)
    m, _ = build_model(ck, engram=eng)
    s = dict(R.SHIPPED, ratio=R.RATIO)
    out_dir.mkdir(parents=True, exist_ok=True)
    experts = list(range(s["n_exp"])) if all_experts else shard["experts"]
    man = {"schema": SCHEMA + ".die_layer_images", "context": ctx, "position": ctx - 1, "layer": L, "rank": rank,
           "tp": s["tp"], "split": "tools/rtl_v41_fullshape_layer_campaign.py die_slices (TP plan section 1; w2 by "
                                    "output rows)", "experts_populated": experts,
           "experts_note": "only the experts this token's router picks carry content (a sparse image) unless "
                           "--all-experts", "files": {}}

    def put(name, arr, fmt, **kw):
        p = out_dir / f"{name}.bin"
        a = np.ascontiguousarray(arr)
        p.write_bytes(a.tobytes())
        man["files"][name] = dict(format=fmt, shape=list(a.shape), dtype=str(a.dtype),
                                  sha256=hashlib.sha256(a.tobytes()).hexdigest(), **kw)

    for name, tensor, rows, cols in die_slices(L, rank, s, experts, eng):
        a, dt = _raw(ck, tensor, rows, cols)
        put(f"w.{name}", a, dt, tensor=tensor, rows=rows, cols=cols)
    # KV / index state entering this layer (the synthetic state + the rows earlier layers of this token appended)
    st, sdesc = synthetic_state(m, ctx, layers=[L])
    win = np.stack(st["win"][L])
    c8, e8 = pack_fp8_ue8m0(win)
    put("kv.window.codes", c8, "F8_E4M3", rows=len(win), note="127 rows before this position, oldest first")
    put("kv.window.scale", e8, "F8_E8M0")
    if s["ratio"][L]:
        src = m.kv_of[L]
        ckv, ik = np.stack(st["ckv"][src]), np.stack(st["ik"][src])
        if L > src:
            zs = np.load(scratch / f"ctx{ctx}_L{src:02d}.npz")
            if f"ckv{src}" in zs:
                ckv = np.concatenate([ckv, zs[f"ckv{src}"][None]])
                ik = np.concatenate([ik, zs[f"ik{src}"][None]])
        nib, sc = pack_fp4_e4m3(ckv)
        put(f"kv.ckv{src}.codes", nib, "E2M1 packed (low nibble first)", rows=len(ckv))
        put(f"kv.ckv{src}.scale", sc, "F8_E4M3 per 16")
        lo, hi = rank * -(-len(ik) // s["tp"]), min(len(ik), (rank + 1) * -(-len(ik) // s["tp"]))
        kn, ks = pack_fp4_ue8m0(ik[lo:hi])
        put(f"kv.ik{src}.codes", kn, "E2M1 packed", rows=[lo, hi], note="this rank's contiguous quarter")
        put(f"kv.ik{src}.scale", ks, "F8_E8M0 per 32")
        if st["slots"].get(src):
            put(f"kv.slots{src}", np.stack([np.stack(p) for p in st["slots"][src]]), "F32 (kv, gate) pairs")
    if eng:
        li = m.engram.layer_ids.index(L)
        ids = m.engram.hashes(token_history(ctx), li)
        put("engram.ids", np.asarray(ids, np.int64), "int64 table rows (the hash of this token)")
        put("engram.rows", ck.rows(f"layers.{L}.engram.embed.weight", ids), "F8_E4M3")
        put("engram.scale", np.asarray(ck.raw(f"layers.{L}.engram.embed.scale")[0]).reshape(-1, 8)[ids], "F8_E8M0 raw")
    for k in ("h_in", "pre_in", "h_out", "pre_out"):
        put(f"io.{k}", z[k], "F32 (BF16 values for h)")
    man["golden"] = golden_pin()
    man["golden_shard"] = {k: shard[k] for k in ("input_sha256", "output_sha256", "experts", "kind")}
    man["state"] = sdesc
    man["bytes"] = sum((out_dir / f"{n}.bin").stat().st_size for n in man["files"])
    man["wall_s"] = round(time.time() - t0, 1)
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    log(f"images ctx {ctx} L{L} rank {rank}: {len(man['files'])} files, {man['bytes'] / 1e6:.1f} MB, {man['wall_s']} s")
    return man


PROPOSED = {"A": 30, "N": 21, "xu_k": 12, "INSTR_BITS": 2048, "TW": 17, "PW": 21, "kvd_addr": 30, "kvd_count": 21,
            "kvd_pos": 21, "kv_addr": 30}


def _bits(v):
    return max(1, int(v).bit_length())


def _chk(need, have):
    """ok / BARELY (< 2x headroom) / INSUFFICIENT for a value that must fit in `have` unsigned bits."""
    if need >= (1 << have):
        return "INSUFFICIENT"
    return "BARELY" if need * 2 >= (1 << have) else "ok"


def constraints(contexts=(1048576, 200000)) -> tuple[str, dict]:
    """The first full-shape die-layer shard's shape constraints (layer 0, and every layer type), as Markdown for
    the ISA / core owner, with the numbers derived from the shipped shape and the tp = 4 split of
    tools/hdc_replay_v41.py (SHIPPED) and checked against the proposed full-mode widths."""
    import hdc_isa_v41 as I
    import hdc_replay_v41 as R
    s = R.SHIPPED
    tp, hd, D, hc = s["tp"], s["hd"], s["dim"], s["hc"]
    lay = R.ShapeLayout(s)
    kinds = R.layer_types()
    cnt_fields = ("su_nout", "su_nin", "me_nout", "me_tiles", "me_k", "qe_nb", "qe_tiles", "xu_n", "xu_k", "he_k",
                  "he_nout", "su_chase")
    per = {}
    for lab, L in kinds:
        prog = R.build(s, layers=[L], embed=False, head=False)
        per[lab] = {"layer": L, "instructions": len(prog), "units": {}}
        for u in prog:
            per[lab]["units"][u["unit"]] = per[lab]["units"].get(u["unit"], 0) + 1
        for ctx in contexts:
            mx = {k: 0 for k in cnt_fields}
            for f in prog:
                r = R.resolved(f, ctx - 1, s)
                for k in cnt_fields:
                    mx[k] = max(mx[k], int(r.get(k, 0)))
            per[lab][str(ctx)] = mx
    # vector-memory resident footprint: every region but the compressed-KV copies (KV lives in HBM, KV_HBM = 1)
    items = sorted(lay.vm.map.items(), key=lambda kv: kv[1])
    sizes = {n: (items[i + 1][1] if i + 1 < len(items) else lay.vm.top) - b for i, (n, b) in enumerate(items)}
    resident = {n: v for n, v in sizes.items() if not n.startswith("CKV")}
    vm_res = sum(resident.values())
    # per-die KV / index state a layer die holds (element = one FP32 lane of a 16-element KV word)
    kv = {}
    for ctx in contexts:
        pos = ctx - 1
        for lab, L in kinds:
            r = R.RATIO[L]
            win = 2 * s["window"] * hd                                  # KT + KR copies of the window rows
            ck = ((pos + 1) // r) * hd if r else 0                      # the source's compressed rows (replicated)
            ik = -(-((pos + 1) // r) // tp) * s["ihd"] if r and L in R.IDX_SRC + R.KV_SRC else 0
            tot = win + ck + ik
            kv[(ctx, lab)] = dict(window_elems=win, ckv_elems=ck, ikey_elems_per_die=ik, total_elems=tot,
                                  element_bits=_bits(tot), word16_bits=_bits(-(-tot // 16)),
                                  users_at_30_bits_elements=(1 << PROPOSED["A"]) // max(tot, 1),
                                  users_at_30_bits_words=(1 << PROPOSED["A"]) // max(-(-tot // 16), 1))
    # ROM of one die's share of one layer, bytes (FP8 1 + 1/1024 B, FP4 0.5 + 1/32 B, BF16 2 B, FP32 4 B)
    def rom_bytes(L):
        b = 0.0
        for k, v in lay.qmat.items():
            if not isinstance(k, tuple) or k[0] != L or not isinstance(v, dict):
                continue
            n, kk = v["n"], v["nb"] * 32
            if k[1] == "exp":
                b += s["n_exp"] * n * kk * (0.5 + 1 / 32)
            else:
                b += n * kk * (1 + 1 / 1024)
        b += 2 * 24 * hc * D * 4                                         # hc_attn_fn, hc_ffn_fn (replicated)
        b += (s["n_exp"] // tp) * D * 2 + 2 * (s["o_groups"] // tp) * s["o_rank"] * (s["heads"] // s["o_groups"]) * hd
        if L in R.KV_SRC:
            b += (2 if R.RATIO[L] == 2 else 1) * hd // tp * D * 2 + s["ihd"] * hd * 2
        if L in R.IDX_SRC:
            b += s["ih"] // tp * D * 2
        return b
    rom = {lab: rom_bytes(L) for lab, L in kinds}
    # instruction bits at the proposed widths
    wmap = {I.A: PROPOSED["A"], I.N: PROPOSED["N"]}
    used_now = sum(w for _, w in I.FIELDS)
    used_new = sum((PROPOSED["xu_k"] if n == "xu_k" else wmap.get(w, w) if w in (I.A, I.N) and n not in (
        "imm1", "imm2", "imm3") else w) for n, w in I.FIELDS)
    # DYN table at the shipped shape: (name, formula, max at each context)
    RHs, HDs = s["rd"] // 2, hd
    def dynrow(pos):
        n2 = (pos + 1) >> 1
        ns1, ns2 = min(s["topk"], pos + 1), min(s["topk"], n2)
        rnd = lambda x: (x - 1) // (16 * 4) + 1 if x > 0 else 0          # noqa: E731
        rnd16 = lambda x: (x - 1) // 16 + 1 if x > 0 else 0             # noqa: E731
        tok = s["vocab"] - 1
        rv = R.dyn_values(s, pos)
        return [("ZERO", "0", 0), ("EMBED", "token x DIM (5120)", tok * D),
                ("ROPE", f"pos x RH (RH = rope_dim / 2 = {RHs})", pos * RHs),
                ("ROPE_G2", "(pos - 1) x RH", (pos - 1) * RHs), ("POS", "pos", pos), ("POS1", "pos + 1", pos + 1),
                ("N2", "(pos + 1) >> 1", n2), ("N2M1", "N2 - 1", n2 - 1), ("NSEL1", "min(TOPK = 512, pos + 1)", ns1),
                ("NSEL2", "min(512, N2)", ns2), ("T1", "pos + 1 + NSEL1", pos + 1 + ns1),
                ("T2", "pos + 1 + NSEL2", pos + 1 + ns2), ("RND_POS1", "ceil((pos+1) / 64)", rnd(pos + 1)),
                ("RND_N2", "ceil(N2 / 64)", rnd(n2)), ("RND_T1", "ceil(T1 / 64)", rnd(pos + 1 + ns1)),
                ("RND_T2", "ceil(T2 / 64)", rnd(pos + 1 + ns2)), ("ROW", f"pos x HDIM ({HDs})", pos * HDs),
                ("ROW1", "(pos + 1) x HDIM", (pos + 1) * HDs), ("SLOTW", "(pos & 1) x 2 HDIM / 16", 2 * HDs // 16),
                ("SLOTE", "(pos & 1) x 2 HDIM", 2 * HDs), ("CKV2", "(N2 - 1) x HDIM", (n2 - 1) * HDs),
                ("RND16_POS1", "ceil((pos+1)/16)", rnd16(pos + 1)), ("RND16_N2", "ceil(N2/16)", rnd16(n2)),
                ("RND16_T1", "ceil(T1/16)", rnd16(pos + 1 + ns1)), ("RND16_T2", "ceil(T2/16)", rnd16(pos + 1 + ns2)),
                ("SLOTW8/SLOTP8/TOK32", "MTP only (NSLOT > 1): not in a one-position layer shard", 0),
                ("SC1 (new)", "ceil((pos+1) / tp): per-die index-key scan, ratio-1 source", rv["SC1"]),
                ("SC2 (new)", "ceil(N2 / tp): per-die scan, ratio-2 source", rv["SC2"]),
                ("SCR (new)", "ceil(min(pos+1, 16384) / tp): per-die scan under the candidate cap", rv["SCR"]),
                ("NSL1 (new)", "min(512, SC1): per-die local selection", rv["NSL1"]),
                ("NSL2 (new)", "min(512, SC2)", rv["NSL2"]), ("NSLR (new)", "min(512, SCR)", rv["NSLR"])]
    dyn = {ctx: dynrow(ctx - 1) for ctx in contexts}
    # collective points of one layer (tools/decode_critical_path.py v41_graph) and their bit-exactness
    L0 = kinds[0][0]
    md = []
    w = md.append
    w("# V4.1-Flash full-shape die-layer shard: shape constraints (layer 0 first, every layer type checked)\n")
    w(f"Generated by `tools/rtl_v41_fullshape_layer_campaign.py --steps constraints` (Claude, fullshape campaign), "
      f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.  Shape: "
      f"`tools/hdc_replay_v41.py` SHIPPED (dim {D}, heads {s['heads']}, head_dim {hd}, rope {s['rd']}, "
      f"q_rank {s['q_rank']}, o {s['o_groups']} x {s['o_rank']}, experts {s['n_exp']} top-{s['k_exp']} ff {s['moe_ff']}, "
      f"index {s['ih']} x {s['ihd']} top-{s['topk']}, window {s['window']}, vocab {s['vocab']}), ONE die of a tensor "
      f"group of tp = {tp} (the design point's split).  Contexts: {', '.join(map(str, contexts))} (position = "
      f"context - 1).  Checked against the proposed full-mode widths: "
      + ", ".join(f"{k} = {v}" for k, v in PROPOSED.items()) + ".\n")
    w("Verdict key: **ok** (>= 2x headroom), **BARELY** (fits with < 2x headroom), **INSUFFICIENT**.\n")
    w("## 1. Layer 0 (sliding window, no compressor / indexer / Engram)\n")
    lab0 = kinds[0][0]
    w(f"- Instructions (per-die shipped program, timing emitter, no collective ops): **{per[lab0]['instructions']}** "
      f"(by unit: {per[lab0]['units']}); + 4 collective ops (section 7) = {per[lab0]['instructions'] + 4}.")
    w(f"- Attention rows T = min(pos + 1, 128) = 128 (window only; T_MAX must still be 640 for the compressed layers).")
    w(f"- Heads per die {s['heads'] // tp}, head_dim {hd}, rope tail {s['rd']} (RH = {RHs}).")
    w(f"- One-die ROM share of layer 0: {rom[lab0] / 1e9:.3f} GB = {int(rom[lab0] // 128):,} 128-B words "
      f"({_bits(rom[lab0] // 128)} bits); whole-die ROM capacity 2.714 GB = {int(2.714e9 // 128):,} words "
      f"({_bits(2.714e9 // 128)} bits) -> A = 30 word-addressed: {_chk(int(2.714e9 // 128), 30)}; element (2 B) "
      f"addressed: {int(2.714e9 // 2):,} ({_bits(2.714e9 // 2)} bits) -> {_chk(int(2.714e9 // 2), 30)}.")
    w(f"- Vector memory, resident regions (all but the compressed-KV copies, which live in HBM): "
      f"**{vm_res:,} elements** ({_bits(vm_res)} bits) -> VM_ELEMS >= {1 << _bits(vm_res):,}; "
      f"largest regions: " + ", ".join(f"{n} {v:,}" for n, v in sorted(resident.items(), key=lambda x: -x[1])[:6]) + ".")
    w("")
    w("## 2. Count, position and token widths\n")
    w("| quantity | full-shape max | bits | proposed | verdict |\n|---|---|---|---|---|")
    w(f"| token | {s['vocab'] - 1:,} | {_bits(s['vocab'] - 1)} | TW = 17 | {_chk(s['vocab'] - 1, 17)} |")
    for ctx in contexts:
        w(f"| position @ {ctx:,} | {ctx - 1:,} | {_bits(ctx - 1)} | PW = 21 | {_chk(ctx - 1, 21)} |")
        w(f"| T1 = pos + 1 + 512 @ {ctx:,} | {ctx + 512:,} | {_bits(ctx + 512)} | N = 21 | {_chk(ctx + 512, 21)} |")
    for lab, _ in kinds:
        for ctx in contexts:
            mx = per[lab][str(ctx)]
            big = max((v, k) for k, v in mx.items() if k != "xu_k")
            w(f"| largest count, {lab} @ {ctx:,} ({big[1]}) | {big[0]:,} | {_bits(big[0])} | N = 21 | {_chk(big[0], 21)} |")
            w(f"| xu_k, {lab} @ {ctx:,} | {mx['xu_k']:,} | {_bits(mx['xu_k'])} | 12 | {_chk(mx['xu_k'], 12)} |")
    w("")
    w("## 3. Base-address spaces per region (per die, one user)\n")
    w("Element = one 32-bit lane of the die's 16-element KV word (kv_raddr = word << 4 | lane, as the die's KV "
      "port is documented).  Window = the layer's 128 rows in both copies (KT, KR); CKV = the KV source's "
      "compressed rows (replicated per die: every head reads its selections); IK = the die's quarter of the "
      "source's index keys.\n")
    w("| layer type | context | window | CKV | IK / die | total elements | bits (element) | verdict A = 30 | "
      "users per die at 30 bits (element / word addressing) |\n|---|---|---|---|---|---|---|---|---|")
    for (ctx, lab), v in kv.items():
        w(f"| {lab} | {ctx:,} | {v['window_elems']:,} | {v['ckv_elems']:,} | {v['ikey_elems_per_die']:,} | "
          f"{v['total_elems']:,} | {v['element_bits']} | {_chk(v['total_elems'], 30)} | "
          f"{v['users_at_30_bits_elements']:,} / {v['users_at_30_bits_words']:,} |")
    w("\nFinding: element addressing at A = 30 holds exactly ONE 1M-context user on a ratio-1 layer die "
      "(2^29 CKV elements + keys); a second user's kv_base overflows.  Word addressing (drop the 4 lane bits in "
      "the descriptor, as kvd_wbase already counts words) gives 16x.  The design point batches users per stage, "
      "so either address KV in words or give kv_base its own (user-slice) field outside A.\n")
    w("The emitter's flat allocator places the compressed rows in the vector-memory space (CKV20 at element "
      "805,761,216, 30 bits); in the adopted die they are HBM-resident behind KV_HBM, so the vector-memory fields "
      f"(a_base, b_base, c_base, qe_obase, me_obase) only need the resident {vm_res:,} elements "
      f"({_bits(vm_res)} bits) if the compressor / gather ops address CKV through the KV port.\n")
    w("## 4. DYN table at the shipped shape\n")
    w("| entry | formula at full shape | " + " | ".join(f"max @ {c:,} (bits)" for c in contexts) +
      " | verdict (A = 30 for addresses, N = 21 for counts) |\n|---|---|" + "---|" * len(contexts) + "---|")
    for i, (name, f, _) in enumerate(dyn[contexts[0]]):
        vals = [dyn[c][i][2] for c in contexts]
        lim = 30 if any(t in name for t in ("EMBED", "ROPE", "ROW", "CKV2", "SLOT")) else 21
        w(f"| {name} | {f} | " + " | ".join(f"{v:,} ({_bits(v)})" for v in vals) +
          f" | {_chk(max(vals), lim)} ({lim}) |")
    w("\nROW / ROW1 / CKV2 (pos x 512) reach 2^29 at 1M: fit A = 30 with exactly 2x headroom -- a user base added to "
      "them overflows at the second 1M user (same finding as section 3).  ROPE = pos x 32 needs a RoPE table of "
      f"2^20 x {RHs} cos + sin entries per theta (2 thetas) = {2 * 2 * (1 << 20) * RHs * 4 / 2 ** 20:.0f} MiB of ROM at FP32: "
      "compute the angle (pos x freq, one FP32 mul, then cos/sin) instead of a table, or accept the table.\n")
    w("## 5. Attention adapter at full shape (ot_hdc_v41x_att_adapt)\n")
    w(f"| parameter | reduced literal | full shape | derivation |\n|---|---|---|---|")
    w(f"| H (heads per job) | 16 | {s['heads'] // tp} | 64 heads / tp 4 |")
    w(f"| D (head dim) | 32 | {hd} | head_dim |")
    w(f"| TD (tile width) | 32 | 32 (unchanged; divides 512 into 16 tiles) | engine tile |")
    w(f"| TROWS (rows per job) | 160 | >= {s['t_max']} (use 640) | window 128 + top-{s['topk']} selections |")
    w(f"| NHMAX (heads per op) | 32 | >= {s['heads'] // tp} | heads on this die |")
    w(f"| die KV_STG (words per staging slot) | 2,048 | >= {s['t_max'] * hd // 16:,} | largest op: 640 rows x 512 / 16 |")
    w("")
    w("The die staging at 16 FP32 lanes a word is 640 x 512 x 4 B = 1.25 MiB a slot (2 slots 2.5 MiB) against the "
      "floorplan's 338 KB (stored FP8); staging the stored format and dequantising in the engine (as the attention "
      "engine does) restores the floorplan figure.  This is a die-side (Claude) change.\n")
    w("## 6. ISA constants at full shape\n")
    w("| constant | as built | full shape | note |\n|---|---|---|---|")
    w(f"| T_MAX | {I.T_MAX} | {s['t_max']} | 128 + 512 |")
    w(f"| POS_MAX | {I.POS_MAX} | 1,048,576 | positions provisioned (1M headline) |")
    w(f"| ROPE_POS | {I.ROPE_POS} | 1,048,576 (+16 for MTP) or no table | see section 4 |")
    w(f"| KV_WORDS | {I.KV_WORDS:,} | per die, one user, 1M, ratio-1 layer: "
      f"{-(-kv[(contexts[0], kinds[5][0])]['total_elems'] // 16):,} words | HBM-resident |")
    w(f"| VM_ELEMS | {I.VM_ELEMS:,} | >= {1 << _bits(vm_res):,} ({vm_res:,} resident) | section 1 |")
    w(f"| HD (hdc_program_v41) | 32 | {hd} | |")
    w(f"| DIM / TOPK (core parameters) | 160 / 16 | {D} / {s['topk']} | DYN EMBED and the NSEL clamps |")
    w(f"| INSTR_BITS | {I.INSTR_BITS} | {used_new} bits used at the proposed widths (now {used_now}) -> 2048: "
      f"{'ok' if used_new <= 2048 else 'INSUFFICIENT'} | |")
    w("")
    w("## 7. TP = 4 split of every matrix (one die) and the collective points\n")
    w("| matrix | full [n x K] | per die [n x K] | split | bit-exact with the golden under R-ARITH? |\n|---|---|---|---|---|")
    ff, og = s["moe_ff"], s["o_groups"] * s["o_rank"]
    rows = [
        ("hc_attn_fn / hc_ffn_fn (FP32)", f"24 x {hc * D}", f"24 x {hc * D}", "replicated", "yes (local)"),
        ("wq_a (FP8)", f"{s['q_rank']} x {D}", f"{s['q_rank'] // tp} x {D}", "output rows; all-gather q_a", "yes"),
        ("wkv (FP8)", f"{hd} x {D}", f"{hd // tp} x {D}", "output rows; all-gather", "yes"),
        ("wq_b (FP8)", f"{s['heads'] * hd} x {s['q_rank']}", f"{s['heads'] // tp * hd} x {s['q_rank']}",
         "heads", "yes (needs the full q_a: all-gather)"),
        ("wo_a (BF16, grouped)", f"{s['o_groups']} x [{s['o_rank']} x {s['heads'] // s['o_groups'] * hd}]",
         f"{s['o_groups'] // tp} groups", "o-groups", "yes (local)"),
        ("wo_b (FP8)", f"{D} x {og}", f"{D} x {og // tp}", "K (o-groups); FP32 all-reduce",
         f"yes IF the die sends its FP32 csum partial unrounded and the all-reduce adds ((r0+r1)+(r2+r3)): "
         f"{og // tp // 32} blocks a die = {og // tp // 32 // 8} chunks of 8, a power-of-two-aligned subtree of the "
         f"{og // 32 // 8}-chunk tree"),
        ("gate (BF16)", f"{s['n_exp']} x {D}", f"{s['n_exp'] // tp} x {D}", "output rows; all-gather scores", "yes"),
        ("experts w1 / w3 (FP4)", f"{ff} x {D}", f"{ff // tp} x {D}", "output rows (ff)", "yes"),
        ("experts w2 (FP4)", f"{D} x {ff}", f"{D} x {ff // tp}", "K (ff); ONE FP32 combine all-reduce",
         f"**NO**: the golden rounds EACH expert's w2 output to BF16 (linear_q) before the weighted FP32 expert sum, "
         f"and {ff // tp // 32} blocks a die is not a multiple of the 8-block chunk ({ff // 32} blocks = 9 chunks; "
         f"chunk 2 spans dies 0 and 1).  Proposed: split w2 by OUTPUT rows ({D // tp} x {ff} a die), all-gather the "
         f"activation a ({ff // tp} per expert per die, 7 experts) before w2 and all-gather y ({D // tp} FP32) "
         f"after: bit-exact, same order of bytes"),
        ("shared expert w2 (FP8)", f"{D} x {ff}", f"{D} x {ff // tp}", "K", "**NO**, same reason; same fix"),
        ("indexer wq_b (FP8)", f"{s['ih'] * s['ihd']} x {s['q_rank']}", "replicated", "none", "yes"),
        ("indexer weights_proj (BF16)", f"{s['ih']} x {D}", f"{s['ih'] // tp} x {D}", "output rows; all-gather",
         "yes"),
        ("indexer keys (state)", "n x 128", "ceil(n / 4) x 128 contiguous", "positions; top-512 merge",
         "yes: top-k of the union = top-k of the per-die top-k's (ties to the lower GLOBAL index)"),
        ("candidate blocks (layer 20)", "ceil(n / 8) blocks", "a die's contiguous quarter", "blocks; top-2048 merge",
         "yes if every die boundary is a multiple of 8 positions (262,144 and 50,000 are)"),
        ("compressor wkv|wgate (BF16)", f"{2 * hd} x {D} (ratio 2) / {hd} x {D} (ratio 1)", "1/4 of the rows",
         "output rows; all-gather", "yes"),
        ("Engram wkv (FP8)", f"{(hc + 1) * D} x {s['ecols'] * s['ehd']}", f"{(hc + 1) * D // tp} x "
         f"{s['ecols'] * s['ehd']}", "output rows", "yes"),
        ("lm_head (BF16)", f"{s['vocab']} x {D}", f"{-(-s['vocab'] // tp)} x {D}", "vocabulary; argmax merge",
         "yes (merge by value, ties to the lower global id)")]
    for r_ in rows:
        w("| " + " | ".join(r_) + " |")
    w("\nCollective points of a layer (tools/decode_critical_path.py v41_graph): a_allgather (q_a | kv | index "
      "weights | compressor rows), idx.topk_merge (index-source layers), cand.merge (layer 20), rows_allgather "
      "(compressed layers), out_allreduce (wo_b, FP32 5,120), router_allgather (384 FP32), combine_allreduce (MoE). "
      "Layer 0: a_allgather, out_allreduce, router_allgather, combine_allreduce (+ the w2 change above).\n")
    w("## 8. Collective-engine op proposal (unit COLL = 6; the unit field has room: 0..5 used)\n")
    w("| field | bits | meaning |\n|---|---|---|")
    for f_, b_, m_ in (
            ("coll_op", 2, "0 ALL_REDUCE_SUM (FP32), 1 ALL_GATHER, 2 TOPK_MERGE (value, global index), 3 ARGMAX_MERGE"),
            ("coll_src", "A", "vector-memory element base of this die's contribution"),
            ("coll_dst", "A", "vector-memory element base of the result (ALL_GATHER: rank r's part lands at "
                              "dst + r x coll_n)"),
            ("coll_n", "N", "elements this die contributes (ALL_REDUCE: the vector length)"),
            ("coll_k", 12, "TOPK_MERGE: k (512 index, 2,048 candidate blocks); the merge keeps value-descending, "
                           "ties to the lower global index"),
            ("coll_ibase", "A", "TOPK_MERGE / ARGMAX: base of the index vector (global indices = local + rank "
                                "offset, added by the engine from cfg_rank x coll_n)"),
            ("coll_seq", 8, "sequence number of the collective within the token (matches the engine's record tag; "
                            "a mismatch faults)"),
            ("coll_rnd", 1, "round the ALL_REDUCE result to BF16 after the sum (wo_b, MoE y)")):
        w(f"| {f_} | {b_} | {m_} |")
    w("\nSemantics.  Issue sends the die's `coll_n` elements to the die's one-shot collective engine (u_cdma -> "
      "u_coll, ot_rom_oneshot_die_px) and the unit stays busy until the result is written; the region scoreboard / "
      "wait mask treats coll_dst as the op's write set, coll_src as its read set, so later readers wait and "
      "earlier independent units overlap.  ALL_REDUCE_SUM adds in the FIXED rank order ((r0 + r1) + (r2 + r3)) in "
      "FP32 RNE with +0 canonical (the qualified add pipe), which is the top two levels of the golden's csum tree "
      "whenever each die's partial is a power-of-two-aligned subtree (section 7).  No op may reorder: the engine "
      "applies records in rank order regardless of arrival.  Faults: seq mismatch, a rank missing past a "
      "timeout, n mismatch between ranks.  Die side (Claude, rtl/chip/ot_chip_v41x_die.sv): the core's COLL "
      "request port (valid, op, n, seq, a read port of coll_n elements, a write port) is wired to u_cdma, "
      "which already serialises words to u_coll and writes the result back; cfg_rank and the group id come from "
      "the package controller's CSRs.\n")
    w("## 9. Every layer type against the proposed widths\n")
    w("| layer type | instr | " + " | ".join(f"largest count @ {c:,}" for c in contexts) +
      " | xu_k | KV elements @ " + f"{contexts[0]:,}" + " | ROM share GB | verdict |\n|---|---|" +
      "---|" * len(contexts) + "---|---|---|---|")
    for lab, L in kinds:
        cm = [max(v for k, v in per[lab][str(c)].items() if k != "xu_k") for c in contexts]
        xk = max(per[lab][str(c)]["xu_k"] for c in contexts)
        kvt = kv[(contexts[0], lab)]["total_elems"]
        verdicts = [_chk(c_, 21) for c_ in cm] + [_chk(xk, 12), _chk(kvt, 30)]
        worst = "INSUFFICIENT" if "INSUFFICIENT" in verdicts else "BARELY" if "BARELY" in verdicts else "ok"
        w(f"| {lab} | {per[lab]['instructions']} | " + " | ".join(f"{c_:,}" for c_ in cm) +
          f" | {xk:,} | {kvt:,} | {rom[lab] / 1e9:.3f} | {worst} |")
    w("\nBARELY items: the token (129,279 of 131,071 at TW = 17), POS1 / T1 / T2 at 1M (1,049,088 of 2,097,151 at "
      "N = 21; the position itself, 1,048,575, has 2x), xu_k 2,048 of 4,095, KV elements on the ratio-1 dies at 1M "
      "(one user), DYN EMBED (token x 5,120 = 661,908,480 of 2^30) and ROW1 (2^29 of 2^30).  Nothing is "
      "insufficient at one user per die; multi-user KV needs word addressing or a separate user base.\n")
    data = {"per_layer_type": per, "vm_resident_elements": vm_res, "kv": {f"{c}/{l}": v for (c, l), v in kv.items()},
            "rom_bytes_per_die_layer": rom, "instr_bits_now": used_now, "instr_bits_proposed": used_new,
            "proposed": PROPOSED}
    return "\n".join(md) + "\n", data


GATE = "/tmp/claude-1000/remote_gate.sh"
GATE_ENV = {"OT_GATE_EXCLUDE": "ot-pve1,155.103.253.114"}


def rtl_shards(blk: dict, golden: dict) -> dict:
    """The RTL shard of every golden shard.  Refused while blockers() locates a blocking row: no full-shape layer
    program or image can be expressed for the adopted die, so there is nothing a simulator could run.  When the
    blockers clear, a shard runs as `remote_gate.sh <this tool> --steps rtl-one --layer L --context C` with
    OT_GATE_MIN_GB = 1.3 x the pilot shard's measured peak RSS (GATE_ENV excludes the hosts outside this half)."""
    out = {}
    for ctx, g in golden.items():
        for s in g["layers"]:
            out[f"{ctx}/L{s['layer']:02d}"] = {"status": "blocked" if blk["blocking"] else "not_run",
                                               "blocked_by": blk["blocking"]}
    return out


def assemble(scratch: Path, blk: dict, cyc: dict, output: Path) -> dict:
    import hdc_replay_v41 as R
    golden = {}
    for f in sorted(scratch.glob("golden_ctx*_*.json")):
        g = json.loads(f.read_text())
        cur = golden.setdefault(str(g["context"]), {k: v for k, v in g.items() if k != "layers"} | {"layers": []})
        have = {s["layer"] for s in cur["layers"]}
        cur["layers"] += [s for s in g["layers"] if s["layer"] not in have]
        if "head" in g:
            cur["head"] = g["head"]
    for g in golden.values():
        g["layers"].sort(key=lambda s: s["layer"])
    rtl = rtl_shards(blk, golden)
    per_layer = {}
    for ctx, g in golden.items():
        mc = cyc["by_context"].get(ctx, {}).get("per_layer_kind", {})
        rows = []
        for s in g["layers"]:
            kind = layer_kind(s["layer"])
            rows.append({"layer": s["layer"], "kind": s["kind"], "program_kind": kind,
                         "golden_input_sha256": s["input_sha256"], "golden_output_sha256": s["output_sha256"],
                         "experts": s["experts"], "golden_wall_s": s["golden_wall_s"],
                         "rtl": rtl[f"{ctx}/L{s['layer']:02d}"],
                         "design_point_model_cycles": mc.get(kind, {}).get("design_point_cycles"),
                         "as_built_width_cycles_estimate": mc.get(kind, {}).get("as_built_width_cycles_estimate")})
        per_layer[ctx] = rows
    token = {}
    for ctx, c in cyc["by_context"].items():
        kinds = c["per_layer_kind"]
        s_dp = sum(kinds[layer_kind(L)]["design_point_cycles"] for L in range(40))
        s_ab = sum(kinds[layer_kind(L)]["as_built_width_cycles_estimate"] for L in range(40))
        token[ctx] = {
            "rtl_token_cycles": None,
            "rtl_token_cycles_note": "not composed: no RTL shard ran (every shard blocked)",
            "design_point_model": {"per_die_layer_cycles_sum": s_dp,
                                   "token_compute_cycles_whole_program": c["design_point_token_compute_cycles"],
                                   "us_per_token_incl_comm": c["design_point_us_per_token"],
                                   "comm_us_added": c["design_point_comm_us"],
                                   "label": "MODEL (tools/hdc_timing_v41x at spec widths + the DAG's collective / "
                                            "hop terms), not RTL"},
            "as_built_width_estimate_layer_cycles_sum": s_ab,
            "as_built_estimate_label": "hdc_replay_v41.simulate Cfg() on the per-die shipped program: sizes the RTL "
                                       "shards' simulated cycles (the adopted RTL's widths are MG = 8, SUN = 16, ...)"}
    tool = Path(__file__)
    srcs = [tool, ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_replay_v41.py",
            ROOT / "tools/hdc_timing_v41x.py", ROOT / "tools/hdc_isa_v41.py", CORE, TILE, DIE, CONFIG]
    rec = {
        "schema": SCHEMA,
        "tool": str(tool.relative_to(ROOT)),
        "question": "the V4.1-Flash ROM headline from bit-exact RTL simulation at FULL model shape, layer-sharded",
        "decomposition": {
            "shard": "one backbone layer of one decode token at one context position on one layer die",
            "shard_input": "the golden's exact layer input (h [4, 5120], pre [4], position, token history, the "
                           "index selection / candidate blocks carried from the source layers) and the layer's "
                           "KV / index state",
            "shard_check": "the layer output (h, pre), the appended KV / index rows and the transients, bit for bit",
            "golden_order": "one sequential full-shape golden pass per token (layer L's output is L+1's input)",
            "tensor_group": "one die of the tp = 4 group with a bit-exact collective model (the other ranks' "
                            "partial sums from the golden, combined in the one-shot collective's fixed rank order); "
                            "not the 4-die group, which quadruples memory without new arithmetic",
            "state": "SYNTHETIC BUT GOLDEN-CONSISTENT at 1M / 200K (a real 1M prefill is infeasible): rows made by "
                     "the golden's own quantisers in the stored formats, the context's row counts; the token is "
                     "then exact on that state",
            "weights": "the RELEASED checkpoint (48 shards, memory-mapped; a layer reads its own tensors and the "
                       "6 routed experts its router picks)",
            "token_composition": "sum over the 40 layer shards on the critical path + the design point's collective "
                                 "and stage-hop terms (labelled model) + the head"},
        "golden": golden_pin(), "arith": V.ARITH,
        "golden_shards": golden, "per_layer": per_layer, "rtl_feasibility": blk, "model_cycles": cyc,
        "token": token,
        "status": "golden_shards_only" if blk["blocking"] else "rtl_pending",
        "claim_boundary": (
            "Full-shape GOLDEN layer shards of the released checkpoint are computed (inputs and outputs pinned by "
            "digest). No full-shape RTL shard ran: the adopted die cannot express a full-shape layer (see "
            "rtl_feasibility.rows, each with its file:line evidence and the proposed change; all but the ROM depth "
            "are in Codex-owned ISA / core / program files). Cycle figures here are MODEL figures, labelled; no "
            "RTL cycle count at full shape exists yet. The KV / index state is synthetic (format-consistent), not "
            "from a prefill."),
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                        cwd=ROOT).stdout.strip(),
        "source_dirty": bool(subprocess.run(["git", "status", "--porcelain", "--", *map(str, srcs)],
                                            capture_output=True, text=True, cwd=ROOT).stdout.strip()),
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in srcs},
        "checkpoint": {"snapshot": str(HF.name), "index_sha256": hashlib.sha256(
            (HF / "model.safetensors.index.json").read_bytes()).hexdigest()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def parse_layers(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--steps", default="golden")
    ap.add_argument("--contexts", default="1048576")
    ap.add_argument("--layers", default="0-39")
    ap.add_argument("--scratch", type=Path, default=Path(os.environ.get("OT_SCRATCH", "/tmp")) / "v41_fullshape")
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--rank", type=int, default=0, help="images: the die's rank in its tensor group")
    ap.add_argument("--all-experts", action="store_true", help="images: every routed expert, not only the token's")
    ap.add_argument("--constraints-md", type=Path, default=Path("/tmp/claude-1000/v41_fullshape_layer0_constraints.md"))
    a = ap.parse_args()
    steps = a.steps.split(",")
    a.scratch.mkdir(parents=True, exist_ok=True)
    if "golden" in steps:
        for ctx in map(int, a.contexts.split(",")):
            r = golden_token(ctx, parse_layers(a.layers), a.scratch)
            (a.scratch / f"golden_ctx{ctx}_{a.layers}.json").write_text(json.dumps(r, indent=1) + "\n")
    if "images" in steps:
        for ctx in map(int, a.contexts.split(",")):
            for L in parse_layers(a.layers):
                images(ctx, L, a.rank, a.scratch, a.scratch / "images" / f"ctx{ctx}_L{L:02d}_r{a.rank}",
                       all_experts=a.all_experts)
    if "constraints" in steps:
        md, _ = constraints(tuple(map(int, a.contexts.split(","))))
        a.constraints_md.write_text(md)
        print("wrote", a.constraints_md)
    if "assemble" in steps:
        ctxs = tuple(map(int, a.contexts.split(",")))
        rec = assemble(a.scratch, blockers(ctxs), model_cycles(ctxs), a.output)
        print(rec["status"], "blocking:", rec["rtl_feasibility"]["blocking"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
