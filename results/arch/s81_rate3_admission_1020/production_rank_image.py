"""Verify actual full-field production cfg emission against native rank-tag frame vectors."""
import hashlib,json,os,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import xs_place as X
import dv_layer_compile as C
from field_cfg7_image import decode_bank
O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False);D=C.Die(C.die_tree(None,'/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'))
fr='u_f_0R03';rec,field=X.compile_frame(D,fr,'/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0',['attn.wq_b'],only=set())
assert rec['phases'][0]['row_index']==field.aproj_rank_rows==[28,29,30,31]
paths={}
for flag in ['0','1']:
 os.environ['OT_XS_APROJ_RANK_TAGS']=flag;o=O/('rank'+flag);o.mkdir()
 names,tmp=X.write_images(field,rec['pairs'],rec['q_pairs'],rec['bf_pairs'],fr,o);paths[flag]=(o,names)
changed=[]
for name in paths['0'][1]+['spine_phase.hex','spine_stream.hex']:
 a=(paths['0'][0]/name).read_bytes();b=(paths['1'][0]/name).read_bytes()
 if a!=b:
  assert '_c' in name and name.endswith('.viamap.hex'),name
  wa=decode_bank([int(x,16) for x in a.split()]);wb=decode_bank([int(x,16) for x in b.split()])
  assert wa[4:]==wb[4:],name
  assert all(((u^v)&~65535)==0 for u,v in zip(wa[:4],wb[:4])),name
  changed.append(name)
assert changed
# Native rank-tag golden vector used the independent single-phase writer.
V=Path('/srv/opentallas-scratch/codex/s81-rate3-admission-1020/out/aproj_rank_tags')/fr/'gold'
for name in paths['1'][1]:
 if '_c' not in name:continue
 other=V/('f'+name[len(fr):]);a=decode_bank([int(x,16) for x in (paths['1'][0]/name).read_text().split()]);b=decode_bank([int(x,16) for x in other.read_text().split()]);assert a[:4]==b[:4],name
r=dict(scope='ACTUAL_PRODUCTION_CFG_IMAGE_ONLY',source='d4350d97c',PASS=True,full_stage_qualified=False,
 changed_only_phase0_row_tags=True,weights_streams_nonphase0_cfg_unchanged=True,actual_native_vector_phase0_cfg_equal=True,
 changed_files=changed,rank_rows=field.aproj_rank_rows,
 files={flag:{name:hashlib.sha256((o/name).read_bytes()).hexdigest() for name in names+['spine_phase.hex','spine_stream.hex']} for flag,(o,names) in paths.items()})
(O/'image_check.json').write_text(json.dumps(r,indent=1)+'\n');print('PRODUCTION_RANK_IMAGE_PASS',len(changed),flush=True)
