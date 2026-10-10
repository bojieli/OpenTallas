#!/usr/bin/env python3
"""Chip Explorer die geometry: every placed instance of a die, exported from the SAME recipe the die runs use.

A die entry of explorer_dies.json names a generator kind (qwen / hbm / s81), its recipe (die_top_lint Qwen recipe,
HBM generator variant, S81 die options) and the source it is built from: a pinned commit, or a ref whose last commit
under `paths` is the recipe commit.  The export runs the generator from a source snapshot of that commit
(<state>/explorer/src/<commit12>/): tools/ is extracted from git eagerly, every other file the generator touches
(LEFs, records under physical/ and results/) is materialised from the same commit on first access (audit hook on
open / listdir / scandir plus os.stat / pathlib stat), so the snapshot is exact and small.

Output (<state>/explorer/geom/<die>.json.gz, schema opentallas.explorer.die_geometry.v1):
  outline W x H (um), masters [{name, w, h, kind, n}], instances as columns (name, master index, x, y, w, h, orient,
  kind, region), regions / reserved rectangles, buses [cls, bits, [inst indices]] (die nets between instances, widths
  in bits), relays (instances whose kind or master marks a die register hop), view status per master when the die
  has a view index.

  python3 explorer_geom.py export --die qwen_r21b --repo /home/ubuntu/OpenTallas --state ~/.local/state/fleet-viz
  python3 explorer_geom.py status                 # recipe commit vs cached commit for every die
"""
import argparse, builtins, datetime, gzip, hashlib, io, json, os, pathlib, re, subprocess, sys, tarfile, threading, time

HERE = pathlib.Path(__file__).resolve().parent
DIES = HERE / 'explorer_dies.json'
SCHEMA = 'opentallas.explorer.die_geometry.v1'


def git(repo, *a, binary=False, check=True):
    p = subprocess.run(['git', '-C', str(repo)] + list(a), capture_output=True, timeout=600)
    if check and p.returncode:
        raise RuntimeError('git %s: %s' % (' '.join(a[:3]), p.stderr.decode(errors='replace')[:300]))
    return p.stdout if binary else p.stdout.decode(errors='replace').strip()


def load_dies():
    return json.loads(DIES.read_text())['dies']


def recipe_commit(repo, d):
    """the commit the die is built from: pinned, or the last commit under d['paths'] reachable from d['ref']"""
    if d.get('commit'):
        return git(repo, 'rev-parse', d['commit'] + '^{commit}')
    for ref in [d['ref']] + d.get('ref_fallback', []):
        try:
            c = git(repo, 'log', '-1', '--format=%H', ref, '--', *d.get('paths', ['tools']))
        except RuntimeError:
            continue
        if c:
            return c
    raise RuntimeError('no commit for %s (ref %s)' % (d['id'], d['ref']))


def recipe_key(d, commit):
    keep = {k: d[k] for k in ('kind', 'recipe', 'variant', 'opts', 'die', 'relays', 'env') if k in d}
    return commit[:12] + '-' + hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:8]


