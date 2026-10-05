"""Post-run comparison only: actual QA/H/CROM into retained SU golden, no native replay."""
import os
os.environ.setdefault('HDC_V41_ARITH','chunk8')
import json,re,hashlib
from pathlib import Path
import numpy as np
import v41_fullshape_isa as M
if M.V.ARITH!='chunk8' or M.V.FUSE:raise ValueError('retained chunk8/unfused golden required')
j=Path('/home/ubuntu/cicero-s81-L20-native-I11-I13-qnorm-r2');b=Path('/home/ubuntu/arch-s81-I11-I13-qnorm-caller-r2');t=json.loads((j/'terminal.json').read_text())
if t['exit']!=0 or 'QNORM_COMPLETE' not in (j/'runtime.log').read_text():raise ValueError('completed native I11/I12/I13 required')
source=b/'s81_minimum_l20_qnorm.cpp';text=source.read_text();ops=[]
for pc in (2482,2483,2484):
 m=re.search(r'\{'+str(pc)+r',2,"([0-9a-f]+)",\{([^}]+)\}\}',text);words=[int(x.rstrip('u'),16) for x in m[2].split(',')];assert len(words)==64
 w=sum(x<<(32*i) for i,x in enumerate(words));assert hashlib.sha256(w.to_bytes(256,'little')).hexdigest()==m[1];ops.append(M.I.decode(w,full_shape=True))
crompath=Path(json.loads((j/'runtime.env.json').read_text())['DSROM_S81_MINIMUM_CROM_HEX']);data={};address=0
for line in crompath.read_text().splitlines():
 for word in line.split():
  if word.startswith('@'):address=int(word[1:],16)
  else:data[address]=int(word,16);address+=1
crom=np.zeros((max(data)+1,2),dtype='<u4');valid=np.zeros(len(crom),dtype=bool)
for a,w in data.items():crom[a]=[w&0xffffffff,w>>32];valid[a]=True
h=np.fromfile(t['argv'][-1],dtype='<u4')[:16].view(M.F);results=[]
for rank in range(4):
 qa=np.fromfile(t['argv'][3+rank],dtype='<u4').view(M.F);assert qa.size==1280
 r=M.Rank.__new__(M.Rank);r.r=rank;r.pos=1048575;r.stores=None;r.vm=np.zeros(M.VM_ELEMS,dtype=M.F);r.ok=np.zeros(M.VM_ELEMS,dtype=bool);r.unwritten=[];r.dyn=M.full_dyn(1048575,rank=rank);r.crom=crom.view(M.F);r.crom_ok=valid;r.rope_held={};r.write(0,h);r.write(51648,qa)
 for k,(addr,count) in enumerate(((51584,1),(51616,1),(52928,1280))):
  f=dict(ops[k])
  if k==2:f['c_base']+=10240 # SAME released q_norm binding as native constants.hpp; instruction itself unchanged.
  r.su(f,11+k,[])
  if r.unwritten:raise ValueError(f'unwritten golden operand: {r.unwritten}')
  ref=r.vm[addr:addr+count].view(np.uint32);p=j/f'runtime/native_L20_I{11+k}_rank{rank}.u32';actual=np.fromfile(p,dtype='<u4');assert actual.shape==ref.shape
  bad=np.flatnonzero(actual!=ref);results.append(dict(rank=rank,node=f'L20.I{11+k}',compared=count,bit_mismatches=int(bad.size),output_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),first=[dict(index=int(i),actual=int(actual[i]),reference=int(ref[i])) for i in bad[:8]]))
record=dict(scope='Native I11/I12/I13 on actual I9 QA; golden comparison after native terminal, no field I14/full token/timing qualification',source_cpp_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),crom_sha256=hashlib.sha256(crompath.read_bytes()).hexdigest(),initial_h_sha256=t['initial_h_sha256'],source_arithmetic_sha256=hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest(),expected_outputs_used_by_native=False,exact=all(x['bit_mismatches']==0 for x in results),results=results)
with (j/'comparison.json').open('x') as stream:stream.write(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True);raise SystemExit(0 if record['exact'] else 1)
