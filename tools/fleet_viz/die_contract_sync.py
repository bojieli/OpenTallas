#!/usr/bin/env python3
"""Regenerate the fleet-viz die contracts from the CURRENT die netlists / bind tables (FLEETVIZ-ELEM 2026-10-18).

results/fleet_viz/die_contracts.json was hand-registered 10-17 for old die revisions and joined to jobs by exact name,
so renamed or replaced kits read 'not started'.  This tool (run hourly by fleet-viz-elem-sync.timer) writes
{state}/die_contracts_live.json, which die_contracts.py prefers over the committed file:

  designs     one per die from results/fleet_viz/die_sources.json (origin/main, else the copy beside this tool): the die
              masters of the current revision's strict port-bind / bind table / compose contract ('add' entries with
              role master / leaf / macro and the parent), and 'retire' entries for elements the revision replaced
              (frame_members 'replaces', compose 'remastered X -> Y', retired masters, binding 'from', curated
              'supersede') so the old element reads 'superseded by X'.
  aliases     element -> [job blocks] that implement it under another name, derived automatically from
                - the native audit (margin_live.json: a CLOSED view's LEF cell = the element, its job's block),
                - bind-table / port-bind view notes (job names, physical/ref_tile/<kit> paths),
                - closure-loop job specs (record 'to' physical/ref_tile/<kit>/views, lint top 'module ot_lint_top; X u_top'),
                - ref_tile kit specs committed on any ref in the last KIT_DAYS days (spec top -> kit),
              plus curated die_sources.json 'aliases'.
  kits        element -> [kit dirs] with a committed ref_tile kit but no closure-loop job yet (the viewer shows
              'kit prepared, no route job', not 'not started').
  supersede   job-spec 'structural_change' texts '<new> replaces <old>' -> old element superseded by the job's block.

    die_contract_sync.py [--repo /home/ubuntu/OpenTallas] [--state ~/.local/state/fleet-viz]
"""
import argparse, collections, datetime, gzip, json, os, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
JOBS = pathlib.Path(os.environ.get('CL_STATE', str(pathlib.Path.home() / '.local/state/closure_loop'))) / 'jobs'
SOURCES = 'results/fleet_viz/die_sources.json'
KIT_DAYS = 10
STD_RE = re.compile(r'_ASAP7_|^(TAPCELL|FILLER|DECAP)')
NAME_RE = re.compile(r'[A-Za-z_]\w*$')
# PHY / analog models and bumps (only modelled, never hardened: role 'macro', no row of their own)
PHY_RE = re.compile(r'(hbm3e_phy|ucie_x64_phy|serdes_112g_x12_phy|outline_marker|^qfd_(ckbump|sigbump|clkrx)$|'
                    r'^qkd_(ckbump|fwdbump)$|_bb$|ot_s81_pma_bm|hbm3e_dev_bm|pll_analog_model)')
JOBNAME_RE = re.compile(r'\b([A-Za-z][A-Za-z0-9_]*-[A-Za-z0-9_]+-[0-9a-f]{9}(?:-[A-Za-z0-9_]+)?)\b')
KIT_RE = re.compile(r'physical/ref_tile/([A-Za-z0-9_]+)')
REPL_RE = re.compile(r'\b([A-Za-z_]\w{3,})\s+replaces\s+([A-Za-z_]\w{3,})')
REMASTER_RE = re.compile(r'remastered\s+([A-Za-z_]\w+)\s*->\s*([A-Za-z_]\w+)')


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


class Git:
    def __init__(self, repo):
        p = pathlib.Path(repo)
        self.gd = str(p / '.git') if (p / '.git').exists() else str(p)
        self.batch = None

    def run(self, *a, timeout=900):
        return subprocess.run(['git', '--git-dir', self.gd, *a], capture_output=True, text=True, timeout=timeout).stdout

    def blob(self, spec):
        if self.batch is None or self.batch.poll() is not None:
            self.batch = subprocess.Popen(['git', '--git-dir', self.gd, 'cat-file', '--batch'], stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE)
        p = self.batch
        p.stdin.write((spec + '\n').encode()); p.stdin.flush()
        head = p.stdout.readline().decode().split()
        if len(head) != 3: return None
        data = p.stdout.read(int(head[2])); p.stdout.read(1)
        return data if head[1] == 'blob' else None


def loads(data, name=''):
    if data is None: return None
    if name.endswith('.gz') or data[:2] == b'\x1f\x8b': data = gzip.decompress(data)
    return json.loads(data)


