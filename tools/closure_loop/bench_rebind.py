"""Route-preserving recovery of the reviewed SEQHOST file-path declaration bug.

This deliberately supports one instrumentation-only transformation, not arbitrary
replacement benchmarks. The routed source/attempt and every acceptance check stay
fixed. No running stage can be stopped through this operation.
"""
import base64
import copy
import hashlib
import json
from pathlib import PurePosixPath
import shlex
import subprocess

TB = 'rtl/dsrom_sys/s81_dv/unit/test/tb_dsdv_seq_host_mu.sv'
NOTE = '    // Fleet closure paths can exceed128bytes; strings preserve full manifest paths.\n'


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def plan(repo, job, target, keys, stages):
    if (job.get('status') != 'NEEDS_RTL' or job.get('stage_key') != 'verdict'
            or not job.get('bench_par') or not job.get('source_synced')):
        raise ValueError('bench-rebind requires a terminal benchmark failure after the completed route')
    if any(x.get('state') == 'running' for x in (job.get('btrack') or {}).values()):
        raise ValueError('bench-rebind never stops a running benchmark or route')
    if not job.get('freeze_helper_overlay') or not job.get('route_overlay_plan'):
        raise ValueError('bench-rebind requires the original frozen helper plan')
    keys = sorted(set(keys))
    if not keys or any(k not in stages or stages[k]['kind'] != 'bench' for k in keys):
        raise ValueError('select actual benchmark stage keys')
    if not any(k in job.get('benches', {}) and not job['benches'][k]['ok'] for k in keys):
        raise ValueError('selected benchmarks must include the recorded failure')
    if any(job.get('benches', {}).get(k, {}).get('ok') for k in keys):
        raise ValueError('successful benchmark receipts cannot be replaced')
    if any('{COMMIT}' in stages[k]['cmd'] for k in keys):
        raise ValueError('commit-substituting benchmarks need separate source-binding support')
    old = git(repo, 'rev-parse', job['commit_full'] + '^{commit}').decode().strip()
    new = git(repo, 'rev-parse', target + '^{commit}').decode().strip()
    changed = git(repo, 'diff', '--name-only', '-z', '--no-renames', old, new).split(b'\0')[:-1]
    if changed != [TB.encode()]:
        raise ValueError('only the reviewed testbench path declaration may differ; route inputs must be identical')
    a, b = git(repo, 'show', old + ':' + TB), git(repo, 'show', new + ':' + TB)
    if a.count(b'    reg [1023:0] dir, mufile, cfgfile;\n') != 1:
        raise ValueError('requires exactly the reviewed path declaration')
    expected = a.decode().replace('    reg [1023:0] dir, mufile, cfgfile;\n',
                                 NOTE + '    string dir, mufile, cfgfile;\n')
    if expected == a.decode() or expected.encode() != b:
        raise ValueError('unsupported testbench change: only the reviewed path registers to strings is allowed')
    # Compare all other repository objects, not just an operator-selected RTL list.
    def inventory(commit):
        rows = git(repo, 'ls-tree', '-r', '-z', commit).split(b'\0')
        return b'\0'.join(row for row in rows if row and row.rsplit(b'\t', 1)[-1] != TB.encode())
    frozen, candidate = inventory(old), inventory(new)
    if frozen != candidate:
        raise ValueError('a routed input object changed')
    return dict(schema='opentallas.bench_path_rebind.v1', route_commit=old, source_commit=new,
                route_attempt=job.get('route_attempt', job['attempt']), keys=keys,
                host=job['host'], run=job['run'],
                unchanged_tree_sha256=hashlib.sha256(frozen).hexdigest(),
                testbench=TB, old_sha256=hashlib.sha256(a).hexdigest(),
                new_sha256=hashlib.sha256(b).hexdigest(), payload=base64.b64encode(b).decode())


def source_for_stage(job, key):
    row = (job.get('bench_rebind') or {}).get(key)
    if row is None:
        return None
    if (row['route_commit'] != job['commit_full'] or row['route_attempt'] != job.get('route_attempt', job['attempt'])
            or row['host'] != job['host'] or row['run'] != job['run']):
        raise ValueError('bench-rebind source is pinned to a different route/attempt/location')
    root = PurePosixPath(job['run']) / 'bench_rebind'
    path = PurePosixPath(row['source_path'])
    if '..' in path.parts or not path.is_relative_to(root) or path.name != 'source':
        raise ValueError('invalid private benchmark recovery source')
    return row


def launch_guard(row):
    """Refuse a missing/modified private source before the normal copy fallback."""
    tb = str(PurePosixPath(row['source_path']) / row['testbench'])
    return ("[ -d " + shlex.quote(row['source_path']) + " ] || exit 97\n"
            + "printf '%s  %s\\n' " + shlex.quote(row['new_sha256']) + " " + shlex.quote(tb)
            + " | sha256sum -c - || exit 97\n")


def apply_state(job, receipt, stages):
    """Only benchmark-track and terminal-result fields change; route identity stays fixed."""
    history = dict(id=receipt['id'], status=job['status'], reason=job.get('reason'),
                   finished_at=job.get('finished_at'),
                   benches={k: copy.deepcopy(job.get('benches', {}).get(k)) for k in receipt['keys']},
                   btrack={k: copy.deepcopy(job.get('btrack', {}).get(k)) for k in receipt['keys']})
    job.setdefault('bench_rebind_history', []).append(history)
    public = {k: v for k, v in receipt.items() if k != 'payload'}
    for key in receipt['keys']:
        job.setdefault('bench_rebind', {})[key] = dict(public)
        job.setdefault('benches', {}).pop(key, None)
        previous = job.setdefault('btrack', {}).get(key, {})
        job['btrack'][key] = dict(previous, state='retry')
        job.get('bench_work', {}).pop(key, None)
    job.update(status='READY', reason=None, errors=[], bwait=None)
    job.pop('finished_at', None)


