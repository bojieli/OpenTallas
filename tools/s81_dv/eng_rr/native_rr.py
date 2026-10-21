#!/usr/bin/env python3
"""Actual ORFS synthesis and loaded-Liberty native census; no floorplan/CTS/route."""
import hashlib,json,pathlib,re,shutil,subprocess,sys
r=pathlib.Path.cwd();s=r/'src';w=r/'native';w.mkdir(exist_ok=False)
t=s/'tools/s81_dv/eng_rr/native_template';shutil.copytree(t,w,dirs_exist_ok=True)
b=json.loads((t/'reference_native.json').read_text())
f=re.search(r'F=\((.*?)\)\n',(s/'tools/s81_dv/eng_rr/run_eng_rr.sh').read_text(),re.S)[1].split()
f=[x for x in f if '/test/' not in x]
macros=[]
for i,p in enumerate(f):
 if p.startswith('physical/'):
  m=p[:-2];macros.append(m);f[i]=m+'_bb.v'
macros=list(dict.fromkeys(macros))
assert len(macros)==4,macros
assert all((s/x).is_file() for x in f)
c=(w/'config.mk').read_text();nickname='opentallas_dsdv_eng_rr_asap7_native'
# Retain the actual lookup's ORFS synthesis settings and exact standard-cell TT/FF library selection.
overrides={'DESIGN_NICKNAME':nickname,'DESIGN_NAME':'dsdv_eng_rr','VERILOG_FILES':' '.join('/src/'+x for x in f),
 'VERILOG_DEFINES':'-DSYNTHESIS -DOT_ENGRAM_CRCMAT -DOT_S81ENG_RR_N32','VERILOG_TOP_PARAMS':'',
 'DIE_AREA':'0 0 1296 1209.6','CORE_AREA':'2.16 2.16 1293.84 1207.44','NUM_CORES':'8',
 'WC_LIB_FILES':'$(WC_NLDM_LIB_FILES) '+' '.join('/src/'+m+'_tt.lib' for m in macros),
 'BC_LIB_FILES':'$(BC_NLDM_LIB_FILES) '+' '.join('/src/'+m+'_ff.lib' for m in macros),
 'ADDITIONAL_LIBS':' '.join('/src/'+m+'_tt.lib' for m in macros),
 'ADDITIONAL_LEFS':' '.join('/src/'+m+'.lef' for m in macros),
 'SYNTH_BLACKBOXES':' '.join(pathlib.Path(m).name for m in macros)}
c+='\n# WholeRR native-only profile; no physical result from the nominal die-area fields.\n'
c+=''.join('export '+k+' = '+v+'\n' for k,v in overrides.items());(w/'config.mk').write_text(c)
(w/'constraint.sdc').write_text('create_clock -name ck -period 770 [get_ports ck]\n')
(w/'io_constraints.tcl').write_text('')
inputs=f+[m+e for m in macros for e in ['_tt.lib','_ff.lib','.lef']]
manifest={'rtl_commit':'602383e79','top':'dsdv_eng_rr','params':{'RETURN_AGE':640,'XQ_TXD':8,'AQ_LATENCY':18},
 'defines':['SYNTHESIS','OT_ENGRAM_CRCMAT','OT_S81ENG_RR_N32'],'mode':'ACTUAL_ORFS_SYNTH_NATIVE_ONLY_NO_PHYSICAL',
 'configuration_template':'agidock128/ref_gate/s81engm_lkp_ra640a-20261021-134946/routes/gate/work/orfs/config.mk',
 'source_sha256':{p:hashlib.sha256((s/p).read_bytes()).hexdigest() for p in inputs},
 'config_sha256':hashlib.sha256(c.encode()).hexdigest()}
(w/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
docker=['docker','run','--rm','-v',str(s)+':/src:ro','-v',str(w)+':/work']
cmd=docker+['-w','/OpenROAD-flow-scripts/flow','openroad/orfs:latest','bash','-lc',
 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth']
with (w/'synth.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
net='/work/results/asap7/'+nickname+'/base/1_2_yosys.v';np=w/net.removeprefix('/work/')
if not np.exists():raise SystemExit('ACTUAL_SYNTH_FAILED_NO_MAPPED_NETLIST rc='+str(rc))
cmd=docker+['openroad/orfs:latest','python3','/src/tools/ref_tile/native_census.py','--netlist',net,'--top','dsdv_eng_rr','--out','/work/native_census.json']
for lib in b['liberty']:
 if not lib['path'].startswith('/src/'):cmd+=['--liberty',lib['path']]
for m in macros:
 for corner in ['tt','ff']:cmd+=['--liberty','/src/'+m+'_'+corner+'.lib']
with (w/'census.log').open('w') as log:crc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
j=json.loads((w/'native_census.json').read_text());text=np.read_text()
counts={pathlib.Path(m).name:len(re.findall(r'\n  '+re.escape(pathlib.Path(m).name)+r'\s+',text)) for m in macros}
(w/'macro_count.json').write_text(json.dumps(counts,indent=2)+'\n')
print('ACTUAL_MACROS',counts,sum(counts.values()),flush=True);assert sum(counts.values())==15,counts
print('ACTUAL_NATIVE',j['status'],j['max_dynamic_loads'],len(j['violations']),len(j['role_errors']),'SYNTH_RC',rc,flush=True)
raise SystemExit(crc if crc else rc)
