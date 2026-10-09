"""HGI-1 program records (docs/HBM_GENERIC_INTERFACE.md section 6, the owner-approved current design): encode / decode,
bit for bit.

Every field position comes from tools/hbm_generic_iface.py's current-design tables (D_UOP_FIELDS, D_MDESC_FIELDS,
D_SUT_LAYOUT, D_OPS, D_UNITS, D_OPND, PRED, SPACE, FMT), so a spec change shows up here without edits.  A record is a
128-bit header (UOP), an optional 256-bit SU template (SUT), then one 256-bit memory descriptor (MDESC) per set `opnd`
bit in A, B, C, D, O, R, I order; all little-endian.  The legacy v0.9 encoding is not used.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hbm_generic_iface as HGI  # noqa: E402

OPND = tuple(HGI.D_OPND)                    # A, B, C, D, O, R, I
OPS = HGI.D_OPS
UNITS = HGI.D_UNITS
NSEL_FROM_VM = HGI.NSEL_FROM_VM
DYN = {k: i for i, k in enumerate(HGI.D_DYN)}

# Gaps found while lowering; G1-G14 and C3b are folded into the approved spec (aba41e7b4).  Kept as history.
SPEC_GAPS = [
    dict(id="G1", item="SUT bit positions", status="resolved: packed from bit 0 in list order"),
    dict(id="G2", item="SU.VOP D and R operands", status="resolved: opnd A,B,C,D,O,R,I"),
    dict(id="G3", item="per-row scalar broadcast", status="resolved: MDESC ibcast"),
    dict(id="G4", item="softmax op", status="resolved: FUSED.SOFTMAX (SU fallback bound until CF-SFX)"),
    dict(id="G5", item="norm output format per op", status="resolved: O.fmt"),
    dict(id="G6", item="multipass carry order", status="resolved: carry the csum8 binary-counter state"),
    dict(id="G7", item="CTL.END token source", status="resolved: A required on r25"),
    dict(id="G8-G14", item="DS native lowering items", status="resolved: QDQ ops, even-split gather, group reduce, "
         "per-die images, ATT B+C ring, IDX.EHASH, COLL.ROW_GATHER"),
    dict(id="C3b", item="indexed descriptors", status="resolved: MDESC indexed + I operand"),
    # OPEN (found while moving the DS native lowering onto the approved encoding, 2026-10-09; sent to hbm-iface)
    dict(id="G15", item="IDX.TOPK output order: the approved order is descending score, but the DS router top-6 and "
         "the DS index top-512 select by rank comparators and emit ids in ASCENDING ID order, which is the golden's "
         "order (expert slot order, the route-weight sum order, the selected-row order); no order flag exists",
         status="open; PROVISIONAL reading param[12] = 1 -> ids in ascending id order (machine.TOPK_ASC)"),
    dict(id="G16", item="DS indexer engines (IDX.INDEX_Q, INDEX_SCORES, SELECT, the index TOPK and COLL.TOPK_MERGE "
         "of the candidate lists) keep their scores / candidates in the indexer engine's own buffers; section 6.7 "
         "defines no operands, param or immediates for them",
         status="open; the DS lowering passes layer = imm_b, source layer = param, count = imm_a (DS engine fields)"),
    dict(id="G17", item="ARGMAX.LOCAL id offset for DS: spec 5.4 lists DS imm_a = 0 (ids already global), but the "
         "DS head's even split (129,280 over 96: 1,346 or 1,347 rows) is not RANK x imm_a",
         status="open; the DS lowering uses uniform 1,347-row head shards (rows are independent dots, so logits are "
                "unchanged) and imm_a = 1,347"),
]


@dataclasses.dataclass
class MDesc:
    space: str = "VM"          # HBM | VM | STREAM | NONE
    fmt: str = "FP32"
    base: int = 0
    n: int = 1
    m: int = 1
    stride: int = 0
    istride: int = 0           # 0 = 1
    lstride: int = 0
    dyn_sel: int = 0
    dyn_mul: int = 0
    n_sel: int = 0
    l1stride: int = 0
    ibcast: int = 0            # inner stride 0 (per-row scalar broadcast)
    indexed: int = 0           # base += U32(VM[I + L]) * dyn_mul instead of the DYN term

    def encode(self) -> int:
        v = dict(space=HGI.SPACE.index(self.space), fmt=HGI.FMT[self.fmt], base=self.base, n=self.n, m=self.m,
                 stride=self.stride & 0xFFFFFFFF, istride=self.istride, lstride=self.lstride & 0xFFFFFFFF,
                 dyn_sel=self.dyn_sel, dyn_mul=self.dyn_mul, n_sel=self.n_sel, l1stride=self.l1stride & 0xFFFFFFFF,
                 ibcast=self.ibcast, indexed=self.indexed)
        w = 0
        for name, lsb, width in HGI.D_MDESC_FIELDS:
            x = int(v[name])
            if not 0 <= x < (1 << width):
                raise ValueError(f"MDESC {name}={x} outside {width} bits")
            w |= x << lsb
        return w

    @classmethod
    def decode(cls, w: int):
        v = {name: (w >> lsb) & ((1 << width) - 1) for name, lsb, width in HGI.D_MDESC_FIELDS}
        inv = {b: a for a, b in HGI.FMT.items()}
        return cls(space=HGI.SPACE[v["space"]], fmt=inv[v["fmt"]], base=v["base"], n=v["n"], m=v["m"],
                   stride=_s32(v["stride"]), istride=v["istride"], lstride=_s32(v["lstride"]), dyn_sel=v["dyn_sel"],
                   dyn_mul=v["dyn_mul"], n_sel=v["n_sel"], l1stride=_s32(v["l1stride"]), ibcast=v["ibcast"],
                   indexed=v["indexed"])


def _s32(x):
    return x - (1 << 32) if x & (1 << 31) else x


SUT_LAYOUT = HGI.D_SUT_LAYOUT


def sut_encode(t: dict) -> int:
    w = 0
    for name, lsb, width in SUT_LAYOUT:
        x = int(t.get(name, 0))
        if not 0 <= x < (1 << width):
            raise ValueError(f"SUT {name}={x} outside {width} bits")
        w |= x << lsb
    return w


def sut_decode(w: int) -> dict:
    return {name: (w >> lsb) & ((1 << width) - 1) for name, lsb, width in SUT_LAYOUT}


@dataclasses.dataclass
class Rec:
    unit: str
    op: str
    wait: int = 0              # drain mask (bit = unit code)
    pred: str = "ALWAYS"
    slot: int = 0
    param: int = 0
    imm_a: int = 0
    imm_b: int = 0
    sut: dict | None = None
    desc: dict = dataclasses.field(default_factory=dict)    # A, B, C, D, O, R, I
    tag: str = ""              # not encoded (trace only)
    family: str = ""           # not encoded

    @property
    def opnd(self):
        return sum(1 << i for i, k in enumerate(OPND) if k in self.desc)

    def descs_in_order(self):
        return [(k, self.desc[k]) for k in OPND if k in self.desc]

    def encode(self) -> bytes:
        bad = set(self.desc) - set(OPND)
        if bad:
            raise ValueError(f"unknown operand slots {bad}")
        v = dict(unit=UNITS.index(self.unit), op=OPS[self.unit].index(self.op), wait=self.wait,
                 pred=HGI.PRED.index(self.pred), opnd=self.opnd, tmpl=int(self.sut is not None), slot=self.slot,
                 param=self.param, imm_a=self.imm_a & 0xFFFFFFFF, imm_b=self.imm_b & 0xFFFFFFFF)
        h = 0
        for name, lsb, width in HGI.D_UOP_FIELDS:
            x = int(v[name])
            if not 0 <= x < (1 << width):
                raise ValueError(f"UOP {name}={x} outside {width} bits")
            h |= x << lsb
        out = h.to_bytes(16, "little")
        if self.sut is not None:
            out += sut_encode(self.sut).to_bytes(32, "little")
        for _, d in self.descs_in_order():
            out += d.encode().to_bytes(32, "little")
        return out


def decode_one(buf: bytes, off: int):
    h = int.from_bytes(buf[off:off + 16], "little")
    v = {name: (h >> lsb) & ((1 << width) - 1) for name, lsb, width in HGI.D_UOP_FIELDS}
    unit = UNITS[v["unit"]]
    if unit not in OPS:
        raise ValueError(f"reserved unit code {v['unit']}")
    ops = OPS[unit]
    if v["op"] >= len(ops):
        raise ValueError(f"illegal op {v['op']} for {unit}")
    r = Rec(unit=unit, op=ops[v["op"]], wait=v["wait"], pred=HGI.PRED[v["pred"]], slot=v["slot"], param=v["param"],
            imm_a=v["imm_a"], imm_b=v["imm_b"])
    p = off + 16
    if v["tmpl"]:
        r.sut = sut_decode(int.from_bytes(buf[p:p + 32], "little"))
        p += 32
    for i, k in enumerate(OPND):
        if v["opnd"] >> i & 1:
            r.desc[k] = MDesc.decode(int.from_bytes(buf[p:p + 32], "little"))
            p += 32
    return r, p


def encode_program(recs) -> bytes:
    return b"".join(r.encode() for r in recs)


def decode_program(buf: bytes):
    out, off = [], 0
    while off < len(buf):
        r, off = decode_one(buf, off)
        out.append(r)
    return out


def rec_bytes(r: Rec) -> int:
    return 16 + (32 if r.sut is not None else 0) + 32 * len(r.descs_in_order())


def wait_mask(*units):
    m = 0
    for u in units:
        m |= 1 << UNITS.index(u)
    return m


def bcast(d: MDesc) -> MDesc:
    d.ibcast = 1
    return d
