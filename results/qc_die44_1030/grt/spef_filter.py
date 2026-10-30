# drop NAME_MAP entries with '$' or ':' (OpenSTA SPEF lexer rejects them) and every D_NET that references one
import sys,re
src,dst=sys.argv[1:3]
L=open(src).read().split('\n')
out=[];bad=set();i=0;mode='hdr';dn=[];kept=dropped=0;dnames=[]
for l in L:
    if l.startswith('*NAME_MAP'): mode='map'; out.append(l); continue
    if mode=='map' and l.startswith('*PORTS'): mode='rest'
    if mode=='map' and l.startswith('*'):
        idx,_,nm=l.partition(' ')
        if '$' in nm or ':' in nm: bad.add(idx); continue
    if mode=='rest' and l.startswith('*D_NET'): mode='net'; dn=[l]; continue
    if mode=='net':
        dn.append(l)
        if l.startswith('*END'):
            refs=set(re.findall(r'\*\d+',' '.join(dn)))
            if refs & bad: dropped+=1; dnames.append(dn[0].split()[1])
            else: kept+=1; out.extend(dn)
            mode='rest'
        continue
    out.append(l)
open(dst,'w').write('\n'.join(out))
print('bad_names',len(bad),'dnets_kept',kept,'dropped',dropped)
