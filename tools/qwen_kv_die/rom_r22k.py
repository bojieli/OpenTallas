"""kv-die 2026-10-09 (OWNER DECISION ~04:00 PT, option 1a): the r22k Qwen3-8B ROM die of the ROM die + KV die pair.

r22k = r21c (tools/die_top_lint.py QWEN_R21C) with every KV-die block moved off, applied through the generator's
`before_relays` hook of tools/qwen_rom_fulldie_b3r2.selected() (the relays are then derived for the new buses):

  removed   the four HBM3E PHYs, their controllers, the 128 per-PC CDC frames, the four KV landing concentrators
            (qfd_kvc / qfd_kvc_n), the die hub (qfd_hub) and the hub <-> strip link stations, with every bus among them
            (dfi, CDC, landing fabric to the tiles, the hub <-> strip link channels): the W and E HBM bands go, the die
            narrows by 2 x 1,381.5 um less a 21.6 um margin each side.
  tiles     qfd_tile / qfd_tile_e -> qfd_tile_nk: attention runs on the KV die (near-HBM row engines), so the tile has
            no KV slice and no landing hop (li / lo); the r19 slot width is kept (a tighter re-slot is a later option).
  added     ucie_kv  ot_qkvd_ucie_x64_phy (777.6 x 777.6 um, bump field on the S die edge) at the bottom of spine
                     column M (free from y 21.6 to 6,287.8 um in r21c) -- the KV die abuts the S edge below the spine;
            d2d_rom  qfd_d2d_rom: the ROM end of the link (rtl/qwen_sys/kv_die_20261009/ot_qkvd_rom_end.sv: the
                     hub's SU / VM face x3 / ar / ea / eq / ecr unchanged, plus the sequencer's CTL / HCTL words),
                     directly above the PHY (FDI pins abut);
            clk_rx   qfd_clkrx at the hub's slot: the clock root (the KV-die PLL's forwarded clock from the bump beside
                     the PHY, deskew buffer, the same 121 region trunks the hub drove) and the reset synchroniser.
  rebound   x3 / attn_ret / emb / emb_a / emb_cr end at d2d_rom instead of the hub; clk_root (formerly
            io_collective.pll_stream -> hub) is driven by clk_rx (the PLL leaves the ROM die); new words seq_d2d
            (sequencer -> d2d_rom, CTL class) and d2d_seq (d2d_rom -> sequencer, HCTL class), the forwarded clock
            pll_fwd and reset rst_fwd (d2d_rom bumps -> clk_rx), the clock / reset of d2d_rom + PHY, and clk_rx's
            synchronised reset to the sequencer (rsi), which distributes it in its words as today.
Contract: results/arch/qwen_kv_die_20261009/CONTRACT.md.
"""
import copy

MOVED_KINDS = {'phy', 'ctrl', 'cdc', 'link_fifo', 'hub_element', 'link_station'}
DROP_CLASSES = {'kv_land', 'link_channel', 'link_spine', 'hbm_cdc', 'cdc_core', 'phy_dfi', 'strip_fan'}
REMAP_HUB = {'x3': 'x3', 'ar': 'ar', 'eq': 'eq', 'ea': 'ea', 'ecr': 'ecr'}      # hub port -> d2d_rom port
UCIE = 'ot_qkvd_ucie_x64_phy'
UCIE_WH = 777.6
FDI_BITS = 1 + 1 + 548 + 1 + 548          # tx_up, tx_v, tx_flit, rx_v, rx_flit
CTL_BITS = 528 + 1 + 1                    # word + valid down, credit back
D2D_H = 518.4                             # qfd_d2d_rom frame height (cw x 518.4 = 0.403 mm2), see CONTRACT.md
MARGIN = 21.6


