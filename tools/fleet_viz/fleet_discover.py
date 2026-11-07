#!/usr/bin/env python3
"""Fleet membership for the monitors (MONITOR-FIX 2026-11-06).

fleet_hosts.json carries curated metadata (labels, CPU text, regions); the ot-run HOSTS list on the hub is the list of hosts
that actually run work.  A host in ot-run HOSTS but not in fleet_hosts.json used to be invisible (epyc5/epyc6 for a day):
it now appears by itself, as an entry in <state>/fleet_hosts_auto.json with its CPU text probed over ssh.  Additive only:
retiring a host is still done by deleting it from fleet_hosts.json (or the auto file); a failed read changes nothing.
"""
import ast, json, os, pathlib, re, subprocess

HUB = os.environ.get('FLEET_HUB', 'intel2')
HERE = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
AUTO = STATE / 'fleet_hosts_auto.json'
SSH = ['ssh', '-n', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ControlPath=none']
# ~/.local/bin/ot-run is a wrapper that execs the released script (or, in older installs, the script itself)
READ_HOSTS = (r'''f=$HOME/.local/bin/ot-run; g=$(sed -n 's/^exec .*python3 \(.*ot-run\) .*/\1/p' "$f"); '''
              r'''grep -m1 '^HOSTS = ' "${g:-$f}"''')
PROBE = "lscpu | sed -n 's/^Model name: *//p' | head -1; lscpu | sed -n 's/^Socket(s): *//p'; nproc; sed -n 's/^MemTotal: *\\([0-9]*\\).*/\\1/p' /proc/meminfo"


def parse_hosts_line(line):
    """'HOSTS = ["a", "b"]   # comment' -> ['a', 'b'], None when it is not such a line"""
    m = re.match(r'\s*HOSTS\s*=\s*(\[[^\]]*\])', line or '')
    if not m: return None
    try: v = ast.literal_eval(m.group(1))
    except (ValueError, SyntaxError): return None
    return v if isinstance(v, list) and all(isinstance(x, str) for x in v) else None


def read_shared_hosts(hub=HUB, timeout=30):
    """ot-run HOSTS as the hub sees it ('localhost' there = the hub), or None when it cannot be read"""
    try: p = subprocess.run(SSH + [hub, READ_HOSTS], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError): return None
    v = parse_hosts_line(p.stdout) if p.returncode == 0 else None
    return None if v is None else [hub if h == 'localhost' else h for h in v]


def missing_hosts(cfg_hosts, shared):
    known = {h['id'] for h in cfg_hosts} | {h['ssh'] for h in cfg_hosts if h.get('ssh')}
    return [h for h in shared if h not in known]


def kind_text(probe_out):
    """'AMD EPYC 9554P 64-Core Processor\\n1\\n128\\n791870488' -> '1x EPYC 9554P (128T, 755 GB)'"""
    f = (probe_out or '').strip().splitlines()
    if len(f) < 4: return 'fleet host'
    cpu = re.sub(r'\(R\)|\(TM\)|CPU|@.*|\d+-Core Processor|Processor', '', f[0]).split()
    cpu = [w for w in cpu if w not in ('AMD', 'Intel')]
    try: return '%sx %s (%sT, %d GB)' % (int(f[1]), ' '.join(cpu), int(f[2]), round(int(f[3]) / 1048576))
    except ValueError: return 'fleet host'


def auto_entry(host, probe_out):
    return dict(id=host, name=host.upper(), ssh=host, label=host.upper(), kind=kind_text(probe_out), region='unknown', auto=True)


def read_auto(path=AUTO):
    try: v = json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError): return []
    return v if isinstance(v, list) else []


def load_hosts(cfg_hosts, path=AUTO):
    """fleet_hosts.json entries + discovered ones (a host later curated in fleet_hosts.json wins)"""
    ids = {h['id'] for h in cfg_hosts}
    return list(cfg_hosts) + [h for h in read_auto(path) if h.get('id') and h['id'] not in ids]


def config_hosts(cfg_path=None, auto_path=AUTO):
    """all hosts for a reader outside the server (the :8090 collector, plan_now.py)"""
    p = pathlib.Path(cfg_path or os.environ.get('FLEET_VIZ_HOSTS', HERE / 'fleet_hosts.json'))
    return load_hosts(json.loads(p.read_text())['hosts'], auto_path)


def discover(cfg_hosts, path=AUTO, hub=HUB, reader=read_shared_hosts, prober=None):
    """Add hosts of the shared list missing from cfg_hosts to the auto file; returns the ones added (written first)."""
    shared = reader(hub)
    if not shared: return []
    new = missing_hosts(cfg_hosts, shared)
    if not new: return []
    prober = prober or _probe
    auto = read_auto(path) + [auto_entry(h, prober(h)) for h in new]
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(auto, indent=1)); tmp.replace(path)
    return new


def _probe(host):
    try: return subprocess.run(SSH + [host, PROBE], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError): return ''
