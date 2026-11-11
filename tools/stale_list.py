#!/usr/bin/env python3
"""WAVE-OPS-1 11-10 (OWNER 11-10 'yes to all 5', item A): STALE list for the hourly BREAKDOWN block.

STALE = an unsigned hard core or type of the five current plans (PLANS in release_tree_plan.py, read from the plan
cache) with
  - no live job: no RUNNING/LAUNCHING kit-wave record (hub kit_wave_state.json), no OWNERS.tsv live_job, and no
    process (ps args, systemd --user units on the hub) or docker container (name + mount sources) on any fleet host
    naming the item; and
  - no kit-wave row change (kit_wave_stages.tsv 'updated', any plan_current) for >= STALE_H hours (or no row at all).
Each line carries the last row (status / stage / class), its time and the owner from OWNERS.tsv ('unowned' when
OWNERS has no row).  Read-only: it never launches, kills or deletes anything.  A host that does not answer is named in
the header (its jobs cannot be seen, so a listed item may be live there).
"""
import csv, json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor

COORD = os.path.expanduser('~/coord')
OWNERS = os.path.join(COORD, 'autopilot/OWNERS.tsv')
HOSTS_TSV = os.path.join(COORD, 'tools/fleet_hosts.tsv')
STALE_TSV = os.path.join(COORD, 'lanes/STALE.tsv')
STALE_H = 6.0
HUB = 'intel2'
HUB_STATE = 'coord/autopilot/kit_wave_state.json'          # relative to the hub home
LOCAL_STATE = os.path.join(COORD, 'autopilot/kit_wave_state.json')
LIVE_WAVE = ('RUNNING', 'LAUNCHING')

# One remote probe per host: every path-like token of every process (ps args, which also covers the hub's
# systemd-run ap-*/kw-* units and every ot-run client), the systemd --user unit names, and every container's name +
# mount sources + working dir.  Tokens only (the base64 admission blobs are dropped by the '/' filter).
PROBE = (r"""{ ps -eo args= ; systemctl --user list-units --no-legend --plain --state=running 2>/dev/null | """
         r"""awk '{print $1}'; docker ps -q 2>/dev/null | xargs -r docker inspect --format """
         r"""'{{.Name}} {{range .Mounts}}{{.Source}} {{end}}{{.Config.WorkingDir}}' 2>/dev/null; } | tr ' "=' '\n\n\n' | """
         r"""grep -E '/|^(ap|kw)-' | sort -u""")


def ts(s):
    """'YYYY-mm-dd HH:MM' (local time, as kit_wave_stages.tsv writes it) -> epoch s, None when unparsable"""
    try:
        return time.mktime(time.strptime((s or '').strip()[:16], '%Y-%m-%d %H:%M'))
    except ValueError:
        return None


class Tokens:
    """name tokens ([A-Za-z0-9_]+) of the live text.  hit(item): the item as a whole token, or a token '<item>__...'
    (its classes and core views); 'x__t4' never matches 'x__t45' nor 'x__t4_b'"""
    def __init__(self, text):
        self.set = set(re.findall(r'[A-Za-z0-9_]+', text or ''))
        self.pre = {}
        for t in self.set:
            i = t.find('__')
            while i > 0:
                self.pre.setdefault(t[:i], True)
                i = t.find('__', i + 2)

    def hit(self, item):
        return item in self.set or item in self.pre


def fleet_hosts(path=HOSTS_TSV):
    out = []
    try:
        for l in open(path):
            if l.strip() and not l.startswith('#'):
                out.append(l.split('\t')[0].strip())
    except OSError:
        pass
    return out


def probe_host(h, timeout=60):
    cmd = ['bash', '-c', PROBE] if h == 'localhost' else \
        ['timeout', str(timeout), 'ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', h, PROBE]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    except (subprocess.TimeoutExpired, OSError):
        return h, None
    if p.returncode not in (0, 1) or (not p.stdout and p.returncode):
        return h, None
    return h, p.stdout


