#!/usr/bin/env python3
"""HBM-SMBUDGET (10-19, coordinator decision 0jx): token-resident SM service programme for the d4g SM -- compiler +
end-to-end bench of options C + C2 + P2 + the 2,048-word programme store.

As built (VEH-FMT-SM2 finding, slice_sw/sm_mv/issuer_budget_1019.txt) a token needs ~1,700 issuer descriptors and
~5.3k programme words per SM: the 128-row table is rewritten per layer through the host ingress (~51k edges a layer vs
~14.6k cycles, run-locked) and the 1,024-word programme store overflows 2.2-2.7x -> the static schedule would stall.
This tool compiles the RELATIVE form instead and proves it on RTL:
  * P2 shape-generic programmes: every svg block (<= 64 lines = one group-slot wave of IL 8 items x 8 t steps) is a
    programme whose words carry row / slot / tag RELATIVE to the block (row r - r0, line tag l) and no epoch / cache bank;
    ot_hbm_svc_sm_feed_programmed_rel_id relocates them per launch from the issuer's go context {row_off r0, tag_base,
    epoch, bank}.  Word-identical programmes are stored once (dedup across ops, records and layers of a kind).
    An op's first block carries fl (format launch on the edge before its first line, from the descriptor).
  * C layer-stride descriptors: DRAM row = row_base + run_layer x layer_stride (layer-major placement per kind).
  * C2 indexed routed experts: + ids[slot] x expert_stride, ids = the router's top-k broadcast (record input I).
  * one install of programme + descriptor rows through the real host collars (ot_static_run_target cp_svg, xc collar),
    then per layer ONE run descriptor per target (loops = layer + 1) + one global launch.
Bench (tb_hbm_svg_rel_sm.sv): the real collar -> relative svg group (issuer, 2,048-word feed, four-PC producer, landing +
cache SRAMs) -> 4 real controller leaves -> DRAM command fixture, the lockstep xc extension calendar, and the d4g die SM
master ot_hbm_accel_smh_attn.  Several DS layers (L00 / L02 / L14 / head) run back to back from ONE resident table and
store; every go is a FIXED compiler slot (FIXED_GO: a go whose block is not resident + copied is a sticky fault, i.e. the
static schedule never stalls -- it would fault); every result row is checked bit for bit (FP32 accumulator + O format vs
the fixture O, as sm_mv_unit.py).

  smb_unit.py compile --fix FIXROOT --smw SMWROOT --out DIR [--layers L00:0,L02:2,L14:14,head:0] [--mut M]
  smb_unit.py run --fix ... --smw ... --bundle B --work W --out J [--mut M] [--define IMUT=1]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402
import sm_mv_unit as MV  # noqa: E402

F = np.float32
IL, C8, FMT_LEAD = 8, 8, MV.FMT_LEAD
PAW, PSTORE, ATT_RESERVED = 11, 2048, 1019        # 2,048-word store; HBM-ATTGAP resident QK+PV (KV8) = 1,019 words
TBL = 256                                         # issuer descriptor table rows (DD 256)
NID, IDW, NEXP = 6, 9, 384                        # router broadcast: top-6 slots of 9-bit ids (DS V4.1: 384 routed experts)
BSCALE = int(os.environ.get('SMB_BSCALE', 8))       # 8 = one block per DRAM row index (slot 0, the as-built layout)
BLK_MAX = 1 << 18                                 # 18-bit block address = DRAM row index [17:3] + sub-row slot [2:0]
SVG_TGT, XC_TGT = 64, 192
LANDING = 4
MAGIC_ROW, MAGIC_DESC = 0xC7A1, 0x5D15
# schedule constants (stream edges); LAT_GO = go edge -> first relocated word at the SM (start_v_q, running, macro,
# capture, calendar, RELOC); OFF = launch event edge -> issuer rc 0
LAT_GO, OFF = 7, 3
X_GAP, OP_GAP, DRAIN = 16, 256, 1200
FIRST_GO = int(os.environ.get('SMB_FIRST_GO', 520))             # first block of a run: HBM first access + copy (elastic boundary, calibrated by the bench)
PACE_NUM, PACE_DEN, PACE_ADD = (int(os.environ.get(k, d)) for k, d in (('SMB_PACE_NUM', 200), ('SMB_PACE_DEN', 64), ('SMB_PACE_ADD', 4)))
# >= 1.375 edges / 136-B line (immutable HBM price) + 8; env overrides for calibration probes
FETCH = int(os.environ.get('SMB_FETCH', 200))       # measured HBM boundary: one 64-line block per ~160-170 edges (distinct rows) + refresh slack
EXP_FIRST = int(os.environ.get('SMB_EXP_FIRST', 260))  # ids -> first routed block resident + copied
IDS_LAG = int(os.environ.get('SMB_IDS_LAG', 200))     # router gate last command -> top-k ids broadcast
BUSY = 6                  # calendar done -> issuer go_busy clear -> next go


def put(v, lo, w, x, name):
    x = int(x)
    if not 0 <= x < 1 << w:
        raise ValueError(f"{name}={x} does not fit {w} b")
    return v | (x << lo)


# ------------------------------------------------------------------------------------------------ row ABI
def svg_word(cmd83=0, read=None, retire=None):
    """W135 envelope (feed_programmed): [82:0] cmd, [83] read_v [84] bank [100:85] epoch [106:101] row [116:107] tag,
    [117] retire_v [118] bank [134:119] epoch.  Relative form: bank / epoch 0 (taken from the go context), tag = line."""
    v = put(0, 0, 83, cmd83, "cmd83")
    if read is not None:
        row, tag = read
        v |= 1 << 83
        v = put(v, 101, 6, row, "read_row")
        v = put(v, 107, 10, tag, "read_tag")
    if retire:
        v |= 1 << 117
    return v


def prog_row(addr, payload, w):
    """ot_smh_calendar_static_x word: magic [255:240], identity [234:224] (AW 11), payload [w-1:0]."""
    assert w <= 223
    return put(put(0, 0, w, payload, "payload"), 224, PAW, addr, "addr") | (MAGIC_ROW << 240)


def desc_row(i, *, row_base, landing, epoch, rows, tag_base, prog_base, prog_limit, go_at, layer_stride=0,
             expert_stride=0, id_sel=0, row_off=0, loops=1, lstep=0, mode=0, mrel=0, fl=0):
    """ot_hbm_svc_sm_issuer_rel descriptor (layout in the RTL header; identity [239:232])."""
    if not 1 <= rows <= 64:
        raise ValueError(f"rows={rows}")
    v = put(0, 7, 3, row_base & 7, "slot")           # stack 0; base[9:7] = sub-row block slot, other base bits 0
    v = put(v, 32, 15, row_base >> 3, "row_base")
    v = put(v, 47, 2, landing, "landing")
    v = put(v, 49, 16, epoch, "epoch")
    v = put(v, 65, 7, rows, "rows")
    v = put(v, 72, 10, tag_base, "tag_base")
    v = put(v, 82, 10, prog_base & 1023, "prog_base")
    v = put(v, 92, 11, prog_limit & 2047, "prog_limit")
    v = put(v, 103, 16, loops, "loops")
    v = put(v, 119, 24, go_at, "go_at")
    v = put(v, 143, 15, layer_stride, "layer_stride")
    v = put(v, 158, 15, expert_stride, "expert_stride")
    v = put(v, 173, 4, id_sel, "id_sel")
    v = put(v, 177, 12, row_off, "row_off")
    v = put(v, 189, 1, prog_base >> 10, "prog_base10")
    v = put(v, 190, 1, prog_limit >> 11, "prog_limit11")
    v = put(v, 191, 4, lstep, "lstep")
    v = put(v, 195, 3, mode, "mode")
    v = put(v, 198, 1, mrel, "mrel")
    v = put(v, 199, 1, fl, "fl")
    v = put(v, 232, 8, i, "identity")
    return v | (MAGIC_DESC << 240)


def ingress(cfg=None, desc=None, launch=False, target=0):
    """F20 bus word {cfg_v, desc_v, launch_v, target8, addr12, data256, base12, limit13, loops16} (320 b)."""
    v = 0
    if cfg is not None:
        addr, data = cfg
        v |= 1 << 319
        v = put(v, 41, 256, data, "data")
        v = put(v, 297, 12, addr, "addr")
    if desc is not None:
        base, limit, loops = desc
        v |= 1 << 318
        v = put(v, 0, 16, loops, "loops")
        v = put(v, 16, 13, limit, "limit")
        v = put(v, 29, 12, base, "base")
    if launch:
        v |= 1 << 317
    return put(v, 309, 8, target, "target")


def cmd_ext_of(c):
    """the xc half of a 192-bit SM command word (bits [191:83] -> cmd_ext[108:0])."""
    return MV.cmd_word(**c) >> 83 if c else 0


# ------------------------------------------------------------------------------------------------ records
def layer_records(fix: Path, smw: Path):
    wj = json.loads((smw / "weights.json").read_text())
    ks = [e["k"] for e in wj["records"] if e["rank"] == 0]
    z = np.load(fix / "operands.npz")
    out = []
    for k in ks:
        rec, ent, fmt, w, x, o = MV.load_record(fix, smw, k)
        acc, ofmt, gok = MV.check_golden(rec, fmt, w, x, o)
        slot = None
        tag = rec["tag"]
        if tag.startswith("expert slot "):
            s = int(tag.split()[2])
            if s < NID:                                    # routed slot (slot NID = the shared expert: fixed)
                slot = s
        eid = int(z[f"r0.k{rec['k']}.I"][0]) if slot is not None else None
        m = len(o)
        R = -(-(-(-m // 2)) // 16)
        out.append(dict(k=k, rec=rec, fmt=fmt, w=w, x=x, o=o, acc=acc, ofmt=ofmt, gok=gok, slot=slot, eid=eid, m=m, R=R))
    return out


# ------------------------------------------------------------------------------------------------ programmes
class Store:
    """programme store shared by svg (W135) and xc (W173): word-identical programmes stored once."""

    def __init__(self, base):
        self.base, self.top, self.progs, self.svg, self.xc = base, base, {}, {}, {}

    def add(self, svg_words, xc_words):
        key = (tuple(svg_words), tuple(xc_words))
        if key not in self.progs:
            b = self.top
            for i, (s, x) in enumerate(zip(svg_words, xc_words)):
                self.svg[b + i], self.xc[b + i] = s, x
            self.top += len(svg_words)
            if self.top > PSTORE:
                raise SystemExit(f"programme store overflow: {self.top} > {PSTORE}")
            self.progs[key] = (b, self.top)
        return self.progs[key]


def block_programme(Gn, items, r0):
    """one group-slot wave (<= 8 (row, group) items) -> the LOOPED relative body: 8 line-aligned words (issue slot s = word
    s; a slot without an item is an idle word), run with loops = 8 (t = iteration) and lstep = len(items).  Word s holds
    the cache read of line s (relocated to line t*n + s) and the command of the same line (row / slot relative to r0,
    xaddr g*8 (+ t), first / last from the iteration, packet tag s (+ tag_base + t*n)); the retire rides the last word of
    the final iteration.  xc words: magic + mode 0 (the descriptor's mode is substituted, mrel)."""
    svg, xc = [], []
    for s_ in range(IL):
        if s_ < len(items):
            r, g = items[s_]
            rr = r - r0
            c = MV.cmd_word(valid=1, row=rr, glast=int(g == Gn - 1), slot=rr & 7, xaddr=g * C8, pkt=1, pkt_tag=s_)
            svg.append(svg_word(c & ((1 << 83) - 1), (s_, s_), retire=(s_ == IL - 1)))
            xc.append(c >> 83)
        else:
            svg.append(svg_word(0, None, retire=(s_ == IL - 1)))
            xc.append(0)
    cyc = [(t * IL + s_, s_, t) for t in range(C8) for s_ in range(len(items))]
    return svg, xc, len(cyc), cyc


def waves(R, Gn):
    items = [(r, g) for r in range(R) for g in range(Gn)]
    return [items[i:i + IL] for i in range(0, len(items), IL)]


# ------------------------------------------------------------------------------------------------ compile
def compile_all(fix_root: Path, smw_root: Path, layers, mut=""):
    sys.path.insert(0, str(ROOT / "tools"))
    from hbm_svc_packed136_image import sector_address  # noqa: E402
    store = Store(ATT_RESERVED)                        # rows [0, 1019) reserved for the HBM-ATTGAP attention programmes
    descs, mem, xw_ev, ids_ev, ing = [], {}, [], [], []
    kinds, report = [], []
    row_top = 0
    # ---- per kind: blocks, programmes, descriptors (resident), HBM image for the bench's layer index
    for name, L in layers:
        recs = layer_records(fix_root / name, smw_root / name)
        bad = [r["k"] for r in recs if not r["gok"]]
        if bad:
            raise SystemExit(f"{name}: golden self-test mismatch {bad}")
        kd = dict(name=name, layer=L, d0=len(descs), ops=[], nonexp_blocks=0, exp_blocks=0)
        nonexp = []
        exp_blocks = {}                                # slot -> list of blocks (per routed expert: w1+w3 then w2)
        for r in recs:
            line, Gn, xw = MV.pack(r["fmt"], r["w"], r["x"])
            r.update(Gn=Gn, line=line, xw=xw)
            for wi, it in enumerate(waves(r["R"], Gn)):
                r0 = it[0][0]
                svg, xc, nl, cyc = block_programme(Gn, it, r0)
                pb, pl = store.add(svg, xc)
                lines = [line(it[s][0], it[s][1], t) for (_, s, t) in cyc]
                blk = dict(k=r["k"], wave=wi, r0=r0, items=it, n_lines=nl, prog=(pb, pl), nwords=len(svg) * C8,
                           lines=lines, head=wi == 0, lstep=len(it), fmt=r["fmt"])
                r.setdefault("blocks", []).append(blk)
                if r["slot"] is None:
                    nonexp.append(blk)
                else:
                    exp_blocks.setdefault(r["slot"], []).append(blk)
        kd["nonexp_blocks"] = len(nonexp)
        # 18-bit block addresses: nonexpert = kbase + L*lstride + j; routed = ebase + L*elstride + id*estride + b
        lstride = len(nonexp) * BSCALE
        kbase = row_top
        row_top += lstride * (max(L, 0) + 1)
        estride = max((len(v) for v in exp_blocks.values()), default=0) * BSCALE
        if exp_blocks:
            assert len({len(v) for v in exp_blocks.values()}) == 1, "routed experts of one kind must share a shape"
        kd.update(lstride=lstride, kbase=kbase, estride=estride)
        for j, b in enumerate(nonexp):
            b.update(row_base=kbase + j * BSCALE, layer_stride=lstride, id_sel=0, expert_stride=0,
                     dram_row=kbase + L * lstride + j * BSCALE)
        kd["exp"] = {}
        if exp_blocks:
            elstride = NEXP * estride
            eb = row_top
            row_top += elstride * (L + 1)
            for s, bl in exp_blocks.items():
                eid = next(r["eid"] for r in recs if r["slot"] == s)
                kd["exp"][s] = eid
                for b_i, b in enumerate(bl):
                    b.update(row_base=eb + b_i * BSCALE, layer_stride=elstride, id_sel=s + 1, expert_stride=estride,
                             dram_row=eb + L * elstride + eid * estride + b_i * BSCALE)
            kd.update(ebase=eb, elstride=elstride)
        if row_top >= BLK_MAX:
            raise SystemExit(f"block addresses exhausted ({row_top})")
        kd["recs"] = recs
        kinds.append(kd)
    # ---- issue order of a layer = record order (weights.json k order), blocks in wave order; one descriptor a block
    for kd in kinds:
        kd["d0"] = len(descs)
        for r in kd["recs"]:
            for b in r["blocks"]:
                b["desc_i"] = len(descs)
                descs.append(b)
        kd["d1"] = len(descs)
    if len(descs) > TBL:
        raise SystemExit(f"descriptor table overflow: {len(descs)} > {TBL}")
    # ---- HBM image (sector30 data) of every block at its layer's DRAM row
    for b in descs:
        raw = b"".join(int(x).to_bytes(136, "little") for x in b["lines"])
        total = ((len(b["lines"]) * 136 + 127) // 128) * 4
        raw += bytes(32 * total - len(raw))
        alloc = dict(pcs=[0, 1, 2, 3], row_base=b["dram_row"] >> 3, stack_bytes=1 << 35)
        for o in range(total):
            sa = sector_address(o + 512 * (b["dram_row"] & 7), alloc)   # slot k = per-PC words 128k..
            assert sa not in mem, ("HBM image alias", hex(sa))
            mem[sa] = int.from_bytes(raw[32 * o:32 * o + 32], "little")
    # ---- schedule: install, then per layer launch + fixed go slots; x writes before every op
    t = 10
    for a in range(ATT_RESERVED, store.top):
        for tgt, w, wd in ((SVG_TGT, store.svg[a], 135), (XC_TGT, store.xc[a], 173)):
            ing.append((t, ingress(cfg=((0 if a < 1024 else 2) << 10 | (a & 1023), prog_row(a, w, wd)), target=tgt)))
            t += 1
    # descriptor rows: go_at filled after scheduling -> collect row data later; reserve the install edges now
    desc_install_t = t
    t += 2 * len(descs)
    ops_out = []
    last_cmd_abs = t
    epoch = 1
    for kd in kinds:
        recs = kd["recs"]
        # launch: arm both targets, then the global launch
        t_arm = max(t, last_cmd_abs + 8)
        t_launch = t_arm + 2
        rc0 = t_launch + OFF                           # absolute edge of issuer rc 0 (calibrated by the bench trace)
        kd.update(t_launch=t_launch, rc0=rc0)
        rc = FIRST_GO
        prev_go, prev_len, prev_lines = None, 0, 0
        cur_abs = last_cmd_abs
        ids_rc, n_after = None, 0
        for r in recs:
            nx = len(r["xw"]) * MV.NBEAT
            x0 = max(cur_abs + 32, desc_install_t + 2 * len(descs) + 4)
            x_end = x0 + nx
            for a, word in enumerate(r["xw"]):
                for g in range(MV.NBEAT):
                    xw_ev.append((x0 + a * MV.NBEAT + g, (1 << 2062) | (a << 2055) | (g << 2048) |
                                  ((word >> (2048 * g)) & ((1 << 2048) - 1))))
            op = dict(layer=kd["name"], k=r["k"], tag=r["rec"]["tag"], fmt=MV.FMT_NAME[r["fmt"]], O_fmt=r["ofmt"], m=r["m"],
                      R=r["R"], Gn=r["Gn"], slot=r["slot"], eid=r["eid"], blocks=len(r["blocks"]),
                      lines=sum(b["n_lines"] for b in r["blocks"]),
                      priced=(r["rec"].get("priced") or [{}])[0].get("base_cost"))
            for bi, b in enumerate(r["blocks"]):
                P = 0
                lo = rc
                if prev_go is not None:
                    lo = max(lo, prev_go + prev_len + BUSY, prev_go + (PACE_NUM * prev_lines + PACE_DEN - 1) // PACE_DEN + PACE_ADD)
                if bi == 0:
                    lo = max(lo, x_end + X_GAP - rc0 - LAT_GO - P, cur_abs + OP_GAP - rc0 - LAT_GO - P)
                # C2: the reserve pipeline is in order; from the first routed descriptor on, every block is fetched only
                # after the router broadcast: resident >= ids + EXP_FIRST + n x FETCH (HBM boundary, measured)
                if kd["exp"] and (r["slot"] is not None or n_after):
                    if ids_rc is None:
                        ids_rc = lo - EXP_FIRST - 1                    # no router record in this kind: ids just in time
                    lo = max(lo, ids_rc + EXP_FIRST + n_after * FETCH)
                    n_after += 1
                b["go_at"] = lo
                b["first_cmd_abs"] = rc0 + lo + LAT_GO + P
                b["landing"] = b["desc_i"] % LANDING
                b["epoch"] = epoch
                epoch += 1
                b["tag_base"] = (b["desc_i"] % 16) * 64
                prev_go, prev_len, prev_lines = lo, b["nwords"], b["n_lines"]
                rc = lo
                cur_abs = rc0 + lo + LAT_GO + b["nwords"] - 1
            op["first_cmd_abs"] = r["blocks"][0]["first_cmd_abs"]
            op["last_cmd_abs"] = cur_abs
            if r["rec"]["tag"].startswith("router") and kd["exp"]:
                ids_rc = cur_abs - rc0 + IDS_LAG                # router result -> top-k -> broadcast (modelled lag)
            ops_out.append(op)
        kd["rc_end"] = prev_go + prev_len + BUSY
        last_cmd_abs = cur_abs
        t = rc0 + kd["rc_end"] + 4
        # router ids (C2): the broadcast arrives a fixed time before the first routed block's go (compiler slot)
        if kd["exp"]:
            first_exp = min(b["go_at"] for r in recs if r["slot"] is not None for b in r["blocks"])
            ids_at = rc0 + (ids_rc if mut != "late_ids" else first_exp + 40)
            ids = 0
            for s, e in kd["exp"].items():
                ids |= e << (IDW * s)
            ids_ev.append((ids_at, (kd["layer"] << (IDW * NID)) | ids))
            kd["ids_at_rc"] = ids_at - rc0
        ing.append((t_arm, ingress(desc=(kd["d0"], kd["d1"], kd["layer"] + 1), target=SVG_TGT)))
        ing.append((t_arm + 1, ingress(desc=(kd["d0"], kd["d1"], kd["layer"] + 1), target=XC_TGT)))
        ing.append((t_launch, ingress(launch=True, target=0)))
    # descriptor rows now that go slots exist (the table is written ONCE, before the first launch)
    for i, b in enumerate(descs):
        d = desc_row(i, row_base=b["row_base"], landing=b["landing"], epoch=b["epoch"], rows=b["n_lines"],
                     tag_base=b["tag_base"], prog_base=b["prog"][0], prog_limit=b["prog"][1], go_at=b["go_at"],
                     layer_stride=b["layer_stride"], expert_stride=b["expert_stride"], id_sel=b["id_sel"], row_off=b["r0"],
                     loops=C8, lstep=b["lstep"], mode=b["fmt"], mrel=1, fl=int(b["head"]))
        for j, tgt in enumerate((SVG_TGT, XC_TGT)):
            ing.append((desc_install_t + 2 * i + j, ingress(cfg=(1 << 10 | i, d), target=tgt)))
    ing.sort(key=lambda e: e[0])
    xw_ev.sort(key=lambda e: e[0])
    assert len({e[0] for e in ing}) == len(ing), "two ingress words on one edge"
    assert len({e[0] for e in xw_ev}) == len(xw_ev), "two x beats on one edge"
    n_end = last_cmd_abs + DRAIN
    budget = dict(descriptors=len(descs), table_rows=TBL, programme_words_matvec=store.top - ATT_RESERVED,
                  attention_reserved=ATT_RESERVED, store_top=store.top, store_words=PSTORE,
                  distinct_programmes=len(store.progs),
                  per_kind=[dict(name=k["name"], layer=k["layer"], descriptors=k["d1"] - k["d0"], nonexpert_blocks=k["nonexp_blocks"],
                                 routed_expert_descriptors=sum(len(r["blocks"]) for r in k["recs"] if r["slot"] is not None),
                                 lstride=k["lstride"], kbase=k["kbase"], estride=k["estride"], expert_ids=k["exp"],
                                 ids_at_rc=k.get("ids_at_rc"), rc_end=k["rc_end"]) for k in kinds],
                  install_ingress_edges=2 * (store.top - ATT_RESERVED) + 2 * len(descs),
                  per_layer_ingress_edges_this_sm=3, blocks_addressed=row_top)
    return dict(ing=ing, xw=xw_ev, ids=ids_ev, mem=mem, ops=ops_out, kinds=kinds, n_end=n_end, budget=budget, descs=descs)


def write_events(c, d: Path):
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "ing.hex", "w") as f:
        for t, v in c["ing"]:
            f.write(f"{(t << 320) | v:088x}\n")
    with open(d / "xw.hex", "w") as f:
        for t, v in c["xw"]:
            f.write(f"{(t << 2064) | v:0524x}\n")
    with open(d / "ids.hex", "w") as f:
        for t, v in c["ids"]:
            f.write(f"{(t << 62) | v:024x}\n")
        if not c["ids"]:
            f.write("0" * 24 + "\n")
    with open(d / "mem.hex", "w") as f:
        for a in sorted(c["mem"]):
            f.write(f"{a:08x} {c['mem'][a]:064x}\n")
    return dict(NI=len(c["ing"]), NX=len(c["xw"]), ND=len(c["ids"]), END=c["n_end"])


# ------------------------------------------------------------------------------------------------ build / run / check
TB = "rtl/test/hbm_accel/svg_rel/tb_hbm_svg_rel_sm.sv"
SVG_SRC = ["rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv",
           "rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv",
           "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_issuer_rel.sv",
           "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_feed_programmed_rel_id.sv",
           "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_group_rel_id.sv",
           "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel.sv",
           "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel_t.sv",
           "rtl/test/hbm_accel/svg_rel/tb_svg_rel_dram_sparse.sv"]


def build(work: Path, bundle: Path, defines):
    tag = "_".join(d.replace("=", "") for d in defines) or "base"
    rev = (ROOT / "REV").read_text().strip()[:9] if (ROOT / "REV").exists() else "wt"
    obj = work / f"obj_{tag}_{rev}"
    exe = obj / "Vtb_hbm_svg_rel_sm"
    if exe.exists():
        return exe
    mf = json.loads((bundle / "master_files.json").read_text())
    sm = [bundle / p for p in mf["ot_hbm_accel_smh_attn"]]
    svc = [ROOT / p for p in (HERE / "smb_svc_files.txt").read_text().split()]
    own = [ROOT / p for p in SVG_SRC]
    if "SMB_SRAMFIFO" in defines:
        own += [ROOT / p for p in (
            "rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo_sram285.sv",
            "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm8_landing_bank_sram285.sv",
            "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm4pc_cdc_rel_sram_id.sv",
            "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_feed_programmed_rel_sram_id.sv",
            "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_group_rel_sram_id.sv",
            "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_8x285_m1/ot_sram_1r1w2c_8x285_m1.v")]
    names = {Path(p).name for p in sm}
    files = sm + [p for p in svc + own if p.name not in names] + [ROOT / TB]
    vl = os.environ.get("VERILATOR") or os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    incs = sorted({str(p.parent) for p in files})
    cmd = [vl, "--binary", "-j", os.environ.get("VL_JOBS", "16"), "-O1", "-CFLAGS", "-O1", "--x-assign", "fast",
           "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "256",
           "--timing", "--top-module", "tb_hbm_svg_rel_sm", "--Mdir", str(obj)] + \
          [f"-D{d}" for d in MV.DIE_DEFINES + list(defines)] + [f"-I{i}" for i in incs] + [str(f) for f in files]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / f"build_{tag}.log").write_text(" ".join(cmd) + "\n" + r.stdout[-20000:] + r.stderr[-20000:] +
                                           f"\nBUILD_RC {r.returncode} wall {time.time() - t0:.0f} s\n")
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_{tag}.log)")
    return exe


