import json,sys,re,collections
for n in sys.argv[1:]:
    d=json.load(open(f'/tmp/claude-1000/visaudit/tiles/{n}/dump.json'))
    x0,y0,x1,y1=d['die']; W,H=x1-x0,y1-y0
    face=collections.Counter(); span={}
    clk=[]
    for p in d['pins']:
        nm,l,a,b,c,e=p; cx,cy=(a+c)/2,(b+e)/2
        if nm in ('VDD','VSS'): continue
        f=min((cy-y0,'S'),(y1-cy,'N'),(cx-x0,'W'),(x1-cx,'E'))[1]
        face[f]+=1
        pos=cx if f in'NS' else cy
        s=span.setdefault(f,[1e9,-1e9]); s[0]=min(s[0],pos); s[1]=max(s[1],pos)
        if re.search(r'clk|ck_|entry',nm,re.I) and not re.search(r'en$|_en\b|gate',nm): clk.append((nm,f,round(cx,1),round(cy,1)))
    g=[v for v in d.get('density',{}).get('grid',[]) if v is not None]; nb=len(g)
    over=sum(1 for v in g if v>0.8)/max(1,nb); empty=sum(1 for v in g if v<0.05)/max(1,nb)
    mac=[(b[1][:28],round(b[2],1),round(b[3],1),round(b[4],1),round(b[5],1)) for b in d['blocks']]
    print(f"== {n} {W:.2f}x{H:.2f} fill {d['stats']['fill']} pins {len(d['pins'])} bins>0.8 {over:.2f} bins<0.05 {empty:.2f} max {max(g) if g else 0:.2f}")
    for f in 'NSEW':
        if face[f]:
            L=W if f in 'NS' else H; s=span[f]
            print(f"   {f}: {face[f]} pins, span {s[0]:.1f}-{s[1]:.1f} ({s[1]-s[0]:.1f} of {L:.1f} um), {face[f]/max(1,s[1]-s[0]):.1f} pins/um")
    print('   clock-like pins:', clk[:8], '...' if len(clk)>8 else '')
    if len(mac)<=8: print('   macros:', mac)
    else: print('   macros:', len(mac), collections.Counter(m[0] for m in mac))
