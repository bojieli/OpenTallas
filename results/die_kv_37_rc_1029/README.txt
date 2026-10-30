DIE-KV-37-RC (2026-10-29 PDT) root cause of KV CLOSURE rows KV-023 / KV-024 (regen_constants MISMATCH on the KV bind of
record event28b/bindB2 and identically on event27f control). Evidence: intel1 die-kv-36-1029/regen_constants_bindB2.json,
intel1 /srv/opentallas-scratch2/claude/die-kv-37-rc-1029 (pvcol.log).

KV-023 PV ctl TRUNK_D/FLAG_D (bound 54/58 = as-built; regen law 62/77 S, 63/75 N, cmd_delta_uniform/flag_uniform FALSE)
  WRONG SIDE = the BOUND RTL (recipe), not regen_constants.  ot_qwen_tp8_pv_wide_ctl_tbf checks all 32 column flags in ONE
  cycle (COL_CHK = COL_LAT + TRUNK_D + FLAG_D); on the bind of record the column command depths are not uniform vs as-built
  and the flag returns land at different totals, so the bound ctl (as-built 54/58) samples before most column flags land:
  PV is functionally wrong on the bind of record.  DIE-KV-14d/15/19 fixed exactly this with PV column equalisation pads
  (r8/kv_pv_col_pads.py table in land_r8_extra) + param hook r8/kv_pv_col_regen.py (DIE-KV-19 recipe_kv19_b6: TRUNK_D 63 /
  FLAG_D 78, regen PASS).  ROOT CAUSE: the CODEX-KV-24 recipe (-> kv26b -> kv27f -> eA2 -> eB2) was derived from
  recipe_kv19_t1, the INTERMEDIATE DIE-KV-19 recipe built WITHOUT the column table (only to regenerate it) and with the
  pre-14d hook regen_kv_2350.py, not from recipe_kv19_b6.  Every later bind dropped the pads and the TRUNK_D/FLAG_D regen.
  FIX (files here, bind NOT run): kv_pv_col_pads.py on bindB2 (made without the table) -> pv_col_pads_28b.json:
  TRUNK_D 63, FLAG_D 78, C 9, 1178 members, max cmd pad 19 / flag pad 116, 141,684 pad FF (134,208 cmd + 7,476 flag);
  member set IDENTICAL to DIE-KV-19 pv_col_pads_t1.json (1178/1178, 0 diff): column depths unchanged since KV-19 [CHECKED].
  recipe_kv27f_eB3.json = eB2 + that table in land_r8_extra + param_regen kv_pv_col_regen.py (composes regen_kv_2350
  unchanged).  test_kv_pv_col_pads.py 3/3 PASS [CHECKED].  Next: strict bind eB3 -> expect 0 errors and regen_constants
  TRUNK_D/FLAG_D OK 63/78 [UNCHECKED until bound]; kv3_pv* kit RTL changes (pads + 2 params) -> re-kit + LEC the pv types.
  TOK: +1 TRUNK / +1 FLAG cycle vs the law on unpadded depths (as-built 54/58 is not a valid baseline: it is broken).

KV-024 xdie D2D_TXDP_K (bind applied 32h030304aa = K [170,4,3,3]; regen 32h030304a9 = [169,4,3,3])
  WRONG SIDE = the committed pair image record kvbind1025/pair_image_txdp.json (stale), not regen_constants.
  The record was made on claude/die-kv-16-1028 bind5 with seams XDIE_SEAM_K 90,90,88,88,88,78,78 (SK_TXP 78): K0 = KS_TXS 88
  + codec 2 + SK_TXP 78 + pinreg 2 = 170.  The bind of record has SK_TXV/SK_TXP 77 (regen XDIE_SEAM_K 90,90,88,88,88,77,77 OK,
  D2D_KV_TX_LAT 169 OK) -> K0 = 169.  regen_kv_2350.py copies the record verbatim, so the bind applies 170.  Same on event27f.
  FIX belongs to TOK-KV-4 (COORD 17:23 ruling (A): pair image + production script + regen_constants derive K from the bind,
  fail closed): its regenerated pair image must re-derive K0 (169) and XDIE_SEAM_K (..77,77) from the bind, not only K1
  (4 -> 157), and QC must bind the same image.  Not duplicated here.