def live_text(hosts=None):
    """-> (joined token text of all answering hosts, [unreachable hosts])"""
    hosts = list(hosts if hosts is not None else ['localhost'] + fleet_hosts())
    with ThreadPoolExecutor(max(1, len(hosts))) as ex:
        res = list(ex.map(probe_host, hosts))
    return '\n'.join(t for _, t in res if t), [h for h, t in res if t is None]


def hub_state(hub=HUB):
    """the hub's kit_wave_state.json (the local copy is not synced); the local copy when the hub does not answer"""
    try:
        p = subprocess.run(['timeout', '90', 'ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', hub,
                            'cat ' + HUB_STATE], capture_output=True, text=True, timeout=100)
        if p.returncode == 0 and p.stdout:
            return json.loads(p.stdout), 'hub'
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass
    try:
        return json.load(open(LOCAL_STATE)), 'local copy %s' % time.strftime(
            '%m-%d %H:%M', time.localtime(os.path.getmtime(LOCAL_STATE)))
    except (OSError, ValueError):
        return {}, 'none'


def owners_rows(path=OWNERS):
    try:
        lines = [l for l in open(path) if l.strip() and not l.startswith('#')]     # line 1 is a '# OWNERS --' stamp
        return {(r['die'], r['item']): r for r in csv.DictReader(lines, delimiter='\t')}
    except (OSError, KeyError):
        return {}


def base_names(name, design=None):
    """names under which the wave / OWNERS may know a plan item: itself, its module, its wave keys, and its parent type
    without the class suffix"""
    out = [name]
    m = name.split('#')[0]
    out.append(m)
    out += list((design or {}).get('wave_keys') or [])
    if design and design.get('module'):
        out.append(design['module'])
    out.append(re.sub(r'__cl[0-9a-f]{6,}$', '', m))
    out.append(re.sub(r'__v[0-9a-f]{12}$', '', m))
    seen, res = set(), []
    for x in out:
        if x and x not in seen:
            seen.add(x); res.append(x)
    return res


def row_index(rows):
    """(die, item) -> rows sorted by 'updated' (all plan_current values: any row change counts as activity)"""
    idx = {}
    for r in rows:
        idx.setdefault((r['die'], r['item']), []).append(r)
    for v in idx.values():
        v.sort(key=lambda r: r.get('updated', ''))
    return idx


def item_rows(idx, die, names, prefix_ok=True, all_items=None):
    """every kit-wave row of a plan item: exact names, plus its classes / core views (<name>__...)"""
    got = []
    for n in names:
        got += idx.get((die, n), [])
    if prefix_ok:
        keys = all_items.get(die, ()) if all_items is not None else [k for d, k in idx if d == die]
        for n in names[:1]:
            for k in keys:
                if k.startswith(n + '__') and k not in names:
                    got += idx[(die, k)]
    return sorted(got, key=lambda r: r.get('updated', ''))


def wave_live(state):
    """{(die, item)} with a RUNNING/LAUNCHING kit-wave record (item and parent_item)"""
    out = set()
    for r in (state.get('items') or {}).values():
        if r.get('status') in LIVE_WAVE:
            out.add((r.get('die'), r.get('item')))
            if r.get('parent_item') not in (None, '', 'None'):
                out.add((r.get('die'), r.get('parent_item')))
    return out


def owner_of(own, die, names):
    for n in names:
        r = own.get((die, n))
        if r:
            return r
    return None


