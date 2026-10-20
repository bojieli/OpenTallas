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

SB_W, Q_W = 2422, dict(control=1742, vmr=240, vmw=312, rf=54, red=74)
START_ADVANCE, CFG_LEAD, EDGES_MAX = 9, 2, 7111
FILL_COMMIT, LANE_FETCH, DRAIN_DONE = 13, 3, 11       # pgslice.sv:14-22
SETUP_TO_EMIT = 8                                       # su_arith_compile.py: ld at cycle 0, emits from cycle 8
# first lane output after the setup line: su_top_compile FO = 8 + 23 + 4(MLAT-3) + (ALAT-3) + LEAF + 4 PIN_REG with
# the die's su_<q><g> parameters MLAT 4, ALAT 3, LEAF 1, PIN_REG 0 (die.v su_SW0 #(...))
FIRST_OUT = 8 + 23 + 4 * (4 - 3) + 0 + 1 + 0
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
            v = s.f["control"].get(e, 0)
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


def su_record(raw, q=0, rng=None, data=None, place=None, tag="", pad_zero=False, timing=None, safe_calendar=False):
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
    row, sched = L.lower(raw)
    _, unit, sut, desc = I.decode(raw)
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
            if r in desc or (safe_calendar and r in "ABCD"):
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
            ready = setup + FIRST_OUT + (issue_at[g] - setup - SETUP_TO_EMIT) + int(safe_calendar)
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
               data={str(a): f"{int(np.float32(data[a]).view(np.uint32)):08x}" for a in logical},
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
            "rows (ot_hgi_coll_issuer_m) have no production compiler",
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
    ap.add_argument("--safe-calendar", action="store_true", help="opt-in exclusive control lifetime, legal absent readers, OLD-read drain gap")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
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
    a.out.mkdir(parents=True, exist_ok=True)
    events, manifest, t_su_free = [], [], 0
    rng = np.random.default_rng(1018)
    place, vm_data = Placement(a.quarter), {}
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
        if unit == "SU" and pk is not None and prog[pk][1] is not None:
            import su_bench as SB
            raw = SB.pack_rec(prog[pk][1])
            fr = fx.get(r["i"])
            if fr is not None:
                vm_data.update(fr["vm_in"])           # the record's operands = ds_native VM state before it
            try:
                su = su_record(raw, a.quarter, rng, data=vm_data, place=place, tag=r["tag"], pad_zero=fr is not None, timing=native_timing, safe_calendar=a.safe_calendar)
            except AssertionError as ex:                # su_program_inventory.decode: adapter contract refusal
                ent.update(status="adapter_refused", reasons=[f"su_record: {ex}"])
                manifest.append(ent)
                continue
            if fr is not None:
                fixture_check(su, fr)
            ent.update(status=su["status"], reasons=su["reasons"], lowering=su["lowering"],
                       inputs_placeholder=su.get("inputs_placeholder"))
            if fx:
                ent["fixture"] = dict(su.get("fixture", dict(matched=False)), pad_words_zero=su.get("pad_words_zero", 0))
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
    # SU programmes: adjacent SU records share ONE pgp programme (one start) when they fit EDGES 7111 and the gap to
    # the next is too short to reload; each programme is loaded while the producer is idle, >= CFG_LEAD before start.
    progs = []
    for r, ent, su in pending:
        want0 = serial(r["start"]) - su["setup_edge"]               # desired line-0 edge, relative to t0
        P = progs[-1] if progs else None
        if P is None or want0 - P["end"] >= a.reload_gap or want0 - P["base"] + len(su["lines"]) > EDGES_MAX:
            P = dict(base=want0, end=want0, ql=QLine(), recs=[])
            progs.append(P)
        o = max(0, want0 - P["base"])
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
        P["recs"].append((r, ent, su, o))
    cfgs = []
    for k, P in enumerate(progs):
        lines = P["ql"].lines()
        man, cfg = column_image(lines, a.out / "images" / f"su_prog{k:02d}")
        P.update(lines=lines, cfg=cfg, man=man)
    t0 = 3 + (len(progs[0]["cfg"]) if progs else 0) + CFG_LEAD + START_ADVANCE + a.load_gap
    busy_until, shift, written_at = 3, 0, {}
    for k, P in enumerate(progs):
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
            ent["commit_slack_edges"] = ent["priced_end_serial"] - ent["compiled_commit_serial"]
            if note:
                ent.setdefault("reasons", []).append(note)
    events.sort(key=lambda x: (x["dom"], x["cyc"], x["k"]))
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
    (a.out / "replay.json").write_text(json.dumps(rep) + "\n")
    man = dict(schema="opentallas.hbm_layer_images.v1", design=a.design, layer=a.layer,
               scope=rep["scope"], qualifies_native_layer=False, qualifies_native_chain=False,
               state_seed_provenance=rep["state_seed_provenance"],
               priced=str(a.priced), programme=str(prog_src), programme_sha256=sha(Path(prog_src).read_bytes()),
               fixtures=str(a.fixtures) if a.fixtures else None,
               boundary=str(a.boundary), records=manifest, placement_conflicts=place.conflicts,
               placed_sectors=len(place.map), su_programmes=cfgs, t0_serial=t0,
               counts={k: sum(1 for m in manifest if m["status"] == k) for k in sorted({m["status"] for m in manifest})})
    (a.out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(dict(records=len(manifest), events=len(events), counts=man["counts"], t0_serial=t0)))


if __name__ == "__main__":
    main()