# Executed remotely with JSON input. It never modifies src/, cl stage logs, or routes/.
REMOTE = r'''
import base64,hashlib,json,os,subprocess,sys
from pathlib import Path
p=json.load(sys.stdin); run=Path(p['run']).resolve(); src=run/'src'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
def snapshot():
 rc=run/'cl'/(p['route_tag']+'.rc')
 if rc.read_text().strip()!='0':raise ValueError('original route did not complete successfully')
 finals=list((run/'routes').rglob('6_final.odb'))
 if len(finals)!=1:raise ValueError('requires one unambiguous final routed database')
 base=finals[0].parent
 files=[base/x for x in ('6_final.odb','6_final.sdc','6_final.spef','5_route.odb')]
 if any(not x.is_file() or not x.resolve().is_relative_to(run/'routes') for x in files):raise ValueError('missing/outside routed artifact')
 if sha(src/p['testbench'])!=p['old_sha256']:raise ValueError('frozen original testbench differs')
 return {str(x.relative_to(run)):sha(x) for x in files}
for rel in p.get('outputs',[]):
 q=Path(rel)
 if q.is_absolute() or '..' in q.parts or not q.parts or q.parts[0] in ('src','routes','cl','bench_rebind'):
  raise ValueError('unsafe benchmark output path')
before=snapshot()
if p['action']=='inspect':print(json.dumps(dict(route_files=before)));sys.exit(0)
if before!=p['route_files']:raise ValueError('routed input/output SHA changed since inspection')
home=run/'bench_rebind'/p['id']
if home.exists():raise ValueError('recovery already exists; refusing overwrite')
home.mkdir(parents=True)
private=home/'source'
subprocess.run(['cp','-a','--reflink=auto',str(src),str(private)],check=True)
tb=private/p['testbench']; temp=tb.with_name(tb.name+'.rebind-tmp');temp.write_bytes(base64.b64decode(p['payload']));os.replace(temp,tb)
if sha(tb)!=p['new_sha256']:raise ValueError('replacement testbench SHA mismatch')
saved=[]
for rel in p['outputs']:
 q=Path(rel)
 if q.is_absolute() or '..' in q.parts or not q.parts or q.parts[0] in ('src','routes','cl','bench_rebind'):
  raise ValueError('unsafe benchmark output path')
 old=run/q
 if old.exists():
  dest=home/'previous_outputs'/q;dest.parent.mkdir(parents=True,exist_ok=True);old.rename(dest);saved.append(str(dest))
after=snapshot()
if before!=after:raise ValueError('route changed during recovery preparation')
receipt={k:v for k,v in p.items() if k not in ('payload','action','outputs')}
receipt.update(source_path=str(private),preserved_outputs=saved,route_files_after=after)
(home/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
'''


def remote(cl, host, payload):
    r = cl.ssh(host, 'python3 -c ' + shlex.quote(REMOTE), input=json.dumps(payload), timeout=600)
    if r.returncode:
        raise ValueError('benchmark rebind remote guard refused: ' + r.stderr[-1500:])
    return json.loads(r.stdout)


def command(cl, args):
    job = cl.load_job(args.name)
    stages = {s['key']: s for s in cl.stage_list(job['spec'])}
    receipt = plan(cl.REPO, job, args.commit, args.bench, stages)
    receipt['route_tag'] = 'route.a' + str(receipt['route_attempt'])
    helpers = cl.installed_helper_receipt(job['host'], job['run'], job['route_overlay_plan'])
    expected = job.get('helper_overlay_verification') or {}
    if helpers.get('status') != 'verified_original' or helpers.get('content_sha256') != expected.get('content_sha256'):
        raise ValueError('original frozen helper identity differs')
    receipt['helpers'] = helpers
    receipt.update(remote(cl, job['host'], dict(receipt, action='inspect')))
    receipt['id'] = hashlib.sha256((receipt['source_commit'] + cl.now_iso()).encode()).hexdigest()[:20]
    if not args.apply:
        print(json.dumps({k: v for k, v in receipt.items() if k != 'payload'}, indent=2))
        return
    backup = cl.STATE / 'bench_rebind' / job['name'] / receipt['id']
    backup.mkdir(parents=True, exist_ok=False)
    (backup / 'job_before.json').write_text(json.dumps(job, indent=2) + '\n')
    outputs = sorted({d for k in receipt['keys'] for d in cl.bench_scratch_dirs(stages[k]['cmd'])})
    prepared = remote(cl, job['host'], dict(receipt, action='prepare', outputs=outputs))
    if cl.installed_helper_receipt(job['host'], job['run'], job['route_overlay_plan']) != helpers:
        # verified_at is not in this readonly receipt; helper bytes must remain exact.
        raise ValueError('frozen helpers changed during preparation')
    (backup / 'receipt.json').write_text(json.dumps(prepared, indent=2) + '\n')
    apply_state(job, prepared, stages)
    cl.event(job, 'bench-only path recovery ' + prepared['id'] + ': original route and helpers unchanged; ' + args.why)
    cl.save_job(job)
    cl.ledger(job, 'BENCH-REBIND ' + prepared['id'] + ' (route preserved)')
    print(json.dumps(prepared, indent=2))
