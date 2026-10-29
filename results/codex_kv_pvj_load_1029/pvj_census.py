import re,json
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kv-pvj-load-1029')
k=p/'kits/ot_qwen_tp8_pv_join_t__172.8x172.8'
s=(k/'1_synth_odb.v').read_text()
rows=re.findall(r'^\s*(DFF\S+)\s+\\(\S+)\s+\((.*?)\);',s,re.M|re.S)
assert len(rows)==15971,len(rows)
canon=lambda x:x.replace('\\[','[').replace('\\]',']')
actual={n+'/CLK' for m,n,ports in rows if re.search(r'\.CLK\(clk\)',ports)}
c=json.load(open(k/'pv_clock_census.json'))
expect={canon(x) for x in c['sinks']}
assert actual==expect,('missing',list(expect-actual)[:10],'extra',list(actual-expect)[:10])
local=[n for m,n,ports in rows if 'g_output_load_local' in n]
assert len(local)==32
out=dict(actual_sequential=len(rows),actual_clock_sinks=len(actual),local_output_load_ff=len(local),predicted_exact_match=True,local_masters=sorted(set(m for m,n,v in rows if 'g_output_load_local' in n)),formal=json.load(open(k/'lec/lec.json'))['verdict'] if 'verdict' in json.load(open(k/'lec/lec.json')) else 'see lec.json')
(p/'actual_census.json').write_text(json.dumps(out,indent=2)+'\n')
print(out)
