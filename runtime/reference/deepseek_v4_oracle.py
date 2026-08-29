"""Single-GPU streaming execution of the vendor DeepSeek-V4-Flash-0731 model.

This module is the execution engine behind ``tools/run_deepseek_v4_reference_oracle.py``.
It is an *external reference comparator* only: it never produces accelerator
tokens and never supplies an activation to the accelerator path.  ADR-003
section 18 permits exactly this use.

Why a streaming engine at all
-----------------------------
The vendor ships ``inference/model.py`` + ``inference/kernel.py`` and a
``convert.py`` that reshards the checkpoint for tensor-parallel execution
(``torchrun --nproc-per-node 4``).  Neither the resharding nor the four GPUs are
available here: this host has a single RTX PRO 6000 Blackwell whose free memory
is shared with other tenants, and the checkpoint is 156 GiB against ~11 GiB of
usable device memory.  So the vendor modules are imported *verbatim* and driven
by a loader that materialises one transformer block - and, inside the MoE, one
expert - at a time, directly from the released HuggingFace shards.

What is changed, and why
-----------------------
Every deviation is recorded in :data:`ADAPTATIONS` so the report states it
rather than burying it:

``sparse_attn`` is launched 16 heads at a time
    The released TileLang kernel asks for 141,312 bytes of dynamic shared memory
    when instantiated at ``h=64, d=512`` (this model's ``n_heads`` and
    ``head_dim`` at ``world_size=1``).  sm_120 offers 101,376 bytes per block, so
    the 64-head launch cannot start at all - this is a hard property of the GPU,
    not a memory-pressure problem.  It launches at ``h<=16``, which is precisely
    the per-rank head count the vendor's own ``world_size=4`` configuration
    produces.  Every head in that kernel is independent - its own query row, its
    own online softmax accumulators, its own ``attn_sink`` entry, its own output
    row - so calling it four times with 16 heads and concatenating returns
    *bitwise* identical results.  :func:`verify_head_split_identity` re-proves
    that on this machine at startup rather than asserting it from the source,
    and the engine refuses to run if it ever fails.

The routed experts may take the vendor's FP8 path instead of its FP4 one
    :func:`verify_fp4_gemm` runs the released ``fp4_gemm`` on a real expert
    tensor from the checkpoint at startup and compares it against two mutually
    independent references: the vendor's own ``convert.cast_e2m1fn_to_e4m3fn``
    recast fed to ``fp8_gemm``, and a direct PyTorch dequantisation using the
    vendor's ``FP4_TABLE``.  On this sm_120 GPU the two references agree to
    bf16 output rounding and ``fp4_gemm`` does not, so the experts are recast to
    FP8 - which is exactly the configuration the release README documents
    (``--expert-dtype fp8``) and which ``convert.py`` documents as lossless.
    This matters more than it looks: the routed experts are most of the model,
    so a wrong ``fp4_gemm`` yields fluent but semantically empty text instead of
    an obvious failure.

Parameter residency is on demand
    Blocks, and individual routed experts within a block's MoE, are copied to
    the device only while they execute.  Values are untouched; only residency
    and timing differ.

The embedding and the LM head sit in host memory
    The embedding (1.01 GiB) is a pure gather, and the LM head (2.02 GiB once
    widened to the float32 the vendor declares) is one matmul per step.  Keeping
    them on the host frees 3 GiB of contended device memory for the same
    arithmetic.  ``--head-on-device`` moves the head back when there is room.

The three DSpark stages are not built
    ``dspark_block_size`` is set to 0.  They are a speculative-decoding draft
    head that the vendor's own ``generate.py`` never invokes, and the 43-layer
    main model's token outputs do not depend on them.

``rotate_activation`` has a PyTorch fallback that is *not* normally used
    The official ``fast_hadamard_transform`` extension is preferred and is what
    runs here.  If it is unavailable, :func:`torch_hadamard_transform` takes
    over with the arithmetic OpenTallas froze in ``runtime/reference/hadamard.py``
    - seven ascending-stride binary32 butterfly stages, one binary32 scale
    multiply, one RNE conversion to bfloat16 - which the tests check is bitwise
    identical to the extension at this graph's only width, 128.

Nothing else is altered.  The attention, compressor, indexer, hyper-connection,
gating, expert and quantisation math all run the vendor's own code and the
vendor's own TileLang kernels.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/"
    "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
)

#: Vendor sources this engine is pinned to.  The same digests appear in
#: ``compiler/models/deepseek-v4-flash-0731/checkpoint_source.json``.
VENDOR_SOURCE_SHA256 = {
    "inference/model.py": (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    ),
    "inference/kernel.py": (
        "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
    ),
    "inference/config.json": (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    ),
    "encoding/encoding_dsv4.py": (
        "abc0d26120250dda0ae077dc64aa28836026e61e970854aaeb792445e6a0dde6"
    ),
    "tokenizer.json": (
        "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf"
    ),
}

#: Width of every Hadamard rotation in this graph, per runtime/reference/hadamard.py.
HADAMARD_WIDTH = 128

#: Heads per ``sparse_attn`` launch.  16 is the vendor's own ``world_size=4``
#: per-rank head count and the largest that fits sm_120 shared memory at d=512.
SPARSE_ATTN_HEADS_PER_LAUNCH = 16


class OracleError(RuntimeError):
    """Raised when the reference engine cannot honour its contract."""


# ---------------------------------------------------------------------------
# Vendor module import
# ---------------------------------------------------------------------------
def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_vendor_sources(snapshot: Path) -> dict[str, str]:
    """Hash the vendor files this engine imports, refusing any drift."""
    observed: dict[str, str] = {}
    for relative, expected in sorted(VENDOR_SOURCE_SHA256.items()):
        path = snapshot / relative
        if not path.exists():
            raise OracleError(f"vendor source missing: {path}")
        digest = _sha256_file(path)
        if digest != expected:
            raise OracleError(
                f"{relative} sha256 {digest} differs from pinned {expected}"
            )
        observed[relative] = digest
    return observed


def import_vendor(snapshot: Path) -> tuple[Any, Any, Any, Any]:
    """Import the vendor ``kernel``, ``model``, ``convert`` and encoding modules.

    ``model.py`` does ``from kernel import ...``, so ``inference/`` must be on
    ``sys.path`` rather than the modules being loaded by file path.
    """
    inference = str(snapshot / "inference")
    encoding = str(snapshot / "encoding")
    for entry in (inference, encoding):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    kernel = importlib.import_module("kernel")
    model = importlib.import_module("model")
    convert = importlib.import_module("convert")
    encoding_dsv4 = importlib.import_module("encoding_dsv4")
    return model, kernel, convert, encoding_dsv4


# ---------------------------------------------------------------------------
# Routed-expert numeric path
# ---------------------------------------------------------------------------
def verify_fp4_gemm(kernel_mod: Any, convert_mod: Any, store: "WeightStore") -> dict:
    """Check the released FP4 GEMM against two independent references.

    The routed experts hold the overwhelming majority of this model's weights,
    so a wrong ``fp4_gemm`` produces fluent but semantically empty text rather
    than an obvious failure.  The check is run on a *real* expert tensor from
    the checkpoint and compared against:

    1. the vendor's own ``convert.py --expert-dtype fp8`` recast followed by the
       vendor's ``fp8_gemm`` - the alternative the release's README documents;
    2. a direct PyTorch dequantisation using the vendor's own ``FP4_TABLE``.

    References (1) and (2) are independent of each other.  If they agree and
    ``fp4_gemm`` does not, ``fp4_gemm`` is the outlier.
    """
    import torch

    name = "layers.5.ffn.experts.7.w1.weight"
    packed = store.raw(name)
    scale = store.raw(name.replace(".weight", ".scale"))
    device = torch.device("cuda")

    fp8_weight, fp8_scale = convert_mod.cast_e2m1fn_to_e4m3fn(packed, scale)
    fp8_weight = fp8_weight.to(device).contiguous()
    fp8_scale = fp8_scale.to(device).contiguous()
    fp4_weight = packed.to(device).view(torch.float4_e2m1fn_x2).contiguous()
    fp4_scale = scale.to(device).contiguous()

    generator = torch.Generator(device=device).manual_seed(20260829)
    x = torch.randn(
        16, packed.size(1) * 2, dtype=torch.bfloat16, device=device,
        generator=generator,
    )
    activation, activation_scale = kernel_mod.act_quant(
        x, 128, "ue8m0", torch.float8_e8m0fnu
    )

    via_fp8 = kernel_mod.fp8_gemm(
        activation, activation_scale, fp8_weight, fp8_scale, torch.float8_e8m0fnu
    ).float()
    via_fp4 = kernel_mod.fp4_gemm(
        activation, activation_scale, fp4_weight, fp4_scale, torch.float8_e8m0fnu
    ).float()

    # Independent reference: unpack the nibbles with the vendor's own table.
    codes = packed.to(device).view(torch.uint8)
    table = convert_mod.FP4_TABLE.to(device)
    low = table[(codes & 0x0F).long()]
    high = table[((codes >> 4) & 0x0F).long()]
    values = torch.stack([low, high], dim=-1).flatten(1)
    dequantised = (
        values.view(values.size(0), -1, 32) * fp4_scale.float().unsqueeze(-1)
    ).reshape(values.size(0), -1)
    widened = (
        activation.float().view(16, -1, 128) * activation_scale.float().unsqueeze(-1)
    ).reshape(16, -1)
    via_torch = widened @ dequantised.T

    magnitude = float(via_torch.abs().mean())
    fp8_error = float((via_fp8 - via_torch).abs().max())
    fp4_error = float((via_fp4 - via_torch).abs().max())
    # The FP8 path only has to agree to bf16 output rounding; the FP4 path is
    # judged against the same bar.
    tolerance = max(8.0 * magnitude * 2**-8, 1e-3)
    return {
        "probe_tensor": name,
        "reference_mean_abs": magnitude,
        "tolerance": tolerance,
        "fp8_path_max_abs_error": fp8_error,
        "fp4_path_max_abs_error": fp4_error,
        "fp8_gemm_agrees": fp8_error <= tolerance,
        "fp4_gemm_agrees": fp4_error <= tolerance,
    }


def cast_experts_to_fp8(
    convert_mod: Any, packed, scale, device
):  # noqa: ANN001
    """Run the vendor's own FP4 -> FP8 expert recast, on the device.

    ``convert.py`` performs exactly this when invoked with
    ``--expert-dtype fp8``, which the release README documents as the supported
    alternative to the FP4 expert path.  The only change is that the vendor's
    ``FP4_TABLE`` constant is read from device memory so the arithmetic runs on
    the GPU instead of 32 CPU threads; the values are identical.
    """
    import torch

    table = convert_mod.FP4_TABLE
    if table.device != device:
        convert_mod.FP4_TABLE = table.to(device)
    return convert_mod.cast_e2m1fn_to_e4m3fn(
        packed.to(device), scale.to(device)
    )


# ---------------------------------------------------------------------------
# Replacement 1: head-split sparse attention
# ---------------------------------------------------------------------------
def make_head_split_sparse_attn(
    vendor_sparse_attn: Callable[..., Any],
    heads_per_launch: int = SPARSE_ATTN_HEADS_PER_LAUNCH,
) -> Callable[..., Any]:
    """Wrap the vendor kernel so each launch sees at most ``heads_per_launch``.

    The kernel body is untouched; only the head count per launch changes, and it
    changes to a value the vendor itself produces under ``world_size=4``.
    """
    import torch

    def sparse_attn(q, kv, attn_sink, topk_idxs, softmax_scale):  # noqa: ANN001
        heads = q.size(2)
        if heads <= heads_per_launch:
            return vendor_sparse_attn(q, kv, attn_sink, topk_idxs, softmax_scale)
        pieces = []
        for start in range(0, heads, heads_per_launch):
            stop = min(start + heads_per_launch, heads)
            # ``.contiguous()`` is not enough: at decode the query is
            # [1, 1, 64, 512], so a head slice keeps stride 32768 on the
            # size-1 sequence axis and still counts as contiguous, while the
            # kernel's signature check demands the canonical 8192.  A
            # contiguous-format clone forces the canonical strides.
            pieces.append(
                vendor_sparse_attn(
                    q[:, :, start:stop].clone(
                        memory_format=torch.contiguous_format
                    ),
                    kv,
                    attn_sink[start:stop].clone(
                        memory_format=torch.contiguous_format
                    ),
                    topk_idxs,
                    softmax_scale,
                )
            )
        return torch.cat(pieces, dim=2)

    return sparse_attn


def verify_head_split_identity(
    vendor_sparse_attn: Callable[..., Any],
    *,
    heads: int = 64,
    head_dim: int = 128,
    kv_len: int = 512,
    topk: int = 128,
    queries: int = 3,
    seed: int = 20260829,
) -> dict[str, Any]:
    """Re-prove on this machine that head splitting is bitwise identity.

    ``head_dim`` is 128 rather than the model's 512 because the un-split
    64-head/512-dim launch is exactly the configuration that cannot start on
    sm_120 - there is nothing to compare against at that width.  The property
    being checked is head independence, which does not depend on ``head_dim``.
    """
    import torch

    device = torch.device("cuda")
    generator = torch.Generator(device=device).manual_seed(seed)
    q = torch.randn(
        1, queries, heads, head_dim, dtype=torch.bfloat16,
        device=device, generator=generator,
    )
    kv = torch.randn(
        1, kv_len, head_dim, dtype=torch.bfloat16, device=device, generator=generator
    )
    attn_sink = torch.randn(
        heads, dtype=torch.float32, device=device, generator=generator
    )
    topk_idxs = torch.randint(
        -1, kv_len, (1, queries, topk), dtype=torch.int32,
        device=device, generator=generator,
    )
    scale = head_dim**-0.5
    full = vendor_sparse_attn(q, kv, attn_sink, topk_idxs, scale)
    split = make_head_split_sparse_attn(vendor_sparse_attn)(
        q, kv, attn_sink, topk_idxs, scale
    )
    identical = bool(torch.equal(full.view(torch.int16), split.view(torch.int16)))
    return {
        "heads": heads,
        "head_dim": head_dim,
        "kv_len": kv_len,
        "topk": topk,
        "queries": queries,
        "seed": seed,
        "heads_per_launch": SPARSE_ATTN_HEADS_PER_LAUNCH,
        "bitwise_identical": identical,
        "max_abs_difference": float((full.float() - split.float()).abs().max()),
    }


# ---------------------------------------------------------------------------
# Replacement 2: Hadamard rotation
# ---------------------------------------------------------------------------
def torch_hadamard_transform(x, scale: float):  # noqa: ANN001
    """Sylvester Walsh-Hadamard transform in binary32, then one RNE to bfloat16.

    Mirrors ``runtime/reference/hadamard.py``: ascending strides 1,2,...,n//2,
    every butterfly a binary32 add or subtract, a single binary32 multiply by
    ``scale``, and a single conversion back to bfloat16.
    """
    import torch

    if x.dtype is not torch.bfloat16:
        raise OracleError(f"hadamard input must be bfloat16, got {x.dtype}")
    width = x.size(-1)
    if width & (width - 1):
        raise OracleError(f"hadamard width {width} is not a power of two")
    shape = x.shape
    y = x.float().reshape(-1, width)
    stride = 1
    while stride < width:
        y = y.view(-1, width // (2 * stride), 2, stride)
        low = y[:, :, 0, :]
        high = y[:, :, 1, :]
        y = torch.stack((low + high, low - high), dim=2).reshape(-1, width)
        stride *= 2
    return (y * scale).to(torch.bfloat16).reshape(shape)


def make_rotate_activation(fast_hadamard: Any | None) -> tuple[Callable, str]:
    """Return the ``rotate_activation`` implementation and its provenance."""
    import torch

    if fast_hadamard is not None:
        def rotate_activation(x):  # noqa: ANN001
            if x.dtype is not torch.bfloat16:
                raise OracleError("rotate_activation expects bfloat16")
            return fast_hadamard.hadamard_transform(x, scale=x.size(-1) ** -0.5)

        return rotate_activation, "fast_hadamard_transform"

    def rotate_activation(x):  # noqa: ANN001
        return torch_hadamard_transform(x, x.size(-1) ** -0.5)

    return rotate_activation, "opentallas_binary32_butterfly"


def try_import_fast_hadamard() -> Any | None:
    try:
        return importlib.import_module("fast_hadamard_transform")
    except Exception:  # pragma: no cover - environment dependent
        return None


# ---------------------------------------------------------------------------
# Weight streaming
# ---------------------------------------------------------------------------
@dataclass
class StreamStats:
    """Byte and time counters for honest reporting."""

    tensors_read: int = 0
    bytes_read: int = 0
    read_seconds: float = 0.0
    host_cache_hits: int = 0
    host_cache_bytes: int = 0


class WeightStore:
    """Reads vendor checkpoint tensors and converts them to the model's dtypes.

    The released shards already use the inference module's parameter names, so
    no renaming is needed - unlike ``convert.py``, which also renames
    ``self_attn``/``mlp``.  Two conversions ``convert.py`` performs *are*
    reproduced here, because the model's declared dtypes require them:

    * ``attn.wo_a.weight`` is stored FP8 with an E8M0 block scale but declared
      bfloat16, so it is dequantised exactly as ``convert.py`` does.
    * routed expert ``w1/w2/w3.weight`` are stored as packed ``int8`` and are
      bit-cast (not converted) to ``float4_e2m1fn_x2``.

    Everything else is a straight dtype widening (bf16 -> float32 for the norms,
    the compressor projections, the hyper-connection tensors and the LM head;
    int64 -> int32 for the hash-routing table).
    """

    def __init__(
        self,
        snapshot: Path,
        *,
        device: str = "cuda",
        host_cache_dense: bool = True,
        pin_host_cache: bool = True,
    ) -> None:
        from safetensors import safe_open

        self._safe_open = safe_open
        self.snapshot = snapshot
        self.device = device
        self.host_cache_dense = host_cache_dense
        self.pin_host_cache = pin_host_cache
        index_path = snapshot / "model.safetensors.index.json"
        self.weight_map: dict[str, str] = json.loads(index_path.read_text())[
            "weight_map"
        ]
        self._handles: dict[str, Any] = {}
        self._host_cache: dict[str, Any] = {}
        self.stats = StreamStats()
        #: Set by the engine when the routed experts run through the vendor's
        #: FP8 recast instead of the FP4 kernel.  Holds the (weight, scale) pair
        #: for the expert tensor being materialised right now; weight and scale
        #: are always requested back to back for the same module.
        self.expert_recast: Callable[..., Any] | None = None
        self._expert_pair: tuple[str, Any, Any] | None = None

    def _handle(self, filename: str):
        handle = self._handles.get(filename)
        if handle is None:
            handle = self._safe_open(
                str(self.snapshot / filename), framework="pt", device="cpu"
            )
            self._handles[filename] = handle
        return handle

    def raw(self, name: str):
        """Read one checkpoint tensor into host memory, exactly as stored."""
        filename = self.weight_map.get(name)
        if filename is None:
            raise OracleError(f"checkpoint has no tensor {name!r}")
        started = time.perf_counter()
        tensor = self._handle(filename).get_tensor(name)
        self.stats.read_seconds += time.perf_counter() - started
        self.stats.tensors_read += 1
        self.stats.bytes_read += tensor.numel() * tensor.element_size()
        return tensor

    def host_tensor(self, name: str, target):  # noqa: ANN001
        """Return the host-side tensor in the model's declared dtype."""
        import torch

        cached = self._host_cache.get(name)
        if cached is not None:
            self.stats.host_cache_hits += 1
            return cached

        if name.endswith("attn.wo_a.weight"):
            # convert.py: fold the E8M0 128x128 block scale into bfloat16.
            weight = self.raw(name)
            scale = self.raw(name.replace(".weight", ".scale"))
            widened = (
                weight.unflatten(0, (-1, 128)).unflatten(-1, (-1, 128)).float()
                * scale[:, None, :, None].float()
            )
            out = widened.flatten(2, 3).flatten(0, 1).bfloat16()
        else:
            raw = self.raw(name)
            if target.dtype is torch.float4_e2m1fn_x2:
                if raw.dtype is not torch.int8:
                    raise OracleError(
                        f"{name}: expected int8 storage for FP4, got {raw.dtype}"
                    )
                out = raw.view(torch.float4_e2m1fn_x2)
            elif raw.dtype is target.dtype:
                out = raw
            else:
                out = raw.to(target.dtype)

        if tuple(out.shape) != tuple(target.shape):
            raise OracleError(
                f"{name}: checkpoint shape {tuple(out.shape)} != model "
                f"{tuple(target.shape)}"
            )
        return out

    def cache_host(self, name: str, tensor) -> None:  # noqa: ANN001
        if not self.host_cache_dense:
            return
        if name in self._host_cache:
            return
        stored = tensor
        if self.pin_host_cache:
            try:
                stored = tensor.pin_memory()
            except RuntimeError:
                stored = tensor
        self._host_cache[name] = stored
        self.stats.host_cache_bytes += stored.numel() * stored.element_size()

    def _is_routed_expert(self, name: str) -> bool:
        return ".ffn.experts." in name and (
            name.endswith(".weight") or name.endswith(".scale")
        )

    def _recast_expert(self, name: str):
        """Return one half of the vendor FP4 -> FP8 expert recast.

        ``convert.py`` produces the weight and its block scale together, so the
        pair is computed once and held until both halves have been asked for.
        """
        base = name[: -len(".scale")] + ".weight" if name.endswith(".scale") else name
        if self._expert_pair is None or self._expert_pair[0] != base:
            packed = self.raw(base)
            scale = self.raw(base[: -len(".weight")] + ".scale")
            weight_fp8, scale_fp8 = self.expert_recast(packed, scale)
            self._expert_pair = (base, weight_fp8, scale_fp8)
        _, weight_fp8, scale_fp8 = self._expert_pair
        return scale_fp8 if name.endswith(".scale") else weight_fp8

    def device_tensor(self, name: str, target, *, cache: bool = False):  # noqa: ANN001
        if self.expert_recast is not None and self._is_routed_expert(name):
            out = self._recast_expert(name)
            if tuple(out.shape) != tuple(target.shape):
                raise OracleError(
                    f"{name}: recast shape {tuple(out.shape)} != model "
                    f"{tuple(target.shape)}"
                )
            return out
        host = self.host_tensor(name, target)
        if cache:
            self.cache_host(name, host)
            host = self._host_cache.get(name, host)
        return host.to(self.device, non_blocking=host.is_pinned())


