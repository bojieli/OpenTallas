"""Apply source-pinned native macro origins before planning relay occupancy.

The real placer uses site/track-compatible origins. Its measured movements must
enter the GEN geometry; an outward-moving PHY cannot consume relay space later.
An explicit plan is opt-in and refuses stale instance/master/orientation/shape.
"""
import math


def apply(instances, plan, source_positions=None):
    if plan.get('schema') != 'opentallas.native_origin_plan.v1':
        raise ValueError('native origin plan: unsupported schema')
    by = {i.name: i for i in instances}
    rows, seen = [], set()
    for r in plan['entries']:
        n = r['instance']
        if n in seen or n not in by:
            raise ValueError(f'native origin plan: duplicate or missing instance {n}')
        seen.add(n)
        if source_positions is not None and n not in source_positions:
            raise ValueError(f'native origin plan: missing source position {n}')
        i = by[n]
        if i.master != r['master'] or getattr(i, 'orient', 'R0') != r['orient']:
            raise ValueError(f'native origin plan: stale master/orientation {n}')
        before = [i.x, i.y, i.w, i.h]
        if len(r['before']) != 4 or any(abs(a-b) > 0.0011 for a,b in zip(before, r['before'])):
            raise ValueError(f'native origin plan: stale geometry {n}: {before} != {r["before"]}')
        after = r['after_xy']
        if len(after) != 2 or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x < 0 for x in after):
            raise ValueError(f'native origin plan: invalid origin {n}')
        if len(r.get('master_lef_sha256','')) != 64 or len(r.get('track_snap_source_sha256','')) != 64:
            raise ValueError(f'native origin plan: missing source proof {n}')
        rows.append((i, before, after))
    # Validate the entire plan before any mutation.
    for i, _, after in rows:
        i.x, i.y = after
        if source_positions is not None:
            source_positions[i.name]['x'], source_positions[i.name]['y'] = after
    return dict(schema=plan['schema'], source=plan.get('source'),
                moved=[dict(instance=i.name, master=i.master, before=before, after=[i.x,i.y,i.w,i.h])
                       for i,before,_ in rows])


def verify(instances, receipt):
    """Refuse any later source transform that restores or shifts the proved origin."""
    by={i.name:i for i in instances}
    for r in receipt['moved']:
        i=by[r['instance']]
        if i.master != r['master'] or any(abs(a-b)>0.0011 for a,b in zip([i.x,i.y,i.w,i.h],r['after'])):
            raise ValueError(f'native origin plan overwritten before relay planning: {i.name}')
    return len(receipt['moved'])
