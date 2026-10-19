#!/usr/bin/env python3
"""KV-CLOCK 10-18 (landed-regions standard, lanes/LANDING-CONTRACT.md + section 7; CLOCK-AUDIT KV FAILING): FORWARDED
HALF-CYCLE LANES + LANDINGS on every KV die relay chain that crosses core clock trees.

The KV die runs five core clock regions (c = centre, WS / WN / ES / EN = the HBM stacks), each its own tree and NOT
balanced against the others (tools/die_clock/specs/kv_regions_1018.json).  A data relay chain runs on its DRIVER's tree
(OT_KV_SEAM); its last hop into a load on another tree was a plain root -> root hop (rt4: 299 failing c <-> stack pairs,
TT 249 / FF 311 ps).  This pass (after kv_rly_std.py, on the replica netlist) turns every such chain of n replica stations
into the Qwen / S81 lane form, slice by slice (each standard replica of a row is its own lane):

    station 0        qkd_rlysh0_<S>  ck = SOURCE region root, en = the source block's released reset (hop-0 ICG,
                                     rising capture, ck_o = ~cko)
    stations 1..n-2  qkd_rlysh_<S>   ckf / ea = previous ck_o / eb (half-cycle: capture T/2 after the previous one)
    station n-1      qkd_landsh_<S>  the LANDING: ring D 4 written on the lane clock, read on the RECEIVING block's
                                     root ck at (rc - K) mod D, rs = the receiving block's regional reset
    n = 1            qkd_landsh0_<S> landing carrying the hop-0 gate (ck_s = source root, en = source reset)

Same instance names, same frames, same placement: only the masters and the clock / epoch / strap wiring change
(rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv over rtl/qwen_split/qfd_fwd_lane.sv).  K straps come from the instance's
own tie_hi / tie_lo (never a netlist literal), K = (planned E + h0(n)) mod 8 (contract L5: E = max over corners of
1 + ceil(-S1/T); until the die STA measures S1 the S81 p4j half-cycle fit ceil((n-1)/2) + 1, >= 2, as
tools/qwen_split/fwd_lane_price.py; h0 = 1 for an n = 1 qkd_landsh0 (QK-LANDEN: en registered on ck_s before the ICG moves
the write epoch one source edge later, lane_groups.HOP0_EN_REG), else 0; the calendar G - R0 is 0 on the KV die).
KVR-FWDAGE 10-19: the landing delivers the source word o = w(t - L), L = E + 1 core edges, for EVERY n (the in-band lane
epoch makes the ring absorb the station delay; L = K + 1 - h0, ot_qfd_land), so the compiled age ceil(landed - 1) needs
landed = E + 2 (+ post-landing stages): not 1 + (n-2)/2 + 1 + E + 1, which counted the station delay twice (1..47 edges
late on kvs14r, results/rtl/kvr_landlag_1019).
Reset / boot nets are NOT laned (they define the epochs; OT_KV_RST_PER_TREE keeps one root hop a tree, timed by the die
STA release window).  fault outputs drive private open wires (recorded: owed to the block fault OR).

    kv_fwd_lanes.py --run RUN [--netlist-only] [--dry-run]
rewrites RUN/case_kv/die.v (original kept as die.v.prefwd), adds the lane masters to expand.json leaves (and their closed
views / LEF / libs when physical/ref_tile/qkd_<fam>_<S>/views exist), writes RUN/fwd_lanes.json (every lane: bus slice,
n, source / receiving block and region, planned E, K, latency today n + 1 vs landed E + 2 (+ post stages)).
"""
import argparse
import json
import math
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_rly_std as RS        # noqa: E402
import kv_lane_orientation as LO  # noqa: E402
import kv_lane_reach as LR  # noqa: E402
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
import lane_groups as LG  # noqa: E402

RTL = 'rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv'
CORE_RTL = ['rtl/qwen_split/qfd_fwd_lane.sv', 'rtl/hdc/ot_hdc_cg.sv']
FAM = ('qkd_rlysh0_', 'qkd_rlysh_', 'qkd_landsh_', 'qkd_landsh0_')
CORE = re.compile(r'^n_clk_core_(\w+)$')
RST_NET = re.compile(r'^n_(rst_|hboot|rrs_)')
STD_RE = re.compile(r'^qkd_rlys_(\d+)$')
INST = re.compile(r'^(\s+)(\S+) (\S+) \((.*)\);\s*$')
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')
RESET_PORTS = ('rst_n', 'rs', 'rsi', 'rst', 'rstn', 'rs_n')
CORNERS = ('tt', 'ff', 'ss')


