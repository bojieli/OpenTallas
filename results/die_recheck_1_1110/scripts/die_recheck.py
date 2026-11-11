#!/usr/bin/env python3
"""DIE-RECHECK-1 (ADVISORY, DO_NOT_COUNT): incremental die-level budget re-check of the deferred core items.

By owner rule three core-level mismatches are carried to die STA instead of stopping a core:
  (1) clock-insertion band misses (11-03, METHODOLOGY 12.3a): the die taps the core early (12.3 v5.0);
  (2) planned early taps (e.g. HBM vsN4 insertion_ps 380 vs common 250);
  (3) NEEDS_PARENT port hold (11-03): io_hold_parent receipt moves to die STA FF.
This tool sums them against the die related-pair budget (TT setup >= 0, FF hold >= 0, 12.4a / 12.25 / 11-02) for every
design of the CURRENT plan of record that has a signed view (or a NEAR-CLOSE candidate view), and appends one row per
die to a TSV.  It re-runs whenever cores sign (new signed records in the release cache) -> incremental.

Per design, from its signoff.json (core_latency.measured pin-flop insertion, checks.hold_ff, io_hold, policy):
  e_tt / e_ff   = pin-flop insertion mean - target (plan partition_types[t].clock.insertion_ps, else the die
                  clock.common_latency_ps; FF target = the sign-off's insertion_bound.ff, else x0.81).
  early tap     = the die taps the core early by e_tt (12.3 v5.0, balanced at TT); at FF the tap moves k_die * e_tt
                  (k_die = FF/TT ratio of the die clock tree; S81 routed inv2 tree 0.845, --k-die).
  xcorner       = e_ff - k_die * e_tt   (> 0: core still late at FF after the tap; < 0: early -> hold risk on its inputs)
  pess_hold     = clk_aocv.branch_pessimism (0.21 %/mm table, same region): capture branch = the core's internal tree
                  (class B, insertion_ff), launch branch = an in-band neighbour (class B, target_ff) + the die tree segment the
                  early tap removed from the core's branch (class Ainv, k_die*e_tt), distance = core diagonal.
  NOTE OWNER 12.24b (10-31): die STA gate numbers are NOMINAL (no AOCV/spice/droop): die_hold_ff is nominal (the gate
  form); die_hold_ff_aocv = die_hold_ff - pess_hold is INFO.
  port hold at die (only when checks.hold_ff is port-start dominated, i.e. NEEDS_PARENT / port_only_needs_parent, or
  a NEAR-CLOSE candidate whose hold fails):
      die_hold_ff = wns_core + (target_ff - L_vclk) - in_min + cq_ff + k_die * e_tt'
      where the core sign-off launched its inputs at L_vclk + in_min (overlay / ff_vclk_reference), the die launches
      from an in-band neighbour at target_ff + clk->q (cq_ff, --cq-ff, 25 ps: DFFHQNx1 FF, pessimistic low) and the
      die early tap e_tt' = e_tt only when the tap is applied (|e_tt| > --tap-min-ps, default 0 = always, 12.3 v5.0).
  internal hold / setup stay the core's own sign-off numbers (not re-timed here).
A row is 'below 0' when die_hold_ff < 0.  ESTIMATE: no die netlist, no routed die RC; plan budgets where no view.

Incremental: --state FILE keeps the key of the signed-view set (die, design, newest record); an unchanged set is a no-op,
so an hourly cron only appends when a core signed or a record moved.
Usage: die_recheck.py --cache CACHE.json --repo REPO --tools COORD_TOOLS [--near-close TSV] --out-dir DIR
                      [--tsv APPEND.tsv] [--k-die 0.845] [--cq-ff 25] [--hosts-ok h1,h2]
"""
import argparse
import collections
import datetime
import gzip
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

