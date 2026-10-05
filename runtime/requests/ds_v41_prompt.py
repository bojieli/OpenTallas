"""Bounded prompt ingestion through the existing ABI device, no host arithmetic."""
import struct
from runtime.abi3.constants import CompletionStatus, NO_ID
from runtime.abi3.descriptors import Phase, Symbol


def ingest_prompt(device, session, token_ids):
    """One position-zero bounded block, then source-legal one-token steps.

    The SAME device, session and committed KV/Engram/compressor state survive
    every submission. Intermediate steps do not sample, append output tokens,
    clear scratch, reset cursors or recreate state. Source causal decode is
    used for continuations; this does not claim equality to one large prefill's
    floating-point association. The generic prefill path remains available.
    """
    contract = device.deployment.notes.get('request_runtime', {})
    if not contract.get('prompt_ingestion_only'):
        raise ValueError('requires a source-compiled prompt ingestion deployment')
    tokens = tuple(token_ids)
    if not tokens or any(type(t) is not int or not 0 <= t < 2**32 for t in tokens):
        raise ValueError('prompt must contain U32 token IDs')
    if session.finished or session.position != 0 or session.generated:
        raise ValueError('prompt ingestion requires a fresh, unfinished session')
    if len(tokens) > contract['context_capacity']:
        raise ValueError('prompt exceeds persistent context capacity')
    object_id = contract.get('input_token_object_id', NO_ID)
    if object_id == NO_ID:
        raise ValueError('compiled input token object is absent')
    # Bind actual compiled input memory on every node; only external token IDs
    # are written. No activation, expected logits or numerical result is supplied.
    memories, _ = device._session_address_space(session)
    receipts=[]
    position=0
    first=min(contract['query_rows'],len(tokens))
    while position < len(tokens):
        span=first if position == 0 else 1
        phase=Phase.PREFILL if position == 0 else Phase.DECODE
        # The emitted HOST input view reads the current request window at
        # element zero. Absolute POSITION_START applies to committed state,
        # not to this external-token staging window.
        chunk = tokens[position:position+span]
        payload = struct.pack('<' + 'I'*span, *chunk)
        for memory in memories:
            memory[object_id].write(0, payload)
        entries=[i for i,e in device._entrypoints.items() if e['phase'] == int(phase)]
        if len(entries) != 1:
            raise ValueError('compiled phase entrypoint is not unique')
        symbols={int(Symbol.SPAN_TOKENS):span, int(Symbol.POSITION_START):position,
                 int(Symbol.POSITION_END):position+span,
                 int(Symbol.CONTEXT_LENGTH):position+span, int(Symbol.PHASE):int(phase),
                 int(Symbol.BATCH):1, int(Symbol.SPAN_LAST_INDEX):span-1}
        result=device.run_transaction(session,entrypoint_id=entries[0],symbols=symbols)
        receipts.append(result)
        if result.status != CompletionStatus.SUCCESS:
            return tuple(receipts)
        if result.produced_tokens or session.generated or session.finished:
            raise RuntimeError('prompt-only program unexpectedly published generation')
        if session.position != position+span:
            raise RuntimeError('actual transaction did not commit the expected source position')
        position += span
    return tuple(receipts)
