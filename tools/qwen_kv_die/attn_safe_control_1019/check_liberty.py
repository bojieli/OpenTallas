import pathlib,re,json,hashlib,collections
r=pathlib.Path('.');libs=list((r/'liberty').glob('*.lib'));cells={};hashes={}
for p in libs:
 s=p.read_text();hashes[p.name]=hashlib.sha256(s.encode()).hexdigest()
 for m in re.finditer(r'\bcell\s*\(\s*(\w+)\s*\)\s*\{',s):
  pos=m.end();depth=1
  while depth:depth+=(s[pos]=='{')-(s[pos]=='}');pos+=1
  b=s[m.end():pos-1];cells[m[1]]=b
for n,op in [('AND2x2_ASAP7_75t_R','&'),('XOR2x1_ASAP7_75t_R','^')]:
 b=cells[n];f=re.findall(r'\bfunction\s*:\s*"([^"]+)"',b);assert len(f)==1,(n,f)
 for a in (0,1):
  for c in (0,1):
   expr=f[0].replace('A',str(a)).replace('B',str(c)).replace('*','&').replace('+','|').replace('!','~');v=int(bool(eval(expr,{'__builtins__':{}},{})));want=(a&c) if op=='&' else (a^c);assert v==want,(n,f,a,c)
counts=collections.Counter(re.findall(r'\b(\w+_ASAP7_75t_R)\s+c\d+\s*\(', (r/'candidate/qkd_kvs_attn_safe_control.v').read_text()))
areas=json.loads((r/'candidate/master_areas.json').read_text());area=0
for n,k in counts.items():
 assert n in areas,n;area+=areas[n]*k
out={'primitive_boolean_all8':'PASS','candidate_cells':sum(counts.values()),'master_histogram':dict(counts),'native_ODB_master_area_um2':area,'liberty_hashes':hashes,'native_timing_qualified':False}
(r/'candidate/liberty_proof.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
