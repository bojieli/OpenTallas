"""Complete actual-bit producer coverage before applying band TT constants."""

WIDTH = 1538


def connected_bands(model, bands):
    by = {i.name: i.master for i in model['insts']}
    claims = {name: {} for name in bands}
    for bid, _, width, eps in model['buses']:
        for position, (inst, port) in enumerate(eps):
            if inst not in claims:
                continue
            alias = model.get('port_join', {}).get(by[inst], {}).get(port)
            if port == 'tt':
                indexes = list(range(width))
            elif alias and alias[0] == 'tt':
                indexes = alias[1]
            else:
                continue
            if position == 0:
                raise ValueError(f'{inst}.tt: input incorrectly drives {bid}')
            if len(indexes) != width or any(type(i) is not int or not 0 <= i < WIDTH for i in indexes):
                raise ValueError(f'{inst}.tt: invalid alias width/bounds on {bid}/{port}')
            for bit in indexes:
                if bit in claims[inst]:
                    raise ValueError(f'{inst}.tt[{bit}]: duplicate/conflicting producers {claims[inst][bit]} and {bid}')
                claims[inst][bit] = bid
    connected = set()
    for name, bits in claims.items():
        if bits and set(bits) != set(range(WIDTH)):
            raise ValueError(f'{name}.tt: partial producer coverage {len(bits)}/{WIDTH}')
        if name == 'sp_band_lanes_0' and not bits:
            raise ValueError(f'{name}.tt: missing actual upper-tree producer')
        if bits:
            connected.add(name)
    for inst, port, _, _ in model.get('ties', []):
        if inst in connected and port == 'tt':
            raise ValueError(f'{inst}.tt: actual producer conflicts with literal tie')
    return connected
