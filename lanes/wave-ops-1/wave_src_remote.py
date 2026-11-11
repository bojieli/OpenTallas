#!/usr/bin/env python3
"""WAVE-OPS-1 nightly wave-source rebuild: the host-side half (stdlib only; run with python3 -I).

  manifest SRC OUT [--cache C]        git-style manifest of a tree: path<TAB>mode<TAB>blob-sha1 (symlinks 120000 =
                                      sha of the target).  An (dev, inode, size, mtime_ns) -> sha cache makes the
                                      hard-linked (cp -al) wave trees cheap after the first night.
  compose REPO SPEC OUT               (compose host) main + overlays in order in a private worktree; per die + its
                                      die branch (src_sha); never touches any other checkout.
  classify REPO LIVE_MANIFEST BASE NEW OUT_JSON
                                      per path: live (L) vs base commit (B = the live tree's src_sha) vs composed (N):
                                      same / take-new / carry-live (overlay not in git) / delete / merge / conflict.
  pack REPO ACTIONS_JSON OUT_TAR      tar of every blob the new tree needs (git cat-file; merged files from the
                                      actions' merge texts)
  materialize LIVE NEW ACTIONS_JSON TAR
                                      NEW = cp -al LIVE, then every changed path is written as a NEW inode (the live
                                      tree and its hard-linked twins are never modified); deletes unlink in NEW only.
  verify TREE EXPECT_MANIFEST OUT_JSON [--cache C]
                                      byte check: manifest(TREE) == expected
  expect LIVE_MANIFEST ACTIONS_JSON OUT
                                      expected manifest of the new tree
Nothing here deletes outside a NEW tree it created, kills a process or edits a live tree.
"""
import hashlib, json, os, shutil, stat, subprocess, sys, tarfile, tempfile, time

MODE_X, MODE_F, MODE_L = '100755', '100644', '120000'


# ------------------------------------------------------------------------------------------------- manifest
def blob_sha(path, size):
    h = hashlib.sha1(b'blob %d\0' % size)
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''):
            h.update(c)
    return h.hexdigest()


def _hash_one(a):
    return blob_sha(*a)


def link_sha(target):
    b = os.fsencode(target)
    return hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()


def load_cache(path):
    c = {}
    if path and os.path.exists(path):
        with open(path) as f:
            for l in f:
                k, _, v = l.rstrip('\n').rpartition('\t')
                if k:
                    c[k] = v
    return c


def manifest(root, cache_path=None):
    """{relpath: (mode, sha)}; the walk does not follow symlinks below root (root itself may be one)"""
    root = os.path.realpath(root)
    cache, new, todo = load_cache(cache_path), {}, {}
    out = {}
    for d, dirs, files in os.walk(root):
        rel_d = os.path.relpath(d, root)
        for n in list(dirs):
            p = os.path.join(d, n)
            if os.path.islink(p):                     # a symlinked dir is one link entry, as git stores it
                dirs.remove(n)
                files.append(n)
        if rel_d == '.' and '.git' in dirs:
            dirs.remove('.git')
        for n in files:
            p = os.path.join(d, n)
            rel = os.path.normpath(os.path.join(rel_d, n))
            st = os.lstat(p)
            if stat.S_ISLNK(st.st_mode):
                out[rel] = (MODE_L, link_sha(os.readlink(p)))
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            key = '%d:%d:%d:%d' % (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
            sha = cache.get(key)
            if not sha:
                todo.setdefault(key, (p, st.st_size))
            out[rel] = (MODE_X if st.st_mode & 0o111 else MODE_F, sha or key)
    if todo:                                          # hash each new inode once, in parallel (niced by the caller)
        from concurrent.futures import ProcessPoolExecutor
        keys = list(todo)
        jobs = int(os.environ.get('WSR_JOBS', '8'))
        if jobs <= 1 or len(keys) < 256:
            for k in keys:
                new[k] = _hash_one(todo[k])
        else:
            with ProcessPoolExecutor(jobs) as ex:
                for k, h in zip(keys, ex.map(_hash_one, [todo[k] for k in keys], chunksize=64)):
                    new[k] = h
        for rel, (mode, v) in out.items():
            if v in new:
                out[rel] = (mode, new[v])
    if cache_path and new:
        with open(cache_path, 'a') as f:
            for k, v in new.items():
                f.write('%s\t%s\n' % (k, v))
    return out


def write_manifest(m, out):
    tmp = out + '.tmp'
    with open(tmp, 'w') as f:
        for p in sorted(m):
            f.write('%s\t%s\t%s\n' % (p, m[p][0], m[p][1]))
    os.replace(tmp, out)


def read_manifest(path):
    m = {}
    with open(path) as f:
        for l in f:
            p, mode, sha = l.rstrip('\n').split('\t')
            m[p] = (mode, sha)
    return m


# ------------------------------------------------------------------------------------------------- git helpers
def git(repo, *a, check=True, input=None):
    p = subprocess.run(['git', '-C', repo] + list(a), capture_output=True, text=input is None or isinstance(input, str),
                       input=input)
    if check and p.returncode:
        raise RuntimeError('git %s: %s' % (' '.join(a[:3]), (p.stderr or '')[-400:]))
    return p


def ls_tree(repo, rev):
    """{path: (mode, sha)} of blobs and links (submodules skipped)"""
    out = {}
    p = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '-z', '--full-tree', rev], capture_output=True, check=True)
    for ent in p.stdout.split(b'\0'):
        if not ent:
            continue
        meta, path = ent.split(b'\t', 1)
        mode, typ, sha = meta.decode().split()
        if typ == 'blob':
            out[path.decode('utf-8', 'surrogateescape')] = (mode, sha)
    return out


