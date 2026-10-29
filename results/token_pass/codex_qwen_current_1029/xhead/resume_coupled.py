import json,subprocess
from pathlib import Path
P=Path('/srv/opentallas-scratch2/claude/codex-xh-consumer-1027');E=Path('/srv/opentallas-scratch2/claude/codex-qwen-token-1028/xh_resume')
def read(p):return [(int(c),int(port),int(v,16)) for c,port,v in (l.split() for l in p.read_text().splitlines())]
result={}
for name in ('o','down'):
 base=read(P/'runs'/f'pins6_{name}_nominal.ev');data=[r for r in base if r[1]==1]
 arm=next(r for r in base if r[1]==2 and r[2]&2);go=next(r for r in base if r[1]==2 and r[2]>>452)
 isa=read(P/'runs'/f'pins6_{name}_isaxbase.ev');ia=next(r for r in isa if r[1]==2 and r[2]&2);ig=next(r for r in isa if r[1]==2 and r[2]>>452)
 cases={}
 for case,hr in [('xpflate',[(arm[0]+1,2,arm[2]|go[2])]),('isa',[(arm[0],2,ia[2]),(arm[0]+1,2,ig[2])])]:
  tag=f'{name}_coupled_{case}';ev=E/'runs'/f'{tag}.ev';out=E/'runs'/f'{tag}.log';pin=E/'runs'/f'{tag}.pins'
  ev.write_text(''.join(f'{c} {p} {v:x}\n' for c,p,v in sorted(data+hr)))
  r=subprocess.run([str(P/'obj/Vtb_pins'),f'+EV={ev}',f'+LOG={out}','+NCYC=10000','+SID=0',f'+PINLOG={pin}'],capture_output=True,text=True)
  pins=[tuple(map(int,l.split())) for l in pin.read_text().splitlines()];hg=[c for c,h,g,x in pins if h];xf=[c for c,h,g,x in pins if x]
  assert hg==[c+1 for c,p,v in hr if v>>452] and xf==[c+1 for c,p,v in hr if v&2],(tag,hg,xf)
  log={}
  for line in out.read_text().splitlines():
   c,n,v=line.split();log.setdefault(n,[]).append((int(c),int(v,16)))
  ok=r.returncode==0 and not log.get('S0HF') and bool(log.get('S0CW')) and log['S0CW'][0][1]==255
  cases[case]=dict(ok=ok,hr_go=hg,xpf=xf,hf=log.get('S0HF'),returncode=r.returncode)
  print(name,case,ok,flush=True)
 result[name]=cases
(E/'result_coupled_controls.json').write_text(json.dumps(result,indent=2)+'\n')
assert not any(v['ok'] for x in result.values() for v in x.values())
