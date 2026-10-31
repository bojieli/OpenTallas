import sys,re,collections
def load(f):
    P=[];hdr=''
    for l in open(f):
        if l.startswith('WS'):hdr=l.strip()
        elif l.startswith('P '):
            _,s,sp,ep=l.split(None,3);P.append((float(s),sp,ep.strip()))
    return hdr,P
def cls(sp,ep):
    if re.search(r'rst_n|por_n',sp) or ep.endswith(('/RESETN','/SETN')):return 'reset'
    if 'did_q' in sp or 'role_onehot' in sp or 'die_capture' in sp: src='role'
    elif re.search(r'g_mu\.rp|g_rp\[',sp): src='rp'
    else: src='other'
    tk = 'tk8' in ep
    return f'{src}->{"tk8" if tk else "other"}'
for f in sys.argv[1:]:
    hdr,P=load(f);print('==',f,hdr,'NVIOL',len(P))
    d=collections.defaultdict(list)
    for s,sp,ep in P:d[cls(sp,ep)].append(s)
    for k in sorted(d):print(f'  {k:16s} n={len(d[k]):6d} worst={min(d[k]):8.1f}')
    tk=[s for s,sp,ep in P if 'tk8' in ep];print(f'  ALL->tk8 n={len(tk)} worst={min(tk) if tk else 0:.1f}')
