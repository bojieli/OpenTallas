import sys,json,collections
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/path-hbm-r9-1026/tools/die_plan')
import hbm_r9_delta as D, plan_cut as PC
P=json.load(open('/srv/opentallas-scratch2/claude/path-hbm-r8-1026/t_banks/die_plan.json'))
tn=sys.argv[1]; S=int(sys.argv[2]); Hn=float(sys.argv[3]); kx=int(sys.argv[4])
t=P['partition_types'][tn]; W,H=t['outline_um']
# baseline
b=D.cut(t); print('BASE',tn,'blocked x',b['blocked']['x'],'\n  y',b['blocked']['y'])
nsf=sum(s['bits'] for s in t['internal_stations'] if str(s.get('launch','')).startswith('face') or min(s['from_um'][1],s['to_um'][1])<=0.5 or max(s['from_um'][1],s['to_um'][1])>=H-0.5)
print('face-touching station bits', nsf, 'y supply unblocked', round(W*0.75*(1/0.048+1/0.064)))
Q=D.plan_quadrants(t,S)
cores,st,infos,stats=D.realise(t,Q,Hn,kx=kx,route=False)
u=D.cut(dict(outline_um=[W,Hn],hard_cores=cores,internal_stations=st))
print('R9',S,Hn,kx,'blocked x',u['blocked']['x'],'\n  y',u['blocked']['y'])
print('fill per seg',[ (k,v['fill'],v['shelves']) for k,v in infos.items()])
