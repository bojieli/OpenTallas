#!/usr/bin/env python3
"""Arbitrary-state source/copy one-edge miter; actual ROM outputs are shared inputs.

Compares every retained FF transition, every external output, clock pins and
all three ROM input faces. No startup, ROM content or physical claim.
"""
import copy,json,re,sys
from pathlib import Path
MACRO='ot_rom_4096x72_m8'
D=json.loads(Path(sys.argv[1]).read_text());top='qfd_sys_face_lctx3_wrapped';old=copy.deepcopy(D['modules'][top]);cells=old['cells']
nb=max(b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b,int))+1
while True:
 nested=[(n,c) for n,c in cells.items() if c['type'] in D['modules'] and c['type']!=MACRO]
 if not nested:break
 for n,c in nested:
  sub=D['modules'][c['type']];mp={}
  for p,v in sub['ports'].items():mp.update(zip(v['bits'],c['connections'][p]))
  for sc in sub['cells'].values():
   for bs in sc['connections'].values():
    for b in bs:
     if isinstance(b,int) and b not in mp:mp[b]=nb;nb+=1
  del cells[n]
  for sn,sc in sub['cells'].items():
   cc=copy.deepcopy(sc);cc['connections']={p:[mp[b] if isinstance(b,int) else b for b in bs] for p,bs in sc['connections'].items()};cells[n+'/'+sn]=cc
old['cells']={n:c for n,c in cells.items() if c['type']!='$scopeinfo'}
r=json.loads(Path(sys.argv[2]).read_text());new=r['graph']
def ff(t):return t.startswith('$_DFF') or t.startswith('$_SDFF')
oldff={n:c for n,c in old['cells'].items() if ff(c['type'])}
oldmac={n:c for n,c in old['cells'].items() if c['type']==MACRO}
assert len(oldmac)==3
free={b for p in old['ports'].values() if p['direction']=='input' for b in p['bits'] if isinstance(b,int)}
free|={c['connections']['Q'][0] for c in oldff.values()}
free|={b for c in oldmac.values() for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for b in bs if isinstance(b,int)}
vid={b:i for i,b in enumerate(sorted(free))}
exprs={'$_AND_':'A & B','$_OR_':'A | B','$_XOR_':'A ^ B','$_XNOR_':'~(A ^ B)','$_NOT_':'~A','$_MUX_':'S ? B : A','$_NAND_':'~(A & B)','$_NOR_':'~(A | B)','$_ANDNOT_':'A & ~B','$_ORNOT_':'A | ~B','$_AO21_':'(A & B) | X','$_OA21_':'(A | B) & X'}
lines=[f'module lctx_full_transition(input[{len(free)-1}:0]v,output bad);'];checks=[];labels=[]
def bn(p,b):return f'{p}{b}' if isinstance(b,int) else "1'b"+b
def emit(m,p,aliases):
 bits={b for c in m['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int)}
 bits|={b for x in m['ports'].values() for b in x['bits'] if isinstance(b,int)}
 lines.extend(f'wire {p}{b};' for b in sorted(bits))
 lines.extend(f'assign {p}{b}={a};' for b,a in aliases.items())
 for n,c in m['cells'].items():
  t=c['type']
  if ff(t) or t==MACRO:continue
  assert t in exprs,(n,t)
  ex=exprs[t]
  for pin in ('A','B','S','X'):
   if pin in c['connections']:ex=re.sub(r'\b'+pin+r'\b','('+bn(p,c['connections'][pin][0])+')',ex)
  lines.append('assign '+bn(p,c['connections']['Y'][0])+'='+ex+';')
emit(old,'o',{b:f'v[{i}]' for b,i in vid.items()})
a={b:f'v[{vid[b]}]' for x in old['ports'].values() if x['direction']=='input' for b in x['bits'] if isinstance(b,int)}
for n,c in new['cells'].items():
 if ff(c['type']):a[c['connections']['Q'][0]]=f"v[{vid[oldff[r['origins'][n]]['connections']['Q'][0]]}]"
 elif c['type']==MACRO:
  orig=oldmac[r['origins'][n]]
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='output':
    for b,ob in zip(bs,orig['connections'][p]):a[b]=f'v[{vid[ob]}]'
emit(new,'n',a)
def nxt(c,p):
 t=c['type'];x=c['connections'];q=bn(p,x['Q'][0]);d=bn(p,x['D'][0]);ra=None;en=None
 if 'R' in x:
  m=re.search(r'P([NP])([01])',t);assert m,t
  ra=bn(p,x['R'][0]);ra='!'+ra if m[1]=='N' else ra;val="1'b"+m[2]
 if 'E' in x:
  m=re.search(r'([PN])_$',t);assert m,t
  en=bn(p,x['E'][0]);en='!'+en if m[1]=='N' else en
 if t.startswith('$_SDFFCE'):
  assert en is not None and ra is not None
  return f'({en}?({ra}?{val}:{d}):{q})'
 if en is not None:d=f'({en}?{d}:{q})'
 if ra is not None:d=f'({ra}?{val}:{d})'
 return d
for n,c in new['cells'].items():
 if ff(c['type']):
  o=oldff[r['origins'][n]];labels.extend([n+':D',n+':C']);checks.append('('+nxt(o,'o')+' !== '+nxt(c,'n')+')');checks.append('('+bn('o',o['connections']['C'][0])+' !== '+bn('n',c['connections']['C'][0])+')')
 elif c['type']==MACRO:
  o=oldmac[r['origins'][n]]
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='input':
    labels.extend(n+':'+p+'['+str(i)+']' for i in range(len(bs)));checks.extend('('+bn('o',ob)+' !== '+bn('n',b)+')' for b,ob in zip(bs,o['connections'][p]))
assert set(old['ports'])==set(new['ports'])
for p,v in old['ports'].items():
 assert v['direction']==new['ports'][p]['direction'] and len(v['bits'])==len(new['ports'][p]['bits'])
 if v['direction']=='output':
  labels.extend('OUTPUT '+p+'['+str(i)+']' for i in range(len(v['bits'])));checks.extend('('+bn('o',x)+' !== '+bn('n',y)+')' for x,y in zip(v['bits'],new['ports'][p]['bits']))
# Explicit reset-valid control invariant for the specialized NL1 admission sequencer.
rb=old['netnames']['u_ot_pr_core.u_cseq.u_seq.u_seq.running']['bits'][0]
rf=next(c for c in oldff.values() if c['connections']['Q']==[rb])
assert rf['type']=='$_DFFE_PN0P_',rf['type']
lines[0]=lines[0].replace('output bad','output reset_control_is_zero,output control_next_bad,output bad')
lines.append('assign reset_control_is_zero=!'+bn('o',rb)+';')
lines.append('assign control_next_bad='+nxt(rf,'o')+';')
lines[0]=lines[0].replace('output bad','output bad,output['+str(len(checks)-1)+':0]fail_bits');lines.append('assign fail_bits={'+','.join(checks)+'};');lines.append('assign bad=|fail_bits;');lines.append('endmodule');Path(sys.argv[3]+'.labels.json').write_text(json.dumps(labels));Path(sys.argv[3]).write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(comparisons=len(checks),arbitrary_binary_input_state_rom_output_bits=len(free),original_ff=len(oldff),new_ff=sum(ff(c['type']) for c in new['cells'].values()),rom_instances=3,scope='four-state definedness-preserving one-edge transition/all-output/clock/ROM-input correspondence under equal copied state; no startup or ROM-content/physical claim')))
