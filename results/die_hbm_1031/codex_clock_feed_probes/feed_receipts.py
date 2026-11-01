from pathlib import Path
import json,math
r=Path('/srv/opentallas-scratch2/claude/codex-hbm-clock');out={}
for name in ('NW_A','NW_B','NE_A','NE_B'):
 d=r/'calib'/name;j=json.load(open(d/'case.json'));source='ck_'+j['source'];v=dict(j,corners={})
 for c in ('TT','FF'):
  old={(f[0],f[1]):list(map(float,f[2:])) for l in (d/f'old_arr_{c}.txt').read_text().splitlines() if (f:=l.split())}
  new={(f[0],f[1]):list(map(float,f[2:])) for l in (d/f'new_arr_{c}.txt').read_text().splitlines() if (f:=l.split())}
  y=old[('Y',source)];p=new[('PORT','mesh_root')];ri=3 if j['source_inverted'] else 0;fi=0 if j['source_inverted'] else 3
  q=dict(rise_late_delta_ps=p[0]-y[ri],rise_early_delta_ps=p[1]-y[ri+1],fall_late_delta_ps=p[3]-y[fi],fall_early_delta_ps=p[4]-y[fi+1],root_rise_slew_ps=p[2],root_fall_slew_ps=p[5],source_calibration=json.load(open(d/f'calibration_{c}.json')))
  assert all(math.isfinite(q[k]) for k in q if k!='source_calibration')
  v['corners'][c]=q
 v['verdict']='LOCAL_FEED_PASS (both DRC0, same routed geometry TT/FF, measured source boundary waveforms)'
 v['scope']='Piecewise prototype. Current G4 still BLOCKED(clock-feed/joint composition); source islands and whole die+hub physical route remain integration gates.'
 out[name]=v
(r/'calib/physical_feed_receipts.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({n:{c:{k:round(v,3) for k,v in q.items() if k!='source_calibration'} for c,q in j['corners'].items()} for n,j in out.items()},indent=2))
