#!/usr/bin/env python3
"""plan_pin_change.py -- which COUNTED designs does a plan pin change touch (COUNT-ARCHIVE-2, COORD 11-10, owner review list).

Why: a plan pin event quietly un-counts signed designs.  KV e2 moved 68 pins and a signed core dropped out of the count
with no warning; the re-sign was queued only after somebody noticed the count fall.  This tool lists, per die, every
currently counted design whose pin table (or outline) changes between an old and a new plan, so the die owner can queue
the re-signs in the same batch as the plan event.

ADVISORY ONLY.  It never credits, revokes or blocks anything; the counter's own pin compare still decides the count.

A design is the counter's design (release_tree_plan.plan_designs: module + outline + pin table without strap_* pins).
For each design counted on the old plan (cache signed_designs) its old pin rows are compared with the new plan's design
of the same module (same outline first, else the only one, else the closest by pin names):
  moved    same pin name, different layer or |dx| or |dy| > PIN_TOL_NM (the counter's tolerance)
  added    pin only in the new table          removed  pin only in the old table
  outline  outline changed                    gone     module no longer a hard core of the new plan
A change inside the tolerance is not listed (the counter would still credit the record).

Uses:
  * by hand:  plan_pin_change.py --old OLD/die_plan.json[.gz] --new NEW/die_plan.json[.gz] --die qwen_kvsys [--cache C]
              (plan-relative pins files resolve beside each plan, as in the counter; counted designs come from the
              counter cache entry of that die; --all lists every changed design, counted or not)
  * hourly:   release_tree_plan.refresh() calls track() per die after crediting.  track() keeps the last plan pin rows
              per die in STATE/plan_pins/<die>.json, compares, and appends any finding to STATE/plan_pin_changes.jsonl.
              count_hourly.py posts unposted findings to the review queue, addressed to the die owner.
"""
import argparse
import gzip
import json
import os
import pathlib
import sys
import time

STATE = pathlib.Path(os.environ.get('OT_PIN_CHANGE_STATE') or pathlib.Path.home() / '.local/state/fleet-viz')
LOG = 'plan_pin_changes.jsonl'
PIN_TOL_NM = 200          # = release_tree_plan.PIN_TOL_NM
SHOW = 6                  # pin names shown per class in a queue line
DIE_OWNER = {'s81': 'DIE-S81', 's81_head': 'DIE-HEAD', 'qwen_compute': 'DIE-QC', 'qwen_kvsys': 'DIE-KV', 'hbm': 'DIE-HBM'}


def diff_rows(a, b, tol=PIN_TOL_NM):
    """old rows a vs new rows b ({pin: (layer, x_nm, y_nm)}) -> {moved, added, removed}: sorted pin names"""
    a, b = a or {}, b or {}
    moved = []
    for n in sorted(set(a) & set(b)):
        la, xa, ya = a[n]
        lb, xb, yb = b[n]
        if la != lb or None in (xa, ya, xb, yb):
            if (la, xa, ya) != (lb, xb, yb): moved.append(n)
        elif abs(xa - xb) > tol or abs(ya - yb) > tol:
            moved.append(n)
    return dict(moved=moved, added=sorted(set(b) - set(a)), removed=sorted(set(a) - set(b)))


def _pick(g, rows, cands, new_designs, new_rows):
    """the new design of the same module that stands for old design g"""
    if not cands: return None
    same = [k for k in cands if new_designs[k].get('outline_um') == g.get('outline_um')]
    if len(same) == 1: return same[0]
    pool = same or cands
    if len(pool) == 1: return pool[0]
    names = set(rows or {})
    return max(sorted(pool), key=lambda k: len(names & set(new_rows.get(k) or {})))


def changes(die, old_designs, old_rows, new_designs, new_rows, counted=None, still=None, old_plan=None, new_plan=None,
            tol=PIN_TOL_NM):
    """-> list of findings, one per old design whose pin table / outline changes (only counted ones when counted is
    given: {old design id: [refs]}).  still = the new plan's signed_designs, to say whether it is still counted."""
    by_mod = {}
    for k, g in (new_designs or {}).items():
        by_mod.setdefault(g.get('module'), []).append(k)
    out = []
    for did in sorted(old_designs or {}):
        if counted is not None and did not in counted: continue
        g = old_designs[did]
        m = g.get('module')
        ro = (old_rows or {}).get(did)
        nk = _pick(g, ro, by_mod.get(m) or [], new_designs, new_rows or {})
        f = dict(die=die, design=did, module=m, old_plan=old_plan, new_plan=new_plan, new_design=nk,
                 counted_entry=((counted or {}).get(did) or [None])[0])
        if nk is None:
            f.update(gone=True, moved=[], added=[], removed=sorted(ro or {}), outline=None)
        else:
            ng = new_designs[nk]
            if ng.get('pins_sha') == g.get('pins_sha') and ng.get('outline_um') == g.get('outline_um'): continue
            d = diff_rows(ro, (new_rows or {}).get(nk), tol)
            ol = None if ng.get('outline_um') == g.get('outline_um') else [g.get('outline_um'), ng.get('outline_um')]
            if not (d['moved'] or d['added'] or d['removed'] or ol): continue
            f.update(gone=False, outline=ol, **d)
        if still is not None:
            f['still_counted'] = bool(nk and nk in still)
        out.append(f)
    return out


