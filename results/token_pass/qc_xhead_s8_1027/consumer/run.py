import json,os,subprocess,sys
from pathlib import Path
E=Path('/srv/opentallas-scratch2/claude/codex-xh-consumer-1027');T=Path('/srv/opentallas-scratch2/claude/codex-qc-xhead-1027/tree')
sys.path[:0]=[str(T/'rtl/test/qwen_dv'),str(T/'tools/qwen_layerbench')]
import xhead_bench as X

def logread(p):
 d={}
 for line in p.read_text().splitlines():
  c,n,h=line.split();d.setdefault(n,[]).append((int(c),int(h,16)))
 return d
base=logread(E/'fixtures/baseline.log')
streams={}
for family,filename in [('resid','baseline.log'),('silu','silu.log'),('attn','attn.log')]:
 l=logread(E/'fixtures'/filename);ev=[];ea=set()
 for c,(s,a,data) in X.VB.e5_words(l).items():
  # Existing compiler law: ST_HOP4, targetSID0, measured tap+1.
  cyc=c-4*(11-s)+4*s+1
  ev.append((cyc,1,(a<<1024)|data));ea.update(range(a,a+64))
 streams[family]=(sorted(ev),ea)
assert [(c,v>>1024) for c,_,v in streams['resid'][0]]==base['S0XT'],'captured XT law does not match full-row baseline'
fields={name:X.X.dv_fields(X.X.me_ops()[name],streams[X.FAMILY[name]][1]) for name in X.FAMILY}
(E/'runs').mkdir(exist_ok=True)
def run(name,g=None,L=None,baseline=False,isa=False,tag=None):
 ev,ea=streams[X.FAMILY[name]];f=dict(fields[name])
 if isa:f['me_xbase']=f['isa_xbase']
 if baseline:
  hr=[]
  for line in (E/'fixtures/baseline.ev').read_text().splitlines():
   c,p,w=line.split()
   if int(p)==42:hr.append((int(c),2,int(w,16)))
 else:
  first,last=ev[0][0],ev[-1][0]
  hr=[(first-L,2,X.X.hr_word(xpf72=X.X.pack_xpf72(f))),(last+g,2,X.X.hr_word(go=1,ib=X.X.pack_ib(f)))]
 tag='pins6_'+(tag or f'{name}_g{g}_L{L}_isa{int(isa)}');p=E/'runs'/f'{tag}.ev';out=E/'runs'/f'{tag}.log'
 p.write_text(''.join(f'{c} {port} {v:x}\n' for c,port,v in sorted(ev+hr)))
 n=max(c for c,_,_ in hr)+X.X.read_span(f)+256
 pin=E/'runs'/f'{tag}.pins'
 r=subprocess.run([str(E/'obj/Vtb_pins'),f'+EV={p}',f'+LOG={out}',f'+NCYC={n}','+SID=0',f'+PINLOG={pin}'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
 rc=r.returncode
 pins=[tuple(map(int,line.split())) for line in pin.read_text().splitlines()] if pin.exists() else []
 hr_go=[c for c,hr,head,xf in pins if hr];head_go=[c for c,hr,head,xf in pins if head];xf_edges=[c for c,hr,head,xf in pins if xf]
 want_go=[c+1 for c,_,v in hr if (v>>452)&1];want_xf=[c+1 for c,_,v in hr if (v>>1)&1]
 assert hr_go==want_go and xf_edges==want_xf,(tag,'actual control pins differ',hr_go,want_go,xf_edges,want_xf)
 l=logread(out) if out.exists() else {};ok=rc==0 and not l.get('S0HF') and bool(l.get('S0CW')) and l['S0CW'][0][1]==255 and bool(head_go)
 return dict(ok=ok,returncode=rc,hf=l.get('S0HF'),cw=l.get('S0CW'),xl=l.get('S0XL'),hr_go=hr_go,actual_head_go=head_go,xpf=xf_edges,stderr=r.stderr[-1000:])
r=run('gu',baseline=True,tag='actual_full_baseline_replay')
assert r['cw']==base['S0CW'] and r['xl']==base['S0XL'] and r['ok'],('carved baseline differs',r['cw'],base['S0CW'],r['hf'])
res=dict(scope='Exact bound S8 x-delivery component, SID0 four columns and32leaves; captured producer streams. Not a full-row/whole-token pass.',baseline_match=True,full_producer='numeric rc0 and12/12heads clean, x_tap1/d_head21',consumers={})
prior=json.loads((Path(__file__).parent/'evidence/gu_qkv_actual_pin_qualified.json').read_text())
res['consumers']=prior['consumers']
for name in ('o','down'):
 ls={L:run(name,24,L)['ok'] for L in range(0,17)}
 L=min(k for k in ls if all(ls[j] for j in range(k,17)))
 ev=streams[X.FAMILY[name]][0]
 low=ev[0][0]-L-ev[-1][0]+1 # distinct ordered HR writes only
 gs={g:run(name,g,L)['ok'] for g in range(low,25)}
 g=min(k for k in gs if all(gs[j] for j in range(k,25)))
 bounded=g==low
 if bounded:g=24 # Keep arm-late control a distinct HR write; no GO edge is claimed.
 nominal=run(name,g,L,tag=f'{name}_nominal')
 mutants=dict(xpflate=run(name,g,L-1,tag=f'{name}_xpflate'),isaxbase=run(name,g,L,isa=True,tag=f'{name}_isaxbase'))
 if not bounded:mutants['goearly']=run(name,g-1,L,tag=f'{name}_goearly')
 ok=nominal['ok'] and not any(v['ok'] for v in mutants.values()) and not bounded
 res['consumers'][name]=dict(verdict='PASS' if ok else 'NO_LEGAL_GO_BOUNDARY' if bounded else 'FAIL',go_lag=g,xpf_lead=L,legal_go_envelope=[low,24],sweep_go=gs,sweep_xpf=ls,nominal=nominal,mutants=mutants)
 (E/'result_partial_final_pins6.json').write_text(json.dumps(res,indent=1)+'\n')
 print('ACTUAL_S8_XHEAD_CONSUMER',name,res['consumers'][name]['verdict'],g,L,flush=True)
res['verdict']='PASS' if all(x['verdict']=='PASS' for x in res['consumers'].values()) else 'PARTIAL_COMPONENT_ONLY'
(E/'result_final_pins6.json').write_text(json.dumps(res,indent=1)+'\n');raise SystemExit(0 if res['verdict']=='PASS' else 2)
