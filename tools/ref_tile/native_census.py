"""Mandatory post-synthesis admission; roles come from the actual loaded Liberty.

This deliberately has no threshold/waiver options. Historical route lint remains
separate. Only constant functions, actual clock pins and transparent unary cells
are special; reset and macro data pins count like other dynamic endpoints.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import textbook_lint as TL


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
            for typ, name, body in groups(body):
                if typ != 'cell':
                    continue
                pins, seq = {}, False
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
                role = {'pins': pins, 'sequential': seq}
                if name in cells and cells[name] != role:
                    raise ValueError(f'conflicting Liberty roles across corners: {name}')
                cells[name] = role
    if not receipts or not cells:
        raise ValueError('missing loaded Liberty roles')
    return cells, receipts


def census(g, roles):
    drivers, loads, ports, transparent = {}, {}, {}, {}
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
            for bit, net in enumerate(nets):
                p = (role['pins'].get(f'{pn}[{len(nets)-1-bit}]') if len(nets) > 1 else None) or role['pins'].get(pn) or role['pins'].get(TL._base(pn))
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
        d = drivers.get(source)
        provenance = ({'kind': 'liberty_function', 'instance': g.cells[d[0]][1],
                       'master': g.cells[d[0]][0], 'pin': d[1],
                       'function': roles[g.cells[d[0]][0]]['pins'][d[1]]['function']}
                      if d and d[0] != 'port' else {'kind': 'literal', 'net': g.net_name[source]})
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
    except Exception as exc:
        report.update(status='FAIL', role_errors=[f'{type(exc).__name__}: {exc}'])
    Path(a.out).write_text(json.dumps(report, indent=2) + '\n')
    print('PRE_GATE_NATIVE_CENSUS ' + report['status'] + ' report=' + a.out)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
