# QC-V4-COLL handoff (Opus; sub-lane of QC-V4; adopted OPUS-FIX-QC-COLL-R3 11-23 06:0x PST)
Read lanes/handoff/OPUS-FIX-QC-COLL-R3.md + FABLE-FIX-QC-COLL-R2.md. Work dirs: epyc10 fable-fix-qc-coll-r2 (pkg/pk/pkit), opus-fix-qc-coll-r3 (census, tl*), qc-v4-coll (snap_relays.py); chains on intel2 fable-fix-qc-coll-r2/*.sh.
## Items (QC-V4 gate 13:00; not GATED by 12:30 -> REASONED text with the census for FABLE-RC-QC)
1. pkit_core8 = pkg15 d44c372da00a, probe kit goal grt (LBL DRAFT refuses goal route): intel2 unit qc-v4-coll-core8g (coreg_chain.sh 15 8 4737f2eea2fd, log core8g_chain.log). Auto-census epyc10 unit opus-qc-coll-r3-ac-pkit_core8 -> census/pkit_core8_probe. Baseline 8195 (pkit_core4), bound < 820.
   core8_chain died 05:12 on FALSE strict check (bind.log fine). Comparison: pkit_core6 probe total 11 (H4 V7); pkit_core7 probe running (opus-qc-coll-r3-ac-pkit_core7).
2. RST-LAUNCH-1 fixpoint pushed main a98811abf9 (lane clone epyc8 opus-fix-qc-coll-r3/clone). pkit_core9 = pkg17 (pkg15 + relay snap-out, 91d21665533a) on rt a98811abf9fc:
   bind unit intel2 qc-v4-coll-core9 (core9_chain.sh; its goal-route run-item will be LBL-refused), then qc-v4-coll-core9g (coreg_chain.sh 17 9 ..) runs the probe kit pkit_core9 (goal grt, includes CTS). Auto-census qc-v4-coll-ac-pkit_core9 (epyc10).
   Read hold at CTS from the post-hook report only; grep OT_TAP_RESET_SPLIT_LAUNCH "rounds N converged 1" in the CTS log.
   Residual known: async cross-tap sinks 4 (launch=0) / 9 (rounds) on clk_t70 clones = cap recheck after hop latches re-assigns split sinks (19 vs 6), not the split pass.
3. 31 vs 32: launch inline order bug (u_rrl_340 new source 11 taps; u_rrl_234 1->6 taps); deterministic; pre-split taps identical. Posted.
4. c4 row: epyc8 qc-v4-coll/coll15_edits.json b938ddecaf1f (posted 06:3x).
