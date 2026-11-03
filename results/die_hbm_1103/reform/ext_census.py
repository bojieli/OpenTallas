#!/usr/bin/env python3
"""DIE-HBM-61/PLAN scope-ext census (a)-(d) for an HBM plan dir.
    python3 census.py PLAN_DIR OUT_DIR [--g0 G0_REPORT.json] [--geomcoll GEOMCOLL.json] [--rtl-add RTL.json] [--jobs N]
(a) slot infra (PG / clock entry + sinks / registered reset relay) per partition type and hard-core slot
(b) die nets/buses > 400 um: hop compliance (check.py lane_geometry + lane_pin_hops), type internal stations, GRT hot spots
(c) ONE crossing latency table -> OUT/crossing_latency.json
(d) template census (unique types / hard-core designs, near-duplicate groups)
Plan-time only; reads check.py / schema.py / reset_tree.py / gen_phys.py from the repo next to PLAN_DIR (../../repo)."""
import argparse, json, sys, os, re, collections, hashlib
from pathlib import Path
from multiprocessing import Pool

ap = argparse.ArgumentParser()
ap.add_argument('plan_dir'); ap.add_argument('out')
ap.add_argument('--repo', default='/home/ubuntu/scratch-root/claude/die-hbm-60-plan/repo')
ap.add_argument('--g0'); ap.add_argument('--geomcoll'); ap.add_argument('--rtl-add')
ap.add_argument('--latency-changes'); ap.add_argument('--jobs', type=int, default=8)
ap.add_argument('--skip-reset', action='store_true')
a = ap.parse_args()
PD = Path(a.plan_dir).resolve(); OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, a.repo + '/tools/die_plan')
import schema as S  # noqa
RAW = S.load(str(PD / 'die_plan.json'))
P = S.Plan(RAW, str(PD / 'die_plan.json'))
T = P.types
REACH = 405.0
inst_n = collections.Counter(p['type'] for p in P.parts.values())

def rtfor(tn):
    import reset_tree as RT
    try:
        X = RT.for_type(P, tn)
        return tn, dict(relays=len(X.get('relays') or []), entry=X.get('entry'), max_hop=X.get('max_hop_um'),
                        core_resets=sorted(c['inst'] for c in X.get('core_resets') or []), err=None)
    except Exception as ex:
        return tn, dict(err=f'{type(ex).__name__}: {str(ex)[:200]}')

