import re,json,sys,collections,math,glob,os
W=json.load(open(sys.argv[1]));base=sys.argv[2];res={}
SW=.054;RH=.27
FFRE=re.compile(r'DFF|DHL|DLL|SDF')
pat=re.compile(r'^\s*(\S+_ASAP7_75t_R)\s+\\?u_bound\.(u_cland_[^/\s]+)/')
for tdir in sorted(glob.glob(base+'/ot_s81sl_leaf__t*')):
    t=os.path.basename(tdir)
    ks=[a+'/gen/'+t for a in sorted(glob.glob(tdir+'/attempt_*'),key=lambda p:int(p.rsplit('_',1)[1]),reverse=True) if os.path.isfile(a+'/gen/'+t+'/1_synth_odb.v') and os.path.isfile(a+'/gen/'+t+'/landing_placement.tcl')]
    if not ks: continue
    k=ks[0];tx=open(k+'/landing_placement.tcl').read();bands={}
    for m in re.finditer(r'\{(u_cland_\S+) \{([0-9. ]+)\} ring:([^\s}]+)\}',tx):
        bands.setdefault(m.group(1),[m.group(3),[]])[1].append(list(map(float,m.group(2).split())))
    ff=collections.Counter();ffn=collections.Counter();alln=collections.Counter()
    for l in open(k+'/1_synth_odb.v'):
        m=pat.match(l)
        if m and m.group(2) in bands:
            c=m.group(1);w=W.get(c,0);rw=math.ceil(w/.4/SW-1e-9)*SW*RH
            alln[m.group(2)]+=rw
            if FFRE.search(c): ff[m.group(2)]+=rw;ffn[m.group(2)]+=1
    log=glob.glob(k+'/run/logs/asap7/*/base/3_3_place_gp.log')
    err=None;mx=None
    if log:
        for l in open(log[0]):
            if 'OT_CLAND no legal' in l or 'OT_CLAND band' in l: err=l.strip()[-90:]
    ld=glob.glob(k+'/run/logs/asap7/*/base/*.log');st=sorted(os.path.basename(x) for x in ld)
    sign=glob.glob(tdir+'/attempt_*/gen/'+t+'/signoff.json')+glob.glob(k+'/run/**/signoff.json',recursive=True)[:1]
    rows={}
    for b,(tag,rs) in bands.items():
        r=rs[0];A=sum((x[2]-x[0])*(x[3]-x[1]) for x in rs)
        rows[b[8:]]=dict(tag=tag,area=round(A,1),w=round(r[2]-r[0],2),h=round(r[3]-r[1],2),nff=ffn[b],need_ff=round(ff[b],1),need_all=round(alln[b],1))
    res[t]=dict(kit=k,attempt=k.split('attempt_')[1].split('/')[0],err=err,last=st[-1] if st else None,signed=bool(sign),bands=rows)
json.dump(res,open(sys.argv[3],'w'))
print(len(res))
