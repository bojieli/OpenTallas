"""Program interface of the r25 HBM die, as the simulator and the compiler see it (stream hbm-sim, 2026-10-09).

PROVISIONAL.  The binding interface is being written by stream hbm-iface (docs/HBM_GENERIC_INTERFACE.md).  Until its
v0.9 lands, this module fixes only what does not depend on the exact encoding:

  * a program is an ordered list of COMMANDS, issued by the die's command processor (CP) in order;
  * every command names ONE unit, one op FAMILY of that unit, its MODE fields, the ranks (dies) that run it, its
    operand references (`buf` or `buf[lo:hi]`, element offsets into a die's vector / staging memory), and the
    family's arguments (weight descriptors, sizes, positions);
  * a MODEL DESCRIPTOR (dimensions, layer kinds, TP, weight placement) travels with the program.

The encoding is deliberately the canonical JSON of each command (`encode` / `decode` round-trip, checked by the
tests).  When the spec lands, `encode_words` / `decode_words` replace it with the spec's word format; nothing above
this layer (compiler, simulator) depends on the bytes.

Units of the r25 die (results/arch/qwen_on_r25_20261008/PLAN.md section 1, tools/hbm_accel_die_fp.py R25):
  CP      hfd_cmdproc_n/s           in-order launch, doorbell / completion (token 18 b, position 20 b)
  SM      smh_front + 32 SM / die   matvec: weight decode modes (BF16, FP8 / FP4 block dot, INT8 unpack), output dtype
  SU      hfd_su (N1024 / M256)     stream unit: vector programs (vec-campaign words), reductions, scalar side pipe
  SFU     hfd_sfu                   SFU-lane element functions (exp, silu, sqrt(softplus), SwiGLU)
  NORM    norm engine (DS)          fused hc_pre + RMSNorm (D5120, HC4); DS only
  HC      hfd_hc                    hyper-connection mixes / Sinkhorn / hc_post (DS)
  ATT     attention tiles           q.k scores, p.v, window + selection attention (DS fused mode)
  IDX     indexer                   index q prep, key scan (DS)
  SEL     select units              local top-k, router top-6, candidate selection (DS)
  ARGMAX  argmax_m                  per-die argmax (lowest index on ties)
  HBM     svc stream service        weight / KV / table streams, posted KV writes, fences
  COLL    TU endpoint               all-gather, owner-tree all-reduce, top-k merge, KV row gather
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from typing import Any

UNITS = ("CP", "SM", "SU", "SFU", "NORM", "HC", "ATT", "IDX", "SEL", "ARGMAX", "HBM", "COLL")

# Op families per unit and the mode fields each family accepts (name -> allowed values).  A command whose mode is
# outside this table is refused at encode time: the simulator never runs a mode the hardware does not have.
FAMILIES: dict[str, dict[str, dict[str, tuple]]] = {
    "SM": {
        # y[rows] = W[rows, :] . x ; weight decode and accumulation per mode
        "MATVEC": dict(wfmt=("bf16", "fp8_bd", "fp4_bd", "int8"),       # weight decode (fmt 0 / 1 / 2 / 3)
                       act=("bf16", "fp8_k32"),                          # activation path
                       acc=("csum8", "split"),                           # chunk-8 csum tree / engine K-split order
                       ksplit=("none", "group1024", "head512"),          # DS grouped / K-split wo_a
                       out=("fp32", "bf16"),
                       slot=("none", "expert")),                         # weight base from the route register
    },
    "SU": {
        "PROG": dict(abi=("vec_c12",)),                                  # a list of vec-campaign words
        "ROW_SCALE": dict(out=("fp32", "bf16")),                         # y = t * s_row (one RNE multiply)
        "RESIDUAL": dict(out=("fp32",)),                                 # x = x + y
        "EMBED_DEQ": dict(out=("fp32",)),                                # row = code * scale
        "PV_NORM": dict(div=("ieee",)),                                  # o = pv / Z
        "ARGMAX_MERGE": dict(ties=("lowest_index",)),                    # global argmax over die winners
        "DS": dict(fn=("q_norm_kv_row", "q_rope", "moe_sum", "compressor", "engram_mix")),
    },
    "SFU": {"DS": dict(fn=("router_act", "swiglu"))},
    "NORM": {"DS": dict(fn=("hc_pre_norm", "final_norm"))},
    "HC": {"DS": dict(fn=("hc_mixes", "hc_post"))},
    "ATT": {
        "QK": dict(acc=("csum8",), scale=("post",)),                     # s = (q . k) * scale
        "PV": dict(acc=("csum8_p2",)),                                   # pv = sum_p bf16(e_p) v_p
        "DS": dict(fn=("attend",)),
    },
    "IDX": {"DS": dict(fn=("index_q", "index_scores", "cand_mask"))},
    "SEL": {"DS": dict(fn=("topk_local", "route", "cand_local", "cand_apply"))},
    "ARGMAX": {"LOCAL": dict(ties=("lowest_index",)), "DS": dict(fn=("argmax_local",))},
    "HBM": {
        "EXPERT_FETCH": dict(),
        "ENGRAM_ROWS": dict(),
        "KV_APPEND": dict(fmt=("fp8",)),
        "KV_FENCE": dict(),
        "EMBED_ROW": dict(),
    },
    "COLL": {
        "GATHER": dict(),
        "REDUCE": dict(tree=("pairwise",), round=("none", "bf16")),
        "MERGE": dict(what=("sel", "cand", "argmax")),
        "KV_GATHER": dict(),
    },
}

_REF = re.compile(r"^([A-Za-z_][\w.]*)(?:\[(\d+):(\d+)\])?$")


def parse_ref(ref: str):
    """'buf' -> (buf, None, None); 'buf[lo:hi]' -> (buf, lo, hi)."""
    m = _REF.match(ref)
    if not m:
        raise ValueError(f"bad operand reference {ref!r}")
    b, lo, hi = m.groups()
    return b, (int(lo) if lo is not None else None), (int(hi) if hi is not None else None)


@dataclasses.dataclass
class Cmd:
    unit: str
    op: str
    mode: dict
    ranks: Any                      # "all" | "heads" | [rank, ...]
    src: list
    dst: list
    args: dict
    layer: Any = None
    tag: str = ""
    id: int = -1

    def check(self):
        if self.unit not in UNITS:
            raise ValueError(f"unknown unit {self.unit}")
        fam = FAMILIES.get(self.unit, {}).get(self.op)
        if fam is None:
            raise ValueError(f"{self.unit} has no op family {self.op}")
        for k, v in self.mode.items():
            if k not in fam:
                raise ValueError(f"{self.unit}.{self.op}: unknown mode field {k}")
            if v not in fam[k]:
                raise ValueError(f"{self.unit}.{self.op}: mode {k}={v!r} not in {fam[k]}")
        for r in list(self.src) + list(self.dst):
            parse_ref(r)
        return self

    def to_json(self) -> dict:
        return dict(id=self.id, unit=self.unit, op=self.op, mode=dict(sorted(self.mode.items())), ranks=self.ranks,
                    src=list(self.src), dst=list(self.dst), args=self.args, layer=self.layer, tag=self.tag)


@dataclasses.dataclass
class Program:
    model: dict                     # the model descriptor
    cmds: list                      # [Cmd]
    meta: dict = dataclasses.field(default_factory=dict)

    def add(self, **kw) -> Cmd:
        c = Cmd(**kw).check()
        c.id = len(self.cmds)
        self.cmds.append(c)
        return c

    def to_json(self) -> dict:
        return dict(schema=SCHEMA, model=self.model, meta=self.meta, cmds=[c.to_json() for c in self.cmds])


SCHEMA = "opentallas.hbm_sim.program.v0"


def _canon(x):
    return json.loads(json.dumps(x, sort_keys=True, default=_default))


def _default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


def encode(prog: Program) -> bytes:
    """Canonical byte form of a program (JSON, sorted keys).  Placeholder for the spec's word encoding."""
    return json.dumps(_canon(prog.to_json()), sort_keys=True, separators=(",", ":")).encode()