# ---------------------------------------------------------------------------
# The streaming model
# ---------------------------------------------------------------------------
@dataclass
class OracleConfig:
    snapshot: Path = DEFAULT_SNAPSHOT
    max_seq_len: int = 4096
    device: str = "cuda"
    #: Keep every block's non-expert weights in host memory after first use.
    host_cache_dense: bool = True
    pin_host_cache: bool = True
    #: Hold the float32 LM head on the device when there is room for it.
    head_on_device: bool = False
    #: Rows of the vocabulary per LM-head matmul when the head is on the device.
    head_chunk: int = 0
    verbose: bool = True


ADAPTATIONS: tuple[dict[str, str], ...] = (
    {
        "id": "sparse_attn_head_split",
        "vendor_symbol": "kernel.sparse_attn",
        "change": (
            "launched with 16 heads per call and concatenated instead of 64 in "
            "one call"
        ),
        "reason": (
            "the released TileLang kernel requests 141312 bytes of dynamic "
            "shared memory at h=64,d=512; sm_120 provides 101376 bytes per "
            "block, so the 64-head launch cannot start on this GPU"
        ),
        "fidelity": (
            "16 heads per launch is the vendor's own world_size=4 per-rank head "
            "count; heads are independent in the kernel and the split is "
            "re-verified bitwise at runtime"
        ),
    },
    {
        "id": "hadamard_fallback_available_but_unused",
        "vendor_symbol": "model.rotate_activation",
        "change": (
            "the official fast_hadamard_transform extension is used when "
            "importable; a PyTorch binary32 Sylvester butterfly stands in "
            "otherwise. The report's environment.fast_hadamard_transform field "
            "records which one actually ran"
        ),
        "reason": (
            "the released extension has no wheel for this toolchain and had to "
            "be built from source against CUDA 12.8 for sm_120"
        ),
        "fidelity": (
            "the fallback matches the arithmetic frozen in "
            "runtime/reference/hadamard.py - seven ascending-stride binary32 "
            "butterfly stages, one binary32 scale multiply, one RNE bfloat16 "
            "conversion - and is checked bitwise identical to the extension at "
            "this graph's only width, 128"
        ),
    },
    {
        "id": "endpoint_residency",
        "vendor_symbol": "model.ParallelEmbedding / model.ParallelHead",
        "change": (
            "the embedding and the float32 LM head are held in host memory "
            "unless --head-on-device is passed"
        ),
        "reason": (
            "3.03 GiB of device memory for a gather and one matmul per step, "
            "on a GPU whose free memory was measured dipping to 1.59 GiB"
        ),
        "fidelity": "same arithmetic and same float32 width; only the device differs",
    },
    {
        "id": "routed_experts_via_vendor_fp8_recast",
        "vendor_symbol": "kernel.fp4_gemm",
        "change": (
            "when the startup check finds fp4_gemm wrong on this GPU, the "
            "routed experts are recast FP4 -> FP8 by the vendor's own "
            "convert.cast_e2m1fn_to_e4m3fn and run through the vendor's "
            "fp8_gemm. The report's fp4_gemm_verification field carries the "
            "measurement and expert_numeric_path says which was used"
        ),
        "reason": (
            "on this sm_120 GPU the released fp4_gemm TileLang kernel "
            "disagrees with two mutually independent references - the vendor's "
            "own FP4->FP8 recast fed to fp8_gemm, and a direct PyTorch "
            "dequantisation using the vendor's FP4_TABLE - which agree with "
            "each other to bf16 output rounding. The routed experts are most "
            "of the model, so this produced fluent but vacuous text rather "
            "than a visible failure"
        ),
        "fidelity": (
            "this is the release README's own documented alternative "
            "(remove \"expert_dtype\": \"fp4\" from config.json, convert.py "
            "--expert-dtype fp8). convert.py documents the recast as lossless: "
            "every FP4 value is exactly representable in E4M3 and the applied "
            "offset is a power of two bounded by 2**6 so that 6.0*2**6=384 "
            "stays under the E4M3 maximum of 448"
        ),
    },
    {
        "id": "layer_streaming",
        "vendor_symbol": "model.Transformer parameter residency",
        "change": (
            "blocks and individual routed experts are materialised on the "
            "device only while executing, from the released HF shards"
        ),
        "reason": (
            "the checkpoint is 156 GiB and this host has one GPU with about "
            "11 GiB free; convert.py's tensor-parallel reshard targets 4 GPUs"
        ),
        "fidelity": "values are unchanged; only residency and timing differ",
    },
    {
        "id": "dspark_stages_not_built",
        "vendor_symbol": "model.Transformer.mtp",
        "change": "dspark_block_size=0 and dspark_target_layer_ids=()",
        "reason": (
            "the 3 mtp.* DSpark stages are a speculative-decoding draft head; "
            "the vendor's own generate.py never calls forward_spec"
        ),
        "fidelity": (
            "the 43-layer main model and its token outputs are unaffected"
        ),
    },
)


