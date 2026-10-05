"""First-principles technology-envelope derivations.

These functions deliberately stop at physical capacity and raw service ceilings.
They do not infer application throughput, yield, price, or an unexplained
``technology advantage`` multiplier.  Inputs retain their evidence class in the
JSON ledger that calls these functions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math


BITS_PER_BYTE = 8.0


def scaled_density_bytes_mm2(
    *,
    anchor_density_mbit_mm2: float,
    anchor_node_nm: float,
    target_node_nm: float,
    scaling_exponent: float,
) -> float:
    """Scale a measured macro density with an explicit, inspectable exponent.

    Exponent 1 is a wire/periphery-limited linear bound; exponent 2 is ideal
    feature-size-squared scaling.  Neither is promoted to a target-node
    measurement.
    """

    for value in (
        anchor_density_mbit_mm2,
        anchor_node_nm,
        target_node_nm,
        scaling_exponent,
    ):
        if value <= 0:
            raise ValueError("density-scaling inputs must be positive")
    density_mbit = anchor_density_mbit_mm2 * (
        anchor_node_nm / target_node_nm
    ) ** scaling_exponent
    # Decimal Mb and MB match semiconductor macro/data-sheet convention.
    return density_mbit * 1e6 / BITS_PER_BYTE


def usable_array_capacity_bytes(
    *,
    wafer_area_mm2: float,
    macro_density_bytes_mm2: float,
    array_area_fraction: float,
    usable_fraction: float,
) -> float:
    """Capacity after whole-wafer floorplan and repair/spare deductions."""

    if wafer_area_mm2 <= 0 or macro_density_bytes_mm2 <= 0:
        raise ValueError("area and density must be positive")
    if not 0 < array_area_fraction <= 1 or not 0 < usable_fraction <= 1:
        raise ValueError("area and usable fractions must be in (0, 1]")
    return (
        wafer_area_mm2
        * macro_density_bytes_mm2
        * array_area_fraction
        * usable_fraction
    )


def raw_array_bandwidth_bytes_s(
    *,
    wafer_area_mm2: float,
    array_area_fraction: float,
    bandwidth_density_bytes_s_mm2: float,
) -> float:
    """Sum independent macro read service before array/clock derates."""

    if wafer_area_mm2 <= 0 or bandwidth_density_bytes_s_mm2 <= 0:
        raise ValueError("area and bandwidth density must be positive")
    if not 0 < array_area_fraction <= 1:
        raise ValueError("array_area_fraction must be in (0, 1]")
    return wafer_area_mm2 * array_area_fraction * bandwidth_density_bytes_s_mm2


def cim_weight_bandwidth_density_bytes_s_mm2(
    *,
    operations_s: float,
    macro_area_mm2: float,
    operations_per_weight: float,
    weight_bits: float,
) -> float:
    """Convert a macro's operation rate into encoded-weight service density.

    For a dense MVM, one weight participates in one multiply-add, conventionally
    two operations.  This is internal array service, not an external bus rate.
    """

    for value in (operations_s, macro_area_mm2, operations_per_weight, weight_bits):
        if value <= 0:
            raise ValueError("CIM bandwidth inputs must be positive")
    weights_s = operations_s / operations_per_weight
    encoded_bytes_s = weights_s * weight_bits / BITS_PER_BYTE
    return encoded_bytes_s / macro_area_mm2


@dataclass(frozen=True)
class HBMPackage:
    stacks: int
    stack_capacity_bytes: float
    stack_bandwidth_bytes_s: float
    capacity_bytes: float
    bandwidth_bytes_s: float
    perimeter_pitch_utilization: float

    def to_dict(self) -> dict:
        return asdict(self)


def hbm_package(
    *,
    stacks: int,
    stack_capacity_bytes: float,
    stack_bandwidth_bytes_s: float,
    wafer_perimeter_mm: float,
    stack_pitch_mm: float,
) -> HBMPackage:
    """Check the first-order wafer-edge stack pitch and derive raw totals."""

    if stacks <= 0:
        raise ValueError("HBM stack count must be positive")
    for value in (
        stack_capacity_bytes,
        stack_bandwidth_bytes_s,
        wafer_perimeter_mm,
        stack_pitch_mm,
    ):
        if value <= 0:
            raise ValueError("HBM package inputs must be positive")
    pitch_use = stacks * stack_pitch_mm / wafer_perimeter_mm
    if pitch_use > 1 + 1e-12:
        raise ValueError(
            f"{stacks} HBM stacks require {pitch_use:.1%} of ideal perimeter pitch"
        )
    return HBMPackage(
        stacks=stacks,
        stack_capacity_bytes=stack_capacity_bytes,
        stack_bandwidth_bytes_s=stack_bandwidth_bytes_s,
        capacity_bytes=stacks * stack_capacity_bytes,
        bandwidth_bytes_s=stacks * stack_bandwidth_bytes_s,
        perimeter_pitch_utilization=pitch_use,
    )


def area_scaled_product_value(
    *, value: float, source_area_mm2: float, target_area_mm2: float
) -> float:
    """Iso-node, iso-composition area extrapolation used only as a control."""

    if value <= 0 or source_area_mm2 <= 0 or target_area_mm2 <= 0:
        raise ValueError("area-scaling inputs must be positive")
    return value * target_area_mm2 / source_area_mm2


def geometric_midpoint(lower: float, upper: float) -> float:
    if lower <= 0 or upper <= 0 or lower > upper:
        raise ValueError("geometric midpoint requires 0 < lower <= upper")
    return math.sqrt(lower * upper)
