import json,sys,os,statistics
sys.path.insert(0,'tools/hier_contract')
import pinreg_audit as PA
c=json.load(open('/tmp/claude-1000/flowhold/cands.json'))
out={}
for o in c:
    v=o['view']; cell=o['cell']; r={}
    ij=os.path.join(v,'insertion.json'); ins=json.load(open(ij)) if os.path.exists(ij) else None
    for cor in ('tt','ff'):
        p=os.path.join(v,f'{cell}_{cor}.lib')
        if not os.path.exists(p): p+='.gz'
        if not os.path.exists(p): continue
        lib=PA.parse_lib(p); refs=PA.clock_refs(lib,ins,cor)
        m=PA.pin_metrics(lib,refs)
        r[cor]={n:dict(d=x['dir'],cap=x['inp'],hold=x['hold'],lo=x['out'],lmin=x['lmin'],comb=bool(x['comb'])) for n,x in m.items()}
        r[cor+'_R']={k:v_['rise'] for k,v_ in refs.items()}
    out[v]=r
json.dump(out,open('/tmp/claude-1000/flowhold/libscan.json','w'))
