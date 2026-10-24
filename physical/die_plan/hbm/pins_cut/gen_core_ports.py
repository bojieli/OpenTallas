#!/usr/bin/env python3
"""HBM-P5-PINS: port lists of the planned hard cores that have no as-built view (G3 prerequisite, GEOM-REVIEW5).

Each core is cut out of the hierarchical yosys netlist of its as-built master (netcut.py: every net bit that touches
a core member and anything outside the core is one port bit).  Where the core is the HBM-P4-SPLIT RTL twin of a
module that is not in the as-built netlist (score hcol, Sinkhorn step0/steady), its ports are the twin's declared
ports (RTL).  Output: ports JSON in the pins_plan_v2.py --ports schema {module: {module: [[name, dir, width, lsb]]}}
plus a provenance record per core.

    python3 gen_core_ports.py --net DIR --out ports_cut.json
"""
import argparse, json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netcut                                                     # noqa: E402


def busify(res, strip=''):
    """netcut result -> [[name, dir, width, 0]] (one bus per (label, dir))."""
    ports, used = [], set()
    for d, key in (('input', 'inp'), ('output', 'out')):
        for lbl, n in sorted(res[key].items()):
            nm = lbl[len(strip):] if strip and lbl.startswith(strip) else lbl
            nm = nm.replace('~', 'x_')
            nm = re.sub(r'[^A-Za-z0-9_]+', '_', nm).strip('_') or 'glue'
            nm = re.sub(r'_+', '_', nm)
            base, k = nm, 1
            while nm in used:
                nm = f'{base}_{k}'; k += 1
            used.add(nm)
            ports.append([nm, d, n, 0])
    return ports


def tot(ports):
    i = sum(p[2] for p in ports if p[1] == 'input'); o = sum(p[2] for p in ports if p[1] == 'output')
    return i, o


def find_paths(n, top, typ_rx, pre='', mod=None, out=None):
    out = [] if out is None else out
    mod = n.resolve(top) if mod is None else mod
    for i, t in n.children(mod):
        p = pre + i
        if re.search(typ_rx, netcut.base(t)):
            out.append(p)
        else:
            find_paths(n, top, typ_rx, p + '/', t, out)
    return out


