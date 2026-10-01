"""Actual encoded491PC local immutable coefficient placement, no checkpoint reads."""
import argparse,ast,gzip,hashlib,json,math,re,struct,subprocess,types
from collections import defaultdict
import w17_crom_finite_prefetch as C

def digest(b):return hashlib.sha256(b).hexdigest()
def ranges(values):
    out=[]
    for v in sorted(values):
        if out and out[-1][1]==v:out[-1][1]=v+1
        else:out.append([v,v+1])
    return out

def build(readonly_banks=6):
    pins={}
    def raw(name,ref,path,gz=False):
        b=subprocess.check_output(['git','show',ref+':'+path]);pins[name]=dict(commit=ref,path=path,sha256=digest(b));return gzip.decompress(b) if gz else b
    wire=raw('SS_wire_model','541a1d2f','tools/uarch_model.py').decode()
    fp=json.loads(raw('SU_geometry','541a1d2f','results/floorplan/v41_pack_refit_w10_interim.json'))
    region=next(z for z in fp['soft_regions'] if z[0]=='HUB_SU_VECTOR')
    reach=float(re.search(r'^WIRE_REACH_SS_UM\s*=\s*([0-9.]+)',wire,re.M)[1])
    route=math.ceil((region[4]+region[5])/reach)
    assert reach==504 and route==17
    demand=json.loads(raw('demand',*C.SOURCES['demand'],True))
    audit=json.loads(raw('program',*C.SOURCES['encoded_audit']))
    isa=types.ModuleType('isa');isa.__file__=C.__file__;exec(compile(raw('ISA',*C.SOURCES['ISA']),'<pinned>','exec'),isa.__dict__)
    source=raw('emit_source',*C.SOURCES['emit_source'])
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('clog','batches')]
    env={'I':isa};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<batch>','exec'),env)
    enc=raw('rank0',C.PIN,C.PREFIX+'.rank0.templates.bin.gz',True)
    assert digest(enc)==audit['ranks'][0]['encoded_template_sha256']
    commands=[];unions=defaultdict(set)
    for rec in demand['ranks'][0]['records']:
        f=isa.decode(int.from_bytes(enc[rec['global_instruction']*256:(rec['global_instruction']+1)*256],'little'),full_shape=True)
        bursts=[]
        for batch in env['batches'](f):
            uses=[]
            for oi,o in enumerate(rec['operand_demands']):
                for lane,(outer,inner) in enumerate(batch):
                    a=o['base']+outer*o['outer_stride']+(inner//2 if o['half_inner'] else inner)*o['inner_stride']
                    if o['kind']=='unbound_generated':a+=508800+(20480 if rec['layer']==14 else 0)
                    uses.append((oi,lane,a));unions[rec['layer']].add(a)
            bursts.append(uses)
        assert len(bursts)==rec['emit_bursts']
        commands.append((rec,bursts))
    assert len(commands)==491 and len(unions)==41
    assert all(rank['records']==demand['ranks'][0]['records'] for rank in demand['ranks'])
    independent=json.loads(raw('independent_union','8e28902ff','results/uarch/w11_stage_crom_union_20261001/read_union.json.gz',True))
    for rank in independent['ranks']:
        for stage in rank['stages']:
            values=unions[stage['layer']]
            assert stage['unique_words']==len(values)
            assert stage['global_sorted_addressSHA']==digest(b''.join(struct.pack('<I',a) for a in sorted(values)))
    for rank in audit['ranks'][1:]:
        binary=raw('encoded_rank'+str(rank['rank']),C.PIN,C.PREFIX+f".rank{rank['rank']}.templates.bin.gz",True)
        assert digest(binary)==rank['encoded_template_sha256']
    maximum=max(len(v) for v in unions.values());storage_minimum=math.ceil(maximum/(4096*3))
    banks=readonly_banks
    if banks<storage_minimum: raise ValueError('undersized regular bank element')
    ordered={k:sorted(v) for k,v in unions.items()}
    maps={k:{a:i for i,a in enumerate(v)} for k,v in ordered.items()}
    stages={}
    request_hash={k:hashlib.sha256() for k in unions}
    fill_hash={k:hashlib.sha256() for k in unions}
    for k,v in unions.items():
        stages[k]=dict(layer=k,unique_words=len(v),global_ranges=ranges(v),
            global_address_SHA256=digest(b''.join(struct.pack('<I',a) for a in sorted(v))),
            mapping='localindex = ordinal in ascending unique globaladdress; bank=(localindex//3)%regularbanks,row=(localindex//3)//regularbanks,slot=localindex%3',
            invalid_L1_local_ranges=ranges(maps[k][a] for a in v if 508800<=a<529280),
            commands=[],request_words=0,fill_words=0,peak_landing_coefficients=0,
            full_immutable_image_valid=not any(508800<=a<529280 for a in v))
    coverage=hashlib.sha256();uses_total=0
    for rec,bursts in commands:
        stage=stages[rec['layer']];mapping=maps[rec['layer']]
        waves_all=[];count=0
        for uses in bursts:
            local={mapping[a] for _,_,a in uses};waves=C.bank_waves(local,ports=banks)
            count+=len(local)
            for wave in waves:
                landing={a:i for i,a in enumerate(sorted(wave))}
                assert len(landing)<=3*banks and max(landing.values(),default=0)<256
                targets={(oi,lane//16) for oi,lane,a in uses if mapping[a] in wave}
                req=0
                for container in sorted({a//3 for a in wave}):
                    bank=container%banks;row=container//banks
                    mask=sum(1<<(a%3) for a in wave if a//3==container)
                    req|=(row|(1<<12)|(mask<<13))<<(16*bank)
                decoded=set()
                for bank in range(banks):
                    field=(req>>(16*bank))&65535
                    if field&(1<<12):
                        row=field&4095
                        for sl in range(3):
                            if field&(1<<(13+sl)): decoded.add((row*banks+bank)*3+sl)
                assert decoded==wave
                request_hash[rec['layer']].update(req.to_bytes(35,'little'))
                for oi,group in sorted(targets):
                    entries={lane%16:landing[mapping[a]] for oo,lane,a in uses if oo==oi and lane//16==group and mapping[a] in wave}
                    mask=sum(1<<lane for lane in entries)
                    fill=sum(sel<<(8*lane) for lane,sel in entries.items())|(mask<<128)|(oi<<144)|(group<<145)
                    assert fill>>151==0
                    fill_hash[rec['layer']].update(fill.to_bytes(35,'little'))
                    for lane,sel in entries.items():
                        decodedsel=(fill>>(lane*8))&255
                        assert decodedsel==sel and sorted(decoded)[decodedsel]==sorted(wave)[sel]

                stage['peak_landing_coefficients']=max(stage['peak_landing_coefficients'],len(landing))
                stage['request_words']+=math.ceil(banks*16/274)
                stage['fill_words']+=len(targets)
                for oi,lane,a in uses:
                    if mapping[a] in wave:
                        # Scalar route proof is exact address identity, not arithmetic execution.
                        back=ordered[rec['layer']][mapping[a]]
                        assert back==a
                        coverage.update(struct.pack('<IIIII',rec['global_instruction'],oi,lane,a,mapping[a]));uses_total+=1
                waves_all.append((len(wave),len(targets)))
        assert count==rec['one_port_cycles_within_emit_dedup']
        service=[]
        for credit in (2,4,128):
            ticks=sum(12+C.credit_calendar(n,credit,route=route)['last_cache_write_and_reverse_credit_tick'] for _,n in waves_all)
            ticks=max(ticks,math.ceil(count/16)*3)
            service.append(dict(credits=credit,finite_fill_and_reverse_credit_ticks=ticks,actual_absolute_PC_release=None))
        stage['commands'].append(dict(PC=rec['global_instruction'],coefficient_reads=count,
            emit_bursts=len(bursts),bank_read_waves=len(waves_all),fill_packets=sum(n for _,n in waves_all),
            finite_services=service,selected16port_floor_fast_cycles=math.ceil(count/16)))
    assert sum(c['coefficient_reads'] for s in stages.values() for c in s['commands'])==549760
    for stage in stages.values():
        stage['request_catalog_word_SHA256']=request_hash[stage['layer']].hexdigest()
        stage['fill_catalog_word_SHA256']=fill_hash[stage['layer']].hexdigest()
        stage['request_catalog_macros']=math.ceil(stage['request_words']/4096)
        stage['fill_catalog_macros']=math.ceil(stage['fill_words']/4096)
    reqmax=max(s['request_catalog_macros'] for s in stages.values());fillmax=max(s['fill_catalog_macros'] for s in stages.values())
    catalog=reqmax+fillmax
    l14=raw('L14','60545ff45','results/uarch/w11_engram_product_source_20261001/L14.product.crom64-logical-slice.bin.gz',True)
    assert digest(l14)=='f2297940486c2604a7a4baf8887ed319c264f77cb10ccc3f164c16e01182f377'
    image_receipt=json.loads(raw('images','70f73928f','results/uarch/w11_dsrom_crom_writer_20261001/verification.json'))
    rankvalues=[]
    for rank in range(4):
        image=raw(f'image{rank}','70f73928f',f'results/uarch/w11_dsrom_crom_writer_20261001/rank{rank}.crom.bin.gz',True)
        assert digest(image)==image_receipt['rank_images'][rank]['image_sha256']
        homes=[]
        for k in sorted(stages,key=lambda a:40 if a=='head' else a):
            values=bytearray();valid=bytearray()
            for a in sorted(unions[k]):
                if a<508800:v=image[a*8:a*8+8];ok=1
                elif a>=529280:v=l14[(a-529280)*8:(a-529280+1)*8];ok=1
                else:v=bytes(8);ok=0
                assert len(v)==8
                values.extend(v);valid.append(ok)
            local_used=len(valid)
            physical=[bytearray(4096*3*8) for _ in range(banks)]
            physical_valid=[bytearray(4096*3) for _ in range(banks)]
            pad=banks*4096*3-len(valid)
            values.extend(bytes(pad*8));valid.extend(bytes([1])*pad)
            for a in range(banks*4096*3):
                bank=(a//3)%banks;offset=((a//3)//banks)*3+a%3
                physical[bank][offset*8:offset*8+8]=values[a*8:a*8+8]
                physical_valid[bank][offset]=valid[a]
            reconstructed=hashlib.sha256()
            for a in range(local_used):
                bank=(a//3)%banks;offset=((a//3)//banks)*3+a%3
                word=physical[bank][offset*8:offset*8+8]
                assert word==values[a*8:a*8+8] and physical_valid[bank][offset]==valid[a]
                reconstructed.update(word)
            homes.append(dict(layer=k,physical_bank_payload_SHA256=[digest(b) for b in physical],
                physical_bank_validity_SHA256=[digest(b) for b in physical_valid],
                used_words_roundtrip_SHA256=reconstructed.hexdigest(),logical_words=len(unions[k]),padded_words=banks*4096*3,
                diagnostic_placeholder_payload_SHA256=digest(values),validity_SHA256=digest(valid),
                source_invalid_words=valid.count(0),complete_image_SHA256=digest(values) if 0 not in valid else None))
        rankvalues.append(dict(rank=rank,homes=homes))
    return dict(schema='opentallas.CROM-stage-local.v1',source_pins=pins,
        SS_route_basis=dict(reach_um=reach,envelope_um=region[4]+region[5],
            stages_each_direction=route,historical11_qualified=False,actual1152bit_bus_capacity_and_reach_bound=False),
        regular_element=dict(stage_count_per_rank=41,reference_rank_count=4,candidate_home_count=164,
            storage_minimum_banks=storage_minimum,nominal_bank_FP32_supply_per_fast_cycle=3*banks,
            maximum_stage_words=maximum,max_stage_ids=[k for k,v in unions.items() if len(v)==maximum],
            readonly_banks_per_home=banks,capacity_words_per_home=banks*4096*3,
            regular_request_catalog_banks=reqmax,regular_fill_catalog_banks=fillmax,total_macros_per_home=banks+catalog,
            read_port_per_bank=1,selected_FP32_outputs=16,landing_capacity_coefficients=3*banks,
            gamma_cache5coeff_per1024lane_perfamily=True,
            prior_45readonly_plus16catalog_not_retained_in_this_new_candidate=True,
            actual_home_replica_ownership_still_unbound=True),
        stages=[stages[k] for k in sorted(stages,key=lambda a:40 if a=='head' else a)],rank_values=rankvalues,
        exact_address_route=dict(all491commands=True,logical_coefficient_reads=549760,
            fill_destination_checks=uses_total,route_mapping_digest=coverage.hexdigest(),
            ISA_arithmetic_and_rounding_unchanged=True,
            model_request_and_fill_catalog_bytes_roundtripped=True,
            actual_compiler_published_physical_catalog=False,
            no_global_address_truncation=True,parameter_values_from_retained_images_only=True),
        fit=dict(macro_capacity_bound=True,all_capture_control_cells_and_routes_typed=False,
            actual_SU_nonoverlap_and_placed_catalog=False,physical_admission=False),
        checkpoint_reads=0,jobs_launched=0,hardware_admission=False,full_token_cycles=None,
        initial_generator_failure=dict(error='missing pinned ISA __file__; later duplicate comma syntax caught beforecommit',preserved=True,corrected_before_commit=True))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--banks',type=int,default=6);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(a.banks),f,sort_keys=True,indent=2);f.write('\n')
