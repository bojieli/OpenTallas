from pathlib import Path
import re,hashlib,json
files=['ot_qwen_fixed_issue.sv','ot_qwen_fixed_issue_pw.sv','ot_qwen_fixed_issue_dense_pw.sv'];old=Path('closed_ae6b/rtl/qwen_sys/static_schedule_20261014');out=Path('results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv/reset_unit');texts=[(old/f).read_text()for f in files];names=set(n for s in texts for n in re.findall(r'\bmodule\s+(\w+)',s));receipt=[]
for f,s in zip(files,texts):
 t=re.sub(r'\b('+'|'.join(sorted(names,key=len,reverse=True))+r')\b',lambda m:'gold_'+m.group(0),s);(out/('gold_'+f)).write_text(t);receipt.append(dict(path=str(old/f),sha256=hashlib.sha256(s.encode()).hexdigest(),rewrite='prefix module identifiers only'))
(out/'source_binding.json').write_text(json.dumps(receipt,indent=2)+'\n')
