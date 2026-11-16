from pathlib import Path
import sys,os,json,hashlib,shutil
r=Path('/tmp/token_ds_followthrough1116');source=r/'source';fixture=r/'gb_fixture';out=r/'gb_component/field'
sys.path[:0]=[str(source/'tools'),str(source/'tools/s81_dv'),str(source/'tools/s81_dv/layer_prog')]
os.environ.update(OT_S81_FRAME_SOURCE_ROOT=str(r/'f2s4_source'),OT_XS_FRAME_SCHEDULE_DIR=str(r/'f2s4_source/results/arch/s81_dv_1016/frame_l4_cluster/compiler'),OT_XS_APROJ_TOPO='1',OT_XS_APROJ_RANK_TAGS='1')
import numpy as np
import lower_xs as L,frame_bench as B
files=json.load(open(fixture/'files.json'))
def arr(n):
 d=files[n];p=fixture/n;assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256'];return np.fromfile(p,dtype=np.dtype(d['dtype'])).reshape(d['shape'])
rows=[4,5,6,7];m=L.FixMat('wq_a',arr('weights/wq_a.bin'),arr('weights/wq_a.scale.bin'),rows);x=arr('ops/attn.norm.scale.bin')
q,bf=B.frame_pairs('col_h10');field,ph,plan,qa,q,bf=L.frame_programme('col_h10_l4_lp',0x492,[m],x,iters=4000,pairs=q[:10],rank_rows=rows)
assert plan['faults']==0,plan['faults']
assert not out.exists();out.mkdir();images=out/'images';images.mkdir();L.field_images(field,qa,q,bf,'u_f_0L01',images,rank_rows=rows)
local=out/'images.phase_local';local.mkdir();shutil.copytree(images/'_field',local/'_field',copy_function=os.link)
meta=dict(frame='u_f_0L01',master='col_h10_l4',component_source_master='col_h10_l4_lp',source_scope='one actual GB-split pair contract, field label is the established native component filename ABI, not current physical whole-frame adoption',nphases=1,phases=[dict(phase=0,mat='wq_a',row_index=rows,nseg=L.NSEG,K=5120,faults=plan['faults'])],production_enabled=False)
(out/'field.json').write_text(json.dumps(meta,indent=2)+'\n');(out/'frame.json').write_text(json.dumps(meta,indent=2)+'\n')
print('GENUINE_GB_FIELD_READY',rows,'pairs',qa,'faults',plan['faults'])
