"""Target-context source selections for the EXISTING canonical S81 compiler.

No constructor/map replay, payload loading, state generation or host arithmetic.
Arch retains compiler extents and execution; this helper consumes his existing
CanonicalS81Execution and emitted entries. Historical 1M files are labelled by
actual provenance, never granted as native carry or a released prompt history.
"""
from pathlib import Path

POSITION = 1048575
CONTEXT = POSITION + 1
REFERENCE = Path('/home/ubuntu/w17work/ref/ctx1048576_seed20260930')
W17 = Path('/home/ubuntu/w17work/die')
REPRESENTATIVE_LAYERS = (1, 2, 20, 39)
HEAD_CHAIN = (37, 38, 39)


def source_nodes(execution, layer):
    """Exact ordered IDs usable by the canonical dispatch/nonfield emitters."""
    if type(layer) is not int or not 0 <= layer < 40:
        raise ValueError('actual source layer0..39 required')
    nodes = sorted((n for n in execution.source.nodes.values()
                    if n.get('scope') == layer and n.get('kind') == 'instruction'),
                   key=lambda n: n['instruction_index'])
    if not nodes or [n['instruction_index'] for n in nodes] != list(range(len(nodes))):
        raise ValueError('missing/nonconsecutive actual layer program')
    if nodes[-1]['instruction']['unit'] != 0 or nodes[-1]['instruction']['wait'] != 31:
        raise ValueError('actual source layer END required')
    return [n['id'] for n in nodes]


def selection(execution, *, rank, layers=HEAD_CHAIN, position=POSITION):
    """Select actual nodes, not fabricated phase/entry0 or pos0 operands.

    Each field request goes through execution.dispatch with the actual native
    expert IDs; nonfield operations use existing emit_nonfield_run. This does
    not modify dynamic selectors: caller captures them at the selected position.
    """
    if position != POSITION or type(rank) is not int or not 0 <= rank < 4:
        raise ValueError('selected DS1M position and actual TP4 rank required')
    layers = tuple(layers)
    if not layers or len(set(layers)) != len(layers):
        raise ValueError('unique actual source layer sequence required')
    groups = []
    for layer in layers:
        nodes = source_nodes(execution, layer)
        field = [n for n in nodes if execution.source.bindings[n].get('address_bound')]
        groups.append(dict(layer=layer, nodes=nodes, field_nodes=field,
                           nonfield_nodes=[n for n in nodes if n not in field]))
    head = [f'Lhead.I{i}' for i in range(7)]
    if any(n not in execution.source.nodes for n in head):
        raise ValueError('actual released head source absent')
    return dict(position=position, context=CONTEXT, requested_rank=rank, layers=groups,
                head_nodes=head, head_consumers=['global_argmax','Lhead.fence'],
                attach_head=layers[-1] == 39,
                head_input_source='actual native L39 H[4,5120]/PF[4] carry; '
                    'then literal Lhead.I0..I4 produce normalized XN',
                short_chain_initial_source=f'actual retained L{layers[0]-1} output '
                    f'at position{position}' if layers[0] else 'actual selected prompt input',
                chain_contains_all40_layers=False,
                whole_token_qualification=False)


def bind_emitted_entries(execution, selection_record, emitted):
    """Attach context to EXISTING emitted entry/phase/key records, unchanged.

    No source-node->allocation-stage arithmetic, entry invention or phase0
    fallback. Requested rank and physical owner rank can differ: keep both.
    """
    if selection_record['position'] != POSITION:
        raise ValueError('target context changed')
    allowed = {n for g in selection_record['layers'] for n in g['field_nodes']}
    records = []
    for entry in emitted['entries']:
        node = entry['node']
        if node not in allowed or node not in execution.source.nodes:
            raise ValueError('emitted program belongs to different source selection')
        source = execution.source.nodes[node]
        if not all(k in entry for k in ('entry','phase','key','stage','rank')):
            raise ValueError('actual native emitted entry missing')
        records.append(dict(entry, source_scope=source['scope'],
                            source_instruction_index=source['instruction_index'],
                            source_template_sha256=source['template_word_sha256'],
                            requested_rank=selection_record['requested_rank'], position=POSITION))
    if not records:
        raise ValueError('no actual emitted entries to bind')
    return records


def existing_assets(rank):
    """Exact historical locators only; no implied initialized data or GO."""
    if type(rank) is not int or not 0 <= rank < 4:
        raise ValueError('actual TP4 rank required')
    die = W17/f'ctx1048576_s20260930_L20_r{rank}'
    state = W17/'ctx1048576_s20260930_L20'/f'r{rank}'
    return dict(position=POSITION, context=CONTEXT, seed=20260930,
                provenance='released checkpoint weights; seeded synthetic KV/history; golden shard I/O',
                native_input_authority=False, real_prompt_1M_history=False,
                L20_die_manifest=str(die/'manifest.json'),
                L20_previous_window=str(die/'hbm_s0.hex'),
                L20_previous_absolute_rows=[1048448,1048574],
                current_row=1048575, current_row_requires_native_producer=True,
                excluded_current_row_oracle=str(die/'hbm_s0_with_current_row.hex'),
                L20_index_keys=str(state/'ikhbm_region.hex'),
                L20_compressed_KV=[str(state/f'ckv_s{k}.hex') for k in range(4)],
                L20_weight_IO_manifest=str(Path('/home/ubuntu/w17work/isa/scratch_s20260930/images')/
                    f'ctx1048576_L20_r{rank}'/'manifest.json'),
                L39_reference_only=str(REFERENCE/'ctx1048576_L39.npz'),
                head_oracle_only=str(REFERENCE/'ctx1048576_head.npz'),
                candidate_reference_only=str(REFERENCE/'ctx1048576_cand.npz'),
                source_record=str(REFERENCE/'golden_ctx1048576_0-39.json'))
