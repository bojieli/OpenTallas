# CODEX HEAD SPN/TILE/SC takeover 2026-11-08 11:13 PST

STATE 11:2x PST: collected actual current logs; no launches/restarts or live-job edits.

- SPN vG_LK: intel2:/srv/opentallas-scratch2/claude/dh86spn/hd_spn_vG_LK, container dpkit-hd_spn_vG_LK-859713. Healthy detailed route, initial pass90%. GRT TT+7.4 and nonport FF-38.12/344 were superseded by route release08:45; do not reapply old HOLD. Next actual routed signoff + images + port/nonport census and routedEQ.
- SPN end vE3_LK: intel2:/srv/opentallas-scratch2/claude/dh86spn/hd_spn_end_vE3_LK, container dpkit-hd_spn_end_vE3_LK-641584. Healthy detailed route, first optimization iteration30%. GRT TT+82.25 and nonportFF-14.81/63; route released08:45. Next actual routed signoff/images/census/EQ.
- TILE latest is vH11_pktap, not failed H9: intel1:/srv/opentallas-scratch2/claude/head-forms-3/hd_tile_vH11_pktap, dpkit-hd_tile_vH11_pktap-883177, routing70%. vH10 early anchors removed ALL latch timing misses; vH11 additionally aligns pk_h clocks to c1 consumers after vH10 TT-77.15/11. Next routed signoff and image review; no duplicate.
- SC vJ: intel1:/srv/opentallas-scratch2/claude/head-forms-2/sc_vj/hd_serdes_SC_vJ. Actual GRT FAILED GRT-0116 at18:44UTC after3h39m, congestion remains around x1429..1432,y20..95 at cmem west edge. No live SC pilot found. Read full final congestion and render5_1_grt-failed.odb; then apply measured spacing form rather than repeat sameGRT. Prepared source codex/head-sc-syndrome-1108@4dbdab4ec69 lives intel1:/srv/opentallas-scratch2/claude/codex-head-spn-tile-0222/sc_src; placement only, no cycle/RTL/clock/macro changes; no launch yet.

No OT_CLOCK_TAPS WARN core tap warnings found in actual TILEvH11/SCvJ4_1_cts.log. Therefore do not blindly apply cb13e19342a or rerun these healthy jobs for the escaped-generate class. SPN core-warning audit pending.

SC rendering initial lightweight command failed because image requires bash login to put OpenROAD in PATH; corrected bash-lc probe running. Source failedDB unmodified. No merges/tags/POR/deletions.
