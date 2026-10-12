"""Element page shell (/explorer/element/<name>): one call that tells the page who the element is and what it can show.

  /api/explorer/elem_shell?e=<element>   header (target, status, best TT / FF / DRC, throughput, owner, last closure),
                                         breadcrumb (die -> region), the export data id that holds its routed views, and
                                         per-tab availability with a one-line reason when a tab has nothing to show.
  /api/explorer/elem_coverage            every counted CLOSED element of the registry -> does its page have routed data.

Data id resolution (why many CLOSED elements used to have no page): the closure loop's post-close hook runs
tools/explorer_elem_export.py auto WITHOUT --element, so the export lands under the job spec's block name
(hfd_hc_tile_xl, dsfd_coll_cbfj, ot_pqc_t_*, ...) while the registry counts the element under its own name (hfd_hc,
dsfd_coll_cbj, ot_v41_pqc_spine_screen).  The page resolves element -> data id by (1) its own name, (2) the export index
entry whose job is the element's best closing job, (3) a variant with a data file; an element with none of these still
gets its page, from the registry alone, with the routed tabs disabled and the reason stated.
"""
import json, os, pathlib, threading, time
import elem_desc

CLOSED_PREFIX = 'closed'


class Shell:
    def __init__(self, elem_dir, elements, explorer, log=print, repo='/home/ubuntu/OpenTallas'):
        self.desc = elem_desc.Desc(repo, log=log)
        self.dir = pathlib.Path(elem_dir) / 'data'
        self.pages = pathlib.Path(elem_dir) / 'pages.json'
        self.E, self.X, self.log = elements, explorer, log
        self.lock = threading.Lock()
        self._idx = (None, {})
        self._pg = (None, {})
        self._marks = pathlib.Path.home() / '.local/state/viz-elem'

    # ---------------------------------------------------------------- inputs (cached by mtime)
    def index(self):
        p = self.dir / 'index.json'
        try: mt = p.stat().st_mtime
        except OSError: return {}
        with self.lock:
            if self._idx[0] == mt: return self._idx[1]
        try: d = json.loads(p.read_text()).get('elements') or {}
        except Exception as e:
            self.log('elem_shell index: %s' % e); d = {}
        with self.lock: self._idx = (mt, d)
        return d

    def prose(self):
        try: mt = self.pages.stat().st_mtime
        except OSError: return {}
        with self.lock:
            if self._pg[0] == mt: return self._pg[1]
        try: d = json.loads(self.pages.read_text())
        except Exception: d = {}
        with self.lock: self._pg = (mt, d)
        return d

    def rows(self):
        try: rs = self.E.snapshot().get('rows') or []
        except Exception: rs = []
        return {r['element']: r for r in rs}

    # ---------------------------------------------------------------- resolution
    def resolve(self, el, row, idx):
        """-> (data id or None, how)"""
        if (self.dir / (el + '.json')).is_file(): return el, 'own name'
        job = ((row or {}).get('best') or {}).get('job')
        if job:
            hits = [k for k, v in idx.items() if v.get('job') == job and (self.dir / (k + '.json')).is_file()]
            if hits: return sorted(hits, key=len)[0], 'exported under the closing job’s block name'
        for v in (row or {}).get('variants') or []:
            if (self.dir / (v + '.json')).is_file(): return v, 'variant ' + v
        return None, None

    def why_missing(self, row):
        """one line: why a counted element has no routed data"""
        if not row: return 'not a closure-registry element (a die master or story name): no routed database of its own'
        if not str(row.get('category', '')).startswith(CLOSED_PREFIX):
            return 'not closed yet (%s): routed views are exported when it closes' % row.get('category', '?')
        job = (row.get('best') or {}).get('job')
        if not job: return 'no closing job recorded'
        try: mk = json.loads((self._marks / (job + '.json')).read_text())
        except Exception: mk = {}
        st = mk.get('state')
        if st == 'running': return 'routed views are being exported now'
        if st == 'failed': return 'export of the routed DB failed (%s); it is retried by the exporter batch' % (mk.get('error') or '?')[:90]
        return 'no routed database archived yet (the closing job’s DB was released before export, or it sits on localhost)'

    # ---------------------------------------------------------------- page
    def page(self, el, safe=False):
        idx, rows = self.index(), self.rows()
        row = rows.get(el)
        if row is None:     # a variant name, or an export-only block name: show its owning element's header
            own = next((r for r in rows.values() if el in (r.get('variants') or [])), None)
            if own is None:
                ent = idx.get(el) or {}
                own = next((r for r in rows.values() if ent.get('job') and (r.get('best') or {}).get('job') == ent.get('job')), None)
            row = own
        did, how = self.resolve(el, row, idx)
        if did is None and row and row['element'] != el: did, how = self.resolve(row['element'], row, idx)
        ent = idx.get(did) or {} if did else {}
        best = (row or {}).get('best') or {}
        tq = (row or {}).get('throughput') or {}
        cat = (row or {}).get('category') or ent.get('category') or ('exported' if did else 'unknown')
        closed = str(cat).startswith(CLOSED_PREFIX)
        out = dict(element=el, registry=(row or {}).get('element'), known=bool(row or did),
                   decoded=self._decode(el), target=(row or {}).get('target') or ent.get('target'),
                   category=cat, closed=closed, purpose=(row or {}).get('purpose'),
                   best=dict(tt=best.get('tt'), ff=best.get('ff'), ss=best.get('ss'), drc=best.get('drc'), corner=best.get('corner'),
                             job=best.get('job'), commit=best.get('source_commit')),
                   throughput=dict(status=tq.get('status'), ratio=tq.get('ratio')) if tq else None,
                   owner=(row or {}).get('owner'), closed_t=(row or {}).get('closed_t'),
                   live=(row or {}).get('live'), revoked=bool((row or {}).get('revoked')), superseded=bool((row or {}).get('superseded')),
                   data=did, data_how=how, exported_at=ent.get('exported_at'),
                   has=dict(layout=bool(ent.get('layout')), sta=bool(ent.get('sta')), rtl=bool(ent.get('rtl')),
                            reference=bool(ent.get('reference'))),
                   missing=None if did else self.why_missing(row),
                   crumbs=self._crumbs(el, row), stories=self._stories(el, row),
                   desc=self.desc.get(el, (row or {}).get('purpose'), ((row or {}).get('element'), did) + tuple(c['master'] for c in self._crumbs(el, row))),
                   prose=bool(((self.prose().get('elements') or {}).get(did or el) or {}).get('function')))
        if safe:
            out['best']['job'] = out['best']['commit'] = None; out['owner'] = None; out['purpose'] = None; out['data_how'] = None
            out['crumbs'] = [dict(c, region=None) for c in out['crumbs']]
            if out['desc'].get('src') != 'manual': out['desc'] = dict(summary='', about='', family='', src=None)
        return out

    def _decode(self, el):
        try: return self.X.decode(el)
        except Exception: return ''

    def _crumbs(self, el, row):
        """[{die, label, region, master}]: where the element sits on the exported die maps (first = primary)"""
        m = getattr(self.X, 'meta', None)
        if not m: return []
        names = {el} | ({row['element']} if row else set())
        labels = {d['id']: d['label'] for d in m.get('dies', [])}
        out = []
        for t in m.get('tree', []):
            for g in t.get('groups', []):
                for i in g.get('items', []):
                    if i.get('m') in names or i.get('el') in names or names & set(i.get('kids') or []):
                        out.append(dict(die=t['id'], label=labels.get(t['id'], t['id']), region=g.get('name'), master=i.get('m')))
                        break
                else: continue
                break
        if not out:
            for d_id, ms in (m.get('masters') or {}).items():
                for mn, v in ms.items():
                    if mn in names or names & set(v.get('els') or []):
                        out.append(dict(die=d_id, label=labels.get(d_id, d_id), region=None, master=mn)); break
        return out

    def _stories(self, el, row):
        cards = getattr(self.X, 'cards', {}) or {}
        names = {el} | ({row['element']} if row else set()) | set((row or {}).get('variants') or [])
        return [dict(id=c['id'], title=c.get('title'), status=c.get('status'), summary=(c.get('summary') or '')[:240])
                for c in cards.values() if names & set(c.get('attach') or []) or c.get('element') in names]

    # ---------------------------------------------------------------- coverage
    def coverage(self):
        idx, rows = self.index(), self.rows()
        closed = [r for r in rows.values() if str(r.get('category', '')).startswith(CLOSED_PREFIX)]
        own = alias = 0; missing = []; layout = 0
        for r in closed:
            did, how = self.resolve(r['element'], r, idx)
            if did is None: missing.append(dict(element=r['element'], why=self.why_missing(r))); continue
            if how == 'own name': own += 1
            else: alias += 1
            if (idx.get(did) or {}).get('layout'): layout += 1
        return dict(t=time.time(), closed=len(closed), with_data=own + alias, by_own_name=own, by_job_or_variant=alias,
                    with_routed_layout=layout, page_for_every_element=True, missing=missing)

    def summaries(self, safe=False):
        """{element: one-line summary} for the Chip Explorer lists, hover and search (safe view: manual text only)"""
        rows = self.rows()
        if safe: return {k: v['summary'] for k, v in self.desc.manual().items() if v.get('summary')}
        return self.desc.summaries(rows)
