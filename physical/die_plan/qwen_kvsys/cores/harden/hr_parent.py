"""Emit the native HR parent from the same elaborated member cut as its cores.

The reference keeps actual member functions. Selected implementations change only
explicit child providers; their timing/context contracts remain in the receipt.
"""
import copy
import hashlib
import json
import re
from pathlib import Path


class ParentError(ValueError):
    pass


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _decl(doc):
    return {k: list(v) for k, v in doc['port_decl'].items()}


def reachable_sources(files, top):
    """Keep the provider's reached modules/packages; final HDL hierarchy remains the gate."""
    definitions, packages = {}, {}
    for path in dict.fromkeys(files):
        text = Path(path).read_text()
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
        for match in re.finditer(r'(?s)\bmodule\s+(\w+)\b.*?\bendmodule\b', text):
            name, body = match.group(1), match.group(0)
            if name in definitions and definitions[name][1] != body:
                raise ParentError(f'provider has conflicting definitions of {name}')
            definitions[name] = (path, body)
        for match in re.finditer(r'(?s)\bpackage\s+(\w+)\b.*?\bendpackage\b', text):
            packages[match.group(1)] = (path, match.group(0))
    if top not in definitions:
        raise ParentError(f'provider source does not define {top}')
    todo, seen, wanted = [top], set(), set()
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        path, body = definitions[name]
        wanted.add(path)
        for candidate in definitions:
            if candidate != name and re.search(r'\b' + re.escape(candidate) + r'\s*(?:#\s*\([^;]*?\)\s*)?(?:\\\S+|[A-Za-z_]\w*)\s*\(', body, re.S):
                todo.append(candidate)
        for pkg, (pkgpath, _) in packages.items():
            if re.search(r'\b' + re.escape(pkg) + r'\s*::', body):
                wanted.add(pkgpath)
    return [str(p) for p in dict.fromkeys(files) if p in wanted]


