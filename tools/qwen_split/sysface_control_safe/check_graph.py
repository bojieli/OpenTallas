#!/usr/bin/env python3
"""Independent sequential-correspondence proof, without importing the generator.

Every original combinational/memory equation must remain exact. Every extra
state bit must be a same-edge copy with identical reset/enable priority, except
the separately proved balanced three-edge reset forest. This proves induction
after asserted reset; unreset payload FF copies require their common first
sampling edge, exactly like the original initialization contract.
"""
import argparse,collections,hashlib,json
from pathlib import Path

def check(original, candidate, receipt):
    o=original['modules']['qfd_sys_face']; c=next(iter(candidate['modules'].values()))
    cells=c['cells']; origins=receipt['origins']; rr=receipt['reset_chain_original']
    extra={x['port']: {'direction':'input','bits':[x['bit']]} for x in receipt.get('input_capture_copies',[])}
    assert c['ports']==dict(o['ports'],**extra), 'public/core alias port graph changed'
    assert set(cells)==set(origins), 'unaccounted cell'
    buf={n:x for n,x in cells.items() if x['type']=='BUFx2_ASAP7_75t_R'}
    forest={x['cell']:x for x in receipt['forest']}
    state_alias={x['bit']:x['original_bit'] for x in receipt.get('input_capture_copies',[])}
    for n,x in cells.items():
        old=origins[n]
        if old is not None and ('Q' in x['connections'] or (receipt.get('useful_cones') and 'Y' in x['connections'])):
            pin='Q' if 'Q' in x['connections'] else 'Y'
            state_alias[x['connections'][pin][0]]=o['cells'][old]['connections'][pin][0]
    for n,f in forest.items():state_alias[f['q']]=rr[f['depth']-1]
    buffer_alias={x['connections']['Y'][0]:x['connections']['A'][0] for x in buf.values()}
    def canon(b,seen=None):
        seen=set() if seen is None else seen
        assert b not in seen, 'buffer cycle'
        if b in buffer_alias:return canon(buffer_alias[b],seen|{b})
        return state_alias.get(b,b)
    def con(x):return {p:[canon(b) for b in bb] for p,bb in x['connections'].items()}
    original_cells={n:x for n,x in o['cells'].items() if x['type']!='$scopeinfo'}
    removed=set(receipt['removed_reset_cells'])
    assert len(removed)==3
    assert {original_cells[n]['connections']['Q'][0] for n in removed}==set(rr)
    covered=collections.Counter()
    drivers=collections.defaultdict(list);loads=collections.Counter()
    for n,x in cells.items():
        assert all(bb for bb in x['connections'].values()), 'empty connection'
        assert set(x['connections'])==set(x['port_directions']), 'untyped pin'
        for p,bb in x['connections'].items():
            for b in bb:
                if x['port_directions'][p]=='output':drivers[b].append((n,p))
                else:loads[b]+=1
        if origins[n] is not None:
            old=origins[n];covered[old]+=1
            assert old in original_cells and old not in removed
            assert x['type']==original_cells[old]['type'], 'primitive/reset kind changed'
            assert x['parameters']==original_cells[old]['parameters'], 'parameters changed'
            assert x['port_directions']==original_cells[old]['port_directions']
            assert con(x)==original_cells[old]['connections'], 'D/clock/reset/enable/equation changed: '+n
        elif n in buf:
            assert set(x['connections'])=={'A','Y'}
            assert x['port_directions']=={'A':'input','Y':'output'}
        else:
            assert n in forest, 'unaccounted new functional cell'
            f=forest[n]; assert x['type']=='$_DFF_PN0_'
            assert x['connections']['C']==[receipt['clock']]
            assert x['connections']['D']==['1']
            assert x['connections']['Q']==[f['q']]
            reset=canon(x['connections']['R'][0])
            assert reset==(o['ports']['rst_n']['bits'][0] if f['depth']==1 else rr[f['depth']-2])
    assert set(covered)==set(original_cells)-removed, 'lost original equation'
    input_bits={b for p in c['ports'].values() if p['direction']=='input' for b in p['bits']}
    for b,nn in drivers.items(): assert len(nn)==1 and b not in input_bits, 'multiply driven signal'
    for b in loads:
        assert isinstance(b,str) or b in input_bits or b in drivers, 'undriven input'
        if not receipt.get('useful_cones') and b!=receipt['clock'] and isinstance(b,int):assert loads[b]<=24, 'fanout exceeded'
    for p in c['ports'].values():
        if p['direction']=='output':
            for b in p['bits']:assert isinstance(b,str) or b in drivers or b in input_bits
    # Exact original reset chain, not an assumed three-cycle label.
    for depth,n in enumerate(sorted(removed,key=lambda n:rr.index(original_cells[n]['connections']['Q'][0]))):
        x=original_cells[n];assert x['type']=='$_DFF_PN0_'
        assert x['connections']['C']==[receipt['clock']]
        assert x['connections']['R']==o['ports']['rst_n']['bits']
        assert x['connections']['D']==(['1'] if depth==0 else [rr[depth-1]])
    return {'sequential_correspondence':'PASS', 'original_equations':len(covered),
            'same_edge_copies':sum(v-1 for v in covered.values()),
            'reset_forest_ff':len(forest),'native_buffers':len(buf),
            'max_nonclock_load':max(v for b,v in loads.items() if isinstance(b,int) and b!=receipt['clock']),
            'macro_counts':dict(collections.Counter(x['type'] for x in cells.values() if x['type'].startswith('ot_'))),
            'clock_pins':loads[receipt['clock']], 'undriven':0,'multiply_driven':0}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('original');ap.add_argument('candidate');ap.add_argument('receipt');ap.add_argument('--out');a=ap.parse_args()
    receipt=json.loads(Path(a.receipt).read_text())
    assert hashlib.sha256(Path(a.original).read_bytes()).hexdigest()==receipt['source_graph_sha256']
    result=check(json.loads(Path(a.original).read_text()),json.loads(Path(a.candidate).read_text()),receipt)
    print(json.dumps(result,sort_keys=True))
    if a.out:Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
