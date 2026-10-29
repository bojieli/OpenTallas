"""Candidate only: spread actual GQ output without adopting unrealized stations."""
import json,math,hashlib,sys
from pathlib import Path
base=Path(sys.argv[1]); out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
d=json.loads((base/'die_plan.json').read_text());reports=[]
for typ,t in d['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')!='ot_hgi_coll_gq_issue':continue
  old=base/c['pins_file'];a=json.loads(old.read_text()); before={r['name']:dict(r) for r in a}
  for r in a:
   if r['name'].startswith('ra_lp_data['):
    k=int(r['name'].split('[')[1][:-1]);r['y']=round(.024+.048*round((9.0+219.6*k/255-.024)/.048),3)
  changed=[r['name'] for r in a if r!=before[r['name']]]
  assert set(changed)=={'ra_lp_data[%d]'%k for k in range(256)}
  assert len({(r['layer'],r['x'],r['y'])for r in a if r['name'].startswith('ra_lp_data[')})==256
  new=Path('cores')/(old.stem+'__srcout_spread.json');(out/new).parent.mkdir(exist_ok=True);(out/new).write_text(json.dumps(a,indent=1));c['pins_file']=str(new)
  ys=sorted(r['y']for r in a if r['name'].startswith('ra_lp_data['));oldys=[before['ra_lp_data[%d]'%i]['y']for i in range(256)]
  reports.append(dict(type=typ,instance=c['inst'],pins_file=str(new),changed_data_pins=256,other_pins_exact=3776,old_span_um=max(oldys)-min(oldys),new_span_um=ys[-1]-ys[0],new_face_fraction=(ys[-1]-ys[0])/237.6,peak_10um=max(sum(y<=z<y+10 for z in ys)for y in ys)/10,bit_order='ascending k preserved',track='M4 y=.024+n*.048',source_realization='q1 only; q0 UNREALIZED'))
(out/'die_plan.json').write_text(json.dumps(d,indent=1))
r=dict(status='SRC OUT candidate; NO P&R',clock=dict(layer='M5',x=116.664,y=116.64,w=.048,h=.48),users=reports,actual_source_edges='hcollgi_NE/NW.ra_lp_data[k] -> hb_coll_NE/NW.ra_lp_data[k], q1 only',bound_last_station_sites=0,station_reach_status='UNREALIZED / no actual bound sites; no qualified station reach delta available',q0_status='UNREALIZED: no native producer',cycles_added=0)
(out/'gq_srcout_report.json').write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
