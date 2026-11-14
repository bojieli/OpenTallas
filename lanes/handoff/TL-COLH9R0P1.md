# TL-COLH9R0P1 (s81 col_h9_r0_p1__t1 + 6 pv) 11-14
- Base col_h9_r0_p1__t1 is dead (not a partition type in plan_h2_2249; split into pv697f40c9, 8c197f8e, a2e3974f, b3e2a60a, b49c16c8, f9acce4c; no cl* in B1/B3v plan). Old "no partition type" failure = that.
- pv "RTL lint at gen" = class cause (see TL-COLH9R0P5/TL-LEAFT14): wave src B3v lacks LOCAL param in rtl/common/ot_dp_clk_landing.sv while bind emits .LOCAL(1). Applies to all col_h9_r0_p2..p6. Fix on epyc9 B3v/src by TL-LEAFT14; wave retry via KIT-OPS-3.
- Private forms: B1 src_pgL (has LOCAL), epyc9, spec template = TYPE-COLH9P5 fa_ee6f8140. Specs intel2 ~/type-s81-colh9p1/fa_<pv>, work epyc9 /srv/opentallas-scratch2/claude/tl-colh9r0p1/fa_<pv>, launched 04:50 via ~/mk_colh9p1.py (form arg, gen_env json).
- Next: follow to GRT/route; on overflow launch fb (OT_CONS_KIT=1 UTIL -0.1). On pass: AUTO-RESIGN row + RESULT.
- 08:1x routes on epyc2 (gen dirs copied from epyc9, ~/route_p1.sh): fa_697f40c9 (identity A, rep of 5 pv) and fa_f9acce4c (identity B). Others cancelled as duplicates of A. On pass: AUTO-RESIGN row for rep + RESULT credit for the 4 pv.
