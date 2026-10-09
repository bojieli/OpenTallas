#!/usr/bin/env python3
"""Die-level academic-validation evidence, one table per die, with explicit error bars for placeholder views.

Owner steer 2026-10-07 (BRIEF.md "academic validation"): per die, report full-die GRT overflow, die STA on GRT parasitics
(TT setup / FF hold, option B), the CTS-validated clock plan, IR, representative-region DRT (GRT-vs-DRT wire length and
slack, with each region's boundary caveat) and the share of the die on real views vs placeholders.

Error bar: every timing endpoint is classified by the masters at both ends of its worst path:
  real         both ends on real views (closed routed ETMs, assembled slab ETMs, macros)
  real+relay   ends on real views or die relay stations (relay = generated die flop; constants may be interim)
  placeholder  any end on a placeholder / interim / assumed-constant view, or a die port
The real-only result is the evidence; [real-only WNS, all-paths WNS] is the placeholder error bar.
Runs that have not produced a result are reported as {"status": "pending"}, never as numbers.

    python3 tools/die_evidence_report.py [--out results/arch/die_evidence_20261008] [--die qwen,hbm,s81]

Each die is probed on its host over ssh: this file is piped to `python3 - probe <die>` (remote python, stdlib only)."""
import argparse
import bisect
import concurrent.futures
import glob
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

SCR = '/srv/opentallas-scratch/claude'
DIES = {
    'qwen': dict(
        name='Qwen3-8B ROM die r21b', host='ot-epyc3',
        note='adopted die r21b (qwen-repack 9d2719325): 846.792 mm2, 13,220 instances; chain '
             f'{SCR}/qwen-die-r20/r21b/STATUS.log (real case -> PDN r5 -> full-die GRT -> STA TT/FF -> IR -> regions)'),
    'hbm': dict(
        name='HBM accelerator die r25', host='ot-epyc1tb',
        note=f'chain {SCR}/die-evidence/hbm_r25/STATUS.log (current view index, rule-H1 die hold pads)'),
    's81': dict(
        name='DeepSeek-V4.1 ROM die S81 (m221pq)', host='ot-epyc3',
        note=f'{SCR}/s81-die/m221pq_r3 (r3 full-die GRT + balanced-kit STA v6) and m221pq_r4 (--nxt-reach relay fix)'),
}
STATIC = {
    # evidence that lives only in a log / committed record (no live probe); cited, never recomputed
    'qwen': {
        'prior_r21': dict(status='superseded', die='r21 (821.3 mm2, pre-repack; NOT the adopted die)',
                          grt_overflow=0, sta_tt_wns_ps=50.84, sta_ff_wns_ps=-5.64,
                          sta_ff_note='FF -5.64 only on ASSUMED qfd_tile views', ir_worst_mv=29.43,
                          source='results/rtl/qwen_dietop_20261007/record.json (commit 660b49c8f)'),
        'clock_plan': dict(status='missing', note='no Qwen die CTS validation: tools/budgets/extract_die.py supports '
                                                  'hbm + s81 only (die-evidence.log 14:20 PT)'),
    },
    'hbm': {
        'ir': dict(status='done (stale placement)', placement='r23 (not r25)', windows_pass='125/125 load windows',
                   worst_interior_rail_to_rail_mv=33.26, budget_mv=35.0, worst_window='c_w10_09',
                   caveat='18 no-load windows (4 PSM segfaults, all no-load row 10); r25 IR not re-run',
                   source='hbm-die.log 2026-10-07 19:23 PT (EPYC2 hbm-die/ir)'),
    },
}


# ----------------------------------------------------------------------------------------------- remote-side helpers
def _read(p):
    try:
        return Path(p).read_text(errors='replace')
    except OSError:
        return ''


def _exists(p):
    return os.path.exists(p)


def netlist_masters(path):
    m = {}
    with open(path, errors='replace') as f:
        for ln in f:
            mm = re.match(r'\s*(\w+)\s+(\\?[^\s(]+)\s*\(', ln)
            if mm and mm.group(1) not in ('module', 'input', 'output', 'wire', 'inout', 'assign', 'endmodule'):
                m[mm.group(2).lstrip('\\')] = mm.group(1)
    return m


def lef_sizes(paths):
    sz, cur = {}, None
    for p in paths:
        for ln in _read(p).splitlines():
            t = ln.split()
            if len(t) >= 2 and t[0] == 'MACRO':
                cur = t[1]
            elif cur and len(t) >= 4 and t[0] == 'SIZE':
                sz[cur] = float(t[1]) * float(t[3])
            elif cur and t[:1] == ['END'] and t[1:2] == [cur]:
                cur = None
    return sz


def area_split(inst2m, sizes, cls):
    out = {}
    for inst, m in inst2m.items():
        c = cls(m)
        d = out.setdefault(c, dict(instances=0, area_mm2=0.0, masters=set()))
        d['instances'] += 1
        d['area_mm2'] += sizes.get(m, 0.0) / 1e6
        d['masters'].add(m)
    ti = sum(d['instances'] for d in out.values()) or 1
    ta = sum(d['area_mm2'] for d in out.values()) or 1
    missing = sorted({m for m in inst2m.values() if m not in sizes})
    return dict(by_class={c: dict(instances=d['instances'], instance_frac=round(d['instances'] / ti, 4),
                                  area_mm2=round(d['area_mm2'], 3), area_frac=round(d['area_mm2'] / ta, 4),
                                  masters=len(d['masters'])) for c, d in sorted(out.items())},
                masters_without_lef_size=missing[:20], n_masters_without_lef_size=len(missing))


