import json,sys,gzip
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan')
import core_infra as CI,core_infra_plan as CP,die_clock_128 as D
p=Path(__file__).parent
for f in (p/'lib').glob('*.lib'):
 with gzip.open(str(f)+'.gz','wb') as g:g.write(f.read_bytes())
s=json.loads((p/'master_slice.json').read_text())
pts={}
for line in (p/'xcal_sinks.txt').read_text().splitlines():
 if line.startswith('#'):continue
 a=line.split();pts[a[0]]=[float(a[2]),float(a[3])]
roots=[(16,170),(16,60),(225,165),(225,60),(125,137),(123,100)]
groups=[[] for _ in roots]
for pin,xy in pts.items():
 i=min(range(6),key=lambda i:abs(roots[i][0]-xy[0])+abs(roots[i][1]-xy[1]))
 groups[i].append(pin)
master='BUFx24_ASAP7_75t_R'
nodes=[dict(name='mp_xcal_root',master=master,xy_um=[125.28,125.28],parent='port:clk')]
leaves=[]
for i,(xy,pins) in enumerate(zip(roots,groups)):
 name=f'mp_xcal_region{i}'
 nodes.append(dict(name=name,master=master,xy_um=list(xy),parent='mp_xcal_root'))
 leaves.append(dict(node=name,sinks=sorted(pins),cts_open=True,domain_sinks=len(pins),cts_fanout=24,cts_stages=3,load_class='register'))
s['core_tree']=dict(clock_port='clk',nodes=nodes,leaves=leaves,stage_basis='total',equal_load=False,load_balance='joint_nldm_plan',trunk_layers=['M4','M5'],install_stage='pre_cts')
libs={c:D.lib_cells(c,p/'lib',names=[master]) for c in ['TT','FF']}
r=CP.predict_tree(s,libs,pts,{},.0185,.1714)
(p/'six_root_slice.json').write_text(json.dumps(s,indent=2)+'\n')
(p/'six_root_estimate.json').write_text(json.dumps(r,indent=2)+'\n')
for c,v in r['corners'].items():print(c,{k:v[k] for k in ['prediction','sinks','min_ps','mean_ps','max_ps','window_ps','out_of_calibration_leaves']})
print('groups',list(map(len,groups)))
