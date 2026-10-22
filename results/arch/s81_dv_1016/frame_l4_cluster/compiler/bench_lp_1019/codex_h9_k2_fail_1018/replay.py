import json,sys
sys.path.insert(0,'tools/s81_dv')
import frame_return_plan as P, frame_bench as B
old=json.load(open('/tmp/tw3f/vec_plan/meta.json'))['plan']
pairs=sorted(int(k[1:]) for k in old['emission']['edges'])
oassign={p:[(R,s,4)] for (sl,R,s),p in zip(old['assign_slots'],pairs)}
P.legalise=lambda topo,pairs_,nsr,nseg,emit_edge,vals,seed,iters:(oassign,0,0)
m=json.load(open('/tmp/tw3f/vec_plan/meta.json'))
# rebuild via gen internals: call plan_phase with same inputs
import numpy as np
B.main(['gen','--master','col_h9','--out','/tmp/tw3f/replay_out','--seed','1','--plan','--nseg','4','--K','2048','--land-e','2','--frame-schedule','results/arch/s81_dv_1016/frame_l4_cluster/compiler/col_h9_schedule.json','--cycles','3000'])
p=json.load(open('/tmp/tw3f/replay_out/meta.json'))['plan']
print('faults',p['faults'],{n:r['faults'] for n,r in p['nodes'].items() if r['faults']})
print('pred',[(e,B._f(B.norm(t))) for e,t,d,er in p['ret']])
