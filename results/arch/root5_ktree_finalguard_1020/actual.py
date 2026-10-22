from pathlib import Path
import hashlib,json,subprocess
r=Path.cwd();rows=[]
for stamp,digest in [('031904','6d1d28a1d58ab5088166ffb25084c552ae7810b51ee401801a55fc3434fc7cea'),('041108','c53dd281eba6a845dff175c6e88876013eb106c5cd3cb6c52053c449f88a2368')]:
 old=Path('/srv/opentallas-scratch/claude/ref_gate')/('ot_qkh_ktree_lk_nc32c-20261020-'+stamp)/'routes/gate/work/orfs'
 rep=json.loads((old/'native_census.json').read_text())
 net=old/'results/asap7/opentallas_ot_qkh_ktree_lk_nc32c_asap7_ref_gate/base/1_2_yosys.v'
 assert hashlib.sha256(net.read_bytes()).hexdigest()==digest
 out='actual_'+stamp+'.json'
 args=['python3','/audit/source/tools/ref_tile/native_census.py','--netlist',rep['netlist']['path'],'--top',rep['top'],'--out','/audit/'+out]
 for lib in rep['liberty']:args+=['--liberty',lib['path']]
 cmd=['docker','run','--rm','-v',str(r)+':/audit','-v',str(old)+':/work:ro','openroad/orfs:latest']+args
 with (r/('actual_'+stamp+'.log')).open('w') as f:z=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 j=json.loads((r/out).read_text())
 assert z.returncode==0 and j['status']=='FAIL' and j['max_dynamic_loads']==34 and len(j['violations'])==15
 assert j['admission']['status']=='PASS_WITH_SCOPED_WAIVER' and j['role_errors']==[]
 assert j['netlist']['sha256']==digest and j['netlist']['positive_buf_identity_sha256']=='24f05e9e4e08b9590b5ce8d6e1d2b00958c5fb0fea739cd7934f7da46b5dc228'
 rows.append({'stamp':stamp,'raw_sha256':digest,'raw_status':j['status'],'max':34,'nodes':15,'exit':z.returncode,'admission':j['admission'],'role_errors':j['role_errors']})
 print('ACTUAL_FINAL_GUARD',stamp,'PASS rawFAIL34/15 scopedadmission',flush=True)
(r/'actual_summary.json').write_text(json.dumps(rows,indent=2)+'\n')