def summary(f):
    """one line per finding"""
    if f.get('gone'):
        what = 'module gone from the new plan'
    else:
        parts = []
        for k in ('moved', 'added', 'removed'):
            if f.get(k):
                parts.append('%d pins %s (%s%s)' % (len(f[k]), k, ', '.join(f[k][:SHOW]), ', ...' if len(f[k]) > SHOW else ''))
        if f.get('outline'):
            parts.append('outline %s -> %s' % tuple('x'.join('%g' % v for v in o or []) for o in f['outline']))
        what = '; '.join(parts)
    st = '' if 'still_counted' not in f else (' still counted' if f['still_counted'] else ' NO LONGER COUNTED')
    return '%s %s: %s.%s Counted entry: %s' % (f['die'], f['design'], what, st, f.get('counted_entry') or '-')


# ---- hourly tracking (called from release_tree_plan.refresh; never raises into the counter) -------------------------
def snapshot(die, plan, designs, rows):
    return dict(die=die, plan=plan, generated=time.time(),
                designs={k: dict(module=g.get('module'), outline_um=g.get('outline_um'), pins_sha=g.get('pins_sha'))
                         for k, g in (designs or {}).items()},
                rows={k: {n: list(v) for n, v in (r or {}).items()} for k, r in (rows or {}).items()})


def _rows_of(snap):
    return {k: {n: tuple(v) for n, v in (r or {}).items()} for k, r in (snap.get('rows') or {}).items()}


def counted_on(cache, die):
    """{design id: refs} counted for die in a counter cache (all plan entries of that die)"""
    out = {}
    for e in ((cache or {}).get('plans') or {}).values():
        if e.get('die') == die:
            out.update(e.get('signed_designs') or {})
    return out


def track(die, plan, designs, rows, old_cache, still=None, state=None, now=None):
    """compare this refresh's plan pins of die with the last snapshot; findings for designs counted in old_cache are
    appended to the log.  Writes the new snapshot.  -> findings (list)"""
    state = pathlib.Path(state or STATE)
    d = state / 'plan_pins'
    d.mkdir(parents=True, exist_ok=True)
    p = d / ('%s.json' % die)
    prev = None
    try: prev = json.loads(p.read_text())
    except (OSError, ValueError): pass
    found = []
    if prev and prev.get('designs') is not None:
        found = changes(die, prev['designs'], _rows_of(prev), designs, rows, counted=counted_on(old_cache, die),
                        still=still, old_plan=prev.get('plan'), new_plan=plan)
    t = p.with_suffix('.tmp')
    t.write_text(json.dumps(snapshot(die, plan, designs, rows)))
    os.replace(t, p)
    if found:
        stamp = time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(now or time.time()))
        with open(state / LOG, 'a') as fh:
            for f in found:
                fh.write(json.dumps(dict(f, at=stamp, id='%s|%s|%s|%s' % (die, f['design'], prev.get('plan'), stamp))) + '\n')
    return found


def unposted(state=None):
    """log rows not yet posted -> (rows, mark function)"""
    state = pathlib.Path(state or STATE)
    log, seen_p = state / LOG, state / (LOG + '.posted')
    try: rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    except (OSError, ValueError): rows = []
    try: seen = set(seen_p.read_text().splitlines())
    except OSError: seen = set()
    new = [r for r in rows if r.get('id') not in seen]

    def mark():
        with open(seen_p, 'a') as fh:
            for r in new: fh.write(r['id'] + '\n')
    return new, mark


def queue_lines(rows, stamp):
    """review-queue lines, one per die, addressed to the die owner (advisory)"""
    by = {}
    for r in rows: by.setdefault(r['die'], []).append(r)
    out = []
    for die in sorted(by):
        rs = by[die]
        plans = sorted({'%s -> %s' % (r.get('old_plan'), r.get('new_plan')) for r in rs})
        out.append('- %s ADVISORY [COUNT-HOURLY -> %s owner, COORD] plan pin change touches %d counted design(s) on %s (%s); '
                   'queue their re-signs with this plan event. Advisory only, nothing revoked or blocked:' % (
                       stamp, DIE_OWNER.get(die, die), len(rs), die, '; '.join(plans)))
        out += ['  - ' + summary(r) for r in rs]
    return out


# ---- CLI --------------------------------------------------------------------------------------------------------------
def _load_plan(path):
    p = pathlib.Path(path)
    raw = p.read_bytes()
    if p.suffix == '.gz': raw = gzip.decompress(raw)
    return json.loads(raw)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--old', required=True); ap.add_argument('--new', required=True)
    ap.add_argument('--die', required=True)
    ap.add_argument('--cache', default=str(pathlib.Path.home() / '.local/state/fleet-viz/release_tree_plan_cache.json'))
    ap.add_argument('--all', action='store_true', help='list every changed design, counted or not')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import release_tree_plan as R
    od, orows = R.plan_designs(_load_plan(a.old), pathlib.Path(a.old).parent)
    nd, nrows = R.plan_designs(_load_plan(a.new), pathlib.Path(a.new).parent)
    cache = None
    if not a.all:
        try: cache = json.loads(pathlib.Path(a.cache).read_text())
        except (OSError, ValueError) as e:
            print('cannot read the counter cache %s (%s); use --all' % (a.cache, e), file=sys.stderr)
            return 2
    found = changes(a.die, od, orows, nd, nrows, counted=None if a.all else counted_on(cache, a.die),
                    old_plan=a.old, new_plan=a.new)
    if a.json:
        print(json.dumps(found, indent=1))
    else:
        print('die\tdesign\tmodule\tmoved\tadded\tremoved\toutline\tcounted_entry')
        for f in found:
            print('\t'.join([f['die'], f['design'], str(f['module']), str(len(f['moved'])), str(len(f['added'])),
                             str(len(f['removed'])), 'gone' if f.get('gone') else ('changed' if f.get('outline') else '-'),
                             f.get('counted_entry') or '-']))
        print('%d design(s)%s with a pin table change' % (len(found), '' if a.all else ' counted'), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
