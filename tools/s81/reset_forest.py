#!/usr/bin/env python3
"""Opt-in source-bound reset forest planner; emits a candidate, never adoption.

Input ABI: model/placement/source hashes; exact reset nets (root and sink endpoint
IDs), pins {id: {xy_um, domain, clock, direction, launch_ps/capture_ps}}, and
reserved hardleaf sites {id, domain, clock, in, out, role: branch|terminal,
area_um2}. Site pins use the same pin ABI. Every terminal site names its sinks.
Explicit pair budgets include compensated phi-R clock delivery, TT setup, FF hold
and recovery/removal. Missing physical evidence fails closed. The planner cannot
turn generated centres, unknown directions, or unqualified views into proof.
"""
import argparse
from collections import Counter, deque
import hashlib
import gzip
import json
from pathlib import Path


class PlanError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise PlanError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plan(data):
    need(data.get('schema') == 's81.reset-forest.input.v1', 'unsupported reset forest ABI')
    for key in ('source_sha256', 'model_sha256', 'placement_sha256'):
        value = data.get(key, '')
        need(len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'missing source binding: ' + key)
    pins = data['pins']
    sites = data['sites']
    need(len({s['id'] for s in sites}) == len(sites), 'duplicate reserved site')
    budgets = data['domains']
    for domain, b in budgets.items():
        need(b['clock_delivery'] == 'phi_minus_R', 'uncompensated clock ' + domain)
        need(b['period_ps'] > 0 and b['setup_uncertainty_ps'] >= 60, 'invalid setup budget ' + domain)
        need(b['hold_uncertainty_ps'] >= 25 and b['max_edge_um'] <= 500, 'relaxed physical gate ' + domain)
        need(b['wire_ps_per_um'] > 0 and b['skew_ps'] >= 0, 'invalid wire/skew budget')
        need(b['max_edge_um'] > 0 and b['max_fanout'] > 0 and b['max_delay_cycles'] > 0, 'invalid physical bounds')
    for pid, pin in pins.items():
        need(pin.get('exact_placed_pin') is True, 'not an exact placed pin: ' + pid)
        need(len(pin['xy_um']) == 2, 'invalid coordinates: ' + pid)
        need(pin['direction'] in ('input', 'output'), 'unknown direction: ' + pid)
        need(pin.get('direction_source_sha256') == data['source_sha256'], 'unbound RTL pin direction: ' + pid)
        need(pin['domain'] in budgets and pin['clock'], 'missing clock/domain: ' + pid)
    need(data['nets'], 'no reset nets')
    bysite = {s['id']: s for s in sites}
    for site in sites:
        need(site['role'] in ('branch', 'terminal'), 'unknown reset site role')
    used = set()
    output = []
    all_expected, all_covered = [], []
    epochs = {}
    for net in data['nets']:
        root, sinks = net['root'], net['sinks']
        need(root in pins and sinks, 'missing root or sinks: ' + net['id'])
        need(len(set(sinks)) == len(sinks), 'duplicate sink: ' + net['id'])
        need(pins[root]['direction'] == 'output', 'root is not a qualified driver')
        need(net.get('root_release') == 'qualified_domain_edge', 'asynchronous root cannot establish fixed calendar')
        d, clock = pins[root]['domain'], pins[root]['clock']
        b = budgets[d]
        need(isinstance(net.get('root_release_cycle'), int) and net['root_release_cycle'] >= 0,
             'missing fixed root release cycle')
        need(bool(net.get('root_epoch')), 'missing compiler reset epoch')
        domain_clock = (d, clock)
        need(epochs.setdefault(domain_clock, net['root_epoch']) == net['root_epoch'],
             'unrelated reset epochs cannot share a release calendar')
        for sink in sinks:
            need(sink in pins and pins[sink]['direction'] == 'input', 'unknown/noninput sink: ' + sink)
            need((pins[sink]['domain'], pins[sink]['clock']) == (d, clock), 'reset domain/clock crossing: ' + sink)
        available = [s for s in sites if s['domain'] == d and s['clock'] == clock and s['id'] not in used]
        terminal = [s for s in available if s['role'] == 'terminal' and s.get('net') == net['id']]
        coverage = [p for s in terminal for p in s['sinks']]
        need(Counter(coverage) == Counter(sinks), 'terminal sites do not exactly cover ' + net['id'])
        for site in available:
            need(site['area_um2'] > 0 and site.get('reserved_nonoverlap') is True, 'unreserved hardleaf site ' + site['id'])
            for port, direction in (('in', 'input'), ('out', 'output')):
                p = pins[site[port]]
                need((p['domain'], p['clock'], p['direction']) == (d, clock, direction), 'site pin ABI mismatch')
        def edge(a, z):
            pa, pz = pins[a], pins[z]
            length = sum(abs(x-y) for x, y in zip(pa['xy_um'], pz['xy_um']))
            required = pa['launch_ps'] + b['wire_ps_per_um'] * length + pz['capture_ps']
            budget = b['period_ps'] - b['setup_uncertainty_ps'] - b['skew_ps']
            # Explicit measured FF/RDC checks are per source/destination pair.
            check = data['pair_checks'].get(a + '->' + z)
            good = check and check.get('source_sha256') == data['source_sha256'] and check.get('placement_sha256') == data['placement_sha256'] and min(check['ff_hold_slack_ps'], check['recovery_slack_ps'], check['removal_slack_ps']) >= 0
            return good and length <= b['max_edge_um'] and required <= budget, length, budget-required
        # Breadth-first source-rooted tree. Terminal sites cannot drive transit links:
        # their padding is independently chosen to equalize all reset release ages.
        parent, depth = {}, {}
        queue = deque([(None, root, 0)])
        while queue:
            src, pin, dep = queue.popleft()
            for site in available:
                sid = site['id']
                if sid in parent:
                    continue
                if edge(pin, site['in'])[0]:
                    parent[sid], depth[sid] = (src, pin), dep + 1
                    if site['role'] == 'branch':
                        queue.append((sid, site['out'], dep + 1))
        need(all(s['id'] in parent for s in terminal), 'unreachable terminal: ' + net['id'])
        chosen = set()
        for site in terminal:
            sid = site['id']
            while sid is not None:
                chosen.add(sid)
                sid = parent[sid][0]
        children = Counter(parent[sid][0] for sid in chosen)
        need(max(children.values(), default=0) <= b['max_fanout'], 'reset branch fanout exceeds bound')
        maxdepth = max(depth[s['id']] for s in terminal)
        # Each leaf: 2 synchronization + >=1 padding cycles. Root edge is cycle0;
        # a same-domain downstream leaf first samples the upstream release next edge.
        release_cycles = 3 * maxdepth
        nodes, edges = [], []
        for sid in sorted(chosen):
            site = bysite[sid]
            pad = 1 + (3 * (maxdepth - depth[sid]) if site['role'] == 'terminal' else 0)
            need(pad <= b['max_delay_cycles'], 'terminal delay exceeds hardened ABI')
            a = parent[sid][1]
            ok, length, slack = edge(a, site['in'])
            need(ok, 'internal unreachable edge')
            edges.append(dict(driver=a, load=site['in'], length_um=length, tt_setup_slack_ps=slack))
            nodes.append(dict(site=sid, master='ot_s81_reset_leaf', delay_cycles=pad, depth=depth[sid], domain=d, clock=clock, driver_pin=a, input_pin=site['in'], output_pin=site['out'], terminal=site['role']=='terminal'))
            if site['role'] == 'terminal':
                need(len(site['sinks']) <= b['max_fanout'], 'terminal fanout exceeds bound')
                for sink in site['sinks']:
                    ok, length, slack = edge(site['out'], sink)
                    need(ok, 'unreachable local sink: ' + sink)
                    edges.append(dict(driver=site['out'], load=sink, length_um=length, tt_setup_slack_ps=slack))
                    all_covered.append(sink)
        all_expected.extend(sinks)
        used.update(chosen)
        output.append(dict(net=net['id'], domain=d, clock=clock, sink_ids=sinks, root_pin=root, nodes=nodes, edges=edges, root_epoch=net['root_epoch'], root_release_cycle=net['root_release_cycle'], release_cycles=release_cycles+net['root_release_cycle'],
                           release_ps=(release_cycles+net['root_release_cycle'])*b['period_ps'], startup_only=True,
                           registers=sum(2+n['delay_cycles'] for n in nodes),
                           area_um2=sum(bysite[s]['area_um2'] for s in chosen)))
    # All roots in one compensated clock domain release together, including
    # independent column nets. Padding is explicit hardware at terminal leaves.
    calendars = {}
    for net in output:
        key = (net['domain'], net['clock'])
        calendars[key] = max(calendars.get(key, 0), net['release_cycles'])
    for net in output:
        cycles = calendars[(net['domain'], net['clock'])]
        extra = cycles - net['release_cycles']
        for node in net['nodes']:
            if node['terminal']:
                node['delay_cycles'] += extra
            need(node['delay_cycles'] <= budgets[net['domain']]['max_delay_cycles'], 'domain calendar exceeds hardened delay ABI')
            # Padding changes the physical master. Refuse to borrow a different
            # parameter's area/view/pins just because the RTL behavior matches.
            view = bysite[node['site']]['delay_views'].get(str(node['delay_cycles']))
            need(view is not None, 'missing exact delay-parameter hardleaf view')
            need(view['source_sha256'] == data['source_sha256'] and len(view['view_sha256']) == 64,
                 'unbound hardleaf view')
            need(view['input_pin'] == node['input_pin'] and view['output_pin'] == node['output_pin'],
                 'delay parameter changes physical pin ABI')
            node['view_sha256'] = view['view_sha256']
            node['area_um2'] = view['area_um2']
            need(0 < node['area_um2'] <= bysite[node['site']]['area_um2'], 'hardleaf exceeds reserved site area')
        net['release_cycles'] = cycles
        net['release_ps'] = cycles * budgets[net['domain']]['period_ps']
        net['cycles_from_root_release'] = cycles - net['root_release_cycle']
        net['registers'] = sum(2+n['delay_cycles'] for n in net['nodes'])
        net['area_um2'] = sum(n['area_um2'] for n in net['nodes'])
    need(Counter(all_expected) == Counter(all_covered), 'reset coverage mismatch')
    need(len(all_expected) == len(set(all_expected)), 'sink assigned to multiple reset roots')
    return dict(schema='s81.reset-forest.candidate.v1', binding={k:data[k] for k in ('source_sha256','model_sha256','placement_sha256')},
                qualification='CANDIDATE_ONLY_REQUIRES_HARDLEAF_ROUTE_AND_INTEGRATION', nets=output,
                covered_sinks=len(all_covered), added_registers=sum(n['registers'] for n in output),
                added_area_um2=sum(n['area_um2'] for n in output))


