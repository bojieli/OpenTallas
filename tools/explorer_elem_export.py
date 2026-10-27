#!/usr/bin/env python3
"""Chip Explorer element pages (fleet-viz /explorer/element/?e=<element>), generated for every CLOSED element with no
per-element manual input.  Inputs: the closure job record (~/.local/state/closure_loop/jobs/<job>.json, its verdict on
main when merged), the job's final routed DB on its fleet host, and the job's source commit (git).

  auto  --job <closure job> [--element <id>]     local orchestrator for one job (the closure loop's post-close hook):
        probe the host for the accepted DB (6_final.odb / spef / sdc) and the job's own sign-off STA scripts
        (w18_sta_tt.tcl, else the TT re-STA, else w18_sta_ss.tcl with its libs swapped to TT), rebuild the source tree
        from git when the loop released src/, run `run` + the RTL export on the host under ot-heavy (nice 19, memory
        sized from the DB), fetch the result and `pack` it into the fleet-viz data store.  Writes a marker
        ~/.local/state/viz-elem/<job>.json (running / done / failed) that deep release honours.  Never raises into
        its caller: a failure is recorded in the marker only.
  batch [--limit N] [--host H] [--redo]           auto for every CLOSED element of the fleet element registry
        (/api/elements, best closing job), at most 2 at a time per host.
  run   (on the host) --orfs <dir> --src <dir> --out <dir> [--tt-tcl F --ff-tcl F --ss2tt | --nosta]
  pack  (local) --raw <dir> --element <id> --job <job> --dest <data dir> [--rtl rtl.json] [...]

Big blobs live in the fleet-viz data store (~/.local/share/fleet-viz/explorer/element/data) and on the host
(<scratch>/viz-elem-store/<job>/raw), never in git.
"""
import argparse, concurrent.futures as cf, fcntl, hashlib, json, math, os, pathlib, re, shlex, shutil, subprocess, sys, threading, time, traceback

HERE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path(os.environ.get('CL_REPO', HERE.parent))
IMAGE = 'openroad/orfs:asap7lock'
OPENROAD = '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
STATE = pathlib.Path.home() / '.local/state/closure_loop/jobs'
MARKS = pathlib.Path.home() / '.local/state/viz-elem'
DEST = pathlib.Path.home() / '.local/share/fleet-viz/explorer/element/data'
CACHE = pathlib.Path.home() / '.cache/viz-elem'
TOOLS = [HERE / 'explorer_elem_export.py', HERE / 'explorer_elem' / 'or_export.py', HERE / 'explorer_elem' / 'rtl_export.py']
REF_NAME = re.compile(r'(oracle|golden|ref_model|refmodel|reference_model|_reference\b|_ref\.py$)', re.I)
PATH_RE = re.compile(r'\b((?:tools|rtl|physical|results|tests|compiler|src)/[A-Za-z0-9_./-]+\.(?:py|sv|svh|v|json|sh|cpp|h|tcl))\b')


# ------------------------------------------------------------------------------------------------ host side: run
def preamble(tcl_text, ss2tt=False):
    """the corner STA setup lines of a closure-loop STA script (everything before the first report)"""
    out = []
    for ln in tcl_text.splitlines():
        s = ln.strip()
        if s.startswith('puts ') or s.startswith('report_') or s.startswith('foreach') or s == 'exit':
            break
        if s: out.append(s)
    if not any(s.startswith('read_db') for s in out) or not any(s.startswith('read_spef') for s in out):
        raise SystemExit('preamble lacks read_db/read_spef: %r' % out[-3:])
    text = '\n'.join(out) + '\n'
    if ss2tt:   # the same swap the loop's own TT re-STA (meas_resta.py) applies to an SS setup script
        text = re.sub(r'_(R|L|SL)VT_SS_nldm', r'_\1VT_TT_nldm', text).replace('_ss.lib', '_tt.lib')
    return text


