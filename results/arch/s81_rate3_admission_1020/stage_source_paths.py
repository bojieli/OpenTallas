"""Record actual selected source endpoint/landing paths before constructing a CAP stage vehicle."""
import hashlib,json,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import lower_xs as L
import dv_layer_compile as C
D=C.Die(C.die_tree(None,'/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'))
O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False)
r=dict(scope='SELECTED_SOURCE_PATH_INVENTORY_ONLY',source='d4350d97c',die_sha=D.die_sha,full_stage_qualified=False,slices={})
for sl in ['u_s_0S','u_s_2S','u_s_3S']:
 frames=D.frames_of(sl);links={}
 for name,lk in D.links.items():
  if any(src[0] in frames for src in lk['src']) and any(dst[0]==sl for dst in lk['dst']):links[name]=lk
 r['slices'][sl]=dict(master=D.inst[sl]['master'],params=D.inst[sl]['params'],slice_inputs={k:v for k,v in D.inst[sl]['conns'].items() if k in ['rt','rt_w','rt_e']},frames={f:dict(master=D.inst[f]['master'],ret_conns={k:v for k,v in D.inst[f]['conns'].items() if k in ['ret','rd']},lk=D.strap(f,'lk')) for f in frames},actual_frame_return_links=links)
paths=['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_capc2.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_p1.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv','tools/s81_dv/layer_prog/final_ffn.py','tools/s81_dv/layer_prog/lower_svc.py']
r['source_hashes']={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in paths}
r['cap_source_candidate']='slice source instantiates ot_s81sl_capc2: PINPIPE1/EDLY24/WL3DLY16; this is NOT the currently qualified landed CAP parent'
r['admission_requires']=['actual physical lane order and all registered frame-return ages','current CAP candidate record with per-port landing ages','native FIN/cfg lifetime and VP/gather producer-consumer evidence','selected all-expert stage map and source per-pair/cfg admission','PPATH SVC producer+MU occupancy for F8']
(O/'stage_source_paths.json').write_text(json.dumps(r,indent=1)+'\n');print('SOURCE_PATH_INVENTORY',json.dumps(r),flush=True)
