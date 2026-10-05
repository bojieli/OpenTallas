import re,sys,collections
def parse(fn):
    txt='\n'+open(fn).read()
    out=[]
    for blk in txt.split('\nStartpoint: ')[1:]:
        sp=blk.split()[0]
        ep=re.search(r'Endpoint: (\S+)',blk).group(1)
        grp=re.search(r'Path Group: (\S+)',blk).group(1)
        sl=float(re.search(r'(-?[\d.]+)\s+slack',blk).group(1))
        halves=re.split(r'\n\s+-?[\d.]+\s+-?[\d.]+\s+clock core_clk \(rise edge\)',blk)
        # halves[1]=launch, halves[2]=capture
        def lat(h):
            m=None; icg='u_icg/GCLK' in h
            for line in h.split('\n'):
                if '/CLK' in line or '(in)' in line and 'clk' in line: pass
            ms=re.findall(r'\s(-?[\d.]+)\s+[\^v] (\S+)/(CLK|clk)\b',h)
            # first sequential clock pin occurrence (not clock buffers)
            for t,p,_ in ms:
                return float(t),icg,p
            mo=re.search(r'([\d.]+)\s+[\^v] (\S+) \((in|out)\)',h)
            return (None,icg,None)
        L=lat(halves[1]) if len(halves)>1 else (None,False,None)
        C=lat(halves[2]) if len(halves)>2 else (None,False,None)
        out.append(dict(sp=sp,ep=ep,grp=grp,slack=sl,llat=L[0],licg=L[1],clat=C[0],cicg=C[1]))
    return out
def group(p):
    s,e=p['sp'],p['ep']
    if e.startswith('p') and '.' not in e: return 'output port (pval/prow/...) I/O budget'
    if 'rst_q' in s: return 'reset rst_q -> async (recovery/removal)'
    if 'u_icg' in e or 'g_cg' in e: return 'ICG enable'
    if 'r_i2_bk' in s or 'r_i2x_bk' in s: return 'capture select r_i2_bk -> lane P0 (cap mux fan-out)'
    if re.search(r'g_ch2|u_c[0-9]\.u_add|fwd[56]',e) and re.search(r'fwd|g_ch2',s): return 'chain fwd5/fwd6 -> fadd'
    if 'fw_' in e or re.search(r'n_c|g_qt_hit',s): return 'n_c / match -> fw_q* fan-out'
    if re.search(r'walk|nA|nB|wA|wB|w_h|w_lu',s+e): return 'walker'
    if 'xs_' in s or s.startswith('xs') or 'r_xs' in e: return 'x boundary / r_xs'
    return 'other'
def summarize(fn,top=200):
    ps=[p for p in parse(fn)][:top]
    viol=[p for p in ps if p['slack']<0]
    c=collections.defaultdict(list)
    for p in viol: c[group(p)].append(p)
    print(f'== {fn}: {len(ps)} paths parsed, {len(viol)} violating')
    for k,v in sorted(c.items(),key=lambda kv:min(x['slack'] for x in kv[1])):
        ws=min(x['slack'] for x in v)
        sk=[(x['clat'] or 0)-(x['llat'] or 0) for x in v if x['clat'] is not None and x['llat'] is not None]
        print(f'  {k:55s} n={len(v):4d} wns={ws:8.1f} mean(capture-launch latency)={sum(sk)/len(sk) if sk else float("nan"):7.1f} launch_icg={sum(x["licg"] for x in v)} capture_icg={sum(x["cicg"] for x in v)}')
        sps=collections.Counter(re.sub(r'\[\d+\]','[*]',x['sp']) for x in v).most_common(4)
        for s,n in sps: print(f'      start {n:4d} {s}')
    return ps
if __name__=='__main__':
    for fn in sys.argv[1:]: summarize(fn)
