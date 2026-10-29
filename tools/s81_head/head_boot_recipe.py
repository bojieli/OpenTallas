#!/usr/bin/env python3
"""Compile the actual HEAD boot bindings and source programme into dated frames.

This is a source recipe, not a token or physical gate. No TEST date, link age,
identity, rank or START producer is supplied by default. Missing production
authority and mission-reset transport paths remain explicit blockers.
"""
import argparse
import json
import re
from pathlib import Path

from head_start_contract import compile_contract

PARAMETERS = ('LOCAL_STAGE', 'LOCAL_RANK', 'PHASE_BOUND', 'CLOCK_RESET_ID',
              'BOOT_HEADER_EDGE', 'BOOT_COMMIT_EDGE')


def number(value):
    if isinstance(value, int):
        return value
    text = str(value).replace('_', '')
    m = re.fullmatch(r"(?:\d+)?'([hHbBdDoO])([0-9a-fA-F]+)", text)
    if m:
        return int(m[2], {'h': 16, 'b': 2, 'd': 10, 'o': 8}[m[1].lower()])
    return int(text, 0)


def defaults(source):
    values = {}
    for name in PARAMETERS:
        m = re.search(r'\b' + name + r'\s*=\s*([^,\n)]+)', source)
        if not m:
            raise ValueError(f'HOST source has no explicit default for {name}')
        values[name] = number(m[1].strip())
    return values


def provider(plan, module):
    matches = []
    for part in plan['partitions']:
        typ = plan['partition_types'][part['type']]
        for content in typ.get('contents', []):
            if content.get('module') == module:
                matches.append((part, typ, content))
    if len(matches) != 1:
        raise ValueError(f'expected one selected {module} provider; found {len(matches)}')
    return matches[0]


def boot_routes(plan, host, ctl):
    """Select actual ingress/config routes by provider interfaces, not type names."""
    ports = {p['id']: p for p in plan['ports']}
    parts = {p['name']: p for p in plan['partitions']}
    routes = []
    wanted = {(host, 'coll_i0'), (host, 'coll_i1')}
    for lane in plan['lanes']:
        rows = [ports[n] for n in lane['ports']]
        ingress = any((r['dst']['part'], r['dst']['bus']) in wanted for r in rows)
        config = any(r['src'] == {'part': host, 'bus': 'h_rx_o'} for r in rows)
        if not (ingress or config):
            continue
        if config and not any(r['dst'] == {'part': ctl, 'bus': 'h_rx_i'} for r in rows):
            raise ValueError('selected HOST config route does not reach the selected CTL')
        names = sorted({r[side]['part'] for r in rows for side in ('src', 'dst') if r[side]['part'] in parts})
        held = []
        for name in names:
            typ = plan['partition_types'][parts[name]['type']]
            role = 'raw_hard_reset' if typ.get('hard') else typ.get('reset', {}).get('start_role', 'mission')
            if role == 'mission':
                used = {r[side]['bus'] for r in rows for side in ('src', 'dst') if r[side]['part'] == name}
                reset = typ.get('reset', {})
                contents = {c['inst'] for c in typ.get('contents', [])}
                leaves = {b.get('leaf', '').split('.')[0] for b in typ.get('buses', []) if b['name'] in used} & contents
                missing_buses = sorted(used - set(reset.get('bootstrap_buses', [])))
                missing_contents = sorted(leaves - set(reset.get('bootstrap_contents', [])))
                if missing_buses or missing_contents:
                    held.append({'part': name, 'type': parts[name]['type'], 'role': role,
                                 'missing_bootstrap_buses': missing_buses,
                                 'missing_bootstrap_contents': missing_contents})
        routes.append({'lane': lane['id'], 'purpose': 'config' if config else 'HBC ingress',
                       'ports': [r['id'] for r in rows], 'parts': names,
                       'mission_reset_blockers': held,
                       'literal_payload_motion': 'NOT INFERRED: ot_dp_st payload may advance with epoch held low; actual PHY/valid/epoch consumption needs RTL measurement',
                       'plan_cycles': plan.get('latency', {}).get('lanes', {}).get(lane['id'], {}).get('cycles')})
    if len([r for r in routes if r['purpose'] == 'HBC ingress']) != 2 or len([r for r in routes if r['purpose'] == 'config']) != 1:
        raise ValueError('expected the two real HOST ingress routes and one HOST-to-CTL config route')
    return routes


