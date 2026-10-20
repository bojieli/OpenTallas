import sys,collections,re,statistics as st
D=sys.argv[1]
root={};xy={}
for l in open(D+'/geom/clknets.tsv'):
    p=l.rstrip('\n').split('\t'); root[p[1]]=p[0].replace('clk_rx/pll_','').replace('[0]',''); xy[p[1]]=(float(p[3]),float(p[4]))
arr={}
for l in open(D+'/rA/tt/arrivals_tt.tsv'):
    p=l.split('\t'); arr[p[0]]=float(p[1])
reg=collections.defaultdict(list)
for pin,a in arr.items(): reg[root.get(pin,'?')].append(pin)
rows=[]
for r,pins in reg.items():
    a=[arr[p] for p in pins]; xs=[xy[p][0] for p in pins if p in xy]; ys=[xy[p][1] for p in pins if p in xy]
    fams=collections.Counter(re.sub(r'_\d+$','',p.split('/')[0]) if p.startswith('rstt') else re.sub(r'_\d+$','',p.split('/')[0]) for p in pins)
    rows.append((st.median(a),r,len(pins),max(a)-min(a),(min(xs),max(xs),min(ys),max(ys)) if xs else None,fams.most_common(3)))
rows.sort(reverse=True)
for x in rows[:30]: print('%.0f'%x[0],x[1],x[2],'spread %.0f'%x[3],'bbox',tuple(round(v) for v in x[4]) if x[4] else None,x[5])
print('...')
# bbox span of cb16 regions
cb=[x for x in rows if any(f.startswith('c16') for f,_ in x[5])]
print('cb16 regions',len(cb),'median arrival range %.0f..%.0f'%(min(x[0] for x in cb),max(x[0] for x in cb)))
sl=[x for x in rows if any(f.startswith('dvs') for f,_ in x[5])]
print('slice regions',len(sl),'median arrival range %.0f..%.0f'%(min(x[0] for x in sl),max(x[0] for x in sl)))
