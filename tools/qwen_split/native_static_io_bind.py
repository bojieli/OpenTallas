"""Bind the compute-die IO row to the static production collective and its PHYs.

Replaces the historical credit IO graph (qfd_io_collective + qfd_io_xfifo + qfd_io_serdes x3 + qfd_io_ucie:
per-link credits, 1,024-bit codec words) by the production boundary Q-COLL froze on main
(results/arch/qwen_coll_io_1014/shared_ucie_1015/production_boundary.json):

  qfd_collective_static_io_production  -- one 1,043-bit shared UCIe FDI + three 597-bit SerDes FDI frames,
                                          108 clock roots, static calendar, no credit / ready port
  ot_qfd_ucie_x64_phy (tp8_1013 view)  -- the selected UCIe PHY (port map from the ABI)
  ot_qfd_serdes_112g_x12_phy_s597 x3   -- SerDes PHY abstract with a 597-bit static FDI (link_phy_gen --static-serdes)

Row order W -> E follows the profile the calendar was compiled for (RS1 = 0 / RS0 = 0 adjacent, RS2 = 5 and
RU = 5 one PHY away): serdes_2, serdes_1, collective, serdes, ucie.  The W PHYs are MY so their FDI window faces the
collective.  The RU / RS relay registers are INSIDE the collective RTL (relay_ck roots), so the collective <-> PHY FDI
buses carry class 'coll_fdi' (no die relays: a die relay would be an unscheduled stage); their physical homes along
the channel are an explicit open item.

Missing production producers are enumerated, never tied: the collective command port (cmd_*), the die identity
(pkg_s / die_ps: package strap bumps, a die-design constant would be wrong for 7 of 8 dies) and the sequencer's
legacy credit input cd_cr (static successor owned by Q-control).
"""
import hashlib
import math
from pathlib import Path

from qwen_split.source_pin_plan import rtl_ports, snap

ROOT = Path(__file__).resolve().parents[2]
MASTER = 'qfd_collective_static_io_production'
SOURCE = 'rtl/physical/ot_qfd_collective_static_io_production.sv'
ABI = 'results/arch/qwen_coll_io_1014/block_stage_r10_1015/production_boundary.json'
UCIE = 'ot_qfd_ucie_x64_phy'
UCIE_VIEW = 'physical/qwen_missing_phy/tp8_1013/ot_qfd_ucie_x64_phy'
SERDES = 'ot_qfd_serdes_112g_x12_phy_s597'
SERDES_VIEW = 'physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy_s597'
SERDES_WH = (2320.056, 1563.57)
UCIE_WH = (777.6, 777.6)
FW_U, FW_S = 1043, 597
ORDER = ('io_serdes_2', 'io_serdes_1', 'io_collective', 'io_serdes', 'io_ucie')
SERDES_INST = ('io_serdes', 'io_serdes_1', 'io_serdes_2')          # SerDes0..2 = production face index 2..4
GAP = 4.32
CORE_CLOCKS = (['clk'] + [f'clk_pfold{k}' for k in range(4)] + [f'clk_xfold{k}' for k in range(4)] +
               [f'clk_pring{k}' for k in range(2)] + [f'clk_sring{k}' for k in range(5)] +
               [f'clk_rring{k}' for k in range(2)])
OPEN_INPUTS = ('cmd_v', 'cmd_mode', 'cmd_words', 'cmd_tag', 'pkg_s', 'die_ps')


def _aliases(ports):
    """Die-level single-bit / slice names for the vector clock and SerDes ports (port_join: alias -> real bits)."""
    a = {}
    for p in ('face_ck', 'relay_ck', 'fdi_rx_ck', 'blk_ck'):
        if p in ports:
            a.update({f'{p}{k}': (p, [k]) for k in range(ports[p][0])})
    for s in range(3):
        a[f'stx{s}'] = ('serdes_tx', list(range(s * FW_S, (s + 1) * FW_S)))
        a[f'srx{s}'] = ('serdes_rx', list(range(s * FW_S, (s + 1) * FW_S)))
        for p in ('serdes_tx_valid', 'serdes_rx_valid', 'serdes_up'):
            a[f'{p}{s}'] = (p, [s])
    return a