def parse(log):
    res, gos, runs, fault, done = [], [], [], None, None
    for ln in log.splitlines():
        p = ln.split()
        if ln.startswith("R ") and len(p) == 4:
            res.append((int(p[1]), int(p[2], 16), int(p[3], 16)))
        elif ln.startswith("G ") and len(p) == 4:
            gos.append((int(p[1]), int(p[2]), int(p[3])))
        elif ln.startswith("D ") and len(p) == 2:
            runs.append(int(p[1]))
        elif ln.startswith("FAULT"):
            fault = fault or ln.strip()
        elif ln.startswith("DONE"):
            done = ln.strip()
    return res, gos, runs, fault, done


def check(c, res):
    """every op: rows 0..R-1 exactly once in [first command, next op's first command), FP32 accumulator + O vs the
    fixture (sm_mv_unit.check_run semantics)."""
    out, ok_all = [], True
    recs = {(k["name"], r["k"]): r for k in c["kinds"] for r in k["recs"]}
    ops = c["ops"]
    for i, op in enumerate(ops):
        r = recs[(op["layer"], op["k"])]
        lo, hi = op["first_cmd_abs"], ops[i + 1]["first_cmd_abs"] if i + 1 < len(ops) else 1 << 40
        e = dict(name="sm0", rows=list(range(r["R"])), first_line=lo, window_end=hi)
        ro, ok = MV.check_run([e], [x for x in res if lo <= x[0] < hi], r["acc"], r["o"], r["ofmt"])
        ro = ro[0]
        out.append(dict(op, verdict=ro["verdict"], results=ro["results"], n_bad=ro["n_bad"], bad=ro["bad"][:4],
                        n_missing=ro["n_missing"], span_first_cmd_to_last_result=ro["cycles_first_line_to_last_result"]))
        ok_all &= ok
    return out, ok_all


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_layers(s):
    return [(a.split(":")[0], int(a.split(":")[1])) for a in s.split(",")]


