"""Explicit new-record recovery of a lost hold ECO; parent history is immutable."""
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

SCHEMA = 'opentallas.closure_loop.infra-eco-continuation.v1'
SHA = re.compile(r'[0-9a-f]{64}')
NAME = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]*')
ALLOWED = {'verdict', 'hold_eco', 'eco_install', 'collect', 'export', 'commit', 'summary'}


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''): h.update(block)
    return h.hexdigest()


def relative(path):
    p = Path(path)
    if p.is_absolute() or not p.parts or any(x in ('.', '..') for x in p.parts):
        raise ValueError('expected confined relative input path')
    return p



# Narrow, reviewed proof: original committed gate readset + frozen route plan +
# exact old hold/TT/hold transformation. Other sources require their own review.
APPROVED_SOURCE_PROOFS = {
    'f51f4ec42ca6f555ae0bb93558d1c485cee732c2':
        '868b3cc1eea80beb9febb38785e8bc7d3c1f02464a8790ad5eb57f5687a36c8c',
}


def expected_source_hashes(parent, manifest):
    proof = manifest.get('canonical_source_readset')
    if (not isinstance(proof, dict) or proof.get('schema') != 'opentallas.canonical-source-readset.v1'
            or proof.get('source_commit') != parent.get('commit_full')
            or canonical_sha(proof) != APPROVED_SOURCE_PROOFS.get(parent.get('commit_full'))):
        raise ValueError('canonical expected source-readset proof missing or not approved for original source')
    if any(manifest.get('runtime', {}).get(k) != v for k,v in proof['approved_runtime'].items()):
        raise ValueError('canonical runtime image or complete loaded-library inventory differs')
    if canonical_sha(parent.get('route_overlay_plan')) != proof['frozen_overlay_plan_sha256']:
        raise ValueError('canonical source frozen overlay plan differs')
    expected = dict(proof['gate_files'])
    expected.update(proof['frozen_files'])
    for path, transform in proof['transformed_templates'].items():
        relative(path)
        if expected.get(path) != transform['before_sha256']:
            raise ValueError('canonical transformation input differs: '+path)
        # Only the literal source-root parameter in the pinned deterministic output
        # may vary; neither arbitrary file exceptions nor caller transforms qualify.
        data = transform['utf8'].replace('@@EXACT_SOURCE_ROOT@@', str(Path(manifest['runtime']['run'])/'src'))
        expected[path] = hashlib.sha256(data.encode()).hexdigest()
    return {'src/'+path: sha for path, sha in expected.items()}


def validate_source_readset(parent, manifest):
    expected = expected_source_hashes(parent, manifest)
    validate_checkpoint_inputs(manifest)
    actual = {p:h for p,h in manifest.get('file_hashes', {}).items() if p.startswith('src/')}
    if actual != expected:
        missing = sorted(expected.keys()-actual.keys())
        changed = sorted(p for p in expected.keys() & actual.keys() if expected[p]!=actual[p])
        extra = sorted(actual.keys()-expected.keys())
        raise ValueError('canonical source readset differs: missing=%s changed=%s extra=%s' %
                         (missing[:3], changed[:3], extra[:3]))
    return expected



def expected_checkpoint_hashes(manifest):
    proof=manifest['canonical_source_readset']
    corner=copy.deepcopy(proof['corner_sta_original'])
    corner['orfs_dir']=str(Path(manifest['runtime']['run'])/Path(proof['checkpoint']['route_base']).parents[3])
    hashes=dict(proof['immutable_input_hashes'])
    hashes[proof['checkpoint']['corner_sta']]=hashlib.sha256((json.dumps(corner,sort_keys=True,indent=1)+'\n').encode()).hexdigest()
    return hashes


def validate_checkpoint_inputs(manifest):
    proof=manifest['canonical_source_readset']
    if manifest.get('checkpoint') != proof['checkpoint'] or manifest.get('post_sdc_files') != proof['post_sdc_files']:
        raise ValueError('canonical checkpoint/config/SDC binding differs')
    for path,sha in expected_checkpoint_hashes(manifest).items():
        if manifest.get('file_hashes',{}).get(path)!=sha:
            raise ValueError('canonical original checkpoint/config or exact corner path-only rebase differs: '+path)