def read_source(git, ref, src, cache_dir):
    """-> (doc, where) for the first readable alternative of a source."""
    for alt in src.get('any') or [src]:
        if alt.get('path'):
            d = git.blob('%s:%s' % (alt.get('ref', ref), alt['path']))
            if d is not None: return loads(d, alt['path']), '%s:%s' % (alt.get('ref', ref), alt['path'])
        elif alt.get('file'):
            p = pathlib.Path(alt['file'])
            if p.exists(): return loads(p.read_bytes(), str(p)), str(p)
        elif alt.get('remote'):
            host, path = alt['remote'].split(':', 1)
            c = cache_dir / re.sub(r'[^A-Za-z0-9_.-]', '_', alt['remote'])
            try:
                r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', host, 'cat', path],
                                   capture_output=True, timeout=120)
                if r.returncode == 0 and r.stdout: c.write_bytes(r.stdout)
            except Exception as e:  # noqa: BLE001
                log('remote %s: %s' % (alt['remote'], e))
            if c.exists(): return loads(c.read_bytes(), path), alt['remote'] + (' (cached %s)' % time.strftime(
                '%m-%d %H:%M', time.localtime(c.stat().st_mtime)))
    return None, None


# ---------------------------------------------------------------- per-source element extraction
def ex_port_bind(doc):
    out = []
    for m, v in (doc.get('masters') or {}).items():
        if STD_RE.search(m): continue
        cls = v.get('kind') or v.get('cls') or ''
        role = 'macro' if cls in ('model', 'HARD_PHY') or PHY_RE.search(m) else 'master'
        out.append(dict(element=m, role=role, note=' '.join(str(v.get(k) or '') for k in ('note', 'view')),
                        verdict=v.get('verdict') or cls, module=v.get('module')))
    return out, []


def ex_s81_bind_table(doc):
    out, retire = [], []
    for m, v in (doc.get('masters') or {}).items():
        out.append(dict(element=m, role='master', note='%s %s' % (v.get('view') or '', v.get('view_note') or ''), module=v.get('module')))
    for m, v in (doc.get('relay_views') or {}).items():
        out.append(dict(element=m, role='master', note=str(v)))
    for fm in doc.get('frame_members') or []:
        out.append(dict(element=fm['master'], role='leaf', parent='col_h9', note=str(fm.get('view') or '')))
        if fm.get('replaces'): retire.append(dict(old=fm['replaces'], by=fm['master'], reason='frame member %s replaces it (%s)'
                                                  % (fm['master'], fm.get('decision') or 'bind table')))
    for m, v in (doc.get('child_views') or {}).items():
        par = str(v.get('parent') or '')
        pm = re.findall(r'[A-Za-z_]\w+', par)
        p = next((w for w in pm if w in (doc.get('masters') or {})), None) or (pm[-1] if pm and '->' in par else (pm[0] if pm else None))
        out.append(dict(element=m, role='leaf', parent=p, note=str(v.get('view') or '')))
    for m, why in (doc.get('child_views_owed') or {}).items():
        out.append(dict(element=m, role='leaf', parent=None, note='OWED: %s' % why))
    for m, v in (doc.get('relay_views_retired') or {}).items():
        retire.append(dict(old=m, by=(v.get('by') if isinstance(v, dict) else None) or 'p4l relay views',
                           reason='retired relay view: %s' % (json.dumps(v)[:160] if not isinstance(v, str) else v)))
    return out, retire


def ex_hbm_contract(doc):
    out, retire, seen = [], [], set()
    masters = doc.get('masters') or {}
    for i, v in (doc.get('instances') or {}).items():
        m = v.get('master')
        for a, b in REMASTER_RE.findall(str(v.get('note') or '')):
            if a not in masters: retire.append(dict(old=a, by=b, reason='d4g compose: remastered %s -> %s' % (a, b)))
        if not m or m in seen: continue
        seen.add(m)
        out.append(dict(element=m, role='macro' if PHY_RE.search(m) else 'master',
                        note=str(v.get('note') or '')[:300], rtl=v.get('source')))
    for m in masters:
        if m not in seen: out.append(dict(element=m, role='master', note=''))
    for r in doc.get('retired_v15') or []:
        m = r.get('master')
        if m and m not in masters:
            why = str(r.get('reason') or '')
            by = re.search(r'(?:successor\s*=|replaced by)\s*([^;(]+)', why)
            retire.append(dict(old=m, by=(by.group(1).strip()[:80] if by else 'd4g GEN1 contract'), reason='d4g: ' + why[:240]))
    for sp in doc.get('soft_parents') or []:
        for ch in (sp.get('children') or {}).values():
            out.append(dict(element=ch, role='leaf', parent=sp.get('master'), note='contract soft_parents'))
    return out, retire


