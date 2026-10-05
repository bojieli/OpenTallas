"""Production lowering for the opt-in DS request graph.

Reuse the pinned emitter body in an isolated symbol-resolution namespace.
Generic emitter globals and independent checker remain untouched.
"""
from types import FunctionType
from compiler.frontends.v3.deepseek_v41_request_r2 import specialize_request, prompt_ingestion_graph
from compiler.backends.hbm_sram import plan as baseline
from compiler.backends.hbm_sram.request_plan_r2 import build_request_plan, _planner
from compiler.backends.hbm_sram import lower as lowering
from compiler.backends.hbm_sram.check import check_deployment
from runtime.abi3.verifier import verify_deployment


def _emitter_class(context_max):
    scope = dict(vars(lowering))
    plan_scope = _planner(context_max).__globals__
    def clone(value):
        fn = FunctionType(value.__code__, scope, value.__name__, value.__defaults__, value.__closure__)
        fn.__kwdefaults__ = value.__kwdefaults__
        return fn
    for name, value in vars(lowering).items():
        if isinstance(value, FunctionType):
            if value.__module__ == baseline.__name__:
                scope[name] = plan_scope[value.__name__]
            elif value.__module__ == lowering.__name__:
                scope[name] = clone(value)
    methods = {}
    for name, value in vars(lowering._Emitter).items():
        if isinstance(value, FunctionType):
            methods[name] = clone(value)
        elif isinstance(value, staticmethod):
            methods[name] = staticmethod(clone(value.__func__))
    original_topology = methods['_declare_topology']
    def topology(self):
        original_topology(self)
        # Enforce the specialized query bound in the actual program, before
        # any state preparation or arithmetic issue; a host note is not a gate.
        bound = self.graph.source['request_specialization']['query_rows']
        predicate = self._predicate_descriptor(f'span_tokens > {bound}')
        self.builder.emit(lowering.Major.CONTROL, lowering.Control.TRAP,
                          predicate_id=predicate)
    methods['_declare_topology'] = topology
    original_entrypoints = methods['_declare_entrypoints']
    def entrypoints(self):
        original_entrypoints(self)
        # Metadata must precede header/digest sealing, never mutate the final
        # deployment manifest after its program header has been authenticated.
        self.builder.notes['request_runtime'] = {
            **self.graph.source['request_specialization'],
            'prompt_ingestion_only': bool(self.graph.source.get('prompt_ingestion_only')),
            'input_token_object_id': self.token_ring_object,
            'graph_id': self.graph.graph_id,
        }
    methods['_declare_entrypoints'] = entrypoints
    emitter = type('_RequestEmitter', (lowering._Emitter,), methods)
    scope['_Emitter'] = emitter
    return emitter


def build_request_deployment(graph, capability, *, phase, prefill_chunk_tokens=None,
                             prompt_ingestion=False, deployment_id=1, generation=1,
                             target_id=None):
    graph = specialize_request(baseline.as_kernel_graph(graph), phase=phase,
                               prefill_chunk_tokens=prefill_chunk_tokens)
    if prompt_ingestion:
        graph = prompt_ingestion_graph(graph)
    plan = build_request_plan(graph, capability)
    context = graph.source['request_specialization']['context_capacity']
    emitter = _emitter_class(context)(graph, capability, plan, deployment_id,
                                     generation, target_id, lowering.BACKEND_ID)
    deployment = emitter.run()
    verification = verify_deployment(deployment, capability)
    legality = check_deployment(graph, deployment, capability)
    if not verification.admitted or not legality['ok']:
        raise ValueError({'verifier': verification.to_dict(), 'checker': legality})
    return graph, plan, deployment
