"""Typed parameters of a physical wrapper, separate from native leaf parameters.

The functional bind keeps the native body. The physical kit must consume every
obligation after its existing exact native-core swap, or fail closed.
"""
import hashlib
import json
import re

SCOPE = 'kit_macro_rtl'
# Explicit supported wrapper contract, not a guessed instance-name exception.
# IDLE_UCK selects the accepted NL idle clock consumer; the logical bind has all
# native clock entries on one net, so this is a physical clock choice, no cycles.
PARAMETERS = {'qfd_tile_nl_a0c': {'IDLE_UCK': {0, 1}}}


def spec(core):
    scope = core.get('params_scope', 'bound_leaf')
    if scope not in ('bound_leaf', SCOPE):
        raise ValueError(f"hard core {core['inst']}: unknown params_scope {scope}")
    if scope != SCOPE:
        return None
    from kit_core_clocks import NATIVE_CORE_BODY
    master = core.get('module')
    if master not in NATIVE_CORE_BODY or master not in PARAMETERS:
        raise ValueError(f"kit_macro_rtl {core['inst']}: no typed wrapper contract for {master}")
    values = core.get('params')
    if not isinstance(values, dict) or not values:
        raise ValueError(f"kit_macro_rtl {core['inst']}: nonempty params required")
    for name, value in values.items():
        if name not in PARAMETERS[master] or type(value) is not int or value not in PARAMETERS[master][name]:
            raise ValueError(f"kit_macro_rtl {core['inst']}: unsupported {master}.{name}={value!r}")
    return master, NATIVE_CORE_BODY[master], dict(values)


def obligation(ctx, partition, core):
    selected = spec(core)
    if selected is None:
        raise ValueError('kit_macro_rtl obligation needs an explicit scope')
    master, native, values = selected
    part = next(p for p in ctx.plan['partitions'] if p['name'] == partition)
    typ = part['type']
    contents = [c for c in ctx.plan['partition_types'][typ].get('contents', [])
                if c.get('inst') == core['inst']]
    if len(contents) != 1 or not contents[0].get('parent_id_leaf'):
        raise ValueError(f"kit_macro_rtl {partition}.{core['inst']}: one explicit contents.parent_id_leaf required")
    rel = contents[0]['parent_id_leaf']
    hit = [ci for ci in ctx.members.get(partition, []) if ctx.rel_of(ci) == rel]
    if len(hit) != 1:
        raise ValueError(f"kit_macro_rtl {partition}.{core['inst']}: declared native leaf {rel} binds {len(hit)} leaves")
    cell = ctx.F.cells[hit[0]]
    if cell.module != native:
        raise ValueError(f"kit_macro_rtl {partition}.{core['inst']}: native module {cell.module}, expected {native}")
    return dict(schema='opentallas.kit_macro_rtl.obligation.v1', scope=SCOPE, partition=partition,
                type=typ, inst=core['inst'], module=master, native_module=native,
                native_rel=rel, leaf=cell.path, params=values, cycles_changed=0)


def validate(ctx, rows):
    expected = []
    for part in ctx.plan.get('partitions', []):
        for core in ctx.plan['partition_types'][part['type']].get('hard_cores', []):
            if spec(core) is not None:
                expected.append(obligation(ctx, part['name'], core))
    sort = lambda xs: sorted(xs, key=lambda r: (r['partition'], r['inst']))
    if sort(rows) != sort(expected):
        raise ValueError('kit_macro_rtl: missing, duplicate or changed physical-wrapper obligation')
    return sort(expected)


def apply(bound, typ, type_spec, partitions, obligations, swaps, leaf_id):
    """Consume the bind obligation on the exact physically swapped instance."""
    selected = [c for c in type_spec.get('hard_cores', []) if spec(c) is not None]
    if not selected:
        if any(r.get('type') == typ for r in obligations):
            raise ValueError(f'kit_macro_rtl {typ}: stale obligation without a scoped core')
        return bound, []
    names = {p['name'] for p in partitions if p['type'] == typ}
    rows = [r for r in obligations if r.get('type') == typ]
    expected = {(p, c['inst']) for p in names for c in selected}
    keys = [(r.get('partition'), r.get('inst')) for r in rows]
    if not names or len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError(f'kit_macro_rtl {typ}: missing or duplicate bind obligation')
    receipt = []
    for core in selected:
        master, native, values = spec(core)
        records = [r for r in rows if r['inst'] == core['inst']]
        content = [c for c in type_spec.get('contents', []) if c.get('inst') == core['inst']]
        rel = content[0].get('parent_id_leaf') if len(content) == 1 else None
        for row in records:
            if (row.get('schema') != 'opentallas.kit_macro_rtl.obligation.v1' or row.get('scope') != SCOPE
                    or row.get('module') != master or row.get('native_module') != native
                    or row.get('native_rel') != rel or row.get('params') != values or row.get('cycles_changed') != 0):
                raise ValueError(f"kit_macro_rtl {typ}.{core['inst']}: physical identity differs from bind obligation")
        matches = [r for r in swaps if r.get('inst') == core['inst'] and r.get('module') == master
                   and r.get('native_module') == native and r.get('native_leaf') == leaf_id(rel)]
        if len(matches) != 1 or matches[0].get('cycles_changed') != 0:
            raise ValueError(f"kit_macro_rtl {typ}.{core['inst']}: exact native-wrapper swap not proved")
        pattern = re.compile(r'^([ \t]+)' + re.escape(master) + r'[ \t]+' + re.escape(core['inst']) + r'[ \t]*\(', re.M)
        hits = list(pattern.finditer(bound))
        if len(hits) != 1:
            raise ValueError(f"kit_macro_rtl {typ}.{core['inst']}: expected one physical wrapper, got {len(hits)}")
        hit = hits[0]
        params = '#(' + ', '.join(f'.{k}({v})' for k, v in values.items()) + ')'
        bound = bound[:hit.start()] + f"{hit.group(1)}{master} {params} {core['inst']} (" + bound[hit.end():]
        receipt.append(dict(inst=core['inst'], module=master, params=values, native_rel=rel,
                            source_bind_changed=False, cycles_changed=0,
                            obligations_sha256=hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()))
    return bound, receipt
