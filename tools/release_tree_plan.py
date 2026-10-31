#!/usr/bin/env python3
"""Current-plan element layer for the release tree (INFRA lane, 2026-10-24; replaces the obsolete 10-21 element list).

Per die plan on origin/main:
  * G0C-clean partition types / total types   -- tools/die_plan/check.py --completeness, run from a git archive of
    origin/main in a tmp dir (cheap: ~90 s, < 1 GB, all five plans in sequence)
  * partition types and hard cores with a SIGNED signoff view -- signoff.py records (schema opentallas.signoff.v1,
    verdict SIGNED) found on origin/main (*signoff.json) and on every fleet host under /srv/opentallas-scratch{,2}
    (KIT/signoff/signoff.json, <kit>/signoff_tt_ff/signoff.json, ...). A record counts for a type when its
    face_guard top (or its name without the dp_/kr_ prefix) is the type's module/key, for a hard core when it is the
    core's module.
Closure order rule 3 (owner 2026-10-25 18:45, INFRA2): a SIGNED record counts only when it names its source commit +
flow release tag -- 'src_commit'/'flow_tag' in the signoff.json itself, else in the nearest PROVENANCE.json (verdict
SIGNED, written by the autopilot archive) or AUTOPILOT.json up to 6 directories above it.  Every record carries
'versioned'; signed_types/signed_cores hold versioned records only, unversioned_types/unversioned_cores the rest;
the cache says provenance_rule 'v1' (tools/autopilot/ownership.py counts only such caches).
RE-SIGN (COORD ruling 2026-10-30 02:03 (3b)): a hand-built SIGNED block counts when its SAME routed DB is re-signed
(signoff.py TT/FF/DRC + post-route LEC) with tools at a released flow tag; the re-sign dir holds signoff.json and a
PROVENANCE.json {kind: 'resign', verdict: 'SIGNED', src_commit: <tag commit>, flow_tag, routed_db, build_commit, lec}.
It counts only with all fields, LEC verdict EQUIVALENT, the routed DB present and flow_tag -> src_commit on origin.
GRANDFATHER (COORD ruling 2026-10-25 19:13): a SIGNED record completed before the first flow-* tag on origin (or while
no flow tag exists) counts as SIGNED-LEGACY -- in signed_types/signed_cores, ref suffixed 'SIGNED-LEGACY' -- when it
names a source commit or a run dir (its scanned path is the run dir; origin/main records name main).  The
src_commit + flow_tag requirement applies only to records generated after the first tag.
Cached in ~/.local/state/fleet-viz/release_tree_plan_cache.json; refreshed when older than REFRESH_S (the hourly
release-tree-render.timer calls this through release_tree_render.py). On any failure the last good per-die values are
kept and the error is reported (the page keeps rendering).
Run alone: python3 tools/release_tree_plan.py [--force] [--print]
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, concurrent.futures as cf

REPO = pathlib.Path('/home/ubuntu/OpenTallas')
CACHE = pathlib.Path.home() / '.local/state/fleet-viz/release_tree_plan_cache.json'
REFRESH_S = 50 * 60
# release-tree die key -> (plan dir under physical/die_plan, plan-of-record file relative to the repo root).
# COUNT-REP (COORD 20:13 10-30, FLOW-12): count against the PLAN OF RECORD, not the stale <dir>/die_plan.json.
# Entry = (die key, plan dir below physical/die_plan, plan-of-record file (repo path, .json or .json.gz), overlays).
# The plan is materialised as <plan dir>/por__<name> (in place when it already lives there uncompressed) so its
# plan-relative tables (pins files, die_io, core_conns, ../census, bind/...) resolve as in the die owner's G0C; overlays =
# plan_of_record data dirs (below physical/die_plan) whose files (*.gz gunzipped, 'die_plan.json' skipped) are laid into
# the plan dir first, in order (HBM: d35a holds every referenced cores/*.json + side JSON as .gz).  Repo-relative
# 'results/...' tables the plan names are fetched too.  Re-point a line here when a die's plan of record changes.
_HBM_POR = 'physical/die_plan/hbm/plan_of_record/'
PLANS = [('s81', 's81', 'physical/die_plan/s81/plan_h2_2249.json', ()),                         # event3 composed (12.20)
         ('s81_head', 's81_head', 'results/die_head_47_1031/l47/source_plan_l47.json.gz', ()),   # HEAD l47 (APPROVED, main c68675660; ROOT-MERGE-AI 04:20 READY, SIGNOFF-SPRINT-11 10-31; was l46a)
         ('qwen_compute', 'qwen_compute/plan_of_record', 'physical/die_plan/qwen_compute/plan_of_record/plan_qc50.json', ()),
         ('qwen_kvsys', 'qwen_kvsys/plan_of_record', 'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json', ()),  # event28w_c
         ('hbm', 'hbm/plan_of_record/d44c', _HBM_POR + 'd44c/die_plan.json.gz',   # d44c = HBM POR + freeze plan (COORD 20:19)
          tuple('hbm/plan_of_record/' + x for x in ('d35a', 'd35b', 'd35c')))]
# PIN ALIASES (FLOW-15 2026-10-31, SIGNOFF-SPRINT-10 ASK (b)): a plan built in a lane tree may name a plan-relative pins
# file that is not on main under that name; its byte-identical main copy elsewhere is laid at the plan-relative path
# before the designs are read (sha256 checked: a different file is an error, never a silent substitute).  This wins
# over the same-name <die>/cores/ fallback in plan_designs.  Key = die key of PLANS; value {plan-relative path:
# (repo path on main, sha256)}.
PIN_ALIASES = {
    's81_head': {   # HEAD l46a lep_pair 777.6x492.48 (lane tree intel2 head_source_l46a/core_pins, sha 0e40649d CHECKED)
        'core_pins/lep_pair_pins_777.json': ('results/die_head_33_1029/lep/lep_pair_pins_777.json',
                                             '0e40649dca0fc3f1a6e55543e5d6679c327ffe1e7f81ba8ec846831ceea70351')},
}


def materialize_pin_aliases(plan_dir, aliases, rev='origin/main', read=None):
    """lay each alias target (repo path on rev) at plan_dir/<plan-relative path> when that path is absent; -> laid paths.
    read(repo path) -> bytes (default: git show rev:path); RuntimeError on a sha256 mismatch or a missing target."""
    import hashlib
    def _git(path):
        r = subprocess.run(['git', '-C', str(REPO), 'show', '%s:%s' % (rev, path)], capture_output=True, timeout=120)
        if r.returncode: raise RuntimeError('pin alias target %s not on %s' % (path, rev))
        return r.stdout
    read = read or _git
    laid = []
    for rel, (target, want) in sorted((aliases or {}).items()):
        dst = pathlib.Path(plan_dir) / rel
        if dst.exists(): continue
        data = read(target)
        got = hashlib.sha256(data).hexdigest()
        if got != want: raise RuntimeError('pin alias %s -> %s sha256 %s != %s' % (rel, target, got[:12], want[:12]))
        dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data); laid.append(rel)
    return laid


REF_RE = re.compile(r'"(results/[^":]+?\.(?:json|tsv|txt)(?:\.gz)?)[":]')


MEM_MACRO_LEF = 'physical/asap7_memory_macros'   # generated SRAM/ROM macros (rom_gen / sram views): not signed-off designs


def is_mem_macro(h):
    """a hard_cores entry that is a generated memory macro (LEF under physical/asap7_memory_macros*): these never carry a
    signoff.py record (OWNER 10-25 ROMs = generated macros), so they stay out of the hard-core design count (FLOW-12 ASK
    default, COUNT-REP); listed per plan as memory_macros."""
    return str(h.get('lef') or '').startswith(MEM_MACRO_LEF)


def plan_label(src):
    """cache / page key of a plan of record: its path below physical/die_plan (else the repo path), without .gz"""
    s = src[:-3] if src.endswith('.gz') else src
    return s[len('physical/die_plan/'):] if s.startswith('physical/die_plan/') else s


def plan_archive_paths(plans=None):
    """git archive paths: tools, each plan's die dir (physical/die_plan/<first part>), plan files outside it"""
    plans = plans or PLANS
    dirs = {'tools'} | {'physical/die_plan/' + pd.split('/')[0] for _, pd, _, _ in plans}
    return sorted(dirs | {src for _, _, src, _ in plans if not any(src.startswith(x + '/') for x in dirs)})


