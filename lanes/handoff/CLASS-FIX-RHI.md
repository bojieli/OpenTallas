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
