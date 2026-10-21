from pathlib import Path
import subprocess,hashlib
B=Path(__file__).resolve().parent
root=B.parents[3]
def source(path,sha):
 data=subprocess.check_output(['git','-C',str(root),'show','7e3ee55f1:'+path])
 assert hashlib.sha256(data).hexdigest()==sha
 return data
s=source('rtl/qwen_sys/static_schedule_20261014/safe32/ot_qwen_fixed_issue_ld.sv','0dd9f9e4fc22c0e8e4a99f7529eb5321c07657849b4034e28028e1d098ea6eee').decode()
(B/'candidate.sv').write_text(s)
target='row_bad_q[gj]<=(gj<count_n)?(rn[46]!=(gj==count_n-1)):(rn!=0);'
assert s.count(target)==1
(B/'mutant_count.sv').write_text(s.replace(target,target.replace('count_n','count')))
target='((H16X>=3)?c3_next:c3)'
assert s.count(target)==1
(B/'mutant_prefix.sv').write_text(s.replace(target,'c3'))
(B/'helpers.sv').write_bytes(source('rtl/qwen_sys/static_schedule_20261014/safe32/ot_hdc_ks_helpers.sv','f46c4ff9d0f713ad2c0da8a8460b79dbd65dc51c4a20c6a41f50871009f4052a'))
