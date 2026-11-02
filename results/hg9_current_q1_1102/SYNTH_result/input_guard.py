from pathlib import Path
import json,hashlib,sys
r=Path(sys.argv[1]);k=r/'kit';d=json.loads((r/'INPUT_HASHES.json').read_text())
for n,w in d.items(): assert hashlib.sha256((k/n).read_bytes()).hexdigest()==w,n
assert '.QK_ISSUE_AGE(34), .RESPONSE_LAT(18)' in (k/'rtl/qkd_ectlk_columns.sv').read_text()
assert not (k/'run').exists(),'refuse inherited run outputs'
(r/'INPUT_GUARD_PASS.json').write_text(json.dumps({'inputs':len(d),'current_profile':[34,18],'source_guard':'PASS','scope':'ONE_SYNTH_ONLY_4GB1T_DISK3_NO_PROOF_FP_STA_ROUTE'})+'\n')
