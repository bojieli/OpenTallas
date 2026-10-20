"""QW-GEN5 10-20 (g5 GEN): structural clock sources of the Qwen compute die, applied after the dv case (instances
placed, masters frozen) and before the relay plan.  Every part is opt-in; defaults leave the GEN unchanged.

  OT_SPLIT_COLL_BLK_DIV=1   coll_blk (200 MHz, 5000 ps) comes from a REAL registered /6 divider (rtl/qwen_split/
                            qfd_ckdiv6.sv, instance ckdiv_coll_blk) on the collective's own core trunk clk_coll, beside
                            io_collective's blk_ck pins.  Before: clk_rx.pll_coll_blk = identity of pll_fwd (833 ps)
                            while clocks_*.tcl declared 5000 ps (functionally wrong receiver model).
  OT_SPLIT_UCIE_PHY_CLK=1   clk_ucie (1 GHz FDI) is driven by the UCIe PHY's own FDI clock output io_ucie.lclk (PHY-
                            modeled boundary, view nface_tall_1017 lclk pin).  Before: clk_rx.pll_ucie = pll_fwd.
  OT_SPLIT_CORE_FEED_XY=x,y the die-core forwarded clock enters at a centre feed bump ckb_core (qfd_ckbump) at x,y (um,
                            43.2 lattice): net pll_core = ckb_core.pll_ck -> clk_rx.pll_fwd.  The corner bump ckb_rom
                            keeps net pll_fwd for the static link's bump hop-0 stations only (OT_SPLIT_FWD_BUMP_FEED=1,
                            tools/qwen_split/bump_feed_clock.py).  The die clock build sources its forwarded spine at
                            ckb_core/pll_ck and dissolves the receiver (DC_SPINE_SOURCE + DC_DISSOLVE_RX): the ~7.5 ns
                            corner trunk (rS1: 125 of 274 spine levels) goes away.

After these, every remaining qfd_clkrx output is a stream (833.333 ps) root: the receiver is a pure identity of the
forwarded core clock, which the regional die clock replaces by its spine (no frequency is modeled any more).
Fails closed on any missing trunk / port / overlap.
"""
import os

DIV = ('ckdiv_coll_blk', 'qfd_ckdiv6', 'rtl/qwen_split/qfd_ckdiv6.sv')
DIV_WH = (21.6, 21.6)
CORE = ('ckb_core', 'qfd_ckbump')
LAT = 43.2
HALO = 4.32


def _bus(m, bid):
    js = [k for k, b in enumerate(m['buses']) if b[0] == bid]
    if len(js) != 1:
        raise ValueError(f'g5 clocking: bus {bid} absent or duplicated ({len(js)})')
    return js[0]


def _overlaps(insts, x, y, w, h, halo=HALO):
    return [i.name for i in insts if x - halo < i.x + i.w and i.x < x + w + halo and y - halo < i.y + i.h
            and i.y < y + h + halo]


def _free_near(insts, cx, cy, w, h, reach=40):
    """nearest lattice origin (43.2 um) whose w x h box (+halo) overlaps nothing; centre distance manhattan."""
    best = None
    i0, j0 = round(cx / LAT), round(cy / LAT)
    for di in range(-reach, reach + 1):
        for dj in range(-reach, reach + 1):
            x, y = round((i0 + di) * LAT, 3), round((j0 + dj) * LAT, 3)
            if x < 0 or y < 0:
                continue
            d = abs(x + w / 2 - cx) + abs(y + h / 2 - cy)
            if best is not None and d >= best[0]:
                continue
            if not _overlaps(insts, x, y, w, h):
                best = (d, x, y)
    if best is None:
        raise ValueError(f'g5 clocking: no free {w} x {h} site within {reach} lattice steps of ({cx}, {cy})')
    return best[1], best[2]


