#!/usr/bin/env python3
"""Opt-in signed-child source PREP and native-gold formal materialization.

No proof or physical stage is launched. Missing actual parent/die producers are
reported as missing inputs, never replaced with a plan-level inventory.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

REPO = Path(__file__).resolve().parents[2]


def shared_adapter():
    path = REPO / 'physical/die_plan/s81/cores/legacy/gen_signed_parent_source.py'
    required(path, 'shared signed parent prepare/stage_contract helper')
    spec = importlib.util.spec_from_file_location('shared_signed_parent_source', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def required(path, producer):
    if not path or not Path(path).is_file():
        raise ValueError(f'missing actual {producer}: {path or "NOT PRODUCED"}')
    return Path(path).resolve()


def modules(path):
    text = shared_adapter()._mask(Path(path).read_text())
    return re.findall(r'\bmodule\s+(\w+)\b', text)


def master_census(readset, selected):
    """Read actual producer source LEFs before basename staging can hide a clash.

    Each producer emits a plain ordered LEF file list from its actual flattened
    readset/config. A list reconstructed from the plan is not accepted evidence.
    The original list itself is hash joined; duplicate paths are harmless.
    """
    readset = required(readset, 'flattened LEF readset')
    paths = []
    raw = readset.read_text()
    if raw.lstrip().startswith('{'):
        entries = json.loads(raw).get('readsets', {}).get('ADDITIONAL_LEFS', [])
        for entry in entries:
            path = required(entry.get('path'), 'actual flattened LEF input')
            if digest(path) != entry.get('sha256'):
                raise ValueError('LEF source differs from actual readset producer')
            if path not in paths:
                paths.append(path)
    else:
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            path = required(line if Path(line).is_absolute() else readset.parent / line, 'flattened LEF input')
            if path not in paths:
                paths.append(path)
    if not paths:
        raise ValueError(f'{readset}: empty flattened LEF readset')
    masters = {}
    for path in paths:
        for name in re.findall(r'^\s*MACRO[ \t]+(\S+)[ \t]*$', re.sub(r'#[^\n]*', '', path.read_text()), re.M):
            if name in masters:
                raise ValueError(f'duplicate actual flattened master {name}: {masters[name]} and {path}')
            masters[name] = str(path)
    for master, lef in selected.items():
        if master not in masters or digest(masters[master]) != digest(lef):
            raise ValueError(f'{readset}: selected qualified master {master} absent or different')
    return dict(readset=str(readset), sha256=digest(readset),
                sources={str(p): digest(p) for p in paths}, masters=masters)


def export_native_view(kit, out, master):
    """Adapt the normal native collector to the existing complete-view schema.

    Boundary measurements are copied verbatim from official SIGNED records;
    the BB is only a physical interface artifact, never a native gold source.
    """
    kit, out = Path(kit), Path(out)
    so_path = required(kit / 'signoff/signoff.json', 'leaf SIGNED record')
    eq_path = required(kit / 'lec/lec.json', 'leaf own-final-netlist equivalence')
    so, eq = json.loads(so_path.read_text()), json.loads(eq_path.read_text())
    if so.get('verdict') != 'SIGNED' or eq.get('verdict') != 'EQUIVALENT' or eq.get('black_boxes'):
        raise ValueError('leaf needs actual SIGNED and own final EQ without logic black boxes')
    if eq.get('top') != master or Path(eq.get('netlist', '')).name != '6_final.v':
        raise ValueError('leaf equivalence is not its own actual final netlist')
    core = json.loads(required(kit / 'core.json', 'native leaf core descriptor').read_text())
    if core.get('module') != master:
        raise ValueError('native leaf module differs')
    if out.exists():
        raise ValueError('refuse existing exported view')
    out.mkdir(parents=True)
    for suffix in ('.lef', '_tt.lib', '_ff.lib'):
        shutil.copyfile(required(kit / 'views' / (master + suffix), 'native leaf view'), out / (master + suffix))
    shutil.copyfile(required(kit / 'pins.json', 'native leaf pins'), out / 'pins.json')
    shutil.copyfile(so_path, out / 'signoff.json')
    shutil.copyfile(eq_path, out / 'lec_post.json')
    insertion = {c: dict(boundary=so['checks']['clock']['by_corner'][c]['pinflops']) for c in ('tt', 'ff')}
    (out / 'insertion.json').write_text(json.dumps(insertion, indent=2) + '\n')
    ports = core['port_decl']
    body = [f'(* blackbox *) module {master}(' + ', '.join(ports) + ');']
    for name, (direction, hi, lo) in ports.items():
        width = '' if hi == lo == 0 else f'[{hi}:{lo}] '
        body.append(f'{direction} wire {width}{name};')
    (out / (master + '_bb.v')).write_text('\n'.join(body + ['endmodule', '']))
    return shared_adapter().signed_view(out, so['policy']['period_ps'])


def prepare_generated_type(P, tn, kd, macros, root=None):
    """Default-off gen_phys consumer; native config/RTL remain the gold readset.

    Stage an alternate physical source config, shared signed mean records and
    exact child sites. Physical execution remains HELD until actual native-parent
    expansion proof and flattened parent/die producer readsets are supplied.
    """
    profile = P.types[tn].get('signed_parent_source')
    if profile is None:
        return None
    if not isinstance(profile, dict) or set(profile) != {'views'} or not profile['views']:
        raise ValueError('signed_parent_source requires only an explicit nonempty views mapping')
    import lec
    import gen_phys
    kd = Path(kd)
    base = Path(root or REPO)
    mapping = {str((base / old).resolve()): str((base / new).resolve())
               for old, new in profile['views'].items()}
    children, used = [], set()
    clock_rows = json.loads(required(kd / 'core_latency.json', 'generated parent measured clock table').read_text())['rows']
    for inst, master, lef, lib, x, y, orient in macros:
        declared = str((base / lef).resolve().parent)
        if declared not in mapping:
            continue
        view = shared_adapter().signed_view(mapping[declared], P.die['period_ps'])
        if master != view['master'] or digest(base / lef) != digest(Path(view['view']) / f'{master}.lef'):
            raise ValueError(f'{inst}: current parent must explicitly select this qualified physical view')
        logical = [c['inst'] for c in P.types[tn].get('hard_cores', [])
                   if gen_phys.content_physical_identity(c)[0] == inst]
        if len(logical) != 1:
            raise ValueError(f'{inst}: unique logical/physical endpoint producer required')
        rows = [r for r in clock_rows if r['inst'] in {inst, logical[0]}]
        if not rows:
            raise ValueError(f'missing actual parent clock/tap producer for child {inst}')
        taps = {r['tap'] for r in rows}
        if len(taps) != 1:
            raise ValueError(f'{inst}: explicit per-clock tap adapter required')
        children.append(dict(inst=inst, logical_inst=logical[0], view=declared, at=[x, y], orient=orient, tap=taps.pop()))
        used.add(declared)
    if used != set(mapping):
        raise ValueError('signed view replacement must match actual generated parent macro inputs')
    env = lec.parse_config(kd)
    sources = [str(required(lec.kpath(kd, p), 'generated native parent source'))
               for p in env['VERILOG_FILES'].split()]
    if env.get('VERILOG_TOP_PARAMS', '').strip():
        raise ValueError('explicit parent parameter specialization producer required')
    out = kd / 'signed_parent'
    if out.exists():
        raise ValueError('refuse existing signed parent PREP output')
    spec = dict(top=env['DESIGN_NAME'], sources=sources, children=children)
    staged, recipe, ledger = shared_adapter().prepare(
        spec, {}, base, out, P.types[tn]['outline_um'], P.die['period_ps'], mapping)
    physical = out / 'physical_rtl'
    physical.mkdir(parents=True)
    paths = []
    for source in staged['sources']:
        source = Path(source)
        target = physical / source.name
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise ValueError('physical source basename collision')
        shutil.copyfile(source, target)
        paths.append('/work/signed_parent/physical_rtl/' + source.name)
    for view in ledger['children'].values():
        source = Path(view['view']) / (view['master'] + '_bb.v')
        shutil.copyfile(source, physical / source.name)
        paths.append('/work/signed_parent/physical_rtl/' + source.name)
    contract = out / 'contract'
    contract.mkdir()
    (contract / 'config.mk').write_text('')
    shared_adapter().stage_contract(contract, spec, ledger, '', clock_only=True)
    actual = {(r['inst'], r['pin']): r for r in clock_rows}
    replacements = {}
    differences = []
    for row in json.loads((contract / 'core_latency.json').read_text())['rows']:
        logical_inst = next(c['logical_inst'] for c in children if c['inst'] == row['inst'])
        current = actual.get((row['inst'], row['pin'])) or actual.get((logical_inst, row['pin']))
        if current is None:
            raise ValueError('actual parent clock pin differs from selected child contract')
        replacements[(current['inst'], row['pin'])] = row
        differences.append(dict(inst=current['inst'], pin=row['pin'], previous=current,
                                signed_replacement=row))
    merged = [replacements.get((r['inst'], r['pin']), r) for r in clock_rows]
    (out / 'physical_core_latency.json').write_text(json.dumps(dict(rows=merged), indent=2)+'\n')
    (out / 'physical_core_latency.txt').write_text(
        '# PREP ONLY: selected signed child means; other rows retain their original labelled basis\n' +
        ''.join(f"{{{r['inst']}}} {{{r['pin']}}} {r['rise_ps']:.6f} {{{r['tap']}}}\n" for r in merged))
    ff_complete = all('ff' in r.get('corners', {}) for r in merged)
    if ff_complete:
        (out / 'physical_core_latency_ff.txt').write_text(
            '# PREP ONLY: FF selected/native measured means\n' +
            ''.join(f"{{{r['inst']}}} {{{r['pin']}}} {r['corners']['ff']['mean_ps']:.6f} {{{r['tap']}}}\n" for r in merged))
    native_config = (kd / 'config.mk').read_text()
    (out / 'native_gold.mk').write_text(native_config)
    # The ordinary config stays native. This alternate physical config is PREP,
    # never the input to a native-parent LEC run.
    blackboxes = sorted(set(env.get('SYNTH_BLACKBOXES', '').split()) | set(recipe['orfs_vars']['SYNTH_BLACKBOXES'].split()))
    (out / 'physical_config.mk').write_text(native_config +
        '\noverride export VERILOG_FILES = ' + ' '.join(paths) +
        '\noverride export SYNTH_BLACKBOXES = ' + ' '.join(blackboxes) +
        '\noverride export OT_CORE_LAT = /work/signed_parent/physical_core_latency.txt\n')
    for name in ('signed_parent_adapter.py', 'signed_parent_synth_prep.sh'):
        shutil.copyfile(required(Path(__file__).with_name(name), 'opt-in source PREP helper'), kd / name)
    guarded = [out / 'physical_config.mk'] + list(physical.iterdir()) + [kd / 'signed_parent_adapter.py', kd / 'signed_parent_synth_prep.sh']
    dependencies = {kd / 'native_bb.py'}
    generated = set()
    if env.get('ADDER_MAP_FILE') == '/work/adder_map_dontuse.v':
        generated.add(kd / 'adder_map_dontuse.v')
        dependencies.add(kd / 'adder_map_dontuse.py')
    dependencies.update(p for p in kd.iterdir() if p.is_file() and p.suffix in ('.tcl', '.py'))
    for value in env.values():
        for name in re.findall(r'/work/[A-Za-z0-9_./+\-]+', value):
            path = Path(lec.kpath(kd, name))
            if path.is_dir():
                dependencies.update(p for p in path.rglob('*') if p.is_file())
            else:
                dependencies.add(path)
    dependencies -= generated
    ledger['generated_synth_inputs'] = [str(p.relative_to(kd)) for p in generated]
    ledger['missing_synth_dependencies'] = [str(p.relative_to(kd)) for p in sorted(dependencies) if not p.is_file()]
    guarded += [p for p in dependencies if p.is_file()]
    ledger['physical_source_guards'] = {str(p.relative_to(kd)): digest(p) for p in set(guarded)}
    ledger.update(status='PREP ONLY; native-parent EQ and actual flattened parent/die census NOT RUN',
                  native_gold_config_sha256=digest(kd / 'config.mk'),
                  native_gold_sources={p: digest(p) for p in sources},
                  physical_config='signed_parent/physical_config.mk',
                  signed_clock_replacements=differences, complete_parent_ff_table=ff_complete,
                  missing_producers=['native parent mapped gate netlist', 'actual flattened parent LEF readset',
                                     'actual flattened die LEF readset', 'actual parent/die TC/BC library readsets', 'standard native-parent expanded-child EQ', 'parent clock compensation/FF qualification'])
    (kd / 'signed_parent_source.json').write_text(json.dumps(ledger, indent=2) + '\n')
    return ledger


def mode_library_census(readset, selected):
    """Actual emitted per-mode source lists, not the selected view in isolation."""
    import lec
    path = required(readset, 'actual TC/BC library readset producer')
    data = json.loads(path.read_text()).get('readsets', {})
    result = dict(producer=str(path), sha256=digest(path), modes={})
    for mode, corner in [('TC_LIB_FILES', 'tt'), ('BC_LIB_FILES', 'ff')]:
        entries = data.get(mode)
        if not entries:
            raise ValueError(f'{path}: missing actual {mode} producer')
        masters, hashes = {}, {}
        for entry in entries:
            source = required(entry.get('path'), f'actual {mode} library')
            if digest(source) != entry.get('sha256'):
                raise ValueError(f'{mode}: source differs from actual readset producer')
            if str(source) in hashes:
                continue
            hashes[str(source)] = digest(source)
            for master in lec.lib_cells(source):
                if master in masters:
                    raise ValueError(f'{mode}: duplicate actual library master {master}')
                masters[master] = str(source)
        for master, view in selected.items():
            expected = Path(view) / f'{master}_{corner}.lib'
            if master not in masters or digest(masters[master]) != digest(expected):
                raise ValueError(f'{mode}: actual consumer does not select qualified {master} {corner.upper()}')
        result['modes'][mode] = dict(masters=masters, sources=hashes)
    return result


def check_synth_prep(kit):
    """Immutable source check; never reuse or interfere with a proof lease."""
    kit = Path(kit).resolve()
    record = json.loads(required(kit / 'signed_parent_source.json', 'signed source PREP ledger').read_text())
    if record.get('missing_synth_dependencies'):
        raise ValueError('missing actual SYNTH producer dependencies: ' + ', '.join(record['missing_synth_dependencies']))
    for name in ('lec_async.pid', 'lec_async.on', 'lec_async.ready', 'lec_async.identity', 'lec/lec.json', 'lec_post/lec.json'):
        if (kit / name).exists():
            raise ValueError('SYNTH PREP requires a fresh owned KIT without an existing proof lease/receipt')
    if digest(kit / 'config.mk') != record['native_gold_config_sha256']:
        raise ValueError('native gold config changed after PREP')
    for source, sha in record['native_gold_sources'].items():
        path = required(source, 'native gold source')
        if not path.is_relative_to(kit) or digest(path) != sha:
            raise ValueError('native gold source changed or leaves owned KIT')
    for relative, sha in record['physical_source_guards'].items():
        path = required(kit / relative, 'physical SYNTH PREP source/helper')
        if not path.is_relative_to(kit) or digest(path) != sha:
            raise ValueError('physical SYNTH PREP source/helper changed')
    return dict(status='SYNTH-only PREP input guards PASS; no EQ/physical release',
                native_gold_config_sha256=record['native_gold_config_sha256'])


def formal_inputs(descriptor):
    """Fail closed until genuine native gold, mapped parent and both readsets exist."""
    import lec
    d = descriptor
    native = d.get('native_kit')
    if not native or not (Path(native) / 'config.mk').is_file():
        raise ValueError(f'missing actual native parent KIT producer: {native or "NOT PRODUCED"}')
    native = Path(native).resolve()
    env = lec.parse_config(native)
    parent = required(d.get('parent_gate_netlist'), 'physical parent mapped netlist producer')
    files = [required(lec.kpath(native, f), 'native parent gold readset source') for f in env['VERILOG_FILES'].split()]
    selected, children, joined = {}, [], {}
    for child in d.get('children', []):
        view = shared_adapter().signed_view(required(child.get('view_signoff'), 'selected view signoff').parent)
        master = view['master']
        packet_path = required(child.get('qualified_packet'), 'qualified child source-proof packet')
        packet = json.loads(packet_path.read_text())
        netlist = required(child.get('final_netlist'), 'qualified child own final netlist producer')
        if packet.get('module') != master or packet.get('parameters') != {} or child.get('parameters', {}) != {}:
            raise ValueError('only exact parameter-free qualified child expansion is currently supported')
        if child.get('port_aliases', {}) or packet.get('added_cycles') != 0:
            raise ValueError('endpoint adapter/latency producer required; no guessed alias or cycle contract')
        if packet.get('leaf_release_qualified') is not True:
            raise ValueError('child packet is not qualified')
        key = next((k for k in packet['backing_artifact_sha256'] if k.endswith('/6_final.v')), None)
        if key is None or digest(netlist) != packet['backing_artifact_sha256'][key]:
            raise ValueError('gate child netlist differs from qualified actual final netlist')
        if modules(netlist) != [master] or master in modules(parent):
            raise ValueError('child final module identity missing or parent gate defines it twice')
        defs = [p for p in files if master in modules(p)]
        if len(defs) != 1 or re.search(r'\bblackbox\b', defs[0].read_text()):
            raise ValueError(f'{master}: native gold implementation missing/ambiguous/blackboxed')
        if master in env.get('SYNTH_BLACKBOXES', '').split():
            raise ValueError(f'{master}: native GOLD explicitly blackboxed')
        expected = packet.get('canonical_source_sha256', {})
        for path, sha in expected.items():
            matches = [p for p in files if p.name == Path(path).name]
            if len(matches) != 1 or digest(matches[0]) != sha:
                raise ValueError(f'qualified child native source-proof join missing: {path}')
        for suffix in ('.lef', '_tt.lib', '_ff.lib'):
            name = master + suffix
            expected_hash = [v for k, v in packet.get('views', {}).items() if k.endswith('/' + name)]
            if len(expected_hash) != 1 or digest(Path(view['view']) / name) != expected_hash[0]:
                raise ValueError(f'{master}: actual selected view differs from qualified packet: {name}')
        eq_hash = packet['backing_artifact_sha256'].get('lec/lec.json')
        if digest(Path(view['view']) / 'lec_post.json') != eq_hash:
            raise ValueError(f'{master}: own-final proof record differs from qualified packet')
        selected[master] = Path(view['view']) / f'{master}.lef' 
        children.append((master, netlist))
        joined[str(packet_path)] = digest(packet_path)
        joined[str(netlist)] = digest(netlist)
    if not children or len({m for m, _ in children}) != len(children):
        raise ValueError('one exact qualified implementation per child master required')
    census = {side: master_census(d.get(side + '_lef_readset'), selected) for side in ('parent', 'die')}
    mode_census = {side: mode_library_census(d.get(side + '_mode_readset'), {m: str(Path(p).parent) for m,p in selected.items()}) for side in ('parent','die')}
    # Standard LEC may cut actual shared memories only. Logic implementations
    # must remain present on native gold and expanded gate sides.
    srcmods = {m for f in files for m in lec.src_modules(f)}
    unresolved = {m for lib in lec.macro_libs(env, native) for m in lec.lib_cells(lib)} - srcmods
    declared_bbs = {m for f in files for m in re.findall(r'\(\*[^*]*\bblackbox\b[^*]*\*\)\s*module\s+(\w+)', f.read_text(), re.S)}
    memory = set(d.get('shared_memory_masters', []))
    synth_bbs = set(env.get('SYNTH_BLACKBOXES', '').split())
    if unresolved | declared_bbs | synth_bbs != memory or any(not re.search(r'(?:sram|rom)', m, re.I) for m in memory):
        raise ValueError(f'non-memory or unmatched native blackbox set: {sorted(unresolved | declared_bbs | synth_bbs)}')
    for include in env.get('VERILOG_INCLUDE_DIRS', '').split():
        if not include.startswith('/work/'):
            raise ValueError('native external include directory needs a self-contained producer KIT')
    if len({f.name for f in files}) != len(set(files)):
        raise ValueError('native gold source basename collision')
    joined.update({str(p): digest(p) for p in files + [parent, native / 'config.mk']})
    return native, env, files, parent, children, dict(inputs=joined, actual_flattened=census, actual_mode_libraries=mode_census)


def materialize_formal(descriptor, out):
    """Materialize only; caller runs the unchanged standard lec.py separately."""
    import lec
    native, env, files, parent, children, record = formal_inputs(descriptor)
    out = Path(out)
    if out.exists():
        raise ValueError('refuse existing formal KIT')
    out.mkdir(parents=True)
    for p in native.iterdir():
        if p.is_file() and p.name != 'config.mk' and not p.name.startswith('run_'):
            shutil.copyfile(p, out / p.name)
    for dirname in ('rtl', 'macros'):
        if (native / dirname).is_dir():
            shutil.copytree(native / dirname, out / dirname)
    # Native source bytes are copied unchanged; only paths are rebased. Child abstract
    # logic libraries are removed only from the formal config; actual memories
    # remain. The source implementations are never replaced with BB headers.
    config = (native / 'config.mk').read_text()
    masters = {m for m, _ in children}
    for master in masters:
        for suffix in ('_tt.lib', '_ff.lib', '_typ.lib'):
            config = config.replace('/work/macros/' + master + suffix, '')
    gold = out / 'native_gold'
    gold.mkdir()
    staged = []
    for source in files:
        target = gold / source.name
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise ValueError(f'native gold source basename collision: {source.name}')
        shutil.copyfile(source, target)
        staged.append('/work/native_gold/' + source.name)
    config += '\noverride export VERILOG_FILES = ' + ' '.join(staged) + '\n'
    (out / 'config.mk').write_text(config)
    gate = out / 'expanded_parent_gate.v'
    gate.write_text(parent.read_text() + '\n' + '\n'.join(p.read_text() for _, p in children))
    record.update(status='PREP ONLY; standard native-parent EQ NOT RUN', top=env['DESIGN_NAME'],
                  gate_netlist=str(gate), child_masters=sorted(masters), native_gold_unchanged=True)
    (out / 'native_parent_formal_inputs.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formal-descriptor')
    parser.add_argument('--check-synth-prep')
    parser.add_argument('--out')
    args = parser.parse_args()
    try:
        if args.check_synth_prep:
            result = check_synth_prep(args.check_synth_prep)
        elif args.formal_descriptor and args.out:
            result = materialize_formal(json.loads(Path(args.formal_descriptor).read_text()), args.out)
        else:
            raise ValueError('use --check-synth-prep KIT or --formal-descriptor JSON --out KIT')
    except (ValueError, KeyError, OSError) as exc:
        raise SystemExit(f'HELD: {exc}')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
