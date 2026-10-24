#!/usr/bin/env python3
"""LAYERBENCH-HBM (10-18) piece (a): d4g layer-programme compiler -> per-unit images + slice replay events.

From the compiler's static schedule of one layer (DS: results/rtl/hbm_ds_layer_tput_1018/priced_layers.json
segments[L].records; Qwen: results/rtl/hbm_qwen_layer_tput_1018/static_schedule.json schedule.<variant>.record.<stage>)
and the HGI programme those records come from, emit for every record the programme image the die would load, as
replay events at the SLICE INPUT PORTS whose driver is outside the slice (boundary.json of cut_slice.py).  Images
never patch on-chip datapath: they enter where the die's own (outside-slice) programme root drives them.

Unit formats (RTL of record = GEN2 die rev abbf5d21f; SU files byte-identical to origin/main):
  SU   pgp_SW (ot_hbm_su_programme_pslice_c5, ot_hbm_su_programme_pgcol.sv:181-211) is fed by su_prog (outside the
       slice) on su_prog__r_we[0] / r_bank[15:0] / r_row / r_data / r_start / r_len.  Quarter command line SB 2422 =
       {control 1742 [2421:680], vmr 8x30 [679:440], vmw 8x39 [439:128], rf 6x9 [127:74], red 74 [73:0]} -- the die
       wiring (die.v pgp_SW__command slices: su_SW<G>.control/vmr_cmd/vmw_cmd, sucore_SW.rf_rd_cmd/red_cmd) is exactly
       su_top_compile.py's quarter layout (su_top_compile.py:20-21, 71-80).  CONFIRMED by the die.v slice map.
       control = su_arith_generate.FIELDS (1742 b, su_arith_generate.py:18-30) lowered by su_arith_lower.lower()
       (canonical dispatch -> affine N512 issue groups; quarter q owns positions [128q,128q+128), su_arith_lower.py:58-66).
       vmr {v,sector16,grp4,row9} / vmw {v,src,grp4,row9,sector16,mask8} and their edges: ot_hbm_su_static_pgslice.sv:
       14-22 (FILL commit E+13; DRAIN LG write E+4, done +7).  Column image: su_programme_compile.lower_columns
       (config bank = 32 x column + local; 16 edges of 16-b dictionary index per row; leaf caps 3/13).
       Start -> command line 0 at the native pslice_c5 consumer = 9 edges (measured native producer, including
       registered column pins and PIPE=2 index/dictionary stages; the older five-edge reference is insufficient).
       config writes while idle, >= 2 edges before start (pgcol.sv:23-25).  Programme capacity EDGES 7111 a start
       (pgcol.sv:56): one programme per SU record, reloaded while the producer is idle (load-window conflicts listed).
  IDX  hb_idx__qctl_SW (ot_hbm_idx_qctl_static.sv) programme bus from col_idx (outside): col_idx__pw_we/pw_addr/pw_data,
       start col_idx__start_v; 32-b instruction, 8 a 256-b row (ot_hbm_idx_calendar_static.sv:2-5); words from
       tools/hbm_idx_static_calendar.compile_program (INDEX microprogram).  ASSUMED for IDX.TOPK route.top6: that
       compiler is the indexer programme, not parameterised by the MoE-router shape -> flagged.
  HOST CP (transport of every non-SU programme): cp_frames() = F20 frame / F28+F2c descriptor / F30 launch events on
       the host_cp_ingress__* slice inputs (hleaf_SW relays, CFG_LAT 2); SW target table SW_TARGETS (die.v tgt straps).
  SFU / COLL / HC / DMA / SM: cp_targets listed per record (SM / DMA row payloads: sm_images.py), others flag
       'format_open', reason 'payload_open: <compiler>'; records
       BLOCKED by an HBM-WIRE datapath gap carry 'blocked_by' (coverage.json grade).
ASSUMPTIONS (flagged in the output): serial edge = ceil(3 x stream cycle / 4) (3:4 serial domain, AGENTS.md clock
domains); the SU quarter-0 VM placement is the compiler's own (quarter-packed, sector s -> bank s mod 8 = store
group s mod 16, pgslice.sv:9-11; sector = q<<13 | row<<4 | hi<<3 | port as su_top_compile.py:113); VM operand words
enter as 'M' (memory preload) events -- the slice has no VM input port, the bench decides (producer replay or
image load); reductions (sut.red) need the reducer join calendar su_arith_lower lists as open -> flagged.
Fixture data: results/rtl/hbm_<d>_layer_tput_1018/fixtures (sibling fork); when absent the operand words are a
seeded placeholder (field inputs_placeholder true) and the expected words are computed from them with hdc_golden.

  PYTHONPATH=tools python3 -m hbm_layer_vehicle.layer_images --design ds --layer 0 --boundary B.json --out DIR
      [--records 4,31] [--programme ds_rank0_program.json] [--priced priced_layers.json] [--coverage coverage.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
for p in (TOOLS, TOOLS / "hbm_static", TOOLS / "hgi_adapters"):
    sys.path.insert(0, str(p))

BASE_SB_W = 2422
SB_W, Q_W = 2470, dict(control=1742, vmr=240, vmw=312, rf=54, red=74, tree=48)
START_ADVANCE, CFG_LEAD, EDGES_MAX = 9, 2, 7111
FILL_COMMIT, LANE_FETCH, DRAIN_DONE = 13, 3, 11       # pgslice.sv:14-22
SETUP_TO_EMIT = 8                                       # su_arith_compile.py: ld at cycle 0, emits from cycle 8
# first lane output after the setup line: su_top_compile FO = 8 + 23 + 4(MLAT-3) + (ALAT-3) + LEAF + 4 PIN_REG with
# the die's su_<q><g> parameters MLAT 4, ALAT 3, LEAF 1, PIN_REG 0 (die.v su_SW0 #(...)).
# HBM-P6-CMP: the over-cap pgslice split (ot_hbm_su_static_pgslice_lg_s) runs PIN_REG 1 = LS 'su_pin_reg' when
# OT_HBM_LEAF_SPLIT=1: first output +4 (36 -> 40 measured), requests +2 (su_top_compile --pin-reg rule).
import leaf_split_latency as LS  # noqa: E402
SU_PIN_REG = LS.shift('su_pin_reg')
FIRST_OUT = 8 + 23 + 4 * (4 - 3) + 0 + 1 + 4 * SU_PIN_REG
DS_PROGRAMME = ROOT / "results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json"


def serial(stream_cyc):
    return int(math.ceil(3 * float(stream_cyc) / 4))


def sha(b):
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------------------------- programme / dispatches
def ds_dispatches(prog_json, layer):
    """per programme record index of the layer: (record, effective dispatch dict | None), via the sequencer Ref
    (su_program_inventory.canonical_dispatches, generalised to any layer and to repeated tags)."""
    import su_bench as SB
    from hgi_sim import records as SR
    program = json.loads(Path(prog_json).read_text())
    ent = program["layers"][layer]["records"]
    words, recs = [], []
    for e in ent:
        payload = bytes.fromhex(e["hex"])
        r, _ = SR.decode_one(payload, 0)
        r.tag = e["tag"]
        recs.append(r)
        words += [int.from_bytes(payload[q:q + 16], "little") for q in range(0, len(payload), 16)]
    words += SB.C.SV.record(SB.C.SV.header("CTL", "END"),
                            descs={"A": SB.C.SV.mdesc(space=1, fmt=5, base=(1 << 18) - 16, n=1, m=1)})
    trace, _ = SB.C.SV.Ref(words, 0, 0, (1 << 20) - 1, 0, 129280, 1 << 20, {}).run()
    pc_of, pc = {}, 0
    for k, r in enumerate(recs):
        pc_of[pc] = k
        pc += SR.rec_bytes(r) // 16
    disp = {}
    for d in trace:
        k = pc_of.get(d["rec"])
        if k is not None and k not in disp:
            disp[k] = d
    return [(recs[k], disp.get(k), ent[k]) for k in range(len(recs))]


def ds_dispatches_image(per_die_json, rank="0"):
    """as ds_dispatches, from a fixture's per-rank HGI-1 layer image (ds_layer_fixtures --export-images:
    ranks[].image_hex + record_tags + dyn) -- the programme ds_native ran, so VM addresses match the fixture."""
    import ast
    import su_bench as SB
    from hgi_sim import records as SR
    img = json.loads(Path(per_die_json).read_text())
    rk = img["ranks"] if isinstance(img["ranks"], list) else ast.literal_eval(img["ranks"])
    rk = [x for x in rk if str(x["rank"]) == str(rank)][0]
    tags = img["record_tags"] if isinstance(img["record_tags"], list) else ast.literal_eval(img["record_tags"])
    buf = bytes.fromhex(rk["image_hex"])
    recs, ent, off = [], [], 0
    while off < len(buf):
        r, _ = SR.decode_one(buf, off)
        n = SR.rec_bytes(r)
        r.tag = tags[len(recs)] if len(recs) < len(tags) else ""
        recs.append(r)
        ent.append(dict(tag=r.tag, hex=buf[off:off + n].hex()))
        off += n
    words = [int.from_bytes(buf[q:q + 16], "little") for q in range(0, len(buf), 16)]
    words += SB.C.SV.record(SB.C.SV.header("CTL", "END"),
                            descs={"A": SB.C.SV.mdesc(space=1, fmt=5, base=(1 << 18) - 16, n=1, m=1)})
    dyn = rk.get("dyn") or [0, (1 << 20) - 1, 1 << 20, 0, 0, 0, 0, (1 << 20) - 1]
    trace, _ = SB.C.SV.Ref(words, 0, int(dyn[3]), int(dyn[1]), int(dyn[5]), 129280, 1 << 20, {}).run()
    pc_of, pc = {}, 0
    for k, r in enumerate(recs):
        pc_of[pc] = k
        pc += SR.rec_bytes(r) // 16
    disp = {}
    for d in trace:
        k = pc_of.get(d["rec"])
        if k is not None and k not in disp:
            disp[k] = d
    return [(recs[k], disp.get(k), ent[k]) for k in range(len(recs))]


# ------------------------------------------------------------------------------------------------------- SU golden
def vop_golden(sut, ops):
    """elementwise SU.VOP semantics of the lane datapath -- the operator model of su_arith_compile.py:63-85,
    generalised to the record's immediates (independent NumPy FP32 RNE, hdc_golden)."""
    from hdc_golden import add, mul, to_bf16
    f = lambda u: np.uint32(u).view(np.float32)
    a, b, c, d = (ops.get(k) for k in "ABCD")
    aa = to_bf16(a) if sut["a_rnd"] else a.copy()
    if sut["a_relu"]:
        aa = np.where(np.signbit(aa), np.float32(0), aa).astype(np.float32)
    if sut["a_min"]:
        aa = np.minimum(aa, f(sut["imm3"])).astype(np.float32)
    cc = np.clip(c, -f(sut["imm3"]), f(sut["imm3"])) if (sut["c_clip"] and c is not None) else c
    x, m = aa.copy(), sut["m1"]
    if m in (1, 2, 3):
        x = mul(aa, b if m == 1 else aa if m == 2 else f(sut["imm1"]))
    if m == 6:
        x = np.maximum(aa, b).astype(np.float32)
    if sut["m2"]:
        x = mul(x, cc if sut["m2"] == 1 else f(sut["imm1"]))
    if sut["qm"]:
        n = len(x)
        neg = (np.ones(n, bool) if sut["qm"] == 2 else np.arange(n) % 2 == 0 if sut["qm"] == 3 else
               np.arange(n) % 2 == 1 if sut["qm"] == 4 else np.zeros(n, bool))
        qv = mul(cc, np.where(neg, -d, d))
    ad = sut["ad"]
    if ad:
        x = add(x, qv if ad == 1 else cc if ad == 2 else -b if ad == 3 else f(sut["imm2"]) if ad == 4 else d)
    e1 = sut["e1"]
    if e1 in (1, 3):
        x = mul(x, cc if e1 == 1 else f(sut["imm2"]))
    if e1 in (2, 4):
        x = add(x, cc if e1 == 2 else f(sut["imm2"]))
    if sut["e2"]:
        x = mul(x, b if sut["e2"] == 1 else f(sut["imm1"]))
    bits = np.asarray(x, np.float32).view(np.uint32).copy()
    if sut["rnd"]:
        bits = ((bits.astype(np.uint64) + 0x7fff + ((bits >> 16) & 1)) & 0xffff0000).astype(np.uint32)
    return bits


