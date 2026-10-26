import json,sys
from pathlib import Path
from core_infra_search import design
kind=sys.argv[1];p=Path(kind);data=json.load(open(p/'input.json'));sl=data['slice'];rects=data['macro_rects']
def profile(h,v,obs=(),vobs=()):return dict(horizontal_rc=h,vertical_rc=v,obstacles=obs,vertical_obstacles=vobs,clearance=0.)
trunk=profile([.0180365/2,.1275*1.1],[.0189935/2,.098*1.1],[[r[0]+.072,r[1],r[2]-.072,r[3]] for r in rects]);leaf=profile([.0297127,.1675],[.031287,.1315],rects,rects)
routing=dict(nonleaf=trunk,leaf=leaf,nodes={l['node']:trunk for l in sl['core_tree']['leaves'] if l.get('load_class')=='macro'})
try:
 candidate,report=design(sl,data['libraries'],data['points'],data['caps'],0,0,slew_limit=78,input_slew_ps=0,routing_model=routing)
 report.update(routing_model=routing,qualification='MODEL-ONLY CONDITIONAL: ideal0input; actualpercornernominalcaps; directionallayerRCfromcanonicalsetRC; Cx1.1NDRassumption; unmergedMST; no via/coupling/capacity/routequalification; sourceleafcentroidsnotyetLEFlegalized')
 (p/'candidate.json').write_text(json.dumps(candidate,indent=1));(p/'report.json').write_text(json.dumps(report,indent=1));print(kind,report['result'],flush=True)
except ValueError as e:
 report=dict(verdict='MODEL_INCOMPLETE_FAIL_CLOSED',reason=str(e));(p/'report.json').write_text(json.dumps(report,indent=1));print(kind,report,flush=True)
