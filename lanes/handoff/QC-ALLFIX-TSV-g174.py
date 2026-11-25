"""g174.py: classify each non-intended guard finding of lin/mn.json (C1m 851b964db1f5 -> C1n ac1e32805d2c) by row json.
INTENDED-BY-ROW R: row R's json holds the exact path with the exact C1n value (C1n absent: R's json has the parent
container present without that leaf, and the type is one R's compose step applied). SUPERSEDED: additionally an older
row's json holds the C1m value at that path and the newer row is declared to supersede it. Else SILENT -> restore C1m."""
import json,re,hashlib
D='/srv/opentallas-scratch2/claude/QC-ALLFIX-TSV/'
sh=lambda f: hashlib.sha256(open(D+f,'rb').read()).hexdigest()[:12]
L=lambda f: json.load(open(D+f))
rep=L('side/c1n_report.json')
ROWS=[('TAPBINS2','rows/plan_tapbins2_c1m.json',set(rep['TAPBINS2']['types'])),
      ('RC97BT2','rows/plan_rc97bt2.json',set(rep['RC97BT2']['types'])),
      ('PGHALO','rows/plan_pgedge.json',set(rep['PGHALO'].get('types') or [])),
      ('SLECTL','rows/plan_slectl.json',set(rep['SLECTL']['types'])),
      ('RTXALL-r4','rows/plan_rtxall_out4.json',set(rep['RTXALL'].get('types') or [])),
      ('FIX-RELAYCOPY','rows/plan_c1m_rc.json',{'sle_st_a_v1__cl989804f6__cl18eece69','slw_st_a_v1__clb036e152'})]
OLD={'TAPBINS2':('TAPBINS','rows/plan_tapbins.json')}
SUP={'TAPBINS':'TAPBINS2'}
A='<ABSENT>'
def toks(p): return re.findall(r'[^.\[\]]+(?:\[[^\]]*\])?',p)
def get(o,path,parent=False):
    t=toks(path); t=t[:-1] if parent else t
    cur=o
    for tok in t:
        m=re.match(r'([^\[]+)(?:\[name=([^\]]*)\])?$',tok); k,nm=m.group(1),m.group(2)
        if not isinstance(cur,dict) or k not in cur: return A
        cur=cur[k]
        if nm is not None:
            c=[x for x in cur if isinstance(x,dict) and x.get('name')==nm] if isinstance(cur,list) else []
            if not c: return A
            cur=c[0]
    return cur
def typ(p):
    t=toks(p)
    if t[0]=='partition_types': return t[1]
    if t[:3]==['clock','tap_offset','per_port_ps'] and len(t)>3: return t[3]
    return None
m=L('plans/c1m.json'); n=L('plans/c1n.json')
R={nm:(L(f),sh(f),ty) for nm,f,ty in ROWS}; O={k:(L(f),sh(f),nm) for k,(nm,f) in OLD.items()}
F=[f for f in L('lin/mn.json') if f.get('intended') not in (True,'True')]
out=['path\tguard_kind\tguard_note\tC1m_value\tC1n_value\tclass\trow\trow_sha\tsupersedes\tsuperseded_sha']
cnt={}
j=lambda v: 'ABSENT' if v is A else json.dumps(v,sort_keys=True)[:200]
for f in F:
    p=f['path']; vm=get(m,p); vn=get(n,p); ty=typ(p)
    hits=[]
    for nm,(rj,s,tys) in R.items():
        if ty not in tys: continue
        vr=get(rj,p)
        if (vn is not A and vr==vn) or (vn is A and vr is A and get(rj,p,parent=True) is not A): hits.append((nm,s))
    hit=('+'.join(h[0] for h in hits),'+'.join(h[1] for h in hits)) if hits else None
    sup=('-','-'); cls='SILENT-RESTORE'
    if hit:
        cls='INTENDED-BY-ROW'
        for hn in hit[0].split('+'):
          if hn in O:
            oj,os_,onm=O[hn]
            if get(oj,p)==vm and vm is not A: cls='SUPERSEDED'; sup=(onm,os_)
    key=cls+(':'+hit[0] if hit else '')
    cnt[key]=cnt.get(key,0)+1
    out.append('\t'.join([p,f['kind'],(f.get('note') or '-')[:40],j(vm),j(vn),cls,hit[0] if hit else '-',hit[1] if hit else '-',sup[0],sup[1]]))
open(D+'out/C1N-GUARD-174.tsv','w').write('\n'.join(out)+'\n')
print('N',len(F),cnt)
import collections
for l in out[1:]:
    if 'SILENT-RESTORE' in l or 'RTXALL' in l or 'RELAYCOPY' in l: print('S',l[:300])
print(collections.Counter((l.split('\t')[1],l.split('\t')[5]) for l in out[1:]))
