"""Production-path compiler primitives for the programmable tensor accelerator.

The package is additive to the ROM-bound executable fixture.  Its first qualified
profile is deliberately small, but the artifact boundaries are the same ones
used by the planned Qwen3 and DeepSeek frontends.
"""

from .build import TensorAcceleratorBuildError, build_deployment
from .capability import Capability, CapabilityError, load_capability
from .model import ModelGraph, ModelGraphError, load_model_graph
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    load_production_model_graph,
    parse_production_model_graph,
)

__all__ = [
    "Capability",
    "CapabilityError",
    "ModelGraph",
    "ModelGraphError",
    "ProductionModelGraph",
    "ProductionModelGraphError",
    "TensorAcceleratorBuildError",
    "build_deployment",
    "load_capability",
    "load_model_graph",
    "load_production_model_graph",
    "parse_production_model_graph",
]
