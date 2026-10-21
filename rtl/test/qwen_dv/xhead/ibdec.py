#!/usr/bin/env python3
"""decode the tt_ctlm hr ROM word {go, ib 379} (ib packing of ot_qwen_me_array_w12: {i_nout, i_tiles, i_k, i_wsrc,
i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode,
i_oen, i_amax, i_rmax, i_mbase}, NW 18, AW 24) and the XPF arm {round, k, split, xks, xcs, xbase, v}."""
NW, AW = 18, 24
FIELDS = [('nout', NW), ('tiles', NW), ('k', NW), ('wsrc', 1), ('wbase', AW), ('ts', AW), ('ks', AW), ('js', AW),
          ('xbase', AW), ('xks', AW), ('xjs', AW), ('xcs', AW), ('jsh', 3), ('split', 4), ('wcs', AW), ('round', 1),
          ('obase', AW), ('ots', AW), ('ojs', AW), ('mmode', 1), ('oen', 1), ('amax', 1), ('rmax', 1), ('mbase', AW)]
IBW = sum(w for _, w in FIELDS)
assert IBW == 379


def dec_ib(ib):
    out, pos = {}, IBW
    for n, w in FIELDS:
        pos -= w
        out[n] = (ib >> pos) & ((1 << w) - 1)
    return out


def enc_ib(f):
    v = 0
    for n, w in FIELDS:
        v = (v << w) | (f[n] & ((1 << w) - 1))
    return v


def dec_rom(hexword):
    """hr[452:73] = {go, ib}"""
    v = int(hexword, 16)
    return v >> IBW, dec_ib(v & ((1 << IBW) - 1))


def dec_xpf(hexword):
    """hr[72:1] = {round 1, k 18, split 4, xks 12, xcs 12, xbase 24, v 1}"""
    v = int(hexword, 16)
    return dict(v=v & 1, xbase=(v >> 1) & 0xFFFFFF, xcs=(v >> 25) & 0xFFF, xks=(v >> 37) & 0xFFF, split=(v >> 49) & 15,
                k=(v >> 53) & 0x3FFFF, round=(v >> 71) & 1)


if __name__ == '__main__':
    import sys
    for line in open(sys.argv[1]):
        p = line.split()
        if len(p) == 3 and p[1] == 'ROM':
            go, f = dec_rom(p[2]); print(p[0], 'ROM go', go, f)
        elif len(p) == 3 and p[1] == 'XPF':
            print(p[0], 'XPF', dec_xpf(p[2]))
