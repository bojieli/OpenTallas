"""Post-terminal native RoPE comparison on actual carry and staged coefficients."""
import os
os.environ.setdefault('HDC_V41_ARITH','chunk8')
import sys,json,re,hashlib
from pathlib import Path
import numpy as np
import v41_fullshape_isa as M
pc=int(sys.argv[1]);assert pc in (19,23)
base=Path(f'/home/ubuntu/cicero-s81-L20-native-I{pc}-rope-r1');t=json.loads((base/'terminal.json').read_text());assert t['exit']==0
marker='KROPE_COMPLETE' if pc==19 else 'QROPE_COMPLETE';assert marker in (base/'runtime.log').read_text()
assert M.V.ARITH=='chunk8' and not M.V.FUSE
source=Path('/home/ubuntu/arch-s81-I19-I23-rope-caller-r2/src/s81_minimum_l20_qnorm.cpp');text=source.read_text();producer=2490 if pc==19 else 2494
m=re.search(r'\{'+str(producer)+r',2,"([0-9a-f]+)",\{([^}]+)\}\}',text);assert m
words=[int(x.rstrip('u'),16) for x in m[2].split(',')];assert len(words)==64
literal=sum(x<<(32*i) for i,x in enumerate(words));assert hashlib.sha256(literal.to_bytes(256,'little')).hexdigest()==m[1]
f=M.I.decode(literal,full_shape=True)
crompath=Path(json.loads((base/'runtime.env.json').read_text())['DSROM_S81_MINIMUM_CROM_HEX']);lines=crompath.read_text().splitlines()
assert lines[:2]==['// SIM_ONLY_ROPE_COEFFICIENTS position1048575 kind1','@1f400'] and len(lines)==34
pairs=np.array([[int(line,16)&0xffffffff,int(line,16)>>32] for line in lines[2:]],dtype='<u4').view(M.F);assert pairs.shape==(32,2)
h=np.fromfile(t['argv'][-1],dtype='<u4')[:16].view(M.F);count=512 if pc==19 else 8192;address=54720 if pc==19 else 55744;results=[]
for rank in range(4):
 inputfile=Path(t['argv'][3+rank]);data=np.fromfile(inputfile,dtype='<u4').view(M.F);assert data.size==count
 r=M.Rank.__new__(M.Rank);r.r=rank;r.pos=1048575;r.stores=None;r.vm=np.zeros(M.VM_ELEMS,dtype=M.F);r.ok=np.zeros(M.VM_ELEMS,dtype=bool);r.unwritten=[];r.dyn=M.full_dyn(1048575,rank=rank)
 r.crom=np.zeros((1,2),dtype=M.F);r.crom_ok=np.zeros(1,dtype=bool)
 # Actual staged I18 input coefficients, not expected RoPE outputs.
 # Retained golden enforces kind1/position1048575 addresses and reduction order.
 r.rope_held={1:(1048575,(pairs[:,0],pairs[:,1]))};r.write(0,h);r.write(address,data);r.su(dict(f),pc,[])
 if r.unwritten:raise ValueError(f'unwritten reference operands: {r.unwritten}')
 actualfile=base/f'runtime/native_L20_I{pc}_rank{rank}.u32';actual=np.fromfile(actualfile,dtype='<u4');ref=r.vm[address:address+count].view(np.uint32);assert actual.shape==ref.shape
 bad=np.flatnonzero(actual!=ref);results.append({'rank':rank,'node':f'L20.I{pc}','compared':count,'bit_mismatches':int(bad.size),'input_sha256':hashlib.sha256(inputfile.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(actualfile.read_bytes()).hexdigest(),'first':[{'index':int(i),'actual':int(actual[i]),'reference':int(ref[i])} for i in bad[:16]]})
record={'scope':f'Native I{pc} allfourranks on actual produced carry; I18 coefficients/initialprefix SIM_ONLY, no fulltoken or physical clock claim','position':1048575,'token':16754,'producer':producer,'source_cpp_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'literal_sha256':m[1],'coefficient_file_sha256':hashlib.sha256(crompath.read_bytes()).hexdigest(),'coefficient_staging':'SIM_ONLY I18 kind1/position1048575, same actual coefficients supplied to native and post-run reference','source_arithmetic_sha256':hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest(),'expected_outputs_used_by_native':False,'exact':all(x['bit_mismatches']==0 for x in results),'results':results}
with (base/'comparison.json').open('x') as out:out.write(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True);raise SystemExit(0 if record['exact'] else 1)
