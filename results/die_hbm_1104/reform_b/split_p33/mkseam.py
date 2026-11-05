import json,sys
A='/srv/opentallas-scratch2/claude/hbm-reform-b5'
N=json.load(open(A+'/p33nl.json'))['modules']['ot_hfd_coll_q2n2_body_core']['cells']
def bits(cn):
  c=[v for k,v in N.items() if k.endswith(cn)][0]; o={}
  for p,b in c['connections'].items():
    for i,x in enumerate(b): o[x]=(f'{p}[{i}]' if len(b)>1 else p)
  return o
q,r=bits('u_q'),bits('u_r')
s={q[n]:r[n] for n in q if n in r and n not in('0','1') and q[n] not in('clk','rst_n')}
json.dump(s,open(sys.argv[1],'w'),indent=0); print(len(s))
