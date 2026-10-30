import re,json
from pathlib import Path
r=Path(__file__).resolve().parent;old=r/'full_boot_actual';o=r/'full_boot_actual_pruned';o.mkdir(exist_ok=True)
def clean(s):return re.sub(r'/\*.*?\*/|//[^\n]*|\(\*.*?\*\)','',s,flags=re.S)
def refs(s):return set(re.findall(r'(?<![.\w])\b[A-Za-z_]\w*\b',s))
def io_decls(head):
 out={}
 for d in re.findall(r'\b(?:input|output|inout)\s+(?:wire\s+|reg\s+)?(?:\[[^]]+\]\s*)?\w+',head):
  n=d.split()[-1];out[n]=d
 return out
def slice_body(body,insts,head):
 decls=re.findall(r'^\s*(?:wire|reg|localparam|parameter)\s+[^;]+;',body,re.M)
 assigns=re.findall(r'\bassign\s+[^;]+;',body)
 needed=set().union(*(refs(c) for c in insts));oldn=None
 while oldn!=needed:
  oldn=needed.copy()
  for a in assigns:
   lhs=a.split('=',1)[0].split()[1];lhs=re.sub(r'\[.*','',lhs)
   if lhs in needed:needed|=refs(a)
  for d in decls:
   # Include initializer dependencies if any declared name used.
   name=re.sub(r'\[[^]]*\]','',d).split(';')[0].split('=',1)[0].split()[-1]
   if name in needed:needed|=refs(d)
 chosen=[]
 for d in decls:
  names=refs(re.sub(r'\[[^]]*\]','',d).split('=',1)[0]) - {'wire','reg','parameter','localparam','integer'}
  if names&needed:chosen.append(d)
 for a in assigns:
  lhs=re.sub(r'\[.*','',a.split('=',1)[0].split()[1])
  if lhs in needed:chosen.append(a)
 ports=io_decls(head);used={n:d for n,d in ports.items() if n in needed}
 return chosen,used
mods={};text=[]
for m in re.finditer(r'\bmodule\s+(\w+)\s*(?:#\s*\(.*?\)\s*)?\(.*?\bendmodule',(old/'controls.sv').read_text(),re.S):
 s=clean(m[0]);end=s.index(');')+2;head=s[:end];body=s[end:-len('endmodule')]
 insts=re.findall(r'\bot_dp_\w+\s+(?:#\s*\([^;]*?\)\s*)?\w+\s*\([^;]*?\);',body,re.S)
 if m[1]=='kv3_hub_C_part':insts.append("qkd_pll_analog_model #(.CORE_HALF(0.4165)) u_pll_boot_model(.por_n(arst_n),.refclk(io_pad_refclk[0]),.locked(w_pll_locked));")
 decl,ports=slice_body(body,insts,head);mods[m[1]]=set(ports)
 # Preserve original module parameters, unused mission parameters accepted by top.
 prefix=head[:head.index('(')]
 if '#' in head:prefix=head[:head.rindex(') (')+2] if ') (' in head else prefix
 params=re.match(r'module\s+\w+\s*(#\s*\(.*?\))?\s*\(',head,re.S)[1] or ''
 text.append('module '+m[1]+' '+params+'(\n'+',\n'.join(ports.values())+'\n);\n'+'\n'.join(decl+insts)+'\nendmodule')
(o/'controls.sv').write_text('\n'.join(text))
top=clean((old/'top.sv').read_text());end=top.index(');')+2;head=top[:end];body=top[end:top.rfind('endmodule')]
insts=[]
for m in re.finditer(r'^\s*(\w+)\s+(?:#\s*\([^;]*?\)\s*)?(\w+)\s*\([^;]*?\);',body,re.M|re.S):
 typ,name=m[1],m[2]
 if typ in mods:
  ports=[]
  for p in re.finditer(r'\.(\w+)\(([^()]*)\)',m[0]):
   if p[1] in mods[typ]:ports.append('.'+p[1]+'('+("1'b1" if p[1]=='pll_locked_i' else p[2])+')')
  # Drop unused mission parameter overrides; defaults don't affect kept controls.
  insts.append(typ+' '+name+'('+','.join(ports)+');')
 elif typ.startswith('ot_dp_'):insts.append(m[0])
decl,ports=slice_body(body,insts,head)
decl=re.findall(r'\b(?:input|output|inout)\s+[^;]+;',body)+decl
# Retain top interface so existing bench connections remain exactly mapped.
(o/'top.sv').write_text(head+'\n'+'\n'.join(decl+insts)+'\nendmodule')
(o/'tb.sv').write_text((old/'tb.sv').read_text())
(o/'extraction.json').write_text(json.dumps({'module_control_ports':{n:sorted(v) for n,v in mods.items()},'top_kept_instances':len(insts),'top_kept_statements':len(decl),'note':'Nativeinstances unchanged; unusedmissionwire/port cone pruned. FunctionalCAS payloadW1 only. Sourcecommonphase diagnostic.'},indent=1))
print('modules',len(mods),'topinstances',len(insts),'topdecl',len(decl),'sizes',[(n,(o/n).stat().st_size) for n in ['controls.sv','top.sv']])
