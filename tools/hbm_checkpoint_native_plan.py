#!/usr/bin/env python3
"""Explicit full native checkpoint address plan, separate from legacy dense WBASE.

Uses actual released tensor headers, TP96 compiler row ownership and all fixed
source-region fences. This reserves addresses; it does not install an image or
qualify a native programme, DRAM controller, clock tree or performance target.
"""
import hashlib,json,math
from pathlib import Path
from hbm_svc_packed136_image import mapped_sector,sector_pc
import hbm_engram_partition as E
ROOT=Path(__file__).resolve().parents[1]

def load_verified(path):
    d=json.loads(path.read_text())
    for p,h in d.get('source_sha256',{}).items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,(p,'source drift')
    return d

def block_bytes(matrix,rank,sm):
    lo,hi=matrix['rank_row_intervals'][rank]
    rows=max(0,(max(0,hi-lo)+31-sm)//32)
    per_expert=128*math.ceil(rows*matrix['packed_bytes_per_row']/128)
    return rows,per_expert

def descriptor(residency,rank,sm,index,expert):
    assert 0<=rank<96 and 0<=sm<32 and 0<=index<len(residency['matrices'])
    cursor=0
    for i,m in enumerate(residency['matrices']):
        rows,stride=block_bytes(m,rank,sm)
        if i==index:
            assert rows and 0<=expert<m['experts']
            lo,hi=m['rank_row_intervals'][rank]
            return dict(rank=rank,sm=sm,stack=sm//8,pcs=list(range(sm%8*4,sm%8*4+4)),
                region_row_base=16640,region_row_count=2048,
                packed_sector_offset=(cursor+expert*stride)//32,sectors=stride//32,
                payload_records=rows*m['packed_bytes_per_row']//136,
                source_matrix_key=m['key'],source_expert=expert,
                source_row_first=lo+sm,source_row_stride=32,source_row_count=rows,
                source_k=m['source_k'],source_format=m['format'],
                source_columns='rank%8*512 .. +512' if m['source_function']=='wo_a_part' else 'all source columns',
                current_mapped4_base0_only_producer_compatible=(cursor+expert*stride)==0)
        cursor+=m['experts']*stride
    raise AssertionError('matrix descriptor')

def transfer_blocks(d):
    # Actual packed136 cache has64 records per epoch. Complete64-record blocks
    # occupy8704 bytes (a multiple of128); only the final block is padded.
    left=d['payload_records'];offset=d['packed_sector_offset'];record=0
    while left:
        count=min(64,left);sectors=4*math.ceil(count*136/128)
        assert offset%4==0 and sectors<=2048
        yield dict(packed_sector_offset=offset,records=count,sectors=sectors,source_record_offset=record)
        offset+=sectors;record+=count;left-=count
    assert offset==d['packed_sector_offset']+d['sectors']

def run(out):
    residency_path=ROOT/'results/arch/hbm_die_v15/checkpoint_residency/receipt.json'
    fixed_path=ROOT/'results/arch/hbm_die_v15/fixed_regions/receipt.json'
    manifest_path=ROOT/'results/arch/hbm_engram_partition_1015/allocation_manifest.json'
    r=load_verified(residency_path);f=load_verified(fixed_path);e=json.loads(manifest_path.read_text())
    assert e==E.allocation_manifest() and not f['source_region_overlaps']
    region=[16640<<20,18688<<20];capacity=2048*131072
    pools=[];vectors=0;peak=0
    for sm in range(32):
        stack=sm//8;pcs=list(range(sm%8*4,sm%8*4+4))
        for x in f['fixed_regions']:
            if x['stack']==stack:
                lo,hi=x['physical_sector_envelope'];assert not(lo<region[1] and region[0]<hi),(sm,x)
        for x in e['intervals']:
            if x['stack']==stack:assert not(x['stack_local_begin']<region[1] and region[0]<x['stack_local_end'])
        for pc in pcs:
            for row in (16640,18687):
                for bank in range(32):
                    for col in range(32):
                        s=mapped_sector(pc,bank,row,col)
                        assert sector_pc(s)==pc and region[0]<=s*32<(s+1)*32<=region[1]<=22500000000
                        vectors+=1
        used=[]
        for rank in range(96):
            cursor=0
            for matrix in r['matrices']:
                rows,stride=block_bytes(matrix,rank,sm)
                assert cursor%128==0 and stride%128==0
                cursor+=stride*matrix['experts']
                assert cursor<=capacity,(rank,sm,cursor)
            assert cursor==r['rank_sm_reserved_bytes'][rank][sm]
            used.append(cursor);peak=max(peak,cursor)
        pools.append(dict(sm=sm,stack=stack,pcs=pcs,row_base=16640,row_count=2048,
            capacity_bytes=capacity,local_byte_envelope=region,rank_used_bytes=used,
            source_layout='matrix order from residency receipt; each expert block padded only to128B; local output row ordinal modulo32'))
    samples=[]
    # Sample actual worst-size matrix/expert and a nonzero offset on every rank/SM.
    for rank in (0,63,64,95):
        for sm in range(32):
            candidates=[(block_bytes(m,rank,sm)[1],i) for i,m in enumerate(r['matrices']) if block_bytes(m,rank,sm)[0]]
            _,i=max(candidates)
            d=descriptor(r,rank,sm,i,r['matrices'][i]['experts']-1)
            blocks=list(transfer_blocks(d))
            d['cache64_transfer_blocks']=dict(count=len(blocks),first=blocks[0],last=blocks[-1],
                all_offsets_128byte_aligned=True,max_sectors_per_block=max(b['sectors'] for b in blocks))
            samples.append(d)
    result=dict(schema='opentallas.hbm.full-native-checkpoint-address-plan.v1',
        status='ALL96_RANK32_SM_SOURCE_ADDRESS_CAPACITY_COLLISION_PASS_INSTALLATION_REQUIRED',
        address_mode='explicit four-PC packed136 native image; legacy dense WBASE direct loads are not this image',
        namespace_fence='Do not mix direct WBASE legacy descriptors with this allocation epoch; native programme/loader must resolve through this source-owned plan',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [residency_path,fixed_path,manifest_path,ROOT/'tools/hbm_checkpoint_native_plan.py']},
        ranks=96,sm_per_rank=32,stack_capacity_bytes=22500000000,pools=pools,
        released_tensor_headers=r['checkpoint_tensor_header_count'],checkpoint_payload_bytes_read=0,
        max_rank_SM_payload_bytes=r['max_rank_bytes'],max_SM_payload_bytes=peak,
        per_SM_capacity_bytes=capacity,each_stack_weight_region_bytes=region[1]-region[0],
        actual_Kmap_boundary_vectors=vectors,fixed_region_conflicts=0,eight_home_Engram_conflicts=0,
        matrix_layout=dict(residency_manifest=str(residency_path.relative_to(ROOT)),
            matrices=len(r['matrices']),offset='sum(prior matrices experts*128*ceil(owned_rows*rowbytes/128)) + expert*128*ceil(owned_rows*rowbytes/128)',
            descriptor_function='tools/hbm_checkpoint_native_plan.py:descriptor',
            transfer_function='tools/hbm_checkpoint_native_plan.py:transfer_blocks',
            cache_records_per_epoch=64,max_full_block_sectors=272,
            physical_sector='mapped_sector(pcs[j%4],bank={t9:7,t1:0},row=16640+(t>>10),col=t6:2);j=packed_sector_offset+relative_sector,t=j//4'),
        checked_sample_descriptors=samples,installation_qualified=False,native_programme_qualified=False,
        performance_qualified=False,physical_qualified=False,
        remaining=['Extend actual mapped4 reserve_base low30 from mandatory0 to declared packed sector offset with bounded region checks',
            'Compile real source row/column/expert offsets, transfer blocks, native83 commands and all programme refill cycles',
            'Generate/ACK/readback full actual checkpoint images and guard installed epochs/legacy descriptor incompatibility',
            'Regenerate relocated HC/IKS/Engram-stage/MTP source images and prove actual native read/write joins',
            'Actual complete immutable-performance, native numerical, clock/pin/TT/FF/DRC qualification'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(dict(vectors=vectors,max_SM_bytes=peak,capacity_per_SM=capacity,all96rank32SM_capacity_pass=True,fixed_conflicts=0)))
    return result
if __name__=='__main__':run(ROOT/'results/arch/hbm_die_v15/full_native_checkpoint_plan/book.json')
