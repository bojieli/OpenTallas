"""Final regional reset ownership, after all clock-region splitting.

Rehome only an existing final capture whose complete terminal fanout names one
actual receiving region. Multiple target roots require physically allocated split
captures; this helper records them and never invents sites, clocks or an endpoint
waiver. Foreign rep/d inputs are candidates only: reset/calendar qualification is
kept on HOLD until source-bound release intervals and boot anchors are supplied.
"""
import hashlib
import re
from collections import defaultdict
from pathlib import Path

REP = ('qfd_rst_rep', 'qfd_rst_rep_p8')
RTL = 'rtl/qwen_sys/reset_tree_20261013/ot_qwen_rst_rep.sv'


def finalize(model, per, source_root=None):
    by = {i.name: i for i in model['insts']}
    clocks = defaultdict(dict)
    # m buses still contain pre-refile regional trunks: only final per is valid.
    for bid, cls, bits, eps in model['buses']:
        if cls == 'clock_trunk' and not re.fullmatch(r'clk_r\d+', bid):
            for i, p in eps[1:]:
                clocks[i][p.lstrip('*')] = bid
    for k, eps in per.items():
        for i, p in eps:
            clocks[i][p.lstrip('*')] = f'clk_r{k}'
    related = {}
    for key in ('dv_cluster_clocks', 'native_static_io_bind'):
        spec = model.get(key) or {}
        if spec.get('master'):
            related[spec['master']] = spec.get('related_pins') or {}

    def receiver(i, p):
        p = p.lstrip('*')
        refs = related.get(by[i].master, {}).get(p)
        if refs:
            return {clocks[i].get(cp) for cp in refs}
        if by[i].kind == 'relay':
            # en is captured on source ck_s (one-frame ring) or ck (hop0).
            # rs releases the reader on ck. Do not use a forwarded write clock.
            order = ('ck_s', 'ck') if p == 'en' else ('ck',)
            for cp in order:
                if cp in clocks[i]:
                    return {clocks[i][cp]}
        return set(clocks[i].values()) or {None}

    terminal = defaultdict(list)
    inputs = {}
    for bid, cls, bits, eps in model['buses']:
        if cls in ('clock_trunk', 'clock', 'constant') or bits != 1 or not eps:
            continue
        si, sp = eps[0]
        for di, dp in eps[1:]:
            if by[di].master in REP and dp.lstrip('*') == 'd':
                inputs[di] = (bid, si, sp)
            if by[si].master in REP and re.fullmatch(r'q\d*', sp.lstrip('*')) and by[di].master not in REP:
                terminal[si].append(dict(net=bid, src_port=sp, dst=di, dst_port=dp,
                                         roots=sorted(receiver(di, dp), key=str)))
    moved, split, unresolved = [], [], []
    for rep, loads in sorted(terminal.items()):
        roots = {r for load in loads for r in load['roots']}
        if None in roots or not roots:
            unresolved.append(dict(rep=rep, reason='unknown receiving clock', loads=loads)); continue
        if len(roots) != 1:
            split.append(dict(rep=rep, receiving_roots=sorted(roots), loads=loads)); continue
        dst = next(iter(roots))
        if not re.fullmatch(r'clk_r\d+', dst):
            unresolved.append(dict(rep=rep, reason='nonregional receiving clock; explicit foreign-domain plan required', loads=loads)); continue
        locations = [(k, p) for k, eps in per.items() for i, p in eps if i == rep]
        if len(locations) != 1:
            unresolved.append(dict(rep=rep, reason='capture has no unique final regional clock', loads=loads)); continue
        k0, cp = locations[0]; k1 = int(dst[5:])
        if k0 != k1:
            per[k0].remove((rep, cp)); per.setdefault(k1, []).append((rep, cp))
            moved.append(dict(rep=rep, from_clock=f'clk_r{k0}', clock=dst, loads=loads))
        clocks[rep][cp] = dst
    for k in [k for k, eps in per.items() if not eps]:
        del per[k]
    candidates = []
    for rep, (net, si, sp) in sorted(inputs.items()):
        rd = set(clocks[rep].values())
        rs = set(clocks[si].values())
        if rd and rs and rd == rs:
            continue
        candidates.append(dict(pin=rep+'/d', master=by[rep].master, net=net,
                               source=si+'/'+sp, source_clocks=sorted(rs), clocks=sorted(rd),
                               latency_edges=10 if by[rep].master.endswith('_p8') else 2,
                               qualification='HOLD: receiving-clock source proof and boot/calendar interval evidence required'))
    # Reuse the source proof already performed by _reset_tree; no new gate.
    proof = dict(path=RTL, sha256=None,
                 structural_pass=bool((model.get('reset_sync', {}).get('rep_check') or [False])[0]))
    if source_root is not None:
        path = Path(source_root) / RTL
        proof['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = dict(schema='opentallas.qwen.final-reset-capture-plan.v1', moved=moved,
                  split_required=split, unresolved=unresolved, sync_candidates=candidates,
                  source_proof=proof, calendar='HOLD: no release bounds invented',
                  qualified=False)
    model['final_reset_capture_plan'] = result
    return result


