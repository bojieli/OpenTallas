import re,sys,collections
def fam(s): return re.sub(r'\d+','#',s)
for f in sys.argv[1:]:
    grp=None; C=collections.defaultdict(lambda:[0,0.0,1e9,''])
    for l in open(f):
        m=re.match(r'(max|min)_delay/(setup|hold) group (\S+)',l)
        if m: grp=m.group(2)+':'+m.group(3); continue
        if 'VIOLATED' not in l: continue
        p=l.split()
        try: sl=float(p[-2])
        except: continue
        inst=p[0].split('/')[0]; pin=re.sub(r'\[\d+\]','',p[0].split('/',1)[1]) if '/' in p[0] else ''
        mst=p[1].strip('()')
        k=(grp,fam(inst)+'/'+pin,fam(mst))
        c=C[k]; c[0]+=1; c[1]+=sl
        if sl<c[2]: c[2]=sl; c[3]=p[0]
    print('==',f)
    for k,v in sorted(C.items(),key=lambda kv:kv[1][2])[:25]:
        print('%-22s %-40s %-34s n=%6d wns=%9.1f tns=%12.1f %s'%(k[0],k[1][:40],k[2][:34],v[0],v[2],v[1],v[3]))
