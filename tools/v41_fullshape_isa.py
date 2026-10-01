#!/usr/bin/env python3
"""ISA-level TP-4 executor of the full-shape DeepSeek-V4.1-Flash layer-0 program, checked against the golden.

    python3 tools/v41_fullshape_isa.py --context 1048576 [--context 200000] \
        [--scratch /home/ubuntu/w17work/isa/scratch] [--record results/rtl/w17_l0_fullshape_isa.json]

WHAT RUNS.  The encoded production program (results/rtl/hdc_v41x_fullshape_l0_program.hex, 2048-bit words
decoded with tools/hdc_isa_v41.py's FULL profile) -- the words the RTL core ot_hdc_core_v41x executes -- on four
ranks in lockstep between collectives.  Each rank holds:

* a vector memory of 2^19 FP32 elements, every element marked UNWRITTEN until an instruction (or the harness
  preload) writes it; a read of an unwritten element is a dataflow defect and is reported with its PC;
* the harness preload, exactly what the RTL harness gives a layer die: the residual H (4 x 5120, the golden
  shard's h_in), the pending pre-mix PF (pre_in) and its norm statistic SSX (the hc_post red_tree of the
  previous layer: csum of h_in squared);
* the constant ROM as the bound layout places it (FP32 lo / +0 hi per word), and the one-position HBM RoPE
  coefficient cache (CTL5 prefetch / CTL6 release, lo = cos, hi = sin at (2 + kind) << 28 | pos * 32 + pair);
* the local 0..639-row attention window, rows 0..126 preloaded with the golden shard's synthetic window rows
  (oldest first, exactly the stored-format BF16 values) -- the die's chronological packed-KV source.

HOW EACH UNIT IS MODELLED.  The point is the program's dataflow, addresses, strides, counts, DYN selectors,
constants and collectives -- not engine microarchitecture:

* weight ops (QE LINQ, ME weight ops, HE) identify their matrix from the instruction's weight base through the
  bound layout records the program was bound against (tools/v41_fullshape_program_bind.py): base -> matrix, an
  expert id read from the vector memory times the family stride -> the expert.  The rank's slice of that matrix
  comes from the rank's die image (tools/rtl_v41_fullshape_layer_campaign.py --steps images --rank r, the
  die_slices split).  The arithmetic is the golden's (linear_q blocks + csum, the chunk8 matvec csum, the HE
  csum), with the activation read from the vector memory at the instruction's addresses and strides and the
  outputs written by its output descriptor;
* KV-sourced ME ops follow ot_hdc_v41x_att_adapt.sv with PACKED_KV (full shape): 16 heads per op
  (IL << hg), q.k over D = 512 (ks = 1) or p.v over T rows (ks != 1), T = the op's nout / k (<= TROWS 640),
  x element (hh, k) at xb + (hh / IL) * xcs + k * xks + (hh % IL) * xjs, BF16-rounded, rows the window
  store's rows 0 .. T-1 chronological, result (hh, o) to word ob + t * ots + (hh / IL) * ogs + (hh % IL) * ojs;
* SU, XU (select, Sinkhorn), QE QDQ are tools/hdc_program_v41.Machine's unit semantics, with the full-shape
  DYN table (ot_hdc_core_v41x.sv, FULL_SHAPE) and the full-shape KV store;
* COLL (unit 6) is W15's engine: all-gather writes rank r's n elements at dst + r * n on every rank; all-reduce
  writes ((r0 + r1) + (r2 + r3)) in FP32, BF16 RNE when coll_rnd (rtl/rom/ot_rom_oneshot_px.sv full-shape fold,
  tools/rtl_v41_tp_layer0_collectives.py).

CHECK.  At fixed points of the program the ranks' vector memories are compared bit for bit with the golden
shard's arrays: L0.attn_norm (XN after the attention norm), L0.attn (Y after the wo_b all-reduce), L0.ffn_norm,
L0.router (BI = scores + bias), L0.ffn (YALL after the y all-gather), block0 / h_out (H at END) and pre0 /
pre_out (PF at END).  The first mismatching region names its PC.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402
import hdc_replay_v41 as R  # noqa: E402
import rtl_v41_fullshape_layer_campaign as LC  # noqa: E402
import v41_program_constants as KC  # noqa: E402

F = np.float32
SCHEMA = "opentallas.rtl.w17_l0_fullshape_isa.v1"
PROGRAM = ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.hex"
PROGRAM_RECORD = ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.json"
PROGRAM_L20 = ROOT / "results/rtl/hdc_v41x_fullshape_l20_program.hex"
# The ISA-level contracts the layer-20 program adds (RTL owners: collective engine W15b, core DYN routing W17).
CONTRACT_L20 = {
    "COLL_TOPK_MERGE": {
        "coll_op": 2,
        "descriptor": {"coll_src": "n scores, FP32 VM elements (BF16-valued index scores; candidate block maxima or "
                                   "+inf for the pinned block)",
                       "coll_ibase": "n local ids, u32 bit patterns in FP32 VM containers, ascending (an XU SELECT "
                                     "output); score i belongs to id i",
                       "coll_n": "n, static, a multiple of 16 (512 index, 2048 candidate)",
                       "coll_k": "k <= 4 n (here k = n)",
                       "coll_d_stride": "DYN selector (FULL profile field appended at offset 1961, 6 bits): global id = "
                                        "rank * dyn[coll_d_stride] + local id (SC1 for the index, ceil(SC1/8) for "
                                        "the candidate blocks)",
                       "coll_dst": "k global ids, u32, one per VM element (16 per word), ascending, on every rank"},
        "order": "(score descending, global id ascending) over the 4n pairs; values compared as reals: -0 == +0 "
                 "(canonicalise before an order-preserving u32 map), -inf the least value, no masking",
        "golden": "hdc_golden_v41.topk_lowest_index over the global score array, then sorted",
        "padding": "entries past a rank's live count must hold -inf (not emitted: the program's contexts have SC1 >= "
                   "512 and >= 2048 blocks; n_pos >= 65,533)",
        "zeros": "no -0 reaches these regions (csum from +0, zero-canonicalising adds); canonicalise anyway",
        "status": "the die faults coll_op[1] today (rtl/chip/ot_chip_v41x_die.sv coll_issue_bad)"},
    "DYN": {"NEWBLK": "FULL_DYN slot 52, rank-aware: owner = (NC1 - 1) // SC1; on the owner rank ((NC1 - 1) - "
                      "RANK * SC1) // 8, else ceil(SC1 / 8) (a pad slot one past the rank's last block)",
            "coll_d_stride": "the core resolves the DYN selector into the collective request like any DYN field"},
    "key_partition": "contiguous quarters: rank r's index keys are global rows [r * SC1, (r + 1) * SC1), SC1 = "
                     "ceil(NC1 / 4); the fused index op's row r is global key r * SC1 + r",
    "stores": "the index-key write (SU KVT, 128 wide) is global key row POS; the compressed-row write (QE QDQ4E, "
              "element address row * 512) is global row POS; the selected-row gather (SU a_ind IND_O into KV/KVT, "
              "a_base 0, a_so 512) reads global compressed rows by id -- HBM stores, not the vector memory",
    "deviation": "indexer weights_proj replicated per rank (32 x 5120 BF16, 320 KB) instead of the model's output "
                 "split: the exact head sum needs all 32 head weights on every rank"}
GOLDEN_RECORD = ROOT / "results/rtl/hdc_v41x_fullshape_golden.json"
ROPE_CACHE = ROOT / "results/rtl/v41x_rope_hbm_cache.json"
BIND = {1048576: ROOT / "results/rtl/hdc_v41x_fullshape_1m_program_bind_rope_hbm.json",
        200000: ROOT / "results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json"}
OUT = ROOT / "results/rtl/w17_l0_fullshape_isa.json"
SCRATCH = Path("/home/ubuntu/w17work/isa/scratch")
# the headline 1M reference token (claude/w17-ref): seed 20260930 -> 21946, margin 3.149
REF_SEED = 20260930
REF_RECORD = ROOT / "results/rtl/w17_v41_1m_reference_token.json"
SEEDED = {(1048576, REF_SEED, 0): dict(bind=ROOT / "results/rtl/hdc_v41x_fullshape_1m_s20260930_program_bind_rope_hbm.json",
                                       scratch=Path("/home/ubuntu/w17work/isa/scratch_s20260930")),
          (1048576, REF_SEED, 20): dict(
              bind=ROOT / "results/rtl/hdc_v41x_fullshape_1m_s20260930_l20_program_bind_rope_hbm.json",
              scratch=Path("/home/ubuntu/w17work/isa/scratch_s20260930"))}


def case(ctx: int, seed: int = LC.SEED, layer: int = 0) -> tuple[Path, Path]:
    """(bind record, scratch dir) of a context, golden seed and layer."""
    if seed == LC.SEED and layer == 0:
        return BIND[ctx], SCRATCH
    c = SEEDED[(ctx, seed, layer)]
    return c["bind"], c["scratch"]


def case_key(ctx: int, seed: int = LC.SEED, layer: int = 0) -> str:
    return (str(ctx) if seed == LC.SEED else f"{ctx}_seed{seed}") + (f"_L{layer}" if layer else "")
VM_ELEMS = 1 << 19
TP, W, IL, GR, BL = 4, I.W_LANES, I.INTERLEAVE, I.GROUPS, I.BL
HD, TROWS, WINDOW, SCAN_CAP, TOPK = 512, 640, 128, 16384, 512
NDYN = 64
ROPE_PAIR = 32
IMG_UNIT = {I.UNIT_ME: "ME", I.UNIT_SU: "SU", I.UNIT_QE: "QE", I.UNIT_XU: "XU", I.UNIT_HE: "HE",
            I.UNIT_COLL: "COLL", I.UNIT_CTL: "CTL"}


class Defect(Exception):
    """A program defect found by the executor (not an arithmetic mismatch)."""


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cdiv(a, b):
    return -(-a // b)


# -- DYN table: ot_hdc_core_v41x.sv, FULL_SHAPE, one slot ----------------------------------------------------------
def full_dyn(pos: int, tok: int = 0, rank: int = 0) -> list[int]:
    p1 = pos + 1
    n2 = p1 >> 1
    ns1, ns2 = min(p1, TOPK), min(n2, TOPK)
    lg = (W * GR).bit_length() - 1
    rnds = lambda x: 0 if x == 0 else ((x - 1) >> lg) + 1  # noqa: E731
    rnd16 = lambda x: 0 if x == 0 else ((x - 1) >> 4) + 1  # noqa: E731
    d = [0] * NDYN
    d[1] = tok * 5120
    d[2] = pos * ROPE_PAIR
    d[3] = 0 if pos == 0 else (pos - 1) * ROPE_PAIR
    d[4], d[5], d[6], d[7] = pos, p1, n2, (n2 - 1 if n2 else 0)
    d[8], d[9], d[10], d[11] = ns1, ns2, p1 + ns1, p1 + ns2
    d[12], d[13], d[14], d[15] = rnds(p1), rnds(n2), rnds(p1 + ns1), rnds(p1 + ns2)
    d[16], d[17] = pos * HD, p1 * HD
    d[18], d[19] = (4 if pos & 1 else 0), (64 if pos & 1 else 0)
    d[20] = (n2 - 1) * HD if n2 else 0
    d[21], d[22], d[23], d[24] = rnd16(p1), rnd16(n2), rnd16(p1 + ns1), rnd16(p1 + ns2)
    win = min(p1, WINDOW)
    sc1, sc2 = cdiv(p1, TP), cdiv(n2, TP)
    scr = cdiv(min(p1, SCAN_CAP), TP)
    fd = {"WIN": win, "NC1": p1, "NC2": n2, "NS1": ns1, "NS2": ns2, "T0": win, "T1": win + ns1, "T2": win + ns2,
          "SC1": sc1, "SC2": sc2, "SCR": scr, "NSL1": min(sc1, TOPK), "NSL2": min(sc2, TOPK), "NSLR": min(scr, TOPK),
          ("ceil", "SC1", 16): cdiv(sc1, 16), ("ceil", "SC1", 8): cdiv(sc1, 8), ("ceil", "SC2", 16): cdiv(sc2, 16),
          ("ceil", "SCR", 16): cdiv(scr, 16), ("ceil", "T0", 32): cdiv(win, 32),
          ("ceil", "T1", 32): cdiv(win + ns1, 32), ("ceil", "T2", 32): cdiv(win + ns2, 32),
          "WINM1": win - 1, "WIN_ROW": win * HD, "WINM1_ROW": (win - 1) * HD,
          # rank-aware (the core's RANK parameter): contiguous key quarters, candidate blocks of 8
          "NEWBLK": ((p1 - 1) - rank * sc1) // 8 if (p1 - 1) // sc1 == rank else cdiv(sc1, 8)}
    for key, slot in I.FULL_DYN.items():
        d[slot] = fd[key]
    # the emitter's symbolic selectors, resolved by hdc_replay_v41.dyn_values, must agree with the core's table
    dv = R.dyn_values(R.SHIPPED, pos, rank)
    for key, slot in I.FULL_DYN.items():
        if R.resolve(key, dv) != d[slot]:
            raise Defect(f"DYN {key}: core {d[slot]} vs emitter {R.resolve(key, dv)} at pos {pos}")
    return d


# -- golden shard and the rank images ------------------------------------------------------------------------------
def load_golden(ctx: int, scratch: Path, seed: int = LC.SEED, layer: int = 0) -> dict:
    if seed == LC.SEED:
        rec = json.loads(GOLDEN_RECORD.read_text())["contexts"][str(ctx)]
        state_sha = rec["initial_state_segments"][0]["description"]["sha256"]["win0"]
    else:
        rec = json.loads(REF_RECORD.read_text())
        if (rec["context"], rec["seed"]) != (ctx, seed):
            raise SystemExit(f"{REF_RECORD.name} is not the ctx {ctx} seed {seed} token")
        state_sha = None       # the record pins the whole state digest only; rows re-derived from the seed
    L0 = rec["layers"][layer]
    assert L0["layer"] == layer
    z = np.load(scratch / f"ctx{ctx}_L{layer:02d}.npz")
    js = json.loads((scratch / f"ctx{ctx}_L{layer:02d}.json").read_text())
    got_in, got_out = LC.digest(z["h_in"], z["pre_in"]), LC.digest(z["h_out"], z["pre_out"])
    if got_in != L0["input_sha256"] or got_out != L0["output_sha256"]:
        raise SystemExit(f"ctx {ctx}: golden shard I/O sha256 differs from its golden record")
    for k, v in js["trace_sha256"].items():
        if LC.digest(z[k]) != v:
            raise SystemExit(f"ctx {ctx}: golden trace array {k} differs from its shard record")
    extra = {}
    if js.get("ctx_out", {}).get("cand_file"):
        extra["cand"] = np.load(scratch / js["ctx_out"]["cand_file"])["cand"]
    return dict(z={k: z[k] for k in z.files}, shard=js, record=L0, position=rec["position"], layer=layer, **extra,
                experts=js["experts"], state_sha=state_sha, seed=seed,
                token_history=js.get("token_history", rec.get("token_history")))


def rank_images(ctx: int, rank: int, scratch: Path, golden: dict) -> tuple[dict, Path, dict]:
    L = golden["layer"]
    d = scratch / "images" / f"ctx{ctx}_L{L:02d}_r{rank}"
    man = json.loads((d / "manifest.json").read_text())
    if (man["context"], man["layer"], man["rank"], man["tp"]) != (ctx, L, rank, TP):
        raise SystemExit(f"{d}: image manifest identity mismatch")
    if man["golden_shard"]["input_sha256"] != golden["record"]["input_sha256"] or \
            man["golden_shard"]["experts"] != golden["experts"]:
        raise SystemExit(f"{d}: image set was not cut from this golden shard")
    for name, e in man["files"].items():
        if sha(d / f"{name}.bin") != e["sha256"]:
            raise SystemExit(f"{d}/{name}.bin: sha256 differs from its manifest")
    return man, d, {"manifest_sha256": sha(d / "manifest.json"), "files": len(man["files"])}


def _raw(d: Path, man: dict, name: str) -> tuple[np.ndarray, str, list]:
    e = man["files"][name]
    return np.fromfile(d / f"{name}.bin", dtype=np.uint8), e["format"], e["shape"]


def decode_q(d: Path, man: dict, name: str) -> V.Q8:
    """A block-quantised slice (FP8 E4M3 32x32-block scale, or packed E2M1 per-row-block scale) -> Q8."""
    raw, fmt, shape = _raw(d, man, f"w.{name}")
    sraw, sfmt, sshape = _raw(d, man, f"w.{name}.scale")
    assert sfmt == "F8_E8M0", (name, sfmt)
    e = sraw.reshape(sshape).astype(np.int32) - 127
    if fmt == "F8_E4M3":
        codes = raw.reshape(shape)
    elif fmt == "I8":
        b = raw.reshape(shape)
        codes = np.stack([V.E2M1[b & 15], V.E2M1[b >> 4]], axis=-1).reshape(shape[0], shape[1] * 2)
    else:
        raise SystemExit(f"{name}: unsupported quantised format {fmt}")
    return V._blocked(codes, e, name)


def decode_dense(d: Path, man: dict, name: str) -> np.ndarray:
    raw, fmt, shape = _raw(d, man, f"w.{name}")       # manifest shape: [rows, bytes per row]
    rows = shape[0]
    if fmt == "BF16":
        v = G.from_bits(raw.view("<u2").astype(np.uint32) << 16)
    elif fmt == "F32":
        v = raw.view("<f4").astype(F)
    else:
        v = None
    if v is not None:
        # a 1-D tensor is stored [elements, element bytes]; a matrix [rows, row bytes]
        return v.reshape(-1) if shape[1] in (2, 4) and v.size == rows else v.reshape(rows, -1)
    raise SystemExit(f"{name}: unsupported dense format {fmt}")


# -- the bound layout: base -> matrix --------------------------------------------------------------------------------
class BoundLayout:
    def __init__(self, bind_path: Path):
        self.bind = json.loads(bind_path.read_text())
        self.bind_path = bind_path
        b = self.bind
        if b["instruction_count"] != {0: 113, 20: 144}[b.get("layer", 0)] or b["rope_mode"] != "hbm_cache":
            raise SystemExit(f"{bind_path}: not a production tagged-RoPE layer bind")
        self.layout_path = ROOT / b.get("layout_path", "results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json")
        self.qe_path = ROOT / b.get("qe_stream_path", "results/rtl/hdc_v41x_fullshape_qe_stream_200k_l0_rank0.json")
        if sha(self.layout_path) != b["layout_sha256"] or sha(self.qe_path) != b["qe_stream_sha256"]:
            raise SystemExit(f"{bind_path}: layout / QE stream records changed since the bind")
        self.layout = json.loads(self.layout_path.read_text())
        self.qe = json.loads(self.qe_path.read_text())
        self.mats = dict(self.layout["matrices"])
        self.mats.update(self.qe["matrices"])
        self.consts = self.layout["constants"]
        self.selected = list(b["source_experts"])
        self.qtrace = {}
        for t in b["qe_address_trace"]:
            self.qtrace.setdefault(t["pc"], []).append(t)

    def engine_matrix(self, engine: str, base: int) -> tuple[str, dict]:
        for name, m in self.mats.items():
            if m["engine"] != engine or m.get("expert_id_base") is not None:
                continue
            if m["base_word"] <= base < m["base_word"] + m["word_count"]:
                return name, m
        raise Defect(f"{engine} base {base} lies in no bound matrix")

    def qe_matrix(self, base: int, eid: int | None, stride: int) -> tuple[str, dict]:
        if eid is None:
            for name, m in self.mats.items():
                if m["engine"] == "qe" and m.get("expert_id_base") is None and m["base_word"] == base:
                    return name, m
            raise Defect(f"QE base {base} is no dense matrix base")
        fam = [n for n, m in self.mats.items() if m["engine"] == "qe" and m.get("expert_id_base") == base]
        if not fam:
            raise Defect(f"QE indexed base {base} is no expert family base")
        kind = fam[0].split(".")[-1]
        name = f"exp{eid}.{kind}"
        if name not in self.mats:
            raise Defect(f"QE expert {eid} of family {kind} is not materialised (fail closed)")
        m = self.mats[name]
        if m["expert_stride_words"] != stride or m["base_word"] != base + eid * stride:
            raise Defect(f"QE {name}: stride {stride} / base {base} do not address its image")
        return name, m


# -- one rank ------------------------------------------------------------------------------------------------------
class Rank:
    def __init__(self, r, lay: BoundLayout, man, img: Path, golden: dict, win_rows: np.ndarray, rope: dict,
                 consts: dict, pos: int, stores=None):
        self.r, self.lay, self.man, self.img, self.pos = r, lay, man, img, pos
        # an indexed layer's HBM stores (shared by the ranks, global row ids): {"ckv": [rows, 512],
        # "ik": [rows, 128], "n": live rows}; the rank scans its contiguous key quarter
        self.stores = stores
        self.vm = np.zeros(VM_ELEMS, dtype=F)
        self.ok = np.zeros(VM_ELEMS, dtype=bool)
        self.unwritten = []                     # (pc, operand, first address, count)
        self.log = []                           # this rank's engine log (weight ops: matrix, expert)
        self.dyn = full_dyn(pos, rank=r)
        self.rope_tab, self.rope_held = rope, {}
        self.consts = consts
        self.m = type("M", (), dict(hc_eps=F(consts["hc_eps"]["value"]),
                                    sinkhorn_iters=consts["_sinkhorn_iters"]))()
        self.q, self.dense = {}, {}
        # CROM: the bound layout's constants, FP32 in lo, +0 hi, from this rank's image
        top = max(c["base_word"] + c["word_count"] for c in lay.consts.values())
        self.crom = np.zeros((top, 2), dtype=F)
        self.crom_ok = np.zeros(top, dtype=bool)
        for name, c in lay.consts.items():
            if name == "pre0":
                v = np.array([1, 0, 0, 0], dtype=F)
            else:
                v = decode_dense(img, man, name).reshape(-1)
                if name in ("hc_attn_scale", "hc_ffn_scale"):
                    v = np.concatenate([np.repeat(v[0], 4), np.repeat(v[1], 4), np.repeat(v[2], 16)]).astype(F)
            assert v.size == c["word_count"], name
            self.crom[c["base_word"]:c["base_word"] + v.size, 0] = v
            self.crom_ok[c["base_word"]:c["base_word"] + v.size] = True
        # the attention window: the die's chronological stored-format rows (rows 0 .. 126 before this token)
        self.kr = np.full((TROWS, HD), np.nan, dtype=F)
        self.kt = np.full((TROWS, HD), np.nan, dtype=F)
        self.kr[:len(win_rows)] = win_rows
        self.kt[:len(win_rows)] = win_rows
        # harness preload: H, PF, SSX
        V_ = R.ShapeLayout(R.SHIPPED, tp_exact=True).vm.map
        self.V = V_
        h = golden["z"]["h_in"].reshape(-1).astype(F)
        self.write(V_["H"], h)
        self.write(V_["PF"], golden["z"]["pre_in"].astype(F))
        self.write(V_["SSX"], np.array([V.csum(G.mul(h, h))], dtype=F))

    # vector memory with written-ness
    def read(self, e, what, pc):
        e = np.asarray(e, dtype=np.int64).reshape(-1)
        if e.size and (e.min() < 0 or e.max() >= VM_ELEMS):
            raise Defect(f"PC {pc}: {what} address outside the vector memory")
        bad = ~self.ok[e]
        if bad.any():
            self.unwritten.append(dict(pc=pc, operand=what, first=int(e[bad][0]), count=int(bad.sum())))
        return self.vm[e]

    def write(self, e0, vals, idx=None):
        vals = np.asarray(vals, dtype=F).reshape(-1)
        e = (np.arange(vals.size) + e0) if idx is None else np.asarray(idx, dtype=np.int64).reshape(-1)
        if e.size and (e.min() < 0 or e.max() >= VM_ELEMS):
            raise Defect(f"write outside the vector memory ({e.min()}..{e.max()})")
        self.vm[e] = vals
        self.ok[e] = True

    def weight(self, name):
        if name not in self.q:
            self.q[name] = decode_q(self.img, self.man, name)
        return self.q[name]

    def dense_w(self, name):
        if name not in self.dense:
            v = decode_dense(self.img, self.man, name) if name != "wo_a" else \
                G.to_bf16(decode_q(self.img, self.man, name).dense())
            self.dense[name] = np.asarray(v, dtype=F)
        return self.dense[name]

    # -- CTL -----------------------------------------------------------------------------------------------------
    def ctl(self, f, pc):
        if f["ctl"] == 5:          # prefetch: the (kind, position) pair is held until release
            kind, p = f["ctl_lane"], self.dyn[4]
            if kind in self.rope_held:
                raise Defect(f"PC {pc}: RoPE kind {kind} prefetched twice without release")
            if (kind, p) not in self.rope_tab:
                raise Defect(f"PC {pc}: RoPE prefetch of kind {kind} position {p}: no coefficients")
            self.rope_held[kind] = (p, self.rope_tab[(kind, p)])
        elif f["ctl"] == 6:
            if f["ctl_lane"] not in self.rope_held:
                raise Defect(f"PC {pc}: RoPE release of a kind never prefetched")
            del self.rope_held[f["ctl_lane"]]
        else:
            raise Defect(f"PC {pc}: unsupported control op {f['ctl']} in the layer program")

    # -- QE --------------------------------------------------------------------------------------------------------
    def qe(self, f, pc, log):
        nb = f["qe_nb"]
        x = self.read(f["qe_xbase"] + np.arange(nb * 32), "qe_x", pc)
        mode = f["qe_mode"]
        ob = f["qe_obase"] + self.dyn[f["qe_d_obase"]]
        if mode == I.QE_QDQ8:
            self.write(ob, V.qdq_fp8(x))
            return
        if mode == I.QE_QDQ4E and self.stores is not None:
            # full shape: the compressed-KV row of the source layer's HBM store, element address row * hd
            row, rem = divmod(ob, HD)
            if rem or nb * 32 != HD or row != self.stores["n"]:
                raise Defect(f"PC {pc}: compressed-row write {ob} is not the next global row {self.stores['n']}")
            self.stores["ckv_new"][self.r] = (row, V.qdq_fp4_e4m3(x, 16))
            log.append(dict(pc=pc, unit="QE", ckv_row=int(row)))
            return
        if mode in (I.QE_QDQ4, I.QE_QDQ4E):
            self.write(ob, V.qdq_fp4_e8m0(x) if mode == I.QE_QDQ4 else V.qdq_fp4_e4m3(x, 16))
            return
        eid = None
        if f["qe_ind"]:
            eid = int(G.bits(self.read([f["qe_ibase"]], "qe_expert_id", pc))[0])
        name, m = self.lay.qe_matrix(f["qe_wbase"], eid, f["qe_istride"])
        geo = m["geometry"]
        if (f["qe_nout"], nb, f["qe_tiles"]) != (geo["nout"], geo["nb"], geo["tiles"]) or \
                bool(f["qe_fp4"]) != m["format"].startswith("FP4_"):
            raise Defect(f"PC {pc}: QE descriptor (nout {f['qe_nout']}, nb {nb}, tiles {f['qe_tiles']}, fp4 "
                         f"{f['qe_fp4']}) does not match {name} {geo['nout']}/{geo['nb']}/{geo['tiles']}")
        if f["qe_tiles"] * IL * BL < f["qe_nout"]:
            raise Defect(f"PC {pc}: QE tiles do not cover nout")
        tr = [t for t in self.lay.qtrace.get(pc, []) if t["expert_id"] == eid]
        if tr and not (tr[0]["start_word"] == m["base_word"] and tr[0]["backed"]):
            raise Defect(f"PC {pc}: bind trace start {tr[0]['start_word']} != {name} base {m['base_word']}")
        w = self.weight(name)
        if w.shape != (f["qe_nout"], nb * 32):
            raise Defect(f"PC {pc}: {name} rank slice {w.shape} vs descriptor ({f['qe_nout']}, {nb * 32})")
        xq, xe = V.quant_fp8(x)
        blocks = [np.ldexp((w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F),
                           w.e[:, b] + xe[b]).astype(F) for b in range(nb)]
        acc = V.csum(np.stack(blocks, axis=-1))
        self.write(f["qe_obase"], acc if f["qe_unrounded"] else G.to_bf16(acc))
        log.append(dict(pc=pc, unit="QE", matrix=name, expert=eid, rows=int(f["qe_nout"]), k=nb * 32,
                        unrounded=bool(f["qe_unrounded"])))

    # -- ME ----------------------------------------------------------------------------------------------------------
    def me(self, f, pc, log):
        d = self.dyn
        n = f["me_nout"] + d[f["me_d_nout"]]
        tiles = f["me_tiles"] + d[f["me_d_tiles"]]
        K = f["me_k"] + d[f["me_d_k"]]
        if n == 0 or tiles == 0 or K == 0:
            return
        if max(1, f["mx_m"]) != 1:
            raise Defect(f"PC {pc}: multi-position ME op in the layer program")
        if f["me_fuse"]:
            self.me_index(f, pc, n, tiles, K, log)
        elif f["me_wsrc"]:
            self.me_att(f, pc, n, tiles, K, log)
        else:
            self.me_weight(f, pc, n, tiles, K, log)

    def me_weight(self, f, pc, n, tiles, K, log):
        d = self.dyn
        wb = f["me_wbase"] + d[f["me_d_wbase"]]
        xb = f["me_xbase"] + d[f["me_d_xbase"]]
        ob = f["me_obase"] + d[f["me_d_obase"]]
        name, m = self.lay.engine_matrix("me", wb)
        S = 1 << f["me_split"]
        if name != "wo_a":
            if wb != m["base_word"] or n != m["nrows"] or K * S != m["ncols"]:
                raise Defect(f"PC {pc}: ME {name} descriptor does not cover its image")
            wmat = self.dense_w(name)
            label = name
        elif name == "wo_a":
            groups = R.SHIPPED["o_groups"] // TP
            gw = m["word_count"] // groups
            g, rem = divmod(wb - m["base_word"], gw)
            if rem or not 0 <= g < groups or n != R.SHIPPED["o_rank"] or K * S != m["ncols"]:
                raise Defect(f"PC {pc}: ME wo_a descriptor is not one local o-group")
            wmat = self.dense_w("wo_a")[g * n:(g + 1) * n]
            label = f"wo_a.group{g}"
        per_round = GR // S
        rr, q, j, l = (a.reshape(-1) for a in np.meshgrid(np.arange(tiles), np.arange(per_round), np.arange(IL),
                                                          np.arange(W), indexing="ij"))
        t = rr * per_round + q
        nidx = (t * IL + j) * W + l
        keep = nidx < n if f["me_mmode"] == 0 else (t * W + l < n)
        t, j, l, nidx = t[keep], j[keep], l[keep], nidx[keep]
        if len(np.unique(nidx)) != n or nidx.max() >= n:
            raise Defect(f"PC {pc}: ME tiles do not cover the {n} output rows exactly once")
        prods = []
        for c in range(S):
            xa = xb + c * f["me_xcs"] + np.arange(K)[None, :] * f["me_xks"] + j[:, None] * f["me_xjs"]
            x = self.read(xa, "me_x", pc).reshape(xa.shape)
            if f["me_round"]:
                x = G.to_bf16(x)
            prods.append(G.mul(wmat[nidx][:, c * K:(c + 1) * K], x))
        acc = V.csum(np.concatenate(prods, axis=1))
        if f["me_oen"]:
            self.write(0, acc, idx=(ob + t * f["me_ots"] + j * f["me_ojs"]) * W + l)
        log.append(dict(pc=pc, unit="ME", matrix=label, rows=int(n), k=int(K * S)))

    def me_index(self, f, pc, n, tiles, K, log):
        """The fused indexer op (ot_hdc_v41x_idx_adapt.sv; Machine.me_fused), full shape: per key row r < n of
        the rank's quarter (global key rank * SC1 + r),
            IS[r] = to_bf16(csum_hh to_bf16(relu(to_bf16(dots_q4(q[hh], key))) * wts[hh]))
        over the 2^hg * IL heads, q[hh] at xbase + (hh / IL) * xcs + (hh % IL) * xjs + k * xks, wts[hh] at
        me_wts + hh; written as element obase * 16 + r."""
        st = self.stores
        if st is None:
            raise Defect(f"PC {pc}: fused index op without index keys")
        nh = IL << f["me_hg"]
        ihd = K
        if f["me_ks"] != 1 or f["me_js"] != 0 or not f["me_mmode"] or not f["me_round"] or \
                tiles * (GR >> f["me_hg"]) * W < n:
            raise Defect(f"PC {pc}: fused index op outside the engine's shapes")
        hh = np.arange(nh)[:, None]
        k = np.arange(ihd)[None, :]
        xa = f["me_xbase"] + (hh // IL) * f["me_xcs"] + k * f["me_xks"] + (hh % IL) * f["me_xjs"]
        q = G.to_bf16(self.read(xa, "idx_q", pc).reshape(xa.shape))
        wts = self.read(f["me_wts"] + np.arange(nh), "idx_wts", pc)
        sc1 = self.dyn[I.FULL_DYN["SC1"]]
        g0 = self.r * sc1
        live = st["n"] + 1                      # the keys before this position + its own (written at PC ik)
        if st["ik_new"] is None:
            raise Defect(f"PC {pc}: index scan before the position's key was written")
        out = np.full(n, -np.inf, dtype=F)
        for c0 in range(0, n, 32768):
            c1 = min(n, c0 + 32768)
            g = g0 + np.arange(c0, c1)
            ok = g < live
            if not ok.any():
                continue
            keys = st["ik"][np.minimum(g[ok], st["n"] - 1)].astype(F)
            if (g[ok] == st["n"]).any():
                keys[g[ok] == st["n"]] = st["ik_new"]
            score = G.to_bf16(V.dots_q4(q, keys))                                  # [heads, keys]
            terms = G.to_bf16(G.mul(np.maximum(score, F(0)).astype(F), wts[:, None]))
            out[c0:c1][ok] = G.to_bf16(V.csum(terms.T))
        ob = (f["me_obase"] + self.dyn[f["me_d_obase"]]) * W
        self.write(ob, out)
        log.append(dict(pc=pc, unit="ME", matrix="index_scores", heads=nh, rows=int(n), first_key=int(g0)))

    def me_att(self, f, pc, n, tiles, K, log):
        """ot_hdc_v41x_att_adapt.sv, PACKED_KV: q.k (ks == 1) or p.v (ks != 1) over chronological rows."""
        d = self.dyn
        pv = f["me_ks"] != 1
        T = K if pv else n
        Dl = n if pv else K
        nhd = IL << f["me_hg"]
        if f["me_js"] != 0 or not f["me_mmode"] or not f["me_round"] or f["mx_m"] > 1 or Dl != HD or \
                T > TROWS or nhd % 16 or nhd > 32:
            raise Defect(f"PC {pc}: attention op outside the adapter's served shapes")
        if tiles * (GR >> f["me_hg"]) * W < (Dl if pv else T):
            raise Defect(f"PC {pc}: attention tiles do not cover the op")
        xb = f["me_xbase"] + d[f["me_d_xbase"]]
        ob = f["me_obase"] + d[f["me_d_obase"]]
        kx = T if pv else HD
        hh = np.arange(nhd)[:, None]
        k = np.arange(kx)[None, :]
        xa = xb + (hh // IL) * f["me_xcs"] + k * f["me_xks"] + (hh % IL) * f["me_xjs"]
        x = G.to_bf16(self.read(xa, "att_x", pc).reshape(xa.shape))          # [heads, kx]
        rows = self.kr[:T]
        if np.isnan(rows).any():
            raise Defect(f"PC {pc}: attention reads a window row never written")
        if not np.array_equal(G.bits(rows), G.bits(self.kt[:T])):
            raise Defect(f"PC {pc}: row-major and transposed KV stores disagree")
        if pv:     # pv[hh, dim] = csum over rows of bf16(p) * kv[row, dim]
            res = V.csum(G.mul(x[:, None, :], rows.T[None, :, :]))           # [heads, HD]
            nout = HD
        else:      # s[hh, row] = csum over dims of q * kv[row, dim]
            res = V.csum(G.mul(x[:, None, :], rows[None, :, :]))             # [heads, T]
            nout = T
        ntw = cdiv(nout, W)
        o = np.arange(nout)
        tt, ll = o // W, o % W
        addr = (ob + tt[None, :] * f["me_ots"] + (hh // IL) * f["me_ogs"] + (hh % IL) * f["me_ojs"]) * W + ll[None, :]
        assert ntw * W >= nout
        if f["me_oen"]:
            self.write(0, res, idx=addr)
        log.append(dict(pc=pc, unit="ME", matrix="pv" if pv else "scores", heads=nhd, rows=int(T)))

    # -- HE ----------------------------------------------------------------------------------------------------------
    def he(self, f, pc, log):
        name, m = self.lay.engine_matrix("he", f["he_wbase"])
        n, K = f["he_nout"], f["he_k"]
        if f["he_wbase"] != m["base_word"] or n != m["nrows"] or K * R.HC_SPLIT != m["ncols"]:
            raise Defect(f"PC {pc}: HE descriptor does not cover {name}")
        x = self.read(f["he_xbase"] + np.arange(R.HC_SPLIT * K), "he_x", pc)
        w = self.dense_w(name)
        self.write(f["he_obase"], V.csum(G.mul(w, x[None, :])))
        log.append(dict(pc=pc, unit="HE", matrix=name, rows=int(n), k=int(K * R.HC_SPLIT)))

    # -- XU ----------------------------------------------------------------------------------------------------------
    def xu(self, f, pc, log):
        op = f["xu_op"]
        if op == I.XU_SEL:
            n = f["xu_n"] + self.dyn[f["xu_d_n"]]
            k = min(f["xu_k"] + self.dyn[f["xu_d_k"]], n)
            vals = self.read(f["xu_src"] + np.arange(n), "xu_src", pc)
            sel = sorted(int(i) for i in V.topk_lowest_index(vals, k))
            self.write(f["xu_dst"], np.array(sel, dtype=np.uint32).view(F))
            log.append(dict(pc=pc, unit="XU", op="select", n=int(n), k=int(k), selected=sel))
        elif op == I.XU_SINK:
            e = self.read(f["xu_src"] + np.arange(16), "xu_src", pc).reshape(4, 4)
            self.write(f["xu_dst"], P.sinkhorn(e, self.m).reshape(-1))
        else:
            raise Defect(f"PC {pc}: XU op {op} not in the layer-0 program")

    # -- SU (tools/hdc_program_v41.Machine.su1, full-shape operands) -------------------------------------------------
    def ckv_rows(self, ids, pc):
        st = self.stores
        if ids.min() < 0 or ids.max() > st["n"]:
            raise Defect(f"PC {pc}: selected compressed row outside the store (max {ids.max()}, rows {st['n'] + 1})")
        rows = st["ckv"][np.minimum(ids, st["n"] - 1)].astype(F)
        new = ids == st["n"]
        if new.any():
            if st["ckv_new"][self.r] is None:
                raise Defect(f"PC {pc}: the position's compressed row is selected before it is written")
            rows[new] = st["ckv_new"][self.r][1]
        return rows

    def addr(self, f, s, no, ni, idx=None):
        o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
        if s in "bd" and f["b_half"]:
            i = i >> 1
        base = f[f"{s}_base"] + self.dyn[f[f"{s}_d"]]
        if s == "a" and f["a_ind"] == I.IND_I:
            i = idx[i]
        if s == "a" and f["a_ind"] == I.IND_O:
            o = idx[o]
        return (base + o * f[f"{s}_so"] + i * f[f"{s}_si"]).reshape(-1)

    def crom_read(self, e, hi, pc):
        e = np.asarray(e, dtype=np.int64)
        top = e >> 28
        out = np.zeros(e.shape, dtype=F)
        rope = top >= 2
        if rope.any():
            kinds = np.unique(top[rope] - 2)
            for kind in kinds:
                sel = rope & (top - 2 == kind)
                if int(kind) not in self.rope_held:
                    raise Defect(f"PC {pc}: RoPE read of kind {kind} outside a CTL5/CTL6 hold")
                p, (cs, sn) = self.rope_held[int(kind)]
                low = e[sel] & ((1 << 28) - 1)
                if np.any(low // ROPE_PAIR != p) or np.any(low % ROPE_PAIR >= ROPE_PAIR):
                    raise Defect(f"PC {pc}: RoPE read of position {sorted(set((low // ROPE_PAIR).tolist()))} "
                                 f"while position {p} is held")
                out[sel] = (sn if hi else cs)[low % ROPE_PAIR]
        plain = ~rope
        if plain.any():
            ep = e[plain]
            if ep.max() >= len(self.crom) or not self.crom_ok[ep].all():
                raise Defect(f"PC {pc}: CROM read outside the bound constants")
            out[plain] = self.crom[ep, 1 if hi else 0]
        return out

    def fetch(self, f, s, e, pc):
        src = f[f"{s}_src"]
        if src == I.SRC_VM:
            return self.read(e, f"su_{s}", pc)
        if src in (I.SRC_CLO, I.SRC_CHI):
            return self.crom_read(e, src == I.SRC_CHI, pc)
        raise Defect(f"PC {pc}: SU operand {s} from the weight ROM in the layer program")

    def su(self, f, pc, log):
        if max(1, f["mx_m"]) > 1:
            raise Defect(f"PC {pc}: multi-position SU op in the layer program")
        d = self.dyn
        no = f["su_nout"] + d[f["su_d_nout"]]
        ni = f["su_nin"] + d[f["su_d_nin"]]
        if no == 0 or ni == 0:
            return
        idx = None
        if f["a_ind"]:
            cnt = ni if f["a_ind"] == I.IND_I else no
            idx = G.bits(self.read(f["a_ibase"] + np.arange(cnt), "su_index", pc)).astype(np.int64)
        ea = self.addr(f, "a", no, ni, idx)
        ckv_gather = self.stores is not None and f["a_ind"] == I.IND_O and f["dst"] in (I.DST_KV, I.DST_KVT)
        if ckv_gather:
            # full shape: the selected rows (global compressed-row ids) of the source's HBM store
            if f["a_src"] != I.SRC_VM or f["a_base"] != 0 or f["a_so"] != HD or f["a_si"] != 1 or ni != HD:
                raise Defect(f"PC {pc}: selected-row gather outside the compressed-store contract")
            a = self.ckv_rows(idx, pc).reshape(-1)
        else:
            a = self.fetch(f, "a", ea, pc)
        b = self.fetch(f, "b", self.addr(f, "b", no, ni), pc) if (f["m1"] in (I.M1_AB, I.M1_DIVB, I.M1_MAXB) or
                                                                 f["ad"] == I.AD_NEGB or f["e2"] == I.E2_MULB) \
            else np.zeros(no * ni, dtype=F)
        uses_c = f["c_pair"] or f["c_clip"] or f["m2"] == I.M2_C or f["qm"] != I.QM_OFF or \
            f["ad"] == I.AD_C or f["e1"] in (I.E1_MULC, I.E1_ADDC)
        ec = ea ^ 1 if f["c_pair"] else self.addr(f, "c", no, ni)
        c = self.fetch(f, "c", ec, pc) if uses_c else np.zeros(no * ni, dtype=F)
        uses_d = f["qm"] != I.QM_OFF or f["ad"] == I.AD_D
        dd = self.fetch(f, "d", self.addr(f, "d", no, ni), pc) if uses_d else np.zeros(no * ni, dtype=F)
        imm1, imm2, imm3 = (P.u32f(f[k]) for k in ("imm1", "imm2", "imm3"))
        if f["a_rnd"]:
            a = G.to_bf16(a)
        if f["a_relu"]:
            a = np.maximum(a, F(0)).astype(F)
        if f["a_min"]:
            a = np.minimum(a, imm3).astype(F)
        if f["c_clip"]:
            c = np.clip(c, -imm3, imm3).astype(F)
        p = {I.M1_BYP: lambda: a, I.M1_AB: lambda: G.mul(a, b), I.M1_AA: lambda: G.mul(a, a),
             I.M1_AIMM: lambda: G.mul(a, imm1), I.M1_DIVB: lambda: V.div(a, b), I.M1_DIVIMM: lambda: V.div(a, imm1),
             I.M1_MAXB: lambda: np.maximum(a, b).astype(F)}[f["m1"]]()
        p = {I.M2_BYP: lambda: p, I.M2_C: lambda: G.mul(p, c), I.M2_IMM: lambda: G.mul(p, imm1)}[f["m2"]]()
        par = np.tile(np.arange(ni) & 1, no)
        qd = {I.QM_OFF: None, I.QM_POS: dd, I.QM_NEG: G.neg(dd),
              I.QM_ALT_NP: np.where(par == 0, G.neg(dd), dd).astype(F),
              I.QM_ALT_PN: np.where(par == 0, dd, G.neg(dd)).astype(F)}[f["qm"]]
        q = None if qd is None else G.mul(c, qd)
        rr = {I.AD_BYP: lambda: p, I.AD_Q: lambda: G.add(p, q), I.AD_C: lambda: G.add(p, c),
              I.AD_NEGB: lambda: G.add(p, G.neg(b)), I.AD_IMM: lambda: G.add(p, imm2),
              I.AD_D: lambda: G.add(p, dd)}[f["ad"]]()
        s = {I.SFU_NONE: lambda: rr, I.SFU_EXP: lambda: G.exp(rr), I.SFU_RSQRT: lambda: G.rsqrt(rr),
             I.SFU_SQRT: lambda: V.sqrt(rr), I.SFU_SIGM: lambda: V.sigmoid(rr), I.SFU_SILU: lambda: V.silu(rr),
             I.SFU_SPSQRT: lambda: V.sqrt(V.softplus(rr))}[f["sfu"]]()
        t = {I.E1_BYP: lambda: s, I.E1_MULC: lambda: G.mul(s, c), I.E1_ADDC: lambda: G.add(s, c),
             I.E1_MULIMM: lambda: G.mul(s, imm2), I.E1_ADDIMM: lambda: G.add(s, imm2)}[f["e1"]]()
        u = {I.E2_BYP: lambda: t, I.E2_MULB: lambda: G.mul(t, b), I.E2_MULIMM: lambda: G.mul(t, imm1)}[f["e2"]]()
        out = np.asarray(u, dtype=F).reshape(-1)
        if f["rnd"]:
            out = G.to_bf16(out)
        if f["red"] and f["red_tree"]:
            v = G.mul(out, out) if f["red_sq"] else out
            x = V.csum(v)
            if f["red_rnd"]:
                x = G.to_bf16(x)
            self.write(f["r_base"], np.array([x], dtype=F))
        elif f["red"]:
            v = G.mul(out, out) if f["red_sq"] else out
            segs = v.reshape(1, -1) if f["red_whole"] else v.reshape(no, ni)
            vals = []
            for sg in segs:
                if f["red"] == I.RED_SUM:
                    vals.append(V.csum(sg))
                elif f["red"] == I.RED_MAX:
                    vals.append(np.max(sg))
                else:
                    acc = F(0)
                    for xx in sg:
                        acc = G.add(acc, xx)
                    vals.append(acc)
            vals = np.asarray(vals, dtype=F)
            if f["red_rnd"]:
                vals = G.to_bf16(vals)
            self.write(0, vals, idx=f["r_base"] + np.arange(len(vals)) * f["r_so"])
        if f["dst"] == I.DST_VM:
            self.write(0, out, idx=self.addr(f, "o", no, ni))
        elif f["dst"] in (I.DST_KV, I.DST_KVT):
            val = G.to_bf16(out).reshape(no, ni)
            if f["dst"] == I.DST_KVT and self.stores is not None and ni == self.stores["ihd"]:
                # the position's index key into the layer's index-key store (global key row dyn[o_d])
                row0 = self.dyn[f["o_d"]]
                if f["o_base"] != 0 or no != 1 or row0 != self.stores["n"]:
                    raise Defect(f"PC {pc}: index-key write to row {row0}, not the next key {self.stores['n']}")
                self.stores["ik_new_by_rank"][self.r] = val[0]
                if self.stores["ik_new"] is None or self.r == 0:
                    self.stores["ik_new"] = val[0]
                log.append(dict(pc=pc, unit="SU", ik_row=int(row0)))
                return
            if f["dst"] == I.DST_KVT:        # row dyn[o_d] + o, dimension i
                row0 = self.dyn[f["o_d"]]
                if f["o_base"] != 0 or ni != HD or not (0 <= row0 and row0 + no <= TROWS):
                    raise Defect(f"PC {pc}: transposed KV write outside the local window")
                self.kt[row0:row0 + no] = val
                log.append(dict(pc=pc, unit="SU", kv="transposed", rows=[int(row0), int(row0 + no)]))
            else:                             # row-major element address row * HD + dimension
                e = self.addr(f, "o", no, ni)
                if e.min() < 0 or e.max() >= TROWS * HD:
                    raise Defect(f"PC {pc}: row-major KV write outside the local window")
                self.kr.reshape(-1)[e] = val.reshape(-1)
                log.append(dict(pc=pc, unit="SU", kv="row_major", rows=[int(e.min() // HD), int(e.max() // HD) + 1]))


# -- the four-rank machine -------------------------------------------------------------------------------------------
def collective(ranks, f, pc, log):
    n, src, dst, op = f["coll_n"], f["coll_src"], f["coll_dst"], f["coll_op"]
    if f["wait"] != 31:
        raise Defect(f"PC {pc}: a collective must drain every unit (wait {f['wait']})")
    if n <= 0 or n % 16 or src % 16 or dst % 16:
        raise Defect(f"PC {pc}: collective count / alignment not in whole 16-lane words")
    out_n = {I.COLL_ALL_REDUCE_SUM: n, I.COLL_TOPK_MERGE: f["coll_k"]}.get(op, TP * n)
    if not (src + n <= dst or dst + out_n <= src):
        raise Defect(f"PC {pc}: collective source and destination overlap")
    parts = [rk.read(src + np.arange(n), "coll_src", pc) for rk in ranks]
    if op == I.COLL_TOPK_MERGE:
        # every rank's n (score, local id) pairs, global id = rank * dyn[coll_d_stride] + local id; the top k
        # by (score desc, global id asc), written ascending as u32 ids on every rank
        k, ib = f["coll_k"], f["coll_ibase"]
        if not 0 < k <= TP * n or ib % 16 or not (ib + n <= dst or dst + k <= ib):
            raise Defect(f"PC {pc}: TOPK_MERGE k / id base outside the contract")
        strides = [rk.dyn[f["coll_d_stride"]] for rk in ranks]
        if len(set(strides)) != 1:
            raise Defect(f"PC {pc}: ranks disagree on the merge stride")
        ids = np.concatenate([G.bits(rk.read(ib + np.arange(n), "coll_ids", pc)).astype(np.int64) + r * strides[0]
                              for r, rk in enumerate(ranks)])
        vals = np.concatenate(parts).astype(np.float64)
        vals = np.where(vals == 0, 0.0, vals)                  # -0 == +0 (values; the golden compares values)
        order = np.lexsort((ids, -vals))[:k]
        res = np.sort(ids[order]).astype(np.uint32).view(F)
        for rk in ranks:
            rk.write(dst, res)
        log.append(dict(pc=pc, unit="COLL", op="topk_merge", n=int(n), k=int(k), stride=int(strides[0]),
                        seq=int(f["coll_seq"])))
        return
    if op == I.COLL_ALL_GATHER:
        res = np.concatenate(parts)
    elif op == I.COLL_ALL_REDUCE_SUM:
        res = G.add(G.add(parts[0], parts[1]), G.add(parts[2], parts[3]))
        if f["coll_rnd"]:
            res = G.to_bf16(res)
    else:
        raise Defect(f"PC {pc}: collective op {op} not in the layer-0 contract")
    for rk in ranks:
        rk.write(dst, res)
    log.append(dict(pc=pc, unit="COLL", op={0: "all_reduce_sum", 1: "all_gather"}[op], n=int(n),
                    seq=int(f["coll_seq"]), rnd=int(f["coll_rnd"])))


def checkpoints(bind, L=0):
    """(name, golden key, VM region, element count, after PC) of the golden comparison points of layer L."""
    tr = bind["instruction_trace"]
    last = lambda tag: max(r["pc"] for r in tr if r["tag"] == tag)  # noqa: E731
    first_w = lambda tag, reg: min(r["pc"] for r in tr if r["tag"] == tag and reg in r["writes"])  # noqa: E731
    end = len(tr) - 1
    cps = [(f"L{L}.attn_norm", f"L{L}.attn_norm", "XN", 5120, last(f"L{L}.attn_norm")),
           (f"L{L}.attn", f"L{L}.attn", "Y", 5120, last(f"L{L}.out.wo_b_reduce")),
           (f"L{L}.ffn_norm", f"L{L}.ffn_norm", "XN", 5120, last(f"L{L}.ffn_norm")),
           (f"L{L}.router", f"L{L}.router", "BI", 384, first_w(f"L{L}.router", "BI")),
           (f"L{L}.ffn", f"L{L}.ffn", "YALL", 5120, last(f"L{L}.moe_sum.y_gather")),
           (f"block{L}", f"block{L}", "H", 20480, end),
           ("h_out", "h_out", "H", 20480, end),
           (f"pre{L}", f"pre{L}", "PF", 4, end),
           ("pre_out", "pre_out", "PF", 4, end)]
    if L == 20:
        fused = [r["pc"] for r in tr if r["tag"] == f"L{L}.indexer" and r["fields"].get("me_fuse")]
        cps += [(f"L{L}.index_scores (rank quarter)", "index_scores", "IS", None, fused[0]),
                (f"L{L}.index_select", "sel", "SELG", 512, last(f"L{L}.indexer.topk_merge")),
                (f"L{L}.candidate_blocks", "cand", "CAND", 2048, last(f"L{L}.candidates.topk_merge")),
                (f"win{L} (window row, KVQ)", f"win{L}", "KVQ", 512, first_w(f"L{L}.attn", "KVQ")),
                (f"ik{L} (index key)", f"ik{L}", "store:ik", 128, end),
                (f"ckv{L} (compressed row)", f"ckv{L}", "store:ckv", 512, end)]
    return cps


def golden_of(golden, gkey, rk, cnt):
    """The golden array a comparison point expects on rank rk (FP32 bit patterns or u32 ids)."""
    z, L = golden["z"], golden["layer"]
    if gkey == "index_scores":
        sc1 = rk.dyn[I.FULL_DYN["SC1"]]
        return z[f"L{L}.index_scores"][rk.r * sc1:(rk.r + 1) * sc1].astype(F)
    if gkey == "sel":
        return np.asarray(golden["shard"]["ctx_out"]["sel"], dtype=np.uint32).view(F)
    if gkey == "cand":
        blocks = np.nonzero(golden["cand"].reshape(-1, 8).any(axis=1))[0]
        return blocks.astype(np.uint32).view(F)
    return z[gkey].reshape(-1).astype(F)


def got_of(rk, reg, V_, n, pc_state=None):
    if reg == "store:ik":
        v = rk.stores["ik_new_by_rank"][rk.r]
        return (np.full(n, np.nan, F) if v is None else v), v is not None
    if reg == "store:ckv":
        v = rk.stores["ckv_new"][rk.r]
        return (np.full(n, np.nan, F) if v is None else v[1]), v is not None
    return rk.vm[V_[reg]:V_[reg] + n], bool(rk.ok[V_[reg]:V_[reg] + n].all())


def indexed_stores(m, st, L):
    """The layer's HBM stores entering the token: compressed rows and index keys (global row ids)."""
    ckv = np.stack(st["ckv"][L]).astype(F)
    ik = np.stack(st["ik"][L]).astype(F)
    assert len(ckv) == len(ik)
    return dict(ckv=ckv, ik=ik, n=len(ckv), ihd=ik.shape[1], ik_new=None,
                ik_new_by_rank={r: None for r in range(TP)}, ckv_new={r: None for r in range(TP)})


