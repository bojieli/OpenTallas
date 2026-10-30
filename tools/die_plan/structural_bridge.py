"""Expand a qualified, parameter-free wire/constant source bridge before Graph.

The caller owns source selection and functional qualification. This helper accepts
an actual bind_elab.Flat fragment, not a list of requested output constants. It
permits one physical leaf, wires and source-declared known constants only. The
original logical ABI remains connected to the same global nets. No RTL is emitted
or patched here and no state, stage or transport is inferred.
"""
from collections import defaultdict


class StructuralBridgeError(ValueError):
    pass


def _abi(ports, dirs):
    return {p: {'dir': dirs[p], 'width': len(bits)} for p, bits in ports.items()}


def expand(F, path, fragment, *, expected_module, expected_abi, physical, Cell):
    """Atomically replace one old leaf with the exact flattened source fragment.

    expected_abi is {port:{dir,width}} from the current native cut. physical is
    {module, relative_path, abi, params}, describing the actual physical child.
    Both old and child must be parameter-free. Return an explicit event receipt.
    """
    def fail(message):
        raise StructuralBridgeError(f'{path}: {message}')

    matches = [c for c in F.cells if c.path == path]
    if len(matches) != 1:
        fail('expected exactly one existing native leaf')
    old = matches[0]
    if old.kind != 'leaf' or old.module != expected_module or old.params:
        fail('old module/kind/parameters differ from the current native descriptor')
    if _abi(old.ports, old.dirs) != expected_abi:
        fail('old native ABI differs from the explicit descriptor')
    frag_abi = {p: {'dir': d, 'width': len(bs)} for p, (d, bs) in fragment.top_ports.items()}
    if frag_abi != expected_abi:
        fail('source bridge does not preserve the full native ABI')
    if any(x['dir'] not in ('input', 'output') or x['width'] < 1 for x in expected_abi.values()):
        fail('only nonempty input/output ports are supported')
    if len(fragment.cells) != 1:
        fail('source bridge must contain exactly one physical leaf and no glue/state')
    child = fragment.cells[0]
    if (child.kind != 'leaf' or child.module != physical['module'] or
            child.path != physical['relative_path'] or child.params or physical.get('params', {})):
        fail('physical child module/path/parameters differ from the descriptor')
    if _abi(child.ports, child.dirs) != physical['abi']:
        fail('physical child ABI differs from the descriptor')
    child_path = path + '.' + child.path
    if any(c.path == child_path for c in F.cells):
        fail('physical child path already exists')

    # Check actual source coverage before allocating any global IDs. A constant
    # written only in metadata cannot manufacture a source for an undriven bit.
    drivers = defaultdict(list)
    inputs = set()
    for p, (direction, bits) in fragment.top_ports.items():
        if direction == 'input':
            if any(not isinstance(b, int) for b in bits):
                fail('source bridge input is not an ordinary input net')
            inputs.update(bits)
    for p, bits in child.ports.items():
        if child.dirs[p] == 'output':
            for b in bits:
                if not isinstance(b, int):
                    fail('physical child output is a literal')
                drivers[b].append(p)
    for net, (value, _) in fragment.const_drivers.items():
        if value not in ('0', '1'):
            fail('unknown source constants are unsupported')
        drivers[net].append('source constant')
    for p, bits in child.ports.items():
        if child.dirs[p] != 'input':
            continue
        for b in bits:
            if isinstance(b, str):
                if b not in ('0', '1'):
                    fail(f'{p}: physical input uses an unknown source literal')
            elif len(drivers.get(b, ())) + (b in inputs) != 1:
                fail(f'{p}: physical input has missing or multiple source drivers')
    for p, (direction, bits) in fragment.top_ports.items():
        if direction != 'output':
            continue
        for b in bits:
            if isinstance(b, str):
                if b not in ('0', '1'):
                    fail(f'{p}: unknown or undriven source output')
            elif len(drivers.get(b, ())) + (b in inputs) != 1:
                fail(f'{p}: source output has missing or multiple drivers')
    if any(len(v) > 1 or (v and n in inputs) for n, v in drivers.items()):
        fail('source fragment contains multiple drivers')

    local = {}
    constants = {}
    constant_ports = []
    def canonical(b):
        return F.find(b) if isinstance(b, int) and b < len(F.parent) else b
    def declare_const(global_net, value, where):
        global_net = canonical(global_net)
        if isinstance(global_net, str):
            if global_net != value:
                fail('source output constant conflicts with an existing literal')
            return
        if global_net in constants and constants[global_net][0] != value:
            fail('source constants conflict after ABI remapping')
        constants[global_net] = (value, where)

    for p, (direction, bits) in fragment.top_ports.items():
        for i, (b, old_net) in enumerate(zip(bits, old.ports[p])):
            old_net = canonical(old_net)
            if isinstance(b, str):
                declare_const(old_net, b, f'{path}.{p}[{i}] source bridge')
                constant_ports.append([p, i, b])
            elif b in local and local[b] != old_net:
                fail('source port alias would join distinct original nets')
            else:
                local[b] = old_net

    # Public output constants replace the old leaf's driver, never an unrelated
    # driver's value. Reject existing constants/input drivers/other leaf outputs.
    top_inputs = {canonical(b) for d, bs in F.top_ports.values() if d == 'input' for b in bs}
    other_outputs = {canonical(b) for c in F.cells if c is not old
                     for p, bs in c.ports.items() if c.dirs.get(p) == 'output' for b in bs}
    for n in constants:
        if n in F.const_drivers or n in top_inputs or n in other_outputs:
            fail('new source constant would create a multiple driver')
    next_id = len(F.parent)
    allocated = {}
    def remap(b):
        if isinstance(b, str):
            if b not in ('0', '1'):
                fail('physical child uses an unknown/undriven literal')
            return b
        if b in local:
            return local[b]
        if b not in allocated:
            allocated[b] = next_id + len(allocated)
        return allocated[b]
    ports = {p: [remap(b) for b in bs] for p, bs in child.ports.items()}
    for n, (value, where) in fragment.const_drivers.items():
        declare_const(remap(n), value, f'{path}.{where} source bridge')
    for n in constants:
        if n < next_id and (n in F.const_drivers or n in top_inputs or n in other_outputs):
            fail('imported source constant would create a multiple driver')
    new = Cell(child_path, child.module, {}, ports, dict(child.dirs), 'leaf',
               ytype=child.ytype, yparams=dict(child.yparams or {}))
    # Commit after every descriptor, source and connectivity check has passed.
    if allocated:
        assert F.new(len(allocated)) == next_id
    F.cells = [new if c is old else c for c in F.cells]
    F.const_drivers.update(constants)
    F.dissolved[path] = expected_module
    return dict(inst=path, native_module=expected_module, physical_child=child_path,
                physical_module=child.module, logical_ports=len(expected_abi),
                physical_ports=len(ports), public_constant_bits=constant_ports,
                imported_constant_nets=len(constants), new_internal_nets=len(allocated),
                extra_cycles=0, source_fragment_only=True)


