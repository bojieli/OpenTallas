"""Cross-backend ownership of ABI 3.0 execution-contract substitutions."""

from compiler.backends.hbm_sram.lower import EXECUTION_CONTRACT as HBM_CONTRACTS
from compiler.backends.numeric_contracts import (
    BLOCKED_CONTRACTION_CONTRACT,
    EXECUTION_CONTRACT,
    reduction_order_for,
)
from compiler.backends.rom.common.program import EXECUTION_CONTRACT as ROM_CONTRACTS
from runtime.abi3.constants import ReductionOrder


DEEPSEEK_PLAIN_CONTRACTIONS = {
    "matrix_bf16_linear_bf16_v1",
    "grouped_output_project_bf16_v1",
    "lm_head_bf16_vocabulary_projection_v1",
    "matrix_dense_fp8_linear_bf16_block_scaled_contraction_v1",
    "routing_router_score_bf16_v1",
    "fp8_swiglu_bf16_gate_contraction_v1",
    "fp8_swiglu_bf16_up_contraction_v1",
    "fp8_swiglu_bf16_down_contraction_v1",
    "mxfp4_swiglu_bf16_gate_contraction_v1",
    "mxfp4_swiglu_bf16_up_contraction_v1",
    "mxfp4_swiglu_bf16_down_contraction_v1",
}


def test_rom_and_hbm_consume_one_execution_contract_table() -> None:
    assert ROM_CONTRACTS is EXECUTION_CONTRACT
    assert HBM_CONTRACTS is EXECUTION_CONTRACT


def test_every_deepseek_plain_contraction_selects_blocked_accumulation() -> None:
    assert DEEPSEEK_PLAIN_CONTRACTIONS <= EXECUTION_CONTRACT.keys()
    for contract in DEEPSEEK_PLAIN_CONTRACTIONS:
        assert EXECUTION_CONTRACT[contract] == BLOCKED_CONTRACTION_CONTRACT


def test_graph_declared_reduction_order_precedes_contract_name() -> None:
    assert reduction_order_for(
        "dispatch_reduce_expert_outputs_bf16_v1",
        "EXPERT_REDUCE",
        {"reduction_order": "pairwise_tree"},
    ) is ReductionOrder.PAIRWISE_TREE


def test_contract_derived_reduction_orders_remain_explicit() -> None:
    assert reduction_order_for(
        "hyper_connection_hc_pre_bf16_v1", "HYPER_CONNECT_PRE"
    ) is ReductionOrder.PAIRWISE_TREE
    assert reduction_order_for(
        BLOCKED_CONTRACTION_CONTRACT, "MATMUL"
    ) is ReductionOrder.BLOCKED_ASCENDING
    assert reduction_order_for(
        "unrecognised_reference_owner_v1", "MATMUL"
    ) is ReductionOrder.SEQUENTIAL_ASCENDING
