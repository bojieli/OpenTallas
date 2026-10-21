from pathlib import Path
import subprocess,hashlib
B=Path(__file__).resolve().parent
root=B.parents[2]
def source(path,sha):
 data=subprocess.check_output(['git','-C',str(root),'show','8f3115533:'+path])
 assert hashlib.sha256(data).hexdigest()==sha
 return data
s=source('rtl/qwen_sys/static_schedule_20261014/safe32/ot_qwen_fixed_issue_ld.sv','1dca4fca4f67ef988deebc3d56624b590c63c0c49cf821831e56d4e23816a075').decode()
(B/'candidate.sv').write_text(s)
target='row_bad_q[gj]<=(gj<count_n)?(rn[46]!=(gj==count_n-1)):(rn!=0);'
assert s.count(target)==1
(B/'mutant.sv').write_text(s.replace(target,target.replace('count_n','count')))
(B/'helpers.sv').write_bytes(source('rtl/qwen_sys/static_schedule_20261014/safe32/ot_hdc_ks_helpers.sv','f46c4ff9d0f713ad2c0da8a8460b79dbd65dc51c4a20c6a41f50871009f4052a'))
