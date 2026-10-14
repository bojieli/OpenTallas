#!/usr/bin/env python3
"""Per-pair die hop audit (owner 2026-10-13): evaluate the die statement (tools/hier_contract/pair_check.py) for every
bundle between two placed instances of a die case, with each side's real view numbers and the real pin-to-pin length,
and name the cheapest fix of every failing bundle.

  table   pinreg_pairs.py table --masters M.json --out view_timing.json [--merge OLD.json]
          M.json: {master: view dir | {"view": dir, "binding": "..."}}.  Reads the view's *_tt / *_ff Liberty ETMs and
          insertion.json (the boundary-register clock arrival; a clock pin without it is recorded "R: null" and its
          pairs are reported, never estimated).
  s81     pinreg_pairs.py s81 --plan plan.json.gz --table T.json --audit s81_audit.json --out OUT.json --md OUT.md
          plan = tools/s81/c5diag_v15_dump.py (insts + every bus hop with per-bit pin-to-pin lengths)
  qwen    pinreg_pairs.py qwen --plan plan.json.gz --table T.json --audit qwen_audit.json --out OUT.json --md OUT.md
          plan = tools/qwen_tp8/pairs_plan_dump.py (same format; the case's LEF pins are all INOUT, so the driver comes
          from the generator's bus list).  Any parent floorplan dumped in this format is judged the same way.
"""
import argparse
import collections
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pair_check as P          # noqa: E402

ROOT = P.ROOT
RESET_CLS = ('reset', 'col_reset', 'reset_tree')


