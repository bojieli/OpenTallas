# d40h = d38s + Codex HH seam-aware candidate (hh_seams2 vs its base d32q), structural 3-way apply; asserts d38s == d32q on every touched path
import json,sys,shutil,os
BASE,HH,POR,OUT=sys.argv[1:5]
a=json.load(open(BASE+'/die_plan.json')); h=json.load(open(HH+'/die_plan.json')); p=json.load(open(POR+'/die_plan.json'))
def key(x):
    for k in ('id','name'):
        if isinstance(x,dict) and k in x: return x[k]
def keyed(l): return isinstance(l,list) and l and all(isinstance(x,dict) and key(x) is not None for x in l)
log=[]
def merge(pa,ph,pp,path):
    # returns new pp
    if pa==ph: return pp
    if isinstance(pa,dict) and isinstance(ph,dict) and isinstance(pp,dict):
        out=dict(pp)
        for k in set(pa)|set(ph):
            if k in ('note','label') and path in ('','/die'):
                out[k]=('DIE-HBM-41 d41e = d41c + d38a q_b010 re-station (d38r->d38a delta) | '+pp[k]); continue
            va,vh=pa.get(k,'<absent>'),ph.get(k,'<absent>')
            if va==vh: continue
            vp=pp.get(k,'<absent>')
            if va=='<absent>':
                assert vp=='<absent>',(path,k); out[k]=vh; log.append(('ADD',path+'/'+k))
            elif vh=='<absent>':
                assert vp==va,(path,k); del out[k]; log.append(('DEL',path+'/'+k))
            else: out[k]=merge(va,vh,vp,path+'/'+str(k))
        return out
    if keyed(pa) and keyed(ph) and keyed(pp):
        ma={key(x):x for x in pa}; mh={key(x):x for x in ph}; mp={key(x):x for x in pp}
        out=[]
        for x in pp:
            k=key(x)
            if k in mh and k in ma: out.append(merge(ma[k],mh[k],x,path+'['+k+']'))
            elif k in ma and k not in mh: assert x==ma[k]; log.append(('DEL',path+'['+k+']'))
            else: out.append(x)
        for x in ph:
            k=key(x)
            if k not in ma:
                assert k not in mp,(path,k); out.append(x); log.append(('ADD',path+'['+k+']'))
        return out
    assert pp==pa,('CONFLICT',path)
    log.append(('CHG',path)); return ph
new=merge(a,h,p,'')
assert not os.path.exists(OUT); shutil.copytree(POR,OUT,symlinks=False)
json.dump(new,open(OUT+'/die_plan.json','w'),indent=1)
for f in []:
    pass
json.dump({'event':'d41e','base_por':'d41c fa542d5c0871','source':'DIE-HBM-38 d38a vs d38r','ops':log},open(OUT+'/d41e_event_report.json','w'),indent=1)
print(len(log),'ops'); [print(*x) for x in log]
