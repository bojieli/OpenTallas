import sys,re,collections
for f in sys.argv[1:]:
    lv=collections.defaultdict(list)
    for l in open(f):
        p=l.split()
        if p[0]=='N':
            m=re.match(r'ckm_n(\d+)_',p[1])
            if m: lv[int(m.group(1))].append(float(p[2]))
        elif p[0]=='D': lv[99].append(float(p[2]))
    print(f.split('/')[-1],' '.join('L%d:%.1f'%(k,max(v)-min(v)) for k,v in sorted(lv.items())))