def _inst(tok, inst2m):
    tok = tok.lstrip('\\')
    if tok in inst2m:
        return tok
    if '/' in tok:
        head = tok.rsplit('/', 1)[0]
        if head in inst2m:
            return head
    return None


def _tier(ca, cb):
    s = {ca, cb}
    if s <= {'real'}:
        return 'real'
    if s <= {'real', 'relay'}:
        return 'real+relay'
    return 'placeholder'


def _agg(rows):
    """rows: slacks (ps) of endpoints -> wns, tns (negative only), violators."""
    if not rows:
        return dict(endpoints=0, wns_ps=None, tns_ps=0.0, viol=0)
    neg = [s for s in rows if s < 0]
    return dict(endpoints=len(rows), wns_ps=round(min(rows), 2), tns_ps=round(sum(neg), 1), viol=len(neg))


def split_pairs(pairs, inst2m, cls, unit=1000.0):
    """pairs file: 'startpin endpin slack' per endpoint (worst path); exact two-ended classification."""
    tiers = {'real': [], 'real+relay': [], 'placeholder': []}
    for ln in _read(pairs).splitlines():
        t = ln.split()
        if len(t) != 3:
            continue
        try:
            s = float(t[2]) * unit
        except ValueError:
            continue
        a, b = _inst(t[0], inst2m), _inst(t[1], inst2m)
        ca = cls(inst2m[a]) if a else 'port'
        cb = cls(inst2m[b]) if b else 'port'
        tiers[_tier(ca, cb)].append(s)
    out = {k: _agg(v) for k, v in tiers.items()}
    # cumulative tiers: real+relay includes real
    rr = tiers['real'] + tiers['real+relay']
    out['real+relay'] = _agg(rr)
    out['placeholder_touching'] = out.pop('placeholder')
    out['method'] = 'exact: start+end masters of each listed endpoint\'s worst path'
    return out


def split_end_paths(ends, paths, inst2m, cls):
    """end report (all endpoints, endpoint pin only) + full path report (top N per group, start+end):
    endpoint-on-real gives a LOWER bound on real-only WNS, the worst listed real-only path an UPPER bound."""
    ep = {'real': [], 'relay': [], 'placeholder': []}
    for ln in open(ends, errors='replace'):
        f = ln.replace('(VIOLATED)', '').replace('(MET)', '').split()
        if len(f) < 4 or '/' not in f[0]:
            continue
        try:
            s = float(f[-1])
        except ValueError:
            continue
        i = _inst(f[0], inst2m)
        c = cls(inst2m[i]) if i else 'port'
        ep['placeholder' if c not in ('real', 'relay') else c].append(s)
    listed = {'real': [], 'real+relay': [], 'placeholder': []}
    cur = {}
    for ln in open(paths, errors='replace'):
        if ln.startswith('Startpoint:'):
            cur = dict(a=ln.split()[1])
        elif ln.startswith('Endpoint:'):
            cur['b'] = ln.split()[1]
        elif 'slack (' in ln and 'a' in cur and 'b' in cur:
            try:
                s = float(ln.split()[0])
            except ValueError:
                continue
            a, b = _inst(cur['a'], inst2m), _inst(cur['b'], inst2m)
            ca = cls(inst2m[a]) if a else 'port'
            cb = cls(inst2m[b]) if b else 'port'
            t = _tier(ca, cb)
            listed[t].append(s)
            if t == 'real':
                listed['real+relay'].append(s)
            cur = {}
    real_end = _agg(ep['real'])
    rr_end = _agg(ep['real'] + ep['relay'])
    def tier(endagg, lst):
        found = min(lst) if lst else None
        lo = endagg['wns_ps']
        exact = found is not None and lo is not None and abs(found - lo) < 0.05
        return dict(wns_ps=found if exact else None, wns_range_ps=[lo, found], exact=exact,
                    endpoints_on_tier=endagg['endpoints'], viol_upper_bound=endagg['viol'],
                    tns_ps_lower_bound=endagg['tns_ps'], listed_paths=len(lst))
    return {'real': tier(real_end, listed['real']), 'real+relay': tier(rr_end, listed['real+relay']),
            'placeholder_touching': dict(endpoint_on_placeholder=_agg(ep['placeholder']),
                                         listed_paths=len(listed['placeholder'])),
            'method': 'end report classifies the endpoint master only (lower bound on real-only WNS: every real-only '
                      'path ends on a real endpoint); the top-N path report gives the startpoint (upper bound: a '
                      'listed real-only path); exact when the two agree'}


