import json,sys,collections,re
EPS=1e-6
p=json.load(open(sys.argv[1]))
pt=p['partition_types']
SIZE={"outline_um","track_offset_um","bit_site_cell_um","window_um","in_window_um","out_window_um","width_um","pitch_um","keepouts_um"}
def xext(t):
    W,H=t['outline_um']
    xs=collections.defaultdict(lambda:[1e9,-1e9])
    def add(cat,x):
        a=xs[cat]; a[0]=min(a[0],x); a[1]=max(a[1],x)
    def walk(o,key=None,top=None):
        if isinstance(o,dict):
            for k,v in o.items():
                if k in SIZE: continue
                if k=='origin_um' and 'outline_um' in o: continue
                walk(v,k,top or k)
        elif isinstance(o,list):
            if o and all(isinstance(v,(int,float)) for v in o):
                if key and 'rect' in key and len(o)==4:
                    add(top,o[0]); add(top,o[2]); return
                if len(o)>=2 and key and (key.endswith('_um') or key in ('xy','root','outs')):
                    x,y=o[0],o[1]
                    if abs(x)<EPS or abs(x-W)<EPS: return
                    add(top,x)
                return
            for v in o: walk(v,key,top)
    for k,v in t.items():
        if k in ('buses','ft_slots','outline_um','hard_cores','contents'): continue
        walk(v,k,k)
    for b in t.get('buses',[]):
        if b.get('face') in ('N','S'):
            w=b['window_um']; add('win_NS',w[0]); add('win_NS',w[1])
    for s in t.get('ft_slots',[]):
        for f,wk in (('in_face','in_window_um'),('out_face','out_window_um')):
            if s.get(f) in ('N','S') and s.get(wk): add('ft_win_NS',s[wk][0]); add('ft_win_NS',s[wk][1])
        walk({k:v for k,v in s.items() if k not in ('in_window_um','out_window_um')},None,'ft_sites')
    for h in t.get('hard_cores',[]):
        o=h['origin_um']; ow=h['outline_um']; orr=h.get('orient','R0')
        w=ow[1] if orr in ('R90','R270','MXR90','MYR90') else ow[0]
        add('hard_cores',o[0]); add('hard_cores',o[0]+w)
    return W,xs
import itertools
rows=collections.defaultdict(list)
for q in p['partitions']:
    if q['name'].startswith('sl_'): rows[round(q['origin_um'][1],2)].append(q)
want=set(sys.argv[2].split(',')) if len(sys.argv)>2 else None
done=set()
for y in sorted(rows):
    print('ROW y=%.2f'%y)
    seq=sorted(rows[y],key=lambda q:q['origin_um'][0])
    for q in seq[:8]:
        t=q['type']
        if t in done: continue
        done.add(t)
        W,xs=xext(pt[t])
        lo=min(a[0] for a in xs.values()); hi=max(a[1] for a in xs.values())
        print('  %-38s W=%.2f content x %.1f..%.1f  '%(t,W,lo,hi)+' '.join('%s:%.0f-%.0f'%(k,a[0],a[1]) for k,a in sorted(xs.items())))
