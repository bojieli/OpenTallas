"""Read-only assigned-pin lattice audit. Never relocates authoritative pins.

Integer nm arithmetic follows emitted LEF .003 formatting. Track table must be
supplied by caller from the actual platform. Returns actionable conflict witnesses.
"""
import collections
import math


def local_residue_conflicts(record):
    """Find impossible common origins independently of track offset/site.

    ASAP7 M1/M3..M9 have one preferred track family per layer. Translation
    and any non-rotated mirror preserve differences of pin centres, so two
    different local residues on one such layer can never share an origin.
    M2 has multiple track offsets and is deliberately left to full platform
    audit(). Cross-face depth centres depend on the final generated outline,
    which can differ from a record by the allowed 24nm shave; leave those to
    the final LEF/platform gate too. A clean result is necessary, not signoff.
    """
    periods={'M1':36,'M3':36,'M4':48,'M5':48,'M6':64,'M7':64,'M8':80,'M9':80}
    groups=collections.defaultdict(lambda:collections.defaultdict(list))
    for port,spec in record['ports'].items():
        coords=spec.get('per_bit')
        if coords is None:
            at=spec['at']
            cs=[at[0]+i*at[1] for i in range(spec['bits'])] if spec['uniform'] else at
            coords=[[spec['face'],spec['layer'],c,spec['depth']] for c in cs]
        if len(coords)!=spec['bits']:
            raise ValueError(f'{port}: bit count mismatch')
        for bit,(face,layer,c,depth) in enumerate(coords):
            if layer not in periods:
                continue
            axis=1 if layer in ('M4','M6','M8') else 0
            if axis!=(1 if face in 'EW' else 0):
                continue
            hw=.009 if layer in ('M1','M3') else .012
            center2=round((c-hw)*1000)+round((c+hw)*1000)
            groups[layer][center2%(2*periods[layer])].append(f'{port}[{bit}]')
    return [dict(layer=layer,period_nm=periods[layer],
                 centre_residues_x2_nm={str(k):dict(pins=len(v),examples=v[:4]) for k,v in sorted(g.items())})
            for layer,g in sorted(groups.items()) if len(g)>1]


def audit(record, tracks, orient='R0', site=(54,270)):
    if orient not in ('R0','MX','MY','R180'):
        raise ValueError('only non-rotated orientations are supported')
    dims=[round(v*1000) for v in record['outline_um']]
    groups=collections.defaultdict(lambda: collections.defaultdict(list))
    unknown=[]
    for port,spec in record['ports'].items():
        coords=spec.get('per_bit')
        if coords is None:
            at=spec['at']
            cs=[at[0]+i*at[1] for i in range(spec['bits'])] if spec['uniform'] else at
            coords=[[spec['face'],spec['layer'],c,spec['depth']] for c in cs]
        if len(coords)!=spec['bits']:
            raise ValueError(f'{port}: bit count mismatch')
        for bit,(face,layer,c,depth) in enumerate(coords):
            name=f'{port}[{bit}]'
            if layer not in tracks:
                unknown.append((name,layer)); continue
            axis,period,offsets=tracks[layer]
            # Reconstruct exactly the coordinate across the preferred direction.
            # Along-face centre is the average of rounded LEF rectangle bounds.
            if axis==(1 if face in 'EW' else 0):
                hw=.009 if layer in ('M2','M3') else .012
                center2=round((c-hw)*1000)+round((c+hw)*1000)
            else:
                d=round(depth*1000)
                center2=d if face in 'WS' else 2*dims[axis]-d
            if (axis==0 and orient in ('MY','R180')) or (axis==1 and orient in ('MX','R180')):
                center2=2*dims[axis]-center2
            allowed=tuple(sorted({(t-center2//2)%period for t in offsets})) if center2%2==0 else ()
            groups[(axis,period)][allowed].append(name)
    axes=[]
    for axis in (0,1):
        constraints=[(p,g) for (a,p),g in groups.items() if a==axis]
        period=math.lcm(site[axis],*(p for p,g in constraints))
        legal=set(range(0,period,site[axis]))
        witnesses=[]
        for p,g in constraints:
            for allowed,names in g.items():
                legal={r for r in legal if r%p in allowed}
                witnesses.append(dict(period_nm=p,allowed_origin_residues_nm=list(allowed),pins=len(names),examples=names[:4]))
        axes.append(dict(axis='xy'[axis],period_nm=period,legal_site_origin_residues_nm=sorted(legal),groups=witnesses))
    return dict(master=record['master'],orientation=orient,unknown_layers=unknown,axes=axes,
                status='PASS' if not unknown and all(a['legal_site_origin_residues_nm'] for a in axes) else 'FAIL')
