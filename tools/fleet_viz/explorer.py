"""Chip Explorer back end for the fleet visualiser (/explorer page, /api/explorer/*).

Joins three sources:
  * die geometry exported from the die recipes (explorer_geom.py; cache <state>/explorer/geom/<die>.json.gz, re-exported
    in a niced subprocess when a die's recipe commit changes);
  * the per-element closure status table (elements.py) and the closure-loop job files (full history per element);
  * curated stories (stories/*.json) and the name decoder (explorer_names.json).

Element <-> die master mapping (per die): the element IS a master of the die; or one of its jobs records its view into a
directory named after a master (spec.record[].to); or its view index lists it as a tile of a master; or its job purpose
names a master ("hfd_su_full slot ...").  A master's map status is its own element's status, else the roll-up of the
elements mapped into it, else its view-index status (closed view / interim / reservation / macro), else 'placeholder'.

Map status keys: closed, below (closed below the +15 ps design margin), running, failing, revoked, superseded,
placeholder (no closure-loop element, generated placeholder or interim view), macro (hard macro), relay (generated die
register hop with no element of its own).
"""
import collections, gzip, json, os, pathlib, re, shutil, subprocess, sys, threading, time

import explorer_geom as G

HERE = pathlib.Path(__file__).resolve().parent
STATUS_KEYS = ['closed', 'below', 'running', 'failing', 'revoked', 'superseded', 'placeholder', 'macro', 'relay']
STATUS_LABEL = dict(closed='closed', below='closed below margin (<+15 ps)', running='running (first trial)',
                    failing='failing / re-running', revoked='revoked', superseded='superseded',
                    placeholder='placeholder (no closed view)', macro='hard macro', relay='die relay / wire stage')
CAT_STATUS = {'closed (TT era)': 'closed', 'closed (TT re-verified)': 'closed', 'closed (earlier)': 'closed',
              'first trial in flight': 'running', 'failed, re-running': 'failing', 'revoked, re-running': 'revoked',
              'revoked (no live job)': 'revoked', 'needs redesign (no live job)': 'failing',
              'flow failure (no live job)': 'failing', 'cancelled only': 'failing', 'superseded': 'superseded'}
ROLL = ['failing', 'revoked', 'running', 'below', 'closed', 'superseded']
MARGIN = 15.0
MASTER_TOKEN = re.compile(r'\b((?:hfd|qfd|dsfd)_[A-Za-z0-9_]+)')
LIVE = {'QUEUED', 'SYNC', 'READY', 'RUNNING', 'ECO', 'MIGRATING'}


def _ts(s):
    import datetime
    try: return datetime.datetime.fromisoformat(s).timestamp()
    except Exception: return 0.0


def _f(x):
    try: return round(float(x), 2)
    except (TypeError, ValueError): return None


