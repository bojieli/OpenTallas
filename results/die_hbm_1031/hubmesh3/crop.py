"""Crop a mesh_form pilot.def to the window around given nets (same tile/track grid, same PG/blockages) for a fast GRT repro."""
import sys,re
src,out,margin,*nets=sys.argv[1:]; margin=int(margin); T=570
d=open(src).read().split('\n')
cells={};N={}
sec=None
for l in d:
    if l.startswith('COMPONENTS'):sec='C';continue
    if l.startswith('END COMPONENTS'):sec=None
    if l.startswith('NETS'):sec='N';continue
    if l.startswith('END NETS'):sec=None
    if sec=='C' and l.startswith('- '): cells[l.split()[1]]=l
    if sec=='N' and l.startswith('- '):
        N[l.split()[1]]=(l,re.findall(r'\( (\S+) (\S+) \)',l))
keep=set(c for n in nets for c,_ in N[n][1])
pts=[tuple(map(int,re.search(r'\( (\d+) (\d+) \)',cells[c]).groups())) for c in keep]
A=11400
x0=(min(p[0] for p in pts)-margin)//A*A; y0=(min(p[1] for p in pts)-margin)//A*A
x1=(max(p[0] for p in pts)+margin)//T*T+T; y1=(max(p[1] for p in pts)+margin)//T*T+T
def clip(a,b,c,dd):
    if c<=x0 or a>=x1 or dd<=y0 or b>=y1: return None
    return max(a,x0),max(b,y0),min(c,x1),min(dd,y1)
ND=int(__import__('os').environ.get('NDUMMY','20'))
dc=[];dn=[]
for i in range(ND):
    xa=x0+2000+i*8000; ya=y0+2430+((i%3)*1080)
    dc+=[f'- DA{i} BUFx4f_ASAP7_75t_R + FIXED ( {xa} {ya} ) N ;',f'- DB{i} BUFx4f_ASAP7_75t_R + FIXED ( {xa+5000} {ya} ) N ;']
    dn+=[f'- n_D{i} ( DA{i} Y ) ( DB{i} A ) + USE CLOCK ;']
o=[l for l in d[:5]]+[f'DIEAREA ( {x0} {y0} ) ( {x1} {y1} ) ;',f'COMPONENTS {len(keep)+len(dc)} ;']+[cells[c] for c in sorted(keep)]+dc+['END COMPONENTS']
blk=[]
sec=None
sp={'VDD':[],'VSS':[]};cur=None
for l in d:
    if l.startswith('BLOCKAGES'):sec='B';continue
    if l.startswith('END BLOCKAGES'):sec=None
    if l.startswith('SPECIALNETS'):sec='S';continue
    if l.startswith('END SPECIALNETS'):sec=None
    if sec=='B':
        m=re.match(r'- LAYER (\S+) RECT \( (\d+) (\d+) \) \( (\d+) (\d+) \) ;',l)
        if m:
            c=clip(*map(int,m.groups()[1:]))
            if c: blk.append(f'- LAYER {m.group(1)} RECT ( {c[0]} {c[1]} ) ( {c[2]} {c[3]} ) ;')
    if sec=='S':
        if l.startswith('- '):cur=l.split()[1]
        if cur in sp:
            m=re.search(r'(M\d) (\d+) \+ SHAPE STRIPE \( (\d+) (\d+) \) \( (\d+) (\d+) \)',l)
            if m:
                L,w,a,b,c_,e=m.group(1),*map(int,m.groups()[1:])
                if a==c_:
                    if x0-w<a<x1+w: sp[cur].append(f'{L} {w} + SHAPE STRIPE ( {a} {y0} ) ( {a} {y1} )')
                else:
                    if y0-w<b<y1+w: sp[cur].append(f'{L} {w} + SHAPE STRIPE ( {x0} {b} ) ( {x1} {b} )')
o+=[f'BLOCKAGES {len(blk)} ;']+blk+['END BLOCKAGES','SPECIALNETS 2 ;']
for k,u in (('VDD','POWER'),('VSS','GROUND')):
    v=sp[k]; o.append(f'- {k} + ROUTED {v[0]}'); o+=[f'    NEW {x}' for x in v[1:]]; o.append(f'  + USE {u} ;')
o+=['END SPECIALNETS',f'NETS {len(nets)+len(dn)} ;']+[N[n][0] for n in nets]+dn+['END NETS','END DESIGN']
open(out,'w').write('\n'.join(o)+'\n')
print(x0,y0,x1,y1,len(blk),len(sp['VDD']),len(sp['VSS']))
