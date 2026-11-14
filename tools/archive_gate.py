#!/usr/bin/env python3
"""archive_gate: a sign-off counts only when the AGIdock archive holds it (OWNER 2026-11-14: "always refer to the agidock
archive when you count the signed records; the fleet is temporary").  ONE gate for the count (release_tree_plan.py ->
forced count, RELEASE_TREE, SIGN-RATE) and the explorer, which reads the gated count cache.

A type / hard-core design the count credits stays in signed_types / signed_cores / signed_designs only when
  (a) /archive/opentallas-signed-1114/<die or target>/<name>/ on AGIdock holds, non-empty: the database (6_final.odb[.zst]),
      at least one view file (.v .def .spef .gds .lef .lib, also .zst) and the metadata (signoff.json); or
  (b) an INDEX.tsv row of that archive names it (SIGNED-RECOVER); or
  (c) the signed store holds a record of it whose files (incl. 6_final.odb) are in an AGIdock archive (the earlier archives).
Everything else moves to pending_archive_types / pending_archive_cores / pending_archive_designs (same refs): reported,
never counted.  Input: the archive listing written by tools/explorer/tools/archive_index.py on rtx-pro and pushed to
<state>/agidock_archive_index.json.  No listing, or one older than MAX_AGE_S: the gate does NOT run and says so in errors
(the count then shows credited numbers, flagged), so a broken timer cannot zero the count silently.

    python3 archive_gate.py [--cache FILE]      # print the gate result of a cache file (reads only)
"""
import argparse, gzip, json, os, pathlib, sys, time

STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
LISTING = pathlib.Path(os.environ.get('AGIDOCK_ARCHIVE_INDEX', STATE / 'agidock_archive_index.json'))
SIGNED_STORE = pathlib.Path(os.environ.get('OT_SIGNED_STORE', os.path.expanduser('~/coord/signed-store')))
MAX_AGE_S = float(os.environ.get('ARCHIVE_GATE_MAX_AGE_S', 6 * 3600))
EXPORT_DIES = dict(s81=('s81', 'DeepSeek_ROM', '_'), s81_head=('s81_head', 'DeepSeek_ROM', '_'), qwen_compute=('qwen_compute', 'Qwen_ROM', '_'),
                   qwen_kvsys=('qwen_kvsys', 'Qwen_ROM', '_'), hbm=('hbm', 'HBM_accelerator', '_'))
VIEW_EXT = ('.v', '.def', '.spef', '.gds', '.lef', '.lib', '.v.zst', '.def.zst', '.spef.zst', '.gds.zst')
KEYS = (('signed_types', 'pending_archive_types'), ('signed_cores', 'pending_archive_cores'), ('signed_designs', 'pending_archive_designs'))


def store_archived(root=None):
    """{(die, key)} of signed-store records whose 6_final.odb is in an archive"""
    out = set(); root = pathlib.Path(root or SIGNED_STORE) / 'records'
    if not root.is_dir(): return out
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if not fn.endswith('.json.gz'): continue
            try:
                with gzip.open(os.path.join(dp, fn), 'rt') as fh: e = json.load(fh)
            except Exception: continue
            if not e.get('archive') or not any(f[0].endswith('6_final.odb') and (len(f) < 2 or f[1]) for f in e.get('files') or []): continue
            for r in e.get('rows') or []: out.add((r.get('die'), r.get('key')))
    return out


def entry_state(files):
    fs = {f: z for f, z in files.items() if z and z > 0}   # a zero-byte file is not an archived file
    have = dict(db=any(f.endswith(('6_final.odb', '6_final.odb.zst')) for f in fs), view=any(f.endswith(VIEW_EXT) for f in fs), metadata=any(f.endswith('signoff.json') for f in fs))
    return [k for k, v in have.items() if not v]


