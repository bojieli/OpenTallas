"""Strict owner-approved IDs-only constants driven at a hardened block's parent.

A content or hard_core descriptor may declare::

    parent_id_straps = {"tile_id": {"width": 16, "value": 23}}

This is an input-port contract, never permission to constant-drive data, fault,
valid or control pins. Physical callers must supply their actual input inventory.
OWNER DECISION 2026-10-25 07:01 (option B) rule 2 overrides normal pin obligations for these pins: they are
quasi-static strap_* inputs, exempt from the pin register, set_false_path -from in the kit SDC, tied at the parent
with TIEHI/TIELO next to the pin (gate side: straps.py).
"""

KV_ID_WIDTHS = {'strap_corner': 2, 'strap_hid': 2, 'strap_bsel': 2}
ID_PORTS = frozenset({'tile_id', 'tile_tid', 'map_lane_j', 'lane_lane_id', *KV_ID_WIDTHS})


def validate_parent_id_straps(descriptor, inputs=None, pins=None):
    """Return {port: {width, value}}; inputs optionally maps input names to widths.

    The caller's actual input inventory is authoritative. A missing or output
    pin must not be supplied in inputs. Empty/missing declarations are opt-out.
    """
    if not isinstance(descriptor, dict):
        raise ValueError('parent_id_straps descriptor must be an object')
    raw = descriptor.get('parent_id_straps', {})
    if not isinstance(raw, dict):
        raise ValueError('parent_id_straps must be an object')
    raw = dict(raw)
    physical = descriptor.get('straps', [])
    if not isinstance(physical, list):
        raise ValueError('hard-core ID straps must be a list')
    seen = set()
    for entry in physical:
        if not isinstance(entry, dict) or not {'port','width','value'} <= set(entry) or set(entry) - {'port','width','value','note'}:
            raise ValueError('hard-core ID strap requires port, width, value and optional note')
        port = entry['port']
        if port not in KV_ID_WIDTHS or port in seen or port in raw:
            raise ValueError(f'hard-core ID strap {port!r}: unapproved or duplicate identity port')
        seen.add(port)
        if 'note' in entry and not isinstance(entry['note'], str):
            raise ValueError(f'hard-core ID strap {port}: note must be a string')
        value = entry['value']
        if isinstance(value, str):
            import re
            if not re.fullmatch(r"2'[bB][01]{2}", value):
                raise ValueError(f'hard-core ID strap {port}: require an exact two-bit binary literal')
            value = int(value[3:], 2)
        raw[port] = dict(width=entry['width'], value=value)
    result = {}
    for port, contract in raw.items():
        if port not in ID_PORTS:
            raise ValueError(f'parent_id_straps: {port!r} is not an approved ID input')
        if not isinstance(contract, dict) or set(contract) != {'width', 'value'}:
            raise ValueError(f'parent_id_straps {port}: require exactly width and value')
        width, value = contract['width'], contract['value']
        if type(width) is not int or width < 1:
            raise ValueError(f'parent_id_straps {port}: width must be a positive integer')
        if port in KV_ID_WIDTHS and width != KV_ID_WIDTHS[port]:
            raise ValueError(f'parent_id_straps {port}: identity width must be exactly two bits')
        if type(value) is not int or value < 0 or value >= 1 << width:
            raise ValueError(f'parent_id_straps {port}: value does not fit width {width}')
        if inputs is not None and inputs.get(port) != width:
            raise ValueError(f'parent_id_straps {port}: no actual input of width {width}')
        result[port] = dict(width=width, value=value)
    if pins is not None:
        import re
        names = {p if isinstance(p, str) else p[0] if isinstance(p, tuple) else p['name'] for p in pins}
        for port, contract in result.items():
            bits = {int(m.group(1)) for n in names if (m := re.fullmatch(re.escape(port) + r'\[(\d+)\]', n))}
            if contract['width'] == 1 and port in names:
                bits.add(0)
            if bits != set(range(contract['width'])):
                raise ValueError(f'parent_id_straps {port}: declared physical pins do not match its exact width')
    return result


def type_parent_id_straps(partition_type):
    """Declarations keyed by exact bound local leaf name.

    The descriptor's inst is the default. parent_id_leaf may explicitly map a
    physical name such as u_t00 to its bound local name u_t[0][0]. No guessing.
    A hard-core/content pair describing the same instance must agree. Matching
    by a suffix or by module name would accidentally bless unrelated replicas.
    """
    out = {}
    for d in partition_type.get('contents', []) + partition_type.get('hard_cores', []):
        ids = validate_parent_id_straps(d)
        if not ids:
            continue
        inst = d.get('parent_id_leaf', d.get('inst'))
        if not isinstance(inst, str) or not inst:
            raise ValueError('parent_id_straps requires an explicit bound local leaf name')
        if inst in out and out[inst] != ids:
            raise ValueError(f'parent_id_straps: conflicting declaration for {inst}')
        out[inst] = ids
    return out
