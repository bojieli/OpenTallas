#!/usr/bin/env python3
"""WAVE-OPS-1 nightly wave-source rebuild (OWNER 11-10 "yes to all 5", item B).  Runs on localhost (cron ~02:00 PST);
every heavy step runs on the fleet (compose + classify on epyc8, manifests + trees on the gen hosts, binds in a
memory-capped container on the bind host).

  plan   (DRY RUN) inputs -> compose -> classify per die; writes runs/<date>/plan.json + REPORT.md; changes nothing
  build  plan + NEW dated trees on every gen host (cp -al of the live tree, changed paths as new inodes, byte-checked
         against the expected manifest) + ARCHIVE-PROTECTED rows + strict binds launched detached
  advance  bind rc collected -> binddiff vs the bind of record (DIE-S81-85 binddiff.py @bc6a24d607) -> REPORT +
         queue post; the wave config is switched to the new tree (NEW launches only) only when
         lanes/wave-ops-1/SWITCH-OK holds 'standing' or tonight's date (written by KW-FIX-44 / COORD)

Sources of the overlay list: the latest "ROOT-MERGE-<n> UNLANDED" queue line (approved, not on main, landing order) and
KW-FIX-44 posts of the last 48 h naming "claude/<branch> @ <sha>".  A die's own src_sha (its wave branch) is merged on
top; whatever the live tree still holds beyond its src_sha (runtime overlays, plan/event files) is carried, 3-way
merged where main changed the same file, and kept live (reported) on conflict.  Live trees, running jobs and the live
config are never edited in place; nothing is deleted.
"""
import datetime, json, os, re, shlex, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
COORD = os.path.expanduser('~/coord')
QUEUE = os.path.join(COORD, 'lanes/COORD-REVIEW-QUEUE.md')
PROTECTED = os.path.join(COORD, 'lanes/prune/ARCHIVE-PROTECTED.tsv')
SWITCH_OK = os.path.join(HERE, 'SWITCH-OK')
HUB = 'intel2'
HUB_CFG = '/home/ubuntu/coord/autopilot/kit_wave.json'
CHOST = 'epyc8'                                            # compose + classify + bind host
LANE = '/srv/opentallas-scratch2/claude/wave-ops-1'
REPO = LANE + '/repo'
TOOLS = LANE + '/tools'
OUT_ROOT = '/srv/opentallas-scratch2/claude/wave-src'      # <OUT_ROOT>/<YYYYMMDD>/<die>/ on every gen host
GH = os.path.expanduser('~/.local/state/wave-ops-1/gh.git')  # localhost blobless GitHub mirror (relay of GitHub-only shas)
DIES = ('s81', 's81_head', 'qwen_compute', 'qwen_kvsys', 'hbm')
BINDDIFF = ('bc6a24d607858d9acc4120ef2159d8056b127d1e', 'results/die_s81_85_ftlock_1110/binddiff.py')
BIND_CAP_GB, YOSYS_CAP_GB = 64, 32


def ts(s):
    try:
        return time.mktime(time.strptime(s.strip()[:16], '%Y-%m-%d %H:%M'))
    except ValueError:
        return None


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def run(cmd, timeout=600, input=None, check=True):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=input)
    if check and p.returncode:
        raise RuntimeError('%s rc %d: %s' % (' '.join(cmd)[:200], p.returncode, (p.stderr or p.stdout)[-800:]))
    return p.stdout


def ssh(host, cmd, timeout=600, check=True, input=None):
    return run(['timeout', str(timeout), 'ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', host,
                'cd / && ' + cmd], timeout=timeout + 15, check=check, input=input)


def scp(src, dst, timeout=600):
    run(['timeout', str(timeout), 'scp', '-q', '-o', 'BatchMode=yes', src, dst], timeout=timeout + 15)


# ------------------------------------------------------------------------------------------------- inputs
SHA = r'\b[0-9a-f]{10,40}\b'