def surgery(v, m):
    by = {i.name: i for i in m['insts']}
    g = m['geo']
    moved = {n for n, i in by.items() if i.kind in MOVED_KINDS}
    hub = by['hub_el']
    rec = dict(removed_instances={}, dropped_buses={}, rebound=[], added_instances=[], added_buses=[])
    for n in moved:
        rec['removed_instances'][by[n].master] = rec['removed_instances'].get(by[n].master, 0) + 1
    nb = []
    for bid, cls, bits, eps in m['buses']:
        hit = [e for e in eps if e[0] in moved]
        if cls in DROP_CLASSES:
            rec['dropped_buses'][cls] = rec['dropped_buses'].get(cls, 0) + 1
            continue
        if not hit:
            nb.append((bid, cls, bits, eps))
            continue
        if cls == 'clock_trunk':
            if bid == 'clk_root':
                # the PLL leaves the ROM die: the clock root is the forwarded clock at clk_rx
                ne = [('clk_rx', 'pll_root')] + [e for e in eps if e[0] not in moved and e[0] != 'hub_el']
                rec['rebound'].append(f'{bid}: source io_collective.pll_stream -> clk_rx.pll_root (collective is a sink)')
            else:
                ne = [('clk_rx', p) if i == 'hub_el' else (i, p) for i, p in eps if i not in moved or i == 'hub_el']
            if len(ne) >= 2 and ne[0][0] == 'clk_rx':
                nb.append((bid, cls, bits, ne))
            else:
                rec['dropped_buses']['clock_trunk'] = rec['dropped_buses'].get('clock_trunk', 0) + 1
            continue
        if cls == 'reset':
            rec['dropped_buses']['reset'] = rec['dropped_buses'].get('reset', 0) + 1
            continue
        if all(e[0] == 'hub_el' for e in hit) and all(e[1] in REMAP_HUB for e in hit):
            ne = [('d2d_rom', REMAP_HUB[p]) if i == 'hub_el' else (i, p) for i, p in eps]
            if bid == 'attn_ret':
                bits = 519          # + the RES tag {g, beat}: the hub may finish g = 0 / 1 in either order
            nb.append((bid, cls, bits, ne))
            rec['rebound'].append(f'{bid} ({bits} b): hub_el.{hit[0][1]} -> d2d_rom.{REMAP_HUB[hit[0][1]]}')
            continue
        raise ValueError(f'r22k: unhandled bus {bid} ({cls}) touching moved {hit}')
    # ---- geometry: drop the moved instances, rename the tiles, shift out the W band ----
    keep = [i for i in m['insts'] if i.name not in moved]
    for i in keep:
        if i.master in ('qfd_tile', 'qfd_tile_e'):
            i.master = 'qfd_tile_nk'
    dx = g['x_arr_w'] - MARGIN
    xr = g['x_eband']
    assert min(i.x for i in keep) >= dx - 1e-6 and max(i.x + i.w for i in keep) <= xr + 1e-6, 'kept outside the bands'
    for i in keep:
        i.x = round(i.x - dx, 4)
    W = round(xr - dx + MARGIN, 4)
    xc = g['x_col_m'] - dx
    y0 = g['y0']
    insts = keep
    Inst = type(hub)
    ph = Inst('ucie_kv', UCIE, xc, y0, UCIE_WH, UCIE_WH, 'R0', kind='phy_d2d', region='io', domain='stream_1p2')
    ad = Inst('d2d_rom', 'qfd_d2d_rom', xc, round(y0 + UCIE_WH + v.GY * 1, 4), g['cw'] - v.SHAVE,
              v.up(D2D_H, v.GY) - v.SHAVE, 'R0', kind='d2d', region='io', domain='stream_1p2')
    ck = Inst('clk_rx', 'qfd_clkrx', round(hub.x - dx, 4), hub.y, hub.w, hub.h, 'R0', kind='clock_root',
              region=hub.region, domain='stream_1p2')
    insts += [ph, ad, ck]
    rec['added_instances'] = [i.d() for i in (ph, ad, ck)]
    top_free = 6287.76     # r21c spine column M is free up to the sequencer
    assert ad.y + ad.h < top_free, 'd2d_rom does not fit under the sequencer'
    add = [('d2d_fdi', 'd2d_fdi', FDI_BITS, [('d2d_rom', 'fdi'), ('ucie_kv', 'fdi')]),
           ('seq_d2d', 'sequencer', CTL_BITS, [('sp_constants_sequencer', 'dc'), ('d2d_rom', 'dc')]),
           ('d2d_seq', 'sequencer', CTL_BITS, [('d2d_rom', 'dh'), ('sp_constants_sequencer', 'dh')]),
           ('pll_fwd', 'clock_trunk', 1, [('d2d_rom', 'pll_fwd_o'), ('clk_rx', 'pll_fwd')]),
           ('rst_fwd', 'spine_local', 1, [('d2d_rom', 'rst_fwd_o'), ('clk_rx', 'rst_fwd')]),
           ('clk_d2d', 'clock_trunk', 1, [('clk_rx', 'pll_d2d'), ('d2d_rom', 'ck'), ('ucie_kv', 'clk')]),
           ('rst_d2d', 'spine_local', 1, [('clk_rx', 'rso_d2d'), ('d2d_rom', 'rst_n'), ('ucie_kv', 'rst_n')]),
           ('rst_seq', 'spine_local', 1, [('clk_rx', 'rso_seq'), ('sp_constants_sequencer', 'rsi')])]
    nb += add
    rec['added_buses'] = [(b[0], b[1], b[2], b[3]) for b in add]
    # regions: drop the HBM bands, shift the rest
    regs = []
    for r in m.get('regions', []):
        if r['kind'] in ('phy', 'ctrl', 'strip', 'cdc', 'cdc_col'):
            continue
        x0, y0r, x1, y1 = r['rect']
        x0, x1 = max(x0 - dx, 0.0), min(x1 - dx, W)
        if x1 - x0 <= 1.0:
            continue
        regs.append(dict(r, rect=[round(x0, 4), y0r, round(x1, 4), y1]))
    m['regions'] = regs
    for k in list(g):
        if k.startswith('x_') and isinstance(g[k], (int, float)):
            g[k] = round(g[k] - dx, 4)
    old_col_x = m['col_x']
    m['col_x'] = lambda c, f=old_col_x: f(c) - dx
    g['x_wband'] = 0.0
    g['x_eband'] = W
    g['r22k_dx_um'] = dx
    m['insts'] = insts
    m['buses'] = nb
    H = m['die']['h']
    m['die'] = dict(m['die'], w=W, mm2=round(W * H / 1e6, 3), margin_mm2=round(858 - W * H / 1e6, 3))
    m['r22k'] = rec
    _wrap_masters(v, m)


