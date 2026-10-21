from pathlib import Path
import subprocess,hashlib
B=Path(__file__).resolve().parent
root=B.parents[3]
def source(path,sha):
 data=subprocess.check_output(['git','-C',str(root),'show','c0ad783cd:'+path])
 assert hashlib.sha256(data).hexdigest()==sha
 return data
s=source('rtl/qwen_sys/static_schedule_20261014/safe32/ot_qwen_fixed_issue_ld.sv','75dbd1cee62fe7e9bb6c41b68a92b8f0180cf6794f29e058a925a64f461acc63').decode()
(B/'candidate.sv').write_text(s)
target='row_bad_q[gj]<=(gj<count_n)?(rn[46]!=(gj==count_n-1)):(rn!=0);'
assert s.count(target)==1
(B/'mutant_count.sv').write_text(s.replace(target,target.replace('count_n','count')))
target='((H16X>=3)?c3_next:c3)'
assert s.count(target)==1
(B/'mutant_prefix.sv').write_text(s.replace(target,'c3'))
target="gs_bad_q<=pw_data[63:32]!=32'h43414c47||pw_data[31:0]==0;"
assert s.count(target)==1
(B/'mutant_gstop.sv').write_text(s.replace(target,target.replace('pw_data','gstop_q')))
(B/'helpers.sv').write_bytes(source('rtl/qwen_sys/static_schedule_20261014/safe32/ot_hdc_ks_helpers.sv','f46c4ff9d0f713ad2c0da8a8460b79dbd65dc51c4a20c6a41f50871009f4052a'))
