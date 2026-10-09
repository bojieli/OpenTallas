"""HGI-1 v0.9 program records (docs/HBM_GENERIC_INTERFACE.md section 3.2): encode / decode, bit for bit.

Every field position comes from tools/hbm_generic_iface.py (UOP_FIELDS, MDESC_FIELDS, SUT_FIELDS, OPS, UNITS, PRED,
SPACE, DYN, FMT), so a spec change shows up here without edits.  A record is a 128-bit header (UOP), an optional
256-bit SU template (SUT), then one 256-bit memory descriptor (MDESC) per set `opnd` bit in A, B, C, O order;
all little-endian.

PROVISIONAL READINGS of v0.9 (reported to hbm-iface; see SPEC_GAPS):
  * SUT bit positions: the spec lists SUT fields without lsbs; they are packed from bit 0 in list order (142 bits).
  * SU.VOP extra descriptors: su1 reads four sources (a, b, c, d) and writes elements (o) AND a reduction (r), but
    `opnd` has four bits (A, B, C, O).  SU.VOP `param` bit 0 = a D descriptor follows, bit 1 = an R descriptor
    follows (after O, in D, R order).  `param` is "—" for SU.VOP in v0.9, so this reading is an amendment.
  * Broadcast: `istride` 0 means 1 (spec), so a per-row scalar broadcast (softmax max, normaliser, row scale of an
    embedding row) cannot be expressed.  `istride` = 0xFFFF is read as inner stride 0.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hbm_generic_iface as HGI  # noqa: E402

OPND = ("A", "B", "C", "O")
# PROVISIONAL op codes the DS native lowering needs and v0.9 lacks (appended after the spec's ops; gaps G8, G10)
PROVISIONAL_OPS = {"FUSED": ["QDQ_FP8"], "COLL": ["GROUP_REDUCE_MCAST"]}
OPS_X = {u: list(v) + PROVISIONAL_OPS.get(u, []) for u, v in HGI.OPS.items()}
EXTRA = ("D", "R")                 # SU.VOP param bits 0, 1 (provisional)
ISTRIDE_BCAST = 0xFFFF

SPEC_GAPS = [
    dict(id="G1", item="SUT field bit positions are not given (spec.json sut.fields has widths only)",
         reading="packed from bit 0 in list order"),
    dict(id="G2", item="SU.VOP needs a D source (qm: RoPE sin) and an R destination (reductions) but opnd has A,B,C,O",
         reading="SU.VOP param bit0 = D descriptor follows, bit1 = R descriptor follows (after O)"),
    dict(id="G3", item="no broadcast: istride 0 means 1, so per-row scalars (softmax max / normaliser, embedding scale) "
         "cannot be addressed", reading="istride 0xFFFF = inner stride 0"),
    dict(id="G4", item="softmax: section 3.7 binds softmax + pv_normalize to a FUSED softmax but FUSED has no SOFTMAX op",
         reading="bound to the SU 3-pass fallback (SU.VOP templates), whose order is the quality harness's"),
    dict(id="G5", item="norm_out_bf16 is static, but Qwen issues ROW_NORM for both prenorm (BF16 out at the matvec "
         "boundary) and QK-norm (FP32 out: RoPE runs in FP32 and q rounds to BF16 only after RoPE)",
         reading="ROW_NORM output format = the O descriptor's fmt (FP32 or BF16) per op"),
    dict(id="G8", item="DS needs the FP8 act_quant QDQ (UE8M0 block-32; hfd_quant) as a unit op: the window row and "
         "the indexer / KV rows are quantised-dequantised; SU cannot form ceil(log2(amax)) exactly",
         reading="provisional FUSED.QDQ_FP8 (op 3)"),
    dict(id="G9", item="COLL.ALL_GATHER segment rule: DS even splits (rank r owns [r*n//G, (r+1)*n//G)) are not "
         "expressible as base + RANK*dyn_mul when G does not divide n", reading="the collective applies the even-split "
         "rule over A.n"),
    dict(id="G10", item="DS o-group reduce: 8-die sub-group owner-tree reduce + multicast to all 96, BF16 out; "
         "coll_group_size is static (96)", reading="provisional COLL.GROUP_REDUCE_MCAST, param = sub-group size"),
    dict(id="C3b", item="indexed descriptors (expert weight base, route-weight gather by router ids)",
         reading="dyn_sel 31: base += VM[lstride] * dyn_mul (one dispatcher VM read; no L*lstride on that record)"),
    dict(id="G6", item="sfx_multipass 'fixed 640-row chunks with carry-in': a scalar carry changes the denominator's "
         "order vs the csum8 tree of the golden / quality run", reading="the carry must be the streaming binary-counter "
         "state (exactly the csum8 tree); the SU fallback is bound until the fused unit is shown equal"),
]


@dataclasses.dataclass
class MDesc:
    space: str = "VM"          # HBM | VM | STREAM | NONE
    fmt: str = "FP32"
    base: int = 0
    n: int = 1
    m: int = 1
    stride: int = 0
    istride: int = 0           # 0 = 1; ISTRIDE_BCAST = 0
    lstride: int = 0
    dyn_sel: int = 0
    dyn_mul: int = 0
    n_sel: int = 0

    def encode(self) -> int:
        v = dict(space=HGI.SPACE.index(self.space), fmt=HGI.FMT[self.fmt], base=self.base, n=self.n, m=self.m,
                 stride=self.stride & 0xFFFFFFFF, istride=self.istride, lstride=self.lstride & 0xFFFFFFFF,
                 dyn_sel=self.dyn_sel, dyn_mul=self.dyn_mul, n_sel=self.n_sel)
        w = 0
        for name, lsb, width in HGI.MDESC_FIELDS:
            x = int(v[name])
            if not 0 <= x < (1 << width):
                raise ValueError(f"MDESC {name}={x} outside {width} bits")
            w |= x << lsb
        return w

    @classmethod
    def decode(cls, w: int):
        v = {name: (w >> lsb) & ((1 << width) - 1) for name, lsb, width in HGI.MDESC_FIELDS}
        inv = {b: a for a, b in HGI.FMT.items()}
        return cls(space=HGI.SPACE[v["space"]], fmt=inv[v["fmt"]], base=v["base"], n=v["n"], m=v["m"],
                   stride=_s32(v["stride"]), istride=v["istride"], lstride=_s32(v["lstride"]), dyn_sel=v["dyn_sel"],
                   dyn_mul=v["dyn_mul"], n_sel=v["n_sel"])


def _s32(x):
    return x - (1 << 32) if x & (1 << 31) else x


SUT_LAYOUT = []
_o = 0
for _n, _w in HGI.SUT_FIELDS:
    SUT_LAYOUT.append((_n, _o, _w))
    _o += _w
SUT_BITS = _o
assert SUT_BITS <= 256


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
    wait: int = 0              # 12-bit unit drain mask (bit = HGI.UNITS index)
    pred: str = "ALWAYS"
    slot: int = 0
    param: int = 0
    imm_a: int = 0
    imm_b: int = 0
    sut: dict | None = None
    desc: dict = dataclasses.field(default_factory=dict)    # A, B, C, O (+ D, R for SU.VOP)
    tag: str = ""              # not encoded: the compiler's name of the op (trace only)
    family: str = ""           # not encoded: the Qwen / DS family the record belongs to

    @property
    def opnd(self):
        return sum(1 << i for i, k in enumerate(OPND) if k in self.desc)

    def descs_in_order(self):
        out = [(k, self.desc[k]) for k in OPND if k in self.desc]
        if self.unit == "SU":
            out += [(k, self.desc[k]) for k in EXTRA if k in self.desc]
        return out

    def encode(self) -> bytes:
        if self.unit == "SU":
            extra = sum(1 << i for i, k in enumerate(EXTRA) if k in self.desc)
            if self.param & ~0x3:
                raise ValueError("SU.VOP param holds only the D / R presence bits")
            self.param = extra
        elif any(k in self.desc for k in EXTRA):
            raise ValueError("D / R descriptors exist only on SU.VOP")
        v = dict(unit=HGI.UNITS.index(self.unit), op=OPS_X[self.unit].index(self.op), wait=self.wait,
                 pred=HGI.PRED.index(self.pred), opnd=self.opnd, tmpl=int(self.sut is not None), slot=self.slot,
                 param=self.param & 0xFFFFFFFF, imm_a=self.imm_a & 0xFFFFFFFF, imm_b=self.imm_b & 0xFFFFFFFF)
        h = 0
        for name, lsb, width in HGI.UOP_FIELDS:
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
    v = {name: (h >> lsb) & ((1 << width) - 1) for name, lsb, width in HGI.UOP_FIELDS}
    unit = HGI.UNITS[v["unit"]]
    ops = OPS_X[unit]
    if v["op"] >= len(ops):
        raise ValueError(f"illegal op {v['op']} for {unit}")
    r = Rec(unit=unit, op=ops[v["op"]], wait=v["wait"], pred=HGI.PRED[v["pred"]], slot=v["slot"], param=v["param"],
            imm_a=v["imm_a"], imm_b=v["imm_b"])
    p = off + 16
    if v["tmpl"]:
        r.sut = sut_decode(int.from_bytes(buf[p:p + 32], "little"))
        p += 32
    keys = [k for i, k in enumerate(OPND) if v["opnd"] >> i & 1]
    if unit == "SU":
        keys += [k for i, k in enumerate(EXTRA) if v["param"] >> i & 1]
    for k in keys:
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
        m |= 1 << HGI.UNITS.index(u)
    return m