def ex_view_bindings(doc):
    out = []
    for c in doc.get('cells') or []:
        m = re.sub(r'__pv\d+$', '', c.get('master') or '')
        if m: out.append(dict(element=m, role='master', note='%s %s' % (c.get('status') or '', c.get('view') or ''),
                              status=c.get('status')))
    return out, []


def ex_binding_replace(doc):
    out, retire = [], []
    for i, v in (doc.get('instances') or {}).items():
        m = v.get('master'); fr = re.match(r'\s*([A-Za-z_]\w+)', str(v.get('from') or ''))
        if not m: continue
        out.append(dict(element=m, role='master', note=str(v.get('view') or '')))
        if fr and fr.group(1) != m:
            retire.append(dict(old=fr.group(1), by=m, reason='%s: %s replaces %s' % (doc.get('lane') or 'binding', m, fr.group(1))))
    return out, retire


def ex_gen1_plan(doc):
    out = []
    for u in doc.get('bind_closed') or []:
        for m in u.get('masters') or []:
            vs = [v for v in u.get('views') or [] if v.rstrip('/').endswith('/' + m)]   # this master's own view only
            out.append(dict(element=m, role='master', note=' '.join(vs)))
    for u in doc.get('bind_pending') or []:
        kits = u.get('kit') if isinstance(u.get('kit'), list) else [u.get('kit')]
        for k in kits:
            if k: out.append(dict(element=None, kit=os.path.basename(k), note=str(u.get('status') or '')))
    return out, []


EXTRACT = dict(port_bind=ex_port_bind, s81_bind_table=ex_s81_bind_table, hbm_contract=ex_hbm_contract,
               view_bindings=ex_view_bindings, binding_replace=ex_binding_replace, gen1_plan=ex_gen1_plan)


# ---------------------------------------------------------------- job / kit / audit indices
def job_index():
    """-> blocks(set), job->block, kit->set(blocks), top->set(blocks), replaces [(old, new block, job)], status per block"""
    blocks, jb, kit, top, repl = set(), {}, collections.defaultdict(set), collections.defaultdict(set), []
    for f in os.scandir(JOBS):
        if not f.name.endswith('.json'): continue
        try: d = json.loads(pathlib.Path(f.path).read_text())
        except (OSError, ValueError): continue
        s = d.get('spec') or {}; b = s.get('block')
        if not b: continue
        blocks.add(b); jb[d.get('name') or f.name[:-5]] = b
        for r in s.get('record') or []:
            m = KIT_RE.match(str(r.get('to', '')) if isinstance(r, dict) else '')
            if m: kit[m.group(1)].add(b)
        t = json.dumps(s.get('stages') or {})
        m = re.search(r'ot_lint_top; ([A-Za-z_]\w*) u_top', t)
        if m and m.group(1) != b: top[m.group(1)].add(b)
        for new, old in REPL_RE.findall(str(s.get('structural_change') or '')):
            repl.append((old, b, d.get('name')))
    return blocks, jb, kit, top, repl


def kit_specs(git, days=KIT_DAYS):
    """kit dir -> spec top, from ref_tile spec.json changed on any ref in the last `days` days, plus origin/main."""
    out = {}
    for ln in git.run('ls-tree', '-r', 'origin/main', 'physical/ref_tile/').splitlines():
        meta, _, path = ln.partition('\t')
        if path.endswith('/spec.json') and path.count('/') == 3:
            out.setdefault(path.split('/')[2], meta.split()[2])
    raw = git.run('log', '--all', '--since=%d.days' % days, '--format=', '--raw', '--no-abbrev', '--diff-filter=AM', '--',
                  'physical/ref_tile/*/spec.json')
    for ln in raw.splitlines():
        if not ln.startswith(':'): continue
        meta, _, path = ln.partition('\t')
        if path.count('/') == 3: out.setdefault(path.split('/')[2], meta.split()[3])
    tops = {}
    for k, blob in out.items():
        try: tops[k] = (json.loads(git.blob(blob) or b'{}') or {}).get('top')
        except ValueError: pass
    return tops


