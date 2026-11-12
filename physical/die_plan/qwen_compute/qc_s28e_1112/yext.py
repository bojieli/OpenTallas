import json,sys,collections
EPS=1e-6
p=json.load(open(sys.argv[1])); pt=p['partition_types']
SIZE={"outline_um","track_offset_um","bit_site_cell_um","window_um","in_window_um","out_window_um","width_um","pitch_um","keepouts_um"}
for t in sorted(pt):
    if not t.startswith(sys.argv[2]): continue
    v=pt[t]; W,H=v['outline_um']; ys=collections.defaultdict(lambda:[1e9,-1e9])
    def add(c,y): a=ys[c]; a[0]=min(a[0],y); a[1]=max(a[1],y)
    def walk(o,key=None,top=None):
        if isinstance(o,dict):
            for k,x in o.items():
                if k in SIZE: continue
                if k=='origin_um' and 'outline_um' in o: continue
                walk(x,k,top or k)
        elif isinstance(o,list):
            if o and all(isinstance(x,(int,float)) for x in o):
                if key and 'rect' in key and len(o)==4: add(top,o[1]); add(top,o[3]); return
                if len(o)>=2 and key and (key.endswith('_um') or key in ('xy','root','outs')):
                    if abs(o[1]-H)<6 : return
                    add(top,o[1])
                return
            for x in o: walk(x,key,top)
    for k,x in v.items():
        if k in ('buses','outline_um','contents','note'): continue
        walk(x,k,k)
    for b in v.get('buses',[]):
        if b.get('face') in ('E','W'): add('win_EW',b['window_um'][0]); add('win_EW',b['window_um'][1])
    for s in v.get('ft_slots',[]):
        for f,wk in (('in_face','in_window_um'),('out_face','out_window_um')):
            if s.get(f) in ('E','W') and s.get(wk): add('ftwin_EW',s[wk][0]); add('ftwin_EW',s[wk][1])
    hi=max(a[1] for a in ys.values())
    print('%-36s H=%.0f content_ymax=%.0f  '%(t,H,hi)+' '.join('%s:%.0f'%(k,a[1]) for k,a in sorted(ys.items()) if a[1]>0.5*H))
