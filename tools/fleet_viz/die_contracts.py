"""Top-down element list from the CURRENT die contracts (registry-sync 2026-10-15).

The fleet registry (elements.py) used to list only blocks that once had a closure-loop job, so a die master nobody had
submitted yet did not exist and 'open' understated what is left.  This module derives the element list top-down:

  results/fleet_viz/die_contracts.json      one entry per die (design): the machine-readable contract sources of that
                                            die revision, the replacements/additions its lead recorded in the die log,
                                            owner-stream patterns (STREAM_CHARTERS_1014.md) and whether the contract is
                                            complete (then every element of its target that is in no current contract is
                                            superseded, with the contract as evidence)

Source kinds (each yields masters, optionally with a parent master and an RTL file):
  port_bind        die_port_bind / die_port_bind_kv JSON: masters{} (+ verdict / cls = the native pin-bind check)
  hier_slots       opentallas.hier_contract.v1 slots[] (cell|master, kind, parent slot)
  json_keys        keys of the dict at `at` (dotted path)
  json_field       `field` of every item of the list/dict at `at`
  filelist         a .f file list: every module defined in a listed file is a master (layer1.f)
  registry         element_registry/*.json records (die-master and hierarchy-member records of another stream, e.g.
                   HBM-V15-HARDEN's hbm_v15_die_masters_*.json): 'parent X' dependencies give the leaf hierarchy
Below each master, the physical leaf hierarchy comes from the RTL: modules instantiated (recursively) under the master's
RTL that are themselves registry elements (have closure jobs / records) are its leaves.  Contract leaves that have no
row yet are 'not started (open)'; RTL-scan leaves only protect/annotate existing rows (a soft sub-module is not an
element).  Files are read from origin/main (the shared checkout can lag), falling back to the working tree.
"""
import collections, json, os, pathlib, re, subprocess, threading, time

CONFIG = 'results/fleet_viz/die_contracts.json'
SKIP_MODULE_FILES = re.compile(r'(^|/)(views|test|tb|bench)/|_stubs?\.s?v$|/die_top_lint_|(^|/)results/', re.I)
VKEYWORDS = set('''module endmodule input output inout wire reg logic always always_ff always_comb assign if else for
generate endgenerate begin end case endcase function endfunction task endtask initial localparam parameter genvar
integer typedef struct enum packed signed unsigned return default posedge negedge or and not while repeat'''.split())


class Repo:
    """Reads committed files at origin/main (one git cat-file --batch process), else the working tree."""

    def __init__(self, root):
        self.root = pathlib.Path(root); self.lock = threading.Lock(); self.proc = None

    def rev(self, ref='origin/main'):
        try: return subprocess.run(['git', '-C', str(self.root), 'rev-parse', ref], capture_output=True, text=True,
                                   timeout=20).stdout.strip()
        except Exception: return ''

    def _batch(self):
        if self.proc is None or self.proc.poll() is not None:
            self.proc = subprocess.Popen(['git', '-C', str(self.root), 'cat-file', '--batch'], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE)
        return self.proc

    def read(self, path, ref='origin/main'):
        with self.lock:
            try:
                p = self._batch(); p.stdin.write(('%s:%s\n' % (ref, path)).encode()); p.stdin.flush()
                head = p.stdout.readline().decode().split()
                if len(head) == 3 and head[1] == 'blob':
                    data = p.stdout.read(int(head[2])); p.stdout.read(1)
                    return data.decode(errors='replace')
            except Exception:
                self.proc = None
        try: return (self.root / path).read_text(errors='replace')
        except OSError: return None

    def json(self, path):
        t = self.read(path)
        return json.loads(t) if t else None

    def module_index(self, ref='origin/main'):
        """module name -> [file] for every committed .sv/.v (routed-view netlists, benches and lint stubs excluded)."""
        out = subprocess.run(['git', '-C', str(self.root), 'grep', '-nE', r'^\s*module\s+[A-Za-z_]\w*', ref, '--',
                              '*.sv', '*.v', ':!*/views/*'], capture_output=True, text=True, timeout=300).stdout
        idx = collections.defaultdict(list)
        for ln in out.splitlines():
            parts = ln.split(':', 3)
            if len(parts) < 4: continue
            path = parts[1]
            if SKIP_MODULE_FILES.search(path): continue
            m = re.match(r'\s*module\s+([A-Za-z_]\w*)', parts[3])
            if m and path not in idx[m.group(1)]: idx[m.group(1)].append(path)
        return dict(idx)