# ---------------------------------------------------------------------------------------------- SU quarter programme
class QLine:
    """one quarter's command line stream (su_top_compile.Prog layout, one quarter)."""

    def __init__(s):
        s.f = {k: {} for k in Q_W}

    def put(s, fld, e, sh, w, val):
        cur = s.f[fld].get(e, 0)
        assert (cur >> sh) & ((1 << w) - 1) == 0, ("slot busy", fld, e, sh)
        s.f[fld][e] = cur | (val << sh)

    def vmr(s, e, p, sector, grp, row):
        s.put("vmr", e, p * 30, 30, (1 << 29) | (sector << 13) | (grp << 9) | row)

    def vmw(s, e, p, src, grp, row, sector, mask):
        s.put("vmw", e, p * 39, 39, (1 << 38) | (src << 37) | (grp << 33) | (row << 24) | (sector << 8) | mask)

    def lines(s):
        n = 1 + max([max(d) for d in s.f.values() if d] or [0])
        out = []
        for e in range(n):
            v = (s.f["tree"].get(e, 0) << Q_W["control"]) | s.f["control"].get(e, 0)
            for k in ("vmr", "vmw", "rf", "red"):
                v = (v << Q_W[k]) | s.f[k].get(e, 0)
            out.append(v)
        return out


class Placement:
    """layer-global quarter VM placement (compiler's own): logical VM sector -> physical sector of quarter q.
    A 128-lane issue block's group k (lanes 8k..8k+7) must sit in a sector on VM port k mod 8 (pgslice.sv:9-11,
    vmr 'port p fills store groups p and p+8'); physical sector = q<<13 | row<<3 | port (bank = port).  A logical
    sector is placed on first touch and keeps its place, so producer -> consumer records chain inside the slice;
    a later touch on another port is a placement conflict (needs an F2 re-placement copy, counted)."""

    def __init__(s, q):
        s.q, s.map, s.nxt, s.written, s.conflicts = q, {}, [0] * 8, set(), []

    def get(s, lsec, port, why):
        if lsec in s.map:
            ps = s.map[lsec]
            if ps % 8 != port:
                s.conflicts.append(dict(logical_sector=lsec, placed_port=ps % 8, wanted_port=port, at=why))
            return ps
        row = s.nxt[port]
        s.nxt[port] += 1
        assert row < 1 << 10, "quarter VM slice full"
        s.map[lsec] = (s.q << 13) | (row << 3) | port
        return s.map[lsec]


# SU reducer ingress (RTL facts, CDS 10-18): each quarter's ot_hbm_su_reduce_static takes ONE external operand per edge,
# the lane chosen by red_sel = {v, op3, osel, lane7} (pgslice.sv:355-361 -> qcore_r5.sv:103-107 slice_x[e_sl]); a lane's
# reducer value ro_v/ro_x is live for one edge only (lane.sv:119 "with vm_we timing", :719).  Dependent reducer ops issue
# >= RED_DEP edges apart, commits/exports +RED_LAT (reduce_static.sv:1-8).  The golden sum (hdc_golden csum: contiguous
# chunks of 8 summed sequentially from +0, chunk sums by a +0-padded pairwise tree) maps onto 8-op chunk chains + tree ops.
RED_DEP, RED_LAT, RED_QUARTERS = 10, 9, 4


