#!/usr/bin/env python3
"""plan_now: the CURRENT die plans and element (core / type) routing + timing for fleet-viz (WEBVIEW-1, 2026-11-03).

Run every 30 min by repo_sync/refresh.sh (cron), never inside the server.  Writes <state>/plan_now.json:

  dies[]      one row per die of the release tree plan of record (~/coord/tools/release_tree_plan.py PLANS, so the list
              follows COORD plan events automatically): plan path on origin/main, last commit + date touching it, file
              sha256, outline / period / partition, type and hard-core counts, the kit-wave event + plan sha in use and
              the RELEASE_TREE.md die header line.
  elements[]  one row per element of each current plan (partition types + hard cores) plus kit-wave items of the
              current event: sign-off state and, where a routed kit or signed view exists, TT setup / FF hold WNS,
              GRT overflow + wirelength, DRT DRC + wirelength, antenna, LEC verdict, sign-off verdict and reasons.

Sources (all read-only):
  * plan files: the sparse trunk checkout $FLEET_VIZ_REPO (origin/main);
  * signed views: <state>/release_tree_plan_cache.json (hourly release-tree-render scan of origin/main + fleet hosts);
  * kit wave: intel2 ~/coord/autopilot/kit_wave_stages.tsv + kit_wave_state.json (compact extract over ssh);
  * per-kit metrics: one niced ssh per fleet host reads signoff.json / lec.json / 5_1_grt.log / 5_2_route.json of the
    listed kits (results cached by file mtime in <state>/plan_now_metrics.json, so unchanged kits are not re-parsed).
"""
import collections, concurrent.futures as cf, datetime, gzip, hashlib, importlib.util, json, os, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path(os.environ.get('FLEET_VIZ_REPO', '/srv/opentallas-scratch/claude/fleet-viz-repo'))
STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
COORD = pathlib.Path(os.environ.get('OT_RELEASE_TREE_DIR', os.path.expanduser('~/coord')))
OUT = STATE / 'plan_now.json'
MCACHE = STATE / 'plan_now_metrics.json'
PCACHE = STATE / 'plan_now_plans.json'
HUB = os.environ.get('PLAN_NOW_HUB', 'intel2')
sys.path.insert(0, str(HERE))
import fleet_discover
try: HOSTS = [h['id'] for h in fleet_discover.config_hosts() if h.get('ssh')]   # MONITOR-FIX 11-06: a fixed list skipped epyc5/epyc6 kits
except Exception: HOSTS = ['intel1', 'intel2', 'epyc2', 'epyc4', 'epyc5', 'epyc6']
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ControlPath=none']
TARGET = dict(s81='DeepSeek ROM', s81_head='DeepSeek ROM', qwen_compute='Qwen ROM', qwen_kvsys='Qwen ROM', hbm='HBM accelerator')
LABEL = dict(s81='S81 data die', s81_head='S81 head die', qwen_compute='Qwen compute die', qwen_kvsys='Qwen KV/system die',
             hbm='HBM accelerator die')
FALLBACK_PLANS = [('s81', 'physical/die_plan/s81/plan_h2_2249.json'),
                  ('s81_head', 'results/die_head_52_1031/pin/source_plan_l48x.json'),
                  ('qwen_compute', 'physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json'),
                  ('qwen_kvsys', 'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json'),
                  ('hbm', 'physical/die_plan/hbm/plan_of_record/d44c/die_plan.json.gz')]

# element categories (index.html colours them; explorer.py maps them to map states)
CATS = ['signed off', 'signed off (legacy view)', 'routed, not signed (timing)', 'route failure', 'flow failure',
        'plan / geometry failure', 'RTL / kit failure', 'routing / sign-off running', 'running (pre-route)', 'queued',
        'waiting (dependency / plan delta)', 'cancelled', 'not started']


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, file=sys.stderr, flush=True)


