#!/usr/bin/env python3
"""S81-DV REAL-VIEW binding mode (S81-BIND, 10-17; owner no-stubs rule 10-14, stub audit 0da S-1..S-11).

Builds the die netlist that binds every plan master to its real RTL module (when one exists) instead of the pin-only
dv_<inst> stand-ins of the diagnostic case, then runs the STRICT tools/die_port_bind.py on it.

  * masters      results/arch/s81_dv_1016/bind/bind_table.json: plan master -> RTL module, source ref, closed view,
                 parameters per instance, and a PORT MAP plan endpoint (port, dir) -> RTL port lanes.  Plan endpoints
                 with no RTL port are listed (plan_port_not_in_rtl) and their nets stay undriven / unread, so the strict
                 check counts them.  Masters with no RTL are instantiated under their PLAN master name (no module ->
                 UNBOUND) and listed as OPEN BINDINGS with their owner -- never stubbed.
  * relays       every planned station is a real F1 relay master dsfd_dvrly_<W>_<dir> (ot_s81_rly RSREG=1 + kept ck_o
                 inverter pair): 276 b closed views (s81dv_rly_276_*); 68 / 512 b exact-width masters (RTL
                 dsfd_rly_masters_dvw.sv; views owed).  No bare flip-flops.
  * reset        regional SYNCHRONOUS-release reset relay tree (die standard item 2): die pad rst_n -> 2-stage root
                 synchroniser -> one dsfd_rly_1_<dir> station per 400-um grid cell on a BFS tree over the block-free
                 streets; every relay rs / block reset pin reads the station of its cell (one hop); each station's rs is
                 its parent's output (async assert, release one regional clock edge per hop).  Release depth per leaf is
                 recorded for the reset release calendar.  No global reset net.
  * clocks       one regional root input ck_<region> per region (DIE-CLOCK neighbour-relative roots); blocks clock on
                 their region root.  S81.CLK (10-21): regions are GEOMETRIC (tools/s81_dv/geo_clock.py: grid cells
                 ck_g<i>_<j>, oversize blocks ck_b_<block>, reset stations on the root of their own cell, reset-tree
                 crossings re-registered by one <child>_xk stage in the receiving region); bind table
                 "clock_regions": {"mode": "logical"} restores the plan-group roots ck_cl*; link hop 0 forwarded clock = the source master's real forwarded-clock output where
                 its RTL has one (slice ck_line / ck_v / ck_xc), else a clock-forward cell (BUFx8) on the source
                 region's root at the source pin.  Station k+1 ck = station k ck_o (F1).
  * hop-0 gate   S81-LBGAP/G1 (10-18, LANDING-CONTRACT L3): on every LANDED lane the hop-0 forward cell is a clock gate
                 (ICGx4, CLK = the source root / the source master's forwarded clock) opened by a released reset, so the
                 landing's ck_f edge 0 is a calendar source edge G for any flight time dL and wc is cleared while ck_f is
                 stopped.  Calendar R0 = G + (N mod 2) per lane (R0 = first read edge of the landing, N stations):
                 the gate enable is the source block's reset leaf, delayed at the source by gate-calendar reset stations
                 when the source would open early; otherwise the LANDING rs is its leaf delayed at the receiver.  K = E
                 for every lane (no strap offset); rs releases before the lane's first clock edge reaches the ring.
"""
from __future__ import annotations

import collections
import json
import math
import os
import re
import subprocess

from frame_bind import instance_clocks
import geo_clock as GC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRID = 400.0                      # reset station grid (<= measured reach 405 um per hop)
FWD = 'BUFx8_ASAP7_75t_R'          # clock-forward cell (hop 0 source)
INV = 'INVx2_ASAP7_75t_R'
ICG = 'ICGx4_ASAP7_75t_R'         # S81-LBGAP/G1: hop-0 clock gate of a landed lane (LANDING-CONTRACT L3)
LAND_W = (70, 276, 512, 562, 682)  # dsfd_dvland_<W> tiles (rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv)          # reset polarity (active-high block reset pins)
RST_RLY = {'EW': 'dsfd_rly_1_EW', 'WE': 'dsfd_rly_1_WE', 'NS': 'dsfd_rly_1_NS', 'SN': 'dsfd_rly_1_NS'}   # SN = NS mirrored (MX)
ORIENT = {'WE': 'R0', 'EW': 'MY', 'NS': 'R90', 'SN': 'R270'}     # dsfd_rly_1_WN (in W, out N) turned to the tree edge
CELL_MODELS = f'''// ASAP7 standard cells used by the S81-DV bound die top (functional models of library cells, not stand-ins)
module {FWD} (input A, output Y); assign Y = A; endmodule
module {INV} (input A, output Y); assign Y = ~A; endmodule
module {ICG} (input CLK, input ENA, input SE, output GCLK);   // latch transparent while CLK is low, ANDed with CLK
    reg en_l;
    /* verilator lint_off COMBDLY */
    always_latch if (!CLK) en_l = ENA | SE;
    /* verilator lint_on COMBDLY */
    assign GCLK = CLK & en_l;
endmodule
'''


def block_clock(table, master, region, instance=None):
    """Use the physical master's declared domain, including peer-clock ports."""
    if instance is not None and instance in table.get('instance_clock_ports', {}):
        return dict(instance_clocks(table, dict(name=instance, master=master), region))[table['masters'][master]['clk']]
    return table['masters'][master].get('clock_port', f'ck_{region}')


def regional_clock(table, blocks, regions, name):
    """Legacy regional source unless this instance explicitly declares its root."""
    if name in table.get('instance_clock_ports', {}):
        return block_clock(table, blocks[name]['master'], regions[name], name)
    return f'ck_{regions[name]}'


def endpoint_clock_override(table, blocks, regions, link, source):
    """Optional declared clock of one packed plan-port; never guess A/B from names."""
    end = link['e'][0 if source else 1]
    block = blocks[end[0]]
    master = table['masters'][block['master']]
    port = f"{end[1]}.{'o' if source else 'i'}"
    rule = master.get('ports', {}).get(port, {})
    cp = rule.get('clock_port')
    if cp is None:
        if port in master.get('port_clock_required', []):
            raise ValueError(f"{block['name']}.{port}: explicit clock_port required")
        return None
    if rule.get('ck'):
        raise ValueError(f"{block['name']}.{port}: clock_port with a forwarded-clock output is unsupported")
    declared = master.get('clock_ports') or [master['clk']] + list(master.get('clk_extra', []))
    if not isinstance(cp, str) or cp not in declared:
        raise ValueError(f"{block['name']}.{port}: unsupported clock_port {cp!r}")
    width = table.get('rtl_widths', {}).get(master['module'], {}).get(cp)
    if type(width) is not int or width != 1:
        raise ValueError(f"{block['name']}.{port}: clock_port {cp} must be a declared scalar input")
    if block['name'] not in table.get('instance_clock_ports', {}):
        raise ValueError(f"{block['name']}.{port}: explicit distinct instance clock mapping required")
    clocks = dict(instance_clocks(table, block, regions[block['name']]))
    if cp not in clocks:
        raise ValueError(f"{block['name']}.{port}: clock_port {cp} has no exact instance mapping")
    return clocks[cp]


def endpoint_clock(table, blocks, regions, link, source):
    clock = endpoint_clock_override(table, blocks, regions, link, source)
    block = blocks[link['e'][0 if source else 1][0]]
    return clock if clock is not None else regional_clock(table, {block['name']: block}, regions, block['name'])

def reset_local_leaf(rst, leaf, clock, xy, master, consumer, enabled=True):
    """Land a reset release on its consuming root before pricing its calendar.

    The street tree is geometric; a block, frame calendar, or landing may use
    a different root from the nearest street station. Reuse one receiving
    stage per leaf/root and record its extra release edge explicitly.
    """
    if not enabled:
        return leaf
    source = rst['net_clocks'][leaf]
    if source == clock:
        return leaf
    key = (leaf, clock)
    taps = rst.setdefault('local_leaf_taps', {})
    if key not in taps:
        net = 'rsleaf_' + re.sub(r'[^A-Za-z0-9_]', '_', leaf + '_' + clock)
        taps[key] = net
        rst['verilog'] += [f'  wire {net};',
            f'  {master} st_{net} (.ck({clock}), .rs({leaf}), .i({leaf}), .o({net}));   '
            f'// local reset release crossing {source} -> {clock}']
        rst['depth'][net] = rst['depth'][leaf] + 1
        rst['net_clocks'][net] = clock
        rst['place'].append(dict(inst=f'st_{net}', master=master, orient='R0',
                                 xy=[round(xy[0], 3), round(xy[1], 3)], kind='reset_leaf_crossing'))
        summary = rst['summary']
        summary['stations'] += 1
        summary['release_crossings'] += 1
        summary.setdefault('leaf_crossings', []).append(dict(parent=('rst_root1' if leaf == 'rst_sync1' else f'st_{leaf}'), stage=f'st_{net}',
            src_region=source.removeprefix('ck_'), dst_region=clock.removeprefix('ck_'), consumer=consumer,
            release_src=rst['depth'][leaf], release_dst=rst['depth'][net]))
        summary['crossings'].append(summary['leaf_crossings'][-1])
        summary['max_release_depth'] = max(summary['max_release_depth'], rst['depth'][net])
    return taps[key]


