from pathlib import Path
import re,json
k=Path('/srv/opentallas-scratch2/claude/codex-q2nf-0222/kit');s=(k/'run/results/asap7/hbc_ot_q2nf_rest/base/1_2_yosys.v').read_text();libs={}
for f in (k/'macros').glob('*.lef'):
 text=f.read_text();pins={}
 for name,b in re.findall(r'\n  PIN (\S+)\n(.*?)\n  END \1',text,re.S):
  if 'USE SIGNAL'not in b:continue
  q=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',b);x0,y0,x1,y1=map(float,q.groups());pins[name]=dict(layer=re.search(r'LAYER (\w+)',b)[1],x=(x0+x1)/2,y=(y0+y1)/2)
 libs[f.stem]=pins
pat=re.compile(r"(\d+)'[bBoOdDhH]([0-9a-fA-FxXzZ_]+)$")
def expand(c):
 c=c.strip()
 if not c:return []
 if c.startswith('{'):c=c[1:-1].strip()
 out=[]
 for t in c.split(','):
  t=t.strip();m=pat.fullmatch(t)
  if m:out.extend([None]*int(m[1]));continue
  assert t and not re.search(r'\s',t),repr(t)
  out.append(t.lstrip('\\'))
 return list(reversed(out))
rows=[];errors=[]
for m in re.finditer(r'(ot_sram_\w+)\s+(\\\S+|\S+)\s*\((.*?)\n\s*\);',s,re.S):
 master,inst,body=m.groups();con={p:expand(c)for p,c in re.findall(r'\.(\w+)\((.*?)\)(?:,|\s*\n|$)',body,re.S)}
 for name,pos in libs[master].items():
  mm=re.fullmatch(r'(.+)\[(\d+)\]',name);port,bit=(mm[1],int(mm[2]))if mm else(name,0)
  if port not in con or bit>=len(con[port]):errors.append([inst,name]);continue
  net=con[port][bit]
  if net is not None:rows.append(dict(inst=inst.lstrip('\\'),pin=name,net=net,**pos))
r=dict(schema='codex.q2nf.actual_macro_signal_pins.v1',pin_records=len(rows),distinct_nets=len({p['net']for p in rows}),errors=errors,pins=rows)
(k.parent/'macro_pinmap.json').write_text(json.dumps(r,indent=1));print(r['pin_records'],r['distinct_nets'],'mapping_errors',len(errors));assert not errors
