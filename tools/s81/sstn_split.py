"""Exact two-leaf slot-station graph expansion. Requires real bound child views."""
from collections import Counter
import copy
import hashlib
import json
import re
from pathlib import Path

BASE_PORTS = dict(ck=('input',1), rs=('input',1), cci=('input',15), xai=('input',283),
                  xbi=('input',266), c0=('input',2), c1=('input',2), e0=('input',2),
                  e1=('input',2), si=('input',2), nf=('input',1), cc=('output',15),
                  xa=('output',283), xb=('output',266), so=('output',2))
PAYLOAD_PORTS = dict(ck=('input',1), rs=('input',1), i=('input',536), o=('output',536))


def _source_abis(leaves):
    root = Path(__file__).resolve().parents[2]
    result = {}
    for key, expected in (('base', BASE_PORTS), ('payload', PAYLOAD_PORTS)):
        master = leaves[key]['master']
        if master != ('ot_s81_sstn_base566' if key == 'base' else 'ot_s81_sstn_payload536'):
            raise ValueError('SSTN split unsupported source master: ' + master)
        path = root / 'rtl/dsrom_sys/s81_static_net' / (master + '.sv')
        text = re.sub(r'//[^\n]*|/\*.*?\*/', '', path.read_text(), flags=re.S)
        header = re.search(r'\bmodule\s+' + master + r'\s*\((.*?)\);', text, re.S)
        if not header:
            raise ValueError('SSTN split missing actual source header: ' + master)
        ports = {}
        for m in re.finditer(r'\b(input|output)\b(.*?)(?=\binput\b|\boutput\b|$)', header[1], re.S):
            width = re.search(r'\[(\d+)\s*:\s*(\d+)\]', m[2])
            width = abs(int(width[1]) - int(width[2])) + 1 if width else 1
            names = re.findall(r'\b[A-Za-z_]\w*\b', re.sub(r'\[[^]]*\]', '', m[2]))
            for name in names:
                if name not in ('wire', 'reg', 'logic', 'signed'):
                    ports[name] = (m[1], width)
        if ports != expected:
            raise ValueError('SSTN split actual source ABI differs: ' + master)
        result[key] = dict(master=master, ports=ports, source=str(path.relative_to(root)),
                           sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return result


def _terminals(buses, selected):
    """Exact used terminal bits; source widths are separate from this census."""
    terminals = Counter()
    used = {}
    seen = {}
    for bi, (bid, cls, width, eps) in enumerate(buses):
        if not isinstance(width, int) or width <= 0:
            raise ValueError('SSTN mixed/invalid bus width: ' + str(bid))
        for j, (name, port) in enumerate(eps):
            if name not in selected:
                continue
            m = re.fullmatch(r'([^\[\]@]+)(?:\[(\d+)(?::(\d+))?\])?(?:@(\d+))?', port)
            if not m:
                raise ValueError(f'SSTN unsupported endpoint {name}.{port} on {bid}')
            base, lo, hi, offset = m.groups()
            lo = int(lo) if lo is not None else 0
            hi = int(hi) if hi is not None else (lo if '[' in port else width - 1)
            offset = int(offset) if offset is not None else None
            direction = 'output' if j == 0 and cls != 'top_in' else 'input'
            if cls == 'phy_dfi' or hi < lo or (offset is None and hi - lo + 1 != width) or \
                    (offset is not None and (direction != 'input' or offset + hi - lo + 1 > width)):
                raise ValueError(f'SSTN mixed-width/direction endpoint {name}.{port} on {bid}, bus width {width}')
            terminal = (name, base)
            prior = seen.setdefault(terminal, [])
            for old_lo, old_hi, old_direction, old_bid, old_bi in prior:
                if max(lo, old_lo) > min(hi, old_hi):
                    continue
                # One source output can fan out to several original nets. An
                # input connected twice or an output also used as a load is ambiguous.
                if direction != old_direction or direction != 'output' or old_bid == bid:
                    raise ValueError(f'SSTN duplicate active terminal {name}.{base}[{max(lo,old_lo)}] on {old_bid} and {bid}')
            prior.append((lo, hi, direction, bid, bi))
            terminals[(bi, name, base, lo, hi, offset or 0, direction)] += 1
            old = used.setdefault(name, {}).setdefault(base, dict(direction=direction, ranges=[]))
            if old['direction'] != direction:
                raise ValueError(f'SSTN mixed direction {name}.{base}')
            old['ranges'].append((lo, hi))
    return terminals, used


def expand(model, usage, mapping, views):
    """Atomically conserve active bits; unused ABI outputs acquire no invented nets."""
    if model.get('sstn_split'):
        return False
    if model.get('bound_views'):
        raise ValueError('expand SSTN source before view binding, never rewrite a completed physical model')
    if mapping.get('schema') != 's81-sstn-two-leaf-map-v1':
        raise ValueError('unknown SSTN split map schema')
    leaves = mapping['leaves']; roles = {r['logical_parent']: r for r in mapping['roles']}
    if len(roles) != len(mapping['roles']):
        raise ValueError('duplicate SSTN role')
    source_abis = _source_abis(leaves)
    for key, size in [('base', (84.24, 30.24)), ('payload', (86.4, 25.92))]:
        leaf = leaves[key]; view = views.get(leaf['master'])
        if not view:
            raise ValueError('SSTN split requires a real bound view: ' + leaf['master'])
        if tuple(leaf['outline']) != size or abs(view['w'] - size[0]) > 1e-6 or abs(view['h'] - size[1]) > 1e-6:
            raise ValueError('SSTN split actual child outline differs from granted map')
    if leaves['base']['origin'] != [0, 0] or leaves['payload']['origin'] != [86.4, 0] or mapping['parent_outline'] != [172.8, 30.24]:
        raise ValueError('SSTN split changes granted parent envelope')
    selected = {i.name for i in model['insts'] if i.kind == 'sstn' and 'x2i' in usage.get(i.name, {})}
    before, incident = _terminals(model['buses'], selected)
    replacements = {}; prepared = []; straps = {}; records = []
    names = {i.name for i in model['insts']}
    abi = dict(BASE_PORTS, x2i=('input', 536), x2=('output', 536))
    for inst in model['insts']:
        if inst.name not in selected:
            continue
        ports = usage.get(inst.name, {})
        role = 'dsfd_sstn_' + ''.join(k for k in ('e0', 'e1', 'c0', 'c1', 'si', 'nf', 'qt') if k in ports) + '_x2'
        absent_outputs = sorted(p for p, (d, _) in abi.items() if d == 'output' and p not in ports)
        context = f'instance={inst.name} role={role} absent_outputs={absent_outputs}: '
        spec = roles.get(role)
        if spec is None or model.get('sstn_ccpad', {}).get(inst.name):
            raise ValueError(context + 'unsupported SSTN split role or padded calendar')
        if inst.orient != 'R0' or abs(inst.w - 172.8) > .025 or abs(inst.h - 30.24) > .025:
            raise ValueError(context + 'SSTN split needs current R0 172.8x30.24 slot')
        actual = incident.get(inst.name, {})
        if set(actual) != set(ports):
            raise ValueError(context + 'SSTN incident used-port census differs from usage: ' +
                             str(dict(only_incident=sorted(set(actual)-set(ports)), only_usage=sorted(set(ports)-set(actual)))))
        for port, signature in ports.items():
            signature = tuple(signature)
            if port not in abi:
                raise ValueError(context + 'unknown live port ' + port)
            direction, width = signature; expected_direction, source_width = abi[port]
            ranges = actual[port]['ranges']
            if direction != expected_direction or width <= 0 or width > source_width or \
                    (direction == 'input' and width != source_width):
                raise ValueError(context + 'SSTN source ABI mismatch: ' + port)
            if actual[port]['direction'] != direction or max(hi for lo,hi in ranges) + 1 != width:
                raise ValueError(context + 'SSTN incident width/direction differs from usage: ' + port)
            if direction == 'input' and (min(lo for lo,hi in ranges) != 0 or sum(hi-lo+1 for lo,hi in ranges) != source_width):
                raise ValueError(context + 'SSTN dropped required input bit: ' + port)
        if ports.get('x2i') != ('input', 536):
            raise ValueError(context + 'SSTN split payload input ABI mismatch')
        allowed = spec['base_role_straps']
        actual_missing = {p for p, (d, _) in BASE_PORTS.items() if d == 'input' and p not in ports}
        if set(allowed) != actual_missing:
            raise ValueError(context + 'SSTN role straps would mask an active or unlisted required input')
        for port, literal in allowed.items():
            if not re.fullmatch(r"[12]'b0+", literal) or int(literal.split("'")[0]) != BASE_PORTS[port][1]:
                raise ValueError(context + 'SSTN role strap is not exact-width zero')
        base = copy.copy(inst); payload = copy.copy(inst); payload.name = inst.name + '__payload'
        if payload.name in names:
            raise ValueError(context + 'duplicate SSTN payload instance')
        names.add(payload.name)
        if hasattr(inst, 'power_w'):
            base.power_w = inst.power_w * 566 / 1102
            payload.power_w = inst.power_w - base.power_w
        payload.master = leaves['payload']['master']; payload.kind = 'sstn_split_payload'
        payload.x = inst.x + 86.4; payload.w, payload.h = 86.4, 25.92
        base.master = leaves['base']['master']; base.kind = 'sstn_split_base'; base.w, base.h = 84.24, 30.24
        prepared.append((inst, base, payload)); replacements[inst.name] = payload.name; straps[inst.name] = dict(allowed)
        records.append(dict(instance=inst.name, payload=payload.name, role=role, neutral_input_ports=dict(allowed),
                            absent_unused_outputs=absent_outputs,
                            used_output_ranges={p: sorted(set(a['ranges'])) for p, a in actual.items() if a['direction'] == 'output'}))
    if not replacements:
        raise ValueError('SSTN split selected no x2 stations')
    new_buses = []
    for bid, cls, bits, endpoints in model['buses']:
        out = []
        for name, port in endpoints:
            payload = replacements.get(name)
            if not payload:
                out.append((name, port)); continue
            base = re.split(r'[\[@]', port, 1)[0]
            if base in ('ck', 'rs'):
                out.extend([(name, port), (payload, port)])
            elif base in ('x2i', 'x2'):
                out.append((payload, ('i' if base == 'x2i' else 'o') + port[len(base):]))
            else:
                out.append((name, port))
        new_buses.append((bid, cls, bits, out))
    # Independently re-read the transformed graph and map every active terminal
    # back to its original source identity. Only declared clock/reset fanout is extra.
    after, _ = _terminals(new_buses, selected | set(replacements.values()))
    inverse = {p: n for n, p in replacements.items()}; conserved = Counter(); clock_duplicates = Counter()
    for (bi, name, port, lo, hi, netbit, direction), count in after.items():
        if name in inverse:
            original = inverse[name]
            if port in ('ck', 'rs'):
                clock_duplicates[(bi, original, port, lo, hi, netbit, direction)] += count
                continue
            port = {'i': 'x2i', 'o': 'x2'}.get(port, port); name = original
        conserved[(bi, name, port, lo, hi, netbit, direction)] += count
    expected_clocks = Counter({key: value for key, value in before.items() if key[2] in ('ck', 'rs')})
    if conserved != before or clock_duplicates != expected_clocks:
        raise ValueError('SSTN split active terminal conservation failure')
    # Commit only after every station, source ABI and transformed bit passes.
    for original, base, payload in prepared:
        for attr in ('master', 'kind', 'w', 'h', 'power_w'):
            if hasattr(base, attr):
                setattr(original, attr, getattr(base, attr))
    model['insts'].extend(payload for _, _, payload in prepared)
    model['buses'][:] = new_buses
    model.setdefault('neutral_role_inputs', {}).update(straps)
    model['sstn_split'] = dict(schema='s81-sstn-two-leaf-expansion-v2', instances=len(records), roles=records,
                               source_abi=source_abis, conserved_active_terminal_bits=sum((key[4]-key[3]+1)*value for key,value in before.items()),
                               duplicated_clock_reset_terminal_bits=sum((key[4]-key[3]+1)*value for key,value in clock_duplicates.items()),
                               conservation_unit='incident terminal-bit occurrences per bus; original output fanout preserved',
                               extra_production_edges=0, clock_delivery='same logical edge; separate actual phi-R per child')
    return True


def populate(source, macro, ports):
    """Plan against the actual published LEF contacts, never a guessed parent pin layout."""
    view=source.bound_views().get(macro.name)
    if not view:raise ValueError('SSTN split child has no bound physical view')
    pins=source.real_lef(view['lef'])['pins']
    macro.ports={};macro.order=[]
    for port,(_,width) in ports.items():
        names=[f'{port}[{i}]' for i in range(width)]
        if width==1 and names[0] not in pins:names=[port]
        if any(n not in pins for n in names):raise ValueError('SSTN split missing actual LEF bit '+port)
        macro.ports[port]=('rects',[(n,*pins[n]) for n in names]);macro.order.append(port)