def parse_train(text):
    """latest 'ROOT-MERGE-<n> UNLANDED' line -> {line, main, overlays [{name, sha}] in landing order, excluded}"""
    line = None
    for l in text.splitlines():
        if re.search(r'ROOT-MERGE-\d+ UNLANDED', l):
            line = l
    if not line:
        return dict(line=None, main=None, overlays=[], excluded=[])
    m = re.search(r'main=([0-9a-f]{7,40})', line)
    body = line.split('in landing order:', 1)[-1]
    cut = re.search(r'Out of stack|Held:|Refused:', body)
    stack, rest = (body[:cut.start()], body[cut.start():]) if cut else (body, '')
    ovs = []
    for seg in stack.split(';'):
        seg = re.sub(r'\([^)]*\)', '', seg)
        shas = re.findall(SHA, seg)
        if not shas:
            continue
        name = seg[:seg.find(shas[0])].strip(' .,+')
        for s in shas:
            ovs.append(dict(name=name, sha=s, src='train'))
    exc = [dict(sha=s, why=w.strip()[:60]) for w, s in
           [(rest[:mm.start()].rsplit('.', 1)[-1], mm.group(0)) for mm in re.finditer(SHA, re.sub(r'\([^)]*\)', '', rest))]]
    return dict(line=line[:300], main=m.group(1) if m else None, overlays=ovs, excluded=exc)


def parse_kw44(text, now_s=None, window_h=48):
    """KW-FIX-44-authored blocks of the last window_h hours -> [{name: branch, sha}] (first sha per branch)"""
    now_s = now_s or time.time()
    out, seen, cur = [], set(), None
    for l in text.splitlines():
        h = re.match(r'^## \[KW44-[^\]]*\] KW-FIX-44 (\d{4}-\d\d-\d\d \d\d:\d\d)', l) or \
            re.match(r'^- (\d{4}-\d\d-\d\d \d\d:\d\d) PST \w[\w+]* \[KW-FIX-44 ->', l)
        if h:
            t = ts(h.group(1)); cur = t is not None and now_s - t <= window_h * 3600
        elif l.startswith('- ') or l.startswith('## '):
            cur = False
        if cur:
            for b, s in re.findall(r'(claude/[A-Za-z0-9._/-]+) ?@ ?(' + SHA[2:-2] + ')', l):
                if b not in seen:
                    seen.add(b); out.append(dict(name=b, sha=s, src='KW-FIX-44'))
    return out


def hub_cfg():
    return json.loads(ssh(HUB, 'cat ' + HUB_CFG, timeout=120))


def die_inputs(cfg):
    out = {}
    for die in DIES:
        d = (cfg.get('dies') or {}).get(die) or {}
        if not d.get('src'):
            continue
        out[die] = dict(src=d['src'], src_sha=d.get('src_sha'), gen_host=d.get('gen_host') or 'epyc7',
                        gen_hosts=list(d.get('gen_hosts') or [d.get('gen_host') or 'epyc7']), plan=d.get('plan'),
                        kit_rtl=d.get('kit_rtl') or {}, item_inputs=sorted(d.get('item_inputs') or {}),
                        bind_mem_gb=d.get('bind_mem_gb'))
    return out


# ------------------------------------------------------------------------------------------------- git relay
def ensure_shas(shas):
    """every sha resolvable in the compose clone: fetch the hub; GitHub-only ones through a localhost bundle"""
    ssh(CHOST, 'git -C %s fetch -q origin 2>/dev/null; true' % REPO, timeout=900)
    have = lambda: set(ssh(CHOST, 'cd %s && for s in %s; do git rev-parse -q --verify "$s^{commit}" >/dev/null && echo $s; '
                           'done; true' % (REPO, ' '.join(shas)), timeout=120).split())
    got = have()
    missing = [s for s in shas if s not in got]
    if not missing:
        return []
    run(['git', '-C', GH, 'fetch', '-q', 'origin'], timeout=900, check=False)
    refs, gone = [], []
    for s in missing:
        p = subprocess.run(['git', '-C', GH, 'rev-parse', '-q', '--verify', s + '^{commit}'], capture_output=True, text=True)
        if p.returncode:
            gone.append(s); continue
        refs.append('refs/wave/' + s)
        run(['git', '-C', GH, 'update-ref', refs[-1], p.stdout.strip()])
    if refs:
        main = run(['git', '-C', GH, 'rev-parse', 'main']).strip()
        b = os.path.expanduser('~/.local/state/wave-ops-1/relay.bundle')
        run(['git', '-C', GH, 'bundle', 'create', b] + refs + ['^' + main], timeout=900)
        scp(b, '%s:%s/relay.bundle' % (CHOST, LANE))
        ssh(CHOST, 'git -C %s fetch -q %s/relay.bundle "refs/wave/*:refs/wave/*"' % (REPO, LANE), timeout=600)
    return sorted(set(gone) | (set(missing) - have()))


