from pathlib import Path
import subprocess,json,hashlib
r=Path('/srv/opentallas-scratch/claude/codex-pvm-bindfirst-orfs-1020')
old=Path('/srv/opentallas-scratch/claude/ref_gate/smh_pvm_ref_s6a-20261020-031321/routes/gate/work/orfs/native_census.json')
p=r/'work/config.mk';s=p.read_text()
s=s.replace('export VERILOG_DEFINES = -DSYNTHESIS','export VERILOG_DEFINES = -DSYNTHESIS -DOT_PVM_NATIVE_BIND_FIRST')
s=s.replace('export VERILOG_FILES = ', 'export VERILOG_FILES = /src/rtl/hdc/ot_hdc_fp32_add_lat_fan32_bindfirst.sv /src/rtl/hdc/ot_hdc_fp32_add_lat7_fan32_bindfirst_native.v ')
p.write_text(s)
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
mapped='/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/1_2_yosys.v'
base=['docker','run','--rm','-v',str(r/'src')+':/src:ro','-v',str(r/'work')+':/work','-w','/OpenROAD-flow-scripts/flow',img]
script='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=4 '+mapped+' && chmod -R a+rwX /work'
with (r/'orfs_synth.log').open('w') as f:rc=subprocess.run(base+['bash','-lc',script],stdout=f,stderr=subprocess.STDOUT).returncode
print('SYNTH',rc,flush=True)
if rc:raise SystemExit(rc)
cmd=base+['python3','/src/tools/ref_tile/native_census.py','--netlist',mapped,'--top','ot_hbm_sm_pv_merge_distributed','--out','/work/native_census.json']
for l in json.loads(old.read_text())['liberty']:cmd.extend(['--liberty',l['path']])
with (r/'census.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
print('CENSUS',rc,flush=True)
if (r/'work/native_census.json').exists():
 d=json.loads((r/'work/native_census.json').read_text());print({k:d.get(k) for k in ['status','roots_examined','max_dynamic_loads','role_errors']},flush=True)
print('MAPPED_SHA256',hashlib.sha256((r/mapped.lstrip('/')).read_bytes()).hexdigest(),flush=True)
raise SystemExit(rc)
