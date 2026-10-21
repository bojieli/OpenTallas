"""Discover forwarded clocks from bind contracts and connected source topology.

No pin-name heuristics. Native Liberty stays immutable; callers must validate
clock propagation on the actual loaded design before adopting STA evidence.
"""
BAD = {'CONST', 'Z', 'UNDECL'}

def contract_clock_nets(insts, bits, masters, mod2master, directions, known):
    nets = set(known)
    sources, sinks = [], []
    def active(inst, port):
        return {n for n, _ in bits.get(inst, {}).get(port, []) if n not in BAD}
    def check(module, inst, port, direction):
        actual = directions.get(module, {}).get(port)
        if actual != direction or port not in bits.get(inst, {}):
            raise ValueError(f'clock contract {inst}.{port}: expected connected {direction}, got {actual}')
    for module, inst, _, _ in insts:
        tm = masters.get(mod2master.get(module, ''), {})
        for row in tm.get('ports', {}).values():
            if not isinstance(row, dict):
                continue
            if row.get('ck'):
                cp = row['ck']; check(module, inst, cp, 'output')
                root = tm.get('clk')
                if not root:
                    raise ValueError(f'clock source {inst}.{cp}: no declared input clock')
                check(module, inst, root, 'input')
                sources.append((inst, cp, active(inst, root), active(inst, cp)))
            if row.get('ck_in'):
                cp = row['ck_in']; check(module, inst, cp, 'input')
                sinks.append((inst, cp, active(inst, cp)))
    pending = sources[:]
    while pending:
        rest = []
        changed = False
        for inst, cp, roots, outputs in pending:
            if roots and roots <= nets:
                nets |= outputs; changed = True
            else:
                rest.append((inst, cp, roots, outputs))
        if not changed:
            raise ValueError('unreached declared clock source: ' + ', '.join(f'{i}.{p}' for i,p,_,_ in rest))
        pending = rest
    for inst, cp, inputs in sinks:
        missing = inputs - nets
        if missing:
            raise ValueError(f'clock input {inst}.{cp} missing clock source: {sorted(missing)[:4]}')
    return nets, [(inst, cp) for inst, cp, inputs in sinks if inputs]
