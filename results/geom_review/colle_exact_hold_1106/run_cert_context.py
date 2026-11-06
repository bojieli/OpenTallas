from pathlib import Path
import os,sys,subprocess,json,importlib.util
side=sys.argv[1];assert side in ('e','w')
r=Path('/srv/opentallas-scratch2/claude/codex-colle-exact-hold-1106');t=Path('/srv/opentallas-scratch2/claude/codex-bank128-wface/release_bh/tools/die_plan');kit=r/side/'cert_input1'
subprocess.run([sys.executable,str(r/'prepare_cert.py'),side],check=True)
spec=importlib.util.spec_from_file_location('eco',t/'eco_loop.py');eco=importlib.util.module_from_spec(spec);spec.loader.exec_module(eco)
# Standard released abstraction, exact restored source SDC, normal two-mode setup.
subprocess.run(['bash','-c',eco.ABSTRACT_SH,'colle-cert-abstract',str(kit),'4','16','openroad/orfs:asap7lock','docker','1'],check=True)
env=dict(os.environ,COLLE_AUDIT_SIDES=side)
subprocess.run(['bash',str(r/'count_audit.sh')],env=env,check=True)
audit=json.load(open(kit/'final_pin_audit.json'));assert audit['verdict']=='PASS',audit
count=json.load(open(kit/'final_functional_count.json'));assert len(count['new_buffers'])==4,count
assert count['counts']['functional']<=150000 and count['functional_utilization']<=.45,count
cmd=[sys.executable,str(t/'resign.py'),'run','--kit',str(kit),'--tag','flow-20261106-bh-hbm','--repo',str(t.parent.parent/'tag_manifest.json'),'--tools',str(t),'--out',str(r/side/'cert1_bh'),'--auto','--lec-mem','32g','--name','codex-colle-'+side+'-exact4','--lane','CODEX-BANK128','--pincmp','actual final ODB PASS '+str(audit['ok'])+'/'+str(audit['pins'])+'; released DIE-S81-62 native rectangle retains logical clock anchor','--note','Exact four near-D noninverting hold buffers; own E/W pins and clock. Original source SDC restored byte-exact before standard MM abstraction; no RTL/clock/constraint changes. Clock geometry PASS; parent NEEDS_PARENT explicit; normal routedEQ required.']
print('COLLE_NORMAL_CERT_COMMAND',cmd,flush=True)
raise SystemExit(subprocess.call(cmd))
