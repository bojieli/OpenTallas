#!/usr/bin/env python3
"""RE-SIGN a routed core at a released flow tag and write its kind:resign PROVENANCE.json.

COORD ruling 2026-10-30 02:03 (3b) / OWNER 12.20 RE-SIGN rule: a signed block counts once sign-off (signoff.py) and the
post-route LEC (lec.py) are re-run on its SAME routed DB with the tools of a released per-die flow tag.  The release
counter (coord tools/release_tree_plan.py) counts such a record only through a PROVENANCE.json next to the re-sign
signoff/ dir: {kind: resign, src_commit: <tag commit>, flow_tag, routed_db, build_commit, lec}.  Until now every lane
wrote that file by hand (or forgot it: KV PHY103 10-30 13:0x).  This tool makes it part of the re-sign step.

  resign.py run        --kit K --tag TAG --tools T --out D [--run-dir R] [--lec-netlist V] ...   (sign-off + LEC + record)
  resign.py provenance --kit K --tag TAG --dir D [--tools T] ...                                   (record only)
  resign.py run --auto ...   the unattended form the autopilot uses (tools/autopilot/auto_resign.py): LOCAL_PASS_NEEDS_PARENT
                             counts as the counter counts it, the routed LEC runs with OT_LEC_SUPERSET_VEC=1 and must be
                             all_shown, every signoff_chain gate must be PASS, and .keep goes in the kit and re-sign dirs.
                             --repo may name a tag manifest JSON (written by the hub) on hosts with no repo.

The record is written only when every check passes (fail closed, nothing written otherwise):
  * TAG is a flow release tag name (flow-YYYYMMDD-x[-die]) that resolves in the repo; src_commit = its commit;
  * D/signoff/signoff.json verdict SIGNED and D/lec/lec.json verdict EQUIVALENT;
  * the routed DB the re-sign read (signoff.json inputs.odb) exists, and equals the kit's routed DB when given;
  * with --tools: signoff.py and lec.py in T are byte-identical to TAG:tools/die_plan/{signoff,lec}.py;
  * build_commit is known (--build-commit, or the kit's own provenance/freeze record).
No check or threshold is added to sign-off itself; this only records what ran.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time

TAG_RE = re.compile(r'^flow-\d{8}-[a-z]+(?:-(qc|s81|head|kv|hbm))?$')  # = release_tree_plan.check_resign_tag
SHA_RE = re.compile(r'^[0-9a-f]{40}$')
TOOLS = ('signoff.py', 'lec.py')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST_SCHEMA = 'opentallas.resign_tag_manifest.v1'
# = signoff_chain.REQUIRED_GATES: the gates a SIGNED record must carry PASS; a missing gate is NOT RUN, never PASS
REQUIRED_GATES = ('setup_tt', 'hold_ff', 'drv', 'clock', 'drc', 'antenna', 'pg')
RULE = 'COORD ruling (3b) 2026-10-30 02:03 / OWNER 12.20: RE-SIGN on the same routed DB with flow-tag tools, no new checks'


class ResignError(Exception):
    pass


def git(repo, *args):
    p = subprocess.run(['git', '-C', repo] + list(args), capture_output=True)
    if p.returncode:
        raise ResignError('git %s: %s' % (' '.join(args), p.stderr.decode(errors='replace').strip()))
    return p.stdout


def manifest(repo):
    """the tag manifest when repo names one, else None (repo is a git checkout).  The hub writes it from git, so a
    fleet host checks the same bytes without holding the repo."""
    if not str(repo).endswith('.json'):
        return None
    try:
        m = load(repo)
    except Exception as e:
        raise ResignError('unreadable tag manifest %s (%s)' % (repo, e))
    if m.get('schema') != MANIFEST_SCHEMA or not SHA_RE.match(str(m.get('commit'))):
        raise ResignError('%s is not a tag manifest' % repo)
    return m


def tag_commit(repo, tag):
    if not TAG_RE.match(tag or ''):
        raise ResignError('%r is not a flow release tag name (flow-YYYYMMDD-x[-die])' % tag)
    m = manifest(repo)
    if m is not None:
        if m.get('tag') != tag:
            raise ResignError('manifest %s is for %s, not %s' % (repo, m.get('tag'), tag))
        return m['commit']
    return git(repo, 'rev-parse', '--verify', tag + '^{commit}').decode().strip()


def tag_file_sha(repo, tag, rel):
    """sha256 of TAG:rel, None when the tag has no such file"""
    m = manifest(repo)
    if m is not None:
        return (m.get('files') or {}).get(rel)
    try:
        return hashlib.sha256(git(repo, 'show', '%s:%s' % (tag, rel))).hexdigest()
    except ResignError:
        return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def check_tools(repo, tag, tools):
    out = {}
    for n in TOOLS:
        p = os.path.join(tools, n)
        if not os.path.isfile(p):
            raise ResignError('tag tools dir %s has no %s' % (tools, n))
        want = tag_file_sha(repo, tag, 'tools/die_plan/%s' % n)
        if want is None:
            raise ResignError('%s has no tools/die_plan/%s' % (tag, n))
        got = sha256(p)
        if got != want:
            raise ResignError('%s sha256 %s != %s:tools/die_plan/%s %s' % (p, got[:12], tag, n, want[:12]))
        out[n] = got
    return out


CLOCK_FAMILY = 'clock_family.tcl'
CLOCK_FAMILY_TAG = ('tools/die_plan/clock_family.tcl', 'physical/common_flow/clock_family.tcl')


def export_clock_family(repo, tag, tools):
    """DIE-HEAD-44 10-30 (FLOW-11): the tag's signoff.py bundles clock_family.tcl (SIGNOFF_BUNDLE), read from its own
    dir or else <dir>/../../physical/common_flow/.  'git archive TAG tools' has no physical/common_flow, so a tag
    sign-off failed before STA ('incomplete tool bundle').  The file is taken from the TAG (tools/die_plan first, then
    physical/common_flow, as signoff.py looks): written into the tools dir when signoff.py would not find it, byte-
    checked when it would.  A tag without the file, or a different copy in place, fails here before any run."""
    rel, want = None, None
    for rel in CLOCK_FAMILY_TAG:
        want = tag_file_sha(repo, tag, rel)
        if want:
            break
    if not want:
        raise ResignError('%s has no %s (signoff.py needs it in its tool bundle)' % (tag, ' or '.join(CLOCK_FAMILY_TAG)))
    tools = os.path.abspath(tools)
    for p in (os.path.join(tools, CLOCK_FAMILY),
              os.path.join(os.path.dirname(os.path.dirname(tools)), 'physical', 'common_flow', CLOCK_FAMILY)):
        if os.path.isfile(p):
            if sha256(p) != want:
                raise ResignError('%s differs from %s clock_family.tcl (signoff.py would read it)' % (p, tag))
            return p
    if manifest(repo) is not None:
        raise ResignError('%s not staged in %s (a manifest holds shas, not bytes)' % (CLOCK_FAMILY, tools))
    p = os.path.join(tools, CLOCK_FAMILY)
    with open(p, 'wb') as f:
        f.write(git(repo, 'show', '%s:%s' % (tag, rel)))
    return p


def load(path):
    with open(path) as f:
        return json.load(f)


ABBREV_RE = re.compile(r'^[0-9a-f]{7,39}$')


def full_commit(repo, v):
    """an abbreviated commit (freeze.json repo_rev is written short, e.g. faecd095101) -> the full 40-hex commit in repo;
    None when repo is not a git checkout (a tag manifest) or does not hold exactly that commit."""
    if not repo or not ABBREV_RE.match(v) or not os.path.isdir(repo):
        return None
    try:
        out = git(repo, 'rev-parse', '--verify', '--quiet', '%s^{commit}' % v).decode().strip()
    except ResignError:
        return None
    return out if SHA_RE.match(out) and out.startswith(v) else None


def commit_repos(repo):
    """git checkouts that can expand a short commit for repo: repo itself, or for a tag manifest (no repo on the host)
    the checkout the manifest names ('repo' / 'source_repo') and this tool's own checkout (KW-FIX-32 11-07, DIE-S81-78
    18:31: an --auto re-sign on a manifest finished sign-off + LEC, then stopped at 'build_commit unknown' because the
    kit's freeze.json repo_rev was short).  Read-only; a dir that is not a checkout simply resolves nothing."""
    if not repo:
        return []
    m = manifest(repo)
    if m is None:
        return [repo]
    out = []
    for r in (m.get('repo'), m.get('source_repo'), REPO):
        if isinstance(r, str) and os.path.isdir(r) and r not in out:
            out.append(r)
    return out


