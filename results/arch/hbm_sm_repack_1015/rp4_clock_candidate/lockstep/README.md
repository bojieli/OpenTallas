rp4 local-root clock lockstep (tools/hbm_sm_repack_1015/local_clock_lockstep.py) on source 8934fe46d + harness fix 7fdc03da3,
production-shape stress sequence NC8 active8 RMAX4096 TAGW16 with the rp3 defines, ot-run on ot-epyc1tb 2026-10-16:
- rp4_positive.log: ot_hbm_smh_rp4_gated (28 gated roots) in place of ot_hbm_accel_smh_tile_eg/wg: 13 commands exact, PASS total_cycles 14059.
- rp4_clockdrop.log: --mut-clockdrop (clk_hard[0] held low) FAILS (no command completes), as required.