EXTRACT = r'''
import json, sys
out = {}
for p in sys.stdin.read().split():
    try:
        d = json.load(open(p))
    except Exception as e:
        out[p] = {"error": str(e)[:200]}; continue
    c = d.get("checks", {}); h = c.get("hold_ff", {}); s = c.get("setup_tt", {})
    cl = (d.get("core_latency") or {}).get("measured") or {}
    if not cl:
        cl = {k: (d.get("corners", {}).get(k, {}).get("insertion_pinflops") or {}) for k in ("tt", "ff")}
    pol = d.get("policy", {})
    out[p] = dict(name=d.get("name"), verdict=d.get("verdict"), local_verdict=d.get("local_verdict"),
                  reasons=d.get("reasons"), hold=dict(wns=h.get("wns_ps"), n=h.get("violators"), overlay=h.get("overlay"),
                  vclk=h.get("ff_vclk_reference"), port_only=h.get("port_only_needs_parent"),
                  ports=h.get("port_start_ports")), setup=dict(wns=s.get("wns_ps"), n=s.get("violators")),
                  ins=cl, bound=pol.get("insertion_bound"), band=(d.get("insertion_band") or {}).get("outside"),
                  io_hold=(d.get("io_hold") or {}).get("basis"))
print(json.dumps(out))
'''


LOCAL = set()


def ssh_extract(host, paths, timeout=600):
    if not paths:
        return {}
    if host in LOCAL:
        r = subprocess.run([sys.executable, '-I', '-c', EXTRACT], input='\n'.join(paths), capture_output=True, text=True,
                           timeout=timeout)
        return json.loads(r.stdout) if r.returncode == 0 else {p: {'error': 'local rc %d' % r.returncode} for p in paths}
    import base64
    b = base64.b64encode(EXTRACT.encode()).decode()
    cmd = ['timeout', str(timeout), 'ssh', '-o', 'ControlPath=none', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes',
           host, "python3 -I -c \"import base64;exec(base64.b64decode('%s'))\"" % b]
    r = subprocess.run(cmd, input='\n'.join(paths), capture_output=True, text=True)
    if r.returncode:
        return {p: {"error": "ssh %s rc %d %s" % (host, r.returncode, r.stderr.strip()[-200:])} for p in paths}
    return json.loads(r.stdout)


def load_plan(path):
    raw = Path(path).read_bytes()
    if path.endswith('.gz'):
        raw = gzip.decompress(raw)
    return json.loads(raw)


def parse_overlay(s):
    m = re.search(r'in_min (-?[\d.]+)', s or '')
    return float(m.group(1)) if m else None


def parse_vclk(s):
    m = re.search(r'latency_ps (-?[\d.]+)', s or '')
    return float(m.group(1)) if m else None


