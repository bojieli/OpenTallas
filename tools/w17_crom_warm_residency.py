"""Immutable coefficient cold/warm mapping and actual lane-port obligations."""
import argparse,ast,gzip,hashlib,json,subprocess,types
from decimal import Decimal
from collections import defaultdict,Counter
import w17_crom_finite_prefetch as C

def valid_hit(expected,actual,initialized,image_valid,reset_valid,lease_valid):
    return expected==actual and bool(expected) and all(x is True for x in (initialized,image_valid,reset_valid,lease_valid))

def C_ranges(values):
    out=[]
    for a in sorted(values):
        if out and out[-1][1]==a:out[-1][1]=a+1
        else:out.append([a,a+1])
    return out

def build():
    pins={}
    def raw(n,ref,path,gz=False):
        b=subprocess.check_output(['git','show',ref+':'+path]);pins[n]=dict(commit=ref,path=path,sha256=hashlib.sha256(b).hexdigest());return gzip.decompress(b) if gz else b
    demand=json.loads(raw('demand',*C.SOURCES['demand'],True))
    isa=types.ModuleType('isa');isa.__file__=C.__file__;exec(compile(raw('ISA',*C.SOURCES['ISA']),'<ISA>','exec'),isa.__dict__)
    source=raw('emit_source',*C.SOURCES['emit_source'])
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('clog','batches')]
    env={'I':isa};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<batch>','exec'),env)
    binary=raw('rank0',C.PIN,C.PREFIX+'.rank0.templates.bin.gz',True)
    union=json.loads(raw('union','8e28902ff','results/uarch/w11_stage_crom_union_20261001/read_union.json.gz',True))
    stageinfo={s['layer']:s for s in union['ranks'][0]['stages']}
    gamma=defaultdict(lambda:defaultdict(set));product=defaultdict(set);allwords=defaultdict(set)
    uses_by_cmd=[]
    families=defaultdict(lambda:defaultdict(lambda:dict(addresses=set(),PCs=set(),kind=None)))
    for rec in demand['ranks'][0]['records']:
        f=isa.decode(int.from_bytes(binary[rec['global_instruction']*256:(rec['global_instruction']+1)*256],'little'),full_shape=True)
        bursts=[]
        for batch in env['batches'](f):
            uses=[]
            for oi,o in enumerate(rec['operand_demands']):
                tensor=str(o.get('tensor',''));isgamma=tensor=='norm.weight' or tensor.endswith(('attn_norm.weight','ffn_norm.weight'))
                for lane,(outer,inner) in enumerate(batch):
                    a=o['base']+outer*o['outer_stride']+(inner//2 if o['half_inner'] else inner)*o['inner_stride']
                    kind='gamma' if isgamma else 'other'
                    if o['kind']=='unbound_generated':a+=508800+(20480 if rec['layer']==14 else 0);kind='product';product[rec['layer']].add(a)
                    if isgamma:gamma[rec['layer']][tensor].add(a)
                    families[rec['layer']][tensor]['addresses'].add(a);families[rec['layer']][tensor]['PCs'].add(rec['global_instruction']);families[rec['layer']][tensor]['kind']=kind
                    allwords[rec['layer']].add(a);uses.append((oi,lane,a,kind,tensor))
            bursts.append(uses)
        uses_by_cmd.append((rec,bursts))
    maps={};rows={};lane_local=defaultdict(lambda:defaultdict(set))
    for layer,words in allwords.items():
        assert len(words)==stageinfo[layer]['unique_words']
        remaining=words-set().union(*gamma[layer].values())-product[layer]
        bases={family:min(v) for family,v in gamma[layer].items()}
        gm={a:(family,(a-bases[family])%1024,(a-bases[family])//1024) for family,v in gamma[layer].items() for a in v}
        other={a:('other',i%1024,i//1024) for i,a in enumerate(sorted(remaining))}
        prod={a:('product',i%1024,i//1024) for i,a in enumerate(sorted(product[layer]))}
        maps[layer]={**gm,**other,**prod};assert len(maps[layer])==len(words)
        assert len(set(maps[layer].values()))==len(words)
        rows[layer]=dict(layer=layer,gamma_words=sum(map(len,gamma[layer].values())),other_words=len(remaining),product_words=len(product[layer]),
            gamma_families=len(gamma[layer]),gamma_capacity_words=10240,other_capacity_words=4096,
            extra_persistent_product_bits=len(product[layer])*32,
            actual_other_cache_ports_per_lane=None,max_distinct_slots_per_bank_per_emit=0,
            maximum_other_fanout_per_word_per_emit=0,crosslane_other_delivery_edges=0,
            command_hits=[],image_valid=layer!=1,
            gamma_and_other_capacity_pass=sum(map(len,gamma[layer].values()))<=10240 and len(remaining)<=4096)
    hitcount=0;mappinghash=hashlib.sha256()
    for rec,bursts in uses_by_cmd:
        layer=rec['layer'];row=rows[layer];mapping=maps[layer];reads=0;max_other_words=0;max_gamma_words=0;max_product_words=0
        for uses in bursts:
            max_other_words=max(max_other_words,len({a for _,_,a,k,_ in uses if k=='other'}))
            max_gamma_words=max(max_gamma_words,len({a for _,_,a,k,_ in uses if k=='gamma'}))
            max_product_words=max(max_product_words,len({a for _,_,a,k,_ in uses if k=='product'}))
            slots=defaultdict(set);fanout=defaultdict(set)
            for oi,lane,a,kind,tensor in uses:
                cache,bank,slot=mapping[a]
                mappinghash.update(f'{layer}:{rec["global_instruction"]}:{oi}:{lane}:{a}:{cache}:{bank}:{slot}\n'.encode())
                slots[(cache,bank)].add(slot);reads+=1;hitcount+=1
                if kind=='other':
                    fanout[a].add(lane);lane_local[layer][lane].add(a)
                    row['crosslane_other_delivery_edges']+=int(bank!=lane)
            row['max_distinct_slots_per_bank_per_emit']=max(row['max_distinct_slots_per_bank_per_emit'],max(map(len,slots.values()),default=0))
            row['maximum_other_fanout_per_word_per_emit']=max(row['maximum_other_fanout_per_word_per_emit'],max(map(len,fanout.values()),default=0))
        row['command_hits'].append(dict(PC=rec['global_instruction'],logical_reads=reads,
            max_other_unique_words_per_emit=max_other_words,max_gamma_unique_words_per_emit=max_gamma_words,
            max_product_unique_words_per_emit=max_product_words,
            selected16_other_delivery_floor_fast_cycles_per_emit=(max_other_words+15)//16,
            actual_existing_cache_read_and_delivery_schedule_bound=False,
            misses_after_complete_source_valid_init=0 if layer!=1 else None,
            source_invalid_requests=reads if rec['global_instruction']==118 else 0))
    for layer,row in rows.items():
        replicated=sum(map(len,lane_local[layer].values()))
        maxlane=max(map(len,lane_local[layer].values()),default=0)
        row['alternative_lane_local_other_replica_words']=replicated
        row['regular_lane_local_other_depth_words']=maxlane
        row['regular_lane_local_other_capacity_words']=1024*maxlane
        row['additional_regular_other_bits_vs_existing4096']=max(0,1024*maxlane-4096)*32
        row['static_families']=[dict(family=name,cache_kind=f['kind'],unique_words=len(f['addresses']),
            global_address_ranges=C_ranges(f['addresses']),consumer_PCs=sorted(f['PCs']),
            global_address_SHA256=hashlib.sha256(b''.join(a.to_bytes(4,'little') for a in sorted(f['addresses']))).hexdigest()) for name,f in sorted(families[layer].items())]
        row['other_lane_local_map_digest']=hashlib.sha256(''.join(f'{lane}:{a}\n' for lane,values in sorted(lane_local[layer].items()) for a in sorted(values)).encode()).hexdigest()
    assert hitcount==549760 and len(rows)==41
    fp=json.loads(raw('SU_reserved_geometry','541a1d2f','results/floorplan/v41_pack_refit_w10_interim.json'))
    raw('sequential_cache_scope','3fdbeb823','results/uarch/w11_crom_gamma_interleave_20261001/verification.json')
    raw('existing_SU_read_interface','d2c28c279','rtl/hdc/v41x/ot_hdc_v41x_vec.sv')
    raw('existing_SU_lane_capture','d2c28c279','rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv')
    value_checks=[]
    l14=raw('L14_product','60545ff45','results/uarch/w11_engram_product_source_20261001/L14.product.crom64-logical-slice.bin.gz',True)
    authority=json.loads(raw('retained_image_authority','70f73928f','results/uarch/w11_dsrom_crom_writer_20261001/verification.json'))
    for rank in range(4):
        image=raw('image'+str(rank),'70f73928f',f'results/uarch/w11_dsrom_crom_writer_20261001/rank{rank}.crom.bin.gz',True)
        assert hashlib.sha256(image).hexdigest()==authority['rank_images'][rank]['image_sha256']
        checksum=hashlib.sha256();checked=0;invalid=0
        for layer,mapping in maps.items():
            cells={}
            for a,key in mapping.items():
                if 508800<=a<529280:invalid+=1;continue
                word=image[a*8:a*8+8] if a<508800 else l14[(a-529280)*8:(a-529280+1)*8]
                assert len(word)==8 and word[4:]==bytes(4)
                cells[key]=word[:4]
            for a,key in sorted(mapping.items()):
                if 508800<=a<529280:continue
                original=image[a*8:a*8+4] if a<508800 else l14[(a-529280)*8:(a-529280)*8+4]
                assert cells[key]==original;checksum.update(original);checked+=1
        assert checked==529280 and invalid==20480
        value_checks.append(dict(rank=rank,actual_retained_FP32_value_checks=checked,invalid_L1_words=invalid,
            checked_FP32_stream_SHA256=checksum.hexdigest(),all_checkpoint_and_product_CHI_bits_zero=True))
    cold_candidates=[]
    for banks in (6,9,16,45):
        path=(f'results/quality/w16_engram_initializer_20261001/stage_local{banks}_SS17.json' if banks!=45 else 'results/quality/w16_engram_initializer_20261001/stage_local45_rows_SS17.json')
        model=json.loads(raw('cold_SS17_'+str(banks),'30ee8b637',path))
        bystage={}
        for stage in model['stages']:
            if banks==45:
                ticks=sum(next(v for v in c['deliveries'] if v['credits']==128)['cold_fill_plus_credit_ticks'] for c in stage['commands'])
            else:
                ticks=sum(next(v for v in c['finite_services'] if v['credits']==128)['finite_fill_and_reverse_credit_ticks'] for c in stage['commands'])
            bystage[str(stage['layer'])]=ticks
        cold_candidates.append(dict(banks=banks,credits=128,
            declared_nooverlap_rank_serial_fill_partial_us=str(Decimal(sum(bystage.values()))/3600),
            largest_individual_home_fill_partial_us=str(Decimal(max(bystage.values()))/3600),
            actual_parallel_init_or_actual_TTFT=None,perhome_fill_ticks=bystage))
    return dict(schema='opentallas.CROM-immutable-warm-residency.v1',source_pins=pins,
        stages=[rows[k] for k in sorted(rows,key=lambda a:40 if a=='head' else a)],
        retained_value_checks=value_checks,actual491command_logical_hits=hitcount,mapping_digest=mappinghash.hexdigest(),
        cold_init=dict(SS17_cold_candidates=cold_candidates,actual_TTFT=None,
            initialization_launch_arbitration_shareddecoder_and_global_completion_unbound=True,
            per_reference_rank_unique_words=549760,only_once_per_actual_image_generation=True,
            complete_image_or_validinit_not_present=True,source_L1_invalid=True,
            minimumTTFT_requires_prefill_capture_checksum_tag_lease_and_reset_barriers=True,
            current17delivery_subtotals_not_automatically_per_token=True),
        warm_tokens=dict(immutable_content_reuse_permitted=True,
            programme_scope='main40layers+head only; optionalMTP requires matching ownimage/layout/operatorbinding',
            parameter_cache_changes_no_arithmetic_rounding_or_tree_order=True,
            actual_RTL_cache_module=None,live_L0_L20_warm_hit_credit=False,
            topology_qualified=False,cache_key=['immutable_imageSHA','source_revision','rank','stage','reset_generation','cache_layoutSHA','validfill_and_lease_owner'],
            logical_external_CROM_reads_after_complete_validinit=0,
            actual_warm_cycles=None,actual_reset_retention_and_epoch_provider=False,
            logical_hit_is_not_port_or_RTL_gain=True),
        allocation_scope='retained candidate FF reservations only; not established DUTcache',
        topology_cases=dict(
            stage_local_candidate=dict(proposed_SU_owner_count=164,proposed_stages_per_rank=41,reference_ranks=4,
                absolute_owner_keys=[dict(home_id=rank*41+stage,rank=rank,layer=stage if stage<40 else 'head') for rank in range(4) for stage in range(41)],
                each_owner_retains_only_its_own_stage=True,
                SU_core_reserved_mm2_per_home=str(Decimal(str(fp['refit']['hub_units']['stream_unit']['area_mm2']))),
                aggregate164_SU_core_reserved_mm2=str(Decimal(str(fp['refit']['hub_units']['stream_unit']['area_mm2']))*164),
                reservation_is_not_contextual_N1024_physical_qualification=True,
                actual_product_SU_instances_and_home_topology=None,
                accepted_whole_geometry_already_charges164_SU=False,
                actual_shared_decoder_arbitration_and_hops=None),
            fourrank_sequential_SU=dict(proposed_SU_count=4,per_rank_allstage_words=549760,
                retained_candidate_words=14336,allstage_word_deficit=535424,
                extra_allstage_bits_per_rank=17133568,
                existing_twofamily_cannot_retain40layers=True,
                SU_core_reserved_aggregate_mm2=str(Decimal(str(fp['refit']['hub_units']['stream_unit']['area_mm2']))*4),
                actual_global_persistent_cache_or_refill=None,fullrank_decode_routes_and_ports=None,
                live_replay_warm_credit=False)),
        generic_emit_buffers_repurposed_as_readonly_other_cache='candidate explicitrole change; cannot simultaneously use them forcoldstreaming/product refill or mutableactivation storage',
        no_clock_gating_or_power_subtraction=True,
        extra_product_words_per_Engram_home=20480,extra_product_bits_per_Engram_home=655360,
        product_20entry_lane_select_MUX2_bits=1024*19*32,
        extra_product_reference_home_count=8,actual_physical_replicas_not_automatically_four=True,
        existing_hardware_constructive_failures=['candidate genericcompactcache addresscapacity alone does not connect physicalbanks to consumerlanes',
            'directlane-localother regulardepth17/19 exceeds candidate4wordcapacity',
            'Engram20slotpersistentproduct not incandidategamma/genericallocation',
            'noactualwarmcachetag/reset/init/lease readproviderinstantiated; fullcontextslotFAIL preserved'],
        required_read_interface=dict(SUN_candidate=1024,physical_streams=4,word_bits=32,
            existing_rd_q_bits_per_serial_emit=131072,unusedVMstreams_not_elided=True,
            newcache_read_network_port_and_contextual_SSFF_bound=False),
        remaining=['actual init/valid/reset/lease publication','other coefficients bankports/fanout/permutation or extra lane-local replicas',
            'persistent Engram product extra storage/ports','actualcontextSSFF andRTLgain','L1provenance'],
        hardware_admission=False,full_token_cycles=None,jobs_launched=0,checkpoint_reads=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