def clock_summary(plan):
    if not _exists(plan):
        return dict(status='pending', plan=plan)
    d = json.loads(_read(plan))
    regs = d.get('regions') or {}
    intra = [r.get('intra_skew_bound_ss_ps') for r in regs.values() if r.get('intra_skew_bound_ss_ps') is not None]
    inter = [v.get('skew_bound_ss_ps') for v in (d.get('inter_region') or {}).values()]
    v = d.get('violations') or {}
    return dict(status='done', plan=plan, source_commit=d.get('source_commit'), regions=len(regs),
                synchronous_pairs=d.get('synchronous_pairs'), max_intra_skew_ss_ps=max(intra) if intra else None,
                max_inter_skew_ss_ps=max(inter) if inter else None, policy=d.get('policy'),
                violations_intra=v.get('intra'), violations_inter=v.get('inter'), violation_rows=(v.get('rows') or [])[:3],
                trees=len(d.get('trees') or {}))


def grt_overflow(log):
    txt = _read(log)
    if not txt:
        return dict(status='pending', log=log)
    tot = re.findall(r'^Total\s+\S+\s+\S+\s+\S+\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', txt, re.M)
    wl = re.findall(r'Total wirelength:\s*([\d.]+)\s*um', txt)
    if not tot:
        return dict(status='pending', log=log)
    h, v_, t = map(int, tot[-1])
    return dict(status='done', log=log, overflow_total=t, overflow_h=h, overflow_v=v_,
                wirelength_m=round(float(wl[-1]) / 1e6, 1) if wl else None)


def wl_compare(grt_csv, drt_csv):
    def load(p):
        d = {}
        for ln in _read(p).splitlines():
            t = ln.split()
            if len(t) >= 3 and t[0] in ('grt:', 'drt:'):
                try:
                    d[t[1]] = float(t[2])
                except ValueError:
                    pass
        return d
    g, r = load(grt_csv), load(drt_csv)
    common = [n for n in g if n in r and g[n] > 0]
    if not common:
        return None
    ratios = sorted(r[n] / g[n] for n in common)
    return dict(nets=len(common), grt_total_um=round(sum(g[n] for n in common), 1),
                drt_total_um=round(sum(r[n] for n in common), 1),
                total_ratio=round(sum(r[n] for n in common) / sum(g[n] for n in common), 4),
                median_ratio=round(statistics.median(ratios), 4), p95_ratio=round(ratios[int(0.95 * (len(ratios) - 1))], 4),
                max_ratio=round(ratios[-1], 3))


def guided_region(d):
    """Qwen/HBM guided-window region (tools/qwen_die_region_guided.py)."""
    name = re.sub(r'^region[g]?_', '', os.path.basename(d.rstrip('/')))
    out = dict(region=name, dir=d)
    cut = re.findall(r'QDR_CUT_DONE (\{.*\})', _read(f'{d}/cut.log'))
    if cut:
        c = json.loads(cut[-1])
        pg = c.get('pins_guides', {})
        nets = pg.get('nets') or c.get('region_nets') or 0
        out['window_um'] = c.get('region_um')
        out['area_mm2'] = round(c.get('area_mm2', 0), 3)
        out['kept_instances'] = c.get('kept_instances')
        out['boundary'] = dict(nets=nets, guided_pins=pg.get('guided'), projected_pins=pg.get('projected'),
                               no_track=pg.get('no_track'),
                               unpinned_crossing_frac=round(pg.get('no_track', 0) / nets, 3) if nets else None,
                               intruders_as_obstructions=len(c.get('intruders_as_obstructions') or []),
                               caveat='no_track crossings found no free track at the window edge: those wires end '
                                      'short of the edge, so DRT under-counts edge demand by about this fraction')
    else:
        out['status'] = 'pending' if _exists(f'{d}/cut.log') or _exists(f'{d}/start.out') else 'not started'
        return out
    st, drt = _read(f'{d}/STATUS.log'), _read(f'{d}/drt.log')
    err = re.findall(r'\[ERROR (\w+-\d+)\]\s*(.*)', drt)
    fail = re.findall(r'OT_STEP_FAIL (\w+) (\S+)', st + drt)
    viol = [int(x) for x in re.findall(r'(?:Number of violations =|with)\s+(\d+)\s+violations?', drt)]
    out['drt'] = dict(final_violations=viol[-1] if viol else None, logged=len(viol))
    if not _exists(f'{d}/drt.exit') and not _exists(f'{d}/drt.log.exit'):
        out['status'] = 'pending (detail route running or queued)'
        return out
    if err or (fail and not viol):
        out['status'] = 'failed'
        out['failure'] = (err[0][0] + ': ' + err[0][1][:200]) if err else ' '.join(fail[-1])
        if not out.get('kept_instances'):
            out['failure'] += ' (window cut kept 0 instances / 0 nets: the window misses the IO edge it targets)'
        return out
    out['status'] = 'done'
    out['wirelength'] = wl_compare(f'{d}/wl_grt.csv', f'{d}/wl_drt.csv')
    sl = {}
    for m in re.finditer(r'OT_STA para=(\w+) corner=(\w+) wns_ns=(\S+)', st):
        v = float(m.group(3))
        sl.setdefault(m.group(2), {})[m.group(1)] = None if abs(v) > 1e30 else round(v * 1000, 2)
    for f in glob.glob(f'{d}/sta_*_*.log'):
        mm = re.match(r'sta_(grt|rcx)_(\w+)\.log$', os.path.basename(f))
        w = re.findall(r'worst slack (?:max|min)\s+(\S+)', _read(f))
        if mm and w:
            sl.setdefault(mm.group(2), {})[mm.group(1)] = float(w[-1])
    for c, v in sl.items():
        if v.get('grt') is not None and v.get('rcx') is not None:
            v['delta_ps'] = round(v['rcx'] - v['grt'], 2)
    out['slack_ps'] = sl or None
    if out['wirelength'] is None:
        out['caveat'] = 'no DRT wire-length table (wl_drt.csv empty): GRT-vs-DRT wire length not measurable'
    return out