def is_ancestor(repo, a, b):
    return git(repo, 'merge-base', '--is-ancestor', a, b, check=False).returncode == 0


def full_sha(repo, rev):
    p = git(repo, 'rev-parse', '--verify', '-q', rev + '^{commit}', check=False)
    return p.stdout.strip() if p.returncode == 0 else None


# ------------------------------------------------------------------------------------------------- compose
def compose(repo, spec):
    """spec: {main, overlays: [{name, sha}], dies: {die: src_sha}, branch_prefix, worktree}
    -> {base, overlays: [{name, sha, status}], dies: {die: {sha, die_branch}}}"""
    main = full_sha(repo, spec['main'])
    wt = spec['worktree']
    if os.path.isdir(wt):
        git(repo, 'worktree', 'remove', '--force', wt, check=False)
        if os.path.isdir(wt):
            raise RuntimeError('compose worktree still present: ' + wt)
    git(repo, 'worktree', 'add', '-q', '--no-checkout', '--detach', wt, main)   # the full tree is ~49 GB: sparse
    w = lambda *a, **k: git(wt, '-c', 'user.name=WAVE-OPS-1', '-c', 'user.email=wave-ops-1@opentallas', *a, **k)
    res = dict(main=main, overlays=[], dies={})
    try:
        w('sparse-checkout', 'set', '--no-cone', '/tools/autopilot/*.py')
        w('read-tree', '-mu', 'HEAD')
        for ov in spec.get('overlays') or []:
            s = full_sha(repo, ov['sha'])
            r = dict(ov, full=s)
            if not s:
                r['status'] = 'missing (not fetched)'
            elif is_ancestor(repo, s, main):
                r['status'] = 'on main'
            elif is_ancestor(repo, s, 'HEAD'):
                r['status'] = 'contained (earlier overlay)'
            else:
                p = w('merge', '--no-ff', '--no-edit', '-q', '-m', 'wave-src overlay %s %s' % (ov['name'], s[:12]), s,
                      check=False)
                if p.returncode:
                    w('merge', '--abort', check=False)
                    r['status'] = 'conflict (not applied)'
                    r['detail'] = (p.stdout + p.stderr)[-600:]
                else:
                    r['status'] = 'merged'
            res['overlays'].append(r)
        base = w('rev-parse', 'HEAD').stdout.strip()
        res['base'] = base
        for die, src_sha in sorted((spec.get('dies') or {}).items()):
            s = full_sha(repo, src_sha) if src_sha else None
            d = dict(src_sha=s)
            if not s:
                d.update(sha=base, die_branch='missing (not fetched)')
            elif is_ancestor(repo, s, base):
                d.update(sha=base, die_branch='on main/overlays')
            else:
                w('checkout', '-q', '--detach', base)
                p = w('merge', '--no-ff', '--no-edit', '-q', '-m', 'wave-src die %s src %s' % (die, s[:12]), s, check=False)
                if p.returncode:
                    w('merge', '--abort', check=False)
                    d.update(sha=base, die_branch='conflict (die branch not merged; its files carried from live)',
                             detail=(p.stdout + p.stderr)[-600:])
                else:
                    d.update(sha=w('rev-parse', 'HEAD').stdout.strip(), die_branch='merged')
            ref = '%s/%s' % (spec.get('branch_prefix', 'refs/wave-src/x'), die)
            git(repo, 'update-ref', ref, d['sha'])
            d['ref'] = ref
            res['dies'][die] = d
    finally:
        git(repo, 'worktree', 'remove', '--force', wt, check=False)
    return res


