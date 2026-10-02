#!/usr/bin/env python3
"""Source-emitted descriptor/owner join and finite calendar input, without RTL."""
import argparse,collections,copy,gzip,hashlib,json
from pathlib import Path
import dsrom_full_product_binding as B
import dsrom_finite_resources as D
F=B.F

class OwnerTrace(F.FullLayerBuilder):
    def __init__(self,layer):
        super().__init__(layer)
        for table in (self.lay.mat,self.lay.qmat):
            for key,mat in table.items():
                if isinstance(key,tuple) and isinstance(mat,dict):mat['_owner_key']=key
    def me(self,mat,*args,**kwargs):
        super().me(mat,*args,**kwargs)
        self.prog[-1][0]['_owner_key']=mat.get('_owner_key')
    def linq(self,mat,*args,**kwargs):
        super().linq(mat,*args,**kwargs)
        self.prog[-1][0]['_owner_key']=mat.get('_owner_key')

def emitted_owner_keys(demand):
    keys={};old=F.I.SU_LANES;F.I.SU_LANES=8
    try:
        for stage in demand['functional_program']['stages']:
            layer=stage['layer'];builder=OwnerTrace(layer)
            actual=F.jsonable(builder.build_layer())
            normalized=[{k:v for k,v in f.items() if k!='_owner_key'} for f in actual]
            if normalized!=stage['instructions']:raise ValueError('owner trace changes original emitted instructions')
            for pc,f in enumerate(actual):keys[f'L{layer}.I{pc}']=f.get('_owner_key')
    finally:F.I.SU_LANES=old
    return keys

ALIASES={'iwq_b':'indexer.wq_b','iwk':'indexer.wk','iwp':'indexer.weights_proj',
         'cwkv':'compressor.wkv','cwgate':'compressor.wgate','ewkv':'engram.wkv'}

def alias_for(key):
    if len(key)==2:return ALIASES.get(key[1],key[1])
    if key[1]=='shared':return 'shared.'+key[2]
    if key[1]=='exp':return 'exp'+str(key[2])+'.'+key[3]
    raise ValueError('unknown immutable logical key: '+str(key))