def cmd_run(a):
    orfs, src, out = pathlib.Path(a.orfs), pathlib.Path(a.src), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    exp = out / 'exp'; exp.mkdir(exist_ok=True)
    shutil.copy(HERE / 'explorer_elem' / 'or_export.py', exp / 'or_export.py')
    jobs = []
    if a.nosta:
        odb = sorted(orfs.glob('results/asap7/*/base/6_final.odb'))
        if not odb: raise SystemExit('no 6_final.odb under %s' % orfs)
        (out / 'pre_geom.tcl').write_text('read_db /work/%s\n' % odb[0].relative_to(orfs))
        jobs.append(('geom', 'pre_geom.tcl'))
    else:
        tt = pathlib.Path(a.tt_tcl) if a.tt_tcl else orfs / 'w18_sta_tt.tcl'
        ff = pathlib.Path(a.ff_tcl) if a.ff_tcl else orfs / 'w18_sta_ff.tcl'
        (out / 'pre_tt.tcl').write_text(preamble(tt.read_text(), a.ss2tt)); jobs.append(('tt', 'pre_tt.tcl'))
        if ff.exists(): (out / 'pre_ff.tcl').write_text(preamble(ff.read_text())); jobs.append(('ff', 'pre_ff.tcl'))
    procs = []
    for c, pre in jobs:
        cmd = ['nice', '-n', '19', 'ot-heavy', '--mem', str(a.mem), '--', 'docker', 'run', '--rm', '--memory', '%dg' % a.mem,
               '--cpu-shares', '128', '--user', '%d:%d' % (os.getuid(), os.getgid()),
               '-v', '%s:/work:ro' % orfs, '-v', '%s:/src:ro' % src, '-v', '%s:/exp:ro' % exp, '-v', '%s:/out' % out,
               '-e', 'OT_PRE=/out/' + pre, '-e', 'OT_CORNER=' + c, '-e', 'OT_OUT=/out', '-e', 'OT_NPATH=%d' % a.npath,
               '-e', 'OT_NOSTA=%d' % int(bool(a.nosta)), '-e', 'HOME=/tmp', a.image, OPENROAD, '-python', '-exit', '-threads', str(a.threads), '/exp/or_export.py']
        lg = open(out / ('export_%s.log' % c), 'w')
        print(' '.join(cmd), file=lg, flush=True)
        procs.append((c, subprocess.Popen(cmd, stdout=lg, stderr=subprocess.STDOUT)))
    rc = 0
    for c, p in procs:
        r = p.wait(); print('%s rc %d' % (c, r)); rc |= r
    return rc


PROBE = r'''
import glob, json, os, re, sys
a = json.loads(sys.stdin.read()); run = (a.get("run") or "").rstrip("/")
cands = [a["orfs_dir"]] if a.get("orfs_dir") else []
if run:
    cands += sorted(glob.glob(run + "/cl/eco*/pass*/orfs"), key=os.path.getmtime, reverse=True)
    cands += sorted(glob.glob(run + "/routes/*/work/orfs"))
res = dict(run=bool(run and os.path.isdir(run)))
for d in cands:
    b = glob.glob(d + "/results/asap7/*/base/6_final.odb")
    if not b: continue
    base = os.path.dirname(b[0])
    res.update(orfs=d, base=base, odb_gb=os.path.getsize(b[0]) / 1e9,
               spef_gb=os.path.getsize(base + "/6_final.spef") / 1e9 if os.path.exists(base + "/6_final.spef") else None,
               sdc=os.path.exists(base + "/6_final.sdc"))
    tt = [(d + "/w18_sta_tt.tcl", 0), (os.path.dirname(d) + "/tt_resta_corner_sta.tt.tcl", 0), (d + "/w18_sta_ss.tcl", 1)]
    for p, ss in tt:
        if os.path.exists(p):
            res.update(tt_tcl=p, ss2tt=bool(ss)); break
    if os.path.exists(d + "/w18_sta_ff.tcl"): res["ff_tcl"] = d + "/w18_sta_ff.tcl"
    break
cfgs = sorted(glob.glob(run + "/routes/*/work/orfs/config.mk")) if run else []
if res.get("orfs") and os.path.exists(res["orfs"] + "/config.mk"): cfgs.insert(0, res["orfs"] + "/config.mk")
if cfgs: res["config"] = cfgs[0]
need = set()
for k in ("tt_tcl", "ff_tcl"):
    if res.get(k):
        need.update(re.findall(r"/src/(\S+)", open(res[k]).read()))
res["need_sta"] = sorted(need)
if res.get("config"):
    t = open(res["config"]).read()
    need.update(re.findall(r"/src/(\S+)", t))
res["need"] = sorted(need)
try: res["src_commit"] = open(run + "/src/SOURCE_COMMIT").read().strip()
except OSError: res["src_commit"] = None
res["src_missing"] = [p for p in res["need"] if not os.path.exists(run + "/src/" + p)] if run else res["need"]
print(json.dumps(res))
'''


