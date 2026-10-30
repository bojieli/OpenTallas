#!/usr/bin/env python3
"""RE-SIGN a routed core at a released flow tag and write its kind:resign PROVENANCE.json.

COORD ruling 2026-10-30 02:03 (3b) / OWNER 12.20 RE-SIGN rule: a signed block counts once sign-off (signoff.py) and the
post-route LEC (lec.py) are re-run on its SAME routed DB with the tools of a released per-die flow tag.  The release
counter (coord tools/release_tree_plan.py) counts such a record only through a PROVENANCE.json next to the re-sign
signoff/ dir: {kind: resign, src_commit: <tag commit>, flow_tag, routed_db, build_commit, lec}.  Until now every lane
wrote that file by hand (or forgot it: KV PHY103 10-30 13:0x).  This tool makes it part of the re-sign step.

  resign.py run        --kit K --tag TAG --tools T --out D [--run-dir R] [--lec-netlist V] ...   (sign-off + LEC + record)
  resign.py provenance --kit K --tag TAG --dir D [--tools T] ...                                   (record only)

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

TAG_RE = re.compile(r'^flow-\d{8}-[a-z](?:-(qc|s81|head|kv|hbm))?$')  # = release_tree_plan.check_resign_tag
SHA_RE = re.compile(r'^[0-9a-f]{40}$')
TOOLS = ('signoff.py', 'lec.py')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULE = 'COORD ruling (3b) 2026-10-30 02:03 / OWNER 12.20: RE-SIGN on the same routed DB with flow-tag tools, no new checks'


class ResignError(Exception):
    pass


def git(repo, *args):
    p = subprocess.run(['git', '-C', repo] + list(args), capture_output=True)
    if p.returncode:
        raise ResignError('git %s: %s' % (' '.join(args), p.stderr.decode(errors='replace').strip()))
    return p.stdout


def tag_commit(repo, tag):
    if not TAG_RE.match(tag or ''):
        raise ResignError('%r is not a flow release tag name (flow-YYYYMMDD-x[-die])' % tag)
    return git(repo, 'rev-parse', '--verify', tag + '^{commit}').decode().strip()


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
        want = hashlib.sha256(git(repo, 'show', '%s:tools/die_plan/%s' % (tag, n))).hexdigest()
        got = sha256(p)
        if got != want:
            raise ResignError('%s sha256 %s != %s:tools/die_plan/%s %s' % (p, got[:12], tag, n, want[:12]))
        out[n] = got
    return out


def load(path):
    with open(path) as f:
        return json.load(f)


def kit_build_commit(kit):
    """the original build commit from the kit's own records (lec kit_provenance, autopilot, freeze)."""
    for n in ('PROVENANCE.json', 'AUTOPILOT.json', 'freeze.json', 'kit_provenance.json'):
        p = os.path.join(kit, n)
        try:
            x = load(p)
        except Exception:
            continue
        if not isinstance(x, dict) or x.get('kind') == 'resign':
            continue
        for v in (x.get('build_commit'), x.get('src_commit'), (x.get('provenance') or {}).get('commit')
                  if isinstance(x.get('provenance'), dict) else None, x.get('source_commit')):
            if isinstance(v, str) and SHA_RE.match(v):
                return v
    return None


def find_lec(d):
    for p in [os.path.join(d, 'lec', 'lec.json')] + sorted(glob.glob(os.path.join(d, 'lec', '*.json'))):
        if os.path.isfile(p):
            return p
    return None


def build_record(d, kit, tag, repo=REPO, tools=None, build_commit=None, routed_db=None, lec=None, src_commit=None,
                 lane=None, note=None, pincmp=None, hash_db=True):
    """validate one re-sign dir and return its PROVENANCE dict; raises ResignError on any failed check."""
    d, kit = os.path.abspath(d), os.path.abspath(kit)
    full = tag_commit(repo, tag)
    if src_commit and not full.startswith(src_commit):
        raise ResignError('--src-commit %s is not %s = %s' % (src_commit, tag, full[:12]))
    so_p = os.path.join(d, 'signoff', 'signoff.json')
    try:
        so = load(so_p)
    except Exception as e:
        raise ResignError('no readable re-sign %s (%s)' % (so_p, e))
    if so.get('verdict') != 'SIGNED':
        raise ResignError('re-sign %s verdict %s, not SIGNED' % (so_p, so.get('verdict')))
    lec = os.path.abspath(lec) if lec else find_lec(d)
    if not lec:
        raise ResignError('no post-route lec.json under %s/lec' % d)
    try:
        lv = load(lec).get('verdict')
    except Exception as e:
        raise ResignError('unreadable %s (%s)' % (lec, e))
    if lv != 'EQUIVALENT':
        raise ResignError('post-route LEC %s verdict %s, not EQUIVALENT' % (lec, lv))
    read_db = (so.get('inputs') or {}).get('odb')
    if not read_db:
        raise ResignError('%s names no inputs.odb (cannot prove the same routed DB)' % so_p)
    if routed_db and os.path.realpath(routed_db) != os.path.realpath(read_db):
        raise ResignError('re-sign read %s, not the routed DB %s' % (read_db, routed_db))
    if not os.path.isfile(read_db):
        raise ResignError('routed DB %s missing' % read_db)
    tool_sha = check_tools(repo, tag, tools) if tools else None
    bc = build_commit or kit_build_commit(kit)
    if not bc:
        raise ResignError('build_commit unknown: pass --build-commit (no commit in %s records)' % kit)
    rec = dict(schema='opentallas.resign_qualification.v1', kind='resign', verdict='SIGNED',
               src_commit=full, flow_tag=tag, routed_db=read_db, build_commit=bc, lec=lec, lec_verdict=lv,
               resign_signoff=so_p, kit=kit, original_signoff=os.path.join(kit, 'signoff', 'signoff.json'),
               name=so.get('name'), rule=RULE, writer='tools/die_plan/resign.py',
               host=socket.gethostname(), created=time.strftime('%Y-%m-%d %H:%M %Z'))
    if hash_db:
        rec['routed_db_sha256'] = sha256(read_db)
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


