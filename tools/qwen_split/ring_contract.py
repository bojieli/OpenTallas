"""Implemented power-of-two landing storage/epoch contract (not a STA D bound)."""


def contract(depth=4):
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 2 or depth & (depth - 1):
        raise ValueError(f'landing ring: implemented depth must be power-of-two >=2, got {depth!r}')
    address_bits = (depth - 1).bit_length()
    return dict(D=depth, address_bits=address_bits, K_bits=address_bits+1, epoch_modulus=2*depth)


def native_depth(required, allowed=(4,8)):
    """Choose an actual allowed capacity; callers must retain the original bound separately."""
    if not isinstance(required,int) or required < 2:
        raise ValueError('landing ring: invalid required capacity')
    choices=sorted(contract(x)['D'] for x in allowed)
    for depth in choices:
        if depth >= required:
            return depth
    raise ValueError(f'landing ring: required capacity {required} exceeds native choices {choices}')


def strap(E, G, R0, depth=4):
    return (int(E)+int(G)-int(R0)) % contract(depth)['epoch_modulus']