def materialize_plan(root, plan_dir, src, overlays=()):
    """write the plan-of-record file `src` (repo-relative, .json or .json.gz, already extracted under root) as plain JSON
    into root/physical/die_plan/<plan_dir>/por__<name> (after laying the overlay dirs' files into plan_dir) and return
    that path (no copy when it already lives there uncompressed)."""
    import gzip
    root = pathlib.Path(root); base = root / 'physical/die_plan' / plan_dir
    for ov in overlays:
        od = root / 'physical/die_plan' / ov
        if not od.is_dir(): raise RuntimeError('plan overlay %s missing' % ov)
        for f in sorted(od.rglob('*')):
            if not f.is_file(): continue
            rel = f.relative_to(od).as_posix()
            rel = rel[:-3] if rel.endswith('.gz') else rel
            if rel in ('die_plan.json', 'SHA256SUMS'): continue
            t = base / rel; t.parent.mkdir(parents=True, exist_ok=True)
            t.write_bytes(gzip.decompress(f.read_bytes()) if f.name.endswith('.gz') else f.read_bytes())
    f = root / src
    name = pathlib.Path(src[:-3] if src.endswith('.gz') else src).name
    dst = base / name
    if f == dst: return dst
    dst = dst.with_name('por__' + name)   # never over an older plan file of that dir (hbm/die_plan.json is the 10-2x plan)
    data = gzip.decompress(f.read_bytes()) if src.endswith('.gz') else f.read_bytes()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.read_bytes() != data: raise RuntimeError('plan %s would overwrite a different %s' % (src, dst))
    dst.write_bytes(data)
    return dst


def fetch_results_refs(root, plan_path, rev='origin/main'):
    """extract the repo-relative results/... tables a plan names (existing on rev) under root; -> list of fetched paths"""
    refs = sorted(set(REF_RE.findall(pathlib.Path(plan_path).read_text())))
    have = [r for r in refs if not (pathlib.Path(root) / r).exists() and
            sh(['git', '-C', str(REPO), 'cat-file', '-e', '%s:%s' % (rev, r)], 30).returncode == 0]
    if have:
        p1 = subprocess.Popen(['git', '-C', str(REPO), 'archive', rev] + have, stdout=subprocess.PIPE)
        subprocess.run(['tar', '-x', '-C', str(root)], stdin=p1.stdout, capture_output=True, timeout=600); p1.wait(60)
    return have


HOSTS = ['local', 'epyc2', 'intel1', 'intel2']
SCAN_ROOTS = '/srv/opentallas-scratch /srv/opentallas-scratch2'
# RETIRED sign-offs (HEAD-CORE-R13 2026-10-27): a SIGNED record of a superseded build (older RTL / flow) that must not
# count for the current design. One line per record: '<scan_host>:<path>\t<date>\t<lane>\t<reason>' ('#' = comment).
# Matching records are dropped from signed_records / signed_* and listed in retired_records (visible, not deleted).
# RETIRE BY NAME (COORD ruling 2026-10-30 14:40, FLOW-11): a path line only covers that one copy, and a fresh worktree /
# release cache copies the same record to a new path.  Two rules close that:
#  (a) COPY: a SIGNED record with the same identity (name, face_guard top, generated) as a path-retired record is retired
#      too, wherever it lives;
#  (b) NAME line 'name:<die>:<type key or module>\t<date>\t<lane>\t<reason>' (<die> = release-tree die key, e.g. s81)
#      retires every SIGNED record of that die type / hard core generated BEFORE <date> ('YYYY-MM-DD[ HH:MM[ TZ]]', local
#      time; a record without a readable 'generated' is retired).  A fresh build signed off after <date> counts again.
RETIRED = pathlib.Path(__file__).resolve().parent.parent / 'RETIRED_SIGNOFFS.tsv'


def _retired_lines(path=None):
    try: lines = pathlib.Path(path or RETIRED).read_text().splitlines()
    except Exception: return []
    out = []
    for ln in lines:
        if not ln.strip() or ln.startswith('#'): continue
        f = ln.split('\t')
        out.append((f[0].strip(), f))
    return out


def retired_refs(path=None):
    """'<scan_host>:<path>' -> reason text (path lines only)"""
    return {k: '\t'.join(f[1:]).strip() for k, f in _retired_lines(path) if not k.startswith('name:')}


def _date_ts(s):
    import datetime
    m = re.match(r'^\s*(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}:\d{2}))?', s or '')
    if not m: return None
    return datetime.datetime.strptime(m.group(1) + ' ' + (m.group(2) or '00:00'), '%Y-%m-%d %H:%M').timestamp()


def retired_names(path=None):
    """(die, type key or module) -> (cutoff unix time or None, reason text) for 'name:<die>:<name>' lines"""
    out = {}
    for k, f in _retired_lines(path):
        if not k.startswith('name:'): continue
        parts = k.split(':', 2)
        if len(parts) != 3 or not parts[1] or not parts[2]: continue
        out[(parts[1], parts[2])] = (_date_ts(f[1] if len(f) > 1 else ''), '\t'.join(f[1:]).strip())
    return out


def rec_ident(r):
    return (r.get('name'), r.get('top'), str(r.get('generated')))


def split_retired(recs, ret):
    """-> (kept, retired): path-retired records plus every copy of one (same name/top/generated at another path)"""
    ref = lambda r_: r_['scan_host'] + ':' + r_['path']
    ids = {rec_ident(r_): ret[ref(r_)] for r_ in recs if ref(r_) in ret and r_.get('generated') is not None}
    kept, gone = [], []
    for r_ in recs:
        why = ret.get(ref(r_))
        if why is None and r_.get('generated') is not None and rec_ident(r_) in ids:
            why = 'COPY of a retired record: ' + ids[rec_ident(r_)]
        (kept if why is None else gone).append(r_ if why is None else dict(r_, retired=why))
    return kept, gone


def name_retired(r_, die, names, keys):
    """reason when record r_ (matched to die type/core names 'keys') is retired by a 'name:' line, else None"""
    for k in keys:
        hit = names.get((die, k))
        if not hit: continue
        cut, why = hit
        t = gen_ts(r_)
        if cut is None or t is None or t < cut:
            return 'name:%s:%s %s' % (die, k, why)
    return None
PROV_PY = r'''
RESIGN_KEYS = ('src_commit', 'flow_tag', 'routed_db', 'build_commit', 'lec')
def resign(f, x, load):
    # COORD ruling 2026-10-30 02:03 (3b): RE-SIGN record = a routed DB re-checked (signoff.py TT/FF/DRC + post-route LEC)
    # with tools at a released flow tag.  PROVENANCE.json {kind: resign, src_commit: tag commit, flow_tag, routed_db,
    # build_commit: original build commit, lec: post-route lec.json}.  Counts only when every field is present, the
    # routed DB exists and the LEC verdict is EQUIVALENT; the tag -> src_commit match is checked on the hub (refresh).
    miss = [k for k in RESIGN_KEYS if not x.get(k)]
    if miss:
        return dict(resign_error='re-sign PROVENANCE %s lacks %s' % (f, ','.join(miss)), prov_file=f)
    lp = x['lec'] if os.path.isabs(x['lec']) else os.path.join(os.path.dirname(f), x['lec'])
    db = x['routed_db'] if os.path.isabs(x['routed_db']) else os.path.join(os.path.dirname(f), x['routed_db'])
    try:
        lv = (load(lp) or {}).get('verdict')
    except Exception:
        lv = None
    if lv != 'EQUIVALENT':
        return dict(resign_error='re-sign LEC %s verdict %s' % (lp, lv), prov_file=f)
    if not os.path.exists(db):
        return dict(resign_error='re-sign routed DB %s missing' % db, prov_file=f)
    return dict(src_commit=x['src_commit'], flow_tag=x['flow_tag'], prov_file=f, resign=True, routed_db=db,
                build_commit=x['build_commit'], lec=lp)
def prov(p, d, load):
    if d.get('src_commit') and d.get('flow_tag'):
        return dict(src_commit=d['src_commit'], flow_tag=d['flow_tag'], prov_file=p)
    q = os.path.dirname(p)
    for _ in range(6):
        for n in ('PROVENANCE.json', 'AUTOPILOT.json'):
            f = os.path.join(q, n)
            try:
                x = load(f)
            except Exception:
                continue
            if not isinstance(x, dict):
                continue
            # SIGNOFF-SPRINT-6 10-30 (FLOW-11): a kit's own build record (lec.write_kit_provenance, schema
            # opentallas.kit_provenance.v1, no flow_tag) is not the sign-off provenance: skip it and keep looking
            # upward for the resign / tagged record (KV PHY103 was unversioned by it, SPRINT-4 13:10).
            if n == 'PROVENANCE.json' and str(x.get('schema', '')).endswith('kit_provenance.v1'):
                continue
            if n == 'PROVENANCE.json' and x.get('verdict') not in (None, 'SIGNED'):
                return {}
            if n == 'PROVENANCE.json' and x.get('kind') == 'resign':
                return resign(f, x, load)
            if x.get('src_commit') and x.get('flow_tag'):
                return dict(src_commit=x['src_commit'], flow_tag=x['flow_tag'], prov_file=f)
            return {}
        nq = os.path.dirname(q)
        if nq == q: break
        q = nq
    return {}
'''
SCAN_PY = r'''
import json, os, sys
''' + PROV_PY + r'''
out = []
for p in sys.stdin.read().split():
    try:
        if os.path.getsize(p) > 8 << 20: continue
        d = json.load(open(p))
    except Exception: continue
    if not isinstance(d, dict) or d.get('verdict') != 'SIGNED': continue
    fg = d.get('face_guard') or {}
    r = dict(path=p, name=d.get('name'), top=fg.get('top') if isinstance(fg, dict) else None,
             generated=d.get('generated'), host=d.get('host'), pins_path=fg.get('pins') if isinstance(fg, dict) else None)
    r.update(prov(p, d, lambda f: json.load(open(f))))
    r['versioned'] = bool(r.get('src_commit') and r.get('flow_tag'))
    out.append(r)
print(json.dumps(out))
'''


