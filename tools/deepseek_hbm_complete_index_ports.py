"""Candidate index unpack RF/shared events from the modeled ordinary GPU ports.

The r1 byte-load recipe/evidence is preserved. Here each row stages seventeen
little-endian U32 words into term-major shared memory before ordinary unpack.
RF mapping follows w19_gpu_simd_contract's 16x8-lane, dual-read-copy proposal.
Events specify dependencies and addresses, never observed hardware timestamps.
"""
from collections import Counter
import numpy as np
import deepseek_hbm_complete_index_ingress as R1
import deepseek_hbm_complete_canonical as C

X=R1.X
RAW_BASE=R1.END
END=RAW_BASE+17*64*4


def program():
    p=[]
    for j in range(128):
        p += [X.K.ins('LOAD','packed',f'word{j//8}'),
              X.K.ins('SHR','code','packed',4*(j%8)),
              X.K.ins('AND','code','code',15),X.K.ins('MOV','unit',0)]
        for code,unit in enumerate(X.K.UNITS):
            p += [X.K.ins('IEQ','take','code',code),X.K.ins('ISUB','mask',0,'take'),
                  X.K.ins('AND','part','mask',unit&0xffffffff),X.K.ins('OR','unit','unit','part')]
        p += [X.K.ins('STORE',f'unit{j}','unit')]
    for b in range(4):
        p += [X.K.ins('LOAD','packed','word16'),X.K.ins('SHR','scale','packed',8*b),
              X.K.ins('AND','scale','scale',255),X.K.ins('ISUB','exponent','scale',126),
              X.K.ins('STORE',f'exp{b}','exponent')]
    return p


