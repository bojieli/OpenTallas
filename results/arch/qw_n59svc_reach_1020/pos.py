import json,gzip,re,collections,sys
g=json.load(gzip.open(sys.argv[1]));N=g['endpoint_nodes']
def fam(s):return re.sub(r'\\\[\d+\\\]|\[\d+\]','[]',s)
L=[]
for a,z in g['edges']:
    pa=N[a]['point'];pz=N[z]['point'];d=abs(pa[0]-pz[0])+abs(pa[1]-pz[1])
    if d>405:L.append((d,a,z))
grp=collections.defaultdict(list)
for d,a,z in L:grp[(fam(N[a]['inst']).split('$')[0][:70],fam(N[z]['inst']).split('$')[0][:70])].append((d,N[a]['point'],N[z]['point']))
for k,v in sorted(grp.items(),key=lambda x:-len(x[1]))[:8]:
    xs=[p[1][0] for p in v];ys=[p[1][1] for p in v];xz=[p[2][0] for p in v];yz=[p[2][1] for p in v]
    print(len(v),k,'src x %.0f-%.0f y %.0f-%.0f  dst x %.0f-%.0f y %.0f-%.0f  d %.0f-%.0f'%(min(xs),max(xs),min(ys),max(ys),min(xz),max(xz),min(yz),max(yz),min(p[0] for p in v),max(p[0] for p in v)))
# whole families: where do all codec rx_payload FFs sit, and all p_native_rx_payload?
P=collections.defaultdict(list)
for k,n in N.items():
    f=fam(n['inst'])
    for key in ['g_recv.p_native_rx_payload','u_codec.rx_payload','g_q_payload32.g_vmw','dvf[]','p_esq','g_recv.p_emb_scale_q','rq_c']:
        if key in f:P[key+('|'+f.split('.')[1] if 'g_slot' in f else '')].append(n['point'])
for k,v in P.items():
    xs=[p[0] for p in v];ys=[p[1] for p in v];print(k,len(v),'x %.0f-%.0f mean %.0f y %.0f-%.0f'%(min(xs),max(xs),sum(xs)/len(xs),min(ys),max(ys)))