def sh(cmd, timeout, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw)


def scan_host(h):
    find = "nice -n 15 ionice -c3 find %s -xdev \\( -name signoff.json -o -name '*.signoff.json' \\) -size -8M 2>/dev/null" % SCAN_ROOTS
    if h == 'local':
        cmd = ['bash', '-c', find + ' | python3 -c %s' % shlex_quote(SCAN_PY)]
    else:
        cmd = ['ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', '-o', 'ControlPath=none', h,
               find + ' | python3 -c %s' % shlex_quote(SCAN_PY)]
    r = sh(cmd, 300)
    if r.returncode != 0 and not r.stdout.strip():
        raise RuntimeError('%s: rc %d %s' % (h, r.returncode, r.stderr.strip()[-200:]))
    recs = json.loads(r.stdout.strip().splitlines()[-1])
    for x in recs: x['scan_host'] = h
    return recs


def shlex_quote(s):
    import shlex
    return shlex.quote(s)


def first_flow_tag_ts():
    """unix time of the oldest flow-* tag on origin, or None when no flow release exists yet (GRANDFATHER cutoff)."""
    sh(['git', '-C', str(REPO), 'fetch', '-q', '--tags', 'origin'], 180)
    r = sh(['git', '-C', str(REPO), 'for-each-ref', '--sort=creatordate', '--format=%(creatordate:unix)', 'refs/tags/flow-*'], 30)
    ts = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    return min(ts) if ts else None


def tag_commit(tag):
    r = sh(['git', '-C', str(REPO), 'rev-parse', '-q', '--verify', 'refs/tags/%s^{commit}' % tag], 30)
    return r.stdout.strip() if r.returncode == 0 else ''


def check_resign_tag(r, tag_commit=tag_commit):
    """a RE-SIGN record counts only when its flow_tag is a flow release tag on origin whose commit is its src_commit
    (the re-sign tools ran at the released flow); otherwise it is unversioned with the reason."""
    if not r.get('resign'): return r
    full = tag_commit(r['flow_tag']) if re.match(r'^flow-\d{8}-[a-z](?:-(qc|s81|head|kv|hbm))?$', r['flow_tag'] or '') else ''
    sc = str(r.get('src_commit') or '')
    if not full or len(sc) < 7 or not full.startswith(sc):
        r['resign_error'] = 're-sign flow_tag %s %s src_commit %s' % (r['flow_tag'], 'is at ' + full[:12] if full else 'not a flow tag on origin', sc[:12])
        r['versioned'] = False
    return r


def gen_ts(r):
    g = r.get('generated')
    if isinstance(g, (int, float)): return float(g)
    if isinstance(g, str):
        try:
            import datetime
            return datetime.datetime.fromisoformat(g.replace('Z', '+00:00')).timestamp()
        except Exception:
            return None
    return None


def is_legacy(r, cutoff):
    """GRANDFATHER: unversioned SIGNED record made before the first flow tag that names a src commit or run dir."""
    if r.get('versioned') or r.get('resign_error'): return False
    names = bool(r.get('src_commit') or r.get('source_commit') or r.get('path'))
    if not names: return False
    if cutoff is None: return True
    t = gen_ts(r)
    return t is not None and t < cutoff


_PROV_NS = {'os': os}
exec(PROV_PY, _PROV_NS)


def main_records(tree):
    out = []
    for p in tree.rglob('*signoff.json'):
        try: d = json.loads(p.read_text())
        except Exception: continue
        if isinstance(d, dict) and d.get('verdict') == 'SIGNED':
            fg = d.get('face_guard') or {}
            r = dict(path='origin/main:' + str(p.relative_to(tree)), name=d.get('name'), top=fg.get('top') if isinstance(fg, dict) else None,
                     generated=d.get('generated'), host=d.get('host'), scan_host='origin/main',
                     pins_path=fg.get('pins') if isinstance(fg, dict) else None)
            r.update(_PROV_NS['prov'](str(p), d, lambda f: json.loads(pathlib.Path(f).read_text())))
            if r.get('prov_file', '').startswith(str(tree)):
                r['prov_file'] = 'origin/main:' + str(pathlib.Path(r['prov_file']).relative_to(tree))
            r['versioned'] = bool(r.get('src_commit') and r.get('flow_tag'))
            # FLOW-12 10-30: the view's own pins.json + config.mk beside its signoff.json (S81 cores/views/<m>/) on main
            mp = main_view_pins(p.parent)
            if mp: MAIN_PINS[r['path']] = mp
            out.append(r)
    return out


MAIN_PINS = {}   # origin/main record path -> {rows, outline_nm, read} (filled by main_records of this refresh)


def main_view_pins(d):
    try:
        doc = json.loads((d / 'pins.json').read_text())
    except Exception:
        return None
    ol = None
    try:
        for ln in (d / 'config.mk').read_text(errors='replace').splitlines():
            m = re.match(r'\s*(?:export\s+)?DIE_AREA\s*[:?]?=\s*(.*)$', ln)
            if m:
                da = [float(x) for x in m.group(1).split()]
                if len(da) == 4: ol = (_nm(da[2] - da[0]), _nm(da[3] - da[1]))
    except Exception:
        pass
    out = dict(rows=canon_pin_rows(doc), outline_nm=ol, read='origin/main:' + str(d / 'pins.json'))
    # FLOW-13: the view's signed LEF beside pins.json (its pin shapes, for pin_compare)
    lefs = sorted(d.glob('*.lef'))
    if len(lefs) == 1:
        try:
            sh_ = lef_pin_shapes(lefs[0].read_text(errors='replace'))
            if sh_: out['shapes'] = sh_
        except Exception:
            pass
    return out


def rec_keys(r):
    ks = set()
    for v in (r.get('top'), r.get('name')):
        if not v: continue
        ks.add(v)
        m = re.match(r'^(dp|kr)_(.+)$', v)
        if m:
            ks.add(m.group(2)); ks.add(re.sub(r'_(lfp|r\d+|c\d+)$', '', m.group(2)))
    return ks


