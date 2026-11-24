#!/usr/bin/env python3
"""Stage deterministic HEAD kit RTL; this does not enable or launch a wave."""
import argparse
import hashlib
import json
import os
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
HELD = set()
TRANSPORT_STRIPS = {'hd_ctl_n', 'hd_ctl_e'}

def check_transport_strip(typ, entry):
    if typ in TRANSPORT_STRIPS and (not entry.get('ft_slots') or any(
            entry.get(k) for k in ('sources', 'contents', 'hard_cores', 'buses'))):
        raise ValueError('CTL strip carries native logic; explicit native recipe required: ' + typ)


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
        check_transport_strip(typ, plan['partition_types'][typ])
    # The reset solver traverses all types, including held profiles. Snapshot
    # every declared native census instead of relying on mutable lane results.
    asset_receipts = {}
    for t in plan['partition_types'].values():
        clock = t.get('clock', {})
        ref = clock.get('sink_bins_file')
        if not ref:
            continue
        if ref not in asset_receipts:
            source_asset = (args.assets / ref if args.assets else ROOT / ref).resolve()
            if not source_asset.is_file():
                raise ValueError('missing exact native sink census: ' + str(source_asset))
            target = out / 'assets' / ('sink_bins_' + str(len(asset_receipts)) + '.json')
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(source_asset, target)
            asset_receipts[ref] = dict(path=str(target), sha256=digest(target))
        clock['sink_bins_file'] = asset_receipts[ref]['path']
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
          native_sink_censuses=asset_receipts, count_straps=straps, private_exports=private, added_cycles=0))
    print('HEAD_WAVE_PREPARED_DISABLED', out)

def census_path(path, prepared):
    """the receipt's census path, else the same tree-relative file under this prepared tree or this tool tree.
    wave_prepare.json records absolute paths of the tree it was prepared in; a live-tree snapshot or a gen host
    without that tree (KIT_NOT_SELF_CONTAINED, hd_host_n / hd_host_w 11-18) holds the identical file at the same
    tree-relative path.  The sha256 check still decides."""
    p = Path(path)
    if p.is_file():
        return p
    parts = p.parts
    if 'physical' in parts:
        rel = Path(*parts[parts.index('physical'):])
        roots = []
        pp = prepared.parts
        if 'physical' in pp:
            roots.append(Path(*pp[:pp.index('physical')]))
        roots.append(ROOT)
        for r in roots:
            if (r / rel).is_file():
                return r / rel
    raise ValueError('missing exact native sink census: ' + str(path))

