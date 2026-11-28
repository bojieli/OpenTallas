- 2026-11-27 16:57 PST RESULT [S81-PGREAD-R1 -> COORD, CLASS-TRACK-R3; class P-PG-OPEN-INSERTED-CELLS] rtx-pro native ODB readback of the 19 unread S81 INDEX cores plus NNfd re-read and the LL records. Method = S81-INT-R3-VIEWS pgread.tcl (every instance POWER/GROUND iterm bound to same-type net), read-only docker mount of the signed-export copies, nice 10, 4 threads, one at a time; .zst decompressed to a temp file and removed. sha256 of file (or zst/odb) = INDEX sha for all rows except one noted. Table: /srv/opentallas-scratch/claude/S81-PGREAD-R1/result.tsv + result2.tsv on rtx-pro (open = open PG terms).
  FAIL (open>0), 4 of 19 unread cores, DNC HOLD rows needed (CLASS-TRACK-R3 adds):
  dsdv_svc_sx_hrow 172741b9c5ca open 568 (clkbuf_leaf BUFx24 VDD/VSS)
  dsfd_su_t_rxsb e9c3f14d8ea5 open 1474
  dsdv_gunit_l4r 0bf390d87efa open 926
  PASS open 0 (15 cores): dsdv_bksel_c 11f32154a370 (also qrx_1117 e1f3b821e2ab, ax_413511afc429, ax_714ddd43c267 all 0); dsdv_eng_rr_h1 fb5089a9f370; dsdv_gunit_l1f_ba0 dd97d9a51b48 (+fwp_1117 97866b7d4f8e) ; dsdv_gunit_l1f_ba1 c047b7a2f2c2 (+fwp_1117 3d1df6a8acf2, fwppk_1117 17804c0392bc); dsfd_su_t_ikw c3717f52118c (ax record); dsfd_su_t_rxsf__k13t25 f5fed13fea54; ot_s81_rck_tx 45b84446ecb1; ot_s81dv_norm_finish 647beff11680; ot_s81sl_ve_m 2e13f623b612; ot_s81sl_ve_s cb9be51d939d; ot_s81sl_vn_a 3dd80461ccd5; ot_s81sl_vn_b 5f7472e81291; ot_s81sl_vq 9e4df6ba54ba; slice_station__t51 native_e 056a8fedab38 (and r1116_hold5_m7 ad355978c2b7) 0; native_w c21330253d3f 0.
  Notes: ba0/ba1 first rows are status SHA-DIFFERS-FROM-RECORD (read 0 anyway). dsdv_gunit_l1f_ba1__fwppk_1117: file sha d50ea546f00c != INDEX 17804c0392bc (read 0; sha mismatch flagged for INDEX owner).
  NNfd re-read: dsfd_node_NNfd 2023008e81d2 insts 37379 pg_terms 74758 open 608 CONFIRMED (BUFx16f clkbuf_3_* VDD/VSS).
  COORD item, LL records (which INDEX records are 596/586/596):
  dsfd_node_LLd record 6fa0cdaea5f68894 db 7746bace67e6 open 596
  dsfd_node_LLfd record edb9c0633a0fdc45 db 8723bdc652e9 open 586
  dsfd_node_LLfu record 50226227e29fa226 db 54ce2a09bbc4 open 596
  These are the old 1114-generation records (ARCHIVED-BOTH), NOT the counted ax records and NOT the diagnostics 570/570/566.
  COUNTED records re-read natively, all open 0, NO credit reverted: LLd__ax_932488f00d record 4b00224bb4ca9a20 sha 932488f00d60 pg_terms 45122 open 0; LLfd__ax_576f0b774b record ac80dd67bacca831 sha 576f0b774b63 44734 open 0; LLfu__ax_a1c11fa41d record abc97deae935157e sha a1c11fa41d1f 44706 open 0. Other ax rows also 0: LLfd__ax_f9cb03b476 (record 0673fecd01160eb3) 44624 open 0; LLfu__ax_db095894cb (record 58632840934a96b2) 44768 open 0.
  COUNTS: unread 19 -> read 19 / pass 15 / FAIL 4. Combined with 14:57 census (64 read, 60 pass, 4 fail): 83 read, 75 pass, 8 FAIL (LLd, LLfd, LLfu, NNfd, sx_hrow, rxsb, l5f, l4r). No store/archive writes; temp files removed.