def region_of(bl, pitch):
    g = bl['group']
    if g.startswith('cl'):
        return g
    col = int((bl['x'] + bl['w'] / 2) // pitch)
    return f'{g}{col}'


def rly_master(b, d, prefix='dsfd_dvrly'):
    return f'{prefix}_{b}_{d}'


def git_show(ref, path):
    return subprocess.run(['git', '-C', os.environ.get('OT_GIT_DIR', str(ROOT)), 'show', f'{ref}:{path}'], capture_output=True, check=True).stdout


def _read_at(ref, path):
    """text of path at ref (None = absent); ref None = the worktree file, else HEAD of the worktree's git"""
    if ref is None:
        p = ROOT / path
        if p.is_file():
            return p.read_text()
        ref = 'HEAD'
        gd = str(ROOT)
    else:
        gd = os.environ.get('OT_GIT_DIR', str(ROOT))
    r = subprocess.run(['git', '-C', gd, 'show', f'{ref}:{path}'], capture_output=True)
    return r.stdout.decode() if r.returncode == 0 else None


def land_view_reset_stages(master, view, read=_read_at):
    """MU-DIE-S81/PO2 (10-19): reset-landing stage count RL of the CLOSED VIEW bound for landing master dsfd_dvland_<x>.
    view = bind table land_views[master] ({"ref": <record commit/ref>, "kit": physical/ref_tile/<spec>}) or None (= the
    worktree's kit view).  The view's abstract.json names its closure-loop job (orfs_dir .../closure-loop/<job>/...); the
    job's source commit (verdict.json source_commit at the view ref, else the job name's trailing sha) holds the kit
    spec.json the view was hardened from: RL = reset_landing.stages when reset_landing.enable, else 0.
    Returns dict(rl=int|None, job, source, kit, error)."""
    import re as _re
    view = view or {}
    ref = view.get('commit') or view.get('ref')
    kit = view.get('kit') or f"physical/ref_tile/s81dv_land_{master[len('dsfd_dvland_'):]}"
    row = dict(master=master, view_ref=ref, kit=kit, rl=None, job=None, source=None, error=None)
    ab = read(ref, f'{kit}/views/{master}/abstract.json')
    if ab is None:
        row['error'] = f'no closed view {kit}/views/{master} at {ref or "worktree"}'
        return row
    try:
        od = json.loads(ab).get('orfs_dir', '')
    except ValueError:
        od = ''
    m = _re.search(r'closure-loop/([^/]+)/', od)
    if not m:
        row['error'] = f'view abstract names no closure-loop job (orfs_dir {od!r})'
        return row
    job = row['job'] = m.group(1)
    if view.get('job') and view['job'] != job:
        row['error'] = f'table names job {view["job"]} but the view at {ref} is {job}'
        return row
    src = None
    vd = read(ref, f'results/closure_loop/{job}/verdict.json')
    if vd:
        try:
            src = json.loads(vd).get('source_commit')
        except ValueError:
            src = None
    if not src:
        mm = _re.search(r'-([0-9a-f]{7,40})$', job)
        src = mm.group(1) if mm else None
    if not src:
        row['error'] = f'no source commit for job {job}'
        return row
    row['source'] = src
    sp = read(src, f'{kit}/spec.json')
    if sp is None:
        row['error'] = f'kit {kit}/spec.json not at source {src} (fetch it)'
        return row
    rl = json.loads(sp).get('reset_landing') or {}
    row['rl'] = int(rl.get('stages', 0)) if rl.get('enable') else 0
    return row


def landing_reset_check(T, masters, read=_read_at):
    """Strict-bind check: for every landing master bound on the die, the table's landing_reset_stages[master]
    (absent = 0) must equal the stage count of the view actually bound (land_view_reset_stages).  A po2 view bound
    without the key, or the key set on an old (no kit landing) view, shifts every lane of that master by RL cycles."""
    tab = T.get('landing_reset_stages', {})
    lv = T.get('land_views', {})
    rows, mism, unres = [], [], []
    assemblies = T.get('landing_assemblies', {})
    for m in sorted(x for x in masters if x.startswith('dsfd_dvland') or x in assemblies):
        if m in assemblies:
            import hashlib
            a = assemblies[m]
            body = read(a['ref'], a['path'])
            valid = body is not None and hashlib.sha256(body.encode()).hexdigest() == a['sha256']
            if m in lv:
                raise ValueError(f'{m}: an unhardened RTL assembly cannot alias a closed landing view')
            r = dict(master=m, rl=a['reset_stages'] if valid else None, job=None, source=a['ref'],
                     kit=None, qualification='UNHARDENED_RTL_ASSEMBLY',
                     error=None if valid else 'landing assembly source hash mismatch')
        else:
            r = land_view_reset_stages(m, lv.get(m), read)
        r['table'] = int(tab.get(m, 0))
        rows.append(r)
        if r['rl'] is None:
            unres.append(f"{m}: {r['error']}")
        elif r['rl'] != r['table']:
            mism.append(f"{m}: table landing_reset_stages {r['table']} != view {r['job']} reset_landing {r['rl']}")
    unused = sorted(k for k in tab if k not in masters)
    return dict(verdict='PASS' if not (mism or unres) else 'FAIL', mismatch=mism, unresolved=unres,
                unused_keys=unused, rows=rows)


def bundle_age_unequal(land_rows):
    """S81-LBGAP/G8: multi-lane bundles (<stem>_l<i> into one receiver) whose lanes land at different ages
    ceil(N/2) + K + 1 -- the receiver consumes the bundle beat in one cycle, so these tear it"""
    import re as _re
    g = collections.defaultdict(list)
    for r in land_rows:
        m = _re.fullmatch(r'(.+)_l(\d+)', r['link'])
        if m:
            g[(m.group(1), r['inst'])].append(r)
    return [dict(bundle=k[0], dst=k[1], lanes={r['link']: dict(N=r['stages'], E=r['E'], K=r['K'], age=r['age']) for r in v})
            for k, v in sorted(g.items()) if len({r['age'] for r in v}) > 1]


def frame_release_epochs(base, dependencies, sync_edges=2):
    """Resolve actual frame release epochs in source-first order; reject x-chain cycles."""
    resolved, visiting = {}, set()
    def epoch(name):
        if name in resolved:
            return resolved[name]
        if name in visiting:
            raise ValueError(f'cyclic frame x-chain at {name}')
        visiting.add(name)
        value = max([base[name]] + [epoch(src) + parity - sync_edges
                                   for src, parity in dependencies.get(name, [])])
        visiting.remove(name)
        resolved[name] = value
        return value
    for name in base:
        epoch(name)
    return resolved


def emit(plan, out: Path, table_path: Path, sdir, chains_pts, run_bind=True, extra_rtl=(), land_plan=None):
    """plan: loaded plan; sdir[(link_nm, k)] = station direction; chains_pts[link_nm] = station points (die coords).
    land_plan: S81-LAND pilot land_plan.json (per link E) -> landing K straps (else the table's land_plan, else K 1)."""
    T = json.load(open(table_path))
    # S81-LAND2 (LANDING-CONTRACT L1-L7): port rules with "land": true get a dsfd_dvland_<W> tile between the last relay
    # station and the block input (ring on the lane's forwarded clock, read on the block root from its regional reset,
    # K strap, fault -> die status port land_fault).  0-stage links (neighbour root -> root) need none.
    lp = land_plan or (ROOT / T['land_plan'] if T.get('land_plan') else None)
    land_rows_plan = {r['link']: r for r in json.load(open(lp))['links']} if lp else {}
    land_e = {k: r['E'] for k, r in land_rows_plan.items()}
    force_land = {k for k, r in land_rows_plan.items() if r.get('force_landing')}
    # TOK-S81-GAPS/G8R2 (10-19): frame lk straps (one 3-bit K per x lane, crs4 landing inside the receiving frame) are
    # DERIVED from the supplied land plan: K = max over the frame's x lanes of the plan K (E), no-station lanes 1, every
    # lane of the bundle at that K (bind table frame_lk rule).  The table's static strap_values are only cross-checked.
    frame_lk_val, frame_lk_diff = {}, []
    for row in (T.get('frame_lk') or {}).get('rows', []):
        ks = [land_rows_plan[nm].get('K', land_rows_plan[nm]['E']) for nm in row['lanes'].values() if nm in land_rows_plan]
        k_ = max([k for k in ks if k is not None] or [1])
        if not 1 <= k_ <= 7:
            raise SystemExit(f'dv_bind: frame {row["inst"]}: land plan K {k_} outside the 3-bit lk strap')
        nl = len(row['lanes'])
        frame_lk_val[row['inst']] = f"{3 * nl}'h{sum(k_ << (3 * j) for j in range(nl)):0{(3 * nl + 3) // 4}x}"
        old_ = T['masters'].get(row['master'], {}).get('strap_values', {}).get('lk')
        old_ = old_.get(row['inst']) if isinstance(old_, dict) else old_
        if old_ is not None and old_ != frame_lk_val[row['inst']]:
            frame_lk_diff.append(dict(inst=row['inst'], table=old_, land_plan=frame_lk_val[row['inst']], K=k_))
    landings = []                 # (inst, link, bits)
    out.mkdir(parents=True, exist_ok=True)
    W, H = plan['facts']['die_um']
    pitch = plan['facts']['cluster_pitch_um']
    blocks = plan['blocks']
    cr_ = T.get('clock_regions') or {}
    if cr_.get('mode', 'geometric') == 'geometric':
        zero = [(blocks[l['e'][0][0]]['name'], blocks[l['e'][1][0]]['name']) for l in plan['links']
                if not chains_pts.get(l['i'].replace('-', '_'))]     # 0-stage (abutted neighbour) block pairs
        grid = GC.Grid.aligned(W, H, blocks, T, cr_.get('cell_um', GC.CELL_UM), pairs=zero)
        reg, reg_info = GC.block_regions(blocks, grid, T)
    elif cr_['mode'] == 'logical':
        grid, reg_info = None, {}
        reg = {b['name']: region_of(b, pitch) for b in blocks}
    else:
        raise SystemExit(f"dv_bind: clock_regions mode {cr_['mode']!r} (geometric | logical)")
    regions = sorted({r for r in reg.values() if f'ck_{r}' not in T.get('clock_domains', {})})   # table roots declared below
    M = T['masters']
    # Validate optional endpoint contracts even when a forwarded clock or an
    # equal-depth calendar would bypass clock selection during emission.
    for link in plan['links']:
        endpoint_clock_override(T, blocks, reg, link, True)
        endpoint_clock_override(T, blocks, reg, link, False)
    # one net per 0-stage link (no top assigns: the strict checker resolves drivers through ports only)
    dname = lambda nm: f'w_{nm}_src' if not chains_pts[nm] else f'w_{nm}_dst'
    # ------------------------------------------------------------------ endpoints per instance (plan order)
    ends = collections.defaultdict(list)       # inst -> [(port, dir, bits, link_nm, x, y, peer_inst)]
    for l in plan['links']:
        (a, pa, xa, ya, _), (b, pb, xb, yb, _) = l['e']
        nm = l['i'].replace('-', '_')
        ends[blocks[a]['name']].append((pa, 'o', l['b'], nm, xa, ya, blocks[b]['name']))
        ends[blocks[b]['name']].append((pb, 'i', l['b'], nm, xb, yb, blocks[a]['name']))
    # BIND/mu4 10-19: chain-end variants.  A master with "chain_end": {"plan_port": "xo", "dir": "o", "module": M'} binds
    # every instance that has NO plan link on that plan port to M' (the same RTL without that output and its only drivers,
    # e.g. col_h9_l4_nx), so a forward chain's last member carries no output without a consumer (no tie, no spare).
    for mk, m in M.items():
        ce = m.get('chain_end')
        if not ce:
            continue
        for bl in blocks:
            if bl['master'] == mk and not any(e[0] == ce['plan_port'] and e[1] == ce['dir'] for e in ends[bl['name']]):
                m.setdefault('inst_module', {}).setdefault(bl['name'], ce['module'])
    # ------------------------------------------------------------------ port map -> per instance connections
    conn = {}                     # inst -> {rtl_port: [(lo, hi, expr)]}
    link_src = {}                 # link_nm -> (expr driving the link's input, fwd clock expr or None)
    link_dst = {}                 # link_nm -> expr the last stage drives (a wire), or None
    plan_not_in_rtl = []
    params = {}
    top_ports = []
    straps = []
    open_bind = {}
    ckin = collections.defaultdict(dict)   # inst -> {rtl clock-in port: {lane: link}}
    abut_rows, abut_links = [], set()
    same_as, lane_spare = {}, {}           # S81-DIE5: broadcast lanes (link -> link whose source it shares); lane payload width
    out_bits, lane_copy = collections.defaultdict(list), collections.defaultdict(list)   # S81-DIE6: shared output bits
    for bl in blocks:   # plan lanes realised by an abutted face (both ends skip them)
        ab = M[bl['master']].get('abut')
        if ab and M[bl['master']].get('module'):
            for e in ends[bl['name']]:
                if f'{e[0]}.{e[1]}' in ab.get('plan_ports', []):
                    abut_links.add(e[3])
                    abut_rows.append(dict(inst=bl['name'], master=bl['master'], plan_port=e[0], dir=e[1], bits=e[2], link=e[3],
                                          peer=e[6], realised_by=f"abutted face to {ab['peer']} ({', '.join(ab['map'])})"))
    for bl in blocks:
        n = bl['name']; m = M[bl['master']]
        mod = m.get('inst_module', {}).get(n, m.get('module'))   # S81-BIND3: per-instance port variant (svc_rs entry)
        if not mod:
            open_bind[n] = dict(master=bl['master'], owner=m.get('owner'), reason=m.get('reason'))
            continue
        pm = m.get('ports', {})
        c = collections.defaultdict(list)
        # group endpoints by (port, dir) -> lanes ordered by the map's order rule
        grp = collections.defaultdict(list)
        for e in ends[n]:
            grp[(e[0], e[1])].append(e)
        hb = 0
        for (p, d), es in grp.items():
            rule = pm.get(f'{p}.{d}')
            if all(e[3] in abut_links for e in es):
                continue    # plan lane realised by an abutted named face connection: no die wire, no relay
            if rule is None:
                po = m.get('plan_only_ports', {})
                own = po.get('owner') if f'{p}.{d}' in po.get('ports', []) else m.get('owner')
                for e in es:
                    plan_not_in_rtl.append(dict(inst=n, master=bl['master'], module=mod, plan_port=p, dir=d, bits=e[2], link=e[3],
                                                owner=own, note=po.get('reason') if own == po.get('owner') else m.get('port_note')))
                    if d == 'o':
                        link_src[e[3]] = (None, None)
                    else:
                        link_dst[e[3]] = None
                continue
            es = order(es, rule.get('order', 'link'), bl)
            if rule.get('lanes'):
                # S81-DIE5: per-lane RTL bit maps (one plan lane realised by RTL port slices; spare lane bits at the end).
                # lanes[i] = {"split": [[rtl port, rtl lo, lane lo, bits], ...]} | {"same_as": j} (output only: lane i
                # carries lane j's bits -- one RTL source broadcast to several lanes, e.g. seqhost job -> both entries)
                if rule.get('hb'):
                    hb = 1
                for i, e in enumerate(es):
                    lr = rule['lanes'][i] if i < len(rule['lanes']) else None
                    b = e[2]
                    if lr is None:
                        plan_not_in_rtl.append(dict(inst=n, module=mod, plan_port=p, dir=d, bits=b, link=e[3],
                                                    note=f'lane {i} has no RTL bit map'))
                        if d == 'o':
                            link_src[e[3]] = (None, None)
                        else:
                            link_dst[e[3]] = None
                        continue
                    if d == 'o':
                        if 'same_as' in lr:
                            same_as[e[3]] = es[lr['same_as']][3]
                            continue
                        w = f'w_{e[3]}_src'
                        for rport, rlo, plo, nb in lr['split']:
                            if rport.startswith('='):
                                # S81-DIE6: lane bits that COPY an RTL output another lane of this instance already carries
                                # (e.g. seqhost s_j on both per-half job lanes): the station input reads that lane's wire
                                lane_copy[e[3]].append((n, rport[1:], rlo, plo, nb))
                                continue
                            c[rport].append((rlo, rlo + nb - 1, f'{w}[{plo + nb - 1}:{plo}]', nb))
                            out_bits[(n, rport)].append((rlo, nb, w, plo))
                        link_src[e[3]] = (w, None)
                    else:
                        w = dname(e[3])
                        if (chains_pts[e[3]] or e[3] in force_land) and rule.get('adapter'):
                            landings.append((n, e[3], b, rule['adapter'], rule['out_w'], rule.get('adapter_straps', {})))
                            w = f'w_{e[3]}_lnd'
                        elif rule.get('land') and (chains_pts[e[3]] or e[3] in force_land) and b in LAND_W:
                            landings.append((n, e[3], b)); w = f'w_{e[3]}_lnd'
                        for rport, rlo, plo, nb in lr['split']:
                            c[rport].append((rlo, rlo + nb - 1, f'{w}[{plo + nb - 1}:{plo}]', nb))
                        link_dst[e[3]] = w
                    cov = max(plo + nb for _, _, plo, nb in lr['split'])
                    assert cov <= b, (n, p, i, cov, b)
                    if cov < b:
                        lane_spare[e[3]] = cov
                continue
            if rule.get('split'):
                # S81-BIND3: one plan lane realised by SEVERAL RTL ports: split = [[rtl port, rtl lo, plan lo, bits]]
                # (e.g. ctrl_rg2 rd 562 -> svc_rs r_data / r_tag / r_beat / rv / rk / wd / hs per its packing)
                for e in es:
                    b = e[2]
                    assert d == 'i' and len(es) == 1, (n, p, d)
                    w = dname(e[3])
                    if rule.get('land') and (chains_pts[e[3]] or e[3] in force_land) and b in LAND_W:
                        landings.append((n, e[3], b)); w = f'w_{e[3]}_lnd'
                    for rport, rlo, plo, nb in rule['split']:
                        c[rport].append((rlo, rlo + nb - 1, f'{w}[{plo + nb - 1}:{plo}]', nb))
                    link_dst[e[3]] = w
                    tot = sum(x[3] for x in rule['split'])
                    if tot != b:
                        plan_not_in_rtl.append(dict(inst=n, module=mod, plan_port=p, dir=d, bits=b, link=e[3],
                                                    note=f'split covers {tot} of {b} plan bits'))
                continue
            for e in es:
                lane, rport, lw, ck = place_lane(rule, e, es, bl)
                b = e[2]
                if rule.get('hb'):
                    hb = 1
                if d == 'o':
                    w = f'w_{e[3]}_src'
                    c[rport].append((lane * lw, lane * lw + min(b, lw) - 1, w, b))
                    link_src[e[3]] = (w, f'u_{n}_{ck[0]}[{ck[1]}]' if ck else None)
                    if ck:
                        c[ck[0]]  # make sure the clock output is connected
                else:
                    w = dname(e[3])
                    if rule.get('adapter') and (chains_pts[e[3]] or e[3] in force_land):
                        # S81-DIE5: a landing with a static fixed-latency format adapter (e.g. dsfd_dvland_pvrd: P.V word
                        # -> slice band RD beat); its o is the full RTL port
                        landings.append((n, e[3], b, rule['adapter'], rule['out_w'], rule.get('adapter_straps', {})))
                        w = f'w_{e[3]}_lnd'
                        c[rport].append((lane * lw, lane * lw + rule['out_w'] - 1, w, rule['out_w']))
                        link_dst[e[3]] = w
                        continue
                    if rule.get('land') and (chains_pts[e[3]] or e[3] in force_land) and b in LAND_W:
                        landings.append((n, e[3], b))
                        w = f'w_{e[3]}_lnd'          # the landing's o, abutted to the block input
                    elif rule.get('land') and chains_pts[e[3]]:
                        plan_not_in_rtl.append(dict(inst=n, module=mod, plan_port=p, dir=d, bits=b, link=e[3],
                                                    note=f'no dsfd_dvland_{b} tile: lane NOT landed'))
                    c[rport].append((lane * lw, lane * lw + min(b, lw) - 1, w, b))
                    link_dst[e[3]] = w
                    if rule.get('ck_in'):   # the lane's forwarded clock (last station ck_o) into the receiver
                        ckin[n].setdefault(rule['ck_in'], {})[lane] = e[3]
                if b > lw:
                    plan_not_in_rtl.append(dict(inst=n, module=mod, plan_port=p, dir=d, bits=b, link=e[3],
                                                note=f'plan {b} b > RTL lane {lw} b: {b - lw} bits dropped'))
        conn[n] = c
        pp = dict(m.get('params', {}))
        if 'hb_param' in m:
            pp[m['hb_param']] = hb
        if m.get('instance_param'):
            # S81-LBGAP/G4: string identity parameter = the die instance name (frames: each loads its own ROM image
            # <OT_ROM_DIR>/<INSTANCE>_cX_Y.viamap.hex), the naming dv_slice_cut --rom-instance uses
            pp[m['instance_param']] = f'"u_{n}"'
        params[n] = pp
        for s in m.get('straps', []):
            straps.append([mod, s])
    # ------------------------------------------------------------------ reset tree
    rst = reset_tree(plan, reg, chains_pts, sdir, master=T.get('reset_master'), grid=grid)
    if grid is not None:
        regions = sorted(set(regions) | set(rst['summary'].get('clock_regions', [])))   # pruned to the used roots at the end
    early = {m.get('master') for m in T.get('frame_members', []) if m.get('reset')}
    fw = set(T.get('frame_wrapper', {}).get('masters', []))
    # TOK-S81-GAPS/G8R (10-18): frame x-chain read epoch.  A frame x lane lands in the RECEIVING frame's dsfd_cfifo_crs4
    # (ring per lane on xk[k], read on cr from rsync = frame rst_n + FRAME_RSYNC edges).  The hop-0 gate calendar
    # (LANDING-CONTRACT L3, S81-LBGAP/G1) needs R0 = G + (N mod 2) with G = the source frame's reset release; the reset
    # tree releases many receivers BEFORE their source (the x chain runs toward the tree root), and no net beside the
    # source releases earlier than the source's own leaf, so the RECEIVER's frame reset is delayed by calendar stations
    # (dsfd_rly_1 on the frame root, beside its reset pin): rst_n(frame) = max over its x lanes of G + h - FRAME_RSYNC.
    FRAME_RSYNC = T.get('frame_wrapper', {}).get('receiver_reset_edges', 2)
    frame_rst, frame_cal_lines, frame_cal_place, frame_delay = {}, [], [], {}
    lsrc0 = {l['i'].replace('-', '_'): l for l in plan['links']}
    bname = {b['name']: b for b in blocks}
    base_leaf = {n: (rst['block_parent'][n] if early and bname[n]['master'] in fw
                      else rst['block_leaf'][n]) for n in bname}
    # A street station can be geometrically close while using another root.
    # Localise BEFORE epoch solving, so every added edge reaches the compiler.
    for n, leaf in list(base_leaf.items()):
        local = reset_local_leaf(rst, leaf, regional_clock(T, bname, reg, n), rst['block_pin'][n],
                                 T.get('reset_master') or RST_RLY['EW'], f'u_{n}', grid is not None)
        base_leaf[n] = local
        if local != leaf:
            rst['summary']['block_release_depth'][n] += rst['depth'][local] - rst['depth'][leaf]
        target = 'block_parent' if early and bname[n]['master'] in fw else 'block_leaf'
        rst[target][n] = local
    # STW-S81c-DIE2 (10-22, STEWARD-S81c 05:28): a block kit hardened with its own reset landing (ref_tile reset_landing
    # {"enable": true, "stages": RL}: rst_n -> RL plain ck flops -> core; ctrl_rg3 +2, head spo/spr +2) releases its core
    # RL edges after its die reset leaf.  Table "kit_reset_landing_stages" {master: RL} books it in block_release_depth
    # (boot/programme epoch); data latencies and the hop-0 gate calendar are unchanged (landing masters keep using
    # landing_reset_stages).
    kit_rl = T.get('kit_reset_landing_stages', {})
    bad_rl = sorted(m for m in kit_rl if str(m).startswith('dsfd_dvland'))
    if bad_rl:
        raise SystemExit(f'dv_bind: kit_reset_landing_stages names landing masters {bad_rl}: use landing_reset_stages')
    brd = rst['summary']['block_release_depth']
    for n in sorted(bname):
        rl_ = int(kit_rl.get(bname[n]['master'], 0))
        if rl_ and n in brd:
            brd[n] += rl_
            rst['summary'].setdefault('kit_reset_landing', {})[n] = rl_
            rst['summary']['max_release_depth'] = max(rst['summary']['max_release_depth'], brd[n])
    base_epoch = {n: rst['depth'][leaf] for n, leaf in base_leaf.items()}
    dependencies = collections.defaultdict(list)
    for n_, cps in sorted(ckin.items()):
        for lanes in cps.values():
            for nm in lanes.values():
                l_ = lsrc0[nm]
                if chains_pts[nm] and l_['c'] == 'x_frame':
                    src_ = blocks[l_['e'][0][0]]['name']
                    dependencies[n_].append((src_, len(chains_pts[nm]) % 2))
    epochs = frame_release_epochs(base_epoch, dependencies, FRAME_RSYNC)
    for n_ in sorted(dependencies):
        rl0 = base_leaf[n_]
        need = epochs[n_] - base_epoch[n_]
        frame_rst[n_] = rl0
        if need > 0:
            rm_ = T.get('reset_master') or RST_RLY['EW']
            up = rl0
            for k_ in range(need):
                wn = f'rsx_{n_}_{k_}'
                frame_cal_lines += [f'  wire {wn};', f'  {rm_} st_{wn} (.ck({regional_clock(T, bname, reg, n_)}), .rs({up}), .i({up}), .o({wn}));   '
                                    f'// frame x-chain read epoch (TOK-S81-GAPS/G8R): {n_} released after its x source']
                xy_ = rst['block_pin'][n_]
                frame_cal_place.append(dict(inst=f'st_{wn}', master=rm_, orient='R0', xy=[round(xy_[0], 3), round(xy_[1], 3)],
                                            kind='frame_epoch_calendar'))
                rst['depth'][wn] = rst['depth'][up] + 1
                rst['net_clocks'][wn] = regional_clock(T, bname, reg, n_)
                up = wn
            frame_rst[n_] = up
            frame_delay[n_] = need
    # MU endpoint sticky faults share the die status boundary with land_fault.
    # Keep each source visible; an external monitor can attribute the failed endpoint.
    fault_masters = set(T.get('endpoint_fault_masters', []))
    endpoint_faults = {b['name']: j for j, b in enumerate(b for b in blocks if b['master'] in fault_masters)}
    # S81-DIECHAIN 10-19: the other blocks' sticky `fault` outputs (strict OUTPUT_OPEN before) -> die status vector block_fault
    sf_masters = set(T.get('status_fault_masters', []))
    _rw = T.get('rtl_widths', {})
    status_faults = {b['name']: j for j, b in enumerate(
        b for b in blocks if b['master'] in sf_masters and b['name'] not in endpoint_faults and
        'fault' in _rw.get(M[b['master']].get('inst_module', {}).get(b['name'], M[b['master']]['module']), {}))}
    # ------------------------------------------------------------------ netlist
    v = ['// S81-DV REAL-VIEW bound die top (tools/s81_dv/dv_bind.py) -- strict die_port_bind gates it',
         'module dv_die (']
    io = [f'  input wire ck_{r}' for r in regions] + [f'  input wire {p}' for p in sorted(T.get('clock_domains', {}))] + ['  input wire rst_n']
    for bl in blocks:
        m = M[bl['master']]
        for tp in m.get('top_ports', []):
            nm_ = f'{bl["name"]}_{tp["port"]}'
            io.append(f'  {tp["dir"]} wire [{tp["bits"] - 1}:0] {nm_}')
            top_ports.append(nm_)
    if landings:
        io.append(f'  output wire [{len(landings) - 1}:0] land_fault')
        top_ports.append('land_fault')
    if endpoint_faults:
        io.append(f'  output wire [{len(endpoint_faults) - 1}:0] endpoint_fault')
        top_ports.append('endpoint_fault')
    if status_faults:
        io.append(f'  output wire [{len(status_faults) - 1}:0] block_fault')
        top_ports.append('block_fault')
    # non-ANSI header (the strict checker reads port widths from body declarations)
    names = [x.split()[-1] for x in io]
    v[-1] = f'module dv_die ({", ".join(names)});'
    v += [x + ';' for x in io]
    # declare link wires
    for l in plan['links']:
        nm = l['i'].replace('-', '_'); b = l['b']
        if nm in abut_links:
            continue
        v.append(f'  wire [{b - 1}:0] w_{nm}_src, w_{nm}_dst;')
        if chains_pts[nm] or nm in force_land:
            v.append(f'  wire [{len(chains_pts[nm])}:0] n{nm}_fck;')
    # abutted faces (e.g. regional controller <-> HBM PHY): one full-width wire per peer port; instance k drives /
    # reads its slice [k*lane +: lane] (k = x order of the instances of the master)
    abut_conn = collections.defaultdict(list)    # inst -> [connection strings]
    peer_conn = collections.defaultdict(list)
    for mname, mm in M.items():
        ab = mm.get('abut')
        if not ab or not mm.get('module'):
            continue
        insts = sorted((b for b in blocks if b['master'] == mname), key=lambda b: b['x'])
        if not insts:
            continue        # S81-IDX3M: an unused table master has no PHY abutment to wire
        peers = [b for b in blocks if b['master'] == ab['peer']]
        assert len(peers) == 1, (mname, ab['peer'])
        pn = peers[0]['name']
        for port, (pport, lane, pw) in ab['map'].items():
            wn = f'a_{pn}_{pport}'
            v.append(f'  wire [{pw - 1}:0] {wn};')
            peer_conn[pn].append(f'.{pport}({wn})')
            for k, b in enumerate(insts):
                abut_conn[b['name']].append(f'.{port}({wn}[{k * lane + lane - 1}:{k * lane}])')
            assert len(insts) * lane == pw, (port, len(insts), lane, pw)
    # blocks
    v += frame_cal_lines                     # TOK-S81-GAPS/G8R frame read-epoch calendars (declared before use)
    rtl_widths = T.get('rtl_widths', {})
    pads, pad_rows = {}, []
    for bl in blocks:
        n = bl['name']; m = M[bl['master']]
        r = reg[n]
        rl = rst['block_leaf'][n]
        if early and bl['master'] in fw:
            # p4i (QXPQ-RST, coordinator 0co 14:25): the frame's q elements (RSTP=1) add one reset edge at the pin, so the
            # frame reset pin reads the PARENT station of its cell: released one regional edge earlier
            rl = rst['block_parent'][n]
        if n in frame_rst:
            rl = frame_rst[n]                # TOK-S81-GAPS/G8R: the x-chain read epoch (possibly delayed) frame reset
        if n in open_bind:
            # OPEN BINDING: plan master name, plan ports (no RTL module exists -> UNBOUND in the strict check)
            cs = [f'.clk(ck_{r})', f'.rst_n({rl})']
            for p, d, b, lnm, *_ in ends[n]:
                cs.append(f'.{p}_{lnm}({f"w_{lnm}_src" if d == "o" else dname(lnm)})')
            v.append(f'  {bl["master"]} u_{n} ({", ".join(cs)});')
            continue
        mod = m.get('inst_module', {}).get(n, m['module'])
        bc_ = block_clock(T, bl['master'], r, n)
        cs = [f'.{port}({net})' for port, net in instance_clocks(T, bl, r)]
        for cp in m.get('clk_peer', []):     # a port clocked by a peer block's root (e.g. ckh = the PHY clock)
            pb_ = [b for b in blocks if b['master'] == cp['master']]
            cs.append(f".{cp['port']}({block_clock(T, cp['master'], reg[pb_[0]['name']], pb_[0]['name'])})")
        cs += abut_conn.get(n, []) + peer_conn.get(n, [])
        for cport, lanes in ckin.get(n, {}).items():
            wd_ = rtl_widths.get(mod, {}).get(cport, max(lanes) + 1)
            bits_ = []
            for k_ in range(wd_):
                lk = lanes.get(k_)
                if lk is None:
                    v.append(f'  wire u_{n}_{cport}_nc{k_};'); bits_.append(f'u_{n}_{cport}_nc{k_}'); continue
                pts_ = chains_pts[lk]
                if pts_:
                    bits_.append(f'n{lk}_fck[{len(pts_)}]')     # last station ck_o
                elif link_src.get(lk, (None, None))[1]:
                    bits_.append(link_src[lk][1])               # 0-stage: the source's forwarded clock
                else:
                    src_ = [l for l in plan['links'] if l['i'].replace('-', '_') == lk][0]
                    sn = blocks[src_['e'][0][0]]['name']
                    source_clock = endpoint_clock(T, blocks, reg, src_, True)
                    v.append(f'  wire ckf_{lk}; {FWD} fwdi_{lk} (.A({source_clock}), .Y(ckf_{lk}));')
                    bits_.append(f'ckf_{lk}')
            cs.append(f'.{cport}({{{", ".join(reversed(bits_))}}})')
        if m.get('rst'):
            rp, pol = m['rst']
            if pol == 'high':
                v.append(f'  wire u_{n}_rst; {INV} rinv_{n} (.A({rl}), .Y(u_{n}_rst));')
                cs.append(f'.{rp}(u_{n}_rst)')
            else:
                cs.append(f'.{rp}({rl})')
        for sp, sv in m.get('strap_values', {}).items():
            if sv == 'auto_slice':     # slice id: column * 2 + (N row)  (identity strap, audit decision 1)
                val = f"4'd{int(n[2]) * 2 + (1 if n[3] == 'N' else 0)}"
            elif sp == 'lk' and n in frame_lk_val:
                val = frame_lk_val[n]   # TOK-S81-GAPS/G8R2: derived from the land plan K
            else:
                val = sv.get(n, sv.get('*')) if isinstance(sv, dict) else sv
            cs.append(f'.{sp}({val})')
        widths = rtl_widths.get(mod, {})
        col_ = int(n[2]) if n.startswith('s_') else None
        for mu in m.get('mode_unused', []):
            w_ = mu['when']
            if w_ == 'lanes_without_producer':
                # trailing lanes of a lane-packed port that no plan link reaches (e.g. slice rt lanes of row-0 frames
                # the plan dropped): tie 0 and declare the exact bit range as a pad; internal gaps stay undriven (fail)
                segs_ = conn[n].get(mu['port'])
                wd_ = widths[mu['port']]
                top_ = max((hi for lo, hi, _w, _b in segs_), default=-1) if segs_ else -1
                if segs_ is not None and top_ + 1 < wd_ and (top_ + 1) % mu['lane'] == 0:
                    segs_.append((top_ + 1, wd_ - 1, None, wd_ - 1 - top_))
                    pads.setdefault(f'u_{n}', dict(master=mod, reason=mu['reason'], ports={}))['ports'].setdefault(
                        mu['port'], []).append([top_ + 1, wd_ - 1])
                    pad_rows.append(dict(inst=n, master=mod, port=mu['port'], bits=wd_ - 1 - top_, lo=top_ + 1, hi=wd_ - 1,
                                         lanes=(wd_ - 1 - top_) // mu['lane'], reason=mu['reason']))
                continue
            if w_ == 'unlinked_out_bits':
                # TOK-S81-GAPS/SVCP (10-19): OUTPUT bit ranges of a multi-face port that no plan lane reads (the svc_rs
                # faces off the slice's tree / exchange role): left open (_nc nets) and DECLARED as spare outputs with
                # the reason (die_port_bind counts them as spare_out_bits); every other open / unread output fails
                if mu['port'] not in widths:
                    continue
                wd_ = widths[mu['port']]
                got = sorted((lo, hi) for lo, hi, _w, _b in conn[n].get(mu['port'], []))
                gaps, pos_ = [], 0
                for lo, hi in got:
                    if lo > pos_:
                        gaps.append((pos_, lo - 1))
                    pos_ = max(pos_, hi + 1)
                if pos_ < wd_:
                    gaps.append((pos_, wd_ - 1))
                for lo, hi in gaps:
                    pads.setdefault(f'u_{n}', dict(master=mod, reason=mu['reason'], ports={}))['ports'].setdefault(
                        mu['port'], []).append([lo, hi])
                    pad_rows.append(dict(inst=n, master=mod, port=mu['port'], bits=hi - lo + 1, lo=lo, hi=hi,
                                         reason=mu['reason'], spare_output=True))
                continue
            if w_ == 'unlinked_bits':
                # S81-DIE5: bit ranges of a multi-face port that no plan lane reaches (svc_rs faces the role ROM never
                # selects: a stream valid / P.V word / score on a face that is not a tree edge is a sticky fault, so the
                # face is tied 0 and declared as a pad with the reason)
                if mu['port'] not in widths:
                    continue          # the port is not on this instance's module variant (e.g. entry-only q)
                wd_ = widths[mu['port']]
                segs_ = conn[n].setdefault(mu['port'], [])
                got = sorted((lo, hi) for lo, hi, _w, _b in segs_)
                gaps, pos_ = [], 0
                for lo, hi in got:
                    if lo > pos_:
                        gaps.append((pos_, lo - 1))
                    pos_ = max(pos_, hi + 1)
                if pos_ < wd_:
                    gaps.append((pos_, wd_ - 1))
                for lo, hi in gaps:
                    segs_.append((lo, hi, None, hi - lo + 1))
                    pads.setdefault(f'u_{n}', dict(master=mod, reason=mu['reason'], ports={}))['ports'].setdefault(
                        mu['port'], []).append([lo, hi])
                    pad_rows.append(dict(inst=n, master=mod, port=mu['port'], bits=hi - lo + 1, lo=lo, hi=hi, reason=mu['reason']))
                continue
            hit = (w_ == 'always' or (w_ == 'hb0' and not (params.get(n) or {}).get(m.get('hb_param', 'HB'))) or
                   (w_ == 'col0' and col_ == 0) or (w_ == 'col7' and col_ == 7))
            if hit and not conn[n].get(mu['port']):
                wd_ = widths[mu['port']]
                conn[n].pop(mu['port'], None)
                cs.append(f".{mu['port']}({wd_}'d0)")
                pads.setdefault(f'u_{n}', dict(master=mod, reason=mu['reason'], ports={}))['ports'][mu['port']] = [[0, wd_ - 1]]
                pad_rows.append(dict(inst=n, master=mod, port=mu['port'], bits=wd_, reason=mu['reason']))
        for rp, segs in conn[n].items():
            wd = widths.get(rp)
            if not segs:   # clock output used as a forward source
                v.append(f'  wire [{wd - 1}:0] u_{n}_{rp};')
                cs.append(f'.{rp}(u_{n}_{rp})')
                continue
            parts = []
            pos = 0
            segs = sorted(segs)
            for lo, hi, w, b in segs:
                if lo > pos:
                    parts.append(f'u_{n}_{rp}_nc{pos}[{lo - pos - 1}:0]')
                    v.append(f'  wire [{lo - pos - 1}:0] u_{n}_{rp}_nc{pos};')
                parts.append(f"{hi - lo + 1}'d0" if w is None else (w if '[' in w else f'{w}[{hi - lo}:0]'))
                pos = hi + 1
            if wd and pos < wd:
                parts.append(f'u_{n}_{rp}_nc{pos}[{wd - pos - 1}:0]')
                v.append(f'  wire [{wd - pos - 1}:0] u_{n}_{rp}_nc{pos};')
            cs.append(f'.{rp}({{{", ".join(reversed(parts))}}})')
        for tp in m.get('top_ports', []):
            cs.append(f'.{tp["port"]}({n}_{tp["port"]})')
        if n in endpoint_faults:
            cs.append(f'.fault(endpoint_fault[{endpoint_faults[n]}])')
        elif n in status_faults:
            assert 'fault' not in conn[n], (n, 'fault already bound')
            cs.append(f'.fault(block_fault[{status_faults[n]}])')
        pv = params.get(n) or {}
        ps = f' #({", ".join(f".{k}({vv})" for k, vv in pv.items())})' if pv else ''
        v.append(f'  {mod}{ps} u_{n} ({", ".join(cs)});')
    # landings (S81-LAND2): K = E of the link's die STA window (land plan), assuming the hop-0 gate opens at the
    # receiver's reset release (G = R0); E > 7 needs G - R0 = E - 7 in the reset calendar (recorded per row)
    # S81-LBGAP/G1 (LANDING-CONTRACT L3): hop-0 gate calendar.  G = first gated edge at the source, R0 = first read
    # edge of the landing (rc).  The lane clock reaches the ring at G + (N mod 2)/2 + dL (the N half-cycle stations
    # invert it; dL is the forwarded-clock lag the land-plan E absorbs) while the word captured by station 0 at edge s
    # is written at epoch s - G + floor(N/2); the compiler's age ceil(N/2) + E + 1 then needs R0 = G + (N mod 2) with
    # K = E (verified by the lane bench at TT and FF flight).  G_leaf / R_leaf = release edges of the source / receiver
    # reset leaves; the side that would release early is delayed by gate-calendar stations (dsfd_rly_1, one edge
    # each) beside its own block (source pin / landing), clocked by that block's root, tapped from one chain per leaf.
    # The landing rs releases at least T/2 before the first lane clock edge reaches the ring.
    # PO-SUBMIT (10-19, COORD HANDOFF 0jz): a landing VIEW hardened with the kit reset landing (ref_tile reset_landing
    # {"enable": true, "stages": RL}: rs -> RL plain ck flops -> core) releases its core RL edges after its rs leaf, so the
    # receiver's release edge is R_leaf + RL.  Bind table "landing_reset_stages": {master: RL} names it for the views
    # actually bound (absent = 0 = the pre-po2 views without a kit landing).  The calendar below then opens the hop-0
    # gate RL edges later too (more source-side gate-calendar stations, or fewer receiver-side ones): K = E and every
    # data latency are unchanged; only the reset release / first gated edge move RL edges, uniformly.
    land_rl_tab = T.get('landing_reset_stages', {})
    lsrc = {l['i'].replace('-', '_'): l for l in plan['links']}
    rdep = rst['depth']
    gcal, gate_en, land_rs, cal_place = {}, {}, {}, []
    rmst = T.get('reset_master') or RST_RLY['EW']

    def cal_tap(leaf, ckr, nd, xy, why, clock_net=None):
        clock_key = ckr if clock_net is None else clock_net
        ch = gcal.setdefault((leaf, clock_key), [])
        while len(ch) < nd:
            up = ch[-1] if ch else leaf
            wn = f'rsg_{leaf}_{clock_key}_{len(ch)}'
            v.append(f'  wire {wn};')
            v.append(f'  {rmst} st_{wn} (.ck({clock_net if clock_net is not None else f"ck_{ckr}"}), .rs({up}), .i({up}), .o({wn}));   // gate calendar ({why})')
            cal_place.append(dict(inst=f'st_{wn}', master=rmst, orient='R0', xy=[round(xy[0], 3), round(xy[1], 3)], kind='gate_calendar'))
            ch.append(wn)
        return ch[nd - 1]
    land_rows = []
    for j, (n, nm, b, *ad) in enumerate(landings):
        l_ = lsrc[nm]
        a_ = blocks[l_['e'][0][0]]['name']
        sleaf, rleaf = frame_rst.get(a_, rst['block_leaf'].get(a_, 'rst_sync1')), rst['block_leaf'][n]
        sleaf = reset_local_leaf(rst, sleaf, endpoint_clock(T, blocks, reg, l_, True), l_['e'][0][2:4],
                                 rmst, f'fwd_{nm}', grid is not None)
        rleaf = reset_local_leaf(rst, rleaf, endpoint_clock(T, blocks, reg, l_, False), l_['e'][1][2:4],
                                 rmst, f'ld_{nm}', grid is not None)
        pr = land_rows_plan.get(nm, {})
        long_ = (not ad) and pr.get('master') == f'dsfd_dvland_{b}l'
        lm_ = ad[0] if ad else (f'dsfd_dvland_{b}l' if long_ else f'dsfd_dvland_{b}')
        rl_ = int(land_rl_tab.get(lm_, 0))
        ds_, dr_ = rdep[sleaf], rdep[rleaf] + rl_
        h_ = len(chains_pts[nm]) % 2            # R0 - G = N mod 2: an odd half-cycle chain lands on the inverted phase
        if dr_ - ds_ > h_:
            gate_en[nm] = cal_tap(sleaf, reg[a_], dr_ - ds_ - h_, l_['e'][0][2:4], f'gate opens {h_} edges before the {n} landing rs', endpoint_clock_override(T, blocks, reg, l_, True))
            land_rs[nm] = rleaf
        elif dr_ - ds_ < h_:
            gate_en[nm] = sleaf
            land_rs[nm] = cal_tap(rleaf, reg[n], ds_ + h_ - dr_, l_['e'][1][2:4], f'landing rs {h_} edges after the {a_} gate', endpoint_clock_override(T, blocks, reg, l_, False))
        else:
            gate_en[nm], land_rs[nm] = sleaf, rleaf
        st = len(chains_pts[nm])
        e_ = land_e.get(nm)
        # LANDFIX-SQ (10-18): the land plan names the tile per link (D 4 dsfd_dvland_<W>, 3-bit K <= 7; or the long tile
        # dsfd_dvland_<W>l, D 8, 6-bit K <= 63 for E > 7 or a TT/FF spread > 2 ns).  K = E (G = R0: the hop-0 gate opens on
        # the receiver's calendar release edge), so no reset-calendar offset is needed for any E.
        kw_ = 6 if long_ else 3
        if e_ is not None and e_ > (2 ** kw_ - 1):
            raise SystemExit(f'dv_bind: landing {nm} E {e_} > K range {2 ** kw_ - 1} of its tile (land plan {lp})')
        # S81-LBGAP/G8 (10-18): the land plan's K, not E -- lanes <stem>_l<i> of one bundle (one receiver beat, e.g. the
        # rstop 4 x 276 line) read at K = E + (bundle age - lane age) so every lane lands at ONE age ceil(N/2) + K + 1
        # (dv_land_pilot.py agebundle re-checks the window at K); K = E outside the equalised bundles
        k_ = max(int(pr['K']) if pr.get('K') is not None else (e_ or 1), 1)
        if e_ is not None and k_ < e_:
            raise SystemExit(f'dv_bind: landing {nm} K {k_} < E {e_} (land plan {lp})')
        if k_ > (2 ** kw_ - 1):
            raise SystemExit(f'dv_bind: landing {nm} K {k_} > K range {2 ** kw_ - 1} of its tile (land plan {lp})')
        lm, ow, ast = (ad[0], ad[1], ad[2]) if ad else ((f'dsfd_dvland_{b}l' if long_ else f'dsfd_dvland_{b}'), b, {})
        v.append(f'  wire [{ow - 1}:0] w_{nm}_lnd;')
        xs_ = ''.join(f', .{sp}({sv})' for sp, sv in ast.items())
        input_wire = dname(nm)
        if not chains_pts[nm] and nm in lane_spare:
            cov = lane_spare[nm]
            input_wire = f"{{{b - cov}'d0, {input_wire}[{cov - 1}:0]}}"
            why = f'lane quantisation: {cov}-b RTL payload on a {b}-b landing (spare bits never consumed)'
            pads.setdefault(f'ld_{nm}', dict(master=lm, reason=why, ports={}))['ports']['i'] = [[cov, b - 1]]
            pad_rows.append(dict(inst=f'ld_{nm}', master=lm, port='i', bits=b-cov, lo=cov, hi=b-1, reason=why))
        v.append(f'  {lm} ld_{nm} (.ck_f(n{nm}_fck[{st}]), .i({input_wire}), .ck({endpoint_clock(T, blocks, reg, l_, False)}), .rs({land_rs[nm]}), '
                 f".k({kw_}'d{k_}){xs_}, .o(w_{nm}_lnd), .fault(land_fault[{j}]));")
        for sp in ast:
            if [lm, sp] not in straps:
                straps.append([lm, sp])
        land_rows.append(dict(link=nm, inst=n, master=lm, bits=b, stages=st, E=e_, K=k_, D=8 if long_ else 4,
                              age=math.ceil(st / 2) + k_ + 1, bundle=pr.get('bundle'),
                              K_source=(pr.get('K_source') or 'land_plan E (gate calendar R0 = G + N mod 2)') if e_ else 'NO die STA E: K 1 placeholder (re-derive)',
                              calendar_G_minus_R0=-h_, fault_bit=j, src=a_, hop0_gate=f'fwd_{nm}', gate_en=gate_en[nm],
                              land_rs=land_rs[nm], release_src=ds_, release_dst=dr_, land_reset_stages=rl_,
                              calendar_stations=dict(side='source' if dr_ - ds_ > h_ else ('receiver' if dr_ - ds_ < h_ else None),
                                                     n=abs(dr_ - ds_ - h_))))
    # TOK-S81-GAPS/G8R (10-18): frame x lanes land INSIDE the receiving frame (dsfd_cfifo_crs4: one ot_s81_land ring per
    # lane on xk[k], read on cr from rsync = the frame rst_n + 2 cr edges).  dsfd_cfifo_crs4's contract L3 needs the
    # hop-0 ICG at the source opened at or after the frame's release -- G1 gated only the die-top dsfd_dvland lanes.
    # Same calendar as above with R0 = depth(frame rst_n net) + FRAME_RSYNC; the receiver side cannot be delayed per
    # lane (one frame reset), so a lane whose gate would have to open BEFORE its source's release is a hard error.
    land_set = {r['link'] for r in land_rows}
    frame_gate_rows = []
    for n_, cps in sorted(ckin.items()):
        if n_ not in frame_rst:
            continue
        rl_ = frame_rst[n_]
        for cport, lanes in sorted(cps.items()):
            for lane_, nm in sorted(lanes.items()):
                if nm in land_set or not chains_pts[nm] or lsrc[nm]['c'] != 'x_frame':
                    continue
                l_ = lsrc[nm]
                a_ = blocks[l_['e'][0][0]]['name']
                # the source's ACTUAL frame reset net (an early-reset frame wrapper reads its cell's parent station)
                sleaf = frame_rst.get(a_, base_leaf.get(a_, rst['block_leaf'].get(a_, 'rst_sync1')))
                ds_, dr_ = rdep[sleaf], rdep[rl_] + FRAME_RSYNC
                h_ = len(chains_pts[nm]) % 2
                if dr_ - ds_ < h_:
                    raise SystemExit(f'dv_bind: frame lane {nm}: R0 {dr_} - G {ds_} < N mod 2 = {h_}: the hop-0 gate '
                                     f'would open before {a_} releases (frame reset cannot be delayed per lane)')
                gate_en[nm] = (cal_tap(sleaf, reg[a_], dr_ - ds_ - h_, l_['e'][0][2:4],
                                       f'frame gate opens {h_} edges before the {n_} crs4 rsync')
                               if dr_ - ds_ > h_ else sleaf)
                frame_gate_rows.append(dict(link=nm, inst=n_, port=f'{cport}[{lane_}]', src=a_, stages=len(chains_pts[nm]),
                                            frame_rst=rl_, release_src=ds_, read_epoch=dr_, calendar_G_minus_R0=-h_,
                                            calendar_stations=dr_ - ds_ - h_, gate_en=gate_en[nm], hop0_gate=f'fwd_{nm}'))
    for lm in sorted({r['master'] for r in land_rows}):
        straps.append([lm, 'k'])
    if land_rows:
        straps.append([ICG, 'SE'])      # S81-LBGAP/G1: the hop-0 gate's scan enable is a test strap (no scan chain on the die)
    # relay chains (F1)
    nst = collections.Counter(); fwd_cells = 0; gate_cells = 0
    # DRIVE-S81-IDX4 (10-20): a vertical relay direction with no closed view (e.g. dsfd_dvrlyh_562_NS: the --idxrd 4 hrrd
    # lanes come DOWN into the reader N face) uses the closed opposite-direction view mirrored about X (MX): same module,
    # i on the upstream face.  Opt-in per table (relay_mirror_vertical); the mirrored stations go to relay_mirror.json.
    _rv_views = T.get('relay_views', {}); relay_mirror = {}
    def rly_pick(b_, d_, inst_):
        m_ = rly_master(b_, d_, T.get('relay_prefix', 'dsfd_dvrly'))
        if T.get('relay_mirror_vertical') and m_ not in _rv_views and d_ in ('NS', 'SN'):
            o_ = rly_master(b_, 'SN' if d_ == 'NS' else 'NS', T.get('relay_prefix', 'dsfd_dvrly'))
            if o_ in _rv_views:
                relay_mirror[inst_] = dict(master=o_, for_dir=d_, orient='MX')
                return o_
        return m_
    for l in plan['links']:
        nm = l['i'].replace('-', '_'); b = l['b']
        a = blocks[l['e'][0][0]]['name']
        pts = chains_pts[nm]
        if nm in abut_links:
            continue
        root_nm = same_as.get(nm, nm)                     # S81-DIE5: a broadcast lane reads its source lane's wire
        src, ck = link_src.get(root_nm, (f'w_{root_nm}_src', None))
        src = f'w_{root_nm}_src'
        if not pts and nm not in gate_en:
            continue
        if root_nm in lane_spare and pts:
            # lane quantised onto a relay master wider than its RTL payload: the spare top bits enter hop 0 as declared
            # pads (tied 0 at the station input, never read by the receiver)
            cov = lane_spare[root_nm]
            src = f"{{{b - cov}'d0, {src}[{cov - 1}:0]}}"
            pads.setdefault(f'st_{nm}_0', dict(master=rly_pick(b, sdir[(nm, 0)], f'st_{nm}_0'),
                                               reason=f'lane quantisation: {cov}-b RTL payload on a {b}-b relay master (spare top bits)',
                                               ports={}))['ports']['i'] = [[cov, b - 1]]
            pad_rows.append(dict(inst=f'st_{nm}_0', master=rly_pick(b, sdir[(nm, 0)], f'st_{nm}_0'),
                                 port='i', bits=b - cov, lo=cov, hi=b - 1, reason='lane quantisation spare bits'))
        if root_nm in lane_copy:
            segs_ = []          # (plo, nb, expr) covering the lane: own wire where bound, copied bits elsewhere
            for n_, rp_, rlo_, plo_, nb_ in lane_copy[root_nm]:
                hit_ = [(lo_, w_, pl_) for lo_, nb2, w_, pl_ in out_bits[(n_, rp_)] if lo_ <= rlo_ and rlo_ + nb_ <= lo_ + nb2]
                assert hit_, (root_nm, rp_, rlo_, nb_)
                lo_, w_, pl_ = hit_[0]
                segs_.append((plo_, nb_, f'{w_}[{pl_ + rlo_ - lo_ + nb_ - 1}:{pl_ + rlo_ - lo_}]'))
            cov_ = lane_spare.get(root_nm, b)
            pos_, parts_ = 0, []
            for plo_, nb_, ex_ in sorted(segs_) + [(cov_, 0, None)]:
                if plo_ > pos_:
                    parts_.append(f'w_{root_nm}_src[{plo_ - 1}:{pos_}]')
                if ex_:
                    parts_.append(ex_)
                pos_ = max(pos_, plo_ + nb_)
            if cov_ < b:
                parts_.append(f"{b - cov_}'d0")
            src = '{' + ', '.join(reversed(parts_)) + '}'
        st = len(pts)
        gen = gate_en.get(nm)
        if gen:
            # S81-LBGAP/G1: landed lane -> hop-0 clock gate opened by the released reset on the calendar edge G = R0 - (N mod 2)
            v.append(f'  {ICG} fwd_{nm} (.CLK({ck or endpoint_clock(T, blocks, reg, lsrc[nm], True)}), .ENA({gen}), .SE(1\'b0), .GCLK(n{nm}_fck[0]));   '
                     f'// hop 0: clock gate (LANDING-CONTRACT L3) on {"the source master forwarded clock" if ck else "the source region root"}')
            gate_cells += 1
            ck = None
        elif ck:
            v.append(f'  // hop 0: the source master forwards its root (F1): {ck}')
        else:
            v.append(f'  {FWD} fwd_{nm} (.A({endpoint_clock(T, blocks, reg, lsrc[nm], True)}), .Y(n{nm}_fck[0]));   // hop 0: clock-forward cell on the source region root')
            fwd_cells += 1
        prev = src
        for k in range(st):
            d = sdir[(nm, k)]
            wn = f'w_{nm}_dst' if k == st - 1 else f'r_{nm}_{k}'
            if k < st - 1:
                v.append(f'  wire [{b - 1}:0] {wn};')
            cki = ck if (k == 0 and ck) else f'n{nm}_fck[{k}]'
            rm_ = rly_pick(b, d, f'st_{nm}_{k}')
            v.append(f'  {rm_} st_{nm}_{k} (.i({prev}), .o({wn}), .ck({cki}), .ck_o(n{nm}_fck[{k + 1}]), '
                     f'.rs({rst["station_leaf"][(nm, k)]}));')
            nst[rm_] += 1
            prev = wn
    v += rst['verilog']
    v.append('endmodule')
    if T.get('prune_unused_reset_leaves'):
        # Frame epoch roots may consume a station's parent instead of its leaf.
        # Remove only generated reset stations with no reads after final wiring;
        # iterate so entire unused twigs disappear. Surviving sink depths stay fixed.
        removed = []
        while True:
            text = '\n'.join(v)
            uses = collections.Counter(re.findall(r'\brs(?:l)?_[A-Za-z0-9_]+\b', text))
            dead = []
            for row in rst['place']:
                inst = row['inst']
                net = inst[3:]
                if inst in removed:
                    continue
                if uses[net] == 2:
                    dead.append(inst)  # one declaration + the station's own .o
            if not dead:
                break
            for inst in dead:
                net = inst[3:]
                v = [line for line in v if not re.search(r'\b' + re.escape(inst) + r'\s*\(', line)
                     and line.strip() != f'wire {net};']
            removed.extend(dead)
        rst['place'] = [r for r in rst['place'] if r['inst'] not in removed]
        rst['summary']['pruned_unused_reset_stations'] = removed
        rst['summary']['stations'] -= len(removed)
    if grid is not None:
        # S81.CLK: a candidate region root with no load (a cell holding only table-clocked blocks) is not a top port
        text = '\n'.join(v)
        used = [r for r in regions if re.search(r'\(ck_' + re.escape(r) + r'\)', text)]
        drop = {f'ck_{r}' for r in regions if r not in used}
        if drop:
            hdr = next(k for k, x in enumerate(v) if x.startswith('module dv_die ('))
            names_ = [x for x in v[hdr][len('module dv_die ('):-2].split(', ') if x not in drop]
            v[hdr] = f'module dv_die ({", ".join(names_)});'
            v = [x for x in v if not (x.startswith('  input wire ck_') and x[len('  input wire '):-1] in drop)]
        regions = used
    face_rep = None
    if T.get('svc_face_variants'):
        # S81-P9-FACE (10-23, owner: no tie-offs): every rsv slice -> the port variant of its role (svc_rs_faces.py, from
        # the role ROMs); the faces the role never uses are no longer ports (were `unlinked_bits` 0 pads / _nc outputs).
        # The pass proves the mask against this netlist (dropped faces all 0 / _nc, kept input faces constant-free).
        import sys as _sys; _sys.path.insert(0, str(ROOT / 'tools/s81_dv/svc_rs'))
        import svc_rs_face_bind
        txt_, face_rep = svc_rs_face_bind.rewrite('\n'.join(v), str(ROOT))
        v = txt_.split('\n')
        for inst_, r_ in face_rep['instances'].items():
            pd_ = pads.get(inst_)
            if pd_:
                for p_ in [p_ for p_ in pd_['ports'] if p_ in svc_rs_face_bind.GROUP_OF or p_ == 'q']:
                    del pd_['ports'][p_]
                if not pd_['ports']:
                    del pads[inst_]
                else:
                    pd_['master'] = r_['new']
        pad_rows[:] = [r for r in pad_rows if not (f"u_{r['inst']}" in face_rep['instances'] and
                                                   (r['port'] in svc_rs_face_bind.GROUP_OF or r['port'] == 'q'))]
        print('SVC_FACE_VARIANTS', json.dumps({k: face_rep[k] for k in ('dropped_in_bits', 'dropped_out_bits', 'nc_decls_removed')}))
    (out / 'die.v').write_text('\n'.join(v) + '\n')
    (out / 'cells_used.v').write_text(CELL_MODELS)
    (out / 'straps.json').write_text(json.dumps({'straps': straps}, indent=1))
    if T.get('spare_out_rules'):
        # S81-DIECHAIN 10-19: provably role-unused output bits -> declared spare outputs (svc_rs role faces, lane
        # quantisation landing bits, unbuilt forwarded-clock taps); a role-active face left open is a GAP (recorded, not declared)
        import sys as _sys; _sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
        import dv_spare_out
        spare_rec = dv_spare_out.declare(v, pads, ROOT)
        (out / 'spare_out.json').write_text(json.dumps(spare_rec, indent=1))
        print('SPARE_OUT', json.dumps(spare_rec['summary']))
        assert not spare_rec['gaps'], spare_rec['gaps'][:10]
    (out / 'pads.json').write_text(json.dumps({'pads': {}, 'instances': pads}, indent=1))
    frame_rec = frame_contract(T)
    (out / 'frame_contract.json').write_text(json.dumps(frame_rec, indent=1))
    views = collections.Counter()
    for bl in blocks:
        mm = M[bl['master']]
        views['open_binding' if not mm.get('module') else ('closed_view' if mm.get('view') else 'rtl_no_view')] += 1
    rv = T.get('relay_views', {})
    for k_, v_ in nst.items():
        views['relay_closed_view' if k_ in rv else 'relay_rtl_view_owed'] += v_
    rmaster = T.get('reset_master')
    views['reset_station_closed_view' if rmaster in rv else 'reset_station_rtl'] += rst['summary']['stations']
    # RTL closure: worktree rtl/ + refs named by the table (materialised, sha-recorded)
    extra = []
    (out / 'rtl_extra').mkdir(exist_ok=True)
    for ref, paths in T.get('rtl_refs', {}).items():
        for p in paths:
            dst = out / 'rtl_extra' / ref.replace('/', '_') / p
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(git_show(ref, p))
            extra.append(str(dst))
    # MU-DIE-S81/PO2 (10-19): landing_reset_stages must match the reset landing of every bound landing VIEW (both ways)
    lrc = landing_reset_check(T, {r['master'] for r in land_rows})
    (out / 'landing_reset_check.json').write_text(json.dumps(lrc, indent=1))
    rec = dict(schema='opentallas.s81_dv.bind_case.v1', regions=regions, open_bindings=open_bind,
               clock_regions=(dict(mode='geometric', grid=grid.spec(), blocks=reg_info) if grid is not None
                              else dict(mode='logical')),
               instance_clock_ports=T.get('instance_clock_ports', {}),
               clock_source_entries=T.get('clock_domains', {}),
               instance_orientations=T.get('instance_orientations', {}),
               plan_port_not_in_rtl=plan_not_in_rtl, relay_masters=dict(nst), clock_forward_cells=fwd_cells,
               hop0_clock_gates=gate_cells, gate_calendar_stations=len(cal_place),
               abutted_plan_lanes=abut_rows, reset=rst['summary'], straps=straps, mode_unused_pads=pad_rows, views=dict(views),
               frame_contract=dict(verdict=frame_rec['verdict'], members=len(frame_rec['members']), problems=frame_rec['problems']), rtl_extra=extra, top_offchip_ports=top_ports,
               endpoint_fault_sources=endpoint_faults, status_fault_sources=status_faults,
               landing_reset_check={k: lrc[k] for k in ('verdict', 'mismatch', 'unresolved', 'unused_keys')},
               landings=dict(count=len(land_rows), land_plan=str(lp) if lp else None,
                             by_master=dict(collections.Counter(r['master'] for r in land_rows)),
                             by_inst_kind=dict(collections.Counter(r['inst'].split('_')[0] for r in land_rows)),
                             no_E=[r['link'] for r in land_rows if r['E'] is None],
                             calendar_needs=[r for r in land_rows if r['calendar_stations']['n']],
                             bundle_age_unequal=bundle_age_unequal(land_rows), rows=land_rows),
               frame_hop0_gates=dict(count=len(frame_gate_rows), rule=f'TOK-S81-GAPS/G8R: R0 = frame rst_n depth + {FRAME_RSYNC} '
                                     '(receiver reset stages), G = R0 - N mod 2', rows=frame_gate_rows,
                                     frame_epoch_delay=frame_delay, frame_epoch_stations=len(frame_cal_place)),
               frame_lk=dict(count=len(frame_lk_val), source=str(lp) if lp else None,
                             rule='K = max land-plan K over the frame x lanes (no-station lanes 1), every lane at K',
                             differs_from_table=frame_lk_diff, values=frame_lk_val))
    if face_rep:
        rec['svc_face_variants'] = {k: x for k, x in face_rep.items() if k not in ('bitmap', 'src_faces')}
    if run_bind:
        cmd = ['python3', str(ROOT / 'tools/die_port_bind.py'), str(out / 'die.v'), '--top', 'dv_die', '--rtl-root', str(ROOT / 'rtl'),
               '--rtl-file', str(out / 'cells_used.v'), '--strap-file', str(out / 'straps.json'), '--pad-file', str(out / 'pads.json'), '--out', str(out / 'port_bind.json')]
        # S81-LBGAP G6 (10-18): duplicated module names resolve by rule, not by sort order -- the frames' bench list (the
        # _rne_* variants), the svc_rs bench list, then each hardened tile's spec sources (RTL of record of its view);
        # die_port_bind FAILS a first-pick among definitions with different ports / parameters (ambiguous_children)
        for L in ('tools/s81_dv/frame_bench.f', 'tools/s81_dv/svc_rs/rs_files.sh'):
            if (ROOT / L).is_file():
                cmd += ['--prefer-list', str(ROOT / L)]
        cmd += ['--ref-tile-prefer']
        for f in list(extra) + list(extra_rtl) + [str(ROOT / x) for x in T.get('rtl_files', [])]:
            cmd += ['--rtl-file', str(f)]
        for f in T.get('prefer', []):
            cmd += ['--prefer', str(out / 'rtl_extra' / f)]
        for mm in T.get('allow_model', []):
            cmd += ['--allow-model', mm]
        for d_ in T.get('defines', []):         # S81-DIE5: build defines of the bound RTL (e.g. DSFD_PQ_STATIC_X2)
            cmd += ['--define', d_]
        r = subprocess.run(cmd, capture_output=True, text=True)
        log_, rc_ = r.stdout + r.stderr, r.returncode
        nbad_ = len(lrc['mismatch']) + len(lrc['unresolved'])
        # the landing reset check is a strict-bind counter: any mismatch / unresolved view FAILS the bind
        log_ = '\n'.join((l.replace('DIE_PORT_BIND PASS', 'DIE_PORT_BIND FAIL', 1) if nbad_ else l) +
                          (f' landing_reset_mismatch={len(lrc["mismatch"])} landing_reset_unresolved={len(lrc["unresolved"])}'
                           if l.startswith('DIE_PORT_BIND ') else '') for l in log_.split('\n'))
        log_ += ''.join(f'LANDING_RESET {x}\n' for x in lrc['mismatch'] + lrc['unresolved'])
        if nbad_ and rc_ == 0:
            rc_ = 3
        (out / 'port_bind.log').write_text(log_)
        rec['port_bind_rc'] = rc_
        rec['port_bind_cmd'] = cmd
    (out / 'bind_case.json').write_text(json.dumps(rec, indent=1))
    # S81-DIE7 (10-18): placement hints for the real-view physical case (dv_rvcase.py): reset stations of the regional
    # reset tree (street cells + lane companions at the station points), the root synchroniser point and the block reset
    # pin points (top-down pin assignment); landings / relays / forward cells are placed from the plan by dv_rvcase
    (out / 'relay_mirror.json').write_text(json.dumps(relay_mirror, indent=1))
    (out / 'place_hints.json').write_text(json.dumps(dict(
        schema='opentallas.s81_dv.place_hints.v1', reset_place=rst['place'] + cal_place + frame_cal_place, reset_root_xy=rst['summary']['root_xy'],
        block_rst_pin={b: [round(x, 3), round(y, 3)] for b, (x, y) in rst['block_pin'].items()},
        landings=[dict(inst=f'ld_{r["link"]}', link=r['link'], dst=r['inst'], master=r['master'], bits=r['bits'], D=r['D'])
                  for r in land_rows]), indent=1))
    if lrc['verdict'] != 'PASS':
        raise SystemExit('dv_bind: STRICT bind FAIL, landing_reset_stages vs bound landing views:\n  ' +
                         '\n  '.join(lrc['mismatch'] + lrc['unresolved']))
    return rec


def frame_contract(T):
    """Check the frame member contract against the members' RTL at their refs: module exists, every named port and
    parameter exists, clock-tie source and target ports exist.  The frame wrapper itself has no RTL (OPEN binding)."""
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import die_port_bind as D
    import re
    rows, problems = [], []
    for fm in T.get('frame_members', []):
        r = dict(master=fm['master'], ref=fm['ref'], path=fm['path'], view=fm.get('view'))
        try:
            txt = git_show(fm['ref'], fm['path']).decode()
            r['ref_sha'] = subprocess.run(['git', '-C', os.environ.get('OT_GIT_DIR', str(ROOT)), 'rev-parse', fm['ref']],
                                          capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError:
            problems.append(f"{fm['master']}: {fm['path']} not at {fm['ref']}"); rows.append(r); continue
        mods = {m.name: m for m in D.parse_modules(txt, fm['path'])}
        md = mods.get(fm['master'])
        if md is None:
            problems.append(f"{fm['master']}: module not in {fm['path']}@{fm['ref']}"); rows.append(r); continue
        r['kind'] = md.kind(mods)
        miss = [p for p in fm.get('ports_used', []) if p not in md.ports]
        for ct in fm.get('clock_ties', []):
            for q in (ct['port'], ct['to']):
                b = re.sub(r'\[.*', '', q)
                if b not in md.ports and b not in miss:
                    miss.append(b)
        pmiss = [k for k in fm.get('params', {}) if k not in md.params]
        r.update(ports_missing=miss, params_missing=pmiss, clock_ties=fm.get('clock_ties', []), params=fm.get('params', {}),
                 reset=fm.get('reset'))
        if miss or pmiss:
            problems.append(f"{fm['master']}: ports {miss} params {pmiss} not in RTL")
        rows.append(r)
    return dict(schema='opentallas.s81_dv.frame_contract.v1', wrapper=T.get('frame_wrapper'), members=rows, problems=problems,
                verdict='PASS' if not problems else 'FAIL')


def order(es, rule, bl):
    if rule == 'link':
        return sorted(es, key=lambda e: e[3])
    if rule == 'ret':        # L00..L03, R00..R03
        return sorted(es, key=lambda e: (e[6][3], e[6][4:]))
    return es


def place_lane(rule, e, es, bl):
    """-> (lane index, RTL port, lane width, (clock port, bit) or None)"""
    lw = rule['lane']
    if rule.get('kind') == 'xc':    # x chains: 0/1 down W/E (row nearer the slice bottom), 2/3 up; lane by link suffix
        if 'lane_by_link' in rule:
            # Physical pin movement must not change the logical streamer lane.
            # An explicit table is complete: missing entries fail closed.
            idx = rule['lane_by_link'][e[3]]
            if not isinstance(idx, int) or not 0 <= idx < 16:
                raise ValueError(f'xc logical lane outside 0..15: {e[3]}={idx}')
            return idx, rule['port'], lw, (rule['ck'], idx) if rule.get('ck') else None
        peer = e[6]
        side = 0 if peer[3] == 'L' else 1
        cy = bl['y'] + bl['h'] / 2
        up = 1 if e[5] > cy else 0
        lane_in = int(e[3].rsplit('_l', 1)[1])
        ch = 2 * up + side
        idx = ch * 4 + lane_in
        return idx, rule['port'], lw, (rule['ck'], idx) if rule.get('ck') else None
    i = rule['index'] if 'index' in rule else es.index(e)     # S81-DIE5: fixed lane index (svc_rs face N/E/S/W)
    ck = None
    if rule.get('ck'):
        ck = (rule['ck'], rule.get('ck_base', 0) + i)
    return i, rule['port'], lw, ck


RESET_REACH_UM = 405.0             # measured repeated reach (plan 405 um, memory reach-405-repeaters-1016)


def reset_reach_gate(blocks, nodes, sinks, edges, reach=RESET_REACH_UM, mode=None):
    """Die standard (regional reset; as the Qwen generator 27309ba59 and HBM die_case_v16 reset_reach_gate): every reset
    sink must be reachable by the regional reset tree.  Errors (FAIL, ValueError) -- 'warn' does NOT bypass them, only
    OT_RESET_GATE=diag continues (rec reach_gate FAIL_DIAG):
      sink_unreachable    a block reset pin / relay station rs with no reset station of the tree within `reach`
                          (tree stations = the street-cell stations AND, S81-DIE5, the reset bit carried in the relay
                          stations of the lanes: one dsfd_rly_1 companion per lane station on the tree);
      sink_buried         a block reset pin strictly inside ANOTHER block's outline (no street can reach it);
      driver_unreachable  no block-free cell for the root synchroniser.
    nodes: {node: (x, y)} of the tree (connected to the root); sinks: [(pin, (x, y), own block or None, serving node or
    None)]; edges: [(node, parent)] of the tree.
    over_reach (recorded, not a FAIL): a station -> parent hop longer than `reach` (relay timing judges it)."""
    mode = os.environ.get('OT_RESET_GATE') if mode is None else mode
    errors, over = [], 0
    if not nodes:
        errors.append(dict(kind='driver_unreachable', pin='rst_n', why='no block-free reset street cell'))

    def buried(x, y, own):
        for b in blocks:
            if b['name'] != own and b['x'] + 0.5 < x < b['x'] + b['w'] - 0.5 and b['y'] + 0.5 < y < b['y'] + b['h'] - 0.5:
                return b['name']
        return None
    for pin, (x, y), own, srv in sinks if nodes else ():
        if own is not None:
            b = buried(x, y, own)
            if b:
                errors.append(dict(kind='sink_buried', pin=pin, under=b))
                continue
        if srv is None or srv not in nodes:
            errors.append(dict(kind='sink_unreachable', pin=pin, station=None, um=None))
            continue
        um = abs(nodes[srv][0] - x) + abs(nodes[srv][1] - y)
        if um > reach:
            errors.append(dict(kind='sink_unreachable', pin=pin, station=str(srv), um=round(um, 1)))
    for c, p in edges:
        if p is not None and abs(nodes[c][0] - nodes[p][0]) + abs(nodes[c][1] - nodes[p][1]) > reach:
            over += 1
    kinds = dict(collections.Counter(e['kind'] for e in errors))
    rec = dict(reach_um=reach, sinks=len(sinks), errors=len(errors), kinds=kinds, first=errors[:20], over_reach_hops=over,
               reach_gate='PASS' if not errors else ('FAIL_DIAG' if mode == 'diag' else 'FAIL'))
    print('reset_reach_gate', json.dumps({k: rec[k] for k in ('reach_gate', 'sinks', 'errors', 'kinds', 'over_reach_hops')}),
          flush=True)
    if rec['reach_gate'] == 'FAIL':
        raise ValueError(f"reset tree: reachability gate FAIL, {len(errors)} unbuildable {kinds}: {errors[:8]} "
                         f"(OT_RESET_GATE=diag continues for diagnosis only)")
    return rec


def reset_tree(plan, reg, chains_pts, sdir, master=None, reach=RESET_REACH_UM, grid=None):
    """Regional synchronous-release reset tree (die standard item 2).
    Nodes: one reset station per 400-um block-free street cell (as before) PLUS, S81-DIE5 (coordinator 0dt+ / ROOT
    4f7440ccf), the RESET BIT CARRIED IN THE LANE STATIONS: every relay station of a planned lane may hold a 1-b
    reset relay (dsfd_rly_1 companion at the station point, async assert, release one regional edge a hop) whose input
    is the previous / next station of the same lane or any tree node within `reach`.  The tree is the BFS (fewest
    release edges) from the root synchroniser over cell<->cell grid steps and node<->node hops <= `reach`.  A lane
    station's rs reads its own cell station when that is on the tree and within reach (unchanged p4j wiring), else its
    own companion.  A block reset pin sits on the block perimeter point nearest a tree node (the S-face centre when
    that is reachable; top-down pin assignment for the unclosed blocks) and reads that node.  The release depth of
    every sink (edges after rst_n release) is recorded for the reset calendar.
    S81.CLK (10-21), grid = geo_clock.Grid: each station is clocked by the root of the GEOMETRIC cell holding its point
    (else, legacy, the logical region of the nearest block centre).  A tree edge whose parent and child stations lie in
    different cells is a RESET RELEASE CROSSING: one extra registered stage <child>_xk (the reset master, clocked by
    the RECEIVING cell's root, placed at the child) re-registers the released level in the receiving region before the
    child station (two flops of the receiving clock: a landed crossing of a monotonic 1-bit level).  The release depth
    is +1 per crossing on the path from the root, and every depth the calendars read (station / block leaves, gate
    and frame-epoch calendars) includes it.  The crossings are listed in summary['crossings']."""
    rr = {d: master for d in RST_RLY} if master else RST_RLY
    W, H = plan['facts']['die_um']
    blocks = plan['blocks']
    # S81-LINKS gap reserves (geometry-only blockages, no pins): no reset street station inside them; they take no sink
    geo = blocks + plan.get('blockages', [])
    nx, ny = int(math.ceil(W / GRID)), int(math.ceil(H / GRID))

    def inside(x, y):
        for b in geo:
            if b['x'] - 5 <= x <= b['x'] + b['w'] + 5 and b['y'] - 5 <= y <= b['y'] + b['h'] + 5:
                return True
        return False
    free = {}
    cellb = collections.defaultdict(list)          # blocks (inflated 5 um) touching each grid cell
    for b in geo:
        for i in range(max(0, int((b['x'] - 5) // GRID)), min(nx, int((b['x'] + b['w'] + 5) // GRID) + 1)):
            for j in range(max(0, int((b['y'] - 5) // GRID)), min(ny, int((b['y'] + b['h'] + 5) // GRID) + 1)):
                cellb[(i, j)].append(b)

    def inside_c(x, y, bl):
        return any(b['x'] - 5 <= x <= b['x'] + b['w'] + 5 and b['y'] - 5 <= y <= b['y'] + b['h'] + 5 for b in bl)
    for i in range(nx):
        for j in range(ny):
            bl = cellb.get((i, j), [])
            # the reset station of a cell sits at the block-free point nearest the cell centre: a coarse 5 x 5 sample, plus
            # (S81-DIE5) the coordinates just outside every block edge in the cell, so the narrow block-free strips (the
            # 15-25 um slice-column margins, street edges) hold a 1-b reset station too
            x0, y0 = i * GRID, j * GRID
            xs = {x0 + f * GRID for f in (0.1, 0.3, 0.5, 0.7, 0.9)} | {v for b in bl for v in (b['x'] - 6, b['x'] + b['w'] + 6)
                                                                    if x0 <= v < x0 + GRID}
            ys = {y0 + f * GRID for f in (0.1, 0.3, 0.5, 0.7, 0.9)} | {v for b in bl for v in (b['y'] - 6, b['y'] + b['h'] + 6)
                                                                    if y0 <= v < y0 + GRID}
            cx, cy = x0 + GRID / 2, y0 + GRID / 2
            got = []
            for x, y in sorted(((x, y) for x in xs for y in ys if x < W and y < H),
                               key=lambda p: (abs(p[0] - cx) + abs(p[1] - cy), p)):
                # up to 4 points a cell, >= 150 um apart: one per block-free piece of the cell (a strip under the PHY and
                # the band beside it are different pieces; one point a cell disconnected them)
                if not inside_c(x, y, bl) and all(abs(x - u) + abs(y - w) >= 150 for u, w in got):
                    got.append((x, y))
                    if len(got) == 4:
                        break
            for m, xy in enumerate(got):
                free[(i, j, m)] = xy
    if not free:
        reset_reach_gate(blocks, {}, [], [])
    # ---- graph: street cells ('c', i, j) + lane stations ('s', link, k)
    pos = {('c',) + c: xy for c, xy in free.items()}
    for nm, pts in chains_pts.items():
        for k, xy in enumerate(pts):
            pos[('s', nm, k)] = tuple(xy)
    B = reach
    buck = collections.defaultdict(list)
    for n, (x, y) in pos.items():
        buck[(int(x // B), int(y // B))].append(n)

    def near(x, y, r=reach):
        bx, by = int(x // B), int(y // B)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for n in buck.get((bx + dx, by + dy), ()):
                    d = abs(pos[n][0] - x) + abs(pos[n][1] - y)
                    if d <= r:
                        yield d, n

    def nbrs(n):
        if n[0] == 's':
            nm, k = n[1], n[2]
            for kk in (k - 1, k + 1):
                m = ('s', nm, kk)
                if m in pos and abs(pos[m][0] - pos[n][0]) + abs(pos[m][1] - pos[n][1]) <= reach:
                    yield m
        x, y = pos[n]
        for _, m in sorted(near(x, y), key=lambda t: (t[0], str(t[1]))):
            if m != n:
                yield m
    # root: the die reset pad at the south edge centre street
    comp = {}
    for n0 in pos:
        if n0 in comp:
            continue
        comp[n0] = n0; q = collections.deque([n0])
        while q:
            c = q.popleft()
            for m in nbrs(c):
                if m not in comp:
                    comp[m] = n0; q.append(m)
    big = collections.Counter(comp[n] for n in pos if n[0] == 'c').most_common(1)[0][0]
    root = min((n for n in pos if n[0] == 'c' and comp[n] == big), key=lambda n: (abs(pos[n][0] - W / 2) + pos[n][1], n))
    par = {root: None}
    q = collections.deque([root])
    while q:
        c = q.popleft()
        for m in nbrs(c):
            if m not in par:
                par[m] = c; q.append(m)
    depth = {}

    def dep(c):
        if c not in depth:
            depth[c] = 0 if par[c] is None else dep(par[c]) + 1
        return depth[c]

    def serve(x, y, own_station=None):
        """tree node serving a sink at (x, y): its own street cell when on the tree and within reach (p4j wiring),
        else the own lane station's companion, else the nearest tree node within reach (fewest edges, then distance)"""
        ci, cj = min(int(x // GRID), nx - 1), min(int(y // GRID), ny - 1)
        own = [('c', ci, cj, m) for m in range(4) if ('c', ci, cj, m) in par]
        own = [c for c in own if abs(pos[c][0] - x) + abs(pos[c][1] - y) <= reach]
        if own:
            return min(own, key=lambda c: (abs(pos[c][0] - x) + abs(pos[c][1] - y), c))
        if own_station is not None and own_station in par:
            return own_station
        best = None
        for d, n in near(x, y):
            if n in par and (best is None or (dep(n), d) < best[0]):
                best = ((dep(n), d), n)
        return best[1] if best else None
    sinks = []
    station_srv = {}
    for nm, pts in chains_pts.items():
        for k, (x, y) in enumerate(pts):
            s = serve(x, y, ('s', nm, k))
            station_srv[(nm, k)] = s
            sinks.append((f'{nm}[{k}].rs', (x, y), None, s))

    def buried(x, y, own):
        return any(b['name'] != own and b['x'] + 0.5 < x < b['x'] + b['w'] - 0.5 and b['y'] + 0.5 < y < b['y'] + b['h'] - 0.5
                   for b in geo)
    block_srv, block_pin = {}, {}
    for b in blocks:
        cands = [(b['x'] + b['w'] / 2, b['y'])]          # default: S face centre
        for f in range(1, 40):
            t = f / 40.0
            cands += [(b['x'] + b['w'] * t, b['y']), (b['x'] + b['w'] * t, b['y'] + b['h']),
                      (b['x'], b['y'] + b['h'] * t), (b['x'] + b['w'], b['y'] + b['h'] * t)]
        best = None
        for j_, (x, y) in enumerate(cands):
            if buried(x, y, b['name']):
                continue
            s = serve(x, y)
            if s is None:
                continue
            key = (0 if j_ == 0 else 1, abs(pos[s][0] - x) + abs(pos[s][1] - y))
            if abs(pos[s][0] - x) + abs(pos[s][1] - y) <= reach and (best is None or key < best[0]):
                best = (key, (x, y), s)
        if best is None:
            xy = cands[0]; s = serve(*xy)
        else:
            _, xy, s = best
        block_pin[b['name']] = xy; block_srv[b['name']] = s
        sinks.append((f"{b['name']}.rst", xy, b['name'], s))
    tree = set()
    for s in list(station_srv.values()) + list(block_srv.values()):
        while s is not None and s not in tree:
            tree.add(s); s = par[s]
    gate = reset_reach_gate(geo, {n: pos[n] for n in par}, sinks, [(c, par[c]) for c in tree], reach=reach)
    # station clock: the geometric cell of the station point (S81.CLK), legacy: the nearest block region's root
    cen = [(b['x'] + b['w'] / 2, b['y'] + b['h'] / 2, reg[b['name']]) for b in blocks]

    def creg(c):
        x, y = pos[c]
        if grid is not None:
            return grid.region(x, y)
        return min(cen, key=lambda t: abs(t[0] - x) + abs(t[1] - y))[2]

    def crossing(c):
        return int(grid is not None and par[c] is not None and creg(c) != creg(par[c]))
    reld = {}

    def rel(c):
        """release edges of node c after rst_sync1 minus 1 (= dep(c) + the crossing stages on its path)"""
        if c not in reld:
            reld[c] = 0 if par[c] is None else rel(par[c]) + 1 + crossing(c)
        return reld[c]
    v = ['  // ---- regional synchronous-release reset relay tree: one dsfd_rly_1 station per 400-um street cell + the reset',
         '  //      bit carried in the lane stations (dsfd_rly_1 companion at the station point, S81-DIE5)',
         '  wire rst_sync0, rst_sync1;',
         f'  {rr["EW"]} rst_root0 (.ck(ck_{creg(root)}), .rs(rst_n), .i(rst_n), .o(rst_sync0));',
         f'  {rr["EW"]} rst_root1 (.ck(ck_{creg(root)}), .rs(rst_sync0), .i(rst_sync0), .o(rst_sync1));']
    name = {}
    for c in sorted(tree, key=lambda n: (dep(n), str(n))):
        name[c] = (f'rs_{c[1]}_{c[2]}' + (f'_{c[3]}' if c[3] else '')) if c[0] == 'c' else f'rsl_{c[1]}_{c[2]}'
    place, xings = [], []
    for c in sorted(tree, key=lambda n: (dep(n), str(n))):
        p = par[c]
        up = 'rst_sync1' if p is None else name[p]
        if p is None:
            d = 'EW'
        else:
            dx, dy = pos[c][0] - pos[p][0], pos[c][1] - pos[p][1]
            d = ('WE' if dx > 0 else 'EW') if abs(dx) >= abs(dy) else ('SN' if dy > 0 else 'NS')
        if crossing(c):
            # S81.CLK reset release crossing: one extra stage on the RECEIVING cell's root, beside the child station
            xk = f'{name[c]}_xk'
            v.append(f'  wire {xk};')
            v.append(f'  {rr[d]} st_{xk} (.ck(ck_{creg(c)}), .rs({up}), .i({up}), .o({xk}));   '
                     f'// reset release crossing {creg(p)} -> {creg(c)}')
            place.append(dict(inst=f'st_{xk}', master=rr[d], orient=ORIENT[d] if master else ('MX' if d == 'SN' else 'R0'),
                              xy=pos[c], kind='reset_crossing'))
            xings.append(dict(parent=f'st_{name[p]}', stage=f'st_{xk}', child=f'st_{name[c]}',
                              src_region=creg(p), dst_region=creg(c)))
            up = xk
        v.append(f'  wire {name[c]};')
        v.append(f'  {rr[d]} st_{name[c]} (.ck(ck_{creg(c)}), .rs({up}), .i({up}), .o({name[c]}));')
        place.append(dict(inst=f'st_{name[c]}', master=rr[d], orient=ORIENT[d] if master else ('MX' if d == 'SN' else 'R0'),
                          xy=pos[c], kind='street' if c[0] == 'c' else 'lane'))
    leaves = collections.Counter(list(station_srv.values()) + list(block_srv.values()))
    depths = [rel(c) + 2 for c in tree]
    ncomp = sum(1 for c in tree if c[0] == 's')
    summary = dict(grid_um=GRID, root_cell=list(root[1:]), root_xy=pos[root], stations=len(tree) + 2 + len(xings),
                   street_stations=len(tree) - ncomp, lane_reset_bits=ncomp, max_release_depth=max(depths),
                   min_release_depth=min(depths), max_relay_fanout=max(leaves.values()),
                   region_release_depth={r: max(rel(c) + 2 for c in tree if creg(c) == r) for r in set(map(creg, tree))},
                   block_release_depth={b: rel(s) + 3 for b, s in block_srv.items() if s is not None},
                   clock_regions=sorted(set(map(creg, tree)) | {creg(root)}),
                   release_crossings=len(xings), crossings=xings,
                   max_crossings_on_path=max((rel(c) - dep(c) for c in tree), default=0),
                   crossing_rule=('S81.CLK: a reset-tree edge between two geometric regions = one extra registered '
                                  'stage <child>_xk on the receiving region root; release depth +1 per crossing'
                                  if grid is not None else 'logical regions: no crossing stages'),
                   block_pin_moved={b: [round(xy[0], 1), round(xy[1], 1)] for b, xy in block_pin.items()
                                    if xy != (next(bb for bb in blocks if bb['name'] == b)['x'] + next(bb for bb in blocks if bb['name'] == b)['w'] / 2,
                                              next(bb for bb in blocks if bb['name'] == b)['y'])},
                   unreachable_cells=sum(1 for c in free if ('c',) + c not in par), components=len(set(comp.values())),
                   reach_gate=gate)
    nm_ = lambda s: name.get(s, 'rst_sync1') if s is not None else 'rst_sync1'
    rdepth = {name[c]: rel(c) + 2 for c in tree}
    rdepth.update({x['stage'][3:]: rdepth[x['child'][3:]] - 1 for x in xings})
    rdepth['rst_sync1'] = 1
    net_clocks = {name[c]: f'ck_{creg(c)}' for c in tree}
    net_clocks.update({x['stage'][3:]: f"ck_{x['dst_region']}" for x in xings})
    net_clocks['rst_sync1'] = f'ck_{creg(root)}'
    return dict(verilog=v, depth=rdepth, net_clocks=net_clocks, station_leaf={k: nm_(s) for k, s in station_srv.items()},
                block_leaf={b: nm_(s) for b, s in block_srv.items()},
                block_parent={b: (name[par[s]] if s is not None and par[s] is not None else 'rst_sync1') for b, s in block_srv.items()},
                block_pin=block_pin, summary=summary, place=place)
