"""Current-plan element rows for /api/elements, /api/die_elements and the Chip Explorer (WEBVIEW-1, 2026-11-03).

Reads <state>/plan_now.json (plan_now.py, cron every 30 min) and turns each element of the CURRENT die plans of record
(partition types + hard cores, kit-wave items of the current event) into the row schema elements.py serves, so the
existing pages render today's sign-off / routing / timing state.  The old closure-loop job rows (October) stay available
as legacy_rows (/api/elements?legacy=1)."""
import json, os, pathlib, time

STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
PATH = STATE / 'plan_now.json'
BUCKET = {'signed off': 'closed', 'signed off (legacy view)': 'closed', 'routing / sign-off running': 'in_flight',
          'running (pre-route)': 'in_flight', 'queued': 'in_flight', 'waiting (dependency / plan delta)': 'not_started',
          'not started': 'not_started', 'cancelled': 'failed'}
_cache = dict(mt=None, d=None)


def load():
    try: mt = PATH.stat().st_mtime
    except OSError: return None
    if _cache['mt'] != mt:
        try: _cache.update(mt=mt, d=json.loads(PATH.read_text()))
        except Exception: return _cache['d']
    return _cache['d']


def _num(x):
    try: return round(float(x), 2)
    except (TypeError, ValueError): return None


def row(e, dies):
    m = e.get('m') or {}; kw = e.get('kw') or {}; sg = e.get('signed') or {}; d = dies.get(e['die']) or {}
    signed = e['category'].startswith('signed off')
    t_sig = None
    if m.get('signoff_generated'):
        try:
            import datetime
            t_sig = datetime.datetime.fromisoformat(m['signoff_generated']).timestamp()
        except Exception: t_sig = None
    job = (m.get('signoff') or kw.get('kit') or sg.get('entry') or '')
    lt = None
    if kw:
        lt = dict(t=kw.get('updated') or 0, job='%s %s attempt %s' % (kw.get('event') or '', kw.get('stage') or '', kw.get('attempt') or '-'),
                  status=kw.get('status') or '', text=(kw.get('reason') or '')[:400])
    elif signed:
        lt = dict(t=t_sig or 0, job=(sg.get('entry') or '')[:160], status='SIGNED', text=sg.get('entry') or '')
    reasons = '; '.join(m.get('reasons') or [])
    via = 'signed view: ' + sg['entry'][:300] if sg.get('entry') else ''
    if e.get('not_in_plan'): via = (via + ' · ' if via else '') + 'kit-wave item not in the plan-of-record type list'
    purpose = '%s %s of %s' % (e['die'], e.get('kind') or 'element', pathlib.PurePosixPath(d.get('plan_path') or '').name)
    if reasons: purpose += ' · ' + reasons
    return dict(element=e['element'], target=e['target'], variants=[], category=e['category'], via=via, purpose=purpose, summary=purpose,
                about='', family='', family_about='',
                jobs=int(kw.get('attempt') or 0) if kw else 0, live=1 if kw.get('status') in ('RUNNING', 'ENQUEUED') else 0,
                failed=1 if kw.get('status') == 'FAIL' and not signed else 0, closed_jobs=1 if signed else 0,
                best=dict(tt=_num(m.get('tt_wns')), ff=_num(m.get('ff_wns')), ss=None,
                          drc=m.get('drc') if m.get('drc') is not None else m.get('drt_drc'), job=job, corner='TT' if m.get('tt_wns') is not None else None,
                          source_commit=None),
                area=dict(die=None, core=None, util=None), revoked=None, latest=lt, closed_t=t_sig if signed else None,
                owner='', owner_orig='', owner_stream='', superseded=None, qualification=None, evidence_history=[], throughput=None, gate='',
                dies=[dict(design=e['die'], label=d.get('label') or e['die'], role=e.get('kind') or '', revision=d.get('plan_path'))],
                contract='%s plan %s (%s)' % (e['die'], pathlib.PurePosixPath(d.get('plan_path') or '').name, (d.get('plan_commit') or '')[:10]),
                # current-plan fields (index.html: GRT / DRT / LEC / stage columns)
                die=e['die'], kind=e.get('kind'), grt=m.get('grt_overflow'), grt_wl=m.get('grt_wl_um'), drt=m.get('drt_drc'),
                drt_wl=m.get('drt_wl_um'), lec=m.get('lec'), antenna=m.get('antenna'), verdict=m.get('verdict'),
                failing=m.get('failing'), flow_stage=m.get('flow_stage'), kw_stage=kw.get('stage'), kw_class=kw.get('cls'),
                kw_event=kw.get('event'), kit=kw.get('kit'), signed_view=sg.get('entry'), signoff=m.get('signoff'),
                signoff_generated=m.get('signoff_generated'), metrics_from=e.get('metrics_from'), cells=m.get('cells'),
                plan_sha=kw.get('plan_sha'), current=True)