def core_clock_pins(ports):
    return (CORE_CLOCKS + [f'face_ck{k}' for k in range(ports['face_ck'][0])] +
            [f'relay_ck{k}' for k in range(ports['relay_ck'][0])] + ['gearbox_core_ck'])


def fdi_clock_pins(ports):
    return ['fdi_ck'] + [f'fdi_rx_ck{k}' for k in range(ports['fdi_rx_ck'][0])]


def apply(model):
    by = {i.name: i for i in model['insts']}
    need = ORDER + ('io_xfifo',)
    if any(n not in by for n in need):
        raise ValueError(f'static IO bind requires the historical IO row {need}')
    if by['io_collective'].master != 'qfd_io_collective':
        raise ValueError('static IO bind expects the explicit historical collective master')
    ports = rtl_ports(ROOT / SOURCE, MASTER)
    old = {n: (by[n].x, by[n].y, by[n].w, by[n].h, by[n].master) for n in need}
    coll, xf = by['io_collective'], by['io_xfifo']
    # the collective takes the historical collective + xfifo envelope (the xfifo's function is inside it)
    coll.master, coll.w = MASTER, round(xf.x + xf.w - coll.x, 4)
    model['insts'] = [i for i in model['insts'] if i.name != 'io_xfifo']
    by.pop('io_xfifo')
    for n in SERDES_INST:
        by[n].master, (by[n].w, by[n].h) = SERDES, SERDES_WH
    by['io_ucie'].master, (by['io_ucie'].w, by['io_ucie'].h) = UCIE, UCIE_WH
    y0 = min(old[n][1] for n in ORDER)
    x = min(old[n][0] for n in ORDER)
    for n in ORDER:
        i = by[n]
        i.x, i.y = round(x, 4), y0
        i.orient = 'MY' if n in ('io_serdes_1', 'io_serdes_2') else 'R0'
        x = math.ceil(round((x + i.w + GAP) / .216, 8)) * .216
    row = [by[n] for n in ORDER]
    lo_x, hi_x = row[0].x, row[-1].x + row[-1].w
    # nothing else may sit in the compacted row
    for i in model['insts']:
        if i.name in ORDER:
            continue
        if i.x < hi_x and lo_x < i.x + i.w and i.y < y0 + max(r.h for r in row) and y0 < i.y + i.h:
            raise ValueError(f'static IO row overlaps {i.name}')
    io_old = set(need)
    removed, kept = [], []
    rst_bus = None
    for b, c, n, es in model['buses']:
        if c == 'reset' and any(i in io_old for i, _ in es):
            rst_bus = b
            kept.append((b, c, n, [e for e in es if e[0] not in io_old]))
            continue
        if any(i in io_old for i, _ in es):
            removed.append(b)
            if c == 'clock_trunk':
                es = [e for e in es if e[0] not in io_old]
                if len(es) > 1:
                    kept.append((b, c, n, es))
            continue
        kept.append((b, c, n, es))
    if rst_bus is None:
        raise ValueError('static IO bind: no IO reset bus to extend')
    kept = [(b, c, n, es + ([(x_, 'rst_n') for x_ in ORDER]) if b == rst_bus else es) for b, c, n, es in kept]
    seq = 'seq_su'
    new = [('coll_cd', 'sequencer', 547, [(seq, 'cd_d'), ('io_collective', 'cd')]),
           ('coll_cc', 'sequencer', 518, [('io_collective', 'cc'), (seq, 'cc')]),
           ('ucie_tx', 'coll_fdi', FW_U, [('io_collective', 'shared_tx'), ('io_ucie', 'tx_flit')]),
           ('ucie_txv', 'coll_fdi', 1, [('io_collective', 'shared_tx_valid'), ('io_ucie', 'tx_v')]),
           ('ucie_rx', 'coll_fdi', FW_U, [('io_ucie', 'rx_flit'), ('io_collective', 'shared_rx')]),
           ('ucie_rxv', 'coll_fdi', 1, [('io_ucie', 'rx_v'), ('io_collective', 'shared_rx_valid')]),
           ('ucie_up', 'coll_fdi', 1, [('io_ucie', 'tx_up'), ('io_collective', 'ucie_up')])]
    for s, n in enumerate(SERDES_INST):
        new += [(f'serdes{s}_tx', 'coll_fdi', FW_S, [('io_collective', f'stx{s}'), (n, 'tx_flit')]),
                (f'serdes{s}_txv', 'coll_fdi', 1, [('io_collective', f'serdes_tx_valid{s}'), (n, 'tx_v')]),
                (f'serdes{s}_rx', 'coll_fdi', FW_S, [(n, 'rx_flit'), ('io_collective', f'srx{s}')]),
                (f'serdes{s}_rxv', 'coll_fdi', 1, [(n, 'rx_v'), ('io_collective', f'serdes_rx_valid{s}')]),
                (f'serdes{s}_up', 'coll_fdi', 1, [(n, 'tx_up'), ('io_collective', f'serdes_up{s}')])]
    # clocks: the 1.2 GHz core roots on one trunk (domain 'stream'), the 1 GHz FDI roots + every PHY on the FDI
    # trunk (die_sta_libs domain 'ucie'); the 6:5 relation is inside the collective (root rational-clock contract)
    new += [('clk_coll', 'clock_trunk', 1, [('clk_rx', 'pll_coll')] + [('io_collective', p) for p in core_clock_pins(ports)]),
            ('clk_ucie', 'clock_trunk', 1, [('clk_rx', 'pll_ucie')] + [('io_collective', p) for p in fdi_clock_pins(ports)] +
             [(n, 'clk') for n in ('io_ucie',) + SERDES_INST])]
    if 'blk_ck' in ports:
        # These are actual 200 MHz clock inputs, not 1.2 GHz roots with a
        # pessimistic timing annotation. Their common-PLL implementation and
        # physical phase delivery remain explicit integration obligations.
        new.append(('clk_coll_blk', 'clock_trunk', 1, [('clk_rx', 'pll_coll_blk')] +
                    [('io_collective', f'blk_ck{k}') for k in range(ports['blk_ck'][0])]))
    model['buses'] = [q for q in kept if q[0] not in ('clk_ucie', 'clk_coll')] + new
    split = model.setdefault('port_split', {})
    split[MASTER] = dict(cd=[('in_data', 512), ('in_last', 1), ('in_mode', 1), ('in_tag', 32), ('in_valid', 1)],
                         cc=[('out_data', 512), ('out_last', 1), ('out_rank', 3), ('out_err', 1), ('out_valid', 1)])
    model.setdefault('port_join', {})[MASTER] = _aliases(ports)
    model.setdefault('relay_skip_classes', set()).add('coll_fdi')
    connected = set()
    for p in [p for b, c, n, es in new for i, p in es if i == 'io_collective']:
        if p in split[MASTER]:
            connected |= {s for s, _ in split[MASTER][p]}
        elif p in model['port_join'][MASTER]:
            connected.add(model['port_join'][MASTER][p][0])
        else:
            connected.add(p)
    connected.add('rst_n')
    unknown = sorted(connected - set(ports))
    if unknown:
        raise ValueError(f'static IO bind has non-source endpoints: {unknown}')
    missing = sorted(p for p, (n, d) in ports.items() if d == 'input' and p not in connected)
    if set(missing) != set(OPEN_INPUTS):
        raise ValueError(f'static IO bind: unexpected open inputs {missing}')
    rec = dict(master=MASTER, source=SOURCE, abi=ABI,
               source_sha256=hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
               abi_sha256=hashlib.sha256((ROOT / ABI).read_bytes()).hexdigest(),
               retired=dict(masters=['qfd_io_collective', 'qfd_io_xfifo', 'qfd_io_serdes', 'qfd_io_ucie'],
                            instances=['io_xfifo'], buses=removed,
                            reason='credit / ready IO graph (VOID under the static-schedule owner rule)'),
               phys=dict(ucie=dict(master=UCIE, view=UCIE_VIEW), serdes=dict(master=SERDES, view=SERDES_VIEW,
                         note='597-bit static FDI abstract: licensed PHY FDI configuration ASSUMED, Q-COLL to confirm')),
               row=[dict(n=i.name, m=i.master, x=i.x, y=i.y, w=i.w, h=i.h, o=i.orient) for i in row],
               row_span_um=[round(lo_x, 4), round(hi_x, 4)],
               historical_row={n: dict(zip(('x', 'y', 'w', 'h', 'm'), q)) for n, q in old.items()},
               clock_roots=dict(core=len(core_clock_pins(ports)), fdi=len(fdi_clock_pins(ports)),
                                total=len(core_clock_pins(ports)) + len(fdi_clock_pins(ports))),
               open_inputs=dict(cmd_v_mode_words_tag='collective command producer absent from the compute graph '
                                '(static controller ABI has no 50-bit command output): Q-control / Q-COLL',
                                pkg_s_die_ps='die identity needs package strap bumps (a constant is wrong for 7 of 8 dies)',
                                seq_su_cd_cr='qfd_seq_su still has the legacy credit input: static successor (Q-control)'),
               relay_homes='OPEN: RU=5 (UCIe) and RS2=5 (SerDes2) relay registers are inside the collective RTL '
                           '(30 relay_ck roots); their placed homes along the FDI channels are not modelled; the die '
                           'adds no relay on class coll_fdi',
               unread_outputs=sorted(p for p, (n, d) in ports.items() if d == 'output' and p not in connected),
               qualified=False)
    model['native_static_io_bind'] = rec
    return rec