def run_context(ctx: int, scratch: Path, bind_path: Path, program: Path, log_fn=print, snap=None,
                on_pc=None, ranks_out=None, seed=LC.SEED, layer=0) -> dict:
    """snap: {pc: None} filled with every rank's VM after pc; on_pc(pc, ranks): called after every PC;
    ranks_out: a list that receives the four Rank objects (final VM, per-rank weight-op logs `rk.log`)."""
    L = layer
    golden = load_golden(ctx, scratch, seed, L)
    pos = golden["position"]
    lay = BoundLayout(bind_path)
    if lay.selected != golden["experts"]:
        raise SystemExit(f"bind {bind_path.name} selected experts {lay.selected} != golden {golden['experts']}")
    if lay.bind.get("layer", 0) != L:
        raise SystemExit(f"bind {bind_path.name} is not layer {L}")
    words = [int(x, 16) for x in program.read_text().split()]
    tr = lay.bind["instruction_trace"]
    if len(words) != len(tr):
        raise SystemExit("program and bind instruction counts differ")
    fields = []
    for pc, (w, row) in enumerate(zip(words, tr)):
        d = I.decode(w, full_shape=True)
        enc = {k: (I.FULL_DYN[tuple(v)] if isinstance(v, list) else I.FULL_DYN[v] if isinstance(v, str) else v)
               for k, v in row["fields"].items()}
        diff = [k for k, v in enc.items() if d[k] != v]
        if diff:
            raise SystemExit(f"PC {pc}: encoded program differs from bind {bind_path.name} in {diff}")
        fields.append(d)
    # the model constants, synthetic window / state, RoPE coefficients
    consts = KC.load("deepseek-v4.1-flash")
    man = json.loads(KC.OUT.read_text())["models"]["deepseek-v4.1-flash"]
    consts = dict(consts, _sinkhorn_iters=man["unit_parameters"]["sinkhorn_iters"]["value"])
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    st, sdesc = LC.synthetic_state(m, ctx, seed=seed, layers=[L])
    if golden["state_sha"] is not None and sdesc["sha256"][f"win{L}"] != golden["state_sha"]:
        raise SystemExit(f"ctx {ctx}: synthetic window rows differ from the golden record")
    win = np.stack(st["win"][L]).astype(F)
    stores = indexed_stores(m, st, L) if L in R.KV_SRC else None
    state_check = None
    if stores is not None:
        state_check = {k: sdesc["sha256"][f"{k}{L}"] for k in ("ckv", "ik")}
        state_check["rows"] = stores["n"]
    del st
    yarn = bool(R.RATIO[L])
    cs = V.rope_cs(m.freqs_yarn if yarn else m.freqs_plain, pos)
    rope = {(int(yarn), pos): cs}
    cache = json.loads(ROPE_CACHE.read_text())["fixtures"]
    fx = {(0, 199999): "plain200k", (0, 1048575): "plain1m", (1, 199999): "yarn200k"}.get((int(yarn), pos))
    rope_check = None
    if fx:
        pairs = np.stack(cs, axis=-1).astype("<f4")
        rope_check = dict(fixture=fx, binary_sha256=hashlib.sha256(pairs.tobytes()).hexdigest(),
                          match=hashlib.sha256(pairs.tobytes()).hexdigest() == cache[fx]["binary_sha256"])
        if not rope_check["match"]:
            raise SystemExit(f"RoPE coefficients at {pos} differ from the HBM cache fixture {fx}")
    ranks, rank_pins = [], {}
    for r in range(TP):
        man_r, img, pin = rank_images(ctx, r, scratch, golden)
        ranks.append(Rank(r, lay, man_r, img, golden, win, rope, consts, pos, stores=stores))
        rank_pins[str(r)] = pin
    V_ = ranks[0].V
    cps = checkpoints(lay.bind, L)
    results, trace = [], []
    defects = []
    for pc, f in enumerate(fields):
        f["_tag"] = tr[pc]["tag"]
        unit = f["unit"]
        try:
            if f["pred"] != I.PRED_ALWAYS:
                raise Defect(f"PC {pc}: predicated instruction in the layer program")
            if unit == I.UNIT_CTL and f["ctl"] == I.CTL_END:
                pass
            elif unit == I.UNIT_COLL:
                collective(ranks, f, pc, trace)
            else:
                for rk in ranks:
                    lg = rk.log
                    {I.UNIT_CTL: lambda: rk.ctl(f, pc), I.UNIT_ME: lambda: rk.me(f, pc, lg),
                     I.UNIT_SU: lambda: rk.su(f, pc, lg), I.UNIT_QE: lambda: rk.qe(f, pc, lg),
                     I.UNIT_XU: lambda: rk.xu(f, pc, lg), I.UNIT_HE: lambda: rk.he(f, pc, lg)}[unit]()
        except Defect as exc:
            defects.append(dict(pc=pc, tag=f["_tag"], defect=str(exc)))
            log_fn(f"ctx {ctx} L{L} DEFECT {exc}")
            break
        if on_pc is not None:
            on_pc(pc, ranks)
        if snap is not None and pc in snap:
            snap[pc] = [rk.vm.copy() for rk in ranks]
        for name, gkey, reg, cnt, at in cps:
            if at != pc:
                continue
            per_rank = []
            for rk in ranks:
                want = golden_of(golden, gkey, rk, cnt)
                got, wr = got_of(rk, reg, V_, len(want))
                bad = np.nonzero(G.bits(got) != G.bits(want))[0]
                per_rank.append(dict(rank=rk.r, written=bool(wr), mismatches=int(bad.size), elements=len(want),
                                     first_mismatch=int(bad[0]) if bad.size else None,
                                     got=f"0x{int(G.bits(got[bad[0]])):08x}" if bad.size else None,
                                     want=f"0x{int(G.bits(want[bad[0]])):08x}" if bad.size else None))
            ok = all(x["mismatches"] == 0 and x["written"] for x in per_rank)
            results.append(dict(region=name, golden_array=gkey, vm_region=reg,
                                vm_base=int(V_[reg]) if reg in V_ else None,
                                elements=per_rank[0]["elements"], after_pc=at, after_tag=tr[at]["tag"],
                                bit_exact=ok, per_rank=per_rank))
            log_fn(f"ctx {ctx} L{L} PC {at:3d} {name:32s} {'BIT-EXACT' if ok else 'MISMATCH'} "
                   f"{[x['mismatches'] for x in per_rank]}")
    if ranks_out is not None:
        ranks_out.extend(ranks)
    trace = [x for x in sorted(trace + ranks[0].log, key=lambda x: x["pc"])]
    unwritten = {str(rk.r): rk.unwritten for rk in ranks if rk.unwritten}
    exact = bool(results) and all(x["bit_exact"] for x in results) and not defects and not unwritten \
        and len(results) == len(cps)
    return dict(context=ctx, position=pos, seed=seed, layer=L, verdict="pass" if exact else "fail",
                experts=golden["experts"], regions=results, defects=defects, unwritten_reads=unwritten,
                instructions_executed=len(fields) if not defects else defects[0]["pc"],
                engine_log_rank0=trace, rope=rope_check, state_rows=state_check,
                inputs=dict(golden_shard_input_sha256=golden["record"]["input_sha256"],
                            golden_shard_output_sha256=golden["record"]["output_sha256"],
                            window_rows_sha256=golden["state_sha"] or sdesc["sha256"][f"win{L}"],
                            window_rows_check="golden record win0 digest" if golden["state_sha"] else
                            "re-derived from the seed (the reference record pins only the whole-state digest); "
                            "checked through the bit-exact attention output", rank_images=rank_pins,
                            program=str(program.relative_to(ROOT)), program_sha256=sha(program),
                            bind=str(bind_path.relative_to(ROOT)), bind_sha256=sha(bind_path),
                            layout=str(lay.layout_path.relative_to(ROOT)), layout_sha256=sha(lay.layout_path),
                            qe_stream=str(lay.qe_path.relative_to(ROOT)), qe_stream_sha256=sha(lay.qe_path)))


