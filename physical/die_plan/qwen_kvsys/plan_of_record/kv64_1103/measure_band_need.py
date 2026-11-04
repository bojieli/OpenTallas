import re,json,sys,collections,math,glob,os
W=json.load(open(sys.argv[1]));base=sys.argv[2];res={}
for tdir in sorted(glob.glob(base+'/*')):
    t=os.path.basename(tdir)
    if not t.startswith('kv3_'):continue
    ks=[a+'/gen/'+t for a in sorted(glob.glob(tdir+'/attempt_*'),key=lambda p:int(p.rsplit('_',1)[1]),reverse=True) if os.path.isfile(a+'/gen/'+t+'/1_synth_odb.v') and os.path.isfile(a+'/gen/'+t+'/landing_placement.tcl')]
    if not ks:continue
    k=ks[0];tx=open(k+'/landing_placement.tcl').read();bands={}
    for m in re.finditer(r'\{(u_cland_\S+) \{([0-9. ]+)\} ring:([^\s}]+)\}',tx):
        bands.setdefault(m.group(1),[]).append(list(map(float,m.group(2).split())))
    need=collections.Counter();pat=re.compile(r'^\s*(\S+_ASAP7_75t_R)\s+\\?u_bound\.(u_cland_[^/\s]+)/')
    for l in open(k+'/1_synth_odb.v'):
        m=pat.match(l)
        if m and m.group(2) in bands: need[m.group(2)]+=math.ceil(W.get(m.group(1),0)/0.4/0.054-1e-9)*0.054*0.27
    res[t]=dict(kit=k,bands={b[len('u_cland_'):]:dict(need=round(need[b],1),area=round(sum((r[2]-r[0])*(r[3]-r[1]) for r in rs),1),rects=rs) for b,rs in bands.items() if need[b]})
json.dump(res,open('/tmp/kv64_bandneed.json','w'),indent=1)
for t,v in res.items():
    o=sorted(((b['need']/b['area'],n) for n,b in v['bands'].items()),reverse=True)
    print(t,len(o),'over0.95:',sum(1 for r,_ in o if r>0.95),'max',(round(o[0][0],2),o[0][1]) if o else None)
