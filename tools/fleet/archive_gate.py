#!/usr/bin/env python3
"""archive_gate: a sign-off counts only when the AGIdock archive holds it (OWNER 2026-11-14: "always refer to the agidock
archive when you count the signed records; the fleet is temporary").  ONE gate for the count (release_tree_plan.py ->
forced count, RELEASE_TREE, SIGN-RATE) and the explorer, which reads the gated count cache.

A type / hard-core design the count credits stays in signed_types / signed_cores / signed_designs only when
  (a) /archive/opentallas-signed-1114/<die or target>/<name>/ on AGIdock holds, non-empty: the database (6_final.odb[.zst])
      and the metadata (signoff.json) (COORD 11-14: a missing view pack is a separate column, never a count drop); or
  (b) an INDEX.tsv row of that archive names it (SIGNED-RECOVER); or
  (c) the signed store holds a record of it whose files (incl. 6_final.odb) are in an AGIdock archive (the earlier archives).
Everything else moves to pending_archive_types / pending_archive_cores / pending_archive_designs (same refs): reported,
never counted.  Input: the archive listing written by tools/explorer/tools/archive_index.py on rtx-pro and pushed to
<state>/agidock_archive_index.json.  No listing, or one older than MAX_AGE_S: the gate does NOT run and says so in errors
(the count then shows credited numbers, flagged), so a broken timer cannot zero the count silently.

    python3 archive_gate.py [--cache FILE]      # print the gate result of a cache file (reads only)
"""
import argparse, gzip, json, os, pathlib, re, sys, time

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
    return [k for k in ('db', 'metadata') if not have[k]]


VARIANT_TAIL = re.compile(r'[A-Za-z0-9]+__[A-Za-z0-9_]+')


def variant_of(module, element):
    """FLOW-FLEET-R2 X1 11-22: AUTO-EXPORT gives each variant of one module its own element when units collide: ot_hdc_v41x_attn_tr_x_xoff0__h8_1119 for the module
    ot_hdc_v41x_attn_tr_x (4 xoff designs, pending_archive for hours with their DB + metadata exported).  <module>_<tag>__<rest> is a variant of <module>; a longer
    MODULE name (ot_s81_cfg7_seq_bfp for ot_s81_cfg7_seq) has no '__' tail and never matches."""
    return element.startswith(module + '_') and bool(VARIANT_TAIL.fullmatch(element[len(module) + 1:]))


