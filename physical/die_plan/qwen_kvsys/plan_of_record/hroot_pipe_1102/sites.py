import json,itertools
H='/home/ubuntu/.claude/jobs/b7f906df/tmp/hroot/'
taps=[(l.split()[1],float(l.split()[2]),float(l.split()[3])) for l in open(H+'taps.txt')]
# valid-bit (ring dsel y[W]) launch points in the geom2 placement; the kvpc_next ring moves to the new FF band
ring={'fch_pc':(873.6,27.7),'kvpc_fo':(884.4,27.7),'slg':(1020,44),'kvpc_next':(1369.4,103.7),
 'host_die':(1803,308),'host_hbm':(1800,318),'idsrc':(1817.4,438.9),'kvs_ctl':(1878.2,514.8),'fan_kc':(1851.1,807.7)}
bus={'fch_pc':'i_fch_pc_Q_N_q','kvpc_fo':'i_kvpc_Q_N_pc__fo','slg':'i_slg_Q_N_o_ctl','kvpc_next':'i_kvpc_Q_N_o_next',
 'host_die':'i_host_die_rst_n','host_hbm':'i_host_hbm_rst_n','idsrc':'i_idsrc_Q_y','kvs_ctl':'i_kvs_ctl_o_hroot_Q','fan_kc':'i_seq__g_fan_N__u_fan_kc'}
fch_data=(871,28); bout=(1894.6,232.9)
d=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
lerp=lambda a,b,f:(round(a[0]+(b[0]-a[0])*f,2),round(a[1]+(b[1]-a[1])*f,2))
def neartap(p): return min(taps,key=lambda t:d(p,(t[1],t[2])))
best=None
for ex in range(1000,1850,10):
  for ey in range(150,700,10):
    E=(ex,ey)
    F=lerp(E,bout,0.5)
    m=max([d(ring[l],E)/3 for l in ring]+[d(E,bout)/2, d(fch_data,F)/3, d(neartap(E)[1:],E)])
    if best is None or m<best[0]: best=(m,E)
m,E=best; F=lerp(E,bout,0.5)
print('max hop',round(m,1),'E',E,'F',F)
S={}; hops=[]
for l in ring:
  b=lerp(ring[l],E,1/3); p=lerp(ring[l],E,2/3)
  S[f'u_bin_{bus[l]}/eq']=b; S[f'u_eqp_{l}.q']=p
  t=neartap(b); hops+=[(f'ring {l}->bin',d(ring[l],b)),(f'bin->eqp {l}',d(b,p)),(f'eqp->E {l}',d(p,E)),(f'tap {t[0]}->bin {l}',d(b,t[1:]))]
Bq=lerp(fch_data,F,1/3); Pp=lerp(fch_data,F,2/3)
S['u_bin_i_fch_pc_Q_N_q/q']=Bq; S['u_fchp.q']=Pp; S['u_u_fch.q']=F
for k in ['fault']+[f'cnt[{i}]' for i in range(6)]: S[f'u_u_efault.{k}']=E
te=neartap(E)
hops+=[('E->F',d(E,F)),('F->bout',d(F,bout)),('data->Bq',d(fch_data,Bq)),('Bq->P',d(Bq,Pp)),('P->F',d(Pp,F)),(f'tap {te[0]}->E',d(te[1:],E))]
for h in hops: print(f'{h[0]:34s} {h[1]:7.1f}')
rst={f'u_bin_{bus[l]}':neartap(S[f'u_bin_{bus[l]}/eq'])[0] for l in ring}; rst['u_efault']=te[0]
json.dump(dict(sites=S,reset=rst,E=E,F=F),open(H+'sites.json','w'),indent=1)
print(json.dumps(rst))
