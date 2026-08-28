"""Production-path compiler primitives for the programmable tensor accelerator.

The package is additive to the ROM-bound executable fixture.  Its first qualified
profile is deliberately small, but the artifact boundaries are the same ones
used by the planned Qwen3 and DeepSeek frontends.
"""

from .build import TensorAcceleratorBuildError, build_deployment
from .bf16_qualification import (
    BF16QualificationError,
    load_qualification_report,
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
from .production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from .production_projection import (
    ProductionProjectionBuildError,
    build_projection_deployment,
)
from .production_projection_checking import (
    ProductionProjectionCheckError,
    check_projection_candidate,
)
from .production_rmsnorm import (
    ProductionRMSNormBuildError,
    build_rmsnorm_deployment,
)
from .production_rmsnorm_checking import (
    ProductionRMSNormCheckError,
    check_rmsnorm_candidate,
)
from .qwen3_adapter import (
    Qwen3ProductionAdapterError,
    export_qwen3_production_graph,
    publish_qwen3_production_graph,
)
from .rmsnorm_qualification import (
    RMSNormQualificationError,
    load_rmsnorm_qualification,
    publish_rmsnorm_qualification,
    qualify_locked_rmsnorm,
    qualify_rmsnorm_payloads,
)

__all__ = [
    "Capability",
    "CapabilityError",
    "BF16QualificationError",
    "ModelGraph",
    "ModelGraphError",
    "ProductionModelGraph",
    "ProductionModelGraphError",
    "ProductionCapability",
    "ProductionCapabilityError",
    "ProductionProjectionBuildError",
    "ProductionProjectionCheckError",
    "ProductionRMSNormBuildError",
    "ProductionRMSNormCheckError",
    "Qwen3ProductionAdapterError",
    "RMSNormQualificationError",
    "TensorAcceleratorBuildError",
    "build_deployment",
    "build_projection_deployment",
    "build_rmsnorm_deployment",
    "check_projection_candidate",
    "check_rmsnorm_candidate",
    "export_qwen3_production_graph",
    "load_capability",
    "load_model_graph",
    "load_production_capability",
    "load_production_model_graph",
    "load_qualification_report",
    "load_rmsnorm_qualification",
    "parse_production_model_graph",
    "publish_qualification_report",
    "publish_qwen3_production_graph",
    "publish_rmsnorm_qualification",
    "qualify_bf16_projection_payloads",
    "qualify_locked_bf16_projection",
    "qualify_locked_rmsnorm",
    "qualify_rmsnorm_payloads",
]
