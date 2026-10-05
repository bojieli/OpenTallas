"""Post-terminal native I20 comparison; VM output only, not WINDOW visibility."""
import os
os.environ.setdefault('HDC_V41_ARITH','chunk8')
from pathlib import Path
import json,re,hashlib
import numpy as np
import v41_fullshape_isa as M
base=Path('/home/ubuntu/cicero-s81-L20-native-I20-kquant-r1');t=json.loads((base/'terminal.json').read_text());assert t['exit']==0 and 'KQUANT_COMPLETE' in (base/'runtime.log').read_text()
source=Path('/home/ubuntu/arch-s81-I20-kquant-caller-r1/src/s81_minimum_l20_qnorm.cpp');m=re.search(r'\{2491,3,"([0-9a-f]+)",\{([^}]+)\}\}',source.read_text());assert m
words=[int(x.rstrip('u'),16) for x in m[2].split(',')];assert len(words)==64
literal=sum(x<<(32*i) for i,x in enumerate(words));assert hashlib.sha256(literal.to_bytes(256,'little')).hexdigest()==m[1]
f=M.I.decode(literal,full_shape=True);assert f['qe_mode']==M.I.QE_QDQ8 and f['qe_nb']==16 and f['qe_xbase']==54720 and f['qe_obase']==55232
results=[]
for rank in range(4):
 inputfile=Path(t['argv'][3+rank]);data=np.fromfile(inputfile,dtype='<u4').view(M.F);assert data.size==512
 r=M.Rank.__new__(M.Rank);r.r=rank;r.pos=1048575;r.stores=None;r.vm=np.zeros(M.VM_ELEMS,dtype=M.F);r.ok=np.zeros(M.VM_ELEMS,dtype=bool);r.unwritten=[];r.dyn=M.full_dyn(1048575,rank=rank);r.write(54720,data);r.qe(dict(f),20,[])
 if r.unwritten:raise ValueError(f'unwritten reference operands: {r.unwritten}')
 ref=r.vm[55232:55744].view(np.uint32);p=base/f'runtime/native_L20_I20_rank{rank}.u32';actual=np.fromfile(p,dtype='<u4');assert actual.shape==ref.shape
 bad=np.flatnonzero(actual!=ref);results.append({'rank':rank,'compared':512,'bit_mismatches':int(bad.size),'input_sha256':hashlib.sha256(inputfile.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'first':[{'index':int(i),'actual':int(actual[i]),'reference':int(ref[i])} for i in bad[:16]]})
record={'scope':'Native I20 QE mode1 fourrank KVQ on actual native I19 KVN; matched VM publication only, no currentWINDOW/HBMvisibility. I18coefficients/initialprefix SIM_ONLY. No fulltoken/physical timing claim.','position':1048575,'token':16754,'producer':2491,'source_cpp_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'literal_sha256':m[1],'source_arithmetic_sha256':hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest(),'expected_outputs_used_by_native':False,'exact':all(x['bit_mismatches']==0 for x in results),'results':results}
with (base/'comparison.json').open('x') as out:out.write(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True);raise SystemExit(0 if record['exact'] else 1)
