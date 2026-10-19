import json,re,pathlib
p=pathlib.Path(__file__).parent
raw=(p/'overflow_cex.json').read_text()
# Preserve raw Yosys artifact. Escape only syntactically invalid backslashes in names.
j=json.loads(re.sub(r'\\(?!["\\/bfnrtu])',r'\\\\',raw))
names=['trigger','in_rst_n','in_valid_in','in_a','in_b','gold_err','gate_err','gold_valid_out','gate_valid_out']
dec={}
for s in j['signal']:
 if s.get('name') not in names: continue
 data=s.get('data',[]);di=1 if data and data[0]=='' and s['wave'][0]=='4' else 0
 value=None;values=[]
 for c in s['wave'][1:]:
  if c=='=': value=data[di];di+=1
  elif c in '01xz':value=c
  elif c!='.':raise ValueError(c)
  values.append(value)
 dec[s['name']]=values
rows=[dict(step=i+1,**{k:v[i] for k,v in dec.items()}) for i in range(14)]
first=next(x for x in rows if x['trigger']=='1')
assert first['step']==14 and first['gold_err']=='10' and first['gate_err']=='00'
assert first['gold_valid_out']==first['gate_valid_out']=='1'
(p/'overflow_decoded.json').write_text(json.dumps({'first_difference':first,'steps':rows,'parser_note':'Raw Yosys WaveJSON retained; invalid name escapes normalized only; initial empty bus datum consumed.'},indent=2)+'\n')
print(first)