def git(*a, binary=False, timeout=120):
    p = subprocess.run(['git', '-C', str(REPO)] + list(a), capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError('git %s: %s' % (' '.join(a[:3]), p.stderr.decode(errors='replace')[:200]))
    return p.stdout if binary else p.stdout.decode(errors='replace').strip()


def plans_of_record():
    """[(die, repo path)] from the release tree tool (current COORD plan events), else the 11-03 list"""
    try:
        spec = importlib.util.spec_from_file_location('release_tree_plan', COORD / 'tools' / 'release_tree_plan.py')
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        # WAVE-POR 11-12: the plans the counter counted last (they follow the kit wave), else its pinned PLANS
        cur = getattr(m, 'current_plans', None)
        out = [(p[0], p[2]) for p in (cur() if cur else m.PLANS)]
        if out: return out, 'release_tree_plan.current_plans' if cur else 'release_tree_plan.PLANS'
    except Exception as e:
        log('PLANS import failed, fallback list: %s' % e)
    return FALLBACK_PLANS, 'fallback list (WEBVIEW-1 11-03)'


def read_plan_bytes(rel):
    p = REPO / rel
    if p.is_file(): return p.read_bytes()
    return git('show', 'origin/main:' + rel, binary=True, timeout=300)


def release_headers():
    out = {}
    try:
        for ln in (COORD / 'RELEASE_TREE.md').read_text().splitlines():
            m = re.match(r'^## DIE (\S+) · (.*)$', ln)
            if m: out[m.group(1)] = m.group(2).strip()
    except OSError:
        pass
    return out


# ------------------------------------------------------------------------------------------------ plan geometry
ORIENT_SWAP = {'R90', 'R270', 'MXR90', 'MYR90'}


def place_child(ox, oy, orient, W, H, x, y, w, h):
    """child rect (type-local x, y, w, h) -> die coordinates for a partition at (ox, oy) with orient"""
    if orient == 'MY': x = W - x - w
    elif orient == 'MX': y = H - y - h
    elif orient == 'R180': x, y = W - x - w, H - y - h
    return ox + x, oy + y


def plan_geometry(die, rel, commit, d):
    """explorer geometry record (schema opentallas.explorer.die_geometry.v1) of one plan: partitions + hard cores + buses"""
    pt = d.get('partition_types') or {}
    masters, mi = [], {}
    cols = dict(name=[], m=[], x=[], y=[], w=[], h=[], o=[], k=[], r=[], dom=[])
    kinds = ['partition', 'hard partition', 'hard core']; ors = []; oi = {}
    regs = ['']; doms = ['']

    def master(name, w, h, kind):
        if name not in mi:
            mi[name] = len(masters); masters.append(dict(name=name, w=round(w, 3), h=round(h, 3), kind=kind, n=0))
        masters[mi[name]]['n'] += 1
        return mi[name]

    def add(name, mname, x, y, w, h, orient, kind):
        if orient not in oi: oi[orient] = len(ors); ors.append(orient)
        cols['name'].append(name); cols['m'].append(master(mname, w, h, kinds[kind])); cols['x'].append(round(x, 2)); cols['y'].append(round(y, 2))
        cols['w'].append(round(w, 2)); cols['h'].append(round(h, 2)); cols['o'].append(oi[orient]); cols['k'].append(kind)
        cols['r'].append(0); cols['dom'].append(0)

    pidx = {}
    for p in d.get('partitions') or []:
        t = pt.get(p['type']) or {}
        W, H = (t.get('outline_um') or [0, 0])[:2]
        orient = p.get('orient') or 'R0'
        w, h = (H, W) if orient in ORIENT_SWAP else (W, H)
        ox, oy = p.get('origin_um') or [0, 0]
        pidx[p['name']] = len(cols['name'])
        add(p['name'], p['type'], ox, oy, w, h, orient, 1 if t.get('hard') else 0)
    for p in d.get('partitions') or []:   # hard cores drawn on top of their partitions
        t = pt.get(p['type']) or {}
        W, H = (t.get('outline_um') or [0, 0])[:2]; orient = p.get('orient') or 'R0'; ox, oy = p.get('origin_um') or [0, 0]
        for c in t.get('hard_cores') or []:
            if not isinstance(c, dict) or not c.get('module') or not c.get('origin_um') or not c.get('outline_um'): continue
            cw, ch = c['outline_um'][:2]
            x, y = place_child(ox, oy, orient, W, H, c['origin_um'][0], c['origin_um'][1], cw, ch)
            add(p['name'] + '/' + (c.get('inst') or c['module']), c['module'], x, y, cw, ch, orient, 2)
    agg = collections.defaultdict(int); cls = []; ci = {}
    for prt in d.get('ports') or []:
        s, t = (prt.get('src') or {}).get('part'), (prt.get('dst') or {}).get('part')
        if s in pidx and t in pidx and s != t:
            agg[(prt.get('kind') or 'data', s, t)] += int(prt.get('width') or 0)
    buses = []
    for (k, s, t), bits in sorted(agg.items()):
        if k not in ci: ci[k] = len(cls); cls.append(k)
        buses.append([ci[k], bits, [pidx[s], pidx[t]]])
    di = d.get('die') or {}
    W, H = (di.get('outline_um') or [max(x + w for x, w in zip(cols['x'], cols['w'])), max(y + h for y, h in zip(cols['y'], cols['h']))])[:2]
    return dict(schema='opentallas.explorer.die_geometry.v1', die='plan_' + die, label='%s · %s' % (LABEL.get(die, die), pathlib.PurePosixPath(rel).name),
                target=TARGET.get(die, 'Other'), kind='plan', commit=commit, recipe=dict(ref='origin/main', paths=[rel], tool='fleet-viz plan_now.py (die plan of record)'),
                W=round(W, 3), H=round(H, 3), masters=masters, kinds=kinds, regions_names=regs, orients=ors, domains=doms, inst=cols,
                bus_classes=cls, buses=buses, buses_skipped=0, regions=[], relays=0,
                model_keys=dict(partitions=['list', len(d.get('partitions') or [])], partition_types=['dict', len(pt)], ports=['list', len(d.get('ports') or [])]),
                dataflow_connections=[], views={})


def scan_plans(cached):
    plans, src = plans_of_record()
    heads = release_headers()
    dies, geoms = [], {}
    for die, rel in plans:
        row = dict(die=die, label=LABEL.get(die, die), target=TARGET.get(die, 'Other'), plan_path=rel, plans_source=src,
                   release_header=heads.get(die))
        try:
            c = git('log', '-1', '--format=%H|%cI|%s', 'origin/main', '--', rel).split('|', 2)
            row.update(plan_commit=c[0], plan_date=c[1], plan_subject=c[2][:200] if len(c) > 2 else '')
            blob = git('rev-parse', 'origin/main:' + rel)
            row['plan_blob'] = blob
            prev = cached.get(die)
            if prev and prev.get('plan_blob') == blob and prev.get('summary'):
                row.update(summary=prev['summary'], plan_sha256=prev.get('plan_sha256'), types=prev.get('types'), hard=prev.get('hard'))
            else:
                raw = read_plan_bytes(rel)
                row['plan_sha256'] = hashlib.sha256(raw).hexdigest()[:12]
                d = json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
                pt = d.get('partition_types') or {}; di = d.get('die') or {}
                hard = sorted({c['module'] for t in pt.values() for c in (t.get('hard_cores') or []) if isinstance(c, dict) and c.get('module')})
                used = collections.Counter(p['type'] for p in d.get('partitions') or [])
                row['types'] = sorted(pt); row['hard'] = hard
                row['summary'] = dict(name=di.get('name'), outline_um=di.get('outline_um'), period_ps=di.get('period_ps'),
                                      partitions=len(d.get('partitions') or []), types=len(pt), types_used=len(used), hard_cores=len(hard),
                                      ports=len(d.get('ports') or []), lanes=len(d.get('lanes') or []),
                                      clock=((d.get('clock') or {}).get('spine') or {}).get('topology'), schema=d.get('schema'),
                                      reach_um=di.get('reach_um'),
                                      note=(d.get('note') or '')[:400], type_count=dict(used))
                del d, raw
        except Exception as e:
            row['error'] = str(e)[:300]; log('plan %s: %s' % (die, e))
        dies.append(row)
    return dies, geoms


def sync_explorer_dies(dies):
    """keep the Chip Explorer 'plan_<die>' entries (explorer_dies.json) on the current plan paths; the explorer
    (explorer_geom.py kind 'plan') re-exports a die when the last commit touching its plan path changes"""
    p = HERE / 'explorer_dies.json'
    try: cfg = json.loads(p.read_text())
    except Exception as e: log('explorer_dies.json: %s' % e); return
    keep = [d for d in cfg.get('dies', []) if d.get('kind') != 'plan']
    plan = [dict(id='plan_' + d['die'], label='%s (plan of record %s)' % (d['label'], pathlib.PurePosixPath(d['plan_path']).name),
                 target=d['target'], kind='plan', plan_die=d['die'], plan_path=d['plan_path'], ref='origin/main', ref_fallback=['main'],
                 paths=[d['plan_path']], tool='plan_now.plan_geometry: partitions + hard cores + aggregated plan ports (die_plan.v1)',
                 note='current plan of record (%s); kit-wave event %s' % (d.get('plans_source'), ','.join(sorted(map(str, (d.get('kit_wave') or {}).get('events') or {}))) or '-'),
                 reach_um=405.0, reach_note='plan reach_um (die.reach_um)') for d in dies if not d.get('error')]
    for e, d in zip(plan, [d for d in dies if not d.get('error')]):
        r = ((d.get('summary') or {}).get('reach_um'))
        if r: e['reach_um'] = r
    new = dict(cfg, dies=plan + keep)
    if [x for x in new['dies'] if x.get('kind') == 'plan'] != [x for x in cfg.get('dies', []) if x.get('kind') == 'plan']:
        tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(new, indent=2) + '\n'); os.replace(tmp, p)
        log('explorer_dies.json: plan entries updated')


