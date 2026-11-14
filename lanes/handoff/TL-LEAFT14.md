# TL-LEAFT14 (S81 ot_s81sl_leaf__t14) 11-14
- t14 attempt_4 FAIL GEN_LINT: ot_dp_clk_landing.sv:10 Cant find object for defparam LOCAL. Same error hits 52 wave rows (slice_station t49/t29, col_h9/h10, leaf t35 ...).
- Cause: s81 wave src (epyc9 .../s81-b3-clk/run/b/B3v/src, src_sha 7073a6b4) predates CLAND-RING-LOCALITY ef145cfb0d0; bind emits .LOCAL(1) but staged ot_dp_clk_landing.sv has no LOCAL parameter.
- Fix 11-14: replaced rtl/common/{ot_dp_clk_landing,ot_dp_clk_landing_ca,ot_dp_dly_cnt,ot_meso_fifo}.sv in B3v/src with origin/main versions (new inodes; backup epyc9 /srv/opentallas-scratch2/claude/tl-leaft14/bak). Defaults identical logic.
- Needs: KIT-OPS-3 retry of s81 rows failed with this GEN_LINT error (t14@4 first).