# ----------------------------------------------------------------------------------------------- view -> timing table
def extract(view, binding=None):
    import pinreg_audit as A
    libs = A.corner_libs(view)
    if 'ff' not in libs or not ('tt' in libs or 'ss' in libs):
        return None
    sc = 'tt' if 'tt' in libs else 'ss'
    ij = ROOT / view / 'insertion.json'
    ins = json.loads(ij.read_text()) if ij.exists() else None
    L = {c: A.parse_lib(libs[c]) for c in (sc, 'ff')}
    refs = {c: A.clock_refs(L[c], ins, c if c != 'ss' else 'ss') for c in (sc, 'ff')}
    clocks = {}
    for name, p in L[sc]['pins'].items():
        if not (p['clock'] or name in refs[sc]):
            continue
        r, rf = refs[sc].get(name), refs['ff'].get(name)
        meas = bool(r) and r['src'] == 'insertion.json boundary mean'
        tree = bool(r)
        clocks[name] = dict(R_tt=round(r['rise'], 1) if meas else (None if tree else 0.0),
                            R_ff=round(rf['rise'], 1) if meas and rf else (None if tree else 0.0),
                            spread=round(r['bmax'] - r['bmin'], 1) if meas else None, n=r['n'] if meas else None,
                            src='insertion.json' if meas else ('NOT MEASURED (lib tree arcs %.1f..%.1f)' % (r['min'], r['max']) if tree
                                                                else 'no clock tree in the view (pin = register clock)'))
    buses = collections.OrderedDict()
    cout = {}

    def arc(bus, d, clk, edge):
        b = buses.setdefault(bus, dict(dir=d, bits=0, arcs=[]))
        for a in b['arcs']:
            if a['clk'] == clk and a['edge'] == edge:
                return a
        a = dict(clk=clk, edge=edge, O=None, l=None, S=None, h=None)
        b['arcs'].append(a)
        return a
    mx = lambda x, y: y if x is None else max(x, y)
    mn = lambda x, y: y if x is None else min(x, y)
    for c in (sc, 'ff'):
        for name, p in L[c]['pins'].items():
            if name in clocks or p['dir'] not in ('input', 'output', 'inout'):
                continue
            bus = A.bus_of(name)
            et = collections.defaultdict(set)
            for typ, rel, v in p['arcs']:
                if typ in ('rising_edge', 'falling_edge') and rel:
                    et[rel].add(typ)
            fwd = {rel for rel, s in et.items() if len(s) == 2} if p['dir'] == 'output' else set()
            if c == sc:
                buses.setdefault(bus, dict(dir=p['dir'], bits=0, arcs=[]))['bits'] += 1
            for typ, rel, v in p['arcs']:
                typ = typ or ''
                if typ in ('rising_edge', 'falling_edge') and rel in fwd:
                    co = cout.setdefault(bus, dict(clk=rel, tt={}, ff={}))
                    for tbl, y in (('cell_rise', 'r'), ('cell_fall', 'f')):
                        if v.get(tbl):
                            k = typ[0] + y
                            lo_hi = co['tt' if c == sc else 'ff'].get(k)
                            x = v[tbl][0]
                            co['tt' if c == sc else 'ff'][k] = [round(min(x, lo_hi[0]) if lo_hi else x, 1),
                                                                 round(max(x, lo_hi[1]) if lo_hi else x, 1)]
                elif typ in ('rising_edge', 'falling_edge') and rel:
                    first = [v[k][0] for k in ('cell_rise', 'cell_fall') if v.get(k)]
                    if first:
                        a = arc(bus, p['dir'], rel, typ[0])
                        if c == sc:
                            a['O'] = round(mx(a['O'], max(first)), 1)
                        else:
                            a['l'] = round(mn(a['l'], min(first)), 1)
                elif typ.startswith(('setup_', 'hold_')) and rel:
                    vals = [x for k in ('rise_constraint', 'fall_constraint') for x in v.get(k, [])]
                    if vals:
                        a = arc(bus, p['dir'], rel, 'r' if typ.endswith('rising') else 'f')
                        if typ.startswith('setup') and c == sc:
                            a['S'] = round(mx(a['S'], max(vals)), 1)
                        elif typ.startswith('hold') and c == 'ff':
                            a['h'] = round(mx(a['h'], max(vals)), 1)
    for bus, co in cout.items():
        # an ETM lists both senses of a clock pass-through (one of them a half-period image of the other or a
        # mixed-edge artifact); the hardware sense is the one whose two transitions take the same, positive time
        def gap(k1, k2):
            t = co['tt']
            return abs(t[k1][1] - t[k2][1]) if k1 in t and k2 in t and min(t[k1][0], t[k2][0]) >= 0 else 1e9
        inv, buf = gap('rf', 'fr'), gap('rr', 'ff')
        co['sense'] = None if min(inv, buf) >= 1e9 else ('inv' if inv < buf else 'buf')
    return dict(view=view, binding=binding, cell=L[sc]['cell'], setup_corner=sc, clocks=clocks,
                buses={k: v for k, v in buses.items() if v['arcs']}, clock_out=cout,
                pins_without_arc=sorted(k for k, v in buses.items() if not v['arcs'] and k not in cout and k not in ('VDD', 'VSS'))[:40])


def cmd_table(a):
    spec = json.loads(Path(a.masters).read_text())
    out = json.loads(Path(a.merge).read_text())['masters'] if a.merge else {}
    cache = {}
    miss = []
    for m, v in sorted(spec.items()):
        view, how = (v, None) if isinstance(v, str) else (v.get('view'), v.get('binding') or v.get('how'))
        if not view:
            continue
        if view not in cache:
            cache[view] = extract(view, how)
        if cache[view] is None:
            miss.append(m)
            continue
        out[m] = dict(cache[view], binding=how)
    import pinreg_audit as A
    rec = dict(schema='opentallas.pair_timing.v1', source_commit=A.git('rev-parse', '--short=9', 'HEAD').strip(),
               tool='tools/hier_contract/pinreg_pairs.py table',
               note='O / S at the setup corner (TT), l / h at FF, raw ETM arcs from the clock pin, worst bit of the bus; '
                    'R = insertion.json boundary mean per clock pin (null = not measured: such pairs are reported, not judged)',
               masters=out)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=0, separators=(',', ':')) + '\n')
    un = sorted(m for m, v in out.items() if any(c['R_tt'] is None for c in v['clocks'].values()))
    print(f'table: {len(out)} masters, {len(cache)} views; no corner libs: {miss}; clock pins without a measured R: {un}')


