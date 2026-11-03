from pathlib import Path
import re,json
p=Path('/srv/opentallas-scratch2/claude/s81ck10/kits/ot_s81sl_xrt1_ck13P3M110/run/results/asap7/kl_ot_s81sl_xrt1_ck10/base/6_final.def');rows=[];taps=[];inside=False;buf=''
for line in p.open():
 if line.startswith('ROW '):rows.append(line.strip())
 if line.startswith('COMPONENTS '):inside=True;continue
 if line.startswith('END COMPONENTS'):break
 if not inside:continue
 buf+=line
 if ';' not in line:continue
 if 'TAPCELL' in buf:
  m=re.search(r'-\s+(\S+)\s+(\S+).*?\+\s+(FIXED|PLACED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)',buf,re.S)
  if not m:raise ValueError(buf)
  n,master,status,x,y,orient=m.groups();taps.append(dict(name=n,master=master,status=status,x=int(x)/1000,y=int(y)/1000,orient=orient))
 buf=''
print(json.dumps(dict(source=str(p),rows=rows,taps=taps)))
