from pathlib import Path
import os,sys,json,time
W=Path("/srv/opentallas-scratch2/claude/wt/codex-ds-compiler-1101");R=Path("/srv/opentallas-scratch2/claude/codex-ds-compiler-1101/idle_full_field_batch")
F=Path("/srv/opentallas-scratch2/claude/tok-ds-2/l0prog");R.mkdir(parents=True,exist_ok=False)
os.environ.update(OT_S81_SELECTED_SOURCE_ROOT=str(W),OT_S81_SELECTED_ASBUILT_MANIFEST="asbuilt_kva3_g3tag2_sel.json",
 OT_S81_SELECTED_CHILD_FILES="rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv",
 OT_XS_ASB_SCHEDULE_DIR=str(F/"fs"),OT_XS_FRAME_SCHEDULE_DIR=str(F/"try2/frame_schedules"),
 OT_XS_GB_PROVIDER_UNDER_TEST="1",OT_XS_Q_CPR="1",OT_XS_APROJ_TOPO="1",OT_XS_APROJ_ALIGN4="1",OT_XS_APROJ_RANK_TAGS="1",OT_XS_DENSE_SPLIT2="B",OT_XS_APROJ_CAP_PLAN="1")
M="/srv/opentallas-scratch2/claude/die-s81-46/bind_g3tag2/asbuilt.json";os.environ["OT_S81_SELECTED_DEFINES"]=",".join(json.load(open(M))["defines"])
sys.path[:0]=[str(W/"tools"),str(W/"tools/s81_dv")]
import dv_layer_compile as C
sys.path.insert(0,str(W/"tools/s81_dv/layer_prog"))
import importlib.util
spec=importlib.util.spec_from_file_location("xs_place_idle",str(R.parent/"xs_place_idle2.py"))
X=importlib.util.module_from_spec(spec);spec.loader.exec_module(X)
import traceback,hashlib
frames=['u_f_'+x for x in '1L03 1L13 3L03 3L13 4R03 4R13 6R03 6R13 7L10 7L12 7L13 7R02 7R03 7R10 7R12 7R13'.split()]
die=C.Die(F/'veh/tree_b178')
fixpath=F/'fix/L0'
fx=X.Fix(fixpath);aproj=X.LX.load_fixture(fixpath)
X.Fix=lambda path:fx
X.LX.load_fixture=lambda path:aproj
ops=X.XS_OPS['L0']+X.BF_OPS['L0']
groups={op:[{k:v for k,v in g.items() if k in ('rows','cap_tags')} for g in X.op_groups(fx,op)] for op in ops if op not in X.BF_OPS['L0']}
manifest=dict(status='RUNNING',source_commit='3cd16f543',selected_source=str(W),fixture=str(fixpath),die=str(F/'veh/tree_b178'),frames=frames,
 source_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R.parent/'xs_place_idle2.py',R.parent/'field_rank_images.py']},
 env={k:v for k,v in os.environ.items() if k.startswith('OT_')},production_enabled=False,qualification='full fixture fields; BF capture tags/timing, source lifetimes, transport and whole-token calendar remain unqualified',results=[])
(R/'groups.json').write_text(json.dumps(groups,indent=1)+'\n')
for frame in frames:
 dest=R/frame;dest.mkdir(exist_ok=False)
 try:
  if frame=='u_f_7L10':
   existing=R.parent/'idle_full_field'
   if not (existing/'status').read_text().startswith('BUILT_SOURCE_ONLY'):raise ValueError('pilot did not finish source build')
   result=dict(frame=frame,status='REUSED_SOURCE_PILOT',path=str(existing))
  else:
   rec,field=X.compile_frame(die,frame,fixpath,ops)
   assert rec['phases'][0]['idle_no_issue'] and rec['phases'][0]['rows']==0
   (dest/'field.json').write_text(json.dumps(rec,indent=1)+'\n')
   names,_=X.write_images(field,rec['pairs'],rec['q_pairs'],rec['bf_pairs'],frame,dest/'images',
     rank_context=dict(field=rec,groups=groups,already_ranked=[0]))
   result=dict(frame=frame,status='BUILT_SOURCE_ONLY',path=str(dest),phases=rec['nphases'],images=len(names),max_fill=max(rec['fill']),depth=rec['depth'])
  (dest/'status').write_text(result['status']+'\n')
 except Exception as exc:
  result=dict(frame=frame,status='FAIL',error=str(exc));(dest/'status').write_text('FAIL '+str(exc)+'\n');(dest/'traceback.txt').write_text(traceback.format_exc())
 manifest['results'].append(result)
 (R/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(result,flush=True)
manifest['status']='PARTIAL_SOURCE_IMAGES' if all(r['status']!='FAIL' for r in manifest['results']) else 'FAILURES_COLLECTED'
(R/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(R/'status').write_text(manifest['status']+'\n')
