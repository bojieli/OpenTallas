from pathlib import Path
import sys,json,hashlib
B=Path('/srv/opentallas-scratch2/claude/codex-ds-bf-1131');source=B/'source';sys.path[:0]=[str(source/'tools'),str(source/'tools/s81_dv'),str(source/'tools/s81_dv/layer_prog')]
import lower_xs as L
import xs_calendar as X
from pq_calendar import viamap
R=Path('/srv/opentallas-scratch2/claude/codex-ds-bf-native-programme-0605');R.mkdir(exist_ok=False)
F=Path('/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2/field');raw=F/'images.phase_local/_field'
P=[int(x,16)for x in(raw/'spine_phase.hex').read_text().split()];S=[int(x,16)for x in(raw/'spine_stream.hex').read_text().split()]
c=X.compile_pipeline(P,S,[106],0,512,cfg_lead=63,acc_gap=20,retire_gap=30)
assert X.phase_word(P,106)['bf']==1
L.xs_roms(raw,R)
(R/'pq_calendar_action.viamap.hex').write_text(viamap([x&((1<<72)-1)for x in c['packed']]))
(R/'pq_calendar_time.viamap.hex').write_text(viamap([x>>72 for x in c['packed']]))
iss=dict(c['iss']);iss[310-256+3]=X.isd(gw=1,gw_fam=1,gw_par=0)
ctl=[(t+256-3,0,1|(4<<9)|((1|(2<<16)|(v<<26))<<21))for t,v in iss.items()]
base=Path('/srv/opentallas-scratch2/claude/codex-ds-bf-source-bridge-0442/current_actual_BF')
for label,file in [('actual','producer.txt'),('wrong_operand','wrong_norm_operand_producer.txt')]:
 ev=[(int(t),int(k),int(v,16))for t,k,v in (x.split()for x in(base/file).read_text().splitlines())];ring=[x for x in ev if x[1]==2];bf=[]
 for i in range(0,len(ring),4):
  part=ring[i:i+4];packet=sum((z[2]&((1<<276)-1))<<(276*j)for j,z in enumerate(part))
  if (packet>>1)&7==2:
   for j,z in enumerate(part):bf.append((370+len(bf),2,z[2]))
 assert len(bf)==256
 (R/(label+'_producer.txt')).write_text(''.join(f'{t} {k} {v:x}\n'for t,k,v in sorted(ctl+bf)))
for key in ['pq_calendar_action','pq_calendar_time','pq_phase0','pq_stream0','pq_stream1','pq_stream2','pq_stream3']:(R/('u_s_0S.u_sl.u_xg.'+key+'.viamap.hex')).symlink_to(key+'.viamap.hex')
vm=json.loads((B/'h10vec/meta.json').read_text())
gold=[dict(row=int(k),segment=0,nseg=4,fp32=f'{v["vals"][0]:08x}',full_accumulation=f'{v["acc"]:08x}')for k,v in vm['rows'].items()]
(R/'programme.json').write_text(json.dumps(dict(scope='One real phase106, actual field programme and held-constant preloaded real operand; no mission epoch/provider qualification',field=str(F),phases=c['phases'],cal_rows=c['cal_rows'],iss={str(k):hex(v)for k,v in iss.items()},gold=gold,retained_native_core_to_partial_edges=174,all_global_qualification_flags=False),indent=2)+'\n')
print(json.dumps(dict(phases=c['phases'],cal_rows=c['cal_rows'],gold=gold[:2]),indent=2))