def expand_commit(repo, v):
    """short commit -> full 40-hex through commit_repos(repo); a manifest's own commit counts when v is its prefix.
    None when no checkout holds it, or when two disagree (ambiguous: fail closed)."""
    if not isinstance(v, str) or not ABBREV_RE.match(v):
        return None
    m = manifest(repo) if repo else None
    hits = {m['commit']} if m is not None and m['commit'].startswith(v) else set()
    for r in commit_repos(repo):
        f = full_commit(r, v)
        if f:
            hits.add(f)
    return hits.pop() if len(hits) == 1 else None


def kit_build_commit(kit, repo=None):
    """the original build commit from the kit's own records (lec kit_provenance, autopilot, freeze).  freeze.json carries it
    as repo_rev (gen_phys, often abbreviated): read too, resolved to the full commit through repo, or for a tag manifest
    through commit_repos (S81-COLLE-4 11-06: a
    resign.py run --auto finished sign-off + LEC but wrote no record because only repo_rev named the commit)."""
    for n in ('PROVENANCE.json', 'AUTOPILOT.json', 'freeze.json', 'kit_provenance.json'):
        p = os.path.join(kit, n)
        try:
            x = load(p)
        except Exception:
            continue
        if not isinstance(x, dict) or x.get('kind') == 'resign':
            continue
        for v in (x.get('build_commit'), x.get('src_commit'), (x.get('provenance') or {}).get('commit')
                  if isinstance(x.get('provenance'), dict) else None, x.get('source_commit'), x.get('repo_rev')):
            if isinstance(v, str) and SHA_RE.match(v):
                return v
            f = expand_commit(repo, v)
            if f:
                return f
    return None


