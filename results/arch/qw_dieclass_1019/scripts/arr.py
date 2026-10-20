import sys,collections,re,statistics as st
D=sys.argv[1]
root={};xy={}
for l in open(D+'/geom/clknets.tsv'):
    p=l.rstrip('\n').split('\t'); root[p[1]]=p[0].replace('clk_rx/pll_','').replace('[0]',''); xy[p[1]]=(float(p[3]),float(p[4]))
arr={}
for l in open(D+'/rA/tt/arrivals_tt.tsv'):
    p=l.split('\t'); arr[p[0]]=float(p[1])
reg=collections.defaultdict(list)
for pin,a in arr.items(): reg[root.get(pin,'?')].append(a)
spine=sorted(((st.median(v),k,len(v),max(v)-min(v)) for k,v in reg.items()))
print('regions',len(spine),'median-arrival min/max',spine[0][:2],spine[-1][:2])
# histogram of region medians
h=collections.Counter(int(m//2000)*2 for m,_,_,_ in spine); print('region median arrival hist (ns bucket:count)',sorted(h.items()))
inst=collections.defaultdict(list)
for pin,a in arr.items(): inst[pin.split('/')[0]].append((a,root.get(pin,'?')))
for i in sys.argv[2:]:
    v=inst.get(i,[]); 
    if v: print(i,'n',len(v),'min %.0f max %.0f'%(min(a for a,_ in v),max(a for a,_ in v)),'regions',sorted(set(r for _,r in v))[:8])
# per family spread
fam=collections.defaultdict(list)
for i,v in inst.items():
    f=re.sub(r'_\d+$','',i) if i.startswith('rstt') else re.sub(r'\d','#',i)
    fam[f]+= [a for a,_ in v]
for f,v in sorted(fam.items(),key=lambda kv:-len(kv[1]))[:20]:
    print('fam',f,len(v),'arr %.0f..%.0f med %.0f'%(min(v),max(v),st.median(v)))
