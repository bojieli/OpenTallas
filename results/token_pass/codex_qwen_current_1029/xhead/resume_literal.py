import json, subprocess
from pathlib import Path
P=Path('/srv/opentallas-scratch2/claude/codex-xh-consumer-1027')
E=Path('/srv/opentallas-scratch2/claude/codex-qwen-token-1028/xh_resume')
(E/'runs').mkdir(exist_ok=True)
def read_log(p):
 d={}
 if not p.exists():return d
 for line in p.read_text().splitlines():
  c,n,h=line.split();d.setdefault(n,[]).append((int(c),int(h,16)))
 return d
result={}
for name in ('o','down'):
 rows=[(int(c),int(p),int(v,16)) for c,p,v in (l.split() for l in (P/'runs'/f'pins6_{name}_nominal.ev').read_text().splitlines())]
 data=[r for r in rows if r[1]==1]
 hr=[r for r in rows if r[1]==2]
 arm=next(r for r in hr if (r[2]>>1)&1)
 go=next(r for r in hr if (r[2]>>452)&1)
 cases={}
 for delta in (1,-1,-3,-7,-15,-23,-31):
  go_c=arm[0]+delta
  if go_c<0:continue
  tag=f'{name}_go_arm{delta:+d}'
  ev=E/'runs'/f'{tag}.ev';out=E/'runs'/f'{tag}.log';pin=E/'runs'/f'{tag}.pins'
  ev.write_text(''.join(f'{c} {p} {v:x}\n' for c,p,v in sorted(data+[arm,(go_c,2,go[2])])))
  r=subprocess.run([str(P/'obj/Vtb_pins'),f'+EV={ev}',f'+LOG={out}','+NCYC=10000','+SID=0',f'+PINLOG={pin}'],capture_output=True,text=True)
  pins=[tuple(map(int,l.split())) for l in pin.read_text().splitlines()]
  hg=[c for c,hr,h,x in pins if hr];xf=[c for c,hr,h,x in pins if x];head=[c for c,hr,h,x in pins if h]
  assert hg==[go_c+1] and xf==[arm[0]+1],(tag,hg,xf,go_c,arm)
  l=read_log(out);ok=r.returncode==0 and not l.get('S0HF') and bool(l.get('S0CW')) and l['S0CW'][0][1]==255 and bool(head)
  cases[str(delta)]=dict(ok=ok,returncode=r.returncode,hr_go=hg,head_go=head,xpf=xf,hf=l.get('S0HF'),cw=l.get('S0CW'),xl=l.get('S0XL'),stderr=r.stderr[-1000:])
  print(name,delta,ok,flush=True)
  if delta<0 and not ok:break
 result[name]=dict(arm_edge=arm[0],data_first=data[0][0],data_last=data[-1][0],cases=cases)
 (E/'result_literal.json').write_text(json.dumps(result,indent=2)+'\n')