# ------------------------------------------------------------------------------------------------ kit wave
KW_PY = r'''
import json, os, sys
d = json.load(open(os.path.expanduser("~/coord/autopilot/kit_wave_state.json")))
out = {}
for k, v in (d.get("items") or {}).items():
    out[v.get("die", "") + "|" + v.get("item", "")] = {x: v.get(x) for x in ("kind", "attempt", "status", "stage", "class", "event", "plan_sha", "updated", "started", "kit", "unit", "volume")}
print(json.dumps(dict(items=out, mtime=os.path.getmtime(os.path.expanduser("~/coord/autopilot/kit_wave_state.json")))))
'''


def kit_wave():
    t0 = time.time()
    p = subprocess.run(SSH + [HUB, 'cat ~/coord/autopilot/kit_wave_stages.tsv; echo "@@MTIME $(stat -c %Y ~/coord/autopilot/kit_wave_stages.tsv)"'],
                       capture_output=True, text=True, timeout=120)
    if p.returncode: raise RuntimeError('kit_wave_stages.tsv: %s' % p.stderr[-200:])
    lines = p.stdout.splitlines(); mt = None
    if lines and lines[-1].startswith('@@MTIME'): mt = float(lines.pop().split()[1])
    hdr = lines[0].split('\t'); rows = [dict(zip(hdr, ln.split('\t'))) for ln in lines[1:] if ln.strip()]
    q = subprocess.run(SSH + [HUB, 'nice -n 10 python3 -c %s' % shq(KW_PY)], capture_output=True, text=True, timeout=180)
    st = json.loads(q.stdout) if q.returncode == 0 and q.stdout.strip() else dict(items={}, mtime=None)
    log('kit wave: %d stage rows, %d state items (%.1f s)' % (len(rows), len(st['items']), time.time() - t0))
    return rows, st, mt


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


