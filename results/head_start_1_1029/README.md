HEAD-START-1 (2026-10-29): START/reset-wavefront span blocker, estimate + structural gate

Winner: variant A = Codex leaf START form (leaf CA plan leaf_plan4, 1707 regions = 1356 virtual stages + 351 per-part leaves,
1706/1706 clean edges, 0 J ambiguity) with stage resets taken from existing local registered raw-wavefront relays
(main head_start_reset_exports/local_reset/sources), root SETTLE 74 (prototype). Inputs (sha256 in start_offsets_planned.json):
intel2:/srv/opentallas-scratch2/claude/codex-head-start-0251/leaf_plan4.json, localhost(rtx):/srv/opentallas-scratch/claude/
head-start-mapped-0251/final5/{start_stages,physical}.json, ../die_head_21_1028/hk4/reset_start_offsets_rx_tx.json.

Gate on planned stage-pin geometry (make.py): stage->parent 1355 max 357.372 um, 0>405; last stage->capture pin 351 max 362.576 um,
0>405; reset source->stage 1356 max 322.404 um, 0>405. Provider vs plan: 0 parent/PAD/EDGE mismatches (cycle count matches plan).
Old hk4 CA3 failure reproduced: 303/306 virtual-parent spans >405, max 2219.265 um. CA4 dense tree (no leaves) still has 153/327
last-stage->part START pin hops >405 (max 1919.9 um mesh0S), i.e. CA4 alone does NOT pass; the leaf/capture-site step is needed.

Variant B (nearest-tap origins on CA4 + count-aligned delay) estimate FAILS without moving pins: 277/351 parts have their START pin
>405 um from every own clock tap, and the 30 spine-group parts have no CA4 stage within 360 um with a non-negative PAD. Siting the
origin pin beside the capture tap is exactly variant A's capture-site step, so B collapses into A and was stopped (no build).

START offsets: 351/351 filled, 0 null, PLANNED = root raw release 20 + SETTLE 74 + origin_cycles(leaf) -> 105..309. START follows
reset by >=82 cycles at every part and >=74 at every stage. Authority: planner J from the pre-legalization clock proof; reset relay
phase NOT RUN. Compiler adoption needs the fresh routed phase re-plan (--start-prev fixed point) reproducing this stage set.

Sim (sim_start.py, iverilog, ideal single clock): emitted local_start6 RTL (same topology/resets as final5, plus existing_port tags)
351/351 die START outputs rise exactly at the cycle derived independently from the JSON (diff 0). Scope: wiring/PAD/SETTLE/reset
binding, not phase/J. Not done here: placed-cell (packed.json) reach after BUF8 entry, fresh G1, GRT50 + related TT/FF STA.
