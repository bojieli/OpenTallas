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
import re
from collections import defaultdict
from pathlib import Path

SCHEMA = 'opentallas.die_gen_safety_facts.v1'
RING = ('qfd_landh_', 'qfd_landh0_')
FORWARDED = ('qfd_rlyh_', 'qfd_rlyh0_', 'qfd_rlyr_', 'qfd_rlyr0_')


def channels(model):
    """Y sweep of actual hard-block outlines, preserving every intervening gap."""
    w, h = model['die']['w'], model['die']['h']
    events = defaultdict(list)
    obstacles = [(i.x, i.y, i.x+i.w, i.y+i.h) for i in model['insts']
                 if i.kind not in ('relay', 'reset_rep')]
    obstacles += [tuple(k['rect']) for k in model.get('relay_keepouts', [])]
    for n, (a, b, c, d) in enumerate(obstacles):
        x0, x1 = max(0., a), min(w, c)
        y0, y1 = max(0., b), min(h, d)
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



def relay_chains(segments, by):
    """Trace actual emitted relay ports; keep internal site faces in polylines.

    W2 must see the whole chain: splitting at each relay would reset its unsited
    distance at precisely the site whose channel membership needs checking.
    """
    outgoing = defaultdict(list)
    for k, w in enumerate(segments):
        outgoing[tuple(w['src'])].append(k)
    thru = dict(a='b', a_d='b_d', b_r='a_r', d='q')
    succ, predecessors = {}, set()
    for k, w in enumerate(segments):
        i, p = w['dst']
        dest = by[i]
        out = thru.get(p.lstrip('*')) if dest.kind in ('relay', 'reset_rep') else None
        nxt = outgoing.get((i, out), []) if out else []
        succ[k] = nxt
        predecessors.update(nxt)
    result, visited = [], set()
    def visit(k, path, indexes):
        if k in indexes:
            raise ValueError('GEN safety: cycle in relay wire chain')
        visited.add(k)
        w = segments[k]
        points = path + w['pts']
        ids = indexes + [k]
        if succ[k]:
            for n in succ[k]:
                visit(n, points, ids)
        else:
            parts = [segments[n] for n in ids]
            result.append(dict(id=parts[0]['id'] if len(parts)==1 else 'chain:'+parts[0]['id']+'->'+w['id'],
                pts=points, kind=parts[0]['kind'], src=parts[0]['src'], dst=w['dst'], bits=w['bits'],
                segments=[dict(id=z['id'], worst_net_bit=z.get('worst_net_bit')) for z in parts]))
    for k in range(len(segments)):
        if k not in predecessors:
            visit(k, [], [])
    if len(visited) != len(segments):
        raise ValueError('GEN safety: relay cycle has no source')
    return result

