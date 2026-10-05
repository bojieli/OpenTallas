#!/usr/bin/env python3
"""Conditional whole-row HBROM transport schedule; never measured TP scaling.

Complete K stays at its output-row owner. Gathers replace K-partial reductions.
Prices use finite 64-byte/cycle endpoints; PHY and route budgets remain assumptions.
Call on a pristine normalized DAG, not an already transformed graph.
"""
from __future__ import annotations
import copy
import math

SUPPORTED_TP = (1, 2, 4, 8)
LINK_SOURCE = 'results/uarch/hbrom/inputs/hbrom-links.json'
CAVEAT = ('Analytical store-forward schedule using measured endpoint service; vendor PHY '
          'and old 2x45-cycle route allowance; new topology/SS/FF not qualified.')


def packet_cost(payload_bytes, *, board=True, clock_ghz=1.2):
    if payload_bytes < 0 or clock_ghz <= 0:
        raise ValueError('nonnegative payload and positive clock required')
    if not payload_bytes:
        return dict(duration_ns=0., cycles=0, payload_bytes=0, flits=0)
    flits = math.ceil(payload_bytes / 64)
    # 652 measured endpoint cycles for641flits; physical budgets fixed in ns.
    physical_ns = (156 + 11) / 1.2 if board else 11 / 1.2
    cycles = flits + 11 + 90
    return dict(duration_ns=cycles / clock_ghz + physical_ns,
                cycles=cycles + physical_ns * clock_ghz,
                payload_bytes=payload_bytes, flits=flits,
                endpoint_Bpc=64, physical_budget_ns=physical_ns,
                source=LINK_SOURCE, qualification=CAVEAT)


def gather_cost(payload_bytes, tp, *, clock_ghz=1.2):
    """Conservative serialized ring rounds; full payload is globally gathered."""
    if tp not in SUPPORTED_TP:
        raise ValueError('unsupported TP')
    packet = packet_cost(math.ceil(payload_bytes / tp), board=tp > 2,
                         clock_ghz=clock_ghz)
    return dict(duration_ns=(tp-1)*packet['duration_ns'],
                payload_bytes=payload_bytes, bytes_per_rank=(tp-1)*math.ceil(payload_bytes/tp),
                rounds=tp-1, tp=tp, packet=packet,
                qualification='ASSUMED serialized ring, no measured TP scaling',
                arithmetic='gather disjoint completed rows; no FP32 reassociation')


def pack_layers(layer_bytes, capacity_bytes_per_die, tp):
    """Whole-layer contiguous next-fit; capacity is already net of compute/network."""
    if tp not in SUPPORTED_TP or capacity_bytes_per_die <= 0:
        raise ValueError('invalid TP/capacity')
    limit = capacity_bytes_per_die * tp
    if any(b <= 0 or b > limit for b in layer_bytes):
        raise ValueError('whole layer does not fit this group')
    groups, current, used = [], [], 0
    for layer, size in enumerate(layer_bytes):
        if used + size > limit:
            groups.append(current); current=[]; used=0
        current.append(layer); used += size
    if current:
        groups.append(current)
    return dict(groups=groups, dies=len(groups)*tp,
                stage_by_layer={l:s for s,g in enumerate(groups) for l in g})


def _global_partition_work(name):
    """Only explicitly partitioned dimensions; norm/HC/scalars remain replicated."""
    suffix = name.split('.attn.', 1)[-1]
    if '.attn.' in name:
        if suffix == 'q_rope': return 64*64
        if suffix in ('scores', 'pv'): return 64*640*512  # L0/1 adjusted by caller
        if suffix in ('max','exp','den'): return 64*640
        if suffix == 'sink': return 64
        if suffix == 'normalize': return 64*512
        if suffix == 'z_quant': return 8192
    if '.ffn.' in name:
        suffix = name.split('.ffn.', 1)[1]
        if suffix in ('shared_swiglu','shared_quant'): return 2304
        if suffix in ('swiglu','route_w','quant2'): return 6*2304
        if suffix == 'softplus_sqrt': return 384
    if name == 'head.argmax': return 129280
    return None


