"""Element activity replay, local orchestration (anim-1011 Phase 1).  Used by tools/explorer_elem_export.py:

    explorer_elem_export.py trace --job <closure job> [--element <id>] [--host H] [--window 256]
    explorer_elem_export.py trace-batch [--only a,b] [--per-host 2]     every exported element without a trace
    (auto: after a successful element export the closure loop's detached post-close export also runs trace)

Everything is derived from the closure job record, the element's exported page data and the source commit:
  bench    A. the job spec's first positive bench stage (stages.bench, expect = pass);
           B. else a repository script named in no_bench_reason with the arguments written after it (argparse flags
              of that script at the source commit; a required --work/--out style argument gets a scratch dir);
           C. else a '<fleet host> <absolute dir>' named in no_bench_reason: a prior bench build there, whose
              Verilator V*__verFiles.dat holds the compile (source commit then UNVERIFIED and labelled so).
  host     C: the named host; else the fleet bench host with the most MemAvailable (never localhost).
  source   <anim>/src/<commit>: a --shared clone of the host's git mirror (commit fetched from the public upstream
           or pushed from here), results/ left out except paths the bench names; copied per job (bench writes).
  element  ports, hierarchy, register nets from <element>.rtl.json; placed flops from <element>.json clock leaves.
Outputs: <host>:<anim>/runs/<job>/out (FST, logs: the raw store) and <dest>/<element>.trace.json (the viewer pack).
Marker: ~/.local/state/viz-elem/<job>.trace.json (running / done / failed, with the reason).
"""
import json, os, pathlib, re, shlex, subprocess, time, traceback

HERE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path(os.environ.get('CL_REPO', HERE.parent.parent))
STATE = pathlib.Path.home() / '.local/state/closure_loop/jobs'
MARKS = pathlib.Path.home() / '.local/state/viz-elem'
DEST = pathlib.Path.home() / '.local/share/fleet-viz/explorer/element/data'
HOSTS_JSON = HERE.parent / 'closure_loop' / 'hosts.json'
BENCH_HOSTS = ('ot-epyc4', 'ot-epyc2', 'ot-epyc1tb', 'ot-epyc3')
VERILATOR = '/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def ssh(host, cmd, inp=None, timeout=600):
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=30', '-o', 'ControlPath=none', host, cmd],
                          input=inp, capture_output=True, text=True, timeout=timeout)


def mark(job, **kw):
    MARKS.mkdir(parents=True, exist_ok=True)
    p = MARKS / (job + '.trace.json')
    d = {}
    try: d = json.loads(p.read_text())
    except Exception: pass
    d.update(kw, updated=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); os.replace(tmp, p)
    return d


def hosts_cfg():
    d = json.loads(HOSTS_JSON.read_text())
    return {h['name']: h for h in d['hosts']}


def anim_base(cfg):
    return str(pathlib.PurePosixPath(cfg['base']).parent / 'anim')