def emit(host, hcs, core_mem, records, hck, ckmap, output, module, implementations=None, repo_root=None, extra_sources=()):
    out = Path(output)
    impl = implementations or {}
    repo = Path(repo_root or Path(__file__).resolve().parents[5])
    def resolved(path):
        p = Path(path)
        return str(p if p.is_absolute() else repo / p)
    unknown = set(impl) - {h['module'] for h in hcs}
    if unknown:
        raise ParentError('implementation map names no planned core: ' + ', '.join(sorted(unknown)))
    member_core = {mp: ci for ci, members in core_mem.items() for mp in members}
    nets, glue, _, subtree = host.walk(set(member_core), include_opaque=True)
    root = host.net_root
    endpoint = {}
    for r, ends in nets.items():
        for e in ends:
            if e[0] == 'M':
                endpoint[e[1:]] = r
    bit_ids = {}
    aliases = []
    next_bit = 2

    def bit(value):
        nonlocal next_bit
        if isinstance(value, str):
            return value
        if value not in bit_ids:
            bit_ids[value] = next_bit
            next_bit += 1
        return bit_ids[value]

    def local(path, value):
        return value if isinstance(value, str) else bit(root((path, value)))

    original = host.J[host.top]
    parent = dict(attributes=dict(top='1', hdlname=module),
                  parameter_default_values=copy.deepcopy(original.get('parameter_default_values', {})),
                  ports={}, cells={}, netnames={})
    for name, port in original['ports'].items():
        p = copy.deepcopy(port)
        p['bits'] = [local('', b) for b in port['bits']]
        parent['ports'][name] = p
        parent['netnames'][name] = dict(hide_name=0, bits=p['bits'], attributes={})
        for key in ('offset', 'upto', 'signed'):
            if key in p:
                parent['netnames'][name][key] = p[key]
    opaque, memory_names, memory_rows = {}, {}, []
    for gid, (path, cn, typ) in enumerate(glue):
        owner = subtree[path][0] if path else host.top
        c = copy.deepcopy(host.J[owner]['cells'][cn])
        memid = c.get('parameters', {}).get('MEMID')
        if memid is not None and c['type'].startswith(('$memrd', '$memwr', '$meminit')):
            candidates = [name for name in host.J[owner].get('memories', {})
                          if name.lstrip('\\') == memid.lstrip('\\')]
            if len(candidates) != 1:
                raise ParentError(f'glue memory declaration missing or ambiguous: {path}/{memid}')
            name = candidates[0]
            key = (path, name)
            if key not in memory_names:
                new = f'hr_mem_{len(memory_names)}'
                memory_names[key] = new
                declaration = copy.deepcopy(host.J[owner]['memories'][name])
                parent.setdefault('memories', {})[new] = declaration
                memory_rows.append(dict(owner=path, original_name=name, emitted_name=new,
                                        declaration_sha256=hashlib.sha256(json.dumps(declaration,sort_keys=True).encode()).hexdigest(),
                                        width=declaration['width'], size=declaration['size']))
            c['parameters']['MEMID'] = '\\' + memory_names[key]
        c['connections'] = {p: [local(path, b) for b in bs] for p, bs in c['connections'].items()}
        c.setdefault('attributes', {})['hr_original_path'] = (path + '/' if path else '') + cn
        parent['cells'][f'hr_glue_{gid}'] = c
        if typ in host.J:
            opaque[typ] = copy.deepcopy(host.J[typ])
    initialization, net_rows = {}, []
    owners = [('', host.top)] + [(path, value[0]) for path, value in subtree.items()]
    for path, owner in owners:
        for name, net in host.J[owner].get('netnames', {}).items():
            copied = copy.deepcopy(net)
            copied['bits'] = [local(path,b) for b in net['bits']]
            target = name if not path and name in parent['ports'] else f'hr_net_{len(net_rows)}'
            init = copied.get('attributes', {}).get('init')
            if init is not None:
                if len(init) != len(copied['bits']):
                    raise ParentError(f'glue init width differs: {path}/{name}')
                for b, value in zip(copied['bits'], reversed(init)):
                    if value == 'x':
                        continue
                    if b in initialization and initialization[b] != value:
                        raise ParentError(f'conflicting glue initialization on parent bit {b}')
                    initialization[b] = value
            parent['netnames'][target] = copied
            if copied.get('attributes'):
                net_rows.append(dict(owner=path,original_name=name,emitted_name=target,
                                     attributes=copied['attributes']))
            else:
                net_rows.append(dict(owner=path,original_name=name,emitted_name=target))
    source_reference, source_selected = [], []
    for typ in opaque:
        sources = reachable_sources([resolved(f) for f in extra_sources], typ)
        source_reference.extend(sources)
        source_selected.extend(sources)
    child_rows = []
    boundary_checks, unused_outputs, constant_inputs = [], [], []
    for h in hcs:
        mod, ci = h['module'], h['inst']
        record_path = Path(records[mod])
        rec = json.loads(record_path.read_text())
        expected = _decl(rec)
        ms = core_mem[ci]
        multi = len(ms) > 1
        connections = {p: {} for p in expected}
        clock_roots = {}
        directions = {p: d[0] for p, d in expected.items()}
        for mp, rel in ms.items():
            for p, (direction, values, offset) in host.port_info(mp).items():
                base = f'{rel}__{p}' if multi else p
                for index, value in enumerate(values):
                    r = endpoint.get((mp, p, index))
                    if r is None:
                        owner, _, name = mp.rpartition('/')
                        owner_module = subtree[owner][0] if owner else host.top
                        actual = host.J[owner_module]['cells'][name]['connections'].get(p, [])
                        if base in expected and direction == 'input' and index < len(actual) and isinstance(actual[index], str):
                            value = actual[index]
                            if value not in ('0','1','x','z'):
                                raise ParentError(f'{ci}: invalid source constant {base}[{index+offset}]={value}')
                            connections[base][index+offset] = value
                            constant_inputs.append(dict(inst=ci,pin=base,index=index+offset,value=value))
                        continue
                    ends = nets[r]
                    families = {hck[e[1]] for e in ends if e[0] == 'P' and e[1] in hck}
                    if families:
                        if len(families) != 1 or next(iter(families)) not in ckmap:
                            raise ParentError(f'{ci}: clock source is unknown or ambiguous: {sorted(families)}')
                        family = next(iter(families))
                        cp = ckmap[family]
                        clock_roots.setdefault(cp, {}).setdefault(r, set()).update(
                            e[1] for e in ends if e[0] == 'P' and e[1] in hck)
                        continue
                    others = [e for e in ends if not (e[0] == 'M' and member_core[e[1]] == ci)]
                    if base in expected:
                        if expected[base][0] != direction:
                            raise ParentError(f'{ci}: current boundary direction differs: {base}')
                        connections[base][index+offset] = bit(r)
                        if direction == 'output' and not others:
                            unused_outputs.append(dict(inst=ci,pin=base,index=index+offset,source_net=repr(r),
                                                       reason='actual member output has zero external consumers'))
                    elif others:
                        raise ParentError(f'{ci}: current boundary is absent from reference core: {base}[{index+offset}]')
        for cp, roots in clock_roots.items():
            if cp not in expected or expected[cp] != ['input', 0, 0]:
                raise ParentError(f'{ci}: core clock ABI differs: {cp}')
            # Only the owner-mandated common core domain may merge former host/ingest aliases.
            names = sorted({n for ns in roots.values() for n in ns})
            families = sorted({hck[n] for n in names})
            if len(roots) > 1 and (cp != 'ck' or set(families) - {'clk', 'clk_clk_host', 'clk_clk_ingest'}):
                raise ParentError(f'{ci}: separate clock domains cannot be collapsed: {cp} {families}')
            chosen = sorted(roots, key=repr)[0]
            connections[cp][0] = bit(chosen)
            aliases.append(dict(inst=ci, pin=cp, host_ports=names, families=families,
                                chosen_net=repr(chosen), same_core_domain=len(roots) > 1))
        wire = {}
        for p, (direction, hi, lo) in expected.items():
            actual = connections[p]
            hole = set(rec.get('port_holes', {}).get(p, []))
            missing = set(range(lo, hi+1)) - set(actual)
            if missing - hole:
                raise ParentError(f'{ci}: missing parent connection {p}: {sorted(missing-hole)[:8]}')
            # A declared but unused pin hole remains a private dangling bit, never a public tie.
            wire[p] = [actual.get(i, bit(('unused', ci, p, i))) for i in range(lo, hi+1)]
            unobserved = {row['index'] for row in unused_outputs if row['inst']==ci and row['pin']==p}
            if direction == 'output' and unobserved == set(range(lo,hi+1)):
                wire[p] = []  # explicit .pin(): source proves this complete output is unobserved
            boundary_checks.extend((ci, p, i, actual[i]) for i in sorted(actual))
        parent['cells'][ci] = dict(hide_name=0, type=mod, parameters={}, attributes=dict(hr_group='1'),
                                   port_directions=directions, connections=wire)
        chosen = impl.get(mod)
        selected_record = record_path
        contract = {}
        if chosen:
            contract = chosen if isinstance(chosen, dict) else dict(core_json=chosen)
            selected_record = Path(resolved(contract['core_json']))
            selected = json.loads(selected_record.read_text())
            for path, expected_sha in contract.get('selected_file_sha256', {}).items():
                if _sha(resolved(path)) != expected_sha:
                    raise ParentError(f'{ci}: selected source differs from measured source: {path}')
            if selected.get('module') != mod or _decl(selected) != expected:
                raise ParentError(f'{ci}: selected implementation changes the current core ABI')
        else:
            selected = rec
        source_reference.extend(reachable_sources([resolved(f) for f in rec['files']], mod))
        source_selected.extend(reachable_sources([resolved(f) for f in selected['files']], mod))
        child_rows.append(dict(inst=ci, module=mod, members=ms, reference_core_json=str(record_path),
                               reference_sha256=_sha(record_path),
                               original_member_modules={mp: dict(module=host.mods[mp],
                                   definition_sha256=hashlib.sha256(json.dumps(host.J[host.mods[mp]],sort_keys=True).encode()).hexdigest()) for mp in ms},
                               selected_core_json=str(selected_record),
                               selected_sha256=_sha(selected_record), contract=contract))
    out.mkdir(parents=True, exist_ok=True)
    doc = dict(creator='kv_core_rtl.py HR native grouping', modules={module: parent, **opaque})
    parent_json = out / f'{module}.json'
    parent_sv = out / f'{module}.sv'
    parent_json.write_text(json.dumps(doc, indent=1) + '\n')
    (out / 'write_parent.ys').write_text(f'read_json {parent_json}\nwrite_verilog {parent_sv}\n')
    checks = []
    for name, value in parent['parameter_default_values'].items():
        if not isinstance(value, str) or not value or set(value) - set('01xz'):
            raise ParentError(f'unsupported parameter value {name}={value!r}')
        checks.append(f'    if ({name} !== {len(value)}\'b{value}) $error(\"HR parent fixed-shape parameter {name} differs\");')
    (out / 'parameter_guards.sv').write_text('  initial begin\n' + '\n'.join(checks) + '\n  end\n')
    (out / 'guard_parent.py').write_text(
        'import sys\n' + f'sys.path.insert(0,{str(Path(__file__).resolve().parent)!r})\n' +
        'from hr_parent import guard\n' + f'guard({str(out)!r})\n')
    def files(name, entries):
        unique = list(dict.fromkeys([str(parent_sv)] + entries))
        definitions = {}
        for source in unique[1:]:
            text = re.sub(r'/\*.*?\*/|//[^\n]*', '', Path(source).read_text(), flags=re.S)
            for match in re.finditer(r'(?s)\bmodule\s+(\w+)\b.*?\bendmodule\b', text):
                mod, body = match.group(1), re.sub(r'\s+', '', match.group(0))
                if mod in definitions and definitions[mod][0] != body:
                    raise ParentError(f'{name}: conflicting reached provider definitions of {mod}: {definitions[mod][1]} and {source}')
                definitions[mod] = (body, source)
        (out / name).write_text('\n'.join(unique) + '\n')
    files('reference.f', source_reference)
    files('selected.f', source_selected)
    receipt = dict(schema='opentallas.kv.hr_parent.v1', module=module, source_top=host.top,
                   parent_json=str(parent_json), parent_sv=str(parent_sv), source_port_count=len(parent['ports']),
                   source_port_bits=sum(len(p['bits']) for p in parent['ports'].values()),
                   glue_cells=len(glue), glue_memories=memory_rows, glue_netnames=len(net_rows),
                   glue_initialized_bits=len(initialization), glue_kept_nets=sum(bool(row.get('attributes',{}).get('keep')) for row in net_rows), opaque_modules=sorted(opaque), groups=child_rows, clock_aliases=aliases,
                   reference_unused_outputs=unused_outputs, actual_source_constant_inputs=constant_inputs,
                   grouping_added_cycles=0, grouping_reference_equivalence=dict(
                       status='PASS', method='cut and reconnect identical elaborated member functions and parameters',
                       scope='grouping-only; selected child behavior is a separate model contract',
                       complete_glue_cells=len(glue), complete_glue_memories=len(memory_rows), complete_group_members=len(member_core)),
                   boundary_bits=len(boundary_checks),
                   boundary_sha256=hashlib.sha256(json.dumps(boundary_checks, sort_keys=True).encode()).hexdigest(),
                   equivalence_basis='same elaborated member functions and parameters, exact union-find boundary nets; '
                                     'former core-clock aliases are the declared common core domain only',
                   selected_function_equivalent_to_reference=not bool(impl))
    (out / 'hr_parent.json').write_text(json.dumps(receipt, indent=1) + '\n')
    return receipt


