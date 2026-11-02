from pathlib import Path
import re,json
p=Path('/srv/opentallas-scratch2/claude/codex-cap-west2-0730-r1/after.def');names={'_27644_','_27645_','_27646_','wire19289','wire19399','wire17963','lweco_219418','_27650_'};rows=[];obs=[];targets={};blockages=[];comp=False;buf=''
for line in p.open():
 if line.startswith('ROW '):rows.append(line.strip())
 if line.startswith('COMPONENTS '):comp=True;continue
 if line.startswith('END COMPONENTS'):break
 if not comp:continue
 buf+=line
 if ';' not in line:continue
 m=re.search(r'-\s+(\S+)\s+(\S+).*?\+\s+(FIXED|PLACED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)',buf,re.S);buf=''
 if not m:continue
 n,master,status,x,y,orient=m.groups();x,y=int(x)/1000,int(y)/1000;r=dict(name=n,master=master,status=status,x=x,y=y,orient=orient)
 if n in names:targets[n]=r
 if ((88<x<120 and 76<y<96) or (28<x<42 and 30<y<90) or (94<x<106 and 34<y<41)) and not master.startswith('FILLER'):obs.append(r)
print(json.dumps(dict(actual_DEF=str(p),rows=rows,region_instances=obs,targets=targets),separators=(',',':')))
