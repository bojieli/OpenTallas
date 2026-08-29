"""Execution backends for the ABI 3.0 functional device.

Amendment A7 of ``docs/TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md``
declares two numeric contracts for the BF16 contraction, and this module is the
single place where either one is executed.

``bf16_bf16_fp32_sequential_rne_v1``
    BF16 operands widened exactly to binary32, exact products, strictly
    ascending-K binary32 accumulation, one RNE output rounding.  Reproducible
    on any machine, and therefore the numeric oracle.  Every backend routes
    this contract to the *same* host kernel, so selecting a backend cannot
    change a sequential result.

``bf16_bf16_fp32_blocked_rne_v1``
    BF16 operands widened exactly to binary32, exact products, binary32
    accumulation in the executing implementation's declared deterministic
    blocked association, one RNE output rounding.  The association is fixed by
    an *implementation identity* -- library, version, device and shape -- which
    :meth:`Backend.implementation_identity` returns and every execution report
    must record.  Two runs of the same implementation are bit-identical; the
    contract makes no portability claim across implementations, and anything
    that reports "exact" without naming which contract it means is incomplete.

Why this exists at all is measured, not asserted: at Qwen3-8B shapes the exact
scalar sequential kernel runs at roughly 0.15 GMAC/s, which puts one
8,000-token prefill (6.06e13 MAC) at about 112 hours.  The mandatory workloads
cannot run on it.  ``tools/qualify_numeric_contracts.py`` measures both the
speed and the numeric gap and writes the result to
``results/abi3/numeric_contract_qualification.json``.

Three rules hold everywhere in this module.

*Fail closed.*  An unavailable backend, an unknown contract, or a context in
which TF32 is enabled raises :class:`BackendError`.  Nothing silently degrades
to a different association or a lower mantissa precision.

*One backend per execution.*  Every target of a comparison must run on the same
backend, so that a ROM-versus-HBM token difference is a real difference and
never an artifact of association.  The selection is process-wide and explicit.

*TF32 is off.*  NVIDIA's TF32 mode silently truncates the binary32 significand
to 10 bits inside the matmul.  That would break the "exact products, binary32
accumulation" half of the blocked contract, so the torch backends force it off
and re-check the flag before every contraction.
"""

from __future__ import annotations

import hashlib
import os
import platform
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

import numpy as np

from runtime.abi3.builder import NUMERIC_CONTRACT_REDUCTION_ORDER
from runtime.abi3.constants import ReductionOrder
from runtime.abi3.descriptors import ExtendedDescriptorType

# cuBLAS picks its reduction split from a workspace it allocates once per
# handle.  Pinning the workspace shape makes the split, and therefore the
# blocked association, identical between processes as well as within one.  This
# must be set before CUDA is initialised, so it happens at import time and the
# effective value is recorded in the implementation identity.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


class BackendError(RuntimeError):
    """Raised when a backend is unavailable, misconfigured or misused."""


# ---------------------------------------------------------------------------
# Numeric contracts
# ---------------------------------------------------------------------------
#: The exact, portable, strictly ascending-K contraction.  The oracle.
CONTRACT_SEQUENTIAL = "bf16_bf16_fp32_sequential_rne_v1"
#: The executing implementation's deterministic blocked association.
CONTRACT_BLOCKED = "bf16_bf16_fp32_blocked_rne_v1"

#: Contraction contracts this module knows how to execute.
MATMUL_CONTRACTS = frozenset({CONTRACT_SEQUENTIAL, CONTRACT_BLOCKED})

#: RMSNorm materialises the normalised value in BF16 before the gain multiply.
CONTRACT_QWEN_RMSNORM = "qwen3_rmsnorm_fp32_bf16_v1"
#: RMSNorm stays in binary32 through the gain multiply, rounding once.
CONTRACT_DEEPSEEK_RMSNORM = "deepseek_rmsnorm_binary32_v1"

#: Contract names some emitters still spell as the reference owner they pin.
#: These are aliases, not separate contracts: the arithmetic is identical, so
#: resolving them here is what stops a DeepSeek deployment from silently
#: executing the Qwen rounding (they disagree by 1 ulp on ~27 % of elements).
CONTRACT_ALIASES: Mapping[str, str] = {
    "runtime.reference.normalization.rms_norm_bf16": CONTRACT_DEEPSEEK_RMSNORM,
    "runtime.tensor_accelerator.rmsnorm.rms_norm_bf16": CONTRACT_QWEN_RMSNORM,
}

#: Every contract name this module recognises, alias included.
KNOWN_CONTRACTS: frozenset[str] = frozenset(
    {
        CONTRACT_SEQUENTIAL,
        CONTRACT_BLOCKED,
        CONTRACT_QWEN_RMSNORM,
        CONTRACT_DEEPSEEK_RMSNORM,
        *CONTRACT_ALIASES,
    }
)


