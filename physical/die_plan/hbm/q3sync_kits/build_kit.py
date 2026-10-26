#!/usr/bin/env python3
"""Build one physical q3 core kit from the qualified synchronous-reset closure.

Use the usual core-generator arguments after --, for example:
  build_kit.py --core edge --profile-dir SCRATCH -- --views VIEWS --view VIEW --out KITS

The plan module, canonical pin mapping, outlines and face-shell policy stay with the
ordinary core generator.  This selects the whole namespaced source closure, never
one sync top plus legacy helpers.  No physical run or geometry approval is implied.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
GEN_REL = 'tools/hbm_b2/q3sync/q3_sync_profile.py'
LIST_REL = 'tools/hbm_b2/q3sync/q3b.files'
TOPS = {
    'body': 'ot_hfd_coll_q3_body_core',
    'edge': 'ot_hfd_coll_q3_edge_core',
    'vm': 'ot_hfd_coll_q3_vm_core',
    'reduce': 'ot_hfd_coll_q2_reduce_core',
    'ring_ag': 'ot_hfd_coll_q2_ring_ag_core',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def literal_ports(text, top):
    """Inventory only a fixed ANSI interface; refuse all unresolved declarations."""
    text = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
    starts = list(re.finditer(r"(?m)^\s*module\s+" + re.escape(top) + r"\b", text))
    if len(starts) != 1:
        raise ValueError("ambiguous or missing profile top")
    tail = text[starts[0].end():].lstrip()
    if not tail.startswith("("):
        raise ValueError("profile interface must have no parameters")
    end = tail.find(");")
    if end < 0:
        raise ValueError("unterminated profile interface")
    header = tail[1:end]
    if "`" in header:
        raise ValueError("preprocessor in profile interface")
    depth = 0
    for directive in re.findall(r"(?m)^\s*`(ifdef|ifndef|endif)\b", text[:starts[0].start()]):
        depth += -1 if directive == "endif" else 1
        if depth < 0:
            raise ValueError("unbalanced interface preprocessor")
    if depth:
        raise ValueError("conditional profile interface")
    decl = re.compile(r"(input|output|inout)\s+(?:(?:wire|reg|logic)\s+)?"
                      r"(?:(?:signed|unsigned)\s+)?"
                      r"((?:\[\s*\d+\s*:\s*\d+\s*\]\s*)*)([A-Za-z_]\w*)")
    ports, seen = [], set()
    for item in header.split(","):
        match = decl.fullmatch(item.strip())
        if not match or match[3] in seen:
            raise ValueError("ambiguous or nonliteral profile declaration: " + item.strip())
        seen.add(match[3])
        dims = re.findall(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", match[2])
        ports.append((match[3], match[1], math.prod(abs(int(a)-int(b))+1 for a,b in dims)))
    if not ports:
        raise ValueError("empty profile interface")
    return ports


def materialize(core, profile_dir, root=REPO):
    """Generate and verify the pinned closure; return recipe, staging map, receipt."""
    root = Path(root).resolve()
    profile_dir = Path(profile_dir).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    census_path = profile_dir / 'census.json'
    subprocess.run([sys.executable, str(root / GEN_REL), '--root', str(root),
                    '--files', LIST_REL, '--out', str(profile_dir / 'rtl'),
                    '--census', str(census_path)], check=True)
    census = json.loads(census_path.read_text())
    if (census['status'] != 'PASS_GENERATED' or census['unclassified_total'] or
            census['unresolved_instantiations'] or not census['inputs_clean_at_commit']):
        raise SystemExit('NOT BUILT: q3sync source closure is incomplete or dirty')
    if census['modules_in_closure'] != 32:
        raise SystemExit('NOT BUILT: qualified q3sync cohort is exactly 32 modules')
    return recipe_from_census(core, census, profile_dir, root)


def recipe_from_census(core, census, profile_dir, root=REPO):
    """Keep source paths repo-relative while staging their generated profile bytes."""
    root, profile_dir = Path(root), Path(profile_dir)
    core_files = census['core_filelists'][core]
    wanted = set(core_files['files'])
    selected = [e for e in census['emitted'] if e['emitted'] in wanted]
    if {e['emitted'] for e in selected} != wanted:
        raise SystemExit('NOT BUILT: missing generated closure file')
    staged, sources = {}, []
    receipt = dict(name='q3sync', generator=GEN_REL, helper_list=LIST_REL,
                   source_commit=census['source_commit'], core=core,
                   modules_in_qualified_closure=32, data_cycle_delta=0,
                   reset='synchronous reset on existing reset pins; no reset logic removed',
                   control_only_datapath_reset='Not established by this mechanical transform; use actual elaborated reset-target audit',
                   source_files={}, generated_files={}, macros={},
                   clock_ports=census['totals_per_core'][core]['clocks']['top_clock_ports'],
                   reset_ports=census['totals_per_core'][core]['clocks']['converted_reset_sources_top_ports'])
    for item in selected:
        rel = item['source']
        p = Path(rel)
        if p.is_absolute() or '..' in p.parts:
            raise SystemExit('NOT BUILT: source path is not repository-relative')
        generated = profile_dir / 'rtl' / item['emitted']
        if not generated.is_file():
            raise SystemExit('NOT BUILT: generated source missing: ' + str(generated))
        sources.append(rel)
        staged[rel] = generated
        receipt['source_files'][rel] = sha(root / rel)
        receipt['generated_files'][rel] = sha(generated)
    for rel in core_files['macros']:
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise SystemExit('NOT BUILT: macro path is not repository-relative')
        sources.append(rel)
        receipt['macros'][rel] = sha(root / rel)
    top = TOPS[core]
    top_source = next(e for e in selected if top in e['modules'])
    generated_top = profile_dir / 'rtl' / top_source['emitted']
    try:
        ports = literal_ports(generated_top.read_text(), top + '__q3sync')
    except ValueError as exc:
        raise SystemExit('NOT BUILT: ' + str(exc)) from exc
    receipt['port_inventory'] = dict(method='fixed literal ANSI header',
                                     top=top+'__q3sync', ports=ports,
                                     source_file=top_source['source'],
                                     source_sha256=sha(generated_top))
    recipe = dict(files=sources, top=top, profile_top=top + '__q3sync', params={}, defines=[],
                  macros=[Path(p).stem for p in core_files['macros']],
                  source_commit=census['source_commit'], source='qualified q3sync closure')
    return recipe, staged, receipt




def canonical_oneclk_map(core, recipe, receipt, native_clocks, root=REPO):
    """Keep every legacy q2 data/reset alias; replace certified clock aggregate."""
    path = Path(root) / 'physical/die_plan/hbm/cores/harden/canonical_ports_split.json'
    types = json.loads(path.read_text())['types']
    candidates = [(k, v) for k, v in types.items() if v.get('top') == TOPS[core]]
    if len(candidates) != 1:
        raise ValueError('ambiguous canonical q2 type')
    key, canonical = candidates[0]
    entries = list(canonical['type_ids'].values())
    if len(entries) != 1:
        raise ValueError('ambiguous canonical q2 interface')
    old = entries[0]['cut_pins']
    native = {n: (d, w) for n, d, w in receipt['port_inventory']['ports']}
    if native.get('clk') != ('input', 1):
        raise ValueError('canonical q2 adapter requires one scalar input clk')
    clocks = set(native_clocks)
    mapping, covered, old_clocks = {}, set(), set()
    for alias, destinations in old.items():
        names = set(destinations)
        if names & clocks:
            if not names <= clocks:
                raise ValueError('mixed clock/data canonical alias')
            old_clocks |= names
            continue
        if len(destinations) != 1:
            raise ValueError('ambiguous canonical data alias')
        port, width = next(iter(destinations.items()))
        if port not in native or native[port][1] != width or port in covered:
            raise ValueError('canonical data alias width/coverage mismatch: ' + alias)
        mapping[alias] = dict(destinations)
        covered.add(port)
    if old_clocks != clocks or covered != set(native) - {'clk'} or 'clk' in mapping:
        raise ValueError('canonical q2 map must cover every exact nonclock port')
    mapping['clk'] = {'clk': 1}
    recipe['canonical_pin_map'] = mapping
    receipt['canonical_pin_map'] = dict(canonical_type=key, source_sha256=sha(path),
        preserved_nonclock_aliases=len(mapping)-1, data_cycle_delta=0,
        map=mapping, physical_clock_pin='clk')
    return recipe, receipt


def stage_physical_macros(recipe, staged, receipt, profile_dir, root=REPO):
    """Use opaque physical SRAMs with the exact provider's fixed ANSI ports.

    Token/simulation filelists retain behavioral providers. Physical LEF/lib
    selection still uses the unchanged recipe macro names and provider paths.
    """
    macro_dir = Path(profile_dir).resolve() / 'physical_macros'
    macro_dir.mkdir(parents=True, exist_ok=True)
    receipt['physical_macros'] = {}
    for rel, provider_hash in receipt['macros'].items():
        provider = Path(root) / rel
        if sha(provider) != provider_hash:
            raise SystemExit('NOT BUILT: macro provider changed: ' + rel)
        text = re.sub(r"//[^\n]*|/\*.*?\*/", "", provider.read_text(), flags=re.S)
        top = Path(rel).stem
        ports = literal_ports(text, top)
        match = re.search(r"(?m)^\s*module\s+" + re.escape(top) + r"\b", text)
        end = text.find(');', match.end()) + 2
        header = text[match.start():end]
        stub = '(* blackbox *) ' + header + '\nendmodule\n'
        if literal_ports(stub, top) != ports:
            raise SystemExit('NOT BUILT: macro header port identity changed: ' + rel)
        out = macro_dir / Path(rel).name
        out.write_text(stub)
        staged[rel] = out
        receipt['physical_macros'][rel] = dict(
            module=top, provider_sha256=provider_hash,
            header_sha256=hashlib.sha256(header.encode()).hexdigest(),
            physical_sha256=sha(out), ports=ports,
            scope='physical opaque macro only; simulation provider unchanged')
    return recipe, staged, receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--core', required=True, choices=TOPS)
    ap.add_argument('--profile-dir', required=True)
    ap.add_argument('--common-clock-dir', help='opt-in qualified one-clock adapters; requires explicit matching plan clock-pin batch')
    ap.add_argument('--diagnostic-plan', action='store_true',
                    help='allow an external scratch plan; not release evidence')
    ap.add_argument('core_args', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    args = a.core_args[1:] if a.core_args[:1] == ['--'] else a.core_args
    if '--view' not in args or '--views' not in args:
        ap.error('ordinary core-generator --view is required after --')
    view = args[args.index('--view') + 1]
    # Select a unique recipe key without mutating the shared recipe tables.
    if '--recipe-key' in args:
        ap.error('--recipe-key is supplied by this source profile')
    views_path = Path(args[args.index('--views') + 1]).resolve()
    views = json.loads(views_path.read_text())
    selected_view = next((v for v in views['view_list'] if v['view'] == view), None)
    allowed = {TOPS[a.core]}
    if a.core in ('reduce', 'ring_ag'):
        allowed.add('ot_hfd_coll_q2_hard_v8g__' + a.core)
    if selected_view is None or selected_view['module'] not in allowed:
        ap.error('selected plan view does not belong to the requested q3 core')
    plan_path = Path(views['plan'])
    if not plan_path.is_absolute():
        plan_path = views_path.parent / plan_path
    if not a.diagnostic_plan:
        for path in (views_path, plan_path.resolve()):
            if not path.is_relative_to(REPO):
                ap.error('external plan requires --diagnostic-plan: ' + str(path))
    recipe, staged, receipt = materialize(a.core, a.profile_dir)
    native_clocks = list(receipt['clock_ports'])
    if a.common_clock_dir:
        sys.path.insert(0, str(REPO / 'tools/hbm_b2/q3sync'))
        from q3_common_clock import adapt_recipe
        recipe, staged, receipt = adapt_recipe(a.core, recipe, staged, receipt, a.common_clock_dir)
        if a.core in ('reduce', 'ring_ag') and selected_view['module'] != TOPS[a.core]:
            recipe, receipt = canonical_oneclk_map(a.core, recipe, receipt, native_clocks)
    recipe, staged, receipt = stage_physical_macros(recipe, staged, receipt, a.profile_dir)
    receipt['diagnostic_inputs'] = bool(a.diagnostic_plan)
    receipt['plan_module'] = selected_view['module']
    p = REPO / 'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
    sys.path.insert(0, str(p.parent))
    sys.path.insert(0, str(REPO / 'tools/die_plan'))
    spec = importlib.util.spec_from_file_location('q3sync_coregen', p)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    sys.argv = [str(p), *args, '--recipe-key', 'q3sync:' + view]
    gen.main(recipe_overrides={'q3sync:' + view: recipe}, source_overrides=staged,
             source_profile=receipt)


if __name__ == '__main__':
    main()