def _face_xy(inst, master, port, bit=0):
    """die (x, y) of a 'pins' / 'face' port bit of a placed R0 / MX instance (approximate face point)."""
    sp = master.ports.get(port)
    w, h = master.w, master.h
    if sp is None:
        raise ValueError(f'g5 clocking: {inst.name} ({master.name}) has no port {port}')
    if sp[0] == 'xy' and sp[3]:
        lx, ly = sp[3][bit]
    elif sp[0] == 'pins' and sp[4]:
        face, z = sp[2], sp[4][bit]
        lx, ly = {'W': (0.0, z), 'E': (w, z), 'S': (z, 0.0), 'N': (z, h)}[face]
    elif sp[0] == 'face':
        face, z = sp[2], sp[4]
        lx, ly = {'W': (0.0, z), 'E': (w, z), 'S': (z, 0.0), 'N': (z, h)}[face]
    else:
        raise ValueError(f'g5 clocking: {inst.name}.{port} has no pin geometry ({sp[0]})')
    if inst.orient in ('MX', 'R180'):
        ly = h - ly
    if inst.orient in ('MY', 'R180'):
        lx = w - lx
    return inst.x + lx, inst.y + ly


def apply(v, m):
    div = os.environ.get('OT_SPLIT_COLL_BLK_DIV', '0') == '1'
    phy = os.environ.get('OT_SPLIT_UCIE_PHY_CLK', '0') == '1'
    core = os.environ.get('OT_SPLIT_CORE_FEED_XY', '').strip()
    if not (div or phy or core):
        return None
    M = v.masters(m, 1)
    insts = m['insts']
    by = {i.name: i for i in insts}
    rec = m.setdefault('g5_clocking', dict(schema='opentallas.qwen.g5-clocking.v1', physical_qualification_eligible=False))
    if div:
        j = _bus(m, 'clk_coll_blk')
        b, c, n, eps = m['buses'][j]
        if c != 'clock_trunk' or n != 1 or eps[0] != ('clk_rx', 'pll_coll_blk'):
            raise ValueError(f'g5 clocking: clk_coll_blk is not the clk_rx.pll_coll_blk receiver trunk: {eps[:2]}')
        jc = _bus(m, 'clk_coll')
        bc, cc, nc, ec = m['buses'][jc]
        if ec[0] != ('clk_rx', 'pll_coll') or ('io_collective', 'clk') not in ec:
            raise ValueError('g5 clocking: clk_coll lacks its clk_rx.pll_coll root / collective core sink')
        jr = [k for k, bb in enumerate(m['buses']) if ('io_collective', 'rst_n') in [tuple(e) for e in bb[3]]]
        if len(jr) != 1:
            raise ValueError(f'g5 clocking: io_collective.rst_n on {len(jr)} buses')
        col = by['io_collective']
        cm = M[col.master]
        bp = eps[1][1]
        bk = 0
        if bp not in cm.ports:
            # the die-level alias blk_ck<k> of the collective's blk_ck bus (port_join)
            jn = m.get('port_join', {}).get(col.master, {}).get(bp)
            bp, bk = (jn[0], (jn[1][0] if jn[1] else 0)) if jn else ('blk_ck', 0)
        px, py = _face_xy(col, cm, bp, bk)
        w, h = DIV_WH
        x, y = _free_near(insts, px + w / 2 + HALO, py, w, h)
        q = v.Master(DIV[1], w, h, 3, 'QW-GEN5 real /6 clock divider (6 flops) of clk_coll -> coll_blk 5000 ps')
        q.face('ck', 1, 'W', 'M4', h / 2 + 2.16, 1)
        q.face('rst_n', 1, 'W', 'M4', h / 2 - 2.16, 1)
        q.face('ck_o', 1, 'E', 'M4', h / 2, 1)
        M[DIV[1]] = q
        d_ = v.Inst(DIV[0], DIV[1], x, y, w, h, orient='R0', kind=col.kind, region=col.region, domain=col.domain)
        insts.append(d_)
        by[d_.name] = d_
        m['buses'][j] = (b, c, n, [(DIV[0], 'ck_o')] + list(eps[1:]))
        m['buses'][jc] = (bc, cc, nc, list(ec) + [(DIV[0], 'ck')])
        br, cr, nr, er = m['buses'][jr[0]]
        m['buses'][jr[0]] = (br, cr, nr, list(er) + [(DIV[0], 'rst_n')])
        rec['coll_blk_divider'] = dict(inst=DIV[0], master=DIV[1], rtl=DIV[2], xy=[x, y], wh=[w, h], clock='clk_coll',
                                       reset_bus=br, ratio=6, period_ps=5000.0, source_period_ps=2500.0 / 3,
                                       blk_ck_pin_xy=[round(px, 3), round(py, 3)],
                                       rule='B(m)=F(5m)=C(6m): coll_blk = clk_coll / 6 from a flop; phase = fixed count '
                                            'after the collective reset release (2-stage landing)')
    if phy:
        j = _bus(m, 'clk_ucie')
        b, c, n, eps = m['buses'][j]
        if c != 'clock_trunk' or eps[0] != ('clk_rx', 'pll_ucie') or ('io_ucie', 'clk') not in eps:
            raise ValueError(f'g5 clocking: clk_ucie is not the clk_rx.pll_ucie trunk to io_ucie.clk: {eps[:3]}')
        um = M[by['io_ucie'].master]
        if 'lclk' not in um.ports:
            raise ValueError(f'g5 clocking: UCIe PHY view {by["io_ucie"].master} has no lclk FDI clock output pin')
        m['buses'][j] = (b, c, n, [('io_ucie', 'lclk')] + list(eps[1:]))
        rec['ucie_phy_clock'] = dict(source='io_ucie.lclk', master=by['io_ucie'].master, period_ps=1000.0,
                                     sinks=len(eps) - 1, rule='UCIe FDI clock = the PHY clock output (PHY-modeled '
                                                              'boundary); 6:5 relation to stream recorded in the '
                                                              'clock contract (related domains), not modeled here')
    if core:
        if os.environ.get('OT_SPLIT_FWD_BUMP_FEED', '0') != '1':
            raise ValueError('g5 clocking: OT_SPLIT_CORE_FEED_XY needs OT_SPLIT_FWD_BUMP_FEED=1 (pll_fwd keeps the '
                             'bump hop-0 stations as its only sinks)')
        x, y = (float(z) for z in core.split(','))
        if abs(x / LAT - round(x / LAT)) > 1e-6 or abs(y / LAT - round(y / LAT)) > 1e-6:
            raise ValueError(f'g5 clocking: core feed bump ({x}, {y}) off the 43.2 um lattice')
        ref = by['ckb_rom']
        if ref.master != CORE[1]:
            raise ValueError(f'g5 clocking: ckb_rom is {ref.master}, not {CORE[1]}')
        hit = _overlaps(insts, x, y, ref.w, ref.h)
        if hit:
            raise ValueError(f'g5 clocking: core feed bump at ({x}, {y}) overlaps {hit[:6]}')
        j = _bus(m, 'pll_fwd')
        b, c, n, eps = m['buses'][j]
        if c != 'clock_trunk' or eps[0] != ('ckb_rom', 'pll_ck') or eps.count(('clk_rx', 'pll_fwd')) != 1:
            raise ValueError(f'g5 clocking: pll_fwd is not ckb_rom.pll_ck -> clk_rx.pll_fwd: {eps}')
        i = v.Inst(CORE[0], CORE[1], x, y, ref.w, ref.h, orient='R0', kind=ref.kind, region=ref.region,
                   domain=ref.domain)
        insts.append(i)
        by[i.name] = i
        m['buses'][j] = (b, c, n, [e for e in eps if e != ('clk_rx', 'pll_fwd')])
        m['buses'].append(('pll_core', 'clock_trunk', 1, [(CORE[0], 'pll_ck'), ('clk_rx', 'pll_fwd')]))
        rec['core_feed'] = dict(inst=CORE[0], master=CORE[1], xy=[x, y], net='pll_core', link_feed='pll_fwd',
                                link_feed_sinks_before_relays=len(eps) - 2,
                                rule='die-core forwarded clock enters at the die centre; the die clock spine starts '
                                     'at ckb_core/pll_ck (DC_SPINE_SOURCE) and dissolves clk_rx (DC_DISSOLVE_RX)')
    M_ = dict(M)

    def fixed(model, k=1, port_bits=None):
        return dict(M_)
    v.masters = fixed
    print('G5_CLOCKING', ' '.join(f'{k}={v_.get("inst", v_.get("source"))}@{v_.get("xy", "")}'
                                  for k, v_ in rec.items() if isinstance(v_, dict)), flush=True)
    return rec
