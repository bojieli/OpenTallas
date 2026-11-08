# QC physical-wrapper parameter binding — Codex HEAD cross-lane help

Source branch: hub `codex/qc-physical-param-0222@66ee9cf755`, based on QC v4s `66a32140a0b`. QC lead owns the candidate and actual rebind; this lane owns only the helper class. No POR change or merge.

Failure: actual strict bind_try4 on epyc6 returned one PARAM_REGEN error: `SC_HARD_PARAMS c_E0_bf_10: hard core u_t30 binds 0 leaves`. The physical hard core is qfd_tile_nl_a0c, while the native functional leaf is qfd_tile_nl_rp2_romleaf_rr u_u_t_3_0. IDLE_UCK belongs to the physical wrapper. Existing kit_core_clocks already performs the exact registered native-to-physical swap.

Fix: explicit hard-core `params_scope: kit_macro_rtl` (old bound_leaf remains default). Resolve the declared contents.parent_id_leaf against actual members and the registered native master. Keep logical source params unchanged; emit a mandatory typed bind obligation. kit-rtl must consume that same obligation and exact native swap, then apply IDLE_UCK only to qfd_tile_nl_a0c. Unknown parameter, missing/duplicate/stale obligation, wrong native module or wrapper fail closed. No naming skip, no latency or RTL arithmetic change.

Validation: 31 focused tests PASS in 0.20s, including the original failure when scope is dropped, missing-obligation controls and actual physical-swap application. This is SOURCE-READY only, not batch release.

Actual next step: QC lead consumed all six helper files into its owned E6 farm and added the field to exactly two accepted NL HC rows, candidate SHA c614fa90f616. Fresh strict bind_try5 is queued via ot-run 24GB/2T/disk2, seeded from the same 55MB asbuilt cache. Logs: epyc6 /srv/opentallas-scratch2/claude/codex-qc-nl-wave-0222/bind_try5.log; intel2 ~/codex-qc-0222-dispatch/nl_bind_try5.log. On strict0, ONE affected kit-rtl must show qfd_tile_nl_a0c #(.IDLE_UCK(1)) u_t30 and kit_macro_rtl.json; native source bind must stay unchanged. Old failure retained. No batch release before the actual pilot result.

## Handoff to Claude 2026-11-08 04:23 PST
All new work stopped on explicit reset. Helper66ee9cf755 unchanged/source-ready only. try5 loaded old hook via manifest symlink; try6 absolutebase rejected by manifest_paths, preserved. QC lead built genuine owned d95ec source package intel2 scratch2/claude/codex-qc-nl-native-0222@8d43c2f620d with exactsixfiles and scopedplan; originalrelative manifestPASS pathgate, try7 livefrontend2263313 to ...-run7/bind. Next strictbind0+exact2obligations thenONEaffectedkit-rtl actualwrapperIDLE_UCK1+kit_macro_rtl.json; compareaffectedrawRTLbefore/after only. No pathgate waiver/helper edits/batch release.
