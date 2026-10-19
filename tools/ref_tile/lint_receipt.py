"""Kit CDC-lint receipts: the reviewed CDC lints run once per input set, on the fleet, never on localhost.

Why (ROOT-LINT 2026-10-18, lanes/HBM-WBK.md): kit generation (ref_tile.py gen, and its regeneration inside
pre_route_gate / submit_exact) elaborated the reviewed CDC lint on LOCALHOST on every gen, gate and submit -- up to
41 GB / ~22 min for ot_hbm_svc_wb_kport_q -- against the no-local-heavy-work rule.

``record(policy, lint, error, spec, root)`` returns the lint record the SDC generators bind:

  1. key = sha256 of (policy, the lint-relevant spec fields, the sha256 of every lint input file -- the spec sources
     and the declared macros' Liberty views --, the sha256 of the lint tool modules, and ``yosys -V``);
  2. a receipt ``physical/ref_tile/<name>/lint_receipt.json`` whose entry for the policy carries that exact key is
     reused (its record is the result of the same lint over the same bytes with the same tool);
  3. otherwise the lint runs on the fleet through ``ot-run`` (memory-admitted, any host; OT_LINT_MEM GB, default 48).
     The remote runner recomputes the key over the shipped bytes and its own Yosys and refuses on any difference, so a
     receipt can only record the lint of exactly the keyed inputs. A failing lint raises the policy's error with the
     remote message; failures are never cached.

The lint runs locally only with OT_LINT_LOCAL=1 (the remote runner itself), where no ot-run client exists (a fleet
host), or for fixture roots under the temp directory (unit tests). Gate-Rule neutral: the same lint, on the same bytes, with the same result, is required.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import io
import tarfile
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = 'opentallas.ref_tile.lint_receipt.v1'
RECEIPT = 'lint_receipt.json'
KIT_ROOT = 'physical/ref_tile'
# the lint reads exactly these spec fields (gray_fifo_cdc_constraints / cdc_sync_constraints, incl. relationship(),
# validate(), Netlist and clock_entry_constraints.signoff_period / native_leaf); the remote lint gets ONLY these, so the
# record is a function of the keyed projection by construction
SPEC_KEYS = ('name', 'top', 'kind', 'sources', 'params', 'clock', 'clock_entry_domains', 'clock_relationship',
             'clock_data_paths', 'cdc_synchronizers', 'reviewed_gray_fifo_extensions', 'macros', 'children',
             'defines', 'hard_define', 'hard_defines', 'orfs_vars', 'sdc_extra', 'boundary_tcl', 'pre_cts_extra',
             'forwarded_clock', 'single_clock_contract')
ROUTE_KEYS = ('signoff_period_ps', 'period_ps')          # clock_entry_constraints.signoff_period reads both
# every module the lints execute (cdc_sync_constraints.periods imports clock_entry_constraints)
TOOL_FILES = ('gray_fifo_cdc_constraints.py', 'cdc_sync_constraints.py', 'clock_entry_constraints.py', 'single_clock_contract.py')
DEFAULT_MEM_GB = 48
REMOTE_PARENT = '/srv/opentallas-scratch/claude/kit_lint'
_MEMO = {}


def projection(spec):
    p = {k: spec[k] for k in SPEC_KEYS if k in spec}
    if spec.get('seam_windows') is not None:
        # Mixed CDC/calendar lint must see (and fingerprint) the complete window and actual root names.
        for k in ('seam_windows', 'clock_port', 'clock_ports'):
            if k in spec:
                p[k] = spec[k]
    if any(isinstance(spec.get(k), dict) and spec[k].get('enable') is True
           for k in ('pin_regs', 'reset_landing')):
        for k in ('pin_regs', 'reset_landing'):
            if k in spec:
                p[k] = spec[k]
    route = {k: spec['route'][k] for k in ROUTE_KEYS if k in spec.get('route', {})}
    if route:
        p['route'] = route
    return json.loads(json.dumps(p, sort_keys=True, default=list))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def input_files(spec, root):
    """repo-relative lint inputs: the sources and every declared macro's Liberty views"""
    root = Path(root).resolve()
    files = list(spec.get('sources', []))
    if spec.get('single_clock_contract'):
        from single_clock_contract import evidence_paths
        files += evidence_paths(spec)
    for item in spec.get('macros', []):
        if isinstance(item, dict) and isinstance(item.get('view'), str):
            view = root / item['view']
            files += sorted(str(p.relative_to(root)) for p in view.glob(f'{view.name}_*.lib'))
    return files


