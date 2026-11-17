from pathlib import Path; exec((Path(__file__).parent/'gen_packets.py').read_text().split('meta={}')[0]); lw=json.loads((P/'lowered_candidate.json').read_text())
import subprocess
out=[]
for c in lw['consumers']:
 op=c['matvec'].rstrip('+1');fam=X.PRODUCER[op];mode='resid' if fam.startswith('resid') else fam
 z,_=L.vec_family(mode,comp['ar_order'] if mode=='resid' else 'slice');ex=z['expected']['x'];f=X.dv_fields(ops[op],set(a for w in ex for a in range(w['eaddr'],w['eaddr']+64)))
 shift=comp['calendar']['shifts'][fam]-(comp['composition']['chained_period'] if c['matvec']=='qkv' else 0)
 for sid in range(12):
  words=[(w['edge_e5']+shift-4*(11-w['slice'])+4*abs(sid-w['slice']),w['eaddr']) for w in ex]
  origin=60-min(e for e,a in words);arm=c['xpf_w5']+lw['hr_arrival'][sid]+1+origin;go=c['go_w5']+lw['hr_arrival'][sid]+1+origin;ncy=max(go+X.read_span(f)+120,max(e+origin for e,a in words)+120)
  assert min(arm,go)>=0
  rows=[0]*ncy
  for e,a in words:rows[e+origin]|=(1<<453)|(a<<454)|(sum(0x4000<<(16*k) for k in range(64))<<478)
  rows[arm]|=X.hr_word(xpf72=X.pack_xpf72(f));rows[go]|=X.hr_word(go=1,ib=X.pack_ib(f))
  fn=P/'lowered_probe.hex';fn.write_text('\n'.join(f'{w:0376x}' for w in rows)+'\n')
  for col in range(4):
   r=subprocess.run([str(P/'obj_actual/Vtb'),f'+input={fn}',f'+ncy={ncy}',f'+sid={sid}',f'+col={col}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   line=next((s for s in r.stdout.splitlines() if s.startswith('RESULT')),'');ok=r.returncode==0 and 'fault=0' in line and 'FAULT ' not in r.stdout
   out.append({'matvec':c['matvec'],'sid':sid,'col':col,'arm_q':arm,'go_q':go,'first_xt':60,'last_xt':max(e+origin for e,a in words),'result':line,'pass':ok})
   if not ok:(P/f'lowered_fail_{c["matvec"]}_s{sid}_c{col}.log').write_text(r.stdout)
(P/'lowered_replay.json').write_text(json.dumps({'source_scope':'native_zero_parent_transport','lowering_errors':lw['errors'],'cases':out,'pass':all(x['pass'] for x in out)},indent=2)+'\n')
print('LOWERED_REPLAY',len(out),'FAIL',sum(not x['pass'] for x in out))
