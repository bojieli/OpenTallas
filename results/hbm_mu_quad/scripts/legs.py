import json,sys,re,math,collections
t=json.load(open(sys.argv[1])); R=json.load(open(sys.argv[2]))
H={h['inst']:h for h in t['hard_cores']}
def c(n): h=H[n]; return (h['origin_um'][0]+h['outline_um'][0]/2,h['origin_um'][1]+h['outline_um'][1]/2)
out=dict(vm_service=[],tree=[])
for s in t['internal_stations']:
    a=s.get('launch','').split('.')[0]; b=str(s.get('capture','')).split('.')[0]
    if (a.startswith('u_vmb_') or b.startswith('u_vmb_')) and not ('mu_fused' in a+b):
        L=abs(s['from_um'][0]-s['to_um'][0])+abs(s['from_um'][1]-s['to_um'][1])
        out['vm_service'].append((s['conn'],round(L,1),len(s.get('regs_um',[])),s.get('serial_k',1),max(0,math.ceil(L/405)-1)))
    if str(s.get('conn','')).startswith('mu_tree'):
        L=abs(s['from_um'][0]-s['to_um'][0])+abs(s['from_um'][1]-s['to_um'][1])
        out['tree'].append((s['conn'],round(L,1),len(s.get('regs_um',[])),s.get('serial_k',1)))
vs=out['vm_service']
print('vm_service n',len(vs),'max pin-pin um',max(v[1] for v in vs),'max regs',max(v[2] for v in vs),'max serial_k',max(v[3] for v in vs),'max reg-hops needed(405)',max(v[4] for v in vs))
print('regs hist',sorted(collections.Counter(v[2] for v in vs).items()))
print('reach viol (regs < ceil(L/405)-1):',sum(1 for v in vs if v[2]<v[4]))
for v in sorted(vs,key=lambda v:-v[1])[:5]: print(' ',v)
tr=[x for x in out['tree'] if 'n4' in x[0] or 'root' in x[0]]
for x in tr: print('tree',x)
print('tree max L',max(x[1] for x in out['tree']),'max regs',max(x[2] for x in out['tree']))
print('rebound',R.get('su_service_rebound'),'k',R['k'],'max_axis',R['max_axis'],'failed',R['stats']['failed'],'overlaps',len(R['overlaps']))
json.dump(out,open(sys.argv[3],'w'),indent=0)