# COUNT PER DESIGN (OWNER 12.22 (3) 2026-10-30 18:44, lane COUNT-REP-1): a hard core counts per DESIGN, not per module
# name and not per instance.  Design = (module, outline, pin table without strap_* pins).  Every plan instance of a
# design -- other partitions / types, another orientation (R0/MX/MY/R180 placement of the same view) or other declared
# parent_id_straps values (owner 10-25 option B: ID straps tied at the parent) -- is an identical COPY and is credited
# when its design is signed off (owner 10-25 template-replica rule; copies keep the automated GEOM checks + 1-in-10
# visual sample, see replica_sample()).  NO FALSE CREDIT: a module whose plan entries use two or more different pin
# tables / outlines is two or more designs; a SIGNED record of that module credits only the design whose pin table
# its own face_guard pins file matches (same pin names, same layer, |dx|,|dy| <= PIN_TOL_NM) and whose outline its
# kit DIE_AREA matches; a record whose pins cannot be read or match no design credits none of them
# (design_unmatched).  Different module names are never merged here: the plan carries no netlist identity.
PIN_TOL_NM = 200


def _nm(v):
    return int(round(float(v) * 1000))


def canon_pin_rows(doc):
    """{pin name: (layer, x_nm, y_nm)} of a pins file in any of its forms (list of {name|bus,bit, layer, x, y} or
    {"pins": [...]}); strap_* pins are left out (declared ID ties, owner 10-25 option B)."""
    rows = doc if isinstance(doc, list) else (doc.get('pins', []) if isinstance(doc, dict) else [])
    out = {}
    for q in rows:
        if not isinstance(q, dict): continue
        n = q.get('name')
        if n is None and q.get('bus') is not None:
            n = '%s[%s]' % (q['bus'], q['bit']) if q.get('bit') is not None else q['bus']
        if n is None or 'strap_' in str(n): continue
        try: out[str(n)] = (q.get('layer'), _nm(q['x']), _nm(q['y']))
        except Exception: out[str(n)] = (q.get('layer'), None, None)
    return out


def pins_sha(rows):
    import hashlib
    return hashlib.sha256(json.dumps(sorted([k] + list(v) for k, v in rows.items())).encode()).hexdigest()[:16]


def pins_close(a, b, tol=PIN_TOL_NM):
    """same pin names, same layer per pin, every pin within tol nm in x and y"""
    if not a or set(a) != set(b): return False
    for n, (la, xa, ya) in a.items():
        lb, xb, yb = b[n]
        if la != lb or None in (xa, ya, xb, yb) or abs(xa - xb) > tol or abs(ya - yb) > tol: return False
    return True


# FLOW-13 10-30 (COORD 22:5x): automatic pin compare, no person judges a difference.  Both sides are reduced to the same
# reference: pin-shape centre in core (LEF-origin) coordinates on the same layer.  A plan pin table names its source
# LEF and pick rule ('lef' + 'source': core_pins_gen.py / CORE-KS = centre of the pin's LARGEST non-M1 rect); a signed
# view keeps its own rects (e.g. only the edge port of a 2-port plan pin: S81 dsfd_node fi[0]/fo[0], plan centre of
# the 2.1-um stub y 1.0765 vs view edge port y 0.042, same M5 track).  Per pin:
#   match      same layer, centres within PIN_TOL_NM;
#   convention same layer, one side's centre lies inside one of the OTHER side's shapes of that pin on that layer
#              (exact track; GRID_NM rounding only) = the same pin under a different centre/edge convention;
#   moved      anything else (other layer, other track / position);
#   extra / missing  record-only / plan-only pin names.
# A record credits a design iff it has no moved, extra or missing pin (match + convention only).
GRID_NM = 1


def lef_pin_shapes(txt, mod=None):
    """{pin: [(layer, x0, y0, x1, y1) nm]} of every signal pin RECT in a LEF (MACRO mod, else the first MACRO)."""
    out, inm, cur, layer = {}, False, None, None
    for ln in txt.splitlines():
        t = ln.split()
        if not t: continue
        if not inm:
            inm = t[0] == 'MACRO' and len(t) > 1 and (mod is None or t[1] == mod)
            continue
        if cur is None:
            if t[0] == 'PIN' and len(t) > 1: cur, layer, rs, use = t[1], None, [], 'SIGNAL'
            elif t[0] == 'END' and len(t) > 1 and t[1] not in ('PROPERTYDEFINITIONS', 'OBS'):
                if mod is None or t[1] == mod: break
            continue
        if t[0] == 'END' and len(t) > 1 and t[1] == cur:
            if use not in ('POWER', 'GROUND') and 'strap_' not in cur: out[cur] = rs
            cur = None
        elif t[0] == 'USE' and len(t) > 1: use = t[1].rstrip(';')
        elif t[0] == 'LAYER' and len(t) > 1: layer = t[1]
        elif t[0] == 'RECT' and len(t) >= 5:
            try: rs.append((layer,) + tuple(_nm(x) for x in t[1:5]))
            except ValueError: pass
    return out


def _inside(pt, shapes, layer):
    x, y = pt
    return any(r[0] == layer and r[1] - GRID_NM <= x <= r[3] + GRID_NM and r[2] - GRID_NM <= y <= r[4] + GRID_NM for r in shapes or ())


def pin_compare(a, b, a_shapes=None, b_shapes=None, tol=PIN_TOL_NM):
    """record rows a vs plan rows b ({pin: (layer, x_nm, y_nm)}), optional shapes {pin: [(layer, x0, y0, x1, y1)]} per
    side -> {match, convention, moved, extra, missing: sorted pin names}"""
    a, b = a or {}, b or {}
    res = dict(match=[], convention=[], moved=[], extra=sorted(set(a) - set(b)), missing=sorted(set(b) - set(a)))
    for n in sorted(set(a) & set(b)):
        (la, xa, ya), (lb, xb, yb) = a[n], b[n]
        if la != lb or None in (xa, ya, xb, yb): res['moved'].append(n); continue
        if abs(xa - xb) <= tol and abs(ya - yb) <= tol: res['match'].append(n); continue
        if _inside((xa, ya), (b_shapes or {}).get(n), lb) or _inside((xb, yb), (a_shapes or {}).get(n), la):
            res['convention'].append(n)
        else:
            res['moved'].append(n)
    return res


def accept_die_owned_ft(cmp_, design):
    """move record-only pins the plan design declares die-owned feedthrough (core_die_owned_ft.v1) from 'extra' to
    'die_owned_ft' (accepted, not a miss)"""
    ftn = set((design or {}).get('die_owned_ft') or ())
    if ftn and cmp_['extra']:
        cmp_ = dict(cmp_, extra=[n for n in cmp_['extra'] if n not in ftn],
                    die_owned_ft=[n for n in cmp_['extra'] if n in ftn])
    # FLOW-15 10-31: pins the plan pin table itself declares excluded (excluded_clock / excluded_pg: the clock pin is
    # placed by the clock plan, PG by the PDN) are accepted record extras, not misses (HEAD lep_pair clk)
    exn = set((design or {}).get('plan_excluded') or ())
    if exn and cmp_['extra']:
        cmp_ = dict(cmp_, extra=[n for n in cmp_['extra'] if n not in exn],
                    plan_excluded=[n for n in cmp_['extra'] if n in exn])
    return cmp_


def pins_equiv(cmp_):
    return bool(cmp_['match'] or cmp_['convention']) and not (cmp_['moved'] or cmp_['extra'] or cmp_['missing'])


_LEF_SHAPES = {}


def repo_lef_shapes(path, module=None):
    """pin shapes of a LEF named by a plan pin table ('lef'), read from origin/main (.zst decompressed); None if absent"""
    k = (path, module)
    if k not in _LEF_SHAPES:
        v = None
        try:
            r = subprocess.run(['git', '-C', str(REPO), 'show', 'origin/main:' + path], capture_output=True, timeout=120)
            raw = r.stdout if r.returncode == 0 else None
            if raw and path.endswith('.zst'):
                raw = subprocess.run(['zstd', '-dc'], input=raw, capture_output=True, timeout=120).stdout
            if raw: v = lef_pin_shapes(raw.decode(errors='replace'), module) or None
        except Exception:
            v = None
        _LEF_SHAPES[k] = v
    return _LEF_SHAPES[k]


