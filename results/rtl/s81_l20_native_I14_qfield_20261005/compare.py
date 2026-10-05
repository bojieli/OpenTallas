"""Compare native I14 fragments against released weights on actual produced QR."""
import os
os.environ.setdefault('HDC_V41_ARITH','chunk8')
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import v41_fullshape_isa as M
from dsrom_s81_execution_binding import CanonicalS81Execution
p=argparse.ArgumentParser();p.add_argument('--rank',type=int,choices=range(4),required=True);a=p.parse_args()
base=Path('/srv/opentallas-scratch2/jobs/cicero-s81-I14-native-r4');owner=Path('/srv/opentallas-scratch2/jobs/arch-s81-I14-fragment-caller-r2');job=base/f'rank{a.rank}'
t=json.loads((job/'chain-terminal.json').read_text());assert t['exit']==0
xfile=owner/'qnorm-r2/runtime'/f'native_L20_I13_rank{a.rank}.u32';x=np.fromfile(xfile,dtype='<u4').view(M.F);assert x.size==1280 and M.V.ARITH=='chunk8' and not M.V.FUSE
execution=CanonicalS81Execution(owner/'source');checkpoint=M.LC.Checkpoint(owner/'checkpoint/dba1be0a40aa45a94ad051997016db3960a90277');fragments=execution.source.resolve('L20.I14',a.rank)['fragments'];assert len(fragments)==2
xq,xe=M.V.quant_fp8(x);results=[];weight=None
for fidx,fragment in enumerate(fragments):
 run=job/f'fragment{fidx}';term=json.loads((run/'terminal.json').read_text());assert term['exit_code']==0 and term['rank']==a.rank and term['fragment']==fidx
 binding=json.loads((owner/f'controls-f{fidx}'/f'rank{a.rank}/I14/binding.json').read_text());instruction=binding['instruction'];matrix=fragment['matrix'];assert binding['phase']==20+fidx
 if weight is None:weight=M.V._blocked(checkpoint.get(matrix['tensor']),checkpoint.get(matrix['source_scale_tensor']),matrix['tensor'])
 shard=matrix['rank_slices'][a.rank];r0,r1=shard['rows'];c0,c1=shard['cols'];w=M.V.Q8(weight.q[r0:r1,c0:c1],weight.e[r0:r1,c0//32:c1//32]);assert w.shape==(instruction['qe_nout'],1280)
 blocks=[np.ldexp((w.q[:,b*32:(b+1)*32]@xq[b*32:(b+1)*32]).astype(M.F),w.e[:,b]+xe[b]).astype(M.F) for b in range(40)]
 reference=M.V.csum(np.stack(blocks,axis=-1))
 if not instruction.get('qe_unrounded',0):reference=M.G.to_bf16(reference)
 reference=M.G.bits(reference).astype('<u4');file=run/'runtime'/f'native_L20_I14_fragment{fidx}.u32';actual=np.fromfile(file,dtype='<u4');assert actual.shape==reference.shape
 bad=np.flatnonzero(actual!=reference);results.append(dict(fragment=fidx,phase=20+fidx,output_base=binding['output_base'],words=int(actual.size),bit_mismatches=int(bad.size),output_sha256=M.sha(file),first=[dict(row=int(i),actual=int(actual[i]),reference=int(reference[i])) for i in bad[:16]]))
record=dict(scope='Native I14 two canonical fragments on actual native I13 QR; initial I0-I6 prefix SIM_ONLY; no fulltoken or physicaltiming claim',rank=a.rank,position=1048575,token=16754,exact=all(r['bit_mismatches']==0 for r in results),expected_outputs_used_by_native=False,input_sha256=M.sha(xfile),source_inputs_sha256=execution.input_sha256,results=results)
with (job/'comparison.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(record),flush=True);raise SystemExit(0 if record['exact'] else 1)