# ------------------------------------------------------------------ (a)
def item_a():
    import gen_phys as GP
    CE = json.loads((PD / 'clock_entries.json').read_text()) if (PD / 'clock_entries.json').exists() else {}
    GC = json.loads(Path(a.geomcoll).read_text()) if a.geomcoll else {}
    g0 = json.loads(Path(a.g0).read_text()) if a.g0 else None
    tapsink_fail = set()
    if g0:
        for tn, d in (g0['summary'].get('g0c', {}).get('by_type') or {}).items():
            if d.get('geom_tap_sinks'):
                tapsink_fail.add(tn)
    RTD = {}
    if not a.skip_reset:
        soft = [tn for tn, t in T.items() if not t.get('hard')]
        import multiprocessing as MP
        with MP.get_context("fork").Pool(a.jobs) as pool:
            for tn, d in pool.imap_unordered(rtfor, soft):
                RTD[tn] = d
    types, cores = {}, []
    for tn, t in sorted(T.items()):
        hard = bool(t.get('hard'))
        try:
            mac = GP.type_macros(P, tn)
        except Exception:
            mac = None
        pg_ok = (not mac) or bool(t.get('core_pg_connect'))
        ck = t.get('clock') or {}
        clk_ok = bool(ck.get('tap_um') or ck.get('taps'))
        rs = t.get('reset') or {}
        rd = RTD.get(tn, {})
        rst_ok = bool(rs.get('tap_um')) and (a.skip_reset or hard or (rd.get('err') is None and rd.get('relays', 0) > 0))
        miss = [k for k, ok in (('pg', pg_ok), ('clock', clk_ok), ('reset', rst_ok)) if not ok]
        types[tn] = dict(instances=inst_n[tn], hard=hard, die_pg_grid=[g['layer'] for g in P.die['pg']['grid']],
                         macros=len(mac) if mac is not None else None, core_pg_connect=bool(t.get('core_pg_connect')),
                         clock_taps=len(ck.get('taps') or []), clock_tap_um=ck.get('tap_um'),
                         tap_sinks_over_1500=tn in tapsink_fail, reset_tap_um=rs.get('tap_um'),
                         reset_relays=rd.get('relays'), reset_entry=rd.get('entry'), reset_err=rd.get('err'),
                         missing=miss)
        rset = set(rd.get('core_resets') or [])
        ce_t = CE.get(tn) or {}
        for h in t.get('hard_cores') or []:
            pins = []
            if h.get('pins_file') and (PD / h['pins_file']).exists():
                pins = json.loads((PD / h['pins_file']).read_text())
            names = {re.sub(r'\[\d+\]$', '', q.get('name', '')) for q in pins}
            has_rst = any(n in ('rst_n', 'arst_n', 'rst', 'reset_n') or n.startswith('rst_n') for n in names)
            e = (ce_t.get(h['inst'])
                 or next((v for k_, v in ce_t.items() if isinstance(v, dict) and (h['inst'].startswith(k_ + '__') or h['inst'].startswith(k_ + '.'))), None)
                 or next((v for v in ce_t.values() if isinstance(v, dict) and v.get('module') == h['module']), None) or {})
            g = (GC.get(h['module']) or {}).get('metrics') or {}
            sinks = g.get('clock_sinks')
            reset_relay = (h['inst'] in rset) or any(r.startswith(h['inst'] + '.') or h['inst'].startswith(r + '__') for r in rset) or bool(h.get('reset_from_master'))
            pg = 'lef_pg' if h.get('lef') else 'kit_pdn(unverified at plan)'
            row = dict(type=tn, inst=h['inst'], module=h['module'], outline=h['outline_um'],
                       pg=pg, clock_entry=bool(e.get('xy_um')), clock_entry_xy=e.get('xy_um'), kit_clock_sinks=sinks,
                       entries_needed_5k=(-(-sinks // 5000) if sinks else None), has_reset_pin=has_rst,
                       registered_reset_relay=reset_relay)
            row['missing'] = [k for k, ok in (('clock_entry', row['clock_entry']),
                                              ('reset_relay', reset_relay or not has_rst)) if not ok]
            if sinks and sinks > 5000:
                row['missing'].append('entries>5k_sinks')
            cores.append(row)
    sm = dict(types=len(types), types_all3=sum(1 for v in types.values() if not v['missing']),
              types_missing=collections.Counter(m for v in types.values() for m in v['missing']),
              types_missing_list={k: v['missing'] for k, v in types.items() if v['missing']},
              types_tap_sinks_over_1500=sorted(k for k, v in types.items() if v['tap_sinks_over_1500']),
              core_slots=len(cores), core_slots_all3=sum(1 for c in cores if not c['missing']),
              core_slots_missing=collections.Counter(m for c in cores for m in c['missing']),
              core_slots_pg=collections.Counter(c['pg'] for c in cores),
              core_modules_over_5k_sinks=sorted({(c['module'], c['kit_clock_sinks'], c['entries_needed_5k']) for c in cores
                                                 if c['kit_clock_sinks'] and c['kit_clock_sinks'] > 5000}),
              core_modules_sinks_unknown=len({c['module'] for c in cores if not c['kit_clock_sinks']}),
              core_no_entry=sorted({c['module'] for c in cores if not c['clock_entry']}),
              core_reset_missing=sorted({(c['type'], c['inst']) for c in cores if 'reset_relay' in c['missing']})[:60])
    (OUT / 'a_slot_infra.json').write_text(json.dumps(dict(summary=sm, types=types, cores=cores), indent=1, default=list))
    return sm

# ------------------------------------------------------------------ (b)
HOT = [  # DIE-HBM-60/GRT 05:09 partition GRT50 FAIL/NEAR hot spots (type-frame um; pre-d44t evidence)
    ('q_b001', 448, 759, 3999, 4267, 'L730x2+L36x3 664k (FAIL)'), ('q_b010', 20, 226, 2872, 3026, 'L168m 49k/22k (FAIL)'),
    ('q_b101', 468, 605, 597, 805, 'L12x macro col3 374/278 (FAIL)'), ('q_b011', 215, 361, 2070, 2250, 'L15 M7 545-1027 (FAIL)'),
    ('q_b000', 190, 234, 2881, 2911, 'L28/L36 4348 (FAIL)'), ('q_su10', 24, 1390, 87, 532, 'L0x/L730 1416 (FAIL)'),
    ('q_su30', 1960, 1990, 1490, 1525, 'L53/L48/L181r 155/88 (FAIL)'), ('q_b003', 25, 309, 1516, 1926, 'L18x 22.6k (FAIL d44c)'),
    ('q_su00', 455, 475, 543, 563, 'L730 1 gcell (NEAR)'), ('q_su20', 1700, 1720, 1484, 1504, 'L48/L53 3 (NEAR d44c)')]
HOT_NOXY = [('q_b110', 'L6br 6.5k (FAIL d44c, no xy)')]

def hot_of(tn):
    base = tn.split('__')[0]
    return [h for h in HOT if h[0] == base]

def seg_hits(p, q, r):
    x0, x1, y0, y1 = r
    # L path p->(q.x,p.y)->q ; bbox test per leg
    for (ax, ay), (bx, by) in ((p, (q[0], p[1])), ((q[0], p[1]), q)):
        if max(ax, bx) >= x0 and min(ax, bx) <= x1 and max(ay, by) >= y0 and min(ay, by) <= y1:
            return True
    return False

def item_b():
    import check as C
    lanes = []
    for lid in P.lanes:
        try:
            pts, regs, xs = C.lane_geometry(P, lid)
            hops = C.lane_pin_hops(P, lid, regs)
        except Exception as ex:
            lanes.append(dict(id=lid, err=str(ex)[:160])); continue
        L = sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))
        reach = min(float(P.lanes[lid].get('reach_um', P.reach)), P.reach)
        lanes.append(dict(id=lid, len_um=round(L, 1), regs=len(regs) - 2, max_hop_um=round(max(hops) if hops else 0, 1),
                          reach_um=reach, parts=[x['part'] for x in xs], ok=(max(hops) if hops else 0) <= reach + 1e-6))
    long_l = [l for l in lanes if l.get('len_um', 0) > 400]
    ist = []
    for tn, t in T.items():
        hr = hot_of(tn)
        for k, st in enumerate(t.get('internal_stations') or []):
            path = [tuple(st['from_um'])] + [tuple(r) for r in st.get('regs_um') or []] + [tuple(st['to_um'])]
            hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(path, path[1:])]
            L = sum(hops)
            if L <= 400:
                continue
            hot = sorted({h[5] for h in hr for p, q in zip(path, path[1:]) if seg_hits(p, q, h[1:5])})
            ist.append(dict(type=tn, k=k, conn=st.get('conn'), bits=st.get('bits'), len_um=round(L, 1),
                            regs=len(st.get('regs_um') or []), max_hop_um=round(max(hops), 1), ok=max(hops) <= REACH + 1e-6,
                            hot=hot))
    fts = []
    for tn, t in T.items():
        hr = hot_of(tn)
        for s in t.get('ft_slots') or []:
            regs = [tuple(r) for r in s.get('regs_um') or []]
            hot = sorted({h[5] for h in hr for p, q in zip(regs, regs[1:]) if seg_hits(p, q, h[1:5])})
            hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(regs, regs[1:])]
            fts.append(dict(type=tn, slot=s['name'], width=s.get('width'), stations=s.get('stations'),
                            max_station_gap_um=round(max(hops), 1) if hops else None, hot=hot,
                            ok=(not hops) or max(hops) <= REACH + 1e-6))
    g0 = json.loads(Path(a.g0).read_text()) if a.g0 else None
    errs = collections.Counter()
    errl = collections.defaultdict(list)
    ftb = None
    if g0:
        for f in g0['findings']:
            if f['level'] == 'ERROR' and f['check'] in ('hops', 'reach', 'stations', 'street_die_leg', 'ft_budget'):
                errs[f['check']] += 1; errl[f['check']].append(f['msg'][:220])
        ftb = g0['summary'].get('ft_budget')
    decl = dict(types=len(T), face_layers=sum(1 for t in T.values() if t.get('face_layers')),
                ft_slots_types=sum(1 for t in T.values() if t.get('ft_slots')),
                die_ft_bands_types=sum(1 for t in T.values() if t.get('die_ft_bands')),
                m6m7_on_faces=sum(1 for t in T.values() if any(set(v) & {'M6', 'M7'} for v in (t.get('face_layers') or {}).values())),
                channels_types=sum(1 for t in T.values() if t.get('channels')),
                ft_budget_over=(ftb or {}).get('over'), ft_budget_worst=(ftb or {}).get('worst', [])[:3])
    bad_l = sorted([l for l in long_l if not l.get('ok')], key=lambda l: -l.get('max_hop_um', 0))
    bad_i = sorted([s for s in ist if not s['ok']], key=lambda s: -s['max_hop_um'])
    bad_f = sorted([s for s in fts if not s['ok']], key=lambda s: -(s['max_station_gap_um'] or 0))
    sm = dict(die_lanes=len(lanes), die_lanes_gt400=len(long_l), die_lanes_gt400_ok=sum(1 for l in long_l if l.get('ok')),
              die_lanes_gt400_bad=len(bad_l), die_lanes_bad_worst=[(l['id'], l['len_um'], l['max_hop_um'], l['regs']) for l in bad_l[:20]],
              internal_stations_gt400=len(ist), internal_ok=sum(1 for s in ist if s['ok']), internal_bad=len(bad_i),
              internal_bad_worst=[(s['type'], s['conn'], s['len_um'], s['max_hop_um'], s['regs']) for s in bad_i[:20]],
              ft_slots=len(fts), ft_slots_bad_station_gap=len(bad_f),
              ft_bad_worst=[(s['type'], s['slot'], s['max_station_gap_um'], s['stations']) for s in bad_f[:20]],
              hot_tagged=dict(internal=[(s['type'], s['conn'], s['len_um'], s['max_hop_um'], s['hot']) for s in ist if s['hot']][:40],
                              ft=[(s['type'], s['slot'], s['max_station_gap_um'], s['hot']) for s in fts if s['hot']][:60],
                              no_xy=HOT_NOXY),
              g0c_errors=dict(errs), g0c_error_msgs={k: v[:20] for k, v in errl.items()}, declared_capacity=decl)
    (OUT / 'b_long_nets.json').write_text(json.dumps(dict(summary=sm, lanes=lanes, internal=ist, ft_slots=fts), indent=1))
    return sm

