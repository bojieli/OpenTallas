#!/usr/bin/env python3
"""Bottom-up, per-operator critical-path latency of ONE decode token on the ROM machine.

The analytical model (src/opentallas/roofline.py) prices a token as a bandwidth
sweep plus a flat per-layer floor (`layer_fixed_latency`: 4-5 dependent array
passes x ~36 ns + barrier + sequencer) plus two all-reduces per layer.  This
tool instead builds the operator dependency graph of every layer from the model
config and walks its longest path:

* **Graph.**  One DAG per token: every operator of every layer, with its real
  data dependencies.  Parallel branches take the max, serial ones add.  For
  DeepSeek-V4.1-Flash the operators are those of the golden specification
  (tools/hdc_golden_v41.py, docs/HDC_DEEPSEEK_V41_OPERATOR_INVENTORY.md):
  hyper-connection mixes with the 20-iteration Sinkhorn (a side branch the
  sublayer runs alongside -- the collapse consumes the PREVIOUS sublayer's pre
  mix, so only hc_post waits for it), low-rank q/kv chains with their norms,
  RoPE, the compressor and indexer on KV/index-source layers, top-k selection
  (source vs reuse layers, candidate counts at the context), sparse attention
  with sink, grouped o projection, router (sqrt-softplus, bias, top-6 of 384,
  weight normalise), experts and shared expert, combine, Engram on layers 1
  and 14, lm_head + argmax.
* **Pricing.**  Every node is priced with MEASURED depths of our own RTL:
  tools/hdc_timing.py `K` (sequencer gap, matrix-engine latency and tree, the
  stream unit's per-class depths, reducer tail) and the V4.1 units' pipeline
  depths (rtl/hdc/v41/*.sv and their campaigns), at the slowest routed clock
  among the units the token path uses (results/physical_abi3/asap7/hdc/).
  Lane counts per die come from the analytical design's compute area divided
  by our routed lane areas.  Matrix-vector occupancy is the analytical design's
  own sweep (points.json component times) apportioned by bytes or MACs; that is
  the only analytical input on the compute side.
* **Communication.**  Each collective the weight split requires is a node
  where the data dependency needs the full vector, priced per event by a
  `Fabric` (physical topology) and a reduction algorithm (logical topology):
  latency = traversals x hop, bytes = the real payload (FP32 partials, the
  4-copy hyper-connection residual on stage hops, forwarded compressed-KV rows
  and selections, all x users per stage) over the link it crosses.  Link
  constants: configs/hardware/technology.json `links`.
* **Control.**  seq_gap per issued instruction, plus idle_reg on a barrier;
  chaining (the HDC `chase`) lets streamable consumers overlap their producer.

`build()` validates the machinery on Taalas HC1 (Llama-3.1-8B, published
16,960 tok/s, no fitted constant), then prices Qwen3-8B on the same die and
DeepSeek-V4.1-Flash on the x188 array and the x12 wafer, and sweeps physical
topology x reduction algorithm x group size x dies per package at iso-area.
Output: results/roofline/critical_path/decode_critical_path.json.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import hdc_isa as I  # noqa: E402
import hdc_timing  # noqa: E402

SCHEMA = "opentallas.decode-critical-path.v1"
OUT = ROOT / "results/roofline/critical_path/decode_critical_path.json"
TECH = ROOT / "configs/hardware/technology.json"
V41_CONFIG = ROOT / "configs/models/candidates/deepseek-v4.1-flash.json"
LLAMA = ROOT / "configs/models/anchors/llama-3.1-8b.json"
QWEN = ROOT / "configs/models/qwen3-8b.json"
V41_POINTS = ROOT / "results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/points.json"
V41_ANALYTICAL = ROOT / "results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json"
ARRAY_DESIGN = "DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188"
WAFER_DESIGN = "DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12"
PHYS = ROOT / "results/physical_abi3/asap7/hdc"

# -- measured RTL constants -------------------------------------------------------------------------------
K = hdc_timing.K
SU = {name: K["su_depth"][getattr(I, "SFU_" + name)] for name in ("NONE", "EXP", "RECIP", "RSQRT", "SIGM")}
SU_BASE = SU["NONE"]            # stream address-to-write with no SFU (29); every SU class = base + unit depth
FADD = 5                        # rtl/hdc/ot_hdc_fpu.sv LATENCY (fadd / fmul)
IL = I.INTERLEAVE               # 8 outputs in flight per matrix-engine lane
V41 = dict(fdiv=31,             # rtl/hdc/v41/ot_hdc_fdiv.sv DEPTH, II 1
           fsqrt=31,            # rtl/hdc/v41/ot_hdc_fsqrt.sv DEPTH, II 1
           softplus=259,        # rtl/hdc/v41/ot_hdc_softplus.sv (exp, fdiv, Horner, fsqrt), II 1
           blockdot=15,         # rtl/hdc/v41/ot_hdc_blockdot.sv last block -> ov; campaign latency_cycles 15
           actquant=13,         # rtl/hdc/v41/ot_hdc_actquant.sv; campaign 13; one 32-block per cycle
           fp4qdq=8,            # rtl/hdc/v41/ot_hdc_fp4qdq.sv; campaign 8
           engram_hash=12)      # rtl/hdc/v41/ot_hdc_engram_hash.sv LATENCY
RTL_SOURCES = {
    "seq_gap 5 / me_lat 16 / me_tree 5 per level / su_depth / red_tail 32 / idle_reg 2":
        "tools/hdc_timing.py K (fitted to the Verilator issue trace: 32,191 model vs 32,196 RTL cycles)",
    "fadd/fmul latency 5": "rtl/hdc/ot_hdc_fpu.sv LATENCY",
    "select: K+2 cycles (rank order) or 2K+2 (ascending index) after the last element, 1 element/cycle in":
        "rtl/hdc/v41/ot_hdc_select.sv header; results/rtl/hdc_v41_select_campaign.json latency_cycles",
    "fdiv 31, fsqrt 31, softplus 259 (all II 1)": "rtl/hdc/v41/ot_hdc_fdiv.sv, ot_hdc_fsqrt.sv, ot_hdc_softplus.sv",
    "blockdot 15, actquant 13, fp4qdq 8, engram_hash 12":
        "rtl/hdc/v41/*.sv; results/rtl/hdc_v41_blockdot_campaign.json, hdc_v41_engram_campaign.json",
    "ME lane area 1,051 um2/MAC (BF16, 64-lane ot_hdc_matvec incl. sequencing, not closed)":
        "results/physical_abi3/asap7/hdc/ot_hdc_matvec/physical.json design.area_um2 / 64",
    "SU lane area 42,443 um2 per element/cycle (ot_hdc_stream incl. SFU, not closed)":
        "results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json design.area_um2",
}


def select_latency(k, ascending_index):
    """ot_hdc_select: cycles from the segment's last accepted element to the first output."""
    return k + 2 + (k if ascending_index else 0)


CLOCK_BLOCKS = ["ot_hdc_matvec", "ot_hdc_stream", "v41/ot_hdc_softplus", "v41/ot_hdc_select_k512",
                "v41/ot_hdc_blockdot", "v41/ot_hdc_actquant", "v41/ot_hdc_fp4qdq"]


def physical(block):
    return json.loads((PHYS / block / "physical.json").read_text())["design"]


def routed_clock():
    rows = [dict(block=b, fmax_hz=physical(b)["fmax_hz"], closed=physical(b)["closed"]) for b in CLOCK_BLOCKS]
    return min(r["fmax_hz"] for r in rows), rows


def lane_areas_um2():
    return dict(me_mac=physical("ot_hdc_matvec")["area_um2"] / (I.W_LANES * 4),
                su_lane=physical("ot_hdc_stream")["area_um2"])


# -- parameters ------------------------------------------------------------------------------------------
@dataclass
class Params:
    clock_hz: float = 0.0            # 0: the slowest routed clock among CLOCK_BLOCKS
    lanes_from: str = "rtl_area"     # "rtl_area": compute_mm2 / our lane areas; "analytical": compute_ops_s
    su_area_fraction: float = 0.10   # share of the compute area given to stream-unit lanes
    su_width: int = 0                # 0: derived from the area; else elements/cycle per die
    select_units: int = 64           # ot_hdc_select instances per die (first level of a top-k)
    chaining: bool = True            # streamable consumers chase their producer (the HDC `chase`)
    algorithm: str = "best"          # reduction algorithm (see ALGORITHMS) or "best" per collective
    moe: str = "striped"             # "striped" (every expert split across the group) or "expert_parallel"
    hbm_gather_s: float = 100e-9     # ASSUMED random-row HBM read latency (no constant in technology.json)
    index_order_pass: bool = True    # top-k emitted in position order (the golden's topk_lowest_index)
    engram_hops: int = 2             # fabric distance from the Engram table package to layers 1 / 14
    mc_trials: int = 300             # Monte Carlo trials for expert-parallel load imbalance
    fuse: bool = False               # NOT bit-exact: fold RMSNorm's rstd into the next matvec's output and
                                     # use an online (single-pass) softmax; a labelled what-if only
    kv_mode: str = "broadcast"       # "broadcast": each die reads 1/g of the shared KV rows and the group
                                     # all-gathers them; "replicated": every head-split die reads every row
    fdiv_cycles: int = 31            # divider depth (ot_hdc_fdiv); a what-if knob for the Sinkhorn chain
    sinkhorn_step_cycles: int = 0    # 0: one normalisation = 3 sequential fadd + eps fadd + fdiv (derived);
                                     # >0: a what-if for a redesigned (still bit-exact) normalisation step
    sinkhorn: bool = True            # False: the Sinkhorn chain costs nothing (HYPOTHETICAL; isolates fabric)
    seed: int = 0


CATS = ["compute_chain", "weight_sweep", "kv_sweep", "collective_latency", "collective_bytes",
        "pipeline_hops", "control"]
ALGORITHMS = ["two_step", "one_shot", "ring", "rec_doubling", "tree", "centre_mesh"]
DETERMINISM = {
    "two_step": "fixed order: each shard is summed on its owner in rank order, then broadcast (bit-identical replicas)",
    "one_shot": "fixed order: every die sums all partials in rank order (bit-identical replicas)",
    "ring": "fixed order per shard (ring order); deterministic run to run, order rotates by shard",
    "rec_doubling": "fixed pairing per step; IEEE add is commutative so all ranks hold the same bits",
    "tree": "fixed tree: deterministic",
    "centre_mesh": "fixed centre-rooted spanning tree: deterministic",
    "express_tree": "fixed H-tree: deterministic",
    "expert_parallel_combine": "deterministic ONLY if arrivals are buffered and summed in expert-id order; "
                               "summing in arrival order (dynamic destinations) breaks bit-exactness",
}