# ----------------------------------------------------------------------------------------------- per-die probes
CC_NOTE = ('clock context: {0} view clock pins bound, {1} missing; paths of masters whose clock is missing are untimed, '
           'so the placeholder error bar cannot see them (the all-paths WNS is optimistic by that much)')


def probe_hbm():
    R = f'{SCR}/die-evidence/hbm_r25'
    G = f'{R}/grt2'
    man = json.loads(_read(f'{G}/manifest.json') or '{}')
    real = set(man.get('real_views', {}))
    tt_fb = json.loads(_read(f'{G}/tt_fallback.json') or '[]')
    cls = lambda m: 'real' if m in real else ('relay' if re.search(r'_rly_?\d', m) else 'placeholder')
    inst2m = netlist_masters(f'{G}/die.v')
    out = dict(run=R, status_log=_read(f'{R}/STATUS.log').strip().splitlines()[-3:])
    out['views'] = dict(real_views=len(real), real_views_ss_as_tt=tt_fb,
                        classes='real = manifest real_views (routed abstracts + libs); relay = hfd_rly_* die relays; '
                                'placeholder = analytic / interim masters')
    out['area'] = area_split(inst2m, lef_sizes(glob.glob(f'{G}/*.lef')), cls)
    g = grt_overflow(f'{G}/grt_sta.log')
    out['grt'] = g
    sta = {}
    P = f'{G}/sta_pad'
    for c, chk in (('tt', 'setup'), ('ff', 'hold'), ('ss', 'setup (sensitivity)')):
        log = _read(f'{P}/sta.log')
        w = re.findall(rf'OT_WNS corner={c} pads=(\w+) ns=(\S+) tns_ns=(\S+)', log)
        if not _exists(f'{P}/paths_{c}.txt') or not w:
            sta[c] = dict(status='pending', check=chk, run=f'{P}/sta.log (re-runs the full-die GRT in-session, '
                                                          'then raw and rule-H1-padded STA per corner)')
            continue
        res = dict(status='done', check=chk)
        for pads, wns, tns in w:
            res[f'all_{pads}'] = dict(wns_ps=round(float(wns) * 1000, 2), tns_ps=round(float(tns) * 1000, 1))
        res['split_padded'] = split_pairs(f'{P}/paths_{c}.txt', inst2m, cls)
        cc = re.findall(rf'OT_CLOCK_CONTEXT corner={c} bound=(\d+) missing=(\d+)', log)
        if cc:
            res['clock_context'] = CC_NOTE.format(*cc[-1])
        if _exists(f'{P}/paths_{c}_nopad.txt'):
            res['split_nopad'] = split_pairs(f'{P}/paths_{c}_nopad.txt', inst2m, cls)
        sta[c] = res
    out['sta'] = sta
    # prior full-die GRT STA (hbm-die r25_grt, 2026-10-07 22:29 PT views, no hold pads): kept as the last measured bar
    Q = f'{SCR}/hbm-die/r25_grt'
    if _exists(f'{Q}/grt_sta.log'):
        log = _read(f'{Q}/grt_sta.log')
        qi = netlist_masters(f'{Q}/die.v') if _exists(f'{Q}/die.v') else inst2m
        prior = dict(status='superseded (pending sta_pad replaces it)', run=Q,
                     views='2026-10-07 22:29 PT kit: interim SM / attn_tile views, 22 view clocks missing, no hold pads; endpoints classed with the CURRENT r25 real-view set, so SM / attn_tile paths count as real here although this kit had them interim')
        for c in ('tt', 'ff'):
            w = re.findall(rf'OT_WNS corner={c} ns=(\S+) tns_ns=(\S+)', log)
            if w and _exists(f'{Q}/paths_{c}.txt'):
                prior[c] = dict(all=dict(wns_ps=round(float(w[-1][0]) * 1000, 2), tns_ps=round(float(w[-1][1]) * 1000, 1)),
                                split=split_pairs(f'{Q}/paths_{c}.txt', qi, cls))
                cc = re.findall(rf'OT_CLOCK_CONTEXT corner={c} bound=(\d+) missing=(\d+)', log)
                if cc:
                    prior[c]['clock_context'] = CC_NOTE.format(*cc[-1])
        out['sta_prior_r25_grt'] = prior
    out['clock_plan'] = clock_summary(f'{R}/clock/plan.json')
    out['regions'] = [guided_region(d) for d in sorted(glob.glob(f'{G}/regiong_*'))]
    return out


