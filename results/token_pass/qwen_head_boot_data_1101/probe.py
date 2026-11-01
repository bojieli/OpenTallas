import sys,json,hashlib,tempfile
from pathlib import Path
import numpy as np
R=Path('/srv/opentallas-scratch2/claude/codex-qwen-images-1101')
sys.path.insert(0,str(R/'head_boot_data1131/tools/qwen_layerbench'))
import head_boot_data as H
import dv_lower as D
import dv_lower_mat as M
own=D.ownership(slice_rtl='s8')
results=[]
for rank in range(8):
 b=R/f'recover_l0/banks/head_images/rank{rank}'
 meta=json.loads((b/'head_rom.json').read_text())
 records,scales=H.head_tables(meta,b/'matrix_scale_bf16.hex',own)
 fp=(np.array(scales,dtype=np.uint32)<<16).view(np.float32)
 expected=M.btab_stream(M.btab_layout(own),{'lm_head':fp})
 assert {(r['slice'],r['addr']):int(r['payload_hex'],16) for r in records} == {(s,a):v for s,rows in expected.items() for a,v in rows}
 # Decode actual table words independently at the native interface boundary.
 for r in records:
  w=int(r['native_word_hex'],16)
  assert w>>1027==r['addr'] and ((w>>1025)&3)==2 and ((w>>1024)&1)==1
  assert w&((1<<1024)-1)==int(r['payload_hex'],16)
 with tempfile.TemporaryDirectory() as t:
  p=Path(t)/'matrix_scale_bf16.hex'
  data=(b/'matrix_scale_bf16.hex').read_text(); p.write_text(('1' if data[0]!='1' else '2')+data[1:])
  try:H.head_tables(meta,p,own)
  except ValueError as e:assert 'digest' in str(e)
  else:raise AssertionError('changed scale accepted')
 results.append(dict(rank=rank,records=len(records),native_btab_matches_authority=True,scale_bitflip_rejected=True))
result=dict(status='PASS_DATA_ONLY',ranks=results,native_programme='NOT_LOWERED',native_crom_addresses='NOT_ASSIGNED',transport='NOT_INSTALLED')
(R/'head_boot_data1131/gate.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
