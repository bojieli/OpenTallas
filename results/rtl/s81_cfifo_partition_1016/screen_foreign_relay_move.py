import gzip,json
from pathlib import Path
r=Path(__file__).parent;j=json.load(gzip.open('/home/ubuntu/artifacts/s81-connected-0305/first_pass_plan_17b.json.gz','rt'));d={i['name']:dict(i) for i in j['insts']};m=json.loads((r/'sizing.json').read_text());W,H=m['proposal']['outline_um'];rows=[]
for name in ['f_KW3r_22','f_KW3r_25']:
 a=dict(d[name]);a['y']-=54;ovs=[]
 for n,b in d.items():
  if n==name:continue
  b=dict(b)
  if b['master']=='dsfd_cfifo':b['y']+=b['h']-H;b['w']=W;b['h']=H
  if min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x']) and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y']):ovs.append(n)
 rows.append(dict(name=name,old_xy_um=[d[name]['x'],d[name]['y']],candidate_xy_um=[a['x'],a['y']],delta_um=[0,-54],overlaps=ovs,incident_buses=[b for b in j['buses'] if any(e[0]==name for e in b[3])]))
(r/'foreign_relay_move_diagnostic.json').write_text(json.dumps(dict(scope='UNQUALIFIED_FIRST_PASS_RECTANGLE_DIAGNOSTIC_ONLY',source=j['source_commit'],parent_outline_um=[W,H],source_final_pins=False,source_final_hops=False,rows=rows,open=['Check actual relocated input/output pins and every incident bus','Re-run actual relay allocator and channels/cuts','Clock phase plus native timing must be re-proven; no stage-count claim']),indent=2)+'\n')
print([(a['name'],a['overlaps']) for a in rows])