def plan_designs(P, plan_dir, read=None):
    """-> (designs {design id: {module, outline_um, pins_sha, pins_files, entries, instances, types, orients,
    strap_variants}}, rows {design id: canonical pin rows}).  design id = module when the module has one design,
    else module#<outline>/<pins sha>."""
    def _read(f):
        # FLOW-12 10-30: a plan built in a lane tree names core_pins/<x>.json that is not on main (HEAD l46a, ASK (b));
        # fall back to the die's checked-in pins of the same name, <die dir>/cores/<x>.json (HEAD l46a elemA/elemB/
        # lep_pair checked byte/pin-identical to the lane tree's core_pins 10-30 21:5x)
        q = pathlib.Path(plan_dir) / f
        if not q.exists() and (pathlib.Path(plan_dir) / 'cores' / pathlib.Path(f).name).exists():
            q = pathlib.Path(plan_dir) / 'cores' / pathlib.Path(f).name
        return json.loads(q.read_text())
    read = read or _read
    T = P.get('partition_types') or {}
    tcount = {}
    for p in P.get('partitions') or []:
        tcount[p.get('type')] = tcount.get(p.get('type'), 0) + 1
    cache, groups, rows, lefs, excl = {}, {}, {}, {}, {}
    for tk, v in T.items():
        for h in v.get('hard_cores') or []:
            m = h.get('module')
            if not m or is_mem_macro(h): continue
            pf = h.get('pins_file')
            if pf not in cache:
                try: doc = read(pf) if pf else None
                except Exception: doc = None
                r = canon_pin_rows(doc) if doc is not None else None
                cache[pf] = (pins_sha(r), r) if r else ('file:%s' % pf, None)
                # FLOW-13: the table's source LEF (pick-rule reference for pin_compare)
                lefs[pf] = doc.get('lef') if isinstance(doc, dict) and isinstance(doc.get('lef'), str) else None
                excl[pf] = sorted({str(n) for k in ('excluded_clock', 'excluded_pg') for n in
                                   ((doc.get(k) or []) if isinstance(doc, dict) and isinstance(doc.get(k), list) else [])})
            ps, r = cache[pf]
            ol = tuple(_nm(x) for x in (h.get('outline_um') or []))
            g = groups.setdefault((m, ol, ps), dict(module=m, outline_um=[x / 1000 for x in ol], pins_sha=ps, pins_files=[],
                                                    entries=0, instances=0, types=[], orients=[], strap_variants=[]))
            rows[(m, ol, ps)] = r
            g['entries'] += 1; g['instances'] += tcount.get(tk, 0)
            if lefs.get(pf) and not g.get('pins_lef'): g['pins_lef'] = lefs[pf]
            if excl.get(pf): g['plan_excluded'] = sorted(set(g.get('plan_excluded', [])) | set(excl[pf]))
            for k, x in (('pins_files', pf), ('types', tk), ('orients', h.get('orient') or 'R0'),
                         ('strap_variants', json.dumps(h.get('parent_id_straps'), sort_keys=True) if h.get('parent_id_straps') else None)):
                if x is not None and x not in g[k]: g[k].append(x)
    # FLOW-14 10-31: declared die-owned feedthrough ports (opentallas.core_die_owned_ft.v1 sidecars anywhere below the
    # plan dir, e.g. cores/ or cores/su/signed/: the die routes them through the core, e.g. HBM ring_ag mp_isl*) are accepted record extras of the design
    # whose pins file the sidecar names (plan_core_pins), or of every design of its module when it names none
    ft = []
    for f in sorted(pathlib.Path(plan_dir).rglob('*die_owned_ft*.json')):
        try: doc = json.loads(f.read_text())
        except Exception: continue
        if isinstance(doc, dict) and doc.get('schema') == 'opentallas.core_die_owned_ft.v1' and doc.get('module'):
            ft.append((doc['module'], pathlib.Path(doc.get('plan_core_pins') or '').name,
                       sorted(str(q.get('name')) for q in doc.get('die_owned_ft_pins') or [] if q.get('name')), f.name))
    for (m, _, _), g in groups.items():
        for fm, fp, names, fn in ft:
            if fm == m and names and (not fp or fp in {pathlib.Path(x).name for x in g['pins_files']}):
                g['die_owned_ft'] = sorted(set(g.get('die_owned_ft', [])) | set(names))
                g.setdefault('die_owned_ft_files', []).append(fn)
    nmod = {}
    for (m, _, _) in groups: nmod[m] = nmod.get(m, 0) + 1
    D, R = {}, {}
    for (m, ol, ps), g in groups.items():
        tag = ps if not ps.startswith('file:') else 'file-' + pins_sha({ps: ()})[:12]   # unreadable pins file: its name decides
        did = m if nmod[m] == 1 else '%s#%gx%g/%s' % (m, ol[0] / 1000 if ol else 0, ol[1] / 1000 if len(ol) > 1 else 0, tag)
        assert did not in D, did
        g['strap_variants'] = len(g['strap_variants'])
        D[did] = g; R[did] = rows[(m, ol, ps)]
    return D, R