def sink_capture_groups(model, sinks, clock_inputs):
    """Stable receiving-clock ownership for the allocator's initial leaf bins.

    Unknown/multiple clock identities isolate the endpoint rather than merging
    it with another receiver. Every bin still obtains its own real occ.site().
    """
    by = {i.name: i for i in model['insts']}
    follow = model.get('ck_follow') or {}
    related = {}
    for key in ('dv_cluster_clocks', 'native_static_io_bind'):
        spec = model.get(key) or {}
        if spec.get('master'):
            related[spec['master']] = spec.get('related_pins') or {}
    groups = {}
    for inst, port, _xy in sinks:
        p = port.lstrip('*')
        refs = set(related.get(by[inst].master, {}).get(p) or [])
        inputs = {cp.lstrip('*'): net for net, cp in clock_inputs.get(inst, [])}
        if by[inst].kind == 'relay' and p == 'en':
            refs = {'ck_s' if 'ck_s' in inputs else 'ck'}
        elif by[inst].kind == 'relay' and p == 'rs':
            refs = {'ck'}
        elif not refs and len(inputs) == 1:
            refs = set(inputs)
        if len(refs) != 1:
            groups[inst, port] = ('isolated_endpoint', inst, p)
            continue
        cp = next(iter(refs)); owner = inst
        seen = set()
        while (owner, cp) in follow and (owner, cp) not in seen:
            seen.add((owner, cp)); owner = follow[owner, cp]
            ports = {q.lstrip('*') for _net, q in clock_inputs.get(owner, [])}
            if len(ports) != 1:
                # No per-port ownership was supplied for the followed owner.
                # A dedicated capture is safer than assuming its roots equal.
                owner, cp = inst, 'isolated:'+p
                break
            cp = next(iter(ports))
        if (owner, cp) in seen:
            owner, cp = inst, 'isolated:'+p
        groups[inst, port] = ('receiving_owner', owner, cp)
    return groups


