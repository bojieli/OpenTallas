from pathlib import Path
import re,json,collections,argparse
p=argparse.ArgumentParser(description='Exact current HOST reset-spine consumer census');p.add_argument('--bind-out',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args();b=args.bind_out;out=args.out;out.mkdir(parents=True,exist_ok=True)

def clean(s):return re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
def instances(text):
 s=clean(text);result=[]
 for m in re.finditer(r'^\s*(\w+)\s+(?:#\((.*?)\)\s*)?(\w+)\s*\(',s,re.M|re.S):
  ty,par,name=m.group(1,2,3)
  if ty=='module':continue
  start=m.end();depth=1;k=start
  while k<len(s) and depth:
   depth+=(s[k]=='(')-(s[k]==')');k+=1
  args=s[start:k-1];cs={}
  for c in re.finditer(r'\.(\w+)\s*\(',args):
   a=c.end();z=a;d=1
   while z<len(args) and d:d+=(args[z]=='(')-(args[z]==')');z+=1
   cs[c[1]]=args[a:z-1].strip()
  result.append(dict(type=ty,params=par or '',name=name,ports=cs))
 return result

top=(b/'rtl/qwen_kvsys_bound_top.sv').read_text();cells=instances(top);host=next(c for c in cells if c['name']=='hub_Wi');plan=json.load(open(args.plan));part={p['name']:p for p in plan['partitions']};by_type={}
for f in (b/'rtl').glob('*.sv'):
 s=f.read_text()
 for m in re.finditer(r'^module\s+(\w+)',s,re.M):by_type[m[1]]=(f,s)
rows=[]
for pin,net in host['ports'].items():
 m=re.fullmatch(r'rs_host_(die_rst_n|hbm_rst_n|host_rst_n)__(\d+)',pin)
 if not m:continue
 consumers=[]
 for c in cells:
  if c is host:continue
  for cp,expr in c['ports'].items():
   if re.search(r'\b'+re.escape(net)+r'\b',expr):
    f,body=by_type[c['type']];local=instances(body);sync=[x for x in local if x['type']=='ot_dp_rsync' and re.search(r'\b'+re.escape(cp)+r'\b',x['ports'].get('a',''))];uses=[]
    for rs in sync:
     q=rs['ports']['q']
     uses += [dict(instance=x['name'],module=x['type'],pin=p,expr=e) for x in local if x is not rs for p,e in x['ports'].items() if re.search(r'\b'+re.escape(q)+r'\b',e)]
    pt=part.get(c['name']);t=plan['partition_types'][pt['type']] if pt else {}
    buses=[dict(name=x['name'],width=x['width']) for x in t.get('buses',[]) if x['dir']=='in' and m[1] in x['name']]
    candidates=[]
    for ln in body.splitlines():
     if re.match(r'\s*input\s+wire',ln) and m[1] in ln and 'lane ' in ln:candidates.append(ln.strip())
    consumers.append(dict(partition=c['name'],type=pt['type'] if pt else None,module=c['type'],port=cp,source=str(f),sync=sync,uses=uses,planned_same_family_buses=buses,bound_same_family_input_lines=candidates))
 rows.append(dict(host_pin=pin,family=m[1],net=net,consumers=consumers,lexical_top_uses=len(re.findall(r'\b'+re.escape(net)+r'\b',clean(top)))))
summary={'outputs':len(rows),'families':dict(collections.Counter(r['family'] for r in rows)),'dead':sum(not r['consumers'] for r in rows),'consumer_ports':sum(len(r['consumers']) for r in rows),'functional_leaf_pin_uses':sum(len(c['uses']) for r in rows for c in r['consumers']),'with_same_family_plan_bus':sum(bool(c['planned_same_family_buses']) for r in rows for c in r['consumers']),'by_type':dict(collections.Counter(c['type'] for r in rows for c in r['consumers']))}
(out/'reset_census.json').write_text(json.dumps(dict(summary=summary,rows=rows),indent=1)+'\n');(out/'ot_dp_rsync.sv').write_text(re.search(r'module ot_dp_rsync\s*#.*?endmodule',(b/'rtl/bind_cells.sv').read_text(),re.S)[0]+'\n');print(json.dumps(summary,indent=1))