# ------------------------------------------------------------------------------------------------ per-kit metrics (runs on each host)
MET_PY = r'''
import glob, json, os, re, sys
def mt(p):
    try: return os.path.getmtime(p)
    except OSError: return None
def newest(ps):
    ps = [p for p in ps if os.path.isfile(p)]
    return max(ps, key=os.path.getmtime) if ps else None
def J(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return None
def grt(logp):
    r = {}
    try:
        txt = open(logp, errors="replace").read()
    except OSError:
        return r
    i = txt.rfind("Final congestion report")
    if i >= 0:
        for ln in txt[i:i + 6000].splitlines():
            if ln.startswith("Total"):
                nums = re.findall(r"(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*$", ln)
                if nums: r["grt_overflow"] = int(nums[0][2]); r["grt_overflow_hv"] = [int(nums[0][0]), int(nums[0][1])]
                u = re.findall(r"([\d.]+)%", ln)
                if u: r["grt_usage_pct"] = float(u[0])
                break
    m = re.findall(r"GRT-0018\] Total wirelength: ([\d.]+)", txt)
    if m: r["grt_wl_um"] = float(m[-1])
    if "GRT-0116" in txt or "GRT-0119" in txt: r["grt_error"] = (re.findall(r"\[ERROR GRT-\d+\][^\n]*", txt) or [""])[-1][:200]
    return r
def route(js):
    m = J(js) or {}
    r = {}
    if "detailedroute__route__drc_errors" in m: r["drt_drc"] = m["detailedroute__route__drc_errors"]
    if "detailedroute__route__wirelength" in m: r["drt_wl_um"] = m["detailedroute__route__wirelength"]
    return r
def signoff(p):
    s = J(p)
    if not isinstance(s, dict): return {}
    ch = s.get("checks") or {}; rt = s.get("route") or {}
    tt = (ch.get("setup_tt") or {}); ff = (ch.get("hold_ff") or {})
    r = dict(signoff=p, signoff_mtime=mt(p), verdict=s.get("verdict"), signoff_generated=s.get("generated"), signoff_host=s.get("host"),
             tt_wns=tt.get("wns_ps"), tt_verdict=tt.get("verdict"), tt_tns=tt.get("tns_ps"), ff_wns=ff.get("wns_ps"), ff_verdict=ff.get("verdict"),
             ff_violators=ff.get("violators"), drc=rt.get("drc"), antenna=rt.get("antenna_nets"), reasons=(s.get("reasons") or [])[:4],
             failing=sorted(k for k, v in ch.items() if isinstance(v, dict) and v.get("verdict") not in (None, "PASS", "INFO", "SKIP")),
             design=(s.get("inputs") or {}).get("design"), cells=((s.get("corners") or {}).get("tt") or {}).get("cells"))
    met = (s.get("inputs") or {}).get("metrics") or {}
    g = met.get("5_1_grt.json")
    if g: r.update(grt(g[:-5] + ".log"))
    if met.get("5_2_route.json"): r.update({k: v for k, v in route(met["5_2_route.json"]).items() if k not in r})
    return r
def lec(p):
    l = J(p)
    if not isinstance(l, dict): return {}
    c = l.get("counts") or {}
    return dict(lec=l.get("verdict"), lec_path=p, lec_mtime=mt(p), lec_failing=len(l.get("failing") or []) if isinstance(l.get("failing"), list) else l.get("failing"))
STAGES = [("1_synth", "synth"), ("2_1_floorplan", "floorplan"), ("3_3_place_gp", "place"), ("3_5_place_dp", "place"), ("4_1_cts", "cts"),
          ("5_1_grt", "grt"), ("5_2_route", "drt"), ("6_report", "final")]
old = json.loads(sys.stdin.readline() or "{}")
out = {}
for ln in sys.stdin:
    q = json.loads(ln); p = q["path"]; key = q["id"]
    try:
        r = dict(kind=q["kind"])
        if q["kind"] == "signoff":
            m = mt(p)
            if m is None: r["missing"] = True
            else:
                o = old.get(key)
                if o and o.get("signoff_mtime") == m: out[key] = o; continue
                r.update(signoff(p))
                d = os.path.dirname(os.path.dirname(p))
                lp = newest([os.path.join(os.path.dirname(p), "..", "lec", "lec.json"), os.path.join(d, "lec", "lec.json")])
                if lp: r.update(lec(lp))
        else:
            if not os.path.isdir(p): r["missing"] = True; out[key] = r; continue
            sp = newest([p + "/signoff/signoff.json"] + glob.glob(p + "/eco_*/i*/signoff/signoff.json") + glob.glob(p + "/*/signoff/signoff.json"))
            lp = newest([p + "/lec/lec.json"] + glob.glob(p + "/eco_*/i*/lec/lec.json") + glob.glob(p + "/*/lec/lec.json"))
            base = (glob.glob(p + "/run/logs/asap7/*/base") or [None])[0]
            stamp = [mt(sp) if sp else None, mt(lp) if lp else None, mt(base) if base else None]
            o = old.get(key)
            if o and o.get("_stamp") == stamp: out[key] = o; continue
            r["_stamp"] = stamp
            if base:
                last = None
                for f, nm in STAGES:
                    if os.path.isfile(os.path.join(base, f + ".log")): last = nm
                r["flow_stage"] = last; r["flow_mtime"] = mt(base)
                if os.path.isfile(base + "/5_1_grt.log"): r.update(grt(base + "/5_1_grt.log"))
                if os.path.isfile(base + "/5_2_route.json"): r.update(route(base + "/5_2_route.json"))
            if sp:   # the sign-off view wins, except GRT: an ECO iteration's incremental GRT log is not the kit's global route
                so = signoff(sp)
                r.update({k: v for k, v in so.items() if (v is not None or k not in r) and not (k.startswith("grt_") and k in r)})
            if lp: r.update(lec(lp))
        out[key] = r
    except Exception as e:
        out[key] = dict(kind=q["kind"], error=str(e)[:200])
print(json.dumps(out))
'''


