#!/usr/bin/env python3
"""Audit actual reset-repeater taps in an emitted Qwen die or slice.

Root release edges MUST be declared, never inferred equal across domains. This
produces a strap repair proposal; it does not modify a netlist or certify a lane
whose physical write phase is absent from its simulation model.
"""
import argparse
import hashlib
import json
import re
from lane_groups import safe_land_reset_cycles
from pathlib import Path

# QK-LANDEN 10-19: a one-frame lane's landing (qfd_landh0, no stations) registers en on ck_s before its clock gate, so
# its write epoch is the source release G + 1 (tools/qwen_split/lane_groups.py HOP0_EN_REG; the same value).
# RLYH0-EN 10-19: the multi-frame lanes' hop-0 station (qfd_rlyh0) registers en the same way: +1 for EVERY data lane.
HOP0_EN_REG = 1


def audit(netlist, lanes, roots):
    instances = {}
    drivers = {}
    aliases = {}
    for line in netlist.splitlines():
        match = re.match(r'\s*(\w+)\s+(?:#\(.*?\)\s+)?(\w+)\s+\(', line)
        if match:
            master, name = match.groups()
            ports = dict(re.findall(r'\.(\w+)\((\w+)\)', line))
            instances[name] = master, ports
            if master in ('qfd_rst_rep', 'qfd_rst_rep_p8'):
                for port in ('q0', 'q1'):
                    if port in ports:
                        drivers[ports[port]] = ports['d'], 10 if master.endswith('_p8') else 2
        match = re.match(r'\s*assign\s+(\w+)(?:\[0:0\])?\s*=\s*(\w+)(?:\[0:0\])?\s*;', line)
        if match:
            aliases[match[1]] = match[2]

    def release(net, seen=()):
        if net in seen:
            raise ValueError(f'reset cycle at {net}')
        if net in roots:
            return int(roots[net])
        if net in drivers:
            parent, cost = drivers[net]
            return cost + release(parent, (*seen, net))
        if net in aliases:
            return release(aliases[net], (*seen, net))
        raise ValueError(f'undeclared reset root {net}; supply its measured/compiled release edge')

    rows = []
    for row in lanes['lanes']:
        if row.get('lane') == 'reset' or row['landing'] not in instances:
            continue
        first = (row.get('stations') or [row['landing']])[0]
        if first not in instances:
            raise ValueError(f'{row["bid"]}: source epoch station absent')
        _, source = instances[first]
        sink_master, sink = instances[row['landing']]
        g, r0 = release(source['en']), release(sink['rs'])
        reset_cycles = safe_land_reset_cycles(row, sink_master)
        r0 += reset_cycles
        g += int(reset_cycles != 0)
        g += HOP0_EN_REG              # hop-0 en registered before the gate (landh0 QK-LANDEN, rlyh0 RLYH0-EN): epoch G + 1
        k = (int(row['E']) + g - r0) % 8
        rows.append(dict(bid=row['bid'], landing=row['landing'], E=row['E'], E_sta=row['E_sta'],
                         n=row['n'], G=g, R0=r0, calendar=g-r0, K_before=row['K'], K=k,
                         changed=k != row['K'],
                         simulation_phase_gap=int(row['E_sta']) < 2))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--netlist', type=Path, required=True)
    p.add_argument('--lanes', type=Path, required=True)
    p.add_argument('--root-release', type=Path, required=True, help='JSON net -> release edge in common root-edge units')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    rows = audit(a.netlist.read_text(), json.loads(a.lanes.read_text()), json.loads(a.root_release.read_text()))
    rec = dict(schema='opentallas.qwen.reset-calendar-audit.v1',
               scope='Reset strap proposal only; physical lane phase and full-die root calendar remain required',
               sources={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.netlist,a.lanes,a.root_release)},
               checked=len(rows), changed=sum(r['changed'] for r in rows), lanes=rows)
    a.out.write_text(json.dumps(rec, indent=2)+'\n')
    print(f"RESET_CALENDAR checked {rec['checked']} changed {rec['changed']}")



