#!/usr/bin/env python3
"""Stage deterministic HEAD kit RTL; this does not enable or launch a wave."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/die_plan'), str(ROOT / 'tools/s81_head')]
from head_count_strap_sites import apply as count_sites
from head_start_raw_private import prepare_plan, patch_rtl as private_patch
from head_start_reset_aliases import patch_rtl as alias_patch

# These profiles require additional native/PMA decisions, beyond this recipe.
HELD = {'hd_serdes', 'hd_ctl', 'hd_ctl_n', 'hd_ctl_e'}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def tokens(text):
    # Preserve quoted strings, attributes, escaped identifiers and every RTL token.
    pieces = re.findall(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|\\\S+|\s+|[^\s]', text)
    return [s for s in pieces if not s.isspace() and not s.startswith(('//', '/*'))]

def write(path, data):
    Path(path).write_text(json.dumps(data, indent=1) + '\n')

def prepare(args):
    source, published, out = args.source.resolve(), args.published.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    plan_path = source / 'source_plan.json'
    plan = json.loads(plan_path.read_text())
    types = args.types.split(',')
    if not types or set(types) & HELD or len(types) != len(set(types)):
        raise ValueError('explicit unique eligible types required; CTL/SerDes remain held')
    for typ in types:
        if typ not in plan['partition_types']:
            raise ValueError('unknown type: ' + typ)
    plan, straps = count_sites(plan, plan_path, ROOT, types=set(types))
    plan, private = prepare_plan(plan, set(types))
    # Copy relative native pin/domain material; never depend on a mutable lane symlink.
    for child in source.iterdir():
        if child.is_dir():
            shutil.copytree(child, out / child.name)
    shutil.copy2(source / 'source_sidecar.json', out / 'source_sidecar.json')
    expected = out / 'published'; expected.mkdir()
    wrappers = {}
    for typ in types:
        module = plan['partition_types'][typ]['module']
        p = published / (module + '.sv')
        shutil.copy2(p, expected / p.name)
        wrappers[typ] = dict(module=module, sha256=digest(p))
    write(out / 'source_plan.json', plan)
    write(out / 'wave_prepare.json', dict(schema='opentallas.head_wave_prepare.v1',
          enabled=False, release=False, eligible_types=types, held_types=sorted(HELD),
          source_plan_sha256=digest(plan_path), prepared_plan_sha256=digest(out / 'source_plan.json'),
          sidecar_sha256=digest(out / 'source_sidecar.json'), published_wrappers=wrappers,
          count_straps=straps, private_exports=private, added_cycles=0))
    print('HEAD_WAVE_PREPARED_DISABLED', out)

def export(args):
    plan_path, out = args.plan.resolve(), args.out.resolve()
    prepared = plan_path.parent
    receipt = json.loads((prepared / 'wave_prepare.json').read_text())
    if args.type in HELD or args.type not in receipt['eligible_types']:
        raise ValueError('type held or not explicitly staged')
    if digest(plan_path) != receipt['prepared_plan_sha256']:
        raise ValueError('prepared plan changed')
    sidecar = prepared / 'source_sidecar.json'
    if digest(sidecar) != receipt['sidecar_sha256']:
        raise ValueError('prepared sidecar changed')
    out.mkdir(parents=True, exist_ok=False)
    plan = json.loads(plan_path.read_text()); t = plan['partition_types'][args.type]
    bootstrap = out / 'bootstrap'
    cmd = [sys.executable, str(ROOT / 'tools/die_plan/gen.py'), 'phys', str(plan_path),
           '--clock-landing', str(sidecar), '--types', args.type, '--out', str(bootstrap),
           '--rtl-root', str(ROOT), '--trial']
    result = subprocess.run(cmd, capture_output=True, text=True)
    (out / 'bootstrap.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError('bootstrap GEN failed: ' + str(result.returncode))
    kit = bootstrap / args.type
    wrapper = bootstrap / '_rtl' / (t['module'] + '.sv')
    text = alias_patch(wrapper.read_text(), t.get('reset_start_raw_exports', []))
    published = prepared / 'published' / wrapper.name
    if digest(published) != receipt['published_wrappers'][args.type]['sha256']:
        raise ValueError('published wrapper changed')
    if tokens(text) != tokens(published.read_text()):
        (out / 'unmatched_preprivate.sv').write_text(text)
        raise ValueError('bootstrap HEAD RTL differs from published source cohort')
    text, private = private_patch(text, t)
    wrapper.write_text(text); (kit / 'rtl' / wrapper.name).write_text(text)
    config = (kit / 'config.mk').read_text().replace('\\\n', ' ')
    def value(name):
        matches = re.findall(r'^export ' + name + r'\s*=\s*(.*)$', config, re.M)
        if len(matches) != 1 or '$' in matches[0]:
            raise ValueError('nonliteral or ambiguous ' + name)
        return matches[0].split()
    files = []
    for path in value('VERILOG_FILES'):
        p = kit / path.removeprefix('/work/') if path.startswith('/work/') else Path(path)
        if not p.is_file():
            raise ValueError('missing exact source closure: ' + str(p))
        files.append(p.resolve())
    (out / 'kit_rtl.f').write_text(''.join(str(p) + '\n' for p in files))
    write(out / 'kit_rtl.json', dict(schema='opentallas.head_wave_kit_rtl.v1', plan_type=args.type,
          defines=value('VERILOG_DEFINES'), added_cycles=0, private_raw=private,
          published_wrapper_sha256=digest(published), source_sha256={str(p): digest(p) for p in files},
          release=False, route_qualified=False, gen_cmd=cmd))
    print('HEAD_WAVE_KIT_RTL_PASS_DISABLED', args.type, len(files))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='mode', required=True)
    q = sub.add_parser('prepare'); q.add_argument('--source', type=Path, required=True)
    q.add_argument('--published', type=Path, required=True); q.add_argument('--out', type=Path, required=True)
    q.add_argument('--types', required=True); q.set_defaults(run=prepare)
    q = sub.add_parser('export'); q.add_argument('--plan', type=Path, required=True)
    q.add_argument('--out', type=Path, required=True); q.add_argument('--type', required=True); q.set_defaults(run=export)
    a = p.parse_args(); a.run(a)