def run_metrics(host, reqs, old):
    payload = json.dumps({k: old[k] for k in (q['id'] for q in reqs) if k in old}) + '\n' + ''.join(json.dumps(q) + '\n' for q in reqs)
    cmd = (['nice', '-n', '15', 'python3', '-c', MET_PY] if host == 'local' else
           SSH + [host, 'nice -n 15 python3 -c %s' % shq(MET_PY)])
    t0 = time.time()
    p = subprocess.run(cmd, input=payload, capture_output=True, text=True, timeout=600)
    if p.returncode: raise RuntimeError('%s rc %d: %s' % (host, p.returncode, p.stderr[-300:]))
    r = json.loads(p.stdout)
    log('metrics %s: %d paths (%.1f s)' % (host, len(r), time.time() - t0))
    return r


def split_hp(s):
    h, _, p = s.partition(':')
    return (h, p) if p.startswith('/') else (None, s)


# ------------------------------------------------------------------------------------------------ categories
def kw_category(r):
    st, cl, sg = r.get('status') or '', r.get('cls') or r.get('class') or '', r.get('stage') or ''
    if st == 'FAIL':
        if cl == 'TIMING': return 'routed, not signed (timing)'
        if cl == 'ROUTING' or (cl in ('FLOW', 'INFRA') and sg in ('route', 'signoff', 'resume_nochange')): return 'route failure'
        if cl == 'PLAN': return 'plan / geometry failure'
        if cl == 'RTL': return 'RTL / kit failure'
        return 'flow failure'
    if st == 'RUNNING': return 'routing / sign-off running' if sg in ('route', 'signoff', 'resume_fp') else 'running (pre-route)'
    if st in ('ENQUEUED', 'QUEUED'): return 'queued'
    if st == 'CANCELLED': return 'cancelled'
    if st.startswith('PENDING') or st.startswith('WAIT') or st == 'LINT-ADVISORY': return 'waiting (dependency / plan delta)'
    if st in ('SIGNED', 'PASS', 'DONE'): return 'signed off'
    return 'flow failure' if st else 'not started'


