"""Opt-in shared-layout prompt ingestion and generation in one deployment.

The released SAMPLE arithmetic still executes on every forward. Only its
irreversible TOKEN_APPEND publication is disabled for intermediate prompt
requests (MAX_NEW_TOKENS=0). The final prompt and each generated-token forward
use the positive, policy-bounded generation budget. No state/layout migration.
"""
from compiler.backends.hbm_sram import plan as baseline
from compiler.backends.hbm_sram import lower as lowering
from compiler.backends.hbm_sram.request_plan_r2 import build_request_plan
from compiler.backends.hbm_sram.request_deployment import _emitter_class
from compiler.frontends.v3.deepseek_v41_request_r2 import specialize_request
from compiler.backends.hbm_sram.check import check_deployment
from runtime.abi3.verifier import verify_deployment
from runtime.abi3.constants import NO_ID, Major, Selection
from runtime.abi3.descriptors import PredicateKind, Comparison, SelectorKind, Symbol
from runtime.abi3.records import decode_body, split_program


def publication_predicate(builder):
    return builder.predicate(kind=PredicateKind.COMPARE_SYMBOL,
        comparison=Comparison.GT, selector_kind=SelectorKind.RUNTIME_SYMBOL,
        selector_index=int(Symbol.MAX_NEW_TOKENS), immediate=0,
        key='request.prompt_generation.publish')


def validate_publication_dependencies(deployment):
    """A skipped append must not strand any waited completion event."""
    _, body = split_program(deployment.program)
    instructions = decode_body(body)
    appends = [i for i in instructions if i.major == int(Major.SELECTION)
               and i.sub == int(Selection.TOKEN_APPEND)]
    if len(appends) != 1:
        raise ValueError('shared request program requires exactly one append instruction')
    append = appends[0]
    if append.predicate_id == NO_ID:
        raise ValueError('append is missing the explicit request publication gate')
    p = deployment.table[append.predicate_id].payload
    expected = {'predicate_kind': int(PredicateKind.COMPARE_SYMBOL),
        'comparison': int(Comparison.GT),
        'selector_kind': int(SelectorKind.RUNTIME_SYMBOL),
        'selector_index': int(Symbol.MAX_NEW_TOKENS), 'immediate': 0}
    if any(p[k] != v for k, v in expected.items()):
        raise ValueError('append publication predicate is not MAX_NEW_TOKENS>0')
    from runtime.abi3.constants import InstructionFlag
    if not append.flags & int(InstructionFlag.PREDICATED) or append.flags & int(InstructionFlag.PREDICATE_INVERT):
        raise ValueError('append publication predicate is disabled or inverted')
    for instruction in instructions:
        if instruction.wait_set_id != NO_ID:
            wait = deployment.table[instruction.wait_set_id].payload
            for index in range(wait['producer_count']):
                if wait[f'producer_{index}'] == append.signal_event_id:
                    raise ValueError('skipped append would strand a completion dependency')
    return {'append_instructions': 1, 'append_event_has_consumers': False,
            'state_layout_migrations': 0, 'checkpoint_prefix_replays': 0}


def build_shared_request_deployment(graph, capability, *, prefill_chunk_tokens,
                                    deployment_id=1, generation=1, target_id=None):
    graph = specialize_request(baseline.as_kernel_graph(graph), phase='prefill',
                               prefill_chunk_tokens=prefill_chunk_tokens)
    samples = [k for k in graph.kernels if k.attributes.get('source_operation_kind') == 'SAMPLE']
    if [k.kind for k in samples] != ['SCALE', 'ARGMAX', 'TOKEN_APPEND']:
        raise ValueError('requires the released SCALE/ARGMAX/TOKEN_APPEND tail')
    plan = build_request_plan(graph, capability)
    base = _emitter_class(graph.source['request_specialization']['context_capacity'])
    class SharedEmitter(base):
        def _kernel_predicate(self, planned):
            previous = super()._kernel_predicate(planned)
            if self.kernels[planned.index].kind != 'TOKEN_APPEND':
                return previous
            if previous != NO_ID:
                raise ValueError('cannot replace a source append predicate')
            if not hasattr(self, '_publication_gate'):
                self._publication_gate = publication_predicate(self.builder)
            return self._publication_gate

        def _declare_entrypoints(self):
            super()._declare_entrypoints()
            self.builder.notes['shared_prompt_generation'] = {
                'schema': 'ds-v41.shared-request.r1', 'one_deployment': True,
                'prompt_budget': 0, 'publication': 'MAX_NEW_TOKENS>0',
                'intermediate_sample_arithmetic_executes': True,
                'state_layout_migrations': 0, 'prefix_replays': 0,
                'continuation_query_rows': 1,
                'first_generated_token_has_no_fabricated_KV': True,
            }
    deployment = SharedEmitter(graph, capability, plan, deployment_id, generation,
                               target_id, lowering.BACKEND_ID).run()
    dependencies = validate_publication_dependencies(deployment)
    verification = verify_deployment(deployment, capability)
    legality = check_deployment(graph, deployment, capability)
    if not verification.admitted or not legality['ok']:
        raise ValueError({'verifier': verification.to_dict(), 'checker': legality})
    return graph, plan, deployment, dependencies
