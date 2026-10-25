import collections,statistics as S
U=lambda s:s.replace("\\","")
def load(fn):
    D=collections.defaultdict(list)
    for l in open(fn):
        t=l.rstrip("\n").split("\t"); D[t[0]].append(t[1:])
    return D
def mif(fn):
    R=[]
    for l in open(fn):
        t=l.rstrip("\n").split("\t")
        if t[0] in("IN","OUT") and len(t)>8:
            xy=t[7].split()
            R.append(dict(dir=t[0],m=U(t[1]),pin=t[2],px=float(t[3]),py=float(t[4]),reg=U(t[5]),rx=float(xy[0]) if xy else None,ry=float(xy[1]) if len(xy)>1 else None))
    return R