class Explorer:
    def __init__(self, repo, state, jobs_dir, elements, log=print, check_every=600):
        self.repo = pathlib.Path(repo); self.state = pathlib.Path(state); self.jobs_dir = pathlib.Path(jobs_dir)
        self.E = elements; self.log = log; self.check_every = check_every
        self.lock = threading.Lock(); self.geom = {}; self.exporting = None; self.export_err = {}; self.want = {}
        self.jcache = {}; self.meta = None; self.meta_t = 0; self.safe_geom = {}
        self.names = self._load_names(); self.names_mt = 0
        threading.Thread(target=self.run, daemon=True, name='explorer').start()

    # ------------------------------------------------------------------ geometry cache / refresh
    def dies(self):
        try: return G.load_dies()
        except Exception as e: self.log('explorer dies: %s' % e); return []

    def load_geom(self, die_id):
        p = self.state / 'explorer' / 'geom' / (die_id + '.json.gz')
        try: mt = p.stat().st_mtime
        except OSError: return None
        c = self.geom.get(die_id)
        if c and c['mt'] == mt: return c
        try:
            raw = p.read_bytes(); rec = json.loads(gzip.decompress(raw))
        except Exception as e:
            self.log('explorer geom %s: %s' % (die_id, e)); return c
        c = dict(mt=mt, raw=raw, rec=rec, key=rec.get('key'))
        with self.lock:
            self.geom[die_id] = c; self.safe_geom.pop(die_id, None)
        return c

    def check(self):
        for d in self.dies():
            try:
                key = G.recipe_key(d, G.recipe_commit(self.repo, d))
            except Exception as e:
                self.export_err[d['id']] = 'recipe commit: %s' % e; continue
            self.want[d['id']] = key
            c = self.load_geom(d['id'])
            if (c is None or c['key'] != key) and self.exporting is None:
                self.export(d['id'], key)

    def export(self, die_id, key):
        self.exporting = dict(die=die_id, key=key, t=time.time())
        logp = self.state / 'explorer' / ('export_%s.log' % die_id)
        logp.parent.mkdir(parents=True, exist_ok=True)
        self.log('explorer: exporting %s (%s)' % (die_id, key))
        cmd = [sys.executable, str(HERE / 'explorer_geom.py'), 'export', '--die', die_id, '--repo', str(self.repo), '--state', str(self.state)]
        try:
            if shutil.which('systemd-run'):
                # a transient user unit: the export (~300 MB, minutes of CPU) runs outside fleet-viz.service's
                # MemoryMax / CPUQuota, niced
                logp.write_text('')
                p = subprocess.run(['systemd-run', '--user', '--wait', '--collect', '--quiet', '--unit', 'fleet-viz-export-' + die_id,
                                    '-p', 'Nice=15', '-p', 'MemoryMax=8G', '-p', 'WorkingDirectory=/tmp',
                                    '-p', 'StandardOutput=file:%s' % logp, '-p', 'StandardError=file:%s' % logp] + cmd,
                                   timeout=3 * 3600, capture_output=True)
            else:
                with open(logp, 'w') as lf:
                    p = subprocess.run(['nice', '-n', '15'] + cmd, stdout=lf, stderr=subprocess.STDOUT, timeout=3 * 3600, cwd='/tmp')
            if p.returncode:
                tail = logp.read_text(errors='replace')[-600:]
                self.export_err[die_id] = tail; self.log('explorer: export %s failed: %s' % (die_id, tail[-200:]))
            else:
                self.export_err.pop(die_id, None); self.load_geom(die_id)
        except Exception as e:
            self.export_err[die_id] = str(e)
        finally:
            self.exporting = None

    def run(self):
        t_check = 0
        while True:
            try:
                for d in self.dies(): self.load_geom(d['id'])
                if time.time() - t_check >= self.check_every:
                    t_check = time.time(); self.check()
                self.build_meta()
            except Exception as e:
                import traceback
                self.log('explorer: %s %s' % (e, traceback.format_exc()[-400:]))
            time.sleep(20)

    # ------------------------------------------------------------------ names / stories
    def _load_names(self):
        try: return json.loads((HERE / 'explorer_names.json').read_text())
        except Exception as e: self.log('explorer names: %s' % e); return dict(prefixes=[], tokens={}, roles=[])

    def stories(self):
        cards = {}
        files = sorted((HERE / 'stories').glob('*.json'), key=lambda p: (p.name != 'planned.json', p.name))
        meta = {}
        for p in files:      # planned.json first, so any real card with the same id replaces its hook
            try: d = json.loads(p.read_text())
            except Exception as e: self.log('explorer story %s: %s' % (p.name, e)); continue
            if p.name == 'curated.json':
                meta = {k: d.get(k) for k in ('legend', 'loop_src', 'loop_taken', 'built', 'source')}
            for c in d.get('cards', []):
                if c.get('id'): cards[c['id']] = dict(c, _file=p.name)
        return list(cards.values()), meta

    # ------------------------------------------------------------------ jobs (full history)
    def jobs(self):
        seen = set()
        for f in os.scandir(self.jobs_dir):
            if not f.name.endswith('.json'): continue
            seen.add(f.name)
            try: mt = f.stat().st_mtime
            except OSError: continue
            c = self.jcache.get(f.name)
            if c and c[0] == mt: continue
            try: j = json.loads(open(f.path).read())
            except Exception: continue
            self.jcache[f.name] = (mt, self.reduce(j))
        for k in set(self.jcache) - seen: del self.jcache[k]
        return [v for _, v in self.jcache.values() if v and v['status'] != 'SUMMARY']

    @staticmethod
    def reduce(j):
        s = j.get('spec') or {}; m = j.get('metrics') or {}; ev = j.get('events') or []
        rec_to = [r.get('to') for r in (s.get('record') or []) if isinstance(r, dict) and r.get('to')]
        closed_t = None
        for e in ev:
            if re.match(r'\S+ CLOSED', e): closed_t = _ts(e.split(' ', 1)[0])
        tt = m.get('setup_corner') == 'tt'
        evs = []
        for e in ev[-6:]:
            t, _, txt = e.partition(' ')
            evs.append([_ts(t), txt[:240]])
        src = s.get('source') or {}
        return dict(name=j.get('name') or '', block=s.get('block') or re.sub(r'[-_][0-9a-f]{9}.*$', '', j.get('name') or ''),
                    status=j.get('status'), owner=s.get('owner') or '', branch=src.get('branch') or '',
                    commit=(src.get('commit') or j.get('commit_full') or '')[:12], purpose=(s.get('purpose') or '')[:600],
                    created=_ts(j.get('created', '')), updated=_ts(j.get('updated', '')), closed_t=closed_t,
                    host=j.get('host'), stage=j.get('stage_key') or '', reason=(j.get('reason') or '')[:400],
                    tt=_f(m.get('ss_ps')) if tt else None, ss=_f(m.get('ss_sensitivity_ps')) if tt else _f(m.get('ss_ps')),
                    ff=_f(m.get('ff_ps')), drc=m.get('drc'), corner='TT' if tt else 'SS', record_to=rec_to,
                    cycles_added=s.get('cycles_added'), merge_target=s.get('merge_target') or '',
                    failed_checks=j.get('failed_checks') or [], events=evs, attempt=j.get('attempt'))

    # ------------------------------------------------------------------ model
    def decode(self, name):
        """human name of an element / master / instance from explorer_names.json"""
        N = self.names; n = name
        for p in N.get('prefixes', []):
            m = re.match(p['re'], n)
            if m:
                rest = n[m.end():]
                head = p['name']
                break
        else:
            head, rest = '', n
        words = []
        for tok in [t for t in re.split(r'_+', rest) if t]:
            words.append(self.token(tok))
        body = ' '.join(w for w in words if w)
        return (head + (': ' if head and body else '') + body).strip() or name

    def token(self, tok):
        T = self.names.get('tokens', {})
        if tok in T: return T[tok]
        if tok.lower() in T: return T[tok.lower()]
        for p in self.names.get('token_patterns', []):
            m = re.fullmatch(p['re'], tok)
            if m: return p['name'].format(*m.groups())
        return tok

    def role(self, name, target=''):
        for r in self.names.get('roles', []):
            if re.search(r['re'], name): return r['role']
        return ''

    def build_meta(self):
        try: mt = (HERE / 'explorer_names.json').stat().st_mtime
        except OSError: mt = 0
        if mt != self.names_mt: self.names = self._load_names(); self.names_mt = mt
        es = self.E.snapshot(False)
        smt = tuple(sorted((p.name, p.stat().st_mtime) for p in (HERE / 'stories').glob('*.json')))
        key = (es.get('v'), tuple((k, v['key'], v['mt']) for k, v in sorted(self.geom.items())), smt, self.names_mt,
               self.exporting and self.exporting['die'], tuple(sorted(self.export_err)))
        if key == getattr(self, '_mk', None) and self.meta is not None and time.time() - self.meta_t < 120: return
        jobs = self.jobs()
        rows = {r['element']: r for r in es.get('rows', [])}
        known = set(rows)
        for r in es.get('rows', []): known.update(r.get('variants') or [])
        import elements as EL
        jobs_by_el = collections.defaultdict(list)
        for j in jobs: jobs_by_el[EL.master(j['block'], known)].append(j)
        cards, smeta = self.stories()
        story_of = collections.defaultdict(list)
        for c in cards:
            for a in c.get('attach') or []: story_of[a].append(c['id'])
        comp = self.compose()
        dies = []; mstat = {}; el_dies = collections.defaultdict(dict); el_lin = collections.defaultdict(dict)
        children = collections.defaultdict(lambda: collections.defaultdict(set))
        for d in self.dies():
            g = self.geom.get(d['id']); rec = g['rec'] if g else None
            info = dict(id=d['id'], label=d['label'], target=d['target'], want=self.want.get(d['id']),
                        key=g['key'] if g else None, exporting=bool(self.exporting and self.exporting['die'] == d['id']),
                        error=(self.export_err.get(d['id']) or '')[-300:] or None, tool=d.get('tool'), note=d.get('note'),
                        reach_um=d.get('reach_um'), reach_note=d.get('reach_note'))
            if rec:
                info.update(commit=rec['commit'], generated=rec['generated'], insts=len(rec['inst']['name']), W=rec['W'], H=rec['H'],
                            masters=len(rec['masters']), relays=rec.get('relays'), buses=len(rec['buses']))
            dies.append(info)
            if not rec: continue
            ms, roles = self.map_die(d, rec, rows, jobs_by_el, comp)
            for n, els in roles.items():
                for el, (role, src) in els.items():
                    tgt = el_lin if role == 'lineage' else el_dies
                    tgt[el].setdefault(d['id'], [])
                    if n not in tgt[el][d['id']]: tgt[el][d['id']].append(n)
                    if role not in ('lineage', 'exact', 'primary', 'variant'): children[d['id']][n].add(el)
            mstat[d['id']] = ms
        els = []; dieless = comp.get('dieless') or {}
        for el, r in rows.items():
            st = self.el_status(r)
            dl = None
            if not el_dies.get(el) and not el_lin.get(el):
                dl = dieless.get(el) or next((why for rx, why in comp.get('dieless_re') or [] if re.search(rx, el)), None) or ('superseded: ' + ((r.get('superseded') or {}).get('reason') or 'no instance on a current die')
                                         if st == 'superseded' else 'no die master on an exported die (unaccounted)')
            els.append(dict(element=el, target=r['target'], s=st, cat=r['category'], decoded=self.decode(el),
                            dies=el_dies.get(el, {}), lineage=el_lin.get(el, {}), dieless=dl,
                            stories=sorted(set(story_of.get(el, []) + [s for v in r.get('variants') or [] for s in story_of.get(v, [])])),
                            live=r['live'], jobs=r['jobs'], variants=r.get('variants') or []))
        tree = self.tree(dies, mstat, children, rows)
        recon = self.reconcile(els, es)
        meta = dict(t=time.time(), status_keys=STATUS_KEYS, status_label=STATUS_LABEL, dies=dies, masters=mstat, elements=els,
                    tree=tree, stories=[{k: c.get(k) for k in ('id', 'title', 'target', 'status', 'element', 'summary', 'attach', '_file')} for c in cards],
                    story_meta=smeta, names=self.names, exporting=self.exporting, reconcile=recon)
        with self.lock:
            self.meta = meta; self.meta_t = time.time(); self._mk = key
            self.jobs_by_el = jobs_by_el; self.rows = rows; self.cards = {c['id']: c for c in cards}; self.children = children

    def compose(self):
        """explorer_compose.json (rules + dieless + fold); reloaded when it changes"""
        p = HERE / 'explorer_compose.json'
        try: mt = p.stat().st_mtime
        except OSError: return dict(rules=[], dieless={})
        if getattr(self, '_comp_mt', None) != mt:
            try:
                c = json.loads(p.read_text())
                for r in c.get('rules', []):
                    r['_m'] = re.compile(r['masters']); r['_d'] = re.compile(r['die']) if r.get('die') else None
                c['_fold'] = re.compile(c['fold']) if c.get('fold') else None
                self._comp = c; self._comp_mt = mt
            except Exception as e:
                self.log('explorer compose: %s' % e); self._comp = getattr(self, '_comp', dict(rules=[], dieless={}))
        return self._comp

    def map_die(self, d, rec, rows, jobs_by_el, comp):
        """master -> {element: (role, source)} for one die, and the per-master map status.

        Order: exact name / element variants; curated composition (explorer_compose.json); job record dirs and
        view-index tiles; the generic variant fold (qfd_cst_n -> qfd_cst); job / element purpose naming a master."""
        mset = {m['name'] for m in rec['masters']}; views = rec.get('views') or {}
        roles = collections.defaultdict(dict)
        def add(m, el, role, src):
            if el in roles[m] and roles[m][el][0] in ('exact', 'primary'): return
            roles[m][el] = (role, src)
        cand = {el: r for el, r in rows.items() if r['target'] == d['target'] or r['target'] == 'Other'}
        ruled = set()
        for r in comp.get('rules', []):
            if r['_d'] and not r['_d'].search(d['id']): continue
            ms_ = [m for m in mset if r['_m'].search(m)]
            for el in [e for x in r['elements'] for e in (sorted(c for c in cand if re.search(x[3:], c)) if x.startswith('re:') else [x])]:
                if el not in cand or not ms_: continue
                ruled.add(el)
                for m in ms_: add(m, el, r['role'], 'composition: ' + r.get('src', ''))
        for el, r in cand.items():
            names = [el] + (r.get('variants') or [])
            for n in names:
                if n in mset: add(n, el, 'exact' if n == el else 'variant', 'element name' if n == el else 'element variant ' + n)
            if el in ruled: continue
            for js in jobs_by_el.get(el, []):
                for to in js['record_to']:
                    for part in pathlib.PurePosixPath(to).parts[::-1]:
                        if part in mset and part not in names: add(part, el, 'part', 'job record dir ' + to); break
            for v_m, v in views.items():
                if v_m in mset and el in (v.get('tiles') or []): add(v_m, el, 'part', 'view index tile of ' + v_m)
        # generic variant fold: a master with no element of its own whose base name is an element (qfd_cst_n -> qfd_cst)
        fold = comp.get('_fold')
        if fold:
            for m in mset:
                if m in rows or any(v[0] in ('exact', 'primary', 'variant') for v in roles.get(m, {}).values()): continue
                mm = fold.match(m)
                if mm and mm.group('base') in cand: add(m, mm.group('base'), 'variant', 'variant fold %s -> %s' % (m, mm.group('base')))
        placed = {el for m in roles for el in roles[m]}
        for el, r in cand.items():
            if el in placed or el in ruled: continue
            texts = [r.get('purpose') or ''] + [js['purpose'] for js in sorted(jobs_by_el.get(el, []), key=lambda j: j['created'])]
            for t in texts:
                tok = next((t_ for t_ in MASTER_TOKEN.findall(t) if t_ in mset and t_ != el), None)
                if tok: add(tok, el, 'part', 'purpose names ' + tok); break
        ms = {}
        for m in rec['masters']:
            n = m['name']; rl = roles.get(n, {})
            prim = sorted(e for e, (ro, _) in rl.items() if ro == 'primary')
            own = prim[0] if prim else (n if n in rows else next((e for e, (ro, _) in sorted(rl.items()) if ro in ('exact', 'variant')), None))
            if prim and n in rl and n != own: rl[n] = ('lineage', 'superseded on this die by ' + own)
            if own and own != n and n in rows and n not in rl: rl[n] = ('lineage', 'superseded on this die by ' + own)
            parts = sorted(e for e, (ro, _) in rl.items() if ro in ('part', 'relay') and e != own)
            lin = sorted(e for e, (ro, _) in rl.items() if ro == 'lineage')
            relay = bool(re.search(r'(^|_)(rly|rlyf|wstg)(_|$)', n) or n.startswith('hfd_rly'))
            v = views.get(n) or {}
            if own:
                st = self.el_status(rows[own]); src = 'element' if own == n else ('primary element ' + own if prim else 'element variant ' + own)
            elif parts:
                sts = [self.el_status(rows[e]) for e in parts]
                st = next((s for s in ROLL if s in sts), 'placeholder'); src = 'relay element' if relay else 'parts'
            else:
                vs = (v.get('status') or '')
                if vs in ('closed',): st = 'closed'
                elif vs == 'closed-below-margin': st = 'below'
                elif vs == 'macro': st = 'macro'
                elif relay: st = 'relay'
                elif not re.match(r'(hfd|qfd|dsfd)_', n) and not v: st = 'macro'
                else: st = 'placeholder'
                src = 'view index' if v else 'generator'
            if relay and st != 'relay' and not parts and not own: st = 'relay'
            hard = ([own] if own else []) + parts
            ms[n] = dict(s=st, src=src, el=own or (parts[0] if len(parts) == 1 else None), els=sorted(set(hard)), lin=lin,
                         relay=relay, roles={e: [ro, s_[:300]] for e, (ro, s_) in rl.items()},
                         view=v.get('status') if v else None)
        return ms, roles

    def reconcile(self, els, es):
        """every /api/elements row accounted: placed on a die (as itself, a part or a relay), lineage only, or die-less
        with a reason; per target and per map status (closed counts include closed-below-margin)"""
        out = {}
        for e in els:
            t = out.setdefault(e['target'], dict(total=0, placed=0, lineage_only=0, dieless=0, unaccounted=0,
                                                 closed=dict(total=0, placed=0, lineage_only=0, dieless=0, unaccounted=0),
                                                 unaccounted_list=[], closed_offdie=[]))
            k = 'placed' if e['dies'] else 'lineage_only' if e['lineage'] else ('unaccounted' if 'unaccounted' in (e['dieless'] or '') else 'dieless')
            t['total'] += 1; t[k] += 1
            if e['s'] in ('closed', 'below'):
                t['closed']['total'] += 1; t['closed'][k] += 1
                if k != 'placed': t['closed_offdie'].append([e['element'], k, e['dieless'] or 'lineage: ' + ', '.join(sorted({m for v in e['lineage'].values() for m in v}))])
            if k == 'unaccounted': t['unaccounted_list'].append(e['element'])
        api = collections.Counter()
        for r in es.get('rows', []):
            if self.el_status(r) in ('closed', 'below'): api[r['target']] += 1
        for tg, t in out.items(): t['closed']['api'] = api.get(tg, 0)
        return out

    def el_status(self, r):
        st = CAT_STATUS.get(r['category'], 'failing')
        if st == 'closed':
            b = r.get('best') or {}
            setup = b.get('tt') if b.get('corner') == 'TT' or b.get('tt') is not None else b.get('ss')
            if (setup is not None and setup < MARGIN) or (b.get('ff') is not None and b['ff'] < MARGIN): st = 'below'
        return st

    def tree(self, dies, mstat, children, rows):
        out = []
        for d in dies:
            g = self.geom.get(d['id'])
            if not g: out.append(dict(id=d['id'], label=d['label'], groups=[], counts={})); continue
            rec = g['rec']; ms = mstat[d['id']]
            groups = collections.defaultdict(list)
            for m in rec['masters']:
                st = ms[m['name']]
                if st.get('relay') or st['s'] == 'relay': grp = 'die relays / wire stages'
                else: grp = m['kind'] or 'other'
                groups[grp].append(dict(m=m['name'], n=m['n'], s=st['s'], el=st.get('el'),
                                        kids=sorted(children[d['id']].get(m['name'], set()) - {m['name']})))
            gl = []
            for k, v in sorted(groups.items(), key=lambda kv: (kv[0].startswith('die relays'), kv[0])):
                c = collections.Counter(x['s'] for x in v)
                if k.startswith('die relays'):     # one row per hardening element, not 1,800 single-instance masters
                    fam = collections.defaultdict(list)
                    for x in v: fam[x['el'] or ''].append(x)
                    v = [dict(m='(%d relay / wire-stage masters%s)' % (len(xs), ': ' + el if el else ''), n=sum(x['n'] for x in xs),
                              s=xs[0]['s'] if el else 'relay', kids=[el] if el else [], group=True, el=el or None)
                         for el, xs in sorted(fam.items(), key=lambda kv: (kv[0] == '', kv[0]))]
                gl.append(dict(name=k, items=sorted(v, key=lambda x: (x.get('group') and not x.get('el'), x['m'])), counts=dict(c)))
            real = [x for x in ms.values() if not x.get('relay') and x['s'] != 'relay']
            c = collections.Counter(x['s'] for x in real)
            rl = collections.Counter(x['s'] for x in ms.values() if x.get('relay') or x['s'] == 'relay')
            out.append(dict(id=d['id'], label=d['label'], groups=gl, counts=dict(c), closed=c['closed'] + c['below'],
                            total=sum(v for k, v in c.items() if k not in ('macro', 'relay')), relay_counts=dict(rl)))
        return out

    # ------------------------------------------------------------------ API
    def api_meta(self, safe):
        with self.lock: m = self.meta
        if m is None: return dict(warming=True)
        if not safe: return m
        sm = dict(m, elements=[dict(element=self.alias(e['element']), target=e['target'], s=e['s'], decoded=e['decoded'],
                                    dies={k: [self.alias(x) for x in v] for k, v in e['dies'].items()}, stories=e['stories'], live=e['live'], jobs=e['jobs'], variants=[],
                                    lineage={k: [self.alias(x) for x in v] for k, v in (e.get('lineage') or {}).items()}, dieless=bool(e.get('dieless')))
                                for e in m['elements']],
                  masters={d: {self.alias(k): dict({k_: v_ for k_, v_ in v.items() if k_ != 'roles'}, el=self.alias(v['el']) if v['el'] else None,
                                                   els=[self.alias(x) for x in v['els']], lin=[self.alias(x) for x in v.get('lin', [])])
                               for k, v in ms.items()} for d, ms in m['masters'].items()},
                  reconcile={t: {k: v for k, v in r.items() if not k.endswith('_list') and k != 'closed_offdie'} for t, r in (m.get('reconcile') or {}).items()},
                  tree=[dict(t, groups=[dict(g, items=[dict(i, m=self.alias(i['m']) if not i.get('group') else i['m'], kids=[self.alias(k) for k in i['kids']]) for i in g['items']])
                                        for g in t['groups']]) for t in m['tree']],
                  dies=[{k: v for k, v in d.items() if k not in ('error', 'tool', 'note', 'want', 'key', 'commit')} for d in m['dies']],
                  stories=[{k: v for k, v in x.items() if k not in ('attach', '_file', 'element')} for x in m['stories']],
                  exporting=None, safe=True)
        return sm

    def alias(self, name):
        """share-safe label: the decoded name (no raw block / master / instance names)"""
        if name is None: return None
        return self.decode(name)

    def geom_bytes(self, die_id, safe):
        g = self.geom.get(die_id) or self.load_geom(die_id)
        if not g: return None
        if not safe: return g['raw']
        c = self.safe_geom.get(die_id)
        if c and c[0] == g['key']: return c[1]
        r = json.loads(gzip.decompress(g['raw']))
        r['masters'] = [dict(m, name=self.alias(m['name'])) for m in r['masters']]
        r['inst']['name'] = [''] * len(r['inst']['name'])
        for k in ('recipe', 'commit', 'key', 'model_keys', 'views', 'view_index', 'relay_record', 'fetched_files'): r.pop(k, None)
        for x in r['regions']: x['name'] = ''
        b = gzip.compress(json.dumps(r, separators=(',', ':')).encode(), 6)
        self.safe_geom[die_id] = (g['key'], b)
        return b

    def card(self, element=None, master=None, die=None, safe=False):
        with self.lock:
            meta = self.meta; rows = getattr(self, 'rows', {}); jbe = getattr(self, 'jobs_by_el', {}); cards = getattr(self, 'cards', {})
            children = getattr(self, 'children', {})
        if meta is None: return dict(warming=True)
        if element is None and master and die:
            ms = meta['masters'].get(die, {}).get(master)
            element = (ms or {}).get('el') or (master if master in rows else None)
        r = rows.get(element) if element else None
        name = element or master
        out = dict(name=name, decoded=self.decode(name or ''), element=element, master=master, die=die,
                   role=self.role(name or ''), status_label=STATUS_LABEL)
        if r:
            out.update(target=r['target'], s=self.el_status(r), category=r['category'], via=r.get('via'), purpose=r.get('purpose'),
                       best=r.get('best'), area=r.get('area'), revoked=r.get('revoked'), latest=r.get('latest'), owner=r.get('owner'),
                       superseded=r.get('superseded'), variants=r.get('variants') or [], closed_t=r.get('closed_t'),
                       live=r['live'], failed=r['failed'], jobs_n=r['jobs'])
            js = sorted(jbe.get(element, []), key=lambda j: j['created'])
            out['history'] = js
            best = (r.get('best') or {}).get('job')
            bj = next((j for j in js if j['name'] == best), None)
            if bj: out['adopted'] = dict(job=bj['name'], commit=bj['commit'], branch=bj['branch'], record_to=bj['record_to'], status=bj['status'])
            cyc = [j['cycles_added'] for j in js if j.get('cycles_added') is not None]
            out['cycles_added'] = cyc[-1] if cyc else None
        if element:
            em = next((e for e in meta['elements'] if e['element'] == element), None)
            if em and em.get('dieless'): out['dieless'] = em['dieless']
        # where it sits: per die, its masters, instances counted by the client from geometry
        places = {}
        for d_id, ms in meta['masters'].items():
            for mn, v in ms.items():
                if mn == name or (element and element in v['els']) or (master and mn == master and d_id == die):
                    ro = (v.get('roles') or {}).get(element or '', [None, None])
                    places.setdefault(d_id, []).append(dict(master=mn, s=v['s'], src=v['src'], view=v.get('view'), els=v['els'],
                                                            role=ro[0], via=ro[1], relay=v.get('relay')))
                elif element and element in (v.get('lin') or []):
                    ro = (v.get('roles') or {}).get(element, [None, None])
                    places.setdefault(d_id, []).append(dict(master=mn, s=v['s'], src='lineage', view=v.get('view'), els=v['els'],
                                                            role='lineage', via=ro[1], relay=v.get('relay')))
        out['places'] = places
        kids = set()
        for d_id, ch in children.items():
            for mn in [p['master'] for p in places.get(d_id, [])]:
                kids |= ch.get(mn, set())
        kids.discard(name)
        out['children'] = sorted(kids)
        out['child_status'] = {k: self.el_status(rows[k]) for k in kids if k in rows}
        parents = sorted({p['master'] for v in places.values() for p in v if p['master'] != name})
        out['parents'] = parents
        sids = set()
        for c in cards.values():
            att = c.get('attach') or []
            if name in att or (element and element in att) or any(p in att for p in parents) or any(v in att for v in out.get('variants', [])):
                sids.add(c['id'])
        out['stories'] = [{k: cards[i].get(k) for k in ('id', 'title', 'status', 'target', 'summary')} for i in sorted(sids)]
        if not r and places:     # a die master with no closure-loop element of its own: status / purpose from the map
            pl = places.get(die) or next(iter(places.values()))
            out['s'] = pl[0]['s']; out['target'] = meta['dies'] and next((d['target'] for d in meta['dies'] if d['id'] in places), None)
            subs = [rows[k] for k in out['children'] if k in rows and rows[k].get('purpose')]
            out['purpose'] = ('Die master (status %s, from %s).' % (STATUS_LABEL.get(pl[0]['s'], pl[0]['s']), pl[0]['src'])
                              + (' Hardens: ' + '; '.join('%s: %s' % (x['element'], x['purpose'][:160]) for x in subs[:3]) if subs else ''))
        out['views'] = {}
        for d_id, pl in places.items():
            g = self.geom.get(d_id)
            vw = (g['rec'].get('views') or {}) if g else {}
            for p in pl:
                if p['master'] in vw: out['views'].setdefault(d_id, {})[p['master']] = vw[p['master']]
        if safe:
            out = self.safe_card(out)
        return out

    def safe_card(self, c):
        keep = dict(name=self.alias(c['name']), decoded=c['decoded'], role=c['role'], s=c.get('s'), target=c.get('target'),
                    category=c.get('category'), status_label=c['status_label'], live=c.get('live'), failed=c.get('failed'),
                    jobs_n=c.get('jobs_n'), area=c.get('area'), cycles_added=c.get('cycles_added') if isinstance(c.get('cycles_added'), (int, float)) else None,
                    places={d: [dict(master=self.alias(p['master']), s=p['s']) for p in v] for d, v in c['places'].items()},
                    children=[self.alias(k) for k in c['children']], parents=[self.alias(k) for k in c['parents']],
                    stories=c['stories'], safe=True,
                    history=[dict(status=j['status'], created=j['created'], updated=j['updated'], closed_t=j['closed_t'])
                             for j in c.get('history', [])])
        return keep

    def story(self, sid):
        with self.lock: cards = getattr(self, 'cards', {})
        return cards.get(sid)

    def card_safe_by_index(self, die, mi):
        """share-safe card: the client knows masters only by index (names are aliased)"""
        g = self.geom.get(die or '')
        try: name = g['rec']['masters'][int(mi)]['name']
        except Exception: return dict(error='no such master')
        return self.card(master=name, die=die, safe=True)