def needs_parent_only(so):
    """= release_tree_plan.counts_signed (COORD 11-03 18:48 + OWNER 18:49, standing, every die): local sign-off SIGNED and
    io_hold_parent the only open reason.  The receipt moves to the die STA FF row."""
    return (so.get('verdict') == 'LOCAL_PASS_NEEDS_PARENT' and so.get('local_verdict') == 'SIGNED' and
            all(str(r).startswith('io_hold_parent') for r in (so.get('reasons') or [])))


def signoff_gates(so):
    """= signoff_chain.signoff_gates: required gate -> verdict; a missing gate or corner is NOT RUN"""
    checks = so.get('checks') or {}
    out = {}
    for k in REQUIRED_GATES:
        v = checks.get(k)
        out[k] = (v.get('verdict') or 'NOT RUN') if isinstance(v, dict) else str(v) if v else 'NOT RUN'
    corners = so.get('corners') or {}
    for c in ('tt', 'ff'):
        if corners and not (corners.get(c) or {}).get('done'):
            out['corner_' + c] = 'NOT RUN'
    return out


def find_lec(d):
    p = os.path.join(d, 'lec', 'lec.json')  # lec.py's verdict file; other lec/*.json are its work files
    return p if os.path.isfile(p) else None


def build_record(d, kit, tag, repo=REPO, tools=None, build_commit=None, routed_db=None, lec=None, src_commit=None,
                 lane=None, note=None, pincmp=None, hash_db=True, auto=False):
    """validate one re-sign dir and return its PROVENANCE dict; raises ResignError on any failed check.
    auto: the unattended form, see the module doc: adds the chain's gate and all_shown checks, never removes one."""
    d, kit = os.path.abspath(d), os.path.abspath(kit)
    full = tag_commit(repo, tag)
    if src_commit and not full.startswith(src_commit):
        raise ResignError('--src-commit %s is not %s = %s' % (src_commit, tag, full[:12]))
    so_p = os.path.join(d, 'signoff', 'signoff.json')
    try:
        so = load(so_p)
    except Exception as e:
        raise ResignError('no readable re-sign %s (%s)' % (so_p, e))
    np = auto and needs_parent_only(so)
    if so.get('verdict') != 'SIGNED' and not np:
        raise ResignError('re-sign %s verdict %s, not SIGNED' % (so_p, so.get('verdict')))
    if auto:
        bad = sorted(k for k, v in signoff_gates(so).items() if v != 'PASS')
        if bad:
            raise ResignError('re-sign %s gates not PASS: %s' % (so_p, ','.join(bad)))
    lec = os.path.abspath(lec) if lec else find_lec(d)
    if not lec:
        raise ResignError('no post-route lec.json under %s/lec' % d)
    try:
        lec_rec = load(lec)
        lv = lec_rec.get('verdict')
    except Exception as e:
        raise ResignError('unreadable %s (%s)' % (lec, e))
    if lv != 'EQUIVALENT':
        raise ResignError('post-route LEC %s verdict %s, not EQUIVALENT' % (lec, lv))
    if auto and (lec_rec.get('superset_vec') or {}).get('all_shown') is not True:
        raise ResignError('post-route LEC %s superset check: all_shown must be true (OT_LEC_SUPERSET_VEC=1)' % lec)
    read_db = (so.get('inputs') or {}).get('odb')
    if not read_db:
        raise ResignError('%s names no inputs.odb (cannot prove the same routed DB)' % so_p)
    if routed_db and os.path.realpath(routed_db) != os.path.realpath(read_db):
        raise ResignError('re-sign read %s, not the routed DB %s' % (read_db, routed_db))
    if not os.path.isfile(read_db):
        raise ResignError('routed DB %s missing' % read_db)
    tool_sha = check_tools(repo, tag, tools) if tools else None
    bc = build_commit or kit_build_commit(kit, repo)
    if not bc:
        raise ResignError('build_commit unknown: pass --build-commit (no commit in %s records)' % kit)
    rec = dict(schema='opentallas.resign_qualification.v1', kind='resign', verdict='SIGNED',
               src_commit=full, flow_tag=tag, routed_db=read_db, build_commit=bc, lec=lec, lec_verdict=lv,
               resign_signoff=so_p, kit=kit, original_signoff=os.path.join(kit, 'signoff', 'signoff.json'),
               name=so.get('name'), rule=RULE, writer='tools/die_plan/resign.py',
               host=socket.gethostname(), created=time.strftime('%Y-%m-%d %H:%M %Z'))
    if hash_db:
        rec['routed_db_sha256'] = sha256(read_db)
    if np:
        rec['verdict_basis'] = ('LOCAL_PASS_NEEDS_PARENT (local SIGNED, only io_hold_parent open) counts SIGNED per COORD '
                                '2026-11-03 18:48 ruling / OWNER 18:49; io_hold_parent receipt moves to die STA FF')
    if tool_sha:
        rec['tag_tools'] = dict(dir=os.path.abspath(tools), sha256=tool_sha, checked='byte-identical to %s' % tag)
    for k, v in (('lane', lane), ('as_run_note', note), ('pincmp', pincmp)):
        if v:
            rec[k] = v
    return rec