# ------------------------------------------------------------------------------------------------ source snapshot
def snapshot(repo, commit, state):
    root = pathlib.Path(state) / 'explorer' / 'src' / commit[:12]
    if (root / '.complete').exists():
        return root
    tmp = root.with_name(root.name + '.tmp')
    if tmp.exists():
        subprocess.run(['rm', '-rf', str(tmp)])
    tmp.mkdir(parents=True)
    data = git(repo, 'archive', '--format=tar', commit, 'tools', binary=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        t.extractall(tmp)
    (tmp / 'SOURCE_COMMIT').write_text(commit + '\n')
    (tmp / '.blobs').write_text(git(repo, 'ls-tree', '-r', '-l', '--full-tree', commit))
    (tmp / '.complete').write_text(datetime.datetime.now().isoformat() + '\n')
    if root.exists():
        subprocess.run(['rm', '-rf', str(root)])
    tmp.rename(root)
    return root


class GitFS:
    """materialise files of `commit` under `root` on first access (open / listdir / scandir / stat)"""
    def __init__(self, repo, commit, root):
        self.repo, self.commit, self.root = str(repo), commit, str(root)
        self.blobs, self.dirs = {}, set()
        for ln in (pathlib.Path(root) / '.blobs').read_text().splitlines():
            meta, path = ln.split('\t', 1)
            if meta.split()[1] != 'blob':
                continue
            self.blobs[path] = meta.split()[2]
            p = path
            while '/' in p:
                p = p.rsplit('/', 1)[0]
                self.dirs.add(p)
        self.placeholder = set(); self.listed = set(); self.busy = threading.local(); self.fetched = 0

    def rel(self, path):
        try:
            p = os.fsdecode(path)
        except TypeError:
            return None
        p = os.path.abspath(p)
        if not p.startswith(self.root + '/'):
            return None
        return p[len(self.root) + 1:]

    def fetch(self, rel):
        full = os.path.join(self.root, rel)
        if rel in self.blobs and (rel in self.placeholder or not os.path.lexists(full)):
            os.makedirs(os.path.dirname(full), exist_ok=True)
            data = subprocess.run(['git', '-C', self.repo, 'cat-file', 'blob', self.blobs[rel]], capture_output=True).stdout
            with _orig_open(full + '.part', 'wb') as f:
                f.write(data)
            os.replace(full + '.part', full)
            self.placeholder.discard(rel); self.fetched += 1
        elif rel in self.dirs and not os.path.isdir(full):
            os.makedirs(full, exist_ok=True)

    def listing(self, rel):
        full = os.path.join(self.root, rel) if rel else self.root
        pre = rel + '/' if rel else ''
        if rel and rel not in self.dirs:
            return
        if rel in self.listed:
            return
        self.listed.add(rel)
        os.makedirs(full, exist_ok=True)
        kids = set()
        for p in self.blobs:
            if p.startswith(pre):
                kids.add(p[len(pre):].split('/', 1)[0])
        for k in kids:
            r = pre + k; f = os.path.join(full, k)
            if os.path.lexists(f):
                continue
            if r in self.dirs:
                os.makedirs(f, exist_ok=True)
            else:
                with _orig_open(f, 'wb'):
                    pass
                self.placeholder.add(r)

    def hook(self, event, args):
        if event not in ('open', 'os.listdir', 'os.scandir') or getattr(self.busy, 'on', False):
            return
        self.busy.on = True
        try:
            rel = self.rel(args[0]) if args and args[0] is not None and not isinstance(args[0], int) else None
            if rel is None:
                return
            if event == 'open':
                self.fetch(rel)
            else:
                self.listing(rel)
        finally:
            self.busy.on = False

    def install(self):
        sys.addaudithook(self.hook)
        ostat = os.stat
        fs = self

        def stat(path, *a, **k):
            try:
                return ostat(path, *a, **k)
            except FileNotFoundError:
                if getattr(fs.busy, 'on', False) or isinstance(path, int):
                    raise
                fs.busy.on = True
                try:
                    rel = fs.rel(path)
                    if rel is None or (rel not in fs.blobs and rel not in fs.dirs):
                        raise
                    fs.fetch(rel)
                finally:
                    fs.busy.on = False
                return ostat(path, *a, **k)
        os.stat = stat
        try:
            import pathlib as _pl
            if hasattr(_pl, '_NormalAccessor'):
                _pl._NormalAccessor.stat = staticmethod(stat)
        except Exception:
            pass


_orig_open = builtins.open


# ------------------------------------------------------------------------------------------------ die builders
def _qwen(d):
    import die_top_lint as DTL
    import qwen_rom_fulldie_b3r2 as B
    r = dict(DTL.QWEN_RECIPES[d['recipe']])
    cdc = r.pop('cdc')
    v, m = B.selected(True, cdc=B._cdc_arg(cdc), **r)
    m['buses'] = [(bid, cls, bits, [(i, p.lstrip('*')) for i, p in eps]) for bid, cls, bits, eps in m['buses']]
    W, H = _outline(m)
    return m, W, H, None


def _hbm(d):
    import die_top_lint as L
    import hbm_die_views as V
    import hbm_accel_die_fp as H
    L.VARIANT = d.get('variant', '')
    m, pw, M, real = V.model()
    rec = None
    index = V.ROOT / V.VIEWS / d.get('index', 'index.json')
    if d.get('relays'):
        import tempfile
        import hbm_die_relays as RL
        views = V.real_views(index) if index.exists() else {}
        vchk = json.loads(index.read_text())['masters'] if index.exists() else {}
        with tempfile.TemporaryDirectory(prefix='explorer-hbm-') as work:
            work = pathlib.Path(work)
            H.case_real(m, work)
            lt = (work / 'elements.lef').read_text() + '\n'.join(pathlib.Path(p_).read_text() for n_, p_ in views.items()
                                                                 if vchk[n_].get('check', {}).get('verdict') != 'MISMATCH')
            for nm_ in ('phy.lef', 'serdes.lef', 'ucie.lef'):
                lt += '\n' + (work / nm_).read_text()
            rec = RL.instance_relays(m, real, lt, H, L, wire_stages=True, relay_all=False)
    views = None
    if index.exists():
        views = {n: dict(status=v.get('status'), verdict=(v.get('check') or {}).get('verdict'), dir=v.get('dir'),
                         job=v.get('job') or (v.get('receipt') or {}).get('job') if isinstance(v.get('receipt'), dict) else v.get('job'),
                         slack={k: v.get(k) for k in ('setup_tt', 'setup_ss', 'hold_ff') if v.get(k) is not None} or None)
                 for n, v in json.loads(index.read_text())['masters'].items()}
    return m, m['geo']['W'], m['geo']['H'], dict(views=views, view_index=str(index.relative_to(V.ROOT)) if index.exists() else None,
                                                  relay_record={k: v for k, v in (rec or {}).items() if isinstance(v, (int, float, str))} or None)


def _s81(d):
    import shlex
    import dsrom_s81_fulldie as S
    for k, v in (d.get('env') or {}).items():
        os.environ[k] = v
    S.apply_options(S.die_options(argparse.ArgumentParser()).parse_args(shlex.split(d['opts'])))
    m = S.build()
    S.finalize_r8(m)
    W, H = _outline(m)
    views = None
    if d.get('index_file'):
        p = pathlib.Path(d['index_file'])
        if p.exists():
            idx = json.loads(p.read_text())
            views = {n: dict(status=v.get('view'), tiles=v.get('tiles'), glue=v.get('glue_worst_ps'))
                     for n, v in idx.get('masters', {}).items()}
    return m, W, H, dict(views=views)


def _outline(m):
    g = m.get('geo') or {}
    if 'W' in g:
        return g['W'], g['H']
    for k in ('die', 'DIE', 'outline'):
        v = m.get(k)
        if isinstance(v, (list, tuple)) and len(v) >= 2 and all(isinstance(x, (int, float)) for x in v[:2]):
            return (v[0], v[1]) if len(v) == 2 else (v[2] - v[0], v[3] - v[1])
        if isinstance(v, dict) and 'W' in v:
            return v['W'], v['H']
        if isinstance(v, dict) and 'w' in v:
            return v['w'], v['h']
    xs = [it.x + it.w for it in m['insts']]; ys = [it.y + it.h for it in m['insts']]
    return max(xs), max(ys)


RELAY_RX = re.compile(r'rly|relay|_rt_|wstg|wire_stage|^g_rt|stn|meso|hop', re.I)


def _rects(v):
    out = []
    if isinstance(v, dict):
        if 'rect' in v and isinstance(v['rect'], (list, tuple)) and len(v['rect']) == 4:
            out.append(dict(name=str(v.get('name', '')), kind=str(v.get('kind', '')), rect=[round(float(x), 2) for x in v['rect']],
                            clock=v.get('clock')))
        return out
    if isinstance(v, (list, tuple)):
        if len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
            return [dict(name='', kind='', rect=[round(float(x), 2) for x in v])]
        for x in v:
            out += _rects(x)
    return out


def serialise(d, commit, m, W, H, extra):
    insts = m['insts']
    mi = {}; masters = []; kinds = []; ki = {}; regs = []; ri = {}; ors = []; oi = {}
    cols = dict(name=[], m=[], x=[], y=[], w=[], h=[], o=[], k=[], r=[], dom=[])
    doms = []; di = {}

    def ix(tab, idx, v):
        if v not in idx:
            idx[v] = len(tab); tab.append(v)
        return idx[v]
    for it in insts:
        mst = getattr(it, 'master', '') or ''
        if mst not in mi:
            mi[mst] = len(masters); masters.append(dict(name=mst, w=round(it.w, 3), h=round(it.h, 3), kind=getattr(it, 'kind', '') or '', n=0))
        masters[mi[mst]]['n'] += 1
        cols['name'].append(it.name); cols['m'].append(mi[mst])
        cols['x'].append(round(it.x, 2)); cols['y'].append(round(it.y, 2)); cols['w'].append(round(it.w, 2)); cols['h'].append(round(it.h, 2))
        cols['o'].append(ix(ors, oi, getattr(it, 'orient', 'R0') or 'R0'))
        cols['k'].append(ix(kinds, ki, getattr(it, 'kind', '') or ''))
        cols['r'].append(ix(regs, ri, str(getattr(it, 'region', '') or '')))
        cols['dom'].append(ix(doms, di, str(getattr(it, 'domain', '') or '')))
    byn = {n: i for i, n in enumerate(cols['name'])}
    cls = []; ci = {}; buses = []; skipped = 0
    for b in m.get('buses', []):
        try:
            bid, c, bits, eps = b[0], b[1], b[2], b[3]
        except Exception:
            skipped += 1; continue
        ids = []
        for e in eps:
            n = e[0] if isinstance(e, (list, tuple)) else e
            if n in byn and byn[n] not in ids:
                ids.append(byn[n])
        if len(ids) < 2:
            continue
        if c in ('clock_trunk', 'reset', 'clock', 'rst') or len(ids) > 64:
            buses.append([ix(cls, ci, str(c)), int(bits), ids[:1] + [-len(ids)]])   # broadcast: source + count only
            continue
        buses.append([ix(cls, ci, str(c)), int(bits) if isinstance(bits, (int, float)) else 0, ids])
    regions = []
    for key in ('regions', 'region_extra', 'reserved_regions', 'clock_regions'):
        if key in m:
            for r in _rects(m[key]):
                r['src'] = key; regions.append(r)
    relay = [i for i, it in enumerate(insts) if RELAY_RX.search(getattr(it, 'kind', '') or '') or
             re.search(r'(^|_)(rly|relay|wstg)', getattr(it, 'master', '') or '')]
    keys = {k: (type(v).__name__, len(v) if hasattr(v, '__len__') else None) for k, v in m.items() if not k.startswith('_')}
    out = dict(schema=SCHEMA, die=d['id'], label=d['label'], target=d['target'], kind=d['kind'], commit=commit,
               recipe={k: d.get(k) for k in ('ref', 'commit', 'paths', 'recipe', 'variant', 'opts', 'relays', 'tool', 'note') if d.get(k) is not None},
               key=recipe_key(d, commit), generated=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
               W=round(W, 3), H=round(H, 3), masters=masters, kinds=kinds, regions_names=regs, orients=ors, domains=doms,
               inst=cols, bus_classes=cls, buses=buses, buses_skipped=skipped, regions=regions, relays=len(relay),
               model_keys=keys)
    if extra:
        out.update({k: v for k, v in extra.items() if v is not None})
    return out


def export(d, repo, state, out=None):
    commit = recipe_commit(repo, d)
    root = snapshot(repo, commit, state)
    fs = GitFS(repo, commit, root); fs.install()
    os.chdir(root)
    sys.path.insert(0, str(root / 'tools'))
    t0 = time.time()
    fn = dict(qwen=_qwen, hbm=_hbm, s81=_s81)[d['kind']]
    if d.get('index_file'):     # view status: the live record in the repo checkout, not the recipe snapshot
        d = dict(d, index_file=str(pathlib.Path(repo) / d['index_file']))
    m, W, H, extra = fn(d)
    rec = serialise(d, commit, m, W, H, extra)
    rec['build_s'] = round(time.time() - t0, 1); rec['fetched_files'] = fs.fetched
    gdir = pathlib.Path(state) / 'explorer' / 'geom'; gdir.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(out) if out else gdir / (d['id'] + '.json.gz')
    tmp = out.with_name(out.name + '.tmp')
    with gzip.open(tmp, 'wt') as f:
        json.dump(rec, f, separators=(',', ':'))
    os.replace(tmp, out)
    return rec


def cached(state, die_id):
    p = pathlib.Path(state) / 'explorer' / 'geom' / (die_id + '.json.gz')
    if not p.exists():
        return None
    try:
        with gzip.open(p, 'rt') as f:
            return json.load(f)
    except Exception:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['export', 'status', 'commit'])
    ap.add_argument('--die')
    ap.add_argument('--repo', default=os.environ.get('FLEET_VIZ_REPO', '/home/ubuntu/OpenTallas'))
    ap.add_argument('--state', default=os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    dies = {d['id']: d for d in load_dies()}
    if a.mode == 'status':
        for d in dies.values():
            c = recipe_commit(a.repo, d); g = cached(a.state, d['id'])
            print(d['id'], recipe_key(d, c), (g or {}).get('key'), 'FRESH' if g and g.get('key') == recipe_key(d, c) else 'STALE')
        return 0
    d = dies[a.die]
    if a.mode == 'commit':
        print(recipe_key(d, recipe_commit(a.repo, d)))
        return 0
    rec = export(d, a.repo, a.state, a.out)
    print(json.dumps(dict(die=rec['die'], key=rec['key'], insts=len(rec['inst']['name']), masters=len(rec['masters']),
                          buses=len(rec['buses']), regions=len(rec['regions']), relays=rec['relays'], W=rec['W'], H=rec['H'],
                          build_s=rec['build_s'], fetched=rec['fetched_files'], model_keys=rec['model_keys'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