def candidates(recs):
    """record strings 'host:path src .. flow ..' -> [(host, path)] newest flow tag first"""
    out = []
    for i, r in enumerate(recs):
        host, path = r.split()[0].split(':', 1)
        m = re.search(r'flow (flow-(\d{8})\S*)', r)
        out.append(((m.group(2) if m else '0', i), host, path))
    return [(h, p) for _, h, p in sorted(out, reverse=True)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    ap.add_argument('--repo', required=True, help='checkout of origin/main (plans of record)')
    ap.add_argument('--tools', required=True, help='repo tools/die_plan (clk_aocv)')
    ap.add_argument('--near-close')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--tsv')
    ap.add_argument('--k-die', type=float, default=0.845)
    ap.add_argument('--cq-ff', type=float, default=25.0)
    ap.add_argument('--tap-min-ps', type=float, default=0.0)
    ap.add_argument('--hosts-ok', default='')
    ap.add_argument('--dies', default='')
    ap.add_argument('--state', help='JSON with the key of the last run: re-run only when the signed-view set changed')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--clock-note', type=json.loads, default=None, help='JSON {die: text} for the clock column')
    ap.add_argument('--local', default='', help='host aliases that are this machine (read without ssh)')
    a = ap.parse_args()
    sys.path.insert(0, a.tools)
    import clk_aocv as CA
    T = CA.load(Path(a.tools) / 'clk_aocv_table_g021.json')
    cache = json.loads(Path(a.cache).read_text())
    LOCAL.update(x for x in a.local.split(',') if x)
    hosts_ok = set(x for x in a.hosts_ok.split(',') if x)
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')

    jobs = []        # (die, design, kind, type or None, host, path, label)
    plans = {}
    for key, p in cache['plans'].items():
        die = p['die']
        if a.dies and die not in a.dies.split(','):
            continue
        plan = load_plan(str(Path(a.repo) / p['plan_src']))
        plans[die] = dict(key=key, plan=plan, src=p['plan_src'])
        for kind, tbl in (('type', p.get('signed_types') or {}), ('core', p.get('signed_designs') or {})):
            for name, recs in tbl.items():
                if not recs:
                    continue
                jobs.append((die, name, kind, name if kind == 'type' else None, candidates(recs), 'SIGNED'))
    if a.near_close and Path(a.near_close).exists():
        for ln in Path(a.near_close).read_text().splitlines():
            if ln.startswith('#') or ln.startswith('die\t'):
                continue
            f = ln.split('\t')
            if len(f) < 4 or (a.dies and f[0] not in a.dies.split(',')) or f[0] not in plans:
                continue
            path = f[3].rstrip('/')
            path = path if path.endswith('signoff.json') else path + '/signoff/signoff.json'
            jobs.append((f[0], f[1], 'near', None, [(f[2], path)], 'NEAR-CLOSE'))
    import hashlib
    # key = signed-view set + every plan file's sha: a plan event or a new sign-off re-runs, nothing else does
    psha = {d: hashlib.sha256((Path(a.repo) / v['src']).read_bytes()).hexdigest()[:12] for d, v in plans.items()}
    for d in plans:
        plans[d]['sha'] = psha[d]
    key = hashlib.sha256(json.dumps([sorted((j[0], j[1], j[4][0][0], j[4][0][1]) for j in jobs),
                                     sorted(psha.items())]).encode()).hexdigest()[:16]
    if a.state and Path(a.state).exists() and json.loads(Path(a.state).read_text()).get('key') == key and not a.force:
        print('die_recheck: signed-view set unchanged (key %s) -> nothing to do' % key)
        return
    byhost = collections.defaultdict(list)
    for j in jobs:
        for h, p in j[4]:
            if h == 'origin/main':
                byhost['@repo'].append(p)
            elif not hosts_ok or h in hosts_ok:
                byhost[h].append(p)
    got = {}
    for h, ps in sorted(byhost.items()):
        if h == '@repo':
            LOCAL.add('@repo')
            res = ssh_extract('@repo', sorted(set(str(Path(a.repo) / p) for p in ps)))
            for p in ps:
                got[('origin/main', p)] = res.get(str(Path(a.repo) / p))
            continue
        for p, v in ssh_extract(h, sorted(set(ps))).items():
            got[(h, p)] = v

    rows, per_die = [], collections.defaultdict(list)
    for die, name, kind, typ, cands, label in jobs:
        host, path = cands[0]
        v = None
        for h, p in cands:
            x = got.get((h, p))
            if x is not None and 'error' not in x:
                host, path, v = h, p, x
                break
            v = v or x
        P = plans[die]['plan']; ck = P.get('clock', {})
        if v is None or 'error' in v:
            rows.append(dict(die=die, design=name, kind=kind, label=label, host=host, path=path,
                             status='UNREAD', note=(v or {}).get('error', 'host skipped')))
            continue
        common = float(ck.get('common_latency_ps') or 250.0)
        pt = (P.get('partition_types') or {}).get(typ or '', {}) if typ else {}
        tgt_tt = float((pt.get('clock') or {}).get('insertion_ps') or common)
        early_planned = (pt.get('clock') or {}).get('early_tap_ps')
        b = v.get('bound') or {}
        tgt_ff = float(b['ff']) if b.get('ff') and float(b.get('tt') or 0) == tgt_tt else tgt_tt * 0.81
        ins = v.get('ins') or {}
        itt, iff = (ins.get('tt') or {}).get('mean'), (ins.get('ff') or {}).get('mean')
        r = dict(die=die, design=name, kind=kind, label=label, host=host, path=path, verdict=v.get('verdict'),
                 tgt_tt=tgt_tt, tgt_ff=round(tgt_ff, 2), ins_tt=itt, ins_ff=iff, early_planned=early_planned,
                 hold_wns=v['hold'].get('wns'), hold_n=v['hold'].get('n'), setup_wns=v['setup'].get('wns'))
        if itt is None or iff is None:
            r.update(status='NO_INSERTION'); rows.append(r); per_die[die].append(r); continue
        e_tt, e_ff = itt - tgt_tt, iff - tgt_ff
        tap = e_tt if abs(e_tt) > a.tap_min_ps else 0.0
        xc = e_ff - a.k_die * tap
        stages_core = max(1, round(iff / T['classes']['B']['FF']['mu_cell_ps']))
        stages_nb = max(1, round(tgt_ff / T['classes']['B']['FF']['mu_cell_ps']))
        die_seg = max(0.0, a.k_die * tap)
        launch = dict(cell_ps=tgt_ff + die_seg, net_ps=0.0,
                      stages={'B': stages_nb, 'Ainv': max(0, round(die_seg / T['classes']['Ainv']['FF']['mu_cell_ps']))})
        capture = dict(cell_ps=iff, net_ps=0.0, stages={'B': stages_core})
        dist = 400.0
        pess = CA.branch_pessimism(T, 'FF', launch, capture, dist, True, 'hold')
        r.update(e_tt=round(e_tt, 1), e_ff=round(e_ff, 1), tap_tt=round(tap, 1), xcorner_ff=round(xc, 1),
                 pess_hold=round(pess, 1), band_out=abs(e_tt) > 20 or abs(e_ff) > 20, far_out=abs(e_tt) > 40)
        h = v['hold']; reasons = ' '.join(v.get('reasons') or [])
        port = bool(h.get('port_only')) or 'io_hold_parent' in reasons or v.get('io_hold') == 'ff_hold_port_start_only'
        mixed = (not port and label == 'NEAR-CLOSE' and (h.get('wns') or 0) < 0 and bool(h.get('overlay')))
        if (port or mixed) and h.get('wns') is not None:
            m = parse_overlay(h.get('overlay')); L = parse_vclk(h.get('vclk'))
            if m is not None and L is not None:
                dh = h['wns'] + (tgt_ff - L) - m + a.cq_ff + a.k_die * tap      # NOMINAL (OWNER 12.24b gate form)
                if port:
                    r.update(port_hold=True, in_min=m, l_vclk=L, die_hold_ff=round(dh, 1),
                             die_hold_ff_aocv=round(dh - pess, 1))
                else:   # candidate whose failing hold is not flagged port-only: upper bound of what die STA recovers
                    r.update(port_hold=False, in_min=m, l_vclk=L, die_hold_ff_ub=round(dh, 1))
        r['status'] = 'OK'
        rows.append(r); per_die[die].append(r)

    (out_dir / 'die_recheck_rows.json').write_text(json.dumps(rows, indent=1))
    summ = {}
    for die in sorted(plans):
        R = [r for r in per_die[die] if r.get('status') == 'OK']
        ph = [r for r in R if 'die_hold_ff' in r]
        neg = sorted([r for r in ph if r['die_hold_ff'] < 0], key=lambda r: r['die_hold_ff'])
        neg_aocv = [r for r in ph if r['die_hold_ff_aocv'] < 0]
        neg_ep = sum(int(r.get('hold_n') or 0) for r in neg)
        band = [r for r in R if r.get('band_out')]
        far = sorted([r for r in R if r.get('far_out')], key=lambda r: -abs(r['e_tt']))
        xc = sorted(R, key=lambda r: r['xcorner_ff'])
        unread = [r for r in rows if r['die'] == die and r.get('status') == 'UNREAD']
        summ[die] = dict(plan=plans[die]['src'], plan_sha=plans[die]['sha'], designs=len(R), unread=len(unread), band_out=len(band), far_out=len(far),
                         port_hold_designs=len(ph), port_hold_below0=len(neg), port_hold_below0_aocv=len(neg_aocv),
                         port_hold_below0_core_viol_endpoints=neg_ep,
                         worst_port_hold=(neg[0]['design'], neg[0]['die_hold_ff']) if neg else
                         ((min(ph, key=lambda r: r['die_hold_ff'])['design'], min(r['die_hold_ff'] for r in ph)) if ph else None),
                         worst_xcorner=(xc[0]['design'], xc[0]['xcorner_ff']) if xc else None,
                         max_early_tap=(far[0]['design'], far[0]['e_tt']) if far else None,
                         below0=[(r['design'], r['die_hold_ff'], r['die_hold_ff_aocv'], int(r.get('hold_n') or 0), r['e_tt'],
                                  r['label']) for r in neg[:14]],
                         far=[(r['design'], r['e_tt'], r['e_ff']) for r in far[:12]])
    (out_dir / 'die_recheck_summary.json').write_text(json.dumps(dict(generated=now, k_die=a.k_die, cq_ff=a.cq_ff,
                                                                      dies=summ), indent=1))
    if a.tsv:
        new = not Path(a.tsv).exists()
        with open(a.tsv, 'a') as f:
            if new:
                f.write('# DIE-RECHECK (DIE-RECHECK-1, ADVISORY, DO_NOT_COUNT): die-level sum of deferred core items '
                        '(insertion band / early taps / NEEDS_PARENT port hold) per plan of record; tools die_recheck.py\n')
                f.write('time\tdie\tplan\tdesigns_read\tunread\tband_out\tfar_out_40\tmax_early_tap\tworst_xcorner_ff\t'
                        'port_hold_designs\tport_hold_below0_nominal\tport_hold_below0_aocv_info\tworst_port_hold_ff_nominal\t'
                        'clock\tnote\n')
            for die, s in summ.items():
                f.write('\t'.join(str(x) for x in (now, die, s['plan'], s['designs'], s['unread'], s['band_out'],
                                                   s['far_out'], s['max_early_tap'], s['worst_xcorner'],
                                                   s['port_hold_designs'], s['port_hold_below0'],
                                                   s['port_hold_below0_aocv'], s['worst_port_hold'],
                                                   (a.clock_note or {}).get(die, '-'),
                                                   'ESTIMATE k_die %.3f cq_ff %.0f' % (a.k_die, a.cq_ff))) + '\n')
    if a.state:
        st = Path(a.state)
        prev = json.loads(st.read_text()).get('summary', {}) if st.exists() else {}
        F = ('plan_sha', 'designs', 'unread', 'far_out', 'max_early_tap', 'worst_xcorner', 'port_hold_designs',
             'port_hold_below0', 'port_hold_below0_aocv', 'worst_port_hold')
        for die, s in summ.items():
            p = prev.get(die)
            if p is None:
                print('DELTA %s: first run' % die)
                continue
            ch = ['%s %s -> %s' % (f, json.dumps(p.get(f)), json.dumps(s.get(f))) for f in F
                  if json.dumps(p.get(f)) != json.dumps(s.get(f))]
            print('DELTA %s: %s' % (die, '; '.join(ch) if ch else 'no change'))
        st.write_text(json.dumps(dict(key=key, time=now, summary=summ)))
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
