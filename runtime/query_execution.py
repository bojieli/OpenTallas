"""Query lifetime admission for explicitly specialized compiler deployments.

This narrows request admission; it never changes arithmetic or engine handlers.
Legacy deployments without the contract keep their existing behavior.
"""
from __future__ import annotations

from typing import Any, Mapping

from runtime.abi3.descriptors import Phase, Symbol


def validate_query_execution(contract: Mapping[str, Any]) -> None:
    if contract.get("schema") != "deepseek-v41-query-execution-v1":
        raise ValueError("unknown query execution contract")
    mode = contract.get("mode")
    if mode not in ("generic", "decode", "bounded-prefill"):
        raise ValueError("unknown query execution mode")
    for name in ("context_tokens", "query_tokens", "decode_tokens", "prefill_tokens"):
        if type(contract.get(name)) is not int:
            raise ValueError(f"query execution {name} must be an integer")
    context, query = contract["context_tokens"], contract["query_tokens"]
    if not 1 <= query <= context or contract["decode_tokens"] != 1:
        raise ValueError("invalid context/query/decode bounds")
    if mode == "decode" and (query != 1 or contract["prefill_tokens"] != 0):
        raise ValueError("decode specialization must have one query and no prefill")
    if mode != "decode" and contract["prefill_tokens"] != query:
        raise ValueError("prefill bound must equal admitted query block")
    if mode == "generic" and query != context:
        raise ValueError("generic prefill retains its full context-sized query block")
    if contract.get("prefill_position_start") != 0:
        raise ValueError("released prefill requires position_start zero")


def admit_query_execution(
    contract: Mapping[str, Any] | None, symbols: Mapping[int, int], phase: int,
) -> None:
    if contract is None:
        return
    validate_query_execution(contract)
    if int(symbols.get(int(Symbol.PHASE), phase)) != phase:
        raise ValueError("request phase disagrees with selected entrypoint")
    span = int(symbols[int(Symbol.SPAN_TOKENS)])
    context = int(symbols[int(Symbol.CONTEXT_LENGTH)])
    start = int(symbols[int(Symbol.POSITION_START)])
    if not 1 <= context <= contract["context_tokens"]:
        raise ValueError("request exceeds compiled context capacity")
    if phase == int(Phase.DECODE):
        maximum = contract["decode_tokens"]
    elif phase == int(Phase.PREFILL):
        maximum = contract["prefill_tokens"]
        if start != 0:
            raise ValueError("later prefill chunks are not the released position-zero operation")
    else:
        raise ValueError("unknown request phase")
    if not 1 <= span <= maximum:
        raise ValueError(f"request span {span} exceeds compiled phase bound {maximum}")
