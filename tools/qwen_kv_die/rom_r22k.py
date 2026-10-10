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
            ckb_rom  qfd_ckbump: the forwarded clock / reset bump pair from the KV die (pad cell) beside the macro;
            d2d_rom  qfd_d2d_rom: the ROM end of the link (rtl/qwen_sys/kv_die_20261009/ot_qkvd_rom_end.sv: the
                     hub's SU / VM face x3 / ar / ea / eq / ecr unchanged, plus the sequencer's CTL / HCTL words),
                     directly above the PHY (FDI pins abut);
            clk_rx   qfd_clkrx at the hub's slot: the clock root (the KV-die PLL's forwarded clock from the bump beside
                     the PHY, deskew buffer, the same 121 region trunks the hub drove) and the reset synchroniser.
  rebound   x3 / attn_ret / emb / emb_a / emb_cr end at d2d_rom instead of the hub; clk_root (formerly
            io_collective.pll_stream -> hub) is driven by clk_rx (the PLL leaves the ROM die); new words seq_d2d
            (sequencer -> d2d_rom, CTL class) and d2d_seq (d2d_rom -> sequencer, HCTL class), the forwarded clock
            pll_fwd and reset rst_fwd (ckb_rom bump cell -> clk_rx), the clock / reset of d2d_rom + PHY, and clk_rx's
            synchronised reset to the sequencer (rsi), which distributes it in its words as today.
Contract: results/arch/qwen_kv_die_20261009/CONTRACT.md.

