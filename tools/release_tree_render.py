#!/usr/bin/env python3
"""Render the shared release tree (RELEASE-TREE lane, owner 10-18 0hb/0hc).

Source of truth: /home/ubuntu/coord/RELEASE_TREE.md, the hand-edited work tree that Claude and Codex
coordinators keep current. The element layer is generated from the live element table (fleet-viz /api/elements, which
derives each current die's element list from results/fleet_viz/die_sources.json via die_contract_sync). Elements are
never hand-edited.

Writes:
  RELEASE_TREE.html          served live by fleet-viz at /release
  RELEASE_TREE_SUMMARY.txt   compact text summary for HANDOFF (also printed with --summary)
Run: python3 tools/release_tree_render.py [--summary] [--md PATH] [--elements URL|FILE]
Hourly: release-tree-render.timer (user). fleet-viz also re-renders on page load when the .md is newer than the .html.
"""
import argparse, collections, datetime, html, json, os, pathlib, re, sys, tempfile, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as RTP   # current-plan element layer (INFRA 10-24): G0C-clean types + SIGNED types/hard cores

BASE = pathlib.Path('/home/ubuntu/coord')
CACHE = pathlib.Path.home() / '.local/state/fleet-viz/release_tree_elements_cache.json'
STATUSES = ['RUNNING', 'WAITS', 'TODO', 'NEW', 'COORD', 'OWNER', 'FAIL', 'PASS', 'DONE', 'BLOCKED', 'NOT RUN']
CHIP = dict(DONE='ok', PASS='ok', RUNNING='run', WAITS='wait', TODO='wait', BLOCKED='wait', NEW='new', COORD='me', OWNER='me', FAIL='me', **{'NOT RUN': 'wait'})
GATES = [('BIND', 'Strict bind'), ('GRT', 'Die GRT overflow 0'), ('STA', 'Die STA TT/FF, real views'), ('CLK', 'Die clock check TT+FF')]
DIE_ORDER = ['s81', 'qwen_compute', 'qwen_kvsys', 'hbm']

# ------------------------------------------------------------------ markdown tree
ITEM = re.compile(r'^(\s*)- \[( |x|X)\] (\S+)\s+(.*)$')


def parse_item(m):
    ind, done, iid, rest = len(m.group(1).expandtabs(2)) // 2, m.group(2).lower() == 'x', m.group(3), m.group(4)
    f = [x.strip() for x in rest.split(' · ')]
    task = f[0]; rem = f[1:]
    struck = task.startswith('~~') and task.endswith('~~') and len(task) > 4
    task = task[2:-2] if struck else task
    status, owner, note = None, '', []
    si = next((i for i, x in enumerate(rem) if x.upper() in STATUSES), None)
    if si is not None:
        status = rem[si].upper(); owner = rem[0] if si >= 1 else ''
        note = rem[1:si] + rem[si + 1:] if si >= 1 else rem[si + 1:]
    elif rem:
        if len(rem) >= 2 or re.fullmatch(r'[A-Z0-9][A-Za-z0-9\-/+ ]{0,40}', rem[0]) and ' ' not in rem[0]:
            owner, note = rem[0], rem[1:]
        else:
            note = rem
    if status is None: status = 'DONE' if done else 'TODO'
    if done and status not in ('DONE', 'PASS'): status = 'DONE'
    return dict(level=ind, done=done or status in ('DONE',) and done, checked=done, id=iid, task=task, owner=owner,
                status=status, note=' · '.join(note), kids=[])


def parse_md(text):
    secs, cur, rules, pre = [], None, [], []
    stack = []
    sub = None
    for line in text.splitlines():
        if line.startswith('## '):
            head = line[3:].strip()
            parts = [p.strip() for p in head.split(' · ')]
            kind = parts[0].split()[0].upper()
            if kind == 'EDIT':
                cur = dict(kind='RULES', title=head, items=[], text=[]); secs.append(cur); stack = []; continue
            if kind == 'DIE':
                key = parts[0].split()[1]
                cur = dict(kind='DIE', key=key, title=parts[1] if len(parts) > 1 else key,
                           rev=next((p[4:] for p in parts if p.startswith('rev ')), ''),
                           est=next((p[5:].strip() for p in parts if p.startswith('est.')), ''), items=[], text=[])
            else:
                cur = dict(kind=kind, title=parts[1] if len(parts) > 1 else parts[0], extra=parts[2:], items=[], text=[], subs=[])
            secs.append(cur); stack = []; sub = None; continue
        if cur is None:
            pre.append(line); continue
        m = ITEM.match(line)
        if m:
            it = parse_item(m)
            while stack and stack[-1]['level'] >= it['level']: stack.pop()
            (stack[-1]['kids'] if stack else cur['items']).append(it); stack.append(it)
            continue
        if cur['kind'] == 'WAITS':
            if line.startswith('### '):
                sub = dict(title=line[4:].strip(), lines=[]); cur['subs'].append(sub); continue
            if line.startswith('- ') and sub is not None:
                sub['lines'].append(line[2:].strip()); continue
        if line.strip(): cur['text'].append(line)
    return pre, secs


def sec_key(s):
    return s['key'] if s['kind'] == 'DIE' else s['kind']


def load_done(md_path):
    """Finished items archived in RELEASE_TREE_DONE.md (next to the tree), counted per section key (die key or kind)."""
    p = pathlib.Path(md_path).with_name('RELEASE_TREE_DONE.md')
    out = collections.Counter()
    try: _, secs = parse_md(p.read_text())
    except OSError: return out
    for s in secs:
        if s['kind'] == 'RULES': continue
        out[sec_key(s)] += sum(1 for _ in walk(s['items']))
    return out