def push_tools():
    for h in sorted(set([CHOST]) | set(HOSTS)):
        ssh(h, 'mkdir -p %s' % TOOLS, timeout=60)
        scp(os.path.join(HERE, 'wave_src_remote.py'), '%s:%s/wave_src_remote.py' % (h, TOOLS))


HOSTS = []


def remote(host, args, timeout=7200):
    return ssh(host, 'nice -n 10 ionice -c3 python3 -I %s/wave_src_remote.py %s' % (TOOLS, args), timeout=timeout)


# ------------------------------------------------------------------------------------------------- plan
def plan(date, run_dir, cfg=None, queue_text=None):
    os.makedirs(run_dir, exist_ok=True)
    cfg = cfg or hub_cfg()
    queue_text = queue_text if queue_text is not None else open(QUEUE, errors='replace').read()
    dies = die_inputs(cfg)
    HOSTS[:] = sorted({h for d in dies.values() for h in d['gen_hosts']})
    train = parse_train(queue_text)
    kw44 = parse_kw44(queue_text)
    known = {o['sha'] for o in train['overlays']}
    overlays = train['overlays'] + [o for o in kw44 if o['sha'] not in known]
    main = ssh(CHOST, 'git -C %s fetch -q origin main 2>/dev/null; git -C %s rev-parse origin/main' % (REPO, REPO), 900).strip()
    shas = sorted({o['sha'] for o in overlays} | {d['src_sha'] for d in dies.values() if d['src_sha']})
    gone = ensure_shas(shas)
    push_tools()
    tag = 'wave-src-' + date
    spec = dict(main=main, overlays=overlays, dies={k: d['src_sha'] for k, d in dies.items()},
                branch_prefix='refs/wave-src/' + date, worktree='%s/compose-%s' % (LANE, date))
    ssh(CHOST, 'mkdir -p %s/runs/%s && cat > %s/runs/%s/spec.json' % (LANE, date, LANE, date), input=json.dumps(spec))
    remote(CHOST, 'compose %s %s/runs/%s/spec.json %s/runs/%s/compose.json' % (REPO, LANE, date, LANE, date), 3600)
    comp = json.loads(ssh(CHOST, 'cat %s/runs/%s/compose.json' % (LANE, date)))
    res = dict(date=date, main=main, train_line=train['line'], train_main=train['main'], excluded=train['excluded'],
               overlays=comp['overlays'], base=comp['base'], unfetched=gone, dies={})
    for die, d in dies.items():
        r = dict(d, new_sha=comp['dies'][die]['sha'], die_branch=comp['dies'][die]['die_branch'],
                 new_tree='%s/%s/%s' % (OUT_ROOT, date, die))
        mdir = '%s/runs/%s' % (LANE, date)
        # live manifests on every gen host (inode cache per host); the canonical one is the config gen_host
        mans = {}
        for h in d['gen_hosts']:
            try:
                ssh(h, 'mkdir -p %s/cache %s' % (LANE, mdir), 60)
                remote(h, 'manifest %s %s/live_%s.tsv --cache %s/cache/manifest.tsv' % (d['src'], mdir, die, LANE))
                mans[h] = ssh(h, 'sha256sum %s/live_%s.tsv' % (mdir, die), 60).split()[0]
            except Exception as e:
                mans[h] = 'ERROR ' + str(e)[-200:]
        r['live_manifests'] = mans
        canon = d['gen_host'] if not str(mans.get(d['gen_host'], 'ERROR')).startswith('ERROR') else \
            next((h for h, v in mans.items() if not str(v).startswith('ERROR')), None)
        r['canonical_host'] = canon
        if not canon:
            r['error'] = 'no live manifest'; res['dies'][die] = r; continue
        if canon != CHOST:
            ssh(CHOST, 'mkdir -p %s && timeout 1200 scp -q -o BatchMode=yes %s:%s/live_%s.tsv %s/live_%s.tsv'
                % (mdir, canon, mdir, die, mdir, die), 1300)
        # 3-way merges read the live file on the compose host when its copy is identical, else nothing is merged
        live_root = d['src'] if mans.get(CHOST) == mans[canon] else ''
        out = remote(CHOST, 'classify %s %s/live_%s.tsv %s %s %s/classify_%s.json %s' % (
            REPO, mdir, die, d['src_sha'] or comp['dies'][die]['sha'], r['new_sha'], mdir, die, live_root), 7200)
        r['classify'] = json.loads(out.strip().splitlines()[-1])
        detail = json.loads(ssh(CHOST, "python3 -I -c \"import json;c=json.load(open('%s/classify_%s.json'));"
                                       "print(json.dumps({k:c[k] for k in ('carried','conflicts','merged')}))\"" % (mdir, die)))
        r['carried_dirs'] = top_dirs(detail['carried'])
        r['conflicts'] = detail['conflicts'][:60]
        r['merged'] = detail['merged'][:60]
        r['bind'] = bind_job(die, d, r['new_tree'], '%s/%s/%s.bind' % (OUT_ROOT, date, die),
                             script_text=script_text(d))
        res['dies'][die] = r
    json.dump(res, open(os.path.join(run_dir, 'plan.json'), 'w'), indent=1)
    open(os.path.join(run_dir, 'REPORT.md'), 'w').write(report(res))
    return res


