"""Mandatory post-synthesis admission; roles come from the actual loaded Liberty.

This deliberately has no configurable threshold/waiver options. Historical route lint remains
separate. Only constant functions, actual clock pins and transparent unary cells
are special; reset and macro data pins count like other dynamic endpoints.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import textbook_lint as TL


# COORD 2026-10-20 03:30: exactly fifteen library-adder internal nodes,
# each 34 loads, accepted at <=36. This registry admits ONLY the reviewed
# complete mapped image, actual Liberty bytes and node identities. ROOT reviewed
# a second image differing solely in complete positive-BUF instance IDs/order.
# Its fixed canonical fingerprint is the only alternative to the original SHA.
KTREE_SCOPE = 'coord-20261020-0330-ktree-15-library-adder-nodes'
KTREE_NETLIST = '6d1d28a1d58ab5088166ffb25084c552ae7810b51ee401801a55fc3434fc7cea'
KTREE_CANONICAL = '24f05e9e4e08b9590b5ce8d6e1d2b00958c5fb0fea739cd7934f7da46b5dc228'
KTREE_LIBERTY = frozenset((
    '9e3848d247f9bbc8d405ee55617af98797b6d5be9a1af02988ec5d59ca9dad99',
    'fe9f1c18e88ab129d63ad82adc256f3a85c7e38e47dabbe0a96749b41087dea1',
    'e0c65688e6067ee485b0693651298636ae9ef5a0512154bcd4b7c4914d1a0ac6',
    '8d6db2c2f83c3c162be54a5e102b2d379fcaaaef2db5f0b1d4152c395d01fea1',
    'cc9651e9235bcd29bba0737b7ba7a8afddde7462df3ff48d3870c22d05c86fb3',
    'bbe6d904d58c7367de1ed7639e4eae386c65fa0a5af26ae62dc5e4e2ec52b08b',
    'd9b6e75c8720cdd450cff15178528502cc8df34c5ab6b0ffb53fc99d664b5302',
    '57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3',
    '0c93d44fcc6a30182d71031997771ea3fc0d09235201e9252f71daf48a1c7a38',
    '073ac4b6b08f272b6953b0ad54d1d9743767a7d15a0e2964ed86cf44c3dbe00e',
))


def ktree_scoped_admission(report):
    """Verify the fixed coordinator decision, retaining the raw FAIL receipt."""
    if not isinstance(report, dict) or not isinstance(report.get('netlist'), dict):
        return False
    raw_sha = report['netlist'].get('sha256')
    if (not isinstance(raw_sha, str) or not re.fullmatch('[a-f0-9]{64}', raw_sha)
            or type(report.get('limit')) is not int
            or type(report.get('max_dynamic_loads')) is not int
            or report.get('role_errors') != []):
        return False
    if (report.get('schema') != 'opentallas.pre_gate_native_census.v1'
            or report.get('top') != 'ot_qkh_ktree_lk_nc32c'
            or (report.get('netlist', {}).get('sha256') != KTREE_NETLIST
                and report.get('netlist', {}).get('positive_buf_identity_sha256') != KTREE_CANONICAL)
            or report.get('status') != 'FAIL' or report.get('limit') != 32
            or report.get('max_dynamic_loads') != 34 or report.get('role_errors')):
        return False
    libs = report.get('liberty', [])
    if (not isinstance(libs, list) or len(libs) != len(KTREE_LIBERTY)
            or any(not isinstance(row, dict) for row in libs)
            or {row.get('sha256') for row in libs} != KTREE_LIBERTY):
        return False
    expected = {(f'u_kt.g_n[{i}].u_a.{"_6386_" if i == 14 else "_6361_"}/Y',
                 f'u_kt.g_n[{i}].u_a.{"_2981_" if i == 14 else "_2948_"}',
                 'combinational_or_macro', 34) for i in range(15)}
    rows = report.get('violations', [])
    if (not isinstance(rows, list) or len(rows) != 15
            or any(not isinstance(r, dict) or type(r.get('loads')) is not int for r in rows)):
        return False
    actual = {(r.get('driver'), r.get('net'), r.get('driver_role'), r.get('loads')) for r in rows}
    return len(rows) == 15 and actual == expected


BUF = re.compile(r'^  (BUFx\w+) (_\d+_) \(\n(.*?)\n  \);', re.M | re.S)
PIN = re.compile(r'^    \.(\w+)\(([^()]+)\)(,?)$')


def ktree_positive_buf_canonical(raw, roles):
    """Fixed-image fingerprint; only complete actual unary BUF IDs/order vary.

    All bytes outside those statements, contact bodies and multiplicities survive.
    Unsupported syntax/attributes, duplicate identities across any cell masters,
    and references to a removed identity fail closed. No general equivalence claim.
    """
    text = raw.decode()
    pieces, counts = [], []
    for module in re.split(r'(?=^module )', text, flags=re.M):
        rows, names = [], set()
        parsed = TL.parse_verilog(module)
        for mod in parsed.values():
            identities = [name for _, name, _ in mod.insts]
            if len(identities) != len(set(identities)):
                raise ValueError('duplicate instance identity across cells')

        def replace(match):
            master, instance, body = match.groups()
            if instance in names:
                raise ValueError('duplicate buffer identity')
            names.add(instance)
            prefix = module[module.rfind(';', 0, match.start()) + 1:match.start()]
            if '(*' in prefix or '*)' in prefix:
                raise ValueError('buffer attribute is unsupported; preserve its association')
            role = roles.get(master)
            if not role or role['sequential'] or role['bus_order']:
                raise ValueError('unsupported buffer master ' + master)
            pins = role['pins']
            ins = [p for p, r in pins.items() if r['direction'] == 'input']
            outs = [p for p, r in pins.items() if r['direction'] == 'output']
            if len(pins) != 2 or len(ins) != 1 or len(outs) != 1 or any(p['clock'] for p in pins.values()):
                raise ValueError('not an actual unary non-clock buffer ' + master)
            function = re.sub(r'[\s()]', '', pins[outs[0]]['function'] or '')
            if function != ins[0]:
                raise ValueError('not an actual positive BUF function ' + master)
            contacts = [PIN.fullmatch(line) for line in body.splitlines()]
            if len(contacts) != 2 or any(c is None for c in contacts):
                raise ValueError('unsupported buffer connection statement')
            if {c[1] for c in contacts} != set(pins) or contacts[0][3] != ',' or contacts[1][3]:
                raise ValueError('missing/extra/duplicate buffer contact')
            # Include master plus the COMPLETE exact contact body and multiplicity.
            # Only this statement's instance ID and position among other BUF
            # statements are omitted; net names and all non-BUF context survive.
            rows.append((master, body))
            return '  __REVIEWED_POSITIVE_BUF_STATEMENT__;'

        outside = BUF.sub(replace, module)
        # Refuse any candidate BUFx instance that did not match the supported form.
        if re.search(r'^\s+BUFx\w+\s+\S+\s*\(', outside, re.M):
            raise ValueError('unsupported BUFx statement left in context')
        if names.intersection(re.findall(r'(?<![\w$])_\d+_(?![\w$])', outside)):
            raise ValueError('buffer identity referenced outside its complete statement')
        pieces.append(outside + '\n' + json.dumps(sorted(rows), separators=(',', ':')))
        counts.append(dict(count=len(rows), masters=dict(Counter(m for m, _ in rows))))
    # Refuse hierarchical instance references even when in a parent module.
    # Escaped generated hierarchy in master/instance names is also unsupported
    # when it names a removed buffer, since its association would be ambiguous.
    removed = {m.group(2) for m in BUF.finditer(text)}
    refs = set(re.findall(r'\.\s*(_\d+_)(?![\w$])', text))
    if removed.intersection(refs):
        raise ValueError('hierarchical buffer identity reference')
    return ''.join(pieces).encode(), counts



def groups(text):
    """Immediate Liberty groups, respecting quoted strings and nested braces."""
    pat = re.compile(r'([A-Za-z_][\w]*)\s*\(([^{}]*?)\)\s*\{')
    pos = 0
    while m := pat.search(text, pos):
        start = end = m.end()
        depth, quote, escape = 1, False, False
        while end < len(text) and depth:
            c = text[end]
            if escape:
                escape = False
            elif c == '\\' and quote:
                escape = True
            elif c == '"':
                quote = not quote
            elif not quote:
                depth += (c == '{') - (c == '}')
            end += 1
        if depth:
            raise ValueError('unterminated Liberty group')
        yield m.group(1), m.group(2).strip().strip('"'), text[start:end-1]
        pos = end


def attr(text, name):
    # Remove nested groups so timing/ff attributes cannot masquerade as pin roles.
    out, depth, quote, escape = [], 0, False, False
    for c in text:
        before = depth
        if escape:
            escape = False
        elif c == '\\' and quote:
            escape = True
        elif c == '"':
            quote = not quote
        elif not quote:
            depth += (c == '{') - (c == '}')
        if before == depth == 0:
            out.append(c)
    flat = ''.join(out)
    m = re.search(r'\b' + name + r'\s*:\s*("(?:\\.|[^"\\])*"|[^;]+)\s*;', flat)
    return m.group(1).strip().strip('"') if m else None


def liberty_roles(paths):
    cells, receipts = {}, []
    for path in sorted(set(paths)):
        p = Path(path)
        raw = p.read_bytes()
        receipts.append({'path': str(p), 'sha256': hashlib.sha256(raw).hexdigest()})
        text = (gzip.decompress(raw) if p.suffix == '.gz' else raw).decode()
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
        libs = list(groups(text))
        for typ, _, body in libs:
            if typ != 'library':
                continue
            members = list(groups(body))
            types = {}
            for typ, name, tb in members:
                if typ == 'type' and attr(tb, 'bit_from') is not None and attr(tb, 'bit_to') is not None:
                    hi, lo = int(attr(tb, 'bit_from')), int(attr(tb, 'bit_to'))
                    types[name] = list(range(hi, lo + (1 if lo >= hi else -1), 1 if lo >= hi else -1))
            for typ, name, body in members:
                if typ != 'cell':
                    continue
                pins, bus_order, seq = {}, {}, False
                for kind, pn, pb in groups(body):
                    seq |= kind in ('ff', 'latch', 'ff_bank', 'latch_bank')
                    if kind not in ('pin', 'bus'):
                        continue
                    def pin_role(body, inherited=None):
                        inherited = inherited or {}
                        d = attr(body, 'direction') or inherited.get('direction')
                        if d not in ('input', 'output', 'internal', 'inout'):
                            raise ValueError(f'unsupported Liberty pin direction {name}/{pn}: {d}')
                        ck = attr(body, 'clock')
                        return {'direction': d, 'clock': ck == 'true' if ck is not None else inherited.get('clock', False),
                                'function': attr(body, 'function') or inherited.get('function')}
                    inherited = pin_role(pb)
                    pins[pn] = inherited
                    if kind == 'bus':
                        order = types.get(attr(pb, 'bus_type'))
                        if order is not None:
                            bus_order[pn] = order
                        for child_kind, child_name, child_body in groups(pb):
                            if child_kind != 'pin':
                                continue
                            pr = pin_role(child_body, inherited)
                            r = re.fullmatch(r'(.*)\[(-?\d+):(-?\d+)\]', child_name)
                            if r:
                                root, hi, lo = r.group(1), int(r.group(2)), int(r.group(3))
                                for bit in range(min(hi, lo), max(hi, lo) + 1):
                                    pins[f'{root}[{bit}]'] = pr
                            else:
                                pins[child_name] = pr
                if not pins:
                    continue
                role = {'pins': pins, 'sequential': seq, 'bus_order': bus_order}
                if name in cells and cells[name] != role:
                    raise ValueError(f'conflicting Liberty roles across corners: {name}')
                cells[name] = role
    if not receipts or not cells:
        raise ValueError('missing loaded Liberty roles')
    return cells, receipts


def census(g, roles):
    drivers, loads, ports, transparent = {}, {}, {}, {}
    output_sources, constant_sources = {}, {}
    constants = {g.find(i) for name, i in g.net_id.items() if name in ("1'0", "1'1")}
    errors = []
    for name, (direction, net) in g.ports.items():
        if direction == 'input':
            drivers[net] = ('port', name)
        elif direction == 'output':
            ports.setdefault(net, set()).add(('port', name, 0))
        else:
            errors.append(f'unsupported top port role {name}: {direction}')
    for ci, (master, name, pins) in enumerate(g.cells):
        role = roles.get(master)
        if role is None:
            errors.append(f'missing Liberty cell {master} instance {name}')
            continue
        ins, outs = [], []
        for pn, nets in pins.items():
            order = role.get('bus_order', {}).get(pn)
            if order is not None and len(order) != len(nets):
                errors.append(f'Liberty bus width mismatch {master}/{pn}: {len(order)} vs {len(nets)}')
                continue
            if order is None and len(nets) > 1:
                # Without an explicit Liberty bus type, varying indexed roles
                # cannot be safely matched to a packed Verilog connection.
                indexed = [p for name, p in role['pins'].items() if name == pn or name.startswith(pn + '[')]
                def category(p):
                    f = re.sub(r'[\s()]', '', p.get('function') or '')
                    return p['direction'], p['clock'], f if f in ('0','1',"1'b0","1'b1") else 'dynamic'
                if len({category(p) for p in indexed}) > 1:
                    errors.append(f'ambiguous packed Liberty bus roles without type order {master}/{pn}')
                    continue
            for bit, net in enumerate(nets):
                idx = order[bit] if order is not None else len(nets)-1-bit
                p = (role['pins'].get(f'{pn}[{idx}]') if len(nets) > 1 or order is not None else None) or role['pins'].get(pn) or role['pins'].get(TL._base(pn))
                if p is None:
                    errors.append(f'missing Liberty pin {master}/{pn}[{bit}] instance {name}')
                    continue
                if p['direction'] not in ('input', 'output'):
                    errors.append(f'unsupported connected Liberty pin role {master}/{pn}: {p["direction"]}')
                    continue
                if p['direction'] == 'output':
                    if net in drivers and drivers[net] != (ci, pn):
                        errors.append(f'multiple drivers net {g.net_name[net]}')
                    drivers[net] = (ci, pn)
                    outs.append((net, p['function']))
                    output_sources[net] = {'kind': 'liberty_function', 'instance': name, 'master': master,
                                           'pin': f'{pn}[{idx}]' if len(nets) > 1 or order is not None else pn,
                                           'function': p['function']}
                else:
                    ins.append((pn, net))
                    if not p['clock']:
                        loads.setdefault(net, set()).add((ci, pn, bit))
        # Truth-functional unary buffers/inverters only; no name-based exemption.
        if not role['sequential'] and len(ins) == len(outs) == 1:
            pn, src = ins[0]
            dst, function = outs[0]
            if function is not None:
                f = re.sub(r'[\s()]', '', function)
                if f in (pn, '!' + pn, '~' + pn, pn + "'"):
                    transparent[ci] = (src, dst)
        if not role['sequential']:
            for dst, function in outs:
                if function is not None and re.sub(r'[\s()]', '', function) in ('0', '1', "1'b0", "1'b1"):
                    constants.add(dst)
                    constant_sources[dst] = output_sources[dst]
    for net in loads:
        if net not in drivers and net not in constants:
            errors.append(f'undriven dynamic net {g.net_name[net]}')
    # Report constants for independent source-contract review. Packed protocol
    # fields/instance IDs may be constant; mapped topology cannot decide whether
    # a bit is a reserved field or an illegal functional tie-off.
    const_reached, todo, output_bits = set(), [(x, x, []) for x in constants], []
    while todo:
        x, source, path = todo.pop()
        if x in const_reached:
            continue
        const_reached.add(x)
        provenance = constant_sources.get(source, {'kind': 'literal', 'net': g.net_name[source]})
        for _, name, _ in ports.get(x, ()):
            output_bits.append({'port_bit': name, 'source': provenance, 'transparent_path': path})
        for ci, _, _ in loads.get(x, ()):
            if ci in transparent:
                todo.append((transparent[ci][1], source, path + [g.cells[ci][1]]))
    violations, counts, max_loads, examined = [], [], 0, 0
    for net, driver in drivers.items():
        if net in constants or driver[0] in transparent:
            continue
        seen, stack, endpoints = set(), [net], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            endpoints.update(ports.get(x, ()))
            for end in loads.get(x, ()):
                if end[0] in transparent:
                    stack.append(transparent[end[0]][1])
                else:
                    endpoints.add(end)
        n = len(endpoints)
        examined += 1
        max_loads = max(max_loads, n)
        who = driver[1] if driver[0] == 'port' else g.cells[driver[0]][1] + '/' + driver[1]
        driver_role = 'input_port' if driver[0] == 'port' else ('sequential' if roles.get(g.cells[driver[0]][0], {}).get('sequential') else 'combinational_or_macro')
        if n:
            counts.append({'driver': who, 'driver_role': driver_role, 'net': g.net_name[net], 'loads': n})
        if n > 32:
            violations.append({'driver': who, 'driver_role': driver_role, 'net': g.net_name[net], 'loads': n,
                               'endpoints': [list(e) for e in sorted(endpoints, key=str)[:40]]})
    return {'status': 'FAIL' if errors or violations else 'PASS', 'limit': 32,
            'roots_examined': examined, 'max_dynamic_loads': max_loads,
            'driver_counts': counts, 'constant_output_bits': output_bits,
            'functional_pin_contract': 'NOT_EVALUATED',
            'pin_registration_contract': 'NOT_EVALUATED', 'storage_contract': 'NOT_EVALUATED',
            'independent_source_contract_audit_required': True,
            'role_errors': errors, 'violations': violations}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--netlist', required=True)
    p.add_argument('--top', required=True)
    p.add_argument('--liberty', action='append', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    report = {'schema': 'opentallas.pre_gate_native_census.v1'}
    try:
        roles, report['liberty'] = liberty_roles(a.liberty)
        raw = Path(a.netlist).read_bytes()
        report['netlist'] = {'path': a.netlist, 'sha256': hashlib.sha256(raw).hexdigest()}
        modules = TL.parse_verilog(raw.decode())
        if a.top not in modules:
            raise ValueError(f'mapped top absent: {a.top}')
        # Mapped library-cell declarations are black boxes, not empty logic to
        # flatten away. Preserve their real Liberty contacts as endpoints.
        modules = {k: v for k, v in modules.items() if k == a.top or k not in roles}
        g, top = TL.flatten(modules, a.top)
        report['top'] = top
        report.update(census(g, roles))
        # Compute only for this reviewed source family and actual Library set.
        # Other images retain identical admission and role-error behavior.
        if (report['top'] == 'ot_qkh_ktree_lk_nc32c'
                and len(report['liberty']) == len(KTREE_LIBERTY)
                and {r['sha256'] for r in report['liberty']} == KTREE_LIBERTY):
            try:
                canonical, _ = ktree_positive_buf_canonical(raw, roles)
                report['netlist']['positive_buf_identity_sha256'] = hashlib.sha256(canonical).hexdigest()
            except ValueError as exc:
                report['netlist']['positive_buf_identity_refusal'] = str(exc)
    except Exception as exc:
        report.update(status='FAIL', role_errors=[f'{type(exc).__name__}: {exc}'])
    scoped = ktree_scoped_admission(report)
    if scoped:
        report['admission'] = {'status': 'PASS_WITH_SCOPED_WAIVER', 'authority': KTREE_SCOPE,
                               'raw_status': 'FAIL', 'waived_nodes': 15, 'global_limit': 32}
    Path(a.out).write_text(json.dumps(report, indent=2) + '\n')
    print('PRE_GATE_NATIVE_CENSUS ' + report['status'] + ' report=' + a.out)
    return 0 if report['status'] == 'PASS' or scoped else 1


if __name__ == '__main__':
    raise SystemExit(main())
