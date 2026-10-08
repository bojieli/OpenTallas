"""Append-only fleet recording and window loading for replay (shared by server.py and export_replay.py).

Layout: <root>/YYYY-MM-DD/HH.jsonl.gz (local time), one JSON record per line. Each hour file opens
with keyframes (meta, loop, recent, full job table, status md, full verdict list) so it replays on
its own. A restart appends a new gzip member to the same file; every tick ends with a zlib sync
flush, so a crash loses at most the sample in flight and the reader tolerates a missing trailer.

Records ('k'):
  meta    poll, regions, hosts [{id, name, label, kind, region}]
  s       every tick: h = per host [state, cores (base64 uint8), mem_total, mem_used, load, docker, gpu, routes]
  loop    loop counters, on change               recent  closure ticker rows (internal), on change
  jobs    full=1 rows (keyframe, every 10 min and at file start) | up=[rows], rm=[names] (diff, on change)
  md      closure-loop STATUS.md digest, on change
  verd    full=1 rows (file start) | add=[rows] (new verdicts)
"""
import base64, datetime, gzip, json, math, os, pathlib, re, time, zlib

KEEP = """# KEEP: fleet-viz recordings

Append-only recording of the fleet visualiser (tools/fleet_viz, recorder.py) for later replay.
Retention: keep everything. Fleet sweepers, scratch cleaners and disk reapers must skip this
directory. Do not delete, rotate or compress-in-place.
"""
JOB_KEYFRAME = 600
MAGIC = b'\x1f\x8b\x08'


def hour_path(root, t):
    lt = time.localtime(t)
    return pathlib.Path(root) / time.strftime('%Y-%m-%d', lt) / ('%02d.jsonl.gz' % lt.tm_hour)


def pack_cores(cores):
    return base64.b64encode(bytes(max(0, min(255, int(c))) for c in cores)).decode()


def unpack_cores(s):
    return list(base64.b64decode(s)) if s else None


class Recorder:
    """Writer. keyframes() must return the list of records that open a new hour file."""

    def __init__(self, root, keyframes):
        self.root = pathlib.Path(root); self.keyframes = keyframes
        self.path = None; self.f = None; self.bytes = 0
        self.root.mkdir(parents=True, exist_ok=True)
        keep = self.root / 'STATUS.md'
        if not keep.exists(): keep.write_text(KEEP)

    def _open(self, t):
        p = hour_path(self.root, t)
        if p == self.path and self.f: return False
        if self.f: self.f.close()
        p.parent.mkdir(parents=True, exist_ok=True)
        self.f = gzip.GzipFile(filename=p.name, mode='ab', fileobj=open(p, 'ab'), compresslevel=6)
        self.path = p
        return True

    def write(self, t, recs):
        if self._open(t):
            recs = list(self.keyframes(t)) + list(recs)
        for r in recs:
            b = (json.dumps(r, separators=(',', ':')) + '\n').encode()
            self.f.write(b); self.bytes += len(b)
        self.f.flush(zlib.Z_SYNC_FLUSH); self.f.fileobj.flush()

    def close(self):
        if self.f:
            fo = self.f.fileobj; self.f.close(); fo.close(); self.f = None


def read_records(path):
    """Yield records from a multi-member, possibly truncated gzip JSONL file."""
    data = pathlib.Path(path).read_bytes(); out = bytearray(); pos = 0
    while pos < len(data):
        d = zlib.decompressobj(31)
        try:
            chunk = d.decompress(data[pos:])
            if d.eof:
                out += chunk; pos = len(data) - len(d.unused_data); continue
        except zlib.error:
            pass
        # unterminated member (writer killed, or still open): decode up to the next member header
        nxt = data.find(MAGIC, pos + 10); end = nxt if nxt >= 0 else len(data)
        try: out += zlib.decompressobj(31).decompress(data[pos:end]) + b'\n'
        except zlib.error: pass
        pos = end
    for line in out.split(b'\n'):
        if not line: continue
        try: yield json.loads(line)
        except ValueError: continue     # torn last line


