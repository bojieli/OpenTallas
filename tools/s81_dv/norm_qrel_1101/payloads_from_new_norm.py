from pathlib import Path
import sys,numpy as np,json,hashlib
src=Path('/srv/opentallas-scratch2/claude/wt/codex-s81b-1101');sys.path[:0]=[str(src/'tools'),str(src/'tools/s81_suhc')]
import hc_gate as HG
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');n=r/'new_down_norm_arith_v1';y=np.fromfile(n/'norm_y.u32','<u4').view(np.float32);assert y.size==5120;q=HG.g_quant(y);words=[]
for beat in range(80):
 word=0
 for k in range(2):
  e,c=q[2*beat+k];word|=int.from_bytes(bytes(np.asarray(c,np.uint8)),'little')<<(266*k);word|=(int(e)&1023)<<(266*k+256)
 bf=sum((int(v)>>16)<<(16*j)for j,v in enumerate(y[64*beat:64*(beat+1)].view('u4')));words.extend([word,bf])
out=r/'global_QREL_transport_v1/source';(out/'payloads.memh').write_text(''.join(f'{x:0256x}\n'for x in words));(out/'fresh_payload_source.json').write_text(json.dumps(dict(source_arithmetic_result=str(n/'result.json'),norm_y_sha256=hashlib.sha256((n/'norm_y.u32').read_bytes()).hexdigest(),fresh_new_source_assignment=True,old_partial_payloads_read=False,actual_native_producer_or_state_residency=False),indent=1)+'\n');print('FRESH_QREL_TRANSPORT_PAYLOADS',len(words))
