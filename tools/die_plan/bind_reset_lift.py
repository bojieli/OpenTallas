"""Explicit wiring for approved hierarchical reset lifts into unchanged data leaves."""


def connections(binder, type_name, partition, tree, error):
    """Return per-leaf extra reset ports and consumed (planned instance,pin) targets.

    Manifest slot order is the lifted input-vector order. Every slot must resolve
    uniquely to a declared physical core reset; neither a basename nor a module
    name alone can choose a replica. Source helper receipts approve only external
    parent distribution replacement, never the private core reset implementation.
    """
    specs = binder.ab.get('reset_lifts', {})
    result, consumed = {}, set()
    planned = {(x['inst'], x['pin']): x for x in tree.get('core_resets', [])}
    core_modules = {x['inst']: x['module'] for x in binder.types[type_name].get('hard_cores', [])}
    for ci in binder.members[partition]:
        cell = binder.F.cells[ci]
        spec = specs.get(cell.module)
        if spec is None:
            continue
        port = spec.get('port', 'ot_core_rst_n')
        enable = spec.get('enable_parameter', spec.get('enable', 'OT_HIER_RST'))
        slots = spec.get('targets', [])
        interface = binder.lift_interfaces.get((cell.ytype, cell.module), {})
        declared = interface.get('ports', {}).get(port, {})
        if declared.get('direction') != 'input' or len(declared.get('bits', [])) != len(slots) or not slots:
            raise error(f'reset lift {cell.path}.{port}: declared input width does not match {len(slots)} targets')
        if enable not in interface.get('parameters', {}):
            raise error(f'reset lift {cell.path}: missing explicit enable parameter {enable}')
        supplied = cell.ports.get(port, [])
        if any(bit != 'x' for bit in supplied):
            raise error(f'reset lift {cell.path}.{port}: source already supplies a real connection')
        exprs, targets = [], []
        for slot in slots:
            if slot.get('source_role') != 'external_distribution':
                raise error(f'reset lift {cell.path}: private or unknown reset source role')
            nested, pin = slot['inst'], slot['pin']
            candidates = [key for key in planned if key[1] == pin and
                          (key[0] == nested or key[0].endswith('.' + nested)) and
                          core_modules.get(key[0]) == slot['module']]
            if len(candidates) != 1:
                raise error(f'reset lift {type_name}/{cell.path}/{nested}.{pin}: expected one planned core, found {len(candidates)}')
            key = candidates[0]
            if key in consumed:
                raise error(f'reset lift {type_name}/{key}: target delivered more than once')
            consumed.add(key)
            exprs.append(f"rst_n_t{planned[key]['tap']}")
            targets.append(dict(inst=key[0], pin=key[1], tap=planned[key]['tap']))
        result[ci] = dict(port=port, enable=enable, expression='{' + ', '.join(reversed(exprs)) + '}', targets=targets)
    return result, consumed
