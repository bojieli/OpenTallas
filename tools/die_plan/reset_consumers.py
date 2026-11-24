"""Opt-in, type-local control-reset localization onto equal-depth same-clock relays.

The emitted RTL and published tree must agree. No data ports, new flops, reset
logic, clocks or interface changes are introduced. Callers supply native reset
roles from the binder's actual k='rst' classification; names alone grant no role.
"""
import re

class ResetConsumerError(ValueError):
    pass

_ID = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*$')
_CALL = re.compile(r'(?m)^[ \t]*(?P<module>[A-Za-z_$][\w$]*)(?:[ \t]+#\((?P<params>[^\n]*)\))?[ \t]+(?P<instance>[A-Za-z_][\w]*)[ \t]*\(')

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
        name = m['instance']
        end = _close(text, m.end() - 1)
        ports = {}
        for p in re.finditer(r'\.([A-Za-z_]\w*)\s*\(', text[m.end():end]):
            lo = m.end() + p.end()
            hi = _close(text, lo - 1)
            if p[1] in ports:
                raise ResetConsumerError(f'duplicate port {name}.{p[1]}')
            ports[p[1]] = (text[lo:hi].strip(), lo, hi)
        if name in out:
            raise ResetConsumerError(f'duplicate instance {name}')
        out[name] = dict(module=m['module'], ports=ports, params=m['params'])
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
            # QC-S4Z: a mission-role consumer tap rst_n_t<k> is the gated leaf relay ot_dp_rgate[_drive] (reset AND run,
            # same release depth as a plain relay). Only the LEAF node (first step) may be one; its d is the raw parent net.
            gated_leaf = bool(c and c['module'] in ('ot_dp_rgate', 'ot_dp_rgate_drive') and net == first
                              and re.fullmatch(r'rst_n_t\d+', net) and 'run' in c['ports'])
            if not c or (c['module'] not in ('ot_dp_rrelay', 'ot_dp_rrelay_nl') and not gated_leaf):
                raise ResetConsumerError(f'{net}: not an actual registered reset relay')
            ps = c['ports']
            if any(k not in ps for k in ('clk', 'd', 'q')) or ps['clk'][0] != clock:
                raise ResetConsumerError(f'{net}: reset clock domain mismatch')
            dnet = ps['d'][0]
            if dnet != r.get('d'):
                # RLK-1108 latch form: the relay's d is its hop lockup latch q (0 cycles), whose d is the published edge
                import reset_tree
                li, lq = reset_tree.lockup_latch_names(r.get('name', ''))
                lc = calls.get(li)
                if (dnet == lq and lc and lc['module'] == 'ot_dp_lk' and all(k in lc['ports'] for k in ('clk', 'd', 'q'))
                        and lc['ports']['q'][0] == lq and lc['ports']['clk'][0] == clock):
                    dnet = lc['ports']['d'][0]
            if ps['q'][0] != net or dnet != r.get('d'):
                raise ResetConsumerError(f'{net}: emitted/published reset edge mismatch')
            net, depth = r['d'], depth + 1
        pd = published[first].get('depth')
        if isinstance(pd, bool) or not isinstance(pd, int) or pd != depth:
            raise ResetConsumerError(f'{first}: published depth differs from emitted reset path')
        # The shared root input must also be an actual relay on this same core clock.
        root = [c for c in calls.values() if c['module'] == 'ot_dp_rrelay'
                and c['ports'].get('q', (None,))[0] == 'rst_root_n']
        relay_root = (tree.get('entry') != 'sync' and len(root) == 1
                      and root[0]['ports'].get('clk', (None,))[0] == clock)
        if not relay_root:
            # QC SC die-root type: the declared synchronous-entry graph starts at
            # the canonical two-flop root synchronizer, rather than u_rst_in.
            # Both relocated branches still trace to this ONE actual same-clock
            # root. Keep the ordinary relayed-root contract unchanged.
            def driver_is(output, name):
                drivers = [n for n, v in calls.items()
                           if any(v['ports'].get(p, (None,))[0] == output for p in ('q', 'sync_rst_n'))]
                return output not in aliases and drivers == [name]

            def canonical_sync_root(name, source, output):
                c = calls.get(name)
                if not c or c['module'] != 'ot_dp_rsync_s2':
                    return False
                ps = {k: v[0] for k, v in c['ports'].items()}
                return (ps == {'clk': clock, 'async_rst_n': source, 'sync_rst_n': output}
                        and driver_is(output, name))

            def canonical_tied_hold(lock):
                from reset_tree import HOLD_TIED, LOCKQ_EXTRA
                stable = lock.get('stable')
                if (type(stable) is not int or stable < 1
                        or lock.get('stages') != stable + LOCKQ_EXTRA):
                    return False
                c = calls.get('u_rst_lockq')
                if not c or c['module'] != 'ot_dp_lockq':
                    return False
                ps = {k: v[0] for k, v in c['ports'].items()}
                param = re.fullmatch(r'\s*\.STABLE\s*\(\s*([0-9]+)\s*\)\s*', c['params'] or '')
                return (ps == {'clk': clock, 'd': 'rst_por_n', 'locked': HOLD_TIED, 'q': 'rst_root_n'}
                        and param is not None and int(param[1]) == stable
                        and driver_is('rst_root_n', 'u_rst_lockq')
                        and canonical_sync_root('u_rst_root', 'arst_n', 'rst_por_n'))

            lock = tree.get('lock') or {}
            sync_root = (tree.get('entry') == 'sync' and tree.get('sync_stages') == 2
                         and (canonical_tied_hold(lock) if lock.get('tied') is True
                              else canonical_sync_root('u_rst_root', 'arst_n', 'rst_root_n')))
            if sync_root and tree.get('start'):
                sync_root = canonical_sync_root('u_run_root', 'start_i', 'run_root')
            if not sync_root:
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
        # QC-SC-ROWS-1115: a gated tap carries reset AND run per START role; both taps must have the same published role
        troles = tree.get('tap_roles') or {}
        otap, ntap = published[old_node].get('tap'), published[new_node].get('tap')
        if troles and (troles.get(otap, troles.get(str(otap))) != troles.get(ntap, troles.get(str(ntap)))):
            raise ResetConsumerError(f'{key}: reset tap role differs between {old_node} and {new_node}')
        _, lo, hi = c['ports'][pin]
        # Retain whitespace around the connection; rewrite only the old identifier.
        raw = text[lo:hi]
        patches.append((lo, hi, raw.replace(old, new)))
        receipts.append(dict(consumer=key, old_reset=old, old_node=old_node, new_reset=new,
                             new_node=new_node, depth=old_depth, clock_net=clock, cycles_added=0))
    for lo, hi, value in sorted(patches, reverse=True):
        text = text[:lo] + value + text[hi:]
    return text, receipts
