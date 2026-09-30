#!/usr/bin/env python3
"""K-split ROM bank map for every DeepSeek-V4.1 layer die (W10 build item 1, model row_split="ksplit").

    python3 tools/v41_rom_ksplit_bankmap.py --snapshot <HF snapshot dba1be0a...> \
        --output results/uarch/v41_rom_ksplit_bankmap.json

Successor of tools/v41_rom_striped_bankmap.py (whole rows; FAIL recorded at f02e4600).  The model
(tools/uarch_model.py price_matvec, row_split="ksplit") splits each row's K over up to s macros in
power-of-two-aligned runs of golden chunks (8 blocks of 32 = 256 elements), s doubling while rows*s < macros
and s < chunks; partials are added in golden csum padded-tree order on the way back.

SEGMENTS.  Golden csum (tools/hdc_golden_v41.py) is exact for any engine that sums power-of-two-ALIGNED runs of
chunks and combines them by the same padded tree.  A row of C chunks split s ways uses segments of
c = next_pow2(ceil(C / s)) chunks: ceil(C / c) segments, all of c chunks but the last.  The model's
seg_words = ceil(ceil(K / s) / wpw) is an even split, which is not aligned when C is not a power of two.

UNITS AND WORDS.  A lane accumulates golden chunks (sequential from +0), one term per word:
  FP8  unit = one 256-element chunk; word = one 32-block (lane 0).
  FP4  unit = a chunk PAIR (2p, 2p+1); word = {block b of chunk 2p+1 | block b of chunk 2p} (lanes 1, 0).
  BF16 unit = a lane group of 16 golden BF16 chunks (8 products each, 128 elements); word = element b of each.
A unit is 8 words, b = 0..7.

ELEMENT READ ORDER (element_order; each segment's words are contiguous at its own base in the order the element
reads them, segment_order):
  for sub-block q (unit index j within its segment, 8q <= j < 8q + 8):
    for b in 0..7:
      for each class (segments with equal (e0, elems, fmt)) in ascending e0: for unit j in the sub-block:
        for each segment of the class by row: word (segment, j, b)
Every chain (unit, lane) is revisited once per round (q, b); a round lasts at least 5 cycles (the FP32 adder
recurrence), so one pipelined adder per lane and IL = 8 chain registers per lane suffice.

X STREAM.  The vector memory reads 64 elements per cycle.  In round (q, b) it streams, for every distinct unit
(K position) needed in the sub-block, the x slice that word b uses (FP8: 2 units per beat, FP4: 1, BF16: 4),
in ascending K; every element's reads are a subsequence of that stream.  Round length
r_q = max(5, ceil(distinct units / per-beat), most words any element reads in the round); a phase takes
8 * sum_q r_q cycles per format, and a phase mixing FP8 and BF16 matrices streams x once per format.

PLACEMENT.  Dense phases: segments largest first, each batch to the macros with the fewest words in that phase
(then most free depth, then lowest id).  BF16 matrices only on the 2,048 BF16 macros floor(i * N / 2048).
Routed experts: the split is chosen per expert (one expert's rows x segments cover the field, T = 1 tile);
expert j's tile starts at j * tile mod N and wraps round the field, so active experts spread over every macro
(a macro may hold segments of several experts at different K ranges: up to 7 classes with the shared expert,
within the element's 8).  A segment-major banded map (one K range per macro) was measured and rejected: it
collides more (down t_read 45.6 vs 38 on the busiest die).  Active experts are data-dependent: reported as
the mean over draws of six active experts per die-layer (the model's case) and of the true occupancy.

Reported per phase: t_read = most words any macro reads (the model's t_read) and t_phase = the stream-round
cycles above (the element array's issue time), each against the model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_floorplan_die_macromap as M  # noqa: E402

DEPTH = 8192
BF16_MACROS = 2048                  # uarch_model PRESETS['proposal'] (92879e95)
CHUNK_EL = 256
IL = 8                              # chain registers per lane = units per sub-block
# BF16_PAIR (root decision 2026-09-30): BF16 weights on the standard FP8/FP4 pair.  A BF16 word (16 weights)
# is held BF16_WORD_CYCLES cycles and multiplied 2 per cycle per macro into the pair's two chunk chains
# (NCH = 16 slots each), so a BF16 sub-block is IL_BF16 = 2 units (16 chunk slots per lane) and every macro
# may carry BF16.  Off by default so the committed records keep their meaning (--bf16-pair).
BF16_PAIR = False
BF16_WORD_CYCLES = 8
BF16_CAP = 0                        # BF16_PAIR: max BF16 words in flight per element per round (0 = no cap)
BF16_SPLIT_BOOST = 0                # 0: the model's split; 1: split BF16 rows as if each word were 8 (BF16_PAIR)
IL_BF16 = 2


def il(fmt: str) -> int:
    """Units per sub-block of a format's family."""
    return IL_BF16 if (BF16_PAIR and fmt == "bf16") else IL
