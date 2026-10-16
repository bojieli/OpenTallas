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
