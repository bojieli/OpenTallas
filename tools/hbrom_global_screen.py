#!/usr/bin/env python3
"""Architecture-only global ROM capacity screen; never predicts token latency.

Rank ownership is imported from W19 at TP96. Other TP values are explicitly
new-ownership sensitivities. Native row records use the existing exact allocator
geometry. Within-rank placement is a declared analytical schedule assumption.
"""
import argparse, collections, gzip, hashlib, json, math, re
from pathlib import Path
import numpy as np
from hbrom_allocator import row_geometry, normalize_format, summarize_storage_records


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def append_rows(cursor, count, records):
    """Vectorized equivalent of allocator whole-row, eight-record aligned append."""
    start=(cursor+7)//8*8
    room=(8192-start%8192)//records
    overflow=count>room
    left=np.maximum(count-room,1)
    end=np.where(overflow,(start//8192+1)*8192+((left-1)//(8192//records))*8192+((left-1)%(8192//records)+1)*records,start+count*records)
    return np.where(count>0,end,cursor)


def compile_matrices(inputs, program):
    ops={}; expert={}
    for layer in program['layers']:
        for op in layer['ops']:
            if op['kind']!='mv': continue
            if isinstance(op['w'],str): ops[op['w']]=op
            else: expert[(layer['layer'],op['w'][1],op['w'][0]==6)]=op
    matrices=[]; deferred=[]
    for t in sorted(inputs['tensors'],key=lambda x:x['name']):
        n=t['name']; op=None
        if n.endswith(':execution_bf16'): op=ops.get(n.split(':')[0])
        elif n.endswith('.wo_a.weight'): pass # preserve released FP8 as archive
        elif n in ops: op=ops[n]
        else:
            m=re.match(r'layers\.(\d+)\.ffn\.(experts\.\d+|shared_experts)\.(w[123])\.weight$',n)
            if m: op=expert[(int(m[1]),m[3],m[2]=='shared_experts')]
        if op is None: deferred.append(t); continue
        assert normalize_format(t['format'])==op['fmt'],(n,t['format'],op['fmt'])
        matrices.append((t,op))
    return matrices,deferred


def screen(matrices,tp,sm,rotate,area):
    cur=np.zeros((tp,sm),dtype=np.int64); payload=0; census=collections.Counter(); families={}
    for idx,(t,o) in enumerate(matrices):
        if tp==96: counts=np.array([b-a for a,b in o['rows']],dtype=np.int64)
        elif o['fn']=='wo_a_part': counts=np.array([1024 if r<64 else 0 for r in range(tp)])
        elif '.wq_b.weight' in t['name']: counts=np.array([512 if r<64 else 0 for r in range(tp)])
        else: counts=np.array([(r+1)*o['n']//tp-r*o['n']//tp for r in range(tp)])
        # Remainder-first balanced whole-row partition has measured ceil busiestSM.
        tile=counts[:,None]//sm+(np.arange(sm)[None,:]<counts[:,None]%sm)
        if rotate:
            # Same stable expert identity and layer origin for paired gate/up.
            key=re.sub(r'\.w[123]\.weight$', '',t['name'])
            shift=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%sm
            tile=np.roll(tile,shift,axis=1)
        g=row_geometry(o['fmt'],o['k']); rpr=g['records_per_row']
        cur=append_rows(cur,tile,rpr); payload+=int(tile.sum())*rpr
        census[o['fmt']]+=int(tile.sum())*rpr
        family=re.sub(r'layers\.\d+\.', '',t['name']).split(':')[0]
        family=re.sub(r'experts\.\d+', 'experts.*',family)
        if family not in families:
            families[family]={'active_ranks':int(np.count_nonzero(counts)), 'active_sms':int(np.count_nonzero(tile)), 'busiest_sm_rows':int(tile.max()), 'k':o['k'],'format':o['fmt'],'native_groups':g['groups'], 'issue_slot_cycles_lower_bound':math.ceil(int(tile.max())*g['groups']/8)*64}
    pairs=((cur+8191)//8192)*4
    rank_area=pairs.sum(axis=1)*2*area
    return dict(tp=tp,sms_per_rank=sm,placement='explicit_local_rotation_candidate' if rotate else 'remainder_first_contiguous_rows',rank_ownership='authoritative_W19' if tp==96 else 'new_rank_ownership_sensitivity_not_existing_HBM_schedule',within_rank_mapping_status='analytical partition consistent with busiest-SM ceil; complete physical schedule unproved',matrix_count=len(matrices),native_records=payload,native_code_slot_bytes=payload*128,allocated_pairs_total=int(pairs.sum()),max_pairs_per_sm=int(pairs.max()),min_pairs_per_sm=int(pairs.min()),max_pairs_per_rank=int(pairs.sum(axis=1).max()),uniform_pool_raw_rom_mm2_per_rank=int(pairs.max())*sm*2*area,max_mux_inputs_per_stream=int(pairs.max())//4,max_mux_binary_levels=math.ceil(math.log2(max(1,int(pairs.max())//4))),max_raw_rom_mm2_per_rank=float(rank_area.max()),min_raw_rom_mm2_per_rank=float(rank_area.min()),max_pool_records=int(cur.max()),allocation_holes_records=int(cur.sum())-payload,pair_highwaters=pairs.tolist(),families=families,qualified=False,tpot_us=None,rotation_obligations=['tagged output ownership and ordered expert combine','gate/up same owner','finite per-matrix segment dispatch; costs not yet priced'] if rotate else [])


def build(input_path,program_path):
    with gzip.open(input_path,'rt') as f: inputs=json.load(f)
    program=json.load(open(program_path)); matrices,deferred=compile_matrices(inputs,program)
    bound=summarize_storage_records(inputs['tensors'],tp=1)
    deferred_bytes=sum(t['bytes'] for t in deferred)
    cases=[screen(matrices,tp,sm,rot,inputs['macro']['area_mm2']) for tp,sm in [(64,32),(96,16),(96,32),(128,32)] for rot in (False,True)]
    return dict(schema='opentallas.hbrom.global_screen.v1',architecture_only=True,default_enabled=False,source_pins={str(p):digest(p) for p in [input_path,program_path,Path(__file__),Path(__file__).with_name('hbrom_allocator.py')]},native_census_bound=bound,mapped_executable_tensor_count=len(matrices),deferred_tensor_count=len(deferred),deferred_source_and_dedicated_bytes=deferred_bytes,deferred_replicated_bytes_per_rank=sum(t['bytes'] for t in deferred if t.get('replicated')),deferred_capacity_note='Base bytes count one copy; add (TP-1) times replicated bytes if preserving inherited per-rank replication. Dedicated service placement may alter this only with explicit transport.',auxiliary_storage_bytes=inputs['auxiliary_storage_bytes'],separate_storage_total_bytes=deferred_bytes+inputs['auxiliary_storage_bytes'],separate_storage_obligations=['Exact released source scales/wo_a source preserved in archival storage','FP32 HC weights and dedicated Engram/index operators require explicit replication/read ports near their service','Embedding is a row lookup with transport; head is included in executable matrix pools','MTP/vision retained capacity, no AR traffic claim','Separate archive die count needs physical native format and service placement; no zero-cost lookup assumption'],cases=cases,port_contract={'rom_word_bits':274,'streams_per_sm':4,'physical_bits_per_cycle_per_sm':1096,'sm_bits_per_cycle':1088,'macs_per_cycle':{'fp4':256,'fp8':128,'bf16':64},'clock_hz_assumption':1200000000,'macro_capture':'two-cycle local capture, alternating banks','compute_state':'full private RF/SIMD/SRAM per engine required to inherit existing HBM schedule; no shared-RF area credit'},qualification_blockers=['No full token schedule composed; TPOT intentionally null','Bank mux routing/capture, finite issue and stream conflicts need pricing','Actual per-SM HBM dispatcher mapping not fully recorded; contiguous partition is explicit assumption','64/128 rank sensitivities require new collective/exact topology schedule','Full private compute, protected SRAM, service hub, TU fabric PHY and archive service area missing from raw ROM bound','No RTL or physical jobs authorized by this analytical screen'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',default='results/uarch/hbrom/g0_inputs.json.gz');p.add_argument('--program',default='results/rtl/w19_hbm_tp96_program_oreduce.json');p.add_argument('--out',default='results/uarch/hbrom/global_screen.json');a=p.parse_args()
    result=build(a.inputs,a.program);Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    for c in result['cases']: print(c['tp'],c['sms_per_rank'],c['placement'],c['max_pairs_per_sm'],round(c['max_raw_rom_mm2_per_rank'],3))