def land_forwarded_reset(v, model, occ, pin_pos, width, height, reach, source_root):
    """Append a real closed two-stage receiving capture to lnk_fwd_lrst.

    The original forwarded relay lane remains intact. New placement uses the
    existing occupancy allocator in a conservative feasible box for BOTH actual
    pin hops. Failure asks for real channel/endcap space; there is no overlap or
    reach bypass. Added latency is two cold-reset edges and zero per-token edges.
    """
    lane = next((x for x in model.get('fwd_lanes', {}).get('lanes', [])
                 if x['bid'] == 'lnk_fwd_lrst' and x.get('lane') == 'reset'), None)
    if lane is None or lane.get('reset_capture'):
        return None
    by = {i.name: i for i in model['insts']}
    last, dst = lane['landing'], lane['dst']
    matches = [(j, b, e) for j, b in enumerate(model['buses']) for e in b[3][1:]
               if b[0].startswith(lane['bid']+'__r') and b[3][0][0] == last and e[0] == dst]
    if len(matches) != 1:
        raise ValueError('forwarded reset capture: no unique actual final relay-to-receiver wire')
    j, bus, endpoint = matches[0]
    roots = [(b[0], p) for b in model['buses'] if b[1] == 'clock_trunk'
             for i, p in b[3][1:] if i == dst and p in ('ck', 'clk')]
    if len(roots) != 1:
        raise ValueError('forwarded reset capture: receiver has no unique actual clock root')
    clock = roots[0][0]
    name = 'rstcap_lnk_fwd_lrst'
    if name in by:
        raise ValueError('forwarded reset capture: duplicate capture instance')
    # Get actual closed master pin coordinates, rather than assuming centres.
    master = v.masters(model, 1)['qfd_rst_rep']
    pins = {}
    for p, layer, rect in v.pin_rects(master, 1, {q: 1 for q in master.order}):
        if p.split('[')[0] in ('d', 'q0'):
            pins[p.split('[')[0]] = ((rect[0]+rect[2])/2, (rect[1]+rect[3])/2)
    dxy, qxy = pins['d'], pins['q0']
    a, b = pin_pos(*bus[3][0]), pin_pos(*endpoint)
    # Allowable lower-left corners are intersecting Manhattan balls. Their
    # midpoint and this inscribed square are entirely inside both reach balls.
    ca, cb = (a[0]-dxy[0], a[1]-dxy[1]), (b[0]-qxy[0], b[1]-qxy[1])
    distance = abs(ca[0]-cb[0])+abs(ca[1]-cb[1])
    radius = reach-distance/2
    if radius <= 0:
        raise ValueError('forwarded reset capture: actual terminal pins require another relay/channel')
    cx, cy = (ca[0]+cb[0])/2+width/2, (ca[1]+cb[1])/2+height/2
    box = (cx-radius/2, cy-radius/2, cx+radius/2, cy+radius/2)
    site = occ.site(cx, cy, box=box, lim=reach, w=width, h=height)
    if site is None:
        raise ValueError('forwarded reset capture: no legal cell-row site; enlarge real receiving endcap/channel/outline')
    occ.add((site[0], site[1], site[0]+width, site[1]+height))
    cap = v.Inst(name, 'qfd_rst_rep', site[0], site[1], width, height,
                 kind='reset_rep', region='reset_tree', domain=by[dst].domain)
    model['insts'].append(cap)
    eps = [e for e in bus[3] if e != endpoint] + [(name, 'd')]
    model['buses'][j] = (bus[0], bus[1], bus[2], eps)
    output = bus[0]+'_sync'
    model['buses'].append((output, 'reset', 1, [(name, 'q0'), endpoint]))
    for k, old in enumerate(model['buses']):
        if old[0] == clock and old[1] == 'clock_trunk':
            model['buses'][k] = (old[0], old[1], old[2], old[3]+[(name, 'clk')])
            break
    model.setdefault('ck_follow', {})[name, 'clk'] = dst
    rec = dict(inst=name, master='qfd_rst_rep', input_net=bus[0], output_net=output,
               source=[last, bus[3][0][1]], receiver=list(endpoint), clock=clock,
               cold_reset_edges=2, cycles_per_token=0, site_um=list(site),
               calendar='HOLD: compile added two-edge reset release into boot/epoch calendar')
    lane['reset_capture'] = rec
    sync = model.setdefault('reset_sync', dict(endpoints=[]))
    # This is an observed, physically instantiated two-stage d input. Its
    # existence does not qualify the boot/calendar relationship or feed timing.
    if (sync.get('rep_check') or [False])[0]:
        sync.setdefault('endpoints', []).append(dict(pin=name+'/d', inst=name, master='qfd_rst_rep',
            net=bus[0], driver=last, clock=clock, cls='forwarded_reset_synchroniser',
            why='actual closed qfd_rst_rep d->s[0]->r0; two receiving-root edges, calendar HOLD',
            calendar=rec['calendar']))
    else:
        rec['source_proof'] = 'HOLD: existing reset source proof unavailable; no synchronizer endpoint declared'
    model.setdefault('tp8_reset_tree', {})['forwarded_reset_capture'] = rec
    return rec
