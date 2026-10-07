#!/usr/bin/env python3
"""PER-BLOCK BUDGET SHEETS from the die floorplans and the die clock plan (CLAUDE BUDGETS, 2026-10-06).

One JSON per hardened master (results/rtl/budgets_20261006/sheets/<master>.json) plus summary.json / SUMMARY.md.
Every interface of a master is taken from the generator nets of every die it is placed in (worst instance):

  length        pin-to-pin Manhattan wire to the nearest register on the other side (the neighbour block's pin, or the
                planned die station / relay / waypoint, which the generators place as instances)
  skew term     intra-region: the clock plan's measured region bound + 25 ps margin, capped at 90 ps (OWNER rule:
                measured + margin); a different clock region, a mesochronous crossing or a forwarded-clock <-> region
                hop: 150 ps; forwarded-clock station to station: the intra term; CDC (different frequency): no
                synchronous budget (datapath max delay)
  SS setup      input  delay = clk->Q 90 + pin driver 40 + 1.135 ps/um x L + skew       (against vclk at the block's
                output delay = 1.135 ps/um x L + receiver 41 + setup 30 + skew           own sheet insertion: the die
                                                                                         tree aligns the flops of every
                                                                                         block in a region, so the
                                                                                         neighbour's flop = own flop)
                internal = 833.333 - 60 - 15 (acceptance) - external; it must cover the block-side fixed part
                (input: receiver + setup 71; output: clk->Q + driver 130) -> feasible / INFEASIBLE
  FF hold       input min delay = clk->Q(FF min) 32.2 + 0.112 ps/um x L (50 % FF wire credit, stations method);
                output min delay = hold 15 - 0.112 x L; plus the 50 ps hold IO uncertainty
  stages        ceil(L / reach(skew)) register stages for the segment (reach = (833.333 - 60 - 15 - 201 - skew) /
                1.135: 412 um intra, 359 um inter); > 1 means the floorplan needs another station (INFEASIBLE as
                planned: an architecture / stage change)
  registration  every data pin is a flop at the pin (OWNER: block boundary register-to-register); exceptions are
                clock, async reset (synchronised inside), and PHY / link black-box pins (macro-side protocol)
  fanout        internal control nets <= 32 loads (kept replicas above); die nets of a 1-bit output with > 32 loads
                are flagged (need replicated pins or a distribution station)
  clock         clock-arrival target at the block clock pin = region flop target - the block's own insertion (the
                die pads small blocks), per corner, from the clock plan (CTS-measured pin arrivals)

  budget_sheet.py --die NAME=model.json.gz[:plan.json] ... [--calib calibrations.json] [--tiles tiles.json] --out DIR
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

SKIP_CLS = {'clock', 'col_clock', 'clock_trunk', 'reset', 'reset_tree', 'col_reset', 'fclk', 'top_in'}
BLACKBOX_KINDS = {'phy', 'link', 'serdes_slab', 'host_slab', 'cfg'}     # macro pins: protocol of the macro, not a flop
LINK_STAGE_UM = 430.56
PIN_LAST_UM = 100.0     # HBM r19b pin-abutting station: last segment into the receiving pin
FREQ = {'stream_1p2': 1.2, 'fwd': 1.2, 'serial_0p9': 0.9, 'hbm': 0.9766, 'link': 1.2}
IN_FIXED_BLOCK = C.RCV_IN_PS + C.SETUP_SS_PS          # 71: what the receiving block needs inside
OUT_FIXED_BLOCK = C.CLKQ_SS_PS + C.DRV_OUT_PS         # 130: what the launching block needs inside


def fwd_links(d):
    """{(src, dst)} instance pairs joined by a forwarded clock (S81 fclk nets: the source block / previous station
    launches data and its clock together)"""
    out = set()
    for bid, cls, bits, eps in d['buses']:
        if cls == 'fclk':
            for e in eps[1:]:
                out.add((eps[0][0], e[0]))
    return out


def classify(d, ia, ib, reg, trees, plan_intra, fl=frozenset(), fbus=False):
    """skew class and setup term between instances a (driver) and b (load); fbus: the net carries its own forwarded
    clock bits (HBM r15 fwd segments)"""
    da, db = ia[4], ib[4]
    if fbus or (ia[0], ib[0]) in fl or (ib[0], ia[0]) in fl:
        # forwarded-clock hop: the capture clock travels the same wire as the data (positive skew on setup, absorbed
        # in the 60 ps uncertainty; hold by opposite-edge capture / hold repair)
        return 'fwd', C.SKEW_FWD_PS
    if FREQ.get(da) and FREQ.get(db) and FREQ[da] != FREQ[db]:
        # different frequency: the crossing's CDC FIFO sits inside one of the two blocks; the pin is timed in the
        # PEER's domain (both pins are flops of the same clock), across a region boundary
        return 'xdomain', C.SKEW_INTER_PS
    ra, rb = reg.get(ia[0]), reg.get(ib[0])
    if ra is None and rb is None:
        return 'fwd-unlinked', C.SKEW_INTRA_PS
    if ra is None or rb is None:
        return 'inter', C.SKEW_INTER_PS
    if ra[0] != rb[0]:
        # a tree root driving its own tree (S81 column FIFO -> column): the region root
        for x, y in ((ia, rb), (ib, ra)):
            if trees[y[0]]['root'][0] == x[0]:
                return 'root', plan_intra.get(y[1], C.SKEW_INTRA_PS)
        return 'meso', C.SKEW_INTER_PS
    if ra[1] != rb[1]:
        return 'inter', C.SKEW_INTER_PS
    return 'intra', plan_intra.get(ra[1], C.SKEW_INTRA_PS)


def budgets(L, skew, period, planned=1, last_um=None):
    """as-planned feasibility on the floorplan length L; the delay budgets themselves on the segment after the stages
    the interface needs (L / stages_needed), i.e. what the block must close once the floorplan carries those stations"""
    avail = period - C.UNC_SETUP_PS - C.ACCEPT_PS
    reach = C.reach_um(skew, period)
    st = max(1, math.ceil(L / reach)) if reach > 0 else 99
    if skew > C.SKEW_INTRA_PS and L > reach:
        # a staged path crosses the region boundary once: one hop at the inter reach, the rest at the intra reach
        st = 1 + math.ceil((L - reach) / C.reach_um(C.SKEW_INTRA_PS, period))
    seg = L / max(st, planned)
    if last_um is not None:     # HBM r19b: a die station abuts this receiving pin (last segment <= last_um)
        seg = min(seg, last_um)
    w0, w = C.WIRE_SS_PS_PER_UM * L, C.WIRE_SS_PS_PER_UM * seg
    fixed_in, fixed_out = C.CLKQ_SS_PS + C.DRV_OUT_PS + skew, C.RCV_IN_PS + C.SETUP_SS_PS + skew
    ind, outd = fixed_in + w, fixed_out + w
    return dict(input_delay_ss_ps=round(ind, 1), output_delay_ss_ps=round(outd, 1),
                input_fraction_of_T=round(ind / period, 3), output_fraction_of_T=round(outd / period, 3),
                internal_input_ps=round(avail - ind, 1), internal_output_ps=round(avail - outd, 1),
                as_planned_internal_input_ps=round(avail - fixed_in - w0 / planned, 1),
                as_planned_internal_output_ps=round(avail - fixed_out - w0 / planned, 1),
                # the stage count already places the one region-crossing hop at the inter reach: feasible = enough stages
                feasible_input=st <= planned, feasible_output=st <= planned,
                reach_um=round(reach, 1), stages_needed=st, stages_planned=planned, extra_stages_needed=max(0, st - planned),
                segment_after_stages_um=round(seg, 1),
                input_min_delay_ff_ps=round(C.CLKQ_FF_MIN_PS + C.WIRE_FF_CREDIT_PS_PER_UM * seg, 1),
                output_min_delay_ff_ps=round(C.HOLD_FF_PS - C.WIRE_FF_CREDIT_PS_PER_UM * seg, 1))


def load_plan(path):
    if not path:
        return None
    import gzip
    p = Path(path)
    return json.loads(gzip.open(p, 'rt').read() if p.suffix == '.gz' else p.read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', action='append', required=True, help='NAME=model.json.gz[:plan.json]')
    ap.add_argument('--calib', help='measured block insertions {master: {ss_mean, ss_min, ss_max, ff_mean, ff_min, ff_max, source}}')
    ap.add_argument('--tiles', help='tile compositions (tools/budgets/tiles.py output)')
    ap.add_argument('--insertion-override', help='{master: {target_ss?, reason}}: re-planned internal insertion target '
                    '(default the measured ss_max); its die entry target follows the measured insertion (the die tree '
                    'delivers earlier) and the extra OCV on its deeper tree, OCV x (ss_max - cap), is added to the skew '
                    'term of every synchronous interface of that master (block-side budget, die skew budget unchanged)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    calib = json.loads(Path(a.calib).read_text()) if a.calib else {}
    ovr = json.loads(Path(a.insertion_override).read_text()) if a.insertion_override else {}
    ovr_extra = {}
    for m_, o_ in ovr.items():
        c_ = calib.get(m_, {})
        ins_ = o_.get('target_ss', c_.get('ss_max', C.LINT_CAP_PS))
        ovr_extra[m_] = round(C.OCV * max(0.0, ins_ - C.LINT_CAP_PS), 1)
    out = Path(a.out)
    (out / 'sheets').mkdir(parents=True, exist_ok=True)
    M = {}                     # master -> accumulated record
    region_flop = {}           # (die, region) -> region flop target (SS, FF)

    def lint(master, w, h):
        """the block's internal insertion: TARGET (size model capped at 900 ps) and the value the die plan compensates
        (measured calibration where one exists, else the target)"""
        mss, _ = C.lint_model(w, h)
        tgt = round(min(mss, C.LINT_CAP_PS), 1)
        base = dict(target_ss=tgt, target_ff=round(tgt * C.LINT_FF_RATIO, 1), target_basis=(
            f'min({C.LINT_A_PS} + {C.LINT_B_PS_PER_UM} x sqrt(w h) = {mss}, cap {C.LINT_CAP_PS:.0f} = intra skew '
            f'{C.SKEW_INTRA_PS:.0f} / (2 x OCV {C.OCV}))'), tolerance_ps=C.LINT_TOL_PS)
        c = calib.get(master)
        if c:
            base.update(ss=c['ss_mean'], ff=c['ff_mean'], ss_min=c.get('ss_min'), ss_max=c.get('ss_max'),
                        ff_min=c.get('ff_min'), ff_max=c.get('ff_max'), grade='measured', source=c['source'],
                        over_target=c['ss_mean'] > tgt + C.LINT_TOL_PS)
            if master in ovr:       # re-planned target: the measured tree is accepted, its OCV priced on the IO skew
                o_ = ovr[master]
                for k_ in ('ss', 'ff', 'ss_min', 'ss_max', 'ff_min', 'ff_max', 'source'):   # newer measurement
                    if k_ in o_:
                        base[k_] = o_[k_]
                t_ = o_.get('target_ss', c.get('ss_max', c['ss_mean']))
                base.update(target_ss=t_, target_ff=o_.get('target_ff', c.get('ff_max', c['ff_mean'])), over_target=False,
                            target_basis=f"RE-PLANNED: {o_.get('reason', '')} (measured SS {c['ss_min']}..{c['ss_max']}); "
                                         f"IO skew +{ovr_extra[master]} ps (OCV x (target - cap {C.LINT_CAP_PS:.0f}))",
                            replanned=True)
            return base
        base.update(ss=tgt, ff=base['target_ff'], ss_min=round(tgt * 0.95, 1), ss_max=round(tgt * 1.10, 1),
                    ff_min=round(base['target_ff'] * 0.95, 1), ff_max=round(base['target_ff'] * 1.10, 1),
                    grade='target', source='no calibration yet: the target', over_target=False)
        return base

    for spec in a.die:
        name, rest = spec.split('=', 1)
        mp, _, pp = rest.partition(':')
        d = C.load_die(mp)
        plan = load_plan(pp)
        trees = C.clock_trees(d)
        reg = C.sink_regions(d, trees)
        reg = {k: (v[0], v[1]) for k, v in reg.items()}
        fl = fwd_links(d)
        fb = set(d.get('fclk_buses', []))
        pb = set(d.get('path_buses', []))
        ps_ = set(d.get('pin_stage_buses', []))      # HBM r19b: a station abuts the receiving pin (+1 hop)
        rl_ = {(r[0], r[1]) for r in d.get('relay_ends', [])}     # HBM r22: relay abutting (bus, block instance) pin
        relay_out = set()
        rlc_ = defaultdict(int)
        for r in d.get('relay_ends', []):
            rlc_[r[0]] += 1
        plan_intra = {r: v['intra_budget_ps'] for r, v in (plan or {}).get('regions', {}).items()}
        sink_ins = (plan or {}).get('sink_insertion', {})
        clk_port = defaultdict(list)
        for t, tr in trees.items():
            for inst, port in tr['sinks']:
                clk_port[inst].append((t, port))
        if plan:                  # the planned (hierarchical) clock regions
            sr = plan.get('sink_region', {})
            for inst, (t, r) in list(reg.items()):
                port = next((p for tt, p in clk_port[inst] if tt == t), None)
                if f'{inst}/{port}' in sr:
                    reg[inst] = (t, sr[f'{inst}/{port}'])
        # region flop targets: CTS pin arrival + the largest block insertion of the region
        per_region = defaultdict(list)
        for inst, (t, r) in reg.items():
            it = d['by'][inst]
            port = next((p for tt, p in clk_port[inst] if tt == t), None)
            ins = sink_ins.get(f'{inst}/{port}')
            L = lint(it[1], it[7], it[8])
            per_region[r].append((ins, L, it))
        for r, l in per_region.items():
            have = [(x[0], x[1]) for x in l if x[0]]
            if have:
                region_flop[(name, r)] = (round(max(i[0] + L_['ss'] for i, L_ in have), 1),
                                          round(max(i[1] + L_['ff'] for i, L_ in have), 1))
        for it in d['insts']:
            rec = M.setdefault(it[1], dict(master=it[1], kinds=set(), dies={}, size_um=[it[7], it[8]], ports={},
                                            clock=dict(ports=set(), regions=set(), domains=set(), entry_ss=[], entry_ff=[],
                                                       pad_ss=[]),
                                            lint=lint(it[1], it[7], it[8])))
            rec['kinds'].add(it[2])
            rec['dies'][name] = rec['dies'].get(name, 0) + 1
            rec['clock']['domains'].add(it[4])
            for t, p in clk_port.get(it[0], []):
                rec['clock']['ports'].add(p)
            if it[0] in reg:
                r = reg[it[0]][1]
                rec['clock']['regions'].add(f'{name}:{r}')
                rec['intra_budget'] = max(rec.get('intra_budget', 0.0), plan_intra.get(r, C.SKEW_INTRA_PS))
                ft = region_flop.get((name, r))
                if ft:
                    e_ss, e_ff = ft[0] - rec['lint']['ss'], ft[1] - rec['lint']['ff']
                    rec['clock']['entry_ss'].append(e_ss)
                    rec['clock']['entry_ff'].append(e_ff)
                    port = next((p for tt, p in clk_port[it[0]] if tt == reg[it[0]][0]), None)
                    ins = sink_ins.get(f'{it[0]}/{port}')
                    if ins:
                        rec['clock']['pad_ss'].append(e_ss - ins[0])
            else:
                rec['clock']['regions'].add(f'{name}:forwarded')
        # interfaces
        for bid, cls, bits, eps in d['buses']:
            if cls in SKIP_CLS:
                continue
            if eps[0][0] == 'TOP':
                continue
            drv = d['by'][eps[0][0]]
            loads = [e for e in eps[1:] if e[0] != 'TOP']
            fan = len(loads)
            for e in loads:
                ld = d['by'][e[0]]
                L, basis = C.pin_dist(d, drv, eps[0][1], ld, e[1])
                kls, skew = classify(d, drv, ld, reg, trees, plan_intra, fl, bid in fb)
                ex_ = ovr_extra.get(drv[1], 0.0) + ovr_extra.get(ld[1], 0.0)
                if kls not in ('fwd', 'fwd-unlinked') and ex_:
                    skew = round(skew + ex_, 1)
                # planned die stations: S81 places every station as an instance (1 hop); the HBM die prices the
                # wire stages of its path segments at ceil(L / 430.56) (hbm_accel_die_fp LINK_STAGE_UM)
                if bid not in pb:
                    plan_st = 1
                elif d.get('budget_stages') and bid not in fb:     # HBM r17: common-clock segments planned at the
                    plan_st = 1 + math.ceil(max(0.0, L - 359.0) / 412.0)   # inter + intra reach (generator seg_stages)
                else:
                    plan_st = max(1, math.ceil(L / LINK_STAGE_UM))
                if bid in ps_:
                    plan_st += 1
                if d.get('relay_rule'):   # HBM r22 rule: a relay at every hardened-block end of a > 100 um pin segment
                    for it_, pt_ in ((drv, eps[0][1]), (ld, e[1])):
                        if L > PIN_LAST_UM and it_[2] not in ('waypoint', 'phy') and cls not in ('phy_dfi',):
                            rl_.add((bid, it_[0]))
                            relay_out.add((bid, it_[0], pt_))
                    rlc_[bid] = sum(1 for r_ in relay_out if r_[0] == bid)
                plan_st += rlc_.get(bid, 0)
                for me, port, peer, dirn in ((drv, eps[0][1], ld, 'out'), (ld, e[1], drv, 'in')):
                    pr = M[me[1]]['ports'].setdefault((port, dirn), dict(port=port, dir=dirn, bits=0, classes=set(), neighbours=set(),
                                                                       L=0.0, basis=set(), skew_cls=set(), skew=0.0, cdc=False,
                                                                       period=1e9, fanout=0, n=0, worst=None, dies=set()))
                    pr['bits'] = max(pr['bits'], bits)
                    pr['classes'].add(cls)
                    pr['neighbours'].add(peer[1])
                    pr['dies'].add(name)
                    pr['n'] += 1
                    pr['skew_cls'].add(kls)
                    per = 1000.0 / FREQ.get(peer[4] if kls == 'xdomain' else me[4], 1.2)
                    if kls == 'xdomain':
                        pr.setdefault('domains', set()).add(peer[4])
                    pr['period'] = min(pr['period'], per)
                    if dirn == 'out':
                        pr['fanout'] = max(pr['fanout'], fan)
                    sev = C.WIRE_SS_PS_PER_UM * L / plan_st + skew
                    if pr['worst'] is None or sev > pr['worst'][0]:
                        pr['worst'] = (sev, L, skew, kls, f'{name}:{me[0]}<->{peer[0]}', basis, plan_st,
                                       PIN_LAST_UM if ((bid in ps_ and dirn == 'in') or (bid, me[0]) in rl_) else None)
                    pr['L'] = max(pr['L'], L)
                    pr['basis'].add(basis)
        if d.get('relay_rule'):
            (out / f'relay_ends_{name}.json').write_text(json.dumps(sorted(list(r) for r in relay_out), indent=0) + '\n')
    # tiles (S81-PH slab compositions)
    tiles = json.loads(Path(a.tiles).read_text()) if a.tiles else {}
    for tm, t in tiles.get('tiles', {}).items():
        rec = M.setdefault(tm, dict(master=tm, kinds={'tile'}, dies={'s81 (in slab ' + t['slab'] + ')': t['instances']},
                                    size_um=t['size_um'], ports={},
                                    clock=dict(ports=set(t.get('clock_ports', ['ck'])), regions={f'slab:{t["slab"]}'},
                                               domains={t.get('domain', 'stream_1p2')}, entry_ss=[], entry_ff=[], pad_ss=[]),
                                    lint=lint(tm, *t['size_um'])))
        rec['tile_of'] = t['slab']
        slab = M.get(t['slab'])
        if slab and slab['clock']['entry_ss']:
            # the slab entry is the die-tree sink; the tile pin is one slab-local tree level further (balanced)
            rec['clock']['entry_ss'] = [max(slab['clock']['entry_ss']) + slab['lint']['ss'] - rec['lint']['ss']]
            rec['clock']['entry_ff'] = [max(slab['clock']['entry_ff']) + slab['lint']['ff'] - rec['lint']['ff']]
        for e in t['edges']:
            for port_dir in e['ports']:
                port, dirn = port_dir
                pr = rec['ports'].setdefault((port, dirn), dict(port=port, dir=dirn, bits=e.get('bits', 0), classes=set(),
                                                               neighbours=set(), L=0.0, basis=set(), skew_cls=set(), skew=0.0,
                                                               cdc=False, period=1000.0 / FREQ.get(t.get('domain', 'stream_1p2'), 1.2), fanout=0, n=0, worst=None, dies=set()))
                kls = e.get('skew_class', 'intra')
                skew = C.SKEW_INTER_PS if kls in ('inter', 'meso') else (slab or {}).get('intra_budget', C.SKEW_INTRA_PS)
                if e.get('inherit'):
                    sm, names = e['inherit']
                    cand = [q for (pn, dn), q in M.get(sm, {}).get('ports', {}).items()
                            if dn == dirn and q['worst'] and (names is None or pn in names)]
                    if not cand:
                        continue
                    w = max(cand, key=lambda q: q['worst'][0])['worst']
                    L, skew, kls = w[1], w[2], w[3]
                    e = dict(e, length_um=L, what=e['what'] + f' [inherits {sm}: {w[4]}]', basis='inherited ' + w[5])
                pr['classes'].add(e['what'][:60])
                pr['neighbours'].add(e.get('peer', '?'))
                pr['skew_cls'].add(kls)
                pr['basis'].add(e.get('basis', 'composition'))
                pr['n'] += 1
                pr['dies'].add('s81')
                L = e['length_um']
                sev = C.WIRE_SS_PS_PER_UM * L + skew
                if kls == 'cdc':
                    pr['cdc'] = True
                elif pr['worst'] is None or sev > pr['worst'][0]:
                    pr['worst'] = (sev, L, skew, kls, e['what'], e.get('basis', 'composition'), 1, None)
                    pr['L'] = max(pr['L'], L)
    # finalise
    summary, infeasible = [], []
    for mst, rec in sorted(M.items()):
        bb = bool(rec['kinds'] & BLACKBOX_KINDS)
        ports = []
        for (port, dirn), pr in sorted(rec['ports'].items()):
            row = dict(port=port, dir='input' if dirn == 'in' else 'output', bits=pr['bits'], bus_classes=sorted(pr['classes']),
                       neighbours=sorted(pr['neighbours'])[:12], connections=pr['n'], dies=sorted(pr['dies']),
                       registered_at_pin=not bb, period_ps=round(pr['period'], 3),
                       clock_domain=sorted(pr.get('domains', [])) or None)
            if pr['worst'] is None and not pr['cdc']:
                row.update(timing='unresolved', note='no die / composition peer resolved for this port')
                ports.append(row)
                continue
            if pr['worst'] is None:
                row.update(timing='cdc', cdc_max_delay_ps=round(pr['period'] - 123.0, 3),
                           note='different frequency domain: async / ratio FIFO; set_max_delay -datapath_only')
                ports.append(row)
                continue
            sev, L, skew, kls, where, basis, plan_st, last_ = pr['worst']
            b = budgets(L, skew, pr['period'], plan_st, last_)
            row.update(timing='sync', length_um=round(L, 1), length_basis=basis, skew_class=kls, skew_ps=skew,
                       hold_io_ps=C.HOLD_IO_SKEW_PS, worst_instance=where, also_cdc=pr['cdc'], **b)
            if dirn == 'out' and pr['bits'] == 1 and pr['fanout'] > C.MAX_FANOUT_CTRL:
                row['die_fanout'] = pr['fanout']
                row['fanout_flag'] = f'1-bit die net with {pr["fanout"]} loads > {C.MAX_FANOUT_CTRL}: replicate the pin flop or add a distribution station'
            elif dirn == 'out':
                row['die_fanout'] = pr['fanout']
            ok = b['feasible_input'] if dirn == 'in' else b['feasible_output']
            row['feasible'] = ok and b['extra_stages_needed'] == 0
            if not row['feasible']:
                infeasible.append(dict(master=mst, port=port, dir=row['dir'], bits=pr['bits'], length_um=round(L, 1),
                                       skew_class=kls, skew_ps=skew, stages_needed=b['stages_needed'],
                                       stages_planned=plan_st,
                                       internal_ps=b['as_planned_internal_input_ps' if dirn == 'in' else 'as_planned_internal_output_ps'],
                                       where=where, classes=sorted(pr['classes'])))
            ports.append(row)
        ck = rec['clock']
        ent = lambda v: dict(mean=round(sum(v) / len(v), 1), min=round(min(v), 1), max=round(max(v), 1)) if v else None  # noqa: E731
        sheet = dict(schema='opentallas.budgets.sheet.v1', master=mst, kinds=sorted(rec['kinds']), dies=rec['dies'],
                     size_um=[round(x, 3) for x in rec['size_um']], tile_of=rec.get('tile_of'),
                     clock=dict(ports=sorted(ck['ports']), domains=sorted(ck['domains']), regions=sorted(ck['regions'])[:20],
                                n_regions=len(ck['regions']),
                                entry_target_ss_ps=ent(ck['entry_ss']), entry_target_ff_ps=ent(ck['entry_ff']),
                                die_pad_ss_ps=ent(ck['pad_ss']),
                                internal_insertion=rec['lint'],
                                calibrate_check=dict(compare='closure-loop CK_SS_MEAN vs internal_insertion.ss (the value the '
                                                             'die plan compensates) and vs internal_insertion.target_ss',
                                                     tolerance_ps=rec['lint']['tolerance_ps'],
                                                     on_deviation='FLAG (NEEDS_BUDGET): re-plan the die pin target; '
                                                                  'never silently re-calibrate the IO SDC')),
                     skew=dict(intra_ps=C.SKEW_INTRA_PS, inter_ps=C.SKEW_INTER_PS, hold_io_ps=C.HOLD_IO_SKEW_PS,
                               setup_uncertainty_ps=C.UNC_SETUP_PS, hold_uncertainty_ps=C.UNC_HOLD_PS,
                               route_period_ps=C.ROUTE_T_PS, signoff_period_ps=C.T_PS, accept_ps=C.ACCEPT_PS),
                     control=dict(max_fanout_internal=C.MAX_FANOUT_CTRL,
                                  rule='nets above 32 loads get kept (dont_touch) replicas; reductions > 4 inputs get a '
                                       'register per 4-6 levels (DESIGN SIMPLIFICATION 3/5)'),
                     interfaces=ports,
                     totals=dict(ports=len(ports), sync=sum(1 for p in ports if p['timing'] == 'sync'),
                                 cdc=sum(1 for p in ports if p['timing'] == 'cdc'),
                                 infeasible=sum(1 for p in ports if p.get('feasible') is False),
                                 fanout_flags=sum(1 for p in ports if p.get('fanout_flag')),
                                 max_length_um=max((p.get('length_um', 0) for p in ports), default=0),
                                 max_stages_needed=max((p.get('stages_needed', 0) for p in ports), default=0)),
                     constants=dict(wire_ss_ps_per_um=C.WIRE_SS_PS_PER_UM, clkq_ss=C.CLKQ_SS_PS, drv_out=C.DRV_OUT_PS,
                                    rcv_in=C.RCV_IN_PS, setup_ss=C.SETUP_SS_PS, clkq_ff_min=C.CLKQ_FF_MIN_PS,
                                    hold_ff=C.HOLD_FF_PS, wire_ff_credit_ps_per_um=C.WIRE_FF_CREDIT_PS_PER_UM))
        (out / 'sheets' / f'{mst}.json').write_text(json.dumps(sheet, indent=1, default=sorted) + '\n')
        summary.append(dict(master=mst, kinds=sheet['kinds'], dies=rec['dies'], size_um=sheet['size_um'],
                            entry_ss=sheet['clock']['entry_target_ss_ps'], lint_ss=rec['lint']['ss'], lint_grade=rec['lint']['grade'],
                            lint_target_ss=rec['lint']['target_ss'], lint_over_target=rec['lint']['over_target'],
                            **sheet['totals']))
    (out / 'summary.json').write_text(json.dumps(dict(schema='opentallas.budgets.summary.v1', masters=len(summary),
                                                      rows=summary, infeasible=infeasible), indent=1, default=sorted) + '\n')
    md = ['# Budget sheets: summary (tools/budgets/budget_sheet.py)', '',
          f'{len(summary)} hardened masters. Sign-off 833.333 ps, SS 60 / FF 25 ps, accept +15/+15; skew terms intra '
          f'(clock-plan region bound + 25, <= 90) / inter-region, meso, cross-domain 150 / forwarded-clock hop 0; '
          f'wire 1.135 ps/um SS; reach {C.reach_um(C.SKEW_INTRA_PS):.0f} um intra, {C.reach_um(C.SKEW_INTER_PS):.0f} um inter, '
          f'{C.reach_um(C.SKEW_FWD_PS):.0f} um forwarded.', '',
          '| master | kind | dies (instances) | size um | block insertion SS (grade) / target | die entry target SS | ports | max L um | max stages | infeasible | fanout flags |',
          '|---|---|---|---|---|---|---:|---:|---:|---:|---:|']
    for r in summary:
        e = r['entry_ss']
        md.append(f"| {r['master']} | {','.join(r['kinds'])} | {', '.join(f'{k}:{v}' for k, v in r['dies'].items())} | "
                  f"{r['size_um'][0]:.0f} x {r['size_um'][1]:.0f} | {r['lint_ss']:g} ({r['lint_grade']}) / {r['lint_target_ss']:g}"
                  f"{' OVER' if r['lint_over_target'] else ''} | {(str(e['min']) + '..' + str(e['max'])) if e else '-'} | "
                  f"{r['ports']} | {r['max_length_um']:.0f} | {r['max_stages_needed']} | {r['infeasible']} | {r['fanout_flags']} |")
    md += ['', '## Interfaces infeasible as planned (need an architecture / stage change)', '',
           '| master | port | dir | bits | L um | skew class | stages needed | internal ps as planned | worst instance |',
           '|---|---|---|---:|---:|---|---:|---:|---|']
    for x in sorted(infeasible, key=lambda x: (-x['stages_needed'], -x['length_um'])):
        md.append(f"| {x['master']} | {x['port']} | {x['dir']} | {x['bits']} | {x['length_um']:.0f} | {x['skew_class']} | "
                  f"{x['stages_needed']} | {x['internal_ps']:.0f} | {x['where']} |")
    (out / 'SUMMARY.md').write_text('\n'.join(md) + '\n')
    print(json.dumps(dict(masters=len(summary), infeasible_ports=len(infeasible),
                          infeasible_masters=len({x['master'] for x in infeasible}))))


if __name__ == '__main__':
    main()