def stale_items(cache, rows, own, state, text, dies, now=None, stale_h=STALE_H, plan_die=None):
    """-> [dict(die, tag, kind, item, last_status, last_stage, last_class, last_time, age_h, owner)], pure"""
    now = now or time.time()
    idx = row_index(rows)
    all_items = {}
    for d, k in idx:
        all_items.setdefault(d, []).append(k)
    wl = wave_live(state)
    tok = Tokens(text) if text else None
    out = []
    for die, tag in dies:
        plan = next((p for k, p in cache['plans'].items() if (plan_die or {}).get(k.split('/')[0], k.split('/')[0]) == die), None)
        if not plan:
            continue
        items = []
        sd = set(plan.get('signed_designs') or {})
        for did, d in (plan.get('designs') or {}).items():
            if did not in sd:
                items.append(('core', did, d))
        st = set(plan.get('signed_types') or {})
        pt = plan.get('plan_types') or {}
        for t in (pt if not isinstance(pt, int) else {}):
            if t not in st:
                items.append(('type', t, None))
        for kind, name, d in items:
            names = base_names(name, d)
            if any((die, n) in wl for n in names):
                continue
            o = owner_of(own, die, names)
            if o and o.get('live_job', 'none') not in ('', 'none'):
                continue
            if tok and any(tok.hit(n) for n in names[:2] + list((d or {}).get('wave_keys') or [])):
                continue
            rs = item_rows(idx, die, names, all_items=all_items)
            last = rs[-1] if rs else None
            t = ts(last['updated']) if last else None
            if t is not None and now - t < stale_h * 3600:
                continue
            out.append(dict(die=die, tag=tag, kind=kind, item=name.split('#')[0] if kind == 'type' else name,
                            last_item=(last or {}).get('item', ''),
                            last_status=(last or {}).get('status', 'no kit-wave row'),
                            last_stage=(last or {}).get('stage', ''), last_class=(last or {}).get('class', ''),
                            last_time=(last or {}).get('updated', ''),
                            age_h=round((now - t) / 3600, 1) if t else None,
                            owner=(o or {}).get('owner') or 'unowned', owner_state=(o or {}).get('state', '')))
    return out


def render(stale, unreachable, src, stale_h=STALE_H, per_die_limit=None):
    """block lines: one header, one summary line per die (counts by owner), one line per item"""
    out = ['### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= %g h: %d '
           '(live check: ps/systemd/docker on all hosts%s; wave state: %s; full list lanes/STALE.tsv)'
           % (stale_h, len(stale), ', NOT SEEN: ' + ' '.join(unreachable) if unreachable else '', src)]
    by = {}
    for s in stale:
        by.setdefault(s['tag'], []).append(s)
    for tag, ss in by.items():
        own = {}
        for s in ss:
            own[s['owner']] = own.get(s['owner'], 0) + 1
        out.append('- [ ] STALE.%s %d (cores %d, types %d) · by owner: %s' % (
            tag, len(ss), sum(s['kind'] == 'core' for s in ss), sum(s['kind'] == 'type' for s in ss),
            ', '.join('%s %d' % kv for kv in sorted(own.items(), key=lambda kv: -kv[1]))))
        ss = sorted(ss, key=lambda s: (-(s['age_h'] if s['age_h'] is not None else 1e9), s['item']))
        for s in ss[:per_die_limit] if per_die_limit else ss:
            last = s['last_status'] if s['last_status'] == 'no kit-wave row' else '%s %s%s @ %s (%gh)%s' % (
                s['last_status'], s['last_stage'], (' ' + s['last_class']) if s['last_class'] else '', s['last_time'],
                s['age_h'], (' row ' + s['last_item']) if s['last_item'] and s['last_item'] != s['item'].split('#')[0] else '')
            out.append('  - %s %s · %s · owner %s' % (s['kind'], s['item'], last, s['owner']))
        if per_die_limit and len(ss) > per_die_limit:
            out.append('  - ... +%d more in lanes/STALE.tsv' % (len(ss) - per_die_limit))
    return out


def write_tsv(stale, path=STALE_TSV):
    cols = ['die', 'kind', 'item', 'last_status', 'last_stage', 'last_class', 'last_time', 'age_h', 'owner',
            'owner_state', 'last_item']
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write('# STALE (stale_list.py, %s): unsigned plan item, no live job, no kit-wave row change >= %g h\n'
                % (time.strftime('%Y-%m-%d %H:%M %Z'), STALE_H))
        f.write('\t'.join(cols) + '\n')
        for s in stale:
            f.write('\t'.join('' if s.get(c) is None else str(s.get(c)).replace('\t', ' ') for c in cols) + '\n')
    os.replace(tmp, path)


