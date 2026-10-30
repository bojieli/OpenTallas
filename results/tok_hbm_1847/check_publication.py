"""Native record payload and malformed-publication controls on actual a122 rows."""
import copy,importlib.util,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
t=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools')
sys.path[:0]=[str(t/'hbm_next'),str(t),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,image_check as IC
from hgi_sim import records as RC
spec=importlib.util.spec_from_file_location('PUB',root/'tools/hbm_next/vm_phase_publication.py');PUB=importlib.util.module_from_spec(spec);spec.loader.exec_module(PUB)
p=json.loads((Path(__file__).parent/'native_publication.json').read_text())
prep=json.loads((root/'results/tok_hbm_1355/phase_1470.json').read_text())
assert PUB.replay(p,prep,IR)==245760
caught=[]
for name,change in [('wrong_hbm_word',lambda r,x:setattr(r.desc['A'],'base',r.desc['A'].base+4)),
                    ('wrong_row_stride',lambda r,x:x.rs.update(A=x.rs['A']-32)),
                    ('wrong_vm_destination',lambda r,x:setattr(r.desc['O'],'base',r.desc['O'].base+8))]:
    q=copy.deepcopy(p);pub=q['phases'][0]['publication'][0];raw=bytes.fromhex(pub['reload_hex']);r,x,_=IR.decode_one(raw,0);change(r,x);pub['reload_hex']=IR.encode(r,x).hex()
    try:PUB.replay(q,prep,IR)
    except (KeyError,ValueError):caught.append(name)
    else:raise AssertionError(name+' escaped')
q=copy.deepcopy(p);raw=bytes.fromhex(q['phases'][0]['consumer_hex']);r,x,_=IR.decode_one(raw,0);r.wait &= ~(1<<RC.UNITS.index('DMA'));q['phases'][0]['consumer_hex']=IR.encode(r,x).hex()
try:PUB.replay(q,prep,IR)
except ValueError:caught.append('consumer_outruns_dma')
else:raise AssertionError('consumer without DMA dependency escaped')
rr=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes())
for name,base,size in [('scratch_underflow',0xF000000000,983008),('scratch_unaligned',0xF000000001,983040)]:
    try:PUB.build(rr,1470,prep,base,size,IR,RC)
    except ValueError:caught.append(name)
    else:raise AssertionError(name+' escaped')
print(json.dumps(dict(payload_words=245760,producer_records=sorted({s['producer_record_index']for ph in p['phases']for s in ph['publication']}),caught=caught)))