def expr_bits(expr, wires):
    """Verilog connection (net, slice, concatenation, sized literal) -> bit refs LSB first ('0' / '1' = constant)"""
    expr = expr.strip()
    if not expr:
        return []
    if expr.startswith('{'):
        out = []
        for part in reversed([p.strip() for p in expr[1:-1].split(',')]):
            out += expr_bits(part, wires)
        return out
    m = re.fullmatch(r"(\d+)'[bB]([01]+)", expr)
    if m:
        v = m.group(2).zfill(int(m.group(1)))
        return list(reversed(v))
    return RS.net_bits(expr, wires)


def planned_e(n):
    return max(2, math.ceil((n - 1) / 2) + 1)


def hop0_en_reg(n):
    """release edges the landing adds to its write epoch: 1 for an n = 1 qkd_landsh0 (en registered on ck_s), else 0"""
    return LG.HOP0_EN_REG if n == 1 else 0


def strap_k(n, E):
    """the K strap that makes the landing deliver age E + 1: K = (E + G - R0 + h0(n)) mod 8 with G = R0 (the KV GEN
    calendar); 0 is tied as 000 (K 8 == 0 mod 2D for the 3-bit counters)"""
    return (E + hop0_en_reg(n)) % 8 or 8


def landed_cost(n, E):
    # KVR-FWDAGE 10-19: the landing reads slot (rc - K) mod D: the station transit (hop 0 full cycle, later stations
    # half-cycle) is INSIDE the ring age E (kv-check window E_sta in [2, D - 1]), not on top of it.  Hardware o = w(t - L),
    # L = E + 1 (the o flop); landed adds the block flop: landed = E + 2, compiled age ceil(landed - 1) = E + 1 = L.
    landed = E + 2
    return dict(today=n + 1, landed=landed, added=landed - (n + 1))