# -- graph --------------------------------------------------------------------------------------------------
class Graph:
    """A DAG of operators; `solve` is a longest-path walk with per-category attribution."""

    def __init__(self):
        self.nodes = {}

    def add(self, name, deps, *, layer, issue=0.0, issue_cat="compute_chain", depth=0.0,
            depth_cat="compute_chain", ctrl=0.0, stream=False, kind="op", sweep=None, desc="", **extra):
        assert name not in self.nodes, name
        deps = [d for d in deps if d]
        for d in deps:
            assert d in self.nodes, (name, d)
        self.nodes[name] = dict(name=name, deps=deps, layer=layer, issue=issue, issue_cat=issue_cat,
                                depth=depth, depth_cat=depth_cat, ctrl=ctrl, stream=stream, kind=kind,
                                sweep=sweep, desc=desc, **extra)
        return name

    def assign_sweep(self, total_s, basis):
        """Give every matvec its share of the design's sweep time (bytes or MACs basis)."""
        tot = sum(n["sweep"][basis] for n in self.nodes.values() if n["sweep"])
        for n in self.nodes.values():
            if n["sweep"]:
                share = total_s * n["sweep"][basis] / tot * n["sweep"].get("imbalance", 1.0)
                n["sweep"]["share_s"] = share
                n["issue"] = max(share, n["sweep"]["floor_s"])
                n["issue_cat"] = "weight_sweep" if share >= n["sweep"]["floor_s"] else "compute_chain"

    def solve(self, chaining=True):
        fin, start, crit, contrib = {}, {}, {}, {}
        for name, n in self.nodes.items():       # insertion order is topological
            deps = n["deps"]
            if deps:
                c = max(deps, key=fin.__getitem__)
                pf, ps = fin[c], max(start[d] for d in deps)
            else:
                c, pf, ps = None, 0.0, 0.0
            parts = {}
            iss, dep, ctl = n["issue"], n["depth"], n["ctrl"]
            if n["stream"] and chaining and deps:
                s = ps + ctl
                a = s + iss
                if a > pf:
                    ex = a - pf
                    parts[n["issue_cat"]] = min(ex, iss)
                    if ex > iss:
                        parts["control"] = ex - iss
                f = (a if a > pf else pf) + dep
            else:
                s = pf + ctl
                f = s + iss + dep
                parts["control"] = ctl
                parts[n["issue_cat"]] = parts.get(n["issue_cat"], 0.0) + iss
            parts[n["depth_cat"]] = parts.get(n["depth_cat"], 0.0) + dep
            fin[name], start[name], crit[name], contrib[name] = f, s, c, parts
        self.fin, self.crit, self.contrib = fin, crit, contrib
        return fin

    def path(self, sink):
        out, n = [], sink
        while n is not None:
            out.append(n)
            n = self.crit[n]
        return out[::-1]


# -- machine ---------------------------------------------------------------------------------------------------
@dataclass
class Machine:
    name: str
    kind: str                     # single | array | wafer
    group: int                    # tensor group (dies or fields)
    stages: int                   # pipeline stages a token traverses
    substages_per_layer: int      # >1 when a layer does not fit one group
    layers_per_stage: float
    weight_sweep_s: float         # per token, from the analytical point (scaled for the group)
    sweep_basis: str              # "bytes" (weight-bound) or "macs" (compute-bound)
    kv_bw_per_die: float          # bytes/s
    mac_rate_per_die: float       # BF16 MAC/s for attention / index scoring
    su_width: int                 # stream-unit elements/cycle per die
    microbatch: float             # users per stage (microbatch per slot)
    batch: int
    context: int
    slots: float                  # microbatches in flight
    reference: dict = field(default_factory=dict)
    capacity_note: str = ""


def link_consts(tech):
    L = tech["links"]
    return {n: dict(hop=L[n]["hop_latency_s"]["value"], bw=L[n]["bytes_s"]["value"],
                    hop_low=L[n]["hop_latency_s"].get("range_low"), hop_high=L[n]["hop_latency_s"].get("range_high"))
            for n in ("rom_package_ucie", "rom_board_serdes", "on_wafer_n5", "rom_wafer_serdes")}