def files_for(root, t0, t1):
    seen = []; t = (int(t0) // 3600) * 3600 - 3600
    while t <= t1 + 3600:
        p = hour_path(root, t)
        if p not in seen and p.exists(): seen.append(p)
        t += 1800
    return seen


def parse_time(s, now=None):
    """epoch seconds, 'now', 'now-30m' / '-2h' / '-90s', or ISO (naive = local time)."""
    now = time.time() if now is None else now
    s = str(s).strip()
    if re.fullmatch(r'\d+(\.\d+)?', s): return float(s)
    m = re.fullmatch(r'(?:now)?\s*(?:([+-])\s*(\d+(?:\.\d+)?)\s*([smhd]))?', s)
    if m and s:
        if not m.group(1): return now
        v = float(m.group(2)) * dict(s=1, m=60, h=3600, d=86400)[m.group(3)]
        return now - v if m.group(1) == '-' else now + v
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def _merge(dst, up, rm):
    for r in up: dst[r['name']] = r
    for n in rm: dst.pop(n, None)


def load_window(root, t0, t1, safe=False, max_frames=3000):
    """Return a replay package for [t0, t1] (history rows reach back 60 min before t0).

    Frames and job diffs are downsampled to at most max_frames buckets; safe=True keeps only
    share-safe labels (no job table, status md or verdicts; ticker rows reduced to t/cat/host)."""
    meta = None; frames = []; hist = []; loops = []; recents = []; mds = []
    state = {}; jobs0 = None; jdiffs = []; vfull = {}; vadd = []
    last_loop = None; last_recent = None; last_md = None
    for p in files_for(root, t0 - 3600, t1):
        for r in read_records(p):
            k = r.get('k'); t = r.get('t', 0)
            if k == 'meta': meta = r; continue
            if t > t1: continue
            if k == 's':
                if t >= t0 - 3600: hist.append(r)
                if t >= t0: frames.append(r)
            elif k == 'loop':
                if t < t0: last_loop = r
                else: loops.append(r)
            elif k == 'recent':
                if t < t0: last_recent = r
                else: recents.append(r)
            elif k == 'md':
                if t < t0: last_md = r
                else: mds.append(r)
            elif k == 'jobs':
                if t > t0 and jobs0 is None: jobs0 = dict(state)
                if r.get('full'):
                    new = {j['name']: j for j in r['rows']}
                    up = [j for n, j in new.items() if state.get(n) != j]; rm = [n for n in state if n not in new]
                    state = new
                else:
                    up, rm = r.get('up', []), r.get('rm', []); _merge(state, up, rm)
                if t > t0 and (up or rm): jdiffs.append([t, up, rm])
            elif k == 'verd':
                for v in (r['rows'] if r.get('full') else r.get('add', [])):
                    key = (v['t'], v['name'], v['status'])
                    if key not in vfull: vfull[key] = v
    if meta is None: return None
    if jobs0 is None: jobs0 = state
    if last_loop: loops.insert(0, dict(last_loop, t=t0))
    if last_recent: recents.insert(0, dict(last_recent, t=t0))
    if last_md: mds.insert(0, dict(last_md, t=t0))
    step = max(1, math.ceil(len(frames) / max_frames)) if frames else 1
    span = (t1 - t0) / max_frames if len(frames) > max_frames else 0
    frames = frames[::step]
    if len(hist) > 2 * max_frames: hist = hist[::math.ceil(len(hist) / (2 * max_frames))]
    if span:   # coalesce change streams into time buckets (last write wins)
        def bucket(rs):
            out = {}
            for r in rs: out[int((r['t'] - t0) // span)] = r
            return list(out.values())
        loops, recents, mds = bucket(loops), bucket(recents), bucket(mds)
        cj = {}
        for t, up, rm in jdiffs:
            b = int((t - t0) // span); e = cj.setdefault(b, [t, {}, set()])
            e[0] = t
            for j in up: e[1][j['name']] = j; e[2].discard(j['name'])
            for n in rm: e[1].pop(n, None); e[2].add(n)
        jdiffs = [[e[0], list(e[1].values()), sorted(e[2])] for e in cj.values()]
    hosts = meta['hosts']
    name2label = {h['name']: h['label'] for h in hosts}
    # history rows as the page draws them: t, busy threads, threads, routes running, fleet RAM GB, per-host RAM GB
    li = 0; allloops = ([last_loop] if last_loop else []) + loops
    hrows = []
    for s in hist:
        busy = 0.0; thr = 0; mem = []; tot = 0.0
        for h in s['h']:
            up = h[0] == 'up'
            c = unpack_cores(h[1]) if up and h[1] else None
            if c: busy += sum(c) / 100; thr += len(c)
            mu = h[3] if up and h[3] is not None else 0; mem.append(mu); tot += mu
        while li + 1 < len(allloops) and allloops[li + 1]['t'] <= s['t']: li += 1
        run = allloops[li]['loop'].get('running', 0) if allloops else 0
        hrows.append([round(s['t']), round(busy, 1), thr, run, round(tot, 1), mem])
    pkg = dict(v=1, t0=t0, t1=t1, safe=safe, step=step, poll=meta['poll'] * step, regions=meta['regions'],
               hosts=[dict(label=h['label'] if safe else h['name'], kind=h['kind'], region=h['region'],
                           **({} if safe else dict(alias=h['id']))) for h in hosts],
               frames=[[s['t'], s['h']] for s in frames], hist=hrows, loops=[[r['t'], r['loop']] for r in loops])
    if safe:
        pkg['recents'] = [[r['t'], [dict(t=x['t'], cat=x['cat'], host=name2label.get(x['host'], 'fleet')) for x in r['rows']]] for r in recents]
    else:
        pkg['recents'] = [[r['t'], r['rows']] for r in recents]
        pkg['jobs0'] = list(jobs0.values()); pkg['jdiffs'] = jdiffs
        pkg['mds'] = [[r['t'], r['md']] for r in mds]
        pkg['verdicts'] = sorted(vfull.values(), key=lambda v: v['t'])
    return pkg