# ------------------------------------------------------------------------------------------------ local helpers
def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def ssh(host, cmd, inp=None, timeout=600):
    if host in ('localhost', '127.0.0.1', None):
        return subprocess.run(['bash', '-c', cmd], input=inp, capture_output=True, text=True, timeout=timeout)
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=30', host, cmd],
                          input=inp, capture_output=True, text=True, timeout=timeout)


def mark(job, **kw):
    MARKS.mkdir(parents=True, exist_ok=True)
    p = MARKS / (job + '.json')
    d = {}
    try: d = json.loads(p.read_text())
    except Exception: pass
    d.update(kw, updated=__import__('datetime').datetime.now().astimezone().isoformat(timespec='seconds'))   # parseable by fromisoformat (py3.10)
    tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); os.replace(tmp, p)
    return d


def git_has(commit):
    return bool(commit) and sh(['git', '-C', str(REPO), 'cat-file', '-e', commit + '^{commit}']).returncode == 0


def git_show(commit, path):
    r = sh(['git', '-C', str(REPO), 'show', '%s:%s' % (commit, path)])
    return r.stdout if r.returncode == 0 else None


def store_dir(run, job):
    p = pathlib.PurePosixPath(run.rstrip('/'))
    return str(p.parent.parent / 'viz-elem-store' / job)


def find_reference_model(spec, state, commit, max_files=80):
    """the reference model a job's bench names: seed paths from the job's bench fields, then follow file references at
    the source commit (depth <= 2) until a file whose name marks it as an oracle / golden / reference model"""
    seeds_txt = json.dumps({k: v for k, v in spec.items() if 'bench' in k.lower()}) + json.dumps((spec.get('stages') or {}).get('bench') or [])
    seeds_txt += json.dumps(state.get('benches') or {})
    seen, frontier, parent = set(), [], {}
    for p in PATH_RE.findall(seeds_txt):
        if p not in seen: seen.add(p); frontier.append(p); parent[p] = None
    found = None
    for depth in range(3):   # bench file -> at most 2 hops: deeper chains wander into generic models (uarch_model.py)
        nxt = []
        for p in frontier:
            if REF_NAME.search(os.path.basename(p)) and git_show(commit, p) is not None:
                found = p; break
            if len(seen) > max_files: continue
            t = git_show(commit, p)
            if t is None: continue
            for q in PATH_RE.findall(t):
                if q not in seen: seen.add(q); nxt.append(q); parent[q] = p
        if found: break
        frontier = nxt
    if not found:
        return dict(found=False, seeds=[p for p, v in parent.items() if v is None][:8])
    chain, p = [], found
    while p: chain.append(p); p = parent.get(p)
    txt = git_show(commit, found)
    return dict(found=True, path=found, commit=commit, chain=list(reversed(chain)), sha256=hashlib.sha256(txt.encode()).hexdigest(), text=txt)


