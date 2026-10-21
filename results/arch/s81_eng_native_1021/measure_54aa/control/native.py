import hashlib,json,subprocess
from pathlib import Path
base=json.load(open('/baseline/native_census.json'))
for row in base['liberty']:
 got=hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()
 if got!=row['sha256']:raise SystemExit('LIBRARY HASH MISMATCH '+row['path'])
net='/work/results/asap7/opentallas_dsfd_engram_lkp_ra640_asap7_ref_gate/base/1_2_yosys.v'
cmd=['python3','/src/tools/ref_tile/native_census.py','--netlist',net,'--top','dsfd_engram_lkp_ra640','--kit','s81engm_lkp_ra640a','--out','/work/native_census.json']
for row in base['liberty']:cmd+=['--liberty',row['path']]
Path('/work/native_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
raise SystemExit(subprocess.run(cmd).returncode)