def cmd_compile(a):
    c = compile_all(Path(a.fix), Path(a.smw), parse_layers(a.layers), a.mut)
    d = Path(a.out)
    n = write_events(c, d)
    doc = dict(budget=c["budget"], events=n, ops=c["ops"])
    (d / "compile.json").write_text(json.dumps(doc, indent=1, default=str) + "\n")
    print(json.dumps(dict(budget=c["budget"], events=n), indent=1, default=str))
    return c, n


def cmd_run(a):
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    defines = [x for x in a.define.split(",") if x]
    exe = build(work, Path(a.bundle).resolve(), defines)
    a.out_dir = work / f"run_{a.name}"
    c = compile_all(Path(a.fix), Path(a.smw), parse_layers(a.layers), a.mut)
    d = a.out_dir
    n = write_events(c, d)
    t0 = time.time()
    r = subprocess.run([str(exe), f"+ING={d}/ing.hex", f"+XW={d}/xw.hex", f"+IDS={d}/ids.hex", f"+MEM={d}/mem.hex",
                        f"+NI={n['NI']}", f"+NX={n['NX']}", f"+ND={n['ND']}", f"+END={n['END']}"],
                       capture_output=True, text=True, cwd=d)
    log = r.stdout + r.stderr
    (d / "run.log").write_text(log)
    res, gos, runs, fault, done = parse(log)
    ops, ok = check(c, res)
    # go slots: the trace's (cycle, base, rc) against the compiled go_at of every descriptor, in issue order
    go_at = [b["go_at"] for k in c["kinds"] for b in c["descs"][k["d0"]:k["d1"]]]
    go_ok = len(gos) == len(go_at) and all(g[2] == ga for g, ga in zip(gos, go_at))
    ok = ok and go_ok and fault is None and done is not None and r.returncode == 0 and len(runs) == len(c["kinds"])
    doc = dict(schema="opentallas.hbm_smbudget_unit.v1", name=a.name, mut=a.mut or None, defines=defines,
               rtl="cp_svg ot_static_run_target -> ot_hbm_svc_sm_group_rel_id (issuer_rel + feed_programmed_rel_id, "
                   "2,048-word store) -> 4 controller leaves -> DRAM fixture; xc ot_hbm_svc_sm_xcal_rel_t; SM = "
                   "ot_hbm_accel_smh_attn die master (bundle master_files, DIE_DEFINES); tb_hbm_svg_rel_sm.sv, Verilator 5.050",
               budget=c["budget"], events=n, fault=fault, done=done, runs_done=runs, gos=len(gos), go_slots_exact=go_ok,
               sim_s=round(time.time() - t0, 1), run_rc=r.returncode, run_log_sha256=sha(d / "run.log"), ops=ops,
               verdict="PASS" if ok else "FAIL")
    Path(a.out).write_text(json.dumps(doc, indent=1, default=str) + "\n")
    print(f"SMB_UNIT {doc['verdict']} ops={len(ops)} pass={sum(o['verdict'] == 'PASS' for o in ops)} gos={len(gos)}/"
          f"{len(go_at)} go_slots_exact={go_ok} runs={len(runs)} fault={fault} {done}")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("compile", "run"):
        p = sp.add_parser(nm)
        p.add_argument("--fix", required=True)
        p.add_argument("--smw", required=True)
        p.add_argument("--layers", default="L00:0,L02:2,L14:14,head:0")
        p.add_argument("--mut", default="", choices=["", "late_ids"])
        if nm == "compile":
            p.add_argument("--out", required=True)
        else:
            p.add_argument("--bundle", required=True)
            p.add_argument("--work", required=True)
            p.add_argument("--out", required=True)
            p.add_argument("--name", default="pos")
            p.add_argument("--define", default="")
    a = ap.parse_args(argv)
    if a.cmd == "compile":
        cmd_compile(a)
        return 0
    return cmd_run(a)


if __name__ == "__main__":
    raise SystemExit(main())