def join(demand,route):
    if route['candidate']!=B.CANDIDATE or route['capacity']!='PASS_SYMBOLIC_STORAGE_PLACEMENT':raise ValueError('same candidate successful owner map required')
    layers={x['layer']:x for x in route['layer_owners']}
    if set(layers)!=set(range(40)):raise ValueError('all40 actual owner map')
    keys=emitted_owner_keys(demand);templates={};counts=collections.Counter();wo_groups=collections.Counter()
    for node in demand['nodes']:
        identity=node['id'];f=node.get('instruction',{});u=f.get('unit');layer=node['scope'];owner={};role=node['kind']
        if isinstance(layer,int):
            r=layers[layer];home=r['immutable_HE_CROM_home']
            dense={x['alias']:x for x in r['dense_matrix_owners']}
            if u==5:
                which='attn' if f['_tag'].endswith('hc_attn') else 'ffn' if f['_tag'].endswith('hc_ffn') else None
                if which is None:raise ValueError('HE alias not source bound')
                owner={'kind':'HE','alias':'hc_'+which+'_fn','stage':home,'native_HROM_bits':768,
                       'input_F32_bytes':f['he_k']*8*4,'output_F32_bytes':f['he_nout']*4,
                       'native_issue_cycles_default_NL3_IL8':f['he_k']*8,
                       'default_NL3_IL8_profile_not_selected_physical_configuration':True}
                role='HE_adapter';counts['HE_call_sites']+=1
            elif (u==3 and not f.get('qe_mode',0)) or (u==1 and not f.get('me_wsrc',0)):
                key=keys.get(identity)
                if key is None and u==1 and f.get('_tag')==f'L{layer}.out':
                    g=wo_groups[layer];wo_groups[layer]+=1;alias='wo_a.group'+str(g)
                elif key is not None:alias=alias_for(key)
                elif u==3 and f.get('_tag')==f'L{layer}.engram':alias='engram.wkv'
                else:raise ValueError('immutable descriptor owner unresolved: '+identity)
                if alias.startswith('exp'):
                    if not f.get('qe_ind'):raise ValueError('runtime expert selector missing')
                    part=alias.rsplit('.',1)[1];table={int(e):int(s) for e,s in r['expert_stage_IDs'].items()}
                    if set(table)!=set(range(384)):raise ValueError('complete runtime expert owner map')
                    owner={'kind':'runtime_expert_field','part':part,'owner_stage_by_EID':table,
                           'source_EID_VM_address':f['qe_ibase'],'source_EID_stride':f['qe_istride'],
                           'golden_order':'source emitted call order; selected EIDs ascending6; no owner-home sorting'}
                else:
                    if alias not in dense:raise ValueError('actual dense alias absent: '+alias)
                    m=dense[alias]
                    issued_rows=f.get('qe_nout') if u==3 else f.get('me_nout')
                    issued_K=f['qe_nb']*32 if u==3 else f['me_k']*(1<<f.get('me_split',0))
                    if (issued_rows,issued_K)!=(m['rows_per_rank'],m['K_per_rank']):raise ValueError('actual owner/ISA row or K extent mismatch: '+identity)
                    owner={'kind':'dense_field','alias':alias,'stage':m['matrix_stage'],
                        'source_key':m['source_key'],'format':m['format'],'rows_per_rank':m['rows_per_rank'],
                        'K_per_rank':m['K_per_rank'],'rank_slices':m['rank_slices'],
                        'conditional_LAT8_issue_cycles':m['conditional_LAT8_issue_cycle_model'],
                        'issue_cost_is_source_model_not_connected_measurement':True}
                role='field_adapter';counts['field_cfg_call_sites']+=1
            else:owner={'kind':'native_frontend_service','placement_binding':'frontend_home(layer,rank) REQUIRED; immutable provider home is not frontend proof'}
            owner['immutable_HE_CROM_home']=home
        else:owner={'kind':str(layer)+'_service','physical_provider_bound':False}
        t={'id':identity,'node_sha256':B.digest(node),'kind':role,'source_unit':u,'owner':owner,
           'source_collective_input_bits':f.get('coll_n',0)*(64 if f.get('coll_op')==2 else 32),
           'source_instruction_predicate':f.get('pred',0),'source_dynamic_fields':{k:v for k,v in f.items() if '_d_' in k or k.startswith('me_d') or k.startswith('qe_d')},
           'source_reads':f.get('_reads',[]),'source_writes':f.get('_writes',[]),
           'cfg':{'source_load_cycles':27,'phase_request_required_if_accepted':role=='field_adapter',
                  'source_accepted_phase_and_busy_fence_required':True,'resident_phase_count_is_not_token_event_count':True},
           'cost_profile_required':role,'no_invented_frontend_owner_or_zero_duration':True}
        templates[identity]=t;counts['all_node_templates']+=1
    events=[]
    for rank in range(4):
        previous=None;prior_scope=None;last_unit={};scope_nodes=[];last_writer={}
        for node in demand['nodes']:
            t=templates[node['id']];f=node.get('instruction',{});nid=t['id']+f'.R{rank}';deps=set()
            if node['scope']!=prior_scope:
                if previous:deps.add(previous)
                last_unit={};scope_nodes=[];last_writer={};prior_scope=node['scope']
            for unit,last in last_unit.items():
                if unit in F.I.UNITS and f.get('wait',0)>>(unit-1)&1:deps.add(last)
            for name in f.get('_reads',[]):
                if name in last_writer:deps.add(last_writer[name])
            if f.get('unit')==F.I.UNIT_END or node['kind']=='consumer_done_fence':deps.update(scope_nodes)
            if f:
                last_unit[f['unit']]=nid
                for name in f.get('_writes',[]):last_writer[name]=nid
            events.append({'id':nid,'template':t['id'],'rank':rank,'previous_acceptance':previous,
                           'required_completion_dependencies':sorted(deps)})
            previous=nid;scope_nodes.append(nid)
    return {'schema':'opentallas.dsrom.provider-first-event-join.v1','candidate':B.CANDIDATE,
            'functional_program_sha256':demand['functional_program_sha256'],'templates':templates,'events':events,
            'census':dict(counts),'rank_event_count':len(events),'trace_preserves_all_original_instructions':True,
            'storage_PASS_is_not_calendar_PASS':True,'schedule_costs_complete':False,'build_admitted':False,
            'actual_selected_expert_trace_required':True,'physical_or_rate_admission':False}