def build(parent, manifest, new_name):
    """Pure preparation: no daemon/state/remote writes and no EDA launches."""
    m = copy.deepcopy(manifest)
    if m.get('schema') != SCHEMA or m.get('operation') != 'lost_hold_eco':
        raise ValueError('unsupported continuation operation')
    if not NAME.fullmatch(new_name) or new_name == parent['name']:
        raise ValueError('new distinct record name required')
    link = m.get('parent', {})
    if (link.get('name') != parent['name'] or link.get('state_sha256') != canonical_sha(parent)
            or link.get('source_commit') != parent.get('commit_full')):
        raise ValueError('immutable parent state/source does not match')
    if (parent.get('status') != 'CANCELLED' or not parent.get('cancelled_at')
            or not re.search(r'EPYC\d*[-_ ]RETIRE|scheduled.*retire', parent.get('reason', ''), re.I)
            or m.get('infrastructure_cause') != 'scheduled_retirement'):
        raise ValueError('only explicitly identified infrastructure retirement is supported')
    physics = m.get('physical_disposition', {})
    pre = (parent.get('eco') or {}).get('pre') or {}
    if (physics.get('kind') != 'hold_only' or physics.get('source_structural_required') is not False
            or physics.get('setup_tt_ps') != pre.get('ss_ps')
            or physics.get('hold_ff_ps') != pre.get('ff_ps')
            or type(pre.get('ss_ps')) not in (float, int) or not math.isfinite(pre['ss_ps']) or pre['ss_ps'] < 0
            or type(pre.get('ff_ps')) not in (float, int) or not math.isfinite(pre['ff_ps']) or pre['ff_ps'] >= 0
            or (parent.get('eco') or {}).get('result') is not None
            or parent.get('metrics', {}).get('drc') != 0
            or physics.get('drc') != 0 or (parent.get('eco') or {}).get('installed')):
        raise ValueError('measured source/setup/DRC failure is not a lost hold ECO')
    if not (parent.get('eco') or {}).get('started') or m.get('interrupted_eco_checkpoint') != 'none':
        raise ValueError('lost ECO must have started without a durable ECO checkpoint')
    if not parent.get('benches') or not all(x.get('ok') is True for x in parent['benches'].values()):
        raise ValueError('original source-bound benchmarks are incomplete')
    runtime = m['runtime']; run = Path(runtime['run'])
    if (not run.is_absolute() or '..' in run.parts or run.name != new_name or str(run) == parent['run']
            or str(run).startswith(parent['run'].rstrip('/')+'/')):
        raise ValueError('runtime must be an exclusive distinct new record root')
    if type(runtime.get('ram_gb')) is not int or runtime['ram_gb'] <= 0:
        raise ValueError('positive admitted runtime RAM required')
    image = runtime['image']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image) or not runtime.get('library_hashes'):
        raise ValueError('new immutable image and exact loaded-library hashes required')
    hashes = m.get('file_hashes') or {}
    for path, expected in hashes.items():
        relative(path)
        if not isinstance(expected, str) or not SHA.fullmatch(expected): raise ValueError('invalid input SHA')
    if not any(x.startswith('src/rtl/') for x in hashes) or not any(x.startswith('cl/') for x in hashes):
        raise ValueError('exact restored source and frozen helpers required')
    for entry in parent.get('route_overlay_plan', {}).get('files', []):
        if hashes.get('cl/'+Path(entry['path']).name) != entry['sha256']:
            raise ValueError('frozen helper SHA missing or changed: '+entry['path'])
    if not parent.get('freeze_helper_overlay') or not parent.get('route_overlay_plan', {}).get('files'):
        raise ValueError('source-bound frozen helper plan required')
    validate_source_readset(parent, m)
    cp = m['checkpoint']; base = relative(cp['route_base'])
    if cp['config'] != str(base.parents[3]/'config.mk'):
        raise ValueError('original route configuration location differs')
    if cp.get('kind') != '5_2_route' or cp.get('eco_odb') != str(base/'5_2_route.odb'):
        raise ValueError('actual original 5_2 route checkpoint required')
    required = [str(base/x) for x in ('5_2_route.odb','6_final.odb','6_final.spef','6_final.sdc')]
    required += [cp['config'], cp['corner_sta'], *m.get('post_sdc_files', [])]
    if not m.get('post_sdc_files') or any(x not in hashes for x in required):
        raise ValueError('checkpoint/config/signoff/reference input hash missing')
    for path, expected in runtime['library_hashes'].items():
        if not path.startswith('/OpenROAD-flow-scripts/') or not SHA.fullmatch(expected):
            raise ValueError('unbound immutable-image library')
    if not m.get('source_completeness', {}).get('known_required_source_bytes_missing') == []:
        raise ValueError('known required source bytes remain missing')
    old_run = parent['run']
    def relocate(x):
        if isinstance(x, dict): return {k: relocate(v) for k,v in x.items()}
        if isinstance(x, list): return [relocate(v) for v in x]
        return x.replace(old_run, str(run)) if isinstance(x,str) else x
    spec = relocate(copy.deepcopy(parent['spec'])); old_label = parent['name'].replace('-', '_')
    def fixed_label(x):
        if isinstance(x,dict): return {k:fixed_label(v) for k,v in x.items()}
        if isinstance(x,list): return [fixed_label(v) for v in x]
        return x.replace('{LABEL}', old_label) if isinstance(x,str) else x
    spec = fixed_label(spec); spec['name'] = new_name
    # Keep frozen route/bench templates for normal kit/reset/native/clock policy discovery.
    # Execution starts at verdict, with the production launch allowlist preventing rollback.
    cal=spec['stages'].get('calibrate') or {}
    if cal.get('cmd') and cal.get('enabled',True):
        raise ValueError('parallel calibration is not part of a lost hold ECO')
    spec['hold_eco'] = dict(spec.get('hold_eco') or {}, enabled=True, allow_fresh_grt=False, vtswap=False, combo=False)
    spec['auto_react'] = False
    spec['peak_ram_gb'] = max(spec.get('peak_ram_gb',0), runtime['ram_gb'])
    spec['mem_cap_gb'] = runtime['ram_gb']  # explicit new runtime cap; no generic factor-four expansion
    guard = str(run/'cl/linked_infra_eco/inputs.json')
    j = dict(name=new_name, spec=spec, origin='linked-infrastructure-continuation',
             status='READY', stage_key='verdict', attempt=parent['attempt']+1,
             retries_used=0, benches={k:dict(copy.deepcopy(v),inherited_from=parent['name']) for k,v in parent['benches'].items()},
             bench_par=False, hosts_tried=[runtime['host']],
             host=runtime['host'], run=str(run), commit_full=parent['commit_full'],
             source_synced=True, freeze_helper_overlay=True,
             route_overlay_plan=copy.deepcopy(parent['route_overlay_plan']),
             pinflop_ref_applied=parent.get('pinflop_ref_applied',False),
             metrics=relocate(copy.deepcopy(parent['metrics'])), events=[], errors=[],
             eco_overlay_recovery=dict(guard=guard,out=str(run/'cl/linked_infra_eco/candidate')),
             linked_infra_eco=dict(parent=link,manifest=m,manifest_sha256=canonical_sha(m),
                 inherited_benches=copy.deepcopy(parent['benches']),
                 historical_provenance=m.get('historical_provenance',{})))
    for key in ('clock_rule','kit_reset_ports','submit_checks'):
        if key in parent:j[key]=copy.deepcopy(parent[key])
    return j


