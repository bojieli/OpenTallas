import json,sys,re,collections
p=json.load(open(sys.argv[1]))
T=p['partition_types']
rect={}
for line in open('parts.tsv'):
    n,t,o,x0,y0,x1,y1=line.rstrip('\n').split('\t'); rect[n]=(t,float(x0),float(y0),float(x1),float(y1))
def fam(n):
    m=re.match(r'sl_([EW]\d)_(.+)$',n)
    if m: return m.group(1),m.group(2)
    m=re.match(r'c_([EW]\d)_(\w\w_\d\d)$',n)
    if m: return m.group(1),m.group(2)
    return '-',n
def seam(a,b):
    _,ax0,ay0,ax1,ay1=rect[a];_,bx0,by0,bx1,by1=rect[b]
    e=0.5
    if abs(ax1-bx0)<e or abs(bx1-ax0)<e:
        L=min(ay1,by1)-max(ay0,by0); return ('V',L) if L>0 else (None,0)
    if abs(ay1-by0)<e or abs(by1-ay0)<e:
        L=min(ax1,bx1)-max(ax0,bx0); return ('H',L) if L>0 else (None,0)
    return (None,0)
lanes={L['id']:L['ports'] for L in p['lanes']}
port={q['id']:q for q in p['ports']}
S=collections.defaultdict(float); thru=collections.defaultdict(float); nonadj=[]
lanelist=[]
for lid,pl in lanes.items():
    chain=[]
    for q in pl:
        P=port[q]; s,d=P['src']['part'],P['dst']['part']; w=P['width']
        k=tuple(sorted((s,d))); S[k]+=w
        o,L=seam(s,d)
        if o is None: nonadj.append((q,s,d,w))
        chain.append(s)
    chain.append(port[pl[-1]]['dst']['part'])
    for m in chain[1:-1]: thru[m]+=port[pl[0]]['width']
    lanelist.append((lid,chain,port[pl[0]]['width']))
print('non-adjacent hops',len(nonadj),nonadj[:5])
out=[]
for (a,b),bits in S.items():
    o,L=seam(a,b)
    if not L: continue
    cap=L*12  # budget face pins/um x layers
    out.append((bits/cap,a,b,o,L,bits,cap))
out.sort(reverse=True)
with open('seams.tsv','w') as f:
    f.write('ratio\ta\tb\tdir\tlen_um\tbits\tpin_cap\n')
    for r in out: f.write('%.3f\t%s\t%s\t%s\t%.1f\t%d\t%.0f\n'%r)
for r in out[:40]: print('%.3f %-14s %-14s %s %7.1f %6d %6.0f'%r)
# per slice part thru bits (E0, W0)
print('--- ft through bits per part (E0/W0/E5/W5 + coll)')
for n in sorted(thru):
    if re.search(r'_(E0|W0)_',n) or not n.startswith(('sl_','c_')):
        print('%-14s %-34s thru %7d'%(n,rect[n][0],thru[n]))
json.dump([(a,c,w) for a,c,w in lanelist],open('lane_chains.json','w'))
