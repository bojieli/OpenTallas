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
SPINE_RELAY_CH = 259.2                      # KV2: set by tools/die_top_lint.py QWEN_R22K (KV2 spine M | E relay channel; 0 = r22k as first built)
TT_ISSUE_BOTTOM = False                    # relay fix F1: the tree top's issue / status pins at its BOTTOM (toward the VM / SU)
SEQ_COMPACT_ANCHOR = 'top'                 # 'top': the compact frame at the top of the old slot (toward the SU / VM / tree top)
SEQ_COMPACT = None                         # (w, h): the closed compact ICUT sequencer (icut_t-a8f3ba53c 259.2 x 333.36)
SPINE_RELAY_CH_WM = 129.6                   # KV2: extra relay channel width between spine columns W and M


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
    if SEQ_COMPACT:
        # the compact ICUT constants sequencer (struct-close / drive-0849, CLOSED TT +12.32 / FF +4.69): the frame shrinks
        # in place, anchored at the old frame's bottom-left (its d2d words leave from its S face, toward d2d_rom)
        sq = next(i for i in insts if i.name == 'sp_constants_sequencer')
        rec['seq_compact'] = dict(old=[round(sq.w, 3), round(sq.h, 3)], new=list(SEQ_COMPACT))
        top = sq.y + sq.h
        sq.w, sq.h = SEQ_COMPACT[0] - v.SHAVE, SEQ_COMPACT[1] - v.SHAVE
        if SEQ_COMPACT_ANCHOR == 'top':
            sq.y = round(v.dn(top - sq.h - v.SHAVE, v.GY), 4)
        elif str(SEQ_COMPACT_ANCHOR).startswith('chan:'):
            # in the W | M spine channel (between the W column's right edge and the sequencer's column), centred at y
            yc = float(SEQ_COMPACT_ANCHOR.split(':')[1])
            wcol = max(i.x + i.w for i in insts if i.kind == 'spine_block' and i.x + i.w <= sq.x + 1.0 and i.name != sq.name)
            sq.x = round(v.up((wcol + sq.x - sq.w) / 2, v.GX), 4)
            sq.y = round(v.dn(yc - sq.h / 2, v.GY), 4)
        elif SEQ_COMPACT_ANCHOR == 'mid':
            sq.y = round(v.dn(top - (rec['seq_compact']['old'][1] + sq.h) / 2, v.GY), 4)
        rec['seq_compact']['anchor'] = SEQ_COMPACT_ANCHOR
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


