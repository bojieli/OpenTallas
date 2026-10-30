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
# HEAD-BIND-4 10-27 (COORD ruling on HEAD-CORE-R13 ASK4): s81_head hd_tile position straps (row0 = the bundle's first
# local vocab row, ten = 1 used / 0 dark tile), per-instance partition straps tied at the die top (plan id_straps)
S81HD_ID_WIDTHS = {'strap_row0': 17, 'strap_ten': 1}
# OWNER 2026-10-30 00:10 decision (3)(B): a physical strap_* ALIAS over a native ID port.  The hardened master exposes
# the strap_* pin (METHODOLOGY 1.8 / sdc_lint unchanged) and wires it straight to the native ID port inside its own
# wrapper; the plan maps the logical ID onto the alias explicitly (hard core physical_id_alias {strap: native}).
# Exact (alias -> native, width, master) rows only; no name-pattern rule, no native unprefixed physical pin.
PHYSICAL_ID_ALIASES = {
    'strap_lane_lane_id': dict(native='lane_lane_id', width=11, module='ot_hbm_su_static_pgslice_lg__lane_exp0_id'),
}
# Three exact canonical SU physical aliases; 9-bit bases retain the fixed
# per-lane low two bits in their wrappers. Legacy single-master row is unchanged.
PHYSICAL_ID_ALIAS_MASTERS = {
    ('strap_lane_lane_id', 'ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691'): dict(native='lane_lane_id', width=11),
    ('strap_lane_lane_id', 'ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77'): dict(native='lane_lane_id', width=9),
    ('strap_lane_lane_id', 'ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526'): dict(native='lane_lane_id', width=9),
}

def physical_id_alias_row(port, module):
    row = PHYSICAL_ID_ALIAS_MASTERS.get((port, module))
    if row is not None:
        return dict(row, module=module)
    return PHYSICAL_ID_ALIASES.get(port)

PHYSICAL_ID_WIDTHS = {**KV_ID_WIDTHS, 'strap_tile_tid': 6, **S81HD_ID_WIDTHS, 'strap_qid': 2,
                      **{a: r['width'] for a, r in PHYSICAL_ID_ALIASES.items()}}
ID_PORTS = frozenset({'tile_id', 'tile_tid', 'map_lane_j', 'lane_lane_id', 'sidx', 'strap_lane_id', *PHYSICAL_ID_WIDTHS})


def validate_parent_id_straps(descriptor, inputs=None, pins=None, actual_module=None):
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
        if port not in PHYSICAL_ID_WIDTHS or port in seen or port in raw:
            raise ValueError(f'hard-core ID strap {port!r}: unapproved or duplicate identity port')
        seen.add(port)
        if 'note' in entry and not isinstance(entry['note'], str):
            raise ValueError(f'hard-core ID strap {port}: note must be a string')
        value = entry['value']
        if isinstance(value, str):
            import re
            width = physical_id_alias_row(port, descriptor.get('module'))['width'] if port in PHYSICAL_ID_ALIASES else PHYSICAL_ID_WIDTHS[port]
            if not re.fullmatch(str(width) + r"'[bB][01]{" + str(width) + "}", value):
                raise ValueError(f'hard-core ID strap {port}: require an exact {width}-bit binary literal')
            value = int(value.split("'", 1)[1][1:], 2)
        raw[port] = dict(width=entry['width'], value=value)
    # Exact owner-approved key-buffer position ID; never authorize a similarly
    # named data/control port on another hardware master.
    if 'strap_lane_id' in raw:
        if actual_module is not None and actual_module != 'ot_hnx_idxn_keybuf_slice':
            raise ValueError('strap_lane_id actual hardware master differs from KEYBUF contract')
        pos = descriptor.get('position_id_contract')
        if descriptor.get('module') != 'ot_hnx_idxn_keybuf_slice' or not isinstance(pos, dict):
            raise ValueError('strap_lane_id requires exact KEYBUF hardware master and position contract')
        if set(pos) != {'kind', 'pbase', 'lane'} or pos.get('kind') != 'KEYBUF_LANE_ID':
            raise ValueError('strap_lane_id requires typed KEYBUF_LANE_ID position')
        base, lane = pos['pbase'], pos['lane']
        if type(base) is not int or base not in (0, 4) or type(lane) is not int or not 0 <= lane <= 3:
            raise ValueError('KEYBUF_LANE_ID requires pbase 0/4 and lane 0..3')
        if raw['strap_lane_id'] != {'width': 3, 'value': base + lane}:
            raise ValueError('KEYBUF_LANE_ID requires exact 3-bit pbase+lane value')
    if 'strap_qid' in raw:
        ring = 'ot_hfd_coll_q2_hard_v8g__ring_ag'
        if descriptor.get('module') != ring or (actual_module is not None and actual_module != ring):
            raise ValueError('strap_qid is authorized only for the exact HBM collective RING master')
        if raw['strap_qid'] not in ({'width':2,'value':2}, {'width':2,'value':3}):
            raise ValueError('HBM collective RING strap_qid requires the native NW=2 or NE=3 identity')
    _check_physical_id_alias(descriptor, raw, actual_module)
    result = {}
    for port, contract in raw.items():
        if port not in ID_PORTS:
            raise ValueError(f'parent_id_straps: {port!r} is not an approved ID input')
        if not isinstance(contract, dict) or set(contract) != {'width', 'value'}:
            raise ValueError(f'parent_id_straps {port}: require exactly width and value')
        width, value = contract['width'], contract['value']
        if type(width) is not int or width < 1:
            raise ValueError(f'parent_id_straps {port}: width must be a positive integer')
        if port == 'sidx' and width != 3:
            raise ValueError('parent_id_straps sidx: identity width must be exactly 3 bits')
        approved_width = physical_id_alias_row(port, descriptor.get('module'))['width'] if port in PHYSICAL_ID_ALIASES else PHYSICAL_ID_WIDTHS.get(port)
        if approved_width is not None and width != approved_width:
            raise ValueError(f'parent_id_straps {port}: identity width must be exactly {approved_width} bits')
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