SOURCES = ("tools/v41_fullshape_isa.py", "tools/hdc_isa_v41.py", "tools/hdc_replay_v41.py",
           "tools/hdc_program_v41.py", "tools/hdc_golden_v41.py", "tools/hdc_golden.py",
           "tools/rtl_v41_fullshape_layer_campaign.py", "tools/v41_program_constants.py",
           "tools/v41_fullshape_program_bind.py", "tools/rtl_v41x_fullshape_l0_program.py",
           "results/rtl/v41_program_constants.json", "results/rtl/hdc_v41x_fullshape_l0_program.hex",
           "results/rtl/hdc_v41x_fullshape_l0_program.json", "results/rtl/hdc_v41x_fullshape_golden.json",
           "results/rtl/v41x_rope_hbm_cache.json", "results/rtl/w17_v41_1m_reference_token.json",
           "rtl/hdc/v41x/ot_hdc_core_v41x.sv",
           "rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv", "rtl/rom/ot_rom_oneshot_px.sv",
           "compiler/models/deepseek-v4.1-flash/inference_config.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--context", type=int, action="append")
    ap.add_argument("--scratch", type=Path, default=SCRATCH)
    ap.add_argument("--program", type=Path, default=PROGRAM)
    ap.add_argument("--record", type=Path)
    ap.add_argument("--fixes", type=Path, help="JSON list of the program fixes this run verifies")
    ap.add_argument("--seed", type=int, default=LC.SEED, help="golden seed (20260930: the 1M reference token)")
    ap.add_argument("--layer", type=int, default=0, help="0 (sliding) or 20 (ratio-1 KV / index / candidate source)")
    a = ap.parse_args()
    if a.layer == 20 and a.program == PROGRAM:
        a.program = PROGRAM_L20
    ctxs = a.context or [1048576, 200000]
    out = {}
    for ctx in ctxs:
        bind, scratch = case(ctx, a.seed, a.layer)
        scratch = a.scratch if (a.seed == LC.SEED and a.layer == 0) else scratch
        key = case_key(ctx, a.seed, a.layer)
        out[key] = run_context(ctx, scratch, bind, a.program, seed=a.seed, layer=a.layer)
        print(f"ctx {key}: {out[key]['verdict']}")
    if a.record:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        rec = dict(schema=SCHEMA,
                   status="pass" if all(v["verdict"] == "pass" for v in out.values()) else "fail",
                   claim_boundary=f"ISA-level execution of the encoded full-shape TP-4 layer-{a.layer} program on four "
                                  "ranks (program dataflow, addresses, strides, counts, DYN, constants, "
                                  "collectives) against the released-checkpoint golden on synthetic "
                                  "golden-consistent KV state. Weight-engine arithmetic is the golden's on the "
                                  "rank's image slice; no engine microarchitecture, RTL, cycle or physical verdict.",
                   generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   source_commit=head, arith=V.ARITH, program=str(a.program.relative_to(ROOT)),
                   program_sha256=sha(a.program),
                   fixes=json.loads(a.fixes.read_text()) if a.fixes else [],
                   contexts=out,
                   headline=f"1048576_seed{REF_SEED}" + (f"_L{a.layer}" if a.layer else ""),
                   **({"contract": CONTRACT_L20} if a.layer == 20 else {}),
                   source_sha256={s: sha(ROOT / s) for s in SOURCES},
                   reproduction="python3 tools/rtl_v41_fullshape_layer_campaign.py --steps images --contexts C "
                                "--layers 0 --rank R --scratch SCRATCH (R = 0..3, SCRATCH holding the golden "
                                "ctxC_L00.{json,npz} shards); python3 tools/v41_fullshape_isa.py --context C "
                                "--scratch SCRATCH --record OUT")
        if a.record.exists():          # contexts not re-run, the fix list and failed verdicts are kept
            old = json.loads(a.record.read_text())
            rec["contexts"] = {**old.get("contexts", {}), **out}
            rec["status"] = "pass" if all(v["verdict"] == "pass" for v in rec["contexts"].values()) else "fail"
            rec["fixes"] = rec["fixes"] or old.get("fixes", [])
            rec["failed_runs"] = list(old.get("failed_runs", []))
            for k in out:                 # a failed verdict is never overwritten: it moves to failed_runs
                if old.get("contexts", {}).get(k, {}).get("verdict") == "fail":
                    rec["failed_runs"].append(dict(key=k, program_sha256=old.get("program_sha256"),
                                                   source_commit=old.get("source_commit"), **{
                                                       x: old["contexts"][k].get(x) for x in
                                                       ("verdict", "defects", "regions")}))
        a.record.write_text(json.dumps(rec, indent=1) + "\n")
        print("wrote", a.record)
    return 0 if all(v["verdict"] == "pass" for v in out.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
