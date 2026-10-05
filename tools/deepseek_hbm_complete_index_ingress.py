"""Candidate finite 68B index ingress, ordinary integer unpack and shared layout.

Wire proposal:64 low-nibble-first E2M1 bytes then four UE8M0 bytes.
Actual producer/allocator binding is pending; no physical service timing credit.
"""
import numpy as np
import deepseek_hbm_complete_index as X

TILE=64
QUERY_BASE=0
KEY_BASE=16384
QUERY_SCALE_BASE=49152
KEY_SCALE_BASE=49664
END=50688

def program():
    p=[]
    for j in range(128):
        p += [X.K.ins('LOAD','packed',f'byte{j//2}'),X.K.ins('SHR','code','packed',4*(j%2)),X.K.ins('AND','code','code',15),X.K.ins('MOV','unit',0)]
        # Ordinary compare/bit mask selection, no free native table lookup.
        for code,unit in enumerate(X.K.UNITS):
            p += [X.K.ins('IEQ','take','code',code),X.K.ins('ISUB','mask',0,'take'),X.K.ins('AND','part','mask',unit & 0xffffffff),X.K.ins('OR','unit','unit','part')]
        p += [X.K.ins('STORE',f'unit{j}','unit')]
    for b in range(4):
        p += [X.K.ins('LOAD','scale',f'byte{64+b}'),X.K.ins('ISUB','exponent','scale',126),X.K.ins('STORE',f'exp{b}','exponent')]
    return p

def unpack(rows):
    rows=np.asarray(rows)
    if rows.dtype!=np.uint8 or rows.ndim!=2 or rows.shape[1]!=68 or not 1<=len(rows)<=TILE:raise ValueError('bounded uint8 68B key rows')
    # This scope keeps every decoded value exactly representable after BF16.
    # More extreme scales require explicit producer rounding/overflow handling.
    if np.any(rows[:,64:]<1) or np.any(rows[:,64:]>252):raise ValueError('producer BF16 boundary not admitted')
    pad=(-len(rows))%32;v=np.pad(rows,((0,pad),(0,0)))
    m=X.SIMT((len(v)//32,32),{f'byte{j}':v[:,j].reshape(-1,32).astype(np.uint32) for j in range(68)}).run(program())
    units=np.stack([m.stores[f'unit{j}'].view(np.int32).reshape(-1)[:len(rows)] for j in range(128)],axis=-1)
    exponents=np.stack([m.stores[f'exp{j}'].view(np.int32).reshape(-1)[:len(rows)] for j in range(4)],axis=-1)
    return units,exponents,m

def address(family,term,lane):
    if family=='query' and 0<=term<128 and 0<=lane<32:return QUERY_BASE+4*(term*32+lane)
    if family=='key' and 0<=term<128 and 0<=lane<TILE:return KEY_BASE+4*(term*TILE+lane)
    raise ValueError('finite staging address')

def tile_contract(rank,start,count,base):
    if not 0<=rank<96 or start<0 or not 1<=count<=TILE or base<0 or base%256:raise ValueError('owner tile/aligned region')
    first=base+start*68;last=first+count*68
    sector0=first//32;sectorend=(last+31)//32
    requests=[{'sector_address':s,'length_sectors':min(16,sectorend-s),'bytes_per_sector':32} for s in range(sector0,sectorend,16)]
    ids=[(i//8)*768+rank*8+i%8 for i in range(start,start+count)]
    return {'rank':rank,'global_ids':ids,'local_row_start':start,'count':count,'requests':requests,
      'valid_byte_range':[first,last],'neighbor_sector_bytes_discarded':True,
      'shared_allocation_bytes':END,'shared_capacity_bytes':65536,'shared_bank_count':32,'shared_bank_word_bytes':4,
      'layout':{'query':'word=term*32+head;32 unique banks','key':'word=4096+term*64+tile_row;unpack warp adjacent rows unique banks;score warp single-row broadcast',
                'query_scales':[QUERY_SCALE_BASE,KEY_SCALE_BASE],'key_scales':[KEY_SCALE_BASE,END]},
      'lease_dependencies':['req_accept reserves tag/epoch','actual backend return matches tag/epoch','return bytes staged before unpack issue','unpack RF writeback before shared store','shared store visible before score LOAD','all score consumers done before tile overwrite','reverseCDC credit return before slot reuse'],
      'lease_events_actual':False,'production_wire_binding':None,'qualified_cycles':None,'physical_admission':'FAIL_CLOSED'}
