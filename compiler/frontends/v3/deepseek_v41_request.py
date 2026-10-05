"""Opt-in request-sized DS V4.1 IR; generic export remains unchanged."""
from copy import deepcopy
from compiler.ir.v3.kernel_ir import KernelGraph
from compiler.frontends.v3.deepseek_v41 import export_deepseek_v41_kernel_graph


def specialize_request(graph: KernelGraph, *, phase: str, prefill_chunk_tokens: int | None = None) -> KernelGraph:
    """Bound query rows independently from persistent context capacity.

    Prefill is a bounded request graph, not an automatic chunk execution driver.
    Callers must retain absolute position and all persistent state between chunks.
    No kernel arithmetic, reduction order, predicate or state initialization changes.
    """
    if phase not in ('decode', 'prefill'):
        raise ValueError('phase must be decode or prefill')
    context = next(s.maximum for s in graph.symbols if s.name == 'context_length')
    if phase == 'decode':
        if prefill_chunk_tokens is not None:
            raise ValueError('decode does not accept a prefill chunk size')
        rows = 1
    else:
        if not isinstance(prefill_chunk_tokens, int) or isinstance(prefill_chunk_tokens, bool) or not 1 <= prefill_chunk_tokens <= context:
            raise ValueError('prefill requires an explicit chunk bound within context capacity')
        rows = prefill_chunk_tokens
    body = deepcopy(graph.to_dict())
    original = next(s.maximum for s in graph.symbols if s.name == 'span_tokens')
    if rows > original:
        raise ValueError('request cannot enlarge the source span bound')

    def bound(value):
        if isinstance(value, list):
            return [bound(v) for v in value]
        if not isinstance(value, dict):
            return value
        value = {k: bound(v) for k, v in value.items()}
        symbol = value.get('symbol', '')
        if symbol == 'span_tokens':
            value['maximum'] = rows * value.get('multiplier', 1)
        elif symbol.startswith('span_groups_ratio'):
            ratio = int(symbol.removeprefix('span_groups_ratio'))
            # Zero groups are predicate-controlled; zero maximum means unknown
            # in the legacy planner, so reserve one seat for that guarded path.
            value['maximum'] = max(1, rows // ratio) * value.get('multiplier', 1)
        return value

    body = bound(body)
    for symbol in body['symbols']:
        if symbol['name'] == 'span_tokens':
            symbol['maximum'] = rows
        elif symbol['name'].startswith('span_groups_ratio'):
            symbol['maximum'] = max(1, rows // int(symbol['name'].removeprefix('span_groups_ratio')))
    for state in body['states']:
        if state['state_id'].startswith('candidate_pool_mask.'):
            # The mask persists across layers/tokens, but has only query rows.
            state['capacity_rows'] = rows
    body['entrypoints'] = [e for e in body['entrypoints'] if e['phase'] == phase]
    if not body['entrypoints']:
        raise ValueError('source graph has no selected entrypoint')
    body['source']['request_specialization'] = {
        'phase': phase, 'query_rows': rows, 'context_capacity': context,
        'original_graph_id': graph.graph_id,
        'persistent_state_reinitialization_between_chunks': False,
        'automatic_prefill_chunk_driver': False,
    }
    return KernelGraph.from_dict(body)


def export_request_graph(*, phase: str, prefill_chunk_tokens: int | None = None, **kwargs) -> KernelGraph:
    return specialize_request(export_deepseek_v41_kernel_graph(**kwargs), phase=phase,
                              prefill_chunk_tokens=prefill_chunk_tokens)
