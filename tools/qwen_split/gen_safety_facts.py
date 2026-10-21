"""Export final Qwen GEN geometry for ROOT14; never infer a passing relay chain.

The generator installs this at the end of selected(). case_real/case_grt write
work/gen_safety_facts.json automatically. OT_GEN_SAFETY_FACTS_OUT also exports
without emitting a case (e.g. a plan-only fleet run). Pins come from _pin_pos with
strict=True: missing pin geometry is an export error, not an instance centre.

Channels are the vacant placement-row envelope between opaque hard instances,
clipped to the die. Relay/reset frames occupy that envelope, so their footprints
remain available in this *planning* channel map. No new sites, frames or hops are
invented. Detailed occupancy remains the relay allocator's responsibility.
"""
import json
import os
from collections import defaultdict
from pathlib import Path

SCHEMA = 'opentallas.die_gen_safety_facts.v1'
RING = ('qfd_landh_', 'qfd_landh0_')
FORWARDED = ('qfd_rlyh_', 'qfd_rlyh0_', 'qfd_rlyr_', 'qfd_rlyr0_')


def channels(model):
    """Y sweep of actual hard-block outlines, preserving every intervening gap."""
    w, h = model['die']['w'], model['die']['h']
    events = defaultdict(list)
    for n, i in enumerate(model['insts']):
        if i.kind in ('relay', 'reset_rep'):
            continue
        x0, x1 = max(0., i.x), min(w, i.x + i.w)
        y0, y1 = max(0., i.y), min(h, i.y + i.h)
        if x0 < x1 and y0 < y1:
            events[y0].append((n, (x0, x1)))
            events[y1].append((n, None))
    events[0.]; events[h]
    active, out = {}, []
    ys = sorted(events)
    for y0, y1 in zip(ys, ys[1:]):
        for n, interval in events[y0]:
            if interval is None:
                active.pop(n, None)
            else:
                active[n] = interval
        x = 0.
        for lo, hi in sorted(active.values()):
            if x < lo:
                out.append([x, y0, lo, y1])
            x = max(x, hi)
        if x < w:
            out.append([x, y0, w, y1])
    # Empty space is genuinely empty, not "channels undeclared" to gen_check.
    if not out:
        raise ValueError("GEN safety: no vacant placement-row channel in die")
    return out


def export_model(model, pin_pos):
    by = {i.name: i for i in model['insts']}
    roots, clock = {}, defaultdict(set)
    for bid, cls, bits, eps in model['buses']:
        if cls != 'clock_trunk':
            continue
        source = eps[0] if eps else None
        root = '/'.join(source) if source and source[0] in by and len(eps) > 1 else None
        roots[bid] = dict(root=root)
        for inst, port in eps[1:]:
            clock[inst].add(bid)
    unknown = lambda i: 'UNDRIVEN:' + i
    def region(i):
        rs = clock.get(i, set())
        # Keep all clock identities when a block has several clock pins. The
        # communicating-pair intersection below avoids declaring intra-block CDC.
        if not rs:
            roots.setdefault(unknown(i), dict(root=None))
            return {unknown(i)}
        return rs
    wires, crossings = [], []
    def cross(bid, si, di, bits, landing=None, src=None, dst=None):
        ra, rb = region(si), region(di)
        if src is not None:
            ra = {src}; roots.setdefault(src, dict(root=None))
        if dst is not None:
            rb = {dst}; roots.setdefault(dst, dict(root=None))
        if ra & rb:
            return
        for a in sorted(ra):
            for b in sorted(rb):
                crossings.append(dict(id=bid, src_region=a, dst_region=b,
                                      landing=landing, bits=bits, src=si, dst=di))
    lane_instances = set()
    for lane in (model.get('fwd_lanes') or {}).get('lanes', []):
        st = lane.get('stations') or []
        land = lane.get('landing')
        lane_instances.update(st)
        if land:
            lane_instances.add(land)
        # Only an instantiated SRAM landing ring counts. rlyrl reset capture
        # flops are recorded as unlanded rather than mistaken for rings.
        ring = land if land in by and by[land].master.startswith(RING) else None
        cross(lane['bid'], lane['src'], lane['dst'], lane['bits'], ring,
              lane.get('src_ck'), lane.get('dst_ck'))
    for bid, cls, bits, eps in model['buses']:
        if cls in ('clock_trunk', 'clock', 'constant') or len(eps) < 2:
            continue
        si, sp = eps[0]
        for k, (di, dp) in enumerate(eps[1:]):
            pts = [list(pin_pos(si, sp)), list(pin_pos(di, dp))]
            wires.append(dict(id=f'{bid}:{k}', pts=pts, bits=bits,
                              kind='reset' if cls == 'reset' else 'sync',
                              src=[si, sp], dst=[di, dp]))
            # Forwarded lanes are checked end-to-end above, on actual regional
            # roots, not on their intermediate forwarded-clock nets.
            if si in lane_instances or di in lane_instances:
                continue
            ring = di if by[di].master.startswith(RING) else None
            cross(bid, si, di, bits, ring)
    return dict(schema=SCHEMA, design='qwen_compute', reach_um=405.,
                regions=roots, crossings=crossings, wires=wires, channels=channels(model),
                provenance=dict(generator='tools/qwen_rom_fulldie_b3r2.py:selected final model',
                                pins='strict oriented master pin centroids',
                                wires='every emitted non-clock/non-constant bus source-to-sink segment',
                                channels='vacant row envelope outside placed hard-block bodies'))


def write(model, pin_pos, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = export_model(model, pin_pos)
    p.write_text(json.dumps(doc, separators=(',', ':')) + '\n')
    return doc


def install(v, model, pin_factory):
    """Wrap the final model emitters without changing placement or RTL."""
    explicit = os.environ.get('OT_GEN_SAFETY_FACTS_OUT')
    if explicit:
        write(model, pin_factory(), explicit)
    for name in ('case_real', 'case_grt'):
        original = getattr(v, name, None)
        if original is None:
            continue
        def emit(m, work, *args, _emit=original, **kwargs):
            result = _emit(m, work, *args, **kwargs)
            # pin_factory closes over selected's final model. Emitters may use
            # a shallow bus-filtered copy; use that copy for exported coverage.
            write(m, pin_factory(), Path(work) / 'gen_safety_facts.json')
            return result
        setattr(v, name, emit)
