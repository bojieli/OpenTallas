"""Opt-in physical landing-network endpoints for the die route target.

START boundary inputs are explicitly provisional. The actual registered START
provider must replace these boundaries during the infrastructure import;
this module never invents a tie, driver or timing model for them.
Boundary port names must be resolved through actual ODB BTerms before creating
an infra-replay net allowlist: a real-launch output can alias an existing net.
"""
from collections import defaultdict
import re


MONITOR_MACROS = {
    "fwd_clock_relay": "ot_landing_monitor_fwd_route",
    "die_clock_relay": "ot_landing_monitor_die_route",
}


def scalar_pins(P, tn):
    """Pin rectangles match landing_contract.io_tcl; edge inputs are tap_pins."""
    typ = P.types[tn]
    existing = {p['port'] for p in typ.get('clock', {}).get('edge_clocks', [])}
    return [p for p in typ.get('clock', {}).get('landing_contract', {}).get('pins', [])
            if p['name'] not in existing]


def monitor_route_lef(forms):
    """Route-only M7 access anchors. A mapped relay and its PDN are a separate physical gate."""
    from reach_relay_plan import FLOP_W, ROW

    lines = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    for form in sorted(forms):
        name = MONITOR_MACROS[form]
        buses = ('ready', 'fault', 'clk') if form == 'fwd_clock_relay' else ('ready', 'fault')
        width = FLOP_W * len(buses[:2]) * (2 if form == 'fwd_clock_relay' else 1)
        lines += [f'MACRO {name}', '  CLASS BLOCK ;', '  ORIGIN 0 0 ;',
                  f'  SIZE {width:.4f} BY {ROW:.4f} ;', '  SYMMETRY X Y ;']
        for direction, side in (('INPUT', 'i'), ('OUTPUT', 'o')):
            for index, bus in enumerate(buses, 1):
                x = width * index / (2 * (len(buses) + 1))
                if side == 'o':
                    x += width / 2
                pin = f'{bus}_{side}'
                use = 'CLOCK' if bus == 'clk' else 'SIGNAL'
                lines += [f'  PIN {pin}', f'    DIRECTION {direction} ;', f'    USE {use} ;',
                          '    PORT', '      LAYER M7 ;',
                          f'        RECT {x - .056:.4f} .0300 {x + .056:.4f} {ROW - .030:.4f} ;',
                          '    END', f'  END {pin}']
        lines.append(f'END {name}')
    return '\n'.join([*lines, 'END LIBRARY', ''])


def monitor_route_origin(relay):
    """Place the access anchor around the planned center on the die frame."""
    from reach_relay_plan import FLOP_W, ROW

    width = FLOP_W * (4 if relay['form'] == 'fwd_clock_relay' else 2)
    x, y = relay['xy_um']
    return x - width / 2, y - ROW / 2


def _monitor_segments(net):
    """Separate the three wires at each forwarded-clock station, as the bound RTL does."""
    from clock_landings import ident, monitor_relays

    selected = monitor_relays({'clock': {'landing_network': net}})
    by_edge = {}
    relays = {}
    for child, group in selected.items():
        stage_names = []
        for number, station in enumerate(group['relays'], 1):
            inst = f'u_cland_rl{number}_{ident(child)}'
            if inst in relays:
                raise ValueError('monitor relay identifier collision: ' + inst)
            relays[inst] = dict(form=group['form'], xy_um=station['xy_um'], relay=station.get('id'))
            if group['form'] == 'die_clock_relay':
                relays[inst]['clock_node'] = station['clock_node']
                relays[inst]['clock_node_xy_um'] = station['clock_node_xy_um']
            stage_names.append(inst)
        for bus in sorted(group['kinds']):
            by_edge[f'cland_mon_{bus}__{child}'] = (bus, stage_names)
    return by_edge, relays