def tie_audit_record(plan_path, out):
    """-> kit_rtl.json keys naming the bound plan's die-top tie audit (count_strap_evidence.find_audit reads kit_rtl.tie_audit), or {}.

    Candidates: env OT_BIND_TIE_AUDIT, else $OT_KIT_BIND_OUT/tie_audit.json (the private spec's --bind-out, STRAP-EVIDENCE-PRIV-1124),
    else <plan dir>/bind_of_record/tie_audit.json.  A declared source (either env) marks the kit strap_evidence_strict: gen's
    COUNT_STRAP_EVIDENCE_CHECK must then read VERIFIED or the gen fails.  The audit must be PASS and record the
    sha256 of THIS plan (head_die_portbind writes plan_sha256); an audit of another plan is refused.  One without a recorded plan
    sha, or no audit at all, is not named: the kit evidence stays as before.  The file is copied into the kit."""
    env = os.environ.get('OT_BIND_TIE_AUDIT')
    kbo = os.environ.get('OT_KIT_BIND_OUT')       # STRAP-EVIDENCE-PRIV-1124: the private spec's declared bind (kit_wave script mode)
    declared = env or (str(Path(kbo) / 'tie_audit.json') if kbo else None)
    src = Path(declared) if declared else plan_path.parent / 'bind_of_record' / 'tie_audit.json'
    if not src.is_file():
        if declared:
            raise ValueError(('OT_BIND_TIE_AUDIT' if env else 'OT_KIT_BIND_OUT tie_audit.json') + ' does not exist: ' + declared)
        print('HEAD_KIT_TIE_AUDIT NONE'); return {}
    data = src.read_bytes(); doc = json.loads(data)
    want = digest(plan_path); got = doc.get('plan_sha256')
    if not got:
        print('HEAD_KIT_TIE_AUDIT WARN no plan_sha256 recorded, not named:', src); return {}
    if got != want:
        raise ValueError('tie audit %s is of plan %s, the kit plan is %s' % (src, got[:12], want[:12]))
    if doc.get('verdict') != 'PASS':
        raise ValueError('tie audit is not PASS: ' + str(src))
    kept = Path(out) / 'tie_audit.json'; kept.write_bytes(data)
    print('HEAD_KIT_TIE_AUDIT PASS plan', want[:12], src)
    return dict(tie_audit=str(kept), tie_audit_source=str(src), tie_audit_sha256=hashlib.sha256(data).hexdigest(),
                tie_audit_plan_sha256=got, strap_evidence_strict=bool(declared))

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
    censuses = {}
    for ref, asset in receipt.get('native_sink_censuses', {}).items():
        src = census_path(asset['path'], prepared)
        if digest(src) != asset['sha256']:
            raise ValueError('native sink census changed')
        censuses[ref] = (src, asset['sha256'])
    out.mkdir(parents=True, exist_ok=False)
    # KIT self-containment: the verified censuses travel inside the kit, so no later stage reads the
    # prepare-time tree (which a cleanup or a new gen host may not have).
    kit_assets = {}
    for i, (ref, (src, sha)) in enumerate(sorted(censuses.items())):
        dst = out / 'assets' / ('sink_bins_' + str(i) + '.json')
        dst.parent.mkdir(exist_ok=True)
        shutil.copy2(src, dst)
        kit_assets[ref] = dict(path=str(dst), source=str(src), sha256=sha)
    write(out / 'native_sink_censuses.json', kit_assets)
    plan = json.loads(plan_path.read_text()); t = plan['partition_types'][args.type]
    check_transport_strip(args.type, t)
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
    # gen.py --kit-rtl identifies the partition from the first source. ORFS's
    # VERILOG_FILES order puts common cells first, so preserve that closure but
    # explicitly lead with this exact generated partition wrapper.
    wrapper_file = (kit / 'rtl' / wrapper.name).resolve()
    if files.count(wrapper_file) != 1:
        raise ValueError('exact partition wrapper absent/duplicated in source closure')
    files = [wrapper_file] + [f for f in files if f != wrapper_file]
    if args.type == 'hd_ctl':   # DIE-HEAD-59 11-03: the reviewed hd_ctl profile of head_ctl_hk5_kit (dead g_rsel copies)
        from head_ctl_hk5_kit import rsel_fix
        hsf = [p for p in files if p.name == 'ot_s81hd_ctl_hsf0_static.sv']
        if len(hsf) != 1:
            raise ValueError('hd_ctl: hsf0_static absent/duplicated in source closure')
        hsf[0].write_text(rsel_fix(hsf[0].read_text())[0])
    (out / 'kit_rtl.f').write_text(''.join(str(p) + '\n' for p in files))
    write(out / 'kit_rtl.json', dict(schema='opentallas.head_wave_kit_rtl.v1', plan_type=args.type,
          defines=value('VERILOG_DEFINES'), added_cycles=0, private_raw=private,
          published_wrapper_sha256=digest(published), source_sha256={str(p): digest(p) for p in files},
          release=False, route_qualified=False, gen_cmd=cmd, **tie_audit_record(plan_path, out)))
    print('HEAD_WAVE_KIT_RTL_PASS_DISABLED', args.type, len(files))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='mode', required=True)
    q = sub.add_parser('prepare'); q.add_argument('--source', type=Path, required=True)
    q.add_argument('--assets', type=Path, help='exact native source-assets root; defaults to the pinned source checkout')
    q.add_argument('--published', type=Path, required=True); q.add_argument('--out', type=Path, required=True)
    q.add_argument('--types', required=True); q.set_defaults(run=prepare)
    q = sub.add_parser('export'); q.add_argument('--plan', type=Path, required=True)
    q.add_argument('--out', type=Path, required=True); q.add_argument('--type', required=True); q.set_defaults(run=export)
    a = p.parse_args(); a.run(a)
