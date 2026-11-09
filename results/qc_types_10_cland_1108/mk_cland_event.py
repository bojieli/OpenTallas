"""QC-TYPES-10/CLAND plan event plan_qc53v4m_cland on v4w: landing_contract.group_rects_um['u_cland_rst_<bus>'] for every
landing-ring raw reset copy whose kit site (landing_place: the collector-tree site of the source's tap) is >405 um from
its bound d relay (bind_clock_landings reset_placements[T][bus].copied_raw_parent site).  New site: the bound d relay's
own site when the ring face point is within 405 um of it, else a point on the Manhattan d->face path that keeps BOTH
hops <=405 um and clears every hard core by 5 um.  Touches only group_rects_um keys; every other byte-identical (checked).
usage: mk_cland_event.py BASE_PLAN BIND_DIR OUT_PLAN REPORT.json"""
import json,sys,re,copy,hashlib
BASE,BD,OUT,REP=sys.argv[1:5]
raw=open(BASE,'rb').read();P=json.loads(raw);L=json.load(open(BD+'/bind_clock_landings.json'))
S=json.load(open(BD+'/asbuilt.json')) if False else None
rel=re.compile(r"ot_dp_r(?:relay|gate)\w*\s+(\w+)\s*\([^;]*?\.q\(([^)]+)\)\);\s*//[^@\n]*?@\s*\(([-\d.]+),\s*([-\d.]+)\)")
cp=re.compile(r"ot_dp_rrelay\s+u_cland_rst_(\w+)\s*\(\.clk\(clk\),\s*\.d\(([^)]+)\),")
REACH=405.0;H=2.16
def man(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def lpath(a,b,s,vfirst=False):
    if vfirst:
        p=lpath((a[1],a[0]),(b[1],b[0]),s);return (p[1],p[0])
    dx=abs(b[0]-a[0])
    if s<=dx:return (a[0]+(s if b[0]>=a[0] else -s),a[1])
    return (b[0],a[1]+((s-dx) if b[1]>=a[1] else -(s-dx)))
def face_point(t,b):
    g=next((x for x in t.get('buses',[]) if x['name']==b and 'face' in x and 'window_um' in x),None)
    if g is None:
        s=next((x for x in t.get('ft_slots',[]) if x['name']+'_i'==b and 'in_window_um' in x),None)
        if s:g=dict(face=s['in_face'],window_um=s['in_window_um'])
    if g is None:return None
    w,h=t['outline_um'];at=sum(g['window_um'])/2;f=g['face']
    return (0 if f=='W' else w,at) if f in 'EW' else (at,0 if f=='S' else h)
def boxes(t):
    out=[]
    for c in t.get('hard_cores',[]) or []:
        if 'origin_um' not in c or 'outline_um' not in c:continue
        (ox,oy),(cw,ch)=c['origin_um'],c['outline_um']
        if c.get('orient') in ('R90','R270','MXR90','MYR90'):cw,ch=ch,cw
        out.append((ox-5,oy-5,ox+cw+5,oy+ch+5))
    return out
def free(p,bx,w,h):
    return H<=p[0]<=w-H and H<=p[1]<=h-H and not any(x0<=p[0]<=x1 and y0<=p[1]<=y1 for x0,y0,x1,y1 in bx)
rows=[];new=copy.deepcopy(P)
for T,t in sorted(P['partition_types'].items()):
    lc=(t.get('clock') or {}).get('landing_contract') or {}
    tree=lc.get('collector_tree')
    if not isinstance(tree,dict) or not tree.get('relays') or tree.get('hard'):continue
    try:txt=open(f"{BD}/rtl/{t.get('module',T)}.sv",errors='replace').read()
    except FileNotFoundError:continue
    body={m.group(2):(float(m.group(3)),float(m.group(4))) for m in rel.finditer(txt)}
    xy={r['q']:tuple(r['xy']) for r in tree['relays']}
    src={s['name']:s for s in lc.get('collector_local_sources',[])}
    over=lc.get('group_rects_um',{})
    w,h=t['outline_um'];bx=boxes(t)
    for m in cp.finditer(txt):
        b,d=m.group(1),m.group(2)
        s=src.get(b)
        if s is None or d not in body:continue
        node=f"rst_n_t{s['tap']}" if s.get('tap') is not None else s.get('node')
        if node not in xy:continue
        site=xy[node];ds=body[d];hop=man(site,ds)
        if hop<=REACH+1e-6:continue
        pref='u_cland_rst_'+b
        r=dict(type=T,inst=pref,d=d,d_xy=ds,old_site=site,old_hop=round(hop,1))
        if pref in over:r.update(result='SKIP existing override');rows.append(r);continue
        fp=face_point(t,b)
        if fp is None and s.get('xy_um'):fp=tuple(s['xy_um'])     # no bus geometry: the ring's own status-pin site
        r['face']=fp
        tot=man(ds,fp) if fp else None
        pick=None
        if fp is None:pick=ds if free(ds,bx,w,h) else None
        elif tot<=REACH:pick=ds          # the bound relay's own site is a legal relay site by construction
        elif tot<=2*REACH:
            cands=sorted({round(tot/2+k*1.25,3) for k in range(-400,401)},key=lambda v:abs(v-tot/2))
            for sd in cands:
                if sd<tot-REACH or sd>REACH:continue
                for vf in (False,True):
                    p=lpath(ds,fp,sd,vf)
                    if free(p,bx,w,h):pick=p;break
                if pick:break
        if pick is None:r.update(result='OPEN no legal site (d->face %.1f um)'%(tot or -1));rows.append(r);continue
        x,y=pick;rect=[round(max(0,x-H),5),round(max(0,y-H),5),round(min(w,x+H),5),round(min(h,y+H),5)]
        new['partition_types'][T]['clock']['landing_contract'].setdefault('group_rects_um',{})[pref]=rect
        r.update(result='SET',site=[round(x,3),round(y,3)],hop_d=round(man(ds,pick),1),hop_face=round(man(pick,fp),1) if fp else None,rect=rect)
        rows.append(r)
# prove only group_rects_um changed
a=copy.deepcopy(P);b=copy.deepcopy(new)
for q in (a,b):
    for T,t in q['partition_types'].items():
        ((t.get('clock') or {}).get('landing_contract') or {}).pop('group_rects_um',None)
assert a==b,'non group_rects_um change'
gr_changed=sorted(T for T in P['partition_types'] if ((P['partition_types'][T].get('clock') or {}).get('landing_contract') or {}).get('group_rects_um')!=((new['partition_types'][T].get('clock') or {}).get('landing_contract') or {}).get('group_rects_um'))
for T in gr_changed:   # existing override entries untouched
    old=P['partition_types'][T]['clock']['landing_contract'].get('group_rects_um',{});nw=new['partition_types'][T]['clock']['landing_contract']['group_rects_um']
    assert all(nw.get(k)==v for k,v in old.items())
out=json.dumps(new,indent=1)+'\n'
if raw.decode().endswith('\n') and json.dumps(P,indent=1)+'\n'!=raw.decode():print('NOTE base formatting differs from indent=1 dump')
open(OUT,'w').write(out)
import collections
rep=dict(base_sha256=hashlib.sha256(raw).hexdigest(),out_sha256=hashlib.sha256(out.encode()).hexdigest(),types_changed=gr_changed,
         counts=dict(collections.Counter(r['result'].split()[0] for r in rows)),rows=rows)
json.dump(rep,open(REP,'w'),indent=1)
print(rep['counts'],'types',len(gr_changed),'out',rep['out_sha256'][:12])
for r in rows:
    if r['result']!='SET':print(r)
