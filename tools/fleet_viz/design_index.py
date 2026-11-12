#!/usr/bin/env python3
"""design_index: the ONE node index of the die -> type -> core design hierarchy that every explorer page reads
(EXPLORER-2, owner 2026-11-11: refactor every explorer page onto the current hierarchy).

    python3 -I design_index.py [--out <state>/design_index.json] [--die s81,...]

Node ids (valid store keys: [A-Za-z0-9_.-]):
  die   "<die>"                      e.g. "s81"
  type  "<die>.t.<partition type>"   e.g. "s81.t.slice_station__t48"
  core  "<die>.c.<module>"           e.g. "s81.c.ot_s81sl_vq"   (one node per hard-core module, shared by every type
                                                                 instance that places it)
Every node carries:
  level     die | type | core
  status    {state: signed | failed | building | queued | waiting | not built, label (the plan_now category), cls, stage,
             reason, attempt}
  layout    {db, host, stage, source, record}  newest routed DB: the signed view's 6_final.odb (signed store record +
            archive copy) or the newest kit attempt (kit dir; the exact DB stage is resolved by design_export.py on the
            build host), plus {store: manifest id, bytes, verify} once the pack is published
  plan      placement read from the die plan of record:
              die : outline, period, reach, partitions [name, type id, x, y, w, h, orient], port windows (seams) per
                    abutting partition pair, clock spine root + topology, PG domains, landing cohorts
              type: outline, instances in the die, buses (face windows), ft_slots, internal_stations, clock taps,
                    hard_cores [inst, core id, module, x, y, w, h, orient]
              core: outline, used_by [type ids]
Sources (read-only): <state>/plan_now.json (die list, plan path, plan_now categories = signed store + kit wave),
the die plan files ($FLEET_VIZ_REPO), the signed store (~/coord/signed-store records: rows die/key/kind, archived
6_final.odb), ~/coord/lanes/VIS-SWEEP-1111.tsv visual verdicts (optional copy), the layout store manifests.
"""
import argparse, collections, gzip, json, os, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
REPO = pathlib.Path(os.environ.get('FLEET_VIZ_REPO', '/srv/opentallas-scratch/claude/fleet-viz-repo'))
SIGNED = pathlib.Path(os.environ.get('OT_SIGNED_STORE', os.path.expanduser('~/coord/signed-store')))
VIS = pathlib.Path(os.environ.get('DESIGN_INDEX_VIS', STATE / 'VIS-SWEEP.tsv'))
STORE = pathlib.Path(os.environ.get('LV_STORE', HERE / 'layout_store'))
SCHEMA = 'opentallas.fleet_viz.design_index.v1'
ORIENT_SWAP = {'R90', 'R270', 'MXR90', 'MYR90'}
STATE_OF = {'signed off': 'signed', 'signed off (legacy view)': 'signed',
            'routed, not signed (timing)': 'failed', 'route failure': 'failed', 'flow failure': 'failed',
            'plan / geometry failure': 'failed', 'RTL / kit failure': 'failed',
            'routing / sign-off running': 'building', 'running (pre-route)': 'building', 'queued': 'queued',
            'waiting (dependency / plan delta)': 'waiting', 'cancelled': 'not built', 'not started': 'not built'}
STATES = ['signed', 'failed', 'building', 'queued', 'waiting', 'not built']


def log(*a):
    print(time.strftime('%H:%M:%S'), '[design_index]', *a, file=sys.stderr, flush=True)


def tid(die, t): return '%s.t.%s' % (die, t)
def cid(die, m): return '%s.c.%s' % (die, m)


def r2(v): return round(float(v), 3)


def load_plan(rel):
    p = REPO / rel
    b = p.read_bytes()
    return json.loads(gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b)


def place_child(ox, oy, orient, W, H, x, y, w, h):
    """child rect in type-local coordinates -> die coordinates for a partition at (ox, oy) with orient (plan_now.py)"""
    if orient == 'MY': x = W - x - w
    elif orient == 'MX': y = H - y - h
    elif orient == 'R180': x, y = W - x - w, H - y - h
    return ox + x, oy + y