def top_dirs(paths, depth=3, n=15):
    c = {}
    for p in paths:
        k = '/'.join(p.split('/')[:depth])
        c[k] = c.get(k, 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])[:n]


def script_text(d):
    s = (d.get('kit_rtl') or {}).get('script')
    if not s:
        return ''
    try:
        return ssh(d['gen_host'], 'cat ' + shlex.quote(s), 60)
    except Exception:
        return ''


def bind_job(die, d, new_tree, out, script_text=''):
    """the strict bind of record re-run on the new tree: same plan + same asbuilt (its RTL base stays pinned), new
    tools; DIE-S81-85 FTLOCK capped-container form (64g python + 32g sibling yosys, scratch mounted read-only)"""
    kr = d.get('kit_rtl') or {}
    asb, old = kr.get('asbuilt'), kr.get('bind_out')
    m = re.search(r'S81_BIND_OUT=(\S+)', script_text or '')
    if m:
        old = old or m.group(1).strip('"\'')
    m = re.search(r'S81_ASBUILT=(\S+)', script_text or '')
    if m:
        asb = m.group(1).strip('"\'')
    if not asb or not old:
        return dict(cmd=None, why='no strict bind of record in kit_rtl (%s mode, script export): bind-diff not applicable; '
                                  'the new tree is built and byte-checked only' % (kr.get('mode') or '?'),
                    asbuilt=asb, old_bind=old)
    if kr.get('prep_cmd'):
        inner = kr['prep_cmd'].format(plan=shlex.quote(d['plan']), bind=shlex.quote(out), asbuilt=shlex.quote(asb),
                                      src=shlex.quote(new_tree))
    else:
        inner = 'python -I -B tools/die_plan/bind.py bind %s --out %s --asbuilt %s --strict' % (d['plan'], out, asb)
    cmd = ('docker run --rm --name waveops_bind_%s -u $(id -u):$(id -g) --group-add $(stat -c %%g /var/run/docker.sock) '
           '-v /usr/bin/docker:/usr/bin/docker:ro -v /var/run/docker.sock:/var/run/docker.sock -e HOME=/tmp '
           '-e PYTHONDONTWRITEBYTECODE=1 --memory %dg --memory-swap %dg --cpus 2 '
           '-v /srv/opentallas-scratch2:/srv/opentallas-scratch2:ro -v /srv/opentallas-scratch3:/srv/opentallas-scratch3:ro '
           '-v %s:%s -w %s python:3.14-slim %s' % (die, BIND_CAP_GB, BIND_CAP_GB, out, out, new_tree, inner))
    return dict(cmd=cmd, asbuilt=asb, old_bind=old, plan=d['plan'], out=out)


