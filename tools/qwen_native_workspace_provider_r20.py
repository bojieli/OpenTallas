"""Bind final native workspace and separately reserve older calendar arena; no RTL credit."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
D=Path(__file__).resolve().parents[1]/'results/uarch/qwen_native_workspace_provider_r20_20261002'

def inputs():
    pins=json.loads((D/'input_manifest.json').read_bytes());result=[]
    for name in ['native_workspace_metadata.json.gz','calendar_workspace_metadata.json.gz']:
        raw=(D/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pins['files'][name]:raise ValueError('input digest mismatch')
        result.append(json.loads(gzip.decompress(raw)))
    return result

def aligned(n):return (n+511)//512*512

def physical(byte):
    if not 0<=byte<81000000000:raise ValueError('system address aperture')
    local=(byte//512)*128+byte%128;sector=local//32
    if sector>=2**31:raise ValueError('local sector aperture')
    row=sector>>15
    return {'global_byte':byte,'stack':byte//128%4,'local_sector31':sector,'byte_in_sector':local%32,
        'system_sector34':byte//32,'PC':((sector>>2)^(sector>>7)^(sector>>12))&31,
        'bank':((((sector>>12)^(row>>2))&7)<<2)|((sector^row)&3),'row':row}

def prefix_per_stack(end,stack):return end//512*128+min(128,max(0,end%512-stack*128))

def packet(session,pc,object_index,byte_offset,base,client):
    """Explicit windowing; retain full epoch, address and16-bit caller identity."""
    if byte_offset<0 or byte_offset%32 or object_index<0 or client not in (9,10,11):raise ValueError('workspace sector identity')
    sector=byte_offset//32;window=sector//(1<<26);within=sector%(1<<26)
    caller=(object_index+window)*32+within%32
    if not 0<=session<2**64 or not 0<=pc<2048 or not 0<=caller<65536:raise ValueError('identity capacity')
    p=physical(base+byte_offset)
    return {'producer':session,'transport':pc<<21|within//32,'caller':caller,'client':client,
        'stack':p['stack'],'sector':p['local_sector31'],'IRSslot':'actual opcode acceptance','IRSserial':'actual32-bit accepted generation',
        'physical_tag':'actual allocator output retained through validated grant'}

def model():
    native,calendar=inputs();ops=native['operations'];assert len(ops)==1737
    target=calendar['manifest']['targets']['Qwen'];values=calendar['manifest']['endpoint_cycles']['values']
    assert all(v>0 for v in values.values())
    consumed=calendar['manifest']['source_sha256']['results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_native.json.gz']
    current=consumed==native['source_SHA256'];rank_records=[];homes=[];peaks={}
    for a in native['allocation']:
        rank=a['rank'];rank_ops=[o for o in ops if rank in o['participants']]
        peak=max(rank_ops,key=lambda o:o['temporary_storage']['spill_bytes']);size=peak['temporary_storage']['spill_bytes'];peaks[rank]=size
        base=aligned(a['global_allocated_end_bytes']);end=base+size
        # Keep the two incompatible layouts distinct: no equivalence/reuse credit.
        cal_size=next(e['required_bytes'] for e in target['constrained_extent_successors'] if rank in e['rank_group'])
        wide_size=max(sum(aligned(o['temporary_storage']['allocations'][n]['bytes']) for n in o['explicit64bit_symbols']) for o in rank_ops)
        wide_base=aligned(end);wide_end=wide_base+wide_size
        cal_base=aligned(wide_end);cal_end=cal_base+cal_size
        new=[{'name':'native_workspace','base':base,'bytes':size,'provider_ref':f'Qwen.rank{rank}.extent.native_workspace','codec':'FP32/U32LE4bytes; actual final emitter temp widths retained','source_matched':True},
            {'name':'native_I64_highword_codec_sidecar','base':wide_base,'bytes':wide_size,'provider_ref':f'Qwen.rank{rank}.extent.native_I64_highword','codec':'LE upper32bits per explicit FTOI/SHL64/IADD64 symbol; original lowword4byte home retained','adapter_implemented':False},
            {'name':'calendar_padded_workspace_review_candidate','base':cal_base,'bytes':cal_size,'provider_ref':f'Qwen.rank{rank}.extent.calendar_padded_workspace','codec':'8byte logical slots,2buffers; I64 fullwidth, F32/U32 lowword+padding','source_matched':current,'adopted':False}]
        all_ext=a['extents']+new
        for left,right in zip(all_ext,all_ext[1:]):assert left['base']+left['bytes']<=right['base']
        perstack=[prefix_per_stack(cal_end,s) for s in range(4)];assert max(perstack)<=a['capacity_bytes_per_stack']
        rank_records.append({'rank':rank,'old_allocated_end':a['global_allocated_end_bytes'],'extents':all_ext,'native_peak_PC':peak['pc'],
            'native_workspace_bytes':size,'native_workspace_end':end,'I64_highword_sidecar_bytes':wide_size,'I64_highword_sidecar_base':wide_base,'calendar_review_bytes':cal_size,'conservative_combined_end':cal_end,
            'prefix_allocation_bytes_per_stack':perstack,'stack_capacity_bytes':a['capacity_bytes_per_stack'],
            'native_global_byte_address_bits':(end-1).bit_length(),'conservative_combined_global_byte_bits':(cal_end-1).bit_length(),
            'system_sector_bits_used':((cal_end-1)//32).bit_length(),'maximum_local_sector_bits_used':((max(perstack)-1)//32).bit_length(),
            'extent_boundary_witnesses':[{k:physical(e['base']+(e['bytes']-1 if k=='last' else 0)) for k in ['first','last']} for e in new],
            'hardware_or_residence_admission':False})
        for op in rank_ops:
            temp=op['temporary_storage'];assert temp['RF_vectors_used']<=32
            spill_intervals=[];symbol_window_cursor=0;wide_cursor=0
            for symbol,allocation in temp['allocations'].items():
                h=allocation['home'];row={'pc':op['pc'],'rank':rank,'symbol':symbol,'version':allocation['version'],
                    'bytes':allocation['bytes'],'lease':allocation['lease'],'release_after':allocation['release_after'],
                    'release_guard':'Actual software PC retirement after consumer accept, all accepted writes visible and all reverse grants; no hardware ACK inferred from PC number'}
                assert allocation['release_after']==f"PC{op['pc']}.retire"
                if h['class_']=='RF':
                    slots=h['vector_slots'];assert slots and min(slots)>=3 and max(slots)<32
                    row.update(class_='RF_workspace',SM=0,slots=slots,mirrors=2,refill_slots=[0,1,2])
                else:
                    start=base+h['byte_offset'];padded=aligned(allocation['bytes']);assert h['base_by_rank'][str(rank)]==base
                    assert h['byte_offset']%512==0 and h['byte_offset']+padded<=temp['spill_bytes']<=size
                    spill_intervals.append((start,start+padded));windows=max(1,(padded+(1<<31)-1)//(1<<31));assert symbol_window_cursor+windows<=2048
                    row.update(class_='HBM_native_workspace',provider_ref=new[0]['provider_ref'],base=start,end_exclusive=start+padded,
                        reserved_bytes=padded,codec='FP32/U32 littleendian32-bit words',first=physical(start),last=physical(start+allocation['bytes']-1),
                        identity_object_window_base=symbol_window_cursor,identity_windows=windows,client_class=9,
                        identity_recipe='producer=fullsession64; transport=PC11|window-local-sector-group21; caller=object-window11|sectorordinal5; full sector34 and rank/stack retained; no truncated epoch',
                        caller_object_scope='PC-local distinct symbols; consecutive2GiB windows get distinct object-window indices',
                        finite_admission='Existing4sectorcredits/4ACKcapture/one vector issue lease; physical tag is allocator output, no extra queue credit')
                    symbol_window_cursor+=windows
                if symbol in op['explicit64bit_symbols']:
                    high_bytes=aligned(allocation['bytes']);assert wide_cursor+high_bytes<=wide_size
                    row.update(codec='INT64 littleendian split lower32 in source home + upper32 in separately charged highword extent',
                        semantic_bits=64,highword_provider_ref=new[1]['provider_ref'],highword_base=wide_base+wide_cursor,
                        highword_bytes=allocation['bytes'],highword_reserved_bytes=high_bytes,highword_codec='LE upper32bits,4bytes/element',
                        highword_first=physical(wide_base+wide_cursor),highword_last=physical(wide_base+wide_cursor+allocation['bytes']-1),
                        codec_consumer_fence='Join matching PC/symbol/definition/iteration lower+upper owner identities; both durable ACKs before64bit publication; no lossy uint32 cast',
                        codec_adapter_implemented=False)
                    wide_cursor+=high_bytes
                homes.append(row)
            for left,right in zip(sorted(spill_intervals),sorted(spill_intervals)[1:]):assert left[1]<=right[0]
    read=values['HBM_read_sector']+2*(values['owner_lookup']+values['owner_held_accept'])+sum(values[k] for k in ['forward_CDC','consume','reverse_CDC','validated_reverse_grant','retire'])
    write=values['HBM_write_sector']+2*(values['owner_lookup']+values['owner_held_accept'])+sum(values[k] for k in ['visibility_fence','forward_CDC','consume','reverse_CDC','validated_reverse_grant','retire'])
    return {'status':'PASS_FINAL_NATIVE_WORKSPACE_ADDRESS_BINDING_BLOCKED_FINAL_CALENDAR_MATCH','source_native_commit':native['source_commit'],
        'source_native_sha256':native['source_SHA256'],'source_calendar_consumed_native_sha256':consumed,'final_native_calendar_source_match':current,
        'coverage':{'PCs':len(ops),'opcode_classes':len({o['opcode'] for o in ops}),'temporary_home_bindings':len(homes),'explicit_I64_symbol_homes':sum(h.get('semantic_bits')==64 for h in homes)},'rank_allocation':rank_records,'temporary_homes':homes,
        'portable_r18':{'commit':'aeb45b69448727aec32f448c444fb7c467340a4f','tool':'tools/qwen_hbm_provider_portable_r18.py','snapshot':'results/uarch/qwen_hbm_provider_portable_r18_20261002/source_metadata.tar.gz','r17_binding_sha256':'01cb064303e809b2389dad4da6932bb1ffa9d7e40f93cd0918b1eba43ca56da1','private_r15_cost_file_or_git_required':False},
        'service_cost':{'unit':'abstract_software_tick','source':'Captured native_r3 positive provisional cycle table','read_sector_compound_ticks':read,'write_sector_compound_ticks':write,'two_owner_lookups_ticks':2*values['owner_lookup'],
            'source_clock_transfer':False,'measured':False,'source_serial_owner_ceiling_bytes_per_s_at_1GHz':32e9/26,
            'hardware_dependency_rule':'issue=max(requestCDC,bank/refresh/scan availability,reserved write residence,RAW predecessor visibility); completion follows actual PHY return/backing-visible then consumer/CDC/reverse held grant. No physical latency from serial software cost sum.',
            'highword_sidecar_extra_full_sector_read_ticks':read,'highword_sidecar_extra_full_sector_write_ticks':write,'codec_split_join_ticks_per128word_tile':32,'codec_split_join_calibration':'Positive provisional software parameter; not a measured64bit SM instruction cost','partial_sector_update':'Actual read-before-write sector RMW plus merge and visible write costs required; no free overwrite','no_extra_RF_or_PHY_ports':True,'native_workspace_issue':'One SM0 workspace lease; serialize refill/compute/spill, mirrored write ACK;32SM source version homes remain distinct'},
        'older_calendar':{'cycle_count_not_final_native_admission':target['cycles'],'logical_scratch_layout':'8byte slots,2buffers, distinct arena reserved only as review candidate','relocation_contract':'base_by_rank+program.scratch_homes[symbol].byte_offset+parity*buffer_bytes+8*logical_element; exact per-program offsets in snapshotted calendar metadata','endpoint_values':values},
        'blocked':['Calendar native_r3 hash differs from final8fab955; Dewey must regenerate against final package before final token/calendar coverage','Calendar padded arena is separately reserved; no equivalence or sharing credit with native4byte workspace','Explicit native64bit symbols need lower+upper codec adapter before physical serialization; separately charged1.5MiB/rank highword candidate supplies no numerical or hardware credit','Actual native request/WR-visible/reverse/quarantine/reset endpoint andSSFF remain unqualified','32PC owner banking candidate exceeds retained margin; extra queue capacity supplies no throughput repair'],
        'hardware_or_rate_or_physical_admission':False,'jobs':[]}

def emit(out):
    out.mkdir(parents=True,exist_ok=True);m=model();homes=m.pop('temporary_homes');raw=gzip.compress(json.dumps(homes,sort_keys=True,separators=(',',':')).encode(),mtime=0)
    (out/'temporary_provider_homes.json.gz').write_bytes(raw);m['temporary_provider_homes_sha256']=hashlib.sha256(raw).hexdigest();(out/'join.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);emit(p.parse_args().output)
