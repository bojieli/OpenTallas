import sys,json,collections
from pathlib import Path
sys.path.insert(0,sys.argv[1]); import lec as LC
out,work=Path(sys.argv[2]),Path(sys.argv[3]);work.mkdir(parents=True,exist_ok=True)
L=LC.Lec(LC.read_aig(out/'gold.aig'),LC.read_map(out/'gold.map'),LC.read_aig(out/'gate.aig'),LC.read_map(out/'gate.map'))
log=[]
LC.normalize_gold_elements(L,LC.slang_elements(out/'gold.aliases.json'),log)
LC.json_alias_keys(L,log,work=out);LC.slang_element_keys(L,log,work=out);LC.alias_arrays(L,log,work=out);LC.relayout(L,log);LC.renamed(L,log)
L.hyp={(sd,k):tuple(h) for sd,k,h in json.load(open(out/'hyp.json'))}
L.hyp[('gold','ff:u_dut.u_e.w_cgt[1]')]=('eq','gold','ff:u_dut.u_e.w_coh[0]',0)
import pickle,re
pairs=[]
for k in L.tonly:
 if ('gate',k) in L.hyp:continue
 m=re.match(r'(ff:.*\.q1_sg)#t\[(\d+)\]$',k)
 if m:
  i=int(m[2]);g=f'{m[1]}[{i//16}][{i%16}]'
 elif '#t[' in k and ('.drain#t[' in k or '.g_mi.u_c2.q#t[' in k):g=k.replace('#t[','[')
 else:continue
 if g in L.gp:pairs.append(('gate',k,('eq','gold',g,0)))
for mac in (0,1):
 for ch in ('u_c0','u_c1'):
  b=f'ff:u_dut.u_e.g_mac[{mac}].g_ch3.{ch}'
  for a,z in (('.pl[6]','.u_t.g_line.line[68]'),('.u_t.g_line.line[57]','.pl[5]')):
   if b+a in L.gp and b+z in L.gp and ('gold',b+a) not in L.hyp:pairs.append(('gold',b+a,('eq','gold',b+z,0)))
for sd,k,h in pairs:L.hyp[(sd,k)]=h
print('given',len(pairs),flush=True)
(work/'proposals.json').write_text(json.dumps(pairs,indent=2))
with open(work/'context.pickle','wb') as f:pickle.dump(L,f)
m,kind=L.build(with_compare=True,with_hyp=True)
st=LC.prove(m,work,1000,log,tag='hints')
print('statuses',dict(collections.Counter(st.values())),flush=True)
for n,s in st.items():
 if s!='proved':print('BAD',s,n,flush=True)
(work/'log').write_text('\n'.join(log))
(work/'statuses.json').write_text(json.dumps(st))
