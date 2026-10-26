"""Static retirement proof. All ages are in one explicitly proven edge basis.

This pass does not infer fault latency from the fault-tree height. Continuous
health monitors are never assigned a cutoff: only token work has deadlines.
Physical source/path/reset evidence is mandatory for qualification.
"""
import hashlib
import json


def integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f'{name}: nonnegative integer required')
    return value


def prove(contract, tx_first, status_age):
    """Reject incomplete operation/source inventories or an early STATUS slot.

    The manifest enumerates operation nominal_check, missing_check and drain
    ages, their fault sources, and each source's full observation path through
    the sticky collector, UFH, AFR, face, TX capture/landing/link and consumer.
    Path receipt hashes identify measured artifacts; they never make an
    unqualified artifact qualified. Reset release uses the same edge basis.
    """
    tx_first = integer(tx_first, 'tx_first')
    status_age = integer(status_age, 'status_age')
    if status_age < tx_first + 33 or status_age >= 65535:
        raise ValueError('STATUS must follow unchanged RESULT/done and fit compiled_end')
    operations = contract['operations']
    sources = contract['sources']
    if not operations or not sources:
        raise ValueError('empty operation/source inventory')
    source_ids = [s['id'] for s in sources]
    op_ids = [o['id'] for o in operations]
    if len(set(source_ids)) != len(source_ids) or len(set(op_ids)) != len(op_ids):
        raise ValueError('duplicate operation/source')
    if set(source_ids) != set(contract['source_inventory']):
        raise ValueError('source inventory mismatch')
    if set(op_ids) != set(contract['operation_inventory']):
        raise ValueError('operation inventory mismatch')
    cutoff = max(max(integer(o[k], o['id'] + '.' + k)
                     for k in ('nominal_check', 'missing_check', 'drain')) for o in operations)
    required = set()
    for op in operations:
        if not op['fault_sources'] or not set(op['fault_sources']) <= set(source_ids):
            raise ValueError('operation has missing or unknown fault source')
        if op['missing_check'] < op['nominal_check']:
            raise ValueError('missing check precedes nominal functional check')
        required.update(op['fault_sources'])
    if required != set(source_ids):
        raise ValueError('source has no functional operation deadline')
    qualified = (contract.get('edge_basis_qualified') is True and
                 contract.get('inventory_qualified') is True and
                 all(o.get('deadline_qualified') is True for o in operations))
    rows = []
    for source in sources:
        path = source['path']
        # Endpoint identities are explicit; zero edges is legal for a proven
        # combinational face, but no terminal stage may be omitted.
        if [p['role'] for p in path] != [
                'source_to_collector', 'ufh', 'afr', 'face', 'tx_capture',
                'tx_landing', 'link', 'consumer']:
            raise ValueError('incomplete or reordered observation path')
        latency = sum(integer(p['edges'], source['id'] + '.' + p['role']) for p in path)
        for stage in path:
            digest = stage.get('receipt_sha256', '')
            if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('missing path receipt SHA256')
            qualified &= stage.get('qualified') is True
        # STATUS is assembled at status_age and observed downstream after its
        # own suffix. Requiring the entire path before assembly is conservative
        # and explicitly prices every stage instead of silently dropping it.
        ready = cutoff + latency
        if status_age < ready:
            raise ValueError(f"STATUS precedes {source['id']} complete observation: {status_age} < {ready}")
        clear = integer(source['reset_clear_age'], 'reset_clear_age')
        flush = integer(source['reset_propagation_edges'], 'reset_propagation_edges')
        release = integer(source['sink_release_age'], 'sink_release_age')
        if release < clear + flush:
            raise ValueError(f"reset resurrection possible for {source['id']}")
        qualified &= source.get('reset_qualified') is True
        rows.append(dict(source=source['id'], observation_edges=latency,
                         last_functional_observation=ready, margin=status_age-ready))
    return dict(schema='opentallas.kv_retirement.v1', qualified=bool(qualified),
                status='QUALIFIED' if qualified else 'LOGICAL_ONLY',
                cutoff=cutoff, status_age=status_age, compiled_end=status_age+1,
                status_delay=status_age-tx_first-33,
                token_added_edges=36*(status_age-tx_first-33), sources=rows,
                continuous_health='LIVE: never gated, cleared or masked at cutoff',
                manifest_sha256=hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest())
