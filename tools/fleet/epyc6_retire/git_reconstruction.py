"""Additive Git preservation: immutable source reads, temporary object stores, verified archive proof."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile


def run(args, **kw):
    return subprocess.run(args, check=True, capture_output=True, timeout=3600, **kw).stdout


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def digest_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def sync_file(path):
    with pathlib.Path(path).open('rb') as f:
        os.fsync(f.fileno())


def sync_tree(root):
    for dp, dirs, files in os.walk(root, topdown=False):
        for name in files:
            p = pathlib.Path(dp)/name
            if not p.is_symlink():
                sync_file(p)
        fd = os.open(dp, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    # Persist the newly created output directory's own name, not only its contents.
    fd = os.open(pathlib.Path(root).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def refs_listing(common, env=None):
    return run(['git', '--git-dir='+common, 'for-each-ref', '--format=%(objectname) %(refname)'], env=env)


def durable_json(path, data):
    path = pathlib.Path(path)
    tmp = path.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def capture(root, output):
    root, output = pathlib.Path(root).resolve(), pathlib.Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    candidates = sorted(p for p in root.iterdir() if p.is_dir() and (p/'.git').exists())
    if not candidates:
        raise RuntimeError('no worktrees found; no proof')
    stores = {}
    source_refs = {}
    records, errors = {}, {}
    # Registered nested worktrees are enumerated without traversing millions of checkout files.
    for p in list(candidates):
        try:
            common = run(['git', '-C', str(p), 'rev-parse', '--git-common-dir'], env=env).decode().strip()
            common = str((p/common).resolve())
            if common not in stores:
                stores[common] = None
                listing = run(['git', '--git-dir='+common, 'worktree', 'list', '--porcelain'], env=env).decode()
                for line in listing.splitlines():
                    if line.startswith('worktree '):
                        q = pathlib.Path(line[9:]).resolve()
                        if q.is_relative_to(root) and (q/'.git').exists() and q not in candidates:
                            candidates.append(q)
        except Exception as e:
            errors[str(p)] = 'Git discovery failed; preserve full copy: ' + str(e)
    for i, common in enumerate(stores):
        temp = output/('objects-'+str(i))
        run(['git', 'init', '--bare', str(temp)])
        (temp/'objects/info/alternates').write_text(str(pathlib.Path(common)/'objects')+'\n')
        source_refs[common] = refs_listing(common, env)
        (output/('refs-'+str(i)+'.txt')).write_bytes(source_refs[common])
        listing = source_refs[common].decode()
        for line in listing.splitlines():
            oid, ref = line.split(' ', 1)
            run(['git', '--git-dir='+str(temp), 'update-ref', ref, oid])
        stores[common] = temp
    for p in sorted(set(candidates)):
        try:
            gitdir = run(['git', '-C', str(p), 'rev-parse', '--absolute-git-dir'], env=env).decode().strip()
            git = ['git', '-c', 'diff.autoRefreshIndex=false', '--git-dir='+gitdir, '--work-tree='+str(p)]
            common = run(git+['rev-parse', '--git-common-dir'], env=env).decode().strip()
            common = str((p/common).resolve())
            temp = stores[common]
            head = run(git+['rev-parse', 'HEAD'], env=env).decode().strip()
            index = pathlib.Path(run(git+['rev-parse', '--git-path', 'index'], env=env).decode().strip())
            key = hashlib.sha256(str(p).encode()).hexdigest()[:20]
            data = output/key
            data.mkdir()
            shutil.copyfile(index, data/'index')
            # Split-index extensions resolve relative to the temporary git directory, never live state.
            for shared in index.parent.glob('sharedindex.*'):
                shutil.copyfile(shared, temp/shared.name)
            diff = run(git+['diff', '--binary', 'HEAD', '--'], env=env)
            (data/'working.diff').write_bytes(diff)
            symbolic = subprocess.run(git+['symbolic-ref', '-q', 'HEAD'], env=env, capture_output=True).stdout.decode().strip()
            shutil.copyfile(data/'index', temp/('index-'+key))
            tenv = dict(env, GIT_INDEX_FILE=str(temp/('index-'+key)), GIT_AUTHOR_NAME='EP6 archive', GIT_AUTHOR_EMAIL='archive@localhost',
                        GIT_COMMITTER_NAME='EP6 archive', GIT_COMMITTER_EMAIL='archive@localhost')
            tree = run(['git', '--git-dir='+str(temp), 'write-tree'], env=tenv).decode().strip()
            commit = run(['git', '--git-dir='+str(temp), 'commit-tree', tree, '-p', head], input=b'Preserved staged index, original worktree immutable\n', env=tenv).decode().strip()
            run(['git', '--git-dir='+str(temp), 'update-ref', 'refs/preserve/ep6-index-'+key, commit])
            run(['git', '--git-dir='+str(temp), 'update-ref', 'refs/preserve/ep6-head-'+key, head])
            record = dict(head=head, symbolic_ref=symbolic, index_sha256=sha(data/'index'), diff_sha256=sha(data/'working.diff'),
                          refs_sha256=hashlib.sha256(source_refs[common]).hexdigest(),
                          index_commit=commit, index_tree=tree, metadata_dir=key, common=common)
            # A changed source snapshot is never marked reconstructible.
            assert sha(index) == record['index_sha256']
            assert run(git+['rev-parse', 'HEAD'], env=env).decode().strip() == head
            assert hashlib.sha256(run(git+['diff', '--binary', 'HEAD', '--'], env=env)).hexdigest() == record['diff_sha256']
            records[str(p)] = record
        except Exception as e:
            errors[str(p)] = str(e)
    bundles = {}
    for i, (common, temp) in enumerate(stores.items()):
        name = 'store-'+str(i)+'.bundle'
        run(['git', '--git-dir='+str(temp), 'bundle', 'create', str(output/name), '--all'])
        assert refs_listing(common, env) == source_refs[common], 'source refs changed during capture'
        bundles[common] = dict(file=name, sha256=digest_file(output/name), refs_file='refs-'+str(i)+'.txt',
                               refs_sha256=hashlib.sha256(source_refs[common]).hexdigest())
        # The bundle is standalone; the temporary alternate-backed object store is not the durable artifact.
    manifest = dict(at=datetime.datetime.now().astimezone().isoformat(),root=str(root),worktrees=records,errors=errors,bundles=bundles)
    for common in stores:
        assert refs_listing(common, env) == source_refs[common], 'source refs changed before manifest'
    # Bundle, exact raw index/diff, and refs are durable BEFORE the manifest can advertise them.
    sync_tree(output)
    durable_json(output/'source_manifest.json', manifest)
    print(json.dumps(dict(output=str(output),worktrees=len(records),errors=errors,bundles=bundles)), flush=True)


def verify(output, proof):
    output = pathlib.Path(output).resolve()
    manifest = json.loads((output/'source_manifest.json').read_text())
    mirrors = {}
    for common, bundle in manifest['bundles'].items():
        path = output/bundle['file']
        assert digest_file(path) == bundle['sha256'], 'bundle SHA mismatch'
        assert sha(output/bundle['refs_file']) == bundle['refs_sha256'], 'refs listing SHA mismatch'
        mirror = output/(bundle['file']+'.verified.git')
        if mirror.exists():
            raise RuntimeError('verification destination already exists; use fresh artifact')
        run(['git', 'clone', '--mirror', str(path), str(mirror)])
        run(['git', '--git-dir='+str(mirror), 'fsck', '--full', '--strict'])
        mirrors[common] = mirror
    verified = {}
    for path, record in manifest['worktrees'].items():
        data = output/record['metadata_dir']
        assert record['refs_sha256'] == manifest['bundles'][record['common']]['refs_sha256']
        assert sha(data/'index') == record['index_sha256']
        assert sha(data/'working.diff') == record['diff_sha256']
        mirror = mirrors[record['common']]
        for oid, kind in [(record['head'], 'commit'), (record['index_commit'], 'commit'), (record['index_tree'], 'tree')]:
            run(['git', '--git-dir='+str(mirror), 'cat-file', '-e', oid+'^{'+kind+'}'])
        verified[path] = record | dict(archive_verified=True,bundle_sha256=manifest['bundles'][record['common']]['sha256'],archive_bundle=str(output/manifest['bundles'][record['common']]['file']))
    # A proof must never outlive the bundle/metadata/verified object artifacts it certifies.
    sync_tree(output)
    durable_json(proof, dict(at=datetime.datetime.now().astimezone().isoformat(),worktrees=verified,errors=manifest['errors']))
    print(json.dumps(dict(proof=str(proof),verified_worktrees=len(verified),errors=manifest['errors'])), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='mode', required=True)
    c = sub.add_parser('capture'); c.add_argument('root'); c.add_argument('output')
    v = sub.add_parser('verify'); v.add_argument('output'); v.add_argument('proof')
    args = ap.parse_args()
    capture(args.root, args.output) if args.mode == 'capture' else verify(args.output, args.proof)
