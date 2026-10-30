import hashlib,json,re,shutil,sys
from pathlib import Path
import numpy as np
TASK=Path(sys.argv[1]);S=Path('/srv/opentallas-scratch2/claude/codex-s81-h2-bind-2249/frozen_source')
T=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029');sys.path.insert(0,str(T/'tools'))
import hdc_golden_v41 as V
files=(S/'rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f').read_text().split()
files+=['rtl/hdc/v41x/ot_hbm_norm_split.sv','rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
 'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v']
for name in files:
 dest=TASK/'src'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/name,dest)
(TASK/'source.f').write_text('\n'.join('src/'+n for n in files)+'\n')
manifest=Path('/srv/opentallas-scratch2/claude/die-s81-34/h2bind/asbuilt_h2_frozen_d34.json');defines=json.loads(manifest.read_text())['defines']
(TASK/'defines.f').write_text('\n'.join('+define+'+d for d in defines)+'\n')
entry=json.loads(Path('/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030/L14/entry_inputs.json').read_text())
rows=[];partials=[]
for sid in range(16):
 for leaf in range(5):
  writes=[w for w in entry['writes']if w['sid']==sid and w['leaf']==leaf];assert len(writes)==49
  mem={w['row']:int(w['data128'],16)for w in writes}
  rows.extend(f'{w["row"]:04x}{w["data128"]}'for w in writes)
  h=np.zeros((4,64),dtype=np.float32)
  for j in range(8):
   for hf in range(2):
    word=mem[4*j+2*hf]|mem[4*j+2*hf+1]<<128
    for c in range(4):
     for lane in range(4):h[c,8*j+4*hf+lane]=np.array([((word>>(16*(4*c+lane)))&65535)<<16],dtype=np.uint32).view(np.float32)[0]
  pre=np.array([(mem[1008]>>(32*c))&((1<<32)-1)for c in range(4)],dtype=np.uint32).view(np.float32)
  x=V.to_bf16(V.seqsum([V.mul(pre[c],h[c])for c in range(4)]))
  partial=V.csum(V.mul(x,x));partials.append(f'{int(np.asarray(partial,dtype=np.float32).view(np.uint32)):08x}')
(TASK/'entry.memh').write_text('\n'.join(rows)+'\n');(TASK/'partial.memh').write_text('\n'.join(partials)+'\n')
(TASK/'stage.json').write_text(json.dumps(dict(source_sha256={n:hashlib.sha256((S/n).read_bytes()).hexdigest()for n in files},
 defines=defines,selected_manifest=str(manifest),selected_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
 entry_die_sha256=entry['die_sha256'],entry_words=3920,expected_partials=80,golden='checkpoint-derived H/pre -> BF16 sequential hc_pre -> chunk8 FP32 sum-of-squares',
 golden_source_sha256=hashlib.sha256((T/'tools/hdc_golden_v41.py').read_bytes()).hexdigest()),indent=1)+'\n')
print('STAGE current event3 VP/VN source,3920 legitimate store words,80 golden partials')