def price(joined,bindings,resources,rendezvous):
    expected={e['id'] for e in joined['events']}
    if set(bindings)!=expected:raise ValueError('all finite event profiles required; no missing endpoints as zero')
    specs={};selected={}
    for e in joined['events']:
        b=bindings[e['id']];t=joined['templates'][e['template']]
        if b.get('node_sha256')!=t['node_sha256'] or not b.get('source_receipts') or not b.get('native_provider_ABI_receipts'):raise ValueError('source-exact finite native provider profile required')
        c=b['calendar'];period=B.validate_calendar(c)
        if c['complete_cycles']<1 or c['accept_cycles']<1:raise ValueError('native endpoint acceptance/completion cannot be zero')
        if not set(e['required_completion_dependencies'])<=set(c['completion_dependencies']):raise ValueError('causal producer/wait/visibility/fence dependency missing')
        if t['owner']['kind']=='runtime_expert_field':
            eid=b.get('selected_EID');owners={int(k):v for k,v in t['owner']['owner_stage_by_EID'].items()}
            if eid not in owners or b.get('owner_stage')!=owners[eid] or not b.get('selected_EID_source_receipts'):raise ValueError('selected expert actual owner not bound')
            selector=(e['rank'],e['template'].split('.I')[0],t['owner']['source_EID_VM_address'])
            if selector in selected and selected[selector]!=eid:raise ValueError('same source EID changed across expert triple')
            selected[selector]=eid
        if t['owner']['kind']=='dense_field' and b.get('owner_stage')!=t['owner']['stage']:raise ValueError('dense actual owner changed')
        if t['kind']=='field_adapter':
            if not b.get('cfg_acceptance_source_receipts') or c['complete_cycles']<27:raise ValueError('actual cfg acceptance cost/fence unbound')
            claims=[q for q in b.get('resource_claims',[]) if resources.get(q['resource'],{}).get('kind')=='field_cfg_matrix']
            if len(claims)!=1:raise ValueError('unique source field cfg/matrix resource missing')
            q=claims[0];resource=resources[q['resource']]
            if resource.get('owner_stage')!=b.get('owner_stage') or resource.get('domain')!='streaming' or resource.get('scope')!='rank' or resource.get('minimum_issue_cycles',0)<27 or q['release']!='complete':raise ValueError('field cfg/matrix busy and return visibility ownership unbound')
        specs[e['id']]={'binding':b,'period':period,'previous':e['previous_acceptance'],
                        'dependencies':c['completion_dependencies'],'unit':t['source_unit'],'collective_input_bits':t['source_collective_input_bits']}
    bylayer=collections.defaultdict(dict)
    for (rank,layer,addr),eid in selected.items():bylayer[(rank,layer)][addr]=eid
    for slots in bylayer.values():
        values=[slots[a] for a in sorted(slots)]
        if len(values)!=6 or values!=sorted(set(values)):raise ValueError('selected6 expert golden ascending order not bound')
    # Existing strict globally shared resource/domain/II/accept-vs-complete implementation.
    return D.price(specs,resources,rendezvous)

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--demand',type=Path,required=True);a.add_argument('--route',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    raw=args.demand.read_bytes();d=json.loads(gzip.decompress(raw) if args.demand.suffix=='.gz' else raw);rraw=args.route.read_bytes();r=json.loads(rraw)
    x=join(d,r);x['input_receipts']=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [args.demand,args.route]]
    x['compiler_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();data=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
    if args.out.suffix=='.gz':data=gzip.compress(data,mtime=0)
    with args.out.open('xb') as f:f.write(data)
if __name__=='__main__':main()
