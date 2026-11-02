from pathlib import Path
import json,re
p=Path('/srv/opentallas-scratch2/claude/codex-cap-west2-0730-r1/after.def');clean=lambda x:x.replace('\\','');targets={'d3_v[0]$_DFF_PN0_','cw_n_d[126]$_DFF_P_','wire12067','lweco_019416','wire12066','hold13472','_15941_','_17319_','_17320_','wire11949','wire11948','wire19387','lweco_119417','place9190','fanout10577','fanout10576','_17957_','_17958_','_17959_','_17361_'};inst={};nets={};incomp=False;innets=False;buf=''
for line in p.open():
 if line.startswith('COMPONENTS '):incomp=True;continue
 if line.startswith('END COMPONENTS'):incomp=False;continue
 if line.startswith('NETS '):innets=True;continue
 if line.startswith('END NETS'):innets=False;break
 if not(incomp or innets):continue
 buf+=line
 if ';' not in line:continue
 if incomp:
  m=re.search(r'-\s+(\S+)\s+(\S+).*?\+\s+(FIXED|PLACED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)',buf,re.S)
  if m:
   n,master,status,x,y,orient=m.groups();inst[clean(n)]=dict(name=n,master=master,status=status,x=int(x)/1000,y=int(y)/1000,orient=orient)
 else:
  m=re.match(r'\s*-\s+(\S+)',buf)
  if m:
   conn=re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',buf.split('+')[0]);nets[clean(m[1])]=[list(map(clean,x)) for x in conn]
 buf=''
assert targets<=inst.keys(),targets-inst.keys();selected={n:c for n,c in nets.items() if any(i in targets for i,pin in c)};drivers={}
for n in ['lweco_019416','lweco_119417']:
 drivers[n]={pin:[dict(net=k,connections=v,terminal_poses={i:inst[i] for i,p in v if i in inst}) for k,v in selected.items() if [n,pin] in v] for pin in ['A','Y']}
print(json.dumps(dict(source=str(p),scope='READONLY sourceDEF existing reports; NO STA/P&R/candidate edit',path_cells={n:inst[n] for n in sorted(targets)},incident_data_and_clock_nets=selected,two_repeater_inputs_outputs=drivers),indent=2))
