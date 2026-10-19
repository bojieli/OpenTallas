#!/usr/bin/env python3
"""TOK-S81-GAPS/GU (10-18): the compiler's static leaf-store row map (ot_s81sl leaf store: 1,024 rows of 256 b per leaf,
the same map on every leaf of every slice).  Every family that writes or reads fixed leaf rows takes its base from here,
and check() proves the regions disjoint, so no row address is a per-family placeholder.

Region   rows          writer -> reader                                         source
H        0..31         vpx a_allgather RD rows / vp HLOAD a0 (norm input h)    dv_layer_compile lower_norm_smoke r_h, lower_vpx
VPX      0..447        vpx row allgather (80 rows / rank, 320 + 32 / rank)      lower_vpx.py rows_of_rank (shares H by design:
                                                                                  the allgathered rows ARE the norm input)
GAIN     64..79        host / frame gain rows -> vp GAIN                         lower_norm_smoke r_gain (inside VPX: same rows)
VS       512..663      vs operand / result rows (QR, QB, RA, RB, SW)             lower_vs.py VS_ROWS (SW_OUT 632 + 32)
ENG      704..991      Engram K / V / W rows (L1 704.., L14 848.., 144 each)     eng_rowmap.py A0 / REGION_ROWS
GU_ATTN  1000..1005    gunit L5 HC rows -> vp NORMR a0 = R (pre), POST a0 = R+1  lower_gu (dsdv_gunit_l5.sv:79-101; vp op 7)
GU_FFN   1008..1013    same for the ffn HC                                       lower_gu
GU_RT    1016..1018    gunit L1/L3 router rows: ids R, weights R+1 (m f), R+2    lower_gu (dsdv_gunit_l1.sv:150-163) -> vs SW
"""
LEAF_ROWS = 1024
REGIONS = dict(VPX=(0, 448), VS=(512, 664), ENG=(704, 992), GU_ATTN=(1000, 1006), GU_FFN=(1008, 1014), GU_RT=(1016, 1019))
SHARED = dict(H=('VPX', (0, 32)), GAIN=('VPX', (64, 80)))       # sub-ranges of a region by design (same data)
GU_ROWS = dict(attn=REGIONS['GU_ATTN'][0], ffn=REGIONS['GU_FFN'][0], router=REGIONS['GU_RT'][0])


def check():
    rs = sorted(REGIONS.items(), key=lambda kv: kv[1])
    for (a, (a0, a1)), (b, (b0, b1)) in zip(rs, rs[1:]):
        assert a1 <= b0, f'leaf rows: {a} {a0}..{a1 - 1} overlaps {b} {b0}..{b1 - 1}'
    assert rs[-1][1][1] <= LEAF_ROWS
    for n, (reg, (s0, s1)) in SHARED.items():
        r0, r1 = REGIONS[reg]
        assert r0 <= s0 and s1 <= r1, f'{n} outside {reg}'
    # the gunit HC tail writes 6 rows (pre, post, comb 0..3), the router 3 (ids, w 0..3, w 4..5)
    assert REGIONS['GU_ATTN'][1] - REGIONS['GU_ATTN'][0] == 6 and REGIONS['GU_FFN'][1] - REGIONS['GU_FFN'][0] == 6
    assert REGIONS['GU_RT'][1] - REGIONS['GU_RT'][0] == 3
    assert all(v % 2 == 0 for v in GU_ROWS.values()), 'row-pair aligned bases'
    return True


check()
