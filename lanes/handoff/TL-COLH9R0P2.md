# TL-COLH9R0P2 (2026-11-14 04:5x PST) s81 col_h9_r0_p2__t1
CAUSE (shared, all pv): generator emits .LOCAL(1) on plain rings >64b; wave src B3v/src rtl/common/ot_dp_clk_landing.sv has no LOCAL param -> GEN_LINT rtl_check defparam error. Base (non-pv) items: plain name no longer a plan type (bind: no partition type) -> only pv variants valid.
FIX/FORMS: overlay src epyc10 /srv/opentallas-scratch2/claude/tl-colh9r0p2/src (B3v hardlink tree + main ot_dp_clk_landing.sv). Specs intel2 ~/type-s81-colh9r0p2/{fa: cl0045af7b__pve183b536, fb: cl9f71e63d__pvef55eb84}; run: python3 /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot/kit_wave.py run-item <spec> (no -I). Work epyc10 .../tl-colh9r0p2/{fa,fb}.
NEXT: on pass add AUTO-RESIGN row + RESULT; wave needs the file in wave src (KIT-OPS-3).

2026-11-14 19:30 successor: waiting for p1 A/B verdict (ab_a not running, see queue STATE); fallback own A/B on ff 4_cts.odb at ~21:30 PST. p2 route containers on epyc10 alive: -3792347 -561963 -1710695.