def export_model(model, pin_pos):
    by = {i.name: i for i in model['insts']}
    roots, clock, pin_clock, clock_source = {}, defaultdict(set), {}, {}
    related = {}
    for key in ("dv_cluster_clocks", "native_static_io_bind"):
        spec = model.get(key) or {}
        if spec.get("master") and spec.get("related_pins"):
            related[spec["master"]] = spec["related_pins"]
    for bid, cls, bits, eps in model['buses']:
        if cls != 'clock_trunk':
            continue
        source = eps[0] if eps else None
        root = '/'.join(source) if source and source[0] in by and len(eps) > 1 else None
        roots[bid] = dict(root=root)
        clock_source[bid] = source
        for inst, port in eps[1:]:
            clock[inst].add(bid)
            pin_clock[(inst, port.lstrip("*"))] = bid
    source_sync = []
    def canonical(net, seen=()):
        if net in seen:
            raise ValueError(f'GEN safety: cyclic forwarded clock {net}')
        src = clock_source.get(net)
        if src and src[0] in by and src[1] == 'ck_o' and by[src[0]].master.startswith(FORWARDED + RING):
            master = by[src[0]].master
            cp = 'ck_s' if master.startswith('qfd_landh0_') else ('ck' if master.startswith(('qfd_rlyh0_', 'qfd_rlyr0_')) else 'ckf')
            upstream = pin_clock.get((src[0], cp))
            if upstream:
                return canonical(upstream, seen + (net,))
        return net
    for net in clock_source:
        origin = canonical(net)
        if origin != net:
            source_sync.append(dict(clock=net, upstream_region=origin, source=list(clock_source[net])))
    unknown = lambda i: 'UNDRIVEN:' + i
    def region(i, port=None):
        base = re.sub(r'\[.*\]$', '', (port or '').lstrip('*'))
        refs = related.get(by[i].master, {}).get(base)
        if refs:
            sliced = re.search(r'\[(\d+)(?::(\d+))?\]$', port or '')
            if sliced:
                hi, lo = int(sliced[1]), int(sliced[2] or sliced[1])
                refs = refs[min(hi, lo):max(hi, lo)+1]
            rs = set()
            for cp in set(refs):
                r = pin_clock.get((i, cp))
                if r is None:
                    r = unknown(i + '/' + cp)
                    roots.setdefault(r, dict(root=None))
                rs.add(canonical(r))
            return rs
        # Forwarded frames' reset/control pins are synchronous to local ck,
        # while ckf is their data write clock; lane data is checked end-to-end.
        if by[i].kind == 'relay':
            for cp in ('ck', 'ck_s'):
                if (i, cp) in pin_clock:
                    return {canonical(pin_clock[i, cp])}
        rs = clock.get(i, set())
        if not rs:
            roots.setdefault(unknown(i), dict(root=None))
            return {unknown(i)}
        return {canonical(r) for r in rs}
    wires, crossings, centroid_only, reset_landings = [], [], [], []
    def cross(bid, si, di, bits, landing=None, src=None, dst=None, sp=None, dp=None):
        ra, rb = region(si, sp), region(di, dp)
        if src is not None:
            src = canonical(src)
            ra = {src}; roots.setdefault(src, dict(root=None))
        if dst is not None:
            dst = canonical(dst)
            rb = {dst}; roots.setdefault(dst, dict(root=None))
        for a in sorted(ra):
            for b in sorted(rb):
                if a == b:
                    continue
                crossings.append(dict(id=bid, src_region=a, dst_region=b,
                                      landing=landing, bits=bits, src=si, dst=di))
    lane_segments = set()
    for lane in (model.get('fwd_lanes') or {}).get('lanes', []):
        st = lane.get('stations') or []
        land = lane.get('landing')
        n = int(lane.get('n', len(st) + bool(land)))
        lane_segments.add(lane['bid'])
        lane_segments.update(f"{lane['bid']}__r{k}" for k in range(1, n + 1))
        lane_segments.update(f"fep_{lane['bid']}__r{k}" for k in range(1, n))
        capture = lane.get('reset_capture') or {}
        ci = capture.get('inst')
        if lane.get('lane') == 'reset' and ci in by and by[ci].master == 'qfd_rst_rep':
            incoming = any(b[3] and b[3][0][0] == land and (ci, 'd') in b[3][1:] for b in model['buses'])
            outgoing = any(b[3] and b[3][0] == (ci, 'q0') and tuple(capture.get('receiver', [])) in b[3][1:] for b in model['buses'])
            same_clock = clock.get(ci) and clock.get(ci) == clock.get(lane['dst'])
            source_proved = bool((model.get('reset_sync', {}).get('rep_check') or [False])[0])
            if incoming and outgoing and same_clock and source_proved:
                reset_landings.append(dict(id=lane['bid'], landing=ci, src=lane['src'], dst=lane['dst'],
                    kind='observed_closed_two_stage_receiving_reset_capture',
                    clock=sorted(clock[ci]), cold_reset_edges=2,
                    calendar=capture.get('calendar'), source_feed_contract=lane.get('source_feed_contract')))
                continue
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
            bit = None
            if hasattr(pin_pos, 'bits'):
                aa, bb = pin_pos.bits(si, sp, bits), pin_pos.bits(di, dp, bits)
                if aa is not None and bb is not None:
                    bit = max(range(bits), key=lambda j: abs(aa[j][0]-bb[j][0])+abs(aa[j][1]-bb[j][1]))
                    pts = [list(aa[bit]), list(bb[bit])]
            if bit is None:
                centroid_only.append(f'{bid}:{k}')
            wires.append(dict(id=f'{bid}:{k}', pts=pts, bits=bits, worst_net_bit=bit,
                              kind='reset' if cls == 'reset' else 'sync',
                              src=[si, sp], dst=[di, dp]))
            # Forwarded lanes are checked end-to-end above, on actual regional
            # roots, not on their intermediate forwarded-clock nets.
            if bid in lane_segments:
                continue
            ring = di if by[di].master.startswith(RING) else None
            if by[di].master.startswith('qfd_rst_rep') and dp.lstrip('*') == 'd':
                reset_landings.append(dict(id=bid, src=[si, sp], dst=[di, dp],
                    src_regions=sorted(region(si, sp)), dst_regions=sorted(region(di, dp)),
                    landing=di, kind='two_stage_reset_synchronizer'))
                continue
            cross(bid, si, di, bits, ring, sp=sp, dp=dp)
    wires = relay_chains(wires, by)
    return dict(schema=SCHEMA, design='qwen_compute', reach_um=405.,
                regions=roots, crossings=crossings, wires=wires, channels=channels(model),
                reset_capture_plan=model.get('final_reset_capture_plan'),
                observed_reset_captures=model.get('observed_reset_captures', []),
                centroid_only_segments=centroid_only, reset_landings=reset_landings,
                source_synchronous_clocks=source_sync,
                provenance=dict(generator='tools/qwen_rom_fulldie_b3r2.py:selected final model',
                                pins='worst corresponding generated bit pins; centroid_only_segments lists every unresolved bit geometry fallback',
                                wires='actual source-to-sink relay/reset chains, stitching registered frame input/output sites; each segment retains its exact bus and worst corresponding bit',
                                channels='vacant row envelope outside placed hard-block bodies and declared relay keepouts'))


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