def write_record(d, rec):
    p = os.path.join(d, 'PROVENANCE.json')
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(rec, f, indent=1)
        f.write('\n')
    os.replace(tmp, p)
    return p


def mark_keep(rec, *dirs):
    """one line in DIR/.keep naming the signed DB and the lane; the reaper and prune rules read it.  An existing .keep
    is added to, never replaced."""
    line = 'signed DB %s %s %s %s\n' % (rec['routed_db'], rec['flow_tag'], rec.get('lane') or 'resign.py', rec['created'])
    for d in dirs:
        with open(os.path.join(d, '.keep'), 'a') as f:
            f.write(line)


def default_container_suffix(out):
    """Keep parallel output directories distinct without permitting same-output writers."""
    canonical = os.path.realpath(os.path.abspath(out))
    stem = re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.basename(canonical)) or 'out'
    digest = hashlib.sha256(os.fsencode(canonical)).hexdigest()[:16]
    return '%s-%s' % (stem, digest)


# FLOW-CLASS-25 11-06 (COORD 18:0x (3b), DIE-HBM-82 17:38 (4b)): the LEC container got only OT_LEC_SUPERSET_VEC, so a
# kit proved EQUIVALENT with a wider parity budget (q3_edge_link g_rxpre.ne_q, a 612-input CRC compare: DIE-HBM-66 11-04,
# OT_LEC_PARITY_TERMS=800) went UNPROVEN (cone timeout 600 s) on every later re-sign at the lec.py default 256.  These
# lec.py solver knobs are now passed into the container when the caller's env sets them, else when the kit's config.mk
# exports them (a recipe sets them there, e.g. through the generator's ORFS variables).  The caller's env wins.  Only the
# proof budget changes; the verdict rules of lec.py and of this record are unchanged.
LEC_BOOL_PASS = ('OT_LEC_REPLICA_MATCH', 'OT_LEC_MEM_LANES', 'OT_LEC_ENABLE_FILL_GUARD')
LEC_ENV_PASS = ('OT_LEC_PARITY_TERMS',) + LEC_BOOL_PASS
_CFG_RE = re.compile(r'^\s*(?:override\s+)?(?:export\s+)?([A-Z0-9_]+)\s*[:?]?=\s*(.*?)\s*$')


