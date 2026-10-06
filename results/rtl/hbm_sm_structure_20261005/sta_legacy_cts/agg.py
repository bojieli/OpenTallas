import re,sys,collections
def coarse(n):
    n=re.sub(r'\$_.*','',n)
    for pat,lab in [(r'^(rv|fault|rdata|rrow|req_\w+|d_ready|released|busy|arrive)(\[\])?$','OUTPORT'),
                    (r'^[a-z_]+(\[\])?$','INPORT')]:
        if re.match(pat,n): return lab
    m=re.match(r'g_new\.(\w+)',n)
    top=m.group(1) if m else n
    if top=='g_l2s':
        if 'u_leaf/' in n:
            r=n.split('u_leaf/')[1]
            for k,l in [('u_tc/','LEAF.TCmacro'),('u_bd/','LEAF.BDmacro'),('u_x/','LEAF.xSRAM')]:
                if k in r: return l
            return 'LEAF.'+re.sub(r'\[\].*','',r.split('/')[0])
        if 'u_gd' in n or 'u_gv' in n: return 'DG'
        return 'L2.'+n.split('.')[-1].split('/')[0]
    if top=='g_sub': return 'DS/DW.'+n.split('.')[2]
    if top=='g_col':
        return 'COL.'+n.split('.')[1].split('/')[0] if '.' in n else 'COL'
    return top
for c in ('ss','ff'):
    agg=collections.defaultdict(lambda:[0,0.0,0.0])
    for l in open(f'full_{c}.log'):
        if not l.startswith('OT_CLASS\t'): continue
        _,s,k,cl=l.rstrip('\n').split('\t',3)
        a,b=cl.split(' -> ')
        key=(coarse(a),coarse(b))
        v=agg[key]; v[0]+=int(k); v[1]=min(v[1],float(s))
    print('==',c)
    for key,v in sorted(agg.items(),key=lambda kv:kv[1][1]):
        print(f'{v[1]:9.1f} {v[0]:7d}  {key[0]} -> {key[1]}')