def read_tsv(path=STALE_TSV):
    try:
        return [r for r in csv.DictReader([l for l in open(path) if not l.startswith('#')], delimiter='\t')]
    except OSError:
        return []


# COORD 11-10: the wave's own label (KIT-WAVE-<n>) is read by the kit-wave operator lanes
WAVE_OPERATORS = 'KW-FIX-43, KW-FIX-44'


def owner_post(stale, prev=(), stamp=None, unreachable=()):
    """COORD 11-10 (3): hourly queue post, one paragraph per owner lane (unowned -> COORD); '+' = new since the last
    list.  -> text (empty when nothing is stale)"""
    if not stale:
        return ''
    old = {(r.get('die'), r.get('item')) for r in prev}
    by = {}
    for s in stale:
        by.setdefault(s['owner'], []).append(s)
    stamp = stamp or time.strftime('%Y-%m-%d %H:%M %Z')
    owners = sorted(by, key=lambda o: (o == 'unowned', -len(by[o]), o))
    to = ', '.join(o if o != 'unowned' else 'COORD' for o in owners)
    if any(o.startswith('KIT-WAVE') for o in owners):
        to += ', ' + WAVE_OPERATORS
    out = ['- %s STALE [WAVE-OPS-1 -> %s] hourly STALE list (lanes/STALE.tsv): %d unsigned plan cores/types with no live '
           'job and no kit-wave row change >= %g h%s; + = new since the last list. DO_NOT_COUNT, automatic '
           '(lanes/wave-ops-1/stale_cron.sh).' % (stamp, to, len(stale), STALE_H,
                                                  ' (NOT SEEN: %s)' % ' '.join(unreachable) if unreachable else '')]
    for o in owners:
        ss = sorted(by[o], key=lambda s: (s['tag'], s['item']))
        lab = 'COORD (unowned)' if o == 'unowned' else (o + ' (wave label; for %s)' % WAVE_OPERATORS
                                                         if o.startswith('KIT-WAVE') else o)
        items = ['%s%s %s %s (%s%s)' % ('+' if (s['die'], s['item']) not in old else '', s['tag'], s['kind'][0],
                                        s['item'] if s['kind'] == 'core' else s['item'].split('#')[0], s['last_status'],
                                        (' ' + s['last_time'][5:]) if s['last_time'] else '') for s in ss]
        out.append('  %s %d: %s' % (lab, len(ss), '; '.join(items)))
    return '\n'.join(out) + '\n'


def section(cache, rows, dies, plan_die=None, hosts=None, write=True):
    """the STALE block lines for failure_breakdown.main(); probes the fleet"""
    state, src = hub_state()
    text, unreachable = live_text(hosts)
    stale = stale_items(cache, rows, owners_rows(), state, text, dies, plan_die=plan_die)
    if write:
        write_tsv(stale)
    return render(stale, unreachable, src)


def main(argv):
    """--post: compute, rewrite lanes/STALE.tsv, append the owner post to the queue (stale_cron.sh commits both)"""
    import sys as _s
    _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import failure_breakdown as FB
    cache = json.load(open(FB.CACHE))
    rows = list(csv.DictReader(open(FB.STAGES), delimiter='\t'))
    state, src = hub_state()
    text, unreachable = live_text()
    stale = stale_items(cache, rows, owners_rows(), state, text, FB.DIES, plan_die=FB.PLAN_DIE)
    prev = read_tsv()
    write_tsv(stale)
    txt = owner_post(stale, prev, unreachable=unreachable)
    if '--post' in argv and txt:
        with open(os.path.join(COORD, 'lanes/COORD-REVIEW-QUEUE.md'), 'a') as f:
            f.write(txt)
    print(txt or 'no stale items')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
