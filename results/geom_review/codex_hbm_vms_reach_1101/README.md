# VMS existing-stage affinity trial, 2026-11-01

Review: LOOKED at the six actual-geometry plan renders in batch_review.png before placement. PASS-COND for placement-only measurement. No full-tile PASS, routing release or signoff is asserted. No RTL, pin, macro, cycle, clock-period or uncertainty changes in the winning layout.

The original macro stack is retained. Existing long internal FF endpoints are moved into the real central macro-free street; boundary FFs and existing fixed sequential anchors stay fixed. Only the first two reset synchronizer stages move near rst_n; delivered reset stage and reset depth stay unchanged.

|View|Before reach / long captures|After measured reach / captures|After pin max|
|---|---:|---:|---:|
|hnx_vms_bank_q0_faces__vec6293@d2ac2d17712e|511.65 / 59|379.86 / 0|15.46|
|hnx_vms_bank_q0_faces__vec6293@f50d62432a5f|515.59 / 94|379.65 / 0|15.67|
|hnx_vms_bank_q0_faces__vecd4ae@114e9076fa98|445.77 / 2|379.73 / 0|17.68|
|hnx_vms_bank_q0_faces__vecd4ae@d6532bde006e|532.76 / 11|379.62 / 0|17.68|
|hnx_vms_bank_q0_faces__vecd4ae@ed4cba8a8b2a|455.17 / 34|379.84 / 0|17.95|
|hnx_vms_bank_q0_faces__vecd4ae@f9c1bd05a046|439.94 / 2|378.05 / 0|16.60|

All six detailed placements returned zero and have zero cells on macros. Raw remaining failures are preserved individually in placements.json: fill/empty, some partial-face variants, and estimated channels. There is no blanket waiver.

The four actual SRAMs expose415W/414E signal ITerms each and zero N/S signal ITerms. The tight N/S contacts are non-signal faces; the continuous W/E side channels remain ~47um. The signal GRT50 on the f50 winner is pending in epyc2:/srv/opentallas-scratch2/claude/codex-hbm-multitap-1101/auto_kernel; M2-M5, adjustment0.25, budget50, CLOCK nets excluded by the standing geometry GRT recipe. A measured zero overflow would be evidence for a concrete coordinator decision on channel estimates, not automatic release.

Rejected alternatives are retained in the sibling clock trial scratch: widening macro streets17/23um shrank the south logic band and worsened horizontal channel demand1.79/2.44;23um also left21 long captures428.19um. Initial moved-macro attempts failed ODB0359 (LOCKED macro), then DPL had stale macro-cut rows; repaired scratch probes unlock/relock and rebuild rows before measurement. These alternatives are not adopted.

Source: independent planner branch codex/hbm-reach-plan-1101@db2dde426. Native-clock work lives separately on codex/hbm-multitap-1101@74f30a973, which also contains a held PSlice recipe and must not be blanket-merged. Native CTS preserves9 distinct roots,0unrooted/12212sinks, measured leaf65.83/79.60um; TT estimated-RC tap-mean windows22.4/23.0ps still miss the20ps planning target. No clock or routed signoff claim.

Fresh-kit integration still needs an opt-in exact existing-FF placement contract consumed in the normal flow; the standalone measured trials do not by themselves change production recipes.
