import sys,statistics as S
base='/srv/opentallas-scratch2/claude/s81-cores-split/probe/'
def rd(f):
    d={}
    for l in open(f):
        p=l.rstrip('\n').split('\t'); d[p[0]]=(float(p[1]),float(p[2]),float(p[3]),p[4])
    return d
def q(v,ps=(0,1,5,50,95,99,100)):
    v=sorted(v); return ' '.join('p%d=%.1f'%(p,v[min(len(v)-1,int(p/100*len(v)))]) for p in ps)
for core in ['vn_a','vn_b','ve_m','ve_s']:
    c=rd(base+core+'/ck_cts_tt.tsv'); g=rd(base+core+'/ck_grt_tt.tsv'); r=rd(base+core+'/ck_rcx_tt.tsv')
    print('==',core,len(r))
    for nm,d in (('cts',c),('grt',g),('rcx',r)):
        v=[x[2] for k,x in d.items() if not x[3].startswith('ot_sram')]
        print(' ',nm,q(v))
    mac=[(k,x) for k,x in r.items() if x[3].startswith('ot_sram')]
    for k,x in mac: print('  macro',k,x[:2],'cts %.1f grt %.1f rcx %.1f'%(c[k][2],g[k][2],x[2]))
    dg=[g[k][2]-r[k][2] for k in r if k in g]; dc=[c[k][2]-r[k][2] for k in r if k in c]
    print('  grt-rcx',q(dg)); print('  cts-rcx',q(dc))
    # spatial: insertion by x band
    xs=[x[0] for x in r.values()]; ys=[x[1] for x in r.values()]
    X=max(xs);Y=max(ys)
    for nb in range(4):
        row=[]
        for mb in range(6):
            v=[x[2] for x in r.values() if int(x[0]/X*5.999)==mb and int(x[1]/Y*3.999)==3-nb]
            row.append('%5.0f/%-5d'%(S.mean(v),len(v)) if v else '   -       ')
        print('   ',' '.join(row))
