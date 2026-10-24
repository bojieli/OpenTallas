#!/usr/bin/env python3
"""SIGNOFF inventory: every block the current die plans reference as CLOSED, and where its routed database lives.

Re-signoff (OpenSTA MCMM on the routed ODB/DEF + netlist + SPEF) needs the routed database of every hardened block.
This tool walks the 4 current die plans (+ s81_head, flagged 'extra', + HBM-ARCH B2r2 read from its branch), collects
every module they reference as a closed / reused hardened view, looks up the repo evidence for it (view dirs with
LEF/LIB, ref_tile gate_result.json, views/<m>/insertion.json 'base', export_*.tcl read_db, corner_sta.json,
results/closure_loop/*/verdict.json) and then checks where the routed database is NOW:

  repo      6_final.odb (or .def) + netlist + SPEF committed in git
  present   found on a live host (recorded base path still exists, or a surviving routed run of the module)
  LOST      neither (old fleet hosts ot-*, rtx-pro, agidock, pve are wiped) -> status NEEDS RE-RUN

Classification of a plan reference (per die, per module):
  macro            ROM / PHY / PLL hard IP (abstract-only; no routed DB of ours to re-sign)
  not_closed       plan says PLANNED / lef-lib pending / SPLIT PROPOSAL / split piece / MEASURED-SYNTH / gates FAIL,
                   contents status=rework, or a hard core without any closed evidence (repo view / CLOSED verdict)
                   (HBM '(SYNAREA)' / '(YOSYS)' tags only name the cell-count source; they are not a closure claim)
  closed           plan points at a view (lef/lib), says CLOSED / REUSE-CLOSED / closed slice leaf, carries a reuse
                   kit / geom_pass, or the repo holds a closed view / CLOSED closure_loop verdict for the module
  reuse_unverified contents[] status=reuse with no closed claim and no repo evidence (soft RTL reuse, flattened)

Usage:
  python3 tools/die_plan/signoff_inventory.py --out results/signoff_1024/inventory.json \
      [--hosts-scan /tmp/hosts_scan.json [--rescan]] [--no-ssh]
--hosts-scan: cache of the live-host search (loaded if present, else written after scanning).
--no-ssh: never ssh; use the cache if given, else DB status is 'unscanned' for everything not in git.
"""
import argparse, collections, datetime, glob, json, os, re, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DIES = [('s81', False), ('qwen_compute', False), ('qwen_kvsys', False), ('hbm', False), ('s81_head', True)]
B2 = {'die': 'hbm_b2r2', 'branch': 'claude/hbm-arch-1024', 'path': 'physical/die_plan/hbm_arch/B2r2/die_plan.json'}
HOSTS = ['localhost', 'epyc2', 'epyc3', 'intel1', 'intel2']
SCAN_ROOTS = ['/srv/opentallas-scratch', '/srv/opentallas-scratch2', '~/ot-scratch', '~/scratch']
PRUNE = ['numeric_e*', 'reduction_s8*', 'part-cap*', '.git', 'moved', 's81_halfclock_truth_1020', 'sram*', 'proc']
OLD_HOST_RE = re.compile(r'^(ot-|rtx-pro|agidock|pve)')

NOT_CLOSED_RE = re.compile(r'PLANNED|lef/lib pending|lef/lib/pins pending|SPLIT PROPOSAL|split piece|MEASURED-SYNTH|'
                           r'planned hard core|gates FAIL|split pieces of', re.I)
CLOSED_RE = re.compile(r'\bCLOSED\b|REUSE-CLOSED|closed slice leaf|closed view|closed kit')
MACRO_DIR_RE = re.compile(r'^physical/asap7_(memory_macros|v41x_pdie_macros)')
MACRO_NAME_RE = re.compile(r'^ot_rom_\d|_phy(_|$)|^ot_hbm3e_phy|serdes_112g|ucie_x64_phy|^qkd_pllm$')


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


