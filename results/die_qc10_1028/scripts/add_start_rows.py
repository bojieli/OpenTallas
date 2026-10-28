"""DIE-QC-10: append START-TREE-1 fork start rows (one per forwarding edge of FEED: launch + sync flop on the two legs of
the fork node, d = 0 +- LEG, OCV by main clk_aocv, no core latency) to a ca_spice xing JSON, and write the fixed start tree
(--tree-parent list, BFS order).  ESTIMATE form of the start port until START-TREE-1 lands its planner opt-in.
usage: add_start_rows.py XING_IN FEED XING_OUT TP_OUT"""
import json, sys, collections
sys.path.insert(0,'/srv/opentallas-scratch2/claude/die-qc10-1028/est')
from ocvmodel import ocv
xi,feedp,xo,tpo=sys.argv[1:5]; LEG=40.0; CAL=40.0
X=json.load(open(xi)); F=json.load(open(feedp)); par=F['parent']
for cn,c in X['corners'].items():
    C='TT' if cn.startswith('TT') else 'FF'
    s0,h0=ocv(0,0,0,C); s1,h1=ocv(LEG,LEG,0,C)
    for ch,p in par.items():
        if p is None: continue
        c['all'].append(dict(port='start__'+ch,src=p,dst=ch,src_part='fork:'+p,dst_part='fork:'+ch,d_ps=0.0,unshared_a_ps=LEG,unshared_b_ps=LEG,
                             p_up_ps=h1-h0+CAL/2,p_dn_ps=s1-s0+CAL/2,margin_ps=0.0,kind_est='start'))
json.dump(X,open(xo,'w'))
kid=collections.defaultdict(list)
for ch,p in par.items():
    if p: kid[p].append(ch)
order=[]; q=[F['root']]
for x in q:
    for ch in sorted(kid[x]): order.append(f'--tree-parent {ch}=start__{ch}'); q.append(ch)
open(tpo,'w').write(' '.join(order)); print('start rows',len(order))
