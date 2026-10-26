from pathlib import Path
import sys,json,hashlib
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019')
sys.path[:0]=[str(D/'tools'),str(D/'tools/hbm_static'),str(D/'tools/hgi_adapters')]
from hbm_layer_vehicle import layer_images as LI
from hbm_layer_vehicle.native_profile import NativeTiming
import su_bench as SB,su_arith_lower as L,su_program_inventory as I
from su_arith_generate import FIELDS
F=D/'results/rtl/hbm_ds_layer_tput_1018/fixtures/L00'
records=LI.ds_dispatches_image(F/'images/ds_v41_1M_L00_per_die.json')
entries=json.loads((F/'records.json').read_text())['records']['0']
entry=next(x for x in entries if x['k_layer']==6)
fixture=LI.load_fixture(F)[entry['priced'][0]['i']];raw=SB.pack_rec(records[6][1])
row,sched=L.lower(raw);dispatch,unit,sut,desc=I.decode(raw)
off={};pos=0
for n,w in reversed(FIELDS):off[n]=pos;pos+=w
get=lambda v,n:(v>>off[n])&((1<<dict(FIELDS)[n])-1)
r=LI.su_record(raw,data=dict(fixture['vm_in']),pad_zero=True,timing=NativeTiming(18,15))
LI.fixture_check(r,fixture)
groups=[]
for g,words in enumerate(sched):
 for q,w in enumerate(words):
  ls=get(w,'ls');ov=get(w,'o_v');iv=get(w,'i_v');terms=get(w,'ld_c');vb=get(w,'vb')
  active=[l for l in range(128) if ov+(l>>ls)<desc['A'].m and iv+(l&((1<<ls)-1))<dispatch['n'][0]]
  addrs={role:[((vb>>(24*s))&0xffffff)+sum((terms>>(24*(s*10+k)))&0xffffff for k in range(7) if l>>k&1) for l in active] for s,role in enumerate('ABCDO') if role in desc}
  groups.append(dict(group=g,quarter=q,o_v=ov,i_v=iv,active_lanes=len(active),roles={k:dict(first=min(v),last=max(v),words=len(v),logical_sectors=sorted(set(a//8 for a in v))) for k,v in addrs.items()}))
o=dict(scope='MODEL ONLY; legacy calendar is a failed-control candidate, not numerical RTL qualification',record=6,tag=fixture['tag'],lowering=row,sut=sut,descriptors={k:vars(v) for k,v in desc.items()},fixture_input_words=len(fixture['vm_in']),fixture_output_words=len(fixture['vm_out']),groups=groups,legacy_calendar={k:r.get(k) for k in ['status','reasons','fixture','setup_edge','issue_edges','last_commit','fill_sectors','drain_sectors']},physical_preload={str(k):v for k,v in r['preload'].items()},physical_outputs=r['expect'],programme_rows=len(r['lines']),programme_capacity=128,fixture_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [F/'records.json',F/'operands.npz',F/'images/ds_v41_1M_L00_per_die.json']})
import numpy as np
from hgi_sim import lib as A
z=np.load(F/'operands.npz');x=np.asarray(z['r0.k6.A'],np.uint32).view(np.float32)
gold=np.asarray(A.csum(A.mul(x,x)),np.float32).view(np.uint32).reshape(-1)
down=next(t for t in entries if t['tag']=='q_norm.rs')
consumer=np.asarray(z[down['inputs']['A']['array']],np.uint32).reshape(-1)
assert list(gold)==list(consumer),(gold,consumer)
o.update(exact_fixture_entry=entry,downstream_consumer=down,recovered_gold=dict(method='unchanged q_norm.rs A operand, independently matches original csum8(mul(A,A))',bits=[f'{int(v):08x}' for v in gold],matches=True),index_ledger=[dict(hgi_record=k,hgi_tag=records[k][0].tag,fixture=[dict(k_layer=t['k_layer'],tag=t['tag'],priced=t.get('priced')) for t in entries if t['tag']==records[k][0].tag]) for k in [6,11,23,33,50]])
_,u23,s23,d23=I.decode(SB.pack_rec(records[23][1]));o['tested_record23']=dict(unit=u23,sut=s23,descriptors={k:vars(v) for k,v in d23.items()})
o['programme_capacity']=7111
o['programme_capacity_basis']=dict(sram_rows_per_bank=128,packed_indices_per_row=16,index_banks=4,physical_index_slots=8192,enforced_edges=7111,source_sha256=hashlib.sha256((D/'rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme_pgcol.sv').read_bytes()).hexdigest())
for g in groups:
 role=g['roles']['A'];start=(role['first']-desc['A'].base)//8;end=(role['last']-desc['A'].base+1)//8
 frags=[];s=start
 while s<end:
  size=1
  while s%(size*2)==0 and s+size*2<=end:size*=2
  frags.append([s,s+size]);s+=size
 g.update(global_chunk_interval=[start,end],aligned_binary_fragments=frags,required_vm_ports=list(range(8 if g['quarter'] in (0,2) else 4)))
o['reduction_model']=dict(original_words=1280,original_chunks8=160,padded_tree_leaves=256,aligned_fragments=sum(len(g['aligned_binary_fragments']) for g in groups),single_128_word_pretree_safe=all(len(g['aligned_binary_fragments'])==1 for g in groups),full_token=False,numerical_rtl=False)
print(json.dumps(o,indent=2,default=lambda x:int(x)))
