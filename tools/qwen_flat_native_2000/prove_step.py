"""Independent arbitrary-state one-edge correspondence after priced reset release."""
from pathlib import Path
import json,re,sys
sys.path.insert(0,str(Path(__file__).parent));from bound_flat_graph import GATES,FFS,MACROS
orig=json.loads(Path(sys.argv[1]).read_text())['modules']['ot_hdc_vstream_lane'];receipt=json.loads(Path(sys.argv[2]).read_text());new=receipt['graph'];origins=receipt['origins'];out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
inputs={b for p in orig['ports'].values()if p['direction']=='input' for b in p['bits']if isinstance(b,int)}
states={b for c in orig['cells'].values()if c['type']in FFS for b in c['connections']['Q']}
macro_bits={b for c in orig['cells'].values()if c['type']in MACROS for p,bs in c['connections'].items()if c['port_directions'][p]=='output' for b in bs}
variables=sorted(inputs|states|macro_bits);indices={b:i for i,b in enumerate(variables)}
lines=[f'module step_miter(input wire [{len(variables)-1}:0] v,output wire bad);'];neq=[]
def bn(prefix,b):return prefix+str(b) if isinstance(b,int) else "1'b"+b
def bus(prefix,bs):return '{'+','.join(bn(prefix,b)for b in reversed(bs))+'}'
def emit(m,prefix,is_new):
 bits={b for c in m['cells'].values()for bs in c['connections'].values()for b in bs if isinstance(b,int)}|{b for p in m['ports'].values()for b in p['bits']if isinstance(b,int)}
 for k in range(0,len(bits),128):lines.append('wire '+','.join(prefix+str(b)for b in sorted(bits)[k:k+128])+';')
 for p in orig['ports'].values():
  if p['direction']=='input':
   for b in p['bits']:
    if isinstance(b,int):lines.append(f'assign {prefix}{b} = '+("1'b1" if b in orig['ports']['rst_n']['bits'] else f'v[{indices[b]}]')+';')
 for name,c in m['cells'].items():
  typ=c['type'];x=c['connections']
  if typ=='$scopeinfo':continue
  if typ in MACROS:
   original=next(c for c in orig['cells'].values()if c['type']in MACROS)
   for p,bs in x.items():
    if c['port_directions'][p]=='output':
     for b,old in zip(bs,original['connections'][p]):
      if isinstance(b,int):lines.append(f'assign {prefix}{b}=v[{indices[old]}];')
    elif is_new:neq.append(f'({bus("a",original["connections"][p])} != {bus(prefix,bs)})')
  elif typ in FFS:
   if is_new and name.startswith('$reset_forest_'):lines.append(f'assign {prefix}{x["Q"][0]}=1\'b1;');continue
   source=orig['cells'][origins[name]] if is_new else c
   for b,old in zip(x['Q'],source['connections']['Q']):lines.append(f'assign {prefix}{b}=v[{indices[old]}];')
  elif typ in GATES:
   expr=GATES[typ]
   for p in ('A','B','S','X'):
    if p in x:expr=re.sub(r'\b'+p+r'\b','('+bus(prefix,x[p])+')',expr)
   lines.append('assign '+bus(prefix,x['Y'])+'='+expr+';')
  else:raise ValueError(typ)
def transition(prefix,c):
 d=bus(prefix,c['connections']['D']);typ=c['type']
 if 'R'in c['connections']:
  r=bus(prefix,c['connections']['R']);pol,val=typ[-3:-1];test='!'+r if pol=='N'else r;d=f'({test}?1\'b{val}:{d})'
 return d
emit(orig,'a',False);emit(new,'b',True)
for name,c in new['cells'].items():
 if c['type']in FFS and not name.startswith('$reset_forest_'):
  neq.append('('+transition('a',orig['cells'][origins[name]])+' != '+transition('b',c)+')')
for name,p in orig['ports'].items():
 if p['direction']=='output':neq.append('('+bus('a',p['bits'])+' != '+bus('b',new['ports'][name]['bits'])+')')
lines.append('assign bad=|'+'{'+','.join(neq)+'};endmodule');(out/'step_miter.sv').write_text('\n'.join(lines)+'\n')
(out/'step_model.json').write_text(json.dumps(dict(arbitrary_variables=len(variables),next_state_and_boundary_comparisons=len(neq),assumption='Actual three-edge reset forest has released; all original reset terminals and reset forest Q=1; every other original FF state and macro output unconstrained',primitive_types=sorted({c['type']for c in orig['cells'].values()}),scope='One-edge full generic source correspondence; separate actual reset cold/dirty and emitted RTL lockstep required'),indent=2)+'\n')
print(len(variables),len(neq))
