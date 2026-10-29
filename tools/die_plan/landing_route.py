"""Opt-in physical landing-network endpoints for the die route target.

START boundary inputs are explicitly provisional. The actual registered START
provider must replace these boundary nets during the infrastructure import;
this module never invents a tie, driver or timing model for them.
"""
from collections import defaultdict
import re


def scalar_pins(P, tn):
    """Pin rectangles match landing_contract.io_tcl; edge inputs are tap_pins."""
    typ = P.types[tn]
    existing = {p['port'] for p in typ.get('clock', {}).get('edge_clocks', [])}
    return [p for p in typ.get('clock', {}).get('landing_contract', {}).get('pins', [])
            if p['name'] not in existing]


def network(P):
    """Return scalar wire declarations, per-instance binds and provisional nets."""
    import landing_contract as LC
    report = LC.check(P)
    if report['errors']:
        raise ValueError('landing route target requires a valid physical contract: '+str(report['errors'][:3]))
    net = P.clock.get('landing_network') or {}
    pins = {(part, pin['name']): pin for part, instance in P.parts.items()
            for pin in P.types[instance['type']].get('clock', {}).get('landing_contract', {}).get('pins', [])}
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
        union(*endpoints)
        edges.append((edge['id'],endpoints))
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
    return dict(wires=wires, bindings=dict(bindings), provisional=provisional,
                boundary_inputs=boundary_inputs,boundary_outputs=boundary_outputs,
                boundary_aliases=boundary_aliases,
                edges=len(edges), boundary_provider='actual infra import required')
