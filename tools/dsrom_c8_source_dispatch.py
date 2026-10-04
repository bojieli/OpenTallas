"""Prepare native C8 dispatch from the owner's already-loaded source objects.

No allocator, map validation replay, checkpoint read or numerical evaluator.
The parent supplies its existing StageProgramJoin and SourceExecution. The
result directories are the actual +DIR / +OT_ROM_DIR / Field loader ABI.
"""
import hashlib
import json
from pathlib import Path


def source_dispatch_parent(parent_binding_class):
    """Extend Arch's actual ParentBinding without modifying its pinned source.

    Arch constructs this successor in place of ParentBinding, with unchanged
    owner/selected/model_pin/interface_pin arguments. Its inherited source
    selection and ownership checks remain active.
    """
    class SourceDispatchParent(parent_binding_class):
        def prepare_source_dispatch(self, source_execution, join, requests, out):
            return prepare(self, source_execution, join, requests, out)
    return SourceDispatchParent


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def prepare(parent, source_execution, join, requests, out):
    """Emit parent programs/CFG and native offers for source nodes and contexts.

    requests: [{node, rank, context:{token,position,user,epoch}, expert_ids?}].
    parent is Arch's ParentBinding; join is the validated S81 StageProgramJoin.
    Keep these objects in the parent's preparation process; do not reload or
    revalidate the allocation for each node. Weight/VM initializer ingestion
    remains owned by SourceExecution and the real context-restoration producer.
    """
    _require(parent.pairs == join.pairs == 2417 and
             parent.stage_map == join.stage_map, 'parent/source S81 allocation mismatch')
    out = Path(out)
    _require(not out.exists(), 'fresh dispatch output required')
    compiled, contexts = [], []
    for request in requests:
        context = dict(request['context'])
        for name, width in [('token', 21), ('position', 21), ('user', 10), ('epoch', 16)]:
            _require(type(context.get(name)) is int and 0 <= context[name] < 1 << width,
                     'actual C8 context bounds: '+name)
        node, rank = request['node'], request['rank']
        resolved = source_execution.resolve(node, rank, expert_ids=request.get('expert_ids'))
        bound = parent.bind_execution(resolved)
        dispatch = join.compile_operation(source_execution, node, rank,
                                          expert_ids=request.get('expert_ids'))
        _require(len(bound['parent_fragments']) == len(dispatch['fragments']),
                 'parent/source fragment count mismatch')
        for owner, fragment in zip(bound['parent_fragments'], dispatch['fragments']):
            parameters = owner['field_parameters']
            _require(parameters['die_id'] == fragment['die_id'] and
                     parameters['RANK'] == fragment['rank'] and
                     parameters['field_pairs'] == join.pairs and
                     parameters['ROM_PHW'] == join.stage_map['PHW_required_by_stage'][fragment['stage']],
                     'parent/source fragment owner mismatch')
        compiled.append(dispatch)
        contexts.extend([context] * len(dispatch['fragments']))
    _require(compiled, 'actual source requests required')
    out.mkdir(parents=True)
    program = join.emit_programs(compiled, out/'programs', program_address_bits=14)
    offers = []
    fields = {}
    for entry, context in zip(program['entries'], contexts):
        stage, rank = entry['stage'], entry['rank']
        field_key = (stage, rank)
        directory = out/f's{stage}_r{rank}'
        if field_key not in fields:
            # Full allocated phase directory: absent phases are never filled in
            # as fabricated zero. All pair initializers retain native addresses.
            join.emit_stage(stage, rank, directory)
            parent.write_field_meta(directory/'field.txt')
            (out/'programs'/directory.name/'prog.hex').rename(directory/'prog.hex')
            fields[field_key] = parent.field_parameters(stage, rank)
        identity = (context['epoch'] << 31) | (context['user'] << 21) | context['position']
        offers.append(dict(entry, **context, identity=identity,
                           die_id=fields[field_key]['die_id'],
                           runtime_directory=str(directory.resolve()),
                           context_restore_required=True))
    # A compiled array consumed by the actual DieBase c8_offer/context methods;
    # it is not a second interpreter or a prelabelled completion trace.
    rows = [f"  {{{x['die_id']}, {x['token']}u, {x['position']}u, {x['user']}u, "
            f"{x['epoch']}u, {x['entry']}u, {x['identity']}ull}}" for x in offers]
    (out/'source_offers.hpp').write_text(
        '#pragma once\n#include "dsrom_c8_source_dispatch.hpp"\n'
        'static constexpr DsromC8SourceOffer dsrom_source_offers[] = {\n'
        + ',\n'.join(rows)+'\n};\n')
    artifacts = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in out.rglob('*') if p.is_file()}
    result = dict(schema='dsrom.S81.C8.owner-source-dispatch.v1', offers=offers,
                  fields=[dict(stage=s, rank=r, **p) for (s,r),p in fields.items()],
                  artifacts=artifacts, source_execution_qualified=False,
                  context_restore_and_remote_drain_required=True,
                  whole_token_qualified=False)
    (out/'parent_dispatch.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    return result
