import sys,json,inspect
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
p=Path(__file__).parent;v=sys.argv[1];D=G.Design(p/'tile_geom.tsv');a=json.load(open(p/(v+'_groups.json')));by={c[6]:i for i,c in D.cells.items()}
for k,names in a['groups'].items():
 r=a['rects'][k];x,y=(r[0]+r[2])/2,(r[1]+r[3])/2
 for n in names:
  i=by[n];c=D.cells[i];w,h=c[4]-c[2],c[5]-c[3];D.cells[i]=c[:2]+(x-w/2,y-h/2,x+w/2,y+h/2)+c[6:]
s=inspect.getsource(G.r2r_metrics).replace('def r2r_metrics(D):','def trial_pairs(D):').replace('best, arg, n_gt = 0.0, None, 0','best, arg, n_gt = 0.0, None, 0\n    longpairs=[]').replace('n_gt += 1','n_gt += 1\n            longpairs.append((mx,D.cells[src][6],D.cells[cap][6]))').replace('return dict(r2r_memory_instances=', 'return dict(trial_longpairs=sorted(longpairs,reverse=True)[:30],r2r_memory_instances=')
exec(s,G.__dict__);r=G.trial_pairs(D);r['status']='ANALYTIC_BOX_CENTRES_NOT_ACTUAL_PLACE';(p/(v+'_center_estimate.json')).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
