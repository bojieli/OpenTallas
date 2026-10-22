from pathlib import Path
import json,subprocess,hashlib
r=Path.cwd();old=Path('/srv/opentallas-scratch/claude/ref_gate/ot_qkh_ktree_lk_nc32c-20261020-031904/routes/gate/work/orfs')
rep=json.loads((old/'native_census.json').read_text())
net=old/'results/asap7/opentallas_ot_qkh_ktree_lk_nc32c_asap7_ref_gate/base/1_2_yosys.v'
assert hashlib.sha256(net.read_bytes()).hexdigest()=='6d1d28a1d58ab5088166ffb25084c552ae7810b51ee401801a55fc3434fc7cea'
args=['python3','/audit/tools/ref_tile/native_census.py','--netlist',rep['netlist']['path'],'--top',rep['top'],'--out','/audit/actual_ktree_census.json']
for lib in rep['liberty']:args+=['--liberty',lib['path']]
cmd=['docker','run','--rm','-v',str(r)+':/audit','-v',str(old)+':/work:ro','openroad/orfs:latest']+args
z=subprocess.run(cmd);assert z.returncode==0,z.returncode
out=json.loads((r/'actual_ktree_census.json').read_text());assert out['status']=='FAIL' and out['max_dynamic_loads']==34 and len(out['violations'])==15 and out['admission']['status']=='PASS_WITH_SCOPED_WAIVER'
print('ACTUAL_KTREE_CLI_PASS rawFAIL/max34/15 exactnodes; exit0 exactscope; immutable mappedSHA verified',flush=True)