FADD_REC = 5                        # ot_fp32_add_rne_pipe recurrence
SLOTS = {"fp8": 1, "fp4": 2, "bf16": 16}
EXPERT_ROWS = {"w1": (576, 5120), "w3": (576, 5120), "w2": (1280, 2304)}   # rank quarter (rows, K)
# ADOPTED (root, 2026-09-29): W1 macro PAIRS share one element front end (ot_v41_rom_elem NB = 2) and hold one
# segment structure for two rows.  The bank map therefore places "super rows" (rows 2R, 2R+1) on pair slots:
# N macros -> floor(N / 2) pair slots, the BF16 subset likewise halved; words per macro are unchanged.
PAIR = 2
EXPERT = {k: (-(-r // PAIR), K) for k, (r, K) in EXPERT_ROWS.items()}
TOPK, N_EXPERTS = 6, 384
PHASE = {
    "attn.wq_a.weight": "a_proj", "attn.wkv.weight": "a_proj", "attn.indexer.weights_proj.weight": "a_proj",
    "attn.compressor.wkv.weight": "a_proj", "attn.compressor.wgate.weight": "a_proj",
    "attn.wq_b.weight": "wq_b", "attn.indexer.wq_b.weight": "wq_b", "attn.indexer.wk.weight": "cmp.wk",
    "attn.wo_a.weight": "wo_a", "attn.wo_b.weight": "wo_b", "ffn.gate.weight": "router",
    "ffn.shared_experts.w1.weight": "shared_gu", "ffn.shared_experts.w3.weight": "shared_gu",
    "ffn.shared_experts.w2.weight": "down",
}
# the model's a_proj is output-split (tools/decode_critical_path.py "... compressor wkv, wgate, output-split");
# W1's macromap keeps these conservatively replicated.  The model's partition is used here.
MODEL_QUARTER = {"attn.compressor.wkv.weight", "attn.compressor.wgate.weight"}
PERM = None                          # baseline: slot index -> an arbitrary pair position (seeded permutation)
PHASES = ("a_proj", "wq_b", "cmp.wk", "wo_a", "wo_b", "router", "shared_gu", "experts_gu", "down")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def npow2(x: int) -> int:
    return 1 << max(0, math.ceil(math.log2(max(1, x))))


def bf16_set(n: int, nb: int) -> np.ndarray:
    return np.unique((np.arange(nb, dtype=np.int64) * n) // nb)


# ---------------------------------------------------------------------------------------------------------
# segments, units, word layout
# ---------------------------------------------------------------------------------------------------------
def model_split(rows: int, K: int, n: int, fmt: str = "fp8") -> int:
    """The model's s (tools/uarch_model.striped_read, row_split="ksplit").  FP4 caps s so segments stay whole
    chunk PAIRS (c >= 2): an FP4 word carries block b of two sibling chunks, and a one-chunk FP4 segment
    would leave half of every word empty (W10 finding, reported to the model)."""
    C = math.ceil(K / CHUNK_EL)
    s = 1
    while s < C and rows * s < n:
        s *= 2
    s = min(s, npow2(C))
    if fmt == "fp4":
        s = min(s, max(1, npow2(C) // 2))
    return s


def segments(K: int, s: int) -> list[tuple[int, int]]:
    """Golden-aligned segments (first element, elements) of a row of K split s ways."""
    C = math.ceil(K / CHUNK_EL)
    c = npow2(math.ceil(C / s))
    return [(i * c * CHUNK_EL, min(c * CHUNK_EL, K - i * c * CHUNK_EL)) for i in range(math.ceil(C / c))]


def unit_range(fmt: str, e0: int, elems: int) -> tuple[int, int]:
    """Global x units [u0, u1) a segment touches: chunk PAIRS (512 elements) for FP8 and FP4, which share
    the FP8-quantised x stream; 128-element lane groups for BF16."""
    u = 128 if fmt == "bf16" else 512
    return e0 // u, -(-(e0 + elems) // u)


def seg_units(fmt: str, e0: int, elems: int) -> int:
    u0, u1 = unit_range(fmt, e0, elems)
    return u1 - u0


def unit_halves(fmt: str, e0: int, elems: int, u: int) -> list[int]:
    """Words of unit u (per b): FP8 one per chunk of the pair inside the segment (half 0, 1); FP4 and BF16 one."""
    if fmt != "fp8":
        return [0]
    return [h for h in (0, 1) if e0 <= u * 512 + h * 256 < e0 + elems]


def seg_words(fmt: str, e0: int, elems: int) -> int:
    u0, u1 = unit_range(fmt, e0, elems)
    return 8 * sum(len(unit_halves(fmt, e0, elems, u)) for u in range(u0, u1))


def word_slots(fmt: str, e0: int, elems: int, u: int, b: int, h: int = 0) -> list[int]:
    """Row-relative element offset of each slot of word (u, b, half h) (-1 = empty slot)."""
    lo, hi = e0, e0 + elems
    if fmt == "fp8":
        e = u * 512 + h * 256 + b * 32
        return [e if lo <= e < hi else -1]
    if fmt == "fp4":
        return [(e if lo <= e < hi else -1) for e in (u * 512 + b * 32, u * 512 + 256 + b * 32)]
    return [(e if lo <= e < hi else -1) for e in (u * 128 + lane * 8 + b for lane in range(16))]


def family(fmt: str) -> str:
    return "bf16" if fmt == "bf16" else "q"


def segment_order(fmt: str, e0: int, elems: int) -> list[tuple[int, int, int]]:
    """(unit, b, half) of every word of one segment in address order: the segment's words are contiguous
    at its base, in the order the element reads them -- sub-block q (8 units), b, unit, FP8 half."""
    u0, u1 = unit_range(fmt, e0, elems)
    out = []
    L = il(fmt)
    for q0 in range(u0, u1, L):
        for b in range(8):
            for u in range(q0, min(u1, q0 + L)):
                for h in unit_halves(fmt, e0, elems, u):
                    out.append((u, b, h))
    return out


def element_order(segs: list[dict]) -> list[tuple[int, int, int, int]]:
    """(segment index, unit, b, half) in the order the element issues a phase's words: sub-block q, b, class
    (segments sharing a unit range; a macro's classes are disjoint) in ascending unit, unit, the class's
    segments by (fmt, row, tensor), FP8 half.  One captured x slice serves every word of a (class, unit, b);
    each segment's words come out in its own address order (segment_order)."""
    out = []
    cls = {}
    for i, sg in enumerate(segs):
        cls.setdefault(unit_range(sg["fmt"], sg["e0"], sg["elems"]), []).append(i)
    keys = sorted(cls)
    for ids in cls.values():
        ids.sort(key=lambda i: (segs[i]["fmt"], segs[i]["row"], segs[i]["tensor"]))
    for (a0, a1), (b0, b1) in zip(keys, keys[1:]):
        assert a1 <= b0, ("overlapping classes on one macro", keys)
    L = il(segs[0]["fmt"])
    assert len({family(sg["fmt"]) for sg in segs}) == 1, "one x family per phase"
    nq = max(-(-(u1 - u0) // L) for u0, u1 in keys)
    for q in range(nq):
        for b in range(8):
            for u0, u1 in keys:
                for u in range(u0 + L * q, min(u1, u0 + L * q + L)):
                    for i in cls[(u0, u1)]:
                        sg = segs[i]
                        for h in unit_halves(sg["fmt"], sg["e0"], sg["elems"], u):
                            out.append((i, u, b, h))
    return out


def element_needs(segs_fmt: dict[str, list[tuple[int, int, int, int]]]) -> dict:
    """What one phase asks of the busiest element: segments and classes per element, words per round per
    element (chain registers per lane: FP8/FP4 NCH, BF16 NCHB), units per class (sub-blocks) and base nodes per
    segment (segment-tree levels LV: FP8 chunks, FP4 chunk pairs, BF16 lane groups)."""
    per = {}
    for fmt, lst in segs_fmt.items():
        for m, e0, el, _ in lst:
            per.setdefault((family(fmt), m), []).append((fmt, e0, el))
    out = dict(segments=0, classes=0, words_per_round=0, units_per_class=0, base_nodes=0, chain_slots_per_lane=0)
    for (f, m), lst in per.items():
        out["segments"] = max(out["segments"], len(lst))
        cls = {}
        for fmt, e0, el in lst:
            cls.setdefault(unit_range(fmt, e0, el), []).append((fmt, e0, el))
            nodes = -(-el // 256) if fmt == "fp8" else seg_units(fmt, e0, el)
            if BF16_PAIR and fmt == "bf16":
                nodes *= BF16_WORD_CYCLES        # BF16_PAIR: 16 / multipliers chunks per base node
            out["base_nodes"] = max(out["base_nodes"], nodes)
        out["classes"] = max(out["classes"], len(cls))
        # words in the first round (the largest: sub-block 0 holds min(8, units) of every class)
        w = 0
        for (u0, u1), members in cls.items():
            out["units_per_class"] = max(out["units_per_class"], u1 - u0)
            for fmt, e0, el in members:
                w += sum(len(unit_halves(fmt, e0, el, u)) for u in range(u0, min(u1, u0 + il(fmt))))
        out["words_per_round"] = max(out["words_per_round"], w)
        # chain registers per lane the round needs (a BF16_PAIR word spreads over 8 slots per lane)
        slots = (min(w, BF16_CAP) if (BF16_PAIR and f == "bf16" and BF16_CAP) else w) \
            * (BF16_WORD_CYCLES if (BF16_PAIR and f == "bf16") else 1)   # each chain takes `hold` terms per word
        out["chain_slots_per_lane"] = max(out.get("chain_slots_per_lane", 0), slots)
    return out


def merge_needs(a: dict, b: dict) -> dict:
    return {k: max(a.get(k, 0), b.get(k, 0)) for k in set(a) | set(b)}


def phase_cycles(segs_fmt: dict[str, list[tuple[int, int, int, int]]]) -> int:
    """Stream-round cycles of one phase.  segs_fmt[fmt] = [(macro, e0, elems, _)].

    FP8 and FP4 weights both multiply the same FP8-quantised x (golden linear_q); a round (q, b) streams block
    b of both chunks of every needed pair, one pair per beat, and serves both formats.  BF16 (golden mv:
    BF16 x, per-element chunks) is a second stream of 4 lane groups per beat.
    r_q = max(5, beats, most words any element reads in the round); a phase costs 8 * sum_q r_q per stream."""
    total = 0
    fam = {"q": [], "bf16": []}
    for fmt, segs in segs_fmt.items():
        for m, e0, el, _ in segs:
            fam[family(fmt)].append((m, fmt, e0, el))
    for f, segs in fam.items():
        if not segs:
            continue
        info = []
        for m, fmt, e0, el in segs:
            u0, u1 = unit_range(fmt, e0, el)
            info.append((m, u0, [len(unit_halves(fmt, e0, el, u)) for u in range(u0, u1)]))
        L = il("bf16" if f == "bf16" else "fp8")
        nq = max(-(-len(w) // L) for _, _, w in info)
        for q in range(nq):
            need = set()
            demand = {}
            for m, u0, w in info:
                part = w[L * q: L * q + L]
                if not part:
                    continue
                need.update(range(u0 + L * q, u0 + L * q + len(part)))
                demand[m] = demand.get(m, 0) + sum(part)
            if not need:
                continue
            beats = -(-len(need) // 4) if f == "bf16" else len(need)
            hold = BF16_WORD_CYCLES if (BF16_PAIR and f == "bf16") else 1
            if BF16_PAIR and f == "bf16" and BF16_CAP:
                # at most BF16_CAP words in flight per element (chain slots): an element's round words go in
                # groups of BF16_CAP, and the x slices of the round are re-streamed for every group
                G = max(-(-d // BF16_CAP) for d in demand.values())
                for g in range(G):
                    dg = max(min(BF16_CAP, d - BF16_CAP * g) for d in demand.values())
                    total += 8 * max(FADD_REC, beats, hold * dg)
                continue
            total += 8 * max(FADD_REC, beats, hold * max(demand.values()))
    return total


# ---------------------------------------------------------------------------------------------------------
# dies
# ---------------------------------------------------------------------------------------------------------
def dense_matrices(entries: list[dict], layer: int) -> list[dict]:
    out = []
    for e in entries:
        local = e["tensor"].split(f"layers.{layer}.")[1]
        if local not in PHASE:
            continue
        if e["dtype"] == "F8_E4M3":
            rows, K = e["rank_shape"]
            fmt = "bf16" if local == "attn.wo_a.weight" else "fp8"
        else:
            assert e["dtype"] == "BF16", e
            rows, K = e["source_shape"]
            if e["split"] == "program_declared_output_row_quarter" or local in MODEL_QUARTER:
                rows //= 4
            fmt = "bf16"
        out.append(dict(tensor=e["tensor"], phase=PHASE[local], fmt=fmt, rows=-(-rows // PAIR), K=K,
                        real_rows=rows))
    return out


class Die:
    def __init__(self, n: int, nb: int):
        self.n = n
        self.bf = bf16_set(n, nb)
        self.fill = np.zeros(n, dtype=np.int64)
        self.segs = []            # dict(tensor, fmt, K, row, e0, elems, macro, inst)
        self.regions = []         # dict(inst, macro, base, words, seg_ids)

    def close_instance(self, inst: str, ids: list[int]):
        """Give every macro holding segments of `inst` one contiguous region, in element read order."""
        by_m = {}
        for i in ids:
            by_m.setdefault(self.segs[i]["macro"], []).append(i)
        for m, sids in sorted(by_m.items()):
            base = int(self.fill[m])
            for i in sids:                       # each segment contiguous, in its own read order
                sg = self.segs[i]
                sg["base"] = int(self.fill[m])
                self.fill[m] += seg_words(sg["fmt"], sg["e0"], sg["elems"])
            self.regions.append(dict(inst=inst, macro=m, base=base, words=int(self.fill[m]) - base, seg_ids=sids))


def lpt(die: Die, allowed: np.ndarray, load: np.ndarray, count: int, w: int, blocked=None) -> np.ndarray:
    """`count` equal segments to the least-loaded allowed macros; `blocked` (bool per macro) excludes macros
    already holding an overlapping but different unit range in this phase (an element's classes are
    disjoint)."""
    if blocked is not None and blocked[allowed].any():
        allowed = allowed[~blocked[allowed]]
    assert len(allowed) > 0
    out = np.empty(count, dtype=np.int64)
    got = 0
    while got < count:
        order = np.lexsort((allowed, die.fill[allowed], load[allowed]))
        lvl = load[allowed[order]]
        k = min(count - got, int(np.searchsorted(lvl, lvl[0], side="right")))
        take = allowed[order[:k]]
        out[got:got + k] = take
        load[take] += w
        got += k
    return out


# ---------------------------------------------------------------------------------------------------------
# distance-aware placement (root 2026-09-30, a free fix: ROM contents only).  Slot j of a die is the j-th nearest
# pair to the x-broadcast root / return sink (the floorplan's distributed-VM port).  A latency-critical low-work
# phase is confined to the nearest M slots, M the smallest power-of-two fraction of the die whose stream-round
# time equals the whole-die placement's, so its farthest pair (the op's wire latency) shrinks at no issue cost.
# ---------------------------------------------------------------------------------------------------------
NEAR = False
CRITICAL = ("a_proj", "wq_b", "cmp.wk", "wo_b", "router")
REACH_UM = 504.0                     # W15: SS register-to-register reach at 0.833 ns
GATHER_SCATTER = 12                  # the model's VM x-gather + return-scatter stages (6 + 6)
SLOT_XY = None                       # [(x_um, y_um, distance_um)] of slot j (the farther macro of its pair)
SLOT_DIST = None                     # np.array: distance (um) of the j-th nearest pair slot


def wire_cycles_um(L: float) -> int:
    return 2 * math.ceil(L / REACH_UM) + GATHER_SCATTER


def load_geometry(path: Path):
    """Pair-slot distances from a floorplan pack record: every ROM_MAC.* macro pair, Manhattan distance from the
    x-broadcast root (the far-expert crossing's source) to the pair's centre, ascending."""
    r = json.loads(path.read_text())
    root = next(c for c in r["latency_crossings"]["crossings"] if "ROM_MAC.expert" in c["crossing"])["from_um"]
    ms = [i for i in r["instances"] if i[5].startswith("ROM_MAC.")]
    w = 125.712
    pts = sorted((abs(i[2] + w / 2 - root[0]) + abs(i[3] + 60 - root[1]), i[2] + w / 2, i[3] + 60) for i in ms)
    global SLOT_XY
    SLOT_XY = [(round(p[1], 1), round(p[2], 1), round(p[0], 1)) for p in pts[1::2]]   # (x, y, distance) per slot
    return np.array([p[0] for p in pts[1::2]]), root      # one distance per pair (the farther half)


def place_dense(die: Die, mats: list[dict], layer: int):
    res, info = {}, {}
    for ph in PHASES:
        ms = [m for m in mats if m["phase"] == ph]
        if not ms:
            continue
        if NEAR and ph in CRITICAL and SLOT_DIST is not None:
            snap = (die.fill.copy(), len(die.segs), len(die.regions))
            full, _ = _place_phase(die, ms, layer, ph, die.n, {})
            best = die.n
            # candidates: sixteenths of the die, then powers of two below; keep the smallest that costs nothing
            cands = sorted({die.n * k // 16 for k in range(1, 16)} | {die.n >> k for k in range(5, 10)}, reverse=True)
            for M in cands:
                if M < 32:
                    continue
                die.fill[:] = snap[0]; del die.segs[snap[1]:]; del die.regions[snap[2]:]
                try:
                    trial, _ = _place_phase(die, ms, layer, ph, M, {})
                except AssertionError:
                    continue
                if trial["t_phase"] <= full["t_phase"] and int(die.fill[:M].max()) <= DEPTH:
                    best = min(best, M)
            die.fill[:] = snap[0]; del die.segs[snap[1]:]; del die.regions[snap[2]:]
            r_, inf = _place_phase(die, ms, layer, ph, best, info)
            r_["near_slots"] = best
            res[ph] = r_
            continue
        r_, _ = _place_phase(die, ms, layer, ph, die.n, info)
        res[ph] = r_
    return res, info


def _place_phase(die: Die, ms: list[dict], layer: int, ph: str, M: int, info: dict):
    if True:
        load = np.zeros(die.n, dtype=np.int64)
        items = []
        for m in ms:
            n_set = len(die.bf) if m["fmt"] == "bf16" else die.n
            n_set = min(n_set, M)
            if BF16_PAIR and m["fmt"] == "bf16":
                n_set *= BF16_WORD_CYCLES if BF16_SPLIT_BOOST else 1     # a BF16 word costs 8 read cycles: split further
            s = model_split(m["rows"], m["K"], n_set, m["fmt"])
            segs = segments(m["K"], s)
            info[m["tensor"]] = dict(rows=m["rows"], K=m["K"], fmt=m["fmt"], s_model=s,
                                     segment_elems=[x[1] for x in segs])
            cost = BF16_WORD_CYCLES if (BF16_PAIR and m["fmt"] == "bf16") else 1     # read cycles per word
            for si, (e0, el) in enumerate(segs):
                items.append((cost * seg_words(m["fmt"], e0, el), m, si, e0, el))
        items.sort(key=lambda t: (-t[0], t[1]["tensor"], t[2]))
        ids = []
        held = {}                                # unit range -> macros holding it in this phase
        for w, m, si, e0, el in items:
            allowed = die.bf if m["fmt"] == "bf16" else np.arange(die.n)
            allowed = allowed[allowed < M]
            rng = (family(m["fmt"]),) + unit_range(m["fmt"], e0, el)
            blocked = np.zeros(die.n, dtype=bool)
            for (f2, a0, a1), ms_ in held.items():
                if f2 == rng[0] and (a0, a1) != rng[1:] and a0 < rng[2] and rng[1] < a1:
                    blocked[ms_] = True
            mac = lpt(die, allowed, load, m["rows"], w, blocked)
            held[rng] = np.unique(np.concatenate([held.get(rng, np.zeros(0, np.int64)), mac]))
            for r in range(m["rows"]):
                ids.append(len(die.segs))
                die.segs.append(dict(tensor=m["tensor"], fmt=m["fmt"], K=m["K"], row=r, e0=e0, elems=el,
                                     macro=int(mac[r]), seg=si))
        inst = f"L{layer}.{ph}"
        die.close_instance(inst, ids)
        by_fmt = {}
        for i in ids:
            s = die.segs[i]
            by_fmt.setdefault(s["fmt"], []).append((s["macro"], s["e0"], s["elems"], 0))
        used = sorted({x[0] for lst in by_fmt.values() for x in lst})
        far = None
        if SLOT_DIST is not None:
            dd = SLOT_DIST[np.minimum(np.array(used), len(SLOT_DIST) - 1)] if NEAR else \
                SLOT_DIST[np.minimum(PERM[np.array(used)], len(SLOT_DIST) - 1)]
            far = float(dd.max())
        return dict(t_read=int(load.max()), t_phase=phase_cycles(by_fmt), segs=by_fmt, needs=element_needs(by_fmt),
                    slots_used=len(used), farthest_um=far,
                    wire_cycles=None if far is None else wire_cycles_um(far)), info


def expert_tiles(die: Die, ranges: list[dict]):
    n = die.n
    spec = {}
    for fam in ("gu", "down"):
        rows, K = (EXPERT["w1"][0] * 2, EXPERT["w1"][1]) if fam == "gu" else EXPERT["w2"]
        s = model_split(rows, K, n, "fp4")       # the model splits ONE expert's rows over the field (92879e95)
        segs = segments(K, s)
        spec[fam] = dict(rows=rows, K=K, s_model=s, segs=segs, tile=rows * len(segs),
                         T=max(1, n // (rows * len(segs))))
    tables, j = [], 0
    for r in ranges:
        ids = list(range(r["first"], r["last"] + 1))
        per = []
        for e in ids:
            ent = {}
            for fam, sp in spec.items():
                tile, T = sp["tile"], sp["T"]
                base = (j % T) * tile if T > 1 else (j * tile) % n    # T = 1: tiles wrap round the field
                rot = ((j // T) * sp["rows"]) % tile if T > 1 else 0
                sids = []
                for si, (e0, el) in enumerate(sp["segs"]):
                    pos = (base + (rot + si * sp["rows"] + np.arange(sp["rows"])) % tile) % n
                    for rr in range(sp["rows"]):
                        if fam == "gu":
                            h1 = EXPERT["w1"][0]
                            t_name, row = ("w1", rr) if rr < h1 else ("w3", rr - h1)
                        else:
                            t_name, row = "w2", rr
                        sids.append(len(die.segs))
                        die.segs.append(dict(tensor=f"layers.{r['layer']}.ffn.experts.{e}.{t_name}", fmt="fp4",
                                             K=sp["K"], row=row, e0=e0, elems=el, macro=int(pos[rr]), seg=si))
                die.close_instance(f"L{r['layer']}.E{e}.{fam}", sids)
                ent[fam] = [(die.segs[i]["macro"], die.segs[i]["e0"], die.segs[i]["elems"], 0) for i in sids]
            per.append(ent)
            j += 1
        tables.append(dict(layer=r["layer"], ids=ids, per=per))
    return tables, {k: {kk: v[kk] for kk in ("rows", "K", "s_model", "tile", "T")} |
                    {"segment_elems": [x[1] for x in v["segs"]]} for k, v in spec.items()}


def expert_phase(n, t, act, fam, extra):
    segs = [x for i in act for x in t["per"][i][fam]]
    load = np.zeros(n, np.int64)
    for m, e0, el, _ in segs:
        load[m] += seg_words("fp4", e0, el)
    by_fmt = {"fp4": segs}
    if extra:
        for f, lst in extra["segs"].items():
            by_fmt.setdefault(f, [])
            by_fmt[f] = by_fmt[f] + lst
            for m, e0, el, _ in lst:
                load[m] += seg_words(f, e0, el)
    return int(load.max()), phase_cycles(by_fmt), element_needs(by_fmt)


def expert_stats(n, t, shared_down, rng, draws):
    ne = len(t["ids"])
    out = {}
    for mode in ("model_six", "true_occupancy"):
        acc = {"gu_read": [], "gu_phase": [], "down_read": [], "down_phase": [], "k": []}
        needs = {}
        for _ in range(draws):
            if mode == "model_six":
                act = rng.choice(ne, size=min(TOPK, ne), replace=False)
            else:
                pick = set(rng.choice(N_EXPERTS, size=TOPK, replace=False).tolist())
                act = [i for i, e in enumerate(t["ids"]) if e in pick]
            g = expert_phase(n, t, act, "gu", None)
            d = expert_phase(n, t, act, "down", shared_down)
            acc["gu_read"].append(g[0]); acc["gu_phase"].append(g[1])
            needs = merge_needs(needs, merge_needs(g[2], d[2]))
            acc["down_read"].append(d[0]); acc["down_phase"].append(d[1]); acc["k"].append(len(act))
        out[mode] = {k: round(float(np.mean(v)), 2) for k, v in acc.items()}
        out[mode]["element_needs_max"] = needs
    return out


def check_exact_once(die: Die, expect: dict):
    """Segments tile every row's K exactly once; regions per macro disjoint, inside DEPTH, sized to their
    segments' words.  (tests/test_v41_rom_ksplit_bankmap.py checks word by word.)"""
    cover = {}
    for s in die.segs:
        cover.setdefault(s["tensor"], {}).setdefault(s["row"], []).append((s["e0"], s["elems"]))
    assert set(cover) == set(expect), set(cover) ^ set(expect)
    for name, (rows, K) in expect.items():
        c = cover[name]
        assert len(c) == rows and set(c) == set(range(rows)), name
        for r, iv in c.items():
            iv.sort()
            pos = 0
            for e0, el in iv:
                assert e0 == pos, (name, r, iv)
                pos += el
            assert pos == K, (name, r, pos, K)
    seen = np.zeros(len(die.segs), dtype=np.int64)
    for rg in die.regions:
        seen[rg["seg_ids"]] += 1
        assert all(die.segs[i]["macro"] == rg["macro"] for i in rg["seg_ids"])
    assert np.all(seen == 1)
    m = np.array([rg["macro"] for rg in die.regions])
    s = np.array([rg["base"] for rg in die.regions])
    e = s + np.array([rg["words"] for rg in die.regions])
    o = np.lexsort((s, m))
    m, s, e = m[o], s[o], e[o]
    same = m[1:] == m[:-1]
    assert np.all(s[1:][same] >= e[:-1][same]), "overlapping regions"
    return int(e.max())


def model_rows():
    rec = json.loads((ROOT / "results/uarch/v41_rom.json").read_text())
    row = next(r for r in rec["rows"] if r["design"] == "proposal")
    assert row["params"].get("row_split") == "ksplit", row["params"]
    return {v["key"]: v for v in row["layer20_matvecs"].values()}, row["params"]


def derive(snapshot: Path, draws: int, seed: int, only=None, keep=None):
    meta = M.Headers(snapshot)
    owners = json.loads(M.OWNERS.read_text())
    macromap = M.derive(snapshot, compact_woa=False)
    by_die = {d["die"]: d for d in macromap["layer_dies"]}
    rng = np.random.default_rng(seed)
    dies = []
    for stage in range(owners["stage_count"]):
        dense_layers = [o["layer"] for o in owners["layer_owners"] if o["dense_owner_stage"] == stage]
        ranges = [dict(layer=o["layer"], first=r["expert_ids"][0], last=r["expert_ids"][1])
                  for o in owners["layer_owners"] for r in o["routed_expert_candidate_owners"] if r["stage"] == stage]
        dense = {L: M.dense_entries(meta, L, False) for L in dense_layers}
        for rank in range(4):
            name = f"layer_s{stage:02d}_r{rank}"
            if only and name not in only:
                continue
            w1 = by_die[name]
            n_macros = w1["macros"][M.WIDE]
            n = n_macros // PAIR
            die = Die(n, n if BF16_PAIR else min(BF16_MACROS, n_macros) // PAIR)
            expect, per_layer, res_by_layer = {}, [], {}
            for L in dense_layers:
                mats = dense_matrices(dense[L], L)
                res, info = place_dense(die, mats, L)
                res_by_layer[L] = res
                expect.update({m["tensor"]: (m["rows"], m["K"]) for m in mats})
                per_layer.append(dict(layer=L, t_read={p: v["t_read"] for p, v in res.items()},
                                      t_phase={p: v["t_phase"] for p, v in res.items()},
                                      needs={p: v["needs"] for p, v in res.items()}, split=info,
                                      wire={p: dict(slots_used=v.get("slots_used"), near_slots=v.get("near_slots"),
                                                    farthest_um=v.get("farthest_um"),
                                                    wire_cycles=v.get("wire_cycles")) for p, v in res.items()}))
            tables, espec = expert_tiles(die, ranges)
            for t in tables:
                for e in t["ids"]:
                    for fam in ("w1", "w3", "w2"):
                        expect[f"layers.{t['layer']}.ffn.experts.{e}.{fam}"] = EXPERT[fam]
            grp = w1["macros_by_group"]
            other = (grp.get("VM.CONSTANT_HE", {}).get(M.WIDE, 0) + grp["ENGRAM.spill"][M.WIDE]) * DEPTH
            max_addr = check_exact_once(die, expect)
            free = int((DEPTH - die.fill).sum())
            ex = []
            for t in tables:
                sd = res_by_layer[t["layer"]].get("down") if t["layer"] in res_by_layer else None
                ex.append(dict(layer=t["layer"], experts_owned=len(t["ids"]), **expert_stats(n, t, sd, rng, draws)))
            if keep is not None:
                keep.append(die)
            dies.append(dict(die=name, stage=stage, rank=rank, macros=n_macros, pair_slots=n,
                             bf16_pair_slots=len(die.bf), rows_per_slot=PAIR,
                             dense_layers=dense_layers, segments=len(die.segs),
                             weight_words=int(sum(rg["words"] for rg in die.regions)),
                             max_address=max_addr, capacity_ok=bool(max_addr <= DEPTH and other <= free),
                             other_words_capacity_only=other, free_words_after_weights=free,
                             expert_split=espec, dense=per_layer, experts=ex))
    return dies


def compare(dies, model):
    busiest = max(dies, key=lambda d: (d["macros"], d["die"]))
    rd, ph = {}, {}
    for L in busiest["dense"]:
        rd.update(L["t_read"])
        ph.update(L["t_phase"])
    for e in busiest["experts"]:
        rd["experts_gu"] = max(rd.get("experts_gu", 0), e["model_six"]["gu_read"])
        ph["experts_gu"] = max(ph.get("experts_gu", 0), e["model_six"]["gu_phase"])
        rd["down"] = max(rd.get("down", 0), e["model_six"]["down_read"])
        ph["down"] = max(ph.get("down", 0), e["model_six"]["down_phase"])
    wr = {}
    for L in busiest["dense"]:
        for p_, v in L.get("wire", {}).items():
            if v.get("wire_cycles") is not None:
                wr[p_] = v if p_ not in wr or v["wire_cycles"] > wr[p_]["wire_cycles"] else wr[p_]
    rows = {}
    for p in PHASES:
        mv = model[p]
        tr = rd.get(p)
        trf = None if tr is None else max(tr, 8 * FADD_REC)
        tp = ph.get(p)
        binds_here = mv["bind"] in ("rom_read", "vm_read_x")
        rows[p] = dict(wire=wr.get(p), model_wire=mv.get("wire"), model_depth=mv.get("depth"),
                       model_t_read=mv["t_read"], model_ksplit=mv["ksplit"],
                       model_issue=mv["issue"], model_bind=mv["bind"],
                       t_read=tr, t_read_with_chain_floor=trf, t_phase=tp,
                       t_read_equal=bool(trf is not None and abs(trf - mv["t_read"]) < 1e-6),
                       t_read_within_model=bool(trf is not None and trf <= mv["t_read"] + 1e-6),
                       t_phase_equals_issue=bool(tp is not None and abs(tp - mv["issue"]) < 1e-6),
                       issue_ok=bool(tp is not None and (abs(tp - mv["issue"]) < 1e-6 if binds_here
                                                         else tp <= mv["issue"] + 1e-6)))
    return busiest["die"], rows


def element_needs_all(dies):
    """Per-element resources the whole bank map asks for (max over dies, phases and expert draws), against the
    element as built (ot_v41_rom_elem: NSEG 8 segments/classes, NCH 16 / NCHB 8 chain slots, 8 sub-blocks,
    LV 5 tree levels)."""
    dense, expert = {}, {}
    for d in dies:
        for L in d["dense"]:
            for ph, v in L["needs"].items():
                dense[ph] = merge_needs(dense.get(ph, {}), v)
        for e in d["experts"]:
            for mode in ("model_six", "true_occupancy"):
                expert[mode] = merge_needs(expert.get(mode, {}), e[mode]["element_needs_max"])
    allm = {}
    for v in list(dense.values()) + [expert.get("model_six", {})]:
        allm = merge_needs(allm, v)
    lv = math.ceil(math.log2(max(1, allm.get("base_nodes", 1))))
    return dict(dense_by_phase=dense, experts=expert, max_over_proposal=allm,
                tree_levels_needed=lv,
                built=dict(NSEG=8, NCH=16, NCHB=8, sub_blocks=8, LV=5),
                fits_built=bool(allm.get("segments", 0) <= 8 and allm.get("classes", 0) <= 8
                                and allm.get("words_per_round", 0) <= 16 and lv <= 5
                                and allm.get("units_per_class", 0) <= 64))


def price(rows, field, with_wire=False):
    """The model's proposal with each phase's issue replaced by the measured `field` where larger."""
    import copy
    import uarch_model as U
    meas = {p: r[field] for p, r in rows.items() if r[field] is not None}
    wires = {p: r["wire"]["wire_cycles"] for p, r in rows.items() if r.get("wire") and with_wire}
    orig = U.price_matvec

    def patched(nd, name, d, clock, c):
        r = orig(nd, name, d, clock, c)
        if r is not None and r["key"] in wires:
            r["depth"] = r["depth"] - r["wire"] + wires[r["key"]]
            r["wire"] = wires[r["key"]]
        if r is not None and r["key"] in meas:
            if field == "t_read":
                r["t_read"] = meas[r["key"]]
                r["issue"] = max(r["t_read"], r["t_mac"], r["t_x"], r["t_ret"])
            else:
                r["issue"] = max(meas[r["key"]], r["t_ret"])
        return r
    d = copy.deepcopy(U.PRESETS["proposal"])
    U.price_matvec = patched
    try:
        got = U.evaluate(d)
    finally:
        U.price_matvec = orig
    return round(got["tokens_s"], 1)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--draws", type=int, default=200)
    p.add_argument("--seed", type=int, default=20260929)
    p.add_argument("--die", action="append")
    p.add_argument("--no-price", action="store_true")
    p.add_argument("--bf16-pair", action="store_true", help="BF16 on every standard pair (BF16_PAIR)")
    p.add_argument("--bf16-split", action="store_true", help="BF16_PAIR: split BF16 rows for 8-cycle words")
    p.add_argument("--bf16-cap", type=int, default=0, help="BF16_PAIR: max BF16 words in flight per element")
    p.add_argument("--bf16-hold", type=int, default=8, help="BF16_PAIR: cycles a BF16 word is held (16 / multipliers)")
    p.add_argument("--near", action="store_true", help="distance-aware placement of the critical low-work phases")
    p.add_argument("--geometry", type=Path, default=ROOT / "results/floorplan/v41_pack_refit_w10_ss833_interim.json",
                   help="floorplan pack record giving pair-slot distances (with --near or --wire)")
    p.add_argument("--wire", action="store_true", help="measure each phase's farthest pair and wire cycles")
    p.add_argument("--critical", nargs="*", default=None, help="phases confined to the nearest slots (with --near)")
    p.add_argument("--fadd-rec", type=int, default=None, help="FP32 adder recurrence (chain latency) in cycles")
    a = p.parse_args(argv)
    global BF16_PAIR, FADD_REC, NEAR, SLOT_DIST, PERM
    _root = None
    if a.near or a.wire:
        SLOT_DIST, _root = load_geometry(a.geometry)
        PERM = np.random.default_rng(a.seed).permutation(len(SLOT_DIST))
    NEAR = bool(a.near)
    global CRITICAL
    if a.critical is not None:
        CRITICAL = tuple(a.critical)
    BF16_PAIR = bool(a.bf16_pair)
    global BF16_SPLIT_BOOST
    BF16_SPLIT_BOOST = int(a.bf16_split)
    global BF16_CAP, BF16_WORD_CYCLES
    BF16_CAP = a.bf16_cap
    BF16_WORD_CYCLES = a.bf16_hold
    if a.fadd_rec:
        FADD_REC = a.fadd_rec
    model, params = model_rows()
    dies = derive(a.snapshot, a.draws, a.seed, a.die)
    bus, rows = compare(dies, model)
    ok = all(r["issue_ok"] for r in rows.values())
    reads_ok = all(r["t_read_within_model"] for r in rows.values())
    exact = all(r["t_read_equal"] for r in rows.values())
    import uarch_model as U
    rec = dict(
        schema="opentallas.v41.rom_ksplit_bankmap.v1",
        verdict=("PASS" if exact else ("PASS_issue_match_t_read_below_model" if reads_ok
                                       else "PASS_issue_match_t_read_above_model_somewhere")) if ok
                else "FAIL_model_mismatch",
        verdict_rule=("issue_ok: measured stream-round cycles equal the model's issue where the model binds on "
                      "rom_read or vm_read_x, and do not exceed it where it binds elsewhere; t_read_within_model: "
                      "most words per macro (floored at the 40-cycle chain) <= the model's t_read"),
        claim_boundary=("binding and measured per-phase reads under golden-aligned K-split rows; t_read counts "
                        "words per macro; t_phase is the stream-round issue time of the element array"),
        rule=dict(split="s = model's doubling rule; segments of next_pow2(ceil(C/s)) chunks (golden-aligned)",
                  word_order="per macro region: sub-block q (8 units), b = 0..7, segments by (e0, row), units",
                  bf16_macros="floor(i * N / 2048), i < 2048",
                  compressor_rows="model output-split quarter (W1 map keeps full replication)",
                  bf16_pair=dict(enabled=BF16_PAIR, word_hold_cycles=BF16_WORD_CYCLES, sub_block_units=IL_BF16,
                                 split_for_hold=bool(BF16_SPLIT_BOOST)) if BF16_PAIR else None,
                  chain_recurrence_cycles=FADD_REC,
                  distance_aware=dict(critical=list(CRITICAL), geometry=str(a.geometry.relative_to(ROOT))
                                      if a.geometry.is_relative_to(ROOT) else str(a.geometry),
                                      geometry_sha256=sha(a.geometry), reach_um=REACH_UM,
                                      gather_scatter_cycles=GATHER_SCATTER,
                                      slot_order="slot j = the j-th nearest ROM pair to the x-broadcast root",
                                      rule="each critical phase on the smallest nearest-slot prefix (sixteenths of "
                                           "the die, then powers of two) whose stream-round time equals the "
                                           "whole-die placement's; everything else on the whole die")
                  if NEAR else None),
        checkpoint_revision=a.snapshot.name,
        source_sha256={str(q.relative_to(ROOT)): sha(q) for q in
                       [Path(__file__).resolve(), ROOT / "tools/v41_floorplan_die_macromap.py",
                        ROOT / "tools/uarch_model.py", ROOT / "results/uarch/v41_rom.json", M.OWNERS]
                       + ([a.geometry.resolve()] if (a.near or a.wire) else [])},
        draws=a.draws, seed=a.seed, busiest_die=bus, phase_vs_model=rows,
        priced=None if a.no_price else dict(
            model_tokens_s=round(U.evaluate(dict(U.PRESETS["proposal"]))["tokens_s"], 1),
            with_measured_t_read=price(rows, "t_read"), with_measured_t_phase=price(rows, "t_phase"),
            with_measured_t_phase_and_wire=price(rows, "t_phase", True) if (a.near or a.wire) else None),
        all_capacity_ok=all(d["capacity_ok"] for d in dies),
        element_needs=element_needs_all(dies), dies=dies,
        slot_geometry=None if SLOT_XY is None else dict(
            root_um=list(_root), columns=["x_um", "y_um", "manhattan_um_to_root"], slots=SLOT_XY,
            note=("slot j is the j-th nearest ROM pair to ONE x-broadcast root / return sink (the distributed-VM "
                  "port); a multi-root return must map each root's region to a contiguous set of these slots")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(verdict=rec["verdict"], busiest=bus, capacity=rec["all_capacity_ok"],
                          priced=rec["priced"])))
    for p_, r in rows.items():
        print(p_, r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
