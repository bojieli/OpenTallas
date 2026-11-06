"""Opt-in planning repair of over-capacity density-tap tables.

Existing plans/callers are unchanged. New clock ports are explicit physical
costs; callers must regenerate/review the native context and preserve delivered
reset/START authority before any physical trial. This is a sizing helper, not
clock/timing qualification.
"""
import schema
import gen_phys
import taps


def _overload(load, cap):
    return sum(max(0, value-cap) for value in load)


def repair(P, tn, sites, sinks=None):
    typ = P.types[tn]
    clock = typ.get("clock", {})
    cap = int(clock.get("tap_max_sinks", 1200))
    radius = float(clock.get("tap_radius_um", 200))
    if cap <= 0 or radius <= 0:
        raise ValueError("tap repair needs positive declared capacity/radius")
    points = list(taps.sink_sites(P, tn) if sinks is None else sinks)
    if not points or any(p[2] <= 0 or p[2] > cap for p in points):
        raise ValueError("sink inventory is empty or one indivisible sink exceeds capacity")
    if [s[0] for s in sites] != ['clk'] + [f'clk_t{i}' for i in range(1, len(sites))]:
        raise ValueError('requires a canonical contiguous density-tap table')
    xy = [(float(s[1]), float(s[2])) for s in sites]
    if not xy or len(set(xy)) != len(xy):
        raise ValueError("requires distinct existing tap sites")
    core = [(x, y) for _, x, y, _ in schema.core_taps(P, tn)]
    axes = gen_phys.clock_legal_axes(P, tn)
    snap = lambda x, y: gen_phys._snap_tap(P, x, y, pg_legal=not typ.get("hard"))
    added, history = [], []

    def assign():
        return taps.assign([(None, x, y) for x, y in xy], points, cap, radius,
                           max_distance_um=radius)

    load, far, assigned = assign()
    if max(far) > radius+1e-6:
        raise ValueError("input profile has uncovered sinks; repair spatial coverage first")
    history.append(dict(taps=len(xy), excess=_overload(load, cap), max_load=max(load)))
    while _overload(load, cap):
        before = _overload(load, cap)
        pending = []
        for index in sorted((i for i, value in enumerate(load) if value > cap),
                            key=lambda i: (-(load[i]-cap), i)):
            cloud = [p for p, owner in zip(points, assigned) if owner == index]
            span = [max(p[a] for p in cloud)-min(p[a] for p in cloud) for a in (0, 1)]
            axis = 0 if span[0] >= span[1] else 1
            cloud.sort(key=lambda p: (p[axis], p[1-axis]))
            half = sum(p[2] for p in cloud)/2
            split, weight = 0, 0
            while split < len(cloud)-1 and weight < half:
                weight += cloud[split][2]
                split += 1
            halves = [g for g in (cloud[:split], cloud[split:]) if g]
            seeds = [(taps._wmedian(g, 0), taps._wmedian(g, 1)) for g in halves]
            seeds += [(p[0], p[1]) for p in sorted(
                cloud, key=lambda p: (-p[2], -(abs(p[0]-xy[index][0])+abs(p[1]-xy[index][1])), p[0], p[1]))]
            choices = {}
            for x, y in seeds:
                try:
                    q = schema.tap_clear(typ, x, y, core+xy+pending, strict=True,
                                         pin_snap=snap, legal_axes=axes)
                except ValueError:
                    continue
                q = (round(q[0], 4), round(q[1], 4))
                if q in xy or q in pending:
                    continue
                gain = sum(p[2] for p in cloud
                           if abs(p[0]-q[0])+abs(p[1]-q[1])+1e-6 <
                           abs(p[0]-xy[index][0])+abs(p[1]-xy[index][1]))
                distance = sum(p[2]*(abs(p[0]-q[0])+abs(p[1]-q[1])) for p in cloud)
                if gain > 0:
                    choices[q] = (-gain, distance, q)
            if not choices:
                raise ValueError(f"{tn}: no legal local capacity split for tap {index}")
            pending.append(min(choices, key=choices.get))
        xy.extend(pending)
        added.extend(pending)
        load, far, assigned = assign()
        after = _overload(load, cap)
        history.append(dict(taps=len(xy), excess=after, max_load=max(load)))
        if max(far) > radius+1e-6 or after >= before:
            raise ValueError(f"{tn}: added local sites did not strictly reduce capacity debt within declared radius")
    # Empty drops carry no tree; select the main source as density_taps does.
    rows = sorted(((x, y, int(round(n)), r) for (x, y), n, r in zip(xy, load, far) if n > 0),
                  key=lambda q: (q[1], q[0]))
    origin = clock.get("tap_um", [typ["outline_um"][0]/2, typ["outline_um"][1]/2])
    main = min(range(len(rows)), key=lambda i: (abs(rows[i][0]-origin[0])+abs(rows[i][1]-origin[1]), i))
    rows = [rows[main]] + rows[:main] + rows[main+1:]
    output = [("clk" if i == 0 else f"clk_t{i}", x, y, n, round(r, 4))
              for i, (x, y, n, r) in enumerate(rows)]
    return dict(sites=output, added_sites=added, history=history,
                capacity=cap, radius_um=radius, qualified=False)
