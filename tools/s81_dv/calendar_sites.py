"""Reserve complete coincident serial reset calendars before tree placement.

Only physical sites change. A reservation is atomic: every macro must be legal,
inside its own clock region and every internal/external planned hop within reach.
Failure leaves the ordinary placement path available and is reported.
"""
import collections
import math


def reserve(st, parent, kids, terms, planned, loc, placer, reach, box_of, explicit=()):
    hop = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
    same = lambda a, b: hop(planned[a], planned[b]) < 1e-4
    groups = []
    seen = set()
    for first in sorted(st):
        if first in seen or (first in parent and len(kids[parent[first]]) == 1 and same(first, parent[first])):
            continue
        chain = [first]
        while len(kids[chain[-1]]) == 1:
            nxt = kids[chain[-1]][0]
            if not same(chain[-1], nxt):
                break
            chain.append(nxt)
        seen.update(chain)
        if len(chain) >= 4:
            groups.append(chain)
    groups.sort(key=lambda c: (-len(c), c[0]))
    fixed, failures = {}, []
    for v in sorted(explicit):
        c = planned[v]; w,h = loc[v][2:4]
        bx = box_of.get(v)
        r = (c[0]-w/2,c[1]-h/2,c[0]+w/2,c[1]+h/2)
        if placer.hits(r) or (bx and not (bx[0] <= c[0] <= bx[2] and bx[1] <= c[1] <= bx[3])):
            raise ValueError(str(dict(inst=v, xy=c, rectangle=r, region_bbox=bx, colliders=list({q for bucket in placer.buck.values() for q in bucket if q[0] < r[2]+.5 and r[0] < q[2]+.5 and q[1] < r[3]+.5 and r[1] < q[3]+.5}))))
        placer.add(r); fixed[v] = c
    for chain in groups:
        if any(v in fixed for v in chain):
            continue
        w = max(loc[v][2] for v in chain)
        h = max(loc[v][3] for v in chain)
        px, py = planned[chain[0]]
        pitch_x, pitch_y = w + 1.0, h + 1.0
        # A continuous serpentine scan reserves real free sites, skipping fixed
        # obstacles. Entire serial paths are checked before committing any site.
        best = None
        for wide in sorted(set((int(math.ceil(math.sqrt(len(chain)))), 2, 4, 8, 16))):
            rows = int(math.ceil(len(chain) / wide)) + 6
            cols = wide + 6
            for swap in (False, True):
                for flip in (False, True):
                    candidates = []
                    for yy in range(rows):
                        xs = range(cols) if yy % 2 == 0 else range(cols-1, -1, -1)
                        for xx in xs:
                            dx, dy = (xx-(cols-1)/2)*pitch_x, (yy-(rows-1)/2)*pitch_y
                            if swap:
                                dx, dy = dy, dx
                            c = (px + dx, py + dy)
                            if not placer.hits((c[0]-w/2,c[1]-h/2,c[0]+w/2,c[1]+h/2)):
                                candidates.append(c)
                    if flip:
                        candidates.reverse()
                    for offset in range(len(candidates)-len(chain)+1):
                        path = candidates[offset:offset+len(chain)]
                        if any(hop(a,b) > reach-6 for a,b in zip(path,path[1:])):
                            continue
                        valid, score = True, 0.0
                        points = dict(zip(chain,path))
                        for v,c in points.items():
                            bx = box_of.get(v)
                            if bx and not (bx[0] <= c[0] <= bx[2] and bx[1] <= c[1] <= bx[3]):
                                valid=False; break
                            outside = ([parent[v]] if v in parent and parent[v] not in points else []) + [u for u in kids[v] if u not in points]
                            targets = [fixed.get(u, planned[u]) for u in outside] + list(terms[v])
                            if any(hop(c,t) > reach-6 for t in targets):
                                valid=False; break
                            score += hop(c, planned[v]) + 2*sum(hop(c,t) for t in targets)
                        if valid and (best is None or score < best[0]):
                            best = score, points
        if best is None:
            failures.append(dict(first=chain[0], stages=len(chain)))
            continue
        for v,c in best[1].items():
            vw,vh = loc[v][2:4]
            placer.add((c[0]-vw/2,c[1]-vh/2,c[0]+vw/2,c[1]+vh/2))
            fixed[v]=c
    return fixed, dict(groups=len(groups), reserved_stations=len(fixed), unresolved=failures,
                       rule='atomic serial calendar reservation before reset tree placement; legal sites, own region, unchanged nets and stages')


def frame_region_boxes(stations, ibits, blocks, reach, box_of):
    """Bound source-native per-frame clock roots absent from legacy geo grids."""
    import re
    result = dict(box_of)
    for v in stations:
        roots = [n for n, _ in ibits[v].get('ck', [])]
        for root in roots:
            m = re.fullmatch(r'ck_frame_(.+)_r\d+', root)
            if v not in result and m and m[1] in blocks:
                b = blocks[m[1]]; g = reach - 10.0
                result[v] = (b['x']-g,b['y']-g,b['x']+b['w']+g,b['y']+b['h']+g)
    return result


def remove_rect(placer, rectangle):
    """Remove one macro despite sub-DBU float reconstruction of its upper edge.

    A center +/- half-width rectangle and lower-left + width rectangle may
    differ by 2e-12 um. Identity tolerance is 1e-7 um, 10,000 times below the
    consumed LEF's 0.001 um DBU; physical clearance checks remain unchanged.
    """
    eps = 1e-7
    x0,y0,x1,y1 = rectangle
    removed = 0
    for i in range(int((x0-eps)//placer.B),int((x1+eps)//placer.B)+1):
        for j in range(int((y0-eps)//placer.B),int((y1+eps)//placer.B)+1):
            bucket=placer.buck.get((i,j),[])
            for k, other in enumerate(bucket):
                if all(abs(a-b) <= eps for a,b in zip(rectangle,other)):
                    bucket.pop(k); removed += 1; break
    if not removed:
        raise ValueError('reset placement rectangle missing from occupancy: '+str(rectangle))


def rebuild_occupancy(placer, loc, stations, blockages=()):
    """Use current instance geometry, dropping obsolete forward-cell positions."""
    placer.buck.clear()
    for v, (x,y,w,h,_) in sorted(loc.items()):
        if v not in stations:
            placer.add((x,y,x+w,y+h))
    for b in blockages:
        placer.add((b['x'],b['y'],b['x']+b['w'],b['y']+b['h']))
