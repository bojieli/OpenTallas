from pathlib import Path
import json,re
out={'scope':'NARROW_ACTUAL_LITERAL_HARD0_RELATION_DIAGNOSTIC','parameter':0,'data_inputs':107,'independent_reset_supports':5,'observed_Qs':509,'after_first_capture_only':True,'SAT_steps':4,'default_physical_or_native_mapped_adoption':False,'cases':{}}
for tag in ['correct','wrong_plain_data','reset_support_OR','control_forced_one']:
 text=Path(tag+'.log').read_text(errors='replace');rc=int(Path(tag+'.rc').read_text());positive=tag=='correct'
 passed=rc==0 and not re.search(r'^ERROR:',text,re.M) and bool(re.search(r'SAT proof finished[^\n]*'+('SUCCESS'if positive else'FAIL'),text))
 witness=False
 if not positive:
  p=Path(tag+'.vcd')
  if p.exists():
   lines=p.read_text().splitlines();ids=[]
   for l in lines:
    s=l.split()
    if len(s)>5 and s[0]=='$var'and s[2]=='1'and s[4].lstrip('\\')=='bad':ids.append(s[3])
   witness=any(l=='1'+i or l.strip()=='b1 '+i for i in ids for l in lines)
  passed=passed and witness
 out['cases'][tag]={'native_rc':rc,'expected':'RELATION_PASS'if positive else'ACTIVE_HARD0_COUNTEREXAMPLE','bad1_witness':witness,'verdict':'PASS'if passed else'FAIL'}
out['verdict']='PASS'if all(c['verdict']=='PASS'for c in out['cases'].values())else'FAIL'
Path('hard0_lemma_result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if out['verdict']!='PASS':raise SystemExit(1)