def contract_digest(contract: str) -> bytes:
    """The 32-byte digest a numeric descriptor carries for ``contract``."""
    return hashlib.sha256(contract.encode("ascii")).digest()


#: Digest -> canonical contract name, aliases resolved to their canonical form.
_CONTRACT_BY_DIGEST: dict[bytes, str] = {
    contract_digest(name): CONTRACT_ALIASES.get(name, name)
    for name in KNOWN_CONTRACTS
}


def contract_for_digest(digest: bytes | None) -> str:
    """Resolve a numeric descriptor's ``contract_digest`` to a contract name.

    Returns ``""`` for a digest this module does not recognise.  That is
    deliberate: the digest space is open -- an emitter may pin any reference
    owner it likes -- so an unrecognised digest means "no contract-specific
    behaviour is selected here", and the *operation* decides whether that is
    acceptable.  Fail-closed happens where a contract is required, not where a
    digest is merely read.
    """
    if not digest:
        return ""
    return _CONTRACT_BY_DIGEST.get(bytes(digest), "")


def declared_contract(table: Any, numeric_profile_id: int) -> str:
    """The contract name a numeric descriptor declares, or ``""``."""
    descriptor = table.get(numeric_profile_id, ExtendedDescriptorType.NUMERIC)
    return contract_for_digest(descriptor.payload.get("contract_digest"))


def required_reduction_order(contract: str) -> int | None:
    """The reduction order a contract fixes, or ``None`` when it fixes none."""
    order = NUMERIC_CONTRACT_REDUCTION_ORDER.get(contract)
    return None if order is None else int(order)


# ---------------------------------------------------------------------------
# Shared exact kernels
# ---------------------------------------------------------------------------
#: Bounded work tile of the frozen sequential kernel.
SEQUENTIAL_ROW_TILE = 8
SEQUENTIAL_COL_TILE = 64


def sequential_matmul_binary32(
    activations: np.ndarray, weights: np.ndarray
) -> np.ndarray:
    """``[M,K] @ [N,K]^T`` under ``bf16_bf16_fp32_sequential_rne_v1``.

    The products are materialised so the host cannot contract them into an
    FMA, every exact zero is canonicalised before accumulation, and
    ``np.add.accumulate`` performs the strictly ordered binary32 reduction.
    This runs on the host for every backend: the sequential contract is defined
    to be reproducible on any machine, so it must not depend on which backend
    is selected.
    """
    left = np.ascontiguousarray(activations, dtype=np.float32)
    right = np.ascontiguousarray(weights, dtype=np.float32)
    if left.ndim != 2 or right.ndim != 2 or left.shape[1] != right.shape[1]:
        raise BackendError(
            f"sequential contraction shapes {left.shape} and {right.shape} do "
            "not contract as [M,K] x [N,K]^T"
        )
    rows, cols = left.shape[0], right.shape[0]
    output = np.empty((rows, cols), dtype=np.float32)
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        for row_start in range(0, rows, SEQUENTIAL_ROW_TILE):
            row_end = min(row_start + SEQUENTIAL_ROW_TILE, rows)
            row_tile = left[row_start:row_end]
            for col_start in range(0, cols, SEQUENTIAL_COL_TILE):
                col_end = min(col_start + SEQUENTIAL_COL_TILE, cols)
                col_tile = right[col_start:col_end]
                products = np.multiply(
                    row_tile[:, None, :], col_tile[None, :, :], dtype=np.float32
                )
                if not np.all(np.isfinite(products)):
                    raise BackendError("contraction product left the binary32 range")
                products[products == 0] = np.float32(0.0)
                final = np.add.accumulate(products, axis=2, dtype=np.float32)[:, :, -1]
                if not np.all(np.isfinite(final)):
                    raise BackendError("contraction sum left the binary32 range")
                output[row_start:row_end, col_start:col_end] = final
    finally:
        np.seterr(**previous)
    return output


@dataclass(frozen=True, slots=True)
class NarrowResult:
    """BF16 codes and the count of elements that saturated the BF16 range."""

    codes: Any
    saturations: int