def yosys_version(yosys):
    run = subprocess.run([yosys, '-V'], capture_output=True, text=True)
    return (run.stdout or run.stderr).strip()


def components(policy, spec, root, yosys):
    root = Path(root).resolve()
    return {'policy': policy, 'spec': projection(spec),
            'inputs': {f: _sha(root / f) for f in input_files(spec, root)},
            'tool': {f: _sha(HERE / f) for f in TOOL_FILES}, 'yosys': yosys_version(yosys)}


def key_of(comp):
    return hashlib.sha256(json.dumps(comp, sort_keys=True).encode()).hexdigest()


def receipt_path(spec, root):
    name = spec.get('name')
    return Path(root) / KIT_ROOT / name / RECEIPT if isinstance(name, str) and re.fullmatch(r'[a-z0-9][a-z0-9_]*', name) else None


def load(path):
    if path is None:
        return {}
    try:
        doc = json.loads(Path(path).read_text())
        return doc if doc.get('schema') == SCHEMA else {}
    except (OSError, ValueError):
        return {}


def lookup(spec, root, policy, key):
    entry = load(receipt_path(spec, root)).get('lints', {}).get(policy)
    return entry['record'] if isinstance(entry, dict) and entry.get('key') == key and 'record' in entry else None


def store(spec, root, policy, key, comp, record, provenance):
    path = receipt_path(spec, root)
    if path is None or not path.parent.is_dir():
        return None            # no kit directory (fixture roots): nothing to store with
    doc = load(path) or {'schema': SCHEMA, 'lints': {}}
    doc['lints'][policy] = {'key': key, 'components': comp, 'record': record, **provenance}
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    return path


def ot_run():
    return shutil.which('ot-run') or next((str(p) for p in [Path.home() / 'bin/ot-run'] if p.is_file()), None)


def local_allowed(root=None):
    """local lint only for OT_LINT_LOCAL=1 (the remote runner), hosts without an ot-run client (fleet hosts), and
    fixture roots under the temp directory (unit tests: a few-cell netlist, never a kit)"""
    if os.environ.get('OT_LINT_LOCAL') == '1' or ot_run() is None:
        return True
    return root is not None and Path(root).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())