def report(res):
    L = ['# Nightly wave-source rebuild %s (WAVE-OPS-1)' % res['date'], '',
         'main %s; composed base %s; train line: %s' % (res['main'][:12], res['base'][:12], res['train_line'] or 'none'), '']
    groups = {}
    for o in res['overlays']:
        groups.setdefault(o['status'], []).append('%s %s' % (o['name'], o['sha'][:12]))
    for k, v in groups.items():
        L.append('- overlays %s (%d): %s' % (k, len(v), '; '.join(v)))
    if res['excluded']:
        L.append('- not applied (train: out of stack / held / refused): ' + '; '.join(x['sha'] for x in res['excluded']))
    if res['unfetched']:
        L.append('- not found on hub or GitHub: ' + ' '.join(res['unfetched']))
    for die, r in res['dies'].items():
        L += ['', '## %s -> %s (new %s; die branch %s %s)' % (die, r['new_tree'], r['new_sha'][:12],
                                                               (r['src_sha'] or '-')[:12], r['die_branch'])]
        L.append('- live %s on %s; manifests: %s' % (r['src'], r.get('canonical_host'), ', '.join(
            '%s %s' % (h, v[:12]) for h, v in r['live_manifests'].items())))
        if r.get('error'):
            L.append('- ERROR ' + r['error']); continue
        L.append('- paths: ' + ', '.join('%s %d' % kv for kv in sorted(r['classify']['counts'].items(), key=lambda kv: -kv[1])))
        L.append('- carried live overlays (not in git), top dirs: ' + ', '.join('%s %d' % tuple(kv) for kv in r['carried_dirs']))
        if r['merged']:
            L.append('- 3-way merged: ' + ' '.join(r['merged'][:20]))
        if r['conflicts']:
            L.append('- conflicts (live kept): ' + ' '.join(r['conflicts'][:20]))
        b = r['bind']
        L.append('- re-bind: ' + ('strict bind of record (asbuilt %s, old bind %s) -> %s' % (b['asbuilt'], b['old_bind'], b['out'])
                                  if b.get('cmd') else b['why']))
        if r['item_inputs']:
            L.append('- item_inputs pinned (own plan/kit_rtl, not re-bound): %d' % len(r['item_inputs']))
    return '\n'.join(L) + '\n'


# ------------------------------------------------------------------------------------------------- build / advance
def build(date, run_dir):
    res = plan(date, run_dir)
    mdir = '%s/runs/%s' % (LANE, date)
    rows = []
    for die, r in res['dies'].items():
        if r.get('error'):
            continue
        remote(CHOST, 'pack %s %s/classify_%s.json %s/pack_%s.tar' % (REPO, mdir, die, mdir, die), 3600)
        remote(CHOST, 'expect %s/live_%s.tsv %s/classify_%s.json %s/expect_%s.tsv' % (mdir, die, mdir, die, mdir, die))
        r['hosts'] = {}
        for h in r['gen_hosts']:
            try:
                if h != CHOST:
                    ssh(CHOST, 'timeout 3000 scp -q -o BatchMode=yes %s/pack_%s.tar %s/classify_%s.json %s/expect_%s.tsv '
                               '%s:%s/' % (mdir, die, mdir, die, mdir, die, h, mdir), 3100)
                if r['live_manifests'].get(h) == r['live_manifests'][r['canonical_host']]:
                    remote(h, 'materialize %s %s %s/classify_%s.json %s/pack_%s.tar' % (r['src'], r['new_tree'], mdir, die, mdir, die))
                else:                          # a host whose live copy differs gets the canonical new tree
                    ssh(h, 'mkdir -p %s && nice rsync -a --link-dest=%s/ %s:%s/ %s.partial/ && mv %s.partial %s' % (
                        os.path.dirname(r['new_tree']), os.path.realpath(r['src']), r['canonical_host'], r['new_tree'],
                        r['new_tree'], r['new_tree'], r['new_tree']), 14400)
                out = ssh(h, 'nice python3 -I %s/wave_src_remote.py verify %s %s/expect_%s.tsv %s/verify_%s.json --cache '
                             '%s/cache/manifest.tsv' % (TOOLS, r['new_tree'], mdir, die, mdir, die, LANE), 7200, check=False)
                r['hosts'][h] = out.strip()[-300:]
            except Exception as e:
                r['hosts'][h] = 'ERROR ' + str(e)[-300:]
        rows.append('any\t%s\tWAVE-OPS-1 %s nightly wave src %s (new %s; running jobs may name it)' % (
            r['new_tree'], date, die, r['new_sha'][:12]))
        b = r['bind']
        if b.get('cmd') and all('"ok": true' in v for v in r['hosts'].values()):
            rc = '%s.rc' % b['out']
            need = (BIND_CAP_GB + YOSYS_CAP_GB + 32) * 1024 * 1024
            job = ('mkdir -p %s; for i in $(seq 1 720); do [ $(awk \'/MemAvailable/{print $2}\' /proc/meminfo) -ge %d ] && break; '
                   'sleep 60; done; %s > %s.log 2>&1; echo "BIND rc=$? %s" > %s' % (b['out'], need, b['cmd'], b['out'], b['out'], rc))
            ssh(CHOST, 'nohup setsid bash -c %s >/dev/null 2>&1 < /dev/null &' % shlex.quote(job), 60)
            b['launched'] = time.strftime('%Y-%m-%d %H:%M %Z')
            rows.append('any\t%s\tWAVE-OPS-1 %s nightly strict bind %s' % (b['out'], date, die))
    if rows:
        with open(PROTECTED, 'a') as f:
            f.write('\n'.join(rows) + '\n')
    json.dump(res, open(os.path.join(run_dir, 'build.json'), 'w'), indent=1)
    return res, rows


