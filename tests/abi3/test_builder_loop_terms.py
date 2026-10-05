"""Loop selectors are live when an operator executes, not when a view is declared."""

import pytest

from runtime.abi3.builder import BuildError, DeploymentBuilder, DynamicTerm
from runtime.abi3.constants import DType, Major, Tensor
from runtime.abi3.fixture import fixture_capability


def test_predeclared_loop_view_is_checked_at_operator_emission() -> None:
    builder = DeploymentBuilder(
        target_id="loop-liveness",
        model_id="loop-liveness",
        backend="test",
        capability=fixture_capability(),
    )
    loop = builder.loop_control(lower_bound=0, upper_bound=2, step=1)
    view = builder.tensor_view(
        object_id=0,
        dtype=DType.BF16,
        dims=[1],
        dynamic=[DynamicTerm.loop(loop, 1)],
    )
    operator = builder.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[view],
    )

    with pytest.raises(BuildError, match="which is not open here"):
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=operator)

    builder.open_loop(loop)
    builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=operator)
    builder.close_loop()

    with pytest.raises(BuildError, match="which is not open here"):
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=operator)