def finalize_model(model, root_release=None):
    """Re-strap only after the final reset tree exists.

    root_release maps 'instance.output_port' to its fixed release edge. Unknown
    roots are symbolic: they cancel only when BOTH endpoints trace to the same
    root. Distinct unknown roots refuse generation rather than assume G=R0.
    Clock roots must share the compiler's integer edge calendar; any phase
    residual is already included in each lane's E_sta.
    """
    root_release = root_release or {}
    masters = {i.name: i.master for i in model['insts']}
    incoming = {}
    for _, _, bits, eps in model['buses']:
        if bits == 1 and eps:
            for endpoint in eps[1:]:
                endpoint = (endpoint[0], endpoint[1].lstrip('*'))
                incoming[endpoint] = tuple(eps[0])

    def trace(endpoint, seen=()):
        endpoint = tuple(endpoint)
        key = '.'.join(endpoint)
        if key in root_release:
            return '__declared_calendar__', int(root_release[key])
        if endpoint in seen:
            raise ValueError(f'reset calendar cycle at {key}')
        master = masters.get(endpoint[0])
        if master in ('qfd_rst_rep', 'qfd_rst_rep_p8') and endpoint[1] in ('q0', 'q1'):
            root, edge = trace((endpoint[0], 'd'), (*seen, endpoint))
            return root, edge + (10 if master.endswith('_p8') else 2)
        if endpoint in incoming:
            return trace(incoming[endpoint], (*seen, endpoint))
        return key, 0

    proposals = []
    for row in model.get('fwd_lanes', {}).get('lanes', []):
        if row.get('lane') == 'reset':
            continue
        first = (row.get('stations') or [row['landing']])[0]
        gr, g = trace((first, 'en'))
        g += HOP0_EN_REG              # hop-0 en registered before the gate (landh0 QK-LANDEN, rlyh0 RLYH0-EN): epoch G + 1
        rr, r0 = trace((row['landing'], 'rs'))
        reset_cycles = safe_land_reset_cycles(row, masters.get(row['landing']))
        r0 += reset_cycles
        g += int(reset_cycles != 0)
        if gr != rr:
            raise ValueError(f"{row['bid']}: undeclared reset-root relationship {gr} vs {rr}; "
                             'OT_SPLIT_RESET_RELEASE must declare both fixed release edges')
        proposals.append((row, g, r0, (int(row['E']) + g-r0) % 8, gr, reset_cycles))
    # Validate every relationship before mutating any strap.
    drop = {f"ftk_{row['bid']}_{pol}" for row, _, _, _, _, _ in proposals for pol in ('hi', 'lo')}
    buses = [b for b in model['buses'] if b[0] not in drop]
    for row, g, r0, k, gr, reset_cycles in proposals:
        name = row['landing']
        for pol, value in (('hi', 1), ('lo', 0)):
            pins = [(name, f'k{bit}') for bit in range(3) if ((k >> bit) & 1) == value]
            if pins:
                buses.append((f"ftk_{row['bid']}_{pol}", 'constant', 1, [(name, f'tie_{pol}')] + pins))
        row.update(K=k, cal=g-r0, safe_land_reset_cycles=reset_cycles, G_reset_tree=g, R0_reset_tree=r0,
                   reset_calendar_root=gr, K_basis='post-reset-tree: (total E + G - R0) mod 8'
                   + ' with G + 1 (hop-0 en registered: landh0 QK-LANDEN, rlyh0 RLYH0-EN)'
                   + ('; G + 1 write epoch, R0 + 2 receiver reset (safe300 landing)' if row.get('safe_land_reset_cycles') else ''))
    model['buses'] = buses
    if proposals:
        model['fwd_lanes']['reset_calendar_finalized'] = True


if __name__ == '__main__':
    main()
