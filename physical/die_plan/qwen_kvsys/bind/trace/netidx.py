"""bit-level index of die.v: insts, per-pin bits, drivers, sinks (pickled)"""
import json,re,collections,sys,pickle,os
sys.path.insert(0,'/home/ubuntu/wt/kv-p3-1023/physical/die_plan/qwen_kvsys')
import extract_asbuilt as X
D='/home/ubuntu/scratch/kv-p2-1023/case_kv/'
PK='/home/ubuntu/scratch/kv-p3-1023/netidx.pkl'
def load():
    if os.path.exists(PK): return pickle.load(open(PK,'rb'))
    masters=json.load(open(D+'gen_source_ports.json'))['masters']
    wires={}; insts={}; pins={}; drv={}; sinks=collections.defaultdict(list)
    lines=open(D+'die.v').read().splitlines()
    for ln in lines:
        m=X.WIRE_RE.match(ln)
        if m: wires[m.group(4)]=(int(m.group(2)),int(m.group(3))) if m.group(1) else (0,0)
    for ln in lines:
        m=X.INST_RE.match(ln)
        if not m or m.group(1) in ('assign','wire','module'): continue
        mst,name,body=m.groups(); pdef=masters[mst]['ports']; insts[name]=mst
        for p,e in X.split_ports(body):
            bits=X.expr_bits(e,wires); w=len(pdef[p]); pins[(name,p)]=bits
            for k,nb in enumerate(bits):
                idx=w-1-k
                if nb is None: continue
                if pdef[p][idx]=='OUTPUT': drv[nb]=(name,p,idx)
                else: sinks[nb].append((name,p,idx))
    r=dict(insts=insts,pins=pins,drv=drv,sinks=dict(sinks))
    pickle.dump(r,open(PK,'wb')); return r
if __name__=='__main__':
    r=load(); print(len(r['insts']),len(r['drv']))