def jload(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def rel(p):
    return os.path.relpath(p, REPO)


# ----------------------------------------------------------------------------------------------- plans
def load_plans():
    plans = {}
    for die, extra in DIES:
        path = f'physical/die_plan/{die}/die_plan.json'
        plans[die] = {'plan': path, 'extra': extra, 'data': jload(os.path.join(REPO, path))}
    for ref in ('origin/' + B2['branch'], B2['branch']):
        r = sh(['git', '-C', REPO, 'show', f'{ref}:{B2["path"]}'])
        if r.returncode == 0:
            c = sh(['git', '-C', REPO, 'rev-parse', '--short=10', ref]).stdout.strip()
            plans[B2['die']] = {'plan': f'{ref}@{c}:{B2["path"]}', 'extra': False, 'data': json.loads(r.stdout)}
            break
    else:
        print('WARN: B2r2 plan not found on', B2['branch'], file=sys.stderr)
    return plans


def plan_refs(plan):
    """-> {module: {'types': {type: n}, 'instances': n, 'hard': [hc...], 'contents': [c...]}} plus type counts."""
    used = collections.Counter(p['type'] for p in plan.get('partitions', []))
    refs = collections.defaultdict(lambda: {'types': collections.Counter(), 'htypes': collections.Counter(),
                                            'ctypes': collections.Counter(), 'hard': [], 'contents': []})
    for t, v in plan.get('partition_types', {}).items():
        n = used.get(t, 0)
        for h in v.get('hard_cores') or []:
            r = refs[h['module']]
            r['htypes'][t] += n          # one hard-core row per placed instance in the type
            r['hard'].append(h)
        for c in v.get('contents') or []:
            if not isinstance(c, dict):
                continue
            if c.get('status') in ('reuse', 'rework') and ('kit' in c or 'geom_pass' in c) or c.get('status') == 'reuse':
                r = refs[c['module']]
                r['ctypes'][t] += n
                r['contents'].append(c)
    for r in refs.values():
        # instances: hard-core rows when the module is a hard core, else contents rows (never both: a hard core's
        # module usually also appears as a contents row of the same type)
        r['types'] = r['htypes'] if r['hard'] else r['ctypes']
    return refs, used


def instances(r):
    # a module is counted from its hard-core rows when it has them (one row per placed instance), else contents
    return sum(r['types'].values()) if not r['hard'] else None


# ----------------------------------------------------------------------------------------------- repo index
class RepoIndex:
    def __init__(self):
        files = sh(['git', '-C', REPO, 'ls-files', 'physical', 'results']).stdout.split('\n')
        self.files = set(f for f in files if f)
        self.views = collections.defaultdict(list)          # module -> [view dir]
        for f in self.files:
            if f.endswith('.lef') and f.startswith('physical/') and '/provenance/' not in f and '.attempt' not in f:
                d, b = os.path.split(f)
                self.views[b[:-4]].append(d)
        self.dbfiles = collections.defaultdict(set)         # dir -> {6_final.odb ...}
        for f in self.files:
            b = os.path.basename(f)
            if re.match(r'6_final\.(odb|def|v|spef|sdc)(\.gz)?$', b) or b.endswith(('.odb', '.odb.gz', '.spef', '.spef.gz')):
                self.dbfiles[os.path.dirname(f)].add(b)
        self.verdicts = collections.defaultdict(list)       # block -> [verdict summary]
        self.by_job = {}
        for v in glob.glob(os.path.join(REPO, 'results/closure_loop/*/verdict.json')):
            j = jload(v)
            if not j:
                continue
            m = j.get('metrics') or {}
            s = {'job': j.get('job'), 'record': rel(v), 'status': j.get('status'), 'host': j.get('host'),
                 'run_dir': j.get('run_dir'), 'closed_at': j.get('closed_at'), 'ss_ps': m.get('ss_ps'),
                 'ff_ps': m.get('ff_ps'), 'drc': m.get('drc'), 'setup_corner': m.get('setup_corner'),
                 'ss_sensitivity_ps': m.get('ss_sensitivity_ps')}
            self.verdicts[j.get('block')].append(s)
            self.by_job[j.get('job')] = s

    def view_info(self, d):
        """Parse a view dir (physical/.../<m>/) for corners, records, recorded routed DB."""
        a = os.path.join(REPO, d)
        m = None
        lefs = [f for f in os.listdir(a) if f.endswith('.lef') and f != 'pin_only_tech.lef'] if os.path.isdir(a) else []
        if lefs:
            m = lefs[0][:-4]
        info = {'dir': d, 'lef': bool(lefs), 'lib': {c: os.path.exists(os.path.join(a, f'{m}_{c}.lib')) for c in ('ss', 'tt', 'ff')}}
        rec, db, notes = {}, {}, []
        parts = d.split('/')
        kit = None
        if len(parts) >= 5 and parts[1] == 'ref_tile' and parts[3] == 'views':
            kit = parts[2]
        for sf in ('SOURCE.txt', 'PROVENANCE', 'MANIFEST'):
            p = os.path.join(a, sf)
            if os.path.exists(p):
                txt = open(p, errors='replace').read()
                notes.append(f'{sf}: ' + txt.strip().split('\n')[0][:240])
                mk = re.search(r'physical/ref_tile/([^/\s]+)/', txt)
                if mk and not kit:
                    kit = mk.group(1)
                mh = re.search(r'\b(START|host)\s+(ot-[\w-]+|rtx-pro\w*|agidock\w*|localhost|epyc\d|intel\d)', txt)
                if mh:
                    db.setdefault('host', mh.group(2))
                mj = re.search(r'closed_archive\s+\S+/(\S+)', txt)
                if mj:
                    db.setdefault('job', mj.group(1))
        info['kit'] = kit
        if kit:
            kd = f'physical/ref_tile/{kit}'
            info['kit_dir'] = kd
            info['kit_in_repo'] = any(os.path.exists(os.path.join(REPO, kd, f)) for f in ('kit.env', 'spec.json', 'job.json'))
            g = jload(os.path.join(REPO, kd, 'gate_result.json'))
            if g:
                rec['gate_verdict'] = g.get('verdict')
                rec['gate_generated'] = g.get('generated')
                rec['gate_host'] = g.get('host')
                db.setdefault('host', g.get('host'))
                fails = [i.get('check') for i in g.get('items', []) if i.get('severity') == 'FAIL']
                if fails:
                    rec['gate_fail_checks'] = fails[:8]
        ins = jload(os.path.join(a, 'insertion.json'))
        if ins:
            if ins.get('base'):
                db['path'] = ins['base'] + '/' + (ins.get('db') or '6_final.odb')
            for c in ('ss', 'tt', 'ff'):
                b = (ins.get(c) or {}).get('boundary') or {}
                if b.get('max') is not None:
                    rec[f'ins_{c}_ps'] = b.get('mean')
                    rec[f'spread_{c}_ps'] = round(b['max'] - b['min'], 2)
        for c in ('ss', 'tt', 'ff'):
            p = os.path.join(a, f'export_{c}.tcl')
            if os.path.exists(p):
                mm = re.search(r'read_db\s+(\S+)', open(p, errors='replace').read())
                if mm:
                    db.setdefault('export_read_db', mm.group(1))
        cs = jload(os.path.join(a, 'corner_sta.json'))
        if cs:
            for k, nm in (('setup_ss', 'sta_setup_ss_ps'), ('hold_ff', 'sta_hold_ff_ps'), ('setup_tt', 'sta_setup_tt_ps')):
                if isinstance(cs.get(k), dict):
                    rec[nm] = cs[k].get('worst_slack_ps')
            if cs.get('orfs_dir'):
                db.setdefault('path', cs['orfs_dir'])
        ex = jload(os.path.join(a, 'export.json'))
        if ex:
            for c in ('ss', 'ff', 'tt'):
                e = ex.get(c)
                if isinstance(e, dict) and e.get('ws_max') is not None:
                    try:
                        rec[f'export_{c}_ws_max_ps'] = round(float(e['ws_max']) * 1e12, 2)
                        rec[f'export_{c}_ws_min_ps'] = round(float(e['ws_min']) * 1e12, 2)
                    except (TypeError, ValueError):
                        pass
            if ex.get('orfs_dir'):
                db.setdefault('path', ex['orfs_dir'])
        mj = re.search(r'closure-loop/([^/]+)/', db.get('path', ''))
        if mj:
            db['job'] = mj.group(1)
        if db.get('job') in self.by_job:
            v = self.by_job[db['job']]
            db['host'] = v['host']
            db['verdict_record'] = v['record']
            rec.update({'cl_status': v['status'], 'cl_ss_ps': v['ss_ps'], 'cl_ff_ps': v['ff_ps'], 'cl_drc': v['drc'],
                        'cl_closed_at': v['closed_at']})
        # routed DB committed next to the view / in the kit?
        here = set()
        for dd in [d] + ([info['kit_dir']] if kit else []):
            for k, v in self.dbfiles.items():
                if k == dd or k.startswith(dd + '/'):
                    here |= {f'{k}/{x}' for x in v}
        info['repo_db_files'] = sorted(here)
        info['record'], info['recorded_db'], info['notes'] = rec, db, notes
        return info


def repo_db_complete(files):
    names = [os.path.basename(f) for f in files]
    has = lambda pat: any(re.match(pat, n) for n in names)
    return has(r'6_final\.(odb|def)') and has(r'6_final\.v') and has(r'6_final\.spef')


# ----------------------------------------------------------------------------------------------- host scan
REMOTE = r'''
import json, os, re, subprocess, sys
cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.load(sys.stdin)
roots = [os.path.expanduser(r) for r in cfg['roots'] if os.path.exists(os.path.expanduser(r))]
prune = []
for p in cfg['prune']:
    prune += ['-name', p, '-o']
cmd = ['find', '-L'] + roots + ['-maxdepth', '14', '('] + prune[:-1] + [')', '-prune', '-o', '-path', '*/results/asap7/*/base/*.odb', '-printf', '%h\n']
out = subprocess.run(cmd, capture_output=True, text=True).stdout.split('\n') if roots else []
bases = {}
for b in out:
    if b and os.path.realpath(b) not in bases:
        bases[os.path.realpath(b)] = b
STAGES = ['1_synth', '2_floorplan', '3_place', '4_cts', '5_1_grt', '5_route', '6_1_fill', '6_final']
runs = []
for real, b in sorted(bases.items()):
    try:
        names = os.listdir(real)
    except OSError:
        continue
    design = os.path.basename(os.path.dirname(real))
    run = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(real))))
    final = {x: os.path.exists(os.path.join(real, '6_final.' + x)) for x in ('odb', 'def', 'v', 'sdc', 'spef')}
    stage = None
    for s in STAGES:
        if s + '.odb' in names:
            stage = s
    logd = os.path.join(run, 'logs', 'asap7', design, 'base')
    repd = os.path.join(run, 'reports', 'asap7', design, 'base')
    logs = sorted(x for x in (os.listdir(logd) if os.path.isdir(logd) else []) if x.startswith('6_report'))
    reps = sorted(x for x in (os.listdir(repd) if os.path.isdir(repd) else []) if 'drc' in x or x.startswith('6_finish'))
    drc = None
    p = os.path.join(repd, '5_route_drc.rpt')
    if os.path.exists(p):
        try:
            drc = sum(1 for l in open(p, errors='replace') if l.startswith('violation type'))
        except OSError:
            pass
    mt = max((os.path.getmtime(os.path.join(real, x)) for x in names), default=0)
    runs.append({'base': real, 'found_as': b, 'run': run, 'design': design, 'last_stage': stage, 'final': final,
                 'fill_6_1': sorted(x for x in names if x.startswith('6_1_')), 'report_logs': logs, 'reports': reps,
                 'drc_route_violations': drc, 'mtime': mt})
present = [p for p in cfg['paths'] if os.path.exists(p)]
print(json.dumps({'runs': runs, 'present_paths': present}))
'''


def scan_hosts(paths):
    cfg = json.dumps({'roots': SCAN_ROOTS, 'prune': PRUNE, 'paths': sorted(paths)})
    scan = {'generated': now(), 'hosts': {}}
    procs = {}
    for h in HOSTS:
        script = REMOTE
        cmd = ['python3', '-c', script, cfg] if h == 'localhost' else \
            ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', h, 'python3', '-', ]
        procs[h] = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if h != 'localhost':
            # remote: script on stdin needs argv; wrap it so config comes via an env-free literal
            procs[h].stdin.write(f'import sys\nsys.argv=["x", {cfg!r}]\n' + script)
        procs[h].stdin.close()
    for h, p in procs.items():
        try:
            out = p.stdout.read()
            p.wait(timeout=1800)
            scan['hosts'][h] = json.loads(out)
        except Exception as e:
            scan['hosts'][h] = {'error': f'{type(e).__name__}: {e}; {p.stderr.read()[-300:]}', 'runs': [], 'present_paths': []}
    return scan


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


# ----------------------------------------------------------------------------------------------- classify
def classify(module, r, idx):
    """-> (bucket, reason)"""
    notes = [h.get('note', '') for h in r['hard']] + [c.get('note', '') for c in r['contents']]
    lefs = [h.get('lef') for h in r['hard'] if h.get('lef')]
    vdirs = idx.views.get(module, [])
    macro_view = vdirs and all(MACRO_DIR_RE.match(d) for d in vdirs) and not idx.verdicts.get(module)
    if any(MACRO_DIR_RE.match(l) for l in lefs) or macro_view or (MACRO_NAME_RE.search(module) and not idx.verdicts.get(module)):
        return 'macro', 'ROM/PHY/PLL hard IP (abstract view only)'
    nc = [n for n in notes if NOT_CLOSED_RE.search(n)]
    claim = [n for n in notes if CLOSED_RE.search(n)]
    kitref = [c for c in r['contents'] if c.get('status') == 'reuse' and (c.get('kit') or c.get('geom_pass'))]
    evidence = any(not MACRO_DIR_RE.match(d) for d in idx.views.get(module, [])) or any(v['status'] == 'CLOSED' for v in idx.verdicts.get(module, []))
    if lefs:
        return 'closed', 'plan points at view ' + lefs[0]
    if kitref:
        c = kitref[0]
        return 'closed', f"reuse kit={c.get('kit')} geom_pass={c.get('geom_pass')}; plan note: {c.get('note', '')[:120]}"
    if nc:
        return 'not_closed', NOT_CLOSED_RE.search(nc[0]).group(0) + ': ' + nc[0][:160]
    if not r['hard'] and r['contents'] and all(c.get('status') != 'reuse' for c in r['contents']):
        c = r['contents'][0]
        return 'not_closed', f"contents status={c.get('status')} (kit={c.get('kit')}): {c.get('note', '')[:120]}"
    if claim:
        return 'closed', 'plan note: ' + claim[0][:160]
    if evidence:
        return 'closed', 'repo holds a closed view / CLOSED closure_loop verdict for the module'
    if r['hard']:
        return 'not_closed', 'hard core without closed evidence: ' + (notes[0][:160] if notes else '')
    return 'reuse_unverified', 'contents reuse, no closed claim, no view / verdict in repo'


def pick_view(module, r, idx):
    cands = list(dict.fromkeys(idx.views.get(module, [])))
    plan_dirs = [os.path.dirname(h['lef']) for h in r['hard'] if h.get('lef')]
    kit_hint = [c.get('kit') for c in r['contents'] if c.get('kit')]
    kit_hint += [m.group(1) for h in r['hard'] for m in [re.search(r'kit (\w+)', h.get('note', ''))] if m]
    order = []
    for d in plan_dirs:
        order.append(d)
    for k in kit_hint:
        mk = re.search(r'physical/ref_tile/([^\s/()]+)', k or '')
        name = mk.group(1) if mk else (k or '').split()[0] if k else None
        order += [d for d in cands if name and f'/ref_tile/{name}/' in d + '/']
    infos = {}
    for d in cands:
        infos[d] = None
    rest = sorted(cands, key=lambda d: (('/ref_tile/' not in d), d))
    order += rest
    order = list(dict.fromkeys(order))
    return order, plan_dirs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default='results/signoff_1024/inventory.json')
    ap.add_argument('--hosts-scan', help='cache json of the live-host search (read if present, written otherwise)')
    ap.add_argument('--rescan', action='store_true', help='ignore an existing --hosts-scan cache')
    ap.add_argument('--no-ssh', action='store_true')
    a = ap.parse_args()

    plans = load_plans()
    idx = RepoIndex()
    die_types = {die: set(p['data'].get('partition_types', {})) for die, p in plans.items() if p['data']}

    modules, dies = {}, {}
    for die, p in plans.items():
        plan = p['data']
        if not plan:
            continue
        refs, used = plan_refs(plan)
        dd = dies[die] = {'plan': p['plan'], 'extra': p['extra'], 'closed_modules': [], 'not_closed': [],
                          'macros': [], 'reuse_unverified': []}
        for m, r in sorted(refs.items()):
            n = sum(r['types'].values())
            bucket, why = classify(m, r, idx)
            row = {'module': m, 'instances': n, 'types': sorted(r['types']), 'reason': why}
            if bucket != 'closed':
                dd[{'not_closed': 'not_closed', 'macro': 'macros', 'reuse_unverified': 'reuse_unverified'}[bucket]].append(row)
                continue
            dd['closed_modules'].append(m)
            mod = modules.setdefault(m, {'dies': {}, 'refs': [], 'notes': []})
            mod['dies'][die] = {'types': sorted(r['types']), 'instances': n,
                                'source': sorted(set(['hard_cores'] * bool(r['hard']) + ['contents'] * bool(r['contents'])))}
            mod['refs'].append((die, r, why))
            pinned = [h.get('note', '') for h in r['hard'] if re.search(r're-pin|pins provisional|plan-derived pins|'
                                                                        r'top-down pins|plan-track', h.get('note', ''))]
            if pinned or (die == B2['die'] and r['hard']):
                mod['notes'].append(f'{die}: plan re-pins this hard core (plan-track / top-down pins); the closed view '
                                    'was hardened with its as-built pins, so the plan instance needs a re-harden to match')
            tags = sorted(set(re.findall(r'\((SYNAREA|YOSYS)\)', ' '.join(h.get('note', '') for h in r['hard']))))
            if tags:
                mod['notes'].append(f'{die}: plan cell count tagged {"/".join(tags)} (not taken from the closed record)')

    # ---- per module: view, records, recorded DB
    recorded_paths = set()
    for m, mod in modules.items():
        order, plan_dirs = [], []
        for die, r, why in mod['refs']:
            o, pd = pick_view(m, r, idx)
            order += o
            plan_dirs += pd
        order = list(dict.fromkeys(order))
        mod['reasons'] = sorted(set(f'{die}: {why}' for die, r, why in mod['refs']))
        prim = None
        infos = []
        for d in order:
            if os.path.isdir(os.path.join(REPO, d)):
                infos.append(idx.view_info(d))
        # primary: plan-given dir, else first with a recorded DB path, else first
        for i in infos:
            if i['dir'] in plan_dirs:
                prim = i
                break
        if not prim:
            prim = next((i for i in infos if i['recorded_db'].get('path')), infos[0] if infos else None)
        for d in plan_dirs:
            if not os.path.isdir(os.path.join(REPO, d)):
                mod['notes'].append(f'plan view dir {d} NOT in repo')
        vs = sorted(idx.verdicts.get(m, []), key=lambda v: v.get('closed_at') or '')
        mod['_prim'], mod['_alts'], mod['_verdicts'] = prim, [i['dir'] for i in infos if i is not prim], vs
        if prim and prim['recorded_db'].get('path'):
            recorded_paths.add(prim['recorded_db']['path'])
            recorded_paths.add(os.path.dirname(prim['recorded_db']['path']))
        if vs and vs[-1].get('run_dir'):
            recorded_paths.add(vs[-1]['run_dir'])

    # ---- host scan
    scan = None
    if a.hosts_scan and os.path.exists(a.hosts_scan) and not a.rescan:
        scan = jload(a.hosts_scan)
        if scan:
            print(f'hosts scan: cached {a.hosts_scan} ({scan.get("generated")})', file=sys.stderr)
    if scan is None and not a.no_ssh:
        print('hosts scan: searching', ', '.join(HOSTS), '...', file=sys.stderr)
        scan = scan_hosts(recorded_paths)
        if a.hosts_scan:
            os.makedirs(os.path.dirname(os.path.abspath(a.hosts_scan)), exist_ok=True)
            json.dump(scan, open(a.hosts_scan, 'w'), indent=1)
    present = collections.defaultdict(list)    # path -> [host]
    surviving = []
    if scan:
        for h, hs in scan['hosts'].items():
            for pth in hs.get('present_paths', []):
                present[pth].append(h)
            for run in hs.get('runs', []):
                surviving.append(dict(run, host=h))

    # map surviving runs -> module / partition type
    def run_target(run):
        d = run['design']
        mm = re.match(r'opentallas_(.+)_asap7_ref_(.+)$', d)
        if mm:
            return 'module', mm.group(1), mm.group(2)
        mm = re.match(r'(?:hc|kr)_(.+?)(__[\d_x]+)?$', d)
        if mm:
            return 'module', mm.group(1), None
        mm = re.match(r'dp_(.+)$', d)
        if mm:
            t = mm.group(1)
            ds = [die for die, ts in die_types.items() if t in ts]
            return 'partition', t, ','.join(ds) or None
        return 'unknown', d, None

    srv_out = []
    for run in sorted(surviving, key=lambda r: (r['host'], r['base'])):
        kind, tgt, extra = run_target(run)
        routed = bool(run['final'].get('odb'))
        complete = routed and run['final'].get('v') and run['final'].get('spef') and run['final'].get('sdc')
        age_h = (datetime.datetime.now().timestamp() - run['mtime']) / 3600 if run.get('mtime') else None
        state = ('routed (6_final odb/v/sdc/spef)' if complete else 'routed, incomplete final set') if routed else \
            f"in-flight / partial (last stage {run['last_stage']})"
        rr = {'host': run['host'], 'path': run['run'], 'base': run['base'], 'kind': kind, 'target': tgt,
              'job_or_die': extra, 'files': {'6_final': run['final'], '6_1': run['fill_6_1'], 'logs_6_report': run['report_logs'],
                                             'reports_drc': run['reports']},
              'last_stage': run['last_stage'], 'drc_route_violations': run['drc_route_violations'],
              'mtime': datetime.datetime.fromtimestamp(run['mtime']).astimezone().isoformat(timespec='minutes') if run.get('mtime') else None,
              'age_h': round(age_h, 1) if age_h is not None else None, 'state': state,
              'closed_module': tgt if (kind == 'module' and tgt in modules) else None}
        if kind == 'partition':
            rr['note'] = 'partition-level G3 kit run (die partition, not a hardened block referenced as closed)'
        elif kind == 'module' and tgt not in modules:
            nc = [die for die, dd in dies.items() if any(x['module'] == tgt for x in dd['not_closed'])]
            rr['note'] = (f'plan lists the module as not_closed on {",".join(nc)} (hardening in progress)' if nc else
                          'module not referenced by any current plan (sub-core / recovery run)')
        if not routed or (age_h is not None and age_h < 2):
            rr['note'] = (rr.get('note', '') + '; in-flight, not closed').lstrip('; ')
        srv_out.append(rr)

    # ---- finalize module records
    out_mods = {}
    for m in sorted(modules):
        mod = modules[m]
        prim, vs = mod['_prim'], mod['_verdicts']
        rec = dict(prim['record']) if prim else {}
        rdb = dict(prim['recorded_db']) if prim else {}
        if vs:
            last = vs[-1]
            rec.setdefault('cl_status', last['status'])
            rec.setdefault('cl_ss_ps', last['ss_ps'])
            rec.setdefault('cl_ff_ps', last['ff_ps'])
            rec.setdefault('cl_drc', last['drc'])
            rec['cl_records'] = len(vs)
            rec['cl_latest'] = {k: last[k] for k in ('job', 'record', 'host', 'run_dir', 'closed_at')}
            if not rdb.get('path'):
                rdb = {'host': last['host'], 'path': last['run_dir'], 'job': last['job'], 'from': 'closure_loop verdict (latest)'}
        notes = list(mod['notes']) + mod['reasons']
        if prim:
            notes += prim['notes']
        if mod['_alts']:
            notes.append(f"{len(mod['_alts'])} other view dir(s) of this module in repo: " + ', '.join(mod['_alts'][:4]))
        db_status, db = 'LOST', None
        if prim and repo_db_complete(prim['repo_db_files']):
            db_status, db = 'repo', {'host': 'repo', 'path': prim['dir'], 'files': prim['repo_db_files']}
        else:
            for pth in (rdb.get('path'), os.path.dirname(rdb.get('path') or '') or None, (rec.get('cl_latest') or {}).get('run_dir')):
                if pth and present.get(pth):
                    db_status, db = 'present', {'host': present[pth][0], 'path': pth, 'files': None}
                    break
            if db_status == 'LOST':
                runs = [r for r in srv_out if r['closed_module'] == m and r['files']['6_final'].get('odb')]
                if runs:
                    r = runs[0]
                    db_status = 'present'
                    db = {'host': r['host'], 'path': r['path'], 'files': r['files'],
                          'note': 'surviving routed run of the same module (not necessarily the recorded closed run)'}
        if db_status == 'LOST' and not scan:
            db_status = 'unscanned'
        if prim and prim['repo_db_files'] and db_status != 'repo':
            notes.append('partial DB files in repo: ' + ', '.join(prim['repo_db_files'][:3]))
        if rdb.get('host') and OLD_HOST_RE.match(str(rdb['host'])) and db_status == 'LOST':
            notes.append(f"recorded host {rdb['host']} is old fleet (wiped)")
        if not prim and not vs:
            notes.append('no view dir and no closure_loop verdict for this module in repo')
        views = None
        if prim:
            views = {'dir': prim['dir'], 'lef': prim['lef'], 'lib': prim['lib']}
        kit = prim.get('kit') if prim else None
        out_mods[m] = {
            'dies': mod['dies'],
            'kit': kit,
            'ref_dir': prim.get('kit_dir') if prim else None,
            'kit_in_repo': prim.get('kit_in_repo', False) if prim else False,
            'views': views,
            'record': rec,
            'recorded_db': {k: rdb.get(k) for k in ('host', 'path', 'job', 'export_read_db', 'verdict_record', 'from') if rdb.get(k)},
            'db_status': db_status,
            'db': db,
            'status': 'DATA' if db_status in ('repo', 'present') else ('NEEDS RE-RUN' if db_status == 'LOST' else 'UNKNOWN'),
            'notes': notes,
        }

    commit = sh(['git', '-C', REPO, 'rev-parse', '--short=10', 'HEAD']).stdout.strip()
    origin_main = sh(['git', '-C', REPO, 'rev-parse', '--short=10', 'origin/main']).stdout.strip()
    summary = {}
    for die, dd in dies.items():
        cm = dd['closed_modules']
        summary[die] = {'closed': len(cm),
                        'closed_instances': sum(out_mods[m]['dies'][die]['instances'] for m in cm),
                        'DATA': sum(out_mods[m]['status'] == 'DATA' for m in cm),
                        'NEEDS_RE_RUN': sum(out_mods[m]['status'] == 'NEEDS RE-RUN' for m in cm),
                        'kit_in_repo': sum(bool(out_mods[m]['kit_in_repo']) for m in cm),
                        'not_closed': len(dd['not_closed']), 'macros': len(dd['macros']),
                        'reuse_unverified': len(dd['reuse_unverified'])}
    inv = {
        'schema': 'opentallas.signoff.inventory.v1',
        'generated': now(),
        'main_commit': origin_main,
        'worktree_commit': commit,
        'tool': 'tools/die_plan/signoff_inventory.py',
        'hosts_scan': {'generated': scan.get('generated') if scan else None, 'hosts': HOSTS, 'roots': SCAN_ROOTS,
                       'pruned': PRUNE, 'errors': {h: hs.get('error') for h, hs in (scan or {'hosts': {}})['hosts'].items() if hs.get('error')}},
        'classification': {
            'closed': CLOSED_RE.pattern + ' | plan lef/lib path | reuse with kit/geom_pass | repo view or CLOSED closure_loop verdict',
            'not_closed': NOT_CLOSED_RE.pattern + ' (without a plan view path) | hard core without closed evidence',
            'macro': 'lef under physical/asap7_{memory_macros,v41x_pdie_macros}* or name ' + MACRO_NAME_RE.pattern,
            'db_status': 'repo = 6_final odb|def + v + spef in git; present = found on a live host now; LOST = neither',
            'die_contracts': 'results/fleet_viz/die_contracts.json (fleet-viz registry, 2026-10-15) predates the current die '
                             'plans; not used as a module source here',
        },
        'summary': summary,
        'dies': dies,
        'modules': out_mods,
        'surviving_runs': srv_out,
    }
    outp = os.path.join(REPO, a.out) if not os.path.isabs(a.out) else a.out
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    with open(outp, 'w') as f:
        json.dump(inv, f, indent=1, sort_keys=False)
        f.write('\n')

    # ---- summary table
    print(f'{"die":14s} {"closed":>6s} {"inst":>6s} {"DATA":>5s} {"RE-RUN":>6s} {"kit@repo":>8s} {"not_closed":>10s} {"macro":>5s} {"reuse?":>6s}')
    for die, s in summary.items():
        tag = ' (extra)' if dies[die]['extra'] else ''
        print(f'{die:14s} {s["closed"]:6d} {s["closed_instances"]:6d} {s["DATA"]:5d} {s["NEEDS_RE_RUN"]:6d} {s["kit_in_repo"]:8d} '
              f'{s["not_closed"]:10d} {s["macros"]:5d} {s["reuse_unverified"]:6d}{tag}')
    data = [(m, r) for m, r in out_mods.items() if r['status'] == 'DATA']
    print(f'\nmodules with DATA ({len(data)}):')
    for m, r in data:
        print(f'  {m}: {r["db_status"]} {r["db"]["host"]}:{r["db"]["path"]}')
    routed = [r for r in srv_out if r['files']['6_final'].get('odb')]
    print(f'\nsurviving routed runs ({len(routed)} with 6_final.odb, {len(srv_out)} run dirs total):')
    for r in routed:
        print(f'  {r["host"]}:{r["path"]}  [{r["kind"]} {r["target"]}] {r["state"]}')
    print(f'\nwrote {rel(outp)}')


if __name__ == '__main__':
    main()