def walk(items):
    for it in items:
        yield it
        yield from walk(it['kids'])


# ------------------------------------------------------------------ element layer
FAMILY_RULES = [
    ('Relays, landings and forwarded lanes', r'(^|_)(rly|rlyh|rlyi|rlys|land|landh|landsh|dvland|dvrly|dvrlyh)|fwd_lane|_l4$|landing'),
    ('Die links: PHY, D2D, SerDes, UCIe', r'serdes|ucie|d2d|lk_ep|lkep|_sh_lk|xfin|sstn|six_five|phy_adapt'),
    ('Clock and reset', r'ckgen|rst|reset|pll'),
    ('Collectives and argmax', r'coll|ring_ag|argmax|tkm|tp8_col|xp_aq'),
    ('Attention', r'qkh_|attn|astk|ahub|pv16|pv_|_pv|pvw|ktree'),
    ('Embedding', r'embed|emb'),
    ('Issue control (ECTL)', r'ectl'),
    ('SFU', r'sfu'),
    ('Matrix engine (SM)', r'_sm_|smh|xload|sm_vm|_sm$'),
    ('Index (IDX)', r'idx|hidx'),
    ('Vector memory, HBM controller, banks', r'vms|_vm_|vm_calendar|_hc_|hc_|qbank|wbk|wb_|wbw|dma|qdq|qw_daq|_kv|kvs|kv_|pc_refresh'),
    ('Stream unit (SU)', r'(^|_)su_|_su$|stree|reduce|qcore'),
    ('Engram', r'engram'),
    ('KP4 decoder', r'kp4'),
    ('BF16 lanes', r'(^|_)bf_|bf16|_bf$|_bfp?$|lane4r'),
    ('ROM field, nodes and quantise', r'node_|rom_elem|qxpq|qbank|qnt|rxs'),
    ('Collector, selector, column FIFO', r'(^|_)bk|bksel|bkcol|col_h|cfifo|selt'),
    ('Slices, clusters and stations', r'slice|s81sl|c_b16|xstn|hslice|lep'),
    ('gunit', r'gunit'),
    ('Host, sequencer, services and control', r'_sh_|host|seq|ctrl|ctl|cfg|calendar|_cal|status|fault|svc|admission|boot|programme|pghead|collar|cmd_target|ep_static|_ep_|service|ctlm|rstg|sys_face|stack_fault|vmdel|pq_calendar|cap_tr|_eg$|_ve$|_vn$|_vq$|_vs$|_vsw$|_xr1$'),
]
FAMILY_RX = [(n, re.compile(p)) for n, p in FAMILY_RULES]
STATE_LABEL = dict(done='closed, die-bindable', closed_nb='closed, not die-bindable', flight='in flight', kit='kit prepared, no route job',
                   notstarted='not started', stalled='open, no live job', superseded='superseded')
STATE_CHIP = dict(done='ok', closed_nb='me', flight='run', kit='new', notstarted='wait', stalled='me', superseded='wait')
STATE_ORDER = ['stalled', 'notstarted', 'kit', 'closed_nb', 'flight', 'done']


def family(r):
    if r.get('family'): return r['family']
    n = r['element'].lower()
    for name, rx in FAMILY_RX:
        if rx.search(n): return name
    return 'Other'


def state(r):
    c = r.get('category') or ''
    if c == 'superseded' or r.get('superseded'): return 'superseded'
    if c.startswith('closed'):
        b = r.get('die_bindable') or {}
        return 'done' if b.get('ok') and 'not die-bindable' not in c else 'closed_nb'
    if c == 'kit prepared, no route job' and not r.get('live'): return 'kit'
    if r.get('live') or c in ('first trial in flight', 'failed, re-running', 'revoked, re-running', 'parent open, leaves under way'): return 'flight'
    if c == 'not started (open)': return 'notstarted'
    return 'stalled'


def load_elements(src):
    err = None
    try:
        if re.match(r'https?://', src):
            with urllib.request.urlopen(src, timeout=90) as f: d = json.load(f)
        else:
            d = json.loads(pathlib.Path(src).read_text())
        slim = dict(generated_at=d.get('generated_at'), designs=d.get('designs'), rows=[r for r in d.get('rows', []) if r.get('dies')])
        if not slim['rows']:   # fleet-viz still warming after a restart, or the contracts are missing: keep the last good table
            raise ValueError('no current-die rows (warming=%s)' % d.get('warming'))
        try:
            CACHE.parent.mkdir(parents=True, exist_ok=True); CACHE.write_text(json.dumps(slim))
        except OSError: pass
        return slim, None
    except Exception as e:
        err = 'element table unreachable (%s); using the cached copy' % e
    try:
        return json.loads(CACHE.read_text()), err
    except Exception as e:
        return dict(generated_at=None, designs={}, rows=[]), err + ' -- and no cache (%s)' % e


def die_elements(el, key):
    out = []
    for r in el['rows']:
        for x in r.get('dies') or []:
            if x.get('design') == key:
                out.append((r, x)); break
    return out


