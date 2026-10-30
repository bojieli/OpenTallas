"""Opt-in, type-local control-reset localization onto equal-depth same-clock relays.

The emitted RTL and published tree must agree. No data ports, new flops, reset
logic, clocks or interface changes are introduced. Callers supply native reset
roles from the binder's actual k='rst' classification; names alone grant no role.
"""
import re

class ResetConsumerError(ValueError):
    pass

_ID = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*$')
_CALL = re.compile(r'(?m)^[ \t]*([A-Za-z_$][\w$]*)(?:[ \t]+#\([^\n]*\))?[ \t]+([A-Za-z_][\w]*)[ \t]*\(')

def _close(text, start):
    depth = 1
    for i in range(start + 1, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if not depth:
                return i
    raise ResetConsumerError('unterminated generated instance/port')

def _calls(text):
    out = {}
    for m in _CALL.finditer(text):
        end = _close(text, m.end() - 1)
        ports = {}
        for p in re.finditer(r'\.([A-Za-z_]\w*)\s*\(', text[m.end():end]):
            lo = m.end() + p.end()
            hi = _close(text, lo - 1)
            if p[1] in ports:
                raise ResetConsumerError(f'duplicate port {m[2]}.{p[1]}')
            ports[p[1]] = (text[lo:hi].strip(), lo, hi)
        if m[2] in out:
            raise ResetConsumerError(f'duplicate instance {m[2]}')
        out[m[2]] = dict(module=m[1], ports=ports)
    return out

def localize(text, declarations, tree, native_roles=None):
    """Return (RTL, receipts); empty declarations leave the bytes untouched.

    Each row is {instance,pin,old_reset,new_reset,clock_net}. Native roles are
    {"instance.pin": {"kind":"control", "clocks": {clock_pin: emitted_net}}}.
    ot_dp_st.rst_n is the generator's known epoch-control pin, never its data/ea.
    """
    if not declarations:
        return text, []
    if not isinstance(declarations, list) or not isinstance(tree, dict):
        raise ResetConsumerError('localization needs an explicit list and published reset tree')
    calls = _calls(text)
    aliases = dict(re.findall(r'\b(?:wire|assign)\s+([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*;', text))
    published = {}
    for r in tree.get('relays', []):
        q = r.get('q')
        if not isinstance(q, str) or q in published:
            raise ResetConsumerError('missing/duplicate published reset relay')
        published[q] = r
    roles = native_roles or {}
    patches, receipts, seen = [], [], set()

    def resolve(net):
        visited = set()
        while net in aliases:
            if net in visited:
                raise ResetConsumerError('reset alias cycle')
            visited.add(net)
            net = aliases[net]
        return net

    def lineage(net, clock):
        net = resolve(net)
        if net not in published:
            raise ResetConsumerError(f'unknown published reset {net}')
        first, depth, visited = net, 0, set()
        while net != 'rst_root_n':
            if net in visited or net not in published:
                raise ResetConsumerError('reset path absent/cyclic before common root')
            visited.add(net)
            r = published[net]
            c = calls.get(r.get('name'))
            if not c or c['module'] != 'ot_dp_rrelay':
                raise ResetConsumerError(f'{net}: not an actual registered reset relay')
            ps = c['ports']
            if any(k not in ps for k in ('clk', 'd', 'q')) or ps['clk'][0] != clock:
                raise ResetConsumerError(f'{net}: reset clock domain mismatch')
            if ps['q'][0] != net or ps['d'][0] != r.get('d'):
                raise ResetConsumerError(f'{net}: emitted/published reset edge mismatch')
            net, depth = r['d'], depth + 1
        pd = published[first].get('depth')
        if isinstance(pd, bool) or not isinstance(pd, int) or pd != depth:
            raise ResetConsumerError(f'{first}: published depth differs from emitted reset path')
        # The shared root input must also be an actual relay on this same core clock.
        root = [c for c in calls.values() if c['module'] == 'ot_dp_rrelay'
                and c['ports'].get('q', (None,))[0] == 'rst_root_n']
        if len(root) != 1 or root[0]['ports'].get('clk', (None,))[0] != clock:
            raise ResetConsumerError('unknown/different-clock common reset root')
        return first, depth

    required = {'instance', 'pin', 'old_reset', 'new_reset', 'clock_net'}
    for row in declarations:
        if not isinstance(row, dict) or set(row) != required or any(
                not isinstance(row[k], str) or not _ID.fullmatch(row[k]) for k in required):
            raise ResetConsumerError('localization requires five explicit canonical identifiers')
        inst, pin, old, new, clock = (row[k] for k in ('instance','pin','old_reset','new_reset','clock_net'))
        key = f'{inst}.{pin}'
        if key in seen:
            raise ResetConsumerError(f'duplicate consumer {key}')
        seen.add(key)
        c = calls.get(inst)
        if not c or pin not in c['ports']:
            raise ResetConsumerError(f'missing consumer {key}')
        if c['ports'][pin][0] != old:
            raise ResetConsumerError(f'{key}: old reset does not match emitted connection')
        if c['module'] == 'ot_dp_st' and pin == 'rst_n':
            clocks = {'clk': clock}
        else:
            role = roles.get(key, {})
            if role.get('kind') != 'control' or not isinstance(role.get('clocks'), dict) or not role['clocks']:
                raise ResetConsumerError(f'{key}: not a binder-classified control-reset consumer')
            clocks = role['clocks']
        if any(n != clock or c['ports'].get(p, (None,))[0] != clock for p, n in clocks.items()):
            raise ResetConsumerError(f'{key}: consumer clock domain mismatch')
        old_node, old_depth = lineage(old, clock)
        new_node, new_depth = lineage(new, clock)
        if old_depth != new_depth:
            raise ResetConsumerError(f'{key}: reset release depth changes {old_depth}->{new_depth}')
        _, lo, hi = c['ports'][pin]
        # Retain whitespace around the connection; rewrite only the old identifier.
        raw = text[lo:hi]
        patches.append((lo, hi, raw.replace(old, new)))
        receipts.append(dict(consumer=key, old_reset=old, old_node=old_node, new_reset=new,
                             new_node=new_node, depth=old_depth, clock_net=clock, cycles_added=0))
    for lo, hi, value in sorted(patches, reverse=True):
        text = text[:lo] + value + text[hi:]
    return text, receipts
