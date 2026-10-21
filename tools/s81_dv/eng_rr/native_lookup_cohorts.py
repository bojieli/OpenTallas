#!/usr/bin/env python3
"""Pinned actual lookup synthesis + loaded-Liberty census, no placement/CTS/route."""
import pathlib,subprocess,sys,re,json,hashlib,shutil
r=pathlib.Path.cwd();ref=sys.argv[1];g='/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git'
s=r/'src';s.mkdir(exist_ok=False);w=r/'native';w.mkdir(exist_ok=False)
f=['rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv']
f+=['rtl/dsrom_sys/engram/static_lookup_1015/'+n+'.sv' for n in ['ot_s81_engram_hash_n32','ot_s81_engram_hash_cohort_n32','ot_s81_engram_lookup_ra640','dsfd_engram_lkp_ra640']]
m='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2'
f.append(m+'_bb.v')
paths=f+[str(pathlib.Path(m).parent),'tools/s81_dv/eng_rr/native_template','tools/ref_tile/native_census.py','physical/common_flow']
a=subprocess.Popen(['git','--git-dir='+g,'archive',ref,*dict.fromkeys(paths)],stdout=subprocess.PIPE)
b=subprocess.run(['tar','-xf','-','-C',str(s)],stdin=a.stdout);a.stdout.close();assert a.wait()==0 and b.returncode==0
ref_full=subprocess.check_output(['git','--git-dir='+g,'rev-parse',ref],text=True).strip();(r/'snapshot_ref.txt').write_text(ref_full+'\n')
t=s/'tools/s81_dv/eng_rr/native_template';shutil.copytree(t,w,dirs_exist_ok=True);baseline=json.loads((t/'reference_native.json').read_text())
nickname='opentallas_lookup_cohorts_native';top='dsfd_engram_lkp_ra640';defines=['SYNTHESIS','OT_ENGRAM_CRCMAT','OT_S81ENG_HASH_COHORTS']
overrides={'DESIGN_NICKNAME':nickname,'DESIGN_NAME':top,'VERILOG_FILES':' '.join('/src/'+x for x in f),'VERILOG_DEFINES':' '.join('-D'+d for d in defines),'VERILOG_TOP_PARAMS':'RETURN_AGE 640','OT_RST_LAND':'0','OT_PIN_REGS':'0','OT_RST_COPIES_MAX':'0','OT_KEEP_PIN_REGS':'0','SDC_FILE':'/work/constraint.sdc','DIE_AREA':'0 0 604.8 345.6','CORE_AREA':'2.16 2.16 602.64 343.44','NUM_CORES':'8','WC_LIB_FILES':'$(WC_NLDM_LIB_FILES) /src/'+m+'_tt.lib','BC_LIB_FILES':'$(BC_NLDM_LIB_FILES) /src/'+m+'_ff.lib','ADDITIONAL_LIBS':'/src/'+m+'_tt.lib','ADDITIONAL_LEFS':'/src/'+m+'.lef','SYNTH_BLACKBOXES':pathlib.Path(m).name}
c=(w/'config.mk').read_text()+'\n# Native-only: nominal bbox fields are not placement evidence.\n'+''.join('export '+k+' = '+v+'\n' for k,v in overrides.items());(w/'config.mk').write_text(c)
clocks=['ck']+[f'ck_hash[{i}]' for i in range(6)]+['ck_seed','ck_n','ck_s','ck_rd']
(w/'constraint.sdc').write_text(''.join('create_clock -name '+('ck_hash_'+str(i-1) if 1<=i<=6 else p)+' -period 770 [get_ports {'+p+'}]\n' for i,p in enumerate(clocks)));(w/'io_constraints.tcl').write_text('')
inputs=f+[m+e for e in ['_tt.lib','_ff.lib','.lef']]
(w/'source_manifest.json').write_text(json.dumps({'snapshot_commit':ref_full,'top':top,'params':{'RETURN_AGE':640},'defines':defines,'clocks':clocks,'mode':'ACTUAL_ORFS_SYNTH_NATIVE_ONLY_NO_PHYSICAL','source_sha256':{p:hashlib.sha256((s/p).read_bytes()).hexdigest() for p in inputs},'config_sha256':hashlib.sha256(c.encode()).hexdigest()},indent=2)+'\n')
docker=['docker','run','--rm','-v',str(s)+':/src:ro','-v',str(w)+':/work']
cmd=docker+['-w','/OpenROAD-flow-scripts/flow','openroad/orfs:latest','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth']
with(w/'synth.log').open('w')as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
net='/work/results/asap7/'+nickname+'/base/1_2_yosys.v';np=w/net.removeprefix('/work/');assert np.exists(),'no actual mapped netlist'
cmd=docker+['openroad/orfs:latest','python3','/src/tools/ref_tile/native_census.py','--netlist',net,'--top',top,'--out','/work/native_census.json']
for lib in baseline['liberty']:
 if not lib['path'].startswith('/src/'):cmd+=['--liberty',lib['path']]
for corner in ['tt','ff']:cmd+=['--liberty','/src/'+m+'_'+corner+'.lib']
with(w/'census.log').open('w')as log:crc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
j=json.loads((w/'native_census.json').read_text());count=len(re.findall(r'\n  '+re.escape(pathlib.Path(m).name)+r'\s+',np.read_text()));assert count==3,count
(w/'macro_count.json').write_text(json.dumps({pathlib.Path(m).name:count})+'\n');print('ACTUAL_NATIVE',j['status'],j['max_dynamic_loads'],len(j['violations']),len(j['role_errors']),'MACROS',count,'SYNTH_RC',rc,flush=True)
sys.exit(crc or rc)