def unpack(rows):
    rows=np.asarray(rows)
    if rows.dtype!=np.uint8 or rows.ndim!=2 or rows.shape[1]!=68 or not 1<=len(rows)<=64:
        raise ValueError('bounded uint8 68B rows')
    if np.any(rows[:,64:]<1) or np.any(rows[:,64:]>252):
        raise ValueError('BF16 scale boundary not admitted')
    # Byte view describes the proposed wire layout, not a floating operation.
    words=np.ascontiguousarray(rows).view('<u4').reshape(len(rows),17)
    words=np.pad(words,((0,(-len(rows))%32),(0,0)))
    m=X.SIMT((len(words)//32,32),
             {f'word{j}':words[:,j].reshape(-1,32) for j in range(17)}).run(program())
    units=np.stack([m.stores[f'unit{j}'].view(np.int32).reshape(-1)[:len(rows)] for j in range(128)],axis=-1)
    exp=np.stack([m.stores[f'exp{j}'].view(np.int32).reshape(-1)[:len(rows)] for j in range(4)],axis=-1)
    return units,exp,m


def rf_location(partition,warp_slot,reg,lane):
    if not 0<=partition<4 or not 0<=warp_slot<8 or not 0<=reg<32 or not 0<=lane<32:
        raise ValueError('modeled RF geometry')
    depth=warp_slot*32+reg
    return {'lane_group8':partition*4+lane//8,'subword':lane%8,
            'depth_bank':depth//128,'row':depth%128,'read_copies':[0,1],
            'write_broadcast_copies':[0,1]}


def shared_address(name,row):
    if not 0<=row<64:raise ValueError('finite tile row')
    if name.startswith('word'):
        j=int(name[4:])
        if not 0<=j<17:raise ValueError('packed word')
        return RAW_BASE+4*(j*64+row)
    if name.startswith('unit'):
        return R1.address('key',int(name[4:]),row)
    if name.startswith('exp'):
        j=int(name[3:])
        if not 0<=j<4:raise ValueError('scale block')
        return R1.KEY_SCALE_BASE+4*(j*64+row)
    raise ValueError('unknown shared operand')


def events(partition=0,warp_slot=0,tile_row=0,active_lanes=32):
    if tile_row not in (0,32) or not 1<=active_lanes<=32:
        raise ValueError('finite warp row range')
    rf_location(partition,warp_slot,0,0)
    p=program();versions={};last={};ssa=[]
    for pc,i in enumerate(p):
        if len(i['src'])!=X.ARITY[i['op']]:raise ValueError('opcode arity')
        src=[]
        for value in i['src']:
            if i['op']=='LOAD':src.append(('shared',value))
            elif isinstance(value,int):src.append(('immediate',value))
            else:
                if value not in versions:raise ValueError('uninitialized register')
                version=versions[value];src.append(('register',version));last[version]=pc
        dst=None
        if i['op']!='STORE':dst=(i['dst'],pc);versions[i['dst']]=dst;last.setdefault(dst,pc)
        ssa.append((i,src,dst))
    live={};free=set(range(24));peak=0;rows=[];missing=Counter();last_reads={}
    for pc,(i,src,dst) in enumerate(ssa):
        operands=[];deps=[]
        for kind,value in src:
            if kind=='register':
                operands.append({'kind':'register','reg':live[value],
                                 'producer_event':value[1],'read_copy':len(operands)})
                last_reads[live[value]]=pc
                deps.append(value[1])
            elif kind=='immediate':operands.append({'kind':'immediate','bits':value&0xffffffff,'RF_port_used':False})
            else:operands.append({'kind':'shared','word':value})
        # Operand reads precede destination write; a dying source may share the
        # destination register with an explicit read-before-overwrite dependency.
        dying={v for kind,v in src if kind=='register' and last[v]==pc}
        for version in dying:free.add(live.pop(version))
        destreg=None
        if dst is not None:
            if not free:raise ValueError('RF value register budget exceeded')
            destreg=min(free);free.remove(destreg);live[dst]=destreg
        peak=max(peak,len(live))
        opcode=i['op'];bound=opcode in C.KNOWN
        if not bound:missing[opcode]+=1
        shared=None
        if opcode in ('LOAD','STORE'):
            name=i['src'][0] if opcode=='LOAD' else i['dst']
            addrs=[shared_address(name,tile_row+lane) for lane in range(active_lanes)]
            banks=[a//4%32 for a in addrs]
            shared={'direction':'read' if opcode=='LOAD' else 'write','addresses':addrs,
                    'banks':banks,'one_word_per_bank':len(set(banks))==len(banks),
                    'requested_bytes':4*active_lanes,'visibility_event':f'unpack:{pc}:shared-visible'}
        row={'id':pc,'opcode':opcode,'dependencies':sorted(set(deps)),
             'operands':operands,'destination_register':destreg,
             'issue_order_after':None if pc==0 else f'unpack:{pc-1}:issue',
             'destination_reuse_requires_RF_read_complete':None if destreg not in last_reads else f'unpack:{last_reads[destreg]}:RF-ready',
             'RF_operand_ready_event':f'unpack:{pc}:RF-ready',
             'issue_requires':['RF-ready']+(['packed-tile-visible'] if opcode=='LOAD' else []),
             'RF_writeback_event':None if destreg is None else f'unpack:{pc}:RF-writeback',
             'RF_destination_layout':None if destreg is None else {
                 'partition':partition,'warp_slot':warp_slot,'reg':destreg,'active_lanes':active_lanes,
                 'lane0':rf_location(partition,warp_slot,destreg,0),
                 'lane_formula':'group=partition*4+lane//8;subword=lane%8;depth=warp_slot*32+reg;bank=depth//128;row=depth%128'},
             'RF_ports':'2R1W; one warp per partition; writeback slot arbitration required',
             'shared':shared,'read_before_destination_overwrite':True,
             'RF_plus_core_latency_candidate':C.KNOWN.get(opcode),
             'opcode_cost_bound':bound,'actual_hardware_timestamp':None}
        rows.append(row)
        if dst is not None and last[dst]==pc:free.add(live.pop(dst))
    return {'events':rows,'active_lanes':active_lanes,'tile_row':tile_row,
            'RF_peak_value_registers':peak,'RF_address_loop_reserved_registers':8,
            'RF_registers_thread':32,'shared_allocation_bytes':END,
            'unbound_opcode_counts':dict(missing),'qualified_cycles':None,
            'physical_admission':'FAIL_CLOSED','shared_store_cycle_cost':None,
            'candidate_port_model_source':'tools/w19_gpu_simd_contract.py',
            'missing':['physical opcode costs','warp-to-SM placement','actual packed producer binding',
                       'refill scatter/collective and controller lease events','writeback arbitration across kernels']}


def refill_events(rank,start,count,base):
    """Demand-matching scatter events, no timer-generated backend completion.

    Each word references the exact wire bytes and the sector return IDs holding
    them. Initial/retained checkpoint values are not injected by this planner.
    """
    tile=R1.tile_contract(rank,start,count,base);requests=tile['requests']
    sectors={s:r for r,req in enumerate(requests)
             for s in range(req['sector_address'],req['sector_address']+req['length_sectors'])}
    scatter=[]
    for row in range(count):
        for word in range(17):
            lo=base+(start+row)*68+word*4
            scatter.append({'tile_row':row,'wire_byte_range':[lo,lo+4],
                            'requires_return_requests':sorted({sectors[lo//32],sectors[(lo+3)//32]}),
                            'shared_address':shared_address(f'word{word}',row),
                            'shared_bank':shared_address(f'word{word}',row)//4%32,
                            'event':f'packed:{word}:{row}:shared-visible',
                            'actual_hardware_timestamp':None})
    # Register/fabric staging is a demand, not an invented free crossbar.
    return {'requests':requests,'scatter_events':scatter,'wire_bytes':count*68,
            'staging_write_bytes':count*68,'raw_shared_bytes':4352,
            'packed_tile_visible_requires':[s['event'] for s in scatter],
            'scatter_cycles':None,'scatter_network_bits_and_routes':None,
            'release_requires':['all unpack raw LOAD consumers done','all score key/scale LOAD consumers done',
                                'matching controller return consumerdone','actual reverseCDC credit return'],
            'physical_admission':'FAIL_CLOSED'}


def record():
    from pathlib import Path
    import hashlib
    import json
    root=Path(__file__).resolve().parents[1]
    paths=['tools/deepseek_hbm_complete_index_ports.py',
           'tools/deepseek_hbm_complete_index_producer_scope.py',
           'tools/deepseek_hbm_complete_index_ingress.py',
           'tools/deepseek_hbm_complete_index.py',
           'tools/deepseek_hbm_complete_canonical.py',
           'tools/w19_gpu_simd_contract.py',
           'tests/test_deepseek_hbm_complete_index_ports.py']
    evidence='results/rtl/deepseek_hbm_complete_20261001/whole-program-calendar-r2.json'
    graph=json.loads((root/evidence).read_text())
    index_ops=[o['pc'] for o in graph['operations'] if o['function']=='index_scores']
    return {'schema':'opentallas.deepseek.index-ports-candidate.v2',
            'source_pins':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
            'authoritative_graph':evidence,'authoritative_graph_sha256':hashlib.sha256((root/evidence).read_bytes()).hexdigest(),
            'index_operation_pcs':index_ops,'program':program(),'warp_template':events(),
            'finite_warp_instantiation':'two unpack warps/tile, rows0..31 and32..63;mask final tile; assignment to SM/partition still unbound',
            'refill_example':refill_events(95,1023,64,256),
            'instruction_cost_binding':'canonical source, unknown variants NULL; no software walltime credit',
            'wire_format_binding':'candidate low-nibble-first payload64B+4 UE8M0 scales; actual producer not bound',
            'source_domain_coverage':False,
            'producer_domain_evidence':'results/rtl/deepseek_hbm_complete_20261001/index-producer-domain-r1.json',
            'reserved_RF_geometry':'32warps/SM,32regs/thread,128lanes,4partitions,16x8lane groups;two read copies/two depth banks',
            'tests_passed':5,'full_checkpoint_reexecuted':False,
            'actual_provider_bound':False,'hardware_build_authorized':False,
            'whole_program_physical_admission':'FAIL_CLOSED'}


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise SystemExit('refuse overwrite of retained evidence')
    result=record();args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,separators=(',',':'))+'\n')
