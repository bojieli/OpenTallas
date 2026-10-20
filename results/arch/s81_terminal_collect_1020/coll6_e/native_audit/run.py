from pathlib import Path
import os,subprocess,hashlib,json
case=Path('/srv/opentallas-scratch/claude/ref_gate/dscoll_lane_e_s6c-20261020-051416')
base=['docker','run','--rm','--network','none','-v',os.getcwd()+':/audit','-v',str(case)+':/case:ro','-v',str(case/'src')+':/src:ro','openroad/orfs:asap7lock']
odb=next(case.glob('routes/gate/work/orfs/results/**/5_1_grt.odb'))
Path('source_odb_sha256.txt').write_text(hashlib.sha256(odb.read_bytes()).hexdigest()+'  '+str(odb)+'\n')
with open('dump.log','w')as f: rc=subprocess.run(base+['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-exit','/audit/dump.tcl'],stdout=f,stderr=subprocess.STDOUT).returncode
print('dump',rc,flush=True)
if rc:raise SystemExit(rc)
with open('reach.log','w')as f:rc=subprocess.run(base+['python3','/audit/reach.py'],stdout=f,stderr=subprocess.STDOUT).returncode
print('reach',rc,flush=True)
if rc:raise SystemExit(rc)
with open('native.log','w')as f:
 script="""import glob,subprocess
libs=glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*')+glob.glob('/src/physical/asap7_memory_macros_v2/*/*_tt.lib')
cmd=['python3','/audit/tools/ref_tile/native_census.py','--netlist','/audit/grt.v','--top','dsfd_coll_lane_e_safe4','--out','/audit/grt_native_raw.json']
for lib in libs:cmd+=['--liberty',lib]
raise SystemExit(subprocess.run(cmd).returncode)
"""
 rc=subprocess.run(base+['python3','-c',script],stdout=f,stderr=subprocess.STDOUT).returncode
print('raw_native',rc,'raw failure retained and requires actual DB class review',flush=True)
