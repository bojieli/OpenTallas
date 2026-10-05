#!/usr/bin/env python3
"""Emit the real caller factory from existing dispatch and owner TP4 order.

No map reload, operation compilation, input generation or model build. The
enclosing owner supplies its selected offer indices in actual schedule order;
rank-at-a-time dispatch and inferred grouping are deliberately not used.
"""
import argparse
import json
from pathlib import Path


def _selected_groups(dispatch, groups, stage):
    if dispatch['schema'] != 'dsrom.S81.C8.owner-source-dispatch.v1':
        raise ValueError('existing owner source dispatch required')
    if type(stage) is not int or not 0 <= stage < 81 or not groups:
        raise ValueError('actual native stage and nonempty TP4 schedule required')
    if dispatch.get('candidate_only') or dispatch.get('active') is False:
        raise ValueError('inactive candidate cannot enroll executable source caller')
    offers = dispatch['offers']
    selected = []
    for group in groups:
        if len(group) != 4 or any(type(i) is not int or not 0 <= i < len(offers) for i in group):
            raise ValueError('owner TP4 group needs four actual offer indices')
        ranks = {}
        for i in group:
            offer = offers[i]
            rank = offer['die_id'] % 4
            if offer['die_id'] // 4 != stage or rank in ranks:
                raise ValueError('selected offer native stage/rank mismatch')
            if offer['stage'] != stage or offer['rank'] != rank or not offer['node']:
                raise ValueError('source descriptor and physical offer differ')
            ranks[rank] = offer
        first = ranks[0]
        context = ('identity', 'token', 'position', 'user', 'epoch')
        if any(any(r[name] != first[name] for name in context) for r in ranks.values()):
            raise ValueError('TP4 source context mismatch')
        selected.append([ranks[r] for r in range(4)])
    return selected


def fragment_coverage(dispatch, groups, stage, rank, program_root, *, terminal=None):
    """Extract literal native PCs from an existing owner-selected source plan.

    This reads compiled prog.hex only. Complete compiled-fragment coverage is
    distinct from source action/fence visibility and whole-token authority.
    An owner-supplied terminal is checked, never guessed from the last FIELD.
    All four ranks are included because emit() dispatches TP4 groups together.
    """
    import hashlib
    import hdc_isa_v41 as ISA

    def require(ok, why):
        if not ok:
            raise ValueError(why)

    selected = _selected_groups(dispatch, groups, stage)
    require(type(rank) is int and 0 <= rank < 4, 'actual selected rank required')
    indices = [i for group in groups for i in group]
    require(len(set(indices)) == len(indices), 'compiled offer reused in stage order')
    expected = {i for i, o in enumerate(dispatch['offers']) if o['stage'] == stage}
    require(set(indices) == expected,
            'selected groups omit or add compiled stage offers; component is not complete coverage')
    stored = dispatch.get('ownerorderedgroups_by_stage', {}).get(str(stage))
    if stored is not None:
        require(groups == stored, 'compiled owner fragment order changed')
    root = Path(program_root)
    images, pins = {}, {}
    for r in range(4):
        rel = f's{stage}_r{r}/prog.hex'
        raw = (root/rel).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        require(dispatch.get('artifacts', {}).get(rel) == sha,
                'compiled program missing source pin or changed: '+rel)
        text = raw.decode('ascii').splitlines()
        require(text and len(text) <= 1 << 14 and
                all(len(w) == 512 and all(c in '0123456789abcdefABCDEF' for c in w) for w in text),
                'actual FULL_SHAPE entry14 program required')
        images[r] = [int(w, 16) for w in text]
        pins[rel] = sha
    end_word = ISA.encode(full_shape=True, unit=ISA.UNIT_END, wait=31)
    rows = []
    for ordinal, group in enumerate(selected):
        ranks = []
        for r, offer in enumerate(group):
            entry = offer['entry']
            require(type(entry) is int and 0 <= entry < len(images[r]), 'native entry out of image')
            later = [o['entry'] for g in selected for o in [g[r]] if o['entry'] > entry]
            stop = min(later, default=len(images[r]))
            words = images[r][entry:stop]
            require(len(words) >= 2 and words[-1] == end_word and
                    all(not (ISA.decode(w, full_shape=True)['unit'] == ISA.UNIT_END and
                             ISA.decode(w, full_shape=True)['ctl'] == 0) for w in words[:-1]),
                    'fragment needs its actual unique terminal END/wait31, without padding')
            ranks.append(dict(rank=r, die_id=offer['die_id'], source_node=offer['node'],
                              source_nodes=offer.get('source_nodes', [offer['node']]),
                              entry=entry, producer_pc=stop-2, end_pc=stop-1,
                              producer_unit=ISA.decode(words[-2], full_shape=True)['unit'],
                              token=offer['token'], position=offer['position'], user=offer['user'],
                              epoch=offer['epoch'], identity=offer['identity']))
        rows.append(dict(ordinal=ordinal, ranks=ranks))
    designation = None
    if terminal is not None:
        require(set(terminal) == {'ordinal', 'rank', 'source_node', 'entry', 'producer_pc', 'end_pc'},
                'explicit owner terminal fragment/rank/node/entry/producer/END required')
        require(type(terminal['ordinal']) is int and 0 <= terminal['ordinal'] < len(rows) and
                type(terminal['rank']) is int and 0 <= terminal['rank'] < 4,
                'owner terminal outside compiled fragment coverage')
        actual = rows[terminal['ordinal']]['ranks'][terminal['rank']]
        require(all(actual[k] == terminal[k] for k in ('rank','source_node','entry','producer_pc','end_pc')),
                'owner terminal differs from actual compiled producer/END')
        require(terminal['ordinal'] == len(rows)-1, 'terminal designation precedes remaining stage groups')
        designation = dict(terminal)
    return dict(stage=stage, selected_rank=rank, required_ranks=list(range(4)),
                fragment_count_per_rank=len(rows), ordered_fragments=rows,
                node_order=[[o['node'] for o in g] for g in selected],
                program_sha256=pins, complete_compiled_fragment_coverage=True,
                terminal=designation, terminal_designated=designation is not None,
                whole_stage_completion_authority=False,
                remaining_authorities=['source actions/fences and KV/index/remote/allcopy visibility',
                                       'actual fragment acceptance/retirement and C8 quiet/quarantine/fault'],
                producer_pc_semantics='last actual instruction before each fragment END; not catalogue producer ID')


def emit(dispatch, groups, stage, out):
    selected = _selected_groups(dispatch, groups, stage)
    lines = ['#include "s81_source_caller_plan.hpp"',
             '#include "s81_wavefront_stage_poller.hpp"',
             'DsromS81SourcePlan dsrom_s81_bind_source(DsromS81Runtime& runtime) {',
             f'  if(runtime.stage!={stage})throw std::runtime_error("selected source plan stage mismatch");',
             '  DsromS81SourcePlan plan;']
    for group in selected:
        lines += ['  {', '    DsromS81SourceGroup group;']
        for rank, offer in enumerate(group):
            values = [str(offer['die_id'])] + [str(offer[k])+'u' for k in
                      ('token', 'position', 'user', 'epoch', 'entry')] + [str(offer['identity'])+'ull']
            node = json.dumps(offer['node'], ensure_ascii=True)
            lines += [f'    group.ranks[{rank}].offer = {{{", ".join(values)}}};',
                      f'    group.ranks[{rank}].source_node = {node};',
                      f'    dsrom_s81_bind_inputs(runtime,group.ranks[{rank}],{node});',
                      f'    dsrom_s81_bind_receipts(runtime,group.ranks[{rank}],{node});']
        lines += ['    plan.groups.push_back(std::move(group));', '  }']
    lines += ['  return plan;', '}',
              'DsromS81WaveStagePoller::NodeOrder dsrom_s81_bind_source_nodes(DsromS81Runtime& runtime) {',
              f'  if(runtime.stage!={stage})throw std::runtime_error("selected source node order stage mismatch");',
              '  return {']
    # The caller and poller MUST consume the same owner-selected order, not
    # a second traversal of the canonical field map or sorted node IDs.
    for group in selected:
        nodes = ', '.join(json.dumps(o['node'], ensure_ascii=True) for o in group)
        lines.append('    {' + nodes + '},')
    lines += ['  };', '}']
    out = Path(out)
    with out.open('x') as f:
        f.write('\n'.join(lines)+'\n')
    return out


