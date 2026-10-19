exec(open('survival.py').read())
lib=Path('libsource/seq.lib').read_text()
def block(s,pat):
 m=re.search(pat,s);a=s.index('{',m.start());depth=1;i=a+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a+1:i-1]
counts=collections.Counter(c['type'] for c in j['cells'].values() if re.search('DFF',c['type']))
caps={}
for t,count in counts.items():
 b=block(lib,r'cell\s*\(\s*'+re.escape(t)+r'\s*\)');pin=block(b,r'pin\s*\(\s*CLK\s*\)')
 caps[t]={'count':count,'clock_cap':float(re.search(r'(?m)^\s*capacitance\s*:\s*([0-9.eE+-]+)',pin)[1])}
viol=[]
for l in Path('native_census.tsv').read_text().splitlines()[1:]:
 v=l.split('\t')
 if v[1]!='ff' or int(v[2])<=32:continue
 found=[]
 for n,nv in j['netnames'].items():
  if '.ff.' in n:continue
  for k,b in enumerate(nv['bits']):
   if v[0] in root(b):found.append(f'{n}[{k}]')
 viol.append({'root':v[0],'loads':int(v[2]),'aliases':found})
units=re.search(r'capacitive_load_unit\s*\([^;]+',lib)
ans={'clock_cap_units':units.group(0) if units else None,'ff_clock_cap':caps,'total_clock_cap':sum(c['count']*c['clock_cap'] for c in caps.values()),'remaining_ff_violations':viol}
Path('details.json').write_text(json.dumps(ans,indent=2)+'\n');print(json.dumps(ans))