# ------------------------------------------------------------------------------------------------------ die readers
def read_plan(plan):
    """plan.json(.gz): insts [name, master, x, y, w, h, orient, kind, region]; hops [bus, cls, bits, drv, dport, load,
    lport, first, last, min um, max um] (driver first); optional clock_nets {bus: [[inst, port], ...]} = leaf nets of a
    die clock tree without a die-level driver (their domain: the bus name without a regional suffix _r<k> / _<quadrant>)."""
    p = json.load(gzip.open(plan) if str(plan).endswith('.gz') else open(plan))
    ins = {i[0]: i for i in p['insts']}
    hops, drv, cnet, resets = [], {}, {}, 0
    for bid, cls, bits, da, dp, li, lp, first, last, lmin, lmax in p['hops']:
        if cls in P.CLOCK_CLS:
            drv[(li, P.bus_of(lp))] = (da, P.bus_of(dp), lmax, bid)
    for bid, eps in (p.get('clock_nets') or {}).items():
        dom = re.sub(r'_r\d+$', '', bid)
        for i, port in eps:
            cnet[(i, P.bus_of(port))] = dom
    for bid, cls, bits, da, dp, li, lp, first, last, lmin, lmax in p['hops']:
        if cls in P.CLOCK_CLS:
            continue
        if cls in RESET_CLS:
            resets += 1
            continue
        if cls == 'constant':
            continue
        if P.RESET_PIN.search(P.bus_of(lp)):
            resets += 1
            continue
        hops.append(dict(net=bid, cls=cls, bits=bits, a=(da, ins[da][1], dp), b=(li, ins[li][1], lp), um=lmax))
    master_of = {k: v[1] for k, v in ins.items()}
    meta = dict(source=str(plan), instances=len(ins), clock_pins_driven=len(drv), clock_pins_on_tree_nets=len(cnet), reset_hops_skipped=resets,
                measure=p.get('measure') or 'per-bit pin-to-pin Manhattan (LEF pin rects), worst bit of the bus')
    return meta, hops, master_of, drv, cnet


# ------------------------------------------------------------------------------------------------------- evaluation
def gen(n):
    return re.sub(r'\d+', '#', n)


