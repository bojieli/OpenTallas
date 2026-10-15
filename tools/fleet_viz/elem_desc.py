"""Short element descriptions for the Chip Explorer and the element page header.

Source of truth: <repo>/results/fleet_viz/element_descriptions_manual.json (hand-written by agent element-desc-1011):
  {"elements": {"<element or die-master name>": {"summary": "<one line>", "about": "<2-4 sentences>", "family": "<family>"}}}
(a flat {name: {...}} map also works; "text" / "description" are accepted as the summary).  Read from the repo working
tree, else from origin/main (the shared checkout may sit on an old HEAD); re-read when the file changes, at most every
10 min from git.  An element without a manual entry falls back to the registry description (elements.py Describer:
die-master .env / RTL headers, else the cleaned job purpose).
"""
import json, pathlib, subprocess, threading, time

REL = 'results/fleet_viz/element_descriptions_manual.json'


def first_sentence(s, n=140):
    s = ' '.join(str(s or '').split())
    if len(s) <= n: return s
    cut = s[:n]
    i = max(cut.rfind('. '), cut.rfind('; '))
    return (cut[:i + 1] if i > 40 else cut.rsplit(' ', 1)[0] + '…')


class Desc:
    def __init__(self, repo, log=print):
        self.repo = pathlib.Path(repo); self.log = log
        self.lock = threading.Lock(); self.key = None; self.map = {}; self.git_t = 0; self.src = None

    def _parse(self, txt):
        d = json.loads(txt)
        d = d.get('elements', d) if isinstance(d, dict) else {}
        out = {}
        for k, v in d.items():
            if isinstance(v, str): v = dict(summary=v)
            if not isinstance(v, dict) or k.startswith('_') or k in ('schema', 'note', 'generated'): continue
            s = v.get('summary') or v.get('text') or v.get('description') or ''
            out[k] = dict(summary=first_sentence(s, 160), about=v.get('about') or '', family=v.get('family') or '')
        return out

    def manual(self):
        p = self.repo / REL
        try:
            mt = p.stat().st_mtime
            if self.key == ('wt', mt): return self.map
            m = self._parse(p.read_text()); src = 'working tree'
            with self.lock: self.key, self.map, self.src = ('wt', mt), m, src
            return m
        except FileNotFoundError: pass
        except Exception as e: self.log('elem_desc %s: %s' % (p, e))
        if time.time() - self.git_t < 600 and self.key and self.key[0] == 'git': return self.map
        self.git_t = time.time()
        try:
            r = subprocess.run(['git', '-C', str(self.repo), 'show', 'origin/main:' + REL], capture_output=True, text=True, timeout=20)
            m = self._parse(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
        except Exception as e:
            self.log('elem_desc git: %s' % e); m = {}
        with self.lock: self.key, self.map, self.src = ('git', self.git_t), m, 'origin/main' if m else None
        return m

    def get(self, name, purpose=None, aliases=()):
        m = self.manual()
        for k in (name,) + tuple(a for a in aliases if a):
            if k in m: return dict(m[k], src='manual')
        return dict(summary=first_sentence(purpose or ''), about=purpose if purpose and len(purpose) > 160 else '', family='',
                    src='registry' if purpose else None)

    def summaries(self, rows):
        """{element: one line} for every registry element (manual first, registry description otherwise) + manual-only names"""
        m = self.manual()
        out = {el: (m[el]['summary'] if el in m else first_sentence(r.get('purpose') or '')) for el, r in rows.items()}
        for k, v in m.items():
            if k not in out: out[k] = v['summary']
        return {k: v for k, v in out.items() if v}