def verify_model_coverage(data, model):
    """Match ALL reset endpoints of the pinned full model, not a selected subset."""
    expected = {b[0]: b for b in model['buses'] if b[1] in ('reset', 'col_reset', 'reset_tree') and len(b[3]) > 1}
    actual = {n['id']: n for n in data['nets']}
    need(len(actual) == len(data['nets']), 'duplicate reset net')
    need(set(actual) == set(expected), 'full-model reset net coverage mismatch')
    for bid, bus in expected.items():
        n = actual[bid]
        endpoints = [data['pins'][p] for p in [n['root']] + n['sinks']]
        got = Counter((p['instance'], p['port']) for p in endpoints)
        want = Counter((e[0], e[1]) for e in bus[3])
        need(got == want, 'full-model reset endpoint coverage mismatch: ' + bid)


def emit_rtl(result):
    """Compile the candidate forest into real RTL with named boundary ports.

    Boundary index maps remain in the JSON so integration cannot silently reorder
    endpoints. This module is not a physically qualified hardleaf library.
    """
    nets = result['nets']
    sink_count = result['covered_sinks']
    lines = ['// Candidate only: route and integrate every hardleaf before adoption.',
             'module ot_s81_reset_forest_candidate(',
             f'  input wire [{len(nets)-1}:0] ck, root_rst_n,',
             f'  output wire [{sink_count-1}:0] sink_rst_n', ');']
    out_index = 0
    for i, net in enumerate(nets):
        outpins = {node['output_pin']:f'n_{i}_{j}' for j,node in enumerate(net['nodes'])}
        for j, node in enumerate(net['nodes']):
            inp = outpins.get(node['driver_pin'], f'root_rst_n[{i}]')
            wire = outpins[node['output_pin']]
            lines += [f'wire {wire};',
                      f'ot_s81_reset_leaf #(.DELAY_CYCLES({node["delay_cycles"]})) u_{i}_{j}'
                      f'(.ck(ck[{i}]), .upstream_rst_n({inp}), .local_rst_n({wire}));']
        net['sink_port_map'] = {}
        for e in net['edges']:
            if e['load'] in net['sink_ids']:
                lines += [f'assign sink_rst_n[{out_index}] = {outpins[e["driver"]]};']
                net['sink_port_map'][e['load']] = out_index
                out_index += 1
        net['clock_port_index'] = i
        net['root_port_index'] = i
    lines += ['endmodule', '']
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--rtl-out', required=True, type=Path)
    ap.add_argument('--source-manifest', required=True, type=Path)
    ap.add_argument('--model', required=True, type=Path)
    ap.add_argument('--placement', required=True, type=Path)
    args = ap.parse_args()
    data = json.loads(args.input.read_text())
    for key, path in [('source_sha256', args.source_manifest), ('model_sha256', args.model),
                      ('placement_sha256', args.placement)]:
        need(digest(path) == data[key], 'stale source binding: ' + key)
    opener = gzip.open if args.model.suffix == '.gz' else open
    with opener(args.model, 'rt') as f:
        verify_model_coverage(data, json.load(f))
    result = plan(data)
    result['leaf_rtl_sha256'] = digest(Path(__file__).resolve().parents[2] / 'rtl/dsrom_sys/s81_reset_forest/ot_s81_reset_leaf.sv')
    rtl = emit_rtl(result)
    args.rtl_out.write_text(rtl)
    result['candidate_rtl_sha256'] = digest(args.rtl_out)
    result['input_sha256'] = digest(args.input)
    args.out.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
