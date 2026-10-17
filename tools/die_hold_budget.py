#!/usr/bin/env python3
"""Die-wide boundary hold budget: shared post-STA link classifier for every die flow (DIE-FLOW 2026-10-17).

Rule: results/arch/boundary_hold_budget_1016/RULE.md (FLOW-HOLD, owner-approved 2026-10-16 ~22:00), section 5:

    launch_min(o) + w_min + [relay stages] - delta(send, recv) - H(i) - U  >= 0      (FF, U = 25 ps once per link)

  D1  die FF STA >= 0 on the BOUND tiles' ETMs (sender launch-min = the ETM clk->out min arc, never a 65 ps
      placeholder; an unbuilt placeholder launches at C = 25 ps and its links are hold-DIAGNOSTIC);
  D2  neighbour skew |delta| <= 80 ps on every communicating pair (a link over 80 is a FAIL class, never padded);
  D3  a hold shortfall is fixed at die level: in a relay station on the link (hold-delay station variant) or a
      die-net hold cell -- never by re-padding the tile and never by relaxing U.

Input: an OpenSTA FF min report in -format full_clock_expanded (one path per endpoint), written in the die STA
session by tcl_dump().  For every path the parser recovers, from the report's own lines (ideal latencies,
propagated trees and SPEF-annotated clocks alike):
    L     launch clock arrival at the sender's clock pin      launch_min = arrival(sender data pin) - L
    Cap   capture clock arrival at the receiver's clock pin   delta = Cap - L
    w     data arrival(endpoint) - arrival(sender data pin)   (die wire + relay / repeater cells)
    H     library hold time;  U = clock uncertainty line;  slack as reported
A link is (sender instance, receiver instance); a link class is (sender master, receiver master).

    die_hold_budget.py classify --report hold_links_ff.rpt --out hold_budget.json \
        [--masters masters.json] [--relay-re REGEX] [--paths-cap N] [--design NAME]

masters.json: {"diagnostic": [master, ...], "real": [master, ...], "relay": [master, ...], "diagnostic_all": reason}
(any key optional; diagnostic_all = the whole run is hold-diagnostic, e.g. ideal SYNTH_IDEAL_R0 clocks);
diagnostic = placeholder / interim / SYNTH / ASSUMED views: their links' hold verdict is not accepted (RULE D2 note).
Verdict: PASS only with 0 hold violators, 0 skew FAILs, U >= 25 on every path (U > 25 counted: the flows set 25), complete coverage (the dump was not
truncated at --paths-cap) and no diagnostic link; else FAIL / DIAGNOSTIC (never masked).
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

U_PS = 25.0
C_PS = 25.0
SKEW_PS = 80.0
SCHEMA = 'opentallas.die_hold_budget.v1'
RULE = 'results/arch/boundary_hold_budget_1016/RULE.md'
# default relay-station masters of the three designs (S81 dsfd_rly_* / stations, HBM hbfd_rly_*, Qwen qfd_rly / cst
# corridor stations and qkd relays rlys_*)
RELAY_RE = r'(^|_)(rly|rlys|stn|hstn[hv]?|sstn|cst)(_|$)'

_PIN = re.compile(r'^\s*(-?\d+(?:\.\d+)?\s+)?(-?\d+(?:\.\d+)?)\s+([\^v])\s+(\S+)\s+\((\S+)\)\s*$')
_DESC = re.compile(r'^\s*(-?\d+(?:\.\d+)?)?\s+(-?\d+(?:\.\d+)?)\s+(?:[\^v]\s+)?(.+?)\s*$')


def tcl_dump(path, paths=200000, corner=None):
    """the FF min dump line for a die STA session (one path per endpoint, every clock group)"""
    c = f' -corner {corner}' if corner else ''
    return (f'report_checks{c} -path_delay min -group_path_count {int(paths)} -endpoint_path_count 1 '
            f'-format full_clock_expanded -digits 1 > {path}')


def _inst(pin):
    return pin.rsplit('/', 1)[0] if '/' in pin else ''


def parse(text):
    """-> list of path dicts (see module doc); paths the parser cannot read are returned with 'error'"""
    out = []
    for blk in re.split(r'(?m)^(?=Startpoint: )', text):
        if not blk.startswith('Startpoint: '):
            continue
        p = _parse_block(blk)
        if p:
            out.append(p)
    return out


def _parse_block(blk):
    lines = blk.splitlines()
    sp = re.match(r'Startpoint: (\S+) \((.*)\)', lines[0])
    ep = next((re.match(r'Endpoint: (\S+) \((.*)\)', l) for l in lines[1:4] if l.startswith('Endpoint: ')), None)
    if not sp or not ep:
        return None
    r = dict(start=sp.group(1), start_kind='port' if 'port' in sp.group(2) else 'reg',
             end=ep.group(1), end_kind='port' if 'port' in ep.group(2) else 'reg')
    try:
        i_arr = next(i for i, l in enumerate(lines) if l.strip().endswith('data arrival time'))
        i_req = next(i for i, l in enumerate(lines) if i > i_arr and l.strip().endswith('data required time'))
        slack_l = next(l for l in lines if re.search(r'slack \((VIOLATED|MET)', l))
    except StopIteration:
        r['error'] = 'incomplete path block'
        return r
    r['slack'] = float(slack_l.split()[0])
    r['arrival'] = float(lines[i_arr].split()[0])
    launch = lines[:i_arr]
    cap = lines[i_arr + 1:i_req + 1]
    lp = [(k, _PIN.match(l)) for k, l in enumerate(launch)]
    lp = [(k, m) for k, m in lp if m]
    # sender: first consecutive pin pair of the start instance = (clock pin, data pin)
    L = out_t = None
    if r['start_kind'] == 'reg':
        for (k0, m0), (k1, m1) in zip(lp, lp[1:]):
            if _inst(m0.group(4)) == r['start'] and _inst(m1.group(4)) == r['start']:
                L, out_t = float(m0.group(2)), float(m1.group(2))
                r['start_master'], r['start_clock_pin'], r['start_pin'] = m1.group(5), m0.group(4), m1.group(4)
                break
    else:
        for k, l in enumerate(launch):
            if l.strip().endswith('input external delay'):
                m = _DESC.match(launch[k - 1]) if k else None
                L = float(m.group(2)) if m else 0.0
        port = next((m for _, m in lp if m.group(5) == 'in'), None)
        if port:
            out_t = float(port.group(2))
            r['start_master'], r['start_pin'] = 'PORT', port.group(4)
    if L is None or out_t is None:
        r['error'] = 'sender clock/data pin not found'
        return r
    # receiver: last pin line before 'library hold time'; U / CRPR above it are subtracted
    unc = crpr = 0.0
    H = Cap = net = None
    pre = 0.0           # uncertainty + CRPR printed above the capture clock pin (ideal-clock layout)
    for l in cap:
        s = l.strip()
        m = _PIN.match(l)
        d = _DESC.match(l)
        if s.endswith('clock uncertainty'):
            unc = float(d.group(1)); pre += unc if Cap is None else 0.0
        elif s.endswith('clock reconvergence pessimism'):
            crpr = float(d.group(1)); pre += crpr if Cap is None else 0.0
        elif re.search(r'(library|clock gating) hold time$', s):
            H = float(d.group(1))
        elif m and H is None:
            Cap = float(m.group(2)) - pre
            r['end_master'], r['end_clock_pin'] = m.group(5), m.group(4)
        elif s.endswith('clock network delay (propagated)') or s.endswith('clock network delay (ideal)'):
            net = float(d.group(2))
    if Cap is None:
        Cap = net
    if r['end_kind'] == 'port':
        r['end_master'] = 'PORT'
    if Cap is None:
        r['error'] = 'capture clock not found'
        return r
    r.update(L=L, Cap=Cap, delta=round(Cap - L, 3), launch_min=round(out_t - L, 3), wire=round(r['arrival'] - out_t, 3),
             hold=H, U=unc, crpr=crpr)
    return r


def classify(paths, masters=None, relay_re=RELAY_RE, paths_cap=None, design=None, skew_ps=SKEW_PS, u_ps=U_PS):
    masters = masters or {}
    diag = set(masters.get('diagnostic', ()))
    relay_set = set(masters.get('relay', ()))
    rr = re.compile(relay_re) if relay_re else None
    is_relay = lambda m: m in relay_set or bool(rr and m and rr.search(m))
    links = {}
    errors = [p for p in paths if 'error' in p]
    good = [p for p in paths if 'error' not in p]
    u_bad = u_above = 0
    for p in good:
        if p['U'] < u_ps - 0.05:
            u_bad += 1           # under-constrained link: FAIL
        elif p['U'] > u_ps + 0.05:
            u_above += 1         # pessimistic (e.g. Qwen region clock-OCV pairs 25 + OCV): reported, not a FAIL
        key = (p['start'], p['end'] if p['end_kind'] == 'reg' else p['end'])
        lk = links.get(key)
        if lk is None:
            lk = links[key] = dict(sender=p['start'], receiver=p['end'], sender_master=p.get('start_master'),
                                   receiver_master=p.get('end_master'), bits=0, worst_slack=p['slack'],
                                   delta=p['delta'], max_abs_delta=abs(p['delta']), launch_min=p['launch_min'],
                                   min_wire=p['wire'], hold=p['hold'], U=p['U'])
        lk['bits'] += 1
        lk['max_abs_delta'] = max(lk['max_abs_delta'], abs(p['delta']))
        lk['min_wire'] = min(lk['min_wire'], p['wire'])
        lk['launch_min'] = min(lk['launch_min'], p['launch_min'])
        if p['slack'] < lk['worst_slack']:
            lk.update(worst_slack=p['slack'], delta=p['delta'], hold=p['hold'], U=p['U'])
    by_fix = defaultdict(list)
    cls = defaultdict(lambda: dict(links=0, bits=0, violators=0, skew_fail=0, max_abs_delta=0.0, worst_slack=None,
                                   min_launch_min=None))
    for lk in links.values():
        sm, rm = lk['sender_master'], lk['receiver_master']
        diagnostic = sm in diag or rm in diag
        port = 'PORT' in (sm, rm)
        lk['skew_ok'] = port or lk['max_abs_delta'] <= skew_ps   # a die top port has no sender/receiver clock pair
        if lk['worst_slack'] >= 0:
            fix = 'PASS'
        elif port:
            fix = 'PORT_HOLD'                # die top port (external min delay): not a die link, reported, FAILs
        elif not lk['skew_ok']:
            fix = 'SKEW_GT80'                # D2: a clock fix (regional root / neighbour matching), not a hold cell
        elif diagnostic:
            fix = 'DIAGNOSTIC_PLACEHOLDER'   # placeholder / SYNTH / ASSUMED sender or receiver: verdict not accepted
        elif is_relay(sm) or is_relay(rm):
            fix = 'RELAY_STATION'            # D3: hold-delay variant of the station on the link
        else:
            fix = 'DIE_NET_HOLD_CELL'        # D3: die-net hold cell on a direct tile-to-tile hop
        lk['fix'] = fix
        lk['diagnostic'] = diagnostic
        lk['demand_ps'] = round(max(0.0, -lk['worst_slack']), 1)
        by_fix[fix].append(lk)
        c = cls[f'{sm}->{rm}']
        c['links'] += 1; c['bits'] += lk['bits']; c['violators'] += lk['worst_slack'] < 0
        c['skew_fail'] += not lk['skew_ok']; c['max_abs_delta'] = max(c['max_abs_delta'], lk['max_abs_delta'])
        c['worst_slack'] = lk['worst_slack'] if c['worst_slack'] is None else min(c['worst_slack'], lk['worst_slack'])
        c['min_launch_min'] = lk['launch_min'] if c['min_launch_min'] is None else min(c['min_launch_min'], lk['launch_min'])
        c['diagnostic'] = c.get('diagnostic', False) or diagnostic
    truncated = bool(paths_cap) and len(paths) >= paths_cap
    skew_fail = sum(1 for lk in links.values() if not lk['skew_ok'])
    viol = sum(1 for lk in links.values() if lk['worst_slack'] < 0)
    ndiag = sum(1 for lk in links.values() if lk['diagnostic'])
    placeholder_launch = sorted({lk['sender_master'] for lk in links.values() if lk['sender_master'] in diag})
    if viol or skew_fail or u_bad or errors:
        verdict = 'FAIL'
    elif truncated or ndiag or masters.get('diagnostic_all'):
        verdict = 'DIAGNOSTIC'
    else:
        verdict = 'PASS'
    worst = lambda xs: sorted(xs, key=lambda x: x['worst_slack'])[:50]
    return dict(schema=SCHEMA, rule=RULE, design=design, verdict=verdict,
                params=dict(U_ps=u_ps, C_ps=C_PS, skew_limit_ps=skew_ps, relay_re=relay_re, paths_cap=paths_cap),
                coverage=dict(paths=len(paths), parsed=len(good), parse_errors=len(errors), links=len(links),
                              truncated=truncated,
                              note='skew/hold judged on the dumped endpoints; truncated -> DIAGNOSTIC (raise --paths-cap)'),
                counts=dict(hold_violating_links=viol, skew_fail_links=skew_fail, diagnostic_links=ndiag,
                            paths_with_U_below_25=u_bad, paths_with_U_above_25=u_above, by_fix={k: len(v) for k, v in sorted(by_fix.items())},
                            demand_ps_by_fix={k: round(sum(x['demand_ps'] for x in v), 1) for k, v in sorted(by_fix.items())
                                              if k != 'PASS'}),
                placeholder_senders=placeholder_launch, diagnostic_all=masters.get('diagnostic_all'),
                link_classes=dict(sorted(cls.items(), key=lambda kv: (kv[1]['worst_slack'] if kv[1]['worst_slack'] is not None else 0))),
                worst_links={k: worst(v) for k, v in sorted(by_fix.items()) if k != 'PASS'},
                skew_fail_links=sorted((lk for lk in links.values() if not lk['skew_ok']),
                                       key=lambda x: -x['max_abs_delta'])[:50],
                parse_errors=[dict(start=e['start'], end=e['end'], error=e['error']) for e in errors[:20]])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('classify')
    c.add_argument('--report', required=True, type=Path)
    c.add_argument('--out', required=True, type=Path)
    c.add_argument('--masters', type=Path, help='{"diagnostic": [...], "real": [...], "relay": [...]}')
    c.add_argument('--qwen-views', type=Path, help='Qwen die libs views.json (tools/qwen_tp8/die_sta_libs.py): assumed '
                   'single-flop masters -> diagnostic, real ETM / hard macro -> real (instead of --masters)')
    c.add_argument('--relay-re', default=RELAY_RE)
    c.add_argument('--paths-cap', type=int, default=None, help='the dump -group_path_count (truncation detection)')
    c.add_argument('--design', default=None)
    a = ap.parse_args(argv)
    m = json.loads(a.masters.read_text()) if a.masters else {}
    if a.qwen_views:
        v = json.loads(a.qwen_views.read_text())
        m = dict(m, diagnostic=sorted(set(m.get('diagnostic', ())) | set(v.get('assumed', ()))),
                 real=sorted(set(v.get('real', {})) | set(v.get('hard_macro', {}))))
    rec = classify(parse(a.report.read_text()), m, a.relay_re, a.paths_cap, a.design)
    rec['report'] = str(a.report)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(f"OT_HOLD_BUDGET {rec['verdict']} links={rec['coverage']['links']} viol={rec['counts']['hold_violating_links']} "
          f"skew_fail={rec['counts']['skew_fail_links']} diag={rec['counts']['diagnostic_links']} "
          f"by_fix={json.dumps(rec['counts']['by_fix'], separators=(',', ':'))}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
