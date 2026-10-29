# Parked parent physical step at explicit Claude reset

Branch codex/qc-a0-2340-1028. Current immutable source kit intel1:
/srv/opentallas-scratch2/claude/codex-qc-a0-2340/parent_reset.
Only source delta from parent_zero is the proved one-line resetmux cleanup (02f7af5ac).
Fresh SYNTH succeeded; fresh placement continues with this full-FF target table sourced from
face_flops_release.tcl before DPL. Original old-gate placement and failed geometry remain in
nl_parent_placement_trial, anchor_review and anchor_legal_review. No parent CTS/GRT/route run.

The full connectivity graph has14257 FFs/38961 edges. LP/MILP estimate preserves all data/reset
edges except the two proved redundant root-reset mux edges, limit395um, pin30um except hard145um
for reset/outervalid candidates, avoids every macro.765 FFs move relative original placement;
the table includes all FFs so fresh GPL cannot undo the unchanged FF anchors.
The q94 target has15um extra margin: all its incident analytic edges<=380um. The original q94
legalization drift caused405.054um and is preserved, rather than waived.

Read-only original-gate actual DPL moved887->3 captures>405 and collapsed relays10->0.
Two residuals are exactly old resetmux edges (removed by new synth); third is q94 above.
Actual fresh placement must be dumped/rendered/reviewed and exact reach collected before CTS.
Independent GEOM has been asked to classify legacy aspect/partial-face/channel flags; no PASS
is implied here. New-gate proof belongs to /root/hbm_cores/lec; old freshgold-vs-retainedgate
12570joint/31742full PROVED is committed in parent_reset_proof.

PLAN_ONLY parent CTS prototype remains results/codex_qc_a0_2340/parent_hook. It must first run
fresh clustering/model, render and review the DME plan, then adopt plan-declared TT/FF IO frame
via merged FLOW typed contract. Old trial250/202.5 frame remains; no new values chosen.
NK successor recipe NOT GENERATED yet: all three actual SIGNED views are now in ../views.
NK has additional reset output paths/node macro collar and needs its own placement plan;
do not blindly apply the NL-only resetmux proof to NODE1/blackbox valid outputs.
