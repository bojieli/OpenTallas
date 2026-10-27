"""Carry canonical native phase types onto reviewed physical geometry; candidate only."""
import copy, hashlib, json, gzip
from pathlib import Path

def compose(physical, native):
    p=copy.deepcopy(physical)
    pp={x['name']:x for x in p['partitions']}; nn={x['name']:x for x in native['partitions']}
    assert pp.keys()==nn.keys(), 'partition inventory changed'
    assert physical['ports']==native['ports'], 'external buses changed'
    assert physical['lanes']==native['lanes'], 'lane cycles changed'
    types={}; mapping={}
    for name,n in nn.items():
        old=pp[name]['type']; new=n['type']; mapping.setdefault(new,set()).add(old)
    for new,oldset in mapping.items():
        assert len(oldset)==1,(new,oldset)
        old=next(iter(oldset)); t=copy.deepcopy(physical['partition_types'][old]); nt=native['partition_types'][new]
        for key in ('outline_um','buses','hard_cores','internal_stations'):
            assert t.get(key)==nt.get(key),(new,key,'native geometry differs')
        # Native representative IDs/module naming define the exact source class.
        # All clock/FT positions and cost estimates stay with the reviewed physical input.
        t['module']=nt['module'];t['contents']=copy.deepcopy(nt['contents'])
        t['note']=t.get('note','')+' Native phase/support identity from af589e572a; physical cell estimate inherited pending fresh mapped census.'
        types[new]=t
    for name,n in nn.items():pp[name]['type']=n['type']
    # Retain unused families so the generator/clock family inventory remains explicit.
    for key,t in physical['partition_types'].items():types.setdefault(key,copy.deepcopy(t))
    p['partition_types']=types
    # Cached lane prices are recomputed by gen.py latency; input routes/cycles are identical.
    p.pop('latency',None)
    return p,{'input_types':len(physical['partition_types']),'native_types':len(native['partition_types']),
              'output_types':len(types),'changed_partitions':sum(pp[k]['type']!=next(x['type'] for x in physical['partitions'] if x['name']==k) for k in pp),
              'new_types':sorted(set(types)-set(physical['partition_types'])),
              'gates':'CANDIDATE: strict bind, actual FF capacity, final clock islands and G0 remain required'}

if __name__=='__main__':
    import sys
    r=Path(sys.argv[1]);a=json.loads(gzip.decompress((r/'physical_input.json.gz').read_bytes()));b=json.loads(gzip.decompress((r/'native_input.json.gz').read_bytes()))
    p,rec=compose(a,b);(r/'candidate_native100.json').write_text(json.dumps(p,indent=1)+'\n');(r/'compose_receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