def evaluate(a, meta, hops, master_of, drv, cnet):
    table = P.load_table(a.table)
    die = P.Die(table, master_of, drv, cnet)
    cls_o, cls_s = P.relay_class(table, a.relay) if a.relay else (None, None)
    audit = {}
    if a.audit:
        for t in json.loads(Path(a.audit).read_text())['tiles']:
            audit[t['cell']] = t
    cnt = collections.Counter()
    bits = collections.Counter()
    rows = {}
    tiles = collections.defaultdict(lambda: dict(hops=0, real=0, fail=0, hold=0, pass_=0, cross=0, ne=0, pinreg=collections.Counter(),
                                                  relay=0, replan=0, worst_setup=None, worst_hold=None, unmeasured=0, bound=collections.Counter()))
    unmeasured = collections.Counter()
    for h in hops:
        ma, mb = h['a'][1], h['b'][1]
        r = P.check(die, h)
        if r['model'] == 'UNMEASURED':
            unmeasured[r['unmeasured']] += 1
        st = r['status']
        f = None
        if st == 'fail' and r['model'] in ('TREE',):
            f = P.fix(r, h['um'], cls_o, cls_s, a.replan_um)
        elif st == 'fail' and r['model'] == 'DEFAULT':
            f = dict(fix='relay', relays=1, pinreg=[], cycles=1, excess_um=round(h['um'] - P.DEFAULT_UM, 1)) \
                if h['um'] - P.DEFAULT_UM > a.replan_um else dict(fix='replan', relays=0, pinreg=[], cycles=0, excess_um=round(h['um'] - P.DEFAULT_UM, 1))
        elif st == 'fail':
            f = dict(fix='link', relays=None, pinreg=[], cycles=None, note='forwarded-clock link: re-time the pair (see row)')
        elif st == 'hold' and r['model'] == 'FWD' and abs(r.get('window', 0) - P.T_PS) < 1:
            # the receiver samples on the very edge that launches (full-cycle window, zero-cycle hold): capture on the
            # opposite edge in the receiving tile (as the stations do), or hold the data at its pin by -hold_ps
            f = dict(fix='edge', relays=0, pinreg=['dst'], cycles=0, need_ps=round(-r['hold_ps'], 1))
        key = (h['cls'], gen(ma), gen(P.bus_of(h['a'][2])), gen(mb), gen(P.bus_of(h['b'][2])), r['model'], r['real'])
        cnt['bind:' + r.get('bind', 'exact')] += r['real'] > 0 and r['status'] in ('pass', 'fail', 'hold')
        row = rows.setdefault(key, dict(cls=h['cls'], src=gen(ma), src_pin=key[2], dst=gen(mb), dst_pin=key[4],
                                        model=r['model'], real_ends=r['real'], bind=r.get('bind', 'exact') if r['real'] else None, hops=0, bits=0, max_um=None, status=collections.Counter(),
                                        worst_setup_ps=None, worst_hold_ps=None, reach_um=None, o=None, s=None, fixes=collections.Counter(),
                                        cycles=0, example=None, masters=set()))
        row['hops'] += 1
        row['bits'] += h['bits']
        row['status'][st] += 1
        row['masters'] |= {ma, mb}
        if h['um'] is not None:
            row['max_um'] = h['um'] if row['max_um'] is None else max(row['max_um'], h['um'])
        for k, src in (('worst_setup_ps', 'setup_ps'), ('worst_hold_ps', 'hold_ps'), ('reach_um', 'reach_um')):
            if r.get(src) is not None and (row[k] is None or r[src] < row[k]):
                row[k] = r[src]
                if k == 'worst_setup_ps':
                    row['o'], row['s'] = r.get('o'), r.get('s')
                    row['example'] = dict(net=h['net'], a='.'.join(h['a'][::2]), b='.'.join(h['b'][::2]), um=h['um'],
                                          **{x: r[x] for x in ('avail', 'skew', 'window', 'sense', 'l', 'h', 'clock_um') if x in r})
        if f:
            lab = f['fix'] + (':' + '+'.join(f['pinreg']) if f.get('pinreg') else '') + (f" x{f['relays']}" if f.get('relays') else '')
            row['fixes'][lab] += 1
            row['cycles'] = max(row['cycles'], f.get('cycles') or 0)
            row.setdefault('fix_example', f)
        cnt[(r['real'], st)] += 1
        bits[(r['real'], st)] += h['bits']
        cnt['model:' + r['model']] += 1
        for m, sidename in ((ma, 'src'), (mb, 'dst')):
            if m not in table:
                continue
            t = tiles[m]
            t['hops'] += 1
            if st in ('fail', 'hold'):
                t['bound'][r.get('bind', 'exact')] += 1
            t['real'] += r['real'] == 2
            if st == 'fail':
                t['fail'] += 1
                if f and f['fix'] == 'pinreg' and sidename in f['pinreg']:
                    t['pinreg']['out' if sidename == 'src' else 'in'] += 1
                elif f and f['fix'] == 'relay':
                    t['relay'] += 1
                elif f and f['fix'] == 'replan':
                    t['replan'] += 1
            elif st == 'hold' and f and f['fix'] == 'edge' and sidename == 'src':
                t['pass_'] += 1          # the sender of a forwarded link is not the cause of the receiver's capture edge
            elif st == 'hold':
                t['hold'] += 1
                if f and f['fix'] == 'edge' and sidename == 'dst':
                    t['pinreg']['capture-edge'] += 1
            elif st == 'pass':
                t['pass_'] += 1
            elif st == 'cross':
                t['cross'] += 1
            else:
                t['ne'] += 1
                t['unmeasured'] += r['model'] == 'UNMEASURED'
            if r.get('setup_ps') is not None:
                t['worst_setup'] = r['setup_ps'] if t['worst_setup'] is None else min(t['worst_setup'], r['setup_ps'])
            if r.get('hold_ps') is not None and not (f and f['fix'] == 'edge' and sidename == 'src'):
                t['worst_hold'] = r['hold_ps'] if t['worst_hold'] is None else min(t['worst_hold'], r['hold_ps'])
    out_rows = []
    for row in rows.values():
        row['status'] = dict(row['status'])
        row['fixes'] = dict(row['fixes'])
        row['masters'] = sorted(row['masters'])[:6]
        out_rows.append(row)
    out_rows.sort(key=lambda r_: (-(r_['status'].get('fail', 0) + r_['status'].get('hold', 0)), r_['worst_setup_ps'] if r_['worst_setup_ps'] is not None else 1e9))
    # ---- totals by fix class
    fixc = collections.OrderedDict((k, dict(pair_classes=0, hops=0, bits=0)) for k in ('relay', 'pinreg', 'replan', 'edge', 'link', 'none', 'hold_pad'))
    for row in out_rows:
        for lab, n in row['fixes'].items():
            k = lab.split(':')[0].split(' ')[0]
            fixc[k]['pair_classes'] += 1
            fixc[k]['hops'] += n
            fixc[k]['bits'] += n * (row['bits'] // max(1, row['hops']))
        nh = row['status'].get('hold', 0) - sum(n for lab, n in row['fixes'].items() if lab.startswith('edge'))
        if nh > 0:
            fixc['hold_pad']['pair_classes'] += 1
            fixc['hold_pad']['hops'] += nh
            fixc['hold_pad']['bits'] += nh * (row['bits'] // max(1, row['hops']))
    # ---- tiles: a defect that fails a hop vs flagged tiles whose hops all pass
    tl = []
    flagged = {c: t for c, t in audit.items() if t.get('flags')}
    for m in sorted(set(tiles) | set(flagged)):
        t = tiles.get(m)
        fl = (flagged.get(m) or {}).get('flags') or []
        if t is None:
            tl.append(dict(master=m, audit_flags=fl, verdict='NOT IN THE DIE CASE', why='the tile is placed inside an element / parent: '
                           'its hops are in that parent\'s floorplan, not in this die case', hops=0))
            continue
        judged = t['fail'] + t['hold'] + t['pass_']
        if t['pinreg']:
            v = 'RE-ROUTE'
            why = '; '.join(('forwarded link sampled on its launch edge (capture on the opposite edge or hold the data at the pin) on %d hops' % n)
                            if k == 'capture-edge' else f'pin register on the {k} side for {n} hops' for k, n in t['pinreg'].items())
        elif t['fail']:
            v, why = 'STANDS (die fix)', f"{t['fail']} failing hops are fixed in the die ({t['relay']} relay, {t['replan']} re-plan)"
        elif t['hold']:
            v, why = 'STANDS (hold pad)', f"{t['hold']} hops miss hold only (delay on the hop)"
        elif judged and not t['ne']:
            v, why = 'STANDS', f"all {judged} judged hops pass"
        elif judged:
            v, why = 'STANDS (partly judged)', f"{judged} judged hops pass; {t['ne']} not evaluable ({t['unmeasured']} unmeasured clock)"
        else:
            v, why = 'NOT JUDGED', f"{t['ne']} hops not evaluable ({t['unmeasured']} unmeasured clock), {t['cross']} clock crossings"
        cav = []
        if t['bound'].get('direction'):
            cav.append(f"UPPER BOUND on {t['bound']['direction']} of its failing hops: the die master's ports are bound to the view by direction "
                       "(no bind map), worst bus taken")
        if 'ALIAS' in (table[m].get('binding') or ''):
            cav.append('ALIAS view (same-family master): confirm on the real master')
        if cav and (t['fail'] or t['hold']):
            v += ' [candidate]'
            why += '; ' + '; '.join(cav)
        tl.append(dict(master=m, audit_flags=fl, verdict=v, why=why, hops=t['hops'], caveats=cav, both_real=t['real'], fail=t['fail'], hold=t['hold'],
                       passed=t['pass_'], cross=t['cross'], not_evaluable=t['ne'], worst_setup_ps=t['worst_setup'],
                       worst_hold_ps=t['worst_hold'], instances=sum(1 for x in master_of.values() if x == m),
                       view=table[m]['view'], binding=table[m].get('binding')))
    import pinreg_audit as A
    tot = lambda st: sum(v for (r_, s_), v in ((k, v) for k, v in cnt.items() if isinstance(k, tuple)) if s_ == st)
    rec = dict(schema='opentallas.pinreg_pairs.v1', die=a.die, tool='tools/hier_contract/pinreg_pairs.py',
               source_commit=A.git('rev-parse', '--short=9', 'HEAD').strip(), case=meta, table=a.table,
               rule=dict(period_ps=P.T_PS, setup_unc_ps=P.U_SETUP, skew_same_ps=P.SKEW_SAME, skew_deep_ps=P.SKEW_DEEP, level_ps=P.LEVEL_PS,
                         wire_ps_per_um=P.W_TT, wire_ff_credit=P.W_FF_CREDIT, hold_tree_ps=P.HOLD_TREE, hold_fwd_ps=P.HOLD_FWD, ocv=P.OCV,
                         default_um=P.DEFAULT_UM, placeholder_share_ps=round(P.SHARE, 1), replan_um=a.replan_um,
                         relay_class=dict(pattern=a.relay, o_ps=cls_o, s_ps=cls_s)),
               counts=dict(hops=len(hops), bits=sum(h['bits'] for h in hops),
                           by_real_ends={str(k): dict(sorted((s_, v) for (r_, s_), v in ((kk, vv) for kk, vv in cnt.items() if isinstance(kk, tuple)) if r_ == k))
                                         for k in (2, 1, 0)},
                           bits_by_real_ends={str(k): dict(sorted((s_, v) for (r_, s_), v in bits.items() if r_ == k)) for k in (2, 1, 0)},
                           models={k[6:]: v for k, v in cnt.items() if isinstance(k, str) and k.startswith('model:')},
                           port_binding_of_judged_real_hops={k[5:]: v for k, v in cnt.items() if isinstance(k, str) and k.startswith('bind:')},
                           setup_fail=tot('fail'), hold_only=tot('hold'), passed=tot('pass'), crossing=tot('cross'), not_evaluable=tot('n/e'),
                           unmeasured_clock=dict(unmeasured)),
               fix_totals=fixc, tiles=tl, pairs=out_rows)
    return rec


def write_md(rec, path, token):
    c = rec['counts']
    r = rec['rule']
    L = [f"# Per-pair die hop check: {rec['die']}", '',
         f"Tool `tools/hier_contract/pinreg_pairs.py` at {rec['source_commit']}; case `{rec['case']['source']}`; "
         f"{rec['case']['instances']:,} instances, {c['hops']:,} data hops / {c['bits']:,} bits ({rec['case']['measure']}).", '',
         f"Rule: TREE `o_A + {r['wire_ps_per_um']} L + s_B <= W - {r['setup_unc_ps']:.0f} - SKEW` (SKEW {r['skew_same_ps']:.0f}, {r['skew_deep_ps']:.0f} when "
         f"an R is over {r['level_ps']:.0f} ps), hold `l_A + {r['wire_ff_credit']} L - h_B >= {r['hold_tree_ps']:.0f}` at FF; FWD (forwarded clock beside the "
         f"bus) on the real forwarded edge; a side without a view takes the flat share {r['placeholder_share_ps']} ps (two placeholders = "
         f"{r['default_um']:.0f} um). Relay class `{r['relay_class']['pattern']}`: o {r['relay_class']['o_ps']} / s {r['relay_class']['s_ps']} ps.", '',
         '## Counts', '', '| ends with a real view | pass | setup fail | hold only | clock crossing | not evaluable |', '|---|---|---|---|---|---|']
    for k, lab in (('2', 'both'), ('1', 'one'), ('0', 'none (flat 500 um)')):
        d = c['by_real_ends'][k]
        L.append(f"| {lab} | {d.get('pass', 0):,} | {d.get('fail', 0):,} | {d.get('hold', 0):,} | {d.get('cross', 0):,} | {d.get('n/e', 0):,} |")
    L += ['', f"Link models: {', '.join(f'{k} {v:,}' for k, v in sorted(c['models'].items()))}.",
          '', 'Die port -> view pin binding of the judged hops with a real end: ' + ', '.join(f'{k} {v:,}' for k, v in sorted(c['port_binding_of_judged_real_hops'].items()))
          + ' (exact = the view has a bus of the port\'s name; prefix = its <port>_* buses of that direction; direction = the die master\'s port '
            'names are not the element\'s: worst data bus of that direction, an upper bound).']
    if c['unmeasured_clock']:
        L += ['', 'Clock insertion not measured (pairs not judged): ' + ', '.join(f'{k} ({v:,} hops)' for k, v in c['unmeasured_clock'].items()) + '.']
    L += ['', '## Fix totals', '', '| fix | pair classes | hops | bits |', '|---|---|---|---|']
    names = dict(relay='(i) one more die relay (cycle)', pinreg='(ii) pin register in the tile (re-route, +1 cycle a side)',
                 replan='(iii) pin re-plan / shorter hop (no cycle)', edge='(ii-e) capture edge of a forwarded link in the receiving tile (re-route, no cycle)', link='forwarded link re-time', none='no fix with the relay class',
                 hold_pad='hold only: delay on the hop / pin hold cells (no cycle)')
    for k, v in rec['fix_totals'].items():
        if v['hops']:
            L.append(f"| {names[k]} | {v['pair_classes']} | {v['hops']:,} | {v['bits']:,} |")
    if not any(v['hops'] for v in rec['fix_totals'].values()):
        L.append('| none needed | 0 | 0 | 0 |')
    if token:
        L += ['', '## Cycles per token', ''] + token
    L += ['', '## Tiles', '', '| master | inst | audit flags | verdict | hops (both real) | fail | hold | worst setup / hold margin ps | why |', '|---|---|---|---|---|---|---|---|---|']
    for t in sorted(rec['tiles'], key=lambda t: (not t['verdict'].startswith('RE-ROUTE'), t['verdict'], t['master'])):
        L.append(f"| {t['master']} | {t.get('instances', '')} | {', '.join(t['audit_flags']) or '-'} | {t['verdict']} | {t['hops']:,} ({t.get('both_real', 0):,}) | "
                 f"{t.get('fail', 0)} | {t.get('hold', 0)} | {t.get('worst_setup_ps')} / {t.get('worst_hold_ps')} | {t['why']} |")
    L += ['', '## Pair classes that fail (all), then the tightest passing ones', '',
          '| class | src.pin -> dst.pin | model | real | hops | bits | max um | reach um | o / s ps | setup / hold margin ps | fix |', '|---|---|---|---|---|---|---|---|---|---|---|']
    n = 0
    for p in rec['pairs']:
        bad = p['status'].get('fail', 0) + p['status'].get('hold', 0)
        if not bad:
            n += 1
            if n > 40 or p['worst_setup_ps'] is None:
                continue
        L.append(f"| {p['cls']} | {p['src']}.{p['src_pin']} -> {p['dst']}.{p['dst_pin']} | {p['model']}{'' if p.get('bind') in (None, 'exact') else ' (' + p['bind'] + ')'} | {p['real_ends']} | {p['hops']:,} "
                 f"({p['status'].get('fail', 0)} F, {p['status'].get('hold', 0)} H) | {p['bits']:,} | {p['max_um']} | {p['reach_um']} | {p['o']} / {p['s']} | "
                 f"{p['worst_setup_ps']} / {p['worst_hold_ps']} | {', '.join(f'{k} ({v})' for k, v in p['fixes'].items()) or '-'} |")
    Path(path).write_text('\n'.join(L) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('table')
    t.add_argument('--masters', required=True)
    t.add_argument('--merge')
    t.add_argument('--out', required=True)
    for name in ('s81', 'qwen'):
        s = sub.add_parser(name)
        s.add_argument('--plan', required=True)
        s.add_argument('--table', required=True)
        s.add_argument('--audit')
        s.add_argument('--relay', default=r'^dsfd_rly_' if name == 's81' else r'^qfd_cst_[ns]$')
        s.add_argument('--replan-um', type=float, default=50.0)
        s.add_argument('--die', default='ds_rom_s81_layer1' if name == 's81' else 'qwen_rom_tp8')
        s.add_argument('--token', help='JSON: class regex -> uses per token (cycles per token of an added stage)')
        s.add_argument('--out', required=True)
        s.add_argument('--md')
    a = ap.parse_args(argv)
    if a.cmd == 'table':
        return cmd_table(a)
    meta, hops, master_of, drv, cnet = read_plan(a.plan)
    rec = evaluate(a, meta, hops, master_of, drv, cnet)
    token_lines = []
    if a.token:
        tk = json.loads(Path(a.token).read_text())
        tot = 0
        rows = []
        for p in rec['pairs']:
            if not p['cycles']:
                continue
            use = next((v for k, v in tk['classes'].items() if re.search(k, p['cls'])), None)
            p['uses_per_token'] = use
            p['cycles_per_token'] = None if use is None else use * p['cycles']
            rows.append(p)
        by = collections.OrderedDict()
        for p in rows:
            d = by.setdefault(p['cls'], dict(cycles=0, use=p['uses_per_token']))
            d['cycles'] = max(d['cycles'], p['cycles'])
        for k, d in by.items():
            tot += (d['use'] or 0) * d['cycles']
        rec['token'] = dict(basis=tk.get('basis'), by_class=by, added_cycles_per_token=tot, cycles_per_token=tk.get('cycles_per_token'),
                            loss=round(tot / tk['cycles_per_token'], 5) if tk.get('cycles_per_token') else None)
        token_lines = [f"Basis: {tk.get('basis')}", ''] + [f"- {k}: +{d['cycles']} stage(s) x {d['use']} uses per token" for k, d in by.items()] + \
                      ['', f"Added cycles per token: {tot:,}" + (f" of {tk['cycles_per_token']:,} ({100 * tot / tk['cycles_per_token']:.3f} %)" if tk.get('cycles_per_token') else '')]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    if a.md:
        write_md(rec, a.md, token_lines)
    c = rec['counts']
    print(f"{rec['die']}: hops {c['hops']:,} pass {c['passed']:,} setup-fail {c['setup_fail']:,} hold-only {c['hold_only']:,} cross {c['crossing']:,} "
          f"n/e {c['not_evaluable']:,}; both-real {c['by_real_ends']['2']}; fixes "
          + ', '.join(f"{k} {v['hops']}" for k, v in rec['fix_totals'].items() if v['hops']))


if __name__ == '__main__':
    main()
