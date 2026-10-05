from __future__ import annotations

import pytest

from compiler.qwen3.adapter import build_tensor_specs, load_official_config
from compiler.qwen3.graph import build_graph_nodes, build_official_graph_contract
from compiler.qwen3.isa import assemble
from compiler.qwen3.runtime import Qwen3RuntimeError, Qwen3ServiceEngine
from compiler.qwen3.tokenizer import Qwen3Tokenizer, Qwen3TokenizerError


def test_runtime_rejects_generation_that_would_process_past_8000() -> None:
    import threading

    engine = object.__new__(Qwen3ServiceEngine)
    engine._operation_lock = threading.RLock()
    with pytest.raises(Qwen3RuntimeError, match="beyond 8,000"):
        engine.generate_greedy([1] * 8000, max_new_tokens=2)
    with pytest.raises(Qwen3RuntimeError, match="positive integer"):
        engine.generate_greedy([1], max_new_tokens=0)
    with pytest.raises(Qwen3RuntimeError, match="at least one token"):
        engine.generate_greedy([], max_new_tokens=1)


def test_runtime_fails_closed_on_concurrent_session_use() -> None:
    import threading

    engine = object.__new__(Qwen3ServiceEngine)
    engine._operation_lock = threading.Lock()
    assert engine._operation_lock.acquire(blocking=False)
    try:
        with pytest.raises(Qwen3RuntimeError, match="another operation"):
            engine.run_span([1])
        with pytest.raises(Qwen3RuntimeError, match="another operation"):
            engine.generate_greedy([1], max_new_tokens=1)
    finally:
        engine._operation_lock.release()


def test_runtime_rejects_use_after_close() -> None:
    import threading

    engine = object.__new__(Qwen3ServiceEngine)
    engine._operation_lock = threading.RLock()
    engine._closed = True
    with pytest.raises(Qwen3RuntimeError, match="closed"):
        engine.run_span([1])
    with pytest.raises(Qwen3RuntimeError, match="closed"):
        engine.generate_greedy([1], max_new_tokens=1)


def test_execution_expectations_reconcile_full_graph_and_long_context() -> None:
    from types import SimpleNamespace

    engine = object.__new__(Qwen3ServiceEngine)
    engine.config = load_official_config()
    specs = build_tensor_specs(engine.config)
    engine.nodes = build_graph_nodes(engine.config)
    engine.locations = {
        spec.name: SimpleNamespace(shape=spec.shape, size_bytes=spec.size_bytes)
        for spec in specs
    }
    engine.program = assemble(
        engine.nodes,
        tuple(spec.name for spec in specs),
        build_official_graph_contract()["graph_id"],
    )
    engine.device = SimpleNamespace(type="cuda")

    decode = engine._expected_counters(7999, 1)
    assert decode["matrix_multiplications"] == 253
    assert decode["matrix_multiply_add_operations"] == 15_136_194_560
    assert decode["attention_multiply_add_operations"] == 4_718_592_000
    assert decode["kv_bytes_read"] == 1_179_648_000
    assert decode["rom_weight_bytes_addressed"] == 16_381_470_720

    prefill = engine._expected_counters(0, 8000)
    assert prefill["tokens_processed"] == 8000
    assert prefill["matrix_multiply_add_operations"] == 111_133_523_443_712
    assert prefill["attention_multiply_add_operations"] == 18_876_727_296_000
    assert prefill["vector_elements_processed"] == 11_239_424_000


@pytest.mark.parametrize(
    "messages,match",
    [
        ([], "nonempty"),
        ([{"role": "user", "content": "<|im_end|>"}], "reserved delimiter"),
        ([{"role": "root", "content": "x"}], "unsupported role"),
        ([{"role": "user", "content": ["x"]}], "must be text"),
        ([{"role": "user", "content": "x", "extra": 1}], "fields differ"),
    ],
)
def test_chat_boundary_fails_closed(messages: list, match: str) -> None:
    with pytest.raises(Qwen3TokenizerError, match=match):
        Qwen3Tokenizer._validate_messages(messages)


def test_valid_chat_boundary_normalizes_optional_template_fields() -> None:
    assert Qwen3Tokenizer._validate_messages(
        [{"role": "user", "content": "hello"}]
    ) == [
        {
            "content": "hello",
            "reasoning_content": None,
            "role": "user",
            "tool_calls": [],
        }
    ]
