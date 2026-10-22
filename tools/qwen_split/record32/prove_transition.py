"""Independent arbitrary-state, one-edge source-to-copy miter; run SAT on fleet."""
import json,pathlib,sys,re
orig=json.loads(pathlib.Path(sys.argv[1]).read_text())['modules']['qfd_sys_face_record_port'];r=json.loads(pathlib.Path(sys.argv[2]).read_text());new=r['graph']
oldff={n:c for n,c in orig['cells'].items() if c['type'].startswith('$_DFF')}
statebits={c['connections']['Q'][0] for c in oldff.values()}
inputs={b for v in orig['ports'].values() if v['direction']=='input' for b in v['bits'] if isinstance(b,int)}
vars=sorted(statebits|inputs);vid={b:i for i,b in enumerate(vars)}
exprs={'$_AND_':'A & B','$_OR_':'A | B','$_XOR_':'A ^ B','$_NOT_':'~A','$_MUX_':'S ? B : A'}
lines=[f'module record32_transition(input [{len(vars)-1}:0] v, output bad);'];bad=[]
def bn(pre,b):return f'{pre}{b}' if isinstance(b,int) else "1'b"+b
def emit(m,pre,aliases):
 bits={b for c in m['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int)}|{b for p in m['ports'].values() for b in p['bits'] if isinstance(b,int)}
 for b in sorted(bits):lines.append(f'wire {pre}{b};')
 for b,eq in aliases.items():lines.append(f'assign {pre}{b}={eq};')
 for n,c in m['cells'].items():
  t=c['type']
  if t=='$scopeinfo' or t.startswith('$_DFF'):continue
  assert t in exprs,t
  ex=exprs[t]
  for pin in ['A','B','S']:
   if pin in c['connections']:ex=re.sub(r'\b'+pin+r'\b','('+bn(pre,c['connections'][pin][0])+')',ex)
  lines.append('assign '+bn(pre,c['connections']['Y'][0])+'='+ex+';')
a={b:f'v[{vid[b]}]' for b in vars};emit(orig,'o',a)
a={b:f'v[{vid[b]}]' for b in inputs if b not in orig['ports']['rst_rn']['bits']}
for cp in r['input_copies']:a[cp['copy_bit']]=f"v[{vid[cp['original_bit']]}]"
for leaf in r['reset_leaves']:a[leaf['bit']]=f"v[{vid[leaf['original_reset_bit']]}]"
for n,c in new['cells'].items():
 if c['type'].startswith('$_DFF'):
  old=oldff[r['origins'][n]];a[c['connections']['Q'][0]]=f"v[{vid[old['connections']['Q'][0]]}]"
emit(new,'n',a)
def nxt(c,pre):
 t=c['type'];d=bn(pre,c['connections']['D'][0]);q=bn(pre,c['connections']['Q'][0])
 if t.startswith('$_DFFE'):
  e=bn(pre,c['connections']['E'][0]);d=f'({e}?{d}:{q})' if t[-2]=='P' else f'({e}?{q}:{d})'
 if 'R' in c['connections']:
  rst=bn(pre,c['connections']['R'][0]);mt=re.search(r'P([NP])([01])',t);assert mt,t
  test='!'+rst if mt[1]=='N' else rst;d=f"({test}?1'b{mt[2]}:{d})"
 return d
for n,c in new['cells'].items():
 if c['type'].startswith('$_DFF'):bad.append('('+nxt(oldff[r['origins'][n]],'o')+' ^ '+nxt(c,'n')+')')
for p,v in orig['ports'].items():
 if v['direction']=='output':
  assert len(v['bits'])==len(new['ports'][p]['bits'])
  bad += ['('+bn('o',x)+' ^ '+bn('n',y)+')' for x,y in zip(v['bits'],new['ports'][p]['bits'])]
lines.append('assign bad=|{'+','.join(bad)+'};');lines.append('endmodule');pathlib.Path(sys.argv[3]).write_text('\n'.join(lines)+'\n')
print('Transition comparisons',len(bad),'arbitrary binary input/state bits',len(vars))