def guard(output):
    """Apply fixed-shape guards only to an actually emitted source and audit shared masters."""
    out = Path(output)
    r = json.loads((out/'hr_parent.json').read_text())
    shared, counts = {}, {}
    for group in r['groups']:
        mod = group['module']
        identity = sorted((re.sub(r'\[\d+\]', '[]', path.split('/')[-1]), value['definition_sha256'])
                          for path, value in group['original_member_modules'].items())
        if mod in shared and shared[mod] != identity:
            raise ParentError(f'{mod}: repeated instances have different actual member functions or parameters')
        shared[mod] = identity
        counts[mod] = counts.get(mod, 0) + 1
    p = Path(r['parent_sv'])
    text = p.read_text()
    start = re.search(r'\bmodule\s+' + re.escape(r['module']) + r'\b', text)
    if start is None:
        raise ParentError('actual parent source module missing')
    end = text.find('endmodule', start.end())
    if end < 0:
        raise ParentError('actual parent source module is incomplete')
    checks = (out/'parameter_guards.sv').read_text()
    fixed = json.loads(Path(r['parent_json']).read_text())['modules'][r['module']]['parameter_default_values']
    declarations = []
    for name, value in fixed.items():
        declaration = r'\bparameter\s+(?:(?:integer|int|logic|bit|reg|signed|unsigned)\s+|\[[^]]+\]\s*)*' + re.escape(name) + r'\s*='
        if not re.search(declaration, text[start.end():end]):
            declarations.append(f'  parameter {name} = {len(value)}\'b{value};')
    if declarations or checks not in text[start.end():end]:
        # A failed older guard remains preserved by the caller; replace only our exact generated check block.
        body = text[start.end():end].replace(checks, '')
        body += '\n'.join(declarations) + '\n' + checks
        p.write_text(text[:start.end()] + body + text[end:])
    r.update(verdict='PASS', scope='grouping reference graph, actual host ABI, fixed-shape parameter guards; '
             'selected function changes retain their separate model contracts', guarded_parent_sha256=_sha(p),
             shared_master_identity={m:dict(instances=counts[m],member_definition_sha256=[v for _,v in shared[m]],
                                              verdict='PASS') for m in shared if counts[m] > 1})
    (out/'host_guard.json').write_text(json.dumps(r,indent=1)+'\n')
    return r