class StreamingDeepSeekV4:
    """The vendor ``Transformer`` driven by an on-demand weight loader."""

    def __init__(self, config: OracleConfig) -> None:
        import torch

        self.torch = torch
        self.config = config
        self.snapshot = config.snapshot
        self.device = torch.device(config.device)

        self.vendor_digests = verify_vendor_sources(self.snapshot)
        (
            self.model_mod,
            self.kernel_mod,
            self.convert_mod,
            self.encoding_mod,
        ) = import_vendor(self.snapshot)

        # Deterministic float32: TF32 would silently degrade every float32
        # matmul in this graph (norms, gating, hyper-connections, LM head).
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        # generate.py sets this before touching the model, and the vendor GEMM
        # kernels read it to pick their output dtype
        # (``a.new_empty(..., dtype=torch.get_default_dtype())``), so it has to
        # be bfloat16 before the first kernel call, not just before the build.
        torch.set_default_dtype(torch.bfloat16)

        self.vendor_sparse_attn = self.kernel_mod.sparse_attn
        self.head_split_evidence = verify_head_split_identity(
            self.vendor_sparse_attn
        )
        if not self.head_split_evidence["bitwise_identical"]:
            raise OracleError(
                "head-split sparse attention is not bitwise identical on this "
                "machine; refusing to produce a reference result"
            )
        self.model_mod.sparse_attn = make_head_split_sparse_attn(
            self.vendor_sparse_attn
        )

        self.fast_hadamard = try_import_fast_hadamard()
        rotate, self.hadamard_source = make_rotate_activation(self.fast_hadamard)
        self.model_mod.rotate_activation = rotate

        self.store = WeightStore(
            self.snapshot,
            device=config.device,
            host_cache_dense=config.host_cache_dense,
            pin_host_cache=config.pin_host_cache,
        )

        # The routed experts are most of this model.  Prove the FP4 GEMM before
        # trusting it, and fall back to the vendor's documented FP8 expert path
        # if it is wrong on this GPU.
        self.fp4_gemm_evidence = verify_fp4_gemm(
            self.kernel_mod, self.convert_mod, self.store
        )
        if not self.fp4_gemm_evidence["fp8_gemm_agrees"]:
            raise OracleError(
                "the vendor fp8_gemm kernel disagrees with a PyTorch "
                "dequantisation of the same checkpoint tensor on this machine; "
                "refusing to produce a reference result "
                f"({self.fp4_gemm_evidence})"
            )
        self.expert_dtype = (
            "fp4" if self.fp4_gemm_evidence["fp4_gemm_agrees"] else "fp8"
        )
        self._log(
            f"routed-expert numeric path: {self.expert_dtype} "
            f"(fp4_gemm max abs error "
            f"{self.fp4_gemm_evidence['fp4_path_max_abs_error']:.4g} vs "
            f"tolerance {self.fp4_gemm_evidence['tolerance']:.4g})"
        )
        if self.expert_dtype == "fp8":
            self.store.expert_recast = lambda packed, scale: cast_experts_to_fp8(
                self.convert_mod, packed, scale, self.device
            )

        self.args = self._build_args()
        self._build_skeleton()
        self._install_streaming_hooks()

        self.peak_device_bytes = 0
        self.layer_seconds = 0.0

    # -- construction -----------------------------------------------------
    def _build_args(self):
        raw = json.loads((self.snapshot / "inference" / "config.json").read_text())
        cfg = dict(raw)
        cfg["dspark_block_size"] = 0
        cfg["dspark_target_layer_ids"] = ()
        if self.expert_dtype == "fp8":
            # The release README: "If you want to use fp8, just remove
            # "expert_dtype": "fp4" in config.json and specify
            # --expert-dtype fp8 in convert.py."  This is that configuration.
            cfg["expert_dtype"] = None
        args = self.model_mod.ModelArgs(**cfg)
        args.max_batch_size = 1
        args.max_seq_len = self.config.max_seq_len
        # temperature 0 makes the vendor's own sample() take its argmax branch
        # instead of the Gumbel-max branch.  The oracle additionally computes
        # the greedy token itself and cross-checks; see greedy_generate.
        args.temperature = 0
        self.raw_config = raw
        return args

    def _log(self, message: str) -> None:
        if self.config.verbose:
            print(message, flush=True)

    def _build_skeleton(self) -> None:
        """Instantiate the vendor Transformer with parameters left on ``meta``.

        Buffers - the KV caches, the compressor states and the RoPE tables -
        must be real and must persist across the whole decode, so they are
        rebuilt on the device afterwards.
        """
        torch = self.torch
        torch.set_default_dtype(torch.bfloat16)
        started = time.perf_counter()
        with torch.device("meta"):
            self.model = self.model_mod.Transformer(self.args)
        self._materialise_buffers()
        self._prefix_of: dict[int, str] = {}
        # One "slot" per parameter tensor: the owning module, the local name in
        # that module's ``_parameters`` dict, and the meta placeholder to put
        # back when the parameter is evicted.  Residency is changed by swapping
        # the dict entry rather than by ``Parameter.data =``, because a meta
        # placeholder and a CUDA tensor are different tensor types and
        # ``set_data`` refuses to cross that boundary.
        self._slots: dict[str, tuple[Any, str, Any]] = {}
        for module_name, module in self.model.named_modules():
            self._prefix_of[id(module)] = module_name
            for local, param in module.named_parameters(recurse=False):
                full = f"{module_name}.{local}" if module_name else local
                self._slots[full] = (module, local, param)
        self._module_params: dict[int, list[str]] = {}
        self._block_dense_cache: dict[int, list[str]] = {}
        self.skeleton_seconds = time.perf_counter() - started
        self._log(
            f"skeleton built in {self.skeleton_seconds:.1f}s "
            f"({len(self._slots)} parameter tensors on meta)"
        )

    def _materialise_buffers(self) -> None:
        """Allocate the persistent state buffers for real on the device."""
        torch = self.torch
        args = self.args
        model_mod = self.model_mod
        # precompute_freqs_cis is lru_cached; the meta-device entries must go.
        model_mod.precompute_freqs_cis.cache_clear()
        model_mod.get_window_topk_idxs.cache_clear()
        model_mod.get_compress_topk_idxs.cache_clear()

        prior_device = torch.get_default_device() if hasattr(
            torch, "get_default_device"
        ) else None
        torch.set_default_device(self.device)
        try:
            for layer in self.model.layers:
                attn = layer.attn
                compress_ratio = attn.compress_ratio
                if compress_ratio:
                    original_seq_len = args.original_seq_len
                    rope_theta = args.compress_rope_theta
                else:
                    original_seq_len, rope_theta = 0, args.rope_theta
                freqs_cis = model_mod.precompute_freqs_cis(
                    attn.rope_head_dim,
                    args.max_seq_len,
                    original_seq_len,
                    rope_theta,
                    args.rope_factor,
                    args.beta_fast,
                    args.beta_slow,
                )
                attn.register_buffer("freqs_cis", freqs_cis, persistent=False)
                kv_cache_size = args.window_size + (
                    args.max_seq_len // compress_ratio if compress_ratio else 0
                )
                attn.register_buffer(
                    "kv_cache",
                    torch.zeros(
                        args.max_batch_size,
                        kv_cache_size,
                        attn.head_dim,
                        device=self.device,
                        dtype=torch.bfloat16,
                    ),
                    persistent=False,
                )
                if compress_ratio:
                    self._reset_compressor(attn.compressor)
                    if attn.indexer is not None:
                        indexer = attn.indexer
                        indexer.register_buffer(
                            "kv_cache",
                            torch.zeros(
                                args.max_batch_size,
                                args.max_seq_len // indexer.compress_ratio,
                                indexer.head_dim,
                                device=self.device,
                                dtype=torch.bfloat16,
                            ),
                            persistent=False,
                        )
                        self._reset_compressor(indexer.compressor)
        finally:
            if prior_device is not None:
                torch.set_default_device(prior_device)

    def _reset_compressor(self, compressor) -> None:  # noqa: ANN001
        torch = self.torch
        args = self.args
        coff = 1 + compressor.overlap
        compressor.register_buffer(
            "kv_state",
            torch.zeros(
                args.max_batch_size,
                coff * compressor.compress_ratio,
                coff * compressor.head_dim,
                dtype=torch.float32,
                device=self.device,
            ),
            persistent=False,
        )
        compressor.register_buffer(
            "score_state",
            torch.full(
                (
                    args.max_batch_size,
                    coff * compressor.compress_ratio,
                    coff * compressor.head_dim,
                ),
                float("-inf"),
                dtype=torch.float32,
                device=self.device,
            ),
            persistent=False,
        )
        compressor.kv_cache = None
        compressor.freqs_cis = None

    # -- streaming hooks --------------------------------------------------
    def _params_of(self, module) -> list[str]:  # noqa: ANN001
        key = id(module)
        names = self._module_params.get(key)
        if names is None:
            prefix = self._prefix_of[key]
            names = [
                f"{prefix}.{local}" if prefix else local
                for local, _ in module.named_parameters(recurse=True)
            ]
            self._module_params[key] = names
        return names

    def _materialise_names(self, names: Iterable[str], *, cache: bool) -> None:
        """Bring the named parameters onto the device, then relink FP8/FP4 scales.

        ``model.linear()`` reads the block scale off the weight tensor itself
        (``weight.scale``), which ``Linear.__init__`` aliases to the ``scale``
        parameter.  Swapping the dict entries breaks that alias, so it is
        re-established for every module whose weight actually carries one.
        """
        touched: dict[int, Any] = {}
        for name in names:
            module, local, meta = self._slots[name]
            current = module._parameters[local]
            if current is not None and current.device.type != "meta":
                continue
            module._parameters[local] = self.store.device_tensor(
                name, meta, cache=cache
            )
            touched[id(module)] = module
        for module in touched.values():
            scale = module._parameters.get("scale")
            weight = module._parameters.get("weight")
            if scale is not None and weight is not None:
                weight.scale = scale

    def _release_names(self, names: Iterable[str]) -> None:
        for name in names:
            module, local, meta = self._slots[name]
            current = module._parameters[local]
            if current is None or current.device.type == "meta":
                continue
            module._parameters[local] = meta

    def _materialise(self, module, *, cache: bool) -> None:  # noqa: ANN001
        self._materialise_names(self._params_of(module), cache=cache)

    def _release(self, module) -> None:  # noqa: ANN001
        self._release_names(self._params_of(module))

    def _install_streaming_hooks(self) -> None:
        """Decorate ``Block.forward`` and ``Expert.forward`` with residency.

        The decorated bodies are the vendor's, unmodified; only residency is
        added around them.  Experts are handled separately from their block
        because the vendor MoE only calls the experts a token actually routes
        to - six of 256 per layer at decode - and materialising all 256 would
        cost 3.2 GiB per layer.
        """
        model_mod = self.model_mod
        engine = self

        expert_modules = set()
        for layer in self.model.layers:
            for expert in layer.ffn.experts:
                if expert is not None:
                    expert_modules.add(id(expert))
            expert_modules.add(id(layer.ffn.shared_experts))
        self._expert_ids = expert_modules

        block_forward = model_mod.Block.forward
        expert_forward = model_mod.Expert.forward

        def streaming_block_forward(self, *args, **kwargs):  # noqa: ANN001
            started = time.perf_counter()
            engine._materialise_block(self)
            try:
                return block_forward(self, *args, **kwargs)
            finally:
                engine._release_block(self)
                engine.layer_seconds += time.perf_counter() - started
                engine._note_peak()

        def streaming_expert_forward(self, *args, **kwargs):  # noqa: ANN001
            engine._materialise(self, cache=False)
            try:
                return expert_forward(self, *args, **kwargs)
            finally:
                engine._release(self)

        model_mod.Block.forward = streaming_block_forward
        model_mod.Expert.forward = streaming_expert_forward
        self._vendor_block_forward = block_forward
        self._vendor_expert_forward = expert_forward

    def _block_dense_names(self, block) -> list[str]:  # noqa: ANN001
        """Every parameter of a block except the 257 expert FFNs it contains."""
        key = id(block)
        names = self._block_dense_cache.get(key)
        if names is None:
            expert_prefixes = tuple(
                self._prefix_of[id(module)] + "."
                for module in list(block.ffn.experts) + [block.ffn.shared_experts]
                if module is not None
            )
            names = [
                name
                for name in self._params_of(block)
                if not name.startswith(expert_prefixes)
            ]
            self._block_dense_cache[key] = names
        return names

    def _materialise_block(self, block) -> None:  # noqa: ANN001
        self._materialise_names(
            self._block_dense_names(block), cache=self.config.host_cache_dense
        )

    def _release_block(self, block) -> None:  # noqa: ANN001
        self._release_names(self._block_dense_names(block))

    def _note_peak(self) -> None:
        allocated = self.torch.cuda.max_memory_allocated()
        if allocated > self.peak_device_bytes:
            self.peak_device_bytes = allocated

    # -- head and embedding ----------------------------------------------
    def load_endpoints(self) -> dict[str, Any]:
        """Materialise the embedding, the final norm and the LM head."""
        torch = self.torch
        report: dict[str, Any] = {}

        self._materialise_names(
            ("norm.weight", "hc_head_fn", "hc_head_base", "hc_head_scale"),
            cache=False,
        )

        # The embedding is a pure gather: only the rows the prompt names are
        # ever touched, so keeping its 1.01 GiB in host memory costs one small
        # host-to-device copy per step and frees a GiB of contended device
        # memory.  The values are identical either way.
        embed_module, embed_local, embed_meta = self._slots["embed.weight"]
        embed_module._parameters[embed_local] = self.store.host_tensor(
            "embed.weight", embed_meta
        )
        report["embed_device"] = "cpu"
        engine = self

        def embed_forward(self, x):  # noqa: ANN001
            weight = self.weight
            out = torch.nn.functional.embedding(x.to(weight.device), weight)
            return out.to(engine.device)

        self.model_mod.ParallelEmbedding.forward = embed_forward

        head_module, head_local, head_meta = self._slots["head.weight"]
        head_host = self.store.host_tensor("head.weight", head_meta)
        free_bytes, _ = torch.cuda.mem_get_info()
        need = head_host.numel() * head_host.element_size()
        if self.config.head_on_device and free_bytes > need * 2:
            head_module._parameters[head_local] = head_host.to(self.device)
            report["head_device"] = "cuda"
        else:
            head_module._parameters[head_local] = head_host
            report["head_device"] = "cpu"
        report["head_dtype"] = str(head_meta.dtype).replace("torch.", "")
        report["head_bytes"] = int(need)

        def head_forward(self, x, full_logits=False):  # noqa: ANN001
            if not full_logits:
                x = x[:, -1]
            weight = self.weight
            return torch.nn.functional.linear(
                x.float().to(weight.device), weight
            )

        self.model_mod.ParallelHead.forward = head_forward
        return report

    # -- execution --------------------------------------------------------
    def forward(self, input_ids, start_pos: int):  # noqa: ANN001
        torch = self.torch
        prior = torch.get_default_device()
        torch.set_default_device(self.device)
        try:
            return self.model.forward(input_ids, start_pos)
        finally:
            torch.set_default_device(prior)

    def greedy_generate(
        self,
        prompt_token_ids: Sequence[int],
        *,
        max_new_tokens: int,
        eos_token_id: int,
        progress: Callable[[int, int, float], None] | None = None,
    ) -> dict[str, Any]:
        """Prefill once, then decode greedily one token at a time.

        Selection is ``argmax`` over the float32 logits with ties resolved to
        the lowest token id.  The vendor's ``sample()`` is *not* used for the
        selection: at ``temperature=0`` it would take the same argmax branch,
        but its default path is Gumbel-max
        (``probs.div_(torch.empty_like(probs).exponential_(1)).argmax(-1)``),
        which is not reproducible.  The vendor value is still computed and
        compared, and any disagreement is reported.
        """
        torch = self.torch
        ids = list(prompt_token_ids)
        if not ids:
            raise OracleError("prompt is empty")
        total = len(ids) + max_new_tokens
        if total > self.args.max_seq_len:
            raise OracleError(
                f"prompt {len(ids)} + {max_new_tokens} new exceeds max_seq_len "
                f"{self.args.max_seq_len}"
            )

        generated: list[int] = []
        vendor_agreements = 0
        vendor_disagreements: list[dict[str, int]] = []
        prefill_seconds = 0.0
        decode_seconds: list[float] = []
        stop_reason = "max_new_tokens"

        prompt = torch.tensor([ids], dtype=torch.long, device=self.device)
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        with torch.inference_mode():
            vendor_ids, logits, _ = self.forward(prompt, 0)
        torch.cuda.synchronize()
        prefill_seconds = time.perf_counter() - started
        self._note_peak()

        next_id, vendor_id = self._select(logits, vendor_ids)
        if next_id == vendor_id:
            vendor_agreements += 1
        else:
            vendor_disagreements.append(
                {"step": 0, "greedy": next_id, "vendor_sample": vendor_id}
            )
        generated.append(next_id)
        if progress is not None:
            progress(0, next_id, prefill_seconds)
        if next_id == eos_token_id:
            stop_reason = "eos"

        position = len(ids)
        while stop_reason != "eos" and len(generated) < max_new_tokens:
            step_started = time.perf_counter()
            step = torch.tensor([[generated[-1]]], dtype=torch.long, device=self.device)
            with torch.inference_mode():
                vendor_ids, logits, _ = self.forward(step, position)
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - step_started
            decode_seconds.append(elapsed)
            self._note_peak()
            next_id, vendor_id = self._select(logits, vendor_ids)
            if next_id == vendor_id:
                vendor_agreements += 1
            else:
                vendor_disagreements.append(
                    {
                        "step": len(generated),
                        "greedy": next_id,
                        "vendor_sample": vendor_id,
                    }
                )
            generated.append(next_id)
            if progress is not None:
                progress(len(generated) - 1, next_id, elapsed)
            position += 1
            if next_id == eos_token_id:
                stop_reason = "eos"

        return {
            "generated_token_ids": generated,
            "stop_reason": stop_reason,
            "prefill_seconds": prefill_seconds,
            "decode_seconds_total": sum(decode_seconds),
            "decode_seconds_per_token": (
                sum(decode_seconds) / len(decode_seconds) if decode_seconds else None
            ),
            "decode_steps": len(decode_seconds),
            "vendor_sample_agreements": vendor_agreements,
            "vendor_sample_disagreements": vendor_disagreements,
            "peak_device_bytes": self.peak_device_bytes,
        }

    def _select(self, logits, vendor_ids) -> tuple[int, int]:  # noqa: ANN001
        """Greedy argmax with ties resolved to the lowest token id."""
        row = logits[0].float().cpu()
        best = float(row.max())
        winner = int((row == best).nonzero()[0].item())
        return winner, int(vendor_ids.flatten()[0].item())

    # -- reporting --------------------------------------------------------
    def environment(self) -> dict[str, Any]:
        torch = self.torch
        properties = torch.cuda.get_device_properties(0)
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        versions: dict[str, str] = {}
        for distribution in (
            "torch",
            "transformers",
            "safetensors",
            "tilelang",
            "apache-tvm-ffi",
            "tokenizers",
        ):
            try:
                versions[distribution] = importlib.metadata.version(distribution)
            except Exception:
                versions[distribution] = "absent"
        return {
            "torch_version": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "device_name": properties.name,
            "compute_capability": list(torch.cuda.get_device_capability(0)),
            "device_total_bytes": int(total_bytes),
            "device_free_bytes_at_start": int(free_bytes),
            "device_shared_memory_per_block_optin": int(
                getattr(properties, "shared_memory_per_block_optin", 0)
            ),
            "package_versions": versions,
            "fast_hadamard_transform": self.hadamard_source,
            "tf32_allowed": bool(torch.backends.cuda.matmul.allow_tf32),
            "expert_numeric_path": self.expert_dtype,
        }
