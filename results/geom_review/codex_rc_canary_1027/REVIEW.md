# Shared-flow diagnostic canary review, 2026-10-27

Candidate: RC source 7944d7dae/evidence2bbe885e4, placement repair37d9b8a28, preflightb56b0b55be (includes FF-bound9529b56ff0), centre-track snap5b2b94251f.

Viewed s81.png, s81_head.png, qwen_compute.png, qwen_kvsys.png (reset_tree.render on exact candidate plans), and the retained KV-KITS-1 b51 actual placement image intel2:/srv/opentallas-scratch2/claude/kv-kits-1-1027/render/kv3_io_ft_v1.place.png. Prior independent canary-reference review history remains in coord/lanes/GEOM-REVIEW.md; these are unchanged reference shapes used only to measure shared-flow regression.

The S81/KV relay grids are regular and below405um hop reach (379.1/345.6um); QC has an irregular central fanout corresponding to explicit type taps (max374.4um). Head turn is a narrow tall reference with sparse taps: inherited structural/insertion failures remain; no closure claim or design adoption. KV actual placement has straight two-band east-west data flow, aligned boundary pins, regular station/repeater columns, no macros or blocked channels. The candidate changes placement buffering, so these plan pictures are not an actual-placement approval.

Verdict: PASS-COND for generation and placement-only diagnostic canaries. Every candidate placement must be dumped, rendered and viewed before CTS/global/detail route. A failing actual placement is held for diagnosis; original failed reference verdicts are retained. This review grants no physical sign-off and no mass-route release.

## HBM SRAM actual placement, 08:28 PDT

Viewed hbm_sram.actual_place.png from candidate ab3ae7c3a 3_place.odb. One large central SRAM leaves continuous standard-cell strips (about17um south/east,28um north,46um west), with no overlapping cells or macro wall. Registered pins remain on the east/south faces and clock entries on the rim. Buffers/logic spread around the macro; no newly created strip is cut off. PG binder reports36574 supply terminals,0 open. Shared60um repair adds1112 cells (17175->18287). The four inherited clock entry sites remain the reference geometry; insertion/timing remain measured gates. Verdict PASS-COND for one diagnostic canary continuation through CTS/route, preserving the old insertion/design failures and requiring final native timing/DRV checks.

## QC actual placement, 08:31 PDT

Viewed qwen_compute.actual_place.png from candidate ab3ae7c3a coll_ftm 3_place.odb. Four station bands align east-west, and the intervening parallel repeater rows leave open vertical access; no macros, overlaps or enclosed channels. Clock entries remain on the reference's station lattice. The main data/pin bands stay aligned. PG348168terms/0open. Shared60um repair126648->174084cells (+47436,37.5%): material buffer cost, to be reported with the timing result; outline remains sparse. Verdict PASS-COND for one diagnostic CTS/route continuation. This does not cure or waive the inherited control-input hold failure.

## HEAD actual placement, 08:33 PDT

Viewed s81_head.actual_place.png from candidate ab3ae7c3a hd_turn_a3_place.odb. Left and south pin bands connect through diagonal turn/station rows, with open routing area and no macro wall. Repeaters follow the turns; clock entries remain the three inherited central sites (the northmost region is mostly empty). No new placement overlap/channel blockage. PG55740terms/0open. Shared60um repair24037->27870cells (+3833,15.9%). Verdict PASS-COND for one diagnostic CTS/route continuation; the known reference clock-insertion/FT-setup failures remain gates.

## KV type actual placement, 08:38 PDT

Viewed qwen_kvsys.actual_place.png from ab3ae7c3a kv3_io_ft3_place.odb. Two straight east-west feedthrough bands have aligned face/station columns and more closely spaced parallel repeater columns; open vertical access remains, no macros/walls or pin crossings. The12tap grid is regular. PG273790terms/0open. Shared60um repair121997->136895cells (+14898,12.2%). Verdict PASS-COND for one diagnostic CTS/route continuation; the ruled80ps clock-window/IO-hold model is unchanged and native hold/insertion gates remain active.

## S81 actual placement, 08:52 PDT

Viewed s81.actual_place.png from ab3ae7c3a slice_station__t12 3_place.odb. North/south pin groups align with two vertical station/repeater strips; remaining routing area and clock-grid access are open, with no macros/new walls or overlaps.16 clock entries remain on the reference lattice. PG315024terms/0open; shared60um repair146766->157512cells (+10746). Verdict PASS-COND for one diagnostic CTS/route continuation, retaining the known reference insertion/hold checks.
