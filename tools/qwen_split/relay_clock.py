"""Use explicit source-bound relay clocks; never infer a new frequency."""


def assigned_clock(model, bid, cls):
    mapping = model.get('relay_clock_by_bus', {})
    if bid not in mapping:
        return None
    clock = mapping[bid]
    # The native binder owns the exact FDI bus identities and existing root.
    # Refuse stale metadata, absent clocks, duplicate roots or data-net aliases.
    buses = [b for b in model['buses'] if b[0] == clock]
    if cls != 'coll_fdi' or clock != 'clk_ucie' or len(buses) != 1:
        raise ValueError(f'relay clock {bid}: invalid explicit FDI clock {clock}')
    _, kind, bits, eps = buses[0]
    if kind != 'clock_trunk' or bits != 1 or ('clk_rx', 'pll_ucie') not in eps:
        raise ValueError(f'relay clock {bid}: missing actual FDI receiver root')
    if not any(i == 'io_collective' and p.startswith(('fdi_ck', 'fdi_rx_ck')) for i, p in eps):
        raise ValueError(f'relay clock {bid}: missing actual collective FDI clock sink')
    return clock


# Q-DIEPLAN2r 2026-10-16 (r2h5 strict bind rc3: 55 qfd_rly_1 omit .ck): on the split compute die the collective is
# the native qfd_collective_static_io_production, whose core logic runs on clk_coll (clk_rx.pll_coll, the 1.2 GHz
# 'stream' domain of clock_contract.json; the die has NO serial 0.9 GHz clock).  Its legacy inst domain
# 'serial_0p9' named a clk_serial trunk that never exists here, so relays of its non-FDI buses (fault /
# shared_fault outputs, pkg_s / die_ps strap inputs) were left unclocked.  The actual source clock of those
# relays is the collective core trunk; it is returned only when that trunk exists with its real root and core
# sink, and the bus really ends on a non-FDI collective port.  Anything else fails closed.
COLLECTIVE = 'io_collective'


def collective_core_clock(model, bid, cls, eps):
    ports = [p for i, p in eps if i == COLLECTIVE]
    if not ports:
        raise ValueError(f'relay clock {bid}: serial_0p9 relay on the split compute die has no serial clock '
                         f'and no collective endpoint ({eps})')
    if cls == 'coll_fdi' or any(p.startswith(('fdi_', 'shared_tx', 'shared_rx', 'stx', 'srx', 'serdes_'))
                                 for p in ports):
        raise ValueError(f'relay clock {bid}: FDI-side collective port {ports} needs the explicit FDI clock')
    buses = [b for b in model['buses'] if b[0] == 'clk_coll']
    if len(buses) != 1:
        raise ValueError(f'relay clock {bid}: collective core trunk clk_coll absent or duplicated')
    _, kind, bits, ceps = buses[0]
    if kind != 'clock_trunk' or bits != 1 or ('clk_rx', 'pll_coll') not in ceps:
        raise ValueError(f'relay clock {bid}: clk_coll lacks its actual clk_rx.pll_coll root')
    if (COLLECTIVE, 'clk') not in ceps:
        raise ValueError(f'relay clock {bid}: clk_coll lacks the collective core clock sink')
    return 'clk_coll'
