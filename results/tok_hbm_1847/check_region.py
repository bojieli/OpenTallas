"""Check native dependency-region fragments against actual original expanded rows."""
import copy,importlib.util,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
t=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools');sys.path[:0]=[str(t/'hbm_next'),str(t),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,image_check as IC
spec=importlib.util.spec_from_file_location('REG',root/'tools/hbm_next/vm_phase_region.py');REG=importlib.util.module_from_spec(spec);spec.loader.exec_module(REG)
rr=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes())
packet=json.loads((Path(__file__).parent/'region/region.json').read_text())

def check(info,blob):
    native=IC.decode_all(blob);assert len(native)==16
    mappings=info['source_intervals']
    for i,m in enumerate(mappings):
        assert m['source'][1]-m['source'][0]==m['destination'][1]-m['destination'][0]
        assert 0<=m['destination'][0]<m['destination'][1]<=262144
        if i:assert mappings[i-1]['destination'][1]<=m['destination'][0]
    for (orig_i,(_,q,qx,_)) in zip(range(1458,1474),native):
        original=IR.expand(rr[orig_i][1],rr[orig_i][2])[info['start_row']:info['start_row']+2]
        after=IR.expand(q,qx)
        for (slot,r),(aslot,a) in zip(original,after):
            expected=copy.deepcopy(r)
            for d in expected.desc.values():
                if d.space=='VM':
                    for m in mappings:
                        lo,hi=m['source']
                        if lo<=d.base<hi:d.base=m['destination'][0]+d.base-lo;break
                    else:raise AssertionError('unmapped source')
            assert slot==aslot and vars(expected)==vars(a),'native row graph differs'
    return len(native)*2

checked=0;caught=[]
for info in packet['phases']:
    blob=(Path(__file__).parent/'region'/info['native_fragment']).read_bytes();checked+=check(info,blob)
    decoded=IC.decode_all(blob)
    for name in ('address','slot','template'):
        rows=copy.deepcopy(decoded)
        if name=='address':rows[12][1].desc['A'].base+=8
        elif name=='slot':
            rows[12][2].slot0+=1;rows[12][1].slot=rows[12][2].slot0&7
        else:rows[12][1].imm_a^=1
        mutant=b''.join(IR.encode(r,x)for _,r,x,_ in rows)
        try:check(info,mutant)
        except (AssertionError,ValueError,IR.RangeFault):caught.append(f'{info["start_row"]}:{name}')
        else:raise AssertionError('mutant escaped')
try:REG.make(rr,1458,1473,4,2,IR,reserve=50000)
except ValueError:caught.append('external_reserve_overflow')
else:raise AssertionError('external reserve falsely fits')
print(json.dumps(dict(expanded_rows=checked,high_water=[p['vm_high_water_words']for p in packet['phases']],caught=caught)))
