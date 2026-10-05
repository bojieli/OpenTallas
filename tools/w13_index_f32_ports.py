"""Source-defined ordinary index consumer graph and finite ports; not runtime ticks."""
import ast,hashlib,json,subprocess,types
from collections import Counter
from pathlib import Path
REV='bb38a691e'
PINS={}

def source(path):
    b=subprocess.check_output(['git','show',REV+':tools/'+path+'.py']);PINS['tools/'+path+'.py']={'source_git':REV,'sha256':hashlib.sha256(b).hexdigest()};return b.decode()

def functions(path,names,env):
    tree=ast.parse(source(path));nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),path,'exec'),env)
    return types.SimpleNamespace(**{n:env[n] for n in names})

def programs():
    k=functions('w19_index32_integer_kernel',['ins','branch','program'],{})
    l=functions('w19_gpu_compare_lowering',['op','compare'],{})
    simd=functions('w19_gpu_simd_contract',['instruction'],{})
    c=functions('w19_gpu_norm_calendar',['op','bf16_round'],{'instruction':simd.instruction})
    x=functions('deepseek_hbm_complete_index',['decode_program','reduce_program'],{'K':k,'L':l,'C':c})
    source('deepseek_hbm_complete_executor');source('w19_hbm_tp96_isa')
    return {'decode32':x.decode_program(),'integer_score32':k.program(),'reduce32':x.reduce_program()}


def graph(program,stage):
    rows=[];counts=Counter();unknown=Counter();reads=0;writes=0
    def walk(p,env,controls):
        nonlocal reads,writes
        env={k:set(v) for k,v in env.items()}
        for ins in p:
            op=ins['op'];eid=len(rows);src=ins['src'];deps=set(controls);oper=[]
            for s in src:
                if op=='LOAD':oper.append({'kind':'shared','name':s});continue
                if isinstance(s,int) or str(s).startswith('@'):oper.append({'kind':'immediate','value':s});continue
                reaching=env.get(s)
                if reaching is None:
                    if s not in ('eq','ek'):raise ValueError('uninitialized '+s)
                    oper.append({'kind':'phase_input_register','name':s,'producer_gate':'prior decode RF/shared completion required'})
                else:
                    deps.update(reaching);oper.append({'kind':'register','name':s,'producer_events':sorted(reaching)})
            nr=sum(o['kind'] in ('register','phase_input_register') for o in oper)
            if nr>2:raise ValueError('RF2R violation')
            branch=op.startswith('B');store=op=='STORE'
            # Canonical ADD/MUL/compare + RF import, SHFL. All other variants unresolved.
            latency=9 if op in ('FADD','FMUL','FCMP_GT','FCMP_LT','IADD') else 7 if op=='SHFL' else None
            if latency is None:unknown[op]+=1
            row={'event_id':eid,'op':op,'dst':ins.get('dst'),'operands':oper,'dependencies':sorted(deps),'control_path':list(controls),
                 'RF_reads_per_lane':nr,'RF_read_bits_warp':nr*1024,'RF_write_ports':int(not branch and not store),
                 'RF_write_bits_warp':1024 if not branch and not store else 0,
                 'physical_RF_write_copy_count':2 if not branch and not store else 0,
                 'canonical_serial_latency_candidate':latency,'launch_tick':None,'finish_tick':None,
                 'legacy_latency_field_rejected':ins.get('latency'),'shared_address_binding':('query_or_key term-major: block/term/warp phase parameters required' if op=='LOAD' else 'unit term-major overwrite only after both source LOADs and max-scan complete' if store and str(ins.get('dst','')).startswith('unit') else 'final score destination and phase lease required' if store else None),'predicate_stride':ins.get('predicate_stride')}
            reads+=nr*1024;writes+=row['RF_write_bits_warp'];counts[op]+=1;rows.append(row)
            if branch:
                a=walk(ins['yes'],env,controls+[eid]);b=walk(ins['no'],env,controls+[eid])
                env={v:a.get(v,set())|b.get(v,set()) for v in set(a)|set(b)}
            elif not store:env[ins['dst']]={eid}
        return env
    walk(program,{},[])
    # Conservative linear storage envelope of all mutually exclusive branch nodes;
    # never sum this into an actual runtime instruction calendar.
    last={r['event_id']:r['event_id'] for r in rows if r['RF_write_ports']}
    for r in rows:
        for o in r['operands']:
            for d in o.get('producer_events',[]):last[d]=max(last.get(d,d),r['event_id'])
    live={};free=set(range(32));peak=0
    for r in rows:
        for d in list(live):
            if last[d]<r['event_id']:free.add(live.pop(d))
        if r['RF_write_ports']:
            if not free:raise ValueError('finite register envelope exceeded')
            reg=min(free);free.remove(reg);live[r['event_id']]=reg;r['RF_destination_register_candidate']=reg
        for o in r['operands']:
            if 'producer_events' in o:o['RF_source_register_candidates']=[rows[d]['RF_destination_register_candidate'] for d in o['producer_events']]
        peak=max(peak,len(live))
    return {'stage':stage,'events':rows,'static_all_branch_opcode_counts':dict(counts),'static_all_branch_RF_read_bits':reads,'static_all_branch_RF_write_bits':writes,
            'peak_registers_conservative':peak,'unknown_opcode_latency_variants':dict(unknown),'actual_runtime_path_bound':False,'cycles':None}