def record(policy, lint, error, spec, root, yosys):
    """the lint record for (policy, spec, root): memo -> matching receipt -> local (allowed only off localhost) -> fleet"""
    comp = components(policy, spec, root, yosys)
    key = key_of(comp)
    if key in _MEMO:
        return _MEMO[key]
    rec = lookup(spec, root, policy, key)
    if rec is None:
        t0 = time.time()
        if local_allowed(root):
            rec, prov = json.loads(json.dumps(lint(projection(spec), root))), {'host': os.uname().nodename}
        else:
            rec, prov = remote(policy, spec, root, key, error)
        prov.update(seconds=round(time.time() - t0), created=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
        where = store(spec, root, policy, key, comp, rec, prov)
        if where:
            print(f'lint_receipt: {policy} {spec["name"]}: lint ran on {prov["host"]} ({prov["seconds"]} s); '
                  f'receipt {where} (commit it with the kit)', file=sys.stderr)
    _MEMO[key] = rec
    return rec


# ------------------------------------------------------------------------------------------------------------ fleet
def payload(policy, spec, root, key):
    root = Path(root).resolve()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            tar.addfile(info, io.BytesIO(data))
        for p in sorted(HERE.glob('*.py')):
            add(f'tools/ref_tile/{p.name}', p.read_bytes())
        # clock_entry_constraints (imported by the lints) imports tools/hier_contract/child_lint at module load
        for p in sorted((HERE.parent / 'hier_contract').glob('*.py')):
            add(f'tools/hier_contract/{p.name}', p.read_bytes())
        for f in input_files(spec, root):
            add(f, (root / f).read_bytes())
        add('lint_job.json', json.dumps({'policy': policy, 'spec': projection(spec), 'key': key}).encode())
    return buf.getvalue()


def remote(policy, spec, root, key, error):
    client = ot_run()
    mem = int(os.environ.get('OT_LINT_MEM', DEFAULT_MEM_GB))
    data = payload(policy, spec, root, key)
    run_dir = f'{REMOTE_PARENT}/{spec.get("name", "kit")}-{key[:12]}-{os.getpid()}'
    print(f'lint_receipt: {policy} {spec.get("name")}: no matching receipt; running the lint on the fleet '
          f'(ot-run, {mem} GB)', file=sys.stderr)
    pick = [client, '--mem', str(mem), '--threads', '1', '--disk', '2', '--dir', '/srv/opentallas-scratch', '--pick']
    tried = []
    for _ in range(6):
        picked = subprocess.run(pick, capture_output=True, text=True)
        host = picked.stdout.strip().splitlines()[-1] if picked.returncode == 0 and picked.stdout.strip() else ''
        if not host:
            raise error(f'{policy} lint: fleet admission could not choose a host: {picked.stderr[-400:]}')
        up = subprocess.run(['ssh', host, f'mkdir -p {run_dir} && tar -xzf - -C {run_dir}'], input=data,
                            capture_output=True)
        if up.returncode:
            raise error(f'{policy} lint: cannot ship to {host}: {up.stderr[-300:]!r}')
        cmd = (f'cd {run_dir} && OT_LINT_LOCAL=1 python3 -I tools/ref_tile/lint_receipt.py --run lint_job.json; '
               f'rc=$?; cd / && rm -rf {run_dir}; exit $rc')
        p = subprocess.run([client, '--mem', str(mem), '--threads', '1', '--hosts', host, '--max-wait', '900',
                            '--dir', run_dir, '--', 'bash', '-c', cmd], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True)
        tried.append(host)
        if p.returncode == 75 and 'NOT RUN' in p.stderr:
            subprocess.run(['ssh', host, f'rm -rf {run_dir}'], capture_output=True)
            continue
        if f'ot-run: RAN on {host}' not in p.stderr:
            raise error(f'{policy} lint: fleet run on {host} did not complete: {p.stderr[-400:]}')
        lines = [ln for ln in p.stdout.splitlines() if ln.startswith('{')]
        out = json.loads(lines[-1]) if lines else {}
        if out.get('key') != key:
            raise error(f'{policy} lint: fleet run on {host} returned no result for key {key[:12]}: '
                        f'{(p.stdout + p.stderr)[-400:]}')
        if not out.get('ok'):
            raise error(out.get('error', f'{policy} lint failed on {host}'))
        return out['record'], {'host': host}
    raise error(f'{policy} lint: no host admitted {mem} GB (tried {tried})')


def run_job(job_path):
    """remote side: recompute the key over the shipped bytes and this host's Yosys, then lint"""
    job = json.loads(Path(job_path).read_text())
    root = Path(job_path).resolve().parent
    sys.path.insert(0, str(root / 'tools/ref_tile'))
    import gray_fifo_cdc_constraints as G
    import cdc_sync_constraints as S
    lints = {G.POLICY: (G.lint, G._yosys), S.KEY: (S.lint, S._yosys)}
    policy, spec = job['policy'], job['spec']
    out = {'key': job['key']}
    try:
        lint, yosys = lints[policy]
        key = key_of(components(policy, spec, root, yosys()))
        if key != job['key']:
            raise RuntimeError(f'shipped inputs/tool/Yosys do not reproduce the requested key ({key[:12]} != '
                               f'{job["key"][:12]}): refusing')
        out.update(ok=True, record=lint(spec, root))
    except Exception as e:
        out.update(ok=False, error=str(e))
    print(json.dumps(out, sort_keys=True, default=list))
    return 0


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--run':
        sys.exit(run_job(sys.argv[2]))
    print(__doc__)
    sys.exit(2)