def probe_s81():
    B = f'{SCR}/s81-die'
    out = dict(run=B)
    r4 = f'{B}/m221pq_r4'
    r4s = f'{r4}/grt/summary.txt'
    out['r4'] = dict(status='done' if _exists(r4s) else 'pending', summary=_read(r4s).strip() or None,
                     note='r4 = r3 + --nxt-reach relay placement (fixes the 776-906 um g_rt_*_8a_y1 relays behind TT -244)',
                     gen_log_tail=_read(f'{r4}/real_gen.log').strip().splitlines()[-2:])
    # latest run with a full STA: r4 (when its STA lands) else r3's newest balanced kit
    cand = []
    for run in (r4, f'{B}/m221pq_r3'):
        vs = sorted(glob.glob(f'{run}/sta_v*'), key=lambda p: int(re.sub(r'\D', '', p.rsplit('_v', 1)[1]) or 0), reverse=True)
        for s in vs + [f'{run}/grt']:
            kit = f'{run}/kit_v' + s.rsplit('_v', 1)[1] if '/sta_v' in s else f'{run}/kit'
            if _exists(f'{s}/end_tt.rpt') and _exists(f'{s}/end_ff.rpt') and _exists(f'{kit}/index.json'):
                cand.append((run, s, kit))
    if not cand:
        out['sta'] = dict(status='pending')
        return out
    run, S, K = cand[0]
    out['sta_run'] = dict(run=run, sta=S, kit=K, summary=_read(f'{S}/summary.txt').strip().splitlines())
    idx = json.loads(_read(f'{K}/index.json'))
    view = {m: v.get('view') for m, v in idx.get('masters', {}).items()}
    REAL = ('closed', 'assembled', 'macro')
    cls = lambda m: ('real' if view.get(m) in REAL else
                     'relay' if re.search(r'_rly_', m) else 'placeholder')
    inst2m = netlist_masters(f'{K}/die.v')
    out['views'] = dict(masters_by_view={k: sum(1 for v in view.values() if v == k) for k in sorted(set(view.values()))},
                        classes='real = closed routed views + assembled slab ETMs + macros; relay = dsfd_rly_* die '
                                'relays (INTERIM lib constants, real GRT wire); placeholder = interim + partitioned '
                                'slabs (tiles closed, no composite view)')
    lefs = glob.glob(f'{run}/a_real/*.lef') or glob.glob(f'{B}/m221pq_r3/a_real/*.lef')
    out['area'] = area_split(inst2m, lef_sizes(lefs), cls)
    out['grt'] = grt_overflow(f'{run}/grt/grt.log')
    sm = _read(f'{S}/summary.txt')
    sta = {}
    for c, chk, mx in (('tt', 'setup', 'max'), ('ff', 'hold', 'min')):
        w = re.search(rf'{c} worst slack {mx} (\S+) tns {mx} (\S+)', sm)
        res = dict(status='done', check=chk, all=dict(wns_ps=float(w.group(1)), tns_ps=float(w.group(2))) if w else None)
        res['split'] = split_end_paths(f'{S}/end_{c}.rpt', f'{S}/paths_{c}.rpt', inst2m, cls)
        sta[c] = res
    w = re.search(r'ss worst slack max (\S+) tns max (\S+)', sm)
    sta['ss'] = dict(status='done', check='setup (sensitivity)',
                     all=dict(wns_ps=float(w.group(1)), tns_ps=float(w.group(2))) if w else None)
    out['sta'] = sta
    out['clock_plan'] = clock_summary(f'{run}/clock/plan.json' if _exists(f'{run}/clock/plan.json')
                                      else f'{B}/m221pq_r3/clock/plan.json')
    irr = f'{B}/m221pq/ir/ir_record.json'
    if _exists(irr):
        d = json.loads(_read(irr))
        out['ir'] = dict(status='done', record=irr, die='m221pq (same generator options as r3)',
                         windows={k: dict(pass_interior=v.get('pass_interior'),
                                          rail_to_rail_interior_mv=v.get('rail_to_rail_interior_mv'),
                                          rail_to_rail_worst_mv=v.get('rail_to_rail_worst_mv'),
                                          budget_mv=v.get('budget_mv'))
                                  for k, v in d.get('cases', {}).items()},
                         caveat='judged inside the window interior (one bump pitch from each window edge: the die '
                                'continues); edge cells exceed 35 mV by construction of the window cut')
    else:
        out['ir'] = dict(status='pending', record=irr)
    regs = []
    for d in sorted(glob.glob(f'{run}/regions/region_*') or glob.glob(f'{B}/m221pq_r3/regions/region_*')):
        rj = f'{d}/region.json'
        if not _exists(rj):
            regs.append(dict(region=re.sub(r'^region_', '', os.path.basename(d)), status='pending (DRT running)' if not _exists(f'{d}/run.end')
                             else 'failed (no region.json)', dir=d))
            continue
        j = json.loads(_read(rj))
        cr = j.get('crop', {})
        tm = {c: dict(grt=v.get('wns_grt_ps'), drt=v.get('wns_drt_ps'),
                      delta_ps=(round(v['wns_drt_ps'] - v['wns_grt_ps'], 2)
                                if isinstance(v.get('wns_grt_ps'), (int, float)) and abs(v['wns_grt_ps']) < 1e30
                                and isinstance(v.get('wns_drt_ps'), (int, float)) and abs(v['wns_drt_ps']) < 1e30 else None))
              for c, v in (j.get('timing') or {}).items()}
        regs.append(dict(region=j.get('name'), status='done', dir=d, box_um=j.get('box_um'),
                         kept_instances=cr.get('kept'), boundary_ports=cr.get('ports'),
                         drt=dict(final_drc=j['drt'].get('final_drc'), iterations=j['drt'].get('iterations'),
                                  first_iter=(j['drt'].get('violations_per_iter') or [None])[0]),
                         antenna=j.get('antenna'), wirelength=j.get('wirelength'), slack_ps=tm,
                         caveat='crop keeps whole nets inside the box and turns every cut net into a boundary port at '
                                'its GRT crossing; WNS = inf means no constrained flop-to-flop path lies wholly '
                                'inside the box (timing delta unmeasurable there)'))
    out['regions'] = regs
    return out


