# FAM-S81-SERDES-R3 handoff (started 2026-11-21 05:3x PST; successor of FAM-S81-SERDES-R2)
Read first: lanes/handoff/FAM-S81-SERDES-R2.md, FAM-S81-SERDES.md, FAM-S81-SERDES-j7-split-rows.json, FAM-S81-SERDES-R3-sibling-census.tsv.

## Running (waiters armed in this lane; every ot-run has OT_LANE set and self-posts DONE/DIED)
- t4 J6 rep kw-s81-serdest4-1-63632 (a1, gen epyc9, stage place at 05:3x). At pre_cts read 4_1_cts.log cohort line: if "unfit light-root groups [222]" recurs (as t4 a15), write a reset-cohort row (serdes_cohorts_env.py:15 fail-closed), not a retry.
- J6 a1: t12 kw-s81-serdest12-1-66906, t14 kw-s81-serdest14-1-66906, t16 kw-s81-serdest16-1-66898. Old rt SUPERSEDED-KEEP: t15cla21 a7, t15cla3d a5, t1clb45 a7, t1clfe a9, t13 a7 (do not cancel).
- Core builds on epyc8 (out /srv/opentallas-scratch2/claude/fam-s81-serdes-build/<label>{/,.log,.exit}; clients intel2 ~/fam-s81-serdes-r2 and ~/fam-s81-serdes-r3):
  - enc_j6a (R2, kit s81fam_kp4_enc, pd 0.3, relief 30): oth-ubuntu-853983-1795266987, intel2 client PID 1910765.
  - encb_j6b (A/B, kit s81fam_kp4_encb = reference env: pd 0.5, OT_BH_ROUTE_RELIEF_PS 0): oth-ubuntu-1425806-1795268367, client PID 2685254.
  - dec_j6b (kit s81fam_kp4_dec regenerated: dchn pg_layer M5 -> PDN grid macro_m5 M5-M6; pd 0.5): oth-ubuntu-1425930-1795268368, client PID 2685253.
  - dec_j6a DIED 05:36 in 2_4_floorplan_pdn PDN-0233: signed dchn PG pins are M5 but it sat in the M4 sram grid (fixed above; old kit kept as physical/ref_tile/s81fam_kp4_dec.j6a).
- Column bench (bench_dec_core.sh in the clone, ot-run epyc7, client PID 2972280, out fam-s81-serdes-build/bench_dec_core/): default vs -DOT_S81_SERDES_DEC_CORE, plain + serdes__t4 defines, col PASS / mut1 FAIL expected.

## COORD ruling d442c09bb6e (env parity), applied
Reference = closest signed S81 core, svc hslice_mm3r (epyc7 fable-fix-s81-svc2/svc_r692, mm3b + r692). The wave-only vars (OT_PGCAP, PLACE_MAX_FANOUT, CLAND_STRIP_DENS, SIGNED_VIEW_SHA, GPL_SPARSE_UTIL, flow_tag) are absent from the reference ref_tile flow too. Declared design deltas, kept: pin_regs + reset_landing OFF (0 added cycles), so PRE_DETAIL_PLACE = out_flop_release (not pbp); pin_balance group_max 1 M4/M5 (545-bit faces); dec macros + M6 grant. For the SHELL kit, use the serdes__t4 wave kit env + gen args exactly (spec.json of the J6 row, kit_wave dir s81_serdes__t4_bf6905ce91d07/a1/spec.json) and diff config.mk before launch.

## RTL (lane clone epyc7 /srv/opentallas-scratch2/claude/fam-s81-serdes-core, uncommitted; push after bench PASS)
- rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv: `ifdef OT_S81_SERDES_DEC_CORE` -> u_dec = ot_s81_kp4_dec_lp_core (.ck(pma_rck)); else unchanged (REFORM / lp).
- rtl/dsrom_sys/s81_link/lp/ot_s81_kp4_dec_lp_core.sv (wrapper), tools/die_plan/test_serdes_dec_core.py (6 pass), tools/s81_link/run_serdes_col_bench.sh (COL_DEFINES + wrapper source).

## Next
1. Bench PASS -> ot-push-main (Co-Authored-By: Claude Opus 5.5).
2. Views from the first signed enc/dec (DRC 0, TT >= -42, FF hold >= 0; CTS post-hook) -> private tree on epyc10 (pattern s81-j6/mk_cand.sh + rows/svc/elab.sh + gate.sh: ELAB then strict --all-gaps bind + LATCHECK) with the t4 delta: +define OT_S81_SERDES_DEC_CORE; hard_cores = [u_core.u_dec (ot_s81_kp4_dec_lp_core, origin [1075.68, 388.8] R0 = in-core dchn on the old dchn site), u_core.u_enc (ot_s81_kp4_enc)]; drop u_core.u_dec.u_chn row and the two SRAM physical_parts (now inside dec); manifest: add the wrapper source.
3. Shell kit census (< 400k) from the bound tree. Watch gen_phys.txl_mid_exports: RXPIPE/RCK4 chains name u_dec.u_face_p_d / u_dec.u_rck_transport4, which are inside the hard core in the shell.
4. Rows to S81-J6-ASSEMBLY-R3 (J7); update j7-split-rows json (dec 725.76x388.8, enc 216x216 not 780x920 / 560x710).

## Sibling census (lanes/handoff/FAM-S81-SERDES-R3-sibling-census.tsv)
All 11 serdes types have the same outline 2885.76x1226.88, the same 13 defines, the same contents (ot_pdie_serdes + PMA + dmem/cmem) and the same dchn hard core, so the same cut applies to every type. The dec box placed so that its in-core dchn lands on each type's dchn site (R180 for t14/t2) fits under the PMA rx macro in all 11. Shell estimate = kit cells - 204k = 87k..183k (x1.17 placed repair = 102k..214k), all under 400k.
