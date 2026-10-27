# Shared-flow diagnostic canary review, 2026-10-27

Candidate: RC source 7944d7dae/evidence2bbe885e4, placement repair37d9b8a28, preflightb56b0b55be (includes FF-bound9529b56ff0), centre-track snap5b2b94251f.

Viewed s81.png, s81_head.png, qwen_compute.png, qwen_kvsys.png (reset_tree.render on exact candidate plans), and the retained KV-KITS-1 b51 actual placement image intel2:/srv/opentallas-scratch2/claude/kv-kits-1-1027/render/kv3_io_ft_v1.place.png. Prior independent canary-reference review history remains in coord/lanes/GEOM-REVIEW.md; these are unchanged reference shapes used only to measure shared-flow regression.

The S81/KV relay grids are regular and below405um hop reach (379.1/345.6um); QC has an irregular central fanout corresponding to explicit type taps (max374.4um). Head turn is a narrow tall reference with sparse taps: inherited structural/insertion failures remain; no closure claim or design adoption. KV actual placement has straight two-band east-west data flow, aligned boundary pins, regular station/repeater columns, no macros or blocked channels. The candidate changes placement buffering, so these plan pictures are not an actual-placement approval.

Verdict: PASS-COND for generation and placement-only diagnostic canaries. Every candidate placement must be dumped, rendered and viewed before CTS/global/detail route. A failing actual placement is held for diagnosis; original failed reference verdicts are retained. This review grants no physical sign-off and no mass-route release.