MEM_MACRO_LEF = 'physical/asap7_memory_macros'
MEM_RE = re.compile(r'^ot_(sram|rom|rf)_')


def is_mem_macro(c):
    """generated SRAM / ROM macro (rom_gen / sram views): not a signed-off design (release_tree_plan.is_mem_macro)"""
    return str(c.get('lef') or '').startswith(MEM_MACRO_LEF) or bool(MEM_RE.match(c.get('module') or ''))


def signed_rows():
    """(die, key) -> newest signed-store row: record id, top, archived 6_final.odb (path on AGIdock, bytes), origin"""
    out = {}
    root = SIGNED / 'records'
    if not root.is_dir(): return out
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if not fn.endswith('.json.gz'): continue
            try:
                with gzip.open(os.path.join(dp, fn), 'rt') as fh: e = json.load(fh)
            except Exception: continue
            odb = next((f for f in e.get('files') or [] if f[0].endswith('6_final.odb')), None)
            for r in e.get('rows') or []:
                k = (r.get('die'), r.get('key'))
                rec = dict(record=e['id'], top=e.get('top'), name=e.get('name'), generated=e.get('generated'),
                           origin=e.get('origin'), kind=r.get('kind'), verdict=e.get('verdict'),
                           archive_odb=('%s/%s' % (e['archive'].rstrip('/'), odb[0])) if odb else None,
                           odb_bytes=odb[1] if odb else None,
                           host_odb=('%s:/%s' % (e['archive'].rstrip('/').rsplit('/', 1)[1], odb[0])) if odb else None)
                if k not in out or (rec['generated'] or '') > (out[k]['generated'] or ''): out[k] = rec
    return out


def vis_verdicts():
    out = {}
    try:
        for ln in VIS.read_text().splitlines()[1:]:
            f = ln.split('\t')
            if len(f) >= 7: out[(f[0], f[1])] = dict(attempt=f[2], stage=f[3], verdict=f[4], cls=f[5], cause=f[6], render=f[7] if len(f) > 7 else '')
    except OSError:
        pass
    return out


def store_entry(nid):
    try:
        i = json.loads((STORE / 'elements' / nid / 'index.json').read_text())
        m = json.loads((STORE / 'elements' / nid / (i['latest'] + '.json')).read_text())
        return dict(id=m['id'], job=i['latest'], bytes=m.get('bytes'), verify=(m.get('verify') or {}).get('verdict'),
                    shapes=(m.get('verify') or {}).get('shapes'), stage=(m.get('design') or {}).get('stage'), made=m.get('made'))
    except Exception:
        return None


def status_of(e):
    cat = (e or {}).get('category') or 'not started'
    kw = (e or {}).get('kw') or {}
    st = dict(state=STATE_OF.get(cat, 'not built'), label=cat)
    if st['state'] == 'failed':
        st.update(cls=kw.get('cls') or '', stage=kw.get('stage') or '', reason=(kw.get('reason') or '')[:400], attempt=kw.get('attempt'))
    elif st['state'] in ('building', 'queued'):
        st.update(stage=kw.get('stage') or '', attempt=kw.get('attempt'))
    m = (e or {}).get('m') or {}
    for k in ('tt_wns', 'ff_wns', 'drc', 'drt_drc', 'grt_overflow', 'lec', 'cells', 'verdict'):
        if m.get(k) is not None: st.setdefault('metrics', {})[k] = m[k]
    return st


def layout_of(e, srow):
    """the newest routed DB pointer of a node"""
    sg = (e or {}).get('signed') or {}
    if sg:
        ent = sg.get('entry') or ''
        m = re.search(r'\bdb (\S+)', ent)
        host = ent.split(':', 1)[0] if ':' in ent.split(' ')[0] else None
        out = dict(stage='6_final', source='signed view', db=('%s:%s' % (host, m.group(1))) if m and host else None,
                   legacy=bool(sg.get('legacy')))
        if srow:
            out.update(record=srow['record'], archive_odb=srow['archive_odb'], odb_bytes=srow['odb_bytes'], top=srow['top'])
            if not out['db'] and srow.get('host_odb'): out['db'] = srow['host_odb']
        return out
    kw = (e or {}).get('kw') or {}
    if kw.get('kit') and kw.get('stage') in ('route', 'signoff', 'grt', 'resume_nochange', 'resume_fp', 'final'):
        mm = (e or {}).get('m') or {}
        return dict(stage={'final': '6_final'}.get(mm.get('flow_stage'), mm.get('flow_stage') or kw.get('stage')),
                    source='kit attempt %s' % (kw.get('attempt') or '?'), kit=kw['kit'], db=None)
    return None


