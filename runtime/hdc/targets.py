"""Targets of the hardwired-decode-core runtime: which chip, which model.

Each target names the Verilator top that puts the host interface
(rtl/host/ot_host_if.sv) in front of one architecture's decode engine, the
program/ROM image generator that personalises it, the Hugging Face tokenizer
of the model it runs, and the physical records that give its modelled clock.

The three architectures of docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md section 6:

* ``qwen3-rom``   Qwen3-8B ROM reticle: one decode core, weights in ROM, KV in
                  SRAM with a slice per user (reduced Qwen3 vehicle).
* ``v41-rom``     DeepSeek-V4.1 ROM die: the V4.1 decode core (reduced V4.1
                  vehicle); one user's state at a time, cleared between users.
* ``qwen3-array`` ROM array: the host interface fronts the SOURCE package of a
                  layer-per-package array of decode cores and package
                  controllers (ot_rom_pkg_ctrl) over package links; users run
                  as a batch through the package controllers' user contexts.
* ``qwen3-hbm``   HBM comparator: the decode core with its KV cache streamed
                  from HBM (ot_hdc_kv_stream + the HBM timing model).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HF_HUB = Path.home() / ".cache/huggingface/hub"

_HDC = [f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu",
                                    "ot_hdc_reduce", "ot_hdc_matvec", "ot_hdc_stream", "ot_hdc_core")]
_PIPES = ["rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/proto/ot_fp32_mul_rne_pipe.sv"]
_V41 = (_PIPES + [f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu",
                                             "ot_hdc_reduce", "ot_hdc_matvec")]
        + [f"rtl/hdc/v41/{n}.sv" for n in ("ot_hdc_engram_tables_pkg", "ot_hdc_engram_hash", "ot_hdc_select",
                                           "ot_hdc_blockdot", "ot_hdc_actquant", "ot_hdc_fp4qdq", "ot_hdc_fdiv",
                                           "ot_hdc_fsqrt", "ot_hdc_softplus", "ot_hdc_sinkhorn_seq", "ot_hdc_sk_arith",
                                           "ot_hdc_sk_recip_rom", "ot_hdc_sinkhorn", "ot_hdc_sinkhorn_mc",
                                           "ot_hdc_v41_stream", "ot_hdc_v41_qe", "ot_hdc_v41_xu", "ot_hdc_v41_hcproj",
                                           "ot_hdc_core_v41")])
_HOST = ["rtl/host/ot_host_if.sv"]
_HDC_PHYS = ["hdc/ot_hdc_matvec", "hdc/ot_hdc_stream", "hdc/ot_fp32_add_rne_pipe", "hdc/ot_hdc_fp32_mul_pipe",
             "hdc/ot_hdc_exp_rebalanced_mul", "hdc/ot_hdc_recip_rebalanced_mul", "hdc/ot_hdc_rsqrt_rebalanced_mul"]


def _snapshot(repo: str) -> Path | None:
    snaps = sorted((HF_HUB / f"models--{repo.replace('/', '--')}" / "snapshots").glob("*"))
    return snaps[-1] if snaps else None


@dataclass(frozen=True)
class Target:
    name: str
    architecture: str
    model_id: str
    top: str
    sources: tuple[str, ...]
    images: str                       # "qwen3" | "v41" | "qwen3-array"
    tokenizer_repo: str               # the shipped model whose tokenizer the reduced vocabulary folds
    vocab: int                        # reduced vocabulary: id = shipped id % vocab
    eos: tuple[int, ...]
    ctx_max: int                      # positions per user (prompt + generated - 1)
    slots: int
    mode: int                         # ot_host_if MODE
    chat: str                         # "qwen3" | "deepseek-v41"
    physical: tuple[str, ...]         # records under results/physical_abi3/asap7 bounding the clock
    params: dict = field(default_factory=dict)
    verilator_flags: tuple[str, ...] = ()
    oracle: tuple[int, ...] = ()      # generated ids of the target's reference prompt (RTL campaign)
    status: str = ""

    def tokenizer_path(self) -> Path | None:
        snap = _snapshot(self.tokenizer_repo)
        return snap / "tokenizer.json" if snap and (snap / "tokenizer.json").exists() else None

    def modelled_clock(self) -> dict:
        """The slowest routed block among the core's records: the core itself is
        not routed as one block, so its clock is bounded by its parts."""
        rows = []
        for rel in self.physical:
            p = ROOT / "results/physical_abi3/asap7" / rel / "physical.json"
            if not p.exists():
                continue
            m = json.loads(p.read_text()).get("place_and_route", {}).get("metrics", {})
            if m.get("fmax_hz"):
                rows.append((float(m["fmax_hz"]), rel))
        if not rows:
            return {"hz": 1.0e9, "limiter": None, "source": "default 1 GHz (no physical record found)"}
        hz, rel = min(rows)
        return {"hz": hz, "limiter": rel, "source": f"results/physical_abi3/asap7/{rel}/physical.json"}


TARGETS: dict[str, Target] = {
    "qwen3-rom": Target(
        name="qwen3-rom", architecture="Qwen3-8B ROM reticle", model_id="qwen3-reduced-v1",
        top="tb_host_qwen", sources=tuple(_HDC + _PIPES + _HOST + ["rtl/test/tb_host_qwen.sv"]),
        images="qwen3", tokenizer_repo="Qwen/Qwen3-8B", vocab=4096, eos=(93, 91), ctx_max=64, slots=16, mode=0,
        chat="qwen3", physical=tuple(_HDC_PHYS), oracle=(1073, 382, 93),
        status="host interface + one decode core, 16 user contexts (KV slices)"),
    "v41-rom": Target(
        name="v41-rom", architecture="DeepSeek-V4.1 ROM die", model_id="deepseek-v4.1-flash-reduced-v1",
        top="tb_host_v41", sources=tuple(_V41 + _HOST + ["rtl/test/tb_host_v41.sv"]),
        images="v41", tokenizer_repo="deepseek-ai/DeepSeek-V4.1-Flash", vocab=4040, eos=(1, 0), ctx_max=128,
        slots=16, mode=0, chat="deepseek-v41",
        physical=tuple(["hdc/ot_hdc_matvec", "hdc/ot_hdc_stream"] + [f"hdc/v41/{n}" for n in (
            "ot_hdc_actquant", "ot_hdc_blockdot", "ot_hdc_engram_hash", "ot_hdc_fp4qdq", "ot_hdc_select_k512",
            "ot_hdc_softplus")]),                  # the Sinkhorn unit is a 7-cycle multicycle path (ot_hdc_sinkhorn_mc)
        verilator_flags=("-Wno-IMPORTSTAR",), oracle=(3118, 2400, 318),
        status="host interface + the V4.1 decode core, one user's state at a time"),
    "qwen3-array": Target(
        name="qwen3-array", architecture="ROM array (package controllers + links)", model_id="qwen3-reduced-v1",
        top="tb_host_array", sources=tuple(_HDC + _PIPES + ["rtl/rom/ot_rom_pkg_link.sv", "rtl/rom/ot_rom_pkg_ctrl.sv"]
                                           + _HOST + ["rtl/test/tb_host_array.sv"]),
        images="qwen3-array", tokenizer_repo="Qwen/Qwen3-8B", vocab=4096, eos=(93, 91), ctx_max=64, slots=16,
        mode=1, chat="qwen3", physical=tuple(_HDC_PHYS + ["rom/ot_rom_pkg_ctrl"]), oracle=(1073, 382, 93),
        params={"NODES": 4},
        status="host interface fronting package 0 of a 4-package layer-per-package array"),
    "qwen3-hbm": Target(
        name="qwen3-hbm", architecture="HBM comparator (KV in HBM)", model_id="qwen3-reduced-v1",
        top="tb_host_hbm", sources=tuple(_HDC + _PIPES + ["rtl/hdc/kv/ot_hdc_kv_stream.sv",
                                                          "rtl/hdc/kv/ot_hdc_kv_walk.sv",
                                                          "rtl/hdc/kv/ot_hdc_hbm_model.sv"]
                                         + _HOST + ["rtl/test/tb_host_hbm.sv"]),
        images="qwen3", tokenizer_repo="Qwen/Qwen3-8B", vocab=4096, eos=(93, 91), ctx_max=64, slots=16, mode=0,
        chat="qwen3", physical=tuple(_HDC_PHYS + ["hdc/kv/ot_hdc_kv_stream"]), oracle=(1073, 382, 93),
        status="host interface + the decode core with KV streamed from the HBM model; weights still in ROM"),
}
