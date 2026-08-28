"""Production-path compiler primitives for the programmable tensor accelerator.

The package is additive to the ROM-bound executable fixture.  Its first qualified
profile is deliberately small, but the artifact boundaries are the same ones
used by the planned Qwen3 and DeepSeek frontends.
"""

from .build import TensorAcceleratorBuildError, build_deployment
from .bf16_qualification import (
    BF16QualificationError,
    publish_qualification_report,
    qualify_bf16_projection_payloads,
    qualify_locked_bf16_projection,
)
from .capability import Capability, CapabilityError, load_capability
from .model import ModelGraph, ModelGraphError, load_model_graph
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    load_production_model_graph,
    parse_production_model_graph,
)
from .qwen3_adapter import (
    Qwen3ProductionAdapterError,
    export_qwen3_production_graph,
    publish_qwen3_production_graph,
)

__all__ = [
    "Capability",
    "CapabilityError",
    "BF16QualificationError",
    "ModelGraph",
    "ModelGraphError",
    "ProductionModelGraph",
    "ProductionModelGraphError",
    "Qwen3ProductionAdapterError",
    "TensorAcceleratorBuildError",
    "build_deployment",
    "export_qwen3_production_graph",
    "load_capability",
    "load_model_graph",
    "load_production_model_graph",
    "parse_production_model_graph",
    "publish_qualification_report",
    "publish_qwen3_production_graph",
    "qualify_bf16_projection_payloads",
    "qualify_locked_bf16_projection",
]
