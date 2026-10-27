import sys,json,pathlib
R=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-s81-pd2-2000');sys.path.insert(0,str(R/'tools/die_plan'))
import schema as S, die_trial as D, check as C
f='/srv/opentallas-scratch2/claude/path-s81-pd-1026/plandir/die_plan_pd_thin.json';P=S.Plan(S.load(f),f)
missing={r[0] for r in json.load(open('/srv/opentallas-scratch2/claude/codex-s81-pd2-2000/lef_materialization.json')) if r[1]=='materialized'}
orig=D.lef_top_layer; out=[]
for name in ['with_LEFs','sparse_missing39']:
 D.lef_top_layer=orig if name=='with_LEFs' else lambda f:None
 cores={L:D.die_core_rects(P,L) for L in ['M5','M7']}; bands=D.ft_band_rects(P)
 for c in [18750,19000,20250]:
  for pn in P.parts:
   r=P.rect(pn);lo,hi,a0,a1=r[0],r[2],r[1],r[3]
   if not a0+C.EPS<c<a1-C.EPS or pn!='s_0N_L1':continue
   t=P.ptype(pn);cap=0;ls={}
   for L in C.PART_FT_LAYERS['V']:
    obs=[(cr[0],cr[2]) for cr in D.die_core_rects(P,L) if cr[1]+C.EPS<c<cr[3]-C.EPS]
    reserved=[(br[1],br[3],br[5]) for br in bands if br[0]==L and br[2]+C.EPS<c<br[4]-C.EPS]
    v=C.cut_interval_tracks(lo,hi,P.layers[L]['pitch_um'],t.get('ft_track_frac',C.FT_TRACK_FRAC),obs,reserved);cap+=v;ls[L]=v
   out.append(dict(vehicle=name,part=pn,cut_um=c,tracks=cap,by_layer=ls))
json.dump(out,open('/srv/opentallas-scratch2/claude/codex-s81-pd2-2000/cut_anomaly.json','w'),indent=1);print(json.dumps(out))
