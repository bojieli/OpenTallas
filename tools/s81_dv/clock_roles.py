"""Discover forwarded clocks from bind contracts and connected source topology.

No pin-name heuristics. Native Liberty stays immutable; callers must validate
clock propagation on the actual loaded design before adopting STA evidence.
"""
BAD = {'CONST', 'Z', 'UNDECL'}

def whole_spare_frame_clock_outputs(insts, bits, masters, mod2master, directions,
                                    widths, pads, source_guard):
    """Only source-guarded selected72 frame X-chain ends may omit all xok.

    The release overlay verifies each actual u_xo0..3 forwards xk[k] to
    xok[k], and that its data chain is acyclic. Its exact per-instance output
    spare declaration is already checked by strict bind. No input, connected
    output (including partial/empty connections), or partial spare qualifies.
    """
    frames = set(source_guard.get('frame_instances', []))
    proofs = source_guard.get('frame_source_proofs', [])
    expected = {f'rtl/dsrom_sys/s81_dv/frame_lp/col_h{h}_l4_lp_rf3r.sv' for h in (9, 10)}
    if (len(frames) != 72 or {p.get('path') for p in proofs} != expected
            or any(not p.get('ref') or len(p.get('sha256', '')) != 64 for p in proofs)):
        return set()
    unused = set()
    for module, inst, _, _ in insts:
        if inst.removeprefix('u_') not in frames or module not in ('col_h9_l4_lp', 'col_h10_l4_lp'):
            continue
        tm = masters.get(mod2master.get(module, ''), {})
        if not any(r.get('ck') == 'xok' for r in tm.get('ports', {}).values() if isinstance(r, dict)):
            continue
        ent = pads.get('instances', {}).get(inst, {})
        width = widths.get(module, {}).get('xok')
        if (directions.get(module, {}).get('xok') == 'output'
                and 'xok' not in bits.get(inst, {}) and width == 4
                and ent.get('master') == module
                and ent.get('reason', '').startswith('selected72 frame X-chain end:')
                and ent.get('ports', {}).get('xok') == [[0, width - 1]]):
            unused.add((inst, 'xok'))
    return unused


def contract_clock_nets(insts, bits, masters, mod2master, directions, known, spare_frame_context=None):
    unused_outputs = set()
    if spare_frame_context is not None:
        widths, pads, source_guard = spare_frame_context
        unused_outputs = whole_spare_frame_clock_outputs(
            insts, bits, masters, mod2master, directions, widths, pads, source_guard)
    nets = set(known)
    sources, sinks = [], []
    def active(inst, port):
        return {n for n, _ in bits.get(inst, {}).get(port, []) if n not in BAD}
    def check(module, inst, port, direction):
        actual = directions.get(module, {}).get(port)
        if actual != direction:
            raise ValueError(f'clock contract {inst}.{port}: expected connected {direction}, got {actual}')
        if port not in bits.get(inst, {}):
            if direction == 'output' and (inst, port) in unused_outputs:
                return False
            raise ValueError(f'clock contract {inst}.{port}: expected connected {direction}, got {actual}')
        return True
    for module, inst, _, _ in insts:
        tm = masters.get(mod2master.get(module, ''), {})
        for row in tm.get('ports', {}).values():
            if not isinstance(row, dict):
                continue
            if row.get('ck'):
                cp = row['ck']
                if not check(module, inst, cp, 'output'):
                    continue
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
