Codex HA2 reducer build (run_045cc7411, reduce_build.exit 95: ELABORATION_FAILED_MISSING_ot_hdc_lzc32) re-run with
the missing dependency rtl/hdc/ot_hdc_fastfp.sv (defines ot_hdc_lzc32) added to the file list; RTL unchanged
(source commit in source_commit.txt, branch codex/ha2-direct-links-20261003; inputs pinned in input_sha256.txt).
Icarus elaboration of the 96-leaf tree did not finish in >10 min on a loaded host, so Verilator 5.050 was used:

  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_accel_snapshot_reduce \
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
    rtl/hbm_accel/direct_links/ot_hbm_accel_snapshot_reduce.sv rtl/hbm_accel/direct_links/tb_hbm_accel_snapshot_reduce.sv
  Vtb_hbm_accel_snapshot_reduce +DIR=results/rtl/hbm_accel_ha2_20261003/fixtures_r1

Result: build 0, 12/12 cases bit-exact, 49 cycles (7 levels x LAT 7) for the standalone 96-leaf snapshot tree.
This only fixes Codex's standalone arithmetic check; it is not the W19 o-group all-reduce (8 contributors),
which is measured end to end by tb_ha2_ar in this directory.