def ts(s):
    try: return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M').timestamp()
    except Exception:
        try: return datetime.datetime.fromisoformat(s).timestamp()
        except Exception: return None


def token_now():
    """token pass state: RELEASE_TREE TOK.* lines + the newest results/token_pass records on origin/main + token-path model dates"""
    tok = dict(release_lines=[], token_pass=[], models=[])
    try:
        for ln in (COORD / 'RELEASE_TREE.md').read_text().splitlines():
            if re.match(r'^- \[.\] (TOK\.|KV\.FN)', ln): tok['release_lines'].append(ln[6:][:600])
        tok['release_mtime'] = (COORD / 'RELEASE_TREE.md').stat().st_mtime
    except OSError:
        pass
    try:
        seen = {}
        for ln in git('log', '--since=10 days ago', '--format=@@%h|%cI', '--name-only', 'origin/main', '--', 'results/token_pass/').splitlines():
            if ln.startswith('@@'): cur = ln[2:].split('|'); continue
            parts = ln.split('/')
            if len(parts) > 3 and ln.strip():
                k = parts[2]
                if k not in seen: seen[k] = dict(dir='results/token_pass/' + k, commit=cur[0], date=cur[1])
        for k, v in list(seen.items())[:25]:
            rd = REPO / v['dir'] / 'README.md'
            if rd.is_file():
                txt = [x.strip('# ').strip() for x in rd.read_text(errors='replace').splitlines() if x.strip()][:3]
                v['readme'] = ' · '.join(txt)[:400]
            tok['token_pass'].append(v)
    except Exception as e:
        tok['error'] = str(e)[:200]
    for f in sorted((HERE / 'explorer' / 'token' / 'data').glob('*.json')):
        if f.name.startswith('geo_'): continue
        tok['models'].append(dict(file=f.name, mtime=f.stat().st_mtime))
    return tok


