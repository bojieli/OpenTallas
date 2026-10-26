#!/usr/bin/env python3
"""Count every mapped soft FF of a real CB wrapper, stopping only at explicit hard blackboxes."""
import argparse,collections,json,re
from pathlib import Path
DLY=re.compile(r'(?:^|[./])(u_(?:lpad_[A-Za-z0-9_]+|d[0-9]+_[A-Za-z0-9_]+|pd[0-9]+_[A-Za-z0-9_]+))[./]r\[([0-9]+)\]$')

def census(design,top):
 modules=design['modules'];rows=[];hard=[];unknown=[]
 def walk(module,prefix):
  m=modules[module];aliases=collections.defaultdict(list)
  for name,row in m.get('netnames',{}).items():
   for bit,net in enumerate(row['bits']):
    if isinstance(net,int):aliases[net].append((prefix+name,bit))
  for name,c in m.get('cells',{}).items():
   typ=c['type'];path=prefix+name
   if typ in modules:
    if int(str(modules[typ].get('attributes',{}).get('blackbox','0')),2):hard.append(dict(instance=path,module=typ));continue
    walk(typ,path+'/');continue
   if 'DFF' not in typ.upper():
    if 'LATCH' in typ.upper():unknown.append(dict(instance=path,type=typ))
    continue
   for bit,q in enumerate(c.get('connections',{}).get('Q',[])):
    names=aliases.get(q,[]);delay=[(n,b) for n,b in names if DLY.search(n)];fabric=[(n,b) for n,b in names if 'u_u_fab_u_x_' in n];face=[(n,b) for n,b in names if re.search(r'(?:^|[./])u_b(?:in|out)_',n)];reset=[(n,b) for n,b in names if re.search(r'(?:^|[./])u_(?:rrl|srl|rst|run|rg|ro|so)_',n)]
    n,b=(delay or fabric or face or reset or names or [(path,bit)])[0]
    category='delay' if delay else 'fabric' if fabric else 'boundary' if face else 'reset_start' if reset else 'other'
    row=dict(instance=path,type=typ,register=n,bit=b,category=category,aliases=[dict(name=an,bit=ab) for an,ab in names])
    if delay:
     mm=DLY.search(n);row.update(delay_instance=mm[1],stage=int(mm[2]))
    rows.append(row)
 walk(top,'')
 return dict(scope='ACTUAL_TECHMAPPED_SOFT_LOGIC_ONLY',top=top,soft_ff=len(rows),categories=dict(collections.Counter(r['category'] for r in rows)),ff_types=dict(collections.Counter(r['type'] for r in rows)),hard_blackboxes=hard,unqualified_other_state=unknown,registers=rows)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mapped',type=Path);p.add_argument('--top',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=census(json.loads(a.mapped.read_text()),a.top);a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='registers'}))
if __name__=='__main__':main()
