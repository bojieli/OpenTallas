import json,re,collections,sys
sys.path.insert(0,'.')
import netidx
r=netidx.load(); I=r['insts']; drv=r['drv']; sinks=r['sinks']; pins=r['pins']
PASS=re.compile(r'^(qkd_rlys(h0?)?_\d+|qkd_landsh0?_\d+|qkd_astk_rly_296_fl|qkd_rst_region)$')
cmap=json.load(open('/home/ubuntu/wt/kv-p3-1023/physical/die_plan/qwen_kvsys/census/census_map_v31.json'))['parts']
def upleaf(inst,port='a',depth=0):
    # walk back from pass cell input to a content leaf
    bits=pins.get((inst,port)) or pins.get((inst,'i'))
    if not bits: return None
    for nb in bits[-1:]:
        d=drv.get(nb)
        if d is None: continue
        if PASS.match(I[d[0]]) and depth<2000: return upleaf(d[0],'a',depth+1)
        return d[0]
    return None
def downleaf(inst,depth=0,seen=None):
    out=set()
    for nb in pins.get((inst,'b'),[])[-1:]:
        for (s,p,idx) in sinks.get(nb,[]):
            if PASS.match(I[s]) and depth<2000: out|=downleaf(s,depth+1)
            else: out.add(s)
    return out
rows=[]
for (inst,p),bits in pins.items():
    if I[inst]!='qkd_hp_or2' or p not in ('a','b'): continue
    d=drv.get(bits[0])
    if d and I[d[0]].startswith('qkd_landsh') and d[1]=='fault':
        L=d[0]; src=upleaf(L); dsts=downleaf(L)
        rows.append(dict(orleaf=inst, port=p, land=L, lm=I[L], src=src, src_part=cmap.get(src), dst=sorted(dsts)[:3],
                         dst_parts=sorted({cmap.get(x) for x in dsts}), or_part=cmap.get(inst)))
print(len(rows))
json.dump(rows,open('landing_faults_rtl6.json','w'),indent=0)
c=collections.Counter((x['src_part'] is not None and x['src_part'].rsplit('_',1)[0], tuple(dp.rsplit('_',1)[0] if dp else None for dp in x['dst_parts']), x['or_part'] and x['or_part'].rsplit('_',1)[0]) for x in rows)
for k,v in c.most_common(30): print(v,k)
print(rows[0]); print(collections.Counter(len(x['dst_parts']) for x in rows))
same=sum(1 for x in rows if x['src_part'] and x['dst_parts'] and x['src_part']==x['dst_parts'][0]); print('src==dst partition (landing internal to a plan partition):',same)
