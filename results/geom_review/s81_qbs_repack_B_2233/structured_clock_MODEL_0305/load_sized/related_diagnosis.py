from pathlib import Path
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
sys.path.insert(0,'/home/ubuntu/coord/tmp/codex-hist-anchor-2100');from exact_cones import endpoints
R=Path(__file__).parent;P=Path('/srv/opentallas-scratch/claude/codex-hist-postplace-0246');D=G.Design(P/'actual_geom.tsv');model=json.load(open(R/'model.json'));groups=json.load(open('/srv/opentallas-scratch/claude/codex-hist-clock-model-0305/FF_region_assignments.json'));pins=[p for p in json.load(open(P/'actual_clock_pins.json'))if p['macro']];norm=lambda s:s.replace('\\','');reg={norm(s.rsplit('/',1)[0]):g['node']for g in groups for s in g['sinks']};mreg={norm(p['inst']):'macro_leaf'+str(i)for i,p in enumerate(pins)};phase={c:{g['node']:g for g in q['leaves']}for c,q in model['corners'].items()};answer={c:dict(relationships=0,nominal_gt80=0,interval_upper_gt80=0,nominal_max_ps=0,interval_upper_max_ps=0)for c in phase}
def add(a,b,label):
 for c,leaf in phase.items():
  x,y=leaf[a],leaf[b];d=abs(x['mean_ps']-y['mean_ps']);u=max(abs(x['min_ps']-y['max_ps']),abs(x['max_ps']-y['min_ps']));o=answer[c];o['relationships']+=1
  if len(label)==2:
   o['FF_only_relationships']=o.get('FF_only_relationships',0)+1
   if d>o.get('FF_only_nominal_max_ps',0):o['FF_only_nominal_max_ps']=d;o['FF_only_witness']=dict(label=label,launch_group=a,capture_group=b)
  o['nominal_gt80']+=d>80;o['interval_upper_gt80']+=u>80
  if d>o['nominal_max_ps']:o['nominal_max_ps']=d;o['nominal_witness']=dict(label=label,launch_group=a,capture_group=b)
  if u>o['interval_upper_max_ps']:o['interval_upper_max_ps']=u;o['interval_witness']=dict(label=label,launch_group=a,capture_group=b)
for cid,cell in D.cells.items():
 if cell[0]!='S':continue
 name=norm(cell[6]);a=reg[name];ss,ms=endpoints(D,cid,True)
 for cap in ss:add(a,reg[norm(D.cells[cap][6])],[name,norm(D.cells[cap][6])])
 for k in ms:add(a,mreg[norm(D.cells[k[0]][6])],[name,norm(D.cells[k[0]][6]),'macro_input'])
 ss,ms=endpoints(D,cid,False)
 for k in ms:add(mreg[norm(D.cells[k[0]][6])],a,[norm(D.cells[k[0]][6]),name,'macro_output'])
out=dict(scope='SOURCE CLOCK MODEL same-native-graph FF/macro-frontier relations; deterministic common feed cancels in differences; no additional CPPR credit or actual paired timing gate/STA. Macro endpoints are CLK PIN model, no internal insertion transfer.',corners=answer);(R/'related_diagnosis.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