class Gate:
    def __init__(self, listing=None, store=None, now=None):
        self.error = None; self.ent = {}; self.rows = set(); self.store = set(); self.index = {}; self.by_die = {}
        p = pathlib.Path(listing or LISTING)
        try: A = json.loads(p.read_text())
        except Exception as e: self.error = 'ARCHIVE GATE NOT APPLIED: no archive listing (%s: %s)' % (p, e); return
        if 'agidock' not in A: self.error = 'ARCHIVE GATE NOT APPLIED: listing has no AGIdock part (%s)' % A.get('agidock_error'); return
        self.listed = A.get('agidock_listed') or 0
        if (now or time.time()) - self.listed > MAX_AGE_S: self.error = 'ARCHIVE GATE NOT APPLIED: archive listing is %.1f h old' % (((now or time.time()) - self.listed) / 3600); return
        for e in A['agidock']: self.ent[(e['die'], e['name'])] = e
        # INDEX.tsv (SIGNED-RECOVER): die element kind record db rtx_db size sha256 pack meta status src
        lines = [l for l in (A.get('agidock_index_tsv') or '').splitlines() if l.strip() and not l.startswith('#')]
        self.index = {}
        if lines and lines[0].split('\t')[:2] == ['die', 'element']:
            head = lines[0].split('\t')
            for ln in lines[1:]:
                r = dict(zip(head, ln.split('\t')))
                self.index[(r.get('die'), r.get('element'))] = r
                self.by_die.setdefault(r.get('die'), []).append(r)
        else:
            for ln in lines: self.rows.update(c.strip() for c in ln.split('\t') if c.strip())
        self.store = store_archived(store)

    def view_pack(self, die, names):
        """is the routed-layout view pack of the design in the archive (_view-packs/<die>.<t|c>.<name>.lvp or <name>/...)"""
        for nm in names:
            for d in EXPORT_DIES.get(die, (die,)):
                r = self.index.get((d, nm))
                if r and r.get('pack') and 'NO-VIEWPACK' not in (r.get('status') or ''): return True
        vp = self.ent.get(('_view-packs', die)) or {}
        fs = [f for f, z in (vp.get('files') or {}).items() if z]
        return any(('.%s.lvp' % nm) in f or f.startswith(nm + '/') or f.split('/')[0] in ('%s.t.%s' % (die, nm), '%s.c.%s' % (die, nm)) for nm in names for f in fs)

    def check(self, die, names):
        """-> (archived basis | None, why-not dict)"""
        miss = dict(missing=['db', 'metadata'], path=None)
        for nm in names:   # the archive's own index first: ARCHIVED-BOTH[-NO-VIEWPACK] = DB + metadata in both archives, sha256 equal
            for d in EXPORT_DIES.get(die, (die,)):
                r = self.index.get((d, nm))
                if not r: continue
                if (r.get('status') or '').startswith(('ARCHIVED-BOTH', 'RTX-FULL-AGI-META')): return 'INDEX.tsv ' + r['status'], None   # OWNER split 11-18: full DB on rtx-pro, metadata on AGIdock
                miss = dict(missing=['db'] if 'NO-DB' in (r.get('status') or '') else ['db', 'metadata'], path=r.get('db') or None, index_status=r.get('status'))
        for nm in names:
            for d in EXPORT_DIES.get(die, (die,)):
                e = self.ent.get((d, nm))
                if not e: continue
                m = entry_state(e['files'])
                if not m: return 'opentallas-signed-1114 ' + e['path'], None
                miss = dict(missing=m, path=e['path'], zero_byte=sorted(f for f, z in e['files'].items() if not z))
        for nm in names:       # a variant element of the module (variant_of): the same ARCHIVED-BOTH / RTX-FULL-AGI-META rule
            for d in EXPORT_DIES.get(die, (die,)):
                for r in self.by_die.get(d, ()):
                    if variant_of(nm, r.get('element') or '') and (r.get('status') or '').startswith(('ARCHIVED-BOTH', 'RTX-FULL-AGI-META')):
                        return 'INDEX.tsv variant ' + r['element'], None
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
        # FLOW-FLEET-R1 11-22: AUTO-EXPORT names a type's archive unit by its plan key (die hint) OR by its top module (die inferred from a lane / wave
        # path: s81p_slice_station__t36, qfd_qc_slw_sc for slw_sc_v2), so a type is looked up under both; it sat in pending_archive for hours otherwise
        PT = ent.get('plan_types') or {}
        names_of = dict(signed_types=lambda k: [x for x in dict.fromkeys([k, PT.get(k) if isinstance(PT.get(k), str) else None]) if x], signed_cores=lambda k: [k],
                        signed_designs=lambda k: [x for x in [(D.get(k) or {}).get('module'), k] if x])
        cnt = {}; novp = []
        for sk, pk in KEYS:
            s = ent.get(sk)
            if not isinstance(s, dict): continue
            pend = {}
            for k in list(s):
                ok, miss = g.check(die, names_of[sk](k))
                if ok:
                    basis[k] = ok
                    if sk != 'signed_designs' and not g.view_pack(die, names_of[sk](k)): novp.append(k)
                else: pend[k] = s.pop(k); why[k] = miss
            ent[pk] = pend; cnt[sk] = len(s); cnt[pk] = len(pend)
        cnt['no_view_pack'] = len(novp)
        ent['archive_gate'] = dict(counts=cnt, why=why, basis=basis, no_view_pack=sorted(novp))
        tot[die] = cnt
    cache['archive_gate'] = dict(applied=True, listed=g.listed, entries=len(g.ent), index_tsv=bool(g.rows or g.index), index_rows=len(g.index), store_records=len(g.store), dies=tot,
                                 rule='signed = credited AND database + signoff.json non-empty in the AGIdock archive; a missing view pack is listed, not a count drop (or INDEX.tsv row, or signed-store record in an AGIdock archive); else pending archive, not counted')
    return cache


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', default=str(STATE / 'release_tree_plan_cache.json'))
    a = ap.parse_args()
    c = apply(ungate(json.loads(pathlib.Path(a.cache).read_text())))
    print(json.dumps(c['archive_gate'], indent=1))
