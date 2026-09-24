"""Serial per-token latency from the operator dependency graph.

Why this module exists
----------------------
The analytical roofline used to price the serial part of a decode step as a
flat per-layer floor (``roofline.layer_fixed_latency``: four array-pass
boundaries of ~36 ns plus a barrier and a sequencer, ~250 ns a layer) plus two
all-reduces per layer.  The bottom-up critical path of the machine this program
actually builds (``tools/decode_critical_path.py``, priced with the measured
depths of ``rtl/hdc``) found that floor 10-20x low -- DeepSeek-V4.1 spends
~5.3 us per plain layer on its dependent-operator chain, most of it the 4x4
hyper-connection Sinkhorn -- and found that a weight-splitting tensor group
needs ~6 collectives per V4.1 layer, not 2.  This module is that machinery,
generalised from the tool's one model to every model the studies evaluate, and
applied to both sides of every comparison.

What it computes
----------------
One DAG per token: every operator of every layer with its real data
dependencies, built from ``ModelProfile`` fields plus the structural sidecar
``configs/models/decode_graph_shapes.json`` (dense/MoE, GQA/MLA/DeepSeek sparse
attention, KDA linear attention, norms, hyper-connections, indexer, Engram,
latent MoE and block attention-residuals where the profile says so).  A model
whose structure is not stated is REFUSED, never given another model's graph.

Each node carries

* a constant part: its dependent pipeline depth, its issue time for vector work
  (ROM: elements x users over the stream-unit width), its sequencer control,
  and -- for collectives and pipeline hops -- the fabric's latency plus the real
  payload over the link it crosses;
* a share of the machine's weight sweep ``w`` and of its KV sweep ``k``, by the
  bytes the node reads.  The roofline's service time is distributed over the
  nodes in proportion; nothing here re-derives bandwidth.

The critical path is ``T(W, K) = max over paths (c + w W + k K)``, a convex
piecewise-linear function of the two sweep totals.  Every study point solves it
once on a flattened graph (``CompiledGraph.solve``).  A graph's STRUCTURE is
built once per machine and re-priced per microbatch and stream-unit width
(``Pricer``), because those change what a node costs, never which nodes exist;
``Graph.envelope`` gives the whole line set at one KV:weight split and is kept
as an exact cross-check of the solve.

Two machines, one graph
-----------------------
* **ROM** (the hardwired datapath): every node priced from
  ``technology.serial_latency.rom_datapath`` -- measured RTL depths at the
  slowest routed clock.  Streamable consumers chase their producer.
* **GPU**: the same graph; every dependent kernel boundary pays a published
  CUDA-graph launch gap, vector work fused into a kernel is free, a dependent
  arithmetic chain inside one kernel (the Sinkhorn) pays published instruction
  latencies at the part's clock.

Collectives
-----------
Every collective the weight split needs is a node where the data dependency
needs the whole vector.  On a *hardware* link (``serial_latency.hardware_links``)
the logical algorithm is searched per collective and per point -- two-step,
one-shot, ring, recursive doubling, tree, centre-rooted mesh, and hierarchical
across link classes -- each with a fixed summation order.  On a *measured* link
(NVLink, InfiniBand), ``hop_latency_s`` is half a measured small-message
collective, so a collective costs that floor per switch tier and no algorithm is
credited beyond the measured best kernel.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from .schema import ModelProfile, ValidationError

ROOT = Path(__file__).resolve().parents[2]
SHAPES_PATH = ROOT / "configs" / "models" / "decode_graph_shapes.json"

CATS = ("compute_chain", "weight_sweep", "kv_sweep", "collective_latency",
        "collective_bytes", "pipeline_hops", "control", "kernel_launch")
COMM_CATS = ("collective_latency", "collective_bytes", "pipeline_hops")
ALGORITHMS = ("two_step", "one_shot", "ring", "rec_doubling", "tree", "centre_mesh")
DETERMINISM = {
    "two_step": "fixed order: each shard is summed on its owner in rank order, then broadcast",
    "one_shot": "fixed order: every rank sums all partials in rank order (bit-identical replicas)",
    "ring": "fixed order per shard (ring order); deterministic run to run",
    "rec_doubling": "fixed pairing per step; IEEE add is commutative so all ranks hold the same bits",
    "tree": "fixed tree: deterministic",
    "centre_mesh": "fixed centre-rooted spanning tree: deterministic",
    "hierarchical": "in-domain, then across domains, then an in-domain broadcast; each level fixed",
    "measured_floor": "the measured best small-message kernel (NVLink/InfiniBand); NCCL LL is deterministic for a fixed rank count",
}
FP4_BYTES = 0.53125          # E2M1 + one UE8M0 scale per 32


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------


def _val(node: Mapping[str, Any]) -> float:
    return float(node["value"])


@dataclass(frozen=True)
class RomDatapath:
    clock_hz: float
    seq_gap: int
    idle_reg: int
    me_lat: int
    me_tree: int
    interleave: int
    red_tail: int
    su_none: int
    su_exp: int
    su_recip: int
    su_rsqrt: int
    su_sigm: int
    fadd: int
    fdiv: int
    fsqrt: int
    softplus: int
    blockdot: int
    actquant: int
    fp4qdq: int
    engram_hash: int
    select_extra: int
    su_lane_um2: float
    su_area_fraction: float
    select_units: int
    hbm_gather_s: float
    rom_row_s: float

    @classmethod
    def from_technology(cls, technology: Any) -> "RomDatapath":
        r = technology.raw["serial_latency"]["rom_datapath"]
        return cls(
            clock_hz=_val(r["clock_hz"]), seq_gap=int(_val(r["sequencer_gap_cycles"])),
            idle_reg=int(_val(r["barrier_idle_cycles"])),
            me_lat=int(_val(r["matrix_engine_latency_cycles"])),
            me_tree=int(_val(r["matrix_engine_tree_cycles_per_level"])),
            interleave=int(_val(r["matrix_engine_interleave"])),
            red_tail=int(_val(r["reducer_tail_cycles"])),
            su_none=int(_val(r["stream_depth_none_cycles"])), su_exp=int(_val(r["stream_depth_exp_cycles"])),
            su_recip=int(_val(r["stream_depth_recip_cycles"])),
            su_rsqrt=int(_val(r["stream_depth_rsqrt_cycles"])),
            su_sigm=int(_val(r["stream_depth_sigmoid_cycles"])),
            fadd=int(_val(r["fp_add_cycles"])), fdiv=int(_val(r["fp_div_cycles"])),
            fsqrt=int(_val(r["fp_sqrt_cycles"])), softplus=int(_val(r["softplus_cycles"])),
            blockdot=int(_val(r["blockdot_cycles"])), actquant=int(_val(r["actquant_cycles"])),
            fp4qdq=int(_val(r["fp4qdq_cycles"])), engram_hash=int(_val(r["engram_hash_cycles"])),
            select_extra=int(_val(r["select_extra_cycles"])),
            su_lane_um2=_val(r["stream_lane_area_um2"]),
            su_area_fraction=_val(r["stream_area_fraction"]),
            select_units=int(_val(r["select_units_per_die"])),
            hbm_gather_s=_val(r["hbm_random_row_latency_s"]), rom_row_s=_val(r["rom_row_access_s"]),
        )

    def su_width(self, compute_mm2_per_device: float) -> int:
        lanes = compute_mm2_per_device * 1e6 * self.su_area_fraction / self.su_lane_um2
        return max(16, 2 ** int(math.log2(max(1.0, lanes))))


@dataclass(frozen=True)
class GpuDatapath:
    kernel_gap_s: float
    fp32_dep_cycles: float
    fp32_div_cycles: float

    @classmethod
    def from_technology(cls, technology: Any) -> "GpuDatapath":
        g = technology.raw["serial_latency"]["gpu_datapath"]
        return cls(kernel_gap_s=_val(g["kernel_launch_gap_s"]),
                   fp32_dep_cycles=_val(g["fp32_dependent_cycles"]),
                   fp32_div_cycles=_val(g["fp32_divide_cycles"]))


_DATAPATHS: dict[int, tuple[Any, "RomDatapath", "GpuDatapath"]] = {}


def datapaths(technology: Any) -> tuple["RomDatapath", "GpuDatapath"]:
    """Both datapaths of one technology table (cached per table)."""
    hit = _DATAPATHS.get(id(technology.raw))
    if hit is not None and hit[0] is technology.raw:
        return hit[1], hit[2]
    rom, gpu = RomDatapath.from_technology(technology), GpuDatapath.from_technology(technology)
    if len(_DATAPATHS) > 512:
        _DATAPATHS.clear()
    _DATAPATHS[id(technology.raw)] = (technology.raw, rom, gpu)
    return rom, gpu


#: Leaves whose LOW end of latency is their range_HIGH (a faster clock, a wider
#: unit).  Everything else in serial_latency lowers latency at range_low.
INVERSE_LEAVES = ("clock_hz", "stream_area_fraction", "select_units_per_die")


def at_serial_latency_bound(technology: Any, bound: str) -> Any:
    """A copy with every ranged serial-latency leaf at the end that makes the
    serial path shortest (``low``) or longest (``high``)."""

    if bound not in ("low", "high"):
        raise ValidationError("serial latency bound must be 'low' or 'high'")
    raw = json.loads(json.dumps(technology.raw))
    for block in ("rom_datapath", "gpu_datapath"):
        for name, node in raw["serial_latency"][block].items():
            if not isinstance(node, dict) or "range_low" not in node:
                continue
            fast = "range_high" if name in INVERSE_LEAVES else "range_low"
            slow = "range_low" if name in INVERSE_LEAVES else "range_high"
            node["value"] = node[fast if bound == "low" else slow]
    from dataclasses import replace as _replace
    return _replace(technology, raw=raw)


# ---------------------------------------------------------------------------
# model structure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LayerSpec:
    index: int
    attention: str            # gqa | mla | kda | dsv4
    rows: int                 # attended rows at the context (gqa/mla); window rows (dsv4)
    entry_bytes: float        # KV bytes per attended row (per user, all heads)
    heads: int = 0
    kv_heads: int = 0
    head_dim: int = 0
    v_head_dim: int = 0
    sink: bool = False
    ratio: int = 0            # dsv4 compression ratio (0: window only)
    kv_source: bool = False   # dsv4: this layer compresses and owns KV
    scans: bool = False       # dsv4: runs its own index scan
    dense_compressed: bool = False  # dsv4 HCA: attends every compressed row
    scan_cap: int = 0
    index_entry_bytes: float = 0.0
    window_entry_bytes: float = 0.0
    state_bytes: float = 0.0  # kda recurrent state
    moe: bool = True
    hash_routed: bool = False
    engram: bool = False


@dataclass(frozen=True)
class DecodeShape:
    name: str
    family: str
    hidden: int
    vocab: int
    layers: tuple[LayerSpec, ...]
    dense_bpp: float
    routed_bpp: float
    ffn: int = 0                        # dense FFN intermediate
    experts: int = 1
    topk: int = 1
    moe_ffn: int = 0
    shared_experts: int = 0
    score_function: str = ""
    router_bytes_per_param: float = 4.0
    latent_dim: int = 0
    latent_norm: bool = False
    qk_norm: bool = False
    hc_mult: int = 1
    sinkhorn_iters: int = 0
    attn_res_block: int = 0
    dsv4: Mapping[str, Any] = field(default_factory=dict)
    mla: Mapping[str, Any] = field(default_factory=dict)
    kda: Mapping[str, Any] = field(default_factory=dict)
    engram: Mapping[str, Any] = field(default_factory=dict)
    source: str = ""


_SHAPES_CACHE: dict[str, Any] = {}


def _shapes() -> Mapping[str, Any]:
    if "models" not in _SHAPES_CACHE:
        _SHAPES_CACHE["models"] = json.loads(SHAPES_PATH.read_text())["models"]
    return _SHAPES_CACHE["models"]


def _need(mapping: Mapping[str, Any], key: str, model: str, where: str) -> Any:
    if key not in mapping or mapping[key] is None:
        raise ValidationError(
            f"{model}: the decode graph needs {key!r} and neither the profile nor "
            f"{where} states it; refusing rather than defaulting to another "
            f"architecture's structure"
        )
    return mapping[key]


def _bpp(fmt: str | None) -> float:
    f = (fmt or "").lower()
    if "fp4" in f or "e2m1" in f:
        return FP4_BYTES
    if "fp8" in f or "e4m3" in f or "int8" in f:
        return 1.0
    if "bf16" in f or "fp16" in f:
        return 2.0
    if "fp32" in f:
        return 4.0
    raise ValidationError(f"no byte width known for compute format {fmt!r}")


_SHAPE_MEMO: dict[tuple[str, int], DecodeShape] = {}


def decode_shape(model: ModelProfile, context_tokens: int) -> DecodeShape:
    """The model's operator structure for one decode token at this context."""

    key = (model.name + "|" + model.source_revision + "|" + str(len(model.attention_groups)), int(context_tokens))
    hit = _SHAPE_MEMO.get(key)
    if hit is not None:
        return hit
    table = _shapes()
    entry = table.get(model.name)
    if entry is None:
        raise ValidationError(
            f"{model.name}: no entry in {SHAPES_PATH.relative_to(ROOT)}; the serial "
            f"latency is built from the model's operator graph and an unknown "
            f"structure is refused, not defaulted"
        )
    while "inherits" in entry:
        entry = {**table[entry["inherits"]], **{k: v for k, v in entry.items() if k != "inherits"}}
    family = _need(entry, "family", model.name, "the shapes sidecar")
    meta = dict(model.metadata)
    oc = dict(meta.get("operator_config") or {})
    merged = {**meta, **oc, **entry}
    where = f"metadata/operator_config or {SHAPES_PATH.name}"
    seq = meta.get("attention_sequence")
    if not isinstance(seq, list) or len(seq) != model.num_layers:
        raise ValidationError(f"{model.name}: metadata.attention_sequence must name every layer")
    groups = {g.label or g.kind: g for g in model.attention_groups}
    for label in set(seq):
        if label not in groups:
            raise ValidationError(f"{model.name}: attention_sequence label {label!r} has no attention group")
    ctx = int(context_tokens)
    D, NL = model.hidden_size, model.num_layers
    dense_bpp = _bpp(model.dense_compute_format)
    routed_bpp = _bpp(model.routed_compute_format) if model.routed_compute_format else dense_bpp
    moe_model = (model.num_experts or 1) > 1
    layers: list[LayerSpec] = []
    common: dict[str, Any] = {}

    if family in ("gqa", "mimo_v2"):
        vocab = int(_need(merged, "vocab_size", model.name, where))
        ffn = int(_need(merged, "intermediate_size", model.name, where))
        dense_layers = set(merged.get("dense_layers", [])) if moe_model else set(range(NL))
        if moe_model and family == "gqa":
            raise ValidationError(f"{model.name}: a 'gqa' family entry cannot carry experts")
        for L, label in enumerate(seq):
            grp = groups[label]
            if grp.kind not in ("dense_kv", "window"):
                raise ValidationError(f"{model.name}: family {family} has no operator for {grp.kind!r}")
            swa = grp.kind == "window"
            if family == "mimo_v2" and swa:
                nh = int(_need(merged, "swa_num_attention_heads", model.name, where))
                kvh = int(_need(merged, "swa_num_key_value_heads", model.name, where))
                hd = int(_need(merged, "swa_head_dim", model.name, where))
                vhd = int(_need(merged, "swa_v_head_dim", model.name, where))
                sink = bool(_need(merged, "swa_attention_sink", model.name, where))
            else:
                nh = int(_need(merged, "num_attention_heads", model.name, where))
                kvh = int(_need(merged, "num_key_value_heads", model.name, where))
                hd = int(_need(merged, "head_dim", model.name, where))
                vhd = int(merged.get("v_head_dim", hd))
                sink = bool(merged.get("global_attention_sink", merged.get("attention_sink", False)))
                if "attention_sink" not in merged and "global_attention_sink" not in merged:
                    raise ValidationError(f"{model.name}: attention sink not stated")
            rows = min(grp.window_tokens, ctx) if swa else ctx
            layers.append(LayerSpec(index=L, attention="gqa", rows=rows, entry_bytes=float(grp.entry_bytes),
                                    heads=nh, kv_heads=kvh, head_dim=hd, v_head_dim=vhd, sink=sink,
                                    moe=moe_model and L not in dense_layers))
        common.update(qk_norm=bool(_need(merged, "qk_norm", model.name, where)) if family == "gqa" else False)
        if moe_model:
            common.update(experts=int(model.num_experts), topk=int(model.experts_per_token),
                          moe_ffn=int(_need(merged, "moe_intermediate_size", model.name, where)),
                          shared_experts=int(_need(merged, "shared_experts", model.name, where)),
                          score_function=str(_need(merged, "score_function", model.name, where)),
                          router_bytes_per_param=_bpp(_need(merged, "router_format", model.name, where)))
    elif family == "deepseek_v4":
        vocab = int(_need(merged, "vocab_size", model.name, where))
        for k_ in ("hc_mult", "hc_sinkhorn_iters", "head_dim", "rope_head_dim", "q_lora_rank", "o_groups",
                   "o_lora_rank", "num_attention_heads", "index_heads", "index_head_dim", "index_topk",
                   "window_tokens", "compress_ratios", "moe_intermediate_size", "num_routed_experts",
                   "experts_per_token"):
            _need(merged, k_, model.name, where)
        ratios = list(merged["compress_ratios"])[:NL]
        kv_src = set(merged.get("kv_source_layer_ids", [L for L in range(NL) if ratios[L]]))
        idx_src = merged.get("index_source_layer_ids")
        hash_layers = int(_need(merged, "num_hash_layers", model.name, where))
        engram_layers = set(merged.get("engram_layer_ids", []))
        for L, label in enumerate(seq):
            grp = groups[label]
            ratio = int(ratios[L])
            if grp.kind not in ("window", "compressed_sparse", "compressed_dense"):
                raise ValidationError(f"{model.name}: deepseek_v4 has no operator for {grp.kind!r}")
            sparse = grp.kind == "compressed_sparse"
            scans = sparse and bool(grp.scans_index) and (idx_src is None or L in idx_src)
            win_bytes = float(grp.window_entry_bytes or grp.entry_bytes)
            layers.append(LayerSpec(
                index=L, attention="dsv4", rows=min(int(merged["window_tokens"]), ctx),
                entry_bytes=float(grp.entry_bytes), window_entry_bytes=win_bytes,
                ratio=ratio, kv_source=ratio > 0 and L in kv_src, scans=scans,
                dense_compressed=grp.kind == "compressed_dense", scan_cap=int(grp.index_scan_entries_cap or 0),
                index_entry_bytes=float(grp.index_entry_bytes), moe=True, hash_routed=L < hash_layers,
                engram=L in engram_layers, sink=True))
        common.update(hc_mult=int(merged["hc_mult"]), sinkhorn_iters=int(merged["hc_sinkhorn_iters"]),
                      experts=int(merged["num_routed_experts"]), topk=int(merged["experts_per_token"]),
                      moe_ffn=int(merged["moe_intermediate_size"]),
                      shared_experts=int(_need(merged, "shared_experts", model.name, where)),
                      score_function=str(_need(merged, "score_function", model.name, where)),
                      router_bytes_per_param=_bpp(_need(merged, "router_format", model.name, where)))
        dsv4 = {k_: merged[k_] for k_ in ("head_dim", "rope_head_dim", "q_lora_rank", "o_groups", "o_lora_rank",
                                          "num_attention_heads", "index_heads", "index_head_dim", "index_topk",
                                          "window_tokens")}
        dsv4["index_source_layer_ids"] = sorted(L for L in range(NL) if layers[L].scans)
        dsv4["kv_source_layer_ids"] = sorted(kv_src)
        for k_ in ("candidate_source_layer_id", "candidate_topk_blocks", "candidate_block_size"):
            if k_ in merged:
                dsv4[k_] = merged[k_]
        common["dsv4"] = dsv4
        if engram_layers:
            common["engram"] = dict(layers=sorted(engram_layers),
                                    head_dim=int(_need(merged, "engram_head_dim", model.name, where)),
                                    columns=int(_need(merged, "engram_hash_columns", model.name, where)))
    elif family == "kimi_linear":
        vocab = int(_need(merged, "vocab_size", model.name, where))
        ffn = int(_need(merged, "intermediate_size", model.name, where))
        first_dense = int(_need(merged, "first_k_dense_replace", model.name, where))
        for k_ in ("num_attention_heads", "q_lora_rank", "kv_lora_rank", "qk_nope_head_dim", "qk_rope_head_dim",
                   "v_head_dim", "mla_use_output_gate", "kda_heads", "kda_head_dim", "kda_short_conv_kernel",
                   "kda_full_rank_gate", "moe_intermediate_size", "num_shared_experts", "routed_expert_hidden_size",
                   "latent_moe_use_norm", "score_function", "attn_res_block_size", "router_format"):
            _need(merged, k_, model.name, where)
        for L, label in enumerate(seq):
            grp = groups[label]
            if grp.kind == "recurrent":
                layers.append(LayerSpec(index=L, attention="kda", rows=0, entry_bytes=0.0,
                                        state_bytes=float(grp.recurrent_state_bytes), moe=L >= first_dense))
            elif grp.kind == "dense_mla":
                layers.append(LayerSpec(index=L, attention="mla", rows=ctx, entry_bytes=float(grp.entry_bytes),
                                        heads=int(merged["num_attention_heads"]), moe=L >= first_dense))
            else:
                raise ValidationError(f"{model.name}: kimi_linear has no operator for {grp.kind!r}")
        common.update(experts=int(model.num_experts), topk=int(model.experts_per_token),
                      moe_ffn=int(merged["moe_intermediate_size"]), shared_experts=int(merged["num_shared_experts"]),
                      score_function=str(merged["score_function"]),
                      router_bytes_per_param=_bpp(merged["router_format"]),
                      latent_dim=int(merged["routed_expert_hidden_size"]),
                      latent_norm=bool(merged["latent_moe_use_norm"]),
                      attn_res_block=int(merged["attn_res_block_size"]),
                      mla={k_: merged[k_] for k_ in ("num_attention_heads", "q_lora_rank", "kv_lora_rank",
                                                      "qk_nope_head_dim", "qk_rope_head_dim", "v_head_dim",
                                                      "mla_use_output_gate")},
                      kda={k_: merged[k_] for k_ in ("kda_heads", "kda_head_dim", "kda_short_conv_kernel",
                                                      "kda_full_rank_gate")})
    else:
        raise ValidationError(f"{model.name}: unknown decode-graph family {family!r}")
    if family in ("gqa", "mimo_v2", "kimi_linear"):
        common["ffn"] = ffn
    shape = DecodeShape(name=model.name, family=family, hidden=D, vocab=vocab, layers=tuple(layers),
                        dense_bpp=dense_bpp, routed_bpp=routed_bpp,
                        source=str(entry.get("source", "")), **common)
    _SHAPE_MEMO[key] = shape
    return shape


