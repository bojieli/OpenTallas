from pathlib import Path
import json,subprocess,shutil
B=Path('/srv/opentallas-scratch/jobs/laplace-qwen-tagged-accept1-a60af57e4-r1')
R=B/'top_resume_r2'
S=Path('/srv/opentallas/repos/laplace-qwen-tagged-accept1-a60af57e4')
RT=Path('/srv/opentallas/repos/laplace-qwen-runtime-f6c5e4af1')
R.mkdir(exist_ok=True)
def phase(name,cmd):
 with (R/(name+'.log')).open('x') as log:
  p=subprocess.Popen(cmd,cwd=S,stdout=log,stderr=subprocess.STDOUT)
  (R/'state.json').write_text(json.dumps(dict(phase=name,pid=p.pid,command=cmd),indent=2)+'\n');print(name+'_PID',p.pid,flush=True);rc=p.wait()
 (R/(name+'.exit')).write_text(str(rc)+'\n')
 if rc:raise SystemExit(rc)
b=B/'build/die'
# Existing hierarchy generated wrappers/args remain unchanged: only missing top target executes.
phase('die_model',['/usr/bin/time','-v','make','-C',str(b),'-f','Vdie_hier.mk','-j1','hier_verilation'])
old=Path('/srv/opentallas-scratch/jobs/russell-qwen-rom-combined-r1/build/die')
for leaf in ['Vot_hdc_qadd','Vot_hdc_fmul','Vot_hdc_vstream_lane_a']:
 target=b/leaf;cached=old/leaf
 files={p.name:p for p in target.iterdir() if p.suffix in ('.h','.cpp')}
 archive=cached/('lib'+leaf[1:]+'.a')
 cached_files={p.name:p for p in cached.iterdir() if p.suffix in ('.h','.cpp')}
 if files and archive.is_file() and files.keys()==cached_files.keys() and all(cached_files[n].read_bytes()==p.read_bytes() for n,p in files.items()):
  shutil.copyfile(archive,target/archive.name);print('REUSED_EXACT_LEAF',archive,flush=True)
phase('die_compile',['/usr/bin/time','-v','make','-C',str(b),'-f','Vdie.mk','-j4','Vdie__ALL.a','OPT_FAST=-O2','OPT_SLOW=-O1','CXX=g++-15'])
phase('access',['python3','-c',"import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]+'/tools');import qwen_rom_combined_stream4_access as a;r=Path(sys.argv[2]);a.emit(r/'build/die/Vdie___024root.h','/srv/opentallas-scratch/claude/realmem/build_v2/tile/Vtile___024root.h',r/'build/hbm/Vhbm___024root.h',r/'top_resume_r2/access',nport=48,scale_banks=13,code_banks=5,crom_words=1048576,hbm_layers=36,embed_rom=1,top='ot_qwen_rom_combined_dspark_die')",str(RT),str(B)])
print('SAME_SOURCE_TOP_ARCHIVE_ACCESS_DONE',flush=True)
