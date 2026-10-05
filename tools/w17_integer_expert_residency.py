#!/usr/bin/env python3
"""Metadata-only integer expert placement candidate; no product fit or RTL credit."""
import argparse, ast, gzip, hashlib, json, math, subprocess, types
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=('e0c28412ad892d212661661529a9fc5324af0116','results/rtl/w17_connected_token_preparation_20261001/actual_expert_expected_manifest.json.gz')
INTAKE=('e95c6a2a40b2539cb2844151881535aec12f3957','results/rtl/w17_connected_token_preparation_20261001/actual_manifest_intake.json')
SEG=('42e2471cf20dc081ea59f8f43478435848dc7256','tools/v41_rom_ksplit_bankmap.py')
PLACE=('1c4c5aefdfbbdd41dee75772761a95a3446104cc','tools/v41_die_images_w17w10.py')
AREA=('50e6c9928','results/quality/w16_w10_fullmap_area_20261001/area_price.json')
GEOM=('cc8a2a77bdfc1c69aeda2d0a678d66f5df5a8cd9','tools/uarch_model.py')
RTL=(GEOM[0],'rtl/v41rom/ot_v41_rom_elem_w10.sv')
FAMILIES=('w1','w3','w2')

def blob(pin):return subprocess.check_output(['git','show',pin[0]+':'+pin[1]],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def source_functions(raw,names,env):
    tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if len(nodes)!=len(names):raise ValueError('source function missing')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned metadata functions>','exec'),env)
    return env

def inputs():
    raw=blob(MANIFEST)
    if sha(raw)!='d35d4868d781bae93e4d1f0b999e4293fc19356312ab97073496feb7eb4c8343':raise ValueError('manifest identity')
    m=json.loads(gzip.decompress(raw));receipt=json.loads(blob(INTAKE))
    if not all(receipt[k] for k in ('manifest_source_verified','derivation_source_verified','count_derivation_reproduced')):raise ValueError('source replay absent')
    for p in list(m['source_pins'].values())+list(m['derivation_sources'].values())+[m['catalogue_pin']]:
        if sha(blob((p['commit'],p['path'])))!=p['sha256']:raise ValueError('derivation pin mismatch')
    if len(m['expected_slices'])!=184320:raise ValueError('coverage mismatch')
    expected={(x['layer'],x['rank'],x['expert'],x['family']):x for x in m['expected_slices']}
    if len(expected)!=184320:raise ValueError('duplicate slices')
    for l in range(40):
      for r in range(4):
       for e in range(384):
        for f in FAMILIES:
         x=expected[l,r,e,f];shape=m['shapes'][f]
         if x['word_count']!=shape['rank_shape'][0]*shape['physical_words_per_row']:raise ValueError('count mismatch')
    return m

class MetadataField:
    def __init__(self,q_pairs,regions=128,npairs=8192):
        self.np=npairs;self.r=regions;self.fill=np.zeros(npairs,dtype=np.int64);self.bf=np.zeros(npairs,dtype=bool)
        self.allowed=[];base,extra=divmod(q_pairs,regions)
        for reg in range(regions):self.allowed.append(np.arange(reg*(npairs//regions),reg*(npairs//regions)+base+(reg<extra)))
    def region_pairs(self,reg):return self.allowed[reg]

def templates(m,q_pairs):
    funcs=['npow2','model_split','segments','unit_range','unit_halves','seg_words','segment_order','element_order','family','seg_units']
    env=source_functions(blob(SEG),funcs,dict(math=math,CHUNK_EL=256,IL=8))
    S=types.SimpleNamespace(**{k:env[k] for k in funcs})
    place=source_functions(blob(PLACE),['_place'],dict(np=np,S=S,Field=MetadataField,Mat=object))['_place']
    templates={};stride={}
    for f in FAMILIES:
        rows,K=m['shapes'][f]['rank_shape'];field=MetadataField(q_pairs)
        mat=types.SimpleNamespace(rows=rows,K=K,fmt='fp4',name=f)
        segs,info,_=place(field,[mat]);by_pair={}
        for sg in segs:by_pair.setdefault(sg['pair'],[]).append(sg)
        pairmaps=[];round_units={};round_demand={};max_segments=0
        for pair,ps in sorted(by_pair.items()):
            order=S.element_order(ps);max_segments=max(max_segments,len(ps))
            if len(ps)>8:raise ValueError('descriptor segment slots exceed8')
            records=[]
            for si,u,b,h in order:
                sg=ps[si];first,last=S.unit_range('fp4',sg['e0'],sg['elems']);q=(u-first)//8
                round_units.setdefault((q,b),set()).add(u)
                key=(q,b,pair);round_demand[key]=round_demand.get(key,0)+1
                records.append([si,u,b,h])
            count=len(order)
            if count%2:raise ValueError('PP template alignment changed')
            stride[pair]=stride.get(pair,0)+count
            pairmaps.append(dict(pair=pair,segments=[dict(row=s['row'],segment=s['seg'],first_K=s['e0'],K_elements=s['elems'],segments_per_row=s['nseg']) for s in ps],word_order=records,logical_words_per_mate=count))
        demand=max(round_demand.values())
        if demand>16:raise ValueError('chain register capacity exceeded')
        rounds=[]
        for q,b in sorted(round_units):
            beats=len(round_units[q,b]);dmax=max(v for (qq,bb,p),v in round_demand.items() if (qq,bb)==(q,b))
            rounds.append(dict(subblock=q,block=b,input_512bit_beats=beats,cycles=max(8,beats,dmax)))
        replay_words=sum(p['logical_words_per_mate']*2 for p in pairmaps)
        if replay_words!=next(x['word_count'] for x in m['expected_slices'] if (x['layer'],x['rank'],x['expert'],x['family'])==(0,0,0,f)):
            raise ValueError('template word count differs from actual manifest')
        templates[f]=dict(rank_rows=rows,K=K,pairs=pairmaps,rounds=rounds,stream_issue_cycles=sum(x['cycles'] for x in rounds),maximum_segments_per_pair=max_segments,maximum_words_per_round=demand,physical_word_count=replay_words)
    return templates,stride

def assignments(m,templates,stride,depth=8192):
    cap=min(depth//n for n in stride.values())
    if cap<1:raise ValueError('whole triplet cannot fit')
    owners=[]
    for i in range(40*384):
        stage,slot=divmod(i,cap);l,e=divmod(i,384)
        owners.append(dict(layer=l,expert=e,stage=stage,slot=slot))
    stages=[]
    for stage in range(owners[-1]['stage']+1):
        count=min(cap,len(owners)-stage*cap)
        stages.append(dict(stage=stage,experts=count,expert_phase_entries=3*count,required_expert_phase_bits=(3*count-1).bit_length(),maximum_logical_bank_fill=count*max(stride.values()),physical_macros_touched=4*len(stride),expert_words_all_four_ranks=count*sum(t['physical_word_count'] for t in templates.values())*4))
    return owners,stages,cap

def lookup(candidate,layer,rank,expert,family):
    """Exact PP rows for one slice, compact template expansion; no payload read."""
    if not (type(rank) is int and 0<=rank<4):raise ValueError('rank outsideTP4')
    if not (type(layer) is int and 0<=layer<40 and type(expert) is int and 0<=expert<384 and family in FAMILIES):raise ValueError('slice outside manifest')
    owner=candidate['owners'][layer*384+expert]
    if owner['layer']!=layer or owner['expert']!=expert:raise ValueError('owner mismatch')
    templates=candidate['templates'];stride={int(k):v for k,v in candidate['pair_stride'].items()}
    earlier={}
    for f in FAMILIES[:FAMILIES.index(family)]:
        for p in templates[f]['pairs']:earlier[p['pair']]=earlier.get(p['pair'],0)+p['logical_words_per_mate']
    rows=[]
    for p in templates[family]['pairs']:
        pair=p['pair'];base=owner['slot']*stride[pair]+earlier.get(pair,0)
        for address,(si,u,b,h) in enumerate(p['word_order'],base):
            sg=p['segments'][si]
            for mate in (0,1):
                rows.append(dict(stage=owner['stage'],rank=rank,pair=pair,mate=mate,parity=address%2,physical_row=address//2,row_index=2*sg['row']+mate,segment_index=sg['segment'],first_K_element=sg['first_K'],K_elements=sg['K_elements'],unit=u,block=b,half=h))
    return rows

def price_hop(payload_bits, bits_per_replica_source_cycle, replicas, hop_count,
              registered_route_ticks_per_hop, forward_CDC_ticks, consumer_done_tick,
              reverse_credit_ticks):
    """Conservative whole-packet store/forward; source3 ticks, credit until done.

    Units explicit: per-replica capacity times replicas is aggregate bits/source
    edge. No independent beat-size input can bypass serialization. All latencies
    are supplied contracts on the common3.6GHz integer-tick timeline.
    """
    for x in (payload_bits,bits_per_replica_source_cycle,replicas,hop_count):
        if type(x) is not int or x<=0:raise ValueError('missing positive hop capacity/extent contract')
    for x in (registered_route_ticks_per_hop,forward_CDC_ticks,consumer_done_tick,reverse_credit_ticks):
        if type(x) is not int or x<0:raise ValueError('missing hop latency/consumer contract')
    aggregate=bits_per_replica_source_cycle*replicas
    cycles=(payload_bits+aggregate-1)//aggregate
    arrival=hop_count*(cycles*3+registered_route_ticks_per_hop)+forward_CDC_ticks
    if consumer_done_tick<arrival:raise ValueError('consumer done precedes actual serialized arrival')
    return dict(aggregate_bits_per_source_cycle=aggregate,serialization_source_cycles_per_hop=cycles,
        arrival_tick=arrival,packet_credit_release_tick=consumer_done_tick+reverse_credit_ticks,
        packet_credit_hold_ticks=consumer_done_tick+reverse_credit_ticks,
        scope='Provided service contracts only; full packet retained until serialization/CDC/consumerdone/reversecredit. No actual mapping costs bound.')

def build():
    m=inputs();area=json.loads(blob(AREA));old=area['inherited_baseline'];q=old['maximum_q_pairs_per_die']
    t,stride=templates(m,q);owners,stages,cap=assignments(m,t,stride)
    per_expert=sum(x['stream_issue_cycles'] for x in t.values())
    bounds=[]
    for layer in range(40):
        used=sorted({o['stage'] for o in owners if o['layer']==layer});hub=used[0]
        bounds.append(dict(layer=layer,candidate_hub_anchor=hub,expert_stages=used,furthest_linear_stage_distance=max(used)-hub,dispatch_per_selected_remote_rank_minimum_BF16_activation_bits=m['shapes']['w1']['rank_shape'][1]*16,return_per_selected_remote_rank_minimum_BF16_output_bits=m['shapes']['w2']['rank_shape'][0]*16,selected_experts=None,finite_hop_cycles=None,boundary_bits_per_replica_source_cycle=None,replicas=None,aggregate_boundary_bits_per_source_cycle=None,packet_credit_release='Only actual serialization + priced CDC + consumer acceptance/completion; no beat/port mismatch calendar credit'))
    pins={p:dict(commit=c,sha256=sha(blob((c,p)))) for c,p in (MANIFEST,INTAKE,SEG,PLACE,AREA,GEOM,RTL)}
    return dict(schema='opentallas.w17.integer-expert-residency-candidate.v1',source_pins=pins,status='EXPERT_ONLY_INTEGER_CANDIDATE_FULL_PRODUCT_BLOCKED',geometry_reconciliation=dict(logical_mates_per_pair=2,logical_words_per_mate=8192,physical_parities_per_mate=2,physical_rows_per_parity=4096,physical_bits_per_word=274,capacity_bits_per_pair=2*8192*274,physical_capacity_bits_per_pair=4*4096*274,logical_to_physical='mate unchanged; parity=logical_address%2; row=logical_address//2',w10_baseline_model_macros_per_pair=4,w10_baseline_model_macro_area_um2='4*7881.4',cons_need_area_formula='2*pairs*CONS_MACRO_MM2*(149.6/142.4) + nq*(fq-2*CONS_MACRO_MM2) + nb*(fb-2*CONS_MACRO_MM2)',meaning='cons_need subtracts two baseline8192 logical-macro footprints then adds equivalent capacity at4096 density; not two physical4096 banks/pair and not doubled resident capacity',actual_q_PP_strip_footprint_reconciled=False,historical_3749_q_fit_transferred=False),geometry=dict(NP=8192,return_regions=128,q_pairs=q,reserved_BF16_pairs=old['maximum_pairs_per_die']-q,physical_words_per_parity_macro=4096,logical_depth_per_mate=8192,physical_macros_per_pair=4,q_mask='region first29/30 pairs (37 regions have30); BF16 reserve next8 pairs/region; other tree slots inactive',scope='Historical model pair count + proposed128-region field; NOT actual3109 capacity or physical qualification'),policy='Pinned _place at empty q-only metadata field separately per family; freeze exact element_order template, append whole expert triplets stage/rank. Not fill-awareLPT replay at every resident phase; proposed deterministic allocator.',templates=t,pair_stride=stride,owners=owners,stages=stages,experts_per_stage_capacity=cap,expert_only_stage_count=len(stages),expected_slices=184320,physical_payload_word_totals=m['physical_payload_word_totals'],PP_alignment_gap_words=0,descriptor=dict(cfg_words_per_pair_phase=25,cfg_bits_per_word=48,expert_phase_count_per_rank=46080,phase_bits_current_L0=6,current_64_entry_phase_capacity_fails=True,maximum_stage_expert_entries=max(s['expert_phase_entries'] for s in stages),dense_image_bytes_per_rank=sum(s['expert_phase_entries']*old['maximum_pairs_per_die']*25*48//8 for s in stages),allocated_power_of_two_dense_image_bytes_per_rank=sum((1<<s['required_expert_phase_bits'])*old['maximum_pairs_per_die']*25*48//8 for s in stages),cfg_bits_per_full_pair_per_phase=25*48,config_load_bits_per_full_stage_phase=old['maximum_pairs_per_die']*25*48,config_service_bits_per_cycle=None,config_load_cycle_formula='ceil(active_pairs*25*48 / aggregate_config_bits_per_cycle), plus lookup/CDC/wake completion; port contract unbound',resident_key_bits=17,global_key_not_local_phase=True,compact_lookup_hardware_cycles=None,config_reload_cycles=None,area_mm2=None),port_quantities=dict(fp4_Macs_per_issued_pair_cycle=128,logical_ROM_bytes_per_pair_issue_cycle='68.5',physical_ROM_ports_per_pair=4,physical_bytes_per_port_per_two_cycle_read='34.25',activation_spine_payload_bits_per_source_cycle=512,activation_spine_exponent_bits_per_source_cycle=20,cfg_bits_per_pair_phase=1200,return_bytes_per_pair_issue_cycle=8,boundary_routing_tracks=None,replica_mux_demux_area_mm2=None,scope='Existing NB2/FAST/PP interface quantities; multicast/return/hop/descriptor scheduling and area not closed'),hop_cost_equation='For each hop: ceil(payload_bits/(bits_per_replica_source_cycle*replicas))*3 common3600MHz ticks + registered_route_ticks; then forwardCDC, actual consumerdone, reversecredit. Missing service contracts fail closed; no arbitrary beat width.',phase_costs=dict(per_family_stream_issue_cycles={f:t[f]['stream_issue_cycles'] for f in FAMILIES},one_selected_expert_stream_issue_cycles=per_expert,scope='Conservative one expert at a time FAST LAT8 stream issue only, no sharedexpert or finite routing/reduction/SU/norm/descriptor cost credit',connected_token_cycles=None),layer_hop_requirements=bounds,failures=['Logical8192-to-physical4096 parity capacity reconciled; historical3749 q footprint/strip subtraction and PP mux/capture/ports/clock area transfer still UNPROVEN','Historical fullmapped BF16 element area exceeds unchanged slot; no physical fit transfer','Dense/HC/constants not assigned; reserved BF16 slots do not prove total shared-bank fit','128-region q-only template is proposed product geometry; full profile/return tree/RF ports unqualified','PHW6 cannot address the resident expert phase catalogue; descriptor area/ports/load and lookup latency unpriced','Actual activation formats/framing/routes/credits/CDC/hub/KV owners and selectedexpert gather joins unbound','No complete tensor payload hashes, executable image or full-token exactness'],top_build_ready=False,physical_admission=False,adopt=False,full_token_rate=None)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();r=build();a.out.mkdir(parents=True,exist_ok=True)
    packed=gzip.compress(json.dumps(r,separators=(',',':'),sort_keys=True).encode(),mtime=0);(a.out/'candidate.json.gz').write_bytes(packed)
    summary={k:v for k,v in r.items() if k not in ('templates','owners','pair_stride')};summary['candidate_sha256']=sha(packed)
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