def install_master(M, model, Master):
    """Assigned (top-down) pins of the new unclosed collective parent from its real RTL port list."""
    if 'native_static_io_bind' not in model:
        return
    inst = next(i for i in model['insts'] if i.name == 'io_collective')
    ports = rtl_ports(ROOT / SOURCE, MASTER)
    q = Master(MASTER, inst.w, inst.h, 7, 'Static production collective (Q-COLL ABI); NEW assigned unclosed parent')
    join = model['port_join'][MASTER]
    # FDI windows level with the PHY W-face pin block (y 600 + k * 0.048 from the PHY origin, same die y)
    win = 600.0
    # same order and pitch as the PHY's own FDI pins (clk, rst_n, tx_up, tx_v, tx_flit, rx_v, rx_flit): the
    # SerDes0 / SerDes1 words are straight M4 tracks across the 4.32-um gap; clk / rst_n slots stay empty here
    def phy_order(s):
        return [('serdes_up', [s]), ('serdes_tx_valid', [s]), ('serdes_tx', range(s * FW_S, (s + 1) * FW_S)),
                ('serdes_rx_valid', [s]), ('serdes_rx', range(s * FW_S, (s + 1) * FW_S))]
    EU = [('ucie_up', [0]), ('shared_tx_valid', [0]), ('shared_tx', range(FW_U)), ('shared_rx_valid', [0]),
          ('shared_rx', range(FW_U))]
    pos = {}                                             # (port, bit) -> (face, layer, centre)

    def column(face, items, y):
        y += 2 * .048                                    # the PHY's clk / rst_n slots
        for p, bits in items:
            for b in bits:
                pos[(p, b)] = (face, 'M4', round(.012 + round((y - .012) / .048) * .048, 4))
                y += .048
        return y
    end = column('E', phy_order(0), win)                 # SerDes0, abutting the E PHY window
    column('E', EU, max(end, win + 60.0) + 8.0)           # UCIe, over SerDes0 (M6+) to the PHY beyond it
    end = column('W', phy_order(1), win)                 # SerDes1 (MY PHY, window faces E)
    column('W', phy_order(2), end + 8.0)                 # SerDes2, over SerDes1
    placed = {p for p, _ in pos}
    north = [p for p in ports if p not in placed]
    x = (q.w - sum(ports[p][0] * .096 + 2.0 for p in north)) / 2
    if x < 4.0:
        raise ValueError(f'{MASTER}: N-face pins exceed the outline')
    for p in north:
        for b in range(ports[p][0]):
            pos[(p, b)] = ('N', 'M5', snap(x))
            x += .096
        x += 2.0
    for f in 'NEW':
        zs = [z for (p, b), (ff, _, z) in pos.items() if ff == f]
        if len(zs) != len(set(zs)):
            raise ValueError(f'{MASTER}: overlapping assigned pins on face {f}')
        lim = q.w if f == 'N' else q.h
        if min(zs) < 1.0 or max(zs) > lim - 1.0:
            raise ValueError(f'{MASTER}: pin outside face {f}')
    from qwen_split.direct_up4 import partition_master
    rects = []
    for p, (n, d) in ports.items():
        for k in range(n):
            f, L, z = pos[(p, k)]
            r = {'W': (0, z - .012, .192, z + .012), 'E': (q.w - .192, z - .012, q.w, z + .012),
                 'N': (z - .012, q.h - .192, z + .012, q.h)}[f]
            rects.append((p if n == 1 else f'{p}[{k}]', L, r))
        faces = {pos[(p, k)][0] for k in range(n)}
        if len(faces) == 1:
            f, L, _ = pos[(p, 0)]
            q.ports[p] = ('pins', n, f, L, [pos[(p, k)][2] for k in range(n)], 1)
            q.order.append(p)
        elif p not in {real for real, _ in join.values()}:
            raise ValueError(f'{MASTER}.{p}: spans faces without a die-level slice alias')
        else:
            q.ports[p] = ('pins', n, None, None, [], 1)     # replaced by its aliases (partition_master)
            q.order.append(p)
    partition_master(q, join, rects)
    model['native_static_io_bind']['assigned_ports'] = {
        p: dict(bits=sp[1], face=sp[2] if sp[0] == 'pins' else None, layer=sp[2] if sp[0] == 'xy' else sp[3])
        for p, sp in q.ports.items()}
    for old in ('qfd_io_collective', 'qfd_io_xfifo', 'qfd_io_serdes', 'qfd_io_ucie'):
        M.pop(old, None)
    M[MASTER] = q
    for name, view in ((UCIE, UCIE_VIEW), (SERDES, SERDES_VIEW)):
        M[name] = phy_master(Master, name, view)