# ---------------------------------------------------------------------------
# Backend interface
# ---------------------------------------------------------------------------
class Backend(ABC):
    """One arithmetic substrate.

    A backend is never a model and never a fallback.  It is the substrate a
    simulated engine computes on, exactly as a C++ simulator would call a BLAS
    kernel, and every contract it executes has a bit-exact scalar oracle.

    Values crossing this interface are either host :class:`numpy.ndarray` or
    opaque *device handles* produced by :meth:`place`.  Every method accepts
    both and returns a handle of the backend's own kind; :meth:`fetch` brings
    one back to the host.
    """

    #: Registry name, as accepted by :func:`select_backend`.
    name: str = ""

    # -- availability ----------------------------------------------------
    @classmethod
    @abstractmethod
    def is_available(cls) -> tuple[bool, str]:
        """``(available, reason)``.  ``reason`` explains an unavailable one."""

    @abstractmethod
    def implementation_identity(self) -> dict[str, Any]:
        """Library, version, device and flags that fix the blocked association.

        Every execution report records this.  Two runs of the same identity are
        bit-identical; two different identities make no compatibility claim.
        """

    # -- placement -------------------------------------------------------
    @abstractmethod
    def place(self, array: np.ndarray) -> Any:
        """Move or map a host array onto this backend's device."""

    @abstractmethod
    def fetch(self, value: Any) -> np.ndarray:
        """Return ``value`` as a host :class:`numpy.ndarray`."""

    @property
    @abstractmethod
    def device(self) -> str:
        """The device this backend computes on, as a stable string."""

    # -- conversion ------------------------------------------------------
    @abstractmethod
    def widen_bf16(self, codes: Any) -> Any:
        """Widen architectural BF16 bit patterns to binary32.  Exact."""

    @abstractmethod
    def narrow_rne(self, values: Any) -> NarrowResult:
        """Round binary32 to BF16, ties to even, saturating to the max finite.

        This is the frozen conversion of
        ``runtime/tensor_accelerator/bf16.py``: one rounding, ties to even,
        an overflow clamped to ``0x7f7f`` with its sign and counted, and a
        negative zero canonicalised to ``+0``.
        """

    # -- arithmetic ------------------------------------------------------
    @abstractmethod
    def matmul_binary32(self, a: Any, w: Any, *, contract: str) -> Any:
        """``[M,K] @ [N,K]^T -> [M,N]`` under the named numeric contract.

        Weights are n-major, matching the checkpoint layout, so no relayout
        pass exists.  ``contract`` must name one of :data:`MATMUL_CONTRACTS`;
        anything else raises rather than choosing an association silently.
        """

    @abstractmethod
    def elementwise(self, op: str, *operands: Any) -> Any:
        """One binary32 elementwise operation.

        ``op`` is one of ``multiply``, ``add``, ``subtract``, ``divide``,
        ``maximum``, ``minimum``, ``negative``, ``square`` or ``reciprocal``.
        """

    @abstractmethod
    def reduce_sum(self, values: Any, *, order: int) -> Any:
        """Reduce each row of ``[rows, width]`` under a declared order."""

    @abstractmethod
    def row_max(self, values: Any) -> Any:
        """The maximum of each row, kept as a ``[rows, 1]`` column."""

    @abstractmethod
    def all_finite(self, values: Any) -> bool:
        """Whether every element is a finite binary32 value."""

    @abstractmethod
    def zeros(self, shape: tuple[int, ...]) -> Any:
        """A binary32 zero tensor on this backend's device."""

    # -- convenience -----------------------------------------------------
    def multiply(self, left: Any, right: Any) -> Any:
        return self.elementwise("multiply", left, right)

    def add(self, left: Any, right: Any) -> Any:
        return self.elementwise("add", left, right)

    def subtract(self, left: Any, right: Any) -> Any:
        return self.elementwise("subtract", left, right)

    def divide(self, left: Any, right: Any) -> Any:
        return self.elementwise("divide", left, right)

    def device_cache_bytes(self) -> int:
        """Byte budget a caller may keep resident on this backend's device."""
        return 0

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return f"<{type(self).__name__} {self.name} on {self.device}>"


def _check_matmul_contract(contract: str) -> None:
    if contract not in MATMUL_CONTRACTS:
        raise BackendError(
            f"numeric contract {contract!r} is not a contraction contract; "
            f"expected one of {sorted(MATMUL_CONTRACTS)}.  An unnamed or "
            "unknown contract must not pick an accumulation association."
        )