def mesh_dims(p, shape="square"):
    if p <= 1:
        return 1, 1
    if shape == "rect":
        r = 2 if p <= 28 else 3
    else:
        r = max(1, int(math.isqrt(p)))
    return r, -(-p // r)


def mesh_diameter(p, shape="square"):
    r, c = mesh_dims(p, shape)
    return (r - 1) + (c - 1)


# -- fabrics: physical topology x reduction algorithm -------------------------------------------------------------
@dataclass
class Level:
    """One level of a collective: p nodes, per-hop latency, diameter, and bandwidths."""
    p: int
    alpha: float                  # seconds per traversal (one hop, or one switch crossing)
    D: float                      # diameter in traversals (1 for a switch or a full crossbar)
    Dsum: float                   # sum of partner distances of a recursive-halving schedule
    B_link: float                 # bytes/s of one link
    B_node: float                 # bytes/s a node can inject/receive
    mesh_like: bool               # a centre-rooted reduce applies
    name: str

    def price(self, op, n, algo):
        """(latency_s, bytes_s) for one collective at this level.  n: all_reduce -> one node's partial;
        all_gather -> the full gathered vector."""
        p = self.p
        if p <= 1:
            return 0.0, 0.0
        a, lg = self.alpha, math.ceil(math.log2(p))
        if algo == "centre_mesh" and not self.mesh_like:
            return math.inf, math.inf
        if op == "all_reduce":
            lat = {"two_step": 2 * self.Dsum, "one_shot": self.D, "ring": 2 * (p - 1), "rec_doubling": self.Dsum,
                   "tree": 2 * self.Dsum, "centre_mesh": max(1.0, 1.1 * self.D)}[algo] * a
            byt = {"two_step": 2 * (p - 1) / p * n / self.B_link, "one_shot": (p - 1) * n / self.B_node,
                   "ring": 2 * (p - 1) / p * n / self.B_link, "rec_doubling": lg * n / self.B_link,
                   "tree": 2 * lg * n / self.B_link, "centre_mesh": 2 * n / self.B_link}[algo]
        else:
            lat = {"two_step": self.Dsum, "one_shot": self.D, "ring": p - 1, "rec_doubling": self.Dsum,
                   "tree": 2 * self.Dsum, "centre_mesh": max(1.0, 1.1 * self.D)}[algo] * a
            byt = {"two_step": (p - 1) / p * n / self.B_link, "one_shot": (p - 1) / p * n / self.B_node,
                   "ring": (p - 1) / p * n / self.B_link, "rec_doubling": (p - 1) / p * n / self.B_link,
                   "tree": 2 * n / self.B_link, "centre_mesh": n / self.B_link}[algo]
        return lat, byt


def direct_level(p, alpha, B_link, links_per_node, topo, name, shape="square"):
    """A direct network embedding of p consecutive nodes: chain, ring, mesh, torus, full crossbar."""
    if topo in ("chain", "ring"):
        D = p - 1 if topo == "chain" else max(1, p // 2)
        Dsum = p - 1 if topo == "chain" else max(1, p // 2) + max(0, math.ceil(math.log2(p)) - 1)
    elif topo in ("mesh", "torus"):
        r, c = mesh_dims(p, shape)
        D = (r - 1) + (c - 1)
        if topo == "torus":
            D = r // 2 + c // 2
        Dsum = max(D, math.ceil(math.log2(p)))
    elif topo == "full":
        D, Dsum = 1, math.ceil(math.log2(p))
    else:
        raise ValueError(topo)
    return Level(p=p, alpha=alpha, D=max(1, D), Dsum=max(1, Dsum), B_link=B_link,
                 B_node=B_link * links_per_node, mesh_like=topo != "full", name=name)


BOARD_TOPOLOGIES = ["chain", "ring", "mesh", "torus", "fc2", "fc4", "fc8", "switch"]
SWITCH_LATENCY_S = dict(value=250e-9, range_low=100e-9, range_high=600e-9, grade="assumed",
                        note="one cut-through packet-switch tier port to port; no product for this machine; "
                             "a traversal also pays two SerDes hops (package -> switch -> package)")
SWITCH_RADIX = 64
SERDES_LANES_PER_PACKAGE = 128     # links.rom_board_serdes note: 128 lanes of 112 Gb/s per 4-die package
LANES_PER_PORT = 8                 # an x8 (800G-class) port is the smallest link we split the lanes into


class ArrayFabric:
    """Dies on UCIe inside a package; packages on a board fabric.  Collectives spanning packages are
    hierarchical: in-package, then across packages, then an in-package broadcast."""

    def __init__(self, links, dies_per_package, board, group, algorithm="best", dies=188, switch_s=None):
        self.L, self.dp, self.board, self.g, self.algorithm = links, dies_per_package, board, group, algorithm
        self.packages = math.ceil(dies / dies_per_package)
        b = links["rom_board_serdes"]
        # package SerDes budget scales with the package edge: sqrt(dies / 4) of the 4-die note's 128 lanes
        self.lanes = int(SERDES_LANES_PER_PACKAGE * math.sqrt(dies_per_package / 4))
        self.ports = self.lanes // LANES_PER_PORT
        self.pkg_bw = b["bw"] * self.lanes / SERDES_LANES_PER_PACKAGE
        self.switch_s = SWITCH_LATENCY_S["value"] if switch_s is None else switch_s
        need = {"chain": 2, "ring": 2, "mesh": 4, "torus": 4, "fc2": 1 + 2, "fc4": 3 + 2, "fc8": 7 + 2,
                "switch": 1}[board]
        self.links_per_package = need
        self.refused = None
        if need > self.ports:
            self.refused = f"{board} needs {need} ports, the package edge gives {self.ports} x{LANES_PER_PORT}"
        if board == "switch" and self.packages > SWITCH_RADIX:
            self.refused = f"one switch tier of radix {SWITCH_RADIX} cannot reach {self.packages} packages"
        self.link_bw = self.pkg_bw / need if board != "switch" else self.pkg_bw
        # in-package level
        if dies_per_package <= 4:
            self.pkg_topo = "full"             # every die has a direct link to every other (link note)
        else:
            self.pkg_topo = "mesh"             # 8 dies: a 2 x 4 die mesh on the interposer (assumed)
        self.alpha_board = b["hop"] if board != "switch" else 2 * b["hop"] + self.switch_s

    def label(self):
        return f"array dp{self.dp} {self.board}"

    def _in_pkg(self, p):
        u = self.L["rom_package_ucie"]
        return direct_level(p, u["hop"], u["bw"], min(p - 1, 3) if self.pkg_topo == "full" else 3,
                            self.pkg_topo if p > 1 else "full", "UCIe", shape="rect")

    def _board(self, q):
        if self.board == "switch":
            return Level(p=q, alpha=self.alpha_board, D=1, Dsum=math.ceil(math.log2(max(2, q))),
                         B_link=self.pkg_bw, B_node=self.pkg_bw, mesh_like=False, name="switch")
        if self.board.startswith("fc"):
            k = int(self.board[2:])
            if q <= k:
                lv = direct_level(q, self.alpha_board, self.link_bw, q - 1, "full", self.board)
            else:
                groups = math.ceil(q / k)
                D = (groups - 1) + 2
                lv = Level(p=q, alpha=self.alpha_board, D=D, Dsum=D, B_link=self.link_bw,
                           B_node=self.link_bw * self.links_per_package, mesh_like=True, name=self.board)
            return lv
        topo = self.board if not (self.board in ("ring", "torus") and q < self.packages) else \
            {"ring": "chain", "torus": "mesh"}[self.board]
        return direct_level(q, self.alpha_board, self.link_bw, self.links_per_package, topo, self.board)

    def collective(self, op, n, span, algorithm=None):
        algo = algorithm or self.algorithm
        p = span
        if p <= 1:
            return dict(latency_s=0.0, bytes_s=0.0, algo="none", where="")
        inside = min(p, self.dp)
        q = math.ceil(p / self.dp)
        lv_in, lv_b = self._in_pkg(inside), self._board(q) if q > 1 else None
        best = None
        for a in (ALGORITHMS if algo == "best" else [algo]):
            if q > 1:   # hierarchical: reduce in package, across packages, broadcast in package
                l1, b1 = lv_in.price("all_reduce" if op == "all_reduce" else "all_gather", n, "one_shot")
                l2, b2 = lv_b.price(op, n, a)
                lat, byt = 2 * l1 if op == "all_reduce" else l1, 2 * b1 if op == "all_reduce" else b1
                lat, byt = lat + l2, byt + b2
                where = f"{p} dies = {inside}/package x {q} packages ({self.board}): UCIe + {a}"
            else:
                lat, byt = lv_in.price(op, n, a)
                where = f"{p} dies in one package (UCIe {self.pkg_topo}): {a}"
            if best is None or lat + byt < best[0] + best[1]:
                best = (lat, byt, a, where)
        lat, byt, a, where = best
        return dict(latency_s=lat, bytes_s=byt, algo=a, where=where)

    def combine_a2a(self, v, m, kmax, span):
        """Expert-parallel combine: each host sends its k weighted outputs (v bytes each, m users) to
        every die of the group; priced at the busiest host's egress and every die's ingress."""
        p = span
        q = math.ceil(p / self.dp)
        lv = self._board(q) if q > 1 else self._in_pkg(p)
        D = lv.D + (2 if q > 1 else 0) * (self.L["rom_package_ucie"]["hop"] / lv.alpha)
        byt = max(6 * m * v * (p - 1) / p, kmax * m * v * (p - 1)) / lv.B_node
        return dict(latency_s=D * lv.alpha, bytes_s=byt, algo="expert_parallel_combine",
                    where=f"all-to-all over {p} dies (kmax {kmax:.2f})")

    def hop(self, kind, payload, stage=None):
        u = self.L["rom_package_ucie"]
        g, dp = self.g, self.dp
        if kind in ("stage", "head"):
            q = math.ceil(g / dp)
            # consecutive groups: same package when a package holds several groups
            same_pkg = g < dp and stage is not None and (stage * g) // dp == ((stage - 1) * g) // dp
            if same_pkg:
                return dict(latency_s=u["hop"], bytes_s=payload / u["bw"], link="UCIe")
            trav = 1 if self.board in ("switch",) or self.board.startswith("fc") else \
                (mesh_dims(q)[0] if self.board in ("mesh", "torus") else q) if q > 1 else 1
            fan = u["hop"] * (1 if dp > 1 else 0)
            return dict(latency_s=trav * self.alpha_board + fan, bytes_s=payload / self.link_bw + payload / u["bw"],
                        link=f"board {self.board} x{trav} + UCIe fan-out")
        if kind == "substage":
            same_pkg = g < dp
            if same_pkg:
                return dict(latency_s=u["hop"], bytes_s=payload / u["bw"], link="UCIe")
            return dict(latency_s=self.alpha_board, bytes_s=payload / self.link_bw, link="board")
        if kind == "engram":
            return dict(latency_s=2 * self.alpha_board, bytes_s=payload / self.link_bw, link="board x2")
        if kind == "return":
            n = self.packages
            trav = {"chain": n - 1, "ring": 1, "mesh": mesh_dims(n)[0] - 1 or 1, "torus": 1, "switch": 1}.get(
                self.board, math.ceil(n / int(self.board[2:] or 1)) if self.board.startswith("fc") else 1)
            return dict(latency_s=max(1, trav) * self.alpha_board, bytes_s=payload / self.link_bw,
                        link=f"board x{trav} (token id back to the first stage)")
        raise ValueError(kind)


class WaferFabric:
    """Reticle fields on the on-wafer mesh (125 ns per field crossing, band 75-250 ns); wafers on
    SerDes.  `express_s` > 0 adds a dedicated H-tree reduction network (a labelled sensitivity)."""

    def __init__(self, links, group, shape="square", algorithm="best", hop_s=None, express_s=0.0):
        self.L, self.g, self.shape, self.algorithm = links, group, shape, algorithm
        w = links["on_wafer_n5"]
        self.alpha = w["hop"] if hop_s is None else hop_s
        self.field_bw = w["bw"] / 57 / 4          # one field edge (4 per field)
        self.express_s = express_s
        self.refused = None
        self.board = shape

    def label(self):
        return f"wafer {self.shape}" + (f" + express {self.express_s * 1e9:.0f} ns" if self.express_s else "")

    def _lv(self, p):
        return direct_level(p, self.alpha, self.field_bw, 4, "mesh", "on-wafer", shape=self.shape)

    def collective(self, op, n, span, algorithm=None):
        algo = algorithm or self.algorithm
        if span <= 1:
            return dict(latency_s=0.0, bytes_s=0.0, algo="none", where="")
        lv = self._lv(span)
        best = None
        for a in (ALGORITHMS if algo == "best" else [algo]):
            lat, byt = lv.price(op, n, a)
            if best is None or lat + byt < best[0] + best[1]:
                best = (lat, byt, a)
        if self.express_s:
            lg = math.ceil(math.log2(span))
            lat = (2 if op == "all_reduce" else 1) * lg * self.express_s
            byt = 2 * n / self.field_bw
            if lat + byt < best[0] + best[1]:
                best = (lat, byt, "express_tree")
        r, c = mesh_dims(span, self.shape)
        return dict(latency_s=best[0], bytes_s=best[1], algo=best[2],
                    where=f"{span} fields ({r}x{c} {self.shape}), on-wafer mesh: {best[2]}")

    def combine_a2a(self, v, m, kmax, span):
        lv = self._lv(span)
        byt = max(6 * m * v * (span - 1) / span, kmax * m * v * (span - 1)) / lv.B_node
        return dict(latency_s=lv.D * lv.alpha, bytes_s=byt, algo="expert_parallel_combine",
                    where=f"all-to-all over {span} fields (kmax {kmax:.2f})")

    def hop(self, kind, payload, stage=None):
        s = self.L["rom_wafer_serdes"]
        r, c = mesh_dims(self.g, self.shape)
        gpw = max(1, 57 // self.g)
        if kind in ("stage", "head"):
            if stage is not None and stage // gpw != (stage - 1) // gpw:
                return dict(latency_s=s["hop"] + r * self.alpha, bytes_s=payload / s["bw"],
                            link=f"wafer SerDes + {r} field crossings")
            return dict(latency_s=r * self.alpha, bytes_s=payload / self.field_bw,
                        link=f"{r} field crossings (group width)")
        if kind == "substage":
            return dict(latency_s=r * self.alpha, bytes_s=payload / self.field_bw, link="on-wafer")
        if kind == "engram":
            return dict(latency_s=2 * self.alpha, bytes_s=payload / self.field_bw, link="on-wafer x2")
        if kind == "return":
            return dict(latency_s=s["hop"] + 7 * self.alpha, bytes_s=payload / s["bw"],
                        link="wafer SerDes back to the first wafer (ring) + 7 field crossings")
        raise ValueError(kind)


class SingleFabric:
    board = "none"
    refused = None

    def label(self):
        return "single die"

    def collective(self, op, n, span, algorithm=None):
        return dict(latency_s=0.0, bytes_s=0.0, algo="none", where="")

    def hop(self, kind, payload, stage=None):
        return dict(latency_s=0.0, bytes_s=0.0, link="none")


# -- operator helpers ---------------------------------------------------------------------------------------------
class Ops:
    def __init__(self, g: Graph, p: Params, mach: Machine, clock):
        self.g, self.p, self.m, self.clock = g, p, mach, clock
        self.mb = mach.microbatch
        self.pending_scale = None

    def cyc(self, c):
        return c / self.clock

    def vissue(self, n):
        return self.cyc(math.ceil(n * self.mb / self.m.su_width))

    @property
    def ctrl(self):
        return self.cyc(K["seq_gap"])

    @property
    def bctrl(self):
        return self.cyc(K["seq_gap"] + K["idle_reg"])

    def join(self, name, deps, layer):
        return self.g.add(name, deps, layer=layer, kind="join")

    def ew(self, name, deps, n, depth_cycles, layer, stream=True, desc=""):
        return self.g.add(name, deps, layer=layer, issue=self.vissue(n), depth=self.cyc(depth_cycles),
                          ctrl=self.ctrl if stream else self.bctrl, stream=stream, kind="vector", desc=desc)

    def reduce(self, name, deps, n, layer, segments=1, stream=True, desc=""):
        lanes = max(1, min(self.m.su_width, n // max(1, segments)))
        d = K["red_tail"] + (FADD * math.ceil(math.log2(lanes)) if lanes > 1 else 0)
        return self.g.add(name, deps, layer=layer, issue=self.vissue(n), depth=self.cyc(d),
                          ctrl=self.ctrl if stream else self.bctrl, stream=stream, kind="reduce", desc=desc)

    def rmsnorm(self, pre, deps, n, layer, segments=1, fold=False):
        """fold=True (with Params.fuse): the rstd scale moves to the next matvec's output, so the
        sum of squares and the rsqrt run beside the sweep instead of in front of it (not bit-exact)."""
        a = self.reduce(f"{pre}.sumsq", deps, n, layer, segments, desc=f"sum of squares over {n}")
        b = self.ew(f"{pre}.rsqrt", [a], segments, 2 * FADD + SU["RSQRT"], layer, stream=False,
                    desc="mean, +eps, rsqrt (SU RSQRT)")
        if fold and self.p.fuse:
            self.pending_scale = b
            return self.ew(f"{pre}.wscale", deps, n, SU_BASE + FADD, layer, desc="x * w (rstd folded)")
        return self.ew(f"{pre}.scale", [b], n, SU_BASE + FADD, layer, stream=False, desc="x * rstd * w, BF16")

    def actquant(self, name, deps, n, layer):
        return self.ew(name, deps, n, SU_BASE + V41["actquant"], layer, desc="FP8 activation quantiser")

    def matvec(self, name, deps, layer, *, n_out, k, bytes_, fmt="fp8", imbalance=1.0, desc=""):
        """n_out x k is the FULL matrix (its MACs set the sweep share); the die holds its slice."""
        blocks = math.ceil(k / 32)
        levels = math.ceil(math.log2(max(1, blocks / IL)))
        depth = K["me_lat"] + K["me_tree"] * levels + (V41["blockdot"] if fmt in ("fp8", "fp4") else 0)
        floor = self.cyc(IL * min(IL, blocks) * math.ceil(self.mb))
        sweep = dict(bytes=bytes_, macs=n_out * k * self.mb, floor_s=floor, imbalance=imbalance)
        node = self.g.add(name, deps, layer=layer, depth=self.cyc(depth), ctrl=self.bctrl, kind="matvec",
                          sweep=sweep, desc=desc or f"[{n_out}, {k}] {fmt}")
        if self.pending_scale:
            node = self.g.add(f"{name}.rstd", [node, self.pending_scale], layer=layer, depth=self.cyc(FADD),
                              ctrl=self.ctrl, kind="vector", desc="folded RMSNorm rstd on the outputs")
            self.pending_scale = None
        return node

    def kvscan(self, name, deps, layer, *, kv_bytes, macs, depth_cycles, desc=""):
        t_kv = kv_bytes * self.mb / self.m.kv_bw_per_die
        t_mac = macs * self.mb / self.m.mac_rate_per_die
        cat = "kv_sweep" if t_kv >= t_mac else "compute_chain"
        return self.g.add(name, deps, layer=layer, issue=max(t_kv, t_mac), issue_cat=cat,
                          depth=self.cyc(depth_cycles), ctrl=self.bctrl, kind="kvscan", desc=desc)

    def select_local(self, name, deps, layer, *, n, k, desc=""):
        """First level of a top-k on up to select_units ot_hdc_select units in rank order, then a
        P-way merge of their sorted outputs (k + lg P, streaming).  n per die, per user."""
        best = None
        P = 1
        while P <= self.p.select_units:
            stream = math.ceil(n / P) * self.mb
            tail = select_latency(k, False) + (min(k, n) + math.ceil(math.log2(P)) if P > 1 else min(k, n) - 1)
            if best is None or stream + tail < best[0] + best[1]:
                best = (stream, tail, P)
            P *= 2
        stream, tail, P = best
        return self.g.add(name, deps, layer=layer, issue=self.cyc(stream), depth=self.cyc(tail), ctrl=self.bctrl,
                          kind="select", desc=desc or f"top-{k} of {n} on {P} select units + merge")

    def select_final(self, name, deps, layer, *, k, ways, ascending, desc=""):
        """Merge `ways` sorted lists of k (k + lg ways, streaming) into, if position order is required,
        one ascending-index ot_hdc_select pass (2k+2 latency, k emitted)."""
        merge = (min(k, k) + math.ceil(math.log2(ways))) if ways > 1 else 0
        order = (select_latency(k, True) + k - 1) if ascending else 0
        if ascending and ways <= 1:
            merge = 0
        return self.g.add(name, deps, layer=layer, depth=self.cyc(merge + order), ctrl=self.bctrl, kind="select",
                          desc=desc or f"{ways}-way merge" + (" + ascending-index pass" if ascending else ""))

    def collective(self, name, deps, layer, *, op, payload, desc, span=None):
        span = span or self.m.group
        if span <= 1 or self.m.kind == "single":
            return None
        return self.g.add(name, deps, layer=layer, issue_cat="collective_bytes", depth_cat="collective_latency",
                          ctrl=self.ctrl, kind="collective", desc=desc, op=op, payload=payload, span=span)

    def hop(self, name, deps, layer, *, payload, hop_kind, stage=None, desc):
        if self.m.kind == "single":
            return None
        return self.g.add(name, deps, layer=layer, issue_cat="pipeline_hops", depth_cat="pipeline_hops",
                          ctrl=self.ctrl, kind="hop", desc=desc, hop_kind=hop_kind, payload=payload, stage=stage)


def price_communication(g: Graph, fabric, mb, clock):
    """Set the cost of every collective and hop node for one fabric; returns the event records."""
    events = []
    for n in g.nodes.values():
        if n["kind"] == "collective":
            pay = n["payload"] * mb
            if n["op"] == "combine_a2a":
                r = fabric.combine_a2a(n["v"], mb, n["kmax"], n["span"])
            else:
                r = fabric.collective(n["op"], pay, n["span"])
            red = FADD * math.ceil(math.log2(n["span"])) / clock if n["op"] != "all_gather" else 0.0
            n["issue"], n["depth"] = r["bytes_s"], r["latency_s"] + red
            events.append(dict(name=n["name"], layer=n["layer"], op=n["op"], span=n["span"], payload_bytes=pay,
                               latency_s=n["depth"], bytes_s=n["issue"], algo=r["algo"], where=r["where"],
                               desc=n["desc"]))
        elif n["kind"] == "hop":
            pay = n["payload"] * mb
            r = fabric.hop(n["hop_kind"], pay, n["stage"])
            n["issue"], n["depth"] = r["bytes_s"], r["latency_s"]
            events.append(dict(name=n["name"], layer=n["layer"], op="hop", kind=n["hop_kind"], payload_bytes=pay,
                               latency_s=r["latency_s"], bytes_s=r["bytes_s"], where=r["link"], desc=n["desc"]))
    return events


# -- routed-expert load imbalance ---------------------------------------------------------------------------------
def expert_load(g, experts, topk, mb, basis, trials, seed):
    """(E[max die load] / mean die load, E[max experts on one die]) for g dies holding experts in
    contiguous blocks, `mb` users each choosing top-k (uniform routing: the router trace is synthetic)."""
    if g <= 1:
        return 1.0, float(topk)
    rng = random.Random(seed)
    tokens = max(1, round(mb))
    per = experts / g
    tot = mean = kmax = 0.0
    for _ in range(trials):
        load = [0] * g
        seen = set()
        for _t in range(tokens):
            for e in rng.sample(range(experts), topk):
                if basis == "macs" or e not in seen:
                    seen.add(e)
                    load[min(g - 1, int(e // per))] += 1
        tot += max(load)
        mean += sum(load) / g
        kmax += max(load) / tokens if basis == "macs" else max(load) / tokens
    return (tot / mean if mean else 1.0), kmax / trials


# -- DeepSeek-V4.1-Flash --------------------------------------------------------------------------------------------
def v41_shape():
    d = json.loads(V41_CONFIG.read_text())
    c = dict(d["metadata"]["operator_config"])
    c["num_layers"] = d["num_layers"]
    c["modes"] = {m["layer"]: m for m in d["metadata"]["csa2_layer_modes"]}
    return c


def v41_graph(ops: Ops, c, ctx):
    g, m = ops.g, ops.m
    D, HC, NL = c["hidden_size"], c["hc_mult"], c["num_layers"]
    V, CK = c["vocab_size"], c["candidate_topk_blocks"]
    kv_src, cand_src = c["kv_source_layer_ids"], c["candidate_source_layer_id"]
    G = m.group
    hpd = math.ceil(c["num_attention_heads"] / G)
    fp4 = 0.53125                                # E2M1 + UE8M0 per 32
    if ops.p.moe == "expert_parallel":
        imb, kmax = expert_load(G, c["num_routed_experts"], c["experts_per_token"], ops.mb, m.sweep_basis,
                                ops.p.mc_trials, ops.p.seed)
    else:
        imb, kmax = 1.0, c["experts_per_token"] / max(1, G)
    ops.expert_imbalance, ops.kmax = imb, kmax
    RES = HC * D * 2 + HC * 4                    # 4-copy BF16 residual + pending pre mix (FP32)

    tok = ops.join("token", [], layer=-1)
    emb = g.add("embed", [tok], layer=-1, depth=ops.cyc(SU_BASE) + 2e-9, ctrl=ops.bctrl,
                desc="embedding row read (ROM access) + 4-copy expand")
    # Engram: the row addresses are token ids only, so hash -> gather -> wkv runs from token start
    eng = {}
    for L in c["engram_layer_ids"]:
        h = g.add(f"E{L}.hash", [tok], layer=L, depth=ops.cyc(V41["engram_hash"]), ctrl=ops.bctrl,
                  desc="24 hash columns (multiply, XOR, Barrett modulo)")
        r = g.add(f"E{L}.gather", [h], layer=L, depth=2e-9 + ops.cyc(SU_BASE), ctrl=ops.ctrl,
                  desc="24 table rows from the Engram ROM (row gather port)")
        kv = ops.matvec(f"E{L}.wkv", [r], L, n_out=(HC + 1) * D, k=24 * c["engram_head_dim"],
                        bytes_=(HC + 1) * D * 24 * c["engram_head_dim"], desc="Engram wkv [25600, 6144] FP8")
        kn = ops.rmsnorm(f"E{L}.knorm", [kv], HC * D, L, segments=HC)
        eng[L] = ops.hop(f"E{L}.deliver", [kn], L, payload=(HC + 1) * D * 2, hop_kind="engram",
                         desc="Engram keys + value to the layer's dies (token-addressed: prefetchable)") or kn

    h, pre_ready, sel, prev_stage = emb, emb, {}, 0
    for L in range(NL):
        mode, ratio = c["modes"][L], c["compress_ratios"][L]
        stage = int(L / m.layers_per_stage) if m.stages > 1 else 0
        if stage != prev_stage:
            pay = RES + (1280 + 2048 if L > min(kv_src) else 0) + (CK * 2 if L > cand_src else 0)
            h = ops.hop(f"L{L}.stage_hop", [h], L, payload=pay, hop_kind="stage", stage=stage,
                        desc="stage hop: 4-copy residual + pre mix + forwarded compressed row / selection") or h
            pre_ready, prev_stage = h, stage
        if L in eng:                               # Engram gate on the h side (4 copies in parallel lanes)
            hh = ops.reduce(f"L{L}.eng.hh", [h], HC * D, L, segments=HC)
            dot = ops.reduce(f"L{L}.eng.dot", [h, eng[L]], HC * D, L, segments=HC, desc="(h*w).k per copy")
            s = ops.ew(f"L{L}.eng.gate", [hh, dot], HC, SU["RSQRT"] + 3 * FADD + SU_BASE + V41["fsqrt"] + SU["SIGM"],
                       L, stream=False, desc="rsqrt, scale, signed sqrt, sigmoid")
            h = ops.ew(f"L{L}.eng.add", [s, eng[L]], HC * D, SU_BASE + FADD, L, stream=False, desc="h + gate*value")
        for sub in ("attn", "ffn"):
            P = f"L{L}.{sub}"
            res = h
            # hyper-connection mixes of this sublayer: a side branch, needed only at hc_post
            ss = ops.reduce(f"{P}.hc.sumsq", [res], HC * D, L)
            rs = ops.ew(f"{P}.hc.rsqrt", [ss], 1, 2 * FADD + SU["RSQRT"], L, stream=False)
            fn = ops.matvec(f"{P}.hc.fn", [res], L, n_out=6 * HC, k=HC * D, bytes_=6 * HC * HC * D * 4, fmt="fp32",
                            desc="mixes [24, 20480] FP32 (replicated on every die: 1.97 MB)")
            mx = ops.ew(f"{P}.hc.pre_post", [fn, rs], 6 * HC, FADD * 3 + SU["SIGM"], L, stream=False,
                        desc="mixes*r, scale+base, sigmoid pre/post")
            # 4x4 softmax + 20 Sinkhorn normalisations on a 16-entry unit: each normalisation is a 4-term
            # sequential sum (3 fadd, the golden's seqsum order), +eps, one pipelined divide
            half = ops.p.sinkhorn_step_cycles or (3 * FADD + FADD + ops.p.fdiv_cycles)
            nits = c["hc_sinkhorn_iters"]
            # users interleave through the pipelined unit: a step costs max(depth, users) cycles
            step = max(half, math.ceil(ops.mb))
            sk = g.add(f"{P}.hc.sinkhorn", [mx], layer=L, ctrl=ops.bctrl if ops.p.sinkhorn else 0.0,
                       kind="sinkhorn",
                       depth=ops.cyc(2 + FADD + SU["EXP"] + 2 * nits * step) if ops.p.sinkhorn else 0.0,
                       desc=f"4x4 softmax + {nits} Sinkhorn iterations ({2 * nits} dependent normalisations x "
                            f"{step} cycles)")
            x = ops.ew(f"{P}.hc_pre", [h, pre_ready], HC * D, SU_BASE + 3 * FADD, L,
                       desc="collapse the 4 copies with the pending pre mix")
            x = ops.rmsnorm(f"{P}.norm", [x], D, L, fold=True)
            xq = ops.actquant(f"{P}.quant", [x], D, L)
            if sub == "attn":
                y = v41_attention(ops, c, L, mode, ratio, x, xq, sel, ctx, hpd)
                if mode.get("scans_index"):
                    sel[L] = ops.sel_node
            else:
                y = v41_moe(ops, c, L, x, xq, fp4)
            h = ops.ew(f"{P}.hc_post", [y, sk, res], HC * D, SU_BASE + 4 * FADD, L, stream=False,
                       desc="post*y + comb.res (4-term sums), BF16")
            pre_ready = mx          # attn mix feeds the FFN collapse; the FFN mix feeds the next layer
            if sub == "attn" and m.substages_per_layer > 1:
                for i in range(m.substages_per_layer - 1):
                    h = ops.hop(f"L{L}.substage_hop{i}", [h], L, payload=RES, hop_kind="substage",
                                desc="intra-layer sub-stage hop (the layer is larger than the group)") or h
    h = ops.hop("head.hop", [h], NL, payload=RES, hop_kind="head", stage=m.stages,
                desc="to the lm_head (vocabulary-split) stage") or h
    x = ops.ew("head.hc_pre", [h, pre_ready], HC * D, SU_BASE + 3 * FADD, NL)
    x = ops.rmsnorm("head.norm", [x], D, NL, fold=True)
    lg = ops.matvec("head.lm_head", [x], NL, n_out=V, k=D, bytes_=V * D, fmt="fp8",
                    desc=f"lm_head [{V}, {D}], vocabulary split {G} ways")
    am = ops.reduce("head.argmax", [lg], math.ceil(V / G), NL, desc="local argmax")
    am = ops.collective("head.argmax_merge", [am], NL, op="all_gather", payload=G * 8,
                        desc="best {logit, id} per die") or am
    return ops.hop("token.return", [am], NL, payload=8, hop_kind="return",
                   desc="token id back to the embedding stage") or am


def v41_attention(ops, c, L, mode, ratio, x, xq, sel, ctx, hpd):
    g, m = ops.g, ops.m
    D, H, HD, RD = c["hidden_size"], c["num_attention_heads"], c["head_dim"], c["rope_head_dim"]
    QR, OG, OR = c["q_lora_rank"], c["o_groups"], c["o_lora_rank"]
    IH, IHD, TOPK, WIN = c["index_heads"], c["index_head_dim"], c["index_topk"], c["window_tokens"]
    CB, CK = c["candidate_block_size"], c["candidate_topk_blocks"]
    G = m.group
    P = f"L{L}.attn"
    is_src = L in c["kv_source_layer_ids"]
    scans = bool(mode.get("scans_index"))
    comp = (2 * HD * 4 if ratio == 2 else HD * 2) if is_src else 0
    a_out = QR + HD + IH
    a_bytes = (QR + HD) * D + IH * D * 2 + (2 * HD * D * 4 if (is_src and ratio == 2) else HD * D * 2 if is_src else 0)
    a = ops.matvec(f"{P}.a_proj", [xq], L, n_out=a_out + (2 * HD if is_src else 0), k=D,
                   bytes_=a_bytes, desc="fused wq_a | wkv | indexer weights_proj"
                   + (" | compressor wkv, wgate" if is_src else "") + ", output-split")
    a = ops.collective(f"{P}.a_allgather", [a], L, op="all_gather", payload=a_out * 2 + comp,
                       desc="q_a | kv | index weights (+ compressor) rows") or a
    qn = ops.rmsnorm(f"{P}.q_norm", [a], QR, L, fold=True)
    qq = ops.actquant(f"{P}.q_quant", [qn], QR, L)
    qb = ops.matvec(f"{P}.wq_b", [qq], L, n_out=H * HD + (IH * IHD if scans else 0), k=QR,
                    bytes_=H * HD * QR + (IH * IHD * QR if scans else 0),
                    desc="wq_b (heads split)" + (" | indexer wq_b (replicated)" if scans else ""))
    q = ops.ew(f"{P}.q_rope", [qb], hpd * RD, SU_BASE + 2 * FADD, L, desc="interleaved-pair RoPE on q tails")
    kn = ops.rmsnorm(f"{P}.kv_norm", [a], HD, L)
    kr = ops.ew(f"{P}.kv_rope_qdq", [kn], HD, SU_BASE + 2 * FADD + V41["actquant"], L,
                desc="RoPE + FP8 QDQ, window append")
    rows_dep, n_sel = [q, kr], 0
    if ratio:
        n_comp = ctx // ratio
        n_sel = min(TOPK, n_comp)
        newk = None
        if is_src:                                 # compressor -> new compressed row + index key
            cp = a
            if ratio == 2:
                cp = ops.ew(f"{P}.cmp.pool", [a], 2 * HD, SU["EXP"] + FADD + SU_BASE + ops.p.fdiv_cycles + 2 * FADD, L,
                            stream=False, desc="2-slot softmax per channel + pooling")
            cp = ops.rmsnorm(f"{P}.cmp.norm", [cp], HD, L)
            wk = ops.matvec(f"{P}.cmp.wk", [cp], L, n_out=IHD, k=HD, bytes_=IHD * HD * 2, fmt="bf16",
                            desc="indexer wk [128, 512] BF16")
            kk = ops.rmsnorm(f"{P}.cmp.k_norm", [wk], IHD, L)
            newk = ops.ew(f"{P}.cmp.k_rope_qdq", [kk], IHD, SU_BASE + 2 * FADD + V41["fp4qdq"], L,
                          desc="RoPE + FP4 QDQ -> index key cache")
            rows_dep.append(ops.ew(f"{P}.cmp.row_qdq", [cp], HD, SU_BASE + 2 * FADD + V41["fp4qdq"], L,
                                   desc="RoPE + FP4 (E4M3 scale) QDQ -> compressed KV cache"))
        if scans:
            n_scan = min(n_comp, mode.get("index_scan_entries_cap") or n_comp)
            iq = ops.ew(f"{P}.idx.q", [qb], IH * IHD, SU_BASE + 2 * FADD + V41["fp4qdq"], L,
                        desc="index q RoPE + FP4 QDQ (replicated)")
            per_die = math.ceil(n_scan / G)
            sc = ops.kvscan(f"{P}.idx.score", [iq, a], L, kv_bytes=per_die * 68, macs=per_die * IH * IHD,
                            depth_cycles=K["me_lat"] + K["me_tree"] * 2 + SU_BASE + 3 * FADD + 5 * FADD,
                            desc=f"index scores: {per_die} keys/die x {IH} heads, fused ReLU*w and head sum")
            sdeps = [sc]
            if newk:
                sdeps.append(g.add(f"{P}.idx.newkey", [newk, iq], layer=L, ctrl=ops.bctrl,
                                   depth=ops.cyc(K["me_lat"] + K["me_tree"] * 2 + SU_BASE + 8 * FADD),
                                   desc="score of the just-compressed key"))
            s = ops.select_local(f"{P}.idx.topk_local", sdeps, L, n=per_die, k=TOPK,
                                 desc=f"local top-{TOPK} of {per_die} keys")
            s = ops.collective(f"{P}.idx.topk_merge", [s], L, op="all_gather", payload=G * TOPK * 8,
                               desc=f"{G} x {TOPK} (score, position) candidates") or s
            s = ops.select_final(f"{P}.idx.topk_final", [s], L, k=TOPK, ways=G, ascending=ops.p.index_order_pass,
                                 desc=f"{G}-way merge" + (" + ascending-index pass (K=512)" if ops.p.index_order_pass else ""))
            ops.sel_node = s
            if L == c["candidate_source_layer_id"]:     # candidate blocks for the reindex layers: side branch
                nb = math.ceil(per_die / CB)
                cs = ops.select_local(f"{P}.cand.topk_local", [sc], L, n=nb, k=CK,
                                      desc=f"block max over {CB} + local top-{CK} of {nb} blocks")
                cs = ops.collective(f"{P}.cand.merge", [cs], L, op="all_gather", payload=G * CK * 8,
                                    desc=f"{G} x {CK} candidate blocks") or cs
                ops.select_final(f"{P}.cand.final", [cs], L, k=CK, ways=G, ascending=False)
            rows_dep.append(g.add(f"{P}.gather", [s], layer=L, depth=ops.p.hbm_gather_s, ctrl=ops.ctrl,
                                  desc="selected compressed rows: the address exists only now (HBM round trip)"))
        else:                                       # reuse: the source's selection; rows prefetched
            rows_dep.append(sel[max(s_ for s_ in c["index_source_layer_ids"] if s_ <= L)])
    R = min(WIN, ctx) + n_sel
    kvb = min(WIN, ctx) * 528 + n_sel * 288
    if G > 1 and ops.p.kv_mode == "broadcast":
        # the rows' addresses are known once the selection is (prefetchable on reuse layers); the new
        # window row joins at the scores
        src_sel = [d for d in rows_dep if d not in (q, kr)]
        rg = ops.collective(f"{P}.rows_allgather", src_sel or [a], L, op="all_gather", payload=kvb,
                            desc=f"{R} shared KV rows, read once per group ({kvb} B)")
        rows_dep = [q, kr, rg]
        kvb_die = kvb / G
    else:
        kvb_die = kvb
    scd = K["me_lat"] + K["me_tree"] * math.ceil(math.log2(max(1, (HD // 32) / IL)))
    sco = ops.kvscan(f"{P}.scores", rows_dep, L, kv_bytes=kvb_die, macs=hpd * R * HD, depth_cycles=scd,
                     desc=f"q.k over {R} rows x {hpd} heads/die")
    mx = ops.reduce(f"{P}.max", [sco], hpd * R, L, segments=hpd)
    ex = ops.ew(f"{P}.exp", [sco] if ops.p.fuse else [mx], hpd * R, FADD + SU["EXP"], L, stream=ops.p.fuse,
                desc="online exp with running-max rescale (fused)" if ops.p.fuse else "exp(s - max)")
    den = ops.reduce(f"{P}.den", [ex], hpd * R, L, segments=hpd)
    sink = ops.ew(f"{P}.sink", [mx, den], hpd, FADD + SU["EXP"] + FADD, L, stream=False, desc="+ exp(sink - max)")
    pv = ops.kvscan(f"{P}.pv", [ex], L, kv_bytes=0, macs=hpd * R * HD,
                    depth_cycles=K["me_lat"] + K["me_tree"] * math.ceil(math.log2(max(1, R / 16 / IL))),
                    desc="BF16 P x V")
    o = ops.ew(f"{P}.normalize", [pv, sink], hpd * HD, SU_BASE + ops.p.fdiv_cycles + 2 * FADD, L, stream=False,
               desc="acc / den (IEEE divide), BF16, inverse RoPE")
    z = ops.matvec(f"{P}.wo_a", [o], L, n_out=OG * OR, k=(H // OG) * HD,
                   bytes_=OG * OR * (H // OG) * HD, desc="grouped wo_a [8 x 1024, 4096]")
    if G > OG:
        z = ops.collective(f"{P}.wo_a_group_reduce", [z], L, op="all_reduce", payload=OR * 4,
                           span=math.ceil(G / OG), desc="partial z of an o-group split across dies (FP32)") or z
    zq = ops.actquant(f"{P}.z_quant", [z], OG * OR // max(1, min(G, OG)), L)
    y = ops.matvec(f"{P}.wo_b", [zq], L, n_out=D, k=OG * OR, bytes_=D * OG * OR,
                   desc="wo_b [5120, 8192], K-split by o-group")
    return ops.collective(f"{P}.out_allreduce", [y], L, op="all_reduce", payload=D * 4,
                          desc="attention output partial sums (FP32)") or y


def v41_moe(ops, c, L, x, xq, fp4):
    m = ops.m
    D, NE, KE, FF = c["hidden_size"], c["num_routed_experts"], c["experts_per_token"], c["moe_intermediate_size"]
    G = m.group
    P = f"L{L}.ffn"
    rt = ops.matvec(f"{P}.router", [x], L, n_out=NE, k=D, bytes_=NE * D * 4, fmt="fp32",
                    desc="gate [384, 5120] FP32, experts split")
    sp = ops.ew(f"{P}.softplus_sqrt", [rt], math.ceil(NE / G), SU_BASE + V41["softplus"], L,
                desc="sqrt(softplus) on the SU (exp, divide, Horner, sqrt)")
    sp = ops.collective(f"{P}.router_allgather", [sp], L, op="all_gather", payload=NE * 4,
                        desc="384 FP32 router scores") or sp
    bias = ops.ew(f"{P}.bias", [sp], NE, SU_BASE + FADD, L, desc="+ bias")
    tk = ops.select_local(f"{P}.top6", [bias], L, n=NE, k=KE, desc=f"top-{KE} of {NE}")
    tk = ops.select_final(f"{P}.top6_order", [tk], L, k=KE, ways=1, ascending=True, desc="experts in id order")
    wn = ops.ew(f"{P}.weights", [tk, sp], KE, (KE - 1) * FADD + FADD + SU_BASE + ops.p.fdiv_cycles + FADD, L,
                stream=False, desc="sum of 6 + 1e-20, divide, x route_scale")
    sh = ops.matvec(f"{P}.shared_gu", [xq, rt], L, n_out=2 * FF, k=D, bytes_=2 * FF * D,
                    desc="shared expert w1|w3 [2 x 2304, 5120] FP8, intermediate split")
    shs = ops.ew(f"{P}.shared_swiglu", [sh], math.ceil(FF / G), SU["SIGM"] + 2 * FADD, L, desc="clamp, silu(g)*u")
    shq = ops.actquant(f"{P}.shared_quant", [shs], math.ceil(FF / G), L)
    if ops.p.moe == "expert_parallel":
        epd = max(1, math.ceil(ops.kmax)) if G > 1 else KE
        inter = FF * epd
        imb = ops.expert_imbalance
        desc = f"routed w1|w3, experts whole on their host (busiest die x{imb:.2f})"
    else:
        inter = math.ceil(KE * FF / G)
        imb = 1.0
        desc = f"routed w1|w3 of {KE} experts striped over {G} dies"
    gu = ops.matvec(f"{P}.experts_gu", [tk, sh], L, n_out=2 * FF * KE, k=D, bytes_=KE * 2 * FF * D * fp4,
                    fmt="fp4", imbalance=imb, desc=desc)
    sw = ops.ew(f"{P}.swiglu", [gu], inter, SU["SIGM"] + 2 * FADD, L, desc="clamp, silu(g)*u")
    sw = ops.ew(f"{P}.route_w", [sw, wn], inter, SU_BASE + FADD, L, stream=False, desc="x routing weight")
    sq = ops.actquant(f"{P}.quant2", [sw], inter, L)
    dn = ops.matvec(f"{P}.down", [sq, shq], L, n_out=D, k=FF * (KE + 1), bytes_=KE * D * FF * fp4 + D * FF,
                    fmt="fp4", imbalance=imb, desc="routed w2 + shared w2, summed in id order")
    if G > 1 and ops.p.moe == "expert_parallel":
        n = ops.g.add(f"{P}.combine_a2a", [dn], layer=L, issue_cat="collective_bytes",
                      depth_cat="collective_latency", ctrl=ops.ctrl, kind="collective",
                      desc="expert-parallel combine (dispatch is free: x is replicated in the group)",
                      op="combine_a2a", payload=D * 4, span=G, v=D * 4, kmax=ops.kmax)
        return n
    return ops.collective(f"{P}.combine_allreduce", [dn], L, op="all_reduce", payload=D * 4,
                          desc="MoE combine: routed + shared partial sums (FP32)") or dn


# -- dense models (Llama-3.1-8B, Qwen3-8B) on one die ---------------------------------------------------------------
def dense_graph(ops: Ops, s, ctx):
    g = ops.g
    D, NL, NH, KV, HD, FF, V = s["H"], s["L"], s["NH"], s["KV"], s["HD"], s["FF"], s["V"]
    bpp = s["bytes_per_param"]
    tok = ops.join("token", [], layer=-1)
    h = g.add("embed", [tok], layer=-1, depth=ops.cyc(SU_BASE) + 2e-9, ctrl=ops.bctrl, desc="embedding row")
    for L in range(NL):
        P = f"L{L}"
        x = ops.rmsnorm(f"{P}.attn_norm", [h], D, L, fold=True)
        x = ops.actquant(f"{P}.quant", [x], D, L)
        qkv = ops.matvec(f"{P}.qkv", [x], L, n_out=(NH + 2 * KV) * HD, k=D, bytes_=(NH + 2 * KV) * HD * D * bpp,
                         fmt="w4a8")
        q = ops.rmsnorm(f"{P}.qk_norm", [qkv], (NH + KV) * HD, L, segments=NH + KV) if s.get("qk_norm") else qkv
        q = ops.ew(f"{P}.rope", [q], (NH + KV) * HD, SU_BASE + 2 * FADD, L, desc="RoPE on q and the new k")
        kvb = ctx * KV * HD * 2 * 2
        sco = ops.kvscan(f"{P}.scores", [q], L, kv_bytes=kvb / 2, macs=NH * ctx * HD,
                         depth_cycles=K["me_lat"] + K["me_tree"] * 1, desc=f"q.k over {ctx} positions x {NH} heads")
        mx = ops.reduce(f"{P}.max", [sco], NH * ctx, L, segments=NH)
        ex = ops.ew(f"{P}.exp", [sco] if ops.p.fuse else [mx], NH * ctx, FADD + SU["EXP"], L, stream=ops.p.fuse,
                    desc="online exp with running-max rescale (fused)" if ops.p.fuse else "exp(s - max)")
        den = ops.reduce(f"{P}.den", [ex], NH * ctx, L, segments=NH)
        rc = ops.ew(f"{P}.recip", [den, mx], NH, SU["RECIP"], L, stream=False)
        pv = ops.kvscan(f"{P}.pv", [ex], L, kv_bytes=kvb / 2, macs=NH * ctx * HD,
                        depth_cycles=K["me_lat"] + K["me_tree"] * math.ceil(math.log2(max(1, ctx / 16 / IL))),
                        desc="P x V")
        o = ops.ew(f"{P}.normalize", [pv, rc], NH * HD, SU_BASE + FADD, L, stream=False)
        o = ops.actquant(f"{P}.oquant", [o], NH * HD, L)
        y = ops.matvec(f"{P}.o", [o], L, n_out=D, k=NH * HD, bytes_=D * NH * HD * bpp, fmt="w4a8")
        h = ops.ew(f"{P}.res1", [y, h], D, SU_BASE + FADD, L)
        x = ops.rmsnorm(f"{P}.ffn_norm", [h], D, L, fold=True)
        x = ops.actquant(f"{P}.quant2", [x], D, L)
        gu = ops.matvec(f"{P}.gate_up", [x], L, n_out=2 * FF, k=D, bytes_=2 * FF * D * bpp, fmt="w4a8")
        sw = ops.ew(f"{P}.swiglu", [gu], FF, SU["SIGM"] + 2 * FADD, L, desc="silu(g)*u")
        sw = ops.actquant(f"{P}.quant3", [sw], FF, L)
        dn = ops.matvec(f"{P}.down", [sw], L, n_out=D, k=FF, bytes_=D * FF * bpp, fmt="w4a8")
        h = ops.ew(f"{P}.res2", [dn, h], D, SU_BASE + FADD, L)
    x = ops.rmsnorm("head.norm", [h], D, NL, fold=True)
    lg = ops.matvec("head.lm_head", [x], NL, n_out=V, k=D, bytes_=V * D * bpp, fmt="w4a8")
    return ops.reduce("head.argmax", [lg], V, NL)


# -- evaluation --------------------------------------------------------------------------------------------------------
class Built:
    """A graph built once for a machine shape; `evaluate` prices it on a fabric and solves it."""

    def __init__(self, mach, p, clock, builder, *args):
        self.mach, self.p, self.clock = mach, p, clock
        self.g = Graph()
        self.ops = Ops(self.g, p, mach, clock)
        self.sink = builder(self.ops, *args)
        self.g.assign_sweep(mach.weight_sweep_s, mach.sweep_basis)

    def evaluate(self, fabric, chaining=None):
        g, mach = self.g, self.mach
        events = price_communication(g, fabric, mach.microbatch, self.clock)
        fin = g.solve(self.p.chaining if chaining is None else chaining)
        T = fin[self.sink]
        path = g.path(self.sink)
        cats = dict.fromkeys(CATS, 0.0)
        for n in path:
            for k_, v in g.contrib[n].items():
                cats[k_] += v
        occ = sum(n["issue"] for n in g.nodes.values() if n["kind"] not in ("collective", "hop"))
        occ_bound = occ * mach.slots / max(1, mach.stages)
        period = max(T, occ_bound)
        return dict(T=T, period=period, occupancy_bound_s=occ_bound, cats=cats, path=path, events=events,
                    fabric=fabric)


def summarize(b: Built, r, keep_steps=True, per_layer_top=10, layers=None):
    mach, g = b.mach, b.g
    out = {
        "design": mach.name, "kind": mach.kind, "fabric": r["fabric"].label(), "tensor_group": mach.group,
        "stages": mach.stages, "substages_per_layer": mach.substages_per_layer,
        "layers_per_stage": round(mach.layers_per_stage, 3), "batch": mach.batch,
        "users_per_stage": mach.microbatch, "context_tokens": mach.context, "su_width": mach.su_width,
        "mac_rate_per_die": mach.mac_rate_per_die,
        "critical_path_s": r["T"], "occupancy_bound_s": r["occupancy_bound_s"], "token_period_s": r["period"],
        "tokens_s_per_user": 1.0 / r["period"], "aggregate_tokens_s": mach.batch / r["period"],
        "binding": "critical_path" if r["T"] >= r["occupancy_bound_s"] else
                   "occupancy (breakdown_s is the critical path; the period is the stage occupancy x slots/stages)",
        "breakdown_s": dict(r["cats"]),
        "weight_sweep_input_s": mach.weight_sweep_s, "sweep_basis": mach.sweep_basis,
        "collectives_on_graph": sum(1 for e in r["events"] if e["op"] != "hop"),
        "hops_on_graph": sum(1 for e in r["events"] if e["op"] == "hop"),
        "expert_load_imbalance": getattr(b.ops, "expert_imbalance", None),
    }
    if mach.capacity_note:
        out["capacity_note"] = mach.capacity_note
    if keep_steps:
        by_layer = {}
        for n in r["path"]:
            dur = sum(g.contrib[n].values())
            if dur > 0:
                by_layer.setdefault(g.nodes[n]["layer"], []).append((n, dur))
        out["per_layer_critical_path_us"] = {str(L): round(sum(d for _, d in ss) * 1e6, 4)
                                             for L, ss in sorted(by_layer.items())}
        out["top_serial_steps_per_layer"] = {
            str(L): [dict(node=n, us=round(d * 1e6, 4), desc=g.nodes[n]["desc"],
                          parts_ns={k: round(v * 1e9, 2) for k, v in g.contrib[n].items() if v > 0})
                     for n, d in sorted(ss, key=lambda t: -t[1])[:per_layer_top]]
            for L, ss in sorted(by_layer.items()) if layers is None or L in layers}
    return out


def collective_census(r):
    per = {}
    for e in r["events"]:
        key = e["name"].split(".", 1)[-1] if e["name"][0] in "LE" else e["name"]
        d = per.setdefault(key, dict(count=0, op=e["op"], span=e.get("span"), payload_bytes=e["payload_bytes"],
                                     latency_ns=round(e["latency_s"] * 1e9, 2), bytes_ns=round(e["bytes_s"] * 1e9, 2),
                                     algo=e.get("algo"), where=e["where"], desc=e["desc"], layers=[]))
        d["count"] += 1
        d["layers"].append(e["layer"])
    for d in per.values():
        ls = d.pop("layers")
        d["layers"] = "every layer" if len(set(ls)) >= 39 else sorted(set(ls))
    return per


# -- machines from the analytical artifacts ---------------------------------------------------------------------------
def point(points, design, batch):
    for q in points:
        if q["design"] == design and q["batch_size"] == batch:
            return q
    raise KeyError((design, batch))


def lanes(p, clock, compute_mm2, analytical_bf16_ops_per_die):
    a = lane_areas_um2()
    su = p.su_width or max(16, 2 ** int(math.log2(compute_mm2 * 1e6 * p.su_area_fraction / a["su_lane"])))
    if p.lanes_from == "analytical":
        mac = analytical_bf16_ops_per_die / 2
    else:
        mac = compute_mm2 * 1e6 * (1 - p.su_area_fraction) / a["me_mac"] * clock
    return su, mac


def v41_machine(kind, g, batch, points, designs, p, clock, *, design=None, units=None, per_layer=None,
                g_ref=None):
    """The critical-path machine of one analytical design.  Defaults: the x188 array and the x12 wafer.
    `design`/`units`/`per_layer`/`g_ref` price any other analytical design (units = dies, or fields for a
    wafer at 57 per wafer; per_layer = units one layer's weights occupy; g_ref = the design's tensor group)."""
    if kind == "array":
        dn, g0, u0, pl0 = ARRAY_DESIGN, 4, 188, 4.0
    else:
        dn, g0, u0, pl0 = WAFER_DESIGN, 57, 12 * 57, 684 / 40
    dn = design or dn
    g_ref = g_ref or g0
    units = units or u0
    per_layer = per_layer or pl0
    q = point(points, dn, batch)
    d = designs[dn]
    NL = 40
    if g >= per_layer:
        lps, sub = g / per_layer, 1
    else:
        lps, sub = 1.0, math.ceil(per_layer / g)
    stages = max(1, math.ceil(NL / lps))
    mb_ref, slots_ref = q["microbatch_per_slot"], q["token_slots"]
    if g == g_ref:
        slots, mb = slots_ref, mb_ref
    else:
        slots = max(float(stages), slots_ref * stages / q["pipeline_stages"])
        mb = max(1.0, batch / slots)
    ct = q["component_times_s"]
    S = q["step_time_s"] - ct["layer_fixed_latency"] - ct["link_latency"]
    beta = max(ct["compute"], ct["weight_read"], ct["kv_read"]) / S
    c_ = ct["compute"] * (g_ref / g) * (mb / mb_ref)
    w_ = ct["weight_read"] * (g_ref / g)
    compute_mm2 = d["area_split_per_device"]["compute_mm2"] / (57 if kind == "wafer" else 1)
    su, mac = lanes(p, clock, compute_mm2, d["compute_ops_s"]["bf16"] / units)
    note = ""
    if kind == "wafer":
        used = (units // 57) * (57 // g) * g
        if used < units:
            note = f"groups of {g} tile {used} of {units} fields: {units - used} idle fields hold no weights " \
                   f"({(units - used) / units:.1%} capacity short unless spare ROM elsewhere)"
    ref = dict(step_time_s=q["step_time_s"], tokens_s_per_user=q["per_user_tokens_s"],
               aggregate_tokens_s=q["aggregate_tokens_s"], component_times_s=ct, stage_balance=beta,
               service_time_s=S, hop_breakdown=q.get("hop_breakdown"), microbatch_per_slot=mb_ref,
               token_slots=slots_ref)
    return Machine(name=f"{dn} (group {g})", kind=kind, group=g, stages=stages, substages_per_layer=sub,
                   layers_per_stage=lps, weight_sweep_s=max(c_, w_) / beta,
                   sweep_basis="macs" if c_ >= w_ else "bytes", kv_bw_per_die=d["kv_read_bytes_s"] / units,
                   mac_rate_per_die=mac, su_width=su, microbatch=mb, batch=batch, context=q["context_tokens"],
                   slots=slots, reference=ref, capacity_note=note)


def hc1_machine(model_path, p, clock):
    from opentallas.roofline import Technology, taalas_hc1_anchor
    from opentallas.schema import ModelProfile
    tech = Technology.load(TECH)
    prof = ModelProfile.load(model_path)
    chk = taalas_hc1_anchor(tech, prof)
    step, bud = chk.detail["step"], chk.detail["budget"]
    ct = step["component_times_s"]
    su, mac = lanes(p, clock, bud["area_split_per_device"]["compute_mm2"], bud["compute_ops_s"]["bf16"])
    ref = dict(step_time_s=step["step_time_s"], tokens_s_per_user=step["per_user_tokens_s"],
               component_times_s=ct, published_tokens_s_per_user=chk.published_value, ratio=chk.ratio)
    return Machine(name=f"Taalas-HC1-class die (N6, 815 mm2), {prof.name}", kind="single", group=1, stages=1,
                   substages_per_layer=1, layers_per_stage=prof.num_layers,
                   weight_sweep_s=max(ct["weight_read"], ct["compute"]), sweep_basis="bytes",
                   kv_bw_per_die=bud["kv_read_bytes_s"], mac_rate_per_die=mac, su_width=su,
                   microbatch=1.0, batch=1, context=step["context_tokens"], slots=1.0, reference=ref)


LLAMA_SHAPE = dict(H=4096, L=32, NH=32, KV=8, HD=128, FF=14336, V=128256, qk_norm=False)


# -- the study ----------------------------------------------------------------------------------------------------------
def headline_hc1(p, clock):
    mach = hc1_machine(LLAMA, p, clock)
    shape = dict(LLAMA_SHAPE, bytes_per_param=3.5 / 8)
    b = Built(mach, p, clock, dense_graph, shape, mach.context)
    r = b.evaluate(SingleFabric())
    s = summarize(b, r, layers={0, 32})
    pub = mach.reference["published_tokens_s_per_user"]
    s.update(published_tokens_s_per_user=pub, published_us_per_token=1e6 / pub,
             modelled_over_published_rate=s["tokens_s_per_user"] / pub,
             residual_us=r["period"] * 1e6 - 1e6 / pub, reference_analytical=mach.reference)
    s["no_chaining_us_per_token"] = b.evaluate(SingleFabric(), chaining=False)["period"] * 1e6
    for tag, pp in (("fused_not_bit_exact", replace(p, fuse=True)),
                    ("fused_and_su_4096", replace(p, fuse=True, su_width=4096))):
        m2 = hc1_machine(LLAMA, pp, clock)
        b2 = Built(m2, pp, clock, dense_graph, shape, m2.context)
        r2 = b2.evaluate(SingleFabric())
        s[tag] = dict(us_per_token=r2["period"] * 1e6, rate_over_published=(1 / r2["period"]) / pub,
                      breakdown_us={k: round(v * 1e6, 3) for k, v in r2["cats"].items()})
    sens = []
    for lf in ("rtl_area", "analytical"):
        for w in (0, 64, 256, 1024, 4096):
            pp = replace(p, lanes_from=lf, su_width=w)
            m2 = hc1_machine(LLAMA, pp, clock)
            rr = Built(m2, pp, clock, dense_graph, shape, m2.context).evaluate(SingleFabric())
            sens.append(dict(lanes_from=lf, su_width=m2.su_width, mac_per_cycle=round(m2.mac_rate_per_die / clock),
                             us_per_token=rr["period"] * 1e6, rate_over_published=(1 / rr["period"]) / pub))
    s["lane_sensitivity"] = sens
    return s


def headline_qwen(p, clock):
    mach = hc1_machine(QWEN, p, clock)
    shape = dict(hdc_timing.SHAPES["qwen3-8b"], qk_norm=True, bytes_per_param=3.5 / 8)
    b = Built(mach, p, clock, dense_graph, shape, mach.context)
    s = summarize(b, b.evaluate(SingleFabric()), layers={0, 36})
    s["reference_analytical"] = mach.reference
    return s


def default_fabric(kind, links, g):
    if kind == "array":
        return ArrayFabric(links, 4, "mesh", g)
    return WaferFabric(links, g, "square")


def build(p: Params, quick=False):
    tech = json.loads(TECH.read_text())
    links = link_consts(tech)
    clock, clock_rows = routed_clock()
    clock = p.clock_hz or clock
    p = replace(p, clock_hz=clock)
    rec = dict(schema=SCHEMA, tool="tools/decode_critical_path.py", params=asdict(p),
               clock=dict(hz=clock, basis="slowest routed fmax among the token path's units (ASAP7, TT, 0.7 V)",
                          blocks=clock_rows),
               lane_areas_um2=lane_areas_um2(),
               rtl_constants=dict(K=dict(K, su_depth=SU), v41=V41, sources=RTL_SOURCES),
               links=links, switch_latency=SWITCH_LATENCY_S, determinism=DETERMINISM)
    rec["hc1_llama31_8b"] = headline_hc1(p, clock)
    rec["qwen3_8b_single_reticle"] = headline_qwen(p, clock)

    points = json.loads(V41_POINTS.read_text())
    designs = {d_["name"]: d_ for d_ in json.loads(V41_ANALYTICAL.read_text())["designs"]
               if d_["name"] in (ARRAY_DESIGN, WAFER_DESIGN)}
    c = v41_shape()
    rows = {}
    for kind, g_ref in (("array", 4), ("wafer", 57)):
        for bt in ((1,) if quick else (1, 64, 4096)):
            m_ = v41_machine(kind, g_ref, bt, points, designs, p, clock)
            b = Built(m_, p, clock, v41_graph, c, m_.context)
            fab = default_fabric(kind, links, g_ref)
            r = b.evaluate(fab)
            s = summarize(b, r, layers=None if bt == 1 else {2, 3, 20})
            s["reference_analytical"] = m_.reference
            if bt == 1:
                s["collectives_per_layer"] = collective_census(r)
                s["no_chaining_tokens_s_per_user"] = 1 / b.evaluate(fab, chaining=False)["period"]
                for alg in ALGORITHMS:
                    fa = ArrayFabric(links, 4, "mesh", g_ref, alg) if kind == "array" else \
                        WaferFabric(links, g_ref, "square", alg)
                    per = b.evaluate(fa)["period"]
                    s.setdefault("algorithm_tokens_s_per_user", {})[alg] = 1 / per if math.isfinite(per) else None
                sens = {}
                for name, pp in (("su_width_64", replace(p, su_width=64)), ("su_width_4096", replace(p, su_width=4096)),
                                 ("select_units_16", replace(p, select_units=16)),
                                 ("select_units_256", replace(p, select_units=256)),
                                 ("no_index_order_pass", replace(p, index_order_pass=False)),
                                 ("lanes_from_analytical", replace(p, lanes_from="analytical")),
                                 ("expert_parallel", replace(p, moe="expert_parallel")),
                                 ("fused_not_bit_exact", replace(p, fuse=True)),
                                 ("kv_rows_replicated", replace(p, kv_mode="replicated")),
                                 ("fdiv_12_cycles_hypothetical", replace(p, fdiv_cycles=12))):
                    mm = v41_machine(kind, g_ref, 1, points, designs, pp, clock)
                    sens[name] = 1 / Built(mm, pp, clock, v41_graph, c, mm.context).evaluate(fab)["period"]
                s["sensitivity_tokens_s_per_user"] = sens
            rows[f"{kind}_batch{bt}"] = s
    rec["deepseek_v41_flash"] = rows
    if not quick:
        rec["topology_sweep"] = topology_sweep(p, clock, links, points, designs, c)
    rec["assumptions"] = ASSUMPTIONS
    return rec


ARRAY_GROUPS = (1, 2, 4, 8, 16, 32)
WAFER_GROUPS = (4, 8, 9, 12, 16, 19, 28, 57)


def topology_sweep(p, clock, links, points, designs, c):
    """Iso-area sweep: physical topology x logical reduction x group size x dies per package, per batch."""
    rows = []
    for moe in ("striped", "expert_parallel"):
        pp = replace(p, moe=moe)
        for kind, groups in (("array", ARRAY_GROUPS), ("wafer", WAFER_GROUPS)):
            for g in groups:
                built = {}
                for bt in (1, 64, 4096):
                    m_ = v41_machine(kind, g, bt, points, designs, pp, clock)
                    built[bt] = Built(m_, pp, clock, v41_graph, c, m_.context)
                if kind == "array":
                    fabrics = [(dp, board) for dp in (2, 4, 8) for board in BOARD_TOPOLOGIES]
                else:
                    fabrics = [(None, shape) for shape in ("square", "rect")]
                for dp, board in fabrics:
                    for alg in ["best"] + ALGORITHMS:
                        fab = ArrayFabric(links, dp, board, g, alg) if kind == "array" else \
                            WaferFabric(links, g, board, alg)
                        if fab.refused:
                            rows.append(dict(kind=kind, moe=moe, group=g, dies_per_package=dp, physical=board,
                                             logical=alg, refused=fab.refused))
                            break
                        row = dict(kind=kind, moe=moe, group=g, dies_per_package=dp, physical=board, logical=alg)
                        ok = True
                        for bt, b in built.items():
                            r = b.evaluate(fab)
                            if not math.isfinite(r["period"]):
                                ok = False
                                break
                            if bt == 1:
                                row["breakdown_us_b1"] = {k: round(v * 1e6, 3) for k, v in r["cats"].items()}
                                row["algorithms_chosen_b1"] = sorted({e["algo"] for e in r["events"]
                                                                      if e["op"] != "hop"})
                            row[f"tok_s_user_b{bt}"] = 1 / r["period"]
                            row[f"aggregate_tok_s_b{bt}"] = bt / r["period"]
                            row[f"users_per_stage_b{bt}"] = b.mach.microbatch
                        if not ok:
                            continue
                        row["stages"] = built[1].mach.stages
                        row["deterministic"] = all(a in DETERMINISM for a in row["algorithms_chosen_b1"]) and \
                            moe != "expert_parallel"
                        if built[1].mach.capacity_note:
                            row["capacity_note"] = built[1].mach.capacity_note
                        rows.append(row)
    ok = [r for r in rows if "refused" not in r]
    ranked = sorted(ok, key=lambda r: -r["tok_s_user_b1"])

    def pareto(rs):
        front, seen = [], set()
        for r in rs:
            key = (r["kind"], r["moe"], r["group"], r["dies_per_package"], r["physical"],
                   round(r["tok_s_user_b1"], 6), round(r["aggregate_tok_s_b4096"], 6))
            if key in seen:
                continue
            seen.add(key)
            if not any(o["tok_s_user_b1"] >= r["tok_s_user_b1"] and o["aggregate_tok_s_b4096"] >= r["aggregate_tok_s_b4096"]
                       and (o["tok_s_user_b1"] > r["tok_s_user_b1"] or o["aggregate_tok_s_b4096"] > r["aggregate_tok_s_b4096"])
                       for o in rs):
                front.append(r)
        return sorted(front, key=lambda r: -r["tok_s_user_b1"])

    out = dict(rows=len(rows), refused=[r for r in rows if "refused" in r])
    for kind in ("array", "wafer"):
        rs = [r for r in ranked if r["kind"] == kind]
        det = [r for r in rs if r["deterministic"] and "capacity_note" not in r]
        out[kind] = dict(ranked_top40=rs[:40], pareto_b1_vs_aggregate_b4096=pareto(rs),
                         recommended=det[0] if det else None,
                         best_per_group={str(g): max((r for r in rs if r["group"] == g),
                                                     key=lambda r: r["tok_s_user_b1"], default=None)
                                         for g in (ARRAY_GROUPS if kind == "array" else WAFER_GROUPS)},
                         best_per_physical={f"{r_dp}/{ph}": max((r for r in rs if r["physical"] == ph and
                                                                 r["dies_per_package"] == r_dp),
                                                                key=lambda r: r["tok_s_user_b1"], default=None)
                                            for r_dp, ph in sorted({(r["dies_per_package"], r["physical"]) for r in rs},
                                                                   key=str)})
    # wafer sensitivities (labelled, never the headline): field hop band and a dedicated reduction network
    rec_w = out["wafer"]["recommended"]
    if rec_w:
        sens = []
        pp = replace(p, moe=rec_w["moe"])
        m_ = v41_machine("wafer", rec_w["group"], 1, points, designs, pp, clock)
        b = Built(m_, pp, clock, v41_graph, c, m_.context)
        for hop_s in (75e-9, 125e-9, 250e-9):
            for ex in (0.0, 10e-9, 25e-9, 50e-9):
                fab = WaferFabric(links, rec_w["group"], rec_w["physical"], rec_w["logical"], hop_s=hop_s, express_s=ex)
                sens.append(dict(field_hop_ns=hop_s * 1e9, express_hop_ns=ex * 1e9,
                                 tok_s_user_b1=1 / b.evaluate(fab)["period"]))
        out["wafer"]["sensitivity_field_hop_and_express_network"] = sens
    rec_a = out["array"]["recommended"]
    if rec_a:
        sens = []
        pp = replace(p, moe=rec_a["moe"])
        m_ = v41_machine("array", rec_a["group"], 1, points, designs, pp, clock)
        b = Built(m_, pp, clock, v41_graph, c, m_.context)
        base = dict(links)
        for lo_hi in ("hop_low", "value", "hop_high"):
            ln = {k: dict(v, hop=(v[lo_hi] if lo_hi != "value" else v["hop"]) or v["hop"]) for k, v in base.items()}
            fab = ArrayFabric(ln, rec_a["dies_per_package"], rec_a["physical"], rec_a["group"], rec_a["logical"])
            sens.append(dict(link_hops=lo_hi, tok_s_user_b1=1 / b.evaluate(fab)["period"]))
        for sw in (100e-9, 250e-9, 600e-9):
            fab = ArrayFabric(links, rec_a["dies_per_package"], "switch", rec_a["group"], "best", switch_s=sw)
            if not fab.refused:
                sens.append(dict(switch_ns=sw * 1e9, physical="switch", tok_s_user_b1=1 / b.evaluate(fab)["period"]))
        out["array"]["sensitivity_link_latency"] = sens
    return out


ASSUMPTIONS = [
    "Clock: the slowest routed ASAP7 fmax among the token path's HDC units (ot_hdc_softplus, 1.034 GHz) is "
    "applied to the N5/N6 designs; ot_hdc_matvec and ot_hdc_stream did not close at their probe targets.",
    "Lanes per die: the analytical design's compute area x (1 - 0.10) / 1,051 um2 per BF16 MAC (routed "
    "ot_hdc_matvec) for attention and index scoring, and x 0.10 / 42,443 um2 per stream-unit element/cycle "
    "(routed ot_hdc_stream, SFU included) rounded down to a power of two; ASAP7 areas are not scaled to N5/N6.",
    "Matrix-vector occupancy is the analytical design's own sweep (points.json: max(compute, weight_read) / "
    "stage balance), apportioned to each matvec by bytes (weight-bound) or MACs (compute-bound); other group "
    "sizes scale it by g_ref/g (the compute term also by users per stage).",
    "A reduction over n costs ceil(n*m/W) + red_tail 32 + 5*lg W cycles; SU classes cost 29 + the unit's depth.",
    "Top-k: first level on up to 64 ot_hdc_select units in rank order and a sorted merge, then one "
    "ascending-index pass (the golden emits positions in order); the merge tree and the ascending pass on "
    "merged input are not built RTL.",
    "Partitioning: q_a|kv|index-weights output-split (all-gather), heads split for attention, index keys "
    "split by position (local top-k + all-gather merge), wo_b K-split (all-reduce), router experts split "
    "(all-gather of 384 scores), experts striped over the group (default) or expert-parallel (combine "
    "all-to-all), shared expert split on its intermediate dimension. The hc fn matrix and the indexer wq_b "
    "are replicated (1.97 MB, 5.2 MB) to avoid two collectives.",
    "Hyper-connection mixes and the 20-iteration Sinkhorn run redundantly on every die from the replicated "
    "residual, on a 16-entry fadd/fdiv unit (each normalisation 3 sequential adds + eps + one divide).",
    "Array: 188 reticle dies at every dies-per-package choice; a layer per 4 dies at g=4; the remaining "
    "silicon holds Engram tables and the lm_head (one extra hop). Package SerDes lanes scale with the "
    "package edge (128 x sqrt(dies/4)) and are split evenly over the topology's neighbour links; a topology "
    "needing more x8 ports than that is refused. One switch tier: 250 ns assumed (100-600 ns) plus two SerDes "
    "hops, radix 64. Wafer: 684 fields / 40 layers = 17.1 fields per layer; a group smaller than a layer adds "
    "intra-layer sub-stage hops; groups that do not tile 57 leave fields idle (flagged as a capacity shortfall).",
    "HBM random-row gather latency 100 ns is assumed (technology.json has no HBM latency constant); it is "
    "charged only where the address is data-dependent (index-source layers).",
    "Per-user rate = 1 / max(critical path, occupancy bound), the occupancy bound being every issue term "
    "times slots/stages; aggregate = batch x per-user rate.",
    "Routing is uniform (the router trace is synthetic), so expert-parallel imbalance is a Monte Carlo "
    "expectation of the busiest die over top-6 of 384 at the users per stage.",
]


def print_summary(rec):
    def line(tag, s):
        b = s["breakdown_s"]
        print(f"{tag:30s} {s['tokens_s_per_user']:9.0f} tok/s  {s['token_period_s'] * 1e6:8.2f} us  " +
              " ".join(f"{k.split('_')[0][:5]}{k.split('_')[-1][:3]}={v * 1e6:.2f}" for k, v in b.items()))
    h = rec["hc1_llama31_8b"]
    line("HC1 Llama-3.1-8B", h)
    print(f"  published {h['published_tokens_s_per_user']:.0f} tok/s ({h['published_us_per_token']:.2f} us); "
          f"modelled/published rate {h['modelled_over_published_rate']:.3f}; residual {h['residual_us']:+.2f} us")
    line("Qwen3-8B single reticle", rec["qwen3_8b_single_reticle"])
    for k_, s in rec["deepseek_v41_flash"].items():
        line(f"V4.1 {k_}", s)
    ts = rec.get("topology_sweep")
    if ts:
        for kind in ("array", "wafer"):
            print(f"-- {kind}: recommended {json.dumps(ts[kind]['recommended'])[:400]}")
            for r in ts[kind]["pareto_b1_vs_aggregate_b4096"][:10]:
                print(f"   pareto {r['moe']:15s} g={r['group']:<3} dp={r['dies_per_package']} {r['physical']:7s} "
                      f"{r['logical']:12s} b1={r['tok_s_user_b1']:8.0f} b64={r['tok_s_user_b64']:8.0f} "
                      f"agg4096={r['aggregate_tok_s_b4096']:10.0f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--quick", action="store_true", help="headline rows at batch 1 only, no sweep")
    args = ap.parse_args()
    rec = build(Params(), quick=args.quick)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=1) + "\n")
    print_summary(rec)


if __name__ == "__main__":
    main()
