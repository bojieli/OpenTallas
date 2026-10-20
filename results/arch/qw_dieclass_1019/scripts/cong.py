import sys,re,collections
f=sys.argv[1]
nets=collections.Counter();pref=collections.Counter();ys=collections.Counter();types=collections.Counter();regions=collections.Counter()
cur=None;cnt=0
for line in open(f):
    line=line.strip()
    if line.startswith('violation type'):
        t=line.split(':',1)[1].strip();types[t]+=1;cnt+=1
    elif line.startswith('srcs'):
        n=line.split('net:')[-1] if 'net:' in line else line
        nets[n]+=1
        m=re.match(r'n_dc_r(\d+)_L(\d+)',n)
        if m: regions['r'+m.group(1)]+=1; pref['n_dc_L'+m.group(2)]+=1
        else: pref[re.sub(r'\d+','#',n)[:60]]+=1
    elif line.startswith('bbox'):
        m=re.findall(r'[\d.]+',line); ys[(round(float(m[1])),)]+=1
print('total',cnt,types.most_common())
print('distinct nets',len(nets)); print('top nets',nets.most_common(15))
print('prefix',pref.most_common(20)); print('regions',len(regions),regions.most_common(25))
print('y rows',len(ys),ys.most_common(20))
