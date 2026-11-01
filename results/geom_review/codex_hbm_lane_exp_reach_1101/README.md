# Lane expander measured existing-stage affinity

LOOKED at the existing3-column/2-row6-SRAM plan before placement.486 existing internal FF endpoints move into the actual~17um central street, retaining native clock/pin/macro/PG/outline geometry and every cycle. Placement-only PASS-COND, no routing release.

Actual DPL returned0: register reach569.81/422long captures ->374.60/0, pinmax101.73 unchanged,0cells on macros. Raw overallFAIL remains: aspect2.125 and channel_h1.231. No gate waived. Source sourceview530baacffafb, actualkit intel2:/srv/opentallas-scratch2/claude/codex-hbm-reach-batch-1101/lane_exp_place (ot-run spilled to intel1 unit1317914, outputs copiedback).

The exact-instance preDPL hook is a measured per-source-view payload for kit-owner adoption after rendered-plan/source review, not automatically installed in any production recipe. Next: determine allowed parent-derived outline/aspect treatment and measured-channel structural review before any routing.
