#!/usr/bin/env python3
"""Current timing-closure verdicts for the Live verdicts panel (MONITOR-FIX 2026-11-06).

The panel used to read only the closure-loop ledger, which stopped on 10-29 when work moved to the kit wave, so the "live"
feed was 8 days old with 0 verdicts in 24 h.  This module derives the same row schema from the two current sources:
  * <state>/plan_now.json (plan_now.py, cron 30 min): per element of the current plans, the sign-off verdict, TT/FF WNS, DRC;
  * <coord>/autopilot/kit_wave_stages.tsv (kit wave, rsynced from the hub every 10 min): FAIL / SIGNED rows and running stages.
"""
import collections, csv, datetime, json, os, pathlib, re

STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
COORD = pathlib.Path(os.environ.get('OT_RELEASE_TREE_DIR', os.path.expanduser('~/coord')))
PLAN_NOW = STATE / 'plan_now.json'
STAGES = COORD / 'autopilot' / 'kit_wave_stages.tsv'
HUB = os.environ.get('FLEET_HUB', 'intel2')
TARGET = dict(s81='DeepSeek ROM', s81_head='DeepSeek ROM', qwen_compute='Qwen ROM', qwen_kvsys='Qwen ROM', hbm='HBM accelerator')
ROUTE_STAGES = ('route', 'signoff', 'resume_fp')
FAIL_LABEL = dict(TIMING='FAIL TIMING', ROUTING='FAIL ROUTE', PLAN='FAIL PLAN', RTL='FAIL RTL', SOURCE='FAIL SOURCE',
                  VOLUME='FAIL VOLUME', INFRA='FAIL INFRA')


def _ts(s):
    try: return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M').timestamp()
    except (TypeError, ValueError): pass
    try: return datetime.datetime.fromisoformat(s).timestamp()
    except (TypeError, ValueError): return None


def _host(*vals):
    """fleet host of 'host:/path' (the kit wave says localhost for its hub; the release cache says local for the coordinator)"""
    for v in vals:
        m = re.match(r'(?:.*\| )?([A-Za-z][\w-]*):/', v or '')
        if m: return dict(localhost=HUB, local='localhost').get(m.group(1), m.group(1))
    return ''


def _row(t, die, item, status, kind, why, host, setup=None, hold=None, drc=None, check='', detail=''):
    return dict(t=t, name='%s/%s' % (die, item), block=item, status=status, why=(why or '')[:400], detail=detail[:300], host=host,
                setup=setup, hold=hold, drc=drc, corner='TT', target='TT>=0 / FF>=0', kind=kind, check=check[:160],
                cat=TARGET.get(die, 'Other'))


def signoff_row(e):
    """verdict row of one plan_now element from its sign-off metrics, or None"""
    m = e.get('m') or {}; v = m.get('verdict')
    t = _ts(m.get('signoff_generated')) or m.get('signoff_mtime')
    if not v or not t: return None
    tt, ff, drc = m.get('tt_wns'), m.get('ff_wns'), m.get('drc')
    host = _host((e.get('signed') or {}).get('entry'), (e.get('kw') or {}).get('kit')) if m.get('kind') == 'signoff' else _host((e.get('kw') or {}).get('kit'))
    host = host or m.get('signoff_host') or ''
    reasons = [str(r) for r in m.get('reasons') or []]
    a = (e['die'], e['element'])
    if v == 'SIGNED': return _row(t, *a, 'SIGNED OFF', 'closed', 'sign-off PASS', host, tt, ff, drc)
    if v == 'LOCAL_PASS_NEEDS_PARENT': return _row(t, *a, 'NEEDS PARENT', 'closed', 'local pass; io_hold_parent receipt from die STA outstanding', host, tt, ff, drc)
    late = (tt is not None and tt < 0) or (ff is not None and ff < 0)
    return _row(t, *a, 'NOT SIGNED', 'timing' if late else 'check', '; '.join(reasons), host, tt, ff, drc,
                check='' if late else ', '.join(r.split(':')[0] for r in reasons))


def fail_row(r):
    cl = r.get('class') or ''
    kind = 'timing' if cl == 'TIMING' else 'flow'
    return _row(_ts(r.get('updated')), r['die'], r['item'], FAIL_LABEL.get(cl, 'FAIL FLOW'), kind, r.get('reason') or '',
                _host(r.get('kit'), r.get('evidence')), detail='%s @ %s event %s' % (cl or 'FLOW', r.get('stage') or '?', r.get('event') or '?'))


def build(elements, stage_rows):
    """(verdict rows, running-route count by target).  One element gives at most its sign-off verdict and its latest kit-wave
    failure; a failure older than a sign-off is history and is dropped, and NOT SIGNED + a failure merge into one row."""
    fails = {}; running = collections.Counter(); signed_rows = {}
    for r in stage_rows:
        if r.get('plan_current') != 'yes': continue
        k = (r.get('die'), r.get('item'))
        if r.get('status') == 'FAIL':
            f = fail_row(r)
            if f['t'] and (k not in fails or f['t'] > fails[k]['t']): fails[k] = f
        elif r.get('status') == 'SIGNED':
            t = _ts(r.get('updated'))
            if t and (k not in signed_rows or t > signed_rows[k]['t']):
                signed_rows[k] = _row(t, r['die'], r['item'], 'SIGNED OFF', 'closed', r.get('reason') or '', _host(r.get('kit'), r.get('evidence')))
        elif r.get('status') == 'RUNNING' and r.get('stage') in ROUTE_STAGES:
            running[TARGET.get(r.get('die'), 'Other')] += 1
    out = []; seen = set()
    for e in elements:
        k = (e.get('die'), e.get('element'))
        so = (signoff_row(e) if k[0] and k[1] else None) or signed_rows.get(k)
        f = fails.get(k); seen.add(k)
        if so and f:
            if so['status'] == 'NOT SIGNED':
                if f['t'] > so['t']: so.update(t=f['t'], why=f['why'], status=f['status'], detail=f['detail'])
                f = None
            elif f['t'] <= so['t']: f = None
        out += [x for x in (so, f) if x]
    for k, f in fails.items():
        if k not in seen and not (k in signed_rows and signed_rows[k]['t'] >= f['t']): out.append(f)
    out += [v for k, v in signed_rows.items() if k not in seen]
    return out, dict(running)


class KitVerdicts:
    """rows from the two files, rebuilt only when one of them changes"""
    def __init__(self, plan_now=PLAN_NOW, stages=STAGES):
        self.plan_now, self.stages = pathlib.Path(plan_now), pathlib.Path(stages)
        self.key = None; self.rows = []; self.running = {}; self.err = None; self.t = None

    def scan(self):
        try:
            key = (self.plan_now.stat().st_mtime, self.stages.stat().st_mtime)
            if key != self.key:
                doc = json.loads(self.plan_now.read_text())
                with open(self.stages, newline='', errors='replace') as f:
                    csv.field_size_limit(10 ** 7)
                    st = list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))
                self.rows, self.running = build(doc.get('elements') or [], st); self.key = key
                self.t = min(doc.get('generated') or key[0], key[1])   # the older source: the freshness of the whole feed
            self.err = None
        except (OSError, ValueError, KeyError, TypeError) as e:
            self.err = '%s: %s' % (type(e).__name__, e)
        return self.rows