KIT_STORE = '/srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot/kit_store.py'   # KIT-INPUT-STORE-1 11-10 (on intel2)


def store_ingest(date, die, bind_out, mdir):
    """KIT-INPUT-STORE-1 11-10: strict binds + manifests go through the kit store (sparse: full src trees do not;
    they rebuild from their git sha).  The holding dir's hardlinks keep the blobs alive.  -> one status word/line"""
    try:
        src = ssh(HUB, 'cat ' + KIT_STORE, 120)
        hold = '%s/kit_inputs/%s_%s' % (LANE, date, die)
        out = ssh(CHOST, 'mkdir -p %s && python3 -I - ingest %s/bind.f %s/live_%s.tsv %s/expect_%s.tsv --kit-inputs %s '
                         '--tag wave-src-%s-%s' % (hold, bind_out, mdir, die, mdir, die, hold, date, die),
                  3600, check=False, input=src)
        m = re.search(r'KW_KIT_STORE (\{.*\})', out)
        return ('ingested ' + m.group(1)[:200]) if m else ('NOT ingested: ' + out.strip()[-200:])
    except Exception as e:
        return 'NOT ingested: %s' % str(e)[-200:]


def advance(date, run_dir):
    """after the binds: binddiff, switch (gated), report; returns (text, done)"""
    res = json.load(open(os.path.join(run_dir, 'build.json')))
    mdir = '%s/runs/%s' % (LANE, date)
    ssh(CHOST, 'test -s %s/binddiff.py || git -C %s show %s:%s > %s/binddiff.py' % (TOOLS, REPO, BINDDIFF[0], BINDDIFF[1], TOOLS), 120)
    done, lines = True, []
    for die, r in res['dies'].items():
        b = r.get('bind') or {}
        if not b.get('launched'):
            lines.append('%s: %s' % (die, 'not re-bound: ' + (b.get('why') or 'tree not verified on every gen host')))
            continue
        rc = ssh(CHOST, 'cat %s.rc 2>/dev/null; true' % b['out'], 60).strip()
        if not rc:
            done = False; lines.append('%s: bind running' % die); continue
        if 'rc=0' not in rc:
            lines.append('%s: strict bind FAILED (%s), log %s.log; wave stays on the old tree' % (die, rc, b['out'])); continue
        if not os.path.exists(os.path.join(run_dir, 'binddiff_%s.json' % die)):
            ssh(CHOST, 'echo \'{"types": []}\' > %s/ev_empty.json; cd %s && nice python3 -I %s/binddiff.py %s %s %s %s/ev_empty.json '
                       '%s/binddiff_%s.json > %s/binddiff_%s.out 2>&1' % (mdir, TOOLS, TOOLS, b['old_bind'], b['out'], b['plan'],
                                                                         mdir, mdir, die, mdir, die), 7200, check=False)
            ssh(CHOST, 'cat %s/binddiff_%s.json' % (mdir, die), 120)
            open(os.path.join(run_dir, 'binddiff_%s.json' % die), 'w').write(ssh(CHOST, 'cat %s/binddiff_%s.json' % (mdir, die), 120))
        bd = json.load(open(os.path.join(run_dir, 'binddiff_%s.json' % die)))
        lines.append('%s: strict bind rc 0; bound RTL changed on %d types (re-bound): %s' % (
            die, len(bd['changed']), ' '.join(bd['changed'][:30]) + (' ...' if len(bd['changed']) > 30 else '')))
        r['rebound'] = bd['changed']
        lines.append('%s: kit-store %s' % (die, store_ingest(date, die, b['out'], mdir)))
    for die, r in res['dies'].items():          # COORD 11-10: say which conflicted files the new tree keeps live
        if r.get('conflicts'):
            lines.append('%s: KEPT LIVE (conflicted with main+overlays, live bytes kept; see ATTRIBUTION for which are old main blobs) %d file(s): %s'
                         % (die, len(r['conflicts']), ' '.join(r['conflicts'][:40]) + (' ...' if len(r['conflicts']) > 40 else '')))
    ok = os.path.exists(SWITCH_OK) and open(SWITCH_OK).read().strip() in ('standing', date)
    lines.append('switch: ' + ('ALLOWED by lanes/wave-ops-1/SWITCH-OK; KW-FIX-44 applies it at the next idle gap (new launches only)'
                               if ok else 'NOT applied (no SWITCH-OK for %s): config unchanged, the new trees wait' % date))
    json.dump(res, open(os.path.join(run_dir, 'advance.json'), 'w'), indent=1)
    return '\n'.join(lines), done


