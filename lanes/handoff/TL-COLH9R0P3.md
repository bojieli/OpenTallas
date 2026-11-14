# TL-COLH9R0P3 (s81 col_h9_r0_p3__t1, cl0cd90c0e/cl8ce97bcb/cl31d0dc4b + pv*) 2026-11-14 04:50
- pv/cl lint cause: B3v/src (main 7073a6b4a5) lacks ot_dp_clk_landing LOCAL param (CLAND-RING-LOCALITY ef145cfb0d0); bind emits .LOCAL(1) -> GEN_LINT defparam LOCAL. Same as TL-COLH9R0P5 / TL-LEAFT14.
- TL-LEAFT14 patched only epyc9 B3v/src. I replaced the same 4 files (landing, landing_ca, dly_cnt, meso_fifo; sha 80f7e8c3.. for landing) on epyc7, epyc8, epyc10, intel1 B3v/src (atomic mv, hardlinked trees untouched; backups /srv/opentallas-scratch2/claude/tl-colh9r0p3/bak). epyc2 has no B3v.
- Next: wave relaunched p3 pv rows 04:47; follow place/GRT for first form past gen_lint; then post.