def emit_current_stage_candidate(execution, out, *, stage=37, layer=20,
                                 expert_ids_by_node=None, context=None, calendar_pricer=None):
    """Construct current-assignment source coverage without inventing SU homes.

    Existing CanonicalS81Execution/StageProgramJoin compile physical FIELD
    fragments. Nonfield literals and fences remain ordered explicit unplaced
    operations until their owner supplies actual capacity/visibility hooks.
    """
    import hashlib
    import hdc_isa_v41 as ISA
    if calendar_pricer is None:
        from uarch_model import dsrom_source_fragment_calendar
        calendar_pricer = dsrom_source_fragment_calendar

    if (stage, layer) != (37, 20):
        raise ValueError('bounded current stage37/L20 candidate only')
    if context is not None:
        for name, width in [('token',21),('position',21),('user',10),('epoch',16)]:
            if type(context.get(name)) is not int or not 0 <= context[name] < 1 << width:
                raise ValueError('actual context bounds: '+name)
        if context['position'] != 1048575:
            raise ValueError('target source position must be1048575')
    out = Path(out)
    if out.exists():
        raise ValueError('fresh current compiler candidate output required')
    eids = expert_ids_by_node or {}
    resident_layers = sorted({r['matrix']['layer'] for r in execution.stage_join.by_stage[stage]})
    if layer not in resident_layers:
        raise ValueError('target layer absent from current selected physical stage')
    nodes = execution.target_source_nodes(resident_layers, position=1048575, include_head=False)
    required = {r['node']:r['provider'] for r in execution.target_required_bindings(
        resident_layers, position=1048575, include_head=False)}
    programs, offers, groups, events = {}, [], [], []
    end = ISA.encode(full_shape=True, unit=ISA.UNIT_END, wait=31)
    for ordinal, node in enumerate(nodes):
        n = execution.source.nodes[node]
        binding = execution.source.bindings[node]
        event = dict(ordinal=ordinal, node=node, kind=n['kind'], required_provider=required[node],
                     depends_on=[] if ordinal == 0 else [ordinal-1],
                     catalogue_producer_id=9+list(execution.source.nodes).index(node),
                     native_groups=[], required_ranks=[0,1,2,3], missing=[])
        if binding.get('address_bound'):
            if binding.get('selector_slot') is not None and node not in eids:
                event['missing'].append('actual selected expert IDs before native dispatch')
            else:
                try:
                    dispatched = [execution.dispatch(node,r,expert_ids=eids.get(node)) for r in range(4)]
                except ValueError as exc:
                    event['missing'].append('existing native compiler refusal: '+str(exc))
                else:
                    count = len(dispatched[0]['fragments'])
                    if not count or any(len(d['fragments']) != count for d in dispatched):
                        raise ValueError('actual TP4 fragment count mismatch')
                    for fragment in range(count):
                        group = []
                        for rank, dispatch in enumerate(dispatched):
                            f = dispatch['fragments'][fragment]
                            if f['rank'] != rank or f['die_id'] != 4*f['stage']+rank:
                                raise ValueError('canonical native owner mismatch')
                            image = programs.setdefault((f['stage'],rank), [])
                            entry = len(image)
                            if entry+2 > 1<<14:
                                raise ValueError('actual entry14 capacity exceeded')
                            image.extend((f['word'],end))
                            group.append(len(offers))
                            offer = dict(node=node, source_ordinal=ordinal, stage=f['stage'],rank=rank,
                                die_id=f['die_id'],entry=entry,producer_pc=entry,end_pc=entry+1,
                                fragment_ordinal=fragment, phase=f['phase'],key=f['key'],
                                gather_local_rows=f['gather_local_rows'],ordered_K=f['ordered_K'],
                                source_matrix_sha256=f['source_matrix_sha256'],
                                predicate=dispatch['predicate'],expert_ids=eids.get(node),
                                result_multicast_required=f['result_multicast_required'],
                                context_bound=context is not None)
                            if context is not None:
                                offer.update(context,identity=(context['epoch']<<31)|(context['user']<<21)|context['position'])
                            offers.append(offer)
                        event['native_groups'].append(len(groups));groups.append(group)
            event['missing'] += ['actual SourceIo input lease/restore and output gather/multicast visibility',
                                 'actual C8 fragment acceptance/retirement and all-copy drain']
        elif n['kind'] == 'instruction':
            literal = ISA.encode(full_shape=True,**{k:tuple(v) if isinstance(v,list) and not k.startswith('_') else v
                                                       for k,v in n['instruction'].items()})
            sha = hashlib.sha256(literal.to_bytes(256,'little')).hexdigest()
            if sha != n['template_word_sha256']:
                raise ValueError('literal source template changed')
            event.update(unit=n['instruction']['unit'],template_word_sha256=sha,
                         source_instruction=f'{literal:0512x}',physical_home=None,
                         entry=None,producer_pc=None,end_pc=None,
                         reads=n['instruction'].get('_reads',[]),writes=n['instruction'].get('_writes',[]))
            event['missing'] += ['selected native physical service home/capacity and program entry allocation',
                                 'native operand/publication leases and matched visibility/retirement']
            if n['instruction']['unit'] == ISA.UNIT_END and n['instruction'].get('ctl', 0) == 0:
                event['end_designation']='layer fragment END; not token/HEAD/global argmax terminal'
        else:
            event['source_action']=n
            event['missing'].append('actual source-owned fence/service visibility producer')
        events.append(event)
    out.mkdir(parents=True)
    artifacts = {}
    for (home,rank),words in programs.items():
        path=out/f's{home}_r{rank}'/'prog.hex';path.parent.mkdir()
        raw=''.join(f'{w:0512x}\n' for w in words).encode();path.write_bytes(raw)
        artifacts[str(path.relative_to(out))]=hashlib.sha256(raw).hexdigest()
    selected = [g for g in groups if offers[g[0]]['stage']==stage]
    result = dict(schema='dsrom.S81.C8.owner-source-dispatch.v1',candidate_only=True,active=False,
        adopted=False,hardware_admission=False,parent_dispatch_ready=False,selected_stage=stage,
        selected_rank=0,target_layer=layer,resident_source_layers=resident_layers,position=1048575,context=context,
        offers=offers,ownerorderedgroups=groups,ownerorderedgroups_by_stage={str(stage):selected},
        node_order_by_stage={str(stage):[[offers[i]['node'] for i in g] for g in selected]},
        source_order=events,complete_selected_source_order=list(nodes),
        complete_source_operation_coverage=True,complete_physical_stage_plan=False,
        selected_stage_compiled_fragment_count_per_rank=len(selected),
        required_ranks=[0,1,2,3],native_END_is_whole_stage_or_head_completion=False,
        terminal=None,missing_terminal='intermediate layer handoff requires all source coverage/fences bound; token HEAD terminal outside scope',
        source_input_sha256=execution.input_sha256,artifacts=artifacts,
        calendar=calendar_pricer(events))
    (out/'parent_dispatch.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'ownerorderedgroups.json').write_text(json.dumps(selected,indent=2)+'\n')
    (out/'node_order.json').write_text(json.dumps(result['node_order_by_stage'],indent=2)+'\n')
    return result


def emit_current_service_candidates(candidate, out, *, service_homes, program_root, program_pricer=None):
    """Link literal nonfield runs at explicit current service candidate homes.

    No placement selection or acceptance is performed. Original canonical field
    offers remain unchanged. Actions/fences require their real visibility hooks.
    """
    import copy
    import hashlib
    import hdc_isa_v41 as ISA
    if candidate.get('candidate_only') is not True or candidate.get('active') is not False:
        raise ValueError('current inactive compiler candidate required')
    if service_homes != {19:38,20:40}:
        raise ValueError('bounded owner-requested current L19/L20 service38/40 candidate only')
    out=Path(out)
    if out.exists():
        raise ValueError('fresh service candidate output required')
    rows=[];runs=[];current=None
    programs={};prefixes={};prefix_hashes={}
    for home in service_homes.values():
        lengths=[]
        for rank in range(4):
            rel=f's{home}_r{rank}/prog.hex'
            if rel in candidate['artifacts']:
                raw=(Path(program_root)/rel).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=candidate['artifacts'][rel]:
                    raise ValueError('canonical field program prefix changed')
                prefix=[int(w,16) for w in raw.decode().splitlines()]
                prefix_hashes[rel]=hashlib.sha256(raw).hexdigest()
            else:prefix=[]
            prefixes[home,rank]=prefix;lengths.append(len(prefix))
        if len(set(lengths))!=1:
            raise ValueError('actual TP4 program prefix capacity differs')
        programs[home]=list(prefixes[home,0])
    known_exports={
        'su':('tools/runtime/dsrom/s81_minimum_su256_ports.hpp','dsrom_s81_bind_minimum_su256'),
        'he':('tools/runtime/dsrom/s81_minimum_he_l20.hpp','dsrom_s81_bind_minimum_he_l20'),
        'xu':('tools/runtime/dsrom/s81_minimum_xu.hpp','dsrom_s81_bind_minimum_xu'),
        'collective':('tools/runtime/dsrom/s81_minimum_tp4_gather.hpp','dsrom_s81_bind_native_tp4_gather; retained L0-only shapes require actual L19/L20 adaptation'),
    }
    end=ISA.encode(full_shape=True,unit=ISA.UNIT_END,wait=31)
    def close_run():
        nonlocal current
        if current is None:return
        # A real source END already terminates the last run. Do not fabricate
        # another operation/edge after it. Other runs retain existing END31 ABI.
        words=programs[current['stage']]
        if words[-1] != end:words.append(end)
        current['end_pc']=len(words)-1
        current['producer_pc']=current['end_pc']-1
        runs.append(current);current=None
    for event in candidate['source_order']:
        if event['native_groups']:
            close_run();continue
        e=copy.deepcopy(event)
        provider=e['required_provider'];literal=e.get('source_instruction')
        scope=int(e['node'].split('.')[0][1:])
        if literal is None:
            close_run();decoded={}
        else:
            decoded=ISA.decode(int(literal,16),full_shape=True)
        e['unit']=decoded.get('unit')
        prefix={0:'ctl',1:'me_',3:'qe_',4:'xu_',5:'he_',6:'coll_'}.get(e['unit'])
        e['operand_control_fields']={k:v for k,v in decoded.items() if
            (prefix is not None and k.startswith(prefix)) or
            (e['unit']==2 and (k.startswith('su_') or k.endswith(('_base','_si','_so','_d','_do','_di')))) or
            k in ('unit','wait','pred')}
        e['zero_base_addresses_retained']=True
        e['operand_fields_are_encoded_native_values']=True
        # Physical clock selection remains an owner's actual loaded binding.
        # SU target is explicitly selected in the existing floorplan, not new.
        e['clock_domain']=('serial_0p9 target; physical binding pending' if provider=='su' else
                           'source-owned domain pending; one shared native runtime clock is not a physical domain')
        e['clock_source']=('tools/dsrom_s81_fulldie.py su_s/su_n dom=serial_0p9' if provider=='su' else
                           'tools/dsrom_s81_unified_components.py clock_load selected_VM_GHz=None')
        e['existing_provider_export']=known_exports.get(provider)
        e['provider_scope_qualified']=False
        e['existing_provider_limitation']={
            'su':'SUN256: actual instruction/dynamic operands, layer CROM and span/ACK enrollment required',
            'he':'retained HE adapter is L20.I1/I78 only; L19 needs its own released tensor enrollment',
            'xu':'retained minimum XU wrapper accepts Sinkhorn only; SEL needs actual selected index/router provider',
            'collective':'retained TP4 gather factory is L0 I9/I10 only; current collectives need exact op/count/order enrollment',
            'matrix':'actual selected WINDOW/CKV/QK/PV native provider and retained context required',
        }.get(provider,'actual current source-owned provider and accepted visibility required')
        e['service_home_candidate']=service_homes.get(scope)
        e['physical_home_adopted']=False
        if scope in service_homes and literal is not None:
            words=programs[service_homes[scope]]
            if current is None:
                current=dict(ordinal=len(runs),stage=service_homes[scope],required_ranks=[0,1,2,3],
                             entry=len(words),source_nodes=[],source_pc=[])
            pc=len(words);words.append(int(literal,16))
            current['source_nodes'].append(e['node'])
            current['source_pc'].append(dict(source_node=e['node'],pc=pc,
                                            catalogue_producer_id=e['catalogue_producer_id']))
            e['candidate_native_pc']=pc
            if decoded['unit']==ISA.UNIT_END and decoded['ctl']==0:close_run()
        else:
            close_run();e['candidate_native_pc']=None
        rows.append(e)
    close_run()
    if any(len(w)>1<<14 for w in programs.values()):
        raise ValueError('actual service candidate entry14 capacity exceeded')
    out.mkdir(parents=True)
    files={}
    for home,words in programs.items():
        base=len(prefixes[home,0]);tail=words[base:]
        for rank in range(4):
            path=out/f's{home}_r{rank}'/'prog.hex';path.parent.mkdir()
            raw=''.join(f'{w:0512x}\n' for w in prefixes[home,rank]+tail).encode()
            path.write_bytes(raw);files[str(path.relative_to(out))]=hashlib.sha256(raw).hexdigest()
    handoffs=[]
    for layer,home in service_homes.items():
        last=next(r for r in reversed(runs) if r['stage']==home)
        handoffs.append(dict(source_node=last['source_nodes'][-1],fence_node=f'L{layer}.fence',
            candidate_home=home,terminal_entry=last['entry'],producer_pc=last['producer_pc'],
            end_pc=last['end_pc'],designation='intermediate stage/layer handoff, not token terminal',
            actual_hooks_bound=False))
    result=dict(service_home_candidates=service_homes,candidate_only=True,active=False,
        adopted=False,source_field_mapping_unchanged=True,required_ranks=[0,1,2,3],
        null_binding_operations=rows,ordered_nonfield_runs=runs,
        compiled_program_words_per_rank={h:len(w) for h,w in programs.items()},program_address_bits=14,
        unchanged_field_prefix_sha256=prefix_hashes,
        files_sha256=files,context=candidate['context'],physical_capacity_qualified=False,
        calendar=candidate['calendar'],calendar_prices_complete=False,
        stage_handoff_candidates=handoffs,
        missing=['actual stage40 service slot/ports/clock capacity and native operand/publication enrollment',
                 'actual source action/fence visibility, C8 retirement and 37/38<->40 copy/exclusion/reverse binding',
                 'actual composed service/transport/ACK/drain calendar prices'])
    # SAME source compiler namespace: construct the complete ordered offers,
    # not a second field-only traversal. Source events remain native fences.
    offers=copy.deepcopy(candidate['offers']);groups=[];events=[]
    starts={run['source_nodes'][0]:run for run in runs};members={}
    for run in runs:
        for node in run['source_nodes']:members[node]=run['source_nodes'][0]
    run_groups={}
    for original in candidate['source_order']:
        event=copy.deepcopy(original);event['native_groups']=[]
        for old in original['native_groups']:
            event['native_groups'].append(len(groups))
            groups.append(list(candidate['ownerorderedgroups'][old]))
        if event['node'] in starts:
            run=starts[event['node']];indices=[];index=len(groups)
            for rank in range(4):
                indices.append(len(offers))
                offers.append(dict(node=run['source_nodes'][0],source_nodes=run['source_nodes'],
                    source_pc=run['source_pc'],stage=run['stage'],rank=rank,
                    die_id=4*run['stage']+rank,entry=run['entry'],
                    producer_pc=run['producer_pc'],end_pc=run['end_pc'],
                    context_bound=False,provider='native-source-run',physical_home_adopted=False))
            groups.append(indices);run_groups[event['node']]=index
        if event['node'] in members:
            event['native_groups']=[run_groups[members[event['node']]]]
        events.append(event)
    by_stage={}
    for group in groups:
        by_stage.setdefault(str(offers[group[0]]['stage']),[]).append(group)
    # Existing field images at other homes retain their bytes and keys.
    for rel,sha in candidate['artifacts'].items():
        if rel in files:continue
        raw=(Path(program_root)/rel).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('field image changed')
        path=out/rel;path.parent.mkdir(exist_ok=True);path.write_bytes(raw);files[rel]=sha
    word_counts={}
    for rel in files:
        home=rel.split('_r')[0][1:]
        if home not in word_counts:word_counts[home]=len((out/rel).read_text().splitlines())
    inventory=None if program_pricer is None else program_pricer(word_counts)
    result['program_inventory_model']=inventory
    result['generated_fragment_END_words']=len(groups)-2 # two literal layer ENDs retained
    joined=dict(schema=candidate['schema'],candidate_only=True,active=False,adopted=False,
        parent_dispatch_ready=False,hardware_admission=False,context=candidate['context'],
        source_input_sha256=candidate['source_input_sha256'],source_order=events,
        complete_selected_source_order=candidate['complete_selected_source_order'],
        offers=offers,ownerorderedgroups=groups,ownerorderedgroups_by_stage=by_stage,
        node_order_by_stage={home:[[offers[i]['node'] for i in g] for g in gs] for home,gs in by_stage.items()},
        artifacts=files,complete_source_operation_coverage=True,complete_physical_stage_plan=False,
        native_END_is_whole_stage_or_head_completion=False,stage_handoff_candidates=handoffs,
        calendar=candidate['calendar'],service_home_candidates=service_homes,
        uncompiled_source_events=[e['node'] for e in events if not e['native_groups']],
        program_inventory_model=inventory,generated_fragment_END_words=len(groups)-2)
    (out/'parent_dispatch.json').write_text(json.dumps(joined,indent=2)+'\n')
    (out/'ownerorderedgroups.json').write_text(json.dumps(groups,indent=2)+'\n')
    (out/'node_order.json').write_text(json.dumps(joined['node_order_by_stage'],indent=2)+'\n')
    (out/'service_bindings.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def emit_current_source_continuation(candidate, out, *, program_root, source_input,
                                     calendar_pricer, program_pricer, restore_pricer):
    """Compile the four literal L19/L20 actions in the current service plan.

    The restore uses the existing SU BYP instruction and publication namespace.
    This does not create the external L14 accepted offer, grant a publication,
    or satisfy either native visibility fence. The actual owner must bind those
    prerequisites before enrolling this inactive compiler candidate.
    """
    import copy
    import gzip
    import hashlib
    import hdc_isa_v41 as ISA
    if (candidate.get('candidate_only') is not True or candidate.get('active') is not False
            or candidate.get('service_home_candidates') != {'19':38,'20':40}):
        raise ValueError('current inactive service38/40 source plan required')
    out=Path(out);root=Path(program_root);source_input=Path(source_input)
    if out.exists():raise ValueError('fresh source continuation output required')
    source_sha=candidate['source_input_sha256'].get(str(source_input))
    if source_sha is None:
        source_sha=candidate['source_input_sha256'].get(str(source_input.relative_to(Path(__file__).resolve().parents[1])))
    if hashlib.sha256(source_input.read_bytes()).hexdigest()!=source_sha:
        raise ValueError('canonical source input differs from compiled plan')
    with gzip.open(source_input,'rt') as f:source=json.load(f)
    nodes={n['id']:n for n in source['nodes']}
    source_index={n['id']:9+i for i,n in enumerate(source['nodes'])}
    expected=['L19.A0','L19.fence','L20.A0','L20.fence']
    if candidate['uncompiled_source_events']!=expected:
        raise ValueError('exact four current source events required')
    joined=copy.deepcopy(candidate);events=joined['source_order'];offers=joined['offers']
    groups=[];action_events={e['node']:e for e in events if e['node'] in expected}
    for name,e in action_events.items():
        if e['source_action']!=nodes[name] or e['catalogue_producer_id']!=source_index[name]:
            raise ValueError('source action/catalogue namespace changed')
    for layer,required,origin in ((19,True,14),(20,False,20)):
        if nodes[f'L{layer}.A0']['action'] != dict(before_instruction=7,candidate_source=None,
                hardware_binding=None,kind='restore_position_selection',region='SELG',
                required=required,source=origin):
            raise ValueError('selected restore semantics changed')
    producer=nodes['L14.I63'];inst=producer['instruction']
    if (inst['unit'],inst['coll_op'],inst['coll_dst'],inst['coll_k'],inst['coll_n'])!=(6,2,447360,512,512):
        raise ValueError('actual L14 TOPK SELG producer changed')
    if producer['template_word_sha256']!='d0ca14372349ed80e998c5140108eaf4796bb1ed121c3b5529e9729abd4e6c79':
        raise ValueError('released source14 template changed')
    instruction=dict(unit=ISA.UNIT_SU,wait=31,su_vec=ISA.VEC_I,su_nout=1,
                     su_nin=512,dst=ISA.DST_VM,o_base=447360,o_si=1)
    # Real SU prefetches all operands; all four read the retained source span.
    for operand in 'abcd':
        instruction.update({operand+'_src':ISA.SRC_VM,operand+'_base':447360,operand+'_si':1})
    word=ISA.encode(full_shape=True,**instruction)
    end=ISA.encode(full_shape=True,unit=ISA.UNIT_END,wait=31)
    writer=source_index['L19.A0'];files={};prefixes={};entry=None
    for rel,sha in candidate['artifacts'].items():
        raw=(root/rel).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('current program image changed')
        if rel.startswith('s38_r'):
            words=raw.decode().splitlines()
            if entry is None:entry=len(words)
            if entry!=len(words):raise ValueError('TP4 copy entry differs')
            prefixes[rel]=sha
            raw+=f'{word:0512x}\n{end:0512x}\n'.encode()
        files[rel]=raw
    if entry!=113 or writer!=2360 or source_index['L14.I63']!=1792:
        raise ValueError('current source/native/catalogue association changed')
    if entry+2>1<<14 or writer>=1<<14 or 447360+512>1<<19:
        raise ValueError('native program/publication/VM capacity exceeded')
    restore=dict(source_node='L14.I63',source_catalogue_producer=source_index['L14.I63'],
        source_template_sha256=producer['template_word_sha256'],source_home=28,
        destination_home=38,source_dies=[112,113,114,115],destination_dies=[152,153,154,155],
        source_address=447360,destination_address=447360,words=512,scalar_format='raw unsigned ID32',
        bytes_per_rank=2048,source_native_entry=None,source_native_pc=None,
        source_native_writer=None,source_accepted_offer=None,
        destination_entry=entry,destination_producer_pc=entry,destination_end_pc=entry+1,
        destination_catalogue_writer=writer,word_hex=f'{word:0512x}',
        word_sha256=hashlib.sha256(word.to_bytes(256,'little')).hexdigest(),
        provider_header='tools/runtime/dsrom/s81_source_selection_restore.hpp',
        native_factory='dsrom_s81_bind_minimum_su256',
        required_owner_binding='Arch retained source14 accepted Offer/native writer/lease; Epic native restore provider',
        source_and_destination_numeric_addresses_are_not_aliases=True,
        actual_hooks_bound=False)
    old_to_new={}
    for e in events:
        old=list(e['native_groups']);e['native_groups']=[]
        # Preserve each group once; a nonfield run can cover several nodes.
        for g in old:
            if g not in old_to_new:
                old_to_new[g]=len(groups);groups.append(candidate['ownerorderedgroups'][g])
            e['native_groups'].append(old_to_new[g])
        if e['node']=='L19.A0':
            indices=[]
            for rank in range(4):
                indices.append(len(offers))
                offers.append(dict(node=e['node'],source_nodes=[e['node']],stage=38,rank=rank,
                    die_id=152+rank,entry=entry,producer_pc=entry,end_pc=entry+1,
                    source_pc=[dict(source_node=e['node'],pc=entry,catalogue_producer_id=writer)],
                    provider='native-source-selection-restore',context_bound=False,
                    physical_home_adopted=False))
            e['native_groups']=[len(groups)];groups.append(indices)
            e.update(source_continuation='native_SU_BYP',restore=restore,
                     runtime_binding_required=True,missing=[restore['required_owner_binding']])
        elif e['node']=='L20.A0':
            e.update(source_continuation='inactive_optional_restore',runtime_binding_required=False,
                     native_reads=0,native_writes=0,native_ACKs=0,missing=[])
        elif e['node'].endswith('.fence'):
            terminal=next(t for t in joined['stage_handoff_candidates'] if t['fence_node']==e['node'])
            if e['depends_on']!=[e['ordinal']-1] or events[e['ordinal']-1]['node']!=terminal['source_node']:
                raise ValueError('fence must follow the actual source layer END')
            terminal.update(request_kind=1,request_kind_name='STAGE_HANDOFF',token_result_valid=False)
            e.update(source_continuation='native_typed_STAGE_HANDOFF',terminal=terminal,
                     runtime_binding_required=True,
                     missing=['Arch actual accepted terminal context, whole ordered coverage and native visibility/drain pins'])
    if len(old_to_new)!=len(candidate['ownerorderedgroups']):
        raise ValueError('current compiled group omitted from continuation')
    by_stage={}
    for group in groups:by_stage.setdefault(str(offers[group[0]]['stage']),[]).append(group)
    joined.update(ownerorderedgroups=groups,ownerorderedgroups_by_stage=by_stage,
        node_order_by_stage={h:[[offers[i]['node'] for i in g] for g in gs] for h,gs in by_stage.items()},
        uncompiled_source_events=[],unbound_runtime_source_events=['L19.A0','L19.fence','L20.fence'],
        complete_source_continuation=True,complete_physical_stage_plan=False,
        generated_fragment_END_words=candidate['generated_fragment_END_words']+1,
        source_selection_restore=restore,unchanged_program_prefix_sha256=prefixes)
    # Prices remain unknown until the real owner provides measurements. No
    # zero-cost restore, fence, transport, or drain is implied by source closure.
    prices=restore_pricer()
    joined['source_continuation_model']=prices
    if calendar_pricer is not None:joined['calendar']=calendar_pricer(events)
    if program_pricer is not None:
        counts={rel.split('_r')[0][1:]:len(raw.decode().splitlines()) for rel,raw in files.items()}
        joined['program_inventory_model']=program_pricer(counts)
    out.mkdir(parents=True)
    for rel,raw in files.items():
        path=out/rel;path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
    joined['artifacts']={rel:hashlib.sha256(raw).hexdigest() for rel,raw in files.items()}
    for name,obj in [('parent_dispatch.json',joined),('ownerorderedgroups.json',groups),
                     ('node_order.json',joined['node_order_by_stage']),
                     ('source_actions.json',dict(events=[e for e in events if e['node'] in expected],
                         source_selection_restore=restore,model=prices))]:
        (out/name).write_text(json.dumps(obj,indent=2)+'\n')
    _emit_source_continuation_header(out/'source_actions.hpp',restore,joined['stage_handoff_candidates'])
    return joined


def _emit_source_continuation_header(path, restore, terminals):
    """Existing native operation/terminal types, no new callback/receipt ABI."""
    word=int(restore['word_hex'],16)
    literal=','.join(f'0x{(word>>(32*j))&0xffffffff:08x}u' for j in range(64))
    lines=['#pragma once','#include "s81_prefix_publication.hpp"',
           '#include "s81_source_selection_restore.hpp"',
           '#include "s81_wavefront_native_result_read.hpp"',
           '#include "s81_typed_completion_request_bind.hpp"',
           'namespace dsrom_s81_emitted_source_actions {',
           'constexpr unsigned source14_catalogue_producer=1792;',
           'constexpr unsigned source_home=28, destination_home=38;',
           'constexpr unsigned selection_address=447360, selection_words=512;',
           'constexpr unsigned copy_entry=113, copy_end_pc=114, copy_writer=2360;',
           'constexpr unsigned handoff_request_kind=1;',
           'constexpr bool l20_restore_required=false;',
           'inline DsromS81PrefixOperation l19_restore_operation() {',
           f' return {{copy_writer,2u,"{restore["word_sha256"]}",{{{literal}}}}};','}',
           '// Enrollment is NOT admission or begin; the real provider owns both.',
           'inline void enroll_l19_restore(dsrom_s81_minimum::PrefixPublication& p) {',
           ' p.enroll_literal(copy_writer,{{selection_address,selection_words}});','}',
           '// Bind the ACTUAL owner tuple. Missing source14 is rejected by Epic.',
           'inline std::unique_ptr<dsrom_s81_minimum::SourceSelectionRestore> bind_restore(',
           ' unsigned layer,DsromS81MinimumRuntime& runtime,const DsromC8SourceOffer& destination,',
           ' std::optional<dsrom_s81_minimum::SelectionRestoreSource> retained_source,',
           ' std::optional<DsromS81SourceIoTransferHooks::Binding> native_copy,',
           ' const DsromS81MinimumSourceTags& tags,',
           ' DsromS81SourceIoTransferHooks::Fence positive_context,',
           ' DsromS81SourceIoTransferHooks::Fence input_visible,',
           ' DsromS81SourceIoTransferHooks::Fence remote_drained,',
           ' DsromS81SourceIoTransferHooks::Fence all_copies_drained,bool opt_in=false) {',
           ' if(layer!=19u && layer!=20u)',
           '  throw std::runtime_error("only literal L19/L20 source restore actions are compiled");',
           ' if(layer==19u && (destination.entry!=copy_entry || !native_copy ||',
           '     !native_copy->enrolled_writer || *native_copy->enrolled_writer!=copy_writer))',
           '  throw std::runtime_error("L19 source action requires actual emitted entry113/writer2360");',
           ' const dsrom_s81_minimum::SelectionRestoreAction action{layer,layer==19u?14u:20u,7u,layer==19u};',
           ' return std::make_unique<dsrom_s81_minimum::SourceSelectionRestore>(',
           '  runtime,action,destination,std::move(retained_source),std::move(native_copy),tags,',
           '  std::move(positive_context),std::move(input_visible),std::move(remote_drained),',
           '  std::move(all_copies_drained),opt_in);','}',
           '// Only attach a literal terminal to an ALREADY retained real offer.',
           '// Planck drives saved typed request; Arch supplies coverage/visibility.',
           'inline DsromS81NativeResultTerminal handoff_terminal(unsigned layer,',
           ' const DsromC8SourceOffer& actual_retained_offer) {',
           ' DsromC8SourceDispatch checked(actual_retained_offer);']
    for t in terminals:
        layer=int(t['source_node'].split('.')[0][1:]);home=t['candidate_home']
        lines.extend([f' if(layer=={layer}u) {{',
            f'  if(actual_retained_offer.die_id<{4*home} || actual_retained_offer.die_id>{4*home+3} || actual_retained_offer.entry!={t["terminal_entry"]})',
            '   throw std::runtime_error("source fence does not match retained native terminal offer");',
            f'  return {{actual_retained_offer,"{t["source_node"]}",{t["producer_pc"]}u,{t["end_pc"]}u}};',
            ' }'])
    lines+=[' throw std::runtime_error("only actual L19/L20 source handoff fences are compiled");','}',
            'template<class Top> void drive_source_fence_request(Top& top,unsigned layer,',
            ' const DsromS81WaveRequest& saved_request,',
            ' const DsromC8SourceOffer& saved_accepted_context,',
            ' const DsromC8SourceOffer& actual_retained_terminal_offer,',
            ' int actual_terminal_die_id,bool request_retained) {',
            ' // Rejection cannot leave a stale valid request; accepted RTL debt is untouched.',
            ' top.wf_join_request_v=0; top.wf_join_request_binding_valid=0;',
            ' const auto terminal=handoff_terminal(layer,actual_retained_terminal_offer);',
            ' dsrom_s81_drive_saved_typed_completion_request(top,saved_request,',
            '  saved_accepted_context,terminal,DsromS81CompletionKind::STAGE_HANDOFF,',
            '  actual_terminal_die_id,request_retained);','}',
            '// No restore callback for L20.A0: explicit required=false source action.',
            '// Neither this header nor END grants visibility, completion or an ACK.','}']
    path.write_text('\n'.join(lines)+'\n')


def emit_candidate_dispatch(execution, candidate, context, out, *,
                            layers=None, expert_ids_by_node=None, include_fields=True, endpoint_map=None, fragment_endpoints=None):
    """Pack native candidate programs using the caller's existing source objects.

    This implements compiler mechanics for c3fff's rejected placement, never
    selects that placement for execution. Live EIDs are supplied by node;
    unresolved expert choices remain source events, not guessed instructions.
    """
    import hashlib
    import tempfile
    import hdc_isa_v41 as ISA

    def require(ok, why):
        if not ok:
            raise ValueError(why)

    require(candidate.get('adopted') is False and
            candidate.get('parent_dispatch_ready') is False and
            candidate.get('hardware_admission') is False,
            'explicit inactive service candidate required')
    context = dict(context)
    for name, width in [('token', 21), ('position', 21), ('user', 10), ('epoch', 16)]:
        require(type(context.get(name)) is int and 0 <= context[name] < 1 << width,
                'actual source context bounds: ' + name)
    require(context['position'] == 1048575, 'selected DS1M source position required')
    identity = (context['epoch'] << 31) | (context['user'] << 21) | context['position']
    source = execution.source
    available = sorted({n['scope'] for n in source.nodes.values() if type(n['scope']) is int})
    selected_layers = available if layers is None else list(layers)
    require(selected_layers and selected_layers == sorted(set(selected_layers)) and
            all(type(l) is int and l in available for l in selected_layers),
            'ordered actual source layers required')
    eids = {} if expert_ids_by_node is None else dict(expert_ids_by_node)
    assignments = {a['node']: a for a in candidate['assignments']}
    require(len(assignments) == len(candidate['assignments']), 'duplicate candidate node assignment')
    movements = {m['node']: m for m in candidate['field_movements']}
    require(len(movements) == len(candidate['field_movements']), 'duplicate field movement')
    runs = {}
    covered = set()
    for run in candidate['ordered_nonfield_runs']:
        require(run['nodes'] and not any(n in covered for n in run['nodes']),
                'candidate nonfield run overlap/empty')
        for node in run['nodes']:
            n = source.nodes[node]
            a = assignments[node]
            require(n['kind'] == 'instruction' and n['scope'] == run['layer'] and
                    a['stage'] == run['stage'] and
                    a['rank_dies'] == [4*run['stage']+r for r in range(4)],
                    'candidate run/source assignment differs')
        runs[run['nodes'][0]] = run
        covered.update(run['nodes'])
    service_endpoints, field_endpoints = {}, {}
    if endpoint_map is not None:
        adjacent = endpoint_map.get('schema') == 'opentallas.S81.level2_service_stream.v1'
        if adjacent:
            require(endpoint_map.get('original_field_mapping_unchanged') is True,
                    'adjacent hub requires original field ownership')
        for home in endpoint_map['homes']:
            layer = home['layer'] if adjacent else home['layer_provider']
            endpoint = home['hub_endpoint'] if adjacent else home['service_home']
            dies = home['rank_die_ids'] if adjacent else home['rank_service_die_ids']
            require(type(layer) is int and 0 <= layer < 40 and
                    type(endpoint) is int and 0 <= endpoint and
                    dies == [4*endpoint+r for r in range(4)],
                    'explicit rank service die mapping differs')
            require(layer not in service_endpoints, 'duplicate service source layer')
            service_endpoints[layer] = (endpoint, dies)
            if adjacent:
                require(home['adjacent_field_stage'] in home['canonical_field_stages'],
                        'hub anchor is not a canonical source field stage')
                for logical in home['canonical_field_stages']:
                    require(type(logical) is int and 0 <= logical < 81,
                            'original canonical field stage bounds')
                    field_endpoints[logical] = logical
        require(all(layer in service_endpoints for layer in selected_layers),
                'selected source layer lacks explicit service endpoint')
        for fragment in (fragment_endpoints if fragment_endpoints is not None
                         else endpoint_map.get('matrix_fragments', [])):
            logical, physical = fragment['logical_stage'], fragment['physical_endpoint']
            require(logical not in field_endpoints or field_endpoints[logical] == physical,
                    'field endpoint depends on fragment; explicit fragment map required')
            field_endpoints[logical] = physical
    programs, offers, groups, events, handled, deferred = {}, [], [], [], set(), []
    end = ISA.encode(full_shape=True, unit=ISA.UNIT_END, wait=31)

    def append_group(records):
        require(len(records) == 4, 'complete TP4 native group required')
        stage = records[0]['stage']
        require(all(r['rank'] == rank and r['stage'] == stage for rank, r in enumerate(records)),
                'TP4 fragment stage/rank order differs')
        endpoint = records[0].get('physical_endpoint', stage)
        require(all(r.get('physical_endpoint', stage) == endpoint for r in records),
                'TP4 endpoint differs')
        indices = []
        for rank, record in enumerate(records):
            words = record.pop('words')
            image = programs.setdefault((endpoint, rank), [])
            entry = len(image)
            require(words and entry+len(words)+9 <= 1 << 14, 'native entry14 capacity exceeded')
            image.extend(words)
            for operation in record.get('source_pc', []):
                operation['native_pc'] = entry+operation['pc']
                operation['producer'] = 9+operation['native_pc']
                word = words[operation['pc']]
                operation['native_operation'] = dict(index=operation['producer'],
                    unit=operation['instruction']['unit'],
                    template_sha256=operation['template_word_sha256'],
                    instruction=[(word>>(32*j))&0xffffffff for j in range(64)])
            indices.append(len(offers))
            offers.append(dict(record, entry=entry, physical_endpoint=endpoint, die_id=4*endpoint+rank,
                               **context, identity=identity, candidate_only=True,
                               context_restore_required=True))
        groups.append(indices)
        return len(groups)-1

    # Source dictionary preserves the owner's literal graph order, including
    # non-instruction actions/fences. Neither numeric stage sort nor cost order
    # may replace it.
    with tempfile.TemporaryDirectory(prefix='s81-candidate-runs-') as scratch:
        for node, n in source.nodes.items():
            if n['scope'] not in selected_layers or node in handled:
                continue
            if node in runs:
                run = runs[node]
                records = []
                for rank in range(4):
                    directory = Path(scratch)/f'run{len(groups)}_r{rank}'
                    native = execution.emit_nonfield_run(run['nodes'], run['stage'], rank, directory)
                    words = [int(w, 16) for w in (directory/'prog.hex').read_text().splitlines()]
                    require(native['nodes'] and
                            [r['node'] for r in native['nodes']] == run['nodes'] and
                            native['stage'] == run['stage'] and native['rank'] == rank,
                            'actual emitted nonfield run differs')
                    require(hashlib.sha256((directory/'prog.hex').read_bytes()).hexdigest() ==
                            native['program_sha256'], 'native run image changed')
                    records.append(dict(node=node, source_nodes=list(run['nodes']),
                                        stage=run['stage'], rank=rank, provider='native-source-run',
                                        physical_endpoint=service_endpoints.get(run['layer'], (run['stage'], []))[0],
                                        source_pc=[dict(r) for r in native['nodes']], words=words))
                group = append_group(records)
                events.append(dict(kind='nonfield_run', nodes=list(run['nodes']),
                                   group=group, stage=run['stage']))
                handled.update(run['nodes'])
                continue
            require(node not in covered, 'nonfield run begins outside selected source order')
            binding = source.bindings[node]
            if binding.get('address_bound'):
                require(node in movements, 'source field movement missing')
                movement = movements[node]
                live = eids.get(node)
                indexed = binding.get('selector_slot') is not None
                if not include_fields or (indexed and live is None):
                    deferred.append(node)
                    events.append(dict(kind='deferred_field', node=node,
                                       reason='live_EIDs_required' if indexed and live is None
                                              else 'field_compilation_not_selected',
                                       movement=movement))
                    continue
                dispatches = [execution.dispatch(node, r, expert_ids=live) for r in range(4)]
                count = len(dispatches[0]['fragments'])
                require(count > 0 and all(len(d['fragments']) == count for d in dispatches),
                        'actual rank fragment count mismatch')
                field_groups = []
                for ordinal in range(count):
                    records = []
                    for rank, dispatch in enumerate(dispatches):
                        f = dispatch['fragments'][ordinal]
                        require(endpoint_map is None or f['stage'] in field_endpoints,
                                'explicit selected fragment endpoint mapping required')
                        require(f['rank'] == rank and f['die_id'] == 4*f['stage']+rank and
                                f['stage'] in movement['field_stages'],
                                'actual canonical field owner differs from movement')
                        records.append(dict(node=node, source_nodes=[node],
                                            stage=f['stage'], rank=rank, provider='field',
                                            physical_endpoint=field_endpoints.get(f['stage'], f['stage']),
                                            fragment_ordinal=ordinal, phase=f['phase'], key=f['key'],
                                            gather_local_rows=f['gather_local_rows'],
                                            ordered_K=f['ordered_K'],
                                            source_matrix_sha256=f['source_matrix_sha256'],
                                            source_predicate=dispatch['predicate'],
                                            expert_ids=None if live is None else list(live),
                                            words=[f['word'], end]))
                    field_groups.append(append_group(records))
                events.append(dict(kind='field', node=node, groups=field_groups,
                                   movement=movement, expert_ids=live))
            else:
                require(n['kind'] != 'instruction', 'candidate instruction absent from ordered runs')
                require(node in assignments, 'source action/fence assignment missing')
                # These remain real source events, not fabricated native END or
                # instructions. The owner must supply their actual consumers.
                events.append(dict(kind=n['kind'], node=node, source=n,
                                   assignment=dict(assignments[node],
                                      physical_endpoint=service_endpoints.get(n['scope'],
                                          (assignments[node]['stage'], []))[0])))
            handled.add(node)
    out = Path(out)
    require(not out.exists(), 'fresh candidate program output required')
    out.mkdir(parents=True)
    artifacts = {}
    for (stage, rank), words in programs.items():
        directory = out/f's{stage}_r{rank}'
        directory.mkdir()
        raw = ''.join(f'{word:0512x}\n' for word in words).encode()
        (directory/'prog.hex').write_bytes(raw)
        artifacts[str((directory/'prog.hex').relative_to(out))] = hashlib.sha256(raw).hexdigest()
    by_stage, by_endpoint = {}, {}
    for group in groups:
        stage = offers[group[0]]['stage']
        by_stage.setdefault(str(stage), []).append(group)
        endpoint = offers[group[0]]['physical_endpoint']
        by_endpoint.setdefault(str(endpoint), []).append(group)
    node_order = {s: [[offers[i]['node'] for i in g] for g in gs] for s, gs in by_stage.items()}
    for offer in offers:
        offer['runtime_directory'] = str((out/f"s{offer['physical_endpoint']}_r{offer['rank']}").resolve())
    unassigned = [n for n in source.nodes.values() if type(n['scope']) is not int]
    result = dict(schema='dsrom.S81.C8.owner-source-dispatch.v1',
                  offers=offers, ownerorderedgroups=groups,
                  ownerorderedgroups_by_stage=by_stage, node_order_by_stage=node_order,
                  node_order_by_endpoint={e:[[offers[i]['node'] for i in g]
                                             for g in gs] for e,gs in by_endpoint.items()},
                  service_endpoint_source=None if endpoint_map is None else
                      dict(schema=endpoint_map.get('schema'),
                           candidate=endpoint_map.get('candidate'),homes=endpoint_map['homes']),
                  ownerorderedgroups_by_endpoint=by_endpoint,
                  logical_serial_stages=81, added_serial_stages=0,
                  source_order=events, selected_layers=selected_layers,
                  deferred_field_nodes=deferred, unassigned_dedicated_services=unassigned,
                  source_actions_and_fences_are_native_offers=False,
                  candidate_only=True, active=False, adopted=False,
                  parent_dispatch_ready=False, hardware_admission=False,
                  source_assignment_candidate=candidate['candidate'],
                  candidate_physical_service_union=candidate['physical_service_union'],
                  native_END_is_whole_stage_or_head_completion=False,
                  artifacts=artifacts)
    (out/'parent_dispatch.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    (out/'ownerorderedgroups.json').write_text(json.dumps(groups, indent=2)+'\n')
    (out/'node_order.json').write_text(json.dumps(node_order, indent=2)+'\n')
    return result



def emit_native_transfer(source_offer, source_node, destination_offer, program_words,
                         source_address, destination_address, words, *, dynamic=None, out=None):
    """Append the existing native SU BYP action, with literal writer enrollment.

    program_words is the destination's REAL packed mutable program image.
    The caller holds the source publication/lease: this function supplies no
    runtime acceptance, payload, tag, or publication grant.
    """
    import hashlib
    import hdc_isa_v41 as ISA
    from dsrom_s81_execution_binding import minimum_vm_extents
    for value in (source_address, destination_address, words):
        if type(value) is not int or value < 0:
            raise ValueError('literal scalar VM extent required')
    if not 0 < words <= 65535 or max(source_address+words,destination_address+words) > 1<<19:
        raise ValueError('transfer exceeds scalar VM19')
    operation = next((r for r in source_offer['source_pc']
                      if r['node'] == source_node), None)
    if operation is None:
        raise ValueError('actual emitted source operation required')
    pc = source_offer['entry']+operation['pc']
    if operation.get('native_pc') != pc or operation.get('producer') != 9+pc:
        raise ValueError('source reader association differs from emitted program')
    ranges = minimum_vm_extents(operation['instruction'], dynamic=dynamic)
    if not any(base <= source_address and source_address+words <= base+count
               for base,count in ranges):
        raise ValueError('source span not written by actual native operation')
    if source_offer['rank'] != destination_offer['rank']:
        raise ValueError('cross-rank transfer needs explicit collective, not SU copy')
    for offer in (source_offer,destination_offer):
        if (offer.get('candidate_only') is not True or
            not 0 <= offer['identity'] < 1<<47 or
            offer['die_id'] != 4*offer['physical_endpoint']+offer['rank']):
            raise ValueError('actual candidate offer association required')
    if any(source_offer[k] != destination_offer[k]
           for k in ('identity','token','position','user','epoch')):
        raise ValueError('transfer context differs; explicit version carry required')
    entry = len(program_words)
    if entry+2+9 > 1<<14:
        raise ValueError('destination program/producer14 capacity')
    instruction = dict(unit=ISA.UNIT_SU, wait=31, su_vec=ISA.VEC_I,
                       su_nout=1, su_nin=words, dst=ISA.DST_VM,
                       o_base=destination_address, o_si=1)
    # The actual wrapper prefetches A/B/C/D unconditionally. Alias unused
    # BYP operands to the same held source span, never unwritten VM address0.
    for operand in 'abcd':
        instruction.update({operand+'_src':ISA.SRC_VM,
                            operand+'_base':source_address, operand+'_si':1})
    word = ISA.encode(full_shape=True, **instruction)
    program_words.extend([word, ISA.encode(full_shape=True, unit=ISA.UNIT_END, wait=31)])
    writer = 9+entry
    def io(offer,address):
        return dict(die_id=offer['die_id'], physical_endpoint=offer['physical_endpoint'],
                    identity=offer['identity'], address=address, words=words,
                    token=offer['token'], position=offer['position'],
                    user=offer['user'], epoch=offer['epoch'])
    result = dict(provider='s81_minimum_su256', entry=entry, producer=writer,
                instruction=instruction, word_hex=f'{word:0512x}',
                word_sha256=hashlib.sha256(word.to_bytes(256,'little')).hexdigest(),
                source=dict(io(source_offer,source_address), node=source_node,
                            native_pc=pc, producer=operation['producer']),
                destination=dict(io(destination_offer,destination_address), entry=entry,
                                 producer=writer),
                publication_enrollment=dict(producer=writer,
                    output_extents=[[destination_address,words]],
                    begin='actual native GO/ready edge only',
                    native_scalar='actual registered native VM output only',
                    complete='all matching target ACKs plus publication lease'),
                reader_held_until='validated destination publication AND reverse/allcopy drain',
                capture_owner='existing NativeSu publication',
                transfer_hook='DsromS81SourceIoTransferHooks::Binding::native_copy_visible',
                transfer_accepted=None,
                source_scalar_prefetch_reads=words,
                destination_scalar_writes=words, destination_scalar_ACKs=words,
                transfer_hooks_additional_source_reads=0,
                scalar_port_parallelism=1,
                measured_transport_latency=None, measured_native_latency=None,
                candidate_only=True, parent_dispatch_ready=False,
                hardware_admission=False)
    if out is not None:
        out = Path(out)
        out.mkdir(parents=True,exist_ok=False)
        raw = ''.join(f'{w:0512x}\n' for w in program_words)
        (out/'prog.hex').write_text(raw)
        (out/'transfer.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        literal = ','.join(f'0x{(word>>(32*j))&0xffffffff:08x}u' for j in range(64))
        sha = result['word_sha256']
        # Existing typed operation and PrefixPublication API; no new runtime
        # ABI. Enroll is a descriptor only; begin stays at actual accepted GO.
        header = [
            '#pragma once',
            '#include "s81_prefix_publication.hpp"',
            'namespace dsrom_s81_emitted_transfer {',
            'inline DsromS81PrefixOperation operation() {',
            f'  return {{{writer}u,2u,"{sha}",{{{literal}}}}};',
            '}',
            'inline void enroll(dsrom_s81_minimum::PrefixPublication& p) {',
            f'  p.enroll_literal({writer}u,{{{{{destination_address}u,{words}u}}}});',
            '}',
            f'constexpr unsigned source_producer={operation["producer"]}u;',
            f'constexpr unsigned source_address={source_address}u;',
            f'constexpr unsigned destination_address={destination_address}u;',
            f'constexpr unsigned scalar_words={words}u;',
            f'constexpr unsigned source_die={source_offer["die_id"]}u;',
            f'constexpr unsigned destination_die={destination_offer["die_id"]}u;',
            f'constexpr uint64_t identity={source_offer["identity"]}ull;',
            '}',
        ]
        (out/'transfer.hpp').write_text('\n'.join(header)+'\n')
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dispatch', type=Path, required=True)
    p.add_argument('--groups', type=Path, required=True,
                   help='owner ordered list of four offer indices for each TP4 group')
    p.add_argument('--stage', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--fragment-coverage', action='store_true',
                   help='extract literal compiled stage coverage instead of emitting C++')
    p.add_argument('--rank', type=int, default=0)
    p.add_argument('--program-root', type=Path)
    p.add_argument('--terminal', type=Path,
                   help='owner literal ordinal/rank/source_node/entry/producer_pc/end_pc JSON')
    a = p.parse_args()
    dispatch = json.loads(a.dispatch.read_text())
    groups = json.loads(a.groups.read_text())
    if a.fragment_coverage:
        if a.program_root is None:
            p.error('--fragment-coverage requires existing --program-root')
        result = fragment_coverage(dispatch, groups, a.stage, a.rank, a.program_root,
                                   terminal=None if a.terminal is None else json.loads(a.terminal.read_text()))
        import hashlib
        result['source_sha256'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in (a.dispatch, a.groups)}
        if a.terminal is not None:
            result['source_sha256'][str(a.terminal)] = hashlib.sha256(a.terminal.read_bytes()).hexdigest()
        with a.out.open('x') as f:
            f.write(json.dumps(result, indent=2)+'\n')
        print(a.out)
    else:
        if a.program_root is not None or a.terminal is not None:
            p.error('program/terminal inputs require --fragment-coverage')
        print(emit(dispatch, groups, a.stage, a.out))


if __name__ == '__main__':
    main()
