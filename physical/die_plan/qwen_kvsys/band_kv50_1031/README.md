# DIE-KV-50 ring-band resize (2026-10-31, COORD 03:2x PLAN item from AUTOBUILD-PIPE-3)

Problem: the KV landing-ring storage bands of kv3_io_ft, kv3_io_ft_v1, kv3_io_cor (+ kv3_io_cor_v1) and kv3_hroot are
sized with the padded reserve model; the synthesized count-aligned rings need ~1.3x (io_ft ft0_i 3853 vs 2986 um2).

Change (only partition_types.<these 5>.clock.landing_contract.bands):
1. `clock_landing_plan.py resize-bands` (DIE-KV-32 fix-only tool, ring_ff reserve) over the 5 types: 78 undersized bands re-sited
   (resize.log), every other band byte-identical.
2. `fix4.py`: 3 bands whose ring_ff re-site added a G0C geom WARN (io_cor ft18_i r2r 486 > 405; io_cor i_host_link_rst_n;
   io_cor_v1 ft19_i) instead grow IN PLACE to 1.35x their old area (the measured need).

G0C vs main (g0c_try.sh, findings multiset): 28 errors unchanged; WARN new 3 / gone 2:
  + kv3_hroot pin_reg_max 153.36 (> 150 backstop, ft6_i[9])        - residual
  + kv3_io_cor r2r 447.57 (> 405, ft17 ring->s1, 1 stage)           - residual
  ~ kv3_io_cor_v1 pin_reg_p90 84.24 (was 142.56, max 203.04 cleared) - improvement (text change)
bands_render.png = rendered check (red = resized, blue dashed = old site).
