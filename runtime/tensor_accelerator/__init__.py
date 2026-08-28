"""Artifact-only functional and data-bearing timing simulator."""

from .simulator import SimulationError, TensorAcceleratorSimulator
from .production_simulator import (
    ProductionProjectionSimulator,
    ProductionSimulationError,
    publish_execution_report,
)
from .production_rmsnorm_simulator import (
    ProductionRMSNormSimulationError,
    ProductionRMSNormSimulator,
    publish_rmsnorm_execution_report,
)
from .production_qkv_simulator import (
    ProductionQKVSimulationError,
    ProductionQKVSimulator,
    publish_qkv_execution_report,
)

__all__ = [
    "ProductionProjectionSimulator",
    "ProductionSimulationError",
    "ProductionRMSNormSimulationError",
    "ProductionRMSNormSimulator",
    "ProductionQKVSimulationError",
    "ProductionQKVSimulator",
    "SimulationError",
    "TensorAcceleratorSimulator",
    "publish_execution_report",
    "publish_rmsnorm_execution_report",
    "publish_qkv_execution_report",
]
