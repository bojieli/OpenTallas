"""Use explicit source-bound relay clocks; never infer a new frequency."""
import re

SERDES_INST = ('io_serdes', 'io_serdes_1', 'io_serdes_2')


def _serdes_clock(model, bid, clock, bus):
    """Q-DIE11-COLL 10-18: a SerDes s FDI bus relay runs on that PHY's own FDI clock clk_serdes<s>
    (native_static_io_bind OT_SPLIT_COLL_PHY_CLOCKS).  Fail closed unless the bus is SerDes s's own bus, the trunk has
    its real clk_rx.pll_serdes<s> root, drives SerDes PHY s's clk pin and at least one collective face_ck root, and
    the bus really ends on that PHY."""
    s = int(clock[-1])
    _, kind, bits, eps = bus
    if not bid.startswith(f'serdes{s}_'):
        raise ValueError(f'relay clock {bid}: {clock} belongs to SerDes {s} buses only')
    if kind != 'clock_trunk' or bits != 1 or ('clk_rx', f'pll_serdes{s}') not in eps:
        raise ValueError(f'relay clock {bid}: {clock} lacks its actual clk_rx.pll_serdes{s} root')
    if (SERDES_INST[s], 'clk') not in eps:
        raise ValueError(f'relay clock {bid}: {clock} does not clock SerDes PHY {SERDES_INST[s]}')
    if not any(i == 'io_collective' and p.startswith('face_ck') for i, p in eps):
        raise ValueError(f'relay clock {bid}: {clock} reaches no collective face root')
    data = [b for b in model['buses'] if b[0] == bid]
    if len(data) != 1 or not any(i == SERDES_INST[s] for i, _ in data[0][3]):
        raise ValueError(f'relay clock {bid}: bus does not end on SerDes PHY {SERDES_INST[s]}')
    return clock


def assigned_clock(model, bid, cls):
    mapping = model.get('relay_clock_by_bus', {})
    if bid not in mapping:
        return None
    clock = mapping[bid]
    # The native binder owns the exact FDI bus identities and existing root.
    # Refuse stale metadata, absent clocks, duplicate roots or data-net aliases.
    buses = [b for b in model['buses'] if b[0] == clock]
    if cls == 'coll_fdi' and len(buses) == 1 and re.fullmatch(r'clk_serdes[0-2]', clock):
        return _serdes_clock(model, bid, clock, buses[0])
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