def run_cmds(kit, run_dir, tools, out, image, name, lec_netlist=None, mem='32g', cpus=8):
    """the two commands of one re-sign (same as the lane scripts resign3.sh / tag_signoff_lec.sh)."""
    kit, run_dir, tools, out = map(os.path.abspath, (kit, run_dir, tools, out))
    so = [sys.executable, '-I', os.path.join(tools, 'signoff.py'), 'run', '--run-dir', run_dir, '--kit', kit,
          '--corners', 'tt,ff', '--ff-vclk', 'auto', '--out', os.path.join(out, 'signoff'), '--image', image]
    if lec_netlist:
        net = os.path.abspath(lec_netlist)
        mounts = ['-v', '%s:/net.v:ro' % net]
        net_in = '/net.v'
    else:
        vs = sorted(glob.glob(os.path.join(run_dir, 'results', 'asap7', '*', 'base', '6_final.v')))
        if not vs:
            raise ResignError('no 6_final.v under %s/results/asap7/*/base' % run_dir)
        if not vs[0].startswith(kit + os.sep):
            raise ResignError('6_final.v %s is outside the kit %s (LEC mounts the kit)' % (vs[0], kit))
        mounts, net_in = [], '/work/' + os.path.relpath(vs[0], kit)
    lec = ['docker', 'run', '--rm', '--name', 'resign-%s-lec' % name, '--memory=%s' % mem, '--cpus=%d' % cpus,
           '-v', '%s:/work:ro' % kit, '-v', '%s:/eco' % out, '-v', '%s:/m:ro' % tools] + mounts + [
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
            s.add_argument('--tools', required=True, help='tools/die_plan exported at TAG')
            s.add_argument('--out', required=True, help='re-sign dir (signoff/, lec/, PROVENANCE.json)')
            s.add_argument('--run-dir', help='ORFS run dir (default KIT/run)')
            s.add_argument('--lec-netlist', help='function-neutral normalised 6_final.v copy (default: the run 6_final.v)')
            s.add_argument('--image', default='openroad/orfs:asap7lock')
            s.add_argument('--name', default=None, help='docker container suffix')
            s.add_argument('--dry-run', action='store_true', help='print the commands only')
        else:
            s.add_argument('--dir', required=True, help='re-sign dir holding signoff/signoff.json + lec/lec.json')
            s.add_argument('--tools', help='tag tools dir to verify against TAG (recommended)')
            s.add_argument('--lec', help='post-route lec.json (default DIR/lec/lec.json)')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'run':
            os.makedirs(a.out, exist_ok=True)
            tag_commit(a.repo, a.tag)
            check_tools(a.repo, a.tag, a.tools)  # fail before spending an RCX run on the wrong tools
            name = a.name or re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.basename(os.path.abspath(a.out)))
            so, lec = run_cmds(a.kit, a.run_dir or os.path.join(a.kit, 'run'), a.tools, a.out, a.image, name,
                               a.lec_netlist)
            if a.dry_run:
                print(' '.join(so)); print(' '.join(lec)); return 0
            env = dict(os.environ, SIGNOFF_DOCKER=os.environ.get('SIGNOFF_DOCKER', 'docker'))
            for n, cmd in (('signoff', so), ('lec', lec)):
                with open(os.path.join(a.out, n + '.log'), 'w') as log:
                    rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
                print('%s rc=%d %s' % (n, rc, time.strftime('%H:%M:%S')))
            d, lec_p = a.out, None
        else:
            d, lec_p = a.dir, a.lec
        rec = build_record(d, a.kit, a.tag, repo=a.repo, tools=a.tools, build_commit=a.build_commit,
                           routed_db=a.routed_db, lec=lec_p, lane=a.lane, note=a.note, pincmp=a.pincmp,
                           hash_db=not a.no_db_hash)
    except ResignError as e:
        print('RESIGN NOT RECORDED: %s' % e, file=sys.stderr)
        return 1
    print('RESIGN RECORDED %s (%s %s, LEC %s)' % (write_record(d, rec), rec['flow_tag'], rec['src_commit'][:12],
                                                  rec['lec_verdict']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