# ---------------------------------------------------------------------------
# NumPy backend
# ---------------------------------------------------------------------------
class NumpyBackend(Backend):
    """The always-available host backend.

    The blocked association is NumPy's own ``matmul``: for binary32 operands it
    dispatches to the linked BLAS, whose blocking is fixed by that library,
    its version and the shape.  That is exactly what the blocked contract
    declares, and it is recorded as such rather than described as "exact".
    """

    name = "numpy"

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        return True, ""

    @property
    def device(self) -> str:
        return "host"

    def implementation_identity(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "library": "numpy",
            "library_version": np.__version__,
            "device": self.device,
            "device_name": f"{platform.machine()} {platform.processor()}".strip(),
            "blas": _numpy_blas_identity(),
            "flags": {
                "allow_tf32": False,
                "float32_matmul_precision": "highest",
            },
            "blocked_association": (
                "numpy.matmul over binary32, blocked by the linked BLAS; fixed "
                "by (library, version, device, shape)"
            ),
        }

    # -- placement -------------------------------------------------------
    def place(self, array: np.ndarray) -> np.ndarray:
        return np.asarray(array)

    def fetch(self, value: Any) -> np.ndarray:
        return np.asarray(value)

    # -- conversion ------------------------------------------------------
    def widen_bf16(self, codes: Any) -> np.ndarray:
        array = np.asarray(codes)
        if array.dtype != np.uint16:
            raise BackendError(
                f"BF16 codes must be carried as uint16, not {array.dtype}"
            )
        bits = np.ascontiguousarray(array, dtype=np.uint16).astype(
            np.uint32
        ) << np.uint32(16)
        return np.ascontiguousarray(bits).view(np.float32)

    def narrow_rne(self, values: Any) -> NarrowResult:
        array = np.ascontiguousarray(self.fetch(values), dtype=np.float32)
        if not np.all(np.isfinite(array)):
            raise BackendError("binary32 result is NaN or infinity")
        bits = array.view(np.uint32)
        upper = bits >> np.uint32(16)
        discarded = bits & np.uint32(0xFFFF)
        increment = (discarded > np.uint32(0x8000)) | (
            (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
        )
        rounded = upper + increment.astype(np.uint32)
        saturated = (rounded & np.uint32(0x7F80)) == np.uint32(0x7F80)
        saturations = int(np.count_nonzero(saturated))
        signs = rounded & np.uint32(0x8000)
        rounded = np.where(saturated, signs | np.uint32(0x7F7F), rounded)
        rounded = np.where((rounded & np.uint32(0x7FFF)) == 0, 0, rounded)
        return NarrowResult(
            np.ascontiguousarray(rounded, dtype=np.uint16), saturations
        )

    # -- arithmetic ------------------------------------------------------
    def matmul_binary32(self, a: Any, w: Any, *, contract: str) -> np.ndarray:
        _check_matmul_contract(contract)
        left = np.ascontiguousarray(self.fetch(a), dtype=np.float32)
        right = np.ascontiguousarray(self.fetch(w), dtype=np.float32)
        if contract == CONTRACT_SEQUENTIAL:
            return sequential_matmul_binary32(left, right)
        previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
        try:
            out = np.matmul(left, right.T, dtype=np.float32)
        finally:
            np.seterr(**previous)
        if not np.all(np.isfinite(out)):
            raise BackendError("contraction left the binary32 range")
        return np.ascontiguousarray(out, dtype=np.float32)

    def elementwise(self, op: str, *operands: Any) -> np.ndarray:
        values = [np.asarray(self.fetch(x), dtype=np.float32) for x in operands]
        previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
        try:
            if op == "multiply":
                out = np.multiply(values[0], values[1], dtype=np.float32)
            elif op == "add":
                out = np.add(values[0], values[1], dtype=np.float32)
            elif op == "subtract":
                out = np.subtract(values[0], values[1], dtype=np.float32)
            elif op == "divide":
                out = np.divide(values[0], values[1], dtype=np.float32)
            elif op == "maximum":
                out = np.maximum(values[0], values[1], dtype=np.float32)
            elif op == "minimum":
                out = np.minimum(values[0], values[1], dtype=np.float32)
            elif op == "negative":
                out = np.negative(values[0], dtype=np.float32)
            elif op == "square":
                out = np.multiply(values[0], values[0], dtype=np.float32)
            elif op == "reciprocal":
                out = np.divide(np.float32(1.0), values[0], dtype=np.float32)
            else:
                raise BackendError(f"elementwise operation {op!r} is not defined")
        finally:
            np.seterr(**previous)
        return np.ascontiguousarray(out, dtype=np.float32)

    def reduce_sum(self, values: Any, *, order: int) -> np.ndarray:
        return _numpy_reduce_sum(
            np.ascontiguousarray(self.fetch(values), dtype=np.float32), int(order)
        )

    def row_max(self, values: Any) -> np.ndarray:
        array = np.ascontiguousarray(self.fetch(values), dtype=np.float32)
        return np.max(array, axis=-1, keepdims=True)

    def all_finite(self, values: Any) -> bool:
        return bool(np.all(np.isfinite(np.asarray(self.fetch(values)))))

    def zeros(self, shape: tuple[int, ...]) -> np.ndarray:
        return np.zeros(tuple(shape), dtype=np.float32)


def _numpy_reduce_sum(values: np.ndarray, order: int) -> np.ndarray:
    """Reduce the last axis of ``values`` under a declared reduction order."""
    if values.ndim != 2:
        values = values.reshape(-1, values.shape[-1])
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        if order == int(ReductionOrder.SEQUENTIAL_ASCENDING):
            return np.ascontiguousarray(
                np.add.accumulate(values, axis=1, dtype=np.float32)[:, -1]
            )
        if order == int(ReductionOrder.PAIRWISE_TREE):
            level = np.ascontiguousarray(values, dtype=np.float32)
            while level.shape[1] > 1:
                if level.shape[1] & 1:
                    level = np.concatenate(
                        (level, np.zeros((level.shape[0], 1), dtype=np.float32)),
                        axis=1,
                    )
                level = np.add(level[:, 0::2], level[:, 1::2], dtype=np.float32)
            return np.ascontiguousarray(level[:, 0], dtype=np.float32)
        if order == int(ReductionOrder.BLOCKED_ASCENDING):
            width = values.shape[1]
            if width < 8:
                return np.ascontiguousarray(
                    np.add.accumulate(values, axis=1, dtype=np.float32)[:, -1]
                )
            lanes = np.ascontiguousarray(values[:, :8], dtype=np.float32).copy()
            full = width - width % 8
            for start in range(8, full, 8):
                lanes = np.add(lanes, values[:, start : start + 8], dtype=np.float32)
            tail = width - full
            if tail:
                lanes[:, :tail] = np.add(
                    lanes[:, :tail], values[:, full:], dtype=np.float32
                )
            half = np.add(lanes[:, :4], lanes[:, 4:], dtype=np.float32)
            quarter = np.add(half[:, :2], half[:, 2:], dtype=np.float32)
            return np.ascontiguousarray(
                np.add(quarter[:, 0], quarter[:, 1], dtype=np.float32)
            )
    finally:
        np.seterr(**previous)
    raise BackendError(f"reduction order {order} is not implemented")


def _numpy_blas_identity() -> dict[str, str]:
    """Name the BLAS whose blocking fixes the NumPy blocked association."""
    try:  # NumPy 2 exposes a structured configuration record.
        config = np.show_config(mode="dicts")  # type: ignore[call-arg]
    except Exception:  # pragma: no cover - older NumPy or no config
        return {"name": "unknown", "version": "unknown"}
    try:
        blas = config["Build Dependencies"]["blas"]
        return {
            "name": str(blas.get("name", "unknown")),
            "version": str(blas.get("version", "unknown")),
        }
    except Exception:  # pragma: no cover - layout differs by build
        return {"name": "unknown", "version": "unknown"}


# ---------------------------------------------------------------------------
# Torch backends
# ---------------------------------------------------------------------------
def _import_torch():
    try:
        import torch  # noqa: PLC0415  (deliberately lazy: torch is optional)
    except Exception as exc:  # pragma: no cover - depends on the environment
        raise BackendError(f"PyTorch is not importable: {exc}") from exc
    return torch


class TorchBackend(Backend):
    """Common PyTorch substrate.  Subclasses fix the device."""

    torch_device = "cpu"

    def __init__(self) -> None:
        available, reason = type(self).is_available()
        if not available:
            raise BackendError(
                f"backend {self.name!r} is unavailable: {reason}.  An "
                "unavailable backend fails closed; it never falls back to "
                "another association."
            )
        self.torch = _import_torch()
        self._configure_precision()
        self._device = self.torch.device(self.torch_device)

    # -- precision -------------------------------------------------------
    def _configure_precision(self) -> None:
        """Force full binary32 significands and verify that it took.

        TF32 rounds the significand to 10 bits inside the matmul.  It is a
        silent precision reduction with no descriptor field to declare it, so
        it is disabled and then re-read rather than assumed.
        """
        torch = self.torch
        torch.set_float32_matmul_precision("highest")
        for holder, attribute in (
            (getattr(torch.backends, "cuda", None), "matmul"),
            (getattr(torch.backends, "cudnn", None), None),
        ):
            if holder is None:
                continue
            target = holder if attribute is None else getattr(holder, attribute, None)
            if target is not None and hasattr(target, "allow_tf32"):
                try:
                    target.allow_tf32 = False
                except Exception:  # pragma: no cover - read-only in some builds
                    pass
            if target is not None and hasattr(target, "fp32_precision"):
                try:
                    target.fp32_precision = "ieee"
                except Exception:  # pragma: no cover - not in every build
                    pass
        self._assert_tf32_off()

    def _assert_tf32_off(self) -> None:
        for flag, value in self._tf32_flags().items():
            if value is True:
                raise BackendError(
                    f"{flag} is enabled; TF32 truncates the binary32 "
                    "significand to 10 bits and would violate the exact-product "
                    "half of both numeric contracts"
                )
        precision = self.torch.get_float32_matmul_precision()
        if precision != "highest":
            raise BackendError(
                f"float32 matmul precision is {precision!r}; the numeric "
                "contracts require 'highest'"
            )

    def _tf32_flags(self) -> dict[str, Any]:
        torch = self.torch
        flags: dict[str, Any] = {}
        cuda = getattr(torch.backends, "cuda", None)
        matmul = getattr(cuda, "matmul", None) if cuda is not None else None
        if matmul is not None and hasattr(matmul, "allow_tf32"):
            flags["torch.backends.cuda.matmul.allow_tf32"] = bool(matmul.allow_tf32)
        cudnn = getattr(torch.backends, "cudnn", None)
        if cudnn is not None and hasattr(cudnn, "allow_tf32"):
            flags["torch.backends.cudnn.allow_tf32"] = bool(cudnn.allow_tf32)
        return flags

    # -- placement -------------------------------------------------------
    @property
    def device(self) -> str:
        return str(self._device)

    def _tensor(self, value: Any, dtype: Any = None) -> Any:
        torch = self.torch
        if isinstance(value, torch.Tensor):
            tensor = value
            if tensor.device != self._device:
                tensor = tensor.to(self._device)
        else:
            tensor = self.place(np.asarray(value))
        if dtype is not None and tensor.dtype != dtype:
            tensor = tensor.to(dtype)
        return tensor

    def place(self, array: np.ndarray) -> Any:
        torch = self.torch
        if isinstance(array, torch.Tensor):
            return array.to(self._device)
        host = np.asarray(array)
        if host.dtype == np.uint16:
            # torch.from_numpy accepts uint16, but the int16 reinterpretation
            # is guaranteed zero-copy on every build, and BF16 codes are bit
            # patterns rather than numbers until widen_bf16 decodes them.
            host = host.view(np.int16)
        if not host.flags["C_CONTIGUOUS"]:
            host = np.ascontiguousarray(host)
        return torch.from_numpy(host).to(self._device)

    def fetch(self, value: Any) -> np.ndarray:
        torch = self.torch
        if isinstance(value, torch.Tensor):
            return value.detach().cpu().numpy()
        return np.asarray(value)

    # -- conversion ------------------------------------------------------
    def widen_bf16(self, codes: Any) -> Any:
        torch = self.torch
        tensor = codes if isinstance(codes, torch.Tensor) else self.place(codes)
        if tensor.dtype not in (torch.int16, torch.uint16, torch.int32):
            raise BackendError(
                f"BF16 codes must be carried as a 16-bit pattern, not {tensor.dtype}"
            )
        widened = tensor.to(torch.int32).bitwise_and(0xFFFF) << 16
        return widened.contiguous().view(torch.float32)

    def narrow_rne(self, values: Any) -> NarrowResult:
        torch = self.torch
        tensor = self._tensor(values, torch.float32).contiguous()
        if not bool(torch.isfinite(tensor).all()):
            raise BackendError("binary32 result is NaN or infinity")
        bits = tensor.view(torch.int32)
        upper = (bits >> 16) & 0xFFFF
        discarded = bits & 0xFFFF
        increment = (discarded > 0x8000) | ((discarded == 0x8000) & ((upper & 1) != 0))
        rounded = upper + increment.to(torch.int32)
        saturated = (rounded & 0x7F80) == 0x7F80
        saturations = int(torch.count_nonzero(saturated))
        signs = rounded & 0x8000
        rounded = torch.where(saturated, signs | 0x7F7F, rounded)
        rounded = torch.where(
            (rounded & 0x7FFF) == 0, torch.zeros_like(rounded), rounded
        )
        # Every value now lies in [0, 0xffff], so the narrowing cast to the
        # architectural 16-bit code is exact rather than a wrap.
        return NarrowResult(rounded.to(torch.uint16), saturations)

    # -- arithmetic ------------------------------------------------------
    def matmul_binary32(self, a: Any, w: Any, *, contract: str) -> Any:
        _check_matmul_contract(contract)
        torch = self.torch
        if contract == CONTRACT_SEQUENTIAL:
            # The sequential contract is defined to be machine-independent, so
            # it runs on the one host kernel for every backend.  Routing it to
            # a library matmul would silently substitute a blocked association
            # for the ordered one the descriptor named.
            return self.place(
                sequential_matmul_binary32(
                    self.fetch(self._tensor(a, torch.float32)),
                    self.fetch(self._tensor(w, torch.float32)),
                )
            )
        self._assert_tf32_off()
        left = self._tensor(a, torch.float32)
        right = self._tensor(w, torch.float32)
        if left.ndim != 2 or right.ndim != 2 or left.shape[1] != right.shape[1]:
            raise BackendError(
                f"blocked contraction shapes {tuple(left.shape)} and "
                f"{tuple(right.shape)} do not contract as [M,K] x [N,K]^T"
            )
        out = torch.matmul(left, right.transpose(0, 1))
        if not bool(torch.isfinite(out).all()):
            raise BackendError("contraction left the binary32 range")
        return out

    def elementwise(self, op: str, *operands: Any) -> Any:
        torch = self.torch
        values = [self._tensor(x, torch.float32) for x in operands]
        if op == "multiply":
            return torch.mul(values[0], values[1])
        if op == "add":
            return torch.add(values[0], values[1])
        if op == "subtract":
            return torch.sub(values[0], values[1])
        if op == "divide":
            return torch.div(values[0], values[1])
        if op == "maximum":
            return torch.maximum(values[0], values[1])
        if op == "minimum":
            return torch.minimum(values[0], values[1])
        if op == "negative":
            return torch.neg(values[0])
        if op == "square":
            return torch.mul(values[0], values[0])
        if op == "reciprocal":
            return torch.div(torch.ones_like(values[0]), values[0])
        raise BackendError(f"elementwise operation {op!r} is not defined")

    def reduce_sum(self, values: Any, *, order: int) -> Any:
        torch = self.torch
        tensor = self._tensor(values, torch.float32)
        if tensor.ndim != 2:
            tensor = tensor.reshape(-1, tensor.shape[-1])
        order = int(order)
        if order == int(ReductionOrder.PAIRWISE_TREE):
            level = tensor
            while level.shape[1] > 1:
                if level.shape[1] & 1:
                    pad = torch.zeros(
                        (level.shape[0], 1), dtype=level.dtype, device=level.device
                    )
                    level = torch.cat((level, pad), dim=1)
                level = torch.add(level[:, 0::2], level[:, 1::2])
            return level[:, 0].contiguous()
        if order in (
            int(ReductionOrder.SEQUENTIAL_ASCENDING),
            int(ReductionOrder.BLOCKED_ASCENDING),
        ):
            # Neither order has a torch primitive whose association is
            # declared, so both run on the host kernel that does declare one.
            return self.place(_numpy_reduce_sum(self.fetch(tensor), order))
        raise BackendError(f"reduction order {order} is not implemented")

    def row_max(self, values: Any) -> Any:
        torch = self.torch
        tensor = self._tensor(values, torch.float32)
        return torch.amax(tensor, dim=-1, keepdim=True)

    def all_finite(self, values: Any) -> bool:
        torch = self.torch
        if isinstance(values, torch.Tensor):
            return bool(torch.isfinite(values).all())
        return bool(np.all(np.isfinite(np.asarray(values))))

    def zeros(self, shape: tuple[int, ...]) -> Any:
        return self.torch.zeros(
            tuple(shape), dtype=self.torch.float32, device=self._device
        )

    # -- identity --------------------------------------------------------
    def implementation_identity(self) -> dict[str, Any]:
        torch = self.torch
        flags = dict(self._tf32_flags())
        flags["float32_matmul_precision"] = torch.get_float32_matmul_precision()
        flags["cublas_workspace_config"] = os.environ.get(
            "CUBLAS_WORKSPACE_CONFIG", ""
        )
        return {
            "backend": self.name,
            "library": "torch",
            "library_version": torch.__version__,
            "device": self.device,
            "device_name": self._device_name(),
            "flags": flags,
            "blocked_association": (
                "torch.matmul over binary32; the library's blocked association "
                "is fixed by (library, version, device, shape)"
            ),
        }

    def _device_name(self) -> str:
        return f"{platform.machine()} {platform.processor()}".strip() or "host"


class TorchCpuBackend(TorchBackend):
    """PyTorch on the host CPU."""

    name = "torch_cpu"
    torch_device = "cpu"

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        try:
            _import_torch()
        except BackendError as exc:
            return False, str(exc)
        return True, ""


class TorchCudaBackend(TorchBackend):
    """PyTorch on a CUDA device.

    The blocked association here is cuBLAS's.  It is deterministic for a fixed
    (library, version, device, shape) and a pinned workspace, which is what
    makes ``bf16_bf16_fp32_blocked_rne_v1`` reproducible -- and no more than
    that.  Weights stream: a Qwen deployment addresses 16 GB and this device
    does not have it free, so nothing here assumes residency.
    """

    name = "torch_cuda"
    torch_device = "cuda"

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        try:
            torch = _import_torch()
        except BackendError as exc:
            return False, str(exc)
        if not torch.cuda.is_available():
            return False, "torch.cuda.is_available() is False"
        if torch.cuda.device_count() < 1:
            return False, "no CUDA device is visible"
        return True, ""

    def __init__(self) -> None:
        super().__init__()
        self._index = self.torch.cuda.current_device()
        self._device = self.torch.device(f"cuda:{self._index}")

    def _device_name(self) -> str:
        return self.torch.cuda.get_device_name(self._index)

    def implementation_identity(self) -> dict[str, Any]:
        body = super().implementation_identity()
        torch = self.torch
        major, minor = torch.cuda.get_device_capability(self._index)
        body["device"] = f"cuda:{self._index}"
        body["cuda_version"] = str(torch.version.cuda)
        body["compute_capability"] = f"{major}.{minor}"
        free, total = torch.cuda.mem_get_info(self._index)
        body["device_memory_bytes"] = {"free": int(free), "total": int(total)}
        return body

    def device_cache_bytes(self) -> int:
        """How many bytes of weights a caller may hold resident.

        Zero by default: this device is shared with other tenants and the model
        does not fit, so weights stream unless an operator explicitly opts in
        through ``OPENTALLAS_ABI3_DEVICE_CACHE_BYTES``.
        """
        try:
            budget = int(os.environ.get("OPENTALLAS_ABI3_DEVICE_CACHE_BYTES", "0"))
        except ValueError:
            raise BackendError(
                "OPENTALLAS_ABI3_DEVICE_CACHE_BYTES must be an integer byte count"
            ) from None
        if budget < 0:
            raise BackendError("OPENTALLAS_ABI3_DEVICE_CACHE_BYTES must not be negative")
        if budget == 0:
            return 0
        free, _ = self.torch.cuda.mem_get_info(self._index)
        # Never claim the whole free pool: other tenants hold this device too.
        return min(budget, int(free * 0.5))

    def fetch(self, value: Any) -> np.ndarray:
        torch = self.torch
        if isinstance(value, torch.Tensor) and value.is_cuda:
            torch.cuda.synchronize(self._device)
        return super().fetch(value)


# ---------------------------------------------------------------------------
# Registry and selection
# ---------------------------------------------------------------------------
#: Registry name -> backend class.  ``numpy`` is the default and is always
#: available; the others fail closed when their library or device is missing.
BACKENDS: Mapping[str, type[Backend]] = {
    NumpyBackend.name: NumpyBackend,
    TorchCpuBackend.name: TorchCpuBackend,
    TorchCudaBackend.name: TorchCudaBackend,
}

#: The backend used when neither an explicit selection nor the environment
#: names one.  NumPy has no optional dependency and no device to lose.
DEFAULT_BACKEND = NumpyBackend.name

#: Environment variable naming the process-wide backend.
BACKEND_ENVIRONMENT_VARIABLE = "OPENTALLAS_ABI3_BACKEND"

_selected: str | None = None
_instances: dict[str, Backend] = {}


def backend_names() -> tuple[str, ...]:
    return tuple(sorted(BACKENDS))


def available_backends() -> tuple[str, ...]:
    """Backend names whose library and device are present on this machine."""
    return tuple(
        name for name in sorted(BACKENDS) if BACKENDS[name].is_available()[0]
    )


def backend_availability() -> dict[str, dict[str, Any]]:
    """Availability and reason per registered backend, for a report."""
    out: dict[str, dict[str, Any]] = {}
    for name in sorted(BACKENDS):
        available, reason = BACKENDS[name].is_available()
        out[name] = {"available": bool(available), "reason": reason}
    return out


def _resolve_name(name: str | None) -> str:
    if name is not None:
        return name
    if _selected is not None:
        return _selected
    return os.environ.get(BACKEND_ENVIRONMENT_VARIABLE, "").strip() or DEFAULT_BACKEND


def get_backend(name: str | None = None) -> Backend:
    """Return a backend by name, by explicit selection, or by environment.

    Resolution order is: the ``name`` argument, then a previous
    :func:`select_backend`, then ``OPENTALLAS_ABI3_BACKEND``, then
    :data:`DEFAULT_BACKEND`.  An unknown or unavailable name raises; it never
    resolves to a different backend, because a silent substitution would change
    the accumulation association underneath a comparison.
    """
    resolved = _resolve_name(name)
    if resolved not in BACKENDS:
        raise BackendError(
            f"unknown execution backend {resolved!r}; registered backends are "
            f"{list(backend_names())}"
        )
    instance = _instances.get(resolved)
    if instance is None:
        cls = BACKENDS[resolved]
        available, reason = cls.is_available()
        if not available:
            raise BackendError(
                f"execution backend {resolved!r} is unavailable: {reason}.  "
                "It fails closed rather than falling back, so that every "
                "target of a comparison runs on one association."
            )
        instance = cls()
        _instances[resolved] = instance
    return instance


def select_backend(name: str | None) -> Backend | None:
    """Fix the process-wide backend, or clear the selection with ``None``."""
    global _selected
    if name is None:
        _selected = None
        return None
    backend = get_backend(name)
    _selected = backend.name
    return backend


def selected_backend_name() -> str:
    """The name :func:`get_backend` would resolve to right now."""
    return _resolve_name(None)


@contextmanager
def backend_scope(name: str | None) -> Iterator[Backend]:
    """Temporarily fix the process-wide backend."""
    global _selected
    previous = _selected
    try:
        yield get_backend(name) if name is not None else get_backend()
        if name is not None:
            _selected = name
    finally:
        _selected = previous


def reset_backends() -> None:
    """Drop every cached backend instance and clear the selection."""
    global _selected
    _selected = None
    _instances.clear()


__all__ = [
    "BACKENDS",
    "BACKEND_ENVIRONMENT_VARIABLE",
    "Backend",
    "BackendError",
    "CONTRACT_ALIASES",
    "CONTRACT_BLOCKED",
    "CONTRACT_DEEPSEEK_RMSNORM",
    "CONTRACT_QWEN_RMSNORM",
    "CONTRACT_SEQUENTIAL",
    "DEFAULT_BACKEND",
    "KNOWN_CONTRACTS",
    "MATMUL_CONTRACTS",
    "NarrowResult",
    "NumpyBackend",
    "TorchCpuBackend",
    "TorchCudaBackend",
    "available_backends",
    "backend_availability",
    "backend_names",
    "backend_scope",
    "contract_digest",
    "contract_for_digest",
    "declared_contract",
    "get_backend",
    "required_reduction_order",
    "reset_backends",
    "select_backend",
    "selected_backend_name",
    "sequential_matmul_binary32",
]
