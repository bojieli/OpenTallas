"""Host-performance observations for the ABI 3.0 functional simulator.

These observations explain where simulator wall time and host memory go.  They
are deliberately separate from :mod:`runtime.sim.counters`: that module is the
frozen architectural counter registry shared with the cycle model and RTL,
whereas decoded-weight caches, route scans, resident set size, and page faults
are properties of this simulator process.

One recorder belongs to one activated :class:`runtime.sim.device.Device` and
therefore covers every resolver in a multi-node deployment.  The lock is cheap
under today's sequential node issue and makes the ownership correct before a
bounded worker pool is introduced.
"""

from __future__ import annotations

import hashlib
import json
import resource
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_ZERO_TOTALS = {
    "routed_operator_issues": 0,
    "routed_semantic_segments": 0,
    "routed_physical_backend_calls": 0,
    "routed_selected_rows": 0,
    "routed_weight_source_bytes": 0,
    "decoded_weight_materializations": 0,
    "decoded_weight_source_bytes": 0,
    "decoded_weight_result_bytes": 0,
    "route_organization_passes": 0,
    "route_unique_scans": 0,
    "route_row_selection_scans": 0,
    # WP-E replaces the scans above with stable buckets.  Keeping the zero in
    # cache-off/bucket-off baselines makes that change directly comparable.
    "route_bucket_builds": 0,
    # WP-D owns these fields.  Its required default budget is zero.
    "decoded_weight_cache_budget_bytes": 0,
    "decoded_weight_cache_hits": 0,
    "decoded_weight_cache_misses": 0,
    "decoded_weight_cache_bypasses": 0,
    "decoded_weight_cache_admissions": 0,
    "decoded_weight_cache_evictions": 0,
    "decoded_weight_cache_allocation_failures": 0,
    "decoded_weight_cache_live_bytes": 0,
    "decoded_weight_cache_high_water_bytes": 0,
}

_ZERO_DURATIONS_NS = {
    "routed_operator": 0,
    "routed_contraction": 0,
    "decoded_weight_materialization": 0,
    "route_organization": 0,
}


@dataclass(frozen=True, slots=True)
class ProcessSample:
    """One read-only observation of this simulator process."""

    resident_bytes: int | None
    resident_high_water_bytes: int | None
    minor_page_faults: int
    major_page_faults: int

    def to_dict(self) -> dict[str, int | None]:
        return {
            "resident_bytes": self.resident_bytes,
            "resident_high_water_bytes": self.resident_high_water_bytes,
            "minor_page_faults": self.minor_page_faults,
            "major_page_faults": self.major_page_faults,
        }


def sample_process() -> ProcessSample:
    """Read RSS/high-water RSS and page faults without changing process state."""

    resident: int | None = None
    high_water: int | None = None
    status = Path("/proc/self/status")
    try:
        for line in status.read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                resident = int(line.split()[1]) * 1024
            elif line.startswith("VmHWM:"):
                high_water = int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        # Page-fault observations below remain portable.  An unavailable live
        # RSS is explicit ``null`` rather than a fabricated zero.
        pass
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # Linux reports ru_maxrss in KiB.  Prefer /proc's unambiguous byte value;
    # on another platform leave the unavailable field explicit.
    if high_water is None and status.exists():
        high_water = int(usage.ru_maxrss) * 1024
    return ProcessSample(
        resident_bytes=resident,
        resident_high_water_bytes=high_water,
        minor_page_faults=int(usage.ru_minflt),
        major_page_faults=int(usage.ru_majflt),
    )


def _association_record(
    key: tuple[str, tuple[int, ...], tuple[int, ...], tuple[int, ...]],
    call_count: int,
) -> dict[str, Any]:
    contract, activation, weight, output = key
    return {
        "numeric_contract": contract,
        "activation_shape": list(activation),
        "weight_shape": list(weight),
        "output_shape": list(output),
        "call_count": int(call_count),
    }


