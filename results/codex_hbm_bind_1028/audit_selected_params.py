"""Diagnose top/alias parameters absent from the actually selected preferred master."""
import json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'tools/die_plan'),str(root/'tools')]
import bind_elab as E,die_port_bind as D
ab=json.loads(Path(sys.argv[1]).read_text());ab['base']=str(root);top=Path(sys.argv[2]).read_text()
idx=E.module_index(ab['rtl_roots'],ab.get('files',[]),root);prefer=[str(root/p) if not Path(p).is_absolute() else p for p in ab.get('prefer',[])];cache={};rows=[]
for m in re.finditer(r'^\s+([\w$]+)\s+(?:#\((.*?)\)\s+)?([\w$]+)\s*\(\s*$',top,re.M):
 original,params,inst=m.groups();selected=ab.get('alias',{}).get(original,original)
 if selected not in cache:
  f,_=E.pick(idx,selected,prefer)
  cache[selected]=(f,next((x for x in D.parse_modules(Path(f).read_text(),f) if x.name==selected),None)) if f else (None,None)
 f,mod=cache[selected]
 if not mod:continue
 requested=re.findall(r'\.(\w+)\s*\(',params or '');missing=sorted(set(requested)-set(mod.params))
 if missing:rows.append(dict(inst=inst,original_master=original,selected_master=selected,source=str(Path(f).relative_to(root)),requested_params=params,missing=missing))
Path(sys.argv[3]).write_text(json.dumps(dict(schema='opentallas.hbm.selected_params.v1',failures=rows),indent=2)+'\n');print(json.dumps(rows,indent=2))
