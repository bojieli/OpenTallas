from pathlib import Path
import json,shutil,subprocess,sys,re
l=Path('/srv/opentallas-scratch2/claude/codex-kv-cores-0809');w=Path('/srv/opentallas-scratch2/claude/wt/codex-kv-cores-0809');p=l/'q1_proposal';k=l/'q1_struct'
base=Path('/srv/opentallas-scratch2/claude/kv-cores-pv/kits/qkd_ectlk_q1__216x172.8')
shutil.copytree(base,k)
(k/'PARENT_PROVENANCE.json').write_bytes((k/'PROVENANCE.json').read_bytes())
sys.path.insert(0,str(w/'physical/die_plan/qwen_kvsys/cores/harden'));import gen_core_kit_kv as g
pins=json.load(open(p/'qkd_ectlk_q1_pins.json'))['pins'];io,rows=g.io_tcl(pins,216,172.8,'qkd_ectlk_q1__216x172.8',{'ck[0]'})
(k/'io.tcl').write_text(io);(k/'pins.json').write_text(json.dumps(rows)+'\n')
shutil.copyfile(p/'q1_macro_plan.tcl',k/'q1_macro_plan.tcl')
s=subprocess.check_output(['git','-C',str(w),'show','70264d75fd:tools/die_plan/face_flops.tcl'],text=True)
old=(k/'face_flops.tcl').read_text();skip=next(z for z in old.splitlines() if z.startswith('set ff_skip_re '));s=re.sub(r'^set ff_skip_re .*',lambda m:skip,s,flags=re.M);(k/'face_flops.tcl').write_text('source /work/kvr2_reserve.tcl\n'+s)
helper=subprocess.check_output(['git','-C',str(w),'show','6d6cf6b839:results/kv_cores_r6/tools/pass1_reserve.py'],text=True);(l/'q1_pass1_reserve.py').write_text(helper)
subprocess.run(['python3',str(l/'q1_pass1_reserve.py'),str(p/'q1_slice.json'),str(k)],check=True)
cfg=k/'config.mk';cfg.write_text(cfg.read_text()+'\nexport MACRO_PLACEMENT_TCL = /work/q1_macro_plan.tcl\n')
r=k/'run/results/asap7/hc_qkd_ectlk_q1__216x172_8/base'
for f in r.iterdir():
 if f.name.startswith(('2_','3_')):f.unlink()
(k/'native_struct.tcl').write_text('set ::env(RESULTS_DIR) /work/native_struct\nfile mkdir $::env(RESULTS_DIR)\nread_db /work/run/results/asap7/hc_qkd_ectlk_q1__216x172_8/base/2_4_floorplan_pdn.odb\nsource /work/face_flops.tcl\nwrite_db /work/native_struct/face.odb\nputs Q1_STRUCT_NATIVE_DONE\n')
print('Q1_STRUCT_PREPARED unchangedmappedRTL; newpinentry, macroplan, legalnearestfacehelper702')