def _compact_seq_master(v, model, old, sqi):
    """The compact ICUT sequencer frame: every die port of the r21c master on the E / W face nearest its peer (the routed
    element's pin plan is left / right / top), balanced by face capacity (2-track pitch, two layers a face); the r22k
    words dc / dh / dflt and the reset rsi as before (S face / area)."""
    Master = type(old)
    mm = Master(old.name, sqi.w, sqi.h, old.obs_top, 'compact ICUT constants sequencer (icut_t-a8f3ba53c 259.2 x 333.36)')
    by = {i.name: i for i in model['insts']}
    bits, peer = {}, {}
    for bid, cl, b, eps in model['buses']:
        for j, (inst, port) in enumerate(eps):
            if inst == sqi.name:
                p = port.lstrip('*')
                bits[p] = max(bits.get(p, 0), b)
                others = [by[x] for x, _ in eps if x != inst and x in by]
                if others:
                    peer[p] = others[0]
    cx, cy = sqi.x + sqi.w / 2, sqi.y + sqi.h / 2
    L = {'E': sqi.h, 'W': sqi.h, 'N': sqi.w, 'S': sqi.w}
    cap = {f: (2 if f in 'EW' else 1) * (L[f] - 4.0) / 0.048 for f in 'NSEW'}   # E / W: M4 + M6, N / S: M5
    cap['S'] -= 2 * 530 + 9 + 40                                  # dc / dh / dflt (added below) on the S face
    load = {f: 0 for f in 'NSEW'}
    faces = {}
    for p in sorted(bits, key=lambda q: -bits[q]):
        if p in ('dc', 'dh', 'dflt', 'rsi'):
            continue
        if bits[p] == 1 and p in old.ports and old.ports[p][0] == 'area':
            faces[p] = 'area'
            continue
        pe = peer.get(p)
        if pe is None:
            order = ['E', 'W', 'N', 'S']
        else:
            dx, dy = pe.x + pe.w / 2 - cx, pe.y + pe.h / 2 - cy
            fx, fy = ('E' if dx >= 0 else 'W'), ('N' if dy >= 0 else 'S')
            order = [fy, fx] if abs(dy) >= abs(dx) else [fx, fy]
            order += [f for f in 'NSEW' if f not in order]
        f = next((f for f in order if load[f] + bits[p] <= cap[f]), order[0])
        faces[p] = f
        load[f] += bits[p]
    for f in 'NSEW':
        fl = [p for p in faces if faces[p] == f]
        tot = sum(bits[p] for p in fl) or 1
        span_all = L[f] - 4.0 if f != 'S' else (L[f] - 4.0) * 0.5
        pos = 2.0 if f != 'S' else 2.0 + (L[f] - 4.0) * 0.5
        lay = ('M4', 'M6') if f in 'EW' else ('M5', 'M5')
        for n, p in enumerate(fl):
            span = span_all * bits[p] / tot
            mm.face(p, bits[p], f, lay[n % 2], pos + span / 2, 1)
            pos += span
    j = 0
    for p, fc in faces.items():
        if fc == 'area':
            mm.area(p, 1, mm.w / 2 + ((j % 8) - 4) * 1.6, mm.h / 2 + (j // 8 - 4) * 1.6, 1)
            j += 1
    mm.load = load
    return mm


def _wrap_masters(v, m):
    inner = v.masters

    def masters(model, k=1, port_bits=None):
        tiles = [i for i in model['insts'] if i.master == 'qfd_tile_nk']
        for i in tiles:
            i.master = 'qfd_tile_e' if i.name.split('_')[1].isdigit() and int(i.name.split('_')[1]) >= 32 else 'qfd_tile'
        sqi = next((i for i in model['insts'] if i.name == 'sp_constants_sequencer'), None)
        sq_wh = (sqi.w, sqi.h) if sqi is not None else None
        if SEQ_COMPACT and sqi is not None and m.get('r22k', {}).get('seq_compact'):
            ow, oh = m['r22k']['seq_compact']['old']       # the base generator lays the r21c faces out on the old frame
            sqi.w, sqi.h = ow, oh
        try:
            M = inner(model, k, port_bits)
        finally:
            for i in tiles:
                i.master = 'qfd_tile_nk'
            if sq_wh is not None:
                sqi.w, sqi.h = sq_wh
        if SEQ_COMPACT and sqi is not None and m.get('r22k', {}).get('seq_compact'):
            M['qfd_sp_constants_sequencer'] = _compact_seq_master(v, model, M['qfd_sp_constants_sequencer'], sqi)
        if TT_ISSUE_BOTTOM:
            tt = M['qfd_sp_tree_top']
            for pn, c in (('si', 150.0), ('so', 60.0)):
                if pn in tt.ports:
                    tt.ports[pn] = tt.ports[pn][:4] + (c,) + tt.ports[pn][5:]
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
        cmp_ = bool(SEQ_COMPACT and m.get('r22k', {}).get('seq_compact'))   # compact: the left half of the S face
        sq.face('dc', CTL_BITS, 'S', 'M5', sq.w * (0.1 if cmp_ else 0.3), 1)
        sq.face('dh', CTL_BITS, 'S', 'M5', sq.w * (0.35 if cmp_ else 0.7), 1)
        sq.area('rsi', 1, sq.w / 2, sq.h / 2 + 12.0, 1)
        sq.face('dflt', 9, 'S', 'M5', sq.w * (0.22 if cmp_ else 0.5), 1)
        # collective: its clock pin (was the PLL output pll_stream) stays at the same place, now an input
        return M
    v.masters = masters
