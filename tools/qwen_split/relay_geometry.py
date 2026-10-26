"""Rebuild relay-search geometry after a complete 2210 re-floorplan.

The 2210 generator uses an R0 regular tile array with a station corridor at the
right of each column. Historical PM-H-S lanes must not survive a homes override.
"""
import re


def rebuild(v, m):
    tiles = {}
    for i in m['insts']:
        q = re.fullmatch(r't_(\d+)_(\d+)', i.name)
        if q:
            tiles[tuple(map(int, q.groups()))] = i
    cs = sorted({c for c, r in tiles})
    rs = sorted({r for c, r in tiles})
    if not cs or len(cs) % 2 or cs != list(range(len(cs))) or rs != list(range(len(rs))):
        raise ValueError('2210 relay geometry requires complete paired tile fields')
    if set(tiles) != {(c, r) for c in cs for r in rs}:
        raise ValueError('2210 relay geometry missing tile')
    wh = {(round(i.w, 6), round(i.h, 6)) for i in tiles.values()}
    if len(wh) != 1 or any(i.orient != 'R0' for i in tiles.values()):
        raise ValueError('2210 relay geometry requires equal R0 tile bodies')
    tw, th = next(iter(wh))
    xs = [tiles[c, 0].x for c in cs]
    ys = [tiles[0, r].y for r in rs]
    if any(abs(i.x-xs[c]) > 1e-6 or abs(i.y-ys[r]) > 1e-6 for (c,r),i in tiles.items()):
        raise ValueError('2210 relay geometry has staggered rows/columns')
    half = len(cs)//2
    gaps = [xs[c+1]-xs[c]-tw for c in cs[:-1] if c != half-1]
    if not gaps or min(gaps) <= 0 or max(gaps)-min(gaps) > 1e-3:
        raise ValueError('2210 relay geometry requires uniform positive column corridors')
    corr = min(gaps)
    by = {i.name:i for i in m['insts']}
    for c in cs:
        for r in rs:
            st = by.get(f's_{c}_{r}')
            if st is None or abs(st.x-xs[c]-tw) > 1e-3 or st.w > corr+1e-3:
                raise ValueError('2210 station is not in its actual right corridor')
    v.COLS, v.ROWS = len(cs), len(rs)
    v.CORR, v.TILE_BODY_W = corr, tw
    v.TILE_SLOT = (tw+corr, th)
    m['col_x'] = lambda c: xs[c]
    m['corridor_lanes'] = [(x+tw,corr) for x in xs]
    m['geo'].update(row_y=ys, y0=min(ys), y_top=max(ys)+th, y_io=m['die']['h'])
    rects = [[min(xs[a:b]), min(ys), max(xs[a:b])+tw, max(ys)+th]
             for a,b in [(0,half),(half,len(cs))]]
    fields = [r for r in m['regions'] if r['kind']=='tile_field']
    if len(fields) != 2:
        raise ValueError('2210 relay geometry requires two tile-field regions')
    for region,rect in zip(sorted(fields,key=lambda r:r['rect'][0]),rects):
        region['rect'] = rect
    return dict(columns=len(cs), rows=len(rs), actual_tiles=len(tiles), tile_wh_um=[tw,th],
                corridor_um=corr, row_y_um=ys, corridor_x_um=[x+tw for x in xs],
                field_rects_um=rects, historical_pmhs_lanes_replaced=True,
                clock_delivery='OPEN: regional clock timing/native phi-R still required')