def twin_ports():
    """HBM-P4-SPLIT RTL twins (declared ports; widths from their localparams)."""
    hcol = [['clk_pair', 'input', 2, 0], ['rst_col', 'input', 1, 0], ['qv_b', 'input', 1, 0],
            ['q_b', 'input', 8 + 4 * 128 + 4 * 8 + 16, 0], ['key', 'input', 4 * 136, 0], ['hid4', 'input', 32, 0],
            ['cs_in', 'input', 32, 0], ['cf_in', 'input', 1, 0], ['cs_out', 'output', 32, 0],
            ['cf_out', 'output', 1, 0], ['prdy', 'output', 2, 0]]
    step0 = [['clk', 'input', 1, 0], ['load', 'input', 1, 0], ['in_e', 'input', 512, 0], ['pa', 'input', 1, 0],
             ['pb', 'input', 1, 0], ['b_q', 'output', 512, 0], ['bbad_q', 'output', 1, 0], ['abad_q', 'output', 1, 0]]
    steady = [['clk', 'input', 1, 0], ['rst_n', 'input', 1, 0], ['in_valid', 'input', 1, 0],
              ['in_ready', 'output', 1, 0], ['load', 'output', 1, 0], ['pa', 'output', 1, 0], ['pb', 'output', 1, 0],
              ['b_q', 'input', 512, 0], ['bbad_q', 'input', 1, 0], ['abad_q', 'input', 1, 0],
              ['out_valid', 'output', 1, 0], ['y', 'output', 512, 0], ['fault', 'output', 1, 0],
              ['busy', 'output', 1, 0]]
    return hcol, step0, steady


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--net', required=True, help='dir of <master>.netlist.v (hierarchical yosys, r18h5 recipe)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--plan', default=os.path.join(HERE, '..', 'die_plan.json'))
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    want = set()
    for t in plan['partition_types'].values():
        for c in t.get('hard_cores', []):
            if not c.get('pins_file'):
                want.add(c['module'])
    P, prov = {}, {}

    def put(mod, ports, how):
        if mod not in want:
            return
        P[mod] = {mod: ports}
        i, o = tot(ports)
        prov[mod] = dict(how=how, inp=i, out=o)

    def net(m):
        return netcut.Netlist(os.path.join(a.net, f'{m}.netlist.v'))

    # ---- bankq x4: lanes0_2 / lanes3_5 = 3 hcp_lanes leaves each; lanes6_7_bank = the rest of the master
    for m in ('ot_hbm_hc_bankq0_static', 'ot_hbm_hc_bankq_static', 'ot_hbm_hc_bankq_ft_static',
              'ot_hbm_hc_bankq_term_static'):
        n = net(m)
        lg = sorted(find_paths(n, m, r'hcp_lanes'), key=lambda p: int(re.search(r'\[(\d+)\]\D*$', p).group(1)))
        assert len(lg) == 8, (m, lg)
        pre = lg[0].rsplit('/', 1)[0] + '/'
        for lbl, inc in (('lanes0_2', lg[0:3]), ('lanes3_5', lg[3:6])):
            put(f'{m}__{lbl}', busify(n.cut(m, inc), pre), f'netcut {m}: {", ".join(inc)}')
        put(f'{m}__lanes6_7_bank', busify(n.cut(m, [''], lg[0:6]), pre), f'netcut {m}: master minus lanes 0..5')
    # ---- hc_root: tails minus the Sinkhorn (+ the Sinkhorn twin step0 / steady), hcp sys1
    m = 'ot_hbm_hc_root_static'
    n = net(m)
    tails = sorted(find_paths(n, m, r'hc_tail_unit'))
    _, step0, steady = twin_ports()
    for k, tp in enumerate(tails):
        sink = [s for s in find_paths(n, m, r'ot_hdc_sinkhorn') if s.startswith(tp + '/')]
        put(f'{m}__tail{k}_rest', busify(n.cut(m, [tp], sink), tp + '/'), f'netcut {m}: {tp} minus {sink}')
        put(f'{m}__tail{k}_sk_step0', step0, 'RTL twin ot_hdc_sk_step0 (rtl/hdc/v41/ot_hdc_sinkhorn_s.sv)')
        put(f'{m}__tail{k}_sk_steady', steady, 'RTL twin ot_hdc_sk_steady (rtl/hdc/v41/ot_hdc_sinkhorn_s.sv)')
    core = find_paths(n, m, r'hcp_sys1')
    put(f'{m}__hcp_sys1', busify(n.cut(m, core)), f'netcut {m}: {core}')
    # ---- score quarter: 64 half columns (RTL twin ot_hidx_score_hcol) + 2 tails
    m = 'ot_hbm_idx_score_quarter_static'
    n = net(m)
    hcol, _, _ = twin_ports()
    for mod in sorted(want):
        if mod.startswith(m + '__r'):
            put(mod, hcol, 'RTL twin ot_hidx_score_hcol (rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv)')
    for tp in find_paths(n, m, r'idx_tail_native'):
        e = re.search(r'ge\[(\d+)\]', tp).group(1)
        put(f'{m}__tail{e}', busify(n.cut(m, [tp])), f'netcut {m}: {tp}')
    # ---- tkm: 32 tiles + root (the rest)
    m = 'ot_hgi_coll_tkm_m_tp192'
    n = net(m)
    tiles = find_paths(n, m, r'tkm_tile_e86')
    for tp in tiles:
        k = re.search(r'g_tiles\[(\d+)\]', tp).group(1)
        put(f'{m}__tile{k}', busify(n.cut(m, [tp]), tp + '/'), f'netcut {m}: {tp}')
    put(f'{m}__root', busify(n.cut(m, [''], tiles)), f'netcut {m}: master minus the 32 tiles')
    # ---- sfu split3: 16 lanes (sfu + lane_map), 2 operand stores, ctl (the rest)
    m = 'ot_hgi_sfu_core_split3'
    n = net(m)
    sfu = find_paths(n, m, r'ot_su12_sfu')
    maps = find_paths(n, m, r'sfu_lane_map')
    grp = find_paths(n, m, r'su_lgroup2')
    mem = [p for p in find_paths(n, m, r'operand_store')]
    lanes = []
    for k in range(16):
        inc = [p for p in sfu + maps if f'g_lane[{k}].' in p]
        lanes += inc
        put(f'{m}__lane{k}', busify(n.cut(m, inc), inc[0].rsplit('/', 1)[0] + '/'), f'netcut {m}: {inc}')
    ga = [p for p in grp if re.search(r'g_operand\[[01]\]', p)]
    gb = [p for p in grp if not re.search(r'g_operand\[[01]\]', p)]
    put(f'{m}__opstore_a', busify(n.cut(m, mem, gb), mem[0] + '/'), f'netcut {m}: {mem} minus {gb}')
    put(f'{m}__opstore_b', busify(n.cut(m, gb), mem[0] + '/'), f'netcut {m}: {gb}')
    put(f'{m}__ctl', busify(n.cut(m, [''], lanes + mem)), f'netcut {m}: master minus lanes and operand store')
    # ---- pgslice pv0 / pv8: lanes (+ their pinned banks), side split, pretree
    for m, groups in (('ot_hbm_su_static_pgslice_lg__pv0',
                       [(f'lane_exp{k}', [k]) for k in range(15)] + [('lane_exp_l', [15])] +
                       [(f'lanes_plain{4 * j}_{4 * j + 3}', list(range(16 + 4 * j, 20 + 4 * j))) for j in range(4)]),
                      ('ot_hbm_su_static_pgslice_lg__pv8',
                       [(f'lanes{4 * j}_{4 * j + 3}', list(range(4 * j, 4 * j + 4))) for j in range(8)])):
        n = net(m)
        ln = find_paths(n, m, r'su_static_lane')
        bk = find_paths(n, m, r'pinned_bank')
        plan_mod = 'ot_hbm_su_static_pgslice_lg'
        for lbl, ks in groups:
            inc = [p for p in ln if int(re.search(r'g_lane\[(\d+)\]', p).group(1)) in ks] + \
                  [p for p in bk if int(re.search(r'g_bank\[(\d+)\]', p).group(1)) in ks]
            put(f'{plan_mod}__{lbl}', busify(n.cut(m, inc), inc[0].rsplit('/', 1)[0] + '/'), f'netcut {m}: {inc}')
        pt = find_paths(n, m, r'red_pretree_s')
        put(f'{plan_mod}__pretree', busify(n.cut(m, pt)), f'netcut {m}: {pt}')
        side = find_paths(n, m, r'su_static_side__')
        if side:
            sp = [s for s in find_paths(n, m, r'side_softplus')]
            put(f'{plan_mod}__side_softplus', busify(n.cut(m, sp), sp[0].rsplit('/', 1)[0] + '/'), f'netcut {m}: {sp}')
            put(f'{plan_mod}__side_rest', busify(n.cut(m, side, sp), side[0] + '/'), f'netcut {m}: {side} minus {sp}')
    # ---- coll_q2 (q_rc4): ring_ag, reduce, body = the rest (r18g chainsM view netlist; the r15 stat is deleted)
    m = 'ot_hfd_coll_q2_hard_v8g'
    if os.path.exists(os.path.join(a.net, f'{m}.netlist.v')):
        n = net(m)
        ring = find_paths(n, m, r'coll_ring_ag$')
        red = find_paths(n, m, r'coll_reduce_static$')
        put(f'{m}__ring_ag', busify(n.cut(m, ring), ring[0].rsplit('/', 1)[0] + '/'), f'netcut {m}: {ring}')
        put(f'{m}__reduce', busify(n.cut(m, red), red[0].rsplit('/', 1)[0] + '/'), f'netcut {m}: {red}')
        put(f'{m}__body', busify(n.cut(m, [''], ring + red)), f'netcut {m}: master minus ring_ag and reduce')
    json.dump(P, open(a.out, 'w'))
    json.dump(prov, open(a.out.replace('.json', '.prov.json'), 'w'), indent=1, sort_keys=True)
    miss = sorted(want - set(P))
    print(f'{len(P)} core modules with ports; {len(miss)} pinless modules without a port list:')
    for mm in miss:
        print('  ', mm)
    for k, v in sorted(prov.items()):
        print(f'  {k}: in {v["inp"]} out {v["out"]}')


if __name__ == '__main__':
    main()