def rule_alias(e, cfg):
    """naming rules of renamed kits: the lower-case block name and die_sources 'alias_rules' [[regex, replacement]]"""
    out = {e.lower()}
    for rx, rp in cfg.get('alias_rules') or []:
        n = re.sub(rx, rp, e)
        if n != e: out |= {n, n.lower()}
    out.discard(e)
    return out


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', default='/home/ubuntu/OpenTallas')
    ap.add_argument('--state', default=os.path.expanduser('~/.local/state/fleet-viz'))
    a = ap.parse_args(argv)
    t0 = time.time(); state = pathlib.Path(a.state); state.mkdir(parents=True, exist_ok=True)
    cache_dir = state / 'die_inputs'; cache_dir.mkdir(exist_ok=True)
    git = Git(a.repo)
    raw = git.blob('origin/main:' + SOURCES)
    cfg = json.loads(raw) if raw else json.loads((HERE.parents[1] / SOURCES).read_text() if (HERE.parents[1] / SOURCES).exists()
                                                 else (HERE / 'die_sources.json').read_text())
    blocks, jb, kitb, topb, repl = job_index()
    tops = kit_specs(git)
    kits_of = collections.defaultdict(set)
    for k, t in tops.items():
        if t: kits_of[t].add(k)
    try: margin = json.loads((state / 'margin_live.json').read_text()).get('views', [])
    except (OSError, ValueError): margin = []
    cell_blocks = collections.defaultdict(set)
    for v in margin:
        b = jb.get(v.get('job') or '')
        if b and v.get('cell') and v['cell'] != b: cell_blocks[v['cell']].add(b)

    designs, all_elems, retire_all, notes, fam_kits = [], set(), [], collections.defaultdict(list), {}
    for d in cfg['designs']:
        out = dict(design=d['design'], label=d['label'], target=d['target'], revision=d['revision'], lead=d.get('lead'),
                   complete=bool(d.get('complete')), doc=d.get('doc'), ref=d.get('ref'), add=[], retire=[], evidence_sources=[],
                   errors=[], streams=d.get('streams', []))
        got, prev, same = {}, [], {}
        for src in d['sources']:
            doc, where = read_source(git, d.get('ref', 'origin/main'), src, cache_dir)
            if doc is None:
                out['errors'].append(dict(source=src, error='unreadable')); continue
            els, ret = EXTRACT[src['kind']](doc)
            out['evidence_sources'].append(dict(kind=src['kind'], where=where, n=len(els), use=src.get('use', 'add')))
            if src.get('use') == 'previous':     # an older bind of this die: its masters the current bind dropped are retired
                prev.extend((e['element'], where) for e in els if e.get('element')); continue
            for e in els:
                if e.get('element') and not NAME_RE.match(e['element']): continue
                if src.get('use') == 'annotate':  # status / notes only: a superseded generation must not add masters
                    if e.get('element') in got:
                        if e.get('status'): got[e['element']]['binding'] = e['status']
                        notes[e['element']].append(e.get('note') or '')
                    continue
                if not e.get('element'):
                    if e.get('kit'): notes['__kits__'].append((e['kit'], e.get('note')))
                    continue
                x = got.setdefault(e['element'], dict(element=e['element'], role=e['role'], parent=e.get('parent'),
                                                      evidence='%s (%s)' % (d['revision'].split(' ')[0], where)))
                if e['role'] == 'master' and x['role'] in ('leaf', 'macro') and not e.get('parent'): x['role'] = 'master'; x['parent'] = None
                if e.get('rtl') and not x.get('rtl'): x['rtl'] = e['rtl']
                if e.get('status'): x['binding'] = e['status']
                notes[e['element']].append(e.get('note') or '')
                if e.get('module') and e['module'] != e['element']:
                    notes[e['element']].append('module ' + e['module']); same[e['module']] = e['element']
            for r in ret: r['design'] = d['design']; r['evidence'] = where
            retire_all.extend(ret)
        # a parent named by a leaf that is not itself a die master: keep the leaf as a master of this die
        for x in got.values():
            if x['role'] == 'leaf' and x.get('parent') and x['parent'] not in got: x['parent'] = None; x['role'] = 'master'
            if x['role'] == 'leaf' and not x.get('parent'): x['role'] = 'master'
        # one element under two names (bind-table master Y = RTL module X): keep the RTL module name (jobs, kits and
        # contract leaves use it) unless only Y has a job
        for m, y in same.items():
            if m in got and y in got and m != y:
                keep, drop = (y, m) if (y in blocks and m not in blocks) else (m, y)
                notes[keep] += notes.get(drop, []); del got[drop]
        for x in got.values():
            if PHY_RE.search(x['element']): x['role'] = 'macro'
        for e, where in prev:
            if e not in got and not PHY_RE.search(e):
                v = (cfg.get('supersede') or {}).get(e) or {}
                retire_all.append(dict(old=e, by=v.get('by') or 'current %s bind' % d['revision'].split(' ')[0], design=d['design'],
                                       reason=v.get('reason') or 'master of the previous bind (%s), not in the current bind' % where, evidence=where))
        # GEN-generated families (forwarded-lane relays / landings): members with no job of their own (nor a rule alias)
        # are one family element, so 157 generated frame masters do not read as 157 'not started' rows
        for fam in d.get('families') or []:
            rx = re.compile(fam['pattern'])
            mem = [e for e in got if rx.search(e) and not ({e} | rule_alias(e, cfg)) & blocks]
            if not mem: continue
            for e in mem: del got[e]
            got[fam['element']] = dict(element=fam['element'], role='master', parent=None,
                                       evidence='%s: %d GEN masters without their own job (%s ...) | %s' % (
                                           d['revision'].split(' ')[0], len(mem), ', '.join(sorted(mem)[:4]), fam.get('note', '')))
            fam_kits[fam['element']] = sorted(k for k in tops if fam.get('kit_pattern') and re.search(fam['kit_pattern'], k))
        out['add'] = sorted(got.values(), key=lambda x: x['element'])
        all_elems |= set(got)
        designs.append(out)

    # ---- aliases: element -> job blocks under another name
    aliases, kits = {}, {}
    curated = cfg.get('aliases') or {}
    for e in sorted(all_elems):
        al = set()
        al |= cell_blocks.get(e, set()) | topb.get(e, set())
        txt = ' '.join(notes.get(e, []))
        for j in JOBNAME_RE.findall(txt):
            if j in jb: al.add(jb[j])
            else:
                b = j.rsplit('-', 2)[0]
                if b in blocks: al.add(b)
        ks = set(KIT_RE.findall(txt)) | kits_of.get(e, set())
        for k in ks:
            al |= kitb.get(k, set())
            if k in blocks: al.add(k)
        al |= set(curated.get(e) or []) | rule_alias(e, cfg)
        al.discard(e)
        al = {b for b in al if b in blocks and b not in all_elems}   # another current die element is its own row
        if al: aliases[e] = sorted(al)
        ks |= set(fam_kits.get(e) or [])
        if e not in blocks and not al and ks: kits[e] = sorted(ks)

    # ---- supersession: old element -> successor (never an element of a current die)
    sup = {}
    for r in retire_all:
        if r['old'] not in all_elems: sup.setdefault(r['old'], dict(by=r['by'], reason=r['reason'], evidence=r.get('evidence'), design=r.get('design')))
    for old, v in (cfg.get('supersede') or {}).items():
        if old not in all_elems: sup.setdefault(old, dict(by=v.get('by'), reason=v.get('reason'), evidence=SOURCES + ' supersede'))
    cur_alias = {b for v in aliases.values() for b in v}
    for old, new_block, job in repl:
        if old not in all_elems and old not in cur_alias and old != new_block:
            sup.setdefault(old, dict(by=new_block, reason='job %s structural_change: %s replaces %s' % (job, new_block, old),
                                     evidence='closure-loop job spec ' + str(job)))
    by_design = collections.defaultdict(list)
    for old, v in sorted(sup.items()):
        dsg = v.get('design') or next((d['design'] for d in designs if any(x['element'] == v['by'] for x in d['add'])), None) \
            or designs[0]['design']
        by_design[dsg].append(dict(elements=[old], by=v['by'], reason=v['reason'], evidence=v.get('evidence')))
    for d in designs: d['retire'] = by_design.get(d['design'], [])

    doc = dict(schema='opentallas.fleet_viz.die_contracts.live.v1', generator='tools/fleet_viz/die_contract_sync.py',
               generated=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
               doc='Generated hourly from %s (current die revisions). The viewer prefers this file over results/fleet_viz/die_contracts.json.' % SOURCES,
               designs=designs, aliases=aliases, kits=kits,
               counts={d['design']: dict(elements=len(d['add']), retire=len(d['retire']), errors=len(d['errors'])) for d in designs})
    doc['counts']['aliases'] = len(aliases); doc['counts']['kits'] = len(kits)
    p = state / 'die_contracts_live.json'; tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(doc, indent=1) + '\n'); tmp.replace(p)
    log('die_contracts_live.json: %s (%.0f s)' % (json.dumps(doc['counts']), time.time() - t0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