def probe_qwen():
    Q = f'{SCR}/qwen-die-r20'
    R, C = f'{Q}/r21b', f'{Q}/cases/r21b_pdn'
    G = f'{Q}/dietop_r21/r21b_adjfix_t4p8'
    out = dict(run=R, status_log=_read(f'{R}/STATUS.log').strip().splitlines()[-4:])
    v = json.loads(_read(f'{R}/libs/views.json') or '{}')
    real = set(v.get('etm_bound', {})) | {'ot_hbm3e_phy'}
    assumed = set(v.get('assumed_constants', {}) if isinstance(v.get('assumed_constants'), (dict, list)) else [])
    cls = lambda m: 'real' if m in real else ('relay' if re.search(r'qfd_rlyf?_', m) else 'placeholder')
    inst2m = netlist_masters(f'{C}/die.v') if _exists(f'{C}/die.v') else {}
    out['views'] = dict(etm_bound=len(real) - 1, assumed_constants=len(assumed),
                        classes='real = ETM-bound masters (routed signoff ETMs, incl. relays bound by direction); '
                                'placeholder = ASSUMED constant views (incl. qfd_tile, qfd_cdc); TT assumed = SS '
                                'constants (pessimistic)')
    out['area'] = area_split(inst2m, lef_sizes(glob.glob(f'{C}/*.lef')), cls) if inst2m else dict(status='pending')
    out['grt'] = grt_overflow(f'{G}/grt.log')
    sta = {}
    for c, chk in (('tt', 'setup'), ('ff', 'hold')):
        D = f'{Q}/dietop_r21/sta_r21b_{c}'
        ends, paths, log = f'{D}/grt_{c}_ends.rpt', f'{D}/grt_{c}_paths.rpt', _read(f'{D}/grt_{c}.log')
        w = re.findall(r'worst slack (?:max|min)\s+(\S+)', log)
        t = re.findall(r'tns (?:max|min)\s+(\S+)', log)
        if not (w and _exists(ends)):
            sta[c] = dict(status='pending', check=chk, dir=D)
            continue
        res = dict(status='done', check=chk, all=dict(wns_ps=float(w[-1]), tns_ps=float(t[-1]) if t else None))
        res['split'] = split_end_paths(ends, paths, inst2m, cls) if _exists(paths) else None
        sta[c] = res
    out['sta'] = sta
    jt = _read(f'{R}/ir/judged.txt').strip()
    out['ir'] = dict(status='done', judged=jt.splitlines()[-8:]) if jt else dict(status='pending', dir=f'{R}/ir')
    regs = [guided_region(d) for d in sorted(glob.glob(f'{R}/regions/gw_*'))]
    out['regions'] = regs or [dict(region='gw_col/io/spine/vmsu', status='pending', planned='gw_col / gw_io / gw_spine / gw_vmsu guided windows '
                                                             'cut from the overflow-0 r21b GRT (chain step 6)')]
    return out


PROBES = dict(qwen=probe_qwen, hbm=probe_hbm, s81=probe_s81)


# ----------------------------------------------------------------------------------------------- local driver
def run_probe(die):
    src = Path(__file__).read_text()
    t0 = time.time()
    p = subprocess.run(['ssh', '-o', 'ConnectTimeout=20', DIES[die]['host'], 'python3', '-', 'probe', die],
                       input=src, capture_output=True, text=True, timeout=3600)
    if p.returncode != 0:
        return dict(status='probe failed', stderr=p.stderr[-1500:])
    d = json.loads(p.stdout)
    d['probe_s'] = round(time.time() - t0, 1)
    return d


def fmt(v, unit=''):
    return 'pending' if v is None else (f'{v:+.1f}{unit}' if isinstance(v, float) else f'{v}{unit}')


