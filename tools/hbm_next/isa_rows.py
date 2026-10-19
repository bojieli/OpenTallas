#!/usr/bin/env python3
"""HGI-1R: the N-row record amendment of HGI-1 for the next HBM die (P = 4 position lanes).  SINGLE SOURCE.

Spec text: results/arch/hbm_next_1019/cmtp/isa_rows.md (its field tables are rendered from this file and checked
by `--selftest`).  Implemented by lanes HBM-NEXT-UNITS / SM4 / ATT4 (decode), consumed by CMTP (compiler) and VEH.

What it adds to HGI-1 (docs/HBM_GENERIC_INTERFACE.md section 6; tools/hbm_generic_iface.py tables, unchanged):
  * UOP op[5] (header bit 123) = `rows`: a 256-bit ROWX part follows the header (after the SUT when tmpl = 1, before
    the MDESCs).  No HGI-1 op code uses op[5] (largest list: 8 ops), so an HGI-1 decoder FAULTS on an N-row record
    (illegal op, completion status 3) instead of silently running row 0: fail-closed by construction.
  * ROWX: row count N (1..16), 4-bit first slot (DYN bank), per-operand row strides, a row gap for the static
    schedule, the SM remainder-pass layout (K-split / row-split), and row selection from a VM row table (the expert-union grouped GEMM).
  * New operations: IDX.UNION (op 5: verify expert union + per-expert row tables), CTL.USERS (op 8: per-slot DYN banks
    for independent users).  CTL.TOKX and CTL.ACCEPT (reserved in HGI-1) are defined.  SM.MATVEC param [5:2].

NORMATIVE SEMANTICS (bit-exact): an N-row record is EXACTLY the in-order sequence of its N single-row expansions
(`expand`).  Hardware may overlap rows, share weight / key / KV streams across rows and split reductions (K-split)
only where the result is bit-identical to that sequence; the only timing contract is the static one (c1 + (N - 1) x
(II + rgap), see ROW_II).  Rows of one record must be independent (no row reads what an earlier row of the same
record writes); `check_rows_independent` enforces it at compile time and the static checker re-checks it.

    python3 tools/hbm_next/isa_rows.py --selftest          (pure Python + numpy; seconds)
    python3 tools/hbm_next/isa_rows.py --md-tables          (prints the tables isa_rows.md embeds)
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import hbm_generic_iface as HGI  # noqa: E402
from hgi_sim import records as RC  # noqa: E402

VERSION = "HGI-1R 1.1 (draft for the P = 4 next die, 2026-10-19: rtab 19 b, hsh, IDX.KVUNION, ATT plan mode)"
SPEC_MD = ROOT / "results/arch/hbm_next_1019/cmtp/isa_rows.md"
P_LANES = 4                       # physical lanes of the next die (owner 10-19 00:05, P = 4)
N_MAX = 16                        # rows a record (4-bit nm1)
SLOTS = 16                        # DYN banks (4-bit slot0)
TABLE_ROW_WORDS = 32              # row-table row (rsel): word 0 = count, words 1..count = entries
E_RANGE = 3                       # completion status of every legality fault below

# ---- UOP: the rows flag ------------------------------------------------------------------------------------------
OP_ROWS_BIT = 5                   # UOP op[5]
UOP_ROWS_BIT = 118 + OP_ROWS_BIT  # header bit 123
assert dict((n, (l, w)) for n, l, w in HGI.D_UOP_FIELDS)["op"] == (118, 6)
assert max(len(v) for v in HGI.D_OPS.values()) <= 8, "an HGI-1 op code reaches op[3]: re-check the rows flag"

# ---- ROWX (256 bits).  (name, lsb, width, signed, meaning) -------------------------------------------------------
OPND = tuple(HGI.D_OPND)          # A, B, C, D, O, R, I
RSTRIDE_W = 24
ROWX_FIELDS = [
    ("nm1", 0, 4, False, "N - 1: row count N = 1 .. 16 (with rsel: the upper bound of the table count)"),
    ("slot0", 4, 4, False, "first row's DYN bank / slot (0 .. 15); row r uses bank slot0 + rho(r); "
                           "UOP slot must equal slot0[2:0]; slot0 + N - 1 <= 15"),
    ("rgap", 8, 8, False, "extra cycles between row starts beyond the unit's row II (static-schedule spacing; 0 = back to back)"),
    ("rpl", 16, 2, False, "SM.MATVEC only: remainder-pass layout (r = N mod P rows, g = P / r lanes a row, a power of two): "
                          "0 idle lanes, 1 K-split (lane q of a row group takes K part q), 2 row-split (lane q takes output-row "
                          "part q), 3 reserved; other units 0 (see sm_pass_plan)"),
    ("rsel", 18, 1, False, "rows from the VM row table at rtab + 32 L: N = U32(word 0) <= nm1 + 1, row r takes entry word 1 + r"),
    ("rsv19", 19, 1, False, "reserved, 0"),
    ("rtab", 20, 19, False, "rsel: VM word address of row-table row 0 / of the ATT plan (32-word aligned, < 2^19: the grown "
                            "VM, PROG 10-19; was 18 b in 1.0); else 0"),
    ("emask", 39, 7, False, "rsel: bit k (A..I order) = operand k steps by the entry's e field instead of rho; else 0"),
    ("hsh", 46, 5, False, "HBM row-stride shift: an HBM operand steps rs_k << hsh BYTES a row (0 = bytes, the 1.0 meaning; "
                          "users mode: 12 = 4 KiB units, so the 24-bit rs reaches +-32 GiB per-user KV regions); VM strides are "
                          "never shifted"),
    ("rsv51", 51, 37, False, "reserved, 0"),
] + [(f"rs_{k}", 88 + RSTRIDE_W * i, RSTRIDE_W, True,
      f"row stride of operand {k} (signed; HBM bytes, multiple of 32 / VM FP32 words; 0 = broadcast; "
      f"must be 0 when {k} is absent or a STREAM / NONE descriptor)") for i, k in enumerate(OPND)]
assert sum(w for _, _, w, _, _ in ROWX_FIELDS) == 256
_cover = 0
for _n, _l, _w, _s, _m in ROWX_FIELDS:
    assert _cover == _l, (_n, _cover, _l)
    _cover += _w

# row-table entry (U32): rho in [3:0], e in [15:8], everything else 0
ENTRY_FIELDS = [("rho", 0, 4, "row / position / user index: DYN bank slot0 + rho, operands step by rho x rs"),
                ("rsv4", 4, 4, "0"),
                ("e", 8, 8, "expert-slot index for the operands selected by emask (IDX.UNION: rho x imm_b + kappa)"),
                ("rsv16", 16, 16, "0")]

# ---- new / defined operations --------------------------------------------------------------------------------------
NEW_OPS = {
    "IDX.UNION": dict(code=5, param="none; imm_a = experts E (DS 384); imm_b = slots a position row K (DS image 7 = 6 routed + the shared expert slot; e = rho x K + kappa)",
                      operands="A = U32 top-k ids, m = N rows of n = k, each row strictly ascending (IDX.TOPK order 1); "
                               "O = U32 union ids ascending (O.n >= U); D[0] = U (a CTL.LOOP [17] count); "
                               "R = U row-table rows of 32 words (R.stride = 32): word 0 = c_u, words 1..c_u = "
                               "entries {rho, e} in ascending rho, kappa = rank of u in row rho"),
    "IDX.KVUNION": dict(code=6, param="[3:0] lanes NL - 1 (NL <= P), [7:4] slot0 (the lanes' first DYN bank), [8] users "
                                      "(lanes are users: disjoint KV, masks exclusive), [24:16] line budget a SM (<= 256: the "
                                      "static calendar's reserved ATT span); imm_a = W (window rows, DS 128); "
                                      "imm_b = list-store rows a lane (DS 512)",
                        operands="A = U32 selection lists, m = NL rows of n = k (row l = lane l's TOPK_MERGE selection, "
                                 "strictly ascending, k <= imm_b), A.stride = row stride; window of lane l = positions "
                                 "POS_SLOT(slot0 + l) - W + 1 .. POS_SLOT(slot0 + l) (>= 0); R = the attention PLAN: 32 "
                                 "SM blocks of PLAN_WORDS (R.base 32-aligned; layout isa_rows.md R10); D = the lane map "
                                 "(D.n >= 16 + 128 NL): D[0] = union lines U, D[1 + l] = T_l, D[5 + l] = run chunks nrun_l, "
                                 "D[9] = max lines a SM (<= param [24:16] budget, else E_RANGE), D[10] = nodes, "
                                 "D[16 + 128 l + k] = node of lane l run k = {sm [4:0], node [9:5]}"),
    "ATT.QK/PV plan": dict(code="QK 0 / PV 1", param="unchanged (HGI-1)",
                           operands="with ROWX rsel = 1 and emask = 0: the KV-UNION PLAN mode (R10): rtab = the "
                                    "IDX.KVUNION plan base; row rho = query lane rho (bank slot0 + rho, rs on its q / "
                                    "p / score / output operands); SM s streams the lines of plan block s once, lane l "
                                    "applies the lines whose mask bit l is set on its own ordinal"),
    "CTL.USERS": dict(code=8, param="[3:0] N - 1 when no ROWX (slot0 = 0); with ROWX: N, slot0",
                      operands="A = U32 [2 N]: {token_s, pos_s} for s = 0 .. N - 1; sets DYN bank slot0 + s: "
                               "POS = POS_SLOT = pos_s, POS1 = POS_SLOT1 = pos_s + 1, TOKEN = token_s, SLOT = slot0 + s, "
                               "DS selectors (16..62) from pos_s; range-checked against cp_vocab / cp_ctx_max"),
    "CTL.TOKX": dict(code=5, param="[0] users: 0 = MTP commit (k beats at pos + i - 1), 1 = one beat per user slot",
                     operands="A = U32 [1 + n]: A[0] = k (MTP: 1 <= k <= ncol) or N (users), A[1..] = tokens; "
                              "completion beats {token, pos, slot} (users: pos = bank POS of slot0 + i); END follows"),
    "CTL.ACCEPT": dict(code=7, param="none", operands="A = U32 [1]: a = accepted drafts (0 .. ncol - 1); commit "
                                                      "n <- n + 1 + a; IDX.EHASH history restored to slot a; "
                                                      "no other state rolls back (rule R-POS)"),
    "SM.MATVEC": dict(code=0, param="[1:0] fmt, [5:2] positions - 1 (HGI-1 [4:2] widened; with ROWX it must equal "
                                    "N - 1, or 0 with rsel)", operands="unchanged"),
}
assert HGI.D_OPS["CTL"][5] == "TOKX" and HGI.D_OPS["CTL"][7] == "ACCEPT" and len(HGI.D_OPS["IDX"]) == 5

# ---- row timing: cost of an N-row record = c1 + (N - 1) (II + rgap).  PRICED unless marked MEASURED; UNITS replaces
# each entry with its measured RTL II (throughput qualification: measured within 10 % of this price).
ROW_II = {
    "SM.MATVEC": ("pass plan", "PRICED", "sm_pass_plan: line issues / max(1, issues per line / 1.374) of the AR record; "
                                        "SM4 lane-major publish skew +8 a further lane a pass (hnx_rp4lp4 LSKEW, MEASURED)"),
    "ATT.QK/PV": ("union stream", "MEASURED", "ATT4 bench: span = fixed 113-127 + 7.8 a union row (= fixed + comp x "
                                              "U(N)/U(1)), passes = ceil(N / P); shared 4-lane merge PV span 16-40 "
                                              "shorter (a1); E1 PASS; plan mode R10"),
    "FUSED.HC_PRE_NORM": (81.0, "MEASURED", "UNITS-FUSED hnx FUSED engine (@e70d3285a): 404 + 81 (N - 1), KX = 4 x slots, "
                                            "rgap 0 (KX = 2 needs rgap >= 64); price 160; old P6 RTL 197"),
    "FUSED.HC_POST": (103.0, "MEASURED", "UNITS-FUSED hnx FUSED engine: 196 + 103 (N - 1) (price 100)"),
    "FUSED.QDQ_*": ("n / 32", "PRICED", "quantiser 32 elements a cycle"),
    "HC.HC_MIX*": (250.0, "MEASURED", "UNITS tb_hnx_hc_eng4 (hnx root + 4 ring quarters): HC_MIX 998 + 250 (N - 1), "
                                      "bit-exact N = 1..8"),
    "COLL.ALL_GATHER / ALL_REDUCE": ("3K/2", "MEASURED", "UNITS-COLL ot_hnx_coll_gq: one fire + 40-edge drain, 3K/2 "
                                                         "edges a further row (K ring indices) = the price c1 - 741.7"),
    "COLL.ROW_GATHER": (623.0, "MEASURED", "UNITS-COLL rows: R = 623 flits a rail at the DS verify shape (price 1,449; "
                                           "payload-proportional elsewhere)"),
    "COLL.ARGMAX_MERGE": (32.0, "MEASURED", "UNITS-COLL rows: 53 + 32 (N - 1) (price 12.7-23.7)"),
    "COLL.TOPK_MERGE": ("c1 - 741.7", "PRICED", "one message train: endpoint + crossing + tail once, payload x N"),
    "IDX.TOPK": (49.2, "MEASURED", "UNITS-IDX ot_hnx_idx_topk_rows_static (price 47.0)"),
    "IDX.INDEX": (232.0, "MEASURED", "UNITS-IDXN (@5bf6d2d50): 1,297 + 232 (N - 1), keys read once a record (replay "
                                     "buffer), 8 row streams, 4 time-shared selectors (price 152 of the 658.9 frame)"),
    "IDX.UNION": ("48/67/90/101/142 (N 1/2/3/4/6)", "MEASURED", "UNITS-IDX ot_hnx_idx_union_static (idx packet client, "
                                                                "~18.6 a row; price N x 6 / 8 + 24)"),
    "IDX.KVUNION": ("(W + N k) / 8 + 320", "PRICED", "merge of N ascending lists at 8 ids a cycle + 32 plan blocks x 320 "
                                                     "words at 32 words a cycle; runs on IDX beside the ROW_GATHER the ATT "
                                                     "record waits for anyway (off the critical path)"),
    "SU.VOP": ("2k ceil(e / 512)", "MEASURED", "UNITS-SUDMA2 write-port split (@a42351330): AB 28 / ABC 56 at e = 7,168 "
                                               "(k per-row VM operands; VM fill bandwidth binds); indexed gather 1 (= price)"),
    "DMA.KVWB_DS": (8.0, "MEASURED", "UNITS-SUDMA kvwb: 36 + 8 (N - 1), +28 a 256-slot ring wrap (price 2)"),
    "DMA.*": ("c1 - first access", "PRICED", "first access once, rows at full bandwidth"),
    "ARGMAX.LOCAL": (22.0, "MEASURED", "UNITS-SUDMA2 ot_hnx_argmax_wide_rows: II 22 (1,347 words / 8 a beat on one slice;"
                                       " price 6 needs a ~4-slice row spread)"),
    "CTL.*": (0.0, "n/a", "CTL rows are not issued (USERS / TOKX take N from the record)"),
}


# ======================================================================================================================
# encode / decode
# ======================================================================================================================
@dataclasses.dataclass
class RowX:
    n: int = 1
    slot0: int = 0
    rgap: int = 0
    rpl: int = 0
    rsel: int = 0
    rtab: int = 0
    emask: int = 0
    hsh: int = 0
    rs: dict = dataclasses.field(default_factory=dict)     # operand -> signed row stride

    def fields(self):
        v = dict(nm1=self.n - 1, slot0=self.slot0, rgap=self.rgap, rpl=self.rpl, rsel=self.rsel, rsv19=0,
                 rtab=self.rtab, emask=self.emask, hsh=self.hsh, rsv51=0)
        for k in OPND:
            v[f"rs_{k}"] = int(self.rs.get(k, 0))
        return v

    def encode(self) -> int:
        w = 0
        for name, lsb, width, signed, _ in ROWX_FIELDS:
            x = int(self.fields()[name])
            if signed:
                if not -(1 << (width - 1)) <= x < (1 << (width - 1)):
                    raise RangeFault(f"ROWX {name}={x} outside signed {width} bits")
                x &= (1 << width) - 1
            elif not 0 <= x < (1 << width):
                raise RangeFault(f"ROWX {name}={x} outside {width} bits")
            w |= x << lsb
        return w

    @classmethod
    def decode(cls, w: int):
        v = {}
        for name, lsb, width, signed, _ in ROWX_FIELDS:
            x = (w >> lsb) & ((1 << width) - 1)
            if signed and x >> (width - 1):
                x -= 1 << width
            v[name] = x
        if v["rsv19"] or v["rsv51"]:
            raise RangeFault("ROWX reserved bits set")
        return cls(n=v["nm1"] + 1, slot0=v["slot0"], rgap=v["rgap"], rpl=v["rpl"], rsel=v["rsel"], rtab=v["rtab"],
                   emask=v["emask"], hsh=v["hsh"], rs={k: v[f"rs_{k}"] for k in OPND if v[f"rs_{k}"]})


class RangeFault(Exception):
    status = E_RANGE


def ops_of(unit):
    """HGI-1R op list of a unit (HGI-1 list + the new codes)."""
    ops = list(HGI.D_OPS[unit])
    if unit == "IDX":
        ops += ["UNION", "KVUNION"]
    if unit == "CTL":
        ops += ["USERS"]
    return ops


def encode(rec: RC.Rec, rowx: RowX | None) -> bytes:
    """HGI-1R record bytes: UOP (op[5] = rows when rowx), [SUT], [ROWX], MDESC x opnd.  An HGI-1 record (rowx None,
    op in the HGI-1 list) encodes byte-identically to records.Rec.encode."""
    check(rec, rowx)
    ops = ops_of(rec.unit)
    op = ops.index(rec.op) | ((1 << OP_ROWS_BIT) if rowx is not None else 0)
    v = dict(unit=HGI.D_UNITS.index(rec.unit), op=op, wait=rec.wait, pred=HGI.PRED.index(rec.pred), opnd=rec.opnd,
             tmpl=int(rec.sut is not None), slot=rec.slot, param=rec.param, imm_a=rec.imm_a & 0xFFFFFFFF,
             imm_b=rec.imm_b & 0xFFFFFFFF)
    h = 0
    for name, lsb, width in HGI.D_UOP_FIELDS:
        x = int(v[name])
        if not 0 <= x < (1 << width):
            raise RangeFault(f"UOP {name}={x} outside {width} bits")
        h |= x << lsb
    out = h.to_bytes(16, "little")
    if rec.sut is not None:
        out += RC.sut_encode(rec.sut).to_bytes(32, "little")
    if rowx is not None:
        out += rowx.encode().to_bytes(32, "little")
    for _, d in rec.descs_in_order():
        out += d.encode().to_bytes(32, "little")
    return out


def decode_one(buf: bytes, off: int = 0):
    """-> (Rec, RowX | None, next offset); faults (RangeFault) exactly where the die faults."""
    h = int.from_bytes(buf[off:off + 16], "little")
    v = {name: (h >> lsb) & ((1 << width) - 1) for name, lsb, width in HGI.D_UOP_FIELDS}
    unit = HGI.D_UNITS[v["unit"]]
    if unit not in HGI.D_OPS:
        raise RangeFault(f"reserved unit code {v['unit']}")
    rows = bool(v["op"] >> OP_ROWS_BIT & 1)
    code = v["op"] & ((1 << OP_ROWS_BIT) - 1)
    ops = ops_of(unit)
    if code >= len(ops):
        raise RangeFault(f"illegal op {code} for {unit}")
    r = RC.Rec(unit=unit, op=ops[code], wait=v["wait"], pred=HGI.PRED[v["pred"]], slot=v["slot"], param=v["param"],
               imm_a=v["imm_a"], imm_b=v["imm_b"])
    p = off + 16
    if v["tmpl"]:
        r.sut = RC.sut_decode(int.from_bytes(buf[p:p + 32], "little"))
        p += 32
    rx = None
    if rows:
        rx = RowX.decode(int.from_bytes(buf[p:p + 32], "little"))
        p += 32
    for i, k in enumerate(OPND):
        if v["opnd"] >> i & 1:
            r.desc[k] = RC.MDesc.decode(int.from_bytes(buf[p:p + 32], "little"))
            p += 32
    check(r, rx)
    return r, rx, p


def hgi1_decoder_faults(buf: bytes) -> bool:
    """True when the unchanged HGI-1 decoder (tools/hgi_sim/records.decode_one) refuses the record (fail-closed)."""
    try:
        RC.decode_one(buf, 0)
    except ValueError:
        return True
    return False


# ======================================================================================================================
# legality (the E_RANGE rules of isa_rows.md section 3)
# ======================================================================================================================
def check(rec: RC.Rec, rx: RowX | None):
    if rec.unit == "SM":
        pos_m1 = (rec.param >> 2) & 0xF
        if rec.param >> 6:
            raise RangeFault("SM param bits above [5:2] must be 0")
    if rx is None:
        if rec.unit == "SM" and ((rec.param >> 2) & 0xF) > 7:
            raise RangeFault("HGI-1 SM positions field is [4:2]; [5] needs ROWX")
        return
    if rec.unit == "IDX" and rec.op in ("UNION", "KVUNION"):
        raise RangeFault(f"IDX.{rec.op} carries no ROWX (N = A.m)")
    if rx.hsh and not any(d.space == "HBM" and rx.rs.get(k) for k, d in rec.desc.items()) and not (
            rec.unit == "IDX" and rec.op == "INDEX" and rx.rs.get("I")):
        raise RangeFault("hsh without an HBM row stride")
    if rx.hsh > 20:
        raise RangeFault(f"hsh {rx.hsh} > 20")
    if not 1 <= rx.n <= N_MAX:
        raise RangeFault(f"N {rx.n}")
    if rec.slot != (rx.slot0 & 7):
        raise RangeFault(f"UOP slot {rec.slot} != slot0[2:0] {rx.slot0 & 7}")
    if rx.slot0 + rx.n - 1 >= SLOTS:
        raise RangeFault(f"slot0 {rx.slot0} + N - 1 > 15")
    if rx.rpl and rec.unit != "SM":
        raise RangeFault("rpl is SM.MATVEC only")
    if rx.rpl == 3:
        raise RangeFault("rpl 3 reserved")
    if rx.rpl:
        r = rx.n % P_LANES
        if rx.rsel or r == 0 or P_LANES % r or (P_LANES // r) & (P_LANES // r - 1):
            raise RangeFault(f"rpl {rx.rpl} needs a static N whose remainder r = N mod {P_LANES} divides {P_LANES} "
                             "into a power-of-two group")
    if rx.rsel:
        if rx.rtab % TABLE_ROW_WORDS or rx.rtab >= 1 << 19:
            raise RangeFault(f"rtab {rx.rtab} not 32-word aligned below 2^19")
        if rec.unit == "ATT":
            if rx.emask:
                raise RangeFault("ATT plan mode: emask must be 0")
            if rx.n > P_LANES:
                raise RangeFault(f"ATT plan mode: {rx.n} lanes > P = {P_LANES} (one record a lane pass)")
    elif rx.rtab or rx.emask:
        raise RangeFault("rtab / emask without rsel")
    for k, s in rx.rs.items():
        d = rec.desc.get(k)
        if s and k == "I" and rec.unit == "IDX" and rec.op == "INDEX" and d is None:
            continue                 # R11: users-mode key-store row step (I is otherwise absent on INDEX)
        if s and (d is None or d.space in ("STREAM", "NONE")):
            raise RangeFault(f"row stride on absent / {getattr(d, 'space', 'absent')} operand {k}")
        if s and d.space == "HBM" and (s << rx.hsh) % 32:
            raise RangeFault(f"HBM row stride {s} << {rx.hsh} of {k} not a multiple of 32 bytes")
    if rec.unit == "SM":
        pm1 = (rec.param >> 2) & 0xF
        if rx.rsel:
            if pm1:
                raise RangeFault("SM with rsel: param [5:2] must be 0 (N from the table)")
        elif pm1 != rx.n - 1:
            raise RangeFault(f"SM param [5:2] {pm1} != N - 1 {rx.n - 1}")
    if rec.unit == "CTL" and rec.op in ("LOOP", "ENDLOOP", "END", "FENCE", "NOP"):
        raise RangeFault(f"CTL.{rec.op} takes no ROWX")


# ======================================================================================================================
# the normative row expansion
# ======================================================================================================================
def table_entries(rx: RowX, vm, L: int):
    """rsel: [(rho, e)] of loop iteration L from the VM row table (faults as the die does)."""
    row = rx.rtab + TABLE_ROW_WORDS * L
    cnt = int(vm[row])
    if not 0 <= cnt <= rx.n:
        raise RangeFault(f"row table count {cnt} > nm1 + 1 = {rx.n}")
    out = []
    for i in range(cnt):
        w = int(vm[row + 1 + i])
        rho, e = w & 0xF, (w >> 8) & 0xFF
        if w & ~0xFF0F:
            raise RangeFault(f"row table entry {w:#x} reserved bits")
        if rx.slot0 + rho >= SLOTS:
            raise RangeFault(f"entry rho {rho}: slot {rx.slot0 + rho} > 15")
        out.append((rho, e))
    return out


def expand(rec: RC.Rec, rx: RowX | None, vm=None, L: int = 0):
    """The N single-row HGI-1 records an N-row record means, in order: [(bank, Rec)].  bank = the DYN bank (slot) the
    row evaluates its descriptors in.  SM rows are single-position MATVECs (param [5:2] = 0)."""
    if rx is None:
        return [(rec.slot, rec)]
    att_plan = rx.rsel and rec.unit == "ATT"
    rows = table_entries(rx, vm, L) if rx.rsel and not att_plan else [(r, 0) for r in range(rx.n)]
    out = []
    for rho, e in rows:
        r = copy.copy(rec)
        r.desc = {}
        for k, d in rec.desc.items():
            d2 = copy.copy(d)
            step = e if rx.rsel and rx.emask >> OPND.index(k) & 1 else rho
            d2.base = d.base + step * (rx.rs.get(k, 0) << (rx.hsh if d.space == "HBM" else 0))
            if d2.base < 0 or d2.base >= 1 << 40:
                raise RangeFault(f"row {rho} operand {k} base out of range")
            r.desc[k] = d2
        r.slot = rx.slot0 + rho
        if rec.unit == "SM":
            r.param = rec.param & 3
        out.append((rx.slot0 + rho, r))
    return out


def check_rows_independent(rec: RC.Rec, rx: RowX | None, vm=None, L=0, written=("O", "R", "D")):
    """Compile-time rule: no row reads a VM word an EARLIER row of the same record writes (rows may overlap in
    hardware).  VM intervals only (HBM order is the unit's own posted-write rule).  Returns the first conflict or None."""
    if rx is None:
        return None
    ex = expand(rec, rx, vm, L)

    def span(d):
        if d.space != "VM":
            return None
        ist = 0 if d.ibcast else (d.istride or 1)
        lo = d.base
        hi = d.base + (d.m - 1) * d.stride + (d.n - 1) * ist
        return (min(lo, hi), max(lo, hi))
    wr = []
    for i, (_, r) in enumerate(ex):
        for k, d in r.desc.items():
            s = span(d)
            if s is None:
                continue
            if k not in written:
                for j, ws in wr:
                    if ws[0] <= s[1] and s[0] <= ws[1]:
                        return dict(row=i, reads=k, span=s, written_by_row=j, written=ws)
        for k in written:
            d = r.desc.get(k)
            s = span(d) if d is not None else None
            if s:
                wr.append((i, s))
    return None


# ======================================================================================================================
# SM pass plan and the K-split
# ======================================================================================================================
def csum_chunks(K, fmt):
    """csum chunks of an SM record's reduction (R-ARITH chunk8): FP8 / FP4 block-dot: K / 32 block terms; BF16 / INT8:
    K element terms; chunks of 8 terms."""
    terms = K // 32 if fmt in (1, 2) else K
    return max(1, -(-terms // 8))


def kparts(nc, s):
    """The 2^s K parts of a level-s split of the padded pairwise tree over nc chunk sums: part j = chunks
    [j 2^(t-s), (j + 1) 2^(t-s)) clipped to nc, t = ceil(log2 nc).  Each part is an aligned power-of-two run of the
    tree's leaves, so (part sums combined by the tree's top s levels) == csum bit for bit (an empty part is the
    tree's own +0 padding)."""
    t = max(0, math.ceil(math.log2(nc))) if nc > 1 else 0
    if s > t:
        s = t
    size = 1 << (t - s)
    return [(min(j * size, nc), min((j + 1) * size, nc)) for j in range(1 << s)]


def sm_pass_plan(N, P=P_LANES, rpl=0, nc=None, rows=None):
    """Lane passes of an N-row SM record on P lanes with line hold (one HBM read of a weight line, issued once a pass).
    Full passes: rows p P .. p P + P - 1 on lanes 0 .. P - 1, whole K, every output row.  Last pass (r = N mod P rows,
    g = P / r): rpl 0 -> r lanes busy, P - r idle; rpl 1 (K-split) -> remainder row j on lanes j g .. j g + g - 1, lane q
    of the group on K part q (kparts(nc, log2 g)), the g partials combined by the tree's top log2 g levels; rpl 2
    (row-split) -> lane q of the group on output-row part q of the record's `rows` output rows (rows per SM), no
    combine.  Both need a g-source lane-group broadcast in the remainder pass (two / four held lines at once).
    -> dict(passes=[[(lane, row, part, nparts)]], issues = line issues per weight line (the remainder pass counted at
    its largest part's share), cost_vs_ar = max(1, issues / 1.374))."""
    full, r = divmod(N, P)
    passes = [[(ln, p * P + ln, 0, 1) for ln in range(P)] for p in range(full)]
    issues = float(full)
    if r:
        if rpl:
            if P % r or (P // r) & (P // r - 1):
                raise RangeFault(f"rpl {rpl} with remainder {r} on {P} lanes")
            g = P // r
            passes.append([(j * g + q, full * P + j, q, g) for j in range(r) for q in range(g)])
            if rpl == 1:
                if nc is None:
                    issues += 1.0 / g
                else:
                    parts = kparts(nc, int(math.log2(g)))
                    issues += max(b_ - a_ for a_, b_ in parts) / nc
            else:
                if rows is None:
                    issues += 1.0 / g
                else:
                    issues += math.ceil(rows / g) / rows
        else:
            passes.append([(ln, full * P + ln, 0, 1) for ln in range(r)])
            issues += 1.0
    return dict(N=N, P=P, rpl=rpl, nc=nc, rows=rows, passes=passes, issues=round(issues, 6),
                cost_vs_ar=round(max(1.0, issues / HBM_LINE_RATIO), 6))


HBM_LINE_RATIO = 136 / 98.96      # SM line 136 B at one issue a cycle vs the SM's 98.96 B/cycle HBM share (owner 10-12)


def best_rpl(N, P=P_LANES, nc=None, rows=None):
    """the compiler's remainder-pass layout: the cheapest of idle / K-split / row-split (ties keep the simpler form)"""
    r = N % P
    if not r or P % r or (P // r) & (P // r - 1):
        return 0, sm_pass_plan(N, P, 0, nc, rows)["issues"]
    best = (0, sm_pass_plan(N, P, 0, nc, rows)["issues"])
    for m in (2, 1):
        i = sm_pass_plan(N, P, m, nc, rows)["issues"]
        if i < best[1] - 1e-9:
            best = (m, i)
    return best


# ======================================================================================================================
# DYN banks (doorbell / CTL.USERS)
# ======================================================================================================================
def dyn_bank(slot, pos, token, mode="mtp", users=None, rank=0):
    """The 16 generic DYN codes of bank `slot`.  mode mtp: the doorbell's pos / token, POS_SLOT = pos + slot.
    mode users: CTL.USERS row slot = {token_s, pos_s}: POS = POS_SLOT = pos_s.  (DS selectors 16..62 follow from the
    bank's POS_SLOT by the HGI-1 rule.)"""
    if mode == "users":
        token, p = users[slot]
        ps = p
    else:
        p, ps = pos, pos + slot
    return [0, p, p + 1, token, 0, rank, slot, ps, 0, 0, 0, 0, 0, 0, 0, ps + 1]


def idx_union(ids_rows, experts=384, pitch=6):
    """IDX.UNION reference: ids_rows = N lists of k ascending ids -> (union ascending, row tables [(c_u, [(rho, e)])]).
    e = rho x pitch + kappa, kappa = rank of u in row rho (the position's own top-k order = its combine slot)."""
    for row in ids_rows:
        if any(b <= a for a, b in zip(row, row[1:])) or any(not 0 <= i < experts for i in row):
            raise RangeFault(f"IDX.UNION row not strictly ascending in range: {row}")
    uni = sorted({i for row in ids_rows for i in row})
    tabs = []
    for u in uni:
        ent = [(rho, rho * pitch + row.index(u)) for rho, row in enumerate(ids_rows) if u in row]
        tabs.append((len(ent), ent))
    return uni, tabs


def entry_word(rho, e):
    return (rho & 0xF) | ((e & 0xFF) << 8)


# ======================================================================================================================
# R10: the attention KV-union PLAN (IDX.KVUNION -> ATT plan mode).  Exactness = ATT4 gate E1 (att4/E1.md C1..C5)
# ======================================================================================================================
NSM_ATT = 32                      # SMs a die that run attention jobs
PLAN_WORDS = 320                  # one SM block: header 32 + 256 line words + 32 mask words
PLAN_LINES = 256                  # MROWS of ot_hnx_att4_issue (lines an SM streams in one op)
PLAN_NODES = 16                   # (lane, run) nodes an SM publishes in one op
LINE_WIN = 1 << 31                # line word: [31] 1 = window row {ring lane [29:28], position [27:0]}; 0 = list-store row
DMAP = 16                         # D[16 + 128 l + k] = node of lane l run k
RUN_MAX = 128


def att_lanes_from(sel_rows, pos_rows, W=128, users=False):
    """lane lists in the golden order (E1 C1): window rows oldest first, then the compressed selection ascending.
    sel_rows[l] = lane l's selection (ascending, TOPK_MERGE order), pos_rows[l] = POS_SLOT of its bank."""
    lanes = []
    for l, (sel, ps) in enumerate(zip(sel_rows, pos_rows)):
        if any(b <= a for a, b in zip(sel, sel[1:])):
            raise RangeFault(f"lane {l} selection not strictly ascending")
        ring = l if users else 0
        lanes.append(dict(win=[("w", ring, q) for q in range(max(0, ps - W + 1), ps + 1)],
                          sel=[("c", l if users else 0, i) for i in sel], sel_ids=list(sel), store=l))
    return lanes


def _nrun(T, div=1, nsm=NSM_ATT):
    nch, r = -(-T // 8), 1
    while -(-nch // r) > nsm:
        r *= 2
    return max(1, r // div)


def kv_union_plan(lanes, nsm=NSM_ATT, store_rows=512, budget=PLAN_LINES):
    """IDX.KVUNION reference (the hardware computes exactly this; the compiler reserves `budget` lines a SM).
    1. Union stream (C1): every lane's window rows, ascending by (position, ring lane), then every lane's compressed
       rows ascending by (store lane, id) -- MTP lanes share one ring and one id space (store lane 0), users do not.
    2. Lane ordinals (C2): lane l's lines = the stream entries its list holds, in stream order = its golden list.
    3. Aligned runs (C4): nrun_l = the smallest power of two with ceil(ceil(T_l / 8) / nrun) <= 32, divided by the
       best of 1 / 2 / 4 (smaller aligned runs are equally exact); run k = ordinals [8 nrun k, 8 nrun (k + 1)).
    4. Jobs (ATT4 E1 sec. 4, 'balanced'): run index k of all lanes is ONE job when its union <= 0.75 x the lanes' sum
       (lines shared), else one job a lane; LPT (largest first, least-loaded SM, lowest SM on ties) onto nsm SMs; an
       SM streams its jobs back to back in ascending run index (a lane's short last run is its last node there).
    -> plan dict (blocks per SM, lane map, U, T, nrun, max_lines) or RangeFault (budget / node / run overflow)."""
    keys = sorted({x for ln in lanes for x in ln["win"]}, key=lambda x: (x[2], x[1]))
    keys += sorted({x for ln in lanes for x in ln["sel"]}, key=lambda x: (x[1], x[2]))
    pos_of = {k: i for i, k in enumerate(keys)}
    nl = len(lanes)
    lsets = [set(ln["win"]) | set(ln["sel"]) for ln in lanes]
    lane_ord = [[u for u, k in enumerate(keys) if k in lsets[l]] for l in range(nl)]
    T = [len(x) for x in lane_ord]
    store_of = {}
    for l, ln in enumerate(lanes):
        for j, x in enumerate(ln["sel"]):
            store_of.setdefault(x, ln["store"] * store_rows + j)     # the lowest lane that holds it (MTP) / own (users)
    best = None
    for div in (1, 2, 4):
        nrun = [_nrun(t, div, nsm) for t in T]
        nr = max((-(-t // (8 * r)) for t, r in zip(T, nrun)), default=0)
        jobs = []
        for k in range(nr):
            runs = {l: lane_ord[l][8 * nrun[l] * k: 8 * nrun[l] * (k + 1)] for l in range(nl)}
            runs = {l: r for l, r in runs.items() if r}
            tot = sum(len(r) for r in runs.values())
            uni = sorted(set().union(*[set(r) for r in runs.values()])) if runs else []
            if tot and len(uni) <= 0.75 * tot:
                jobs.append(dict(k=k, lanes=sorted(runs), lines=uni, runs=runs))
            else:
                jobs += [dict(k=k, lanes=[l], lines=list(r), runs={l: r}) for l, r in sorted(runs.items())]
        if nr > RUN_MAX:
            continue
        load = [0] * nsm
        nnod = [0] * nsm
        on = [[] for _ in range(nsm)]
        for j in sorted(jobs, key=lambda j: (-len(j["lines"]), j["k"], j["lanes"])):
            s_ = min((x for x in range(nsm) if nnod[x] + len(j["lanes"]) <= PLAN_NODES), key=lambda x: (load[x], x),
                     default=None)
            if s_ is None:
                break
            load[s_] += len(j["lines"])
            nnod[s_] += len(j["lanes"])
            on[s_].append(j)
        else:
            if best is None or max(load) < best[0]:
                best = (max(load), div, nrun, on)
    if best is None:
        raise RangeFault("KVUNION: no run size fits 128 runs a lane and 16 nodes a SM")
    mx, div, nrun, on = best
    if mx > budget:
        raise RangeFault(f"KVUNION: a SM needs {mx} lines > budget {budget}")
    blocks, dmap = [], {}
    for s_, js in enumerate(on):
        js = sorted(js, key=lambda j: (j["k"], j["lanes"]))
        lines, nodes, masks = [], [], []
        for j in js:
            for u in j["lines"]:
                lines.append(u)
                masks.append(tuple(int(l in j["runs"] and u in set(j["runs"][l])) for l in range(nl)))
            for l in j["lanes"]:
                if len(nodes) >= PLAN_NODES:
                    raise RangeFault(f"KVUNION: SM {s_} > {PLAN_NODES} nodes")
                dmap[(l, j["k"])] = (s_, len(nodes))
                nodes.append((l, j["k"], len(j["runs"][l])))
        words = []
        for u in lines:
            kind, ring, idx = keys[u]
            words.append(LINE_WIN | (ring << 28) | idx if kind == "w" else store_of[keys[u]])
        blocks.append(dict(lines=lines, words=words, masks=masks, nodes=nodes))
    return dict(nl=nl, U=len(keys), T=T, nrun=nrun, div=div, max_lines=mx, blocks=blocks, dmap=dmap, keys=keys,
                lane_ord=lane_ord, store_rows=store_rows)


def plan_words(plan, nsm=NSM_ATT):
    """-> (R, D): the U32 VM images IDX.KVUNION writes (R = nsm blocks of PLAN_WORDS, D = the lane map)"""
    import numpy as np
    R = np.zeros(nsm * PLAN_WORDS, np.uint32)
    for s_, b in enumerate(plan["blocks"]):
        o = s_ * PLAN_WORDS
        R[o] = len(b["lines"])
        R[o + 1] = len(b["nodes"])
        for i, (l, k, n) in enumerate(b["nodes"]):
            R[o + 2 + i] = (l & 3) | (k & 0xFFF) << 2 | (n & 0xFFFF) << 14
        for i, w in enumerate(b["words"]):
            R[o + 32 + i] = w
        for i, mk in enumerate(b["masks"]):
            for l, bit in enumerate(mk):
                if bit:
                    R[o + 288 + 2 * (i // 16) + (i % 16) // 8] |= np.uint32(1 << (4 * (i % 8) + l))
    D = np.zeros(DMAP + RUN_MAX * plan["nl"], np.uint32)
    D[0] = plan["U"]
    for l in range(plan["nl"]):
        D[1 + l] = plan["T"][l]
        D[5 + l] = plan["nrun"][l]
    D[9] = plan["max_lines"]
    D[10] = len(plan["dmap"])
    for (l, k), (s_, n) in plan["dmap"].items():
        D[DMAP + RUN_MAX * l + k] = (s_ & 0x1F) | (n & 0x1F) << 5
    return R, D


def plan_lane_lists(R, D, nl, lanes, store_rows=512, nsm=NSM_ATT):
    """DECODE the VM images as the ATT engines do and rebuild every lane's list in its merge order: for lane l, run k
    = 0, 1, ...: SM / node from D, that SM's masked lines for lane l, the node's slice in stream order.  Also checks
    the per-SM ordinal alignment (C2 / C4).  -> [list of line keys a lane] (compare with the golden lane lists)"""
    out = []
    store_key = {}
    for ln in lanes:
        for j, x in enumerate(ln["sel"]):
            store_key[ln["store"] * store_rows + j] = x
    for l in range(nl):
        T, nrun = int(D[1 + l]), int(D[5 + l])
        lst = []
        k = 0
        while len(lst) < T:
            v = int(D[DMAP + RUN_MAX * l + k])
            s_, node = v & 0x1F, v >> 5 & 0x1F
            o = s_ * PLAN_WORDS
            nlines, nnodes = int(R[o]), int(R[o + 1])
            if node >= nnodes or nlines > PLAN_LINES:
                raise RangeFault(f"lane {l} run {k}: bad node {node} / lines {nlines}")
            mine = [i for i in range(nlines)
                    if int(R[o + 288 + 2 * (i // 16) + (i % 16) // 8]) >> (4 * (i % 8) + l) & 1]
            # the lane's nodes on this SM consume `mine` in node order
            used = 0
            for nn in range(nnodes):
                w = int(R[o + 2 + nn])
                nl_, nk, nlen = w & 3, w >> 2 & 0xFFF, w >> 14 & 0xFFFF
                if nl_ != l:
                    continue
                if nn == node:
                    if nk != k:
                        raise RangeFault(f"lane {l}: node {node} on SM {s_} is run {nk}, map says {k}")
                    if used % 8:
                        raise RangeFault(f"lane {l} run {k}: SM-local ordinal {used} not chunk aligned (C2/C4)")
                    if len(lst) != 8 * nrun * k:
                        raise RangeFault(f"lane {l} run {k}: starts at ordinal {len(lst)}, not {8 * nrun * k}")
                    for i in mine[used:used + nlen]:
                        w_ = int(R[o + 32 + i])
                        if w_ & LINE_WIN:
                            lst.append(("w", w_ >> 28 & 3, w_ & 0x0FFFFFFF))
                        else:
                            lst.append(store_key[w_])
                    break
                used += nlen
            k += 1
            if k > RUN_MAX:
                raise RangeFault(f"lane {l}: runs never reach T = {T}")
        out.append(lst)
    return out


# ======================================================================================================================
# md tables + self test
# ======================================================================================================================
def md_tables():
    out = ["<!-- BEGIN isa_rows.py tables (generated: python3 tools/hbm_next/isa_rows.py --md-tables) -->",
           "", "**ROWX (256 bits)**", "", "| Bits | Field | Signed | Meaning |", "|---|---|---|---|"]
    for name, lsb, width, signed, meaning in ROWX_FIELDS:
        out.append(f"| {lsb + width - 1}:{lsb} | `{name}` | {'yes' if signed else 'no'} | {meaning} |")
    out += ["", "**Row-table entry (U32)**", "", "| Bits | Field | Meaning |", "|---|---|---|"]
    for name, lsb, width, meaning in ENTRY_FIELDS:
        out.append(f"| {lsb + width - 1}:{lsb} | `{name}` | {meaning} |")
    out += ["", "**New and defined operations**", "", "| Operation | Code | `param` / immediates | Operands and semantics |",
            "|---|---:|---|---|"]
    for k, v in NEW_OPS.items():
        out.append(f"| {k} | {v['code']} | {v['param']} | {v['operands']} |")
    out += ["", "**Row II (cost of an N-row record = c1 + (N - 1) (II + rgap))**", "",
            "| Family | II (cycles) | Basis | Source |", "|---|---|---|---|"]
    for k, (ii, st, src) in ROW_II.items():
        out.append(f"| {k} | {ii} | {st} | {src} |")
    out += ["", "<!-- END isa_rows.py tables -->"]
    return "\n".join(out)


def selftest():
    import numpy as np
    import hdc_golden_v41 as GV
    res = {}
    MD = RC.MDesc
    # 1) HGI-1 records encode identically with rowx None; every HGI-1 record round-trips
    r = RC.Rec("SM", "MATVEC", param=1 | (3 << 2), desc=dict(A=MD(space="VM", fmt="FP32", base=4096, n=4096, m=4, stride=4096),
                                                       B=MD(space="HBM", fmt="FP8E4M3", base=1 << 30, n=4096, m=128, stride=4096),
                                                       O=MD(space="VM", fmt="FP32", base=40960, n=128, m=4, stride=128)))
    assert encode(r, None) == r.encode()
    # 2) N-row records: round trip, op[5] set, HGI-1 decoder faults (fail-closed)
    rx = RowX(n=6, slot0=0, rpl=1, rs=dict(A=4096, O=128))
    r6 = copy.deepcopy(r)
    r6.param = 1 | (5 << 2)
    b = encode(r6, rx)
    r2, rx2, end = decode_one(b)
    assert end == len(b) and rx2 == rx and r2.param == r6.param and r2.desc["A"].base == 4096
    assert (int.from_bytes(b[:16], "little") >> UOP_ROWS_BIT) & 1
    assert hgi1_decoder_faults(b)
    res["roundtrip"] = "ok"
    # 3) expansion = N single-row records, bank slot0 + r, bases stepped
    ex = expand(r6, rx)
    assert [s for s, _ in ex] == list(range(6)) and [x.desc["A"].base for _, x in ex] == [4096 * (1 + i) for i in range(6)]
    assert all(x.desc["B"].base == 1 << 30 and x.param == 1 for _, x in ex)
    # 4) legality negatives (each must fault)
    neg = {
        "slot mismatch": lambda: check(dataclasses.replace(r6, slot=1), rx),
        "N 17": lambda: RowX(n=17).encode(),
        "slot overflow": lambda: check(r6, dataclasses.replace(rx, slot0=12)),
        "SM param != N-1": lambda: check(dataclasses.replace(r6, param=1 | (2 << 2)), rx),
        "rpl 3 reserved": lambda: check(r6, dataclasses.replace(rx, rpl=3)),
        "rpl on N = 7 (r = 3)": lambda: check(dataclasses.replace(r6, param=1 | (6 << 2)), dataclasses.replace(rx, n=7)),
        "stride on absent C": lambda: check(r6, dataclasses.replace(rx, rs=dict(C=8))),
        "HBM stride not 32-B": lambda: check(r6, dataclasses.replace(rx, rs=dict(B=16))),
        "rtab unaligned": lambda: check(dataclasses.replace(r6, param=1), RowX(n=6, rsel=1, rtab=33)),
        "rpl on SU": lambda: check(RC.Rec("SU", "VOP"), RowX(n=2, rpl=1)),
        "CTL.LOOP rows": lambda: check(RC.Rec("CTL", "LOOP"), RowX(n=2)),
        "reserved bits": lambda: RowX.decode(RowX(n=2).encode() | (1 << 60)),
        "hsh without HBM stride": lambda: check(RC.Rec("SU", "VOP", desc=dict(A=MD(space="VM", base=0, n=8, m=1))), RowX(n=2, hsh=12, rs=dict(A=8))),
    }
    for k, f in neg.items():
        try:
            f()
        except RangeFault:
            continue
        raise AssertionError(f"legality negative did not fault: {k}")
    res["negatives_fault"] = sorted(neg)
    # 5) rsel + IDX.UNION: grouped GEMM rows from the union tables, combine slots e = rho K + kappa
    ids = [[3, 17, 40, 41, 200, 383], [3, 9, 40, 77, 200, 300], [1, 3, 40, 41, 52, 383]]
    uni, tabs = idx_union(ids)
    assert uni[0] == 1 and dict(zip(uni, tabs))[3] == (3, [(0, 0), (1, 6), (2, 13)])
    vm = np.zeros(1 << 12, dtype=np.uint32)
    for L, (c, ent) in enumerate(tabs):
        vm[64 + 32 * L] = c
        for i, (rho, e) in enumerate(ent):
            vm[64 + 32 * L + 1 + i] = entry_word(rho, e)
    rs = RC.Rec("SM", "MATVEC", param=1, desc=dict(A=MD(space="VM", base=0, n=4096, m=1), B=MD(space="HBM", fmt="FP8E4M3", base=0, n=4096, m=64, stride=4096),
                                                    O=MD(space="VM", base=1 << 16, n=64, m=1)))
    rxs = RowX(n=6, rsel=1, rtab=64, emask=1 << OPND.index("O"), rs=dict(A=4096, O=64))
    L3 = uni.index(40)
    ex = expand(rs, rxs, vm, L3)
    assert [s for s, _ in ex] == [0, 1, 2] and [x.desc["O"].base for _, x in ex] == [(1 << 16) + 64 * e for e in (2, 8, 14)]
    assert check_rows_independent(rs, rxs, vm, L3) is None
    bad = RC.Rec("SU", "VOP", desc=dict(A=MD(space="VM", base=100, n=8, m=1), O=MD(space="VM", base=108, n=8, m=1)))
    assert check_rows_independent(bad, RowX(n=2, rs=dict(A=8, O=8))) is not None     # row 1 reads row 0's output
    res["union_rsel"] = dict(union=len(uni), rows=[t[0] for t in tabs])
    # 6) K-split exactness: csum over block-dot terms == level-s parts combined by the tree's top levels, bit for bit,
    #    for every SM shape of the DS layer (K blocks) and random + adversarial (cancelling, subnormal, -0) terms
    GV.set_arith("chunk8")
    rng = np.random.default_rng(1019)
    shapes = {}
    for K in (512, 1024, 2048, 4096, 5120, 7168, 4096 * 3, 128):
        for fmt in (1, 0):
            nc = csum_chunks(K, fmt)
            terms = K // 32 if fmt == 1 else K
            for s in (1, 2):
                for trial in range(40):
                    kind = trial % 4
                    t = rng.standard_normal((3, terms)).astype(np.float32)
                    if kind == 1:
                        t *= np.float32(2.0) ** rng.integers(-140, 100, size=t.shape).astype(np.float32)
                    elif kind == 2:
                        t[:, ::2] = -t[:, 1::2] if terms % 2 == 0 else t[:, ::2]
                    elif kind == 3:
                        t[:, : terms // 2] = np.float32(-0.0)
                    full = GV.csum(t)
                    parts = []
                    for a_, b_ in kparts(nc, s):
                        seg = t[:, a_ * 8:b_ * 8]
                        # a part is the csum of its own chunks padded to the part's power-of-two leaf count
                        size = 1 << (max(0, math.ceil(math.log2(nc))) - min(s, max(0, math.ceil(math.log2(nc))))) if nc > 1 else 1
                        pad = np.zeros((3, size * 8 - seg.shape[1]), np.float32)
                        parts.append(GV.csum(np.concatenate([seg, pad], axis=1)) if seg.shape[1] else
                                     np.zeros(3, np.float32))
                    while len(parts) > 1:
                        parts = [GV.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
                    assert np.array_equal(full.view(np.uint32), parts[0].view(np.uint32)), (K, fmt, s, kind)
            shapes[f"K{K}_fmt{fmt}"] = dict(nc=nc, N6_ksplit=sm_pass_plan(6, 4, 1, nc)["issues"],
                                            N5_ksplit=sm_pass_plan(5, 4, 1, nc)["issues"])
    res["ksplit_bit_exact"] = dict(trials=8 * 2 * 2 * 40, shapes=shapes)
    # 7) pass plans: 6 rows on 4 lanes
    p0, p1, p2 = sm_pass_plan(6, 4, 0), sm_pass_plan(6, 4, 1), sm_pass_plan(6, 4, 2, rows=13)
    assert p0["issues"] == 2.0 and p1["issues"] == 1.5 and len(p1["passes"][1]) == 4 and abs(p2["issues"] - 20 / 13) < 1e-6
    assert best_rpl(6, 4, nc=20, rows=1) == (1, 1.8) and best_rpl(6, 4, nc=20, rows=40) == (2, 1.5)
    res["pass_plan_N6"] = dict(no_split=p0["cost_vs_ar"], ksplit=p1["cost_vs_ar"], rowsplit_13rows=p2["cost_vs_ar"],
                               lanes_pass2=p1["passes"][1])
    # 9) R10 KV-union plan: decode(images) rebuilds every lane's golden list, chunk-aligned per SM; mutants fail
    rng = np.random.default_rng(1910)
    kvp = {}
    for case, nl, users, ov in (("mtp4_overlap0.6", 4, False, 0.6), ("mtp2_pass2", 2, False, 0.6),
                                ("mtp4_disjoint", 4, False, 0.0), ("mtp4_full", 4, False, 1.0),
                                ("users4", 4, True, 0.0), ("short_ctx", 4, False, 0.5)):
        nrows = 4096 if case != "short_ctx" else 40
        k = 512 if case != "short_ctx" else 9
        base = sorted(rng.choice(nrows, k, replace=False).tolist())
        sels = []
        for l in range(nl):
            keep = [i for i in base if rng.random() < ov]
            rest = sorted(set(rng.choice(nrows, 3 * k, replace=False).tolist()) - set(keep))
            sels.append(sorted(keep + rest[:k - len(keep)]))
        pos = [70000 + l for l in range(nl)] if case != "short_ctx" else [300 + l for l in range(nl)]
        if users:
            pos = [70000 + 977 * l for l in range(nl)]
        lanes = att_lanes_from(sels, pos, 128, users)
        plan = kv_union_plan(lanes)
        R, D = plan_words(plan)
        got = plan_lane_lists(R, D, nl, lanes)
        for l in range(nl):
            assert got[l] == lanes[l]["win"] + lanes[l]["sel"], (case, l)
        kvp[case] = dict(U=plan["U"], T=plan["T"], nrun=plan["nrun"], div=plan["div"], max_lines=plan["max_lines"],
                         nodes=len(plan["dmap"]))
        if case == "mtp4_overlap0.6":
            for mname, mut in (("zero_insertion", "zins"), ("lane_swap", "swap"), ("node_misaligned", "shift")):
                R2 = R.copy()
                o = int(D[DMAP + RUN_MAX * 1 + 0] & 0x1F) * PLAN_WORDS
                if mut == "zins":          # lane 1 gets a beat on a line it did not select (E1 negative 'zins')
                    for i in range(int(R2[o])):
                        wi = o + 288 + 2 * (i // 16) + (i % 16) // 8
                        if not int(R2[wi]) >> (4 * (i % 8) + 1) & 1:
                            R2[wi] |= np.uint32(1 << (4 * (i % 8) + 1))
                            break
                elif mut == "swap":        # lane 1 reads lane 0's mask bits (ATT4 MUT 4)
                    for i in range(int(R2[o])):
                        wi = o + 288 + 2 * (i // 16) + (i % 16) // 8
                        b0 = int(R2[wi]) >> (4 * (i % 8)) & 1
                        R2[wi] = (int(R2[wi]) & ~(1 << (4 * (i % 8) + 1))) | (b0 << (4 * (i % 8) + 1))
                else:                      # a node length off by one: the next node starts off a chunk boundary
                    w = int(R2[o + 2])
                    R2[o + 2] = (w & 0x3FFF) | (((w >> 14) - 1) & 0xFFFF) << 14
                try:
                    bad = plan_lane_lists(R2, D, nl, lanes)
                    ok = all(bad[l] == lanes[l]["win"] + lanes[l]["sel"] for l in range(nl))
                except RangeFault:
                    ok = False
                assert not ok, f"KV plan mutant {mname} not caught"
                kvp[case]["mutant_" + mname] = "caught"
    try:
        kv_union_plan(att_lanes_from([sorted(rng.choice(4096, 512, replace=False).tolist()) for _ in range(4)],
                                     [70000 + l for l in range(4)], 128, True), budget=40)
        raise AssertionError("KVUNION budget overflow did not fault")
    except RangeFault:
        kvp["budget_overflow"] = "faults"
    rx_att = RowX(n=4, rsel=1, rtab=4096 * 32, rs=dict(A=512, O=512))
    att = RC.Rec("ATT", "QK", desc=dict(A=MD(space="VM", base=0, n=512, m=1), O=MD(space="VM", base=1 << 16, n=640, m=1)))
    assert decode_one(encode(att, rx_att))[1] == rx_att and len(expand(att, rx_att)) == 4
    for bad_rx in (dataclasses.replace(rx_att, emask=1), dataclasses.replace(rx_att, n=5)):
        try:
            check(att, bad_rx)
            raise AssertionError("ATT plan-mode negative did not fault")
        except RangeFault:
            pass
    rx_h = RowX(n=4, hsh=12, rs=dict(O=230000))          # users: 4 KiB units -> 942 MB a user region
    kvwb = RC.Rec("DMA", "KVWB_DS", desc=dict(A=MD(space="VM", base=0, n=512, m=1),
                                               O=MD(space="HBM", base=1 << 34, n=512, m=256, stride=2048)))
    assert [x.desc["O"].base for _, x in expand(kvwb, rx_h)] == [(1 << 34) + i * 230000 * 4096 for i in range(4)]
    assert decode_one(encode(kvwb, rx_h))[1] == rx_h
    res["kv_union_plan"] = kvp
    # 8) md tables single source
    md = SPEC_MD.read_text() if SPEC_MD.exists() else ""
    res["md_tables_match"] = md_tables() in md
    assert res["md_tables_match"], "isa_rows.md tables differ from isa_rows.py: re-render with --md-tables"
    res["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return res


def main():
    if "--md-tables" in sys.argv:
        print(md_tables())
        return 0
    if "--selftest" in sys.argv:
        r = selftest()
        print(json.dumps(r, indent=1, default=str))
        print("SELFTEST PASS")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