# ------------------------------------------------------------------ (c)
def item_c():
    lat = (RAW.get('latency') or {}).get('lanes') or {}
    grp = {l: g['name'] for g in RAW.get('latency_groups') or [] for l in g.get('lanes', [])}
    lc = json.loads(Path(a.latency_changes).read_text()) if a.latency_changes and Path(a.latency_changes).exists() else {}
    rtl = json.loads(Path(a.rtl_add).read_text()) if a.rtl_add and Path(a.rtl_add).exists() else {}
    rows = []
    for lid, ln in P.lanes.items():
        d = lat.get(lid) or {}
        ports = ln.get('ports') or []
        src = P.ports.get(ports[0]) if ports else None
        dst = P.ports.get(ports[-1]) if ports else None
        add_plan = (lc.get(lid, {}).get('after', {}).get('cycles', d.get('cycles', 0)) - lc[lid]['before']['cycles']) if lid in lc else 0
        rows.append(dict(kind='die_lane', id=lid, group=grp.get(lid), src=(src or {}).get('src') if src else None,
                         dst=(dst or {}).get('dst') if dst else None, width=(src or {}).get('width'),
                         seams=len(ports), cycles=d.get('cycles'), stations=d.get('stations'), boundary=d.get('boundary'),
                         faces=d.get('faces'), fixed=d.get('fixed'), pad=d.get('pad'), param=d.get('param'),
                         added_plan_cycles=add_plan, added_rtl_cycles=int(rtl.get(lid, 0)), note=ln.get('note')))
    for tn, t in T.items():
        for k, st in enumerate(t.get('internal_stations') or []):
            n = len(st.get('regs_um') or [])
            key = f'{tn}#{st.get("conn")}#{k}'
            rows.append(dict(kind='type_internal', id=key, type=tn, instances=inst_n[tn], conn=st.get('conn'),
                             launch=st.get('launch'), capture=st.get('capture'), bits=st.get('bits'),
                             cycles=n, stations=n, added_plan_cycles=0, added_rtl_cycles=int(rtl.get(key, 0))))
    # partition <-> hard-core crossings: core face = registered by contract (0 added cycles); counted, not listed per pin
    hc = sum(len(t.get('hard_cores') or []) * max(inst_n[tn], 1) for tn, t in T.items())
    by = collections.Counter(r['kind'] for r in rows)
    grp_c = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r['kind'] == 'die_lane':
            g = grp_c[r['group'] or '-']; g[0] += 1; g[1] += r['cycles'] or 0
    sm = dict(crossings=len(rows), by_kind=dict(by), hard_core_face_crossings_instances=hc,
              die_lane_cycles_total=sum(r['cycles'] or 0 for r in rows if r['kind'] == 'die_lane'),
              type_internal_cycles_total=sum(r['cycles'] for r in rows if r['kind'] == 'type_internal'),
              added_plan_cycles_total=sum(r['added_plan_cycles'] for r in rows),
              lanes_with_added_plan_cycles=sorted(r['id'] for r in rows if r['added_plan_cycles']),
              added_rtl_cycles_total=sum(r['added_rtl_cycles'] for r in rows),
              latency_groups=[(k, v[0], v[1]) for k, v in sorted(grp_c.items()) if k != '-'],
              lanes_missing_latency=sorted(l for l in P.lanes if l not in lat))
    doc = dict(schema='opentallas.hbm_crossing_latency.v1', plan=str(PD / 'die_plan.json'),
               plan_sha256=hashlib.sha256((PD / 'die_plan.json').read_bytes()).hexdigest(),
               hooks=dict(added_rtl_cycles='--rtl-add JSON {crossing id: cycles} (DIE-HBM-61/RTL pipeline additions)',
                          added_plan_cycles='--latency-changes JSON {lane: {before, after}} (plan event station changes)',
                          hard_core_faces='all block I/O registered at the face (OWNER 11-03): 0 crossing cycles; '
                                          'core-internal pipeline additions go in --rtl-add as <type>#core:<inst>'),
               summary=sm, crossings=rows)
    (OUT / 'crossing_latency.json').write_text(json.dumps(doc, indent=1))
    return sm

