import json,sys,collections,re
M=json.load(open(sys.argv[1]))
by=collections.defaultdict(list)
for w in M['fixed_wires']:
    m=re.match(r'ckm_n(\d+)_',w['drv'])
    if not m or not w.get('branches'): continue
    L=int(m.group(1))+1
    x,y=w['drv_xy'];man=sum(abs(bx-x)+abs(by_-y) for _,bx,by_ in w['branches'])
    # plan-ideal: each child leg length from htree
    if man<20: continue
    by[L].append((w['wire_um']/man,w['wire_um'],man,w['name']))
for L in sorted(by):
    v=by[L];mx=max(v);print('child level',L,len(v),'max wire/sum-manh %.3f'%mx[0],'n>1.10',sum(1 for t in v if t[0]>1.10),mx)
