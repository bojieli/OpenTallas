"""Strict owner-approved IDs-only constants driven at a hardened block's parent.

A content or hard_core descriptor may declare::

    parent_id_straps = {"tile_id": {"width": 16, "value": 23}}

This is an input-port contract, never permission to constant-drive data, fault,
valid or control pins. Physical callers must supply their actual input inventory.
All ID pins retain normal timing and physical pin obligations.
"""

ID_PORTS = frozenset({'tile_id', 'tile_tid', 'map_lane_j', 'lane_lane_id'})


def validate_parent_id_straps(descriptor, inputs=None):
    """Return {port: {width, value}}; inputs optionally maps input names to widths.

    The caller's actual input inventory is authoritative. A missing or output
    pin must not be supplied in inputs. Empty/missing declarations are opt-out.
    """
    if not isinstance(descriptor, dict):
        raise ValueError('parent_id_straps descriptor must be an object')
    raw = descriptor.get('parent_id_straps', {})
    if not isinstance(raw, dict):
        raise ValueError('parent_id_straps must be an object')
    result = {}
    for port, contract in raw.items():
        if port not in ID_PORTS:
            raise ValueError(f'parent_id_straps: {port!r} is not an approved ID input')
        if not isinstance(contract, dict) or set(contract) != {'width', 'value'}:
            raise ValueError(f'parent_id_straps {port}: require exactly width and value')
        width, value = contract['width'], contract['value']
        if type(width) is not int or width < 1:
            raise ValueError(f'parent_id_straps {port}: width must be a positive integer')
        if type(value) is not int or value < 0 or value >= 1 << width:
            raise ValueError(f'parent_id_straps {port}: value does not fit width {width}')
        if inputs is not None and inputs.get(port) != width:
            raise ValueError(f'parent_id_straps {port}: no actual input of width {width}')
        result[port] = dict(width=width, value=value)
    return result


def type_parent_id_straps(partition_type):
    """Declarations keyed by exact bound local leaf name (descriptor inst).

    A hard-core/content pair describing the same instance must agree. Matching
    by a suffix or by module name would accidentally bless unrelated replicas.
    """
    out = {}
    for d in partition_type.get('contents', []) + partition_type.get('hard_cores', []):
        ids = validate_parent_id_straps(d)
        if not ids:
            continue
        inst = d.get('inst')
        if not isinstance(inst, str) or not inst:
            raise ValueError('parent_id_straps requires an explicit descriptor inst')
        if inst in out and out[inst] != ids:
            raise ValueError(f'parent_id_straps: conflicting declaration for {inst}')
        out[inst] = ids
    return out