def label(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def git_show(commit, path):
    r = sh(['git', '-C', str(REPO), 'show', '%s:%s' % (commit, path)])
    return r.stdout if r.returncode == 0 else None


# ------------------------------------------------------------------------------------------------ bench resolution
SCRIPT_RE = re.compile(r'\b((?:tools|physical|rtl|scripts)/[\w./-]+\.(?:py|sh))\b')
HOSTDIR_RE = re.compile(r'\b(ot-[\w-]+)[\s:]+(/srv/[\w./-]+|/home/[\w./-]+)')
OUTARG_RE = re.compile(r'(work|out|output|outdir|dir|tmp|scratch|run)', re.I)


def argparse_flags(text):
    """{flag: takes_value} and required flags of a Python argparse script"""
    flags, req = {}, []
    for m in re.finditer(r'add_argument\(([^)]*)\)', text):
        body = m.group(1)
        names = re.findall(r"""['"](--?[\w-]+)['"]""", body)
        if not names: continue
        tv = not re.search(r"action\s*=\s*['\"](store_true|store_false|count|help|version)", body)
        for n in names: flags[n] = tv
        if re.search(r'required\s*=\s*True', body): req.append(max(names, key=len))
    return flags, req


def resolve_bench(st, commit):
    spec = st.get('spec') or {}
    for i, b in enumerate((spec.get('stages') or {}).get('bench') or []):
        if b.get('expect', 'pass') == 'pass' and b.get('cmd'):
            return dict(mode='cmd', cmd=b['cmd'], label='stages.bench[%d] %s' % (i, b.get('name', '')), why='closure job spec bench stage',
                        peak_ram_gb=b.get('peak_ram_gb'), commit_verified=True)
    txt = spec.get('no_bench_reason') or ''
    m = SCRIPT_RE.search(txt)
    if m and git_show(commit, m.group(1)) is not None:
        path = m.group(1); src = git_show(commit, path)
        toks = txt[m.end():].split()
        args = []
        if path.endswith('.py'):
            flags, req = argparse_flags(src)
            i = 0
            while i < len(toks):
                t = toks[i].rstrip(',;)')
                f = t.split('=', 1)[0]
                if f not in flags: break
                args.append(t)
                if flags[f] and '=' not in t and i + 1 < len(toks): args.append(toks[i + 1].rstrip(',;)')); i += 2
                else: i += 1
            have = {a.split('=', 1)[0] for a in args}
            for r in req:
                if r in have: continue
                if OUTARG_RE.search(r): args += [r, '{RUN}/bench_' + r.strip('-').replace('-', '_')]
                else: return dict(mode=None, why='no_bench_reason names %s but its required %s is not given' % (path, r))
            cmd = 'python3 ' + path + ' ' + ' '.join(shlex.quote(a) for a in args)
        else:
            cmd = 'bash ' + path + ' ' + ' '.join(shlex.quote(t) for t in toks[:0])
        return dict(mode='cmd', cmd=cmd.strip(), label='no_bench_reason: ' + cmd.strip(), why=txt[:300], commit_verified=True)
    m = HOSTDIR_RE.search(txt)
    if m:
        return dict(mode='workdir', host=m.group(1), workdir=m.group(2).rstrip('.'), label='prior bench build %s:%s' % (m.group(1), m.group(2)),
                    why=txt[:300], commit_verified=False)
    return dict(mode=None, why='no positive bench stage, and no_bench_reason names neither a repository script nor a host directory')


# ------------------------------------------------------------------------------------------------ element data
def element_inputs(eid, dest):
    el = json.loads((dest / (eid + '.json')).read_text())
    rp = dest / (el.get('rtl_file') or (eid + '.rtl.json'))
    if not rp.exists(): raise RuntimeError('no RTL export (%s): run the element export first' % rp.name)
    rtl = json.loads(rp.read_text())
    top = rtl['modules'][rtl['tree']['k']]
    leaves = ((el.get('clock_tt') or {}).get('leaves')) or []
    flops = [l[4] if not l[5] else '' for l in leaves]

    def strip(nd):
        return dict(p=nd.get('p', ''), k=nd.get('k'), c=[strip(c) for c in nd.get('c') or []])
    return dict(el=el, ports=top['ports'], top=rtl['top'], top_params=rtl.get('top_params') or [], tree=strip(rtl['tree']),
                modules={k: m.get('nets') or {} for k, m in rtl['modules'].items()}, flops=flops,
                clock_port=(el.get('clock_roots') or [None])[0])


# ------------------------------------------------------------------------------------------------ host side helpers
SRC_SH = r'''
set -u
B=%(base)s; M=%(mirror)s; C=%(commit)s; S=$B/src/$C
mkdir -p $B/src
exec 9>$B/src/.lock; flock 9
if [ ! -f $S/.anim_ready ]; then
  if ! git -C $M cat-file -e $C^{commit} 2>/dev/null; then
    timeout 600 git -C $M fetch -q %(upstream)s $C 2>/dev/null || { echo NEED_PUSH; exit 11; }
  fi
  rm -rf $S; git clone -q --shared --no-checkout $M $S || exit 12
  git -C $S sparse-checkout set --no-cone '/*' '!/results/' %(keep)s || exit 13
  git -C $S checkout -q --detach $C || exit 14
  echo $C > $S/SOURCE_COMMIT; touch $S/.anim_ready
fi
echo SRC_READY
'''
CELLS_SH = r'''
set -u
B=%(base)s; mkdir -p $B/cells; exec 9>$B/cells/.lock; flock 9
if [ ! -s $B/cells/cells_tt.v ] || [ $B/bin/lib2v.py -nt $B/cells/cells_tt.v ]; then
  ls $B/cells/*TT*.lib* >/dev/null 2>&1 || docker run --rm --user $(id -u):$(id -g) -v $B/cells:/out %(image)s bash -c \
     'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_TT_* /out/' || exit 16
  python3 $B/bin/lib2v.py --out $B/cells/cells_tt.v.tmp --kinds $B/cells/kinds.json $(ls $B/cells/*_TT_*.lib* | grep -v SRAM) || exit 17
  mv $B/cells/cells_tt.v.tmp $B/cells/cells_tt.v
fi
echo CELLS_READY
'''
FSTX_SH = r'''
set -u
B=%(base)s; mkdir -p $B/bin; exec 9>$B/bin/.lock; flock 9
if [ ! -x $B/bin/fstx ] || [ $B/bin/fstx.c -nt $B/bin/fstx ]; then
  G=/usr/share/verilator/include/gtkwave
  gcc -O2 -w -DFST_CONFIG_INCLUDE='"fst_config.h"' -I$G -o $B/bin/fstx $B/bin/fstx.c $G/fstapi.c $G/fastlz.c $G/lz4.c -lz -lpthread || exit 15
fi
echo FSTX_READY
'''


def prepare_host(host, cfg, commit, keep):
    base = anim_base(cfg)
    for name, mode in (('fstx.c', 'cmp'), ('trace_bench.py', 'cat'), ('lib2v.py', 'cat')):
        r = ssh(host, 'mkdir -p {b}/bin && cat > {b}/bin/{n}.new && (cmp -s {b}/bin/{n}.new {b}/bin/{n} && rm {b}/bin/{n}.new || mv {b}/bin/{n}.new {b}/bin/{n})'
                .format(b=base, n=name), inp=(HERE / name).read_text())
        if r.returncode: raise RuntimeError('ship %s: %s' % (name, r.stderr[-300:]))
    r = ssh(host, FSTX_SH % dict(base=base), timeout=900)
    if 'FSTX_READY' not in r.stdout: raise RuntimeError('fstx build on %s: %s' % (host, (r.stdout + r.stderr)[-300:]))
    r = ssh(host, CELLS_SH % dict(base=base, image='openroad/orfs:asap7lock'), timeout=1800)
    if 'CELLS_READY' not in r.stdout: raise RuntimeError('cell models on %s: %s' % (host, (r.stdout + r.stderr)[-300:]))
    if commit is None: return base
    args = dict(base=base, mirror=cfg['git_mirror'], commit=commit, upstream=shlex.quote(cfg.get('git_mirror_upstream') or 'origin'),
                keep=' '.join(shlex.quote('/' + k) for k in keep))
    r = ssh(host, SRC_SH % args, timeout=3600)
    if 'NEED_PUSH' in r.stdout:   # the commit is not on the public upstream: push it into the mirror (delta only)
        p = sh(['git', '-C', str(REPO), 'push', '-q', '%s:%s' % (host, cfg['git_mirror']), '%s:refs/anim/%s' % (commit, commit)], timeout=3600)
        if p.returncode: raise RuntimeError('push %s to %s mirror: %s' % (commit[:10], host, p.stderr[-300:]))
        r = ssh(host, SRC_SH % args, timeout=3600)
    if 'SRC_READY' not in r.stdout: raise RuntimeError('source tree on %s: rc %d %s' % (host, r.returncode, (r.stdout + r.stderr)[-400:]))
    return base


def pick_host(cfgs):
    """the bench host with a free big ot-heavy slot (gate-level builds need one), then the most MemAvailable"""
    best = None
    for h in BENCH_HOSTS:
        if h not in cfgs or not cfgs[h].get('git_mirror'): continue
        r = ssh(h, "awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo; n=0; for f in /var/tmp/ot-heavy/big.*.lock; do "
                   "flock -n $f true && n=$((n+1)); done; echo $n", timeout=60)
        try: av, free = [int(x) for x in r.stdout.split()[:2]]
        except ValueError: continue
        key = (free > 0, av)
        if best is None or key > best[1]: best = (h, key)
    if not best: raise RuntimeError('no reachable bench host')
    return best[0]


# ------------------------------------------------------------------------------------------------ one element
def trace(job, element=None, dest=DEST, host=None, window=256, log=print):
    try:
        return _trace(job, element, pathlib.Path(dest), host, window, log)
    except Exception as e:
        mark(job, state='failed', error=('%s: %s' % (type(e).__name__, e))[:600], trace=traceback.format_exc()[-1500:])
        log('%s trace FAILED %s' % (job, e))
        return False


def _trace(job, element, dest, host, window, log):
    st = json.loads((STATE / (job + '.json')).read_text())
    spec = st['spec']
    eid = element or spec.get('block') or job
    commit = st.get('commit_full') or (spec.get('source') or {}).get('commit')
    mark(job, state='running', element=eid, started=time.strftime('%Y-%m-%dT%H:%M:%S%z'), error=None)
    bench = resolve_bench(st, commit)
    if not bench.get('mode'): raise RuntimeError('NO_BENCH: ' + bench['why'])
    E = element_inputs(eid, dest)
    cfgs = hosts_cfg()
    dbh = (E['el'].get('db') or '').split(':', 1)[0]
    host = host or (bench.get('host') if bench['mode'] == 'workdir' else None) or pick_host(cfgs)
    cfg = cfgs.get(host)
    if not cfg: raise RuntimeError('host %s not in hosts.json' % host)
    keep = sorted({p for p in re.findall(r'\bresults/[\w./-]+', bench.get('cmd') or '')})
    base = prepare_host(host, cfg, commit if bench['mode'] == 'cmd' else None, keep)
    run = '%s/runs/%s' % (base, job)
    nflop = sum(1 for f in E['flops'] if f)
    s = dict(job=job, element=eid, block=spec.get('block') or E['top'], commit=commit, window=window, clock_port=E['clock_port'],
             top_params=E['top_params'], ports=E['ports'], flops=E['flops'], tree=E['tree'], modules=E['modules'],
             verilator=VERILATOR, fstx=base + '/bin/fstx', jobs=16,
             mem_gb=int(max(16, bench.get('peak_ram_gb') or 0, 48 if nflop > 30000 else 24)), capture_mem_gb=31, build_mem_gb=96 if nflop > 30000 else 48)
    db = (E['el'].get('db') or '').split(' ')[0]
    if ':' not in db: raise RuntimeError('element pack names no routed DB')
    dbhost, dbpath = db.split(':', 1)
    nlsrc = dbpath.rsplit('/', 1)[0] + '/6_final.v'
    s.update(netlist=run + '/6_final.v', netlist_ref='%s:%s' % (dbhost, nlsrc), cell_models=base + '/cells/cells_tt.v',
             cell_kinds=base + '/cells/kinds.json', cell_models_ref='tools/explorer_elem/lib2v.py from the ORFS ASAP7 TT NLDM liberty',
             clock_ps=float((E['el'].get('clocks') or [None, 0])[1] or 0) or None, gate_mem_gb=200 if nflop > 30000 else 64, cap=8192)
    if bench['mode'] == 'cmd':
        m = dict(RUN=run, SRC=run + '/src', CL=run + '/cl', HOST=host, NAME=label(job), LABEL=label(job), RAW_NAME=job,
                 BLOCK=spec.get('block', ''), COMMIT=commit, THREADS=str(spec.get('threads', 16)))
        cmd = bench['cmd'].replace('{RUN}/src', '{SRC}')
        for k, v in m.items(): cmd = cmd.replace('{' + k + '}', v)
        bench = dict(bench, cmd=cmd, cwd=run + '/src')
        s['src'] = run + '/src'
    s['bench'] = bench
    log('%s: bench %s on %s' % (job, bench['label'][:160], host))
    prep = ('rm -rf %(r)s && mkdir -p %(r)s/cl %(r)s/out && ' % dict(r=run)) + (
        'cp -a --reflink=auto %s/src/%s %s/src && ' % (base, commit, run) if bench['mode'] == 'cmd' else '') + 'cat > %s/spec.json' % run
    r = ssh(host, prep, inp=json.dumps(s), timeout=1800)
    if r.returncode: raise RuntimeError('job dir: ' + r.stderr[-300:])
    if bench['mode'] == 'workdir' and bench['host'] != host:   # the prior bench directory, without its builds
        wd = bench['workdir']
        r = subprocess.run('ssh -o BatchMode=yes %s "tar -C %s --exclude=\'obj_*\' --exclude=\'*/obj_*\' -cf - ." | ssh -o BatchMode=yes %s "mkdir -p %s/workdir_src && tar -C %s/workdir_src -xf -"'
                           % (bench['host'], shlex.quote(wd), host, run, run), shell=True, capture_output=True, text=True, timeout=7200)
        if r.returncode: raise RuntimeError('workdir copy: ' + r.stderr[-300:])
        # absolute inputs the prior compile names outside its directory (e.g. a shared DPI .cpp)
        r = subprocess.run('ssh -o BatchMode=yes %s "grep -h \'^C \' $(find %s -name \'V*__verFiles.dat\' | head -20) | grep -o \'/[^ \\\"]*\' | sort -u | '
                           'while read f; do [ -f \$f ] && echo \$f; done | grep -v \'^%s/\' | tar -cPf - -T -" | ssh -o BatchMode=yes %s "mkdir -p %s/absfiles && tar -C %s/absfiles -xf -"'
                           % (bench['host'], shlex.quote(wd), wd.rstrip('/'), host, run, run), shell=True, capture_output=True, text=True, timeout=3600)
        s['bench'] = dict(bench, workdir=run + '/workdir_src', origin='%s:%s' % (bench['host'], wd), absroot=run + '/absfiles', prior_root=wd)
        r = ssh(host, 'cat > %s/spec.json' % run, inp=json.dumps(s), timeout=600)
    if dbhost == host:
        r = ssh(host, 'cp %s %s/6_final.v' % (shlex.quote(nlsrc), run), timeout=1800)
    else:
        r = subprocess.run(['scp', '-3', '-q', '-o', 'BatchMode=yes', '%s:%s' % (dbhost, nlsrc), '%s:%s/6_final.v' % (host, run)], capture_output=True, text=True, timeout=7200)
    if r.returncode: raise RuntimeError('netlist copy %s -> %s: %s' % (dbhost, host, r.stderr[-300:]))
    t = time.time()
    r = ssh(host, 'cd %s && nice -n 10 python3 %s/bin/trace_bench.py --spec spec.json --out %s/out > %s/out/driver.log 2>&1; rc=$?; '
                  'rm -rf %s/out/obj_rtl %s/out/obj_gate %s/src %s/out/netlist_gl.v %s/6_final.v; echo RC=$rc; tail -3 %s/out/driver.log' % (run, base, run, run, run, run, run, run, run, run), timeout=12 * 3600)
    rc = re.search(r'RC=(\d+)', r.stdout)
    if not rc or rc.group(1) != '0':
        raise RuntimeError('trace_bench rc %s on %s: %s' % (rc and rc.group(1), host, r.stdout[-500:]))
    dest.mkdir(parents=True, exist_ok=True)
    tmp = dest / ('.%s.trace.json.tmp' % eid)
    p = subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', '%s:%s/out/elem_trace.json' % (host, run), str(tmp)], capture_output=True, text=True)
    if p.returncode: raise RuntimeError('fetch: ' + p.stderr[-200:])
    d = json.loads(tmp.read_text())
    d['provenance']['raw_store'] = '%s:%s/out' % (host, run)
    cdir = dest / ('%s.trace' % eid); cdir.mkdir(exist_ok=True)
    p = subprocess.run(['rsync', '-a', '--delete', '-e', 'ssh -o BatchMode=yes', '%s:%s/out/chunks/' % (host, run), str(cdir) + '/'], capture_output=True, text=True)
    if p.returncode: raise RuntimeError('fetch chunks: ' + p.stderr[-200:])
    d['state']['dir'] = '%s.trace' % eid
    tmp.write_text(json.dumps(d, separators=(',', ':')))
    os.replace(tmp, dest / ('%s.trace.json' % eid))
    size = (dest / ('%s.trace.json' % eid)).stat().st_size
    mark(job, state='done', element=eid, host=host, bytes=size, chunk_bytes=d['state']['bytes'], cycles=d['window']['cycles'],
         exact=d['exactness']['pass'], wall_s=round(time.time() - t), error=None)
    log('%s -> %s.trace.json %d B + chunks %d B / %d cycles (%d B per 1000), exact %s, %d s' % (
        job, eid, size, d['state']['bytes'], d['window']['cycles'], d['state']['bytes_per_1000_cycles'], d['exactness']['pass'], time.time() - t))
    return True