# ---------------------------------------------------------------------------
# the graph
# ---------------------------------------------------------------------------


class Graph:
    """A DAG of operators.  Insertion order is topological."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}

    def add(self, name: str, deps: list[str | None], *, layer: int, issue: float = 0.0,
            issue_cat: str = "compute_chain", w: float = 0.0, k: float = 0.0, floor: float = 0.0,
            depth: float = 0.0, depth_cat: str = "compute_chain", ctrl: float = 0.0, stream: bool = False,
            kind: str = "op", desc: str = "", **extra: Any) -> str:
        assert name not in self.nodes, name
        deps = [d for d in deps if d]
        for d in deps:
            assert d in self.nodes, (name, d)
        self.nodes[name] = dict(name=name, deps=deps, layer=layer, issue=issue, issue_cat=issue_cat, w=w, k=k,
                                floor=floor, depth=depth, depth_cat=depth_cat, ctrl=ctrl, stream=stream,
                                kind=kind, desc=desc, **extra)
        return name

    def normalise_sweep(self) -> tuple[float, float]:
        """Turn byte weights into fractions of the token's weight and KV sweeps."""
        tw = sum(n["w"] for n in self.nodes.values())
        tk = sum(n["k"] for n in self.nodes.values())
        for n in self.nodes.values():
            n["w"] = n["w"] / tw if tw > 0 else 0.0
            n["k"] = n["k"] / tk if tk > 0 else 0.0
        return tw, tk

    # -- numeric solve at one (W, K): attribution and the path ---------------
    def solve(self, W: float = 0.0, K: float = 0.0, chaining: bool = True) -> dict[str, float]:
        fin: dict[str, float] = {}
        start: dict[str, float] = {}
        crit: dict[str, str | None] = {}
        contrib: dict[str, dict[str, float]] = {}
        for name, n in self.nodes.items():
            deps = n["deps"]
            if deps:
                c = max(deps, key=fin.__getitem__)
                pf, ps = fin[c], max(start[d] for d in deps)
            else:
                c, pf, ps = None, 0.0, 0.0
            parts: dict[str, float] = {}
            wpart = n["w"] * W
            use_floor = n["floor"] > wpart
            sweep = n["floor"] if use_floor else wpart
            kpart = n["k"] * K
            iss = n["issue"] + sweep + kpart
            dep, ctl = n["depth"], n["ctrl"]
            if n["stream"] and chaining and deps:
                s = ps + ctl
                a = s + iss
                if a > pf:
                    parts[n["issue_cat"]] = min(a - pf, iss)
                    if a - pf > iss:
                        parts["control"] = a - pf - iss
                f = max(a, pf) + dep
            else:
                s = pf + ctl
                f = s + iss + dep
                parts["control"] = ctl
                parts[n["issue_cat"]] = parts.get(n["issue_cat"], 0.0) + n["issue"]
                if use_floor:
                    parts["compute_chain"] = parts.get("compute_chain", 0.0) + n["floor"]
                else:
                    parts["weight_sweep"] = parts.get("weight_sweep", 0.0) + wpart
                parts["kv_sweep"] = parts.get("kv_sweep", 0.0) + kpart
            parts[n["depth_cat"]] = parts.get(n["depth_cat"], 0.0) + dep
            fin[name], start[name], crit[name], contrib[name] = f, s, c, parts
        self.fin, self.crit, self.contrib = fin, crit, contrib
        return fin

    def path(self, sink: str) -> list[str]:
        out: list[str] = []
        n: str | None = sink
        while n is not None:
            out.append(n)
            n = self.crit[n]
        return out[::-1]

    def breakdown(self, sink: str) -> dict[str, float]:
        cats = dict.fromkeys(CATS, 0.0)
        for n in self.path(sink):
            for k_, v in self.contrib[n].items():
                cats[k_] = cats.get(k_, 0.0) + v
        return cats

    # -- the fast solve used on every study point --------------------------
    def compile(self, sink: str) -> "CompiledGraph":
        """Flatten the DAG into index arrays for ``CompiledGraph.solve``."""
        nodes = list(self.nodes.values())
        index = {n["name"]: i for i, n in enumerate(nodes)}
        return CompiledGraph(
            deps=tuple(tuple(index[d] for d in n["deps"]) for n in nodes),
            issue=tuple(n["issue"] for n in nodes),
            w=tuple(n["w"] for n in nodes),
            k=tuple(n["k"] for n in nodes),
            floor=tuple(n["floor"] for n in nodes),
            depth=tuple(n["depth"] for n in nodes),
            ctrl=tuple(n["ctrl"] for n in nodes),
            stream=tuple(bool(n["stream"]) for n in nodes),
            comm=tuple(n["kind"] in ("collective", "hop") for n in nodes),
            sink=index[sink],
            recipes=tuple((i, n["recipe"]) for i, n in enumerate(nodes) if n.get("recipe")),
        )

    # -- the envelope over the total sweep ------------------------------------
    def envelope(self, sink: str, kv_share: float, chaining: bool = True) -> list[tuple[float, float, float]]:
        """Lines (c, s, comm) with T(S) = max(c + s S) exactly, for a token
        whose sweep S splits (1 - kv_share) S over the weight reads and
        kv_share S over the KV reads; comm is the collective-and-hop part of c
        on that line.

        Every set kept is the upper hull of its lines over S >= 0; shifting a
        hull by one line keeps it a hull, so only a join of several inputs or a
        node with a lane-walk floor (two alternatives) re-takes it."""

        om, ka = 1.0 - kv_share, kv_share
        nodes = list(self.nodes.values())
        index = {n["name"]: i for i, n in enumerate(nodes)}
        need_start = set()
        if chaining:
            for n in nodes:
                if n["stream"] and n["deps"]:
                    need_start.update(index[d] for d in n["deps"])
        fin: list = [None] * len(nodes)
        start: dict[int, list] = {}
        zero = [(0.0, 0.0, 0.0)]
        for i, n in enumerate(nodes):
            deps = n["deps"]
            if not deps:
                pf = zero
            elif len(deps) == 1:
                pf = fin[index[deps[0]]]
            else:
                pf = _union([fin[index[d]] for d in deps])
            comm = n["kind"] in ("collective", "hop")
            ci, dep, ctl = n["issue"], n["depth"], n["ctrl"]
            cm = (ci + dep) if comm else 0.0
            ks = n["k"] * ka
            sw = n["w"] * om + ks
            floor = n["floor"]
            if n["stream"] and chaining and deps:
                if len(deps) == 1:
                    ps = start[index[deps[0]]]
                else:
                    ps = _union([start[index[d]] for d in deps])
                s_ = [(c + ctl, w, m) for c, w, m in ps]
                a = [(c + ci, w + sw, m + cm) for c, w, m in s_]
                if floor > 0:
                    a += [(c + ci + floor, w + ks, m + cm) for c, w, m in s_]
                f = [(c + dep, w, m) for c, w, m in _hull(a + pf)]
            else:
                base = ctl + ci + dep
                f = [(c + base, w + sw, m + cm) for c, w, m in pf]
                if floor > 0:
                    f = _hull(f + [(c + base + floor, w + ks, m + cm) for c, w, m in pf])
                s_ = None
                if i in need_start:
                    s_ = [(c + ctl, w, m) for c, w, m in pf]
            if i in need_start:
                start[i] = s_
            fin[i] = f
        return fin[index[sink]]


