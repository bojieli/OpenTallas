import json,re,sys
names=set(json.load(open(sys.argv[1])))
p=sys.argv[2];rows=[];active=False;buf='';dbu=None
for line in open(p):
 if line.startswith('UNITS DISTANCE MICRONS'):dbu=int(line.split()[3])
 if line.startswith('COMPONENTS '):active=True;continue
 if not active:continue
 if line.startswith('END COMPONENTS'):break
 buf+=line
 if ';' not in line:continue
 m=re.match(r'\s*-\s+(\S+)\s+(\S+).*?\+\s+(PLACED|FIXED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)',buf,re.S)
 if m:
  n,master,status,x,y,orient=m.groups();n=n.replace('\\','')
  if n in names or master.startswith('ot_s81hd_elem'):
   rows.append(dict(name=n,master=master,status=status,x=int(x)/dbu,y=int(y)/dbu,orient=orient))
 buf=''
d=dict(path=p,dbu=dbu,rows=rows,missing=sorted(names-{r['name'] for r in rows}))
open(sys.argv[3],'w').write(json.dumps(d,indent=1)+'\n')
print('dbu',dbu,'selected',len(rows),'missing',len(d['missing']))
