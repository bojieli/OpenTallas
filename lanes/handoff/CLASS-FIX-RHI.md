# CLASS-FIX-RHI handoff (Opus 5.5, started 11-23 01:5x PST)
Brief: rtx-pro scratchpad fable_uncovered_brief.txt + rules.txt. Trailer "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
Scope: HOTSPOT-GAPS NONE items, classes RESET-ASYNC / HOLD-SKEW / IO-BOUNDARY, all dies (S81 168, KV 51, QC 13, HEAD 8). COORD 02:1x: also KV sys_c HSK+IO.
Coordination: FABLE-UNC-KV owns KV cland port_in hold row (I review). FABLE-UNC-HEAD owns W+E cross-tap hold. TAP-GRID-R5 = taps (sys_c, SEAT-1c pin-reg taps, h9_r2 span).
## State
- 02:1x TAKING post 62c7e037. 02:30 REPORT-1 post 94a268e8.
- Row script: intel2+epyc8 /srv/opentallas-scratch2/claude/class-fix-rhi/ROWS_CLASS-FIX-RHI.py sha 72b268847ec4 (RST tap_reset_split / HSK tap_pair_affinity+macro_follow / IO die io_hold sender_min).
  KV dry: base_d28 -> 55 types RST + 55 HSK + die IO; gen_phys tap_pair_affinity_exports 0 errors.
- Census evidence: intel2 /srv/opentallas-scratch2/claude/hotspot-census/central/*/census.json; 50/51 kits had no tap_reset_split (only lepe_mu_LP t2: split 205 sources, still -62 intra-tap + arst_n port -162).
## Next
- PRE on each die's composed plan; probes (KV hroot+sys_c, QC sle_su_l1, S81 col_h9_r2 + leaf t47, HEAD lep0N_w); ROWS-READY to plan lanes + FIX-LEDGER.
## 02:5x
- Harness (in-memory affinity+split on 44 census CTS DBs, ot-run per host): logs intel2 /srv/opentallas-scratch2/claude/class-fix-rhi/h_<host>.otrun.log; mismatched reset sinks after split <=17 everywhere (col_h9_r0_p4 393->6).
- Probes (private-spec wave plan, --goal grt, rows as --ab env): intel2 class-fix-rhi/probe_chain.sh DIE ITEM TAG PAIR; logs probe/<tag>.chain.log, spec probe/pspec_<tag>/ (run.log, result.json): kvhroot, qcsu (sle_su_l1__cl5ea486db), s81col (col_h9_r1 pv4bd36c74), s81leaf (leaf t47), head (hd_lep0N_w).
- Posts: ROW-DRAFT e400f4de, ASK TAP-GRID-R5 SEAT-1c die-wide 6f5c6ed0, ANSWER ledger/HEAD a6668871 (ring IO class = FABLE-UNC-KV REASON e7e8752c; reset REACH legs not mine -> FABLE-UNC-S81-DIE; HSP -> R9 PAIRTAP / BKSEL Row 4).
- Census stage note: S81 HSK 85/93 and RST 131/165 path counts come from pre-repair DBs (4_cts / grt-failed).
- Macro HSK sub-class (col u_u_sN, leaf u_vs, QC u_tN: hard-core launch at 0-117 ps): early core tap; macro_follow in RHI-HSK is the lever, probe s81col decides (setup risk on macro paths).
## Gates owed: HEAD 11:00, S81 12:30, KV/QC 13:00 (PRE on composed plan by plan lane; my probe read under fe8a2a5).