def job_of(r, st):
    b = r.get('best') or {}; lt = r.get('latest') or {}
    if st in ('done', 'closed_nb') and b.get('job'): return b['job']
    if st == 'flight':
        m = re.search(r'([A-Za-z0-9_]+-[A-Za-z0-9_]+-[0-9a-f]{7,9})', r.get('flow_detail') or '')
        if m: return m.group(1)
    return lt.get('job') or b.get('job') or ''


def elem_counts(rows):
    c = collections.Counter(state(r) for r, _ in rows)
    tot = sum(v for k, v in c.items() if k != 'superseded')
    return c, tot


# ------------------------------------------------------------------ HTML
E = html.escape


def inline(s):
    s = E(s)
    s = re.sub(r'~~(.+?)~~', r'<s>\1</s>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'→ ([A-Z][A-Z0-9]*(?:\.[A-Z0-9]+)+)', r'→ <a href="#t-\1">\1</a>', s)
    return s


def chip(status, text=None):
    return '<span class="chip %s">%s</span>' % (CHIP.get(status, 'wait'), E(text or status))


def li(it, gate=False):
    done = it['status'] in ('DONE', 'PASS') and (it['checked'] or it['status'] == 'PASS')
    task = '<s>%s</s>' % inline(it['task']) if it['checked'] else ('<b>%s</b>' % inline(it['task']) if (gate or it['kids']) else inline(it['task']))
    parts = ['<li id="t-%s"%s><div class="node">' % (E(it['id']), ' class="gate"' if gate else ''),
             '<span class="tid">%s</span>' % E(it['id']), task, chip(it['status'])]
    if it['owner']: parts.append('<span class="own">%s</span>' % E(it['owner']))
    if it['note']: parts.append('<span class="why">%s</span>' % inline(it['note']))
    parts.append('</div>')
    if it['kids']: parts.append('<ul>' + ''.join(li(k) for k in it['kids']) + '</ul>')
    parts.append('</li>')
    return ''.join(parts)


def gate_of(sec, g):
    for it in sec['items']:
        if it['id'].split('.')[-1] == g and it['id'].count('.') == 1: return it
    return None


def elements_html(rows, design_sum, rev_md):
    c, tot = elem_counts(rows)
    fams = collections.defaultdict(list)
    for r, x in rows:
        st = state(r)
        if st == 'superseded': continue
        fams[family(r)].append((r, x, st))
    out = []
    rev_tab = (design_sum or {}).get('revision', '')
    warn = ''
    if rev_md and rev_tab and not rev_tab.lower().startswith(rev_md.lower()) and rev_md.lower() not in rev_tab.lower().split(' (')[0]:
        warn = '<p class="warn">The element table reads <b>%s</b>, but this die section names rev <b>%s</b>. Point results/fleet_viz/die_sources.json at the current revision.</p>' % (E(rev_tab), E(rev_md))
    chk = ''
    if design_sum:
        closed_tab = design_sum.get('closed'); tot_tab = design_sum.get('total')
        mine = c['done'] + c['closed_nb']
        chk = '<span class="mono muted">element table summary: closed %s / %s %s</span>' % (closed_tab, tot_tab, '✓ matches' if (closed_tab, tot_tab) == (mine, tot) else '≠ this page %d / %d' % (mine, tot))
    out.append('<details class="elems"><summary><b>Elements (generated, never hand-edited)</b> <span class="cnt">closed %d/%d</span>'
               ' <span class="mono muted">%s</span></summary>' % (c['done'], tot, E(' · '.join('%s %d' % (STATE_LABEL[k], c[k]) for k in STATE_ORDER[:-1] if c[k]) + (' · superseded hidden %d' % c['superseded'] if c['superseded'] else ''))))
    out.append('<div class="einner">%s<p class="mono muted" style="margin:0 0 8px">source: %s %s</p>' % (warn, E(rev_tab or '?'), chk))
    for fam in sorted(fams, key=lambda f: (-sum(1 for *_, s in fams[f] if s != 'done'), f)):
        L = fams[fam]; nd = sum(1 for *_, s in L if s == 'done')
        out.append('<details class="fam"><summary>%s <span class="cnt">%d/%d closed</span>%s</summary><ul class="el">' % (
            E(fam), nd, len(L), '' if nd < len(L) else ' <span class="chip ok">ALL CLOSED</span>'))
        for r, x, st in sorted(L, key=lambda t: (STATE_ORDER.index(t[2]), t[0]['element'])):
            nm = E(r['element']); nm = '<s>%s</s>' % nm if st == 'done' else '<b>%s</b>' % nm
            role = x.get('role') or ''
            if x.get('parents'): role += ' of ' + ', '.join(x['parents'][:3])
            b = r.get('best') or {}
            tim = 'TT %+.1f / FF %+.1f' % (b['tt'], b['ff']) if isinstance(b.get('tt'), (int, float)) and isinstance(b.get('ff'), (int, float)) else ''
            why = ''
            if st == 'closed_nb': why = (r.get('die_bindable') or {}).get('why') or ''
            elif st not in ('done',): why = r.get('category') or ''
            owner = r.get('owner_stream') or r.get('owner') or ''
            out.append('<li><span class="chip %s">%s</span> %s <span class="mono muted">%s</span>%s%s%s%s</li>' % (
                STATE_CHIP[st], E(STATE_LABEL[st]), nm, E(role),
                ' <span class="mono">%s</span>' % E(job_of(r, st)) if job_of(r, st) else '',
                ' <span class="mono muted">%s</span>' % E(tim) if tim else '',
                ' <span class="own">%s</span>' % E(owner) if owner else '',
                ' <span class="why">%s</span>' % E(why) if why else ''))
        out.append('</ul></details>')
    out.append('</div></details>')
    return ''.join(out), c, tot


def plan_cnt(rows):
    """'G0C clean a/b · SIGNED types c/b · cores d/e' summed over the die's plans"""
    if not rows or any(r.get('clean') is None for r in rows): return None
    t = sum(r['types'] or 0 for r in rows); cl = sum(int(r['clean'] or 0) for r in rows)
    st = sum(r['signed_types'] for r in rows); co = sum(r['cores'] for r in rows); sc = sum(r['signed_cores'] for r in rows)
    return dict(types=t, clean=cl, signed_types=st, cores=co, signed_cores=sc)


def plan_html(rows, cache):
    if not rows:
        return '<p class="warn" style="margin:6px 16px">plan layer: no data for this die yet</p>'
    out = ['<details class="elems" open><summary><b>Current-plan elements (generated from origin/main die plans)</b></summary><div class="einner"><ul class="el">']
    for r in rows:
        if r.get('clean') is None:
            out.append('<li><span class="chip me">NOT RUN</span> <b>%s</b> <span class="why">%s</span></li>' % (E(r['plan']), E(r.get('error') or 'G0C did not run')))
            continue
        bad = ', '.join('%s (%s)' % (k, ', '.join(v)) for k, v in sorted(r['bad'].items()))
        out.append('<li><span class="chip %s">G0C %s</span> <b>%s</b> <span class="mono">G0C-clean types %s/%s · SIGNED types %d/%s · SIGNED hard cores %d/%d</span>%s%s%s</li>' % (
            'ok' if r['verdict'] == 'PASS' else 'me', E(str(r['verdict'])), E(r['plan']), r['clean'], r['types'], r['signed_types'], r['types'],
            r['signed_cores'], r['cores'],
            ' <span class="why">not clean: %s%s</span>' % (E(bad), ('; die-level ' + E(json.dumps(r['die_level']))) if r['die_level'] else '') if bad or r['die_level'] else '',
            ' <span class="mono muted">SIGNED: %s</span>' % E(', '.join(r['signed_list'])) if r['signed_list'] else '',
            ' <span class="warn">stale since %s</span>' % E(datetime.datetime.fromtimestamp(r['stale']).strftime('%m-%d %H:%M')) if r.get('stale') else ''))
    gen = (cache or {}).get('generated')
    out.append('</ul><p class="mono muted" style="margin:0 0 8px">origin/main %s · refreshed %s · SIGNED = signoff.py record verdict SIGNED (TT setup / FF hold) found on origin/main or fleet scratch (%s)</p></div></details>' % (
        E(str((cache or {}).get('origin_main'))), datetime.datetime.fromtimestamp(gen).strftime('%Y-%m-%d %H:%M') if gen else '?', E(', '.join((cache or {}).get('scanned') or []))))
    return ''.join(out)


CSS = r'''
:root{--bg:#f6f7fa;--panel:#fff;--fg:#1b1f2a;--muted:#5d6577;--line:#d9dde6;--accent:#2f4fb5;--accent-soft:#e6ebfa;
--ok:#1f7a4d;--ok-bg:#e3f3ea;--run:#1f5fa8;--run-bg:#e2edf9;--wait:#8a6a12;--wait-bg:#f7efd6;--me:#a33d2a;--me-bg:#f8e4df;--new:#6b3fa0;--new-bg:#efe6f8;
--display:"Archivo","Helvetica Neue",Arial,sans-serif;--body:"Source Sans 3","Segoe UI",system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#12151d;--panel:#1a1e29;--fg:#e4e7ef;--muted:#9aa2b5;--line:#2d3342;--accent:#8ea6ff;--accent-soft:#232c48;
--ok:#6fd3a0;--ok-bg:#183428;--run:#8cbcff;--run-bg:#1a2a44;--wait:#e6c46a;--wait-bg:#3a3018;--me:#ff9a85;--me-bg:#3d211b;--new:#c9a6ff;--new-bg:#2d2240;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#12151d;--panel:#1a1e29;--fg:#e4e7ef;--muted:#9aa2b5;--line:#2d3342;--accent:#8ea6ff;--accent-soft:#232c48;
--ok:#6fd3a0;--ok-bg:#183428;--run:#8cbcff;--run-bg:#1a2a44;--wait:#e6c46a;--wait-bg:#3a3018;--me:#ff9a85;--me-bg:#3d211b;--new:#c9a6ff;--new-bg:#2d2240;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:16px/1.55 var(--body);margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:28px 16px 64px;display:flex;flex-direction:column;gap:26px}
h1,h2,h3{font-family:var(--display);text-wrap:balance;margin:0} h1{font-size:2rem;font-weight:800} h2{font-size:1.3rem}
.eyebrow{font:600 .75rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.src{font:600 .82rem var(--mono);color:var(--fg);background:var(--accent-soft);border-radius:4px;padding:6px 10px;display:inline-block;margin-top:8px}
.lede{color:var(--muted);max-width:72ch;margin:6px 0 0} section{display:flex;flex-direction:column;gap:12px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:6px}
.legend{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:.9rem;color:var(--muted)}
.chip{display:inline-block;font:600 .7rem/1 var(--mono);letter-spacing:.04em;padding:4px 7px;border-radius:3px;white-space:nowrap;vertical-align:1px}
.ok{background:var(--ok-bg);color:var(--ok)}.run{background:var(--run-bg);color:var(--run)}.wait{background:var(--wait-bg);color:var(--wait)}.me{background:var(--me-bg);color:var(--me)}.new{background:var(--new-bg);color:var(--new)}
.tablebox{overflow-x:auto} table{border-collapse:collapse;width:100%;font-size:.92rem;min-width:820px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font:600 .72rem var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
td.die{font-family:var(--display);font-weight:700;white-space:nowrap} td small{display:block;color:var(--muted);font-size:.8rem;margin-top:3px}
details.die{background:var(--panel);border:1px solid var(--line);border-radius:6px}
details>summary{cursor:pointer;list-style:none} details>summary::-webkit-details-marker{display:none}
details.die>summary{padding:14px 16px;display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline}
details.die>summary::before,details.elems>summary::before,details.fam>summary::before{content:"▸";color:var(--accent);font-family:var(--mono)}
details.die[open]>summary::before,details.elems[open]>summary::before,details.fam[open]>summary::before{content:"▾"}
details.die>summary h3{font-size:1.1rem} details.die>summary .eta{margin-left:auto;font:600 .82rem var(--mono);color:var(--muted)}
summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tree{padding:0 16px 16px;overflow-x:auto}
.tree ul{list-style:none;margin:0;padding-left:22px;border-left:1px solid var(--line)} .tree>ul{border-left:none;padding-left:0}
.tree li{position:relative;padding:5px 0 5px 12px;min-width:0}
.tree ul ul li::before{content:"";position:absolute;left:-22px;top:17px;width:28px;border-top:1px solid var(--line)}
.node{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline} .node b{font-weight:600}
.why{color:var(--muted);font-size:.9rem} .node .why{flex-basis:100%}
.tid{font:600 .7rem var(--mono);color:var(--muted)} .own{font:.74rem var(--mono);color:var(--accent)}
.gate>.node>b{font-family:var(--display);font-weight:700;color:var(--accent)}
s{color:var(--muted)} .muted{color:var(--muted)} .mono{font-family:var(--mono);font-size:.82em} code{font-family:var(--mono);font-size:.86em}
.cnt{font:600 .78rem var(--mono);color:var(--ok)}
details.elems{margin:6px 16px 16px;border-top:1px dashed var(--line);padding-top:10px} details.elems>summary{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}
.einner{padding:8px 0 0 14px} details.fam{border-left:2px solid var(--line);margin:4px 0;padding:2px 0 2px 10px} details.fam>summary{font-weight:600}
ul.el{list-style:none;margin:4px 0 6px;padding-left:12px;font-size:.9rem} ul.el li{padding:3px 0;border-bottom:1px dotted var(--line)}
.warn{background:var(--me-bg);color:var(--me);padding:6px 10px;border-radius:4px;margin:0 0 8px;font-size:.9rem}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.cols .panel{padding:14px 16px;display:flex;flex-direction:column;gap:8px;min-width:0} .cols h3{font-size:1rem}
.cols ul{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px}
details.rules{padding:10px 16px} details.rules p{margin:6px 0;font-size:.92rem}
footer{color:var(--muted);font-size:.85rem}
'''


UNOWNED_JSON = BASE / 'UNOWNED.json'


def _age(m):
    if m is None: return 'never'
    return '%d min' % m if m < 120 else '%.1f h' % (m / 60.0)


def owner_banner():
    """AUTO-OWNER banner (owner 10-18): ACTIVE / STALE / UNOWNED open elements from tools/element_owner_watch.py"""
    try:
        d = json.loads(UNOWNED_JSON.read_text())
    except Exception as e:
        return '<section><p class="warn">Element owner watch: UNOWNED.json unreadable (%s)</p></section>' % E(str(e))
    c = d.get('counts') or {}
    gen = d.get('generated', '?'); old = (datetime.datetime.now().timestamp() - (d.get('generated_t') or 0)) > 5400
    rows = [x for x in d.get('elements', []) if x.get('state') in ('UNOWNED', 'STALE')]
    items = ''.join('<li><span class="chip %s">%s</span> <b>%s</b> <span class="mono muted">%s · %s</span> <span class="own">%s</span>%s%s</li>' % (
        'me' if x['state'] == 'UNOWNED' else 'wait', x['state'], E(x['element']), E(_age(x.get('age_min'))), E(', '.join(x.get('dies') or [])),
        E(x.get('owner') or 'no owner'), ' <span class="why">auto: %s</span>' % E(x['auto']) if x.get('auto') else '',
        ' <span class="why">needs a family agent</span>' if x.get('needs_agent') else '') for x in rows)
    acts = d.get('actions') or []
    return ('<section><div class="panel" style="padding:12px 16px"><h2 style="font-size:1.1rem">Element owners: '
            '<span class="chip ok">ACTIVE %s</span> / <span class="chip wait">STALE %s</span> / <span class="chip me">UNOWNED %s</span></h2>'
            '<p class="mono muted" style="margin:4px 0">open %s · needs a family agent %s · automatic actions this run %d · watch %s%s · '
            'source UNOWNED.json (tools/element_owner_watch.py, element-owner-watch.timer every 30 min)</p>%s</div></section>' % (
                c.get('ACTIVE', '?'), c.get('STALE', '?'), c.get('UNOWNED', '?'), c.get('open', '?'), c.get('needs_agent', '?'), len(acts), E(gen),
                ' <b>(stale: the watch has not run for > 90 min)</b>' if old else '',
                '<details><summary class="mono">UNOWNED / STALE elements (%d)</summary><ul class="el">%s</ul></details>' % (len(rows), items) if rows else ''))


TASKS_JSON = BASE / 'TASKS_STALE.json'


def task_banner():
    """TASK-WATCH banner (owner 10-19): liveness of every open release-tree task from tools/release_task_watch.py"""
    try:
        d = json.loads(TASKS_JSON.read_text())
    except Exception as e:
        return '<section><p class="warn">Release task watch: TASKS_STALE.json unreadable (%s)</p></section>' % E(str(e))
    c = d.get('counts') or {}
    old = (datetime.datetime.now().timestamp() - (d.get('generated_t') or 0)) > 5400
    rows = [x for x in d.get('tasks', []) if x.get('cls') in ('DEAD', 'STALE')]
    rows.sort(key=lambda x: (x['cls'] != 'DEAD', x['id']))
    items = ''.join('<li><span class="chip %s">%s</span> <b>%s</b> <span class="mono muted">tree %s · %s</span> <span class="own">%s</span> <span class="why">%s</span></li>' % (
        'me' if x['cls'] == 'DEAD' else 'wait', x['cls'], E(x['id']), E(x.get('status_text') or ''),
        E(_age(x.get('last_evidence_min'))), E(x.get('owner') or 'no owner'), E((x.get('why') or '')[:220])) for x in rows)
    errs = d.get('probe_errors') or {}
    return ('<section><div class="panel" style="padding:12px 16px"><h2 style="font-size:1.1rem">Release tasks: '
            '<span class="chip ok">LIVE %s</span> / <span class="chip wait">STALE %s</span> / <span class="chip me">DEAD %s</span></h2>'
            '<p class="mono muted" style="margin:4px 0">open %s · waits on a live task %s · blocked on the owner %s · needs a fresh agent %s · watch %s%s%s · '
            'liveness from processes, run dirs, closure jobs, lanes and HANDOFF, never from the status text '
            '(TASKS_STALE.json, tools/release_task_watch.py, element-owner-watch.timer every 30 min)</p>%s</div></section>' % (
                c.get('LIVE', '?'), c.get('STALE', '?'), c.get('DEAD', '?'), c.get('open', '?'), c.get('WAITS-OK', '?'),
                c.get('BLOCKED-ON-OWNER', '?'), c.get('needs_agent', '?'), E(d.get('generated', '?')),
                ' <b>(stale: the watch has not run for > 90 min)</b>' if old else '',
                ' <b>(probe failed: %s)</b>' % E(', '.join(sorted(errs))) if errs else '',
                '<details%s><summary class="mono">DEAD / STALE tasks (%d)</summary><ul class="el">%s</ul></details>' % (
                    ' open' if any(x['cls'] == 'DEAD' for x in rows) else '', len(rows), items) if rows else ''))


def render(md_path, el, el_err, now, plan=None):
    pre, secs = parse_md(md_path.read_text())
    arch = load_done(md_path)
    for s in secs: s['archived'] = arch.get(sec_key(s), 0)
    dies = {s['key']: s for s in secs if s['kind'] == 'DIE'}
    designs = el.get('designs') or {}
    gen_t = el.get('generated_at')
    gen_s = datetime.datetime.fromtimestamp(gen_t).strftime('%Y-%m-%d %H:%M') if gen_t else 'unknown'
    md_t = datetime.datetime.fromtimestamp(md_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
    H = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>OpenTallas Release Tree</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=Source+Sans+3:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap">',
         '<style>%s</style></head><body><div class="wrap">' % CSS]
    H.append('<header><div class="eyebrow">OpenTallas · ASAP7 · 833 ps (1.2 GHz) · shared Claude + Codex hand-off</div><h1>Release dependency tree</h1>'
             '<div class="src">Source: coord/RELEASE_TREE.md (edited %s) · rendered %s · plan layer %s</div>'
             '<p class="lede">Release needs two independent sets of gates: the four die gates for every die, and the token-pass gate for every design. '
             'Each task appears once. Only open work is shown: finished tasks move to RELEASE_TREE_DONE.md (counted in "tasks done"). Each die also shows its current-plan element layer: partition types that are G0C-clean (check.py --completeness on origin/main) and partition types / hard cores with a SIGNED signoff record (refreshed hourly).</p>%s</header>'
             % (md_t, now.strftime('%Y-%m-%d %H:%M PT'), gen_s, '<p class="warn">%s</p>' % E(el_err) if el_err else ''))
    snapshot = next((ln[len("Snapshot: "):].strip() for ln in md_path.read_text().splitlines() if ln.startswith("Snapshot: ")), "")
    if snapshot:
        H.append('<section class="snapshot"><p>%s</p></section>' % E(snapshot))
    H.append(task_banner())
    H.append(owner_banner())
    H.append('<section><div class="legend"><span>%s finished</span><span>%s agent or fleet job working</span><span>%s blocked by a child task / to do</span>'
             '<span>%s started today</span><span>%s waiting on the coordinator or owner</span></div></section>' % (chip('DONE'), chip('RUNNING'), chip('WAITS'), chip('NEW'), chip('COORD')))
    # gate matrix
    rows = []; summ = []
    ecount = {}
    for key in DIE_ORDER:
        s = dies.get(key)
        if not s: continue
        prow = RTP.die_counts(plan, key); pc = plan_cnt(prow); ecount[key] = pc
        cells = []
        for g, _ in GATES:
            it = gate_of(s, g)
            cells.append('<td>%s<small>%s</small></td>' % (chip(it['status']) if it else chip('TODO', 'MISSING'), inline(it['note']) if it else 'no %s line' % g))
        rows.append('<tr><td class="die"><a href="#die-%s">%s</a><small>rev %s</small></td>%s<td class="num">%s<small>%s</small></td><td>%s</td></tr>' % (
            key, E(s['title']), E(s['rev']), ''.join(cells),
            ('%d/%d' % (pc['clean'], pc['types'])) if pc else 'n/a',
            ('G0C-clean types · SIGNED types %d/%d · SIGNED hard cores %d/%d' % (pc['signed_types'], pc['types'], pc['signed_cores'], pc['cores'])) if pc else 'plan layer missing', E(s['est'])))
    H.append('<section><h2>Die gates</h2><div class="panel tablebox"><table><thead><tr><th>Die</th>%s<th>Current plan (G0C clean / SIGNED)</th><th>First die pass (est.)</th></tr></thead><tbody>%s</tbody></table></div></section>'
             % (''.join('<th>%s</th>' % E(t) for _, t in GATES), ''.join(rows)))
    tok = next((s for s in secs if s['kind'] == 'TOKEN'), None)
    if tok:
        trs = []
        allitems = {it['id']: it for it in walk(tok['items'])}
        for did, lab in (('TOK.DS', 'DeepSeek ROM (S81 array)'), ('TOK.QW', 'Qwen ROM'), ('TOK.HDS', 'HBM-DeepSeek'), ('TOK.HQ', 'HBM-Qwen')):
            p = allitems.get(did)
            if not p: continue
            lay = [k for k in p['kids'] if re.search(r'\.(LAYER|VEH|KV)$', k['id'])]
            xd = [k for k in p['kids'] if re.search(r'\.(XDIE|TP8)$', k['id'])]
            f = lambda L: ''.join('<div>%s <small>%s</small></div>' % (chip(k['status']), inline(k['task'])) for k in L) or '<small>none</small>'
            trs.append('<tr><td class="die"><a href="#t-%s">%s</a></td><td>%s</td><td>%s</td><td><small>%s</small></td></tr>' % (did, E(lab), f(lay), f(xd), inline(p['note'])))
        H.append('<section><h2>Token-pass gate</h2><p class="lede" style="margin:0">Separate from the die gates: it runs on each design\'s current RTL now, and only its final evidence run (TOK.FREEZE) waits for RTL freeze.</p>'
                 '<div class="panel tablebox"><table style="min-width:640px"><thead><tr><th>Design</th><th>Single-die layer runs</th><th>Inter-die co-sims</th><th>Graded today</th></tr></thead><tbody>%s</tbody></table></div></section>' % ''.join(trs))
    H.append('<section><h2>Dependency trees</h2>')
    for key in DIE_ORDER:
        s = dies.get(key)
        if not s: continue
        its = list(walk(s['items'])); nopen = sum(1 for i in its if not i['checked'])
        gates = [gate_of(s, g) for g, _ in GATES]
        first = next((g for g in gates if g and g['status'] not in ('PASS', 'DONE')), None)
        head = chip('DONE', 'DIE GATES PASS') if not first else chip(first['status'], '%s %s' % (first['id'].split('.')[-1], first['status']))
        prow = RTP.die_counts(plan, key); pc = plan_cnt(prow); ehtml = plan_html(prow, plan)
        ecnt = ('G0C-clean types %d/%d · SIGNED types %d/%d · SIGNED hard cores %d/%d' % (pc['clean'], pc['types'], pc['signed_types'], pc['types'], pc['signed_cores'], pc['cores'])) if pc else 'plan layer missing'
        H.append('<details class="die" open id="die-%s"><summary><h3>%s</h3><span class="mono muted">rev %s</span>%s<span class="cnt">tasks done %d/%d · %s</span><span class="eta">est. %s</span></summary>'
                 '<div class="tree"><ul>%s</ul></div>%s</details>' % (key, E(s['title']), E(s['rev']), head, s['archived'] + len(its) - nopen, s['archived'] + len(its), E(ecnt), E(s['est']),
                                                                     ''.join(li(i, gate=re.fullmatch(r'[A-Z0-9]+\.(BIND|GRT|STA|CLK)', i['id']) is not None) for i in s['items']), ehtml))
    for s in secs:
        if s['kind'] in ('TOKEN', 'INFRA') or s['kind'] not in ('DIE', 'WAITS', 'RULES'):
            its = list(walk(s['items'])); nopen = sum(1 for i in its if not i['checked'])
            H.append('<details class="die"%s id="sec-%s"><summary><h3>%s</h3><span class="cnt">tasks done %d/%d</span><span class="eta">%s</span></summary><div class="tree"><ul>%s</ul></div></details>' % (
                ' open' if s['kind'] == 'TOKEN' else '', E(s['kind'].lower()), E(s['title']), s.get('archived', 0) + len(its) - nopen, s.get('archived', 0) + len(its), E(' · '.join(s.get('extra') or [])),
                ''.join(li(i, gate=(s['kind'] == 'TOKEN' and i['id'] == 'TOK.REC')) for i in s['items'])))
    H.append('</section>')
    w = next((s for s in secs if s['kind'] == 'WAITS'), None)
    if w:
        H.append('<section><h2>Who is waiting on whom</h2><div class="cols">%s</div></section>' % ''.join(
            '<div class="panel"><h3>%s</h3><ul>%s</ul></div>' % (E(sb['title']), ''.join('<li>%s</li>' % inline(x) for x in sb['lines'])) for sb in w['subs']))
    r = next((s for s in secs if s['kind'] == 'RULES'), None)
    if r:
        H.append('<section><details class="panel rules"><summary><b>Edit rules (Claude and Codex)</b></summary>%s</details></section>' % ''.join('<p>%s</p>' % inline(t) for t in r['text']))
    H.append('<footer>Generated by coord/tools/release_tree_render.py from RELEASE_TREE.md and tools/release_tree_plan.py '
             '(G0C = tools/die_plan/check.py --completeness on the origin/main die plans; SIGNED = signoff.py records). Edit the .md, never this page.</footer></div></body></html>')
    return '\n'.join(H), secs, dies, ecount


def summary_text(secs, dies, ecount, el, now):
    L = ['RELEASE TREE %s  (source RELEASE_TREE.md · page http://localhost:8765/release)' % now.strftime('%m-%d %H:%M')]
    for key in DIE_ORDER:
        s = dies.get(key)
        if not s: continue
        g = ' | '.join('%s %s' % (gn, (gate_of(s, gn) or {}).get('status', '?')) for gn, _ in GATES)
        its = list(walk(s['items'])); nd = s.get('archived', 0) + sum(1 for i in its if i['checked'])
        pc = ecount.get(key)
        L.append('%-13s rev %-6s %s ; tasks %d/%d done ; %s' % (
            key, s['rev'], g, nd, s.get('archived', 0) + len(its),
            ('G0C-clean types %d/%d, SIGNED types %d/%d, SIGNED hard cores %d/%d' % (pc['clean'], pc['types'], pc['signed_types'], pc['types'], pc['signed_cores'], pc['cores'])) if pc else 'plan layer missing'))
    tok = next((s for s in secs if s['kind'] == 'TOKEN'), None)
    if tok:
        its = list(walk(tok['items']))
        L.append('TOKEN %s ; tasks %d/%d done' % (' | '.join('%s %s' % (i['id'][4:], i['status']) for i in tok['items'][0]['kids'] if i['id'] in ('TOK.DS', 'TOK.QW', 'TOK.HDS', 'TOK.HQ')) if tok['items'] else '',
                                                  tok.get('archived', 0) + sum(1 for i in its if i['checked']), tok.get('archived', 0) + len(its)))
    allits = [i for s in secs for i in walk(s['items'])]
    co = [i['id'] for i in allits if i['status'] == 'COORD' and not i['checked']]
    ow = [i['id'] for i in allits if i['status'] == 'OWNER' and not i['checked']]
    try:
        u = json.loads(UNOWNED_JSON.read_text()); uc = u.get('counts') or {}
        L.append('element owners (%s): ACTIVE %s / STALE %s / UNOWNED %s; needs a family agent %s' % (
            u.get('generated'), uc.get('ACTIVE'), uc.get('STALE'), uc.get('UNOWNED'), uc.get('needs_agent')))
    except Exception: pass
    try:
        tw = json.loads(TASKS_JSON.read_text()); tc = tw.get('counts') or {}
        bad = [x for x in tw.get('tasks', []) if x.get('cls') in ('DEAD', 'STALE')]
        L.append('tasks (%s): LIVE %s / STALE %s / DEAD %s (waits-ok %s, owner %s); DEAD: %s' % (
            tw.get('generated'), tc.get('LIVE'), tc.get('STALE'), tc.get('DEAD'), tc.get('WAITS-OK'), tc.get('BLOCKED-ON-OWNER'),
            ', '.join(x['id'] for x in bad if x['cls'] == 'DEAD') or 'none'))
    except Exception: pass
    L.append('waiting on coordinator: %s' % (', '.join(co) or 'none'))
    L.append('waiting on owner: %s' % (', '.join(ow) or 'none'))
    return '\n'.join(L) + '\n'


def atomic_write(p, text):
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix='.' + p.name + '.')
    with os.fdopen(fd, 'w') as f: f.write(text)
    os.chmod(tmp, 0o644); os.replace(tmp, p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--md', default=str(BASE / 'RELEASE_TREE.md'))
    ap.add_argument('--out', default=str(BASE / 'RELEASE_TREE.html'))
    ap.add_argument('--summary-out', default=str(BASE / 'RELEASE_TREE_SUMMARY.txt'))
    ap.add_argument('--elements', default='http://localhost:8765/api/elements')
    ap.add_argument('--summary', action='store_true', help='print the text summary')
    ap.add_argument('--refresh-plan', action='store_true', help='refresh the plan layer now (default: when older than 50 min)')
    a = ap.parse_args(argv)
    now = datetime.datetime.now()
    el = dict(generated_at=None, designs={}, rows=[])   # the 10-21 element table (fleet-viz /api/elements) is obsolete
    try:
        plan, err = RTP.load(a.refresh_plan)
    except Exception as e:
        plan, err = None, 'plan layer failed: %s' % e
    if plan: el['generated_at'] = plan.get('generated')
    page, secs, dies, ecount = render(pathlib.Path(a.md), el, err, now, plan)
    atomic_write(pathlib.Path(a.out), page)
    st = summary_text(secs, dies, ecount, el, now)
    atomic_write(pathlib.Path(a.summary_out), st)
    if a.summary: sys.stdout.write(st)
    if err: sys.stderr.write(err + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