class HostPerformanceObservations:
    """Device-wide host observations with transaction-delta snapshots."""

    __slots__ = (
        "_activation_process",
        "_association_calls",
        "_association_runs",
        "_durations_ns",
        "_lock",
        "_totals",
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._totals = dict(_ZERO_TOTALS)
        self._durations_ns = dict(_ZERO_DURATIONS_NS)
        self._association_runs: list[
            list[Any]
        ] = []  # [association key, adjacent call count]
        self._association_calls = 0
        self._activation_process = sample_process()

    def add(self, name: str, amount: int = 1) -> None:
        if name not in _ZERO_TOTALS:
            raise KeyError(f"unknown host-performance total {name!r}")
        value = int(amount)
        if value < 0:
            raise ValueError(f"host-performance amount for {name} is negative")
        if value == 0:
            return
        with self._lock:
            self._totals[name] += value

    def maximum(self, name: str, value: int) -> None:
        if name not in _ZERO_TOTALS:
            raise KeyError(f"unknown host-performance maximum {name!r}")
        candidate = int(value)
        if candidate < 0:
            raise ValueError(f"host-performance maximum for {name} is negative")
        with self._lock:
            self._totals[name] = max(self._totals[name], candidate)

    def set_value(self, name: str, value: int) -> None:
        """Set a gauge such as cache live bytes under the recorder lock."""

        if name not in _ZERO_TOTALS:
            raise KeyError(f"unknown host-performance gauge {name!r}")
        current = int(value)
        if current < 0:
            raise ValueError(f"host-performance gauge for {name} is negative")
        with self._lock:
            self._totals[name] = current

    def add_duration_ns(self, name: str, duration_ns: int) -> None:
        if name not in _ZERO_DURATIONS_NS:
            raise KeyError(f"unknown host-performance duration {name!r}")
        value = int(duration_ns)
        if value < 0:
            raise ValueError(f"host-performance duration for {name} is negative")
        with self._lock:
            self._durations_ns[name] += value

    def record_association(
        self,
        *,
        contract: str,
        activation_shape: tuple[int, ...],
        weight_shape: tuple[int, ...],
        output_shape: tuple[int, ...],
    ) -> None:
        """Append one blocked contraction to an adjacent run-length stream."""

        key = (
            str(contract),
            tuple(int(value) for value in activation_shape),
            tuple(int(value) for value in weight_shape),
            tuple(int(value) for value in output_shape),
        )
        with self._lock:
            self._association_calls += 1
            if self._association_runs and self._association_runs[-1][0] == key:
                self._association_runs[-1][1] += 1
            else:
                self._association_runs.append([key, 1])

    def checkpoint(self) -> dict[str, Any]:
        """Return additive totals from which one transaction delta is made."""

        with self._lock:
            return {
                "totals": dict(self._totals),
                "durations_ns": dict(self._durations_ns),
                "association_calls": self._association_calls,
            }

    def transaction_delta(
        self,
        before: Mapping[str, Any],
        process_before: ProcessSample,
        process_after: ProcessSample,
    ) -> dict[str, Any]:
        """Describe only the work and process changes of one transaction."""

        after = self.checkpoint()
        totals = {
            key: int(after["totals"][key]) - int(before["totals"].get(key, 0))
            for key in _ZERO_TOTALS
        }
        durations = {
            f"{key}_seconds": (
                int(after["durations_ns"][key])
                - int(before["durations_ns"].get(key, 0))
            )
            / 1_000_000_000.0
            for key in _ZERO_DURATIONS_NS
        }
        return {
            "schema": "opentallas.abi3.host_performance.transaction.v1",
            "totals": totals,
            "durations": durations,
            "blocked_association_calls": int(after["association_calls"])
            - int(before.get("association_calls", 0)),
            "process": {
                "before": process_before.to_dict(),
                "after": process_after.to_dict(),
                "minor_page_faults": (
                    process_after.minor_page_faults
                    - process_before.minor_page_faults
                ),
                "major_page_faults": (
                    process_after.major_page_faults
                    - process_before.major_page_faults
                ),
            },
        }

    def snapshot(self) -> dict[str, Any]:
        """Return the complete device-epoch observation and ordered manifest."""

        current_process = sample_process()
        with self._lock:
            totals = dict(self._totals)
            durations_ns = dict(self._durations_ns)
            associations = [
                _association_record(key, count)
                for key, count in self._association_runs
            ]
            association_calls = int(self._association_calls)
        association_body = {
            "association_policy": "executed_order_adjacent_run_length",
            "runs": associations,
            "run_count": len(associations),
            "blocked_call_count": association_calls,
        }
        encoded = json.dumps(
            association_body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        association_body["manifest_sha256"] = hashlib.sha256(encoded).hexdigest()
        return {
            "schema": "opentallas.abi3.host_performance.device_epoch.v1",
            "scope": "one_activated_device_including_all_logical_nodes",
            "architectural_counter_registry_unchanged": True,
            "totals": totals,
            "durations": {
                f"{key}_seconds": value / 1_000_000_000.0
                for key, value in durations_ns.items()
            },
            "ordered_executed_associations": association_body,
            "process": {
                "activation": self._activation_process.to_dict(),
                "current": current_process.to_dict(),
                "minor_page_faults_since_activation": (
                    current_process.minor_page_faults
                    - self._activation_process.minor_page_faults
                ),
                "major_page_faults_since_activation": (
                    current_process.major_page_faults
                    - self._activation_process.major_page_faults
                ),
            },
        }