@dataclass(frozen=True)
class CompiledGraph:
    """A priced DAG as flat arrays: one longest-path pass per sweep point."""
    deps: tuple
    issue: tuple
    w: tuple
    k: tuple
    floor: tuple
    depth: tuple
    ctrl: tuple
    stream: tuple
    comm: tuple
    sink: int
    recipes: tuple = ()

    def repriced(self, pricer: "Pricer") -> "CompiledGraph":
        """The same structure with every recipe node re-priced (another microbatch or lane width)."""
        if not self.recipes:
            return self
        issue, depth, floor = list(self.issue), list(self.depth), list(self.floor)
        for i, recipe in self.recipes:
            issue[i], depth[i], floor[i], _ = pricer.price(recipe)
        return replace(self, issue=tuple(issue), depth=tuple(depth), floor=tuple(floor))

    def critical(self, W: float, K: float) -> float:
        """The critical path alone (``solve(W, K)[0]``), without the attribution."""
        n = len(self.deps)
        fin = [0.0] * n
        st = [0.0] * n
        deps_, issue_, w_, k_, floor_ = self.deps, self.issue, self.w, self.k, self.floor
        depth_, ctrl_, stream_ = self.depth, self.ctrl, self.stream
        for i in range(n):
            deps = deps_[i]
            if len(deps) == 1:
                pf = fin[deps[0]]
            elif deps:
                pf = max([fin[d] for d in deps])
            else:
                pf = 0.0
            wp = w_[i] * W
            fl = floor_[i]
            iss = issue_[i] + (wp if wp >= fl else fl) + k_[i] * K
            if stream_[i] and deps:
                ps = st[deps[0]] if len(deps) == 1 else max([st[d] for d in deps])
                s0 = ps + ctrl_[i]
                a = s0 + iss
                st[i] = s0
                fin[i] = (a if a > pf else pf) + depth_[i]
            else:
                s0 = pf + ctrl_[i]
                st[i] = s0
                fin[i] = s0 + iss + depth_[i]
        return fin[self.sink]

    def solve(self, W: float, K: float, chaining: bool = True) -> tuple[float, float, float]:
        """(critical path, its collective-and-hop part, its sweep part) at sweeps W and K.

        The same semantics as ``Graph.solve``: a node starts when its latest
        input finishes, a streamable node may instead chase its producers'
        starts, and its issue is max(lane-walk floor, weight share) + KV share."""
        n = len(self.deps)
        fin = [0.0] * n
        fcomm = [0.0] * n
        fsweep = [0.0] * n
        st = [0.0] * n
        scomm = [0.0] * n
        ssweep = [0.0] * n
        deps_, issue_, w_, k_, floor_ = self.deps, self.issue, self.w, self.k, self.floor
        depth_, ctrl_, stream_, comm_ = self.depth, self.ctrl, self.stream, self.comm
        for i in range(n):
            deps = deps_[i]
            if deps:
                c = deps[0]
                pf = fin[c]
                for d in deps:
                    if fin[d] > pf:
                        pf, c = fin[d], d
                pc, psw = fcomm[c], fsweep[c]
            else:
                pf = pc = psw = 0.0
            wp = w_[i] * W
            fl = floor_[i]
            sw = (wp if wp >= fl else 0.0) + k_[i] * K
            iss = issue_[i] + (wp if wp >= fl else fl) + k_[i] * K
            own_comm = (issue_[i] + depth_[i]) if comm_[i] else 0.0
            ctl, dep = ctrl_[i], depth_[i]
            if stream_[i] and chaining and deps:
                sd = deps[0]
                ps = st[sd]
                for d in deps:
                    if st[d] > ps:
                        ps, sd = st[d], d
                s0 = ps + ctl
                a = s0 + iss
                st[i], scomm[i], ssweep[i] = s0, scomm[sd], ssweep[sd]
                if a > pf:
                    fin[i] = a + dep
                    fcomm[i] = scomm[sd] + own_comm
                    fsweep[i] = ssweep[sd] + sw
                else:
                    fin[i] = pf + dep
                    fcomm[i] = pc + own_comm
                    fsweep[i] = psw
            else:
                s0 = pf + ctl
                st[i], scomm[i], ssweep[i] = s0, pc, psw
                fin[i] = s0 + iss + dep
                fcomm[i] = pc + own_comm
                fsweep[i] = psw + sw
        j = self.sink
        return fin[j], fcomm[j], fsweep[j]


def _slope_key(t: tuple) -> tuple:
    return (t[1], -t[0])


def _hull(lines: list) -> list:
    """Upper envelope of c + s x over x >= 0 (exact convex-hull trick)."""
    if len(lines) <= 1:
        return lines
    lines = sorted(lines, key=_slope_key)
    hull: list = []
    last = None
    for t in lines:
        if t[1] == last:
            continue                      # same slope, lower intercept
        last = t[1]
        while hull and hull[-1][0] <= t[0]:
            hull.pop()                    # steeper and no lower at x = 0: dominated for x >= 0
        while len(hull) >= 2:
            a, b = hull[-2], hull[-1]
            if (a[0] - t[0]) * (b[1] - a[1]) <= (a[0] - b[0]) * (t[1] - a[1]):
                hull.pop()                # t overtakes a no later than b does
            else:
                break
        hull.append(t)
    return hull


def _union(sets: list[list]) -> list:
    if len(sets) == 1:
        return sets[0]
    out: list = []
    for s in sets:
        out.extend(s)
    return _hull(out)


def envelope_value(lines: list, S: float) -> tuple[float, float]:
    """(T, communication part of T) at total sweep S."""
    best, comm = -1.0, 0.0
    for c, s, m in lines:
        v = c + s * S
        if v > best:
            best, comm = v, m
    return best, comm


def envelope_point(lines: list, S: float) -> tuple[float, float, float]:
    """(T, communication part of T, sweep coefficient of the binding line) at total sweep S."""
    best, comm, slope = -1.0, 0.0, 0.0
    for c, s, m in lines:
        v = c + s * S
        if v > best:
            best, comm, slope = v, m, s
    return best, comm, slope


def kv_share_bucket(weight_s: float, kv_s: float) -> float:
    """The KV share of the sweep, quantised to 1/16 decade of the K:W ratio.

    The service time is distributed over the operator nodes by the bytes each
    reads; this share only decides how much of it lands on KV-reading nodes
    versus weight-reading ones.  Quantising it lets one solved envelope serve
    every design of a sweep; the largest error is a 7.5% shift of that split,
    never of the sweep total."""
    if kv_s <= 0 or not math.isfinite(kv_s):
        return 0.0
    if weight_s <= 0 or not math.isfinite(weight_s):
        return 1.0
    rho = 10.0 ** (round(math.log10(kv_s / weight_s) * 16.0) / 16.0)
    return rho / (1.0 + rho)


# ---------------------------------------------------------------------------
# fabrics
# ---------------------------------------------------------------------------