def overlay(res):
    """replace the legacy job rows of an elements.compute() result by the current-plan rows (when plan_now.json exists)"""
    d = load()
    if not d or not d.get('elements'): return res
    dies = {x['die']: x for x in d['dies']}
    rows = [row(e, dies) for e in d['elements']]
    cats = d.get('cats') or sorted({r['category'] for r in rows})
    targets = res.get('targets') or ['Qwen ROM', 'DeepSeek ROM', 'HBM accelerator', 'Other']
    rows.sort(key=lambda r: (targets.index(r['target']) if r['target'] in targets else 99, r['die'], cats.index(r['category']) if r['category'] in cats else 99, r['element']))
    summ = {}
    for r in rows:
        s = summ.setdefault(r['target'], {}); s[r['category']] = s.get(r['category'], 0) + 1
    designs = {}
    for x in d['dies']:
        c = x.get('counts') or {}
        b = {}
        for k, v in c.items(): b[BUCKET.get(k, 'failed')] = b.get(BUCKET.get(k, 'failed'), 0) + v
        kwv = x.get('kit_wave') or {}
        designs[x['die']] = dict(label=x['label'], target=x['target'], lead='',
                                 revision='%s @ %s (%s, sha256 %s) · kit wave %s plan %s' % (
                                     x.get('plan_path'), (x.get('plan_commit') or '')[:10], (x.get('plan_date') or '')[:16],
                                     x.get('plan_sha256'), ','.join(sorted(map(str, kwv.get('events') or {}))) or '-', kwv.get('plan_sha') or '-'),
                                 complete=True, closed=b.get('closed', 0), in_flight=b.get('in_flight', 0), failed=b.get('failed', 0),
                                 not_started=b.get('not_started', 0), superseded=0, open=sum(v for k, v in b.items() if k != 'closed'),
                                 total=sum(b.values()), errors=[x['error']] if x.get('error') else [], integration_records=0)
    legacy = dict(rows=res.get('rows'), summary=res.get('summary'), cats=res.get('cats'), designs=res.get('designs'))
    res = dict(res, rows=rows, independent_rows=rows, integration_rows=[], cats=cats, summary=summ, designs=designs,
               throughput_summary={}, legacy=legacy,
               plan_now=dict(generated=d.get('generated'), repo=d.get('repo'), sources=d.get('sources'),
                             dies=[{k: v for k, v in x.items() if k not in ('types', 'hard')} for x in d['dies']]))
    return res


def die_elements():
    """/api/die_elements in the current-plan form (index.html uses .rows[].element as the current-die set)"""
    d = load()
    if not d: return None
    return dict(schema='opentallas.fleet_viz.die_elements.plan_now.v1', generated=d.get('generated'),
                generator='fleet-viz plan_now.py (current plans of record)',
                dies=[{k: v for k, v in x.items() if k not in ('types', 'hard')} for x in d['dies']],
                rows=[dict(element=e['element'], die=e['die'], kind=e.get('kind'), category=e['category']) for e in d['elements']])
