"""One source-preserving service/field split; no payload, RTL or physical run.

Original stage identities are logical compiler addresses. Explicit physical
endpoint IDs are a branch routing map, never encoded as a new serial stage.
"""
import argparse, collections, gzip, hashlib, json, math
from pathlib import Path

NAME='S81-SERVICE9-FIELD2417-SISTER40-TP4'

def field_endpoint(stage):
    # Preserve L20's actual matrix ownership 37/38; retain all odd stages.
    return 81+stage//2 if stage in range(0,80,2) and stage != 38 else stage

def service_endpoint(layer):
    return 100 if layer == 19 else 2*layer

def anchor(endpoint):
    return 2*(endpoint-81) if endpoint >= 81 else endpoint

def hops(a,b):
    if a==b:return 0
    return abs(anchor(a)-anchor(b))+(a>=81)+(b>=81)

def build(owner):
    owner=Path(owner);C=owner/'results/uarch/dsrom_s81_released_binding_20261004/canonical'
    P=owner/'results/uarch/dsrom_s81_service_home_candidate_20261004/candidate.json'
    old=json.loads(P.read_text());stage=json.loads((C/'stage_map.json').read_text())
    inv=json.loads((C/'inventory.json').read_text());providers=json.loads((C/'providers.json').read_text())
    strictpath=owner/'results/uarch/dsrom_s81_rd64_connectivity_20261004/canonical_binding_r1/model.json'
    strict=json.loads(strictpath.read_text())
    assert stage['layer_matrix_stages']['20']==[37,38]
    assert (inv['pairs_per_rank_die'],inv['BF_dual_pairs'],inv['TP'])==(2417,519,4)
    assert strict['retained_nodes']==5090 and strict['retained_unilateral_nodes']==384
    BF=set(stage['BF_site_IDs']);provider_sites={}
    for l in range(40):
        ps=[p for p in providers if p['layer']==l]
        assert {p['kind'] for p in ps}=={'HE','CROM'} and {p['stage'] for p in ps}=={2*l}
        sites=[i for p in ps for i in p['pairs']]
        assert len(set(sites))==9 and not(set(sites)&BF)
        provider_sites[l]=sites
    fragments=[];by_alias=collections.defaultdict(list);moved=collections.Counter()
    with gzip.open(C/'matrix_map.jsonl.gz','rt') as f:
        for ordinal,line in enumerate(f):
            x=json.loads(line);s=x['stage'];e=field_endpoint(s)
            # The immutable journal ordinal names the ENTIRE exact plan, not
            # a new inferred active mask. All row/MB/PP/K/scale coordinates stay.
            fragments.append({'source_journal_ordinal':ordinal,'layer':x['layer'],
                              'alias':x['alias'],'logical_stage':s,'physical_endpoint':e,
                              'receiver_site_mapping':'identity original pair ID; all2417 compiled sites charged',
                              'all_four_rank_slices_unchanged':True,'original_plan_unchanged':True})
            by_alias[x['layer'],x.get('original_alias') or x['alias']].append(
                {'stage':s,'endpoint':e,'rank_slices':x['rank_slices']})
            if s!=e:moved[s]+=1
    assert len(fragments)==46671
    topology=[{'a':i,'b':i+1,'kind':'existing_serial_stage_edge'} for i in range(80)]
    topology += [{'a':2*l,'b':81+l,'kind':'new_branch_edge_not_serial_stage'} for l in range(40)]
    maps=[]
    for l in range(40):
        s=2*l; added=81+l; sites=provider_sites[l]
        maps.append({'layer_provider':l,'original_home':s,'service_home':service_endpoint(l),
                     'rank_service_die_ids':[4*service_endpoint(l)+r for r in range(4)],
                     'added_endpoint':added,'rank_added_die_ids':[4*added+r for r in range(4)],
                     'provider_source_sites':sites,
                     'provider_service_local_slots':dict(zip(map(str,sites),range(9))),
                     'HE_CROM_words':'original provider journal unchanged; L19 copies nine complete provider elements and preserves originals on38',
                     'added_role':'service_only' if l==19 else 'field_only',
                     'field_from_stage':None if l==19 else s,
                     'displaced_fragments':moved[s] if l!=19 else 0,
                     'field_receiver_slots':{'compiled_NP':2417,'BF_sites':sorted(BF),
                         'map':'old site i -> new site i; provider-role holes still charged'} if l!=19 else None,
                     'reduced_service_field':'no matrix field; nine complete Q_ONLY provider elements, no compact NP9/R128 field generator assumed'})
    src=owner/'results/uarch/dsrom_native_weight_address_join_20261002'
    with gzip.open(src/'r3/node_bindings.jsonl.gz','rt') as f:bindings={x['node']:x for x in map(json.loads,f)}
    movements=[];tot=0.;baseline_tot=0.;L20=0.;L19=0.
    for m in old['field_movements']:
        b=bindings[m['node']];l=int(m['node'].split('.')[0][1:]);newhome=service_endpoint(l)
        choices=[]
        for alias in dict.fromkeys(p['alias'] for p in b['phase_choices']):
            rank_ns=[0.]*4;rank_old=[0.]*4;transfers=[]
            for fragment in by_alias[l,alias]:
                e=fragment['endpoint'];h=hops(newhome,e);ho=abs(2*l-fragment['stage'])
                for r,span in enumerate(fragment['rank_slices']):
                    ib=4*(span['cols'][1]-span['cols'][0]);ob=4*(span['rows'][1]-span['rows'][0]);packet=math.ceil(ib/64)+math.ceil(ob/64)
                    # Same conservative old serial packet model, with graph
                    # distance instead of abs(physical ID). No bandwidth gift.
                    ns=(2*h*909+h*packet)/1.2;ons=(2*ho*909+ho*packet)/1.2
                    rank_ns[r]+=ns;rank_old[r]+=ons
                    if h:transfers.append({'rank':r,'field_endpoint':e,'source_stage':fragment['stage'],
                                           'hops_each_way':h,'input_bytes':ib,'output_bytes':ob,'packet_edges':packet})
            choices.append({'alias':alias,'rank_ns':rank_ns,'rank_old_ns':rank_old,'transfers':transfers})
        worst=max(choices,key=lambda c:max(c['rank_ns']));before=max(max(c['rank_old_ns']) for c in choices)
        ns=max(worst['rank_ns']);tot+=ns;baseline_tot+=before
        if l==20:L20+=ns
        if l==19:L19+=ns
        movements.append({'node':m['node'],'new_service_endpoint':newhome,'alternatives':len(choices),
                          'worst_alias':worst['alias'],'transport_ns':ns,'prior_transport_ns':before,
                          'transfers':worst['transfers']})
    # No proportional pair-area credit. Remove entire matrix field variable
    # and per-element increment classes, retain ALL inherited fixed debit and
    # FULL strict return debit even on the reduced service-only die.
    fixed=465.477;variable=271.142;increments=71.072
    replacement=53.0740740096-.89234;strictreturn=strict['retained_FF50_reservation_mm2']
    # All nine Q_ONLY providers conservatively get larger BF complete-frame
    # outline +halo and all seven 72-bit cfg macros+halo. This is capacity
    # reservation, not qualified macro pin/OBS or installed provider RTL.
    provider9=9*((1002.89+8.64)*(157.68+8.64)+7*(38.016+8.64)*(62.910+8.64))/1e6
    service_screen=fixed+replacement+strictreturn+provider9
    field_screen=fixed+variable+increments+strictreturn
    budget=.98*858
    return {'candidate':NAME,'default_enabled':False,'adopted':False,'physical_build_admitted':False,
            'source_fragment_count':len(fragments),'displaced_fragment_count':sum(moved.values()),
            'matrix_fragments':fragments,'homes':maps,'topology':topology,'field37_38_unchanged':True,
            'original_serial_stage_count':81,'added_serial_stages':0,'added_rank_dies':160,
            'total_rank_dies':484,'total_dies_canonical_baseline':inv['total_dies']+160 if 'total_dies' in inv else 528,
            'whole_model_payload_and_MAC_per_byte_unchanged':True,
            'additional_storage':'nine original HE/CROM complete providers replicated for L19; other weight fragments moved, not duplicated',
            'capacity_screen':{'service_die_mm2':service_screen,'field_die_mm2':field_screen,
                'strict_return_nodes':5090,'strict_return_mm2':strictreturn,'all_fixed_debit_retained_mm2':fixed,
                'nine_provider_complete_frame_cfg_reserve_mm2':provider9,'reticle_mm2':858,'two_percent_budget_mm2':budget,
                'service_margin_before_overlays_mm2':budget-service_screen,
                'field_deficit_at_two_percent_before_overlays_mm2':max(0,field_screen-budget),
                'field_fits_858_before_overlays':field_screen<=858,'two_percent_pass':field_screen<=budget,
                'placed_slot_fit':False,'no_overlays_discarded':'PG/clock/PHY/DFT included inherited fixed charge; changed pin/route/codec/control overlay union still unmeasured'},
            'transport':{'conditional_clock_GHz':1.2,'link_payload_bytes_per_edge':64,'baseline_hop_cycles':909,
                'prior_serial_packet_ns':baseline_tot,'split_serial_packet_ns':tot,'delta_ns':tot-baseline_tot,
                'L20_split_packet_ns':L20,'L19_split_packet_ns':L19,'movements':movements,
                'no_free_overlap_or_input_reuse':True,'selected_expert_scope':'worst legal alternative per source slot, never all384',
                'full_token_delta_ns':None,'MTP_iteration_delta_ns':None,'physical_link_qualified':False},
            'implementation_tasks':['Popper route immutable logical stage/phase/key to explicit physical endpoint table; no ISA arithmetic or phase reordering',
                'field-only source root interception/capture -> branch result packets before service-side VM publication; no unpriced protected VM copy on field die',
                'unchanged canonical field37/38 native callers require explicit remote-result publication path, not automatic software restore',
                'L19 HE/CROM copy source mapping at service100; retain original provider/field38 without pruning credit'],
            'concrete_constraints':['Strict5090 retained unary/root debit makes the unchanged complete field-die screen exceed the2percent budget; do not quietly reuse4706 compact debit',
                'candidate not adoptable until exact changed route/PG/clock/service placement and finite source publication calendar fit; capacity screen is not placed fit',
                'baseline link SS/FF failed; clocks are targets not physical signoff',
                'native field-only root forwarding and selected full-token/MTP acceptance calendar remain unimplemented/unmeasured'],
            'input_sha256':{str(p.relative_to(owner)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                [P,C/'matrix_map.jsonl.gz',C/'stage_map.json',C/'providers.json',C/'inventory.json',strictpath,src/'r3/node_bindings.jsonl.gz']}}

def main():
    a=argparse.ArgumentParser();a.add_argument('--owner',type=Path,required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args()
    d=build(x.owner);x.out.mkdir(parents=True,exist_ok=False)
    fs=d.pop('matrix_fragments');ms=d['transport'].pop('movements')
    for n,rows in [('fragment_endpoints.jsonl.gz',fs),('transport_movements.jsonl.gz',ms)]:
        with (x.out/n).open('wb') as f:
            with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as g:
                for row in rows:g.write((json.dumps(row,sort_keys=True,separators=(',',':'))+'\n').encode())
    (x.out/'model.json').write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(x.out.iterdir())}
    manifest['tool_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (x.out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'fragment_count':len(fs),'moved':d['displaced_fragment_count'],'capacity':d['capacity_screen'],'transport':d['transport']},indent=2))
if __name__=='__main__':main()
