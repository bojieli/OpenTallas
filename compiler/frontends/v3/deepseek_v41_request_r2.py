"""Opt-in request-sized DS V4.1 IR; generic export remains unchanged."""
from copy import deepcopy
from compiler.ir.v3.kernel_ir import KernelGraph
from compiler.frontends.v3.deepseek_v41 import export_deepseek_v41_kernel_graph


def specialize_request(graph: KernelGraph, *, phase: str, prefill_chunk_tokens: int | None = None) -> KernelGraph:
    """Bound query rows independently from persistent context capacity.

    Prefill bounds the initial position-zero request. The companion driver
    retains absolute position and all persistent state on one-token continuations.
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
            # Zero groups remain predicate-controlled at runtime.
            value['maximum'] = (rows // ratio) * value.get('multiplier', 1)
        elif symbol.startswith('attention_rows_ratio'):
            ratio = int(symbol.removeprefix('attention_rows_ratio'))
            value['maximum'] = (rows + rows // ratio) * value.get('multiplier', 1)
        return value

    body = bound(body)
    for symbol in body['symbols']:
        if symbol['name'] == 'span_tokens':
            symbol['maximum'] = rows
        elif symbol['name'].startswith('span_groups_ratio'):
            symbol['maximum'] = rows // int(symbol['name'].removeprefix('span_groups_ratio'))
        elif symbol['name'].startswith('attention_rows_ratio'):
            ratio = int(symbol['name'].removeprefix('attention_rows_ratio'))
            symbol['maximum'] = rows + rows // ratio
    for state in body['states']:
        if state['state_id'].startswith(('candidate_pool_mask.', 'index_selection.')):
            # The mask persists across layers/tokens, but has only query rows.
            state['capacity_rows'] = rows
    # Neutral ABI admission requires both entrypoints. Preserve the table;
    # the emitted program enforces the query-row bound for both phases.
    if phase not in {e['phase'] for e in body['entrypoints']}:
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


def prompt_ingestion_graph(graph: KernelGraph) -> KernelGraph:
    """Execute the released forward/KV path without sampling prompt tokens.

    This is a separate teacher-forced prompt deployment. It returns logits and
    never appends model-selected tokens between causal prompt continuations.
    """
    body = deepcopy(graph.to_dict())
    removed = [k for k in body['kernels']
               if k['attributes'].get('source_operation_kind') == 'SAMPLE']
    if {k['kind'] for k in removed} != {'SCALE', 'ARGMAX', 'TOKEN_APPEND'}:
        raise ValueError('source must contain the exact released SAMPLE tail')
    removed_outputs = {t for k in removed for t in k['outputs']}
    body['kernels'] = [k for k in body['kernels'] if k not in removed]
    for index, kernel in enumerate(body['kernels']):
        kernel['index'] = index
    body['tensors'] = [t for t in body['tensors'] if t['tensor_id'] not in removed_outputs]
    for entry in body['entrypoints']:
        entry['outputs'] = [t for t in entry['outputs'] if t not in removed_outputs]
    body['generation_policy'] = {}
    body['source']['prompt_ingestion_only'] = True
    body['source']['sampling_tail_removed'] = [k['kernel_id'] for k in removed]
    return KernelGraph.from_dict(body)