# ------------------------------------------------------------------------------------------------- classify
def merge_text(repo, b, n, l_bytes):
    """3-way merge of one text file: base blob b, ours = composed blob n, theirs = live bytes -> (ok, bytes)"""
    with tempfile.TemporaryDirectory(prefix='wsr-') as t:
        fb, fn, fl = (os.path.join(t, x) for x in ('base', 'new', 'live'))
        for path, sha in ((fb, b), (fn, n)):
            with open(path, 'wb') as f:
                f.write(subprocess.run(['git', '-C', repo, 'cat-file', 'blob', sha], capture_output=True, check=True).stdout)
        with open(fl, 'wb') as f:
            f.write(l_bytes)
        p = subprocess.run(['git', 'merge-file', '-p', '-q', fn, fb, fl], capture_output=True)
        return p.returncode == 0, p.stdout


def classify(live, base, new, live_bytes=None, repo=None):
    """live/base/new: {path: (mode, sha)}.  live_bytes(path) -> bytes of the live file (for 3-way merges).
    -> {counts, actions: [{op, path, mode, sha|text}], carried: [paths], conflicts: [paths], ...}
    op write = the new tree gets git blob sha; op text = merged content; op delete = absent in the new tree.
    Paths absent from live but in both base and new are a sparse-tree choice of the live tree: kept absent."""
    acts, counts = [], {}
    carried, conflicts, deleted_kept, merged = [], [], [], []
    def c(k):
        counts[k] = counts.get(k, 0) + 1
    for p in sorted(set(live) | set(new)):
        L, B, N = live.get(p), base.get(p), new.get(p)
        if L == N:
            c('same'); continue
        if L is None:                                   # absent live, present new
            if B is not None:
                c('sparse (absent live, kept absent)'); continue
            acts.append(dict(op='write', path=p, mode=N[0], sha=N[1])); c('new file (main/overlay)'); continue
        if N is None:                                   # present live, absent new
            if B is None:
                carried.append(p); c('carry live-only (not in git)'); continue
            if L == B:
                acts.append(dict(op='delete', path=p)); c('deleted on main/overlay'); continue
            deleted_kept.append(p); conflicts.append(p); c('conflict: live-modified, deleted on main (kept live)'); continue
        if L == B:
            acts.append(dict(op='write', path=p, mode=N[0], sha=N[1])); c('take new (main/overlay changed)'); continue
        if N == B or B is None and False:
            carried.append(p); c('carry live overlay (not in git)'); continue
        if B is None:                                   # both added, different content
            conflicts.append(p); c('conflict: added both (kept live)'); continue
        if L[0] == MODE_L or N[0] == MODE_L or live_bytes is None or repo is None:
            conflicts.append(p); c('conflict: both changed (kept live)'); continue
        try:
            lb = live_bytes(p)
        except OSError:
            conflicts.append(p); c('conflict: both changed, live unreadable (kept live)'); continue
        if b'\0' in lb[:8000]:
            conflicts.append(p); c('conflict: both changed, binary (kept live)'); continue
        ok, txt = merge_text(repo, B[1], N[1], lb)
        if ok:
            merged.append(p)
            acts.append(dict(op='text', path=p, mode=L[0], text=txt.decode('utf-8', 'surrogateescape'),
                             sha=hashlib.sha1(b'blob %d\0' % len(txt) + txt).hexdigest()))
            c('3-way merged (live overlay + main)')
        else:
            conflicts.append(p); c('conflict: both changed, merge conflict (kept live)')
    return dict(counts=counts, actions=acts, carried=carried, conflicts=conflicts, merged=merged,
                deleted_kept=deleted_kept)


def expected_manifest(live, actions):
    m = dict(live)
    for a in actions:
        if a['op'] == 'delete':
            m.pop(a['path'], None)
        else:
            m[a['path']] = (a['mode'], a['sha'])
    return m