def at(doc, path):
    for k in [x for x in (path or '').split('.') if x]:
        if isinstance(doc, dict): doc = doc.get(k)
        elif isinstance(doc, list) and k.isdigit(): doc = doc[int(k)] if int(k) < len(doc) else None
        else: return None
    return doc


def module_bodies(text):
    """{module: body text} for every module in a file."""
    out = {}
    for m in re.finditer(r'(?m)^\s*module\s+([A-Za-z_]\w*)(.*?)^\s*endmodule', text or '', re.S):
        out[m.group(1)] = m.group(2)
    return out


INST = re.compile(r'(?m)^\s*([A-Za-z_]\w*)\s*(?:#\s*\(|[A-Za-z_]\w*\s*(?:\[[^\]]*\]\s*)?\()')


def instantiated(body):
    body = re.sub(r'//[^\n]*|/\*.*?\*/', '', body, flags=re.S)
    return {m.group(1) for m in INST.finditer(body) if m.group(1) not in VKEYWORDS}


class Contracts:
    def __init__(self, repo_root, log=print, rtl_period=3600):
        self.repo = Repo(repo_root); self.log = log; self.rtl_period = rtl_period
        self.key = None; self.base = None; self.mods = (0, None, {}); self.bodies = {}; self.hier_cache = {}

    # ---------------------------------------------------------------- contract sources
    def extract(self, src):
        """-> list of dict(element, parent, rtl, role, check) from one source."""
        kind = src.get('kind'); path = src.get('path'); out = []
        doc = None if kind in ('filelist', 'text_table') else self.repo.json(path)
        if kind not in ('filelist', 'text_table') and doc is None: raise ValueError('cannot read %s' % path)
        skip = set(src.get('skip') or []); macro = re.compile(src['macro']) if src.get('macro') else None
        def add(e, **kw):
            if not e or e in skip: return
            role = kw.pop('role', None) or ('macro' if macro and macro.search(e) else src.get('role', 'master'))
            out.append(dict(element=e, role=role, **kw))
        if kind == 'port_bind':
            for m, v in (doc.get('masters') or {}).items():
                cls = v.get('cls') or v.get('kind') or ''
                verdict = v.get('verdict') or ('PASS' if cls == 'REAL' else cls)
                rtl = v.get('rtl') or v.get('file')
                add(m, rtl=rtl if rtl and not rtl.startswith('/') else None, module=v.get('module'),
                    role='macro' if cls in ('HARD_PHY', 'model') else None,
                    check=dict(kind='die port-bind', verdict=verdict, path=path))
        elif kind == 'hier_slots':
            slots = at(doc, src.get('at', 'slots')) or []
            by_name = {s.get('name'): s for s in slots if isinstance(s, dict)}
            for s in slots:
                if not isinstance(s, dict) or s.get('kind') in ('die', 'container'): continue
                c = s.get('cell') or s.get('master')
                if not c or ' ' in c: continue
                ps = by_name.get(s.get('parent')) or {}
                par = None if ps.get('kind') in (None, 'die', 'container') else (ps.get('cell') or ps.get('master'))
                q = s.get('qualification') or s.get('view_status')
                add(c, parent=par, role='leaf' if par else None,
                    check=dict(kind='contract slot', verdict=q, path=path) if q else None)
        elif kind == 'json_keys':
            for k in (at(doc, src.get('at')) or {}): add(k)
        elif kind == 'json_field':
            items = at(doc, src.get('at')) or []
            for it in (items.values() if isinstance(items, dict) else items):
                if not isinstance(it, dict): continue
                if src.get('where') and any(it.get(k) != v for k, v in src['where'].items()): continue
                add(it.get(src['field']), rtl=it.get(src.get('rtl_field', 'source')) if isinstance(it.get(src.get('rtl_field', 'source')), str) else None)
        elif kind == 'filelist':
            text = self.repo.read(path)
            if text is None: raise ValueError('cannot read %s' % path)
            files = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith(('#', '+', '-', '//'))]
            for f in files:
                for m in module_bodies(self.repo.read(f) or ''):
                    add(m, rtl=f, role='soft')   # every module of a listed file: a member only if it is an element
        elif kind == 'text_table':   # a port-bind text table: first column = master
            text = self.repo.read(path)
            if text is None: raise ValueError('cannot read %s' % path)
            for ln in text.splitlines():
                m = re.match(r'([A-Za-z_]\w*)\s+x\d+\s+rtl=(\S+)', ln)
                if m: add(m.group(1), check=dict(kind='die port-bind', verdict='rtl=' + m.group(2), path=path))
        elif kind == 'registry':
            for r in doc.get('records') or []:
                e = r.get('element'); deps = r.get('dependencies') or []
                parents = [d.split(' ', 1)[1] for d in deps if isinstance(d, str) and d.startswith('parent ')]
                rtl = next((p for p in (r.get('source') or {}).get('paths') or [] if p.endswith(('.sv', '.v'))), None)
                stream = (r.get('owner') or '').split(':', 1)[-1] or None
                phys = (r.get('physical') or {}).get('status', '')
                if parents:
                    for p in parents: add(e, parent=p, role='leaf', rtl=rtl, stream=stream)
                else:
                    add(e, rtl=rtl, stream=stream, role='macro' if phys.startswith('hard PHY') else None)
        else:
            raise ValueError('unknown source kind %r' % kind)
        return out

    def build(self, cfg):
        designs = []; elems = {}; retired = {}
        def put(e, d, role, parent=None, rtl=None, check=None, evidence=None, stream=None, module=None):
            x = elems.setdefault(e, dict(designs=[], roles={}, parents={}, rtl=set(), modules=set(), checks=[], evidence=[], stream=None))
            if module: x['modules'].add(module)
            if d['design'] not in x['designs']: x['designs'].append(d['design'])
            prev = x['roles'].get(d['design'])
            if prev is None or prev in ('soft', 'macro') or (prev == 'leaf' and role == 'master'):
                x['roles'][d['design']] = role
            if parent: x['parents'].setdefault(d['design'], set()).add(parent)
            if rtl: x['rtl'].add(rtl)
            if check and check not in x['checks']: x['checks'].append(check)
            if evidence and evidence not in x['evidence']: x['evidence'].append(evidence)
            if stream and not x['stream']: x['stream'] = stream
        for d in cfg.get('designs', []):
            info = {k: d.get(k) for k in ('design', 'label', 'target', 'revision', 'lead', 'log', 'doc', 'complete', 'note')}
            info['sources'] = []; info['errors'] = []
            for src in d.get('sources', []):
                try:
                    got = self.extract(src)
                    for g in got:
                        put(g['element'], d, g['role'], g.get('parent'), g.get('rtl'), g.get('check'),
                            src.get('evidence') or src.get('path'), g.get('stream'), g.get('module'))
                    info['sources'].append(dict(kind=src['kind'], path=src.get('path'), n=len(got), evidence=src.get('evidence')))
                except Exception as e:
                    info['errors'].append(dict(path=src.get('path'), error=str(e)[:200]))
            for a in d.get('add', []):
                put(a['element'], d, a.get('role', 'master'), a.get('parent'), a.get('rtl'), None, a.get('evidence'), a.get('stream'))
            for r in d.get('retire', []):
                pats = r.get('pattern'); names = r.get('elements') or []
                retired_rule = dict(by=r.get('by'), reason=r.get('reason') or r.get('evidence'), evidence=r.get('evidence'),
                                    design=d['design'], label=d.get('label'))
                for n in names:
                    retired[n] = retired_rule
                    if n in elems and d['design'] in elems[n]['designs']:
                        elems[n]['designs'].remove(d['design']); elems[n]['roles'].pop(d['design'], None)
                        elems[n]['parents'].pop(d['design'], None)
                        if not elems[n]['designs']: del elems[n]
                if pats: retired['re:' + pats] = retired_rule
            streams = [(re.compile(p), s) for p, s in d.get('streams', [])]
            info['_streams'] = streams
            designs.append(info)
        return designs, elems, retired

    # ---------------------------------------------------------------- RTL leaf hierarchy
    def modules(self):
        t, rev, idx = self.mods
        if idx and time.time() - t < self.rtl_period: return idx
        r = self.repo.rev()
        if r and r == rev and idx: self.mods = (time.time(), rev, idx); return idx
        try: idx = self.repo.module_index()
        except Exception as e: self.log('die_contracts: module index: %s' % e)
        self.mods = (time.time(), r, idx); self.bodies = {}; self.hier_cache = {}
        return idx

    def children(self, mod, idx):
        if mod in self.bodies: return self.bodies[mod]
        kids = set()
        for f in idx.get(mod, [])[:4]:
            body = module_bodies(self.repo.read(f) or '').get(mod)
            if body: kids |= {k for k in instantiated(body) if k in idx and k != mod}
        self.bodies[mod] = kids
        return kids

    def subtree(self, mod, idx, depth=8):
        if mod in self.hier_cache: return self.hier_cache[mod]
        seen = set(); frontier = [mod]
        for _ in range(depth):
            nxt = []
            for m in frontier:
                for k in self.children(m, idx):
                    if k not in seen: seen.add(k); nxt.append(k)
            frontier = nxt
            if not frontier: break
        self.hier_cache[mod] = seen
        return seen

    # ---------------------------------------------------------------- public
    def load(self, known=()):
        """-> dict(designs, elements, retired, rtl_leaves) ; known = every row/variant name of the registry."""
        try:
            raw = self.repo.read(CONFIG); cfg = json.loads(raw) if raw else {}
        except Exception as e:
            self.log('die_contracts: %s: %s' % (CONFIG, e)); cfg = {}
        key = (self.repo.rev(), raw if raw else '')
        if key != self.key:
            self.base = self.build(cfg); self.key = key
        designs, elems, retired = self.base
        idx = self.modules(); known = set(known)
        # 'soft' members (every module of a die file list) count only when the registry already has them as elements
        elems = {e: x for e, x in elems.items() if e in known or any(r != 'soft' for r in x['roles'].values())}
        rtl_leaves = {}
        for e, x in list(elems.items()):
            if all(r in ('macro', 'soft') for r in x['roles'].values()) and e not in known: continue
            roots = {e} | x['modules']
            if e not in idx:   # a die name with no module of its own: the modules of its RTL file(s)
                for f in x['rtl']: roots |= set(module_bodies(self.repo.read(f) or ''))
            sub = set()
            for r in roots & set(idx): sub |= self.subtree(r, idx) | {r}
            for k in sub - {e}:
                if k in known and k not in elems:
                    rtl_leaves.setdefault(k, dict(parents=set(), designs=set()))
                    rtl_leaves[k]['parents'].add(e); rtl_leaves[k]['designs'].update(x['designs'])
        return dict(designs=designs, elements=elems, retired=retired, rtl_leaves=rtl_leaves, config=CONFIG)

    @staticmethod
    def stream(designs, design, element, explicit=None):
        if explicit: return explicit
        d = next((x for x in designs if x['design'] == design), None)
        if not d: return None
        for rx, s in d.get('_streams', []):
            if rx.search(element): return s
        return d.get('lead')