def update_index(dest, eid, entry):
    dest.mkdir(parents=True, exist_ok=True)
    with open(dest / '.index.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        p = dest / 'index.json'
        try: d = json.loads(p.read_text())
        except Exception: d = dict(schema='opentallas.explorer_elem.index.v1', elements={})
        d['elements'][eid] = entry
        d['generated'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(d, separators=(',', ':'))); os.replace(tmp, p)


# ------------------------------------------------------------------------------------------------ auto (one job)
def auto(job, element=None, dest=DEST, reg=None, log=print, redo=False):
    try:
        return _auto(job, element, pathlib.Path(dest), reg or {}, log, redo)
    except Exception as e:
        mark(job, state='failed', error=('%s: %s' % (type(e).__name__, e))[:400], trace=traceback.format_exc()[-1500:])
        log('%s FAILED %s' % (job, e))
        return False


def _auto(job, element, dest, reg, log, redo):
    st = json.loads((STATE / (job + '.json')).read_text())
    spec, host, run = st['spec'], st.get('host'), (st.get('run') or '').rstrip('/')
    eid = element or spec.get('block') or job
    commit = st.get('commit_full') or (spec.get('source') or {}).get('commit') or ''
    m = st.get('metrics') or {}
    mark(job, state='running', element=eid, host=host, started=time.strftime('%Y-%m-%dT%H:%M:%S%z'), error=None)
    pr = ssh(host, 'python3 -c ' + shlex.quote(PROBE), inp=json.dumps(dict(run=run, orfs_dir=m.get('orfs_dir'))), timeout=300)
    if pr.returncode: raise RuntimeError('probe failed on %s: %s' % (host, pr.stderr[-300:]))
    P = json.loads(pr.stdout)
    S = store_dir(run, job) if run else None
    raw_local = CACHE / job / 'raw'; raw_local.mkdir(parents=True, exist_ok=True)
    have_commit = git_has(commit)
    nosta = not (P.get('orfs') and P.get('tt_tcl') and P.get('sdc') and P.get('spef_gb'))
    layout = bool(P.get('orfs'))
    if layout or P.get('config'):
        # ship the exporter; rebuild the source paths the loop released (git archive of exactly what the scripts read)
        ssh(host, 'mkdir -p %s/tools/explorer_elem %s/raw' % (S, S))
        for t in TOOLS:
            rel = 'tools/explorer_elem/' + t.name if t.parent.name == 'explorer_elem' else 'tools/' + t.name
            r = ssh(host, 'cat > %s/%s' % (S, rel), inp=t.read_text())
            if r.returncode: raise RuntimeError('ship %s: %s' % (rel, r.stderr[-200:]))
        src = run + '/src'
        if P.get('src_missing') or P.get('src_commit') != commit:
            if not have_commit:
                nosta = True; src = None
            else:
                paths = [p for p in P.get('need', []) if sh(['git', '-C', str(REPO), 'cat-file', '-e', '%s:%s' % (commit, p)]).returncode == 0]
                src = S + '/src'
                ssh(host, 'rm -rf %s && mkdir -p %s' % (src, src))
                if paths:
                    ar = subprocess.run(['git', '-C', str(REPO), 'archive', '--format=tar', commit, '--'] + paths, capture_output=True)
                    rr = subprocess.run((['bash', '-c', 'tar -x -C %s' % src] if host in ('localhost', None) else
                                         ['ssh', '-o', 'BatchMode=yes', host, 'tar -x -C %s' % src]), input=ar.stdout, capture_output=True, timeout=600)
                    if rr.returncode: raise RuntimeError('src rebuild: %s' % rr.stderr[-200:])
                ssh(host, 'echo %s > %s/SOURCE_COMMIT' % (commit, src))
                # files the loop GENERATES into a job's src (io_ref_routed.sdc, per-view io_place.tcl, ...) are not in git;
                # the loop keeps text copies elsewhere in the run dir (cl/, routes/...): recover them by name
                missing = [p for p in P.get('need', []) if p not in paths]
                if missing:
                    rec = r'''
import os, shutil, sys
run, src = sys.argv[1], sys.argv[2]
for p in sys.argv[3:]:
    b = os.path.basename(p); hit = None
    for dp, dn, fn in [w for root in (run + "/cl", run) for w in os.walk(root)]:   # the loop's own copy in cl/ first
        if hit: break
        if dp == run + "/src" or dp.startswith(run + "/src/"): dn[:] = []; continue
        if dp.startswith(run + "/routes") and "/objects" in dp: dn[:] = []; continue
        if b in fn: hit = os.path.join(dp, b)
    if hit:
        os.makedirs(os.path.dirname(os.path.join(src, p)), exist_ok=True); shutil.copy(hit, os.path.join(src, p)); print("RECOVERED", p, hit)
'''
                    r = ssh(host, 'python3 -c %s %s %s %s' % (shlex.quote(rec), shlex.quote(run), shlex.quote(src), ' '.join(shlex.quote(p) for p in missing)), timeout=600)
                    got = set(re.findall(r'^RECOVERED (\S+)', r.stdout, re.M))
                    missing = [p for p in missing if p not in got]
                    if got: log('%s: recovered %d generated source file(s) from the run dir: %s' % (job, len(got), ', '.join(sorted(got))))
                sta_missing = [p for p in missing if p in set(P.get('need_sta', P.get('need', [])))]
                if sta_missing and not nosta:
                    log('%s: %d STA source paths neither in git at %s nor in the run dir (%s) -> geometry only' % (job, len(sta_missing), commit[:10], ', '.join(sta_missing))); nosta = True
    if layout:
        odb_gb, spef_gb = P.get('odb_gb') or 0, P.get('spef_gb') or 0
        mem = int(min(160, max(12, math.ceil(10 * odb_gb + 6 * spef_gb + 6))))
        args = ['--orfs', P['orfs'], '--src', src or (S + '/src'), '--out', S + '/raw', '--mem', str(mem)]
        if nosta: args.append('--nosta')
        else:
            args += ['--tt-tcl', P['tt_tcl']] + (['--ff-tcl', P['ff_tcl']] if P.get('ff_tcl') else []) + (['--ss2tt'] if P.get('ss2tt') else [])
        if not (src or nosta): ssh(host, 'mkdir -p %s/src' % S)
        log('%s: run on %s (mem %d GB%s)' % (job, host, mem, ', geometry only' if nosta else ''))
        r = ssh(host, 'cd %s && python3 tools/explorer_elem_export.py run %s' % (S, ' '.join(shlex.quote(x) for x in args)), timeout=6 * 3600)
        if r.returncode:
            raise RuntimeError('run rc %d: %s %s' % (r.returncode, r.stdout[-300:], r.stderr[-300:]))
    rtl_ok, rtl_err = False, None if P.get('config') else 'the route\'s synthesis config (config.mk) was not found on the host'
    if P.get('config') and src:
        r = ssh(host, 'cd %s && nice -n 19 python3 tools/explorer_elem/rtl_export.py --config %s --src %s --out %s/rtl --mem 16' % (S, shlex.quote(P['config']), shlex.quote(src), S), timeout=3600)
        rtl_ok = r.returncode == 0
        if not rtl_ok:
            errs = re.findall(r'^.*ERROR.*$', r.stdout + r.stderr, re.M)
            rtl_err = (errs[-1] if errs else (r.stdout + r.stderr)[-200:]).strip()[:300]
            log('%s: rtl export failed: %s' % (job, rtl_err))
    # fetch
    names = (['tt.json', 'ff.json', 'cells.bin', 'clk.bin', 'power_tt.rpt'] if layout else [])
    for n in names:
        rr = subprocess.run((['cp', S + '/raw/' + n, str(raw_local / n)] if host in ('localhost', None) else
                             ['scp', '-q', '-o', 'BatchMode=yes', '%s:%s/raw/%s' % (host, S, n), str(raw_local / n)]), capture_output=True)
    rtl_local = None
    if rtl_ok:
        rtl_local = CACHE / job / 'rtl.json'
        subprocess.run((['cp', S + '/rtl/rtl.json', str(rtl_local)] if host in ('localhost', None) else
                        ['scp', '-q', '-o', 'BatchMode=yes', '%s:%s/rtl/rtl.json' % (host, S), str(rtl_local)]), capture_output=True)
        if not rtl_local.exists(): rtl_local = None
    ref = find_reference_model(spec, st, commit) if have_commit else dict(found=False, seeds=[], note='source commit not in the repo')
    pack(raw=raw_local if layout and (raw_local / 'tt.json').exists() else None, element=eid, job=job, dest=dest, st=st,
         host=host, raw_remote=(S + '/raw') if S else None, db=('%s:%s/6_final.odb' % (host, P['base'])) if P.get('base') else None,
         rtl=rtl_local, ref=ref, reg=reg, nosta=nosta, rtl_error=None if rtl_local else (rtl_err or 'RTL export produced no output'))
    mark(job, state='done', element=eid, layout=layout, nosta=nosta, rtl=bool(rtl_local), reference=ref.get('path'), error=None)
    log('%s -> %s done (layout %s, sta %s, rtl %s, ref %s)' % (job, eid, layout, not nosta, bool(rtl_local), ref.get('path')))
    return True


# ------------------------------------------------------------------------------------------------ pack
def _num(x):
    try: return float(x)
    except Exception: return None


def pack(raw, element, job, dest, st, host=None, raw_remote=None, db=None, rtl=None, ref=None, reg=None, nosta=False, rtl_error=None,
         label=None, role=None, summary=None, note=None, extra_facts=(), record_ref=None):
    dest = pathlib.Path(dest); dest.mkdir(parents=True, exist_ok=True)
    reg = reg or {}
    tt = json.loads((raw / 'tt.json').read_text()) if raw else None
    ff = json.loads((raw / 'ff.json').read_text()) if raw and (raw / 'ff.json').exists() else None
    spec = st.get('spec') or {}
    rec_dir = REPO / 'results/closure_loop' / job
    verdict = None
    if (rec_dir / 'verdict.json').exists():
        verdict = json.loads((rec_dir / 'verdict.json').read_text()); rec_ref = 'main:results/closure_loop/%s/verdict.json' % job
    elif record_ref:
        r = sh(['git', '-C', str(REPO), 'show', record_ref])
        verdict = json.loads(r.stdout) if r.returncode == 0 else None; rec_ref = record_ref
    else:
        rec_ref = None
    spath = '~/.local/state/closure_loop/jobs/%s.json' % job
    rs = rec_ref or spath
    m = (verdict or {}).get('metrics') or st.get('metrics') or {}
    corner = (m.get('setup_corner') or 'ss').upper()
    raw_ref = '%s:%s' % (host, raw_remote) if raw_remote else ''
    facts = [dict(k='closure job', v=job, src=rs), dict(k='status', v=(verdict or st).get('status'), src=rs),
             dict(k='source commit', v=((verdict or {}).get('source_commit') or st.get('commit_full') or '')[:12], src=rs),
             dict(k='%s setup WNS (sign-off record)' % corner, v=_num(m.get('ss_ps')), unit='ps', src=rs),
             dict(k='FF hold WNS (sign-off record)', v=_num(m.get('ff_ps')), unit='ps', src=rs),
             dict(k='DRC', v=m.get('drc', 0), src=rs)]
    if m.get('ss_sensitivity_ps') is not None: facts.append(dict(k='SS setup sensitivity', v=_num(m.get('ss_sensitivity_ps')), unit='ps', src=rs))
    if m.get('ss_tns_ps') is not None: facts.append(dict(k='%s setup TNS' % corner, v=_num(m.get('ss_tns_ps')), unit='ps', src=rs))
    if spec.get('cycles_added') is not None: facts.append(dict(k='cycles added (job spec)', v=str(spec.get('cycles_added'))[:300], src=rs))
    if tt:
        stx = tt['stats']
        if not tt.get('nosta'):
            facts += [dict(k='TT setup WNS (this export re-timed)', v=tt.get('worst_slack_ps'), unit='ps', src=raw_ref + '/tt.json'),
                      dict(k='FF hold WNS (this export re-timed)', v=ff and ff.get('worst_slack_ps'), unit='ps', src=raw_ref + '/ff.json')]
        facts += [dict(k='die', v='%.2f x %.2f' % (tt['die']['x1'] - tt['die']['x0'], tt['die']['y1'] - tt['die']['y0']), unit='um', src=raw_ref + '/tt.json'),
                  dict(k='core area', v=stx['core_area_um2'], unit='um2', src=raw_ref + '/tt.json'),
                  dict(k='std-cell area (excl. filler/tap/decap)', v=stx['std_cell_area_um2'], unit='um2', src=raw_ref + '/tt.json'),
                  dict(k='macro area', v=stx['macro_area_um2'], unit='um2', src=raw_ref + '/tt.json'),
                  dict(k='utilisation (std+macro)/core', v=round(100 * (stx['std_cell_area_um2'] + stx['macro_area_um2']) / max(1e-9, stx['core_area_um2']), 1), unit='%', src=raw_ref + '/tt.json'),
                  dict(k='std cells', v=stx['std_cells'], src=raw_ref + '/tt.json'), dict(k='flops', v=stx['flops'], src=raw_ref + '/tt.json'),
                  dict(k='LVT cells', v=round(100.0 * stx['lvt_cells'] / max(1, stx['std_cells']), 2), unit='%', src=raw_ref + '/tt.json'),
                  dict(k='SLVT cells', v=round(100.0 * stx['slvt_cells'] / max(1, stx['std_cells']), 2), unit='%', src=raw_ref + '/tt.json'),
                  dict(k='clock-tree cells', v=stx['clock_tree_cells'], src=raw_ref + '/tt.json'), dict(k='macros', v=len(tt['macros']), src=raw_ref + '/tt.json')]
        if tt.get('power_w'):
            p = tt['power_w']; facts.append(dict(k='power (vectorless, TT)', v=round(p['total'] * 1e3, 1), unit='mW', note=p['basis'], src=raw_ref + '/power_tt.rpt'))
    for x in extra_facts: facts.append(x)
    el = dict(schema='opentallas.explorer_elem.v2', id=element, label=label or element, role=role or reg.get('category'), target=reg.get('target'),
              category=reg.get('category'), summary=summary, note=note, block=spec.get('block') or (tt or {}).get('top'), job=job, host=host, db=db,
              record=rec_ref, exported_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'), facts=facts, layout=bool(tt), nosta=bool(nosta or (tt or {}).get('nosta')),
              bench=dict(spec={k: v for k, v in spec.items() if 'bench' in k.lower()}, stages=(spec.get('stages') or {}).get('bench') or [],
                         state=st.get('benches') or {}), reference=ref, rtl_error=rtl_error)
    if tt:
        el['geom'] = {k: tt[k] for k in ('die', 'core', 'cells', 'masters', 'modules', 'module_cells', 'macros', 'ports', 'grid', 'quantum_dbu', 'dbu_per_um', 'stats')}
        el['geom']['cells']['file'] = '%s.cells.bin' % element
        el.update(clocks=tt.get('clocks'), clock_roots=tt.get('clock_roots'), clock_tt=tt['clock_tree'],
                  clock_wires=tt.get('clock_wires') and dict(tt['clock_wires'], file='%s.clk.bin' % element),
                  clock_ff_leaves=ff and [l[3] for l in ff['clock_tree']['leaves']],
                  clock_ff_match=bool(ff and len(ff['clock_tree']['leaves']) == len(tt['clock_tree']['leaves'])),
                  setup_paths=tt['paths'] if not tt.get('nosta') else [], hold_paths=ff and ff['paths'])
        shutil.copy(raw / 'cells.bin', dest / ('%s.cells.bin' % element))
        if (raw / 'clk.bin').exists(): shutil.copy(raw / 'clk.bin', dest / ('%s.clk.bin' % element))
    if rtl:
        r = json.loads(pathlib.Path(rtl).read_text())
        el['rtl_file'] = '%s.rtl.json' % element
        el['rtl_meta'] = dict(top=r['top'], source_commit=r.get('source_commit'), files=len(r['files']), top_params=r.get('top_params'))
        (dest / el['rtl_file']).write_text(json.dumps(r, separators=(',', ':')))
    tmp = dest / ('%s.json.tmp' % element); tmp.write_text(json.dumps(el, separators=(',', ':'))); os.replace(tmp, dest / ('%s.json' % element))
    update_index(dest, element, dict(block=el['block'], target=el['target'], category=el['category'], job=job, layout=el['layout'],
                                     sta=not el['nosta'], rtl=bool(rtl), reference=(ref or {}).get('path'), exported_at=el['exported_at']))
    return dest / ('%s.json' % element)


def cmd_pack(a):
    st = json.loads((STATE / (a.job + '.json')).read_text()) if (STATE / (a.job + '.json')).exists() else {}
    xf = [json.loads(x) for x in a.extra_fact or []]
    commit = st.get('commit_full') or ((st.get('spec') or {}).get('source') or {}).get('commit')
    ref = find_reference_model(st.get('spec') or {}, st, commit) if git_has(commit) else dict(found=False, seeds=[])
    p = pack(pathlib.Path(a.raw) if a.raw else None, a.element, a.job, a.dest, st, host=a.host, raw_remote=a.raw_remote, db=a.db, rtl=a.rtl,
             ref=ref, reg=dict(target=a.target, category=a.category), label=a.label, role=a.role, summary=a.summary, note=a.note,
             extra_facts=xf, record_ref=a.record_ref)
    print('wrote', p, os.path.getsize(p))


# ------------------------------------------------------------------------------------------------ batch
def closed_registry(url='http://127.0.0.1:8765/api/elements'):
    import urllib.request
    d = json.loads(urllib.request.urlopen(url, timeout=120).read())
    return [r for r in d['rows'] if str(r.get('category', '')).startswith('closed') and (r.get('best') or {}).get('job')]


def cmd_batch(a):
    rows = closed_registry()
    todo = []
    for r in rows:
        job = r['best']['job']
        try: host = json.loads((STATE / (job + '.json')).read_text()).get('host')
        except Exception: continue
        if a.host and host != a.host: continue
        if host in (a.skip_host or '').split(','): continue
        mk = {}
        try: mk = json.loads((MARKS / (job + '.json')).read_text())
        except Exception: pass
        if not a.redo and mk.get('state') == 'done' and (pathlib.Path(a.dest) / (r['element'] + '.json')).exists(): continue
        todo.append((r, job, host))
    if a.only: todo = [t for t in todo if t[0]['element'] in a.only.split(',')]
    if a.limit: todo = todo[:a.limit]
    print('batch: %d of %d closed elements to export' % (len(todo), len(rows)), flush=True)
    sems = {}; lock = threading.Lock()
    def one(t):
        r, job, host = t
        with lock: sem = sems.setdefault(host, threading.Semaphore(a.per_host))
        with sem:
            return auto(job, r['element'], a.dest, dict(target=r.get('target'), category=r.get('category')), log=lambda s: print(time.strftime('%H:%M:%S'), s, flush=True))
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(one, todo))
    print('batch done: %d ok, %d failed' % (sum(1 for x in res if x), sum(1 for x in res if not x)), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    r = sp.add_parser('run'); r.add_argument('--orfs', required=True); r.add_argument('--src', required=True)
    r.add_argument('--out', required=True); r.add_argument('--mem', type=int, default=32); r.add_argument('--threads', type=int, default=8)
    r.add_argument('--npath', type=int, default=40); r.add_argument('--image', default=IMAGE)
    r.add_argument('--tt-tcl'); r.add_argument('--ff-tcl'); r.add_argument('--ss2tt', action='store_true'); r.add_argument('--nosta', action='store_true')
    u = sp.add_parser('auto'); u.add_argument('--job', required=True); u.add_argument('--element'); u.add_argument('--dest', default=str(DEST))
    b = sp.add_parser('batch'); b.add_argument('--dest', default=str(DEST)); b.add_argument('--limit', type=int); b.add_argument('--host'); b.add_argument('--skip-host', default='localhost', help='comma list (default localhost: no heavy work there)')
    b.add_argument('--redo', action='store_true'); b.add_argument('--only'); b.add_argument('--workers', type=int, default=10); b.add_argument('--per-host', type=int, default=2)
    p = sp.add_parser('pack'); p.add_argument('--raw'); p.add_argument('--element', required=True)
    p.add_argument('--job', required=True); p.add_argument('--dest', default=str(DEST)); p.add_argument('--label')
    p.add_argument('--role'); p.add_argument('--summary'); p.add_argument('--host', default='')
    p.add_argument('--raw-remote'); p.add_argument('--db', default=''); p.add_argument('--record-ref'); p.add_argument('--note')
    p.add_argument('--rtl'); p.add_argument('--target'); p.add_argument('--category')
    p.add_argument('--extra-fact', action='append', help='JSON {"k":..,"v":..,"unit":..,"src":..}; repeatable')
    a = ap.parse_args()
    if a.cmd == 'run': sys.exit(cmd_run(a))
    if a.cmd == 'auto':
        ok = auto(a.job, a.element, a.dest)
        sys.exit(0 if ok else 1)
    if a.cmd == 'batch': return cmd_batch(a)
    cmd_pack(a)


if __name__ == '__main__':
    main()
