# Exact frozen allocator repair prefix, source SHA256 221a3e092f30590e5facebca44c71676d8a366f3e029df10454ed020ab85e4f4
def repair(idx, pl, gaps=False):
    hs = hops_of(pl)
    bits = pl['bits']
    (w, h) = relay_frame(bits, pl['cl'])
    (W, H) = (w + v.SHAVE, h + v.SHAVE)
    (arr, tree) = sites(W, H, gaps or pl['bid'] in tight_stride or (GATE and pl['cl'] == 'head_chain'))
    if tree is None:
        unrep[pl['bid']] = 'no sites'
        return False
    own = [(f[0], f[1], f[0] + f[2] + v.SHAVE, f[1] + f[3] + v.SHAVE) for f in pl['frames']]
    for r_ in own:
        rm_rect(r_)
    return None
