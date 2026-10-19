import json,math,collections
x=json.load(open('graph_lifetime.json')); roots=x['roots']; byinst=collections.defaultdict(list)
for i,r in enumerate(roots):
 if r['kind']!='INPUT':byinst[r['driver'].rsplit('/',1)[0]].append(i)
c=[1]*len(roots);history=[]
for iteration in range(100):
 demands=[];nc=[]
 for i,r in enumerate(roots):
  demand=sum(max([c[j] for j in byinst.get(inst,[])]or[1]) for inst,pin in r['endpoints'])
  demands.append(demand);nc.append(max(c[i],math.ceil(demand/32)))
 history.append(dict(iteration=iteration,extra=sum(n-1 for n in nc),maximum=max(nc),changed=sum(a!=b for a,b in zip(c,nc))))
 if nc==c:break
 c=nc
else:raise RuntimeError('no convergence')
summary=collections.defaultdict(lambda:dict(extra=0,roots_copied=0))
rows=[]
for i,(r,n,demand) in enumerate(zip(roots,c,demands)):
 if n>1:
  summary[r['kind']]['extra']+=n-1;summary[r['kind']]['roots_copied']+=1
  rows.append(dict(driver=r['driver'],kind=r['kind'],master=r.get('master'),original_fanout=r['fanout'],expanded_pin_demand=demand,total_copies=n))
y=dict(schema='kv_ctl_native_copy_demand_fixedpoint.v1',odb_sha256=x['odb_sha256'],method='Each copied native instance reproduces every nonclock input pin. Transparent endpoints already collapsed. All outputs of an instance use maximum copy multiplicity. Monotonic synchronous iteration to <=32 sinks per root copy.',qualification='Native graph capacity model only; duplicated combinational logic may merge. Source functional state realization, reset equivalence, clock loads and physical costs are NOT proven.',converged=True,iterations=history,summary=dict(summary),copies=rows)
json.dump(y,open('fixedpoint.json','w'),indent=2);print(json.dumps(dict(summary=dict(summary),history=history)))