class Gate:
    def __init__(self, listing=None, store=None, now=None):
        self.error = None; self.ent = {}; self.rows = set(); self.store = set()
        p = pathlib.Path(listing or LISTING)
        try: A = json.loads(p.read_text())
        except Exception as e: self.error = 'ARCHIVE GATE NOT APPLIED: no archive listing (%s: %s)' % (p, e); return
        if 'agidock' not in A: self.error = 'ARCHIVE GATE NOT APPLIED: listing has no AGIdock part (%s)' % A.get('agidock_error'); return
        self.listed = A.get('agidock_listed') or 0
        if (now or time.time()) - self.listed > MAX_AGE_S: self.error = 'ARCHIVE GATE NOT APPLIED: archive listing is %.1f h old' % (((now or time.time()) - self.listed) / 3600); return
        for e in A['agidock']: self.ent[(e['die'], e['name'])] = e
        for ln in (A.get('agidock_index_tsv') or '').splitlines():
            if ln.strip() and not ln.startswith('#'): self.rows.update(c.strip() for c in ln.split('\t') if c.strip())
        self.store = store_archived(store)

    def check(self, die, names):
        """-> (archived basis | None, why-not dict)"""
        miss = dict(missing=['db', 'view', 'metadata'], path=None)
        for nm in names:
            for d in EXPORT_DIES.get(die, (die,)):
                e = self.ent.get((d, nm))
                if not e: continue
                m = entry_state(e['files'])
                if not m: return 'opentallas-signed-1114 ' + e['path'], None
                miss = dict(missing=m, path=e['path'], zero_byte=sorted(f for f, z in e['files'].items() if not z))
        for nm in names:
            if nm in self.rows: return 'INDEX.tsv row', None
            if (die, nm) in self.store: return 'signed-store record in an AGIdock archive', None
        return None, miss


def ungate(cache):
    """the credited sets again (signed + pending), for the carry-over logic of the count"""
    if not cache: return cache
    c = json.loads(json.dumps(cache))
    for ent in (c.get('plans') or {}).values():
        for sk, pk in KEYS:
            if ent.get(pk):
                s = ent.get(sk)
                if s is None: s = ent[sk] = {}
                for k, v in ent[pk].items(): s.setdefault(k, v)
            ent.pop(pk, None)
        ent.pop('archive_gate', None)
    return c


def apply(cache, gate=None):
    """moves what is not archived out of the signed sets, in place; returns the cache"""
    g = gate or Gate()
    if g.error:
        cache.setdefault('errors', []).append(g.error); cache['archive_gate'] = dict(applied=False, error=g.error); return cache
    tot = {}
    for ent in (cache.get('plans') or {}).values():
        die = ent.get('die'); D = ent.get('designs') or {}; why = {}; basis = {}
        names_of = dict(signed_types=lambda k: [k], signed_cores=lambda k: [k], signed_designs=lambda k: [x for x in [(D.get(k) or {}).get('module'), k] if x])
        cnt = {}
        for sk, pk in KEYS:
            s = ent.get(sk)
            if not isinstance(s, dict): continue
            pend = {}
            for k in list(s):
                ok, miss = g.check(die, names_of[sk](k))
                if ok: basis[k] = ok
                else: pend[k] = s.pop(k); why[k] = miss
            ent[pk] = pend; cnt[sk] = len(s); cnt[pk] = len(pend)
        ent['archive_gate'] = dict(counts=cnt, why=why, basis=basis)
        tot[die] = cnt
    cache['archive_gate'] = dict(applied=True, listed=g.listed, entries=len(g.ent), index_tsv=bool(g.rows), store_records=len(g.store), dies=tot,
                                 rule='signed = credited AND database + view file + signoff.json non-empty in the AGIdock archive (or INDEX.tsv row, or signed-store record in an AGIdock archive); else pending archive, not counted')
    return cache


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', default=str(STATE / 'release_tree_plan_cache.json'))
    a = ap.parse_args()
    c = apply(ungate(json.loads(pathlib.Path(a.cache).read_text())))
    print(json.dumps(c['archive_gate'], indent=1))
