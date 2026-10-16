import json,sys,collections,math
def analyse(path):
    d=json.load(open(path)); X0,Y0,X1,Y1=d['die']; W,H=X1-X0,Y1-Y0
    r={'die_um':[round(W,2),round(H,2)],'fill':d['stats'].get('fill'),'std_um2':d['stats'].get('std_area'),'block_um2':d['stats'].get('block_area')}
    bl=d['blocks']; r['n_macros']=len(bl)
    # macro-to-edge and macro-to-macro gaps
    gaps=[]
    for b in bl:
        _,_,x0,y0,x1,y1=b
        gaps.append(('edge',b[0],round(min(x0-X0,X1-x1,y0-Y0,Y1-y1),2)))
    for i in range(len(bl)):
        for j in range(i+1,len(bl)):
            a,b=bl[i],bl[j]
            dx=max(b[2]-a[4],a[2]-b[4],0); dy=max(b[3]-a[5],a[3]-b[5],0)
            ov_x = min(a[4],b[4])-max(a[2],b[2]); ov_y=min(a[5],b[5])-max(a[3],b[3])
            if (ov_x>0 and dy>0) or (ov_y>0 and dx>0):
                g=dy if ov_x>0 else dx
                if g<60: gaps.append(('mm',a[0]+'|'+b[0],round(g,2)))
    r['sliver_gaps_lt20']=[g for g in gaps if 0<g[2]<20]
    r['min_edge_gap']=min([g[2] for g in gaps if g[0]=='edge'],default=None)
    r['macro_mm_gaps']=sorted(set(g[2] for g in gaps if g[0]=='mm'))[:8]
    # pins per face
    faces=collections.defaultdict(list); layers=collections.Counter(); fl=collections.defaultdict(collections.Counter)
    clk=set(d.get('clocks',[]))
    cpins=[]
    for p in d['pins']:
        n,L,a,b,c,e=p; cx,cy=(a+c)/2,(b+e)/2
        dist={'W':cx-X0,'E':X1-cx,'S':cy-Y0,'N':Y1-cy}; f=min(dist,key=dist.get)
        faces[f].append(cx if f in 'NS' else cy); layers[L]+=1; fl[f][L]+=1
        if n.split('[')[0] in clk: cpins.append((n,f,round(cx,1),round(cy,1)))
    fr={}
    for f,v in faces.items():
        edge=W if f in 'NS' else H; v.sort()
        span=v[-1]-v[0] if len(v)>1 else 0
        # densest 20um window
        best=0; j=0
        for i in range(len(v)):
            while v[i]-v[j]>20: j+=1
            best=max(best,i-j+1)
        fr[f]={'pins':len(v),'span_um':round(span,1),'edge_um':round(edge,1),'occ':round(span/edge,2),'pins_per_um':round(len(v)/max(span,1),2),'peak_pins_per_20um':best,'layers':dict(fl[f])}
    r['faces']=fr; r['pin_layers']=dict(layers); r['n_pins']=len(d['pins']); r['clock_pins']=cpins[:6]
    g=[x for x in d['density']['grid'] if x is not None]
    if g:
        g2=sorted(g); r['density']={'bins':len(g),'mean':round(sum(g)/len(g),3),'p95':round(g2[int(.95*len(g2))-1],3),'max':round(g2[-1],3),'frac_gt_0p8':round(sum(1 for x in g if x>0.8)/len(g),3),'frac_lt_0p1':round(sum(1 for x in g if x<0.1)/len(g),3)}
    return r
if __name__=='__main__':
    for p in sys.argv[1:]: print(p); print(json.dumps(analyse(p),indent=1))
