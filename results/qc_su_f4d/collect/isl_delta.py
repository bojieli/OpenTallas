import sys,re,statistics as st,collections
def load(fn):
    d=collections.defaultdict(list)
    for l in open(fn):
        if l.startswith('#'): continue
        f=l.split('\t')
        m=re.fullmatch(r'ot_ms_(Q\d)B\d+L\d+_clk',f[1])
        if m: d[m.group(1)].append(float(f[2]))
    return {k:st.mean(v) for k,v in d.items()}
for c in ('TT','FF'):
    g=load(f'grt_{c}.tsv'); r=load(f'rcx_{c}_prehold.tsv')
    print(c,' '.join(f'{k}:{g[k]:.1f}->{r[k]:.1f}({r[k]-g[k]:+.1f})' for k in sorted(g)))
