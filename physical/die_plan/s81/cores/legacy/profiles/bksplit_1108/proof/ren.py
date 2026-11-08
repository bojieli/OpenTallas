import sys
m=sys.argv[1]; o=sys.argv[2]
def names(f):
    r=[]
    for l in open(f):
        l=l.strip()
        if l.startswith('gate/'): r.append(l[5:])
    return r
allw=set(names(f'{o}/gate_{m}_all.txt'))
pk=names(f'{o}/gate_{m}_wires.txt')
n=0
with open(f'{o}/ren_{m}.ys','w') as f:
    for w in pk:
        nw=w[len('u_pk.'):]
        if nw in allw: continue
        f.write('rename %s %s\n' % (('\\'+w) if not w.startswith('$') else w, '\\'+nw)); n+=1
print('renamed', n, 'of', len(pk))