def reprice_nodes(nodes, tp, layers_per_stage=1, *, clock_ghz=1.2,
                  selected_kv_forwarding='serialized'):
    """Return own transport/nonweight graph, preserving producer dependency joins.

    Row partition is aligned across gate/up and all seven down output matrices.
    New gathers use BF16 unless original payload explicitly specifies FP32.
    No baseline hidden S81 hop charge is carried into this graph.
    """
    if selected_kv_forwarding not in ('serialized','chained'):
        raise ValueError('unknown selected KV forwarding mode')
    if tp not in SUPPORTED_TP or layers_per_stage not in (1,2,4):
        raise ValueError('supported TP1/2/4/8 and layers_per_stage1/2/4 only')
    if any('hbrom_transport' in n for n in nodes):
        raise ValueError('reprice pristine DAG only')
    out=copy.deepcopy(nodes); ids={n['id']:n for n in out}
    def scope(n):
        l=n.get('layer')
        return f'stage{l//layers_per_stage}' if isinstance(l,int) and 0<=l<40 else n.get('stage','head')
    def stamp(n, evidence):
        n['hbrom_transport']=evidence
        n['measurement_inherited']=n.pop('measurement', {})
        n['unknown']=True
    def gathered(n, payload):
        cost=gather_cost(payload,tp,clock_ghz=clock_ghz)
        n.update(duration_ns=cost['duration_ns'],kind='collective',resources=[scope(n)+':transport'])
        stamp(n,dict(op='output_allgather',**cost))
    def insert_before(target, name, deps, payload):
        if target not in ids:return
        n=dict(id=name,deps=list(dict.fromkeys(deps)),layer=ids[target].get('layer'),duration_ns=0,kind='collective')
        gathered(n,payload);out.append(n);ids[name]=n
        ids[target]['deps']=[name]
    # Existing collective nodes represent different algebra under row ownership.
    for n in list(out):
        name=n['id']; original=n.get('original',{})
        if n['kind']=='collective':
            payload=original.get('payload')
            if payload is None:
                raise ValueError('missing collective payload: '+name)
            if name.endswith(('out_allreduce','combine_allreduce')):payload=5120*4
            if name.endswith('idx.topk_merge'):payload=tp*512*8
            if name.endswith('cand.merge'):payload=tp*2048*8
            if name=='head.argmax_merge':payload=tp*8
            gathered(n,payload)
        elif n['kind']=='hop':
            kind=original.get('hop_kind')
            if kind=='substage':
                n.update(duration_ns=0.,kind='join',resources=[])
                stamp(n,dict(op='removed_legacy_substage',reason='whole layer on one storage group'))
                n['unknown']=False
            elif kind in ('head','return'):
                cost=packet_cost(40976 if kind=='head' else 10256,clock_ghz=clock_ghz)
                n.update(duration_ns=cost['duration_ns'],resources=[scope(n)+':transport'])
                stamp(n,dict(op='direct_'+kind,**cost))
        work=_global_partition_work(name)
        if name.endswith(('.idx.score','.idx.topk_local')):
            ratio=2 if n.get('layer',20)<20 else 1
            work=1048576//ratio
        if name.endswith(('.idx.topk_final','.cand.final')):
            old=n['duration_ns'];n['duration_ns']=old*max(1,math.ceil(tp/4))
            stamp(n,dict(op='selection_merge_waves',ways=tp,original_duration_ns=old,
                         qualification='ASSUMED TP4 selector service waves, exact key order retained'))
        if work is not None and n['kind'] not in ('weight','join'):
            if n.get('layer') in (0,1) and name.endswith(('.scores','.pv','.max','.exp','.den')):work=work*128//640
            # Retain entire measured TP4 duration as one service wave, including
            # startup. Fractional credit prohibited; TP8 uses one unchanged wave.
            waves=math.ceil(math.ceil(work/tp)/math.ceil(work/4))
            old=n['duration_ns'];n['duration_ns']=old*waves
            stamp(n,dict(op='nonweight_service_waves',global_work=work,per_rank_work=math.ceil(work/tp),
                         reference_TP4_work=math.ceil(work/4),waves=waves,original_duration_ns=old,
                         qualification='ASSUMED fixed service engine waves, not measured at new width; no sub-wave speedup'))
    for layer in range(40):
        p=f'L{layer}'
        # Arbitrary output-row ownership of wo_a requires all grouped inputs.
        for target,suffix,deps,payload in (
            (p+'.attn.wo_a:component0','attn.wo_a_input_gather',[p+'.attn.normalize'],65536),
            (p+'.attn.wo_b:component0','attn.wo_b_input_gather',[p+'.attn.z_quant'],16384),
            (p+'.ffn.down:component0','ffn.down_input_gather',[p+'.ffn.quant2',p+'.ffn.shared_quant'],32256)):
            if target in ids:
                # Retain resource/order dependencies as well as semantic inputs.
                deps=ids[target]['deps']+deps
                insert_before(target,p+'.'+suffix,[d for d in deps if d in ids],payload)
        combine=p+'.ffn.combine_allreduce'; down=p+'.ffn.down'
        if combine in ids and down in ids:
            name=p+'.ffn.ordered_expert_sum'
            # Seven additions from +0, six routed ascending-id then shared last.
            rows=math.ceil(5120/tp); cycles=7*(math.ceil(rows/1024)+4)
            n=dict(id=name,deps=list(ids[combine]['deps']),layer=layer,kind='vector',
                   duration_ns=cycles/.9,resources=[scope(ids[combine])+':su'])
            stamp(n,dict(op='ordered_expert_sum',rows=rows,terms=7,bytes_read=rows*7*4,
                         qualification='ASSUMED1024 lanes, ALAT4 at0.9GHz; seven ordered rounds; buffer ports unqualified'))
            out.append(n);ids[name]=n;ids[combine]['deps']=[name]
        # One direct hop only when consecutive whole layers change groups.
        prev=f'L{layer-1}.ffn.hc_post'
        if layer and layer%layers_per_stage==0 and prev in ids and any(n.get('layer')==layer for n in out):
            name=p+'.hbrom.stage_in';cost=packet_cost(40976,clock_ghz=clock_ghz)
            n=dict(id=name,deps=[prev],layer=layer,kind='hop',duration_ns=cost['duration_ns'],
                   resources=[f'edge{layer//layers_per_stage-1}:transport'])
            stamp(n,dict(op='neighbor_stage',**cost))
            for other in out:
                if other.get('layer')==layer:other['deps']=[name if d==prev else d for d in other['deps']]
            out.append(n);ids[name]=n
        # Reindex requests execute at KV owner20. Full-score baseline retained;
        # request query travels there, selected rows return to requesting stage.
        if layer in (24,28,32,36):
            distance=layer//layers_per_stage-20//layers_per_stage
            for own in out:
                if own['id'].startswith(p+'.attn.idx.') or own['id']==p+'.attn.gather':
                    own['service_owner_stage']=20//layers_per_stage
                    owner_scope=f'stage{20//layers_per_stage}'
                    own['resources']=[owner_scope+':'+r.split(':',1)[1] if ':' in r and (r.startswith('stage') or r.startswith('layer_')) else r for r in own.get('resources',[])]
                    own['resources'].append(owner_scope+':index_service')
            for suffix,payload,op in (('idx.score',32*128*2+32*4,'remote_index_query'),
                                      ('idx.topk_final',512*8,'remote_selected_ids'),
                                      ('gather',147456,'remote_selected_rows')):
                target=p+'.attn.'+suffix
                if target in ids and distance:
                    n=ids[target];cost=packet_cost(payload,clock_ghz=clock_ghz)
                    n['duration_ns']+=distance*cost['duration_ns']
                    n.setdefault('resources',[]).extend(f'edge{i}:transport' for i in range(20//layers_per_stage,layer//layers_per_stage))
                    n['resources'].append(f'stage{20//layers_per_stage}:index_service')
                    n.setdefault('hbrom_transport',{})[op]=dict(payload_bytes=payload,hops=distance,
                        duration_ns=distance*cost['duration_ns'],qualification='ASSUMED request/response at shared KV owner20; no full-key replication or candidate-only speedup')
                    n['unknown']=True
        # Reuse selected rows from most recent index source. Serial forwarding
        # priced explicitly; conservative no overlapping prefetch credit.
        if layer>=2 and layer not in (2,8,14,20,24,28,32,36):
            source=max(s for s in (2,8,14,20,24,28,32,36) if s<layer)
            crossings=layer//layers_per_stage-source//layers_per_stage
            target=p+'.attn.rows_allgather'
            if crossings and target in ids:
                n=ids[target];cost=packet_cost(147456,clock_ghz=clock_ghz)
                n['duration_ns']+=crossings*cost['duration_ns']
                n['resources']+= [f'edge{i}:transport' for i in range(source//layers_per_stage,layer//layers_per_stage)]
                n['hbrom_transport']['kv_forwarding']=dict(source_layer=source,payload_bytes=147456,hops=crossings,
                    duration_ns=crossings*cost['duration_ns'],qualification='ASSUMED fresh unicast from selection owner; repeated transfers charged, no free prefetch')
    if selected_kv_forwarding=='chained':
        _chain_selected_kv(out,tp,layers_per_stage,clock_ghz)
    return out


def _chain_selected_kv(nodes,tp,layers_per_stage,clock_ghz):
    """Finite one-slot/rank generations, early availability and full handoff.

    Extra slot area is a required separate model ledger, never existing-SRAM credit.
    Slot ports256B/cycle with2 protected pipeline cycles; serial read/link/write.
    No cut-through, unbounded credits, candidate shortcuts or free prefetch.
    """
    ids={n['id']:n for n in nodes}; previous_users={}
    sources=(2,8,14,20,24,28,32,36)
    payload=147456; local_cycles=math.ceil(payload/256)+2
    local_ns=local_cycles/clock_ghz
    for pos,source in enumerate(sources):
        end=sources[pos+1] if pos+1<len(sources) else 40
        producer=f'L{source}.attn.rows_allgather'
        if producer not in ids:continue
        first=source//layers_per_stage;last=(end-1)//layers_per_stage
        visibility={}
        for group in range(first,last+1):
            name=f'KV{source}.stage{group}.visible'
            dependencies=list(previous_users.get(group,[]))
            if group==first:
                dependencies.append(producer)
                duration=local_ns
                resources=[f'stage{group}:transport',f'stage{group}:selected_kv_slot']
                operation='selected_kv_publish'
                packet=None
            else:
                dependencies.append(visibility[group-1])
                packet=packet_cost(payload+16,clock_ghz=clock_ghz)
                duration=2*local_ns+packet['duration_ns']
                resources=[f'edge{group-1}:transport',f'stage{group-1}:transport',
                           f'stage{group}:transport',f'stage{group-1}:selected_kv_slot',
                           f'stage{group}:selected_kv_slot']
                operation='selected_kv_chain_handoff'
            n=dict(id=name,deps=list(dict.fromkeys(dependencies)),layer=max(source,group*layers_per_stage),
                   kind='hop',duration_ns=duration,resources=resources,unknown=True,
                   hbrom_transport=dict(op=operation,source_layer=source,generation=source,
                     payload_bytes=payload,packet=packet,local_port_Bpc=256,
                     protected_port_latency_cycles=2,local_port_cycles=local_cycles,
                     required_extra_sram_bytes_per_rank=payload,overwrite_waits=list(previous_users.get(group,[])),
                     qualification='OPT-IN assumed additional protected slot/rank; explicit read-link-write handoff; no physical/RTL qualification'))
            nodes.append(n);ids[name]=n;visibility[group]=name
        for layer in range(source,end):
            group=layer//layers_per_stage
            target=f'L{layer}.attn.rows_allgather'
            if target not in ids:continue
            if layer!=source:
                n=ids[target];cost=gather_cost(67584,tp,clock_ghz=clock_ghz)
                n.update(duration_ns=cost['duration_ns'],resources=[f'stage{group}:transport'])
                n['deps']=list(dict.fromkeys(n['deps']+[visibility[group]]))
                n['hbrom_transport']=dict(op='window_gather_selected_kv_visible',**cost,
                    selected_visibility=visibility[group],generation=source,selected_bytes=payload)
            # QK and PV both own read leases. Source QK also waits local publish.
            for suffix in ('scores','pv'):
                consumer=f'L{layer}.attn.{suffix}'
                if consumer in ids:
                    ids[consumer]['deps']=list(dict.fromkeys(ids[consumer]['deps']+[visibility[group]]))
                    ids[consumer].setdefault('resources',[]).append(f'stage{group}:selected_kv_slot')
                    ids[consumer]['duration_ns']+=local_ns
                    ids[consumer].setdefault('hbrom_transport',{})['selected_slot_read']=dict(
                        payload_bytes=payload,cycles=local_cycles,duration_ns=local_ns,
                        qualification='additional serial protected slot read, no overlap credit')
        for group in range(first,last+1):
            users=[f'L{l}.attn.pv' for l in range(source,end)
                   if l//layers_per_stage==group and f'L{l}.attn.pv' in ids]
            if group<last:users.append(visibility[group+1])
            previous_users[group]=users or [visibility[group]]


def transport_summary(nodes):
    records={n['id']:n['hbrom_transport'] for n in nodes if 'hbrom_transport' in n}
    return dict(schema='hbrom.transport.v1',records=records,
                neighbor_stage_hops=sum(v.get('op')=='neighbor_stage' for v in records.values()),
                legacy_substage_hops_removed=sum(v.get('op')=='removed_legacy_substage' for v in records.values()),
                qualification=CAVEAT,complete_implementation=False)
