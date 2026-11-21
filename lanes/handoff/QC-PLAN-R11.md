# QC-PLAN-R11 handoff (started 2026-11-21 11:2x PST; succeeds QC-PLAN-R10). Read QC-PLAN-R10.md first.

## 12:4x state
- Ruling 1 (wave runtime): QC kits ALREADY run the scheduler rt/current per launch (TOOLS-DECOUPLE). V2 launches 11:28-11:51 recorded
  tools_sha c2047d41ccdf / a13768301176, and both carry 3ed87c352a, 4f638b4e9f, f56d99cf55, 8d1cff9b1b and a0fc9811a19.
  The die pin dies.qwen_compute.tools_sha (65f3f) is the TREE-tools reference (tool_skew, apply marker). I bumped it (f656e319b7) and then reverted it (a98671dde7):
  the bump only created 229-module skew-warn noise. The pin moves with the V3 tree.
- Ruling 2: strap fix on main 289287760f + 3fba1b4bc0 (confirmed by FABLE-FIX-QC-STRAP-R2). epyc7 qc-plan-r9/v3rows/r8_straps_rows.json is updated:
  T1 LANDED; R8S-1 = asbuilt land_pad_tail_split.r8_keep true + plan budgets.r_r8_core_seat ["slw_st_a","sle_st_a"], PROVISIONAL until the
  STRAP-R2 proof kit (slw_st_a_v2__cl9f076a5c, launched 11:54, epyc8) posts CTS post-hook; R8S-2 PARKED; R8S-3 sle_ctl = SITE class (read done, below).
  The STRAP-R2 b1 private bind (strict 0, LATCHECK 1921/1921) is at epyc8 /srv/opentallas-scratch2/claude/FABLE-FIX-QC-STRAP-R2/b1.
- Item 4: sle_ctl a5 -440.70 read from 3_place.odb (epyc8 /srv/opentallas-scratch3/claude/QC-PLAN-R11/sc_read/sc_path.rpt). The strap mux costs 131 ps;
  a 705 ps buffer detour (1,550 um of wire for a 380 um manhattan) runs bank (618,614) -> rp mux (732,322) -> station (909,526). Fix = relay_sites for the rp chd_q banks; T2 parked.
- Item 5: ot-delete done for epyc7 qc-plan-r9/{b17,b18,b18r,b19} and qc-plan-r8/v2b_host/{b12,b13,b13dbg}.
- btab (g_read -> u_u_r3/bt_q_p -124.3) V3 plan item: owned by QC-PLAN-R11 (ACK to STRAP-R2). Rows asked from FAM-QC-HCST-R2: SRAM column X about 250 um.
- V3 order = ~/coord/lanes/FABLE-PD-QC-1230.md sec 2 (11 rows), and its stop list sec 3 binds. Row cut 11-22 06:00 PST; apply >= 11-22 11:16.
## V3 work dir epyc7 /srv/opentallas-scratch2/claude/qc-plan-r11
- bind_v3.sh = qc-plan-r9/bind_b18.sh + coll RTL from main ae660e1299 (rtl_main/). chain_v3t.sh = TOOLS-ONLY control: V2 plan + rt 31c7ccbd1b93
  (strict bind + LATCHECK -> post-bind G0 vs b20 G0 -> census); log chain_v3t.log, out v3t/.
- Helper QC-PLAN-R11-SITES (subagent): sites for site-less multi-station ft slots at unchanged station counts -> qc-plan-r11/sites/plan_sites.json + static G0.
- Lane clone: epyc7 /srv/opentallas-scratch3/claude/QC-PLAN-R11/clone (sparse tools + physical/die_plan/qwen_compute).
## Rows status (V3)
1 sle_ctl x_su_l0_i pad as count strap: asked QC-SLE-R5. 2 st_a seat (provisional) + btab column: STRAP-R2 / HCST-R2. 3 reach rows with sites: SITES helper + family lanes.
4 cell splits: asked FLOW-STRIPBODY-1121 for the schema; census qc-plan-r9/cells_census.tsv. 5 cb: FAM-QC-CB-R2 (cbf_q00 taps stay t24/t25/t93/t100; stations after CTS).
6 stm row 2b2dfe128b06 (QC-SLE-R5). 8 fw x_sc_i rows (FAM-QC-FEFW-R2, need sites). 11 coll rows_bcd (FAM-QC-COLL-R2, needs main >= aaa1dcff0349).