def main():
    t0 = time.time()
    try: prev = json.loads(OUT.read_text())
    except Exception: prev = {}
    try: mcache = json.loads(MCACHE.read_text())
    except Exception: mcache = {}
    cached = {d['die']: d for d in prev.get('dies', []) if d.get('summary')}
    dies, _ = scan_plans(cached)
    # release cache: signed views per current plan
    rc_path = STATE / 'release_tree_plan_cache.json'
    try: rc = json.loads(rc_path.read_text()); rc_mt = rc_path.stat().st_mtime
    except Exception as e: rc, rc_mt = {}, None; log('release cache: %s' % e)
    signed = collections.defaultdict(dict)   # die -> name -> (entry list, kind)
    for p in (rc.get('plans') or {}).values():
        die = p.get('die')
        for kind, key in (('type', 'signed_types'), ('core', 'signed_cores')):
            for n, ents in (p.get(key) or {}).items():
                if ents: signed[die][n] = (ents, kind)
        p['_hard'] = p.get('hard_cores') or []
    rc_hard = {p.get('die'): p.get('hard_cores') or [] for p in (rc.get('plans') or {}).values()}
    # kit wave
    try: kw_rows, kw_state, kw_mt = kit_wave()
    except Exception as e: kw_rows, kw_state, kw_mt = [], dict(items={}), None; log('kit wave: %s' % e)
    best = {}
    for r in kw_rows:
        k = (r.get('die'), r.get('item'))
        key = (r.get('plan_current') == 'yes', ts(r.get('updated') or '') or 0)
        if k not in best or key > best[k][0]: best[k] = (key, r)
    kw = {k: v[1] for k, v in best.items()}
    # element universe
    rows = {}
    for d in dies:
        die = d['die']
        for t in d.get('types') or []: rows[(die, t)] = dict(element=t, die=die, kind='type')
        for c in set(d.get('hard') or []) | set(rc_hard.get(die) or []): rows[(die, c)] = dict(element=c, die=die, kind='core')
    for (die, it), r in kw.items():
        if (die, it) not in rows and die in TARGET:
            if r.get('plan_current') != 'yes': continue
            rows[(die, it)] = dict(element=it, die=die, kind=(kw_state['items'].get('%s|%s' % (die, it)) or {}).get('kind') or 'item', not_in_plan=True)
    # requests for metrics
    reqs = collections.defaultdict(list)
    for (die, n), e in rows.items():
        s = signed.get(die, {}).get(n)
        if s:
            ents, kind = s
            first = ents[0].split(' ')[0]
            e['signed'] = dict(kind=kind, entry=ents[0][:400], n=len(ents), legacy='SIGNED-LEGACY' in ents[0])
            h, path = split_hp(first)
            if h and path.endswith('.json'):
                e['_sreq'] = '%s|signoff|%s' % (h, path); reqs[h].append(dict(id=e['_sreq'], kind='signoff', path=path))
            elif first.startswith('origin/main:'):
                e['signed']['repo_path'] = first[len('origin/main:'):]
        k = kw.get((die, n))
        if k:
            st = kw_state['items'].get('%s|%s' % (die, n)) or {}
            e['kw'] = dict(status=k.get('status'), stage=k.get('stage'), cls=k.get('class'), event=k.get('event'), plan_sha=k.get('plan_sha'),
                           block_sha=k.get('block_sha'), kit=k.get('kit'), evidence=(k.get('evidence') or '')[:300], updated=ts(k.get('updated') or ''),
                           plan_current=k.get('plan_current') == 'yes', reason=(k.get('reason') or '')[:600], attempt=st.get('attempt'),
                           state_status=st.get('status'))
            h, path = split_hp(k.get('kit') or '')
            if h and path:
                e['_kreq'] = '%s|kit|%s' % (h, path); reqs[h].append(dict(id=e['_kreq'], kind='kit', path=path))
    res = {}
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(run_metrics, h, q, mcache): h for h, q in reqs.items() if h in HOSTS or h == 'local'}
        for f, h in futs.items():
            try: res.update(f.result())
            except Exception as e: log('metrics %s: %s' % (h, e)); res.update({q['id']: mcache[q['id']] for q in reqs[h] if q['id'] in mcache})
    # origin/main signed views (no host): signoff.json from the trunk
    for e in rows.values():
        rp = (e.get('signed') or {}).get('repo_path')
        if rp:
            try:
                s = json.loads(git('show', 'origin/main:' + rp))
                ch = s.get('checks') or {}
                e['_m_repo'] = dict(verdict=s.get('verdict'), signoff='origin/main:' + rp, signoff_generated=s.get('generated'),
                                    tt_wns=(ch.get('setup_tt') or {}).get('wns_ps'), ff_wns=(ch.get('hold_ff') or {}).get('wns_ps'),
                                    drc=(s.get('route') or {}).get('drc'), antenna=(s.get('route') or {}).get('antenna_nets'),
                                    reasons=(s.get('reasons') or [])[:4])
            except Exception as ex_:
                e['_m_repo'] = dict(error=str(ex_)[:120])
    MCACHE.write_text(json.dumps(res))
    out_el = []
    for (die, n), e in sorted(rows.items()):
        ms = res.get(e.pop('_sreq', None)) or e.pop('_m_repo', None) or {}
        e.pop('_m_repo', None)
        mk = res.get(e.pop('_kreq', None)) or {}
        if e.get('signed'):
            e['category'] = 'signed off (legacy view)' if e['signed'].get('legacy') else 'signed off'
            m = dict(mk); m.update({k: v for k, v in ms.items() if v is not None})   # the signed view wins
            e['metrics_from'] = 'signed view' if ms else ('kit' if mk else None)
        else:
            e['category'] = kw_category(e['kw']) if e.get('kw') else 'not started'
            m = mk; e['metrics_from'] = 'kit' if mk else None
        e['m'] = {k: v for k, v in m.items() if not k.startswith('_')}
        e['target'] = TARGET.get(die, 'Other')
        out_el.append(e)
    cnt = collections.defaultdict(collections.Counter)
    for e in out_el: cnt[e['die']][e['category']] += 1
    evs = collections.defaultdict(collections.Counter); shas = collections.defaultdict(collections.Counter); last = collections.defaultdict(float)
    for (die, _), r in kw.items():
        if r.get('plan_current') == 'yes':
            evs[die][r.get('event')] += 1; shas[die][r.get('plan_sha')] += 1
            last[die] = max(last[die], ts(r.get('updated') or '') or 0)
    for d in dies:
        d['counts'] = dict(cnt[d['die']])
        d['kit_wave'] = dict(events=dict(evs[d['die']]), plan_sha=(shas[d['die']].most_common(1) or [(None,)])[0][0],
                             last_update=last[d['die']] or None)
        d['elements'] = sum(cnt[d['die']].values())
    sync_explorer_dies(dies)
    out = dict(schema='opentallas.fleet_viz.plan_now.v1', generated=time.time(), build_s=None, cats=CATS,
               repo=dict(path=str(REPO), origin_main=git('rev-parse', '--short=10', 'origin/main'),
                         origin_main_date=git('log', '-1', '--format=%cI', 'origin/main')),
               sources=dict(release_cache=str(rc_path), release_cache_mtime=rc_mt, release_cache_hosts=rc.get('scanned'),
                            kit_wave_stages='%s:~/coord/autopilot/kit_wave_stages.tsv' % HUB, kit_wave_stages_mtime=kw_mt,
                            kit_wave_state_mtime=kw_state.get('mtime'), metric_hosts=sorted(reqs), metric_paths=len(res)),
               dies=dies, elements=out_el, token=token_now())
    out['build_s'] = round(time.time() - t0, 1)
    tmp = OUT.with_suffix('.tmp'); tmp.write_text(json.dumps(out, separators=(',', ':'))); os.replace(tmp, OUT)
    log('plan_now: %d dies, %d elements, %.1f s' % (len(dies), len(out_el), out['build_s']))


if __name__ == '__main__':
    main()