def _check_physical_id_alias(descriptor, raw, actual_module):
    """OWNER 10-30 (3)(B): an aliased strap is legal only with its exact explicit plan mapping on its exact master,
    and a mapping is legal only for a declared alias strap.  The native name itself is never also declared."""
    alias = descriptor.get('physical_id_alias')
    used = sorted(p for p in raw if p in PHYSICAL_ID_ALIASES)
    if alias is None:
        if used:
            raise ValueError(f'ID strap alias {used[0]} requires an explicit physical_id_alias plan mapping')
        return
    if not isinstance(alias, dict) or not alias:
        raise ValueError('physical_id_alias must be a non-empty {strap_alias: native_port} object')
    if sorted(alias) != used:
        raise ValueError(f'physical_id_alias {sorted(alias)} must map exactly the declared alias straps {used}')
    for strap, native in alias.items():
        row = physical_id_alias_row(strap, descriptor.get('module'))
        if native != row['native']:
            raise ValueError(f'physical_id_alias {strap}: native port must be exactly {row["native"]}')
        if descriptor.get('module') != row['module'] or (actual_module is not None and actual_module != row['module']):
            raise ValueError(f'physical_id_alias {strap} is authorized only on the exact master {row["module"]}')
        if native in raw:
            raise ValueError(f'physical_id_alias {strap}: native {native} must not also be declared (one ID, one pin)')


def logical_id_straps(descriptor):
    """{logical (native) ID port: {width, value}} of a descriptor: physical_id_alias straps are reported under their
    native ID name (e.g. HBM lane identity checks read lane_lane_id); everything else under its own name."""
    ids = validate_parent_id_straps(descriptor)
    alias = descriptor.get('physical_id_alias') or {}
    return {alias.get(p, p): c for p, c in ids.items()}


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


def validate_bound_id_bits(bitsv, width, expected):
    """Check only the literal bits represented by the old bound parameter.

    An ID may contain internal tie-cell/logic bits as well as literals. Those
    connections remain untouched: promoting its existing parameter to an input
    must not turn internal connections into constants or waive unknown bits.
    Unused parameter positions retain their canonical zero fill.
    """
    if not bitsv or any(type(i) is not int or not 0 <= i < width for i in bitsv):
        raise ValueError('ID parameter requires existing in-range literal bits')
    if any(not values or any(v not in ('0', '1') for v in values) for values in bitsv.values()):
        raise ValueError('ID parameter contains an unknown/nonliteral bit')
    representative = sum(int(values[0]) << i for i, values in bitsv.items())
    if representative != expected:
        raise ValueError(f'representative ID literal bits disagree with {expected}')
    return representative
