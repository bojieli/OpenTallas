#!/usr/bin/env python3
"""One targeted smaller-body re-placement after the fixed-body attempt."""
from pathlib import Path
exec(Path('pack_columns.py').read_text())
first_unplaced = list(failed)
locked = {n for n, a in fixed.items() if
          n.startswith(('internal_service_envelope:', 'service_corridor_', 'hb_idx__s_'))
          or a.get('w', 0)*a.get('h', 0) > 4e6
          or a.get('m', '').startswith(('ot_hbm3e_phy', 'ot_pdie_', 'hfd_ckgen', 'hfd_ep_'))}
evicted = {}
def blockers(a):
    seen, hit = set(), []
    for k in keys(a):
        for n in buckets.get(k, ()):
            if n not in seen:
                seen.add(n)
                if overlaps(a, fixed[n]):
                    if n in locked:
                        return None
                    hit.append(n)
    return hit

old_by_name = dict(targets)
remaining = []
for n in first_unplaced:
    if n == 'hc_eng':
        remaining.append(n)
        continue
    old = old_by_name[n]
    best = None
    for x, y in anchors:
        a = dict(x=x, y=y, w=cw, h=ch)
        bs = blockers(a)
        if bs is None:
            continue
        score = (sum(fixed[k]['w']*fixed[k]['h'] for k in bs),
                 len(bs), abs(x-old['x'])+abs(y-old['y']))
        if best is None or score < best[0]:
            best = score, a, bs
    if best is None:
        remaining.append(n)
        continue
    _, a, bs = best
    for k in bs:
        v = fixed.pop(k)
        evicted[k] = v
        for cell in keys(v):
            buckets[cell].discard(k)
    placed[n] = a
    key = 'internal_service_envelope:' + n
    add(key, a)
    locked.add(key)
    for r in C['rectangles']:
        rectangles[n + '/' + r['name']] = dict(
            r, x_um=round(a['x']+r['x_um'], 6),
            y_um=round(a['y']+r['y_um'], 6))

relocated, relocation_failed = {}, []
grid = [(x*GRID, y*GRID) for x in range(1, int(W/GRID))
        for y in range(1, int(H/GRID))]
for n, old in sorted(evicted.items(), key=lambda kv: -kv[1]['w']*kv[1]['h']):
    candidates = [(math.ceil(old['x']/43.2)*43.2, math.ceil(old['y']/43.2)*43.2)]
    candidates += sorted(grid, key=lambda p: abs(p[0]-old['x'])+abs(p[1]-old['y']))
    for x, y in candidates:
        a = dict(old, x=x, y=y)
        if x+a['w'] <= W and y+a['h'] <= H and not blocked(a):
            relocated[n] = a
            add(n, a)
            break
    else:
        relocation_failed.append(n)

out.update(
    status='DIAGNOSTIC_FULL_COUNT_COMPOSITION_FOUND_CLOCK_ROUTE_SOURCE_QUALIFICATION_OPEN'
           if not remaining and not relocation_failed else
           'BOUNDED_SMALLER_BODY_REPLACEMENT_INCOMPLETE_NOT_GLOBAL_NO_FIT',
    placed_service_envelopes=placed, unplaced=remaining,
    individual_source_rectangles=rectangles,
    placed_columns=sum(n != 'hc_eng' for n in placed),
    existing_bodies_moved=relocated,
    existing_bodies_unplaced=relocation_failed,
    existing_bodies_displaced_count=len(evicted),
    large_existing_bodies_remain_fixed=True,
    runtime_s=time.time()-start)
Path('columns_repack.json').write_text(json.dumps(out, indent=1)+'\n')
print(json.dumps({k: out[k] for k in ('status', 'placed_columns', 'unplaced',
    'existing_bodies_displaced_count', 'existing_bodies_unplaced', 'runtime_s')}))