def build(dies_filter=None):
    pn = json.loads((STATE / 'plan_now.json').read_text())
    els = {(e['die'], e['element']): e for e in pn['elements']}
    sr = signed_rows(); vis = vis_verdicts()
    nodes = {}
    for d in pn['dies']:
        die = d['die']
        if dies_filter and die not in dies_filter: continue
        try:
            P = load_plan(d['plan_path'])
        except Exception as ex:
            log('%s: plan %s not readable: %s' % (die, d['plan_path'], ex)); continue
        pt = P.get('partition_types') or {}
        di = P.get('die') or {}
        parts, inst_of = [], collections.Counter()
        for p in P.get('partitions') or []:
            t = pt.get(p['type']) or {}
            W, H = (t.get('outline_um') or [0, 0])[:2]
            o = p.get('orient') or 'R0'
            w, h = (H, W) if o in ORIENT_SWAP else (W, H)
            ox, oy = p.get('origin_um') or [0, 0]
            parts.append([p['name'], tid(die, p['type']), r2(ox), r2(oy), r2(w), r2(h), o])
            inst_of[p['type']] += 1
        pidx = {p[0]: p for p in parts}
        # seams: per abutting partition pair, the port windows that cross it (face + window along that face)
        seams = collections.defaultdict(lambda: dict(bits=0, n=0, win=[]))
        for prt in P.get('ports') or []:
            s, t = (prt.get('src') or {}).get('part'), (prt.get('dst') or {}).get('part')
            if s not in pidx or t not in pidx or s == t: continue
            k = (s, t) if s < t else (t, s)
            z = seams[k]; z['bits'] += int(prt.get('width') or 0); z['n'] += 1
            if prt.get('window_um') and len(z['win']) < 8: z['win'].append([prt.get('face'), r2(prt['window_um'][0]), r2(prt['window_um'][1]), prt['src']['part']])
        clk = P.get('clock') or {}
        pg = (di.get('pg') or {})
        die_node = dict(id=die, level='die', die=die, label=d.get('label') or die, target=d.get('target'),
                        plan=dict(path=d['plan_path'], commit=d.get('plan_commit'), date=d.get('plan_date'), subject=d.get('plan_subject'),
                                  outline=[r2(v) for v in (di.get('outline_um') or [0, 0])[:2]], period_ps=di.get('period_ps'), reach_um=di.get('reach_um'),
                                  partitions=parts, seams=[[a, b, z['bits'], z['n'], z['win']] for (a, b), z in sorted(seams.items())],
                                  clock=dict(root=(clk.get('spine') or {}).get('root_um'), topology=(clk.get('spine') or {}).get('topology'),
                                             layers=(clk.get('spine') or {}).get('layers'), insertion_ps=clk.get('insertion_ps')),
                                  pg_domains=[dict(name=x.get('name'), rect=x.get('rect_um'), nets=x.get('nets')) for x in pg.get('domains') or [] if x.get('rect_um')],
                                  release_header=d.get('release_header')),
                        children=sorted({tid(die, t) for t in inst_of}), counts={})
        nodes[die] = die_node
        core_users = collections.defaultdict(set); core_outline = {}
        for tname, t in pt.items():
            if not inst_of.get(tname): continue
            nid = tid(die, tname)
            e = els.get((die, tname)); srow = sr.get((die, tname))
            hcs = []
            for c in t.get('hard_cores') or []:
                if not isinstance(c, dict) or not c.get('module') or not c.get('origin_um') or not c.get('outline_um'): continue
                mem = is_mem_macro(c)   # generated SRAM / ROM macro: drawn, never a design node (release_tree_plan.is_mem_macro)
                hcs.append([c.get('inst') or c['module'], None if mem else cid(die, c['module']), c['module'], r2(c['origin_um'][0]), r2(c['origin_um'][1]),
                            r2(c['outline_um'][0]), r2(c['outline_um'][1]), c.get('orient') or 'R0'])
                if mem: continue
                core_users[c['module']].add(nid); core_outline.setdefault(c['module'], [r2(c['outline_um'][0]), r2(c['outline_um'][1])])
            ck = t.get('clock') or {}
            nodes[nid] = dict(id=nid, level='type', die=die, name=tname, parent=die, status=status_of(e), layout=layout_of(e, srow),
                              vis=vis.get((die, tname)),
                              plan=dict(outline=[r2(v) for v in (t.get('outline_um') or [0, 0])[:2]], instances=inst_of[tname], hard=bool(t.get('hard')),
                                        landing_base=t.get('landing_base_type'), module=t.get('module'),
                                        buses=[[b.get('name'), b.get('dir'), b.get('width'), b.get('face'), b.get('window_um'), b.get('kind')] for b in t.get('buses') or []],
                                        ft_slots=[dict(name=s.get('name'), in_face=s.get('in_face'), out_face=s.get('out_face'), width=s.get('width'), stations=s.get('stations'),
                                                       in_window=s.get('in_window_um'), out_window=s.get('out_window_um'),
                                                       regs=[r for r in (s.get('regs_um') or []) if isinstance(r, list)][:16]) for s in t.get('ft_slots') or []],
                                        stations=[[s.get('conn'), s.get('from_um'), s.get('to_um'), s.get('regs_um')] for s in t.get('internal_stations') or []][:400],
                                        clock=dict(tap=ck.get('tap_um'), layer=ck.get('layer'), taps=[[x.get('name'), x.get('kind'), x.get('xy')] for x in ck.get('taps') or []][:400]),
                                        hard_cores=hcs),
                              children=sorted({h[1] for h in hcs if h[1]}))
        for mod, users in core_users.items():
            nid = cid(die, mod)
            e = els.get((die, mod)); srow = sr.get((die, mod))
            nodes[nid] = dict(id=nid, level='core', die=die, name=mod, status=status_of(e), layout=layout_of(e, srow),
                              plan=dict(outline=core_outline.get(mod), used_by=sorted(users), placements=sum(1 for u in users for h in nodes[u]['plan']['hard_cores'] if h[2] == mod)))
        for k in ('type', 'core'):
            c = collections.Counter(n['status']['state'] for n in nodes.values() if n['die'] == die and n['level'] == k)
            die_node['counts'][k] = {s: c.get(s, 0) for s in STATES}
        log('%s: %d types, %d cores' % (die, len(die_node['children']), len(core_users)))
    for nid, n in nodes.items():
        s = store_entry(nid)
        if s:
            if not n.get('layout'): n['layout'] = {}
            n['layout']['store'] = s
    return dict(schema=SCHEMA, generated=time.time(), sources=dict(plan_now=str(STATE / 'plan_now.json'), plan_now_generated=pn.get('generated'),
                                                                   repo=str(REPO), signed_store=str(SIGNED), signed_rows=len(sr), vis=str(VIS), store=str(STORE)),
                states=STATES, dies=[d['die'] for d in pn['dies'] if not dies_filter or d['die'] in dies_filter], nodes=nodes)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=str(STATE / 'design_index.json'))
    ap.add_argument('--die', help='comma list (default: every die of plan_now)')
    a = ap.parse_args()
    t0 = time.time()
    o = build(set(a.die.split(',')) if a.die else None)
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp%d' % os.getpid()); tmp.write_text(json.dumps(o, separators=(',', ':'))); os.replace(tmp, p)
    log('%d nodes -> %s (%.1f s, %.1f MB)' % (len(o['nodes']), p, time.time() - t0, p.stat().st_size / 1e6))


if __name__ == '__main__':
    main()
