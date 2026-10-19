"""Scalar native Verilog census, with assignment aliases and vector macro ports."""
import collections, gzip, hashlib, json, math, re, sys
from pathlib import Path
def census(path,narrow=False):
    s=gzip.open(path,'rt').read() if str(path).endswith('.gz') else Path(path).read_text()
    widths={};ports={};par={}
    for kind,a,b,n in re.findall(r'^\s*(input|output|wire)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(\\\S+|\w+)\s*;',s,re.M):
        if a:widths[n]=(int(a),int(b))
        if kind!='wire':ports[n]=kind
    def bits(x):
        x=x.strip()
        if x.startswith('{'):
            assert x.endswith('}');return [b for y in x[1:-1].split(',') for b in bits(y)]
        if x in widths:
            a,b=widths[x];return [x+'['+str(i)+']' for i in range(a,b-1,-1)]
        m=re.fullmatch(r'(\\\S+|\w+)\s*\[(\d+):(\d+)\]',x)
        if m:
            n,a,b=m.groups();return [n+'['+str(i)+']' for i in range(int(a),int(b)-1,-1)]
        if re.fullmatch(r"\d+'[bh][0-9a-fxz]+",x,re.I):
            a,v=x.split("'");base,v=v[0],v[1:]
            if base.lower()=='h':v=''.join(bin(int(q,16))[2:].zfill(4) for q in v)
            return ['CONST_'+q for q in v.zfill(int(a))]
        return [x]
    def root(x):
        if x not in par:par[x]=x
        while par[x]!=x:par[x]=par[par[x]];x=par[x]
        return x
    for l,r in re.findall(r'^\s*assign\s+(.*?)\s*=\s*(.*?)\s*;',s,re.M):
        aa,bb=bits(l),bits(r)
        assert len(aa)==len(bb),(l,r)
        for a,b in zip(aa,bb):par[root(a)]=root(b)
    cells={};drivers={};loads=collections.defaultdict(list);transparent={}
    for m in re.finditer(r'^\s*([A-Za-z0-9_]+)\s+(\\[^\n]+?|\w+)\s*\(\s*\n(.*?)\n\s*\);',s,re.M|re.S):
        t,n,b=m.groups();p={k:[root(v) for v in bits(x)] for k,x in re.findall(r'\.(\w+)\(([^()]*)\)',b)};cells[n]=(t,p)
        if narrow and t=='ot_sram_1r1w_64x512_m1_r2c2':
            for port in ['rd_out','wd_in','w_mask_in']:
                assert len(p[port])==512;p[port]=p[port][-137:]
            assert len(p['cr_sel'])==18;p['cr_sel']=p['cr_sel'][-16:]
            t='ot_sram_1r1w_64x137_m1_r2c2_p192';cells[n]=(t,p)
        for pn,vs in p.items():
            out=pn in ['QN','Q','Y','Z','CON','SN','H','L','rd_out']
            for j,v in enumerate(vs):
                if out:drivers[v]=(n,t,pn,j)
                else:loads[v].append((n,pn,j))
        if t.startswith(('BUF','INV')):
            assert len(p['A'])==1
            op=next(p[k][0] for k in ['Y','Z','QN'] if k in p);transparent[n]=op
    for n,d in ports.items():
        for j,v in enumerate(bits(n)):
            v=root(v)
            if d=='input':drivers[v]=('PORT',n,'',j)
            else:loads[v].append(('OUTPUT',n,j))
    cache={}
    def ends(v,seen=None):
        if v in cache:return cache[v]
        seen=set() if seen is None else seen
        assert v not in seen,('transparent cycle',v)
        out=[]
        for n,p,j in loads[v]:
            if n in transparent:out.extend(ends(transparent[n],seen|{v}))
            else:out.append((n,p,j))
        cache[v]=out;return out
    rows=[]
    for v in set(drivers)|set(loads):
        d=drivers.get(v);es=ends(v)
        if v.startswith('CONST_'):role='constant'
        elif not d:role='UNDRIVEN'
        elif d[0]=='PORT':role='clock' if d[1]=='ck' else 'input'
        elif d[1].startswith(('BUF','INV')):role='BUF_INV'
        elif d[1].startswith('DFF'):role='FF'
        elif d[1].startswith('ot_sram'):role='macro'
        elif d[1].startswith('TIE'):role='tie'
        else:role='comb'
        rows.append(dict(net=v,driver=d,role=role,direct=len(loads[v]),terminal=len(es),
                         min_extra_copies=max(0,math.ceil(len(es)/32)-1)))
    rows.sort(key=lambda x:(x['role'],x['net']))
    violations=[x for x in rows if x['role']!='clock' and x['terminal']>32]
    counts=collections.Counter(t for t,p in cells.values())
    # Same-master-D/reset copies, then charge every extra predecessor input.
    # No transparent buffer is counted as a functional replication boundary.
    factors={n:1 for n in cells if n not in transparent};history=[]
    active=[x for x in rows if x['role'] in ['FF','comb','tie']]
    for iteration in range(1000):
        nxt=dict(factors)
        for x in active:
            demand=sum(factors.get(n,1) for n,p,j in ends(x['net']))
            n=x['driver'][0];nxt[n]=max(nxt[n],math.ceil(demand/32))
        extra=collections.Counter()
        for n,k in nxt.items():extra[cells[n][0]]+=k-1
        history.append(dict(iteration=iteration,extra_cells=sum(extra.values())))
        if nxt==factors:break
        factors=nxt
    else:raise AssertionError('No finite fixedpoint in 1000 monotone passes')
    remaining=[]
    for x in rows:
        if x['role'] not in ['input','macro']:continue
        demand=sum(factors.get(n,1) for n,p,j in ends(x['net']))
        if demand>32:remaining.append(dict(net=x['net'],role=x['role'],demand=demand))
    fp=dict(iterations=len(history),history=history,extra_by_master=dict(extra),extra_cells=sum(extra.values()),
            unresolved_input_or_macro=remaining,
            copied_cells=[dict(cell=n,master=cells[n][0],extra=k-1) for n,k in factors.items() if k>1],
            status='Analytical duplication fixedpoint only; no RTL emission, optimization survival, functional, boundary, physical or timing qualification')
    return dict(sha256=hashlib.sha256(s.encode()).hexdigest(),analytical_macro_port_narrowing=narrow,cells=len(cells),types=dict(counts),rows=rows,
                violations=violations,roles=dict(collections.Counter(x['role'] for x in rows)),
                violations_by_role=dict(collections.Counter(x['role'] for x in violations)),
                independent_root_copy_lowerbounds={r:sum(x['min_extra_copies'] for x in violations if x['role']==r) for r in ['FF','comb','input','macro','constant','tie']},
                copy_fixedpoint=fp)
if __name__=='__main__':
    j=census(sys.argv[1],narrow=('--narrow' in sys.argv));Path(sys.argv[2]).write_text(json.dumps(j,indent=2)+'\n')
    print(json.dumps({k:v for k,v in j.items() if k not in ['rows','types','violations']},indent=2))