def pinned_env(job):
    """Pin override-aware helpers, and fail closed for frozen helpers using the two legacy aliases."""
    import shlex
    link = job.get('linked_infra_eco')
    if not link: return ''
    image=link['manifest']['runtime']['image']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',image): raise ValueError('invalid pinned runtime image')
    out='export ORFS_IMAGE='+shlex.quote(image)+'\n'
    for alias in ('openroad/orfs:asap7lock','openroad/orfs:latest'):
        out+='[ "$(docker image inspect --format \'{{.Id}}\' '+shlex.quote(alias)+')" = '+shlex.quote(image)+' ] || exit 86\n'
    return out


def verify_runtime(manifest):
    """Read-only verification of already restored fresh runtime; never copy or mutate a parent."""
    r = manifest['runtime']; root = Path(r['run']); canonical_root=root.resolve()
    declared = {p for p in manifest['file_hashes'] if p.startswith('src/')}
    actual = {str(p.relative_to(root)) for p in (root/'src').rglob('*')
              if p.is_file() or p.is_symlink()}
    if actual != declared:
        raise ValueError('actual source path set differs from canonical readset: extra=%s missing=%s' %
                         (sorted(actual-declared)[:3], sorted(declared-actual)[:3]))
    for rel, expected in manifest['file_hashes'].items():
        p = root/relative(rel)
        if not p.resolve().is_relative_to(canonical_root) or file_sha(p) != expected:
            raise ValueError('restored input differs: '+rel)
    cp=manifest['checkpoint']
    measured=json.loads((root/cp['corner_sta']).read_text())
    expected_orfs=str(root/relative(cp['route_base']).parents[3])
    if measured.get('orfs_dir') != expected_orfs:
        raise ValueError('corner STA still points outside restored route; explicit path-only rebase required')
    if (root/'cl/SRC_DIR').read_text().strip() != str(root/'src'):
        raise ValueError('restored SRC_DIR still refers to old runtime')
    actual = subprocess.check_output(['docker','image','inspect',r['image'],'--format','{{.Id}}'],text=True).strip()
    if actual != r['image']: raise ValueError('immutable runtime image differs')
    for alias in ('openroad/orfs:asap7lock','openroad/orfs:latest'):
        if subprocess.check_output(['docker','image','inspect',alias,'--format','{{.Id}}'],text=True).strip()!=actual:
            raise ValueError('frozen helper image alias differs: '+alias)
    code = 'import hashlib,json,sys;d=json.loads(sys.argv[1]);' \
           'assert all(hashlib.sha256(open(p,"rb").read()).hexdigest()==h for p,h in d.items()),"library SHA differs"'
    subprocess.run(['docker','run','--rm','--entrypoint','python3',r['image'],'-c',code,
                    json.dumps(r['library_hashes'])],check=True,capture_output=True)
    return dict(verified=True,manifest_sha256=canonical_sha(manifest),files=len(manifest['file_hashes']),image=actual)


def prepare_runtime(manifest, parent):
    root_resolved = Path(manifest['runtime']['run']).resolve()
    parent_resolved = Path(parent['run']).resolve()
    if root_resolved.is_relative_to(parent_resolved) or parent_resolved.is_relative_to(root_resolved):
        raise ValueError('runtime aliases immutable parent tree or its ancestor')
    validate_source_readset(parent, manifest)
    result = verify_runtime(manifest)
    root = Path(manifest['runtime']['run']); dest = root/'cl/linked_infra_eco'; dest.mkdir()
    (dest/'parent_state.json').write_text(json.dumps(parent,indent=1)+'\n')
    (dest/'restoration_manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
    # Existing frozen eco_recovery.py verifies these before ECO and installation.
    guard = dict(hashes={str(root/p):h for p,h in manifest['file_hashes'].items()},
                 source_commit=parent['commit_full'],job=parent['name'])
    (dest/'inputs.json').write_text(json.dumps(guard,indent=1)+'\n')
    return result


if __name__ == '__main__':
    import sys
    request=json.loads(sys.argv[2])
    result=verify_runtime(request['manifest']) if sys.argv[1]=='verify' else prepare_runtime(request['manifest'],request['parent'])
    print(json.dumps(result))