def compile_recipe(plan, offsets, source_defaults, programme=None):
    symbolic = compile_contract(plan, offsets)
    roles = sorted(tn for tn, typ in plan['partition_types'].items()
                   if typ.get('reset', {}).get('start_role') == 'bootstrap')
    if offsets.get('start', {}).get('bootstrap_types') != roles:
        raise ValueError('published offset bootstrap roles differ from the selected plan')
    hp, ht, hc = provider(plan, 'ot_s81hd_host_ep_core')
    cp, ct, _ = provider(plan, 'ot_s81hd_ctl_core')
    params = dict(source_defaults)
    params.update({k: number(v) for k, v in hc.get('params', {}).items() if k in PARAMETERS})
    blockers = []
    for part, typ in ((hp, ht), (cp, ct)):
        if typ.get('reset', {}).get('start_role') != 'bootstrap':
            blockers.append(f"{part['name']}: provider cannot configure before START (not bootstrap)")
    good = (0 <= params['LOCAL_STAGE'] < 241 and 0 <= params['LOCAL_RANK'] < 4 and
            params['PHASE_BOUND'] != 0 and 0 < params['CLOCK_RESET_ID'] < 1 << 64 and
            0 <= params['BOOT_HEADER_EDGE'] < (1 << 48) - 1 and
            params['BOOT_HEADER_EDGE'] + 6 < params['BOOT_COMMIT_EDGE'] < (1 << 48) - 1)
    if not good:
        blockers.append('selected HOST binding has an invalid HBC production profile; bind real stage/rank/phase/clock identity/header/commit values')
    routes = boot_routes(plan, hp['name'], cp['name'])
    for route in routes:
        if route['mission_reset_blockers']:
            blockers.append(f"{route['lane']}: pre-START {route['purpose']} route lacks an explicit raw-reset/epoch transport contract")
    result = {'kind': 'HEAD_PRODUCTION_BOOT_SOURCE_RECIPE', 'status': 'BLOCKED',
              'host_part': hp['name'], 'ctl_part': cp['name'], 'host_params': params,
              'explicit_host_params': hc.get('params', {}), 'routes': routes,
              'host_reset_release': offsets['parts'][hp['name']]['release'],
              'ctl_reset_release': offsets['parts'][cp['name']]['release'],
              'symbolic_contract': dict(parts={n: symbolic['parts'][n] for n in (hp['name'], cp['name'])},
                                        partition_count=len(symbolic['parts']), element_GO=symbolic['element_GO'],
                                        die_START_edge_status=symbolic['die_START_edge_status']),
              'blockers': blockers, 'frames': [],
              'scope': 'source dates/frames only; HBC payload/CRC, RTL, physical and token gates remain separate',
              'steady_state_cycles_added': 0}
    required = ['start.producer and start.die_edge (actual die START authority)',
                'host_boot_counter_zero_global_edge (actual reset/clock phase identity)',
                'transport.peer_to_hbc_input, peer_to_host_frame, peer_to_ctl_csr_apply, hbc_commit_to_context_valid, peer_frame_period',
                'hbc_records: three real {receive_edge,payload} records from the native image compiler',
                'config: plen,glen,group,rbase,issue_offset,issue_period,merge_deadline',
                'csr_apply_edges: actual compiler dates for CSR0,1,2,3,4,8,9,10']
    result['required_production_inputs'] = required
    if not programme:
        blockers.append('production programme/START authority not supplied; TEST501/505/511/750 are not defaults')
        return result
    try:
        start = programme['start']; producer = start['producer']; S = number(start['die_edge'])
        if not producer or 'job_active' in producer.lower() or producer.upper().startswith('TEST'):
            raise ValueError('START requires its actual producer; CTL job_active is downstream of START, not a producer')
        zero = number(programme['host_boot_counter_zero_global_edge'])
        if zero < result['host_reset_release']:
            raise ValueError('HOST boot counter origin precedes published reset release')
        tr = {k: number(programme['transport'][k]) for k in
              ('peer_to_hbc_input', 'peer_to_host_frame', 'peer_to_ctl_csr_apply', 'hbc_commit_to_context_valid', 'peer_frame_period')}
        if any(v < 0 for v in tr.values()) or tr['peer_frame_period'] == 0:
            raise ValueError('negative transport age')
        cfg_path = next(r for r in routes if r['purpose'] == 'config')['plan_cycles']
        if cfg_path is None or tr['peer_to_ctl_csr_apply'] < cfg_path:
            raise ValueError('CSR transport contract omits actual HOST-to-CTL plan stages')
        records = programme['hbc_records']
        dates = [params['BOOT_HEADER_EDGE'], params['BOOT_HEADER_EDGE'] + 4, params['BOOT_COMMIT_EDGE']]
        if [number(r['receive_edge']) for r in records] != dates:
            raise ValueError('native HBC record dates differ from actual bound HOST parameters')
        frames = []
        for record, date in zip(records, dates):
            payload = number(record['payload'])
            if not 0 <= payload < 1 << 512:
                raise ValueError('HBC payload must be exactly within 512 bits')
            launch = zero + date - tr['peer_to_hbc_input']
            if launch < 0:
                raise ValueError('HBC launch precedes the selected reset/clock origin')
            frames.append({'lane': 0, 'launch_global_edge': launch, 'hbc_receive_edge': date,
                           'frame553': f'{((1 << 552) | (payload << 16) | 7):0139x}'})
        for index, opcode in ((0, 0), (2, 1)):
            payload = number(records[index]['payload'])
            field = lambda lo, width: (payload >> lo) & ((1 << width) - 1)
            target_date = dates[1] if index == 0 else dates[2]
            if (field(0, 32) != 0x31434248 or field(32, 4) != 1 or field(36, 4) != opcode or
                field(40, 8) != params['LOCAL_STAGE'] or field(48, 2) != params['LOCAL_RANK'] or
                field(114, 64) != params['CLOCK_RESET_ID'] or field(242, 48) != target_date):
                raise ValueError('HBC payload identity/date differs from actual HOST binding; envelope relocation alone is invalid')
        cfg = {k: number(programme['config'][k]) for k in
               ('plen', 'glen', 'group', 'rbase', 'issue_offset', 'issue_period', 'merge_deadline')}
        limits = {'plen': 21, 'glen': 21, 'group': 4, 'rbase': 17,
                  'issue_offset': 16, 'issue_period': 16, 'merge_deadline': 16}
        if any(not 0 <= value < 1 << limits[k] for k, value in cfg.items()) or not cfg['issue_period'] or not cfg['merge_deadline']:
            raise ValueError('CSR value out of actual provider field range, or zero period/deadline')
        # Every rank has a distinct physical die and row range. The CTL rank
        # CSR defaults to zero: HBC addressing does not configure it. Omitting
        # CSR2 silently tags rank1..3 BEST/RESULT records as rank0.
        values = {0: cfg['plen'], 1: cfg['glen'], 2: params['LOCAL_RANK'], 3: cfg['group'], 4: cfg['rbase'],
                  8: 1, 9: (cfg['issue_offset'] << 16) | cfg['issue_period'], 10: cfg['merge_deadline']}
        mode=programme['config'].get('mode','ar')
        if mode=='mtp':
            values[5]=number(programme['config']['mtp_result_mtag'])
            if not 0 <= values[5] < 1<<16:
                raise ValueError('actual MTP RESULT/DHRES mtag must fit CSR5')
        elif mode!='ar' or cfg['glen']!=0:
            raise ValueError('AR entry needs glen0; MTP requires explicit CSR5 RESULT/DHRES tag')
        seen = S + offsets['parts'][cp['name']]['release']
        context = zero + params['BOOT_COMMIT_EDGE'] + tr['hbc_commit_to_context_valid']
        apply_dates = {address: number(programme['csr_apply_edges'][str(address)]) for address in values}
        if apply_dates[8] <= max(value for address, value in apply_dates.items() if address != 8):
            raise ValueError('CSR8 run must follow all configuration writes (it releases the MTP sequencer)')
        for address, value in values.items():
            applied = apply_dates[address]
            launch = applied - tr['peer_to_ctl_csr_apply']
            if applied >= seen or launch < 0 or launch + tr['peer_to_host_frame'] <= context:
                raise ValueError(f'CSR{address}: must reach context-valid HOST and settle before delivered CTL START')
            frames.append({'lane': 1, 'launch_global_edge': launch, 'csr_apply_global_edge': applied,
                           'csr_address': address, 'csr_value': value,
                           'frame553': f'{((1 << 552) | (value << 24) | (address << 16) | 6):0139x}'})
        for lane in (0, 1):
            edges = sorted(r['launch_global_edge'] for r in frames if r['lane'] == lane)
            if any(b - a < tr['peer_frame_period'] for a, b in zip(edges, edges[1:])):
                raise ValueError('source frame launches violate the declared peer transport period')
        result.update(start=dict(producer=producer, die_edge=S, ctl_seen_edge=seen),
                      first_issue_global_edge=seen + cfg['issue_offset'],
                      issue_period=cfg['issue_period'], merge_deadline=cfg['merge_deadline'],
                      frames=sorted(frames, key=lambda r: (r['launch_global_edge'], r['lane'])))
    except (KeyError, TypeError, ValueError) as error:
        blockers.append(f'production programme: {error}')
    if not blockers:
        result['status'] = 'TEST_RECIPE' if programme.get('test_only') else 'SOURCE_RECIPE_READY'
    else:
        result['frames'] = []
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path); ap.add_argument('offsets', type=Path)
    ap.add_argument('--host-source', type=Path, default=Path(__file__).resolve().parents[2] / 'rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv')
    ap.add_argument('--programme', type=Path); ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error('fresh output path required; preserve prior verdicts')
    recipe = compile_recipe(json.loads(args.plan.read_text()), json.loads(args.offsets.read_text()),
                            defaults(args.host_source.read_text()), json.loads(args.programme.read_text()) if args.programme else None)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(recipe, indent=2) + '\n')
    print(recipe['status'], 'blockers', len(recipe['blockers']), 'frames', len(recipe['frames']))
    return 2 if recipe['status'] == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
