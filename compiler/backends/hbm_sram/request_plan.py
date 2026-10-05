"""Production request-bound planning without the differential span override."""
from compiler.backends.hbm_sram.plan import build_plan, PlanError, as_kernel_graph


def build_request_plan(graph, capability, **kwargs):
    graph = as_kernel_graph(graph)
    request = graph.source.get('request_specialization')
    if not request:
        raise PlanError('request planning requires a specialized graph')
    if 'span_override' in kwargs:
        raise PlanError('request planning refuses differential span_override')
    context = next(s.maximum for s in graph.symbols if s.name == 'context_length')
    if context != request['context_capacity']:
        raise PlanError('request context disagrees with persistent capacity')
    if context > capability.limits['max_context_positions']:
        raise PlanError('persistent context exceeds capability')
    return build_plan(graph, capability, **kwargs)
