def _fwd_clock_manifest_finalize(m):
    """Derive clock metadata from final construction; reject missing/conflicting pins."""
    net = {}
    for bid, cl, bits, eps in m['buses']:
        if cl != 'clock_trunk':
            continue
        for endpoint in eps:
            endpoint = tuple(endpoint)
            if endpoint in net and net[endpoint] != bid:
                raise ValueError(f'conflicting clock drivers: {endpoint}')
            net[endpoint] = bid
    def require(instance, pin):
        if (instance, pin) not in net:
            raise ValueError(f'missing clock: {instance}.{pin}')
        return net[instance, pin]
    for ln in (m.get('fwd_lanes') or {}).get('lanes', []):
        stations = ln.get('stations') or []
        landing = ln.get('landing')
        # The constructor makes non-reset n=1 into landh0 (source ck_s,
        # destination ck); reset single-frame rlyrl uses ck for both.
        first = not stations and ln.get('lane') != 'reset'
        h0 = stations[0] if stations else landing
        ln['src_ck'] = require(h0, 'ck_s' if first else 'ck')
        ln['dst_ck'] = require(landing, 'ck')