# ------------------------------------------------------------------------------------------------- pack / materialize
def pack(repo, actions, out_tar):
    tmp = out_tar + '.tmp'
    with tarfile.open(tmp, 'w') as t:
        for i, a in enumerate(actions):
            if a['op'] == 'delete':
                continue
            if a['op'] == 'text':
                data = a['text'].encode('utf-8', 'surrogateescape')
            else:
                data = subprocess.run(['git', '-C', repo, 'cat-file', 'blob', a['sha']], capture_output=True,
                                      check=True).stdout
            ti = tarfile.TarInfo('%06d' % i)
            ti.size = len(data)
            import io
            t.addfile(ti, io.BytesIO(data))
    os.replace(tmp, out_tar)


def materialize(live, new, actions, tar_path):
    """NEW = hard-link copy of LIVE; every changed path becomes a new inode in NEW only"""
    live = os.path.realpath(live)
    if os.path.lexists(new):
        raise RuntimeError('refusing: new tree exists ' + new)
    os.makedirs(os.path.dirname(new), exist_ok=True)
    part = new + '.partial'
    if os.path.lexists(part):
        raise RuntimeError('refusing: partial tree exists (left for diagnosis) ' + part)
    subprocess.run(['cp', '-al', live, part], check=True)
    for d, dirs, _ in os.walk(part):                    # new dirs are ours: make them writable for the edits
        os.chmod(d, os.stat(d).st_mode | stat.S_IWUSR)
    with tarfile.open(tar_path) as t:
        for i, a in enumerate(actions):
            dst = os.path.join(part, a['path'])
            if os.path.lexists(dst):
                os.unlink(dst)                          # drops only NEW's link; the live inode is untouched
            if a['op'] == 'delete':
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if a['mode'] == MODE_L:
                os.symlink(t.extractfile('%06d' % i).read().decode('utf-8', 'surrogateescape'), dst)
                continue
            with open(dst, 'wb') as f:
                shutil.copyfileobj(t.extractfile('%06d' % i), f)
            os.chmod(dst, 0o755 if a['mode'] == MODE_X else 0o644)
    os.rename(part, new)


def verify(tree, expect, cache=None):
    got = manifest(tree, cache)
    diff = sorted(p for p in set(got) | set(expect) if got.get(p) != expect.get(p))
    return dict(ok=not diff, files=len(got), expected=len(expect), differ=len(diff), sample=diff[:20])


# ------------------------------------------------------------------------------------------------- cli
def main(argv):
    cmd = argv[1]
    cache = None
    if '--cache' in argv:
        i = argv.index('--cache'); cache = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    if cmd == 'manifest':
        t = time.time()
        m = manifest(argv[2], cache)
        write_manifest(m, argv[3])
        print(json.dumps(dict(files=len(m), s=round(time.time() - t, 1))))
    elif cmd == 'compose':
        r = compose(argv[2], json.load(open(argv[3])))
        json.dump(r, open(argv[4], 'w'), indent=1); print(json.dumps(r)[:4000])
    elif cmd == 'classify':
        repo, lm, b, n, out = argv[2:7]
        live_root = argv[7] if len(argv) > 7 else None
        rb = (lambda p: open(os.path.join(live_root, p), 'rb').read()) if live_root else None
        r = classify(read_manifest(lm), ls_tree(repo, b), ls_tree(repo, n), rb, repo)
        json.dump(r, open(out, 'w'))
        print(json.dumps(dict(counts=r['counts'], actions=len(r['actions']), carried=len(r['carried']),
                              conflicts=len(r['conflicts']), merged=len(r['merged']))))
    elif cmd == 'pack':
        pack(argv[2], json.load(open(argv[3]))['actions'], argv[4]); print('packed')
    elif cmd == 'expect':
        write_manifest(expected_manifest(read_manifest(argv[2]), json.load(open(argv[3]))['actions']), argv[4])
        print('expect written')
    elif cmd == 'materialize':
        materialize(argv[2], argv[3], json.load(open(argv[4]))['actions'], argv[5]); print('materialized ' + argv[3])
    elif cmd == 'verify':
        r = verify(argv[2], read_manifest(argv[3]), cache)
        json.dump(r, open(argv[4], 'w')); print(json.dumps(r))
        return 0 if r['ok'] else 2
    else:
        print(__doc__); return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
