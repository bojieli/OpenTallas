"""Request-bound planning with independent query and context symbol maxima.

A private function namespace reuses the pinned planner implementation. No global
monkey patch changes generic builds or concurrent requests.
"""
from dataclasses import replace
from types import FunctionType
from compiler.backends.hbm_sram import plan as baseline

PlanError = baseline.PlanError


def _planner(context_max, diagnostics=None, graph=None):
    scope = dict(vars(baseline))
    for name, value in vars(baseline).items():
        if isinstance(value, FunctionType) and value.__module__ == baseline.__name__:
            clone = FunctionType(value.__code__, scope, value.__name__, value.__defaults__, value.__closure__)
            clone.__kwdefaults__ = value.__kwdefaults__
            scope[name] = clone
    original_extent = scope['request_extent_of']
    def request_extent_of(tensor, query_max):
        if tensor.shape and isinstance(tensor.shape[0], baseline.Symbolic):
            extent = baseline.request_extent_for(tensor.shape[0].symbol)
            if extent is not None and extent.symbol == 'context_length':
                return original_extent(tensor, context_max)
        return original_extent(tensor, query_max)
    scope['request_extent_of'] = request_extent_of
    original_kernels = scope['_plan_kernels']
    def kernels(*args, **kwargs):
        plans, warnings = original_kernels(*args, **kwargs)
        # Context planes are one complete prefix dispatch, independent of
        # query tiling. A divisor of query_max would repeat that prefix.
        plans = tuple(replace(p, context_loop=replace(p.context_loop, divisor=context_max))
                      if p.context_loop is not None else p for p in plans)
        return plans, warnings
    scope['_plan_kernels'] = kernels
    if graph is not None:
        original_scratch = scope['_communication_scratch_bytes']
        tensors = {t.tensor_id: t for t in graph.tensors}
        producers = {name: k for k in graph.kernels for name in k.outputs}
        query_max = next(s.maximum for s in graph.symbols if s.name == 'span_tokens')
        def scratch(kernels, node_count):
            maximum = original_scratch(kernels, node_count)
            if node_count <= 1:
                return maximum
            for kernel in kernels:
                if kernel.link_class != 'sparse_gather':
                    continue
                kv = next(o for o in kernel.operands if o.direction == 'in' and o.slot == 1)
                producer = producers.get(kv.tensor_id)
                if producer is None or 'phase_inputs' not in producer.attributes:
                    continue
                for phase, indices in producer.attributes['phase_inputs'].items():
                    pinned = producer.attributes['phase_symbol_binding'][phase]
                    constants, aliases = scope['phase_substitution'](pinned, producer.kernel_id)
                    extent, static = scope['join_extent_under'](
                        tensors, [producer.inputs[i] for i in indices], 0,
                        query_max, constants, aliases)
                    if extent is not None:
                        extent = scope['extent_on_context_symbol'](extent, aliases)
                        limit = query_max if extent.symbol == 'span_tokens' else context_max
                        rows = extent.numerator * limit // extent.unit + extent.bias
                    else:
                        rows = static
                    # Disjoint node bands reconstruct ONE complete KV plane.
                    maximum = max(maximum, baseline.bytes_for(rows * kv.tile_cols, kv.dtype))
            return baseline.round_up(maximum, 4096)
        scope['_communication_scratch_bytes'] = scratch
        original_activations = scope['_place_activations']
        def activations(*args, **kwargs):
            keys, arenas, arena_of, host = original_activations(*args, **kwargs)
            required = {}
            for producer in graph.kernels:
                if 'phase_inputs' not in producer.attributes:
                    continue
                rows = 0
                for phase, indices in producer.attributes['phase_inputs'].items():
                    constants, aliases = scope['phase_substitution'](
                        producer.attributes['phase_symbol_binding'][phase], producer.kernel_id)
                    extent, static = scope['join_extent_under'](
                        tensors, [producer.inputs[i] for i in indices], 0,
                        query_max, constants, aliases)
                    if extent is not None:
                        extent = scope['extent_on_context_symbol'](extent, aliases)
                        limit = query_max if extent.symbol == 'span_tokens' else context_max
                        count = extent.numerator * limit // extent.unit + extent.bias
                    else:
                        count = static
                    rows = max(rows, count)
                for name in producer.outputs:
                    key = keys.get(name)
                    slot = arena_of.get(key)
                    if slot is None:
                        continue
                    _, cols, _ = baseline.matrix_shape(tensors[name], query_max)
                    needed = baseline.bytes_for(rows * cols, tensors[name].dtype)
                    required[slot] = max(required.get(slot, 0), needed)
            result = []
            for arena in arenas:
                size = max(arena.size_bytes, required.get(arena.slot_id, 0))
                row_bytes = baseline.bytes_for(arena.cols, arena.dtype)
                result.append(replace(arena, size_bytes=size,
                    rows=max(arena.rows, (size + row_bytes - 1)//row_bytes)))
            return keys, tuple(result), arena_of, host
        scope['_place_activations'] = activations
        original_generated = scope['_generated_constants']
        def generated(source, context_max=0, headroom=0):
            headroom = max(headroom, max(baseline.ring_moduli(source), default=1))
            return original_generated(source, context_max, headroom)
        scope['_generated_constants'] = generated
        base_kernels = scope['_plan_kernels']
        def compressor_kernels(*args, **kwargs):
            plans, warnings = base_kernels(*args, **kwargs)
            originals = {k.index: k for k in graph.kernels}
            adjusted = []
            for plan in plans:
                kernel = originals[plan.index]
                ratio = int(kernel.attributes.get('ratio', 1))
                if kernel.kind == 'KV_APPEND' and ratio > query_max and kernel.attributes.get('cache_row') == 'compressed_group_index':
                    # Its prefill predicate is false at this request bound.
                    # Still emit the legal one-trip block-walk geometry, with
                    # induction zero, rather than malformed unreachable views.
                    # The decode path removes the row loop and stays one row.
                    row = baseline.LoopPlan(loop_key=f'k{plan.index}.row', kind='row',
                        trip=1, symbol='span_tokens', divisor=ratio)
                    operands = []
                    for operand in plan.operands:
                        tensor = tensors[operand.tensor_id]
                        extent = scope['request_extent_of'](tensor, query_max)
                        if operand.direction == 'in' and extent is not None and extent.symbol == 'span_tokens':
                            operand = replace(operand,
                                terms=tuple(dict.fromkeys((*operand.terms, 'row'))),
                                extent_numerator=extent.numerator, extent_unit=extent.unit,
                                extent_bias=extent.bias)
                        elif operand.direction == 'in' and operand.tensor_id in baseline.position_inputs(graph):
                            # The position-index operand creates the quotient
                            # walk; it is static metadata, not a payload axis.
                            operand = replace(operand, terms=tuple(dict.fromkeys((*operand.terms, 'row'))))
                        elif operand.direction == 'out':
                            # The quotient-index view derives its walk from
                            # the destination, while the payload walks source.
                            operand = replace(operand, terms=tuple(dict.fromkeys((*operand.terms, 'row'))))
                        operands.append(operand)
                    operands = tuple(operands)
                    plan = replace(plan, row_loop=row, block_rows=ratio, operands=operands)
                adjusted.append(plan)
            return tuple(adjusted), warnings
        scope['_plan_kernels'] = compressor_kernels
    if diagnostics is not None:
        original_prove = scope['_prove']
        def prove(*args, **kwargs):
            result = original_prove(*args, **kwargs)
            diagnostics['proofs'] = dict(result)
            diagnostics['largest_arenas'] = sorted(
                (a.to_dict() for a in args[4]), key=lambda a: a['size_bytes'], reverse=True)[:12]
            diagnostics['state_placements'] = [state.to_dict() for state in args[6]]
            return result
        scope['_prove'] = prove
    return scope['build_plan']


def build_request_plan(graph, capability, **kwargs):
    graph = baseline.as_kernel_graph(graph)
    request = graph.source.get('request_specialization')
    if not request:
        raise PlanError('request planning requires a specialized graph')
    if 'span_override' in kwargs:
        raise PlanError('request planning refuses differential span_override')
    context = next(s.maximum for s in graph.symbols if s.name == 'context_length')
    query = next(s.maximum for s in graph.symbols if s.name == 'span_tokens')
    if context != request['context_capacity'] or query != request['query_rows']:
        raise PlanError('request bounds disagree with persistent capacity or query rows')
    if context > capability.limits['max_context_positions']:
        raise PlanError('persistent context exceeds capability')
    diagnostics = {}
    try:
        return _planner(context, diagnostics, graph)(graph, capability, **kwargs)
    except PlanError as error:
        error.request_diagnostics = diagnostics
        raise