def kit_config_vars(kit, names=LEC_ENV_PASS):
    """{VAR: value} of the named variables set in KIT/config.mk (last assignment wins; no config.mk = {})."""
    out = {}
    try:
        text = open(os.path.join(kit, 'config.mk'), errors='replace').read()
    except OSError:
        return out
    for line in text.splitlines():
        m = _CFG_RE.match(line.split('#', 1)[0])
        if m and m.group(1) in names and m.group(2):
            out[m.group(1)] = m.group(2)
    return out


def lec_env_args(kit, environ=None):
    """docker -e args for the LEC solver knobs set by the caller's env or by the kit's config.mk (env wins)."""
    environ = os.environ if environ is None else environ
    cfg = kit_config_vars(kit)
    args = []
    for k in LEC_ENV_PASS:
        v = environ.get(k) or cfg.get(k)
        if not v:
            continue
        if k in LEC_BOOL_PASS:
            if str(v).strip() not in ('0', '1'):
                raise ResignError('%s=%r must be 0 or 1' % (k, v))
        elif not re.fullmatch(r'[1-9][0-9]*', str(v).strip()):
            raise ResignError('%s=%r (%s) is not a positive integer' % (k, v, 'env' if environ.get(k) else 'kit config.mk'))
        args += ['-e', '%s=%s' % (k, str(v).strip())]
    return args


def lec_kit(kit, up=3):
    """S81-TYPES-5 11-07 RESIGN-PASSDIR class: a late-ECO pass dir (K/eco_*/iN) is a run dir, not a kit: it has no
    config.mk, so lec.py stopped with FileNotFoundError /work/config.mk (slice_station t8 dg-s81, t17 cw-s81 re-signs).
    LEC mounts the nearest kit at or above it that has config.mk (at most `up` levels; the pass dir's 6_final.v stays
    inside it); a kit with config.mk is returned unchanged."""
    k = os.path.abspath(kit)
    for _ in range(up + 1):
        if os.path.exists(os.path.join(k, 'config.mk')):
            return k
        parent = os.path.dirname(k)
        if parent == k:
            break
        k = parent
    return os.path.abspath(kit)


def kit_ff_reference(kit):
    """the kit's own per-corner FF insertion (sdc_lint.json insertion_ff_ps, in the kit or the nearest kit above an ECO
    pass dir), or None"""
    for k in dict.fromkeys((os.path.abspath(kit), lec_kit(kit))):
        p = os.path.join(k, 'sdc_lint.json')
        if os.path.isfile(p):
            try:
                v = load(p).get('insertion_ff_ps')
            except Exception:
                v = None
            if v is not None:
                return v
    return None


def ff_vclk_args(kit, source_record=None):
    """KW-FIX-46 11-12 (STA2204-1 13:32, S81-SVCRS-3 su_smc / svc_merge_h4): the FF reference of a re-sign.  A kit with its
    own sdc_lint insertion_ff_ps keeps '--ff-vclk auto' (signoff.py binds it).  A kit without one, re-signing a record
    that signed under bound-ff, replays that record's contract-pinned reference (policy ff_vclk / ff_vclk_bound_ps /
    ff_vclk_contract): 'auto' resolved to the single TT SDC vclk there and failed ff_ref_missing although nothing in the
    DB or the tools changed.  The reference is the one the record was signed under, not a waiver."""
    if kit_ff_reference(kit) is None and source_record:
        try:
            pol = load(source_record).get('policy') or {}
        except Exception:
            pol = {}
        if pol.get('ff_vclk') == 'bound-ff' and pol.get('ff_vclk_bound_ps') is not None:
            why = 'replayed from signed record %s: %s' % (source_record, pol.get('ff_vclk_contract') or 'bound-ff')
            return ['--ff-vclk', 'bound-ff', '--ff-bound-ps', '%g' % float(pol['ff_vclk_bound_ps']),
                    '--ff-vclk-contract', why[:500]]
    return ['--ff-vclk', 'auto']


