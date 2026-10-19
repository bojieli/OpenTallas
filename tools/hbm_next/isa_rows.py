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

VERSION = "HGI-1R 1.0 (draft for the P = 4 next die, 2026-10-19)"
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
    ("rtab", 20, 18, False, "rsel: VM word address of row-table row 0 (32-word aligned, < 2^18); else 0"),
    ("emask", 38, 7, False, "rsel: bit k (A..I order) = operand k steps by the entry's e field instead of rho; else 0"),
    ("rsv45", 45, 43, False, "reserved, 0"),
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
    "IDX.UNION": dict(code=5, param="none; imm_a = experts E (DS 384); imm_b = slot pitch K (DS 6, e = rho x K + kappa)",
                      operands="A = U32 top-k ids, m = N rows of n = k, each row strictly ascending (IDX.TOPK order 1); "
                               "O = U32 union ids ascending (O.n >= U); D[0] = U (a CTL.LOOP [17] count); "
                               "R = U row-table rows of 32 words (R.stride = 32): word 0 = c_u, words 1..c_u = "
                               "entries {rho, e} in ascending rho, kappa = rank of u in row rho"),
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
    "SM.MATVEC": ("pass plan", "PRICED", "sm_pass_plan: line issues / max(1, issues per line / 1.374) of the AR record"),
    "ATT.QK/PV": ("union stream", "PRICED", "fixed spans once + comp x U(N)/U(1) a pass, passes = ceil(N / P); E1 PASS (att4/E1.md)"),
    "FUSED.HC_PRE_NORM": (197.0, "MEASURED", "P6 RTL 8fe5d18bd: (1,451 - 466) / 5"),
    "FUSED.HC_POST": (100.0, "PRICED", "SU chain 25,600 words / 256"),
    "FUSED.QDQ_*": ("n / 32", "PRICED", "quantiser 32 elements a cycle"),
    "HC.HC_MIX*": (250.0, "PRICED", "HCP W256 x6 measured II 250; Sinkhorn 634 / 3 units; GATE <= 950 (STUDY d), static engine 4,385 FAILS"),
    "COLL.*": ("c1 - 741.7", "PRICED", "one message train: endpoint + crossing + tail (741.7) once, payload x N"),
    "IDX.TOPK": (47.0, "PRICED", "router top-6 RTL 47 cycles a row"),
    "IDX.INDEX": ("c1 x 152 / 658.9", "PRICED", "one key stream; query ingest 152 of the 658.9-cycle frame a row"),
    "IDX.UNION": ("N x 6 / 8 + 24", "PRICED", "8 ids a cycle into a 384-b bitmap + per-expert table write (CMTP estimate)"),
    "SU.VOP": ("su nv", "PRICED", "timing.su_cost at 2 m minus m: lane beats a row, depth once"),
    "DMA.*": ("c1 - first access", "PRICED", "first access once, rows at full bandwidth"),
    "ARGMAX.LOCAL": (6.0, "PRICED", "per-row reduce tail"),
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
    rs: dict = dataclasses.field(default_factory=dict)     # operand -> signed row stride

    def fields(self):
        v = dict(nm1=self.n - 1, slot0=self.slot0, rgap=self.rgap, rpl=self.rpl, rsel=self.rsel, rsv19=0,
                 rtab=self.rtab, emask=self.emask, rsv45=0)
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
        if v["rsv19"] or v["rsv45"]:
            raise RangeFault("ROWX reserved bits set")
        return cls(n=v["nm1"] + 1, slot0=v["slot0"], rgap=v["rgap"], rpl=v["rpl"], rsel=v["rsel"], rtab=v["rtab"],
                   emask=v["emask"], rs={k: v[f"rs_{k}"] for k in OPND if v[f"rs_{k}"]})


class RangeFault(Exception):
    status = E_RANGE


def ops_of(unit):
    """HGI-1R op list of a unit (HGI-1 list + the new codes)."""
    ops = list(HGI.D_OPS[unit])
    if unit == "IDX":
        ops += ["UNION"]
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
        if rec.op in ("UNION",):
            raise RangeFault("IDX.UNION carries ROWX (N = A.m)")
        return
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
        if rx.rtab % TABLE_ROW_WORDS or rx.rtab >= 1 << 18:
            raise RangeFault(f"rtab {rx.rtab} not 32-word aligned below 2^18")
    elif rx.rtab or rx.emask:
        raise RangeFault("rtab / emask without rsel")
    for k, s in rx.rs.items():
        d = rec.desc.get(k)
        if s and (d is None or d.space in ("STREAM", "NONE")):
            raise RangeFault(f"row stride on absent / {getattr(d, 'space', 'absent')} operand {k}")
        if s and d.space == "HBM" and s % 32:
            raise RangeFault(f"HBM row stride {s} of {k} not a multiple of 32 bytes")
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
    rows = table_entries(rx, vm, L) if rx.rsel else [(r, 0) for r in range(rx.n)]
    out = []
    for rho, e in rows:
        r = copy.copy(rec)
        r.desc = {}
        for k, d in rec.desc.items():
            d2 = copy.copy(d)
            step = e if rx.rsel and rx.emask >> OPND.index(k) & 1 else rho
            d2.base = d.base + step * rx.rs.get(k, 0)
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
        "reserved bits": lambda: RowX.decode(RowX(n=2).encode() | (1 << 50)),
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
