from pathlib import Path
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');rows=json.load(open(P/'current_graph_lp_all19.json'))[0];byname={c[6]:k for k,c in D.cells.items()}
# Replay finite current variantA, then inspect captures above390 and their exact upstream extrema.
for cid,c in list(D.cells.items()):
 cc=list(c)
 if 'u_cland_i_seq__g_fan_N__u_fan_kc/' in c[6]:cc[3]-=146.88;cc[5]-=146.88
 elif 'u_cland_i_fch_pc_Q_N_q/' in c[6] or 'u_cland_i_kvpc_Q_N_pc__fo/' in c[6]:cc[2]+=172.8;cc[4]+=172.8
 D.cells[cid]=tuple(cc)
for z in rows['targets']:
 cid=byname[z['name']];c=list(D.cells[cid]);x,y=g.ctr(c);dx,dy=z['new'][0]-x,z['new'][1]-y;c[2]+=dx;c[4]+=dx;c[3]+=dy;c[5]+=dy;D.cells[cid]=tuple(c)
bad=[];g.r2r_metrics(D,capture_pairs=bad,collect_above=390);out=[]
for z in bad:
 cap=byname[z['capture']];q=[cap];seen=set();seq=set()
 while q:
  cid=q.pop()
  for ni,ck in D.cell_in.get(cid,[]):
   if ck:continue
   dr=D.nets[ni][1]
   if not dr or dr[0]!='i':continue
   k=dr[1]
   if D.kind(k)=='S':seq.add(k)
   elif k not in seen:seen.add(k);q.append(k)
 us=[(sum(g.ctr(D.cells[k])),k)for k in seq];vs=[(g.ctr(D.cells[k])[0]-g.ctr(D.cells[k])[1],k)for k in seq];ext=[min(us),max(us),min(vs),max(vs)];radius=max(ext[1][0]-ext[0][0],ext[3][0]-ext[2][0])/2
 out.append(dict(z,upstream_count=len(seq),minimum_capture_radius_um=round(radius,4),extreme_launches=[D.cells[k][6]for _,k in ext]))
(P/'margin_diagnosis.json').write_text(json.dumps(out,indent=1)+'\n');print([(z['capture'],z['distance_um'],z['minimum_capture_radius_um'])for z in out])
