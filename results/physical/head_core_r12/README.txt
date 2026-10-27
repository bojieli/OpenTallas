HEAD-CORE-R12 (s81_head elemA / elemB) -- 2026-10-27 00:26 PDT
Base: claude/head-core-r11 @ dfc4dfc3e7 (CY_COPY source fix, APPROVED, ROOT-MERGE-28).

Finding 1 (elemB "no SIGNOFF line"): the R10 hold2 job is actual_head_grt_repair.sh = do-5_1_grt (HB4 hold repair,
2nd hold pass hook) + read-only GRT STA. It never routes and never runs signoff.py, so no SIGNOFF line is expected.
Finding 2: the elemA "SIGNED" line (elemA_hold2/signoff.log, TT 93.06 / FF 0.99 / skew 59.9/60.6) is dated
2026-10-25 04:08 -- a stale file copied in with the kit from an older hd_elemA_rb build, not this run.
Neither element is signed off yet; sign-off = actual_head_route_r12.sh (route + finish + signoff.py RCX).

hold2 GRT numbers (actual_head_sta.tcl, rc_cal 0.8/0.9 GRT estimate; tool-reported):
  elemA intel1: TT setup +118.468/0, FF hold +10.622/0, FF setup +234.446; R10_HOLD_DONE WNS +15.001 n 0; 15979 HB4.
  elemB epyc2 : TT setup +120.552/0, FF hold +10.710/0, FF setup +237.305; R10_HOLD_DONE WNS +15.001 n 0; 14447 HB4.
  Post-repair incremental GRT: no overflow warning, no congestion_post_repair_* report written (overflow 0).
r11_collect.sh: actual_grt.v newer than repaired 5_1_grt.odb (not stale); portless-TAP export functional changes 0
  (A 8176 / B 6771 TAP rewires) -> KIT.lec_r11 with CY_COPY-patched RTL.

Chain (r12_chain.sh, ot-run 48 GB / 16 t, self-logging to KIT/r12_chain.log):
  lec.py (gold = r11 RTL) on the HOLD-REPAIRED export -> gate: verdict EQUIVALENT, kept missing 0,
  0 dead g_s[0] cy copies in gold.keep -> actual_head_route_r12.sh (Codex route script; only LEC receipt path changed).
Kit tools refreshed to main 4983d8e2d (signoff.py f503e9ae etc.; originals in KIT/.pre_r12/).
Units: elemA intel1 oth-ubuntu-3616694-1793085923, elemB epyc2 oth-ubuntu-1289176-1793085922 (started 00:26 PDT 10-27).
COLLECT: grep -E 'R12_|SIGNOFF' KIT/r12_chain.log; KIT.lec_r11/lec/lec.json; KIT/signoff_actual.log + signoff_actual/signoff.json
  (RCX core latency TT 250+-20 / FF 202.5+-20, DRC 0, pair skew); KIT = /srv/opentallas-scratch2/claude/head-core-r10/elem{A,B}_hold2.