def run_cmds(kit, run_dir, tools, out, image, name, lec_netlist=None, mem='32g', cpus=8, superset=False,
             source_record=None):
    """the two commands of one re-sign (same as the lane scripts resign3.sh / tag_signoff_lec.sh)."""
    kit, run_dir, tools, out = map(os.path.abspath, (kit, run_dir, tools, out))
    lkit = lec_kit(kit)
    so = [sys.executable, '-I', os.path.join(tools, 'signoff.py'), 'run', '--run-dir', run_dir, '--kit', kit,
          '--corners', 'tt,ff'] + ff_vclk_args(kit, source_record) + [
          '--out', os.path.join(out, 'signoff'), '--image', image]
    if lec_netlist:
        net = os.path.abspath(lec_netlist)
        mounts = ['-v', '%s:/net.v:ro' % net]
        net_in = '/net.v'
    else:
        vs = sorted(glob.glob(os.path.join(run_dir, 'results', 'asap7', '*', 'base', '6_final.v')))
        if not vs:
            raise ResignError('no 6_final.v under %s/results/asap7/*/base' % run_dir)
        if not vs[0].startswith(lkit + os.sep):
            raise ResignError('6_final.v %s is outside the kit %s (LEC mounts the kit)' % (vs[0], lkit))
        mounts, net_in = [], '/work/' + os.path.relpath(vs[0], lkit)
    # Existing optional XOR backend; keep the wheel and bundled libraries together.
    solver = os.environ.get('OT_LEC_SOLVER', '')
    solver_mount = []
    if solver and os.path.isdir(solver):
        solver_mount = ['-v', os.path.abspath(solver) + ':/lecsolver:ro',
                        '-e', 'LEC_SOLVER_PATH=/lecsolver']
    lec = ['docker', 'run', '--rm', '--name', 'resign-%s-lec' % name, '--memory=%s' % mem, '--cpus=%d' % cpus] + (
           ['-e', 'OT_LEC_SUPERSET_VEC=1'] if superset else []) + lec_env_args(lkit) + [
           '-v', '%s:/work:ro' % lkit, '-v', '%s:/eco' % out, '-v', '%s:/m:ro' % tools] + mounts + solver_mount + [
           image, 'bash', '-lc', 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '
           'python3 -I /m/lec.py /work --netlist %s --out /eco/lec' % net_in]
    return so, lec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for c in ('run', 'provenance'):
        s = sub.add_parser(c)
        s.add_argument('--kit', required=True, help='kit dir that holds the routed run')
        s.add_argument('--tag', required=True, help='released flow tag, e.g. flow-20261030-a-kv')
        s.add_argument('--repo', default=REPO, help='git repo holding the tag (default: this checkout)')
        s.add_argument('--build-commit', help='original build commit (default: from the kit records)')
        s.add_argument('--routed-db', help='routed 6_final.odb the re-sign must have read (default: signoff inputs.odb)')
        s.add_argument('--lane', help='lane name for the record')
        s.add_argument('--note', help='free as-run note (e.g. netlist normalisation, pincmp)')
        s.add_argument('--pincmp', help='plan-pin match summary (pincmp vs plan of record)')
        s.add_argument('--no-db-hash', action='store_true', help='skip sha256 of the routed DB')
        if c == 'run':
            s.add_argument('--tools', required=True, help='tools/die_plan exported at TAG (clock_family.tcl is added '
                           'from TAG:physical/common_flow when missing)')
            s.add_argument('--out', required=True, help='re-sign dir (signoff/, lec/, PROVENANCE.json)')
            s.add_argument('--run-dir', help='ORFS run dir (default KIT/run)')
            s.add_argument('--lec-netlist', help='function-neutral normalised 6_final.v copy (default: the run 6_final.v)')
            s.add_argument('--image', default='openroad/orfs:asap7lock')
            s.add_argument('--name', default=None, help='docker container suffix')
            s.add_argument('--dry-run', action='store_true', help='print the commands only')
            s.add_argument('--auto', action='store_true', help='the unattended form (module doc)')
            s.add_argument('--lec-mem', default='32g', help='LEC container memory')
            s.add_argument('--source-record', help='signoff.json being re-signed: its FF reference is replayed when the kit '
                           'has no insertion_ff_ps of its own (ff_vclk_args)')
        else:
            s.add_argument('--dir', required=True, help='re-sign dir holding signoff/signoff.json + lec/lec.json')
            s.add_argument('--tools', help='tag tools dir to verify against TAG (recommended)')
            s.add_argument('--lec', help='post-route lec.json (default DIR/lec/lec.json)')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'run':
            os.makedirs(a.out, exist_ok=True)
            tag_commit(a.repo, a.tag)
            # A wave candidate supplies its SUBMIT source via auto_resign.build_commit_of.
            # Standalone copied kits may have no source metadata: refuse before RCX/LEC,
            # rather than spending both runs and discovering this at record time.
            if not a.build_commit:
                a.build_commit = kit_build_commit(a.kit, a.repo)
            if not a.build_commit:
                why = 'build_commit unknown: pass --build-commit (no commit in %s records)' % a.kit
                if not a.dry_run:
                    raise ResignError(why)
                # dry run: show that a real run would refuse, then keep printing the commands
                print('RESIGN NOT RECORDED: %s' % why, file=sys.stderr)
            check_tools(a.repo, a.tag, a.tools)  # fail before spending an RCX run on the wrong tools
            print('clock_family.tcl from %s: %s' % (a.tag, export_clock_family(a.repo, a.tag, a.tools)), file=sys.stderr)
            name = a.name or default_container_suffix(a.out)
            so, lec = run_cmds(a.kit, a.run_dir or os.path.join(a.kit, 'run'), a.tools, a.out, a.image, name,
                               a.lec_netlist, mem=a.lec_mem, superset=a.auto, source_record=a.source_record)
            if a.dry_run:
                print(' '.join(so)); print(' '.join(lec)); return 0
            env = dict(os.environ, SIGNOFF_DOCKER=os.environ.get('SIGNOFF_DOCKER', 'docker'),
                       OT_FLOW_TAG=a.tag)   # COORD 11-02 (d): signed child ETMs count at the same flow tag
            for n, cmd in (('signoff', so), ('lec', lec)):
                with open(os.path.join(a.out, n + '.log'), 'w') as log:
                    rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
                print('%s rc=%d %s' % (n, rc, time.strftime('%H:%M:%S')))
                if n == 'signoff' and a.auto:   # no LEC slot on a re-sign that did not pass; the record says why
                    try:
                        so_rec = load(os.path.join(a.out, 'signoff', 'signoff.json'))
                    except Exception as e:
                        raise ResignError('no sign-off record (%s)' % e)
                    if so_rec.get('verdict') != 'SIGNED' and not needs_parent_only(so_rec):
                        raise ResignError('re-sign verdict %s, LEC not run' % so_rec.get('verdict'))
            d, lec_p = a.out, None
        else:
            d, lec_p = a.dir, a.lec
        rec = build_record(d, a.kit, a.tag, repo=a.repo, tools=a.tools, build_commit=a.build_commit,
                           routed_db=a.routed_db, lec=lec_p, lane=a.lane, note=a.note, pincmp=a.pincmp,
                           hash_db=not a.no_db_hash, auto=a.cmd == 'run' and a.auto)
    except ResignError as e:
        print('RESIGN NOT RECORDED: %s' % e, file=sys.stderr)
        return 1
    print('RESIGN RECORDED %s (%s %s, LEC %s%s)' % (write_record(d, rec), rec['flow_tag'], rec['src_commit'][:12],
                                                    rec['lec_verdict'], ', NEEDS_PARENT basis' if rec.get('verdict_basis') else ''))
    if a.cmd == 'run' and a.auto:
        mark_keep(rec, d, a.kit)
    return 0


if __name__ == '__main__':
    sys.exit(main())
