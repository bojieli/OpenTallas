#!/usr/bin/env python3
"""RESULT-WATCH-1: no-LLM watcher (intel2, every 10 min). Reads lanes/RESULT-WATCH.tsv and posts one RESULT-WATCH
line per newly terminal row to COORD-REVIEW-QUEUE.md (via bin/post.sh -> coord-commit.sh).

TSV (tab separated, '#' comment lines): lane  host  kit_dir  [opts]
  opts = ';'-separated key=value, all optional:
    client_log=<path on intel2>   ot-run client log; its last "ot-run: RAN ... exit N" line is reported
    log=<path on host>;done=<ERE> log-driven row (e.g. G0): terminal only when `grep -E done log` matches
    match=<substring>             process/container match instead of kit_dir
Terminal states (checked per row each run):
  signoff.json under kit_dir (find -maxdepth 8)  -> DRC, TT setup wns, FF hold wns, verdict
  result.json under kit_dir (maxdepth 4)
  log-done pattern (rows with done=)
  process gone: no process cmdline and no docker mount mentioning kit_dir (2 consecutive polls)
State: ~/.local/state/result-watch.json (rows already reported). A row stays reported until it is removed
from the TSV and re-added, or its kit_dir/opts text changes.
"""
import json, os, re, subprocess, sys, time, shlex
HOME = os.path.expanduser('~')
TSV = os.environ.get('RW_TSV') or os.path.join(HOME, 'coord/lanes/RESULT-WATCH.tsv')
STATE = os.environ.get('RW_STATE') or os.path.join(HOME, '.local/state/result-watch.json')
POST = os.path.join(HOME, 'coord/bin/post.sh')
LANE = 'RESULT-WATCH-1'
DRY = '--dry' in sys.argv

PROBE = r'''
K=__K__; M=__M__; LOG=__LOG__; DONE=__DONE__
if [ -n "$DONE" ]; then
  [ -n "$LOG" ] && [ -f "$LOG" ] && l=$(grep -E -- "$DONE" "$LOG" | tail -1) && echo "LOGDONE=$l"
  echo "LOGMTIME=$(stat -c %y "$LOG" 2>/dev/null)"
  exit 0
fi
[ -d "$K" ] || echo "NODIR=1"
s=$(find "$K" -maxdepth 8 -name signoff.json -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
[ -n "$s" ] && echo "SIGNOFF=$s"
r=$(find "$K" -maxdepth 4 -name result.json -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
[ -n "$r" ] && echo "RESULT=$r"
n=$(ps -eo args | grep -F -- "$M" | grep -v -e grep -e 'bash -s' | wc -l)
d=0
if command -v docker >/dev/null 2>&1; then
  for c in $(docker ps -q 2>/dev/null); do
    docker inspect "$c" --format '{{range .Mounts}}{{.Source}} {{end}}' 2>/dev/null | grep -qF -- "$M" && d=$((d+1))
  done
fi
echo "ALIVE=$((n+d))"
'''

def q(s): return shlex.quote(s)

def run_host(host, script, timeout=90):
    if host in ('intel2', 'localhost', os.uname().nodename):
        cmd = ['bash', '-s']
    else:
        cmd = ['ssh', '-n', '-o', 'ControlPath=none', '-o', 'ConnectTimeout=15', '-o', 'BatchMode=yes', host, 'bash -s']
    try:
        if cmd[0] == 'ssh':
            # ssh -n would drop stdin; use stdin variant
            cmd = [c for c in cmd if c != '-n']
        p = subprocess.run(cmd, input=script, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None
    if p.returncode != 0 and not p.stdout:
        return None
    return p.stdout

def cat_host(host, path, timeout=60):
    return run_host(host, 'cat %s\n' % q(path), timeout)

def parse_signoff(host, path):
    t = cat_host(host, path)
    try:
        d = json.loads(t)
    except Exception:
        return 'signoff.json unreadable'
    c = d.get('checks', {})
    drc = d.get('route', {}).get('drc')
    st = c.get('setup_tt', {}); hf = c.get('hold_ff', {})
    return 'DRC %s, TT setup wns %s ps (%s), FF hold wns %s ps (%s), verdict %s' % (
        drc, st.get('wns_ps'), st.get('verdict'), hf.get('wns_ps'), hf.get('verdict'), d.get('verdict'))

def load_rows():
    rows = []
    try:
        for ln in open(TSV):
            ln = ln.rstrip('\n')
            if not ln.strip() or ln.lstrip().startswith('#'):
                continue
            f = ln.split('\t')
            if len(f) < 3:
                continue
            opts = {}
            if len(f) > 3:
                for kv in f[3].split(';'):
                    if '=' in kv:
                        k, v = kv.split('=', 1); opts[k.strip()] = v.strip()
            rows.append(dict(lane=f[0].strip(), host=f[1].strip(), kit=f[2].strip(), opts=opts, raw='\t'.join(f[:4])))
    except FileNotFoundError:
        pass
    return rows

def ran_line(clog):
    if not clog: return ''
    try:
        l = [x for x in open(os.path.expanduser(clog), errors='replace') if 'ot-run: RAN' in x]
        return l[-1].strip()[:160] if l else ''
    except Exception:
        return ''

def main():
    try: state = json.load(open(STATE))
    except Exception: state = {}
    rows = load_rows()
    keys = set()
    posts = []
    for r in rows:
        key = r['raw']
        keys.add(key)
        st = state.get(key, {})
        if st.get('reported'):
            continue
        o = r['opts']
        script = PROBE.replace('__K__', q(r['kit'])).replace('__M__', q(o.get('match', r['kit']))) \
            .replace('__LOG__', q(o.get('log', ''))).replace('__DONE__', q(o.get('done', '')))
        out = run_host(r['host'], script)
        if out is None:
            continue  # host unreachable: no state change
        kv = {}
        for ln in out.splitlines():
            if '=' in ln:
                k, v = ln.split('=', 1); kv[k] = v
        why = None
        if 'done' in o:
            if kv.get('LOGDONE'):
                why = 'log done: ' + kv['LOGDONE'][:200]
        elif kv.get('SIGNOFF'):
            why = 'signoff.json %s: %s' % (kv['SIGNOFF'], parse_signoff(r['host'], kv['SIGNOFF']))
        elif kv.get('RESULT'):
            why = 'result.json %s' % kv['RESULT']
        else:
            alive = int(kv.get('ALIVE', '1') or 1)
            if alive == 0:
                st['dead_polls'] = st.get('dead_polls', 0) + 1
                if st['dead_polls'] >= 2:
                    why = 'process gone (no signoff.json/result.json)%s' % (' [no kit dir]' if kv.get('NODIR') else '')
                    rl = ran_line(o.get('client_log'))
                    if rl: why += '; client: ' + rl
            else:
                st['dead_polls'] = 0
        state[key] = st
        if why:
            st['reported'] = time.strftime('%F %T')
            posts.append('RESULT-WATCH [%s -> %s] %s on %s: %s' % (LANE, r['lane'], r['kit'].rstrip('/').split('/claude/')[-1], r['host'], why))
    for k in list(state):
        if k not in keys: del state[k]
    if not DRY:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(state, open(STATE, 'w'))
    for p in posts:
        print(p)
        if not DRY:
            subprocess.run(['/bin/bash', POST, LANE, p], timeout=900)
    print('rows=%d newly_terminal=%d' % (len(rows), len(posts)))

if __name__ == '__main__':
    main()
