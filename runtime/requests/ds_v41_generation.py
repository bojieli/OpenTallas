"""Real Device prompt-to-generation handoff without state or logit copying."""
import struct
from dataclasses import dataclass
from runtime.abi3.constants import CompletionStatus
from runtime.abi3.descriptors import Phase, Symbol, ExtendedDescriptorType
from compiler.backends.hbm_sram.request_generation import validate_publication_dependencies


@dataclass(frozen=True)
class GenerationRun:
    receipts: tuple
    prompt_committed: bool
    generated_tokens: tuple[int, ...]
    effective_new_token_budget: int
    context_exhausted: bool


def ingest_and_generate(device, session, token_ids, *, max_new_tokens):
    """Last prompt forward publishes token0; each later forward consumes it.

    The actual Device applies commits, advances positions, selects tokens and
    handles EOS. External prompt/generated IDs are staged; the host computes
    no logits, argmax or state. Failed receipts stop the driver immediately.
    """
    contract = device.deployment.notes.get('shared_prompt_generation', {})
    if contract.get('schema') != 'ds-v41.shared-request.r1':
        raise ValueError('requires a shared prompt/generation deployment')
    validate_publication_dependencies(device.deployment)
    if device.sessions.get(session.session_id) is not session:
        raise ValueError('session is not owned by this Device')
    if session.position or session.generated or session.finished:
        raise ValueError('requires a fresh, unfinished session')
    tokens = tuple(token_ids)
    bounds = device.deployment.notes['request_runtime']
    if not tokens or any(type(t) is not int or not 0 <= t < 2**32 for t in tokens):
        raise ValueError('prompt must contain U32 token IDs')
    if len(tokens) > bounds['context_capacity']:
        raise ValueError('prompt exceeds context capacity')
    entries = {}
    for phase in (Phase.PREFILL, Phase.DECODE):
        matches = [(i,e) for i,e in device._entrypoints.items() if e['phase'] == int(phase)]
        if len(matches) != 1:
            raise ValueError('each request phase must have one entrypoint')
        entries[phase] = matches[0]
    policies = {e['generation_policy_id'] for _,e in entries.values()}
    if len(policies) != 1:
        raise ValueError('phases must share the same generation policy')
    policy_id = next(iter(policies))
    policy = device.deployment.table.get(policy_id, ExtendedDescriptorType.GENERATION_POLICY).payload
    if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= policy['max_new_tokens']:
        raise ValueError('generation budget exceeds policy')
    # The released generate loop clips total token length to context capacity.
    # A selected but unprocessed token still occupies a token position. Do not
    # fabricate one extra AR "bonus" token past that bound or cap the run at an
    # unrelated fixture limit. A full-context prompt publishes no new token.
    effective_budget = min(max_new_tokens, bounds['context_capacity']-len(tokens))
    memories, _ = device._session_address_space(session)
    receipts = []
    def submit(chunk, phase, publication_budget):
        position = session.position
        for memory in memories:
            memory[bounds['input_token_object_id']].write(0, struct.pack('<'+'I'*len(chunk), *chunk))
        result = device.run_transaction(session, entrypoint_id=entries[phase][0],
            generation_policy_id=policy_id, symbols={
                int(Symbol.SPAN_TOKENS): len(chunk), int(Symbol.POSITION_START): position,
                int(Symbol.POSITION_END): position+len(chunk),
                int(Symbol.CONTEXT_LENGTH): position+len(chunk), int(Symbol.PHASE): int(phase),
                int(Symbol.BATCH): 1, int(Symbol.SPAN_LAST_INDEX): len(chunk)-1,
                int(Symbol.MAX_NEW_TOKENS): publication_budget,
                int(Symbol.GENERATION_INDEX): len(session.generated)})
        receipts.append(result)
        if result.status == CompletionStatus.SUCCESS:
            if session.position != position+len(chunk):
                raise RuntimeError('Device did not commit the requested source position')
            if len(result.produced_tokens) != int(publication_budget > 0):
                raise RuntimeError('Device publication disagrees with the request gate')
        return result
    position = 0
    while position < len(tokens):
        span = min(bounds['query_rows'], len(tokens)) if position == 0 else 1
        last = position+span == len(tokens)
        result = submit(tokens[position:position+span], Phase.PREFILL if position == 0 else Phase.DECODE,
                        effective_budget if last else 0)
        if result.status != CompletionStatus.SUCCESS:
            return GenerationRun(tuple(receipts), False, tuple(session.generated), effective_budget, False)
        position += span
    while not session.finished and len(session.generated) < effective_budget:
        result = submit((session.generated[-1],), Phase.DECODE, effective_budget)
        if result.status != CompletionStatus.SUCCESS:
            break
    exhausted = len(tokens)+len(session.generated) == bounds['context_capacity']
    return GenerationRun(tuple(receipts), True, tuple(session.generated), effective_budget, exhausted)