def network(P):
    """Return scalar wire declarations, per-instance binds and provisional nets."""
    import landing_contract as LC
    report = LC.check(P)
    if report['errors']:
        raise ValueError('landing route target requires a valid physical contract: '+str(report['errors'][:3]))
    net = P.clock.get('landing_network') or {}
    pins = {(part, pin['name']): pin for part, instance in P.parts.items()
            for pin in P.types[instance['type']].get('clock', {}).get('landing_contract', {}).get('pins', [])}
    by_edge, relays = _monitor_segments(net) if any(edge.get('relays') for edge in net.get('edges', [])) else ({}, {})
    if set(relays) & set(P.parts):
        raise ValueError('monitor relay would collide with a partition instance')
    parent = {}
    def find(key):
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = find(parent[key])
        return parent[key]
    def union(a,b):
        ra,rb = find(a),find(b)
        if ra != rb:
            parent[max(ra,rb)] = min(ra,rb)
    edges = []
    for edge in net.get('edges', []):
        endpoints = tuple((edge[side]['part'],edge[side]['bus']) for side in ('src','dst'))
        if any(p not in pins for p in endpoints):
            raise ValueError('unknown physical landing endpoint: '+edge['id'])
        name = edge['id']
        if name not in by_edge:
            if edge.get('relays'):
                raise ValueError('unsupported physical relay edge: ' + name)
            union(*endpoints)
            edges.append((name, endpoints))
            continue
        bus, stages = by_edge[name]
        previous = endpoints[0]
        for number, inst in enumerate(stages, 1):
            input_pin = (inst, f'{bus}_i')
            output_pin = (inst, f'{bus}_o')
            pins[input_pin] = {'dir': 'in'}
            pins[output_pin] = {'dir': 'out'}
            union(previous, input_pin)
            segment_name = name if number == 1 else f'{name}_relay_{number - 1}'
            edges.append((segment_name, (previous, input_pin)))
            previous = output_pin
        union(previous, endpoints[1])
        edges.append((f'{name}_relay_{len(stages)}', (previous, endpoints[1])))
    groups = defaultdict(list)
    for key in parent:
        groups[find(key)].append(key)
    names = defaultdict(list)
    for name,endpoints in edges:
        names[find(endpoints[0])].append(name)
    bindings = defaultdict(dict)
    wires = []
    for root,endpoints in sorted(groups.items()):
        drivers = [key for key in endpoints if pins[key]['dir']=='out']
        if len(drivers) != 1:
            raise ValueError(f'landing physical net has {len(drivers)} drivers: {endpoints[:4]}')
        name = 'landing_'+re.sub(r'[^A-Za-z0-9_$]', '_', min(names[root]))
        if name in wires:
            raise ValueError('landing net identifier collision: '+name)
        wires.append(name)
        for part,pin in endpoints:
            bindings[part][pin] = name
    provisional = []
    boundary_inputs,boundary_outputs = [],[]
    boundary_aliases = {}
    for use in net.get('start_tree', {}).get('uses', []):
        part,pin,name = use['part'],use['pin'],use['net']
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',name):
            raise ValueError('invalid explicit START boundary net: '+name)
        if (part,pin) not in pins or pins[part,pin]['dir'] not in ('in','out'):
            raise ValueError('invalid START boundary endpoint: '+str((part,pin)))
        if name in wires:
            raise ValueError('START boundary conflicts with existing physical net: '+name)
        if pin in bindings[part]:
            if pins[part,pin]['dir'] != 'out':
                raise ValueError('START boundary conflicts with existing physical net: '+name)
            # One real launch can feed a real child and virtual START stages.
            # Export its existing electrical wire; never bind the output pin
            # twice or turn this real launch into an external input driver.
            boundary_aliases[name] = bindings[part][pin]
        else:
            bindings[part][pin] = name
        provisional.append(name)
        (boundary_inputs if pins[part,pin]['dir']=='in' else boundary_outputs).append(name)
    if len(set(provisional)) != len(provisional):
        raise ValueError('duplicate START provisional boundary net')
    for inst, relay in relays.items():
        relay['bindings'] = bindings.pop(inst)
    return dict(wires=wires, bindings=dict(bindings), provisional=provisional,
                **({'monitor_relays': relays} if relays else {}),
                boundary_inputs=boundary_inputs,boundary_outputs=boundary_outputs,
                boundary_aliases=boundary_aliases,
                edges=len(net.get('edges', [])), boundary_provider='actual infra import required')