REC_PINS_PY = r"""
import glob, json, os, re, sys
out = {}
# FLOW-14 10-31 (SIGNOFF-SPRINT-10 HBM ring_ag): the pins a record signed are the ROUTED DB's pins, not the kit INPUT
# pins.json (what the flow was asked to place).  Order: (0) routed DEF = PROVENANCE.json routed_db (re-sign record) with
# .def beside the .odb, else the one <kit>/run/results/*/*/base/6_final.def of the record's kit; (1) the face_guard kit
# pins.json; (2) <kit>/pins.json; (3) the signed abstract LEF beside the record.  'read' names the file, 'source' the kind.
_OR = {'N': lambda x, y: (x, y), 'S': lambda x, y: (-x, -y), 'E': lambda x, y: (-y, x), 'W': lambda x, y: (y, -x),
       'FN': lambda x, y: (-x, y), 'FS': lambda x, y: (x, -y), 'FE': lambda x, y: (y, x), 'FW': lambda x, y: (-y, -x)}
def _routed_def(key, sp):
    rd = os.path.dirname(sp)
    for pv in (os.path.join(rd, 'PROVENANCE.json'), os.path.join(os.path.dirname(rd), 'PROVENANCE.json')):
        try: db = json.load(open(pv)).get('routed_db')
        except Exception: continue
        if isinstance(db, str):
            c = os.path.splitext(db)[0] + '.def'
            if os.path.isfile(c): return c
    for kit in (os.path.dirname(rd), os.path.dirname(key)):
        c = glob.glob(os.path.join(kit, 'run', 'results', '*', '*', 'base', '6_final.def'))
        if len(c) == 1: return c[0]
    return None
def _read_def(path):
    # PINS section of a DEF: signal pins -> (name, layer, centre um) of the first PORT shape + every shape (nm)
    u, da, pins, shapes, cur, inp = 1000.0, None, [], {}, None, False
    def flush():
        if cur and cur['use'] not in ('POWER', 'GROUND') and cur['rects'] and cur['pl']:
            px, py, o = cur['pl']; f = _OR.get(o, _OR['N']); rs = []
            for (L, x0, y0, x1, y1) in cur['rects']:
                ax, ay = f(x0, y0); bx, by = f(x1, y1)
                rs.append((L, px + min(ax, bx), py + min(ay, by), px + max(ax, bx), py + max(ay, by)))
            L, x0, y0, x1, y1 = rs[0]
            pins.append(dict(name=cur['name'], layer=L, x=round((x0 + x1) / 2 / u, 4), y=round((y0 + y1) / 2 / u, 4)))
            shapes[cur['name']] = [[r[0]] + [int(round(v * 1000.0 / u)) for v in r[1:]] for r in rs]
    import mmap
    with open(path, 'rb') as fb:   # header lines, then jump past COMPONENTS to the PINS section (mmap find, no full parse)
        mm = mmap.mmap(fb.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            i = mm.find(b'\nPINS ')
            if i < 0: return [], None, {}
            j = mm.find(b'\nEND PINS', i)
            head = mm[:min(i, 1 << 20)].decode(errors='replace').splitlines()
            body = mm[i + 1:(j if j > 0 else len(mm))].decode(errors='replace').splitlines()
        finally: mm.close()
    for ln in head:
        if ln.startswith('UNITS DISTANCE MICRONS'): u = float(ln.split()[3])
        elif ln.startswith('DIEAREA'):
            v = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', ln)]
            if len(v) >= 4: da = [v[0] / u, v[1] / u, v[2] / u, v[3] / u]
    if True:
        for ln in body:
            if not inp:
                inp = ln.startswith('PINS ')
                continue
            if ln.startswith('END PINS'): break
            m = re.match(r'\s*-\s+(\S+)\s', ln)
            if m:
                flush(); cur = dict(name=m.group(1).replace('\\', ''), use='SIGNAL', rects=[], pl=None, layer=None)
            if cur is None: continue
            m = re.search(r'\+\s*USE\s+(\w+)', ln)
            if m: cur['use'] = m.group(1)
            for m in re.finditer(r'\+\s*LAYER\s+(\S+)(?:\s+MASK\s+\d+)?(?:\s+SPACING\s+\d+|\s+DESIGNRULEWIDTH\s+\d+)?\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)', ln):
                if cur['pl'] is None or not cur['rects']:
                    cur['rects'].append((m.group(1),) + tuple(int(m.group(i)) for i in range(2, 6)))
            m = re.search(r'\+\s*(?:FIXED|PLACED|COVER)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*(\w+)', ln)
            if m and cur['pl'] is None: cur['pl'] = (int(m.group(1)), int(m.group(2)), m.group(3))
        flush()
    return pins, da, shapes
for key, sp in json.loads(sys.stdin.read()):
    rdef = _routed_def(key, sp)
    if rdef:
        try:
            pins, da, shapes = _read_def(rdef)
            if pins:
                out[key] = dict(doc=pins, die_area=da, read=rdef, source='routed_def', shapes=shapes); continue
        except Exception: pass
    # face_guard pins file; when it is gone, the kit's own pins.json beside <kit>/signoff/signoff.json
    p, d = None, None
    for c in (key, os.path.join(os.path.dirname(os.path.dirname(sp)), 'pins.json')):
        try:
            if os.path.getsize(c) > 32 << 20: continue
            d = json.load(open(c)); p = c; break
        except Exception: continue
    if p is None:
        # FLOW-12 10-30: the kit's pins file is gone (retired host / pruned run) -> the signed abstract beside the
        # record: <record dir>/*.lef, pin = first RECT centre of its first PORT, outline = SIZE
        rd = os.path.dirname(sp)
        lefs = []
        for sub in ('', 'views/' + os.path.basename(rd)):   # <record dir>/*.lef, else <record dir>/views/<record dir name>/*.lef
            try: lefs = sorted(os.path.join(sub, f) for f in os.listdir(os.path.join(rd, sub)) if f.endswith('.lef'))
            except Exception: lefs = []
            if lefs: break
        if len(lefs) != 1: continue
        p = os.path.join(rd, lefs[0])
        try: txt = open(p, errors='replace').read()
        except Exception: continue
        pins, da, shapes = [], None, {}
        m = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', txt)
        if m: da = [0.0, 0.0, float(m.group(1)), float(m.group(2))]
        for pm in re.finditer(r'\n[ \t]*PIN[ \t]+(\S+)', txt):
            em = re.compile(r'\n[ \t]*END[ \t]+' + re.escape(pm.group(1)) + r'[ \t]*\n').search(txt, pm.end())
            if not em: continue
            body = txt[pm.end():em.start()]
            if re.search(r'\bUSE\s+(POWER|GROUND)\b', body): continue
            lm = re.search(r'\bLAYER\s+(\S+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', body)
            if not lm: continue
            x0, y0, x1, y1 = (float(lm.group(i)) for i in range(2, 6))
            pins.append(dict(name=pm.group(1), layer=lm.group(1), x=round((x0 + x1) / 2, 4), y=round((y0 + y1) / 2, 4)))
            # FLOW-13: every RECT of the pin (pin_compare convention class)
            cl, rs = None, []
            for t in re.finditer(r'\bLAYER\s+(\S+)\s*;|\bRECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', body):
                if t.group(1): cl = t.group(1)
                else: rs.append([cl] + [int(round(float(t.group(i)) * 1000)) for i in range(2, 6)])
            shapes[pm.group(1)] = rs
        out[key] = dict(doc=pins, die_area=da, read=p, source='signed_lef', shapes=shapes)
        continue
    da = None
    try:
        for ln in open(os.path.join(os.path.dirname(p), 'config.mk'), errors='replace'):
            m = re.match(r'\s*(?:export\s+)?DIE_AREA\s*[:?]?=\s*(.*)$', ln)
            if m: da = [float(x) for x in m.group(1).split()]
    except Exception: pass
    out[key] = dict(doc=d, die_area=da, read=p, source='kit_pins_json')
print(json.dumps(out))
"""


def fetch_rec_pins(recs, log=lambda *a: None):
    """{(scan_host, pins_path): {rows, outline_nm | None, read}} for the records' face_guard pins files (kit pins.json +
    kit config.mk DIE_AREA; <kit>/pins.json beside <kit>/signoff/ when the face_guard file is gone).  origin/main records name fleet paths of unknown host: not fetched (unmatched)."""
    # FLOW-12 10-30 (credit on pins for every module): an origin/main record uses its view's pins.json on main when it
    # has one; any other record's pins path is asked of its own host first, then of every fleet host (origin/main records
    # name fleet kit paths of unknown host; a kit pins file may sit on another host than the record that names it)
    by = {}; want = []
    out = {}
    for r_ in recs:
        if r_.get('scan_host') == 'origin/main' and r_.get('path') in MAIN_PINS:
            out[('origin/main', r_.get('pins_path'))] = MAIN_PINS[r_['path']]; continue
        if r_.get('pins_path'):
            want.append((r_.get('scan_host'), r_['pins_path']))
            for h in HOSTS:
                by.setdefault(h, set()).add((r_['pins_path'], r_['path'] if h == r_.get('scan_host') else r_['pins_path']))
    found = {}
    for h, ps in by.items():
        cmd = ['python3', '-c', REC_PINS_PY] if h == 'local' else \
            ['ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', '-o', 'ControlPath=none', h, 'python3 -c %s' % shlex_quote(REC_PINS_PY)]
        try:
            r = sh(cmd, 300, input=json.dumps(sorted(ps)))
            if not r.stdout.strip(): raise RuntimeError('rc %d %s' % (r.returncode, r.stderr.strip()[-200:]))
            got = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception as e:
            log('design pins fetch %s: %s' % (h, e)); continue
        for p, x in got.items():
            da = x.get('die_area')
            ol = (_nm(da[2] - da[0]), _nm(da[3] - da[1])) if da and len(da) == 4 else None
            found[(h, p)] = dict(rows=canon_pin_rows(x.get('doc')), outline_nm=ol, read='%s:%s' % (h, x.get('read')),
                                 source=x.get('source'))
            if x.get('shapes'): found[(h, p)]['shapes'] = {k: [tuple(r) for r in v] for k, v in x['shapes'].items()}
    for sh_, p in want:
        for h in ([sh_] if sh_ in HOSTS else []) + [h for h in HOSTS if h != sh_]:
            if (h, p) in found:
                out[(sh_, p)] = found[(h, p)]; break
    return out


def _plan_shapes_default(designs, did):
    g = designs.get(did) or {}
    return repo_lef_shapes(g['pins_lef'], g.get('module')) if g.get('pins_lef') else None


def design_pin_cmp(got, did, designs, rows, plan_shapes=None):
    """pin_compare of a record (got) against plan design did, with the plan table's source-LEF shapes and the record's
    own shapes (signed LEF) when known"""
    ps = (plan_shapes or (lambda d: _plan_shapes_default(designs, d)))(did)
    return accept_die_owned_ft(pin_compare(got['rows'], rows.get(did), got.get('shapes'), ps), designs.get(did))


def _cmp_text(c, a=None, b=None):
    parts = []
    for k in ('moved', 'extra', 'missing', 'convention'):
        if c[k]:
            e = c[k][0]
            ex = ' e.g. %s %s vs plan %s' % (e, a.get(e) if a else '', b.get(e) if b else '') if k in ('moved', 'convention') else ' e.g. %s' % e
            parts.append('%s %d%s' % ({'moved': 'moved pin', 'extra': 'extra pin (record only)', 'missing': 'missing pin (plan only)',
                                         'convention': 'same pin, other convention'}[k], len(c[k]), ex))
    return '; '.join(parts) or 'match'