def phy_master(Master, name, view):
    """The PHY hard macro's own LEF pins (a 'pins' port per base name, bit order from the LEF)."""
    import re
    t = (ROOT / view / f'{name}.lef').read_text()
    w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t).groups())
    q = Master(name, w, h, 5, f'licensed PHY abstract ({view})')
    bits = {}
    for m in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1\s*$', t, re.M | re.S):
        if m.group(1) in ('VDD', 'VSS'):
            continue
        r = re.search(r'LAYER (\S+) ;\s*\n\s*RECT ([-\d. ]+) ;', m.group(2))
        x0, y0, x1, y1 = map(float, r.group(2).split()[:4])
        if x0 <= 1e-6:
            f, z = 'W', (y0 + y1) / 2
        elif x1 >= w - 1e-6:
            f, z = 'E', (y0 + y1) / 2
        elif y0 <= 1e-6:
            f, z = 'S', (x0 + x1) / 2
        elif y1 >= h - 1e-6:
            f, z = 'N', (x0 + x1) / 2
        else:
            raise ValueError(f'{name}.{m.group(1)}: PHY pin not on a face')
        base, _, idx = m.group(1).partition('[')
        bits.setdefault(base, {})[int(idx[:-1]) if idx else 0] = (r.group(1), round(z, 4), f)
    for base, d in bits.items():
        if set(d) != set(range(len(d))) or len({v_[2] for v_ in d.values()}) != 1:
            raise ValueError(f'{name}.{base}: incomplete or multi-face bus in LEF')
        q.ports[base] = ('pins', len(d), d[0][2], d[0][0], [d[k][1] for k in range(len(d))], 1)
        q.order.append(base)
    return q