def apply(binder, descriptors, base):
    """Load frozen source fragments and commit a complete optional source event.

    Each descriptor has json/json_sha256/top/source_files_sha256 and instances.
    Instance fields are path/expected_module/expected_abi/physical. File hashes
    are source identity checks, not a substitute for functional qualification.
    No subprocess or re-elaboration occurs in this reader.
    """
    import copy
    import hashlib
    import json
    import re
    from pathlib import Path
    import bind_elab as E

    if descriptors is None:
        return []
    if not isinstance(descriptors, list):
        raise StructuralBridgeError('structural_bridges must be a list')
    if not descriptors:
        return []
    base = Path(base)
    def filename(value):
        if not isinstance(value, str) or not value:
            raise StructuralBridgeError('source paths must be nonempty strings')
        p = Path(value)
        return p if p.is_absolute() else base / p
    def frozen(value, digest):
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise StructuralBridgeError('source SHA256 must be64 lowercase hex digits')
        p = filename(value)
        try:
            data = p.read_bytes()
        except OSError as exc:
            raise StructuralBridgeError(f'cannot read frozen source {p}: {exc}') from exc
        if hashlib.sha256(data).hexdigest() != digest:
            raise StructuralBridgeError(f'frozen source identity differs: {p}')
        return p, data
    loaded = []
    seen = set()
    rtl = []
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise StructuralBridgeError('source descriptor must be an object')
        sources = descriptor.get('source_files_sha256')
        if not isinstance(sources, dict) or not sources:
            raise StructuralBridgeError('frozen source files are required')
        resolved = {str(filename(n).resolve()): frozen(n, h)[0] for n, h in sources.items()}
        path, data = frozen(descriptor['json'], descriptor['json_sha256'])
        yjs = json.loads(data)
        top = descriptor['top']
        if not isinstance(top, str) or top not in yjs.get('modules', {}):
            raise StructuralBridgeError('fragment top is not in the exact Yosys JSON')
        fragment = E.flatten(yjs, top)
        instances = descriptor.get('instances')
        if not isinstance(instances, list) or not instances:
            raise StructuralBridgeError('exact source instance descriptors are required')
        for instance in instances:
            if not isinstance(instance, dict) or not isinstance(instance.get('path'), str) or not instance['path']:
                raise StructuralBridgeError('instance path must be an exact string')
            name = instance['path']
            if name in seen:
                raise StructuralBridgeError(f'duplicate source bridge instance: {name}')
            seen.add(name)
            physical = instance['physical']
            if physical.get('rtl_file'):
                p = filename(physical['rtl_file'])
                if str(p.resolve()) not in resolved:
                    raise StructuralBridgeError('physical RTL file must have frozen source identity')
                rtl.append(str(p))
            loaded.append((fragment, instance, str(path), descriptor['json_sha256'], top))
    # One bad later instance must not partially mutate the live composition.
    candidate = copy.deepcopy(binder.F)
    receipts = []
    for fragment, instance, path, digest, top in loaded:
        receipt = expand(candidate, instance['path'], fragment,
                         expected_module=instance['expected_module'],
                         expected_abi=instance['expected_abi'],
                         physical=instance['physical'], Cell=E.Cell)
        receipt.update(fragment_json=path, fragment_json_sha256=digest, fragment_top=top)
        receipts.append(receipt)
    binder.F = candidate
    for path in dict.fromkeys(rtl):
        if path not in binder.extra_lib:
            binder.extra_lib.append(path)
    binder.structural_bridge_receipt = receipts
    return receipts