def form(lines, dirs, slots):
    """lane formation on the replica netlist (unchanged rules); slots = landing frames (planner + kv_lane_stations)"""
    wires = {}
    for ln in lines:
        m = re.match(r'\s*wire\s+\[(\d+):0\]\s+(\S+);', ln)
        if m:
            wires[m.group(2)] = int(m.group(1)) + 1
    insts, where = {}, {}
    for li, ln in enumerate(lines):
        m = INST.match(ln)
        if not m or m.group(2) in ('module', 'wire', 'input', 'output', 'inout'):
            continue
        ind, mst, nm, body = m.groups()
        insts[nm] = (mst, {p: v for p, v in CONN.findall(body)})
        where[nm] = (li, ind)
    std = {nm for nm, (mst, _) in insts.items() if STD_RE.match(mst)}

    def trees(nm):
        return {CORE.match(n).group(1) for v in insts[nm][1].values() for n in re.findall(r'n_clk_core_\w+', v)}

    # bit -> driver / loads.  Replicas: a = loads, b = driver; blocks: LEF direction (INPUT load, OUTPUT driver, else both)
    drv, lds = {}, defaultdict(list)
    for nm, (mst, cs) in insts.items():
        for p, v in cs.items():
            if p in ('ck',) and nm in std:
                continue
            d = ('OUTPUT' if p == 'b' else 'INPUT') if nm in std else dirs.get(mst, {}).get(p, 'INOUT')
            for i, b in enumerate(expr_bits(v, wires)):
                if b in ('0', '1'):
                    continue
                if d in ('OUTPUT', 'INOUT'):
                    drv.setdefault(b, (nm, p, i))
                if d in ('INPUT', 'INOUT'):
                    lds[b].append((nm, p, i))
    abits = {nm: expr_bits(insts[nm][1]['a'], wires) for nm in std}
    bbits = {nm: expr_bits(insts[nm][1]['b'], wires) for nm in std}
    rtree = {nm: (CORE.match(insts[nm][1]['ck'].split('[')[0]).group(1) if CORE.match(insts[nm][1]['ck'].split('[')[0])
                  else None) for nm in std}

    def is_rst(nm):
        return any(RST_NET.match(b) for b in abits[nm] + bbits[nm] if b not in ('0', '1')) or nm.startswith('rrs_')

    # region default reset (a block's own reset port; per tree the most common one is the fallback)
    def rst_of(nm):
        cs = insts[nm][1]
        for p in RESET_PORTS:
            if p in cs and cs[p].strip() and not cs[p].strip()[0].isdigit():
                return cs[p].strip()
        return None
    tree_rst = defaultdict(Counter)
    for nm in insts:
        if nm in std:
            continue
        t, r = trees(nm), rst_of(nm)
        if len(t) == 1 and r:
            tree_rst[next(iter(t))][r] += 1

    lanes, skipped, skip_ex = [], Counter(), {}
    # A LANE is a maximal run of stations on one tree X that ends at a station R whose loads sit on ONE other tree Y.
    # It starts after its first station's driver when that driver is not exactly one same-width station on X (a block
    # on X, several stations, a landing of an upstream lane on another tree: all launch on the X root -> an ordinary
    # root -> root hop into the hop-0 station, which captures on the rising X root edge).
    for R in sorted(std):
        X = rtree[R]
        if X is None or is_rst(R):
            continue
        dst, same = set(), False
        for b in bbits[R]:
            for (Ld, p, _) in lds.get(b, ()):
                if Ld == R:
                    continue
                tl = {rtree[Ld]} if Ld in std else trees(Ld)
                tl.discard(None)
                if not tl:
                    continue
                if X in tl:
                    same = True
                else:
                    dst.add((Ld, p, tuple(sorted(tl))))
        if not dst:
            continue
        ytrees = {t for d in dst for t in d[2]}
        if same or len(ytrees) != 1:
            skipped['receiver_on_two_trees'] += 1
            skip_ex.setdefault('receiver_on_two_trees', []).append((R, X, sorted((d[0], d[1], d[2]) for d in dst)[:4]))
            continue
        Y = next(iter(ytrees))
        s = int(STD_RE.match(insts[R][0]).group(1))
        chain, cur_ = [R], R
        while True:
            ds = {drv.get(b, (None,))[0] for b in abits[cur_] if b not in ('0', '1')}
            ds.discard(None)
            P = next(iter(ds)) if len(ds) == 1 else None
            if (P is not None and P in std and rtree[P] == X and not is_rst(P)
                    and int(STD_RE.match(insts[P][0]).group(1)) == s and P not in chain):
                chain.insert(0, P)
                cur_ = P
                continue
            src = P if P is not None else (sorted(ds)[0] if ds else None)
            break
        recv = sorted({d[0] for d in dst})
        lanes.append(dict(chain=chain, S=s, src=src, src_tree=X, dst=recv[0], dsts=recv, dst_port=sorted({d[1] for d in dst})[0],
                          dst_tree=Y, n=len(chain), src_kind=('none' if src is None else 'station' if src in std else 'block')))
    used = defaultdict(set)
    for ln_ in lanes:
        for c in ln_['chain']:
            used[c].add(id(ln_))
    clash = {c for c, v in used.items() if len(v) > 1}
    if clash:
        raise SystemExit(f'kv_fwd_lanes: {len(clash)} stations claimed by two lanes (e.g. {sorted(clash)[:3]})')

    rep = dict(schema='opentallas.qwen_kv_fwd_lanes.v1', contract='lanes/LANDING-CONTRACT.md L1-L7 + section 7 (half-cycle)',
               rtl=[RTL] + CORE_RTL, lanes=[], skipped=dict(skipped), totals=Counter(), per_master=Counter(),
               owed=['fault outputs drive private open wires: each landing fault goes to the receiving block fault OR '
                     '(blocks have no spare fault input yet)',
                     'K = (planned E + h0(n)) mod 8 until the die STA (TT + FF, one E per bundle) measures S1 at every landing; then '
                     're-strap (ties only, no re-harden)',
                     'reset / boot root hops (one a net and tree with OT_KV_RST_PER_TREE) are timed by the die STA as a '
                     'release window (MCP setup E_r / hold E_r - 1) at TT and FF'])
    new = {}
    add_wires = []

    def fallback_rst(t):
        return tree_rst[t].most_common(1)[0][0] if tree_rst[t] else None
    for ln_ in lanes:
        ch, S, n = ln_['chain'], ln_['S'], ln_['n']
        X, Y = ln_['src_tree'], ln_['dst_tree']
        en = (rst_of(ln_['src']) if ln_['src'] and ln_['src'] not in std else None) or fallback_rst(X)
        rs = rst_of(ln_['dst']) if ln_['dst'] not in std else None
        rs = rs or fallback_rst(Y)
        if en is None or rs is None:
            skipped['no_reset_net'] += 1
            continue
        E = planned_e(n)
        K = strap_k(n, E)
        kb = [(K >> j) & 1 for j in range(3)]
        cost = landed_cost(n, E)
        ck_x, ck_y = f'n_clk_core_{X}[0]', f'n_clk_core_{Y}[0]'
        for j, c in enumerate(ch):
            A, B = insts[c][1]['a'], insts[c][1]['b']
            last = j == n - 1
            eb, cko = f'n_{c}__eb', f'n_{c}__cko'
            prev = ch[j - 1] if j else None
            if not last:
                add_wires += [f'  wire [0:0] {eb};', f'  wire [0:0] {cko};']
                if j == 0:
                    mst = f'qkd_rlysh0_{S}'
                    conn = f'.ck({ck_x}), .en({en}), .a({A}), .b({B}), .eb({eb}[0]), .ck_o({cko}[0])'
                else:
                    mst = f'qkd_rlysh_{S}'
                    conn = f'.ckf(n_{prev}__cko[0]), .ea(n_{prev}__eb[0]), .a({A}), .b({B}), .eb({eb}[0]), .ck_o({cko}[0])'
            else:
                hi, lo, flt = f'n_{c}__hi', f'n_{c}__lo', f'n_{c}__flt'
                add_wires += [f'  wire [0:0] {hi};', f'  wire [0:0] {lo};', f'  wire [0:0] {flt};']
                ks = ', '.join(f'.k{q}({hi if kb[q] else lo}[0])' for q in range(3))
                tail = f'.ck({ck_y}), .rs({rs}), {ks}, .tie_hi({hi}[0]), .tie_lo({lo}[0]), .b({B}), .fault({flt}[0])'
                if n == 1:
                    mst = f'qkd_landsh0_{S}'
                    conn = f'.ck_s({ck_x}), .en({en}), .a({A}), {tail}'
                else:
                    mst = f'qkd_landsh_{S}'
                    conn = f'.ckf(n_{prev}__cko[0]), .ea(n_{prev}__eb[0]), .a({A}), {tail}'
            new[c] = (mst, conn)
            rep['per_master'][mst] += 1
        rep['lanes'].append(dict(stations=ch, S=S, n=n, src=ln_['src'], src_kind=ln_['src_kind'], src_tree=X, dst=ln_['dst'],
                                 dsts=ln_['dsts'], dst_port=ln_['dst_port'],
                                 dst_tree=Y, en=en, rs=rs, E_planned=E, K=K, h0=hop0_en_reg(n), **cost))
        rep['totals']['lanes'] += 1
        rep['totals']['stations'] += n
        rep['totals']['bits'] += S
        rep['totals'][f'{X}->{Y}'] += 1
    # KV-LANDSLOT 10-18: the landing must sit in a frame the die planner reserved for it (kv_land_slot.py ->
    # qkd_rly_<W>_land, kv_rly_std.py lays its forward replicas at the landing outlines; RUN/rly_std.json land_slots).
    # A 36 / 296 / 528-b landing outside one does not fit its station outline (KV-LANEKITS util 181 / 128 / 126 %)
    lastst = {L['stations'][-1]: L for L in rep['lanes']}
    unslot = [dict(station=s, S=L['S'], src_tree=L['src_tree'], dst_tree=L['dst_tree'], dst=L['dst'])
              for s, L in sorted(lastst.items()) if s not in slots]
    rep['land_slots'] = dict(reserved=len(slots), slotted=len(lastst) - len(unslot), unslotted=len(unslot),
                             unslotted_wide=sum(1 for u in unslot if u['S'] != 1), unslotted_examples=unslot[:60],
                             reserved_unused=sorted(set(slots) - set(lastst))[:200],
                             reserved_unused_count=len(set(slots) - set(lastst)))
    for s, L in lastst.items():
        L['land_slot'] = s in slots
    rep['skipped'] = dict(skipped)
    rep['skipped_examples'] = {k: v[:40] for k, v in skip_ex.items()}
    rep['totals'] = dict(rep['totals'])
    rep['per_master'] = dict(rep['per_master'])
    return dict(rep=rep, new=new, add_wires=add_wires, where=where, lastst=lastst)


