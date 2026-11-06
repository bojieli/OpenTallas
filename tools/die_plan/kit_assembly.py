"""Shared, explicit source assembly for fixed-port signed children.

This prepares a kit; it does not replace its RTL equivalence or physical signoff.
Only byte-sealed selected source instances lose their parameter overrides. Native
soft siblings keep their complete definitions and parameters.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

def _masked_rtl(text):
    return re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',
                  lambda m: re.sub(r'[^\n]', ' ', m[0]), text, flags=re.S)


def _code_rename(text, old, new):
    matches = list(re.finditer(r'\b'+re.escape(old)+r'\b', _masked_rtl(text)))
    for hit in reversed(matches):
        text = text[:hit.start()]+new+text[hit.end():]
    return text


def _instance_type_spans(text, master, instance):
    code = _masked_rtl(text)
    spans = []
    for hit in re.finditer(r'\b'+re.escape(master)+r'\b', code):
        i = hit.end()
        while i < len(code) and code[i].isspace():
            i += 1
        if i < len(code) and code[i] == '#':
            i += 1
            while i < len(code) and code[i].isspace():
                i += 1
            if i == len(code) or code[i] != '(':
                continue
            depth = 1
            i += 1
            while i < len(code) and depth:
                depth += (code[i] == '(') - (code[i] == ')')
                i += 1
            if depth:
                raise ValueError('unbalanced hard-child parameter list')
        while i < len(code) and code[i].isspace():
            i += 1
        if re.match(re.escape(instance)+r'\s*\(', code[i:]):
            spans.append((hit.start(), hit.end(), i))
    return spans


def specialize_native_children(rtl_dir, children):
    """Only selected instances use the hard view; other parameterizations remain native.

    A source module may serve both a hardened bank and soft banks with different
    parameters. Rename its native definition/references, then restore the type of
    each selected instance to the separately staged fixed-port blackbox master.
    The selected hard instance has fixed sealed parameters, so its native
    override block is removed. Soft-instance parameters/ports and native logic
    remain unchanged.
    """
    paths = [p for p in sorted(Path(rtl_dir).iterdir())
             if p.suffix in ('.sv', '.v') and not p.name.endswith('_bb.v')]
    texts = {p:p.read_text() for p in paths}
    masters = {c['master'] for c in children}
    counts = {}
    for master in sorted(masters):
        alias = master+'__soft'
        if any(re.search(r'\b'+re.escape(alias)+r'\b', _masked_rtl(t)) for t in texts.values()):
            raise ValueError('hard child native alias already exists: '+alias)
        n = sum(len(re.findall(r'(?m)^[ \t]*module\s+'+re.escape(master)+r'\b', _masked_rtl(t)))
                for t in texts.values())
        if n != 1:
            raise ValueError(f'expected exactly one native definition for {master}, found {n}')
        texts = {p:_code_rename(t, master, alias) for p,t in texts.items()}
        leaves = {c['inst'].split('.')[-1] for c in children if c['master'] == master}
        for leaf in sorted(leaves):
            hits = [(p, a, b, end) for p,t in texts.items() for a,b,end in _instance_type_spans(t, alias, leaf)]
            if len(hits) != 1:
                raise ValueError(f'hard child {master}/{leaf}: expected one source instance, found {len(hits)}')
            p,a,b,end = hits[0]
            texts[p] = texts[p][:a]+master+' '+texts[p][end:]
        counts[master] = len(leaves)
    for path,text in texts.items():
        if text != path.read_text():
            path.write_text(text)
    return counts



def module_names(text):
    return set(re.findall(r"\bmodule\s+(?:(?:automatic|static)\s+)?([A-Za-z_][\w$]*)\b",
                          _masked_rtl(text)))


def _named_overrides(text):
    code = _masked_rtl(text).strip()
    if not code:
        return {}
    if not code.startswith('#'):
        raise ValueError('unsupported fixed-child override syntax')
    code = code[1:].strip()
    if not code.startswith('(') or not code.endswith(')'):
        raise ValueError('unbalanced fixed-child parameter block')
    code = code[1:-1]
    out, i = {}, 0
    while i < len(code):
        while i < len(code) and (code[i].isspace() or code[i] == ','):
            i += 1
        if i == len(code):
            break
        match = re.match(r'\.([A-Za-z_][\w$]*)\s*\(', code[i:])
        if not match:
            raise ValueError('fixed child requires explicit named parameter overrides')
        name = match[1]
        start = i + match.end()
        i, depth = start, 1
        while i < len(code) and depth:
            depth += (code[i] == '(') - (code[i] == ')')
            i += 1
        if depth or name in out:
            raise ValueError('unbalanced or duplicate fixed-child parameter: ' + name)
        out[name] = code[start:i-1].strip()
    return out


def _literal_integer(expression):
    value = expression.strip()
    while value.startswith('(') and value.endswith(')'):
        value = value[1:-1].strip()
    if re.fullmatch(r'-?[0-9_]+', value):
        return int(value.replace('_', ''))
    match = re.fullmatch(r"(?:[0-9]+)?'[sS]?([bBoOdDhH])([0-9a-fA-F_]+)", value)
    if match:
        return int(match[2].replace('_', ''), dict(b=2, o=8, d=10, h=16)[match[1].lower()])
    return None  # symbolic expressions are covered by the byte-sealed parent binding


def dedupe_sources(paths, alias_dir):
    """Preserve ordered sources; alias a basename collision only for disjoint modules.

    Alias files retain the exact bytes. Includes/packages/header collisions stay
    errors: relocating them could change relative include or package semantics.
    """
    out, by_name, groups, seen = [], {}, {}, set()
    for source in map(Path, paths):
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        original_name = source.name
        if (original_name, digest) in seen:
            continue
        previous = groups.get(original_name, [])
        if previous:
            text = source.read_text()
            modules = module_names(text)
            previous_texts = [p.read_text() for p in previous]
            occupied = set().union(*(module_names(t) for t in previous_texts))
            if source.stem.endswith(("_bb", "_sim")) or not modules or not occupied or modules & occupied or any(
                    "`include" in t for t in [text] + previous_texts):
                raise ValueError(f"different source files named {source.name}: {previous} vs {source}")
            alias = Path(alias_dir) / (source.stem + "__src_" + digest[:16] + source.suffix)
            alias.parent.mkdir(parents=True, exist_ok=True)
            if alias.exists() and alias.read_bytes() != data:
                raise ValueError(f"source alias collision: {alias}")
            alias.write_bytes(data)
            output = alias
        else:
            output = source
        if output.name in by_name and by_name[output.name].read_bytes() != data:
            raise ValueError(f"source alias collides with another input: {output.name}")
        groups.setdefault(original_name, []).append(source)
        seen.add((original_name, digest))
        by_name[output.name] = output
        out.append(output)
    return out


def assemble_fixed_children(rtl_dir, children, contracts, receipt=None, parent_profile=None):
    """Materialize selected fixed-port calls after checking their exact source seal.

    Contracts use the existing signed_children parameter_contracts format. The
    caller validates child_params against the SIGNED view before this operation;
    this function checks the selected source bytes, instance identity, and fixed
    blackbox interface. It supports unique lexical instances, not arbitrary
    cloning of shared generate/module bodies. Post-elaboration inventory detects
    a lexical instance that elaborates more than once.
    """
    root = Path(rtl_dir)
    paths = [p for p in sorted(root.iterdir()) if p.suffix in (".sv", ".v")]
    sources = {p: p.read_text() for p in paths if not p.name.endswith("_bb.v")}
    selected = {(c["master"], c["inst"]) for c in children}
    sealed = {(c["master"], c["instance"]) for c in contracts}
    if len(selected) != len(children) or len(sealed) != len(contracts) or selected != sealed:
        raise ValueError("selected hard-child instances differ from sealed assembly contracts")
    bindings = []
    for contract in contracts:
        if parent_profile is not None:
            effective = parent_profile.get('parameters', {})
            for parameter, value in contract.get('parent_params', {}).items():
                if effective.get(parameter) != value:
                    raise ValueError(f"effective parent parameter {parameter} differs from sealed child binding")
        master, instance = contract["master"], contract["instance"]
        leaf = instance.split(".")[-1]
        if not re.fullmatch(r"[A-Za-z_][\w$]*", leaf):
            raise ValueError(f"unsupported selected source instance {instance!r}")
        if not isinstance(contract.get("child_params"), dict):
            raise ValueError(f"missing sealed child parameters: {master}/{instance}")
        hits = [(p, a, b, end) for p, text in sources.items()
                for a, b, end in _instance_type_spans(text, master, leaf)]
        if len(hits) != 1:
            raise ValueError(f"{master}/{instance}: expected one source instance, found {len(hits)}")
        path, _, type_end, instance_start = hits[0]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != contract.get("binding_sha256"):
            raise ValueError(f"{master}/{instance}: selected binding source differs from sealed bytes")
        overrides = _named_overrides(sources[path][type_end:instance_start])
        for parameter, expression in overrides.items():
            if parameter not in contract['child_params']:
                raise ValueError(f"{master}/{instance}: unsealed parameter override {parameter}")
            literal = _literal_integer(expression)
            if literal is not None and literal != contract['child_params'][parameter]:
                raise ValueError(f"{master}/{instance}: {parameter} differs from sealed child value")
        blackboxes = [p for p in paths if p.name.endswith("_bb.v") and master in module_names(p.read_text())]
        if len(blackboxes) != 1:
            raise ValueError(f"{master}: expected one staged fixed-port blackbox, found {len(blackboxes)}")
        bb = _masked_rtl(blackboxes[0].read_text())
        if re.search(r"\bmodule\s+" + re.escape(master) + r"\s*#", bb):
            raise ValueError(f"{master}: signed fixed-port blackbox still declares parameters")
        bindings.append(dict(master=master, instance=instance, source=path.name,
                             source_sha256=digest, child_params=contract["child_params"],
                             blackbox=blackboxes[0].name,
                             blackbox_sha256=hashlib.sha256(blackboxes[0].read_bytes()).hexdigest()))
    # Stage all transforms in memory first. No partially transformed output on
    # a missing/ambiguous native definition or source instance.
    import tempfile
    import shutil
    with tempfile.TemporaryDirectory(prefix="kit-assembly-") as directory:
        stage = Path(directory)
        for p in paths:
            shutil.copyfile(p, stage / p.name)
        native_masters = {c["master"] for c in children if any(
            c["master"] in module_names(text) for text in sources.values())}
        native = [c for c in children if c["master"] in native_masters]
        if native:
            specialize_native_children(stage, native)
        # Some parent closures already omit the native child body and stage the
        # fixed view directly. Only seal the explicitly listed calls in that case.
        for contract in contracts:
            master, instance = contract["master"], contract["instance"]
            if master in native_masters:
                continue
            leaf = instance.split(".")[-1]
            hits = [(p, a, b, end) for p in stage.iterdir() if not p.name.endswith("_bb.v")
                    for a, b, end in _instance_type_spans(p.read_text(), master, leaf)]
            if len(hits) != 1:
                raise ValueError(f"{master}/{instance}: fixed source instance is ambiguous")
            p, a, _, end = hits[0]
            text = p.read_text()
            p.write_text(text[:a] + master + " " + text[end:])
        changed = []
        for p in paths:
            data = (stage / p.name).read_bytes()
            if p.read_bytes() != data:
                p.write_bytes(data)
                changed.append(p.name)
    result = dict(schema="opentallas.kit_assembly.v1", bindings=bindings,
                  changed_sources=changed, cycles_changed=0,
                  elaborated_inventory="NOT RUN")
    if parent_profile is not None:
        result['parent_profile'] = parent_profile
    if receipt:
        destination = Path(receipt)
        if destination.name == "kit_assembly.json" and destination.resolve().parent == root.resolve().parent:
            runtime = destination.parent / "kit_assembly.py"
            if runtime.resolve() != Path(__file__).resolve():
                shutil.copyfile(__file__, runtime)
            result["runtime_helper"] = runtime.name
        Path(receipt).write_text(json.dumps(result, indent=2) + "\n")
    return result


def hierarchy_inventory(design, top, children, parent_profile=None, required_instances=None):
    """Inspect actual Yosys write_json hierarchy; no synthesis or invented cells.

    Return explicit discrepancies rather than treating a missing planned child
    as soft logic. This is an assembly diagnostic, not a new signoff gate.
    """
    modules = design["modules"]
    if top not in modules:
        raise ValueError(f"top module absent from Yosys hierarchy: {top}")
    cells = []
    def walk(module, prefix, ancestors):
        if module in ancestors:
            raise ValueError(f"recursive module hierarchy: {module}")
        for name, cell in modules[module].get("cells", {}).items():
            path = prefix + "." + name if prefix else name
            kind = cell["type"]
            cells.append(dict(instance=path, master=kind))
            if kind in modules and not int(str(modules[kind].get("attributes", {}).get("blackbox", "0")), 2):
                walk(kind, path, ancestors + (module,))
    walk(top, "", ())
    problems, selected = [], set()
    if parent_profile and parent_profile.get('top') != top:
        problems.append(f"actual parent top {top} differs from selected profile {parent_profile.get('top')}")
    masters = {c["master"] for c in children}
    for child in children:
        name = child["inst"]
        hits = [c for c in cells if c["instance"] == name or c["instance"].endswith("." + name)]
        if len(hits) != 1:
            problems.append(f"{name}: expected one elaborated instance, found {len(hits)}")
        elif hits[0]["master"] != child["master"]:
            problems.append(f"{name}: elaborated {hits[0]['master']}, expected fixed {child['master']}")
        else:
            selected.add(hits[0]["instance"])
    required_found=[]
    for required in required_instances or []:
        name=required['inst']
        hits=[c for c in cells if c['instance']==name or c['instance'].endswith('.'+name)]
        if len(hits)!=1:
            problems.append(f'{name}: expected one factory instance, found {len(hits)}')
            continue
        kind=hits[0]['master']
        original=modules.get(kind,{}).get('attributes',{}).get('hdlname',kind).split()[0].lstrip('\\')
        if kind!=required['master'] and original!=required['master']:
            problems.append(f"{name}: factory instance {kind}, expected {required['master']}")
        else:
            definition=modules.get(kind,{})
            for parameter,expected in required.get('parameters',{}).items():
                value=definition.get('parameter_default_values',{}).get(parameter)
                actual=int(value,2) if isinstance(value,str) and re.fullmatch('[01]+',value) else value
                if actual!=expected:
                    problems.append(f'{name}: actual {parameter}={actual}, expected {expected}')
            if 'register_bits' in required:
                bits=sum(len(c.get('connections',{}).get('Q',[])) for c in definition.get('cells',{}).values()
                         if c['type']=='$dff')
                if bits!=required['register_bits']:
                    problems.append(f"{name}: actual registered bits {bits}, expected {required['register_bits']}")
            required_found.append(hits[0])
    unplanned = [c for c in cells if c["master"] in masters and c["instance"] not in selected]
    problems += [f"unplanned hard instance {c['instance']} ({c['master']})" for c in unplanned]
    return dict(schema="opentallas.kit_hierarchy.v1", top=top,
                expected=len(children), matched=len(selected), problems=problems,
                hard_instances=[c for c in cells if c["master"] in masters],
                required_expected=len(required_instances or []),required_matched=len(required_found),
                required_instances=required_found)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    assemble = commands.add_parser('assemble', help='stage the explicitly sealed fixed-child calls')
    assemble.add_argument("--rtl-dir", required=True)
    inventory = commands.add_parser('inventory', help='inspect post-assembly Yosys write_json hierarchy')
    inventory.add_argument("--yosys-json", required=True)
    inventory.add_argument("--top", required=True)
    for command in (assemble, inventory):
        command.add_argument("--contracts", required=True, help="JSON with children and parameter_contracts")
        command.add_argument("--receipt", required=True)
    args = parser.parse_args()
    contracts = json.loads(Path(args.contracts).read_text())
    if args.command == 'assemble':
        result = assemble_fixed_children(args.rtl_dir, contracts["children"], contracts["parameter_contracts"],
                                         args.receipt, contracts.get('parent_profile'))
    else:
        result = hierarchy_inventory(
            json.loads(Path(args.yosys_json).read_text()), args.top, contracts["children"],
            contracts.get('parent_profile'),contracts.get('required_instances'))
    Path(args.receipt).write_text(json.dumps(result, indent=2) + "\n")
    return 2 if result.get('problems') else 0


if __name__ == "__main__":
    raise SystemExit(main())
