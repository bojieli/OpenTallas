"""HBM-CORES-REBAL-9: the SU lane build constants the compilers schedule against, in ONE place.

Depths are the localparams of rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane.sv (lane, built
at MLAT / ALAT) and ot_hbm_su_static_side.sv (side pipe, localparam MLAT 3 / ALAT 3).  A lane build is the die's
su_<q><g> / pg_lane* top parameters (build_split_tops.py --pg-params).  AS_BUILT = the d4g / r18h5 build (MLAT 4,
ALAT 3, LEAF 1, WCOPY 0): every compiler default stays byte-identical to it.  MLAT 5 = ot_hdc_fp32_mul_lat5i on every
lane multiplier (bit-identical, one more stage per multiplying stage); WCOPY 1 = the pinned bank's per-column
registered write copy (ot_hbm_su_static_pinned_bank WCOPY): every bank write (fill / delivery / lane) commits one edge
later; the write-port pins (collision rules) are unchanged.
"""

AS_BUILT = dict(mlat=4, alat=3, leaf=1, wcopy=0)
SIDE = dict(mlat=3, alat=3)                     # ot_hbm_su_static_side localparam MLAT=3, ALAT=3
SFU_EXP, SFU_RSQRT, SFU_SQRT, SFU_SIGM, SFU_SILU, SFU_SPSQRT, SFU_EGATE = 1, 2, 3, 4, 5, 6, 7
SIDE_FN = (SFU_RSQRT, SFU_SQRT, SFU_SPSQRT, SFU_EGATE)


def check(mlat, alat, leaf=1, wcopy=0):
    if mlat not in (3, 4, 5, 6, 7) or alat not in (3, 4) or alat > mlat or leaf not in (0, 1) or wcopy not in (0, 1):
        raise ValueError(f"lane build MLAT {mlat} ALAT {alat} LEAF {leaf} WCOPY {wcopy} is not an RTL build")


def depths(mlat, alat):
    """ci_sfu -> lane insertion depth H_* (ot_hbm_su_static_lane.sv D_*)."""
    check(mlat, alat)
    d_div = 19
    d_exp = 7 * mlat + 8 * alat + 4
    d_sig = d_exp + alat + d_div
    d_rsq = 1 + 9 * mlat + 3 * alat
    d_sp = d_exp + 11 * mlat + 10 * alat + 50
    d_eg = 1 + 31 + 1 + d_sig
    return {0: 0, SFU_EXP: d_exp, SFU_RSQRT: d_rsq, SFU_SQRT: 31, SFU_SIGM: d_sig, SFU_SILU: d_sig,
            SFU_SPSQRT: d_sp, SFU_EGATE: d_eg}


def lin(mlat, alat, leaf):
    """emit -> lane write (= su_top_compile FO - 8 at PIN_REG 0)."""
    check(mlat, alat, leaf)
    return 23 + 4 * (mlat - 3) + (alat - 3) + leaf


def div_extra(mlat):
    """cp_m1 divide modes (4, 5): the 19-deep divider replaces the MLAT-deep M1 multiply."""
    return 19 - mlat


def side_ii(fn, mlat, alat):
    """side-pipe element spacing: the side result register holds until the lane takes it at its own depth
    (lane depth - side depth + 1); 1 for non-side functions."""
    if fn not in SIDE_FN:
        return 1
    return depths(mlat, alat)[fn] - depths(SIDE["mlat"], SIDE["alat"])[fn] + 1


def commit_extra(wcopy):
    """bank write commit delay over the as-built n+2 (fill and lane writes alike)."""
    check(4, 3, 1, wcopy)
    return wcopy