def miss_why(got, ds, designs, rows, plan_shapes=None):
    """why a record credits no plan design: record pins not readable / plan design has no pin table / outline differs /
    per-pin classes (moved / extra / missing; convention-only differences are not a miss) -- against each plan design"""
    if not got: return 'pins not readable'
    if not ds: return 'module has no plan design'
    out = []
    for did in ds:
        b = rows.get(did)
        if not b: out.append('plan design %s has no pin table on main' % did); continue
        ol = tuple(_nm(x) for x in designs[did]['outline_um'])
        if got['outline_nm'] is not None and tuple(got['outline_nm']) != ol:
            out.append('outline %s nm vs plan %s nm' % (tuple(got['outline_nm']), ol)); continue
        c = design_pin_cmp(got, did, designs, rows, plan_shapes)
        n = len(c['match']) + len(c['convention']) + len(c['moved'])
        out.append('%d/%d pins: %s' % (len(c['moved']) + len(c['extra']) + len(c['missing']), n + len(c['extra']), _cmp_text(c, got['rows'], b)))
    return 'pins match no plan design: ' + '; '.join(out[:2])


def credit_designs(designs, rows, core_recs, rec_pins, plan_shapes=None):
    """-> (signed {design id: [refs]}, unmatched {module: [refs]}).  core_recs {module: [(ref, record)]} are the
    counted (versioned / legacy, not retired) records of each module.  A record credits the plan-of-record design(s)
    its own pins file matches (pin_compare: every pin match or same-pin-other-convention, no moved / extra / missing
    pin; + outline), and so all their copies; otherwise none (no false credit).
    FLOW-12 10-30 (COORD / SIGNOFF-SPRINT-8 ASK): this holds for a module with ONE plan design too -- that case used to
    credit any versioned record unchecked (KV rx counted before its pin fix merged).
    plan_shapes: did -> {pin: shapes} (default: the plan pin table's source LEF on origin/main)."""
    per_mod = {}
    for did, g in designs.items():
        per_mod.setdefault(g['module'], []).append(did)
    signed, unmatched = {}, {}
    for m, recs in core_recs.items():
        ds = per_mod.get(m) or []
        for ref, r_ in recs:
            got = rec_pins.get((r_.get('scan_host'), r_.get('pins_path')))
            hit = []
            for did in ds:
                if not (got and rows.get(did)) or not (got['outline_nm'] is None or tuple(got['outline_nm']) == tuple(_nm(x) for x in designs[did]['outline_um'])):
                    continue
                c = accept_die_owned_ft(pin_compare(got['rows'], rows[did]), designs[did])   # fast path: centres within tolerance
                if not pins_equiv(c) and not (c['extra'] or c['missing']):
                    c = design_pin_cmp(got, did, designs, rows, plan_shapes)
                if pins_equiv(c):
                    hit.append((did, c))
            for did, c in hit:
                signed.setdefault(did, []).append(ref + ' DESIGN-MATCH pins' + (
                    ' (same pin, other convention %d: %s)' % (len(c['convention']), ' '.join(c['convention'][:4])) if c['convention'] else '') + (
                    ' (+%d declared die-owned FT)' % len(c['die_owned_ft']) if c.get('die_owned_ft') else '') + (
                    ' (+%d plan-excluded %s)' % (len(c['plan_excluded']), ' '.join(c['plan_excluded'][:4])) if c.get('plan_excluded') else '') + (
                    ' [pins from %s]' % got.get('source') if got.get('source') else ''))
            if not hit:
                unmatched.setdefault(m, []).append(ref + ' (%s)' % miss_why(got, ds, designs, rows, plan_shapes))
    return signed, unmatched


def replica_sample(designs, signed, every=10):
    """owner 10-25 template-replica rule: copies of a signed design pass on the automated GEOM checks with 1 in
    'every' sampled for visual review.  -> [(design id, copy index)] deterministic sample (copy 1 is the template)."""
    out = []
    for did in sorted(signed):
        n = (designs.get(did) or {}).get('instances') or 0
        out += [(did, i) for i in range(2, n + 1) if (i - 2) % every == 0]
    return out


