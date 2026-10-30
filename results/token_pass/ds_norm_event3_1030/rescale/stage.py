import hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
R=Path(sys.argv[1]);P=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-producer-1030');X=Path('/srv/opentallas-scratch2/claude/codex-ds-current-xfin-1030')
T=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029');sys.path.insert(0,str(T/'tools'));import hdc_golden_v41 as V
stage=json.loads((P/'stage.json').read_text());root=Path('/srv/opentallas-scratch2/claude/codex-s81-h2-bind-2249/frozen_source')
for name,digest in stage['source_sha256'].items():
 source=root/name
 assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
 target=R/'src'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
for name in ['source.f','defines.f','entry.memh','partial.memh']:shutil.copyfile(P/name,R/name)
shutil.copyfile(X/'actual_rstd.hex',R/'actual_rstd.hex')
rstd=np.array([int((R/'actual_rstd.hex').read_text(),16)],dtype=np.uint32).view(np.float32)[0]
entry=json.load(open('/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030/L14/entry_inputs.json'));out=[]
for sid in range(16):
 for leaf in range(5):
  mem={w['row']:int(w['data128'],16)for w in entry['writes']if w['sid']==sid and w['leaf']==leaf};h=np.zeros((4,64),dtype=np.float32)
  for j in range(8):
   for hf in range(2):
    word=mem[4*j+2*hf]|mem[4*j+2*hf+1]<<128
    for c in range(4):
     for lane in range(4):h[c,8*j+4*hf+lane]=np.array([((word>>(16*(4*c+lane)))&65535)<<16],dtype=np.uint32).view(np.float32)[0]
  pre=np.array([(mem[1008]>>(32*c))&0xffffffff for c in range(4)],dtype=np.uint32).view(np.float32)
  gains=np.array([(mem[64+i//4]>>(32*(i%4)))&0xffffffff for i in range(64)],dtype=np.uint32).view(np.float32)
  x=V.to_bf16(V.seqsum([V.mul(pre[c],h[c])for c in range(4)]));y=V.to_bf16(V.mul(V.mul(x,rstd),gains)).view(np.uint32)
  for j in range(8):out.append(f'{sum(int(y[8*j+l]>>16)<<(16*l)for l in range(8)):032x}')
(R/'expected_y.memh').write_text('\n'.join(out)+'\n')
stage.update(actual_rstd_sha256=hashlib.sha256((R/'actual_rstd.hex').read_bytes()).hexdigest(),
 actual_rstd_source='actual current16XF producer output,not golden norm result',scoreboard_only='independent actualH/pre/gains arithmetic with actualproducer rstd; expected_y never connects to hardware',
 clock_ps=833,source_expected_vectors=640,source_expected_BF16_elements=5120,global_RSTD_dates_qualified=False)
(R/'stage.json').write_text(json.dumps(stage,indent=1)+'\n')
