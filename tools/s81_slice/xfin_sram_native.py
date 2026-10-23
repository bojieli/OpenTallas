#!/usr/bin/env python3
"""Original actual XFIN ORFS configuration, opt-in source/macros, synthesis+census only."""
import pathlib,subprocess,json,re,hashlib
r=pathlib.Path.cwd();w=r/'native';s=r/'src';p=w/'config.mk';c=p.read_text()
macro='physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1'
extra=['rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv',macro+'_bb.v']
lines=[]
for line in c.splitlines():
 if line.startswith('export VERILOG_FILES ='):line+=' '+ ' '.join('/src/'+x for x in extra)
 if line.startswith('export VERILOG_DEFINES ='):line+=' -DOT_S81DV_XFIN_SRAM'
 if line.startswith('export WC_LIB_FILES ='):line+=' /src/'+macro+'_tt.lib'
 if line.startswith('export BC_LIB_FILES ='):line+=' /src/'+macro+'_ff.lib'
 lines.append(line)
lines+=['export ADDITIONAL_LIBS = /src/'+macro+'_tt.lib','export SYNTH_BLACKBOXES = ot_sram_1r1w_32x64_m1']
p.write_text('\n'.join(lines)+'\n')
files=re.search(r'export VERILOG_FILES = (.*)',p.read_text())[1].split()
manifest={'source_commit':'2e42dda2a','model_commit':'18f13c8ce','params':{'NS':16,'NVL':5,'LM':5,'LA':6},'defines':['SYNTHESIS','OT_S81DV_XFIN_SRAM'],'sources':{x:hashlib.sha256((s/x.removeprefix('/src/')).read_bytes()).hexdigest() for x in files},'config_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(r/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
cmd=['docker','run','--rm','-v',str(s)+':/src:ro','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow','openroad/orfs:latest','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth']
with (w/'synth.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
b=json.load(open(r/'baseline_native.json'))
cmd=['docker','run','--rm','-v',str(s)+':/src:ro','-v',str(w)+':/work','openroad/orfs:latest','python3','/src/tools/ref_tile/native_census.py','--netlist',b['netlist']['path'],'--top',b['top'],'--out','/work/native_census.json']
for x in b['liberty']:cmd+=['--liberty',x['path']]
for corner in ['tt','ff']:cmd+=['--liberty','/src/'+macro+'_'+corner+'.lib']
rc=subprocess.run(cmd).returncode
p=w/'results/asap7/opentallas_ot_s81dv_xfin_asap7_ref_gate/base/1_2_yosys.v'
n=len(re.findall(r'\n  ot_sram_1r1w_32x64_m1\s+',p.read_text()))
print('ACTUAL_SRAM_INSTANCES',n,flush=True)
assert n==93,n
s=json.load(open(w/'native_census.json'));print('ACTUAL_NATIVE',s['status'],s['max_dynamic_loads'],len(s['violations']),len(s['role_errors']),flush=True)
raise SystemExit(rc)