def render(lines0, F):
    """the laned netlist: lane masters on the formed stations + their clock / epoch / strap wires"""
    lines = list(lines0)
    for c, (mst, conn) in F['new'].items():
        li, ind = F['where'][c]
        m = INST.match(lines[li])
        if not m or m.group(3) != c:
            raise ValueError(f'render: line {li} is not instance {c} (lane formation stale against the netlist)')
        lines[li] = f'{ind}{mst} {c} ({conn});'
    k = max(i for i, ln in enumerate(lines) if re.match(r'\s*wire\b', ln))
    lines[k + 1:k + 1] = F['add_wires']
    return lines


def reach_classes():
    return sorted((int(k), float(v)) for k, v in
                  (part.split(':') for part in os.environ.get('OT_KV_REACH_W', '36:400,296:370,100000:340').split(',')))


def iterate(run, case, lines, elef, dirs, slots, max_iter=int(os.environ.get('OT_KV_STATIONS_ITER', '6'))):
    """HKV-STATIONS 10-19: form lanes -> adapt -> actual pin reach audit; every overreach becomes a REAL relay stage
    (kv_lane_stations: BEFORE / AFTER, every slice of the bus) and every unslotted wide landing a legal free frame; the
    lanes are re-formed so the new stages take their lane role and the lane E / K / landed age follow from n.  Stops at
    PASS, or when nothing more can be placed (the final audit in main() then refuses)."""
    import kv_lane_stations as KS
    classes = reach_classes()
    vm = {}
    for fam in ('qkd_rlysh0_', 'qkd_rlysh_', 'qkd_landsh_', 'qkd_landsh0_'):
        for S in (1, 36, 296, 528):
            f = ROOT / f'physical/ref_tile/{fam}{S}/views/{fam}{S}/{fam}{S}.lef'
            if f.exists():
                vm.update({m['name']: m for m in LO.C.parse_lef(f.read_text())})
    vlef = '\n'.join(RS.lef_macro(ROOT / f'physical/ref_tile/{n}/views/{n}/{n}.lef')[0] for n in sorted(vm)
                     if not re.search(rf'^MACRO {n}\s*$', elef, re.M))
    t = elef.rstrip()
    end = re.search(r'^END LIBRARY\s*$', t, re.M)
    elef_all = (t[:end.start()] + vlef + '\n' + t[end.start():]) if end else t + '\n' + vlef + '\n'
    macros = {m['name']: m for m in LO.C.parse_lef(elef)}
    macros.update(vm)
    for m in macros.values():
        m['pd'] = {x['name']: x for x in m['pins']}
    die = KS.die_area(case)
    place0 = (case / 'place.tcl').read_text()
    pre, place = list(lines), place0
    slots = dict(slots)
    inserted, moved, records, refused, history = [], [], [], [], []
    F = incident = None
    stale = True                                  # pre / place changed since F was formed
    for it in range(1, max_iter + 1):
        F = form(pre, dirs, slots)
        stale = False
        lane_lines = render(pre, F)
        net = KS.Net(lane_lines, dirs, expr_bits)
        masters = {n: v[0] for n, v in net.insts.items()}
        # SLOT: a wide landing with no planner frame -> a legal free frame of its own outline within reach
        uns = [(s, L) for s, L in sorted(F['lastst'].items()) if s not in slots and L['S'] != 1]
        if uns:
            geo = KS.Geo(macros, KS.parse_place(place), die, dirs)
            geo.build_bins(masters)
            for s, L in uns:
                lm = F['new'][s][0]
                r = KS.reach_of(L['S'], classes)
                cons, cin = [], []
                for i, b in enumerate(net.bits(s, 'a')):
                    d = net.drv.get(b) if b not in ('0', '1') else None
                    if d:
                        cin.append((geo.pin(lm, f'a[{i}]') or geo.pin(lm, 'a'), geo.ep_points(d[0], masters[d[0]], d[1], d[2]), r))
                for i, b in enumerate(net.bits(s, 'b')):
                    for e in net.lds.get(b, ()):
                        if e[0] != s:
                            cons.append((geo.pin(lm, f'b[{i}]') or geo.pin(lm, 'b'), geo.ep_points(e[0], masters[e[0]], e[1], e[2]), r))
                if L['n'] > 1:
                    P = L['stations'][-2]
                    cons.append((geo.pin(lm, 'ckf'), geo.ep_points(P, masters[P], 'ck_o', 0), r))
                    cons.append((geo.pin(lm, 'ea'), geo.ep_points(P, masters[P], 'eb', 0), r))
                if L['n'] > 1:
                    cin += cons[-2:]
                    cons = cons[:-2]
                xy = geo.find(lm, cin + cons, ignore=(s,))
                side = 'both'
                if xy is None:
                    # the landing frame beside its receiver (loads within reach); the driver side becomes an ordinary
                    # overreaching hop that the next iteration repairs with real stations
                    xy, side = geo.find(lm, cons, ignore=(s,)), 'receiver'
                if xy is None:
                    refused.append(dict(op='slot', station=s, master=lm, reason='no legal free landing frame within reach'))
                    continue
                m = macros[lm]
                geo.put(xy[0], xy[1], m['W'], m['H'], s)
                place = KS.move(place, s, xy)
                slots[s] = dict(source='kv_lane_stations', master=lm, x_um=xy[0] / 1000, y_um=xy[1] / 1000)
                moved.append(s)
                records.append(dict(op='slot', inst=s, master=lm, S=L['S'], within_reach=side, x_um=xy[0] / 1000, y_um=xy[1] / 1000,
                                    w_um=m['W'] / 1000, h_um=m['H'] / 1000, iteration=it))
            history.append(dict(iteration=it, slotted=[s for s, _ in uns if s in slots]))
            if any(s in slots for s, _ in uns):
                continue
        placed, orientation = LO.adapt(place, F['new'], vm)
        incident = LR.audit('\n'.join(lane_lines), elef_all, place, placed, orientation, classes,
                            extra=set(inserted) | set(moved))
        history.append(dict(iteration=it, status=incident['status'], **incident['summary']))
        print(f"kv_lane_stations: iteration {it}: {incident['status']} {json.dumps(incident['summary'])}", flush=True)
        if incident['status'] == 'PASS':
            break
        pairs = {(g['src'][0], g['dst'][0]) for g in incident['groups'] if g['transport'] and g['after_overreach_bits']}
        history[-1]['violating'] = sorted(pairs)[:40]
        history[-1]['unmeasured'] = [dict(net=u.get('net'), reason=u.get('reason'), src=u.get('src'), dst=u.get('dst'),
                                          endpoint=u.get('endpoint')) for u in incident['unmeasured'][:20]]
        geo = KS.Geo(macros, KS.parse_place(placed), die, dirs)
        geo.build_bins(masters)
        edits, recs, ref = KS.plan_repairs(pairs, pre, lane_lines, F['new'], F['rep']['lanes'], geo, dirs, expr_bits,
                                           classes, it, None)
        refused += [dict(r, iteration=it) for r in ref]
        (run / 'lane_stations.partial.json').write_text(json.dumps(dict(history=history, stations=records + recs,
                                                                         refused=refused), indent=1, default=str) + '\n')
        if not edits:
            break
        pre, place = KS.apply_edits(pre, place, edits, expr_bits)
        stale = True
        inserted += [e['inst'] for e in edits]
        records += [dict(r, iteration=it) for r in recs]
    if stale and F is not None:
        # KVR-PLACE2 10-19: the last iteration's edits came after the last formation (max_iter reached); render() writes
        # lane masters at F's LINE INDICES, so a stale F overwrote the inserted stations' lines (kvs14r-f9ef813ab-kvrplace:
        # die.v lost 1,000+ AFTER stages that lane_stations / the audit scope still named -> KeyError).  Re-form on the
        # final netlist; the final audit in main() measures it (the in-loop status is not final).
        F = form(pre, dirs, slots)
        incident = None
    # lane records: inserted stages and the receiving-side stage after a landing are fixed latency on the bus
    ins, post = set(inserted), defaultdict(int)
    # KVR-PLACE 10-19: an AFTER progress stage chains (P -> N1 -> N2 -> load): its depth counts on P's lane / bus
    after_of = {r['inst']: r['of'] for r in records if r['op'] == 'after'}
    after_root = {}
    for n_ in after_of:
        d_, q_ = 0, n_
        while q_ in after_of:
            d_, q_ = d_ + 1, after_of[q_]
        after_root[n_] = q_
        post[q_] = max(post[q_], d_)             # forks of one stage are parallel: one edge each level
    for L in F['rep']['lanes']:
        L['inserted_stations'] = [c for c in L['stations'] if c in ins]
        p = post.get(L['stations'][-1], 0)
        if p:
            L['post_stages'] = p
            L['today'] += p
            L['landed'] += p
    sm = defaultdict(lambda: dict(count=0, area_um2=0.0))
    for r in records:
        if r['op'] in ('before', 'after'):
            sm[r['predicted_master']]['count'] += 1
            sm[r['predicted_master']]['area_um2'] += r['w_um'] * r['h_um']
    summary = dict(inserted=len(inserted), moved_landings=len(moved), refused=len(refused),
                   iterations=len(history), per_master=dict(sm),
                   added_area_mm2=round(sum(v['area_um2'] for v in sm.values()) / 1e6, 6),
                   lanes_with_inserted=sum(1 for L in F['rep']['lanes'] if L['inserted_stations']),
                   lanes_with_post_stage=sum(1 for L in F['rep']['lanes'] if L.get('post_stages')),
                   final_status=incident['status'] if incident else None)
    # bus-level added stages outside any lane (kv_static_ages.fwd_overlay; lane stages already ride n / landed)
    import kv_static_ages as KSA
    in_lane = {c for L in F['rep']['lanes'] for c in L['stations']}
    pos = defaultdict(set)
    for r in records:
        if r['op'] == 'before' and r['inst'] not in in_lane:
            pos[KSA.lane_bid(r['of'])].add(re.sub(r'__s\d+$', '', r['of']))
    for q_, d_ in post.items():
        if q_ not in in_lane and d_:
            # AFTER stages behind a plain (non-lane) replica: fixed latency on its bus, one entry per level
            for j_ in range(d_):
                pos[KSA.lane_bid(q_)].add(re.sub(r'__s\d+$', '', q_) + f'__after{j_}')
    F['rep']['plain_added_stages'] = {b: len(v) for b, v in sorted(pos.items())}
    summary['plain_added_stages'] = F['rep']['plain_added_stages']
    record = dict(schema='opentallas.kv_lane_stations.v1', tool='tools/qwen_kv_die/kv_lane_stations.py',
                  rule='every overreaching transport hop of a forwarded lane gets a REAL relay stage in every slice of '
                       'its bus (closed qkd_rlys_<S> replica re-formed into its lane role) or a legal moved landing frame',
                  summary=summary, history=history, stations=records, refused=refused)
    return F, pre, dict(inserted=inserted, moved=moved, extra=set(inserted) | set(moved), place_pre=place,
                        summary=summary, record=record)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--netlist-only', action='store_true',
                    help='bind check before the lane masters have closed views (no LEF / libs; never a physical run)')
    ap.add_argument('--dry-run', action='store_true', help='write RUN/fwd_lanes.dry.json only')
    a = ap.parse_args(argv)
    case, libs = a.run / 'case_kv', a.run / 'libs'
    lines = (case / 'die.v').read_text().split('\n')
    elef = (case / 'elements.lef').read_text()
    dirs = defaultdict(dict)
    cur = pin = None
    for ln in elef.split('\n'):
        s = ln.strip()
        if s.startswith('MACRO '):
            cur, pin = s.split()[1], None
        elif cur and s.startswith('PIN '):
            pin = s.split()[1]
        elif cur and pin and s.startswith('DIRECTION'):
            dirs[cur][pin] = s.split()[1].rstrip(';').upper()
    rsj = a.run / 'rly_std.json'
    slots = json.loads(rsj.read_text()).get('land_slots', {}) if rsj.exists() else {}
    lines0, stations = lines, None
    if a.netlist_only or a.dry_run:
        F = form(lines, dirs, slots)
    else:
        F, lines0, stations = iterate(a.run, case, lines, elef, dirs, slots)
    rep, new, add_wires, where = F['rep'], F['new'], F['add_wires'], F['where']
    if stations is not None:
        rep['stations'] = stations['summary']
    if a.dry_run:
        (a.run / 'fwd_lanes.dry.json').write_text(json.dumps(rep, indent=1) + '\n')
        print(json.dumps(dict(totals=rep['totals'], skipped=rep['skipped'], per_master=rep['per_master'])))
        return 0
    lines = render(lines0, F)
    if not (case / 'die.v.prefwd').exists():
        shutil.copy(case / 'die.v', case / 'die.v.prefwd')
    if stations is not None and stations['inserted']:
        # HKV-STATIONS: die.v.prestations = the replica netlist as planned; die.v.prefwd = + the inserted relay stations
        if not (case / 'die.v.prestations').exists():
            shutil.copy(case / 'die.v.prefwd', case / 'die.v.prestations')
        (case / 'die.v.prefwd').write_text('\n'.join(lines0))
    (case / 'die.v').write_text('\n'.join(lines))
    masters = sorted(rep['per_master'])
    # the lane stations / landings keep the relay standard's connections, so a lane master of width S ties the same
    # DECLARED spare input bits low as qkd_rlys_<S> (kv_rly_std.py die.v.pads.json); kvs14c laned strict bind: 11 lane
    # masters INPUT_TIED on 'a' (e.g. qkd_rlysh_36 .a({24'b0, ...})) because only the qkd_rlys_* pads were declared
    pf = case / 'die.v.pads.json'
    if pf.exists():
        pj = json.loads(pf.read_text())
        pads = pj.setdefault('pads', {})
        for mst in masters:
            mm = re.match(r'^qkd_(?:rlysh0?|landsh0?)_(\d+)$', mst)
            src = pads.get(f'qkd_rlys_{mm.group(1)}') if mm else None
            if src and mst not in pads:
                pads[mst] = dict(reason=f'forwarded lane master on a qkd_rlys_{mm.group(1)} run (kv_fwd_lanes.py): '
                                 + src['reason'], ports=src['ports'])
        if not (case / 'die.v.pads.json.prefwd').exists():
            shutil.copy(pf, case / 'die.v.pads.json.prefwd')
        pf.write_text(json.dumps(pj, indent=1) + '\n')
    views, missing = {}, []
    for mst in masters:
        vd = f'physical/ref_tile/{mst}/views/{mst}'
        if (ROOT / vd / f'{mst}.lef').exists():
            views[mst] = vd
        else:
            missing.append(mst)
    if missing and not a.netlist_only:
        raise SystemExit(f'kv_fwd_lanes: no closed view for {missing} (gate + route the lane kits, or --netlist-only)')
    ls_ = rep['land_slots']
    if ls_['unslotted_wide'] and not a.netlist_only:
        (a.run / 'fwd_lanes.json').write_text(json.dumps(rep, indent=1) + '\n')
        raise SystemExit(f"kv_fwd_lanes: {ls_['unslotted_wide']} wide landings have no reserved landing frame (plan the die "
                         f"with OT_KV_LANDSLOT=1; e.g. {ls_['unslotted_examples'][:3]})")
    # Qualify the actual replacement abstracts before a costly real-case placement.
    # Keep Y orientation; remove an X mirror only when the closed view cannot support it.
    if not a.netlist_only:
        macros = {m['name']: m for mst, vd in views.items()
                  for m in LO.C.parse_lef((ROOT / vd / f'{mst}.lef').read_text())}
        pf = case / 'place.tcl'
        if not (case / 'place.tcl.prefwd').exists():
            shutil.copy(pf, case / 'place.tcl.prefwd')
        if stations is not None and (stations['inserted'] or stations['moved']):
            if not (case / 'place.tcl.prestations').exists():
                shutil.copy(case / 'place.tcl.prefwd', case / 'place.tcl.prestations')
            (case / 'place.tcl.prefwd').write_text(stations['place_pre'])
        placed, orientation = LO.adapt((case / 'place.tcl.prefwd').read_text(), new, macros)
        pf.write_text(placed)
        (case / 'lane_orientations.json').write_text(json.dumps(orientation, indent=1) + '\n')
        rep['orientation_changes'] = len(orientation['changes'])
    add_lef = []
    for mst, vd in views.items():
        blk, sz = RS.lef_macro(ROOT / vd / f'{mst}.lef')
        if not re.search(rf'^MACRO {mst}\s*$', elef, re.M):
            add_lef.append(blk)
    if add_lef:
        if not (case / 'elements.lef.prefwd').exists():
            shutil.copy(case / 'elements.lef', case / 'elements.lef.prefwd')
        t = elef.rstrip()
        end = re.search(r'^END LIBRARY\s*$', t, re.M)
        t = (t[:end.start()] + '\n'.join(add_lef) + '\n' + t[end.start():]) if end else t + '\n' + '\n'.join(add_lef) + '\n'
        (case / 'elements.lef').write_text(t + '\n')
    if not a.netlist_only:
        # Bounding-box fit does not qualify a changed pin face. Refuse before
        # real-case placement if any incident transport bit exceeds its class.
        classes = sorted((int(k), float(v)) for k, v in
                         (part.split(':') for part in os.environ.get('OT_KV_REACH_W',
                                                                    '36:400,296:370,100000:340').split(',')))
        incident = LR.audit((case / 'die.v').read_text(), (case / 'elements.lef').read_text(),
                            (case / 'place.tcl.prefwd').read_text(), pf.read_text(), orientation, classes,
                            extra=stations['extra'] if stations else ())
        (case / 'lane_incident_reach.json').write_text(json.dumps(incident, indent=1) + '\n')
        rep['reach_gate'] = dict(status=incident['status'], **incident['summary'])
        if stations is not None:
            (a.run / 'lane_stations.json').write_text(json.dumps(stations['record'], indent=1) + '\n')
        if incident['status'] != 'PASS':
            raise SystemExit('kv_fwd_lanes: actual adapted lane pin reach FAIL: '
                             + json.dumps(incident['summary'])
                             + '; repair reservation/stages and static E/K ages before physical submission '
                             '(case_kv/lane_incident_reach.json)')
    if views and (libs / 'views.json').exists():
        vj = json.loads((libs / 'views.json').read_text())
        for mst, vd in views.items():
            for c in CORNERS:
                src = ROOT / vd / f'{mst}_{c}.lib'
                if src.exists():
                    txt = re.sub(r'library\s*\(\s*"?[^")]+"?\s*\)', f'library (qfd_etm_{mst}_{c})', src.read_text(), count=1)
                    (libs / f'qfd_etm_{mst}_{c}.lib').write_text(txt)
            vj['views'][mst] = dict(bound=True, view=vd, module=mst, cls='fwd_lane')
        (libs / 'views.json').write_text(json.dumps(vj, indent=1) + '\n')
    ex = a.run / 'expand.json'
    ej = json.loads(ex.read_text()) if ex.exists() else dict(schema='opentallas.qwen_kvsys_expand.v1', frames={})
    ej.setdefault('leaves', {}).update({m: dict(view=f'physical/ref_tile/{m}/views/{m}', rtl=RTL, rtl_deps=CORE_RTL)
                                        for m in masters})
    ex.write_text(json.dumps(ej, indent=1) + '\n')
    if missing:
        (case / 'FWD_NETLIST_ONLY').write_text('kv_fwd_lanes.py --netlist-only: lane masters without closed views: '
                                              + ' '.join(missing) + '\n')
    rep['views_bound'] = sorted(views)
    rep['views_missing'] = missing
    (a.run / 'fwd_lanes.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(dict(totals=rep['totals'], skipped=rep['skipped'], per_master=rep['per_master'], missing=missing,
                          land_slots={k: v for k, v in rep['land_slots'].items() if not k.endswith(('examples', 'unused'))})))
    return 0


if __name__ == '__main__':
    sys.exit(main())
