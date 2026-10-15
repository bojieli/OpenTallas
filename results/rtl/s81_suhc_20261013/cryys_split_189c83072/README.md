# crooty_y as 11 slice leaves ot_s81_hc_cryys: bench record at 189c83072 (ot-epyc1tb, 2026-10-13)

- `lock_m0.out`, `lock_m0_c2.out`: tools/s81_suhc/cryy_split_bench.sh, 11 leaves vs the SRAM tile ot_s81_hc_crooty_y, p_y and
  p_flt every cycle, C 0 and C 2: 0 mismatches / 60,000 cycles, PASS. `lock_m1.out`, `lock_m2.out`: negative controls, FAIL.
- `hc_tile_exact.out` + run_*_probe.json: NG256 production-shape HC composition (hc_tile_bench.sh exact), bit-exact
  0 / 1940 x3 at 6,392 cycles (unchanged), probe: 22 ot_s81_hc_cryys instances at W 256 / YD 16.
- `hc_tile_mut.out` + run_*_tm-ot_s81_hc_cryys.json: p_y bit 30 inverted in the leaf: 1,770 / 1940 error rows x3, FAIL.

Physical closure is the loop job s81hc_cryys_ref-v1-flopslice-023a586ca (not part of this record).
