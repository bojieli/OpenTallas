import json
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-activity-0359/romleaf');f=(p/'romleaf.vcd').open();scope=[];wanted={};names={}
for l in f:
 s=l.strip()
 if s.startswith('\u0024scope'):scope.append(s.split()[2])
 elif s.startswith('\u0024upscope'):scope.pop()
 elif s.startswith('\u0024var'):
  a=s.split();path='.'.join(scope)
  if path=='tb_qwen_romleaf_1552.a.u_rom' and a[2]=='1' and a[4] in ['clk','ce_in','we','we_in','wen']:
   wanted[a[3]]=a[4];names[a[4]]=a[3]
 elif s.startswith('\u0024enddefinitions'):break
assert {'clk','ce_in'}<=set(names),names
state={};last={};high={i:0 for i in wanted};known={i:0 for i in wanted};tog={i:0 for i in wanted};t=0;cycles=0
for l in f:
 if l.startswith('#'):t=int(l[1:]);continue
 if not l or l[0] not in '01xXzZ':continue
 i=l[1:].strip()
 if i not in wanted:continue
 v=l[0].lower();old=state.get(i)
 if old in ['0','1']:
  dt=t-last[i];known[i]+=dt;high[i]+=dt*(old=='1')
  if v in ['0','1'] and v!=old:tog[i]+=1
 if i==names['clk'] and v=='1' and old!='1':cycles+=1
 state[i]=v;last[i]=t
for i,v in state.items():
 if v in ['0','1']:known[i]+=t-last[i];high[i]+=(t-last[i])*(v=='1')
out=dict(scope='actual retained ROMleaf trace macro scalar pins; not macro internal energy calibration',timescale='1ps',duration_ticks=t,cycles=cycles,write_enable='not present on ROM macro',pins={wanted[i]:dict(duty_high=high[i]/known[i] if known[i] else None,known_fraction=known[i]/t,transitions=tog[i],transitions_per_cycle=tog[i]/cycles) for i in wanted})
(p/'macro_pin_activity.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