def mesh_dims(p: int) -> tuple[int, int]:
    if p <= 1:
        return 1, 1
    r = max(1, int(math.isqrt(p)))
    return r, -(-p // r)


@dataclass(frozen=True)
class Level:
    """One level of a collective: p nodes, per-traversal latency, diameter, bandwidths."""
    p: int
    alpha: float
    D: float
    Dsum: float
    B_link: float
    B_node: float
    mesh_like: bool
    name: str

    def price(self, op: str, n: float, algo: str) -> tuple[float, float]:
        """(latency_s, bytes_s).  n: all_reduce -> one node's partial; all_gather -> the gathered vector."""
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


def direct_level(p: int, alpha: float, B_link: float, links_per_node: float, topo: str, name: str) -> Level:
    """A direct network embedding of p consecutive nodes: chain, ring, mesh, torus or full crossbar."""
    if topo in ("chain", "ring"):
        D = p - 1 if topo == "chain" else max(1, p // 2)
        Dsum = p - 1 if topo == "chain" else max(1, p // 2) + max(0, math.ceil(math.log2(p)) - 1)
    elif topo in ("mesh", "torus"):
        r, c = mesh_dims(p)
        D = (r - 1) + (c - 1) if topo == "mesh" else r // 2 + c // 2
        Dsum = max(D, math.ceil(math.log2(max(2, p))))
    elif topo == "full":
        D, Dsum = 1, math.ceil(math.log2(max(2, p)))
    else:
        raise ValidationError(f"unknown direct topology {topo!r}")
    return Level(p=p, alpha=alpha, D=max(1, D), Dsum=max(1, Dsum), B_link=B_link,
                 B_node=B_link * links_per_node, mesh_like=topo != "full", name=name)


class Fabric:
    """The collectives and hops of one topology, on the links it names.

    ``inner`` carries traffic inside a domain of ``domain`` partitions and
    ``outer`` between domains.  A link listed in
    ``serial_latency.hardware_links`` is priced as hardware traversals with the
    reduction algorithm searched; any other link is priced at its measured
    small-message floor per switch tier (``Technology.collective_traversals``).
    """

    def __init__(self, technology: Any, *, inner: str, outer: str, domain: int, partitions: int,
                 group: int, algorithm: str = "best") -> None:
        self.t = technology
        self.inner, self.outer = inner, outer
        self.domain, self.partitions, self.group = max(1, domain), partitions, group
        self.algorithm = algorithm
        self.hw = technology.raw.get("serial_latency", {}).get("hardware_links", {})
        self.regions_per_wafer = max(1, domain)
        self._memo: dict[tuple, Any] = {}

    # -- helpers -----------------------------------------------------------
    def _hw(self, link: str) -> Mapping[str, Any] | None:
        node = self.hw.get(link)
        return node if isinstance(node, Mapping) and "value" in node else None

    def _level(self, link: str, p: int) -> Level:
        key = ("level", link, p)
        hit = self._memo.get(key)
        if hit is None:
            hit = self._memo[key] = self._level_uncached(link, p)
        return hit

    def _level_uncached(self, link: str, p: int) -> Level:
        hop, bw = self.t.link(link)
        spec = self._hw(link)
        assert spec is not None
        topo = str(spec["value"])
        lpn = float(spec.get("links_per_node", 4))
        scope = spec.get("bandwidth_scope", "per_link")
        if scope == "per_wafer":
            b_link = bw.value / self.regions_per_wafer / lpn
        elif scope == "per_node":
            b_link = bw.value / lpn
        else:
            b_link = bw.value
        return direct_level(p, hop.value, b_link, min(lpn, max(1, p - 1)) if topo == "full" else lpn,
                            topo if p > 1 else "full", link)

    def _measured(self, link: str, op: str, n: float, p: int) -> tuple[float, float]:
        hop, bw = self.t.link(link)
        lat = self.t.collective_traversals(link, p) * hop.value
        if op == "all_reduce":
            byt = 2.0 * (p - 1) / p * n / max(bw.value, 1e-30)
        else:
            byt = (p - 1) / p * n / max(bw.value, 1e-30)
        return lat, byt

    def _one_level(self, link: str, op: str, n: float, p: int, algo: str) -> tuple[float, float, str]:
        if p <= 1:
            return 0.0, 0.0, "none"
        if self._hw(link) is None:
            lat, byt = self._measured(link, op, n, p)
            return lat, byt, "measured_floor"
        lv = self._level(link, p)
        best = None
        for a in (ALGORITHMS if algo == "best" else (algo,)):
            lat, byt = lv.price(op, n, a)
            if best is None or lat + byt < best[0] + best[1]:
                best = (lat, byt, a)
        return best

    # -- collectives ---------------------------------------------------------
    def collective(self, op: str, n: float, span: int) -> dict[str, Any]:
        """One all_reduce / all_gather over ``span`` partitions of the group."""
        key = ("coll", op, n, span)
        hit = self._memo.get(key)
        if hit is None:
            hit = self._memo[key] = self._collective(op, n, span)
        return hit

    def _collective(self, op: str, n: float, span: int) -> dict[str, Any]:
        if span <= 1:
            return dict(latency_s=0.0, bytes_s=0.0, algo="none", where="")
        inside = min(span, self.domain)
        across = math.ceil(span / self.domain)
        if across <= 1:
            lat, byt, a = self._one_level(self.inner, op, n, inside, self.algorithm)
            return dict(latency_s=lat, bytes_s=byt, algo=a, where=f"{span} x {self.inner}: {a}")
        # hierarchical: reduce (or gather) in the domain, across domains, broadcast in the domain
        l1, b1, a1 = self._one_level(self.inner, op, n, inside, self.algorithm)
        l2, b2, a2 = self._one_level(self.outer, op, n, across, self.algorithm)
        if op == "all_reduce":
            lat, byt = 2 * l1 + l2, 2 * b1 + b2
        else:
            lat, byt = l1 + l2, b1 + b2
        return dict(latency_s=lat, bytes_s=byt, algo="hierarchical",
                    where=f"{inside} x {self.inner} ({a1}) then {across} x {self.outer} ({a2})")

    def all_to_all(self, n_per_node: float, span: int) -> dict[str, Any]:
        """Expert dispatch or combine: every node sends its tokens' copies to their experts."""
        if span <= 1:
            return dict(latency_s=0.0, bytes_s=0.0, algo="none", where="")
        link = self.outer if span > self.domain else self.inner
        if self._hw(link) is None:
            hop, bw = self.t.link(link)
            lat = self.t.collective_traversals(link, span) * hop.value
            byt = n_per_node / max(bw.value, 1e-30)
        else:
            lv = self._level(link, min(span, self.domain) if link == self.inner else math.ceil(span / self.domain))
            lat = lv.D * lv.alpha
            byt = n_per_node / lv.B_node
        return dict(latency_s=lat, bytes_s=byt, algo="all_to_all", where=f"{span} partitions over {link}")

    def hop(self, level: str, payload: float) -> dict[str, Any]:
        """A point-to-point pipeline hop on the inner or outer link."""
        link = self.inner if level == "inner" else self.outer
        hop, bw = self.t.link(link)
        spec = self._hw(link)
        if spec is None:
            return dict(latency_s=hop.value, bytes_s=payload / max(bw.value, 1e-30), where=link)
        lv = self._level(link, 2)
        trav = 1
        if level == "inner" and str(spec["value"]) == "mesh" and self.group > 1:
            trav = max(1, mesh_dims(self.group)[0])     # consecutive groups sit a group-width apart
        return dict(latency_s=trav * hop.value, bytes_s=payload / lv.B_link, where=f"{link} x{trav}")


# ---------------------------------------------------------------------------
# the machine a graph is priced for
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MachineSpec:
    """Everything about a machine that changes the priced graph of one token.

    Pipeline-stage boundaries are NOT part of the graph: a token crosses every
    boundary on its residual stream, so each boundary adds its hop in series
    and ``stage_hops`` prices them separately.  That keeps one graph serving
    every stage count of a sizing sweep."""
    family: str                 # rom | gpu
    group: int                  # tensor group
    microbatch: float
    clock_hz: float
    su_width: int = 16
    kv_in_hbm: bool = False
    multi_stage: bool = False   # Engram rows must be delivered to their layer's stage
    expert_parallel: bool = False
    ep_span: int = 1
    ep_tokens_per_node: float = 0.0


class Pricer:
    """Everything about a node's cost that depends on the users per stage, the
    stream-unit width or the fabric.

    A node records a *recipe* -- what it is (a vector of n elements, a
    reduction, a select, a collective of p bytes per user, ...) -- and this
    turns it into (issue, depth, floor) seconds.  The graph is built once per
    structure and re-priced for every microbatch and lane width of a sweep."""

    def __init__(self, m: MachineSpec, rom: RomDatapath, fabric: "Fabric | None", *, microbatch: float,
                 su_width: int):
        self.m, self.r, self.fab = m, rom, fabric
        self.mb, self.su, self.clock = microbatch, su_width, m.clock_hz
        self.rom = m.family == "rom"

    def cyc(self, c: float) -> float:
        return c / self.clock

    def vissue(self, n: float) -> float:
        return self.cyc(math.ceil(n * self.mb / self.su)) if self.rom else 0.0

    def price(self, recipe: tuple) -> tuple[float, float, float, dict | None]:
        """(issue, depth, floor, fabric record or None)."""
        kind = recipe[0]
        r = self.r
        if kind == "vec":
            return self.vissue(recipe[1]), self.cyc(recipe[2]), 0.0, None
        if kind == "red":
            n, segments = recipe[1], recipe[2]
            lanes = max(1, min(self.su, n // max(1, segments)))
            d = r.red_tail + (r.fadd * math.ceil(math.log2(lanes)) if lanes > 1 else 0)
            return self.vissue(n), self.cyc(d), 0.0, None
        if kind == "mv":
            return 0.0, self.cyc(recipe[2]), self.cyc(recipe[1] * math.ceil(self.mb)), None
        if kind == "sel":
            n, k = recipe[1], recipe[2]
            best = None
            P = 1
            while P <= r.select_units:
                stream = math.ceil(n / P) * self.mb
                tail = (k + r.select_extra) + (min(k, n) + math.ceil(math.log2(P)) if P > 1 else min(k, n) - 1)
                if best is None or stream + tail < best[0] + best[1]:
                    best = (stream, tail, P)
                P *= 2
            return self.cyc(best[0]), self.cyc(best[1]), 0.0, {"units": best[2]}
        if kind == "sink":
            nits, half, pre = recipe[1], recipe[2], recipe[3]
            return 0.0, self.cyc(pre + 2 * nits * max(half, math.ceil(self.mb))), 0.0, None
        if kind == "coll":
            op, payload, span = recipe[1], recipe[2], recipe[3]
            rec = self.fab.collective(op, payload * self.mb, span)
            red = self.cyc(r.fadd * math.ceil(math.log2(span))) if (op == "all_reduce" and self.rom) else 0.0
            return rec["bytes_s"], rec["latency_s"] + red, 0.0, dict(rec, payload_bytes=payload * self.mb,
                                                                      latency_s=rec["latency_s"] + red)
        if kind == "a2a":
            nbytes = recipe[1] * self.mb
            rec = self.fab.all_to_all(nbytes, self.m.ep_span)
            return rec["bytes_s"], rec["latency_s"], 0.0, dict(rec, payload_bytes=nbytes)
        if kind == "hop":
            rec = self.fab.hop(recipe[1], recipe[2] * self.mb)
            return rec["bytes_s"], rec["latency_s"], 0.0, dict(rec, payload_bytes=recipe[2] * self.mb,
                                                               algo="point_to_point")
        raise ValidationError(f"unknown node recipe {kind!r}")


class Ops:
    """Operator helpers for one machine: each records its recipe and its price."""

    def __init__(self, g: Graph, m: MachineSpec, rom: RomDatapath, gpu: GpuDatapath, fabric: Fabric | None):
        self.g, self.m, self.r, self.gp, self.fab = g, m, rom, gpu, fabric
        self.mb = m.microbatch
        self.rom = m.family == "rom"
        self.census: list[dict[str, Any]] = []
        self.pricer = Pricer(m, rom, fabric, microbatch=m.microbatch, su_width=m.su_width)

    def cyc(self, c: float) -> float:
        return c / self.m.clock_hz

    @property
    def gap(self) -> float:
        return self.gp.kernel_gap_s

    @property
    def ctrl(self) -> float:
        return self.cyc(self.r.seq_gap) if self.rom else 0.0

    @property
    def bctrl(self) -> float:
        return self.cyc(self.r.seq_gap + self.r.idle_reg) if self.rom else 0.0

    def _add(self, name: str, deps: list, layer: int, recipe: tuple, **kw: Any) -> str:
        issue, depth, floor, _rec = self.pricer.price(recipe)
        return self.g.add(name, deps, layer=layer, issue=issue, depth=depth, floor=floor, recipe=recipe, **kw)

    def join(self, name: str, deps: list, layer: int) -> str:
        return self.g.add(name, deps, layer=layer, kind="join")

    def ew(self, name: str, deps: list, n: float, depth_cycles: float, layer: int, stream: bool = True,
           kernel: bool = False, gpu_extra: float = 0.0, desc: str = "") -> str:
        if self.rom:
            return self._add(name, deps, layer, ("vec", n, depth_cycles),
                             ctrl=self.ctrl if stream else self.bctrl, stream=stream, kind="vector", desc=desc)
        return self.g.add(name, deps, layer=layer, depth=(self.gap if kernel else 0.0) + gpu_extra,
                          depth_cat="kernel_launch" if kernel else "compute_chain", kind="vector", desc=desc)

    def reduce(self, name: str, deps: list, n: float, layer: int, segments: int = 1, stream: bool = True,
               kernel: bool = False, desc: str = "") -> str:
        if self.rom:
            return self._add(name, deps, layer, ("red", n, segments),
                             ctrl=self.ctrl if stream else self.bctrl, stream=stream, kind="reduce", desc=desc)
        return self.ew(name, deps, n, 0, layer, kernel=kernel, desc=desc)

    def rmsnorm(self, pre: str, deps: list, n: float, layer: int, segments: int = 1, kernel: bool = True) -> str:
        r = self.r
        a = self.reduce(f"{pre}.sumsq", deps, n, layer, segments, kernel=kernel, desc=f"sum of squares over {n}")
        b = self.ew(f"{pre}.rsqrt", [a], segments, 2 * r.fadd + r.su_rsqrt, layer, stream=False,
                    desc="mean, +eps, rsqrt")
        return self.ew(f"{pre}.scale", [b], n, r.su_none + r.fadd, layer, stream=False, desc="x * rstd * w")

    def actquant(self, name: str, deps: list, n: float, layer: int) -> str:
        return self.ew(name, deps, n, self.r.su_none + self.r.actquant, layer, desc="FP8 activation quantiser")

    def matvec(self, name: str, deps: list, layer: int, *, n_out: float, k: float, bytes_: float,
               fmt: str = "fp8", desc: str = "") -> str:
        """n_out x k is the FULL matrix; its bytes set its share of the sweep."""
        if self.rom:
            r = self.r
            blocks = math.ceil(k / 32)
            levels = math.ceil(math.log2(max(1, blocks / r.interleave)))
            depth = r.me_lat + r.me_tree * levels + (r.blockdot if fmt in ("fp8", "fp4") else 0)
            return self._add(name, deps, layer, ("mv", r.interleave * min(r.interleave, blocks), depth),
                             w=bytes_, ctrl=self.bctrl, kind="matvec",
                             desc=desc or f"[{n_out:.0f}, {k:.0f}] {fmt}")
        return self.g.add(name, deps, layer=layer, w=bytes_, depth=self.gap, depth_cat="kernel_launch",
                          kind="matvec", desc=desc or f"[{n_out:.0f}, {k:.0f}] {fmt} GEMV kernel")

    def kvscan(self, name: str, deps: list, layer: int, *, kv_bytes: float, depth_cycles: float,
               kernel: bool = True, desc: str = "") -> str:
        if self.rom:
            return self.g.add(name, deps, layer=layer, k=kv_bytes, depth=self.cyc(depth_cycles), ctrl=self.bctrl,
                              kind="kvscan", desc=desc)
        return self.g.add(name, deps, layer=layer, k=kv_bytes, depth=self.gap if kernel else 0.0,
                          depth_cat="kernel_launch" if kernel else "compute_chain", kind="kvscan", desc=desc)

    def select_local(self, name: str, deps: list, layer: int, *, n: int, k: int, desc: str = "") -> str:
        if not self.rom:
            return self.g.add(name, deps, layer=layer, depth=self.gap, depth_cat="kernel_launch", kind="select",
                              desc=desc or f"top-{k} of {n} kernel")
        units = self.pricer.price(("sel", n, k))[3]["units"]
        return self._add(name, deps, layer, ("sel", n, k), ctrl=self.bctrl, kind="select",
                         desc=desc or f"top-{k} of {n} on {units} select units + merge")

    def select_final(self, name: str, deps: list, layer: int, *, k: int, ways: int, ascending: bool,
                     desc: str = "") -> str:
        if not self.rom:
            return self.g.add(name, deps, layer=layer, depth=self.gap if ways > 1 else 0.0,
                              depth_cat="kernel_launch", kind="select", desc=desc or f"{ways}-way merge")
        merge = (k + math.ceil(math.log2(ways))) if ways > 1 else 0
        order = (2 * k + self.r.select_extra + k - 1) if ascending else 0
        return self.g.add(name, deps, layer=layer, depth=self.cyc(merge + order), ctrl=self.bctrl, kind="select",
                          desc=desc or f"{ways}-way merge" + (" + ascending-index pass" if ascending else ""))

    def sinkhorn(self, name: str, deps: list, layer: int, *, iterations: int, desc: str) -> str:
        r = self.r
        if self.rom:
            half = 3 * r.fadd + r.fadd + r.fdiv     # 4-term sequential sum, +eps, one pipelined divide
            return self._add(name, deps, layer, ("sink", iterations, half, 2 + r.fadd + r.su_exp),
                             ctrl=self.bctrl, kind="sinkhorn", desc=desc)
        gstep = (4 * self.gp.fp32_dep_cycles + self.gp.fp32_div_cycles) / self.m.clock_hz
        return self.g.add(name, deps, layer=layer, depth=2 * iterations * gstep, kind="sinkhorn", desc=desc)

    def gather(self, name: str, deps: list, layer: int, desc: str) -> str:
        if not self.rom:
            return self.join(name, deps, layer)
        lat = self.r.hbm_gather_s if self.m.kv_in_hbm else self.r.rom_row_s
        return self.g.add(name, deps, layer=layer, depth=lat, ctrl=self.ctrl, kind="gather", desc=desc)

    def _comm(self, name: str, deps: list, layer: int, recipe: tuple, *, kind: str, issue_cat: str,
              depth_cat: str, desc: str, op: str, span: int) -> str:
        issue, depth, _floor, rec = self.pricer.price(recipe)
        node = self.g.add(name, deps, layer=layer, issue=issue, issue_cat=issue_cat, depth=depth,
                          depth_cat=depth_cat, ctrl=self.ctrl, kind=kind, desc=desc, recipe=recipe)
        self.census.append(dict(name=name, layer=layer, op=op, span=span, payload_bytes=rec["payload_bytes"],
                                latency_s=rec["latency_s"], bytes_s=rec["bytes_s"], algo=rec["algo"],
                                where=rec["where"], desc=desc, recipe=recipe))
        return node

    def collective(self, name: str, deps: list, layer: int, *, op: str, payload: float, desc: str,
                   span: int | None = None) -> str | None:
        span = span or self.m.group
        if span <= 1 or self.fab is None:
            return None
        return self._comm(name, deps, layer, ("coll", op, payload, span), kind="collective",
                          issue_cat="collective_bytes", depth_cat="collective_latency", desc=desc, op=op, span=span)

    def all_to_all(self, name: str, deps: list, layer: int, *, bytes_per_node: float, desc: str) -> str | None:
        if self.fab is None or self.m.ep_span <= 1:
            return None
        per_mb = bytes_per_node / self.mb if self.mb > 0 else bytes_per_node
        return self._comm(name, deps, layer, ("a2a", per_mb), kind="collective", issue_cat="collective_bytes",
                          depth_cat="collective_latency", desc=desc, op="all_to_all", span=self.m.ep_span)

    def hop(self, name: str, deps: list, layer: int, *, payload: float, level: str, desc: str) -> str | None:
        if self.fab is None:
            return None
        return self._comm(name, deps, layer, ("hop", level, payload), kind="hop", issue_cat="pipeline_hops",
                          depth_cat="pipeline_hops", desc=desc, op="hop", span=2)


# ---------------------------------------------------------------------------
# graph builders
# ---------------------------------------------------------------------------


def build_graph(shape: DecodeShape, ctx: int, ops: Ops) -> str:
    """Build one token's DAG into ``ops.g``; returns the sink node."""
    g, m, r = ops.g, ops.m, ops.r
    D, NL = shape.hidden, len(shape.layers)
    HC = shape.hc_mult
    G = m.group
    ops.sel = {}

    tok = ops.join("token", [], -1)
    emb = g.add("embed", [tok], layer=-1, depth=ops.cyc(r.su_none) + r.rom_row_s if ops.rom else ops.gap,
                depth_cat="compute_chain" if ops.rom else "kernel_launch",
                ctrl=ops.bctrl, desc="embedding row read" + (" + 4-copy expand" if HC > 1 else ""))
    eng: dict[int, str] = {}
    for L in shape.engram.get("layers", ()):
        hd, cols = shape.engram["head_dim"], shape.engram["columns"]
        h = g.add(f"E{L}.hash", [tok], layer=L, depth=ops.cyc(r.engram_hash) if ops.rom else ops.gap,
                  ctrl=ops.bctrl, desc="Engram hash columns")
        rr = g.add(f"E{L}.gather", [h], layer=L, depth=(r.rom_row_s + ops.cyc(r.su_none)) if ops.rom else 0.0,
                   ctrl=ops.ctrl, desc="Engram table rows (token-addressed)")
        kv = ops.matvec(f"E{L}.wkv", [rr], L, n_out=(HC + 1) * D, k=cols * hd, bytes_=(HC + 1) * D * cols * hd,
                        desc="Engram wkv")
        kn = ops.rmsnorm(f"E{L}.knorm", [kv], HC * D, L, segments=HC)
        eng[L] = kn
        if m.multi_stage:
            eng[L] = ops.hop(f"E{L}.deliver", [kn], L, payload=(HC + 1) * D * 2, level="outer",
                             desc="Engram keys + value to the layer's stage (prefetchable)") or kn

    h, pre_ready = emb, emb
    blocks: list[str] = []
    for spec in shape.layers:
        L = spec.index
        if shape.attn_res_block:
            # block attention-residual: softmax-weighted mix over the block's earlier outputs
            nb = min(shape.attn_res_block, len(blocks) + 1)
            s = ops.reduce(f"L{L}.ares.score", [h], nb * D, L, segments=nb, kernel=True, desc="query . block outputs")
            e = ops.ew(f"L{L}.ares.softmax", [s], nb, r.su_exp + r.fadd * max(1, nb - 1) + r.su_recip, L,
                       stream=False, desc="softmax over block outputs")
            h = ops.ew(f"L{L}.ares.mix", [e, h], nb * D, r.su_none + r.fadd * max(1, math.ceil(math.log2(nb))), L,
                       stream=False, desc="weighted sum of block outputs")
        if spec.engram and L in eng:
            hh = ops.reduce(f"L{L}.eng.hh", [h], HC * D, L, segments=HC, kernel=True)
            dot = ops.reduce(f"L{L}.eng.dot", [h, eng[L]], HC * D, L, segments=HC, desc="(h*w).k per copy")
            s = ops.ew(f"L{L}.eng.gate", [hh, dot], HC, r.su_rsqrt + 3 * r.fadd + r.su_none + r.fsqrt + r.su_sigm,
                       L, stream=False, desc="rsqrt, scale, signed sqrt, sigmoid")
            h = ops.ew(f"L{L}.eng.add", [s, eng[L]], HC * D, r.su_none + r.fadd, L, stream=False)
        for sub in ("attn", "ffn"):
            P = f"L{L}.{sub}"
            res = h
            if HC > 1:
                ss = ops.reduce(f"{P}.hc.sumsq", [res], HC * D, L, kernel=True)
                rs = ops.ew(f"{P}.hc.rsqrt", [ss], 1, 2 * r.fadd + r.su_rsqrt, L, stream=False)
                fn = ops.matvec(f"{P}.hc.fn", [res], L, n_out=6 * HC, k=HC * D, bytes_=6 * HC * HC * D * 4,
                                fmt="fp32", desc="hyper-connection mixes, FP32, replicated on every die")
                mx = ops.ew(f"{P}.hc.pre_post", [fn, rs], 6 * HC, 3 * r.fadd + r.su_sigm, L, stream=False,
                            kernel=True, desc="mixes*r, scale+base, sigmoid pre/post")
                nits = shape.sinkhorn_iters
                sk = ops.sinkhorn(f"{P}.hc.sinkhorn", [mx], L, iterations=nits,
                                  desc=f"4x4 softmax + {nits} Sinkhorn iterations ({2 * nits} dependent "
                                       f"normalisations)")
                x = ops.ew(f"{P}.hc_pre", [h, pre_ready], HC * D, r.su_none + 3 * r.fadd, L,
                           desc="collapse the copies with the pending pre mix")
                x = ops.rmsnorm(f"{P}.norm", [x], D, L, kernel=False)
            else:
                x = ops.rmsnorm(f"{P}.norm", [h], D, L)
            xq = ops.actquant(f"{P}.quant", [x], D, L) if shape.dense_bpp <= 1.0 else x
            if sub == "attn":
                y = _attention(ops, shape, spec, x, xq, ctx)
            else:
                y = _ffn(ops, shape, spec, x, xq, tok)
            if HC > 1:
                h = ops.ew(f"{P}.hc_post", [y, sk, res], HC * D, r.su_none + 4 * r.fadd, L, stream=False,
                           kernel=True, desc="post*y + comb.res (4-term sums)")
                pre_ready = mx
            else:
                h = ops.ew(f"{P}.residual", [y, res], D, r.su_none + r.fadd, L, stream=False, kernel=True,
                           desc="residual add")
        if shape.attn_res_block:
            blocks.append(h)
            if len(blocks) >= shape.attn_res_block:
                blocks = []
    # head
    if HC > 1:
        x = ops.ew("head.hc_pre", [h, pre_ready], HC * D, r.su_none + 3 * r.fadd, NL, kernel=True)
        x = ops.rmsnorm("head.norm", [x], D, NL, kernel=False)
    else:
        x = ops.rmsnorm("head.norm", [h], D, NL)
    V = shape.vocab
    lg = ops.matvec("head.lm_head", [x], NL, n_out=V, k=D, bytes_=V * D * shape.dense_bpp,
                    desc=f"lm_head [{V}, {D}], vocabulary split {G} ways")
    am = ops.reduce("head.argmax", [lg], math.ceil(V / max(1, G)), NL, kernel=True, desc="local argmax")
    am = ops.collective("head.argmax_merge", [am], NL, op="all_gather", payload=8,
                        desc="best {logit, id} per partition") or am
    return am


def _attention(ops: Ops, shape: DecodeShape, spec: LayerSpec, x: str, xq: str, ctx: int) -> str:
    if spec.attention == "gqa":
        return _gqa(ops, shape, spec, xq)
    if spec.attention == "mla":
        return _mla(ops, shape, spec, xq)
    if spec.attention == "kda":
        return _kda(ops, shape, spec, xq)
    if spec.attention == "dsv4":
        return _dsv4(ops, shape, spec, xq, ctx)
    raise ValidationError(f"no attention operator {spec.attention!r}")


def _softmax_pv(ops: Ops, P: str, L: int, sco: str, heads: int, rows: int, hd: int, vhd: int, kv_v: float,
                sink: bool, extra_dep: list | None = None) -> str:
    r = ops.r
    mx = ops.reduce(f"{P}.max", [sco], heads * rows, L, segments=heads)
    ex = ops.ew(f"{P}.exp", [mx], heads * rows, r.fadd + r.su_exp, L, stream=False, desc="exp(s - max)")
    den = ops.reduce(f"{P}.den", [ex], heads * rows, L, segments=heads)
    if sink:
        den = ops.ew(f"{P}.sink", [mx, den], heads, r.fadd + r.su_exp + r.fadd, L, stream=False,
                     desc="+ exp(sink - max)")
    pv = ops.kvscan(f"{P}.pv", [ex], L, kv_bytes=kv_v, kernel=False,
                    depth_cycles=r.me_lat + r.me_tree * math.ceil(math.log2(max(1, rows / 16 / r.interleave))),
                    desc="P x V")
    return ops.ew(f"{P}.normalize", [pv, den] + (extra_dep or []), heads * vhd, r.su_none + r.fdiv + r.fadd, L,
                  stream=False, kernel=True, desc="acc / den (flash-decode combine on a GPU)")


def _gqa(ops: Ops, shape: DecodeShape, spec: LayerSpec, xq: str) -> str:
    r, G, L, D = ops.r, ops.m.group, spec.index, shape.hidden
    P = f"L{L}.attn"
    NH, KV, HD, VHD = spec.heads, spec.kv_heads, spec.head_dim, spec.v_head_dim
    hpd, kpd = math.ceil(NH / G), math.ceil(KV / G)
    n_out = NH * HD + KV * HD + KV * VHD
    qkv = ops.matvec(f"{P}.qkv", [xq], L, n_out=n_out, k=D, bytes_=n_out * D * shape.dense_bpp,
                     desc="fused q|k|v, heads split")
    q = qkv
    if shape.qk_norm:
        q = ops.rmsnorm(f"{P}.qk_norm", [qkv], (hpd + kpd) * HD, L, segments=hpd + kpd)
    q = ops.ew(f"{P}.rope", [q], (hpd + kpd) * HD, r.su_none + 2 * r.fadd, L, kernel=not shape.qk_norm,
               desc="RoPE on q and the new k")
    kvb = spec.rows * spec.entry_bytes
    sco = ops.kvscan(f"{P}.scores", [q], L, kv_bytes=kvb * HD / (HD + VHD),
                     depth_cycles=r.me_lat + r.me_tree, desc=f"q.k over {spec.rows} rows x {hpd} heads")
    o = _softmax_pv(ops, P, L, sco, hpd, spec.rows, HD, VHD, kvb * VHD / (HD + VHD), spec.sink)
    if shape.dense_bpp <= 1.0:
        o = ops.actquant(f"{P}.oquant", [o], hpd * VHD, L)
    y = ops.matvec(f"{P}.o", [o], L, n_out=D, k=NH * VHD, bytes_=D * NH * VHD * shape.dense_bpp,
                   desc="o projection, K-split by heads")
    return ops.collective(f"{P}.out_allreduce", [y], L, op="all_reduce", payload=D * 4,
                          desc="attention output partial sums (FP32)") or y


def _mla(ops: Ops, shape: DecodeShape, spec: LayerSpec, xq: str) -> str:
    r, G, L, D = ops.r, ops.m.group, spec.index, shape.hidden
    c = shape.mla
    P = f"L{L}.attn"
    NH, QR, KR = c["num_attention_heads"], c["q_lora_rank"], c["kv_lora_rank"]
    NOPE, ROPE, VD = c["qk_nope_head_dim"], c["qk_rope_head_dim"], c["v_head_dim"]
    hpd = math.ceil(NH / G)
    bpp = shape.dense_bpp
    a_out = QR + KR + ROPE
    a = ops.matvec(f"{P}.a_proj", [xq], L, n_out=a_out, k=D, bytes_=a_out * D * bpp,
                   desc="q_a | kv_a (latent + rope key), output-split")
    a = ops.collective(f"{P}.a_allgather", [a], L, op="all_gather", payload=a_out * 2,
                       desc="q_a | kv latent rows") or a
    qn = ops.rmsnorm(f"{P}.q_norm", [a], QR, L)
    kn = ops.rmsnorm(f"{P}.kv_norm", [a], KR, L)
    qb = ops.matvec(f"{P}.q_b", [qn], L, n_out=NH * (NOPE + ROPE), k=QR, bytes_=NH * (NOPE + ROPE) * QR * bpp,
                    desc="q_b, heads split")
    qa = ops.matvec(f"{P}.absorb_k", [qb], L, n_out=NH * KR, k=NOPE, bytes_=NH * KR * NOPE * bpp,
                    desc="absorbed W_uk: q_nope into the latent, per head")
    q = ops.ew(f"{P}.rope", [qa, kn], hpd * ROPE, r.su_none + 2 * r.fadd, L, kernel=True, desc="RoPE")
    kvb = spec.rows * spec.entry_bytes
    sco = ops.kvscan(f"{P}.scores", [q], L, kv_bytes=kvb, depth_cycles=r.me_lat + r.me_tree * 2,
                     desc=f"latent scores over {spec.rows} rows x {hpd} heads")
    o = _softmax_pv(ops, P, L, sco, hpd, spec.rows, KR + ROPE, KR, 0.0, False)
    ov = ops.matvec(f"{P}.absorb_v", [o], L, n_out=NH * VD, k=KR, bytes_=NH * VD * KR * bpp,
                    desc="absorbed W_uv: latent to value heads")
    if c["mla_use_output_gate"]:
        gt = ops.matvec(f"{P}.gate", [xq], L, n_out=NH * VD, k=D, bytes_=NH * VD * D * bpp, desc="output gate")
        gs = ops.ew(f"{P}.gate_sig", [gt], hpd * VD, r.su_sigm, L, desc="sigmoid gate")
        ov = ops.ew(f"{P}.gated", [ov, gs], hpd * VD, r.su_none + r.fadd, L, stream=False)
    y = ops.matvec(f"{P}.o", [ov], L, n_out=D, k=NH * VD, bytes_=D * NH * VD * bpp, desc="o projection, K-split")
    return ops.collective(f"{P}.out_allreduce", [y], L, op="all_reduce", payload=D * 4,
                          desc="attention output partial sums (FP32)") or y


def _kda(ops: Ops, shape: DecodeShape, spec: LayerSpec, xq: str) -> str:
    r, G, L, D = ops.r, ops.m.group, spec.index, shape.hidden
    c = shape.kda
    P = f"L{L}.attn"
    H, dk, kern = c["kda_heads"], c["kda_head_dim"], c["kda_short_conv_kernel"]
    hpd = math.ceil(H / G)
    bpp = shape.dense_bpp
    n_out = 3 * H * dk + (H * dk if c["kda_full_rank_gate"] else 0) + H + H * dk
    p = ops.matvec(f"{P}.proj", [xq], L, n_out=n_out, k=D, bytes_=n_out * D * bpp,
                   desc="q|k|v, decay gate, beta, output gate; heads split")
    cv = ops.ew(f"{P}.short_conv", [p], 3 * hpd * dk, r.su_none + kern * r.fadd + r.su_sigm, L, kernel=True,
                desc="depthwise short convolutions + SiLU")
    qk = ops.rmsnorm(f"{P}.l2norm", [cv], 2 * hpd * dk, L, segments=2 * hpd, kernel=False)
    dg = ops.ew(f"{P}.decay", [p], hpd * dk, r.su_exp + r.fadd, L, desc="per-channel decay exp(g), beta sigmoid")
    st = spec.state_bytes
    stk = ops.kvscan(f"{P}.state_read", [qk, dg], L, kv_bytes=st, kernel=True,
                     depth_cycles=r.me_lat + r.me_tree * math.ceil(math.log2(max(1, dk / 32 / r.interleave))) + r.fadd,
                     desc="decayed state S^T k, FP32 state")
    u = ops.ew(f"{P}.delta", [stk, cv], hpd * dk, r.su_none + 2 * r.fadd, L, stream=False,
               desc="u = beta (v - S^T k)")
    o = ops.kvscan(f"{P}.state_update", [u], L, kv_bytes=st, kernel=False,
                   depth_cycles=r.fadd + r.me_lat + r.me_tree * math.ceil(math.log2(max(1, dk / 32 / r.interleave))),
                   desc="S += k u^T, o = S^T q (state written back)")
    on = ops.rmsnorm(f"{P}.o_norm", [o], hpd * dk, L, segments=hpd, kernel=True)
    og = ops.ew(f"{P}.o_gate", [on, p], hpd * dk, r.su_sigm + r.fadd, L, stream=False, desc="gated output")
    if shape.dense_bpp <= 1.0:
        og = ops.actquant(f"{P}.oquant", [og], hpd * dk, L)
    y = ops.matvec(f"{P}.o", [og], L, n_out=D, k=H * dk, bytes_=D * H * dk * bpp, desc="o projection, K-split")
    return ops.collective(f"{P}.out_allreduce", [y], L, op="all_reduce", payload=D * 4,
                          desc="attention output partial sums (FP32)") or y


def _dsv4(ops: Ops, shape: DecodeShape, spec: LayerSpec, xq: str, ctx: int) -> str:
    g, m, r = ops.g, ops.m, ops.r
    c = shape.dsv4
    L, D, G = spec.index, shape.hidden, m.group
    H, HD, RD = c["num_attention_heads"], c["head_dim"], c["rope_head_dim"]
    QR, OG, OR = c["q_lora_rank"], c["o_groups"], c["o_lora_rank"]
    IH, IHD, TOPK, WIN = c["index_heads"], c["index_head_dim"], c["index_topk"], c["window_tokens"]
    hpd = math.ceil(H / G)
    P = f"L{L}.attn"
    ratio, is_src, scans = spec.ratio, spec.kv_source, spec.scans
    comp = (2 * HD * 4 if ratio == 2 else HD * 2) if is_src else 0
    a_out = QR + HD + IH
    a_bytes = (QR + HD) * D + IH * D * 2 + ((2 * HD * D * 4 if ratio == 2 else HD * D * 2) if is_src else 0)
    a = ops.matvec(f"{P}.a_proj", [xq], L, n_out=a_out + (2 * HD if is_src else 0), k=D, bytes_=a_bytes,
                   desc="fused wq_a | wkv | indexer weights" + (" | compressor" if is_src else "") + ", output-split")
    a = ops.collective(f"{P}.a_allgather", [a], L, op="all_gather", payload=a_out * 2 + comp,
                       desc="q_a | kv | index weights (+ compressor) rows") or a
    qn = ops.rmsnorm(f"{P}.q_norm", [a], QR, L)
    qq = ops.actquant(f"{P}.q_quant", [qn], QR, L)
    qb = ops.matvec(f"{P}.wq_b", [qq], L, n_out=H * HD + (IH * IHD if scans else 0), k=QR,
                    bytes_=H * HD * QR + (IH * IHD * QR if scans else 0),
                    desc="wq_b (heads split)" + (" | indexer wq_b (replicated)" if scans else ""))
    q = ops.ew(f"{P}.q_rope", [qb], hpd * RD, r.su_none + 2 * r.fadd, L, kernel=True, desc="RoPE on q tails")
    kn = ops.rmsnorm(f"{P}.kv_norm", [a], HD, L, kernel=False)
    kr = ops.ew(f"{P}.kv_rope_qdq", [kn], HD, r.su_none + 2 * r.fadd + r.actquant, L,
                desc="RoPE + FP8 QDQ, window append")
    rows_dep = [q, kr]
    n_sel = 0
    if ratio:
        n_comp = ctx // ratio
        n_sel = n_comp if spec.dense_compressed else min(TOPK, n_comp)
        newk = None
        if is_src:
            cp = a
            if ratio > 1:
                cp = ops.ew(f"{P}.cmp.pool", [a], 2 * HD, r.su_exp + r.fadd + r.su_none + r.fdiv + 2 * r.fadd, L,
                            stream=False, kernel=True, desc="softmax pooling over the compression window")
            cp = ops.rmsnorm(f"{P}.cmp.norm", [cp], HD, L, kernel=ratio <= 1)
            if scans or spec.index_entry_bytes:
                wk = ops.matvec(f"{P}.cmp.wk", [cp], L, n_out=IHD, k=HD, bytes_=IHD * HD * 2, fmt="bf16",
                                desc="indexer wk, BF16")
                kk = ops.rmsnorm(f"{P}.cmp.k_norm", [wk], IHD, L)
                newk = ops.ew(f"{P}.cmp.k_rope_qdq", [kk], IHD, r.su_none + 2 * r.fadd + r.fp4qdq, L,
                              desc="RoPE + FP4 QDQ -> index key cache")
            rows_dep.append(ops.ew(f"{P}.cmp.row_qdq", [cp], HD, r.su_none + 2 * r.fadd + r.fp4qdq, L,
                                   desc="RoPE + QDQ -> compressed KV cache"))
        if scans:
            n_scan = min(n_comp, spec.scan_cap or n_comp)
            iq = ops.ew(f"{P}.idx.q", [qb], IH * IHD, r.su_none + 2 * r.fadd + r.fp4qdq, L,
                        desc="index q RoPE + QDQ (replicated)")
            per_die = max(1, math.ceil(n_scan / G))
            sc = ops.kvscan(f"{P}.idx.score", [iq, a], L, kv_bytes=n_scan * spec.index_entry_bytes,
                            depth_cycles=r.me_lat + r.me_tree * 2 + r.su_none + 8 * r.fadd,
                            desc=f"index scores: {per_die} keys per partition x {IH} heads")
            sdeps = [sc]
            if newk:
                sdeps.append(g.add(f"{P}.idx.newkey", [newk, iq], layer=L, ctrl=ops.bctrl,
                                   depth=ops.cyc(r.me_lat + r.me_tree * 2 + r.su_none + 8 * r.fadd) if ops.rom else 0.0,
                                   desc="score of the just-compressed key"))
            s = ops.select_local(f"{P}.idx.topk_local", sdeps, L, n=per_die, k=TOPK,
                                 desc=f"local top-{TOPK} of {per_die} keys")
            s = ops.collective(f"{P}.idx.topk_merge", [s], L, op="all_gather", payload=G * TOPK * 8,
                               desc=f"{G} x {TOPK} (score, position) candidates") or s
            s = ops.select_final(f"{P}.idx.topk_final", [s], L, k=TOPK, ways=G, ascending=True,
                                 desc=f"{G}-way merge + ascending-index pass")
            ops.sel[L] = s
            if "candidate_source_layer_id" in c and L == c["candidate_source_layer_id"]:
                CB, CK = c["candidate_block_size"], c["candidate_topk_blocks"]
                nb = max(1, math.ceil(per_die / CB))
                cs = ops.select_local(f"{P}.cand.topk_local", [sc], L, n=nb, k=CK,
                                      desc=f"block max over {CB} + local top-{CK} of {nb} blocks")
                cs = ops.collective(f"{P}.cand.merge", [cs], L, op="all_gather", payload=G * CK * 8,
                                    desc=f"{G} x {CK} candidate blocks") or cs
                ops.select_final(f"{P}.cand.final", [cs], L, k=CK, ways=G, ascending=False)
            rows_dep.append(ops.gather(f"{P}.gather", [s], L,
                                       desc="selected compressed rows: the address exists only now"))
        elif not spec.dense_compressed and not spec.scans:
            srcs = [s_ for s_ in ops.sel if s_ <= L]
            if not srcs:
                raise ValidationError(f"{shape.name}: layer {L} reuses a selection no earlier layer made")
            rows_dep.append(ops.sel[max(srcs)])
    Rw = min(WIN, ctx)
    R = Rw + n_sel
    kvb = Rw * spec.window_entry_bytes + n_sel * spec.entry_bytes
    if G > 1:
        src_sel = [d for d in rows_dep if d not in (q, kr)]
        rg = ops.collective(f"{P}.rows_allgather", src_sel or [a], L, op="all_gather", payload=kvb,
                            desc=f"{R} shared KV rows, read once per group")
        rows_dep = [q, kr] + ([rg] if rg else src_sel)
    scd = r.me_lat + r.me_tree * math.ceil(math.log2(max(1, (HD // 32) / r.interleave)))
    sco = ops.kvscan(f"{P}.scores", rows_dep, L, kv_bytes=kvb, depth_cycles=scd,
                     desc=f"q.k over {R} rows x {hpd} heads per partition")
    o = _softmax_pv(ops, P, L, sco, hpd, R, HD, HD, 0.0, True)
    z = ops.matvec(f"{P}.wo_a", [o], L, n_out=OG * OR, k=(H // OG) * HD, bytes_=OG * OR * (H // OG) * HD,
                   desc="grouped wo_a")
    if G > OG:
        z = ops.collective(f"{P}.wo_a_group_reduce", [z], L, op="all_reduce", payload=OR * 4,
                           span=math.ceil(G / OG), desc="partial z of an o-group split across partitions (FP32)") or z
    zq = ops.actquant(f"{P}.z_quant", [z], OG * OR // max(1, min(G, OG)), L)
    y = ops.matvec(f"{P}.wo_b", [zq], L, n_out=D, k=OG * OR, bytes_=D * OG * OR, desc="wo_b, K-split by o-group")
    return ops.collective(f"{P}.out_allreduce", [y], L, op="all_reduce", payload=D * 4,
                          desc="attention output partial sums (FP32)") or y


def _ffn(ops: Ops, shape: DecodeShape, spec: LayerSpec, x: str, xq: str, tok: str) -> str:
    r, m, L, D, G = ops.r, ops.m, spec.index, shape.hidden, ops.m.group
    P = f"L{L}.ffn"
    if not spec.moe:
        FF = shape.ffn
        gu = ops.matvec(f"{P}.gate_up", [xq], L, n_out=2 * FF, k=D, bytes_=2 * FF * D * shape.dense_bpp,
                        desc="dense gate|up, intermediate split")
        sw = ops.ew(f"{P}.swiglu", [gu], math.ceil(FF / G), r.su_sigm + 2 * r.fadd, L, kernel=True, desc="silu(g)*u")
        if shape.dense_bpp <= 1.0:
            sw = ops.actquant(f"{P}.quant2", [sw], math.ceil(FF / G), L)
        dn = ops.matvec(f"{P}.down", [sw], L, n_out=D, k=FF, bytes_=D * FF * shape.dense_bpp, desc="down, K-split")
        return ops.collective(f"{P}.allreduce", [dn], L, op="all_reduce", payload=D * 4,
                              desc="FFN partial sums (FP32)") or dn
    NE, KE, FF = shape.experts, shape.topk, shape.moe_ffn
    Dl = shape.latent_dim or D
    src = xq
    if shape.latent_dim:
        lat = ops.matvec(f"{P}.latent_down", [xq], L, n_out=Dl, k=D, bytes_=Dl * D * shape.dense_bpp,
                         desc="latent MoE down-projection (assumed reading, see decode_graph_shapes.json)")
        lat = ops.collective(f"{P}.latent_allgather", [lat], L, op="all_gather", payload=Dl * 2,
                             desc="latent rows") or lat
        if shape.latent_norm:
            lat = ops.rmsnorm(f"{P}.latent_norm", [lat], Dl, L)
        src = lat
    rt = ops.matvec(f"{P}.router", [x], L, n_out=NE, k=D, bytes_=NE * D * shape.router_bytes_per_param,
                    fmt="fp32" if shape.router_bytes_per_param >= 4 else "bf16", desc="router, experts split")
    score_depth = {"sqrtsoftplus": r.su_none + r.softplus, "sigmoid": r.su_sigm,
                   "softmax": r.su_exp + r.su_recip}.get(shape.score_function)
    if score_depth is None:
        raise ValidationError(f"{shape.name}: no operator for router score {shape.score_function!r}")
    sp = ops.ew(f"{P}.score", [rt], math.ceil(NE / G), score_depth, L, kernel=True, desc=shape.score_function)
    sp = ops.collective(f"{P}.router_allgather", [sp], L, op="all_gather", payload=NE * 4,
                        desc=f"{NE} FP32 router scores") or sp
    bias = ops.ew(f"{P}.bias", [sp], NE, r.su_none + r.fadd, L, desc="+ bias")
    if spec.hash_routed:
        tk = ops.join(f"{P}.hash_route", [tok], L)       # expert ids from the token id: known at token start
    else:
        tk = ops.select_local(f"{P}.topk", [bias], L, n=NE, k=KE, desc=f"top-{KE} of {NE}")
        tk = ops.select_final(f"{P}.topk_order", [tk], L, k=KE, ways=1, ascending=True, desc="experts in id order")
    wn = ops.ew(f"{P}.weights", [tk, sp], KE, (KE - 1) * r.fadd + r.fadd + r.su_none + r.fdiv + r.fadd, L,
                stream=False, desc=f"sum of {KE} + eps, divide, x route scale")
    deps_sh: list = [src]
    shs = None
    if shape.shared_experts:
        SF = FF * shape.shared_experts
        sh = ops.matvec(f"{P}.shared_gu", [src], L, n_out=2 * SF, k=Dl, bytes_=2 * SF * Dl * shape.dense_bpp,
                        desc="shared expert gate|up, intermediate split")
        shs = ops.ew(f"{P}.shared_swiglu", [sh], math.ceil(SF / G), r.su_sigm + 2 * r.fadd, L, kernel=True)
        shs = ops.actquant(f"{P}.shared_quant", [shs], math.ceil(SF / G), L)
        deps_sh = [sh]
    ep = m.expert_parallel and m.ep_span > 1
    edeps = [tk] + deps_sh
    if ep:
        d = ops.all_to_all(f"{P}.dispatch", [tk, src], L, bytes_per_node=m.ep_tokens_per_node * KE * Dl * 2,
                           desc="expert-parallel dispatch")
        edeps = [d] + deps_sh if d else edeps
    inter = math.ceil(KE * FF / G) if not ep else FF * max(1, math.ceil(KE / max(1, m.ep_span)))
    gu = ops.matvec(f"{P}.experts_gu", edeps, L, n_out=2 * FF * KE, k=Dl, bytes_=KE * 2 * FF * Dl * shape.routed_bpp,
                    fmt="fp4", desc=f"routed gate|up of {KE} experts")
    sw = ops.ew(f"{P}.swiglu", [gu], inter, r.su_sigm + 2 * r.fadd, L, kernel=True, desc="silu(g)*u")
    sw = ops.ew(f"{P}.route_w", [sw, wn], inter, r.su_none + r.fadd, L, stream=False, desc="x routing weight")
    sq = ops.actquant(f"{P}.quant2", [sw], inter, L)
    dn_deps = [sq] + ([shs] if shs else [])
    shared_bytes = Dl * FF * shape.shared_experts * shape.dense_bpp
    dn = ops.matvec(f"{P}.down", dn_deps, L, n_out=Dl, k=FF * (KE + shape.shared_experts),
                    bytes_=KE * Dl * FF * shape.routed_bpp + shared_bytes, fmt="fp4",
                    desc="routed down + shared down, summed in expert-id order")
    if ep:
        dn = ops.all_to_all(f"{P}.combine", [dn], L, bytes_per_node=m.ep_tokens_per_node * KE * Dl * 2,
                            desc="expert-parallel combine (summed in expert-id order)") or dn
    else:
        dn = ops.collective(f"{P}.combine_allreduce", [dn], L, op="all_reduce", payload=Dl * 4,
                            desc="MoE combine: routed + shared partial sums (FP32)") or dn
    if shape.latent_dim:
        dn = ops.matvec(f"{P}.latent_up", [dn], L, n_out=D, k=Dl, bytes_=D * Dl * shape.dense_bpp,
                        desc="latent MoE up-projection")
        dn = ops.collective(f"{P}.latent_up_allreduce", [dn], L, op="all_reduce", payload=D * 4,
                            desc="latent up-projection partial sums (FP32)") or dn
    return dn


def residual_bytes(shape: DecodeShape) -> float:
    """Bytes of one user's residual stream at a stage boundary."""
    D, HC = shape.hidden, shape.hc_mult
    res = (HC * D * 2 + HC * 4) if HC > 1 else D * 2
    if shape.attn_res_block:
        res += shape.attn_res_block * D * 2
    return float(res)


def stage_hops(shape: DecodeShape, *, stages: int, levels: tuple[str, ...], return_level: str,
               fabric: "Fabric | None", microbatch: float) -> dict[str, Any]:
    """The pipeline boundaries one token crosses, each in series on its residual stream.

    Stage ``s`` begins at layer ``floor(s L / S)``.  The payload is the whole
    residual a stage hands on: four hyper-connection copies plus the pending
    FP32 mix on DeepSeek, the attention-residual block outputs on Kimi, and on
    DeepSeek-V4.1 the forwarded compressed row, index key and candidate
    selection a later layer re-reads -- all times the users in the microbatch.
    The token id then returns to the first stage."""
    if stages <= 1 or fabric is None:
        return dict(latency_s=0.0, bytes_s=0.0, count=0, events=[])
    NL = len(shape.layers)
    events = []
    lat = byt = 0.0
    for st in range(1, stages):
        L = (st * NL) // stages
        extra = 0.0
        c = shape.dsv4
        if c.get("kv_source_layer_ids") and "candidate_source_layer_id" in c:
            if L > min(c["kv_source_layer_ids"]):
                extra += 1280 + 2048
            if L > c["candidate_source_layer_id"]:
                extra += c["candidate_topk_blocks"] * 2
        pay = (residual_bytes(shape) + extra) * microbatch
        r = fabric.hop(levels[st - 1], pay)
        lat += r["latency_s"]
        byt += r["bytes_s"]
        events.append(dict(layer=L, level=levels[st - 1], payload_bytes=pay, **r))
    r = fabric.hop(return_level or "outer", 8 * microbatch)
    lat += r["latency_s"]
    byt += r["bytes_s"]
    events.append(dict(layer=NL, level=return_level or "outer", payload_bytes=8 * microbatch, **r))
    return dict(latency_s=lat, bytes_s=byt, count=len(events), events=events)


def boundary_levels(stages: int, domain: int, group: int) -> tuple[tuple[str, ...], str]:
    """Which link each stage boundary crosses: ``domain // group`` consecutive
    stages share one high-bandwidth domain, the boundary after them leaves it."""
    per_domain = max(1, domain // max(1, group))
    levels = tuple("outer" if b % per_domain == 0 else "inner" for b in range(1, stages))
    return levels, ("outer" if math.ceil(stages / per_domain) > 1 else "inner")


def price_stage_hops(technology: Any, shape: DecodeShape, *, stages: int,
                     fabric_links: tuple[str, str, int, int] | None, group: int,
                     microbatch: float) -> dict[str, Any]:
    """``stage_hops`` on the fabric a topology names."""
    if stages <= 1 or fabric_links is None:
        return dict(latency_s=0.0, bytes_s=0.0, count=0, events=[])
    inner, outer, domain, partitions = fabric_links
    levels, ret = boundary_levels(stages, domain, group)
    fabric = Fabric(technology, inner=inner, outer=outer, domain=domain, partitions=partitions, group=group)
    return stage_hops(shape, stages=stages, levels=levels, return_level=ret, fabric=fabric, microbatch=microbatch)


# ---------------------------------------------------------------------------
# entry point used by roofline.evaluate
# ---------------------------------------------------------------------------


@dataclass
class SerialGraph:
    """A built, priced graph of one token on one machine."""
    shape: DecodeShape
    machine: MachineSpec
    graph: Graph
    sink: str
    census: list
    weight_bytes: float
    kv_bytes: float
    fabric: Any = None

    def lines(self, kv_share: float) -> list:
        return self.graph.envelope(self.sink, kv_share)

    def detail(self, W: float, K: float, per_layer_top: int = 6, layers: set | None = None) -> dict[str, Any]:
        """Per-category attribution, the per-layer path and the collective census at sweeps W and K."""
        g = self.graph
        fin = g.solve(W, K)
        path = g.path(self.sink)
        cats = g.breakdown(self.sink)
        by_layer: dict[int, list] = {}
        for n in path:
            dur = sum(g.contrib[n].values())
            if dur > 0:
                by_layer.setdefault(g.nodes[n]["layer"], []).append((n, dur))
        return {
            "critical_path_s": fin[self.sink],
            "breakdown_s": cats,
            "per_layer_critical_path_us": {str(L): sum(d for _, d in ss) * 1e6 for L, ss in sorted(by_layer.items())},
            "top_serial_steps": {
                str(L): [dict(node=n, us=d * 1e6, desc=g.nodes[n]["desc"]) for n, d in
                         sorted(ss, key=lambda t: -t[1])[:per_layer_top]]
                for L, ss in sorted(by_layer.items()) if layers is None or L in layers},
            "collectives": collective_census(self.census, len(self.shape.layers)),
        }


def collective_census(events: list, num_layers: int) -> dict[str, Any]:
    """Every collective and hop on one token's graph, grouped by operator."""
    per: dict[str, Any] = {}
    for e in events:
        key = e["name"].split(".", 1)[-1] if e["name"][:1] in "LE" and e["name"][1:2].isdigit() else e["name"]
        d = per.setdefault(key, dict(count=0, op=e["op"], span=e["span"], payload_bytes=e["payload_bytes"],
                                     latency_ns=e["latency_s"] * 1e9, bytes_ns=e["bytes_s"] * 1e9,
                                     algo=e["algo"], where=e["where"], desc=e["desc"], layers=[]))
        d["count"] += 1
        d["layers"].append(e["layer"])
    for d in per.values():
        ls = sorted(set(d.pop("layers")))
        d["layers"] = "every layer" if len(ls) >= num_layers else ls
    return per


_GRAPH_CACHE: dict[tuple, SerialGraph] = {}
_LINES_CACHE: dict[tuple, tuple[list, dict]] = {}
_TECH_SIG: dict[int, tuple[Any, str]] = {}
GRAPH_CACHE_LIMIT = 48
LINES_CACHE_LIMIT = 200_000


def _tech_signature(technology: Any) -> str:
    hit = _TECH_SIG.get(id(technology.raw))
    if hit is not None and hit[0] is technology.raw:
        return hit[1]
    sig = json.dumps([technology.raw.get("serial_latency"),
                      {k: v.get("hop_latency_s", {}).get("value") for k, v in technology.raw["links"].items()},
                      {k: v.get("bytes_s", {}).get("value") for k, v in technology.raw["links"].items()},
                      {k: v.get("domain_size", {}).get("value") for k, v in technology.raw["links"].items()},
                      {k: v.get("switch_radix", {}).get("value") for k, v in technology.raw["links"].items()},
                      {k: v.get("fabric", {}).get("value") for k, v in technology.raw["links"].items()}],
                     sort_keys=True, default=str)
    if len(_TECH_SIG) > 512:
        _TECH_SIG.clear()
    _TECH_SIG[id(technology.raw)] = (technology.raw, sig)
    return sig


def _graph_key(technology: Any, model: ModelProfile, context_tokens: int, machine: MachineSpec,
               fabric_links: Any, algorithm: str) -> tuple:
    return (model.name, model.source_revision, len(model.attention_groups), int(context_tokens), machine,
            fabric_links, algorithm, _tech_signature(technology))


def serial_graph(technology: Any, model: ModelProfile, *, context_tokens: int, machine: MachineSpec,
                 fabric_links: tuple[str, str, int, int] | None, algorithm: str = "best") -> SerialGraph:
    """Build (or fetch) the priced graph of one token for one machine."""
    key = _graph_key(technology, model, context_tokens, machine, fabric_links, algorithm)
    hit = _GRAPH_CACHE.get(key)
    if hit is not None:
        return hit
    shape = decode_shape(model, context_tokens)
    rom, gpu = datapaths(technology)
    fab = None
    if fabric_links is not None:
        inner, outer, domain, partitions = fabric_links
        fab = Fabric(technology, inner=inner, outer=outer, domain=domain, partitions=partitions,
                     group=machine.group, algorithm=algorithm)
    g = Graph()
    ops = Ops(g, machine, rom, gpu, fab)
    sink = build_graph(shape, int(context_tokens), ops)
    tw, tk = g.normalise_sweep()
    sg = SerialGraph(shape=shape, machine=machine, graph=g, sink=sink, census=ops.census,
                     weight_bytes=tw, kv_bytes=tk, fabric=fab)
    if len(_GRAPH_CACHE) >= GRAPH_CACHE_LIMIT:
        _GRAPH_CACHE.pop(next(iter(_GRAPH_CACHE)))
    _GRAPH_CACHE[key] = sg
    return sg


_STRUCT_CACHE: dict[tuple, tuple["CompiledGraph", dict, Any]] = {}
_POINT_CACHE: dict[tuple, tuple["CompiledGraph", dict]] = {}
STRUCT_CACHE_LIMIT = 1024
POINT_CACHE_LIMIT = 4096


def serial_compiled(technology: Any, model: ModelProfile, *, context_tokens: int, machine: MachineSpec,
                    fabric_links: tuple[str, str, int, int] | None,
                    algorithm: str = "best") -> tuple["CompiledGraph", dict]:
    """The compiled graph of one token on one machine, and a summary of it (cached).

    The structure is built once per machine at a canonical microbatch and lane
    width and re-priced for the actual ones: they change what a node costs,
    never which nodes exist."""
    canonical = replace(machine, microbatch=1.0, su_width=16)
    skey = _graph_key(technology, model, context_tokens, canonical, fabric_links, algorithm)
    pkey = skey + (machine.microbatch, machine.su_width)
    struct = _STRUCT_CACHE.get(skey)
    if struct is None:
        sg = serial_graph(technology, model, context_tokens=context_tokens, machine=canonical,
                          fabric_links=fabric_links, algorithm=algorithm)
        coll = [e for e in sg.census if e["op"] != "hop"]
        summary = {
            "graph_nodes": len(sg.graph.nodes),
            "collectives_per_token": len(coll),
            "collectives_per_layer": len(coll) / max(1, len(sg.shape.layers)),
            "hops_per_token": sum(1 for e in sg.census if e["op"] == "hop"),
            "collective_algorithms": sorted({e["algo"] for e in coll}),
            "collective_payload_bytes_per_user_token": sum(e["payload_bytes"] for e in sg.census),
        }
        struct = (sg.graph.compile(sg.sink), summary, sg.fabric)
        if len(_STRUCT_CACHE) >= STRUCT_CACHE_LIMIT:
            _STRUCT_CACHE.pop(next(iter(_STRUCT_CACHE)))
        _STRUCT_CACHE[skey] = struct
    hit = _POINT_CACHE.get(pkey)
    if hit is None:
        rom, _gpu = datapaths(technology)
        pricer = Pricer(machine, rom, struct[2], microbatch=machine.microbatch, su_width=machine.su_width)
        compiled = struct[0].repriced(pricer)
        summary = dict(struct[1])
        summary["collective_algorithms"] = sorted(
            {pricer_algo(struct[2], recipe, machine.microbatch) for _i, recipe in compiled.recipes
             if recipe[0] == "coll"})
        hit = (compiled, summary)
        if len(_POINT_CACHE) >= POINT_CACHE_LIMIT:
            _POINT_CACHE.pop(next(iter(_POINT_CACHE)))
        _POINT_CACHE[pkey] = hit
    return hit


def pricer_algo(fabric: "Fabric | None", recipe: tuple, microbatch: float) -> str:
    """The algorithm a collective recipe is priced with at this microbatch."""
    if fabric is None:
        return "none"
    return fabric.collective(recipe[1], recipe[2] * microbatch, recipe[3])["algo"]


def serial_lines(technology: Any, model: ModelProfile, *, context_tokens: int, machine: MachineSpec,
                 fabric_links: tuple[str, str, int, int] | None, kv_share: float,
                 algorithm: str = "best") -> tuple[list, dict]:
    """The envelope lines of one token, and a small summary of its graph (cached)."""
    key = _graph_key(technology, model, context_tokens, machine, fabric_links, algorithm) + (kv_share,)
    hit = _LINES_CACHE.get(key)
    if hit is not None:
        return hit
    sg = serial_graph(technology, model, context_tokens=context_tokens, machine=machine,
                      fabric_links=fabric_links, algorithm=algorithm)
    lines = sg.lines(kv_share)
    coll = [e for e in sg.census if e["op"] != "hop"]
    summary = {
        "graph_nodes": len(sg.graph.nodes),
        "collectives_per_token": len(coll),
        "collectives_per_layer": len(coll) / max(1, len(sg.shape.layers)),
        "hops_per_token": sum(1 for e in sg.census if e["op"] == "hop"),
        "collective_algorithms": sorted({e["algo"] for e in coll}),
        "collective_payload_bytes_per_token": sum(e["payload_bytes"] for e in sg.census),
    }
    if len(_LINES_CACHE) >= LINES_CACHE_LIMIT:
        _LINES_CACHE.clear()
    _LINES_CACHE[key] = (lines, summary)
    return lines, summary