def _wrap_masters(v, m):
    inner = v.masters

    def masters(model, k=1, port_bits=None):
        tiles = [i for i in model['insts'] if i.master == 'qfd_tile_nk']
        for i in tiles:
            i.master = 'qfd_tile_e' if i.name.split('_')[1].isdigit() and int(i.name.split('_')[1]) >= 32 else 'qfd_tile'
        try:
            M = inner(model, k, port_bits)
        finally:
            for i in tiles:
                i.master = 'qfd_tile_nk'
        t = M.pop('qfd_tile')
        M.pop('qfd_tile_e', None)
        t = copy.deepcopy(t)
        t.name = 'qfd_tile_nk'
        for p in ('li', 'lo'):
            if p in t.ports:
                t.ports.pop(p)
                t.order.remove(p)
        t.note = 'r22k: W12 ROM tile WITHOUT the KV slice and landing hop (attention on the KV die)'
        M['qfd_tile_nk'] = t
        used = {i.master for i in model['insts']}
        for name in [n for n in M if n not in used]:
            M.pop(name)
        Master = type(t)
        used_ports = {}
        for bid, cl, bits, eps in model['buses']:
            for inst, port in eps:
                used_ports.setdefault(inst, {})[port.lstrip('*')] = bits
        by = {i.name: i for i in model['insts']}
        # UCIe PHY (real LEF geometry: FDI pins on the top edge, clk / rst_n beside them)
        ph = Master(UCIE, UCIE_WH - v.SHAVE, UCIE_WH - v.SHAVE, 5, 'UCIe-A x64 PHY + D2D adapter abstract '
                    '(physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy)')
        ph.face('fdi', FDI_BITS, 'N', 'M5', ph.w / 2, 1)
        ph.face('clk', 1, 'N', 'M5', ph.w / 2 - FDI_BITS * 0.096 - 4.0, 1)
        ph.face('rst_n', 1, 'N', 'M5', ph.w / 2 - FDI_BITS * 0.096 - 6.0, 1)
        M[UCIE] = ph
        a = by['d2d_rom']
        ad = Master('qfd_d2d_rom', a.w, a.h, 7, 'ROM end of the ROM <-> KV die link (ot_qkvd_rom_end)')
        ad.face('fdi', FDI_BITS, 'S', 'M5', ad.w / 2, 1)
        ad.face('ck', 1, 'S', 'M5', ad.w / 2 - FDI_BITS * 0.096 - 4.0, 1)
        ad.face('rst_n', 1, 'S', 'M5', ad.w / 2 - FDI_BITS * 0.096 - 6.0, 1)
        ad.face('pll_fwd_o', 1, 'S', 'M5', 20.0, 1)
        ad.face('rst_fwd_o', 1, 'S', 'M5', 24.0, 1)
        n_side = [('x3', 512), ('ea', 26), ('ecr', 1), ('eq', 513), ('ar', 519), ('dc', CTL_BITS), ('dh', CTL_BITS)]
        span = ad.w - 40.0
        tot = sum(b for _, b in n_side)
        x = 20.0
        for p, b in n_side:
            w_ = span * b / tot
            ad.face(p, b, 'N', 'M4' if p in ('x3', 'eq', 'dc') else 'M6', x + w_ / 2, 1)
            x += w_
        M['qfd_d2d_rom'] = ad
        c = by['clk_rx']
        cm = Master('qfd_clkrx', c.w, c.h, 7, 'ROM-die clock root (forwarded KV-die PLL clock) + reset synchroniser')
        j = 0
        for p in sorted(used_ports.get('clk_rx', {})):
            cm.area(p, 1, min(cm.w - 1.0, max(1.0, cm.w / 2 + ((j % 12) - 6) * 1.6)),
                    min(cm.h - 1.0, max(1.0, cm.h / 2 + (j // 12 - 5) * 1.6)), 1)
            j += 1
        M['qfd_clkrx'] = cm
        sq = M['qfd_sp_constants_sequencer']
        sq.face('dc', CTL_BITS, 'S', 'M4', sq.w * 0.3, 1)
        sq.face('dh', CTL_BITS, 'S', 'M6', sq.w * 0.7, 1)
        sq.area('rsi', 1, sq.w / 2, sq.h / 2 + 12.0, 1)
        # collective: its clock pin (was the PLL output pll_stream) stays at the same place, now an input
        return M
    v.masters = masters
