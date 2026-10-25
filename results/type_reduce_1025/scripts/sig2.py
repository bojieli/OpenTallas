import re,sys,os,collections,glob
d=sys.argv[1]; skip={'wire','input','output','assign','reg','logic','module','endmodule','always','end','begin','if','else','localparam','parameter','genvar','for','generate','endgenerate','initial','integer'}
S={}
for f in sorted(glob.glob(d+'/*.sv')):
    n=os.path.basename(f)[:-3]
    if n in('bind_cells',) or n.endswith('bound_top'): continue
    c=collections.Counter()
    ports=0
    for l in open(f):
        m=re.match(r'\s*([A-Za-z_]\w*)\s+(#\(|[A-Za-z_]\w*\s*\()',l)
        if m and m.group(1) not in skip: c[m.group(1)]+=1
        if re.match(r'\s*(input|output)\b',l): ports+=1
    dly=c.pop('ot_dp_dly',0); st=c.pop('ot_dp_st',0); c.pop('ot_dp_rsync',0)
    S[n]=(tuple(sorted(c.items())),dly,ports)
G=collections.defaultdict(list)
for n,(s,dly,p) in S.items(): G[s].append((n,dly,p))
print(len(S),'bound modules ->',len(G),'instance signatures ignoring ot_dp_dly pads')
for s,v in G.items():
    if len(v)>1: print(' ',[f'{n}(dly{d},p{p})' for n,d,p in v])
