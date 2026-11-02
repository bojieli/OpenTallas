from pathlib import Path
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent
out=[]
for variant,dy,dx in [('A',-146.88,172.8),('B',-151.2,181.44)]:
 D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');byname={c[6]:cid for cid,c in D.cells.items()};missing=[];changed=[]
 def shift(cid,dx,dy):
  cc=list(D.cells[cid]);cc[2]+=dx;cc[4]+=dx;cc[3]+=dy;cc[5]+=dy;D.cells[cid]=tuple(cc)
 for cid,c in list(D.cells.items()):
  if 'u_cland_i_seq__g_fan_N__u_fan_kc/' in c[6]:shift(cid,0,dy)
  elif 'u_cland_i_fch_pc_Q_N_q/' in c[6] or 'u_cland_i_kvpc_Q_N_pc__fo/' in c[6]:shift(cid,dx,0)
 rows=json.load(open('/home/ubuntu/coord/tmp/codex-kv-hroot/reloc'+variant+'.json'))
 for r in rows:
  cid=byname.get(r['name'])
  if cid is None:missing.append(r['name']);continue
  old=g.ctr(D.cells[cid]);x,y=r['new'];shift(cid,x-old[0],y-old[1]);changed.append(r['name'])
 bad=[];m=g.r2r_metrics(D,capture_pairs=bad)
 out.append(dict(variant=variant,scope='STATIC replay of prior absolute FF targets and rigid landing translations onto current actual213407-cell/22411FF graph; no plan/CAD edits',matched_prior_targets=len(changed),missing_prior_targets=missing,metrics=m,remaining_bad=bad,landing_dy_um=dy,landing_dx_um=dx,held=['These old coordinates were solved on countb22408FF; no current LP repair performed.','Paired pins/control/clock/bands/provider event not materialized.','No occupancy, TAP/PG, pin registration or clock closure claim.']))
(P/'prior_replay_current_graph.json').write_text(json.dumps(out,indent=1)+'\n')
for r in out:print(r['variant'],r['matched_prior_targets'],len(r['missing_prior_targets']),r['metrics'])