def post(text, files=()):
    with open(QUEUE, 'a') as f:
        f.write(text if text.endswith('\n') else text + '\n')
    subprocess.run([os.path.join(COORD, 'bin/coord-commit.sh'), 'WAVE-OPS-1 nightly wave src (DO_NOT_COUNT)\n\n'
                    'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', 'lanes/COORD-REVIEW-QUEUE.md'] + list(files),
                   cwd=COORD, timeout=300)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else 'plan'
    date = argv[2] if len(argv) > 2 else datetime.date.today().strftime('%Y%m%d')
    run_dir = os.path.join(HERE, 'runs', date)
    os.makedirs(run_dir, exist_ok=True)
    stamp = time.strftime('%Y-%m-%d %H:%M %Z')
    if cmd == 'plan':
        res = plan(date, run_dir)
        print(open(os.path.join(run_dir, 'REPORT.md')).read())
    elif cmd == 'build':
        if os.path.exists(os.path.join(run_dir, 'build.json')):
            print('already built ' + date); return 0
        res, rows = build(date, run_dir)
        rel = os.path.relpath(run_dir, COORD)
        post('- %s STATE [WAVE-OPS-1 -> COORD, KW-FIX-44, ROOT-MERGE-57, KIT-INPUT-STORE-1] nightly wave src %s BUILT '
             '(new dated trees, live untouched, binds launched where a strict bind of record exists). DO_NOT_COUNT.\n%s%s'
             '  ARCHIVE-PROTECTED +%d rows. Full report %s/REPORT.md.\n' % (
                 stamp, date, ''.join('  %s: %s\n' % (d, '; '.join('%s %s' % (h, v[-80:]) for h, v in r.get('hosts', {}).items()))
                                      for d, r in res['dies'].items()),
                 ''.join('  %s KEPT LIVE (conflicted) %d: %s\n' % (d, len(r['conflicts']), ' '.join(r['conflicts'][:40]))
                         for d, r in res['dies'].items() if r.get('conflicts')), len(rows), rel),
             [os.path.relpath(PROTECTED, COORD)] + [os.path.join(rel, f) for f in ('REPORT.md', 'plan.json', 'build.json')])
    elif cmd == 'advance':
        if not os.path.exists(os.path.join(run_dir, 'build.json')) or os.path.exists(os.path.join(run_dir, 'POSTED')):
            return 0
        txt, done = advance(date, run_dir)
        if done:
            rel = os.path.relpath(run_dir, COORD)
            open(os.path.join(run_dir, 'POSTED'), 'w').write(stamp + '\n')
            post('- %s RESULT [WAVE-OPS-1 -> COORD, KW-FIX-44, ROOT-MERGE-57] nightly wave src %s bind-diff. DO_NOT_COUNT.\n%s\n'
                 % (stamp, date, '\n'.join('  ' + l for l in txt.splitlines())),
                 [os.path.join(rel, f) for f in ('advance.json', 'POSTED')])
        print(txt)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