def decode(blob: bytes) -> Program:
    d = json.loads(blob)
    if d.get("schema") != SCHEMA:
        raise ValueError(f"schema {d.get('schema')}")
    p = Program(model=d["model"], cmds=[], meta=d.get("meta", {}))
    for c in d["cmds"]:
        cid = c.pop("id")
        cmd = Cmd(**c).check()
        if cid != len(p.cmds):
            raise ValueError("command ids must be dense and ordered")
        cmd.id = cid
        p.cmds.append(cmd)
    return p


def digest(prog: Program) -> str:
    return hashlib.sha256(encode(prog)).hexdigest()


def family_counts(prog: Program) -> dict:
    out: dict[str, int] = {}
    for c in prog.cmds:
        k = f"{c.unit}.{c.op}" + (f".{c.mode['fn']}" if "fn" in c.mode else "")
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


# ----------------------------------------------------------------------------------------------------------------
# the op-level TP-96 executor's die memory (named buffers with written masks) and dispatcher
# ----------------------------------------------------------------------------------------------------------------
import numpy as np  # noqa: E402


class Defect(Exception):
    """A program / dataflow defect (unwritten read, ownership violation, unsupported mode)."""


class Die:
    def __init__(self, r):
        self.r = r
        self.mem: dict = {}
        self.ok: dict = {}

    def alloc(self, name, n, dtype=np.float32):
        self.mem[name] = np.zeros(n, dtype=dtype)
        self.ok[name] = np.zeros(n, dtype=bool)

    def put(self, name, vals, lo=0, n=None):
        vals = np.asarray(vals).reshape(-1)
        if name not in self.mem or (n is not None and self.mem[name].size != n):
            self.alloc(name, n if n is not None else vals.size, vals.dtype if vals.dtype != np.float64 else np.float64)
        self.mem[name][lo:lo + vals.size] = vals
        self.ok[name][lo:lo + vals.size] = True

    def get(self, name, lo=0, hi=None):
        if name not in self.mem:
            raise Defect(f"die {self.r}: read of buffer {name} never written")
        hi = self.mem[name].size if hi is None else hi
        if not self.ok[name][lo:hi].all():
            raise Defect(f"die {self.r}: read of unwritten elements of {name}[{lo}:{hi}]")
        return self.mem[name][lo:hi]

    def ref(self, ref):
        b, lo, hi = parse_ref(ref)
        return self.get(b, lo or 0, hi)

    def clear(self, keep=()):
        for k in [k for k in self.mem if k not in keep]:
            del self.mem[k], self.ok[k]


class OpMachine:
    def __init__(self, n_dies, handlers, head_dies=None, die_cls=Die):
        self.dies = [die_cls(r) for r in range(n_dies)]
        self.handlers = handlers
        self.head_dies = head_dies if head_dies is not None else n_dies

    def ranks_of(self, spec):
        if spec == "all":
            return self.dies
        if spec == "heads":
            return self.dies[:self.head_dies]
        return [self.dies[r] for r in spec]

    def run(self, cmds):
        for c in cmds:
            h = self.handlers.get((c.unit, c.op))
            if h is None:
                raise Defect(f"cmd {c.id}: no handler for {c.unit}.{c.op}")
            h(self, c)