def staging():
    # All-F32 tile address equations: exact bit loads, ordinary shared transpose.
    rows=[]
    for term in range(128):
        for warp in range(2):
            row0=warp*32;word=4096+term*64+row0
            rows.append({'op':'shared_scatter_store32','term':term,'row0':row0,'word_addresses':[word+j for j in range(32)],
                'banks':[(word+j)%32 for j in range(32)],'dependencies':['matching sector return payload bits','tag/epoch/format/length valid','RF writeback visible'],
                'RF_read_bits':1024,'shared_write_bytes':128,'launch_tick':None,'visible_tick':None})
    return {'events':rows,'shared_peak_bytes':57472,'base_transport_allocation_bytes':55936,'additional_decode_scale_region':[55936,57472],'query_exponent_region':[55936,56448],'key_exponent_region':[56448,57472],'intermediate_score_storage_reuse_proven':False,'bank_count':32,'bank_word_bytes':4,'bank_ports':'1R1W candidate; same-address R/W requires defined ordering',
      'decode_load_word':'4096+(block*32+term)*64+tile_row;32 adjacent rows =>32 unique banks',
      'score_key_load':'one row/term broadcast32 lanes; one4B bank access only if measured broadcast network admitted',
      'score_query_load':'term*32+head;32 unique banks',
      'transpose_scratch':'word12800+row*33+col;32unique banks for either dimension',
      'ACK_calendar':[{'event':e,'tick':None} for e in ['payload_write_accept','payload_WR_visible','descriptor_WR_visible','reverse_CDC_ack','generation_read_lease','consumer_RF_writeback','score_consumer_done','credit_return']],
      'return_slot_count':16,'return_slot_bytes':32,'physical_provider_bound':False}


def receipt():
    p=programs();out={k:graph(v,k) for k,v in p.items()}
    return {'schema':'w13.index-f32-source-ports.v1','source_pins':PINS,'programs':out,'staging':staging(),
       'SM_geometry':{'SIMT_lanes':128,'warp_lanes':32,'resident_warps':32,'partitions':4,'warp_slots_per_partition':8,'registers_per_thread':32,'RF_ports':'2R1W logical; writes to both physical read copies','RF_depth':'warp_slot*32+register;depth_bank=depth//128,row=depth%128','RF_lane_group':'partition*4+lane//8;subword=lane%8','total_score_liveness_with_query_and_cross_phase_state':None},
       'finite_tile_phase_replication':{'query_decode32_warps':4,'key_decode32_warps':8,'integer_score32_warps':256,'reduce32_warps':64,'separate_head_weight_and_block_accumulate_calendar':None},
       'consumer_domain':'existing decode rejects nonfinite or non-BF16 input; allF32 transport does NOT repair this source consumer domain',
       'baseline_066_preserved':True,'packed_codec_dependency':False,'source_callbacks_to_runtime_path':None,
       'clock_targets_GHz':{'serial':0.9,'fabric':1.2},'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,
       'physical_admission':'FAIL_CLOSED','whole_token_cycles':None,'rate_credit':0,'hardware_launch':False}

if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(receipt(),indent=2)+'\n')
