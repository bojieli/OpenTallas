"""Explicit type-frame die_ft_bands. One geometry source for kit and die.

Shares select floor(N*share) track centres per lattice/band segment;
rectangles end halfway between tracks. Never rounds capacity up. Overlapping
bands use max share. Outside bands the type ft_track_frac (default .25) applies.
"""
import math

LAYERS = ('M4', 'M5', 'M6', 'M7')


def subtract(rect, cut):
    x0,y0,x1,y1 = rect
    a,b,c,d = max(x0,cut[0]),max(y0,cut[1]),min(x1,cut[2]),min(y1,cut[3])
    if a >= c or b >= d:
        return [rect]
    return [r for r in ((x0,y0,a,y1),(c,y0,x1,y1),(a,y0,c,b),(a,d,c,y1))
            if r[0] < r[2] and r[1] < r[3]]


def complement(outline, rects):
    out = [tuple(outline)]
    for cut in rects:
        out = [r for box in out for r in subtract(box,cut)]
    return out


def type_rects(P, tn, ft=True):
    t = P.types[tn]
    w,h = t['outline_um']
    base = float(t.get('ft_track_frac', .25))
    if not 0 <= base <= 1:
        raise ValueError(f'{tn}: invalid ft_track_frac {base}')
    by_layer = {L: [] for L in LAYERS}
    declarations = {L: [] for L in LAYERS}
    for band in t.get('die_ft_bands', []):
        direction = band['dir']
        if direction not in ('EW','NS'):
            raise ValueError(f'{tn}: invalid band direction {direction}')
        lo,hi = map(float,band['span_um'])
        limit = h if direction == 'EW' else w
        if not 0 <= lo < hi <= limit+1e-6:
            raise ValueError(f'{tn}: band outside outline: {lo,hi}')
        hi=min(hi,limit)
        share = float(band.get('die_share',1))
        if not 0 <= share <= 1:
            raise ValueError(f'{tn}: invalid die_share {share}')
        for L in band['layers']:
            if L not in declarations:
                raise ValueError(f'{tn}: reserved band layer {L} outside M4-M7')
            if (P.layers[L]['dir']=='H') != (direction=='EW'):
                raise ValueError(f'{tn}: {L} direction does not match {direction}')
            declarations[L].append((lo,hi,share))
    for L,bands in declarations.items():
        lay=P.layers[L]; horiz=lay['dir']=='H'
        limit=h if horiz else w
        pitch,offset=lay['pitch_um'],lay['offset_um']
        # Partition the cross-track span at band edges and lattice edges.
        # Outside bands the declared background share applies. Inside a band
        # it is replaced, with MAX resolving overlapping declarations.
        grid=getattr(P,'grid',8.64)
        edges=sorted({0,limit,*[v for lo,hi,_ in bands for v in (lo,hi)],
                      *[k*grid for k in range(1,math.ceil(limit/grid))]})
        spans=[]
        for a,b in zip(edges,edges[1:]):
            active=[sh for lo,hi,sh in bands if lo <= (a+b)/2 < hi]
            sh=max(active) if active else base
            k0=math.ceil((a-offset)/pitch-1e-9)
            k1=math.ceil((b-offset)/pitch-1e-9)
            count=max(0,k1-k0)
            n=math.floor(count*sh+1e-9)
            first=k0+(count-n)//2
            ids=range(first,first+n)
            for k in ids:
                c=offset+k*pitch
                low,high=max(a,c-pitch/2),min(b,c+pitch/2)
                if spans and abs(spans[-1][1]-low)<1e-8:
                    spans[-1]=(spans[-1][0],high)
                else: spans.append((low,high))
        by_layer[L]=[(0,a,w,b) if horiz else (a,0,b,h) for a,b in spans]
    return [(L,*r) for L,boxes in by_layer.items()
            for r in (boxes if ft else complement((0,0,w,h),boxes))]


def to_die(P, part, rect):
    p=P.parts[part]; w,h=P.types[p['type']]['outline_um']; ox,oy=p['origin_um']
    L,x0,y0,x1,y1=rect
    lay=P.layers[L]; pitch,offset=lay['pitch_um'],lay['offset_um']
    cross_origin=oy if lay['dir']=='H' else ox
    if abs(cross_origin/pitch-round(cross_origin/pitch)) > 1e-6:
        raise ValueError(f'{part}: {L} origin does not preserve routing tracks')
    orient=p.get('orient','R0')
    if orient not in ('R0','MX','MY','R180'):
        raise ValueError(f'{part}: explicit FT bands require unrotated routing-layer directions, got {orient}')
    mirrored = orient in (('MX','R180') if lay['dir']=='H' else ('MY','R180'))
    cross_size=h if lay['dir']=='H' else w
    if mirrored and abs((cross_size-2*offset)/pitch-round((cross_size-2*offset)/pitch)) > 1e-6:
        raise ValueError(f'{part}: {L} mirror does not preserve routing tracks')
    if orient in ('MY','R180'): x0,x1=w-x1,w-x0
    if orient in ('MX','R180'): y0,y1=h-y1,h-y0
    return (L,ox+x0,oy+y0,ox+x1,oy+y1)


def die_obs_rects(P):
    return [to_die(P,n,r) for n,p in sorted(P.parts.items())
            for r in type_rects(P,p['type'],False)]


def coverage(rect, boxes):
    """Area fraction of a guide covered by a union, respecting both axes."""
    area=(rect[2]-rect[0])*(rect[3]-rect[1])
    if area <= 0: return 0
    left=complement(rect,boxes)
    return max(0,min(1,1-sum((c-a)*(d-b) for a,b,c,d in left)/area))