def sta_cell(s, key='split'):
    """one table cell: real-only | real+relay | all (= placeholder error bar)."""
    if not s or s.get('status') != 'done':
        return 'pending', 'pending', 'pending'
    allw = (s.get('all') or s.get('all_pad') or s.get('all_nopad') or {}).get('wns_ps')
    sp = s.get(key) or s.get('split_padded') or {}
    def t(x):
        if not x:
            return 'n/a'
        if 'wns_range_ps' in x:
            if x.get('exact'):
                return f"{x['wns_ps']:+.1f}"
            lo, hi = x['wns_range_ps']
            return f"[{fmt(lo)}, {fmt(hi)}]" if hi is not None else (f">= {lo:+.1f}" if lo is not None else 'no endpoints')
        return f"{x['wns_ps']:+.1f} ({x['viol']} viol)" if x.get('wns_ps') is not None else 'no failing endpoints'
    return t(sp.get('real')), t(sp.get('real+relay')), fmt(allw)


def readme(rep):
    L = [f"# Die-level evidence ({rep['date']})", '',
         'Academic-validation evidence per die (owner steer 2026-10-07): full-die global route, die STA on global-route',
         'parasitics (option B: setup at TT 833.333 ps, hold at FF), the CTS-validated clock plan, IR, and detail route of',
         'representative regions. Generated by `python3 tools/die_evidence_report.py`; `report.json` holds every number',
         'and its run path. "pending" means the run has not produced a result yet; it is never a number.', '',
         '## Error bar for placeholder views', '',
         'Each failing or reported endpoint is classed by the masters at both ends of its worst path: **real** (both',
         'ends on closed routed ETMs, assembled slab ETMs or macros), **real+relay** (die relay stations allowed: their',
         'wire is real global route, their flop constants may be interim) and **all** (includes paths touching',
         'placeholder, interim or assumed-constant views and die ports). The real-only WNS is the evidence; the gap to the',
         'all-paths WNS is the placeholder error bar. A range `[a, b]` means the endpoint report bounds the real-only WNS',
         'from below (a) and the top-N path report gives a listed real-only path (b). Slacks in ps.', '',
         '| Die | GRT overflow | TT setup WNS real / real+relay / all | FF hold WNS real / real+relay / all | Clock plan (CTS) | IR | Real-view share (inst / area) |',
         '|---|---|---|---|---|---|---|']
    for k, d in rep['dies'].items():
        g = d.get('grt') or {}
        gtxt = f"{g['overflow_total']} ({g.get('wirelength_m')} m)" if g.get('status') == 'done' else 'pending'
        tt = sta_cell((d.get('sta') or {}).get('tt'))
        ff = sta_cell((d.get('sta') or {}).get('ff'))
        cp = d.get('clock_plan') or {}
        ctxt = (f"{cp['regions']} regions, intra <= {cp['max_intra_skew_ss_ps']}, inter <= {cp['max_inter_skew_ss_ps']} ps, "
                f"{cp['violations_intra']}+{cp['violations_inter']} viol" if cp.get('status') == 'done' else cp.get('status', 'pending'))
        ir = d.get('ir') or {}
        if ir.get('windows'):
            vals = [w['rail_to_rail_interior_mv'] for w in ir['windows'].values()]
            itxt = f"{min(vals)}-{max(vals)} mV interior / 35 ({len(vals)} windows)"
        elif ir.get('worst_interior_rail_to_rail_mv') is not None:
            itxt = f"{ir['worst_interior_rail_to_rail_mv']} mV / {ir['budget_mv']:.0f} ({ir.get('placement')})"
        else:
            itxt = ir.get('status', 'pending')
        a = ((d.get('area') or {}).get('by_class') or {}).get('real')
        atxt = f"{a['instance_frac']:.1%} / {a['area_frac']:.1%}" if a else 'pending'
        L.append(f"| {DIES[k]['name']} | {gtxt} | {' / '.join(tt)} | {' / '.join(ff)} | {ctxt} | {itxt} | {atxt} |")
    L += ['', '## Per die', '']
    for k, d in rep['dies'].items():
        L += [f"### {DIES[k]['name']}", '', DIES[k]['note'], '']
        ar = (d.get('area') or {}).get('by_class') or {}
        if ar:
            L.append('View share: ' + '; '.join(f"{c} {v['instances']:,} inst ({v['instance_frac']:.1%}), "
                                               f"{v['area_mm2']:.1f} mm2 ({v['area_frac']:.1%})" for c, v in ar.items()) + '.')
            L.append('')
        for c in ('tt', 'ff'):
            s = (d.get('sta') or {}).get(c) or {}
            if s.get('status') != 'done':
                L.append(f"- STA {c.upper()}: pending ({s.get('dir') or s.get('run') or ''}).")
                continue
            sp = s.get('split') or s.get('split_padded') or {}
            ph = sp.get('placeholder_touching') or {}
            phw = ph.get('wns_ps') if 'wns_ps' in ph else (ph.get('endpoint_on_placeholder') or {}).get('wns_ps')
            phv = ph.get('viol') if 'viol' in ph else (ph.get('endpoint_on_placeholder') or {}).get('viol')
            r = sp.get('real') or {}
            rv = r.get('viol', r.get('viol_upper_bound'))
            L.append(f"- STA {c.upper()} ({s['check']}): real {sta_cell(s)[0]} ps ({rv} failing endpoints"
                     f"{'' if 'viol' in r else ', upper bound'}); real+relay {sta_cell(s)[1]} ps; "
                     f"{'placeholder-touching' if 'viol' in ph else 'endpoints on placeholder masters'} worst "
                     f"{fmt(phw)} ps ({phv} failing); all {sta_cell(s)[2]} ps.")
            if s.get('clock_context'):
                L.append(f"  - {s['clock_context']}")
        pr = d.get('sta_prior_r25_grt') or d.get('prior_r21')
        if pr:
            L.append(f"- Prior (superseded) run: {json.dumps({x: pr[x] for x in pr if x not in ('tt', 'ff')})[:400]}")
            for c in ('tt', 'ff'):
                if isinstance(pr.get(c), dict):
                    sp = pr[c]['split']
                    nf = lambda v: 'none failing' if v is None else f'{v:+.1f}'
                    L.append(f"  - {c.upper()}: all {pr[c]['all']['wns_ps']:+.1f} ps; real {nf(sp['real']['wns_ps'])} "
                             f"({sp['real']['viol']} viol); real+relay {nf(sp['real+relay']['wns_ps'])}; placeholder-touching "
                             f"{nf(sp['placeholder_touching']['wns_ps'])} ({sp['placeholder_touching']['viol']} viol).")
                    if pr[c].get('clock_context'):
                        L.append(f"    {pr[c]['clock_context']}")
        for r in d.get('regions') or []:
            st = r.get('status')
            line = f"- Region {r.get('region', '')}: {st}"
            if r.get('drt') and str(st).startswith('done'):
                line += f"; DRT final violations {r['drt'].get('final_drc', r['drt'].get('final_violations'))}"
            wl = r.get('wirelength')
            if wl:
                line += f"; WL DRT/GRT total {wl['total_ratio']} (median {wl['median_ratio']}, p95 {wl['p95_ratio']}, {wl['nets']:,} nets)"
            sl = r.get('slack_ps') or {}
            dl = [f"{c} {v.get('delta_ps'):+.1f}" for c, v in sl.items() if isinstance(v, dict) and v.get('delta_ps') is not None]
            if dl:
                line += '; slack DRT-GRT ' + ', '.join(dl) + ' ps'
            b = r.get('boundary')
            if b and b.get('unpinned_crossing_frac') is not None:
                line += f"; boundary: {b['unpinned_crossing_frac']:.0%} of {b['nets']:,} crossings unpinned (no free track)"
            if r.get('boundary_ports'):
                line += f"; {r['boundary_ports']:,} boundary ports"
            if r.get('failure'):
                line += f" -- {r['failure']}"
            L.append(line + '.')
        cp = d.get('clock_plan') or {}
        for row in cp.get('violation_rows') or []:
            L.append(f"- Clock plan violation: {row.get('a')} -> {row.get('b')} ({row.get('cls')}) skew {row.get('skew_ps')} ps "
                     f"between regions {row.get('ra')} and {row.get('rb')} (inter-region budget {(cp.get('policy') or {}).get('inter_ps')} ps).")
        for kk in ('clock_plan', 'ir'):
            x = d.get(kk) or {}
            if x.get('status') in ('missing', 'pending') or x.get('caveat'):
                L.append(f"- {kk}: {x.get('status')}. {x.get('note') or x.get('caveat') or ''}")
        if k == 's81' and d.get('r4'):
            L.append(f"- r4 (relay fix): {d['r4']['status']}.")
        L.append('')
    L += ['## Refresh', '', '`python3 tools/die_evidence_report.py` (ssh to ot-epyc1tb and ot-epyc3; ~5-10 min, the S81',
          'endpoint reports are ~350 MB per corner). Re-run in the 15-min closure drive whenever a die chain lands.', '']
    return '\n'.join(L)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv[:1] == ['probe']:
        print(json.dumps(PROBES[argv[1]](), default=lambda o: sorted(o) if isinstance(o, set) else str(o)))
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='results/arch/die_evidence_20261008')
    ap.add_argument('--die', default='qwen,hbm,s81')
    a = ap.parse_args(argv)
    dies = a.die.split(',')
    with concurrent.futures.ThreadPoolExecutor(len(dies)) as ex:
        res = dict(zip(dies, ex.map(run_probe, dies)))
    rep = dict(schema='opentallas.die_evidence_report.v1', date=time.strftime('%Y-%m-%d %H:%M %Z'),
               basis='BRIEF.md owner steer 2026-10-07 (academic validation) + option B (TT setup / FF hold)',
               tool='tools/die_evidence_report.py', dies={})
    for d in ('qwen', 'hbm', 's81'):
        if d in res:
            r = res[d]
            for k, v in STATIC.get(d, {}).items():
                if not r.get(k) or (isinstance(r.get(k), dict) and r[k].get('status') == 'pending'):
                    r[k] = v
            rep['dies'][d] = dict(name=DIES[d]['name'], host=DIES[d]['host'], **r)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').write_text(json.dumps(rep, indent=1) + '\n')
    (out / 'README.md').write_text(readme(rep))
    print(out / 'README.md')
    return 0


if __name__ == '__main__':
    sys.exit(main())