def reducer_bound(words):
    """lower bound (serial edges) of one SU reduction of `words` lane values on the die's reducers: ingress
    ceil(words/4) (one operand / edge / quarter), then the last chunk's tail, the quarter chunk-sum tree, export,
    the 4-quarter join tree (2 levels) and the final export; RF relay / class-4 read edges NOT counted (bound)."""
    per_q = -(-words // RED_QUARTERS)
    chunks_q = max(1, -(-per_q // 8))
    tree_q = (chunks_q - 1).bit_length()
    tail = RED_DEP * (1 + tree_q) + RED_LAT + RED_DEP * 2 + RED_LAT
    return dict(words=words, ingress_edges=per_q, chunks_per_quarter=chunks_q, tail_edges=tail,
                min_serial_edges=per_q + tail,
                rule="1 reducer operand/edge/quarter (pgslice.sv:355-361, lane.sv:119); DEP 10, LAT 9 (reduce_static.sv)")


def calendar_collision(target, candidate, offset, *, exclusive_controls=False):
    """Detect static resource conflicts; an owned control cycle cannot be ORed.

    Disjoint control bits do not identify independent datapaths. The opt-in
    repaired contract therefore reserves the entire control word, including
    all-zero values, until that record's final declared consumer commit.
    """
    return any(offset + edge in target.f[field] and
               ((exclusive_controls and field == "control") or
                bool(target.f[field][offset + edge] & value))
               for field in Q_W for edge, value in candidate.f[field].items())


def su_record(raw, q=0, rng=None, data=None, place=None, tag="", pad_zero=False, timing=None, safe_calendar=False,
              identity_inactive_terms=False, absent_readers_identity=False, drain_guard=0):
    """lower one SU dispatch for quarter q: control (su_arith_lower), fill/drain calendars, expected VM words.
    Returns dict(status, lines, preload, expect, ...) with explicit reasons when v1 cannot emit a runnable image."""
    from hbm_layer_vehicle.native_profile import NativeTiming
    if timing is not None and not isinstance(timing, NativeTiming):
        raise TypeError("timing must be a source-defined NativeTiming")
    if safe_calendar and timing is None:
        raise ValueError("safe calendar requires an explicit native return contract")
    fill_commit = FILL_COMMIT if timing is None else timing.fill_commit
    drain_done = DRAIN_DONE if timing is None else timing.drain_done
    import su_arith_lower as L
    import su_program_inventory as I
    from su_arith_compile import pack, physical_word
    from su_arith_generate import FIELDS
    _, unit, sut, desc = I.decode(raw)
    if safe_calendar and "A" not in desc:
        raise ValueError("safe calendar supported profile requires a live A operand")
    row, sched = L.lower(raw)
    if safe_calendar and len(sched) != 1:
        raise ValueError("safe calendar supported profile requires exactly one issue group")
    if safe_calendar:
        # The native numerical witness is record23's A -> BF16 -> O path.
        # A single issue alone proves neither reducer/R commits nor another
        # backend control lifetime. Keep these unproved modes fail-closed.
        tested_sut = dict.fromkeys((
            "a_src", "a_ind", "b_src", "b_half", "c_src", "c_pair", "d_src",
            "a_rnd", "a_relu", "a_min", "c_clip", "m1", "m2", "qm", "ad", "sfu",
            "e1", "e2", "rnd", "dst", "red", "red_sq", "red_whole", "red_rnd",
            "su_vec", "red_tree", "imm1", "imm2", "imm3"), 0)
        tested_sut.update(rnd=1, dst=1)
        if unit != 2 or sut != tested_sut or set(desc) != {"A", "O"}:
            raise ValueError("safe calendar requires the tested A-to-O BF16 non-reducer control profile")
        for md in desc.values():
            if (md.space != "VM" or md.fmt != "FP32" or md.n != 128 or md.m != 1
                    or md.stride != 0 or md.istride not in (0, 1)
                    or any(getattr(md, name) for name in
                           ("lstride", "dyn_sel", "dyn_mul", "n_sel", "l1stride", "ibcast", "indexed"))
                    or md.base % 8):
                raise ValueError("safe calendar requires the tested aligned 128-word VM descriptor profile")
    res = dict(lowering={k: v for k, v in row.items() if k != "sut"}, sut=sut, reasons=[])
    if timing is not None:
        res["native_timing"] = timing.as_dict()
    if not row["supported"]:
        res.update(status="unsupported_lowering", reasons=row["reasons"])
        return res
    if row.get("empty"):
        res.update(status="empty")
        return res
    if sut["red"]:
        res["reasons"].append("reducer_join_calendar_open (su_arith_lower open: scalar_reducer_external_joins; "
                              "golden csum8 tree order must be matched)")
        res["reducer_bound"] = reducer_bound(int(row["words"]))
    roles = [r for r in "ABCD" if r in desc]
    for r in roles:
        md = desc[r]
        if md.ibcast or (md.istride or 1) != 1:
            res["reasons"].append(f"operand {r} broadcast/strided: needs RF-broadcast (srcs) calendar")
    off = {n: 0 for n, _ in FIELDS}
    pos = 0
    for n, w in reversed(FIELDS):
        off[n] = pos
        pos += w
    get = lambda v, n: (v >> off[n]) & ((1 << dict(FIELDS)[n]) - 1)
    def put(v, name, value):
        mask = ((1 << dict(FIELDS)[name]) - 1) << off[name]
        return (v & ~mask) | (value << off[name])

    if safe_calendar:
        # All four physical readers qualify even when a semantic operand is absent.
        # Use the live A stream's local identity; no additional FILL is required.
        sched = [list(words) for words in sched]
        for words in sched:
            w = words[q]
            terms, vb = get(w, "ld_c"), get(w, "vb")
            for index, role in enumerate("ABCD"):
                if role not in desc:
                    terms |= (terms & ((1 << 240) - 1)) << (240 * index)
                    vb |= (vb & 0xffffff) << (24 * index)
            words[q] = put(put(w, "ld_c", terms), "vb", vb)
    if absent_readers_identity and not safe_calendar:
        # opt-in (TOK-FUNC2-HBM-SU): every lane reads all four operand ports; pgslice.sv:303 faults a live lane whose
        # read address is not its own bank, so an absent role reads the live A stream's own-bank address (as the safe
        # calendar profile does) instead of address 0
        sched = [list(words) for words in sched]
        for words in sched:
            w = words[q]
            t_, vb_ = get(w, "ld_c"), get(w, "vb")
            for index, role in enumerate("ABCD"):
                if role not in desc:
                    t_ = (t_ & ~(((1 << 240) - 1) << (240 * index))) | ((t_ & ((1 << 240) - 1)) << (240 * index))
                    vb_ = (vb_ & ~(0xffffff << (24 * index))) | ((vb_ & 0xffffff) << (24 * index))
            words[q] = put(put(w, "ld_c", t_), "vb", vb_)
    if identity_inactive_terms and not safe_calendar and desc["A"].m == 1:
        # TOK-FUNC2-HBM-SU (opt-in): a single-row record (no == 1) leaves lanes >= 2**ls inactive; their lane-bit terms
        # (outer stride 0) alias every lane onto lanes 0..2**ls-1, so a group's 8 lane addresses are not one sector.
        # Give those bits the lane identity (+2**k): active lanes' addresses are unchanged, inactive lanes point into
        # their own bank (pinned-bank rule), and every active group is one aligned sector.
        sched = [list(words) for words in sched]
        for words in sched:
            w = words[q]
            ls0, terms0 = get(w, "ls"), get(w, "ld_c")
            for s_, role in enumerate("ABCDO"):
                if role not in desc or desc[role].ibcast:
                    continue
                for k in range(ls0, 7):
                    sh = 24 * (s_ * 10 + k)
                    terms0 = (terms0 & ~(0xffffff << sh)) | ((1 << k) << sh)
            words[q] = put(w, "ld_c", terms0)
    # per issue group: the quarter's 128 lanes' logical VM word address of every role (vb + lane terms)
    ls = get(sched[0][q], "ls")
    terms = get(sched[0][q], "ld_c")
    lanes = np.arange(128)
    tsum = lambda s: np.array([sum((terms >> (24 * (s * 10 + k))) & 0xffffff for k in range(7) if l >> k & 1)
                               for l in lanes], dtype=np.int64)
    T = {s: tsum(s) for s in range(5)}
    no, ni = desc["A"].m, raw >> 2176
    groups = []
    for g, words in enumerate(sched):
        w = words[q]
        vb = get(w, "vb")
        ov, iv = get(w, "o_v"), get(w, "i_v")
        act = np.array([(ov + (l >> ls)) < no and (iv + (l & ((1 << ls) - 1))) < ni for l in lanes])
        addr = {r: ((vb >> (24 * s)) & 0xffffff) + T[s] for s, r in enumerate("ABCDO") if r in desc}
        groups.append(dict(word=w, act=act, addr=addr))
    # quarter-packed VM placement (compiler's own) + store rows; fill / issue / drain calendar
    QL, preload, expect = QLine(), {}, []
    place = place if place is not None else Placement(q)
    fills, drains = [], []
    vals = {}
    srow = {r: 0 for r in "ABCDO"}
    fill_e = [0] * 8                         # next free fill edge per VM port (one read sector / bank / edge)
    e_issue = []
    rows_used = 0
    for g, G in enumerate(groups):
        last_commit = 0
        for r in roles:
            st_row = rows_used
            rows_used += 1
            G.setdefault("srow", {})[r] = st_row
            for k in range(16):
                ln = slice(8 * k, 8 * k + 8)
                if not G["act"][ln].any():
                    continue
                la = G["addr"][r][8 * k:8 * k + 8]
                p = k % 8
                if not (la[0] % 8 == 0 and all(int(la[j]) == int(la[0]) + j for j in range(8))):
                    res["reasons"].append(f"operand {r} group {k} not one aligned VM sector")
                    continue
                sec = place.get(int(la[0]) >> 3, p, f"{tag}:{r}")
                e = fill_e[p]
                fill_e[p] = e + 1
                QL.vmr(e, p, sec, k, st_row)
                fills.append((int(la[0]) >> 3, e))
                last_commit = max(last_commit, e + fill_commit)
                if (int(la[0]) >> 3) not in place.written:
                    preload[sec] = [int(a) for a in la]      # not produced earlier in this run: enters as an image
        e_issue.append(last_commit)
    # control lines: setup (ld) then one emit per issue group (issue edges non-decreasing, after the fills commit)
    setup = max(0, min(e_issue) - SETUP_TO_EMIT) if e_issue else 0
    ctl0 = groups[0]["word"]
    vbmask = ((1 << 120) - 1) << off["vb"]

    def with_vb(w, G):
        vb = 0
        for s, r in enumerate("ABCDO"):
            if r in desc or ((safe_calendar or absent_readers_identity) and r in "ABCD"):
                rr = G["srow"].get(r, G["srow"].get("A", 0)) if r != "O" else G["orow"]
                vb |= physical_word(q, rr) << (24 * s)
        return (w & ~vbmask) | (vb << off["vb"])

    out_base = rows_used
    for g, G in enumerate(groups):
        G["orow"] = out_base + g
    QL.f["control"][setup] = (with_vb(ctl0, groups[0]) | (1 << off["ld"])) & ~(1 << off["emit"])
    e = setup + SETUP_TO_EMIT
    issue_at = []
    for g, G in enumerate(groups):
        e = max(e, e_issue[g] - LANE_FETCH)
        QL.f["control"][e] = with_vb(G["word"], G)
        issue_at.append(e)
        e += 1
    # drain the O words of every issue group: store row orow -> VM sector (quarter-packed), after the lane write
    drain_e = [0] * 8
    commits = []
    if "O" in desc:
        for g, G in enumerate(groups):
            # Pin-captured write and read coincide under the old calendar.
            # OLD-read SRAM requires the DRAIN to sample one serial edge later.
            ready = setup + FIRST_OUT + (issue_at[g] - setup - SETUP_TO_EMIT) + int(safe_calendar) + drain_guard
            for k in range(16):
                ln = slice(8 * k, 8 * k + 8)
                m = G["act"][ln]
                if not m.any():
                    continue
                p = k % 8
                de = max(ready, drain_e[p])
                drain_e[p] = de + 1
                la = G["addr"]["O"][8 * k:8 * k + 8]
                if not (la[0] % 8 == 0 and all(int(la[j]) == int(la[0]) + j for j in range(8))):
                    res["reasons"].append(f"output group {k} not one aligned VM sector")
                    continue
                sec = place.get(int(la[0]) >> 3, p, f"{tag}:O")
                place.written.add(int(la[0]) >> 3)
                mask = int(sum(1 << j for j in range(8) if m[j]))
                QL.vmw(de, p, 0, k, G["orow"], sec, mask)
                commits.append(de + drain_done)
                drains.append((int(la[0]) >> 3, de + drain_done))
                expect.append(dict(sector=sec, mask=mask, edge=de + drain_done,
                                   words=[int(a) for a in G["addr"]["O"][8 * k:8 * k + 8]]))
    if safe_calendar:
        # Conservative full-operation reservation: direct backend controls are
        # consumed throughout the pipeline, not only at emit. Different
        # records must never share this reservation, even for disjoint bits.
        variable = sum(((1 << dict(FIELDS)[name]) - 1) << off[name]
                       for name in ("emit", "ld", "vb", "o_v", "i_v"))
        signature = ctl0 & ~variable
        if any((G["word"] & ~variable) != signature for G in groups):
            raise ValueError("heterogeneous arithmetic controls in one live reservation")
        hold = with_vb(ctl0, groups[0]) & ~(1 << off["ld"]) & ~(1 << off["emit"])
        end = max(commits, default=max(issue_at, default=setup))
        for edge in range(end + 1):
            QL.f["control"].setdefault(edge, hold)
        res["control_reservation"] = dict(first=0, last=end, policy="exclusive_record",
                                            drain_extra_serial_edges=1)
    # operand values (fixture or seeded placeholder) and the expected O words (hdc_golden)
    rng = rng or np.random.default_rng(0)
    logical = sorted({a for v in preload.values() for a in v})
    res["inputs_placeholder"] = False
    if data is None:
        data = {}
    pad = 0
    for a_ in logical:
        if a_ not in data:
            if pad_zero:        # fixture run: a word of a fetched sector outside every operand = inactive-lane pad
                data[a_] = np.float32(0)
                pad += 1
            else:
                data[a_] = np.float32(rng.standard_normal())
                res["inputs_placeholder"] = True
    if pad:
        res["pad_words_zero"] = pad
    # Freeze the actual pre-operation inputs before an in-place O can mutate
    # the shared logical state. Hex strings own their bits; no NumPy view aliases.
    input_data = {str(a): f"{int(np.float32(data[a]).view(np.uint32)):08x}" for a in logical}
    if not sut["red"] and "O" in desc and not res["reasons"]:
        # elementwise: lane l of group g computes O[addr_O] from A..D at the same lane
        outv = {}
        for g, G in enumerate(groups):
            idx = np.nonzero(G["act"])[0]
            ops = {r: np.array([data[int(a)] for a in G["addr"][r][idx]], np.float32) for r in roles}
            bits = vop_golden(sut, ops)
            for l, b in zip(idx, bits):
                outv[int(G["addr"]["O"][l])] = int(b)
                data[int(G["addr"]["O"][l])] = np.uint32(b).view(np.float32)   # chained consumers read it
        for x in expect:
            x["value"] = [outv.get(a) for a in x["words"]]
    if res["reasons"]:
        res["status"] = "v1_unsupported"
    res.update(status=res.get("status", "emitted"), ql=QL, fills=fills, drains=drains, lines=QL.lines(), preload=preload, expect=expect,
               data=input_data, preload_data=input_data,
               preload_provenance="pre-operation VM input snapshot; expected outputs never seed M",
               setup_edge=setup, issue_edges=issue_at, last_commit=max(commits) if commits else None,
               fill_sectors=len(preload), drain_sectors=len(expect))
    return res


def column_image(lines, work):
    """quarter line stream -> pslice_c5 configuration writes (su_programme_compile.lower_columns)."""
    import su_programme_compile as PC
    work.mkdir(parents=True, exist_ok=True)
    (work / "quarter.mem").write_text("".join(f"{v:0{(SB_W + 3) // 4}x}\n" for v in lines))
    man = PC.lower_columns(work / "quarter.mem", work / "cols", line_bits=SB_W,
                           resident_edges=EDGES_MAX)
    cfg = [(int(l[:4], 16), int(l[4:6], 16), l[6:]) for l in (work / "cols/config.mem").read_text().split()]
    return man, cfg


# ---------------------------------------------------------------------------------------------------- DS fixtures
def desc_addrs(d):
    """VM word addresses of a fixture descriptor [base, n, m, stride, istride, space, fmt] in array order
    (row i of m, column j of n: base + i*stride + j*istride; ds_layer_fixtures flattens row-major)."""
    base, n, m, st, ist = (int(x) for x in d[:5])
    return [base + i * st + j * ist for i in range(m) for j in range(n)]


def load_fixture(fdir, rank="0"):
    """priced record i -> dict(vm_in {addr: f32}, vm_out {addr: u32}, k, tag) from a ds_layer_fixtures dir."""
    recs = json.loads((Path(fdir) / "records.json").read_text())["records"][str(rank)]
    z = np.load(Path(fdir) / "operands.npz")
    out = {}
    for x in recs:
        ent = dict(k=x["k_layer"], tag=x["tag"], occ=int(x.get("occ", 0)), vm_in={}, vm_out={})
        for io, key in (("inputs", "vm_in"), ("outputs", "vm_out")):
            for role, v in x.get(io, {}).items():
                if v.get("space") != "VM" or v.get("array") not in z:
                    continue
                arr = np.asarray(z[v["array"]], np.uint32)
                ad = desc_addrs(x["desc"][role])
                assert len(ad) == len(arr), (fdir, x["tag"], role, len(ad), len(arr))
                for a_, w in zip(ad, arr):
                    ent[key][a_] = np.uint32(w).view(np.float32) if key == "vm_in" else int(w)
        for p in x.get("priced", []):
            out[int(p["i"])] = ent
    return out


def fixture_check(su, fr):
    """the image compiler's expected O words vs the fixture's post-record VM (bit-exact ds_native)."""
    n = bad = 0
    for x in su.get("expect", []):
        for a_, v in zip(x["words"], x.get("value") or []):
            if v is None or a_ not in fr["vm_out"]:
                continue
            n += 1
            bad += int(v) != fr["vm_out"][a_]
    su["fixture"] = dict(matched=True, k_layer=fr["k"], checked_words=n, mismatched_words=bad)
    if bad:
        su["reasons"].append(f"golden_mismatch: {bad}/{n} O words differ from the ds_native fixture")
        su["status"] = "golden_mismatch"


# ------------------------------------------------------------------------------------------------------------ main
UNIT_PORTS = dict(SU=["su_prog__r_we", "su_prog__r_bank", "su_prog__r_row", "su_prog__r_data", "su_prog__r_start",
                      "su_prog__r_len"],
                  IDX=["col_idx__pw_we", "col_idx__pw_addr", "col_idx__pw_data", "col_idx__start_v", "col_idx__prm"],
                  HC=["hc_eng__qi_v", "hc_eng__qi_word", "hc_eng__qd_v", "hc_eng__result"],
                  COLL=["host_cp_ingress__cfg_v", "host_cp_ingress__cfg_data", "host_cp_ingress__desc_v",
                        "host_cp_ingress__launch_v", "ep_S0__rx_pin_flit", "ep_S1__rx_pin_flit"],
                  SFU=["host_cp_ingress__cfg_v", "host_cp_ingress__cfg_data"], SM=[], DMA=[], ATT=[], FUSED=[])


# Host-CP configuration transport (every non-SU programme of the SW slice; RTL rtl/hbm_accel/host_static_20261015):
# host_cp_ingress (ot_hbm_host_static_ingress, OUTSIDE the slice) -> hleaf_SW (ot_hbm_host_cfg_leaf_sw, CFG_LAT 2, a/b
# copy groups) -> the target's own local programme store.  Frame = {cfg_target 8, cfg_addr (row) 12, cfg_data 256}
# (F20 select + 8 x F24 pieces at the ingress), descriptor {desc_base 12, desc_limit 13 (exclusive), desc_loops 16}
# (F28 + F2c), launch_v (F30).  The replay drives the ingress OUTPUT pins (= slice inputs host_cp_ingress__*), stream
# domain, at the rate the ingress can produce them.
# INGRESS RATE (VEH-FMT-SM 10-18, CONFIRMED against ot_hbm_host_static_ingress.sv:34-80 by a cycle model of its AXI-lite
# admission, tb_hbm_host_static_ingress write32 protocol): every F2x is ONE AXI write; s_awready / s_wready pulse at most
# every other edge, land in pin flops, and stay low while the write's B response is pending, so even an ideal master
# (AW+W together, bready 1) completes one write per AXI_WRITE_EDGES = 5 edges.  A 256-b row = 8 F24 writes = 40 edges
# (the 16 edges assumed before were 2.5x optimistic); F20 select = 1 write and the row address auto-increments, so
# consecutive rows of one target need no new F20; descriptor = F28 + F2c (2 writes); launch = F30, which the ingress
# refuses while its guard (5 after F2c) is non-zero -> one idle write slot between F2c and F30 (launch_ok,
# ingress.sv:62, :114-117).  Output pins are registered one edge after the write executes (ingress.sv:44-51).
AXI_WRITE_EDGES = 5
CP_FRAME_EDGES = 8 * AXI_WRITE_EDGES               # one 256-b row
CP_DESC_GUARD = AXI_WRITE_EDGES                    # kept for callers: one write slot
CP_LAUNCH_GUARD = 7                                # ingress launch guard (README): no frame in the 7 edges after F30
CP_DESC_TO_LAUNCH = 2 * AXI_WRITE_EDGES            # F2c -> F30: guard 5 must be 0 at the F30 execute edge
CP_SCAN_GUARD = 8                                  # desc -> scan start (leaf CFG_LAT 2 + target capture) + margin
# SW-slice targets (die.v GEN2 e92f4d03 scan: instances whose cfg_v is hleaf_SW__a/b_cfg_v, tgt strap) per HGI unit.
# The PAYLOAD (row words) of each target is the target's own ABI (sm_images.py for SM / DMA; sibling lanes for the rest).
# The SW slice holds 8 SMs, but only sm_SW0..3 are SW-leaf configured: cp_svg_SW4..7 / xc_SW4..7 hang on the SE leaf
# (slice inputs hleaf_SE__b_* / hleaf_SE__a_*, SE_LEAF_TARGETS) and sm_SW4..7 results leave the slice (smw_SW lanes4
# serves sm_SW0..3 only, slice.v smw_SW s0..s3) -- VEH-FMT-SM 10-18.
SW_TARGETS = {
    "SM": [(f"cp_svg_SW{k}", 64 + k) for k in range(4)] +                                # ot_static_cmd_target MODE 0
          [("xl_SW_ctl", 100), ("smw_SW", 160)] + [(f"xc_SW{k}", 192 + k) for k in range(4)] +
          [("calendar_SW", 96), ("refcfg_SW", 126)],
    "COLL": [("hb_coll_SW", None), ("vmfc_SW", 56), ("epcal_SW", 132)],   # hb_coll_SW: strap inside the hard master
    "DMA": [("hb_dbk_SW", 104), ("calendar_SW", 96)],
    "HC": [("hc_SW", 108)],
    "FUSED": [("hc_SW", 108), ("col_sfu_SW", 116)],
    "SFU": [("col_sfu_SW", 116)],
    "ATT": [], "IDX": [("col_idx (outside SW, hleaf_SE)", 120)],
}
# targets inside the SW slice configured through OTHER boundary inputs: (instance, tgt, slice input prefix).  A replay
# that drives hleaf_SE__* stands in for the SE leaf's output pins (its CFG_LAT 2 is then the replay's to model).
SE_LEAF_TARGETS = [(f"cp_svg_SW{k}", 64 + k, "hleaf_SE__b_") for k in range(4, 8)] + \
                  [(f"xc_SW{k}", 192 + k, "hleaf_SE__a_") for k in range(4, 8)]
DIRECT_TARGETS = [("hcollgi_SW", 176, "host_cp_ingress__")]          # COLL gather issue: on the ingress bus itself
PAYLOAD_COMPILER = {
    "SM": "sm_images.py (cp_svg feed programme + issuer descriptors, xc ext calendar, xl_SW_ctl x-load table, smw_SW "
          "writer table, calendar_SW VM calendar, packed136 HBM image)",
    "COLL": "ALL_GATHER on-die quadrant phase: hbm_layer_vehicle/coll_images.py (hcollgi_SW gq row + calendar_SW + far-end "
            "ring replay, VEH-FMT-COLL); cross-die / GROUP_REDUCE_MCAST / TOPK_MERGE / ROW_GATHER: hb_coll_SW 1536-b ISA "
            "rows (ot_hgi_coll_issuer_m) have no bound common production compiler; source-only "
            "tkm_endpoint_1021.endpoint_plan@ca8bc89afd537729fc1f722306efa9cf8142c05b is unqualified until "
            "issuer-to-endpoint age, real own/peer producers, qslots, writer and160-clock schedule are bound",
    "DMA": "sm_images.py (hb_dbk_SW command table) + calendar_SW",
    "HC": "hc_SW (ot_hbm_hc_qhub_static) row ABI",
    "FUSED": "hc_SW rows + col_sfu_SW collar (2 striped spaces, tools/hbm_static/su_arith_sfu_compile.py lanes)",
    "SFU": "col_sfu_SW collar (ot_hbm_static_cfg_collar NS 2) <- tools/hbm_static/su_arith_sfu_compile.py",
    "ATT": "no ATT engine in the SW slice (tools/hbm_attention_static_calendar.py is the engine calendar)",
    "IDX": "tools/hbm_idx_static_calendar.py (col_idx collar, SE leaf: outside the SW slice)",
}


class CpBus:
    """the ingress output stream of one replay: AXI-write slots at AXI_WRITE_EDGES, events on the ingress output pins
    (stream domain).  install() / desc() / launch() append in programme order; .t is the next free write edge."""

    def __init__(s, t=0, src="image:CP"):
        s.t, s.ev, s.src, s.sel = t, [], src, None

    def _d(s, c, port, v, **kw):
        s.ev.append(dict(k="D", dom="stream", cyc=c, port=f"host_cp_ingress__{port}", val=f"{v:x}", src=s.src, **kw))

    def _write(s):
        s.t += AXI_WRITE_EDGES
        return s.t                                  # output pins change right after this edge

    def install(s, target, rows, base=0, **kw):
        """rows (256-b ints) at rows base.. of target; returns the edge of the last cfg_v."""
        if s.sel != (target, base):
            s._write()                              # F20 select {row base, target}
        c = None
        for j, w in enumerate(rows):
            assert 0 <= w < 1 << 256 and base + j < 1 << 12
            c = s.t + 7 * AXI_WRITE_EDGES + AXI_WRITE_EDGES     # 8th F24 executes
            s.t = c
            s._d(c, "cfg_target", target, **kw)
            s._d(c, "cfg_addr", base + j, **kw)
            s._d(c, "cfg_data", w, **kw)
            s._d(c, "cfg_v", 1, **kw)
            s._d(c + 1, "cfg_v", 0, **kw)
        s.sel = (target, base + len(rows))
        return c

    def desc(s, target, base, limit, loops=1, **kw):
        if s.sel is None or s.sel[0] != target:
            s._write()                              # F20 select of the target (row field unused by F28/F2c)
            s.sel = (target, base)
        s._write()                                  # F28
        c = s._write()                              # F2c -> desc_v
        s._d(c, "cfg_target", target, **kw)
        s._d(c, "desc_base", base, **kw)
        s._d(c, "desc_limit", limit, **kw)
        s._d(c, "desc_loops", loops, **kw)
        s._d(c, "desc_v", 1, **kw)
        s._d(c + 1, "desc_v", 0, **kw)
        s.last_desc = c
        # VEH-CUTS 10-19: the target scans rows [base, limit) one per edge after the descriptor
        # (ot_static_program_target.sv: launch while scanning faults, measured on the GEN2b idxtk cut with a 151-row
        # calendar: hleaf_SW s_fault, no programme start).  The launch waits for the scan of every armed target.
        s.scan_end = max(getattr(s, "scan_end", -99), c + (limit - base) + CP_SCAN_GUARD)
        return c

    def launch(s, **kw):
        c = max(s._write(), getattr(s, "last_desc", -99) + CP_DESC_TO_LAUNCH, getattr(s, "scan_end", -99))
        s.t = c
        s._d(c, "launch_v", 1, **kw)
        s._d(c + 1, "launch_v", 0, **kw)
        s.t = c + CP_LAUNCH_GUARD
        return c


def cp_frames(target, rows, t, base=0, loops=1, launch=True):
    """replay D events (stream domain, ingress output pins) installing `rows` (256-b ints) at rows base.. of
    `target`, then its descriptor and (optionally) the launch, at the ingress rate.  Returns (events, launch_edge,
    next_free_edge)."""
    b = CpBus(t)
    b.install(target, rows, base)
    b.desc(target, base, base + len(rows), loops)
    lt = b.launch() if launch else None
    return b.ev, lt, b.t


def place_snapshot(p):
    return dict(p.map), list(p.nxt), set(p.written), len(p.conflicts)


def place_restore(p, snap):
    p.map, p.nxt, p.written = dict(snap[0]), list(snap[1]), set(snap[2])
    del p.conflicts[snap[3]:]


def downstream_reference(fx, i, word):
    """bits of VM word `word` as the first LATER fixture record reads it (comparison only, never a DUT input)"""
    for j in sorted(k for k in fx if k > i):
        v = fx[j]["vm_in"].get(word)
        if v is not None:
            return int(np.float32(v).view(np.uint32)), j
    return None, None


def vector_sectors(desc):
    """logical VM sectors of a record's vector operands / output (broadcast B and R excluded)"""
    out = set()
    for role, md in desc.items():
        if role == "R" or (role == "B" and md.ibcast) or md.space != "VM" or md.indexed:
            continue
        for i in range(max(1, md.m)):
            lo = md.base + i * (md.stride or 0)
            out.update(range(lo // 8, (lo + max(1, md.n) * (md.istride or 1) - 1) // 8 + 1))
    return out


def su_lower2(raw, a, r, fx, vm_data, place, timing, bnd, fr, sfu_layout=None, native_components=None):
    """TOK-FUNC2-HBM-SU dispatch: the first production lowering whose profile matches the record; every attempt that
    does not emit restores the layer placement (a refused record never marks its O sectors as written)."""
    import su_program_inventory as I
    from hbm_layer_vehicle import su_layer_lower_1021 as SL
    _, unit, sut, desc = I.decode(raw)
    rng = np.random.default_rng(1018)
    tag = r["tag"]
    tried = []

    def attempt(name, fn):
        snap = place_snapshot(place)
        dsnap = dict(vm_data)
        try:
            res = fn()
        except (AssertionError, ValueError) as ex:    # e.g. quarter VM slice full: refuse, restore, continue
            res = dict(status="adapter_refused", reasons=[f"{name}: {ex}"], lowering=dict(supported=False), sut=sut)
        if res.get("status") == "emitted" and len(place.conflicts) > snap[3]:
            res = dict(res, status="v1_unsupported", reasons=list(res.get("reasons", [])) + [
                f"VM placement conflict: {place.conflicts[snap[3]]}"])
        if res.get("status") != "emitted":
            place_restore(place, snap)
            vm_data.clear()
            vm_data.update(dsnap)
        tried.append(dict(lowering=name, status=res.get("status"), reasons=res.get("reasons", [])[:4]))
        return res

    in_layout = bool(sfu_layout and vector_sectors(desc) & sfu_layout)
    core = {"str_C", "sucore_SW", "stl_SW"}
    tree_ok = core <= set(bnd["instances"])
    res = None
    if unit == 2 and desc.get('A') is not None and desc['A'].indexed and tag.startswith('route.gather'):
        from hbm_layer_vehicle import su_indexed_gather_2000 as G
        window = None
        if a.fixtures:
            metadata = json.loads((a.fixtures/'records.json').read_text())['records'][str(a.rank)]
            current = next(x for x in metadata if x['tag']==tag)
            producers = [x for x in metadata if x['k'] < current['k'] and
                         x.get('desc',{}).get('O',[None,0])[0] == desc['A'].base and
                         x.get('desc',{}).get('O',[None,0])[1] > 1]
            if producers:
                producer = producers[-1]
                md = producer['desc']['O']
                window = dict(base=md[0],limit=md[0]+md[1],producer=producer['tag'],
                              source_receipt=str(a.fixtures/'records.json')+':'+sha((a.fixtures/'records.json').read_bytes()))
        if window is not None and native_components is not None:
            gsc=next((c for c in native_components.comps.values() if c['x']['tag']=='router_gather.gsc' and c.get('lowered')),None)
            if gsc is not None and gsc.get('F')==12 and gsc.get('stride')==16:
                prefix=place.q<<13
                window['segment_bases']=[8*(prefix|gsc['src'])]+[8*(prefix|(gsc['dst']+rank*gsc['stride'])) for rank in (1,2,3)]
                window['placement_source']='actual active COLL GSC component allocation'
        binding = G.load_binding(a.gather_binding) if getattr(a,'gather_binding',None) else None
        if binding and binding.get('status')=='PASS':
            if binding.get('instance') not in bnd['instances']:
                raise ValueError('indexed gather engine is not an actual selected slice instance')
            if any(cal.get('instance') not in bnd['instances'] for cal in binding.get('bank_calendars',{}).values()):
                raise ValueError('native gather bank calendar is not an actual selected slice instance')
        result = G.lower(raw,tag=tag,source_window=window,binding=binding,record_start=r['start'],placement=place)
        result['su_lower2_attempts']=[dict(lowering='native_indexed_scalar',status=result['status'],reasons=result['reasons'])]
        return result
    if a.rope_candidate and unit == 2 and sut.get('c_pair') and sut.get('b_half'):
        from hbm_layer_vehicle import su_rope_bank_1340 as RP
        import copy
        if not tree_ok or not {'sucore_SE','sucore_NW','sucore_NE'} <= set(bnd['instances']):
            return dict(status='unsupported_lowering', reasons=['candidate RoPE requires real four-core RF tree'],
                        lowering=dict(supported=False), sut=sut)
        def candidate_rope():
            saved = copy.deepcopy(place.__dict__)
            try:
                # Reserve one aligned 16-sector live run. Return any alignment
                # padding to the ledger; scratch is written only by runtime RF drains.
                allocation = place.alloc_run(32, 0)
                scratch = ((allocation + 15)//16)*16
                if scratch > allocation:
                    place.free_run(allocation, scratch-allocation)
                if scratch+16 < allocation+32:
                    place.free_run(scratch+16, allocation+32-(scratch+16))
                result = RP.lower(raw, q=a.quarter, data=vm_data, place=place, tag=tag, timing=timing,
                                  scratch_base=8*scratch, pair_c_reads=1,
                                  pair_source_path=a.rope_source, pair_die_path=a.rope_die)
            except Exception:
                place.__dict__.clear(); place.__dict__.update(saved)
                raise
            if result.get('status') != 'emitted':
                place.__dict__.clear(); place.__dict__.update(saved)
            return result
        res = attempt('candidate_runtime_RoPE', candidate_rope)
    elif unit == 2 and SL.reduce_profile(sut, desc) and not (in_layout and SL.sfu_profile(sut, desc, layout=True)):
        if not tree_ok:
            res = dict(status="unsupported_lowering", reasons=["reduction requires the real stree cut (no RF injection)"],
                       lowering=dict(supported=False), sut=sut)
        else:
            R = desc["R"]
            refs = [downstream_reference(fx, r["i"], R.base + k) if fx else (None, None) for k in range(R.m)]
            vals = [x for x, _ in refs]
            res = attempt("pretree_reduce", lambda: SL.lower_reduce(raw, a.quarter, data=vm_data, place=place, tag=tag,
                                                                    timing=timing, expected_reduction_word=vals))
            if any(x is not None for x in vals):
                res["fixture_reduction_reference"] = dict(
                    value=[None if x is None else f"{x:08x}" for x in vals] if R.m > 1 else f"{vals[0]:08x}",
                    source=f"fixture record(s) {sorted({j for _, j in refs if j is not None})} input (later consumer), "
                           "comparison only", matched=res["status"] == "emitted")
    elif unit == 2 and tree_ok and SL.rows_bcast_profile(sut, desc):
        res = attempt("rows_bcast", lambda: SL.lower_rows_bcast(raw, a.quarter, data=vm_data, place=place, tag=tag,
                                                                timing=timing, rf_local=a.rf_local))
    elif unit == 2 and tree_ok and SL.scalar_rf_profile(sut, desc) and not (
            SL.rsqrt_profile(sut, desc) and desc["A"].n == 1 and desc["A"].base % 8 == 0
            and desc["O"].base % 8 == 0):
        res = attempt("scalar_rf", lambda: SL.lower_scalar_rf(raw, a.quarter, data=vm_data, place=place, tag=tag,
                                                              timing=timing, rf_local=a.rf_local))
    elif unit == 2 and SL.rsqrt_profile(sut, desc):
        res = attempt("scalar_rsqrt", lambda: SL.lower_rsqrt(raw, a.quarter, data=vm_data, place=place, tag=tag,
                                                             timing=timing, side_profile=(4, 3),
                                                             side_source_path=a.side_source))
    elif unit == 2 and (SL.sfu_profile(sut, desc) or (in_layout and SL.sfu_profile(sut, desc, layout=True))) and (
            tree_ok or not ((desc.get("B") and desc["B"].ibcast) or sut["red"])):
        ref = None
        if sut["red"] and fx:
            ref, _ = downstream_reference(fx, r["i"], desc["R"].base)
        res = attempt("sfu_lanes", lambda: SL.lower_sfu_lanes(raw, a.quarter, data=vm_data, place=place, tag=tag,
                                                              timing=timing, rf_local=a.rf_local, layout=in_layout,
                                                              pretree_profile=getattr(a, "su_pretree_timing", None),
                                                              expected_reduction_word=ref))
    else:
        # every live lane reads all four operand ports (absent roles = A's own-bank address) and the drain samples
        # one edge after the lane write (OLD-read SRAM), as the safe-calendar profile
        res = attempt("su_record", lambda: su_record(raw, a.quarter, rng, data=vm_data, place=place, tag=tag,
                                                     pad_zero=fr is not None, timing=timing,
                                                     absent_readers_identity=True, drain_guard=1))
        if res.get("status") == "v1_unsupported":
            b = desc.get("B")
            if b is not None and b.ibcast and tree_ok:
                res2 = attempt("rf_broadcast", lambda: SL.lower_bcast(raw, a.quarter, data=vm_data, place=place, tag=tag,
                                                                      timing=timing, rf_local=a.rf_local))
            elif desc["A"].m == 1:
                res2 = attempt("identity_inactive_terms", lambda: su_record(
                    raw, a.quarter, rng, data=vm_data, place=place, tag=tag, pad_zero=fr is not None, timing=timing,
                    identity_inactive_terms=True, absent_readers_identity=True, drain_guard=1))
            else:
                res2 = None
            if res2 is not None and res2.get("status") == "emitted":
                res = res2
    if res.get("status") == "emitted":
        for addr, bits in res.get("expected_post_state", {}).items():
            vm_data[int(addr)] = np.uint32(int(bits, 16)).view(np.float32)
    res.setdefault("reasons", [])
    res.setdefault("lowering", {})
    res["su_lower2_attempts"] = tried
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--design", choices=["ds", "qwen"], default="ds")
    ap.add_argument("--layer", default="0")
    ap.add_argument("--priced", type=Path, default=ROOT / "results/rtl/hbm_ds_layer_tput_1018/priced_layers.json")
    ap.add_argument("--coverage", type=Path, default=ROOT / "results/rtl/hbm_ds_layer_tput_1018/coverage.json")
    ap.add_argument("--programme", type=Path, default=DS_PROGRAMME)
    ap.add_argument("--boundary", type=Path, required=True)
    ap.add_argument("--records", help="comma list of priced record indices (default: all)")
    ap.add_argument("--quarter", type=int, default=0, help="SU quarter of the slice (SW = 0)")
    ap.add_argument("--load-gap", type=int, default=16, help="serial edges between reset release and layer t0 slack")
    ap.add_argument("--reload-gap", type=int, default=600, help="idle serial edges after which a new SU programme is loaded")
    ap.add_argument("--fixtures", type=Path, help="DS per-record fixture dir (ds_layer_fixtures.py: records.json + "
                    "operands.npz, e.g. results/rtl/hbm_ds_layer_tput_1018/fixtures/L02): VM operands = the bit-exact "
                    "ds_native state before each record, expected O checked against its state after (default: seeded "
                    "placeholder operands)")
    ap.add_argument("--rank", default="0", help="fixture rank")
    ap.add_argument("--native-read-return", type=int, help="explicit native stream read-return edges")
    ap.add_argument("--native-write-return", type=int, help="explicit native stream write-return edges")
    ap.add_argument("--connected-lowering", action="store_true", help="selected source-bound L0 reduction/scalar implementation; execution remains unqualified")
    ap.add_argument("--side-source", type=Path, help="actual repaired scoped SIDE source in compiled bundle")
    ap.add_argument("--su-lower2", action="store_true", help="TOK-FUNC2-HBM-SU opt-in production SU lowerings by "
                    "record profile on every layer (pretree reductions, scalar rsqrt, RF-broadcast B, single-row "
                    "identity lane terms); failed attempts leave the VM placement / written state untouched")
    ap.add_argument("--su-pretree-profile", type=Path, help="measured selected-source slice/join timing receipt")
    ap.add_argument("--gather-binding", type=Path, help="actual selected indexed-scalar VM port/clock/producer binding")
    ap.add_argument("--rf-local", type=int, default=1, help="selected su_<q><g> RF_LOCAL parameter (contract)")
    ap.add_argument('--rope-candidate', action='store_true', help='explicit unqualified candidate source: local C bank exchange and runtime coefficient staging')
    ap.add_argument('--rope-source', type=Path, help='actual candidate scoped pgslice source')
    ap.add_argument('--rope-die', type=Path, help='actual candidate die with all four SW PAIR_C_READS=1 bindings')
    ap.add_argument('--pv-probability-candidate', action='store_true', help='emit source-bound partial PV input plans; keeps ATT.PV consumer/calendar open')
    ap.add_argument('--pv-probability-source', type=Path, help='actual source root containing qualified probability producer candidate files')
    ap.add_argument('--pv-probability-contract', type=Path, help='actual selected xload parameter contract')
    ap.add_argument("--nev", type=int, default=0, help="(--su-lower2) built TB event depth: split into independent replays")
    ap.add_argument("--defer-records", default="", help="(--su-lower2, internal) records left unlowered because their "
                    "VM-linked programme group exceeds the TB event depth")
    ap.add_argument("--cx", action="store_true", help="TOK-FUNC2-HBM-CX: COLL/HC component records CONNECTED in the layer "
                    "(shared placement, interleaved SU/component epochs, producer-cone parts; cx_layer_1021)")
    ap.add_argument("--cx-ops", default="COLL,HC")
    ap.add_argument("--cx-contract", type=Path)
    ap.add_argument("--cx-l12", type=Path)
    ap.add_argument("--cx-checkpoint", type=Path)
    ap.add_argument("--cx-hc-source-profile", choices=["safe2_phase40_qchx12"], help="default-off bounded SAFE2 HC candidate, requires matching contract and k31 A64/O72 scope")
    ap.add_argument("--cx-chapters", default="", help="priced records starting a new VM chapter (quarter VM reset; "
                    "parts never span chapters; values crossing it are imaged, listed)")
    ap.add_argument("--cx-skip", default="", help="priced component records left as fixture-imaged probes (VM capacity)")
    ap.add_argument("--safe-calendar", action="store_true", help="opt-in tested 128-word A-to-O BF16 profile, exclusive controls and OLD-read drain gap")
    ap.add_argument("--sm-lowering", action="store_true",
                    help="opt-in (TOK-FUNC2-HBM-SM 10-21): lower every SM.MATVEC record onto the slice's real SM chain "
                         "(sm_slice_lower.py: cp_svg/svg/xc + xl_SW_ctl x load + smw_SW writer + HBM image); writes "
                         "OUT/sm/replay.json (separate component replay) and marks those records emitted")
    ap.add_argument("--smw", type=Path, help="with --sm-lowering: SM weight root (ds_sm_weights.py OUT, holds L<LL>/)")
    ap.add_argument("--sm-count", type=int, default=4, help="with --sm-lowering: SW SM service groups driven (sm_SW0..)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.su_pretree_profile and not a.su_lower2:
        ap.error("--su-pretree-profile requires --su-lower2")
    from hbm_layer_vehicle.native_profile import NativePretreeTiming
    a.su_pretree_timing = NativePretreeTiming.load(a.su_pretree_profile) if a.su_pretree_profile else None
    if a.rope_candidate and (not a.su_lower2 or a.rope_source is None or a.rope_die is None):
        ap.error('--rope-candidate requires --su-lower2 and actual --rope-source/--rope-die bindings')
    if a.pv_probability_candidate and (not a.su_lower2 or a.fixtures is None or
            a.pv_probability_source is None or a.pv_probability_contract is None):
        ap.error('--pv-probability-candidate requires actual source/contract and fixture-backed --su-lower2 producer')
    if a.sm_lowering and (a.smw is None or a.fixtures is None):
        ap.error("--sm-lowering needs --fixtures and --smw")
    if (a.native_read_return is None) != (a.native_write_return is None):
        ap.error("native read/write return contracts must be specified together")
    if a.safe_calendar and a.native_read_return is None:
        ap.error("--safe-calendar requires an explicit native read/write return contract")
    from hbm_layer_vehicle.native_profile import NativeTiming
    native_timing = (None if a.native_read_return is None else
                     NativeTiming(a.native_read_return, a.native_write_return))
    if a.design == "qwen":
        sys.exit("layer_images: Qwen D4G8 programme source (qwen_d4g_proof program.hgi1) not wired yet -- see lane notes")
    bnd = json.loads(a.boundary.read_text())
    inports = {e["name"]: e for e in bnd["inputs"]}
    pr = json.loads(a.priced.read_text())["segments"][a.layer]
    cov = {}
    if a.coverage.exists():
        cv = json.loads(a.coverage.read_text())
        cov = {r["i"]: r for r in cv["layers"].get(a.layer, {}).get("rows", [])}
    lay = int(a.layer) if a.layer.isdigit() else None
    if lay is None:
        sys.exit("layer_images: head segment needs the head programme (ds_rank0_program has layers only)")
    recs = pr["records"]
    fx = load_fixture(a.fixtures, a.rank) if a.fixtures else {}
    if fx:
        # the fixture's own layer image (the programme ds_native ran bit-exact); priced i -> image record k_layer
        imgs = sorted((a.fixtures / "images").glob("*_per_die.json"))
        prog_src = imgs[0]
        prog = ds_dispatches_image(prog_src, a.rank)
        # k_layer counts DISPATCHED records only (the image also holds the rank's CTL.NOPs): match (tag, occurrence)
        where = {}
        for k, (_, _, e) in enumerate(prog):
            where.setdefault(e["tag"], []).append(k)
        pk_of = {i: where[f["tag"]][f["occ"]] for i, f in fx.items()
                 if f["occ"] < len(where.get(f["tag"], []))}
    else:
        prog_src = a.programme
        prog = ds_dispatches(a.programme, lay)
        aligned = len(prog) == len([r for r in recs if r["unit"] != "CTL"]) or len(prog) == len(recs)
        pk_of = {r["i"]: r["i"] for r in recs if aligned and r["i"] < len(prog)}
    want = set(int(x) for x in a.records.split(",")) if a.records else None
    sfu_layout = set()
    if a.su_lower2:
        # tensors touched by a record that needs the KIND-1 lanes live in the 32-lane SFU layout (sector 4s+j on VM
        # port j); every SU record touching them is lowered in that layout (layer-global compiler placement)
        import su_bench as SB
        import su_program_inventory as I
        from hbm_layer_vehicle import su_layer_lower_1021 as SL
        for r in recs:
            pk = pk_of.get(r["i"])
            if r["unit"] != "SU" or pk is None or prog[pk][1] is None:
                continue
            try:
                _, u_, sut_, desc_ = I.decode(SB.pack_rec(prog[pk][1]))
            except AssertionError:
                continue
            if u_ == 2 and SL.sfu_profile(sut_, desc_):
                sfu_layout |= vector_sectors(desc_)
    a.out.mkdir(parents=True, exist_ok=True)
    events, manifest, t_su_free = [], [], 0
    rng = np.random.default_rng(1018)
    place, vm_data = Placement(a.quarter), {}
    if a.rope_candidate and not a.cx:
        from hbm_layer_vehicle import cx_layer_1021 as CX
        place = CX.make_placement(Placement, a.quarter)
    cx = None
    if a.cx:
        from hbm_layer_vehicle import cx_layer_1021 as CX
        if not fx:
            ap.error("--cx requires --fixtures")
        place = CX.make_placement(Placement, a.quarter)
        cx = CX.Cx(a.fixtures, a.rank, recs, place, contract=a.cx_contract, l12=a.cx_l12, checkpoint=a.cx_checkpoint,
                   boundary=bnd, ops=set(a.cx_ops.split(",")), skip={int(x) for x in a.cx_skip.split(",") if x},
                   chapters={int(x) for x in a.cx_chapters.split(",") if x}, hc_source_profile=a.cx_hc_source_profile)
    if cx is not None and getattr(a,'gather_binding',None):
        gathers=[x for x in cx.frecs if x['tag'].startswith('route.gather')]
        if gathers:
            last=max(x['k'] for x in gathers)
            for source in cx.comps.values():
                if source['x']['tag']=='router_gather.gsc':
                    md=source['x']['desc']['O']
                    for sector in range(md[0]//8,(md[0]+md[1]-1)//8+1):
                        place.last_read[sector]=max(place.last_read.get(sector,-1),last)
    # layer t0 (serial): reset relay 3 edges + the first record's whole configuration load + slack
    pending = []
    for r in recs:
        if want is not None and r["i"] not in want:
            continue
        if r["unit"] == "CTL":
            continue
        ent = dict(i=r["i"], unit=r["unit"], op=r["orig_op"], tag=r["tag"], start=r["start"], end=r["end"],
                   cls=r["cls"], grade=cov.get(r["i"], {}).get("grade"),
                   blocked_by=cov.get(r["i"], {}).get("datapath_gaps") or [],
                   open_gaps=cov.get(r["i"], {}).get("open_gaps") or [])
        pk = pk_of.get(r["i"])
        if pk is not None and prog[pk][2]["tag"] != r["tag"]:
            ent["programme_tag_mismatch"] = prog[pk][2]["tag"]
        unit = r["orig_op"].split(".")[0]
        ent["target_ports"] = [p for p in UNIT_PORTS.get(unit, []) if p in inports]
        if cx is not None:
            cx.before_record(r["i"], fx.get(r["i"]), placed=(unit == "SU"))
            if r["i"] in cx.comps:
                e2, comp = cx.lower(r["i"], cap=(a.nev or 11651) - 1)
                ent.update(e2)
                if comp is not None:
                    pending.append((r, ent, dict(cx_comp=comp)))
                if ent["blocked_by"]:
                    ent["status"] = "blocked:" + ent["status"]
                manifest.append(ent)
                continue
        if unit == "SU" and pk is not None and prog[pk][1] is not None:
            import su_bench as SB
            raw = SB.pack_rec(prog[pk][1])
            fr = fx.get(r["i"])
            if fr is not None:
                vm_data.update(fr["vm_in"])           # the record's operands = ds_native VM state before it
            try:
                if a.su_lower2 and str(r["i"]) in a.defer_records.split(","):
                    su = dict(status="deferred_nev", reasons=[f"VM-linked programme group exceeds the built TB event "
                                                               f"depth NEV {a.nev}; record left for a larger TB"],
                              lowering=dict(supported=True, deferred=True))
                elif a.su_lower2:
                    su = su_lower2(raw, a, r, fx, vm_data, place, native_timing, bnd, fr, sfu_layout=sfu_layout, native_components=cx)
                elif a.connected_lowering and lay == 0 and r['i'] in (4, 8):
                    from hbm_layer_vehicle import su_layer_lower_1021 as SL
                    required = {'str_C', 'sucore_SW', 'sucore_SE', 'sucore_NW', 'sucore_NE'}
                    if not required <= set(bnd['instances']):
                        raise ValueError('selected reduction requires real four-core/stree cut; no RF return injection')
                    if r['i'] == 4:
                        expected = int(np.float32(fx[8]['vm_in'][49920]).view(np.uint32))
                        su = SL.lower(raw, a.quarter, rng, data=vm_data, place=place, tag=r['tag'],
                                      pad_zero=fr is not None, timing=native_timing, expected_reduction_word=expected)
                        su['fixture_reduction_reference'] = dict(value=f'{expected:08x}', source='actual downstream fixture k10 A, not prior R input')
                    else:
                        su = SL.lower_norm_rs(raw, a.quarter, data=vm_data, place=place, tag=r['tag'],
                                              timing=native_timing, side_profile=(4,3), side_source_path=a.side_source)
                    for addr,bits in su.get('expected_post_state', {}).items():
                        vm_data[int(addr)] = np.uint32(int(bits,16)).view(np.float32)
                else:
                    su = su_record(raw, a.quarter, rng, data=vm_data, place=place, tag=r["tag"], pad_zero=fr is not None, timing=native_timing, safe_calendar=a.safe_calendar)
            except AssertionError as ex:                # su_program_inventory.decode: adapter contract refusal
                ent.update(status="adapter_refused", reasons=[f"su_record: {ex}"])
                manifest.append(ent)
                continue
            if fr is not None:
                fixture_check(su, fr)
            if cx is not None:
                cx.after_su(r["i"], su, fr)
            ent.update(status=su["status"], reasons=su["reasons"], lowering=su["lowering"],
                       inputs_placeholder=su.get("inputs_placeholder"))
            if su.get('native_gather'):
                directory=a.out/'images'/f"r{r['i']:03d}_gather"
                directory.mkdir(parents=True,exist_ok=True)
                (directory/'plan.json').write_text(json.dumps(su['native_gather'],indent=1)+'\n')
                ent['native_gather']=su['native_gather']
                ent['native_gather_plan']=str(directory/'plan.json')
                if su.get('native_gather_replay_events'):
                    replay=dict(schema='opentallas.hbm_slice_replay.v1',scope='component_probe',
                        qualifies_native_layer=False,qualifies_native_chain=False,
                        events=su['native_gather_replay_events'],
                        assumptions=['actual runtime producer leases required; no fixture output or resolved index injected'])
                    (directory/'replay.json').write_text(json.dumps(replay,indent=1)+'\n')
                    ent['native_gather_replay']=str(directory/'replay.json')
                    ent['target_ports']=sorted({x['port'] for x in su['native_gather_replay_events'] if x['k']=='D'})
            if su.get("su_lower2_attempts") is not None:
                ent["su_lower2_attempts"] = su["su_lower2_attempts"]
            if su.get('runtime_coefficient_moves'):
                ent['candidate_rope'] = dict(execution_qualified=False,
                    runtime_coefficient_moves=su['runtime_coefficient_moves'],
                    scratch_write_footprint=su['scratch_write_footprint'],
                    scratch_read_footprint=su['scratch_read_footprint'],
                    scratch_reuse_after_serial=su['scratch_reuse_after_serial'],
                    preload_provenance=su['preload_provenance'])
            if su.get('timing_obligations'):
                ent.update(timing_obligations=su['timing_obligations'], source_contract=su['source_contract'],
                           execution_qualified=False, quarter_ownership=su.get('quarter_ownership'),
                           expected_reference=su.get('expected_reference'),
                           fixture_reduction_reference=su.get('fixture_reduction_reference'),
                           compiled_record_stream_edges=su['timing_obligations']['stream_edges'],
                           prior_record_price=r['end']-r['start'],
                           prior_record_price_qualified=False,
                           record_price_delta_stream_edges=su['timing_obligations']['stream_edges']-(r['end']-r['start']),
                           price_scope='actual emitted bounded programme, no inherited layer/token throughput claim')
                ent['effective_record_price'] = dict(serial_edges=len(su.get('lines', [])),
                    stream_edges=su['timing_obligations']['stream_edges'],
                    source='actual emitted programme occupancy; configuration cost recorded separately per programme',
                    inherited_price_qualified=False, execution_qualified=False)
            if fx:
                ent["fixture"] = dict(su.get("fixture", dict(matched=False)), pad_words_zero=su.get("pad_words_zero", 0))
                if su.get('fixture_reduction_reference'):
                    ent['fixture']['post_record_output_available'] = False
                    ent['fixture']['comparison_reference'] = 'downstream input plus independent csum8; comparison only'
            if su.get("reducer_bound"):
                rb = dict(su["reducer_bound"], priced_serial_edges=serial(r["end"]) - serial(r["start"]))
                rb["bound_over_price"] = round(rb["min_serial_edges"] / max(1, rb["priced_serial_edges"]), 2)
                ent["reducer_bound"] = rb
            if su.get("lines") and su["status"] == "emitted":
                d = a.out / "images" / f"r{r['i']:03d}_su"
                d.mkdir(parents=True, exist_ok=True)
                ent.update(edges=len(su["lines"]), fill_sectors=su["fill_sectors"], drain_sectors=su["drain_sectors"])
                (d / "record.json").write_text(json.dumps(dict(preload={str(k): v for k, v in su["preload"].items()},
                                                               expect=su["expect"], data=su["data"]), indent=0))
                pending.append((r, ent, su))
        elif unit == "IDX":
            from hbm_idx_static_calendar import compile_program
            try:
                p = compile_program()
                words = p["program"] if isinstance(p, dict) and "program" in p else p
                ent.update(status="emitted_unparameterised", reasons=[
                    "IDX image = hbm_idx_static_calendar INDEX microprogram; not parameterised by the record shape "
                    f"({r['tag']})"], idx_words=len(words) if hasattr(words, "__len__") else None)
            except Exception as ex:  # noqa: BLE001
                ent.update(status="format_open", reasons=[f"compile_program: {ex!r}"])
        else:
            ent.update(status="format_open", reasons=[f"{unit} programme image format not emitted by v1"])
            if unit in SW_TARGETS:
                ent.update(cp_targets=[dict(instance=i, tgt=t_) for i, t_ in SW_TARGETS[unit]],
                           cp_transport="host_cp_ingress F20 frames -> hleaf_SW (cp_frames)")
                ent["reasons"].append(f"payload_open: {PAYLOAD_COMPILER[unit]}")
        if ent["blocked_by"]:
            ent["status"] = "blocked:" + ent["status"]
        manifest.append(ent)
    gather_records=[m for m in manifest if m.get('native_gather')]
    if getattr(a,'gather_binding',None) and gather_records:
        from hbm_layer_vehicle import su_indexed_gather_2000 as G
        binding=G.load_binding(a.gather_binding)
        if len(gather_records)==6 and all(m['status']=='native_gather_emitted' for m in gather_records):
            replay=G.programme_replay([dict(status=m['status'],native_gather=m['native_gather']) for m in gather_records],binding)
            for event in replay['events']:
                if event['k']=='D' and event['port'] not in inports:
                    raise ValueError('gather programme producer is not an actual slice boundary input '+event['port'])
            directory=a.out/'gather_programme';directory.mkdir(parents=True,exist_ok=True)
            (directory/'replay.json').write_text(json.dumps(replay,indent=1)+'\n')
            for record in gather_records:
                record['native_gather_replay']=str(directory/'replay.json')
                record['source_scope']='six-record native component; full-token composition remains open'
    # SU programmes: adjacent SU records share ONE pgp programme (one start) when they fit EDGES 7111 and the gap to
    # the next is too short to reload; each programme is loaded while the producer is idle, >= CFG_LEAD before start.
    progs = []
    cx_before, force_new = {}, False
    for r, ent, su in pending:
        if "cx_comp" in su:                         # component barrier: SU programmes split around it
            cx_before.setdefault(len(progs), []).append(su["cx_comp"])
            force_new = True
            continue
        want0 = serial(r["start"]) - su["setup_edge"]               # desired line-0 edge, relative to t0
        P = progs[-1] if progs else None
        if (P is None or force_new or want0 - P["end"] >= a.reload_gap
                or want0 - P["base"] + len(su["lines"]) > EDGES_MAX):
            P = dict(base=want0, end=want0, ql=QLine(), recs=[])
            progs.append(P)
            force_new = False
        o = max(0, want0 - P["base"])
        if a.su_lower2:
            # opt-in: records of one programme run strictly after the previous record's last commit (store rows are
            # reused from 0 by every record; RAW through VM is then satisfied by construction, and checked below)
            o = max(o, P.get("tail", 0))
        while True:                                                     # first offset without a slot collision
            clash = calendar_collision(P["ql"], su["ql"], o,
                                       exclusive_controls=bool(su.get("control_reservation") or P.get("exclusive_control")))
            if not clash:
                break
            o += 1
        for fld in Q_W:
            for e, v in su["ql"].f[fld].items():
                P["ql"].f[fld][o + e] = P["ql"].f[fld].get(o + e, 0) | v
        P["exclusive_control"] = P.get("exclusive_control", False) or bool(su.get("control_reservation"))
        P["end"] = max(P["end"], P["base"] + o + len(su["lines"]))
        P["tail"] = o + max(len(su["lines"]), 1 + (su.get("last_commit") or 0)) + 1
        P["recs"].append((r, ent, su, o))
    cfgs = []
    for k, P in enumerate(progs):
        lines = P["ql"].lines()
        man, cfg = column_image(lines, a.out / "images" / f"su_prog{k:02d}")
        P.update(lines=lines, cfg=cfg, man=man)
    t0 = 3 + (len(progs[0]["cfg"]) if progs else 0) + CFG_LEAD + START_ADVANCE + a.load_gap
    busy_until, shift, written_at = 3, 0, {}
    cx_ev, cx_comp_place, cx_epochs = [], [], []
    cx_state = dict(t=3, ep=None)

    def cx_close_epoch():
        ep = cx_state["ep"]
        if ep is None:
            return
        last = max([CX.stream_of(e["cyc"]) if e["dom"] == "serial" else e["cyc"] for e in events[ep["start"]:]
                    if e["k"] != "M"] or [ep["launch"]])
        ev_, launch_, end_ = CX.epoch_calendar(ep["t_install"], last)
        cx_ev.extend(ev_)
        cx_epochs.append(dict(t_install=ep["t_install"], launch=launch_, end=end_, last_su_stream=last,
                              programmes=ep["progs"]))
        cx_state.update(t=end_ + CX.CP_GUARD, ep=None)

    def cx_place_comps(lst):
        for comp in lst:
            nm = [e["cyc"] for e in comp["events"] if e["k"] != "M"]
            sh = cx_state["t"] + CX.CP_GUARD - min(nm)
            for e in comp["events"]:
                e2 = dict(e, cx=comp["i"])
                if e2["k"] != "M":
                    e2["cyc"] = e2["cyc"] + sh
                cx_ev.append(e2)
            cx_comp_place.append(dict(i=comp["i"], op=comp["op"], start=min(nm) + sh, end=max(nm) + sh,
                                      events=len(nm)))
            cx_state["t"] = max(nm) + sh + CX.COMP_GAP
    for k, P in enumerate(progs):
        if cx is not None and (k == 0 or k in cx_before):
            cx_close_epoch()
            cx_place_comps(cx_before.get(k, []))
            launch_ = CX.epoch_launch(cx_state["t"])
            cx_state["ep"] = dict(t_install=cx_state["t"], launch=launch_, start=len(events), progs=[])
            min_s = -(-3 * (launch_ + CX.SU_START_GUARD) // 4) + 1
            if t0 + P["base"] + shift - START_ADVANCE < min_s:
                shift += min_s - (t0 + P["base"] + shift - START_ADVANCE)
        if cx is not None:
            cx_state["ep"]["progs"].append(k)
        line0 = t0 + P["base"] + shift
        s_edge = line0 - START_ADVANCE
        load0 = s_edge - CFG_LEAD - len(P["cfg"])
        note = None
        if load0 < busy_until:
            d = busy_until - load0
            note = f"load_window_conflict: programme {k} needs {len(P['cfg'])} idle edges, shifted +{d}"
            shift += d
            load0, s_edge, line0 = load0 + d, s_edge + d, line0 + d
        for j, (b, row, data) in enumerate(P["cfg"]):
            for port, val in (("su_prog__r_we", 1), ("su_prog__r_bank", b), ("su_prog__r_row", row),
                              ("su_prog__r_data", int(data, 16))):
                events.append(dict(k="D", dom="serial", cyc=load0 + j, port=port, val=f"{val:x}", src="image:SU",
                                   prog=k))
        events.append(dict(k="D", dom="serial", cyc=load0 + len(P["cfg"]), port="su_prog__r_we", val="0",
                           src="image:SU", prog=k))
        events.append(dict(k="D", dom="serial", cyc=s_edge, port="su_prog__r_len", val=f"{len(P['lines']):x}",
                           src="image:SU", prog=k))
        events.append(dict(k="D", dom="serial", cyc=s_edge, port="su_prog__r_start", val="1", src="image:SU", prog=k))
        events.append(dict(k="D", dom="serial", cyc=s_edge + 1, port="su_prog__r_start", val="0", src="image:SU",
                           prog=k))
        busy_until = line0 + len(P["lines"])
        cfgs.append(dict(programme=k, records=[x[0]["i"] for x in P["recs"]], edges=len(P["lines"]),
                         config_writes=len(P["cfg"]), load_serial=load0, start_serial=s_edge,
                         image=str((a.out / "images" / f"su_prog{k:02d}/cols/config.mem").relative_to(a.out)),
                         image_sha256=sha((a.out / "images" / f"su_prog{k:02d}/cols/config.mem").read_bytes()),
                         columns=P["man"]["columns"], note=note))
        for r, ent, su, o in P["recs"]:
            l0 = line0 + o
            for sec, words in su["preload"].items():
                events.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=a.quarter, sector=sec,
                                   bank=sec % 8, row=(sec & 0x1fff) >> 3,
                                   val="".join(su["data"][str(w)] for w in reversed(words)), src="image:VM_preload",
                                   rec=r["i"]))
            for x in su["expect"]:
                if x.get("value") is None or any(v is None for v in x["value"]):
                    continue
                val = "".join(f"{v:08x}" for v in reversed(x["value"]))
                msk = "".join("ffffffff" if (x["mask"] >> j) & 1 else "00000000" for j in reversed(range(8)))
                events.append(dict(k="C", dom="serial", cyc=l0 + x["edge"], port=f"vm:{x['sector']:x}", val=val,
                                   mask=msk, src="golden:hdc_golden", rec=r["i"]))
            for ls_, e in su["fills"]:                  # RAW: a chained operand is filled after its producer's commit
                w = written_at.get(ls_)
                if w is not None and l0 + e < w:
                    ent.setdefault("reasons", []).append(f"raw_hazard: sector {ls_} filled at {l0 + e} < commit {w}")
            for ls_, e in su["drains"]:
                written_at[ls_] = l0 + e
            ent.update(programme=k, line0_serial=l0, compiled_commit_serial=l0 + (su["last_commit"] or 0),
                       priced_end_serial=t0 + serial(r["end"]))
            if ent.get('effective_record_price'):
                # Actual consumers (commit slack, following programme occupancy)
                # use the emitted kernel length. Keep the superseded nominal
                # estimate separately so it cannot masquerade as a valid budget.
                ent['inherited_priced_end_serial'] = ent['priced_end_serial']
                ent['inherited_commit_slack_edges'] = ent['priced_end_serial']-ent['compiled_commit_serial']
                ent['priced_end_serial'] = l0+len(su['lines'])
            ent["commit_slack_edges"] = ent["priced_end_serial"] - ent["compiled_commit_serial"]
            if note:
                ent.setdefault("reasons", []).append(note)
    if cx is not None:
        cx_close_epoch()
        cx_place_comps(cx_before.get(len(progs), []))
        cx_img = {e["sector"] for e in cx_ev if e["k"] == "M"}
        cx_dropped = [dict(rec=e.get("rec"), sector=e["sector"]) for e in events if e["k"] == "M" and e["sector"] in cx_img]
        events = [e for e in events if not (e["k"] == "M" and e["sector"] in cx_img)]   # component image wins
        for e in events:                       # SU programme of every SU event (parts)
            if "prog" not in e:
                e["prog"] = next((c["programme"] for c in cfgs if e.get("rec") in c["records"]), None)
    events.sort(key=lambda x: (x["dom"], x["cyc"], x["k"]))

    def drop_holds(evs):
        # a slice input holds its last D value (gen_slice_tb replay model); a D repeating the port's current value is
        # a no-op on the DUT inputs -- drop it so the layer fits the built testbench's event array (NEV)
        last, kept, n = {}, [], 0
        for e in evs:
            if e["k"] == "D":
                key = (e["dom"], e["port"])
                if key in last and last[key] == e["val"]:
                    n += 1
                    continue
                last[key] = e["val"]
            kept.append(e)
        return kept, n

    dropped_holds, extra_parts = 0, []
    cx_parts = None
    if cx is not None:
        # producer-cone parts: every part replays the real producer chain (drives + images) of everything it checks
        nodes = []
        prog_rw = {k_: (set(), set()) for k_ in range(len(progs))}
        for k_, P in enumerate(progs):
            for r_, ent_, su_, o_ in P["recs"]:
                prog_rw[k_][0].update(ls_ for ls_, _ in su_["fills"])
                prog_rw[k_][1].update(ls_ for ls_, _ in su_["drains"])
        by_prog, by_cx = {}, {}
        for e in events:
            by_prog.setdefault(e.get("prog"), []).append(e)
        for e in cx_ev:
            if e.get("cx_epoch"):
                by_cx.setdefault("epoch", []).append(e)
            else:
                by_cx.setdefault(e["cx"], []).append(e)
        comps_by_i = {i_: c for i_, c in cx.comps.items() if c.get("lowered")}

        def chap(i_):
            return sum(1 for b_ in cx.chapters if i_ >= b_)

        def mk(nid, evs, reads, writes):
            i_ = nid[1] if nid[0] == "c" else progs[nid[1]]["recs"][0][0]["i"]
            reads = {(chap(i_), x) for x in reads}
            writes = {(chap(i_), x) for x in writes}
            return dict(id=nid, chapter=chap(i_), drives=[e for e in evs if e["k"] == "D"], checks=[e for e in evs if e["k"] == "C"],
                        images=[e for e in evs if e["k"] == "M"], reads=reads, writes=writes)
        for k_ in range(len(progs) + 1):
            for c in cx_before.get(k_, []):
                nodes.append(mk(("c", c["i"]), by_cx.get(c["i"], []), c["reads"], c["writes"]))
            if k_ < len(progs):
                nodes.append(mk(("p", k_), by_prog.get(k_, []), *prog_rw[k_]))
        stray = by_prog.get(None, [])
        common = by_cx.get("epoch", []) + [e for e in stray if e["k"] == "D"]
        cap = (a.nev or 11651) - 1 - len(common)
        parts_, cone_ = CX.cones_parts(nodes, cap)
        byid = {n["id"]: n for n in nodes}
        parts_out = []
        for p_ in parts_:
            evs = list(common)
            for nid in sorted(p_["members"], key=lambda x: [n["id"] for n in nodes].index(x)):
                evs += byid[nid]["drives"] + byid[nid]["images"]
                if nid in p_["targets"]:
                    evs += byid[nid]["checks"]
            ev_, n_ = drop_holds(sorted(evs, key=lambda x: (x["dom"], x["cyc"], x["k"])))
            dropped_holds += n_
            parts_out.append((ev_, sorted(k_ for t_, k_ in p_["members"] if t_ == "p")))
            p_["events_after_hold_drop"] = sum(1 for e in ev_ if e["k"] != "M")
        for P_ in cx.iso_parts:                # standalone components (no in-slice neighbour)
            ev_, pl_ = CX.iso_part_events(P_)
            cx_comp_place.extend(pl_)
            parts_.append(dict(members={("c", x["i"]) for x in P_["comps"]}, targets=[("c", x["i"]) for x in P_["comps"]],
                               drive_events=sum(e["k"] == "D" for e in ev_), check_events=sum(e["k"] == "C" for e in ev_)))
            ev_, n_ = drop_holds(sorted(ev_, key=lambda x: (x["dom"], x["cyc"], x["k"])))
            parts_[-1]["events_after_hold_drop"] = sum(1 for e in ev_ if e["k"] != "M")
            parts_out.append((ev_, []))
        events = parts_out[0][0] if parts_out else events
        extra_parts = parts_out[1:]
        cx_parts = [dict(part=n_, targets=[f"{t}{k}" for t, k in p_["targets"]],
                         members=[f"{t}{k}" for t, k in sorted(p_["members"], key=lambda x: (x[1], x[0]))],
                         drive_events=p_["drive_events"], check_events=p_["check_events"],
                         events=p_["events_after_hold_drop"], fits_nev=p_["events_after_hold_drop"] <= (a.nev or 11651) - 1)
                    for n_, p_ in enumerate(parts_)]
        for P_k, P in enumerate(progs):
            for r_, ent_, su_, o_ in P["recs"]:
                ent_["replay_part"] = [n_ for n_, p_ in enumerate(parts_) if ("p", P_k) in p_["targets"]]
        for m_ in manifest:
            if m_["i"] in comps_by_i:
                m_["replay_part"] = [n_ for n_, p_ in enumerate(parts_) if ("c", m_["i"]) in p_["targets"]]
                m_["cx"]["timeline"] = next((x for x in cx_comp_place if x["i"] == m_["i"]), None)
    elif a.su_lower2:
        # opt-in: when the layer does not fit NEV, split it into INDEPENDENT replays: programmes linked by a VM
        # producer -> consumer sector stay together (no expected-value carry, no intermediate injection)
        prog_of = {r_: c["programme"] for c in cfgs for r_ in c["records"]}
        pev = {}
        for e in events:
            k_ = e.get("prog", prog_of.get(e.get("rec")))
            pev.setdefault(k_, []).append(e)
        parent = {k_: k_ for k_ in range(len(progs))}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        writer = {}
        for k_, P in enumerate(progs):
            for r_, ent_, su_, o_ in P["recs"]:
                for ls_, _ in su_["fills"]:
                    if ls_ in writer:
                        parent[find(k_)] = find(writer[ls_])
                for ls_, _ in su_["drains"]:
                    writer[ls_] = k_
        groups = {}
        for k_ in range(len(progs)):
            groups.setdefault(find(k_), []).append(k_)
        cap = a.nev - 1 if a.nev else None
        nonm = lambda evs: sum(1 for e in drop_holds(sorted(evs, key=lambda x: (x["dom"], x["cyc"], x["k"])))[0]
                               if e["k"] != "M")
        bins = []
        for g in sorted(groups.values(), key=lambda g: g[0]):
            evs = [e for k_ in g for e in pev.get(k_, [])]
            for b in bins:
                if cap is None or nonm(b["events"] + evs) <= cap:
                    b["events"] += evs
                    b["progs"] += g
                    break
            else:
                bins.append(dict(events=list(evs), progs=list(g)))
        too_big = [b for b in bins if cap is not None and nonm(b["events"]) > cap]
        if too_big:
            if a.rope_candidate and any(r.get('candidate_rope') for r in manifest):
                need = max(nonm(b['events'])+1 for b in too_big)
                raise ValueError(f'new RoPE programme requires at least NEV{need} before protocol/calendar checks; '
                                 f'compiled capacity{a.nev} is insufficient; preserve existing build and '
                                 'derive the necessary incremental top from the full emitted replay')
            # defer the latest record of the oversize VM-linked group (no later record of the group consumes it)
            # and recompile the layer; never an expected-value carry between parts
            last = max(((r_["i"], P["base"] + o_) for k_ in too_big[0]["progs"] for r_, _, _, o_ in progs[k_]["recs"]),
                       key=lambda x: x[1])[0]
            import os
            args = [x for x in sys.argv]
            if "--defer-records" in args:
                j_ = args.index("--defer-records")
                args[j_ + 1] = f"{args[j_ + 1]},{last}".strip(",")
            else:
                args += ["--defer-records", str(last)]
            print(f"SU_LOWER2 NEV: deferring record {last}", file=sys.stderr)
            os.execv(sys.executable, [sys.executable] + args)
        stray = pev.get(None, [])
        if bins:
            bins[0]["events"] += stray
        parts_out = []
        for b in bins:
            ev_, n_ = drop_holds(sorted(b["events"], key=lambda x: (x["dom"], x["cyc"], x["k"])))
            dropped_holds += n_
            parts_out.append((ev_, sorted(b["progs"])))
        events = parts_out[0][0] if parts_out else events
        extra_parts = parts_out[1:]
        part_of = {k_: n for n, (_, ps) in enumerate(parts_out) for k_ in ps}
        for P_k, P in enumerate(progs):
            for r_, ent_, su_, o_ in P["recs"]:
                ent_["replay_part"] = part_of.get(P_k, 0)
    candidate_fault_checks = None
    if a.rope_candidate and any(r.get('candidate_rope') and 'programme' in r for r in manifest):
        # SLICE_OUT reports activity spans, not values, and SLICE_PASS alone
        # does not reject a sticky protocol fault. Assert every actual boundary
        # fault face explicitly after the final commit of each independent part.
        fault_outputs = [p for p in bnd['outputs'] if 'fault' in p['name'].lower()]
        if not fault_outputs:
            raise ValueError('RoPE candidate cut has no observable protocol fault outputs')
        counts = []
        for evs in [events] + [es for es, _ in extra_parts]:
            last_serial = max((e['cyc'] if e['dom']=='serial' else (3*e['cyc']+3)//4
                               for e in evs if e['k']!='M'), default=0)
            for port in fault_outputs:
                evs.append(dict(k='C', dom='serial', cyc=last_serial+16, port=port['name'],
                                val='0', mask=f"{(1<<port['width'])-1:x}",
                                src='source:required_sticky_protocol_fault_zero'))
            evs.sort(key=lambda e:(e['dom'],e['cyc'],e['k']))
            count = sum(e['k']!='M' for e in evs)+1
            if a.nev and count>a.nev:
                raise ValueError(f'RoPE protocol checks require source-bound NEV{count}, compiled capacity{a.nev}; '
                                 'preserve old build and regenerate the necessary top')
            counts.append(count)
        candidate_fault_checks = dict(outputs=[dict(name=p['name'],width=p['width']) for p in fault_outputs],
                                      per_part_checks=len(fault_outputs), required_NEV_by_part=counts,
                                      sticky_check_guard_serial_edges=16)
    for p in {e["port"] for e in events if e["k"] == "D"}:
        assert p in inports, f"replay drives {p}, not a slice input port"
    rep = dict(schema="opentallas.hbm_slice_replay.v1", slice=bnd.get("slice_top", "sw"), design=a.design,
               scope="component_probe", qualifies_native_layer=False, qualifies_native_chain=False,
               state_seed_provenance=["released_checkpoint_fixture" if a.fixtures else "seeded_placeholder"],
               layer=a.layer, t0_serial=t0, priced_layer_cycles=pr["cycles"],
               assumptions=["serial = ceil(3*stream/4)", "SU quarter VM placement quarter-packed (compiler's own)",
                            "VM operands as M preload events (no slice VM input port)",
                            f"start advance {START_ADVANCE}, config lead {CFG_LEAD} (pgcol.sv header)"],
               events=events)
    if candidate_fault_checks is not None:
        rep['candidate_protocol_fault_checks'] = candidate_fault_checks
    if cx is not None:
        rep.update(cx_scope="connected_layer_parts", lane="TOK-FUNC2-HBM-CX", connected_components=True,
                   cx_epochs=cx_epochs, cx_components=cx_comp_place, cx_parts=cx_parts,
                   data_connection="producer -> component -> consumer through the layer VM placement; non-slice "
                                   "words imaged with provenance (manifest cx)")
        rep["assumptions"] = rep["assumptions"] + [
            "SU programmes split at every component; SU epochs (finite owner-0 calendar) and component CP epochs "
            "alternate on compiled edges (no ready/credit)",
            "part = union of producer cones of its checked nodes; cone members replay drives+images, not checks"]
    if a.su_lower2 or cx is not None:
        rep["dropped_same_value_holds"] = dropped_holds
        rep["independent_parts"] = 1 + len(extra_parts)
    (a.out / "replay.json").write_text(json.dumps(rep) + "\n")
    sm_summary = None
    if a.sm_lowering:
        from hbm_layer_vehicle import sm_slice_lower as SML
        by_tag = {}
        for r_ in recs:
            by_tag.setdefault(r_["tag"], []).append(r_["i"])
        rep_sm, per_sm, sm_summary = SML.lower(a.fixtures, a.smw / a.fixtures.name, lay, bnd, nsm=a.sm_count,
                                               priced_by_tag=by_tag)
        (a.out / "sm").mkdir(parents=True, exist_ok=True)
        (a.out / "sm" / "replay.json").write_text(json.dumps(rep_sm) + "\n")
        by_i = {m["i"]: m for m in manifest}
        for pr_ in per_sm:
            for i in pr_["priced"]:
                m = by_i.get(i)
                if m is None or m["op"] != "SM.MATVEC":
                    continue
                m.update(status="emitted", reasons=[], lowering="sm_slice_v1", replay="sm/replay.json",
                         sm_record=dict(pr_), coverage_gaps_superseded=m.get("blocked_by") or [],
                         coverage_note="10-18 coverage gaps (static x-load issuer / host loader calendar) are bound "
                                       "in the r15 die: xl_SW_ctl MODE1 table, calendar_SW target 96")
                m["blocked_by"] = []
    for n_, (ev_, ps) in enumerate(extra_parts, 1):
        (a.out / f"replay_x{n_}.json").write_text(json.dumps(dict(rep, events=ev_, independent_part=n_,
                                                                  programmes=ps)) + "\n")
    man = dict(schema="opentallas.hbm_layer_images.v1", design=a.design, layer=a.layer,
               scope=rep["scope"], qualifies_native_layer=False, qualifies_native_chain=False,
               state_seed_provenance=rep["state_seed_provenance"],
               priced=str(a.priced), programme=str(prog_src), programme_sha256=sha(Path(prog_src).read_bytes()),
               fixtures=str(a.fixtures) if a.fixtures else None,
               boundary=str(a.boundary), records=manifest, placement_conflicts=place.conflicts,
               placed_sectors=len(place.map), su_programmes=cfgs, t0_serial=t0,
               **({"sm_lowering": sm_summary} if sm_summary is not None else {}),
               **({} if cx is None else dict(cx=dict(versions=place.versions, epochs=cx_epochs,
                                                     components=cx_comp_place, parts=cx_parts,
                                                     su_images_superseded_by_component_image=cx_dropped,
                                                     chapters=cx.chapters, chapter_resets=cx.chapter_carried,
                                                     skipped_components=cx.skipped,
                                                     component_runs_top_sector=place.top))),
               counts={k: sum(1 for m in manifest if m["status"] == k) for k in sorted({m["status"] for m in manifest})})
    effective_prices = [dict(i=r['i'], tag=r['tag'], programme=r.get('programme'),
                             **r['effective_record_price'])
                        for r in manifest if r.get('effective_record_price') and 'programme' in r]
    if effective_prices:
        man['emitted_record_prices'] = dict(scope='actual bounded emitted kernels; no complete layer/token rate',
                                           records=effective_prices, inherited_prices_qualified=False,
                                           configuration_cost='su_programmes[].config_writes at one serial edge each')
    if a.pv_probability_candidate:
        from hbm_layer_vehicle import pv_probability_rows_1340 as PV
        producer = next((r for r in manifest if r['tag']=='attend.bf16_p' and 'programme' in r), None)
        partial = []
        for r in manifest:
            if r['op'] != 'ATT.PV':
                continue
            if producer is None:
                r['reasons'].append('PV input producer join OPEN: no emitted attend.bf16_p programme')
                continue
            metadata = json.loads((a.fixtures/'records.json').read_text())['records'][str(a.rank)]
            node = next(x for x in metadata if x['op']=='ATT.PV')
            record = json.loads((a.out/'images'/f"r{producer['i']:03d}_su"/'record.json').read_text())
            plan = PV.plan(logical_words=desc_addrs(node['desc']['A']), producer_entry=producer,
                producer_record=record, contract=json.loads(a.pv_probability_contract.read_text()),
                source_root=a.pv_probability_source)
            directory = a.out/'pv_probability_input'; directory.mkdir(parents=True, exist_ok=True)
            (directory/f"r{r['i']:03d}.json").write_text(json.dumps(plan,indent=1)+'\n')
            r['partial_probability_input'] = dict(status=plan['status'], pages_required=plan['pages_required'],
                rows=plan['probability_rows'], fixed_input_kernel_stream_edges=plan['fixed_input_kernel_stream_edges'],
                full_ATT_PV_lowered=False, producer_join_qualified=False, input_M_events=0,
                refusal=plan['refusal'])
            r['reasons'].append(plan['refusal'])
            partial.append(dict(i=r['i'], **r['partial_probability_input']))
        man['partial_probability_inputs'] = partial
    (a.out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(dict(records=len(manifest), events=len(events), counts=man["counts"], t0_serial=t0)))


if __name__ == "__main__":
    main()