# ------------------------------------------------------------------ (d)
def item_d():
    g0 = json.loads(Path(a.g0).read_text()) if a.g0 else None
    groups = []
    if g0:
        for f in g0['findings']:
            if f['check'] == 'types' and 'near-duplicate' in f['msg']:
                m = re.search(r"\[(.*?)\]", f['msg'])
                groups.append(re.findall(r"'([^']+)'", m.group(1)) if m else f['msg'])
    designs = collections.defaultdict(set)
    hinst = collections.Counter()
    for tn, t in T.items():
        for h in t.get('hard_cores') or []:
            designs[h['module']].add((tuple(h['outline_um']), h.get('pins_file')))
            hinst[h['module']] += max(inst_n[tn], 1)
    uniq = sum(len(v) for v in designs.values())
    multi = sorted(((m, len(v), hinst[m]) for m, v in designs.items() if len(v) > 1), key=lambda x: -x[1])
    sm = dict(partition_types=len(T), partitions=len(P.parts), singleton_types=sum(1 for v in inst_n.values() if v == 1),
              near_duplicate_groups=groups, near_duplicate_types=sum(len(g) for g in groups),
              types_cut_if_merged=sum(len(g) - 1 for g in groups),
              hard_core_modules=len(designs), hard_core_unique_designs=uniq, hard_core_instances=sum(hinst.values()),
              modules_with_variants=multi[:40], designs_cut_if_variants_unified=uniq - len(designs))
    (OUT / 'd_templates.json').write_text(json.dumps(sm, indent=1))
    return sm

res = {}
for k, f in (('d', item_d), ('c', item_c), ('b', item_b), ('a', item_a)):
    try:
        res[k] = f()
    except Exception as ex:
        import traceback; traceback.print_exc(); res[k] = dict(err=str(ex))
    (OUT / 'census_summary.json').write_text(json.dumps(res, indent=1, default=list))
    print(k, 'done', flush=True)
