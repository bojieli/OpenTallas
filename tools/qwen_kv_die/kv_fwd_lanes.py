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
own tie_hi / tie_lo (never a netlist literal), K = planned E (contract L5: E = max over corners of 1 + ceil(-S1/T); until
the die STA measures S1 the S81 p4j half-cycle fit ceil((n-1)/2) + 1, >= 2, as tools/qwen_split/fwd_lane_price.py).
Reset / boot nets are NOT laned (they define the epochs; OT_KV_RST_PER_TREE keeps one root hop a tree, timed by the die
STA release window).  fault outputs drive private open wires (recorded: owed to the block fault OR).

    kv_fwd_lanes.py --run RUN [--netlist-only] [--dry-run]
rewrites RUN/case_kv/die.v (original kept as die.v.prefwd), adds the lane masters to expand.json leaves (and their closed
views / LEF / libs when physical/ref_tile/qkd_<fam>_<S>/views exist), writes RUN/fwd_lanes.json (every lane: bus slice,
n, source / receiving block and region, planned E, latency today n + 1 vs landed 1 + (n-2)/2 + 1 + E + 1).
"""
import argparse
import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_rly_std as RS        # noqa: E402

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


def landed_cost(n, E):
    # hop 0 full-cycle (rising capture), later stations half-cycle, the ring, the E handoff, the block flop
    N = n - 1
    st = (1 + (N - 1) / 2) if N >= 1 else 0
    return dict(today=n + 1, landed=st + 1 + E + 1, added=st + 2 + E - (n + 1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--netlist-only', action='store_true',
                    help='bind check before the lane masters have closed views (no LEF / libs; never a physical run)')
    ap.add_argument('--dry-run', action='store_true', help='write RUN/fwd_lanes.dry.json only')
    a = ap.parse_args(argv)
    case, libs = a.run / 'case_kv', a.run / 'libs'
    lines = (case / 'die.v').read_text().split('\n')
    wires = {}
    for ln in lines:
        m = re.match(r'\s*wire\s+\[(\d+):0\]\s+(\S+);', ln)
        if m:
            wires[m.group(2)] = int(m.group(1)) + 1
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
                     'K = planned E until the die STA (TT + FF, one E per bundle) measures S1 at every landing; then '
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
        K = E % 8 or 8
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
                                 dst_tree=Y, en=en, rs=rs, E_planned=E, K=K, **cost))
        rep['totals']['lanes'] += 1
        rep['totals']['stations'] += n
        rep['totals']['bits'] += S
        rep['totals'][f'{X}->{Y}'] += 1
    # KV-LANDSLOT 10-18: the landing must sit in a frame the die planner reserved for it (kv_land_slot.py ->
    # qkd_rly_<W>_land, kv_rly_std.py lays its forward replicas at the landing outlines; RUN/rly_std.json land_slots).
    # A 36 / 296 / 528-b landing outside one does not fit its station outline (KV-LANEKITS util 181 / 128 / 126 %)
    rsj = a.run / 'rly_std.json'
    slots = json.loads(rsj.read_text()).get('land_slots', {}) if rsj.exists() else {}
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
    if a.dry_run:
        (a.run / 'fwd_lanes.dry.json').write_text(json.dumps(rep, indent=1) + '\n')
        print(json.dumps(dict(totals=rep['totals'], skipped=rep['skipped'], per_master=rep['per_master'])))
        return 0
    for c, (mst, conn) in new.items():
        li, ind = where[c]
        lines[li] = f'{ind}{mst} {c} ({conn});'
    k = max(i for i, ln in enumerate(lines) if re.match(r'\s*wire\b', ln))
    lines[k + 1:k + 1] = add_wires
    if not (case / 'die.v.prefwd').exists():
        shutil.copy(case / 'die.v', case / 'die.v.prefwd')
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
