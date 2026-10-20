"""Mandatory post-synthesis admission; roles come from the actual loaded Liberty.

This deliberately has no threshold/waiver options. Historical route lint remains
separate. Only constant functions, actual clock pins and transparent unary cells
are special; reset and macro data pins count like other dynamic endpoints.
"""
import argparse
import ast
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


def async_release_proof(g, roles, paths, profile):
    """Prove the RTL's two async-clear release stages from actual Liberty.

    This is a deliberately narrow topology proof, not a larger fanout limit.
    The caller must independently pass the mandatory all-driver census. Only
    positive-edge, D=1, inactive-preset FFs with a Liberty-complemented output
    and active-low clear are admitted. Both publication edges include the
    effective polarity of every actual unary buffer/inverter.
    """
    cfg = profile.get('async_release')
    if (not isinstance(cfg, dict) or set(cfg)-{'stages','clock','ports','sync_select'}
            or type(cfg.get('stages')) is not int or cfg.get('stages') != 2):
        raise ValueError('async release requires exactly two stages')
    if profile.get('enable') is not False:
        raise ValueError('async release describes existing RTL, not inserted stages')
    clock = cfg.get('clock')
    if g.ports.get(clock, (None,))[0] != 'input':
        raise ValueError('async release clock must name an actual input')
    declared = cfg.get('ports')
    if not isinstance(declared, dict) or not declared:
        raise ValueError('async release requires exact per-port stage counts')
    seq, plain = {}, {}
    for path in paths:
        p = Path(path); raw = p.read_bytes()
        text = (gzip.decompress(raw) if p.suffix == '.gz' else raw).decode()
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
        for typ, _, library in groups(text):
            if typ != 'library':
                continue
            for typ, name, body in groups(library):
                if typ != 'cell':
                    continue
                ff = [(args, fb) for kind, args, fb in groups(body) if kind == 'ff']
                if len(ff) != 1:
                    continue
                args, fb = ff[0]
                variables = [x.strip().strip('"') for x in args.split(',')]
                norm = lambda x: re.sub(r'[\s()]', '', x or '')
                # Either Liberty state-variable orientation is legal. ASAP7
                # stores !D in variable1 and exports variable1 itself; other
                # equivalent descriptions store D and export variable2.
                def unary(value):
                    value=norm(value)
                    if re.fullmatch(r'[A-Za-z_]\w*',value): return value,0
                    if re.fullmatch(r'[!~][A-Za-z_]\w*',value): return value[1:],1
                    if re.fullmatch(r"[A-Za-z_]\w*'",value): return value[:-1],1
                    return None
                nxt=unary(attr(fb,'next_state'));clear=unary(attr(fb,'clear'));preset=unary(attr(fb,'preset'))
                if len(variables)==2 and norm(attr(fb,'clocked_on'))=='CLK' and nxt and nxt[0]=='D' and not clear and not preset:
                    for pn,pr in roles.get(name,{}).get('pins',{}).items():
                        f=unary(pr.get('function'))
                        if (pr['direction']=='output' and f and f[0]in variables
                                and nxt[1]^variables.index(f[0])^f[1]==1):
                            plain[name]={'out':pn,'normal_inverted':True}
                    continue
                if (len(variables) != 2 or norm(attr(fb, 'clocked_on')) != 'CLK'
                        or not nxt or nxt[0]!='D' or not clear or not preset
                        or clear[1]!=1 or preset[1]!=1):
                    continue
                outputs=[]
                for pn,pr in roles.get(name,{}).get('pins',{}).items():
                    f=unary(pr.get('function'))
                    if pr['direction']!='output' or not f or f[0] not in variables: continue
                    phase=variables.index(f[0])^f[1]
                    if nxt[1]^phase!=1: continue
                    if {clear[0]:phase,preset[0]:1^phase}!={'RESETN':1,'SETN':0}: continue
                    outputs.append(pn)
                if len(outputs) != 1:
                    continue
                value = {'out': outputs[0], 'variables': variables,
                         'clear': attr(fb, 'clear'), 'preset': attr(fb, 'preset'),
                         'clocked_on': attr(fb, 'clocked_on'), 'next_state': attr(fb, 'next_state')}
                if name in seq and seq[name] != value:
                    raise ValueError('conflicting sequential Liberty functions: ' + name)
                seq[name] = value
    drivers, loads, outgoing = {}, {}, {}
    literals = {g.find(i): int(name[-1]) for name, i in g.net_id.items() if name in ("1'0", "1'1")}
    for ci, (typ, name, pins) in enumerate(g.cells):
        role = roles.get(typ)
        if role is None:
            raise ValueError('unknown Liberty master in release proof: ' + typ)
        ins, outs = [], []
        for pn, nets in pins.items():
            pr = role['pins'].get(pn)
            if pr is None or len(nets) != 1:
                raise ValueError('unsupported scalar release-proof contact: ' + name + '/' + pn)
            net = nets[0]
            if pr['direction'] == 'input':
                loads.setdefault(net, []).append((ci, pn)); ins.append((pn, net))
            elif pr['direction'] == 'output':
                if net in drivers:
                    raise ValueError('multiple drivers in release proof')
                drivers[net] = (ci, pn); outs.append((pn, net))
                f = re.sub(r'[\s()]', '', pr.get('function') or '')
                if not role['sequential'] and f in ('0', '1', "1'b0", "1'b1"):
                    literals[net] = int(f[-1])
        if not role['sequential'] and len(ins) == len(outs) == 1:
            pn, src = ins[0]; op, dst = outs[0]
            f = re.sub(r'[\s()]', '', role['pins'][op].get('function') or '')
            if f in (pn, '!' + pn, '~' + pn, pn + "'"):
                outgoing[ci] = (src, dst, int(f != pn))
    def origin(net, seen=None):
        seen = set() if seen is None else seen
        if net in seen:
            raise ValueError('cyclic transparent release path')
        seen.add(net)
        dr = drivers.get(net)
        if dr and dr[0] in outgoing:
            src, _, inv = outgoing[dr[0]]
            root, polarity = origin(src, seen)
            return root, polarity ^ inv
        return net, 0
    def constant(net):
        root, inv = origin(net)
        return None if root not in literals else literals[root] ^ inv
    clk_origin = origin(g.ports[clock][1])
    def capture(ci):
        typ, name, pins = g.cells[ci]
        if typ not in seq or set(pins) != {'CLK', 'D', 'RESETN', 'SETN', seq[typ]['out']}:
            raise ValueError('release stage is not a supported Liberty FF: ' + name)
        data=constant(pins['D'][0])
        inactive='SETN' if data==1 else 'RESETN'
        if origin(pins['CLK'][0]) != clk_origin or data not in (0,1) or constant(pins[inactive][0]) != 1:
            raise ValueError('release stage wrong clock/D/preset: ' + name)
        return pins[seq[typ]['out']][0]
    def release_pin(ci):
        return 'RESETN' if constant(g.cells[ci][2]['D'][0])==1 else 'SETN'
    def release_phase(ci):
        return constant(g.cells[ci][2]['D'][0])
    def terminals(net):
        stack = [(net, 0)]; seen = set(); ends = set()
        while stack:
            x, inv = stack.pop()
            if (x, inv) in seen:
                continue
            seen.add((x, inv))
            if any(d == 'output' and n == x for d, n in g.ports.values()):
                raise ValueError('release tree is exported as a functional output')
            for ci, pn in loads.get(x, ()):
                if ci in outgoing:
                    _, dst, neg = outgoing[ci]; stack.append((dst, inv ^ neg))
                else:
                    ends.add((ci, pn, inv))
        if len(ends) > 32:
            raise ValueError('release publication exceeds32')
        return ends
    # Optional, explicitly typed downstream obligation for the existing D8
    # region: rs1 selects rseed/rnext into an unconditional one-hot D capture.
    # Every Boolean cofactor is checked using actual Liberty functions. A
    # generic combinational sink is never accepted as an asynchronous reset.
    selectors = {}
    select_cfg=cfg.get('sync_select')
    if select_cfg:
        if (not isinstance(select_cfg,dict) or set(select_cfg)!={'kind','scopes'}
                or select_cfg.get('kind')!='qfd_land8_onehot_v1'
                or not isinstance(select_cfg.get('scopes'),list)
                or not select_cfg['scopes'] or len(set(select_cfg['scopes']))!=len(select_cfg['scopes'])):
            raise ValueError('unsupported synchronous reset/select contract')
        compiled={}
        def function(expr, values):
            if expr not in compiled:
                text=re.sub(r"([A-Za-z_]\w*)'",r'~\1',expr).replace('!','~').replace('*','&').replace('+','|')
                tree=ast.parse(text.strip(),mode='eval')
                allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.BitAnd,ast.BitOr,ast.BitXor,ast.Invert,ast.Name,ast.Load,ast.Constant)
                if any(not isinstance(n,allowed)for n in ast.walk(tree)):
                    raise ValueError('unsupported Liberty Boolean expression')
                if any(isinstance(n,ast.Constant)and(type(n.value)is not int or n.value not in (0,1))for n in ast.walk(tree)):
                    raise ValueError('nonbinary Liberty Boolean constant')
                compiled[expr]=compile(tree,'<actual-liberty>','eval')
            return int(eval(compiled[expr],{'__builtins__':{}},values))&1
        def alias(name):
            if name not in g.net_id:raise ValueError('missing source-bound selector alias: '+name)
            return g.find(g.net_id[name])
        for scope in select_cfg['scopes']:
            if not isinstance(scope,str):raise ValueError('invalid selector scope')
            release_name=scope+'.rs1$_DFF_PN0_'
            candidates=[i for i,(_,name,_)in enumerate(g.cells)if name==release_name]
            if len(candidates)!=1:raise ValueError('missing source-bound selector release FF: '+scope)
            ci=candidates[0];release_net=capture(ci);phase=release_phase(ci)
            seed=[alias(scope+'.rseed['+str(i)+']')for i in range(3)]
            nxt=[alias(scope+'.rnext['+str(i)+']')for i in range(3)]
            targets=[];covered=set()
            for bit in range(8):
                output=alias(scope+'.rdsel_o['+str(bit)+']');root,inv=origin(output);dr=drivers.get(root)
                if not dr or g.cells[dr[0]][0]not in plain:raise ValueError('selector output is not an actual plain FF')
                ti=dr[0];typ,name,pins=g.cells[ti]
                if dr[1]!=plain[typ]['out'] or origin(pins['CLK'][0])!=clk_origin:
                    raise ValueError('selector capture clock/output role mismatch')
                targets.append((bit,pins['D'][0],1^inv,ti))
            if len({x[3]for x in targets})!=8:raise ValueError('selector capture bits merged')
            for release in (0,1):
                for sv in range(8):
                    for nv in range(8):
                        cuts={release_net:release^phase}
                        for nets,value in ((seed,sv),(nxt,nv)):
                            for bit,net in enumerate(nets):
                                value_bit=(value>>bit)&1
                                if net in cuts and cuts[net]!=value_bit:raise ValueError('selector cutpoint aliases are not independent')
                                cuts[net]=value_bit
                        cache={};visiting=set()
                        def value(net):
                            if net in cuts:return cuts[net]
                            if net in literals:return literals[net]
                            if net in cache:return cache[net]
                            if net in visiting:raise ValueError('cyclic selector Boolean cone')
                            visiting.add(net);dr=drivers.get(net)
                            if not dr:raise ValueError('unbound selector Boolean input')
                            node,pn=dr;typ,name,pins=g.cells[node];role=roles[typ]
                            if role['sequential']:raise ValueError('unbound state in selector reset cone')
                            expr=role['pins'][pn].get('function')
                            if expr is None:raise ValueError('missing selector Liberty function')
                            inputs={}
                            for ip,nets in pins.items():
                                if role['pins'][ip]['direction']=='input':
                                    covered.add((node,ip));inputs[ip]=value(nets[0])
                            result=function(expr,inputs);visiting.remove(net);cache[net]=result;return result
                        selected=nv if release else sv
                        for bit,dnet,inverted,_ in targets:
                            if value(dnet)!=int(bit==selected)^inverted:
                                raise ValueError('synchronous select/reset Boolean cofactor mismatch: '+scope)
            selectors[ci]={'scope':scope,'cofactors':128,'capture_bits':8,'covered':covered}
    ports = {}; all_final=set()
    for port, counts in declared.items():
        if g.ports.get(port, (None,))[0] != 'input' or not isinstance(counts, dict):
            raise ValueError('unknown release input/count declaration')
        first_count, final_count = counts.get('first'), counts.get('final')
        if (type(first_count) is not int or not 1 <= first_count <= 32
                or type(final_count) is not int or not 1 <= final_count <= 32 * first_count):
            raise ValueError('invalid exact release counts')
        first, final = set(), set()
        for ci, pn, inv in terminals(g.ports[port][1]):
            if inv:
                raise ValueError('raw reset bypass/wrong polarity')
            capture(ci)
            if pn!=release_pin(ci):raise ValueError('raw reset reaches wrong clear/preset role')
            first.add(ci)
        if len(first) != first_count:
            raise ValueError('stale first release-stage count')
        for ci in first:
            for child, pn, inv in terminals(capture(ci)):
                if child in first or inv != release_phase(ci):
                    raise ValueError('first stage bypass/wrong QN publication polarity')
                capture(child)
                if pn!=release_pin(child):raise ValueError('first stage reaches wrong clear/preset role')
                final.add(child)
        if len(final) != final_count:
            raise ValueError('stale final release-stage count')
        all_final.update(final)
        for ci in final:
            for child, pn, inv in terminals(capture(ci)):
                typ, name, pins = g.cells[child]
                if ci in selectors and (child,pn)in selectors[ci]['covered'] and not roles[typ]['sequential']:
                    continue
                if child in first | final or typ not in seq or pn not in ('RESETN', 'SETN') or inv != release_phase(ci):
                    raise ValueError('final reset publication bypass/clock/polarity')
                if origin(pins['CLK'][0]) != clk_origin:
                    raise ValueError('final reset crosses a different clock')
                if ((pn=='RESETN' and constant(pins['D'][0])==1 and constant(pins['SETN'][0])==1)
                        or (pn=='SETN' and constant(pins['D'][0])==0 and constant(pins['RESETN'][0])==1)):
                    raise ValueError('third release stage is not in the two-edge contract')
        ports[port] = {'pass': True, 'first': len(first), 'final': len(final), 'edges': 2,
                       'first_instances': sorted(g.cells[x][1] for x in first),
                       'final_instances': sorted(g.cells[x][1] for x in final)}
    if set(selectors)-all_final:
        raise ValueError('synchronous selector is not an actual second release stage')
    return {'status': 'PASS', 'ports': ports, 'sequential_roles': seq,
            'synchronous_select':[{'instance':g.cells[ci][1],**{k:v for k,v in row.items()if k!='covered'}}for ci,row in selectors.items()]}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--netlist', required=True)
    p.add_argument('--top', required=True)
    p.add_argument('--liberty', action='append', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--async-release-profile')
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
        g, top = TL.flatten(modules, a.top, keep_aliases=bool(a.async_release_profile))
        report['top'] = top
        report.update(census(g, roles))
        if a.async_release_profile:
            profile_raw = Path(a.async_release_profile).read_bytes()
            profile = json.loads(profile_raw)
            if profile.get('schema') != 'opentallas.ref_tile.reset_landing.v1' or profile.get('top') != top:
                raise ValueError('async release profile schema/top mismatch')
            proof = async_release_proof(g, roles, a.liberty, profile)
            proof['profile_sha256'] = hashlib.sha256(profile_raw).hexdigest()
            report['async_release'] = proof
    except Exception as exc:
        report.update(status='FAIL', role_errors=[f'{type(exc).__name__}: {exc}'])
    Path(a.out).write_text(json.dumps(report, indent=2) + '\n')
    print('PRE_GATE_NATIVE_CENSUS ' + report['status'] + ' report=' + a.out)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
