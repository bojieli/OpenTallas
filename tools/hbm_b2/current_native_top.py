#!/usr/bin/env python3
"""Compose the released four-role IDX/VMS graph and native FUSED endpoints.

The B1 vehicle supplies the other existing leaf instances only. It does not
supply the selected IDX/VMS graph. Missing native providers become explicit
boundary ports and a FAIL_CLOSED receipt; they are never tied or aliased.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
from b2_top import Die, parse_expr


def expr(segments):
    terms = []
    for segment in reversed(segments):
        if segment[0] == 'c':
            terms.append(f"{segment[1]}'b" + ('x' * segment[1] if segment[2] == 'x' else format(segment[2], f'0{segment[1]}b')))
        else:
            terms.append(f'{segment[1]}[{segment[3]}:{segment[2]}]')
    if not terms:
        raise ValueError('empty source expression')
    return terms[0] if len(terms) == 1 else '{' + ', '.join(terms) + '}'


def compose(original, base, config, out, preserve_history=False, fused_target=None, target_audit=None, fused_lower_tree=False):
    source = Die(original, config['transport'])
    vehicle = Die(base, config['transport'])
    selected = {name for name in source.insts if name.startswith('hb_idx__') or name == 'hb_argmax' or name in {f'hb_vms_{q}' for q in ('SW', 'SE', 'NW', 'NE')}}
    if {f'hb_vms_{q}' for q in ('SW', 'SE', 'NW', 'NE')} - selected:
        raise ValueError('released source lacks one or more actual VMS roles')
    expected_roles = dict(SW='hfd_hgi_vms_glue_sw_t', SE='hfd_hgi_vms_static_SE_glue', NW='hfd_hgi_vms_glue_nw_t', NE='hfd_hgi_vms_static_NE_glue')
    for q, master in expected_roles.items():
        if source.insts[f'hb_vms_{q}']['master'] != master:
            raise ValueError('original VMS role/master contract differs: ' + q)
    history_cone = set()
    pending = list(selected)
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen: continue
        seen.add(name)
        for raw in source.insts[name]['conns'].values():
            for segment in parse_expr(raw, source.widths):
                if segment[0] != 'n': continue
                driver = source.driver.get(segment[1])
                if driver and source.is_transport(driver[0]) and driver[0] != name:
                    history_cone.add(driver[0])
                    pending.append(driver[0])
    transport_cone = history_cone if preserve_history else set()
    instances = {}
    stages = []
    # Classify outputs by the source netlist's explicit native driver identity.
    for die, names in ((vehicle, set(vehicle.insts) - selected), (source, selected | transport_cone)):
        for name in sorted(names):
            if die.is_transport(name) and name not in transport_cone:
                continue
            spec = die.insts[name]
            ports = {}
            for port, raw in spec['conns'].items():
                net = f'{name}__{port}'
                if die.driver.get(net) == (name, port) and raw == net:
                    lo, hi = die.widths[net]
                    ports[port] = dict(direction='output', width=hi - lo + 1, segments=[('n', net, lo, hi)])
                else:
                    resolved = [(segment, None) for segment in parse_expr(raw, die.widths)] if name in transport_cone else die.resolve(parse_expr(raw, die.widths))
                    segments = parse_expr(raw, die.widths) if preserve_history and die is source else [segment for segment, _ in resolved]
                    ports[port] = dict(direction='input', segments=segments)
                    stages.append(dict(instance=name, port=port, segments=resolved))
            instances[name] = dict(master=spec['master'], params=spec['params'], ports=ports,
                                   origin='released_quad' if name in selected else ('original_transport_history' if name in transport_cone else 'B1_existing_leaf_scaffold'))
    obligations = []
    original_reset_provenance = {}
    def required(name, port, width, reason):
        net = f'native_required__{name}__{port}'
        obligations.append(dict(instance=name, port=port, net=net, width=width, reason=reason))
        return dict(direction='input', segments=[('n', net, 0, width - 1)])
    for q in ('SW', 'SE', 'NW', 'NE'):
        name = 'hb_idx__s_' + q
        obj = instances[name]
        if obj['master'] != 'ot_hbm_idx_score_quarter_static':
            raise ValueError('unexpected selected scorer master: ' + name)
        clocks = [obj['ports'].pop(p) for p in ('clk_ctl', 'clk_engine', 'clk_meta', 'clk_tail', 'clk_chunk', 'clk_hslice')]
        clock_bits = {tuple(s) for clock in clocks for s in clock['segments']}
        if len(clock_bits) != 1:
            # Repeated clock vectors have repeated equal one-bit segments.
            raise ValueError('quarter clocks do not resolve to the same source bit: ' + name)
        obj['ports']['clk'] = clocks[0]
        original_reset_provenance[name] = obj['ports']['rst_n']['segments']
        obj['ports']['rst_n'] = required(name, 'rst_n', 1, 'Current die-delivered reset endpoint/offset is not bound; original POR is provenance only')
        obj['master'] = 'ot_hnx_idxn_quarter_with_keybuf'
        obj['params'] = '.TP(192), .DELIVERED_RESET(1)'
        for p, width in dict(clear=1, live_v=1, live_index=8, pre_v=1, pre_index=8, replay_v=1, replay_index=8).items():
            obj['ports'][p] = required(name, p, width, 'Current IDXN programme/calendar producer is not composed')
    clock = [('n', 'hb_ckgen__pll_stream', 0, 0)]
    reset = [('n', 'hb_ckgen__por_stream', 0, 0)]
    def inp(seg): return dict(direction='input', segments=seg)
    def output(name, port, width): return dict(direction='output', width=width, segments=[('n', f'{name}__{port}', 0, width-1)])
    root = 'u_mu_fused_root'
    original_reset_provenance[root] = reset
    ports = dict(clk=inp(clock), rst_n=required(root, 'rst_n', 1, 'Current die-delivered reset endpoint/offset is not bound; original POR is provenance only'))
    for port, width in dict(job_v=1, job=217, wsc=8, pk5=6, pb5=1).items():
        ports[port] = required(root, port, width, 'Native FUSED job/load/START provider remains unbound')
    for port, width in dict(done=1, fault=1, busy=1, down_nw=173, down_ne=173).items():
        ports[port] = output(root, port, width)
    for side in ('nw', 'ne'):
        name = 'u_mu_fused_n4_' + side
        ports['up_' + side] = inp([('n', f'{name}__uo', 0, 270)])
        original_reset_provenance[name] = reset
        node = dict(clk=inp(clock), rst_n=required(name, 'rst_n', 1, 'Current die-delivered reset endpoint/offset is not bound; original POR is provenance only'), dn=inp([('n', f'{root}__down_{side}', 0, 172)]))
        lower, n4_in = {}, {}
        if fused_lower_tree:
            # HBM-BIND-6 opt-in: the actual lower FUSED tree (16 lanes + 14 tnodes) under this n4 (fused_lower_tree.py)
            from fused_lower_tree import compose_side
            lower, n4_in = compose_side(side, clock, required, output)
        for port, width in dict(pad_k=6, pad_b=1, ua=271, ub=271).items():
            node[port] = n4_in[port] if port in n4_in else required(name, port, width, 'Actual native lower-tree/pad calendar interface remains unbound')
        for port, width in dict(uo=271, da=173, db=173).items():
            node[port] = output(name, port, width)
        instances[name] = dict(master='ot_hnx_fused_tnode', params='.LA(6), .UW(271), .DW(173), .DELIVERED_RESET(1)', ports=node, origin='native_FUSED_contract')
        instances.update(lower)
    instances[root] = dict(master='ot_hnx_fused_hub_n4ext', params='.DELIVERED_RESET(1)', ports=ports, origin='native_FUSED_contract')
    bootstrap = None
    if fused_target is not None:
        if target_audit is None: raise ValueError('explicit native target requires its namespace audit')
        if json.loads(Path(target_audit).read_text()).get('source_graph') != hashlib.sha256(Path(original).read_bytes()).hexdigest():
            raise ValueError('namespace review differs from actual released source graph')
        from native_bootstrap_bind import attach
        bootstrap = attach(instances, fused_target, target_audit, required, output)
        obligations = [entry for entry in obligations if instances[entry['instance']]['ports'][entry['port']]['segments'] == [('n', entry['net'], 0, entry['width']-1)]]
    driven = {}
    for name, obj in instances.items():
        for port, spec in obj['ports'].items():
            if spec['direction'] == 'output':
                net = spec['segments'][0][1]
                if net in driven:
                    raise ValueError('multiple native output drivers: ' + net)
                driven[net] = spec['width']
    inputs = collections.defaultdict(int)
    readers = collections.defaultdict(list)
    for name, obj in instances.items():
        for port, spec in obj['ports'].items():
            if spec['direction'] != 'input': continue
            for segment in spec['segments']:
                if segment[0] != 'n': continue
                _, net, lo, hi = segment
                readers[net].append(dict(instance=name, port=port, lo=lo, hi=hi))
                if net not in driven:
                    inputs[net] = max(inputs[net], hi + 1)
                elif hi >= driven[net]:
                    raise ValueError(f'native output width mismatch: {name}.{port} reads {net}[{hi}] width {driven[net]}')
    unresolved = [dict(net=net, width=width, readers=readers[net], source_driver=source.driver.get(net),
                       reason='explicit_control_obligation' if net.startswith('native_required__') else ('original_external_input' if source.dirs.get(net) == 'input' or vehicle.dirs.get(net) == 'input' else 'missing_native_provider'))
                  for net, width in sorted(inputs.items())]
    exposed_outputs = {net: width for net, width in driven.items() if not readers[net]}
    lines = ['// Generated current native composition candidate. FAIL_CLOSED until native obligations bind.', '`default_nettype none',
             'module hbm_current_native_top (' + ', '.join(sorted(inputs) + sorted(exposed_outputs)) + ');']
    lines.extend(f'  input wire [{width-1}:0] {net};' for net, width in sorted(inputs.items()))
    lines.extend(f'  output wire [{width-1}:0] {net};' for net, width in sorted(exposed_outputs.items()))
    lines.extend(f'  wire [{width-1}:0] {net};' for net, width in sorted(driven.items()) if net not in exposed_outputs)
    for name, obj in sorted(instances.items()):
        par = ' #(' + obj['params'] + ')' if obj['params'] else ''
        lines.append(f'  {obj["master"]}{par} {name} (\n' + ',\n'.join(f'    .{port}({expr(spec["segments"])})' for port, spec in obj['ports'].items()) + '\n  );')
    lines += ['endmodule', '`default_nettype wire']
    out.mkdir(parents=True, exist_ok=False)
    (out / 'hbm_current_native_top.sv').write_text('\n'.join(lines) + '\n')
    history = [dict(instance=path['instance'], port=path['port'],
        original_depths=sorted({depth for _, depth in path['segments']}),
        status='MISSING_CURRENT_PLAN_STATION_AND_CALENDAR_REALIZATION')
        for path in stages if path['instance'] in selected and any(depth != 0 for _, depth in path['segments'])]
    report = dict(schema='opentallas.hbm.current_native_composition.v1', status='FAIL_CLOSED_NATIVE_PROVIDERS_MISSING',
        original_sha256=hashlib.sha256(Path(original).read_bytes()).hexdigest(), base_sha256=hashlib.sha256(Path(base).read_bytes()).hexdigest(),
        instances=len(instances), selected_released_instances=sorted(selected), vms_roles=expected_roles, quarter_count=4,
        quarter_sram_count=68, fused_packet_links=4, fused_packet_bits=888, unresolved_boundary=unresolved,
        transport_history_obligations=history, current_plan_station_binding_ledger=[],
        original_history_realization='ORIGINAL_TRANSPORT_RTL_RETAINED' if preserve_history else 'COLLAPSED_HISTORY_MISSING',
        retained_transport_instances=sorted(transport_cone),
        original_parameters_provenance={name: source.insts[name]['params'] for name in sorted(selected)},
        native_bootstrap_binding=bootstrap, obligations=obligations, original_reset_provenance=original_reset_provenance, unconsumed_native_outputs=sorted(exposed_outputs),
        **(dict(fused_lower_tree='HBM-BIND-6 opt-in: 2 x (16 ot_hnx_fused_lane + 14 ot_hnx_fused_tnode) under the n4 nodes, wired as ot_hnx_fused_tree_top N4EXT=1') if fused_lower_tree else {}),
        scope='Source candidate only. Existing non-IDX/VMS B1 leaves remain historical scaffold pending current full-native review. No geometry, boot, LEC, P&R or timing qualification.')
    (out / 'composition.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'resolved_source_paths.json').write_text(json.dumps(stages) + '\n')
    (out / 'native_instance_manifest.json').write_text(json.dumps(instances, indent=2) + '\n')
    history_nets = {segment[1] for name in selected | history_cone for raw in source.insts[name]['conns'].values() for segment in parse_expr(raw, source.widths) if segment[0] == 'n'}
    history_contract = dict(schema='opentallas.hbm.native_transport_history.v1',
        source_sha256=report['original_sha256'], status='ORIGINAL_SOURCE_CONTRACT_NOT_CURRENT_CALENDAR',
        source_module=source.top, current_plan_binding_ledger=[],
        selected_original_instances={name: source.insts[name] for name in sorted(selected)},
        transport_instances={name: dict(source.insts[name], stages=source.stages(name), rule=source.trule(name)) for name in sorted(history_cone)},
        widths={net: source.widths[net] for net in sorted(history_nets)},
        drivers={net: source.driver.get(net) for net in sorted(history_nets)},
        authority='Original clock/reset expressions and forwarded clock ports are retained literally; current delivered-reset/epoch bindings remain separate obligations.')
    (out / 'transport_history_contract.json').write_text(json.dumps(history_contract, indent=2) + '\n')
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for p in ('original', 'base', 'asbuilt', 'out'): ap.add_argument(p, type=Path)
    ap.add_argument('--preserve-history', action='store_true', help='retain exact original transport RTL cone for selected imported inputs; still no current-plan/calendar qualification')
    ap.add_argument('--fused-target', type=lambda value: int(value,0), help='explicit reviewed target byte; omitted means bootstrap remains unbound')
    ap.add_argument('--target-audit', type=Path, help='exact namespace review required with --fused-target')
    ap.add_argument('--fused-lower-tree', action='store_true', help='opt-in (HBM-BIND-6): compose the actual lower FUSED tree (lanes + lower tnodes) under the two n4 nodes; default output unchanged')
    a = ap.parse_args()
    report = compose(a.original, a.base, json.loads(a.asbuilt.read_text()), a.out, a.preserve_history, a.fused_target, a.target_audit, a.fused_lower_tree)
    print(json.dumps({k: report[k] for k in ('status', 'instances', 'quarter_count', 'quarter_sram_count', 'fused_packet_bits')}))
    print('EXPLICIT_BOUNDARY_PORTS', len(report['unresolved_boundary']))


if __name__ == '__main__': main()
