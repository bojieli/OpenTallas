import json,re,collections,sys
sys.path.insert(0,'.')
import netidx
r=netidx.load(); I=r['insts']; drv=r['drv']; sinks=r['sinks']; pins=r['pins']
cmap=json.load(open('/home/ubuntu/wt/kv-p3-1023/physical/die_plan/qwen_kvsys/census/census_map_v31.json'))['parts']
PASS=re.compile(r'^(qkd_rlys(h0?)?_\d+|qkd_landsh0?_\d+|qkd_astk_rly_296_fl|qkd_rlyi_258s|qkd_rst_region)$')
out={}
for p in ['pll_hbm_WS','pll_hbm_WN','pll_hbm_ES','pll_hbm_EN','pll_phy','pll_host','pll_ingest','pll_fwd','pll_c','pll_WS']:
    bits=pins[('pll',p)]
    cons=collections.Counter(); passn=0
    for nb in bits:
        for (s,pp,idx) in sinks.get(nb,[]):
            if PASS.match(I[s]): passn+=1; continue
            cons[(cmap.get(s,'?'+s), I[s], pp)]+=1
    parts=collections.Counter(); 
    for (pt,m,pp),n in cons.items(): parts[pt]+=n
    out[p]=dict(width=len(bits), pass_sinks=passn, parts=dict(parts), ports=sorted({f'{m}.{pp}' for (pt,m,pp) in cons}))
    print(p, len(bits), 'pass',passn, 'parts',len(parts), sorted(parts)[:12], out[p]['ports'][:8])
json.dump(out,open('noncore_clocks_rtl6.json','w'),indent=1)
# reset root
rb=pins[('host','die_rst_n')]
cons=collections.Counter()
for nb in rb:
    for (s,pp,idx) in sinks.get(nb,[]): cons[I[s]]+=1
print('die_rst_n sinks', cons.most_common(8))
# host inputs: what drives host reset itself
for p in [k for k in pins if k[0]=='host' and 'rst' in k[1]]: print(p, [drv.get(b) for b in pins[p][:1]])
for p in [k for k in pins if k[0]=='pll']: print(p, len(pins[p]), [drv.get(b) for b in pins[p][:1]] if p[1] in ('ref','rst_n','ref_clk') else '')
