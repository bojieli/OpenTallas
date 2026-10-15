#!/usr/bin/env python3
"""Reserve source-owned DATA_WIN space without moving any occupied checkpoint region."""
import ast
import hashlib
import json
from pathlib import Path
from hbm_svc_packed136_image import mapped_sector, sector_pc
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['tools/hgi_sim/ds_native.py','tools/hgi_sim/ds_mtp_kernels.py',
 'rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv','rtl/hbm_accel/service/ot_hbm_kport_map.sv',
 'tools/hdc_v41_engram_shipped.py']

def constants(path,wanted):
    env={}
    for n in ast.parse(path.read_text()).body:
        if not isinstance(n,ast.Assign):continue
        names=[t.id for t in ast.walk(n.targets[0]) if isinstance(t,ast.Name)]
        if names and set(names)<=wanted:
            exec(compile(ast.Module(body=[n],type_ignores=[]),str(path),'exec'),{'__builtins__':{}},env)
    assert wanted<=env.keys(),wanted-env.keys()
    return env

def run(out):
    dn=constants(ROOT/SOURCES[0],{'WBASE','STACK_BYTES','DATA_WIN','DATA_WIN_BYTES','HC_STRIPE_LOC','EG_HOMES','EG_ROWB','EG_TBASE'})
    mt=constants(ROOT/SOURCES[1],{'PMAX','BLK','NCOLSLOT','COLB','CSTR'})
    eg=constants(ROOT/SOURCES[4],{'RELEASED_ROWS'})
    eg_extents=[]
    for layer,rows,homes in zip((1,14),eg['RELEASED_ROWS'],dn['EG_HOMES']):
        per_home=(rows+3)//4
        for i,rank in enumerate(homes):
            actual_rows=min(per_home,max(0,rows-i*per_home))
            eg_extents.append(dict(owner='released Engram table',layer=layer,rank=rank,stack=3,
                local_bytes=[0,actual_rows*dn['EG_ROWB']],rows=actual_rows,
                exceeds_stack_capacity=actual_rows*dn['EG_ROWB']>dn['STACK_BYTES']))
    rowbytes=1<<20
    mt_end=mt['COLB']+mt['NCOLSLOT']*mt['CSTR']
    first=(mt_end+rowbytes-1)//rowbytes
    limit=(dn['DATA_WIN']+dn['DATA_WIN_BYTES'])//rowbytes
    assert dn['DATA_WIN']<=mt['COLB']<mt_end<=first*rowbytes<limit*rowbytes<=dn['STACK_BYTES']
    assert mt['COLB']>=dn['DATA_WIN']+(256<<20)
    assert dn['WBASE']>>35==2 and dn['WBASE']&((1<<35)-1)==0
    sha={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    # Exercise actual Manifest.place/place_at source to verify this reserved window
    # cannot be occupied by either dynamic or fixed checkpoint weight extents.
    tree=ast.parse((ROOT/SOURCES[0]).read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('data_window_hit','Manifest')]
    class FakeMC:
        Fault=ValueError
    scope=dict(dn,ESZ={'fp8':1},SM_GK={},SM_LB=136,MAN_END=94<<30,MC=FakeMC)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),SOURCES[0],'exec'),scope)
    tests=[]
    for stack in range(4):
        base=(stack<<35)+dn['DATA_WIN']
        m=scope['Manifest']();m.cur=base-4096
        rejected=False
        try:
            e=m.place('cross_window',1,8192,'fp8')
            assert e['base']>=base+dn['DATA_WIN_BYTES']
        except ValueError:rejected=True
        try:m.place_at('forbidden',base+258*rowbytes,1,32,'fp8')
        except ValueError:pass
        else:raise AssertionError('actual fixed weight guard failed')
        tests.append(dict(stack=stack,dynamic_weight_crossing_skips_or_rejects_window=True,dynamic_manifest_capacity_rejection=rejected,fixed_weight_window_rejected=True))
    reservations=[];used=set();bounds=[]
    for sm in range(32):
        stack=sm//8;pcs=list(range((sm%8)*4,(sm%8)*4+4))
        a=dict(schema='opentallas.hbm-packed136-allocation.v1',allocation_id=f'hbm96-sm{sm}-packed136-datawin-v1',
            provenance=dict(book='results/arch/hbm_die_v15/checkpoint_allocation/book.json',
                policy='source DATA_WIN remainder after HC first256MiB and actual13 MTP column slots; no occupied range moved',
                source_sha256=sha),stack=stack,pcs=pcs,row_base=first,row_count=limit-first,
            stack_bytes=dn['STACK_BYTES'],sm=sm,rank=0,rank_scope='same local reservation replicated independently on each of96 ranks')
        for pc in pcs:
            for row in range(first,limit):
                key=(stack,pc,row)
                assert key not in used;used.add(key)
                # s>>15==row; exhaust actual bank/column permutations at first
                # and last row to check every boundary PC permutation and byte bound.
                if row in (first,limit-1):
                    for bank in range(32):
                        for col in range(32):
                            s=mapped_sector(pc,bank,row,col)
                            assert s>>15==row and sector_pc(s)==pc
                            assert first*rowbytes<=s*32<(limit*rowbytes)
                            assert (s+1)*32<=dn['STACK_BYTES']
        blocked=[e['rank'] for e in eg_extents if e['stack']==stack and e['local_bytes'][1]>first*rowbytes]
        a['allowed_ranks']=[r for r in range(96) if r not in blocked]
        if 0 not in blocked:reservations.append(a)
        bounds.append(dict(blocked_ranks=blocked,allowed_ranks=a['allowed_ranks'],sm=sm,stack=stack,pcs=pcs,rows=[first,limit],
            local_byte_envelope=[first*rowbytes,limit*rowbytes],
            reserved_payload_bytes=len(pcs)*(limit-first)*32*32*32))
    book=dict(schema='opentallas.hbm-physical-allocation-book.v1',status='PARTIAL_RANK_SCOPED_RESERVATIONS_ENGRAM_CAPACITY_COLLISION_BLOCKS_FULL_BOOK',
        scope=dict(ranks=96,sm_per_rank=32,stacks_per_rank=4,pcs_per_stack=32),
        source_sha256=sha,address=dict(global_byte='stack=byte[36:35], localbyte=byte[34:0]',
            sector='localbyte>>5; full30bits',pc='s[6:2]^s[11:7]^s[16:12]',row='s>>15',
            row_envelope_bytes=rowbytes,WBASE=dn['WBASE'],WBASE_decoded_stack=2,WBASE_decoded_local_byte=0),
        occupied_and_protected=[
            dict(owner='all existing weights/KV/IDX/Engram/tables/DMA outside DATA_WIN',policy='unchanged; new reservations never address outside source DATA_WIN',exact_extent_inventory_complete=False),
            dict(owner='HC future capacity protection',stack='all4',local_bytes=[dn['DATA_WIN'],mt['COLB']],policy='entire first256MiB protected; legacy HC_STRIPE_LOC remains invalid and is not silently relocated'),
            dict(owner='MTP column DMA slots',stack='all4',local_bytes=[mt['COLB'],mt_end],slots=mt['NCOLSLOT'],stride=mt['CSTR']),
            dict(owner='alignment gap',stack='all4',local_bytes=[mt_end,first*rowbytes],policy='not allocated')],
        released_engram_occupied_extents=eg_extents,
        blocked_rank_sm_pairs=[[r,b['sm']] for b in bounds for r in b['blocked_ranks']],
        emitted_allocation_rank=0,
        new_reservations=bounds,weight_guard_source_tests=tests,
        collision_proof=dict(distinct_stack_pc_row_tuples=len(used),duplicate_tuple_count=0,
            actual_bank_column_boundary_vectors=32*4*2*32*32,all_in_data_window=True,
            all_within_stack_capacity=True,weight_manifest_guards_exercised=True),
        occupied_source_errors=[dict(owner='legacy HC stripe',local_base=dn['HC_STRIPE_LOC'],
            capacity=dn['STACK_BYTES'],valid=False,action='requires explicit source relocation by owner; not modified by this reservation')],
        remaining=['released520-record payload counts/sourceSHA must be bound to perSM reservations',
            'native mapped descriptor and actual hardware installation/ACK',
            'full future checkpoint live extents and capacity inventory, beyond current source window reservation',
            'immutable packed136 performance and physical/native qualification'])
    out.mkdir(parents=True,exist_ok=True)
    for sm in range(24,32):
        stale=out/f'sm{sm:02d}.json'
        if stale.exists():stale.unlink()
    for a in reservations:(out/f'sm{a["sm"]:02d}.json').write_text(json.dumps(a,indent=2)+'\n')
    (out/'book.json').write_text(json.dumps(book,indent=2)+'\n')
    print(json.dumps(dict(row_base=first,row_limit=limit,bytes_per_sm=bounds[0]['reserved_payload_bytes'],proof=book['collision_proof'])))
    return book
if __name__=='__main__':run(ROOT/'results/arch/hbm_die_v15/checkpoint_allocation')