def refresh(log=lambda *a: None):
    errs = []
    res = dict(generated=time.time(), errors=errs, dies={}, plans={}, provenance_rule='v1')
    sha = None
    r = sh(['git', '-C', str(REPO), 'fetch', '-q', 'origin', 'main'], 180)
    if r.returncode: errs.append('git fetch origin main failed: %s' % r.stderr.strip()[-200:])
    sha = sh(['git', '-C', str(REPO), 'rev-parse', '--short=10', 'origin/main'], 30).stdout.strip()
    res['origin_main'] = sha
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='release-tree-plan.'))
    try:
        paths = plan_archive_paths()
        p1 = subprocess.Popen(['git', '-C', str(REPO), 'archive', 'origin/main'] + paths, stdout=subprocess.PIPE)
        r = subprocess.run(['tar', '-x', '-C', str(tmp)], stdin=p1.stdout, capture_output=True, timeout=600)
        p1.wait(60)
        if r.returncode or p1.returncode: raise RuntimeError('git archive origin/main failed')
        design_rows = {}
        # SIGNED records: fleet scan in parallel while the G0C checks run here
        with cf.ThreadPoolExecutor(len(HOSTS)) as ex:
            futs = {ex.submit(scan_host, h): h for h in HOSTS}
            for key, pdir, src, ovl in PLANS:
                d = plan_label(src)
                ent = dict(plan=d, plan_src=src)
                try:
                    pj = materialize_plan(tmp, pdir, src, ovl)
                    ent['refs_fetched'] = len(fetch_results_refs(tmp, pj))
                    ent['pin_aliases'] = materialize_pin_aliases(pj.parent, PIN_ALIASES.get(key))
                    P = json.loads(pj.read_text())
                    T = P.get('partition_types') or {}
                    ent['types'] = len(T); ent['partitions'] = len(P.get('partitions') or [])
                    ent['type_modules'] = {k: (v.get('module') or k) for k, v in T.items()}
                    ent['hard_cores'] = sorted({h.get('module') for v in T.values() for h in (v.get('hard_cores') or []) if h.get('module') and not is_mem_macro(h)})
                    ent['memory_macros'] = sorted({h.get('module') for v in T.values() for h in (v.get('hard_cores') or []) if h.get('module') and is_mem_macro(h)})
                    ent['designs'], design_rows[d] = plan_designs(P, pj.parent)
                    out = tmp / ('g0c_' + d.replace('/', '_'))
                    t0 = time.time()
                    rr = sh([sys.executable, str(tmp / 'tools/die_plan/check.py'), str(pj), '--completeness', '--quiet', '--out', str(out)],
                            900, cwd=str(tmp))
                    rep = json.loads((out / 'g0_report.json').read_text())
                    gs = g0c_split(rep, list(T))
                    ent.update(g0c_verdict=rep.get('verdict'), g0c_errors=rep.get('errors'), g0c_clean=gs['clean'],
                               g0c_types=gs['types'], g0c_die_level=gs['die_level'], g0c_bad_types=gs['by_type'],
                               geom_report=gs['geom_report'], check_s=round(time.time() - t0, 1))
                    log('G0C %s: %s/%s clean (%s, %s errors, %.0fs)' % (d, ent['g0c_clean'], ent['g0c_types'], ent['g0c_verdict'], ent['g0c_errors'], ent['check_s']))
                except Exception as e:
                    errs.append('plan %s: %s' % (d, e)); ent['error'] = str(e)
                res['plans'][d] = dict(ent, die=key)
            recs = main_records(tmp)
            scanned = ['origin/main']
            for f, h in futs.items():
                try:
                    recs += f.result(timeout=600); scanned.append(h)
                except Exception as e:
                    errs.append('SIGNED scan %s: %s' % (h, e))
        cutoff = first_flow_tag_ts(); res['first_flow_tag_ts'] = cutoff
        for r_ in recs:
            check_resign_tag(r_)
        for r_ in recs:
            r_['legacy'] = is_legacy(r_, cutoff)
        recs, res['retired_records'] = split_retired(recs, retired_refs())
        names = retired_names()
        res['signed_records'] = recs; res['scanned'] = scanned
        # match SIGNED records to plan types / hard cores
        for d, ent in res['plans'].items():
            if 'types' not in ent: continue
            tm = ent.pop('type_modules')
            st, sc, ut, uc = {}, {}, {}, {}
            core_recs = {}
            for r_ in recs:
                ks = rec_keys(r_)
                ref = r_['scan_host'] + ':' + r_['path'] if r_['scan_host'] != 'origin/main' else r_['path']
                if r_.get('versioned'):
                    ref += ' src %s flow %s' % (str(r_['src_commit'])[:12], r_['flow_tag'])
                    if r_.get('resign'):
                        ref += ' RE-SIGN build %s db %s' % (str(r_['build_commit'])[:12], r_['routed_db'])
                elif r_.get('resign_error'):
                    ref += ' RE-SIGN-INVALID ' + r_['resign_error']
                elif r_.get('legacy'):
                    ref += ' SIGNED-LEGACY'
                T, C = (st, sc) if (r_.get('versioned') or r_.get('legacy')) else (ut, uc)
                for k, m in tm.items():
                    if k in ks or m in ks:
                        why = name_retired(r_, ent['die'], names, (k, m))
                        if why: res['retired_records'].append(dict(r_, retired=why, retired_type=k))
                        else: T.setdefault(k, []).append(ref)
                for m in ent['hard_cores']:
                    if m in ks:
                        why = name_retired(r_, ent['die'], names, (m,))
                        if why: res['retired_records'].append(dict(r_, retired=why, retired_core=m))
                        else:
                            C.setdefault(m, []).append(ref)
                            if C is sc: core_recs.setdefault(m, []).append((ref, r_))
            ent['signed_types'] = st; ent['signed_cores'] = sc
            if ent.get('designs') is not None:
                rp = fetch_rec_pins([r_ for m in core_recs for _, r_ in core_recs[m]], log) if core_recs else {}
                ent['signed_designs'], ent['design_unmatched'] = credit_designs(ent['designs'], design_rows.get(d) or {}, core_recs, rp)
                ent['replica_sample'] = replica_sample(ent['designs'], ent['signed_designs'])
            ent['unversioned_types'] = {k: v for k, v in ut.items() if k not in st}
            ent['unversioned_cores'] = {k: v for k, v in uc.items() if k not in sc}
    except Exception as e:
        errs.append('refresh: %s' % e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def merge_with_cache(new, old):
    """keep the last good per-plan values when this refresh failed for a plan or for the SIGNED scan"""
    if not old: return new
    cur = {plan_label(src) for _, _, src, _ in PLANS}
    for d, ent in (old.get('plans') or {}).items():
        if d not in cur: continue   # plan no longer of record (e.g. hbm_arch/B2n -> d41v): drop, never carry it forward
        n = new['plans'].get(d)
        if (not n or 'g0c_clean' not in n) and 'g0c_clean' in ent:
            ent = dict(ent, stale_since=ent.get('stale_since') or old.get('generated'))
            if old.get('provenance_rule') not in (new.get('provenance_rule'), None):   # GRANDFATHER: pre-rule-3 (None) lists are SIGNED-LEGACY
                for a in ('types', 'cores'):
                    ent['unversioned_' + a] = dict(ent.get('unversioned_' + a) or {}, **(ent.get('signed_' + a) or {}))
                    ent['signed_' + a] = {}
            new['plans'][d] = ent
    return new


def load(force=False, log=lambda *a: None, refresh_stale=True):
    """returns (cache dict or None, error string or None); refreshes when the cache is older than REFRESH_S."""
    old = None
    try: old = json.loads(CACHE.read_text())
    except Exception: pass
    if not force and old and time.time() - old.get('generated', 0) < REFRESH_S:
        return old, None
    if not force and not refresh_stale:
        return old, ('plan layer cache stale; scheduled refresh pending' if old else 'plan layer not cached; run with --refresh-plan')
    try:
        new = merge_with_cache(refresh(log), old)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE.with_suffix('.tmp'); tmp.write_text(json.dumps(new, indent=1)); os.replace(tmp, CACHE)
        return new, ('; '.join(new['errors']) or None)
    except Exception as e:
        return old, 'plan layer refresh failed (%s); %s' % (e, 'using the cached copy' if old else 'no cache')


def design_counts(ent):
    """COUNT PER DESIGN (OWNER 12.22 (3)): cores / signed_cores count DESIGNS (module + outline + pin table) and the
    signed list names designs; instances / signed_instances count every placed copy.  A cache entry from before the
    design layer (no 'designs') keeps the module counts."""
    D = ent.get('designs')
    if D is None: return {}
    sd = ent.get('signed_designs') or {}
    return dict(cores=len(D), signed_cores=len(sd), instances=sum(g['instances'] for g in D.values()),
                signed_instances=sum(D[k]['instances'] for k in sd if k in D),
                signed_list=sorted(ent.get('signed_types') or {}) + sorted(sd),
                design_unmatched=sorted(ent.get('design_unmatched') or {}))


def g0c_split(rep, type_names):
    """FLOW-13 10-31 (COORD 00:2x, AUTOBUILD-GATE-1 826b0c4003f): check.py's summary.g0c counts every g0c-flagged
    finding, including plan_geom REPORT-mode items (level WARN, check geom_*, msg '[G0C-GEOM] ...'), so the G0C-clean
    type count fell (S81 203->85, QC 23->3, KV 29->2, HBM 71->7) with no gate change.  G0C clean = types with no GATE
    finding (every g0c finding except a WARN geom_* one; plan_geom 'enforce' items are ERROR and still count);
    REPORT-mode geom findings are counted separately: geom_report {types (with >=1 finding), by_check {check: n},
    by_type}.  Same per-type/die-level keys as check.g0c_summary."""
    names = set(type_names)
    gate, die, geo, gcnt = {}, {}, {}, {}
    for i in rep.get('findings') or []:
        if not i.get('g0c'): continue
        key = i['check'] + (':%s' % i['field'] if i.get('field') else '')
        tn = i.get('type')
        if str(i.get('check', '')).startswith('geom_') and i.get('level') == 'WARN':
            if tn in names: geo.setdefault(tn, {}); geo[tn][key] = geo[tn].get(key, 0) + 1
            gcnt[i['check']] = gcnt.get(i['check'], 0) + 1
            continue
        tgt = gate.setdefault(tn, {}) if tn in names else die
        tgt[key] = tgt.get(key, 0) + 1
    return dict(types=len(names), clean=len(names) - len(gate), die_level=die, by_type=gate,
                geom_report=dict(types=len(geo), by_check=gcnt, by_type=geo))


def die_counts(cache, key):
    """per release-tree die key: list of per-plan rows"""
    rows = []
    for d, ent in sorted(((cache or {}).get('plans') or {}).items()):
        if ent.get('die') != key: continue
        rows.append(dict(plan=d, types=ent.get('types'), clean=ent.get('g0c_clean'), verdict=ent.get('g0c_verdict'),
                         errors=ent.get('g0c_errors'), bad=ent.get('g0c_bad_types') or {}, die_level=ent.get('g0c_die_level') or {},
                         signed_types=len(ent.get('signed_types') or {}), cores=len(ent.get('hard_cores') or []),
                         signed_cores=len(ent.get('signed_cores') or {}), signed_list=sorted(ent.get('signed_types') or {}) + sorted(ent.get('signed_cores') or {}),
                         modules=len(ent.get('hard_cores') or []), signed_modules=len(ent.get('signed_cores') or {}),
                         stale=ent.get('stale_since'), error=ent.get('error'),
                         geom_report_types=(ent.get('geom_report') or {}).get('types')))
        rows[-1].update(design_counts(ent))
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--force', action='store_true'); ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    c, err = load(a.force, log=lambda *x: print(*x, file=sys.stderr))
    if err: print('WARN', err, file=sys.stderr)
    if a.print:
        for key in ('s81', 's81_head', 'qwen_compute', 'qwen_kvsys', 'hbm'):
            for r in die_counts(c, key):
                print('%-13s %-14s G0C %s/%s clean (%s) [geom report: %s types] ; SIGNED types %d/%s ; SIGNED hard-core designs %d/%d (modules %d/%d, copies %s/%s)%s %s' % (
                    key, r['plan'], r['clean'], r['types'], r['verdict'], r.get('geom_report_types'), r['signed_types'], r['types'], r['signed_cores'], r['cores'],
                    r['signed_modules'], r['modules'], r.get('signed_instances', '?'), r.get('instances', '?'),
                    ' UNMATCHED %s' % r['design_unmatched'] if r.get('design_unmatched') else '', r['signed_list'][:8]))
