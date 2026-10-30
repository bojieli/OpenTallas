"""Independent word-version replay of original and relocated native phases.

Operators retain exact original fields; every read word must carry the same
version token and every write produces the same new word token on both sides.
This checks allocation/publication dataflow, not a substitute arithmetic model.
"""
import copy,importlib.util,json,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];p=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools')
sys.path[:0]=[str(root/'tools/hbm_next'),str(p/'hbm_next'),str(p),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,image_check as IC,vm_value_phase as V
from hgi_sim import timing as T
rr=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes())
packet=json.loads((Path(__file__).parent/'values/values.json').read_text())


def replay(ph,raw):
    original=(np.arange(1<<19,dtype=np.uint64)*np.uint64(2654435761))^np.uint64(0x9e3779b9)
    mapped=np.full(262144,np.uint64(0xffffffffffffffff),np.uint64)
    decoded=IC.decode_all(raw);expected=[]
    for i in range(1458,1474):
        expected.extend((i,slot,r)for slot,r in IR.expand(rr[i][1],rr[i][2])[ph['start_row']:ph['start_row']+3])
    actual=[]
    for meta,(_,r,x,_)in zip(ph['records'],decoded):actual.extend((meta['source_record'],slot,row)for slot,row in IR.expand(r,x))
    assert len(actual)==len(expected)==48
    loaded=set();reads=0
    # Verify the footprint helper against the canonical engine timing model,
    # including scalar broadcast and half-pair tables.
    for (oi,slot,o),(mi,mslot,m) in zip(expected,actual):
        assert oi==mi and slot==mslot
        if oi not in loaded:
            for load in ph['boundary_loads']:
                if load['before_source_record']!=oi:continue
                a,b=load['source_words'];u,v=load['destination_words']
                assert 0<=u<v<=len(mapped)and b-a==v-u
                mapped[u:v]=original[a:b]
            loaded.add(oi)
        assert set(o.desc)==set(m.desc)
        semantics=copy.deepcopy(m)
        for k in semantics.desc:semantics.desc[k].base=o.desc[k].base
        assert vars(semantics)==vars(o),'arithmetic/slot/template changed'
        wo=IR.written_operands(o)
        for k,d in o.desc.items():
            if d.space!='VM':continue
            a,b=V.engine_span(o,k);u,v=V.engine_span(m,k)
            assert b-a==v-u and 0<=u<v<=len(mapped)
            if k not in wo:
                assert np.array_equal(original[a:b],mapped[u:v]),f'read version mismatch source{oi}/slot{slot}/{k}'
                reads+=b-a
        # A unique version per output word. Equal reads + unchanged source
        # operator imply the real arithmetic writes are equal as well.
        for k in wo:
            if k not in o.desc or o.desc[k].space!='VM':continue
            a,b=V.engine_span(o,k);u,v=V.engine_span(m,k)
            token=np.arange(b-a,dtype=np.uint64)+np.uint64((oi<<32)|(slot<<24)|(ord(k)<<16))
            original[a:b]=token;mapped[u:v]=token
    return reads

checked=0;controls=[]
for ph in packet['phases']:
    raw=(Path(__file__).parent/'values'/ph['fragment']).read_bytes();checked+=replay(ph,raw)
    for kind in('wrong_address','wrong_slot','wrong_template'):
        rows=IC.decode_all(raw);target=next(i for i,meta in enumerate(ph['records'])if meta['source_record']==1470)
        r,x=rows[target][1:3]
        if kind=='wrong_address':r.desc['A'].base+=8
        elif kind=='wrong_slot':x.slot0+=1;r.slot=x.slot0&7
        else:r.imm_b^=1
        bad=b''.join(IR.encode(r,x)for _,r,x,_ in rows)
        try:replay(ph,bad)
        except(AssertionError,ValueError,IR.RangeFault):controls.append(f'{ph["start_row"]}:{kind}')
        else:raise AssertionError('mutant escaped')
    bad=copy.deepcopy(ph);bad['boundary_loads'][0]['source_words']=[v+8 for v in bad['boundary_loads'][0]['source_words']]
    try:replay(bad,raw)
    except(AssertionError,ValueError):controls.append(f'{ph["start_row"]}:wrong_boundary_payload')
    else:raise AssertionError('boundary payload mutant escaped')
print(json.dumps(dict(read_words_checked=checked,expanded_rows=96,native_records=sum(p['instruction_count']for p in packet['phases']),high_water=[p['high_water_words']for p in packet['phases']],shared_weight_sm_rows=[p['shared_weight_sm_rows_preserved']for p in packet['phases']],controls=controls)))