Opt-in r22kcs (die-evidence-2 2026-10-09, `surgery_cs`; default r22k unchanged): the sequencer logic in its CLOSED
compact outline (qfd_sp_constants_sequencer_sys ICUT, route qfd_sp_constants_sequencer_sys_icut_t-a8f3ba53c-tc-hm10-
lvt-cl, 259.2 x 333.36 um, TT +12.32 / FF +4.69 / DRC 0) instead of the r21m 777.6 x 2,775.6 um constants+sequencer
reservation.  The reservation also held the constant ROM (ot_qfd_crom, 48 ot_rom_4096x266_m8, cfg qfd_crom48
777.6 x 1,000): it becomes its own instance sp_crom (master qfd_crom) with the reservation's ca / cq ports at their old
N-face offsets; the sequencer keeps every other port (names, widths) on the closed route's pin plan (pin-region rule
of physical/qwen_die_masters/cfg/qfd_sp_constants_sequencer_sys_icut_t.env: inputs W, outputs E, clock / reset N).
Both sit inside the old reservation, at the arrangement with the least bit-weighted pin-to-neighbour distance
(`_compact_seq`); the relays are then derived for the new pin positions as for every other bus.
"""
import copy
import functools
import os

MOVED_KINDS = {'phy', 'ctrl', 'cdc', 'link_fifo', 'hub_element', 'link_station'}
DROP_CLASSES = {'kv_land', 'link_channel', 'link_spine', 'hbm_cdc', 'cdc_core', 'phy_dfi', 'strip_fan'}
REMAP_HUB = {'x3': 'x3', 'ar': 'ar', 'eq': 'eq', 'ea': 'ea', 'ecr': 'ecr'}      # hub port -> d2d_rom port
UCIE = 'ot_qkvd_ucie_x64_phy'
UCIE_WH = 777.6
FDI_BITS = 1 + 1 + 548 + 1 + 548          # tx_up, tx_v, tx_flit, rx_v, rx_flit
CTL_BITS = 528 + 1 + 1                    # word + valid down, credit back
D2D_H = 518.4                             # qfd_d2d_rom frame height (cw x 518.4 = 0.403 mm2), see CONTRACT.md
MARGIN = 21.6
SPINE_RELAY_CH = 259.2                      # KV2: set by tools/die_top_lint.py QWEN_R22K (KV2 spine M | E relay channel; 0 = r22k as first built)
SPINE_RELAY_CH_WM = 129.6                   # KV2: extra relay channel width between spine columns W and M


def surgery(v, m, compact_seq=False):
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
    cb = Inst('ckb_rom', 'qfd_ckbump', round(xc - 43.2 - 4.32, 4), y0, 43.2 - v.SHAVE, 43.2 - v.SHAVE, 'R0', kind='bump',
              region='io', domain='stream_1p2')
    insts += [ph, ad, ck, cb]
    rec['added_instances'] = [i.d() for i in (ph, ad, ck, cb)]
    top_free = 6287.76     # r21c spine column M is free up to the sequencer
    assert ad.y + ad.h < top_free, 'd2d_rom does not fit under the sequencer'
    add = [('d2d_fdi', 'd2d_fdi', FDI_BITS, [('d2d_rom', 'fdi'), ('ucie_kv', 'fdi')]),
           ('seq_d2d', 'sequencer', CTL_BITS, [('sp_constants_sequencer', 'dc'), ('d2d_rom', 'dc')]),
           ('d2d_seq', 'sequencer', CTL_BITS, [('d2d_rom', 'dh'), ('sp_constants_sequencer', 'dh')]),
           ('pll_fwd', 'clock_trunk', 1, [('ckb_rom', 'pll_ck'), ('clk_rx', 'pll_fwd')]),
           ('rst_fwd', 'reset', 1, [('ckb_rom', 'rs'), ('clk_rx', 'rst_fwd')]),
           ('clk_d2d', 'clock_trunk', 1, [('clk_rx', 'pll_d2d'), ('d2d_rom', 'ck'), ('ucie_kv', 'clk')]),
           ('rst_d2d', 'spine_local', 1, [('clk_rx', 'rso_d2d'), ('d2d_rom', 'rst_n'), ('ucie_kv', 'rst_n')]),
           ('rst_seq', 'spine_local', 1, [('clk_rx', 'rso_seq'), ('sp_constants_sequencer', 'rsi')]),
           ('d2d_flt', 'spine_local', 9, [('d2d_rom', 'flt'), ('sp_constants_sequencer', 'dflt')])]   # link-end fault + cause
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
    if SPINE_RELAY_CH:
        W = _spine_relay_channel(v, m, g, round(xc + g['cw'], 4), SPINE_RELAY_CH, W)
        rec['spine_relay_channel_um'] = SPINE_RELAY_CH
    if SPINE_RELAY_CH_WM:
        W = _spine_relay_channel(v, m, g, round(xc, 4), SPINE_RELAY_CH_WM, W)
        rec['spine_relay_channel_wm_um'] = SPINE_RELAY_CH_WM
    if SPINE_RELAY_CH or SPINE_RELAY_CH_WM:
        # the spine relay channels (centres) for the generator's vertical spine paths (b3r2 poly_of, opt-in here)
        sp = [i for i in insts if i.kind == 'spine_block']
        xs = sorted({round(i.x, 1) for i in sp})
        cols = [x for x in xs if sum(1 for i in sp if abs(i.x - x) < 1.0) >= 2]
        v.SPINE_CHANNEL_X = [round((a_ + g['cw'] + b_) / 2, 3) for a_, b_ in zip(cols, cols[1:])]
        rec['spine_channel_x'] = v.SPINE_CHANNEL_X
    H = m['die']['h']
    m['die'] = dict(m['die'], w=W, mm2=round(W * H / 1e6, 3), margin_mm2=round(858 - W * H / 1e6, 3))
    m['r22k'] = rec
    _wrap_masters(v, m)
    if compact_seq:
        _compact_seq(v, m, rec)


surgery_cs = functools.partial(surgery, compact_seq=True)


def _spine_relay_channel(v, m, g, xs, ch, W):
    """review-0528 KV2: a vertical relay channel between spine columns M and E (the r21c columns abut there, so a
    vertical word passing an E-column block -- the port-tile slabs, 1.8 mm tall -- had no relay site and took a
    1.7-2.1 mm hop or a detour).  Everything at or right of x = xs moves right by ch; the die widens by ch."""
    for i in m['insts']:
        if i.x >= xs - 1e-3:
            i.x = round(i.x + ch, 4)
    for key in ('regions', 'clock_regions'):
        out = []
        for r in m.get(key, []):
            x0, y0r, x1, y1 = r['rect']
            if x0 >= xs - 1e-3:
                x0, x1 = x0 + ch, x1 + ch
            elif x1 > xs + 1e-3:
                x1 = x1 + ch
            out.append(dict(r, rect=[round(x0, 4), y0r, round(x1, 4), y1]))
        m[key] = out
    for k in list(g):
        if k.startswith('x_') and isinstance(g[k], (int, float)) and g[k] >= xs - 1e-3:
            g[k] = round(g[k] + ch, 4)
    old = m['col_x']
    m['col_x'] = lambda c, f=old: f(c) + (ch if f(c) >= xs - 1e-3 else 0.0)
    g.setdefault('r22k_spine_relay_channels', []).append(dict(x_um=xs, w_um=ch))
    return round(W + ch, 4)


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
        n_side = [('x3', 512), ('ea', 26), ('ecr', 1), ('eq', 513), ('ar', 519), ('dc', CTL_BITS), ('dh', CTL_BITS),
                  ('flt', 9)]
        span = ad.w - 40.0
        tot = sum(b for _, b in n_side)
        x = 20.0
        for p, b in n_side:
            w_ = span * b / tot
            ad.face(p, b, 'N', 'M5', x + w_ / 2, 1)   # N face: M5 (the die track table's vertical pin layer)
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
        cbm = Master('qfd_ckbump', 43.2 - v.SHAVE, 43.2 - v.SHAVE, 7, 'forwarded clock / reset bump pair from the KV die (pad cell)')
        cbm.area('pll_ck', 1, 21.0, 21.0, 1)
        cbm.area('rs', 1, 21.0, 18.0, 1)
        M['qfd_ckbump'] = cbm
        sq = M['qfd_sp_constants_sequencer']
        sq.face('dc', CTL_BITS, 'S', 'M5', sq.w * 0.3, 1)
        sq.face('dh', CTL_BITS, 'S', 'M5', sq.w * 0.7, 1)
        sq.area('rsi', 1, sq.w / 2, sq.h / 2 + 12.0, 1)
        sq.face('dflt', 9, 'S', 'M5', sq.w * 0.5, 1)
        # collective: its clock pin (was the PLL output pll_stream) stays at the same place, now an input
        return M
    v.masters = masters


# ------------------------------------------------------------------------------------------------ r22kcs (opt-in)
SEQ_CS = 'qfd_sp_constants_sequencer_cs'
SEQ_CS_WH = (259.2, 333.36)              # the closed route's die area (LEF size), cfg qfd_sp_constants_sequencer_sys_icut_t
SEQ_CS_ROUTE = 'qfd_sp_constants_sequencer_sys_icut_t-a8f3ba53c-tc-hm10-lvt-cl'
CROM_H = 1000.08                         # qfd_crom frame (cfg qfd_crom48.env 777.6 x 1,000, on the 2.16 um row lattice)
CROM_PORTS = ('ca', 'cq')                # the reservation's constant-ROM ports (SU <-> constant ROM)
CROM_ST_BITS = 6 + 1                     # crom_stage (LW 6) + its reset, sequencer -> constant ROM (were inside the slot)
CROM_FLT_BITS = 1 + 2                    # fault + fault_code, constant ROM -> sequencer
# closed route pin plan: out words leave on E, in words arrive on W, clock / reset on N (route env PINS rule)
SEQ_CS_OUT = ('dc', 'su', 'ib', 'ti', 'cd', 'cc', 'cst')
SEQ_CS_IN = ('dh', 'dflt', 'cflt', 'sd', 'md', 'mo', 'ts')


def _port_centroids(v, mst, wmap):
    acc = {}
    for nm, layer, r in v.pin_rects(mst, 1, wmap):
        a = acc.setdefault(nm.split('[')[0], [0.0, 0.0, 0])
        a[0] += (r[0] + r[2]) / 2
        a[1] += (r[1] + r[3]) / 2
        a[2] += 1
    return {p: (a[0] / a[2], a[1] / a[2]) for p, a in acc.items()}


def _compact_seq(v, m, rec):
    """r22kcs: the closed compact sequencer + the constant ROM as its own frame, both inside the old reservation."""
    by = {i.name: i for i in m['insts']}
    s = by['sp_constants_sequencer']
    slot = (s.x, s.y, s.w, s.h)
    Inst = type(s)
    cr = Inst('sp_crom', 'qfd_crom', s.x, s.y, s.w, v.up(CROM_H, v.GY) - v.SHAVE, 'R0', kind='spine_block',
              region=s.region, domain=s.domain)
    m['insts'].append(cr)
    by['sp_crom'] = cr
    old_master = s.master
    old_dims = (s.w, s.h)
    old0 = copy.deepcopy(v.masters(m, 1)[old_master])      # the reservation's faces as r22k builds them
    s.master, s.w, s.h = SEQ_CS, SEQ_CS_WH[0], SEQ_CS_WH[1]
    nb, moved = [], []
    for bid, cl, bits, eps in m['buses']:
        if any(e == ('sp_constants_sequencer', p) for e in eps for p in CROM_PORTS):
            eps = [('sp_crom', p) if (i == 'sp_constants_sequencer' and p in CROM_PORTS) else (i, p) for i, p in eps]
            moved.append(bid)
        elif cl == 'clock_trunk' and ('sp_constants_sequencer', 'ck') in eps:
            eps = eps + [('sp_crom', 'ck')]
        nb.append((bid, cl, bits, eps))
    add = [('crom_st', 'sequencer', CROM_ST_BITS, [('sp_constants_sequencer', 'cst'), ('sp_crom', 'st')]),
           ('crom_flt', 'spine_local', CROM_FLT_BITS, [('sp_crom', 'flt'), ('sp_constants_sequencer', 'cflt')])]
    m['buses'] = nb + add
    inner = v.masters
    st = dict(crom_top=True)

    def masters(model, k=1, port_bits=None):
        cur = (s.master, s.w, s.h)
        s.master, (s.w, s.h) = old_master, old_dims       # the inner chain builds the reservation master by name
        try:
            M = inner(model, k, port_bits)
        finally:
            s.master, s.w, s.h = cur
        old = M.pop(old_master)
        q = Master = type(old)
        sq = Master(SEQ_CS, SEQ_CS_WH[0], SEQ_CS_WH[1], 7,
                    f'r22kcs: the CLOSED compact sequencer (ot_qfd_sp_constants_sequencer_sys ICUT, route {SEQ_CS_ROUTE}); '
                    'pin plan of the route (in W / out E / clock-reset N)')
        ports = {}
        for p in old0.order:
            if p in CROM_PORTS or p in ports:
                continue
            ports[p] = old0.ports[p]
        ports['cst'] = ('face', CROM_ST_BITS)
        ports['cflt'] = ('face', CROM_FLT_BITS)
        for face, names in (('E', [p for p in SEQ_CS_OUT if p in ports]), ('W', [p for p in SEQ_CS_IN if p in ports])):
            span = SEQ_CS_WH[1] - 40.0
            tot = sum(ports[p][1] for p in names) or 1
            y = 20.0
            for p in names:                                 # S -> N: the d2d words lowest (the link end is below)
                h_ = span * ports[p][1] / tot
                sq.face(p, ports[p][1], face, 'M4', y + h_ / 2, 1)
                y += h_
        sq.face('rsi', 1, 'N', 'M5', SEQ_CS_WH[0] / 2 + 4.0, 1)
        sq.area('ck', 1, SEQ_CS_WH[0] / 2, SEQ_CS_WH[1] / 2, 1)
        left = [p for p in ports if p not in sq.ports]
        assert not left, f'r22kcs: sequencer ports without a face {left}'
        M[SEQ_CS] = sq
        c = by['sp_crom']
        cm = q('qfd_crom', c.w, c.h, 7, 'constant ROM (ot_qfd_crom: 48 ot_rom_4096x266_m8), cfg qfd_crom48; '
               'the r21m reservation\'s ca / cq ports at their old N-face offsets')
        for p in CROM_PORTS:
            sp = old0.ports[p]
            cm.face(p, sp[1], sp[2], sp[3], sp[4], sp[5])
        f_ = 'S' if st['crom_top'] else 'N'
        cm.face('st', CROM_ST_BITS, f_, 'M5', c.w * 0.25, 1)
        cm.face('flt', CROM_FLT_BITS, f_, 'M5', c.w * 0.25 + 4.0, 1)
        cm.area('ck', 1, c.w / 2, c.h / 2, 1)
        M['qfd_crom'] = cm
        return M
    v.masters = masters
    # ---- arrangement: constant ROM at the top / bottom of the reservation, the sequencer in a corner of the rest
    seq_b = [(b[0], b[2], b[3]) for b in m['buses'] if b[1] not in ('clock_trunk', 'reset')
             and len(b[3]) == 2 and any(e[0] in ('sp_constants_sequencer', 'sp_crom') for e in b[3])]
    xs0, ys0, ws, hs = slot

    def score(crom_top, corner):
        st['crom_top'] = crom_top
        cr.y = round(ys0 + hs - cr.h if crom_top else ys0, 4)
        lo, hi = (ys0, cr.y) if crom_top else (cr.y + cr.h + v.SHAVE, ys0 + hs)
        sx = xs0 if corner[1] == 'W' else v.dn(xs0 + ws - s.w, v.GX)
        sy = v.up(lo, v.GY) if corner[0] == 'S' else v.dn(hi - s.h - v.SHAVE, v.GY)
        s.x, s.y = round(sx, 4), round(sy, 4)
        M = v.masters(m, 1)
        pw = v.port_widths(m, 1)
        cen = {}

        def pos(inst, port):
            i = by[inst]
            if i.master not in cen:
                mst = M[i.master]
                cen[i.master] = _port_centroids(v, mst, {q_: pw.get((i.master, q_), 0) for q_ in mst.order})
            c_ = cen[i.master].get(port)
            if c_ is None:
                return (i.cx, i.cy)
            x, y = c_
            if i.orient in ('MY', 'R180'):
                x = i.w - x
            if i.orient in ('MX', 'R180'):
                y = i.h - y
            return (i.x + x, i.y + y)
        rows = []
        for bid, bits, eps in seq_b:
            a, b_ = pos(*eps[0]), pos(*eps[1])
            d = abs(a[0] - b_[0]) + abs(a[1] - b_[1])
            rows.append(dict(bus=bid, bits=bits, eps=[list(e) for e in eps], pin_dist_um=round(d, 1)))
        return sum(r['bits'] * r['pin_dist_um'] for r in rows), rows, (s.x, s.y), (cr.x, cr.y)
    cands = []
    for crom_top in (True, False):
        for corner in ('SW', 'SE', 'NW', 'NE'):
            sc, rows, sp, cp = score(crom_top, corner)
            cands.append(dict(crom='top' if crom_top else 'bottom', seq_corner=corner, bit_um=round(sc, 0),
                              seq_xy=[round(sp[0], 3), round(sp[1], 3)], crom_xy=[round(cp[0], 3), round(cp[1], 3)],
                              buses=rows))
    best = min(cands, key=lambda c_: c_['bit_um'])
    force = os.environ.get('OT_R22KCS_ARRANGE')       # study only, e.g. 'top:SE' (crom top, sequencer SE corner)
    if force:
        best = next(c_ for c_ in cands if f"{c_['crom']}:{c_['seq_corner']}" == force)
    score(best['crom'] == 'top', best['seq_corner'])
    free_area = ws * hs - s.w * s.h - cr.w * cr.h
    rec['compact_seq'] = dict(
        route=SEQ_CS_ROUTE, master=SEQ_CS, wh_um=list(SEQ_CS_WH), old_master=old_master,
        old_slot_um=[round(xs0, 3), round(ys0, 3), round(ws, 3), round(hs, 3)],
        crom=dict(inst='sp_crom', master='qfd_crom', wh_um=[cr.w, cr.h], moved_buses=moved,
                  added_buses=[(b[0], b[1], b[2], b[3]) for b in add]),
        pin_plan=dict(E=list(SEQ_CS_OUT), W=list(SEQ_CS_IN), N=['rsi'], area=['ck']),
        chosen=dict((k_, best[k_]) for k_ in ('crom', 'seq_corner', 'bit_um', 'seq_xy', 'crom_xy')), forced=force or None,
        candidates=[dict((k_, c_[k_]) for k_ in ('crom', 'seq_corner', 'bit_um')) for c_ in cands],
        chosen_buses=best['buses'], vacated_um2=round(free_area, 1))
