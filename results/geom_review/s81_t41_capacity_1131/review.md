# T41 local ring capacity: two zero-cycle prototypes

LOOK PASS-COND for two prototype band envelopes. No canonical plan adoption or new P&R has occurred. Both avoid every current other band, FT bit/register footprint, fixed reset/control box, macro and declared clock reservation. Only `slice_station__t41` / instance `s_0N_x03` / band `ft2_i` changes; all bus windows, clock/reset sites/topology, ring width/roles, RTL and cycles stay equal. The source utility materializes a requested variant and matching optional sidecar copies; it never edits its input plan.

Original actual attempt4 stays FAIL: GRT overflow4750, column metric1.071, r2r393.31um with0 captures beyond405. Source auto_geom.json is retained. Reported global routing usage8.05% does not remove the local routing failure. Placement log:2677 ring FFs and8999 ring logic cells; normal pinslot placed2607 FFs in21 columns /38.88um-deep strip, with70 FFs by the band cursor. The old ring bounding box is approximatelyx78..106/y1174..1211. This is a local concentration problem; normal global density/clock/repair settings are unchanged.

| variant | envelope (um) | area (um²) | original reserve ratio | maximum pin hop (um) | fixed obstacle hits |
|---|---|---:|---:|---:|---:|
| original |79.7,1098.66,105.62,1209.6|2875.565|1.091|172.226| baseline |
| A |79.7,1098.66,183.38,1152.66|5598.720|2.124|249.986|0|
| B |79.7,1098.66,228.828,1179|11980.944|4.545|295.434|0|

Original reserve remains2636.064um²; larger boxes provide capacity, without extra flops/stages. Existing ring_place=ff and standard pinslot/automatic spread are retained. The wider band gives the existing column placer more columns; it is not a changed cell-spacing or routing-capacity threshold.

Tradeoff: A's upper edge is74.22um from the N face, B47.88um. Thus lower-metal congestion relief must be checked together with actual input-to-register locality and TT/FF timing. The footprint alone is not a new pin_reg or timing pass. Global p90 was24.66/max116.33 on the original actual placement; normal guards remain required. A/B actual placement, GRT and timing are unmeasured.

The leftward versions startingx17.28 are INVALID: they overlap real FT/other-band sites (4–6 hits). Faceward versions endingy1209.6 overlap an existing upper band and reset box. They were rejected before P&R. Two additional collision-free geometry suggestions were reported to S81 owner for locality comparison (not new jobs): A'=[60.48,1112.284,183.38,1166.016], B'=[79.7,1098.66,196.56,1179]. No pinslot/window/clock/cycle override is proposed.

Original evidence: intel1:/srv/opentallas-scratch2/claude/kit-wave/s81/e8cbe5f6c70/items/slice_station__t41/attempt_4/. New candidate source is based on canonical mainb1a212543. Hold CTS/route until actual prototype placement LOOK and normal gates; original failure remains protected.

## Selected actual prototype pair

S81 owner independently LOOKed the original A/B render and selected the closer variants below for GEN/PLACE-only prototype work once the shared b1 portable source/bind bundle is ready. Original A/B remain history, with no jobs launched.

| selected variant | envelope (um) | area (um²) | reserve ratio | maximum hop (um) | N-face offset (um) |
|---|---|---:|---:|---:|---:|
| Anear |60.48,1112.284,183.38,1166.016|6603.663|2.505|236.362|60.864|
| Bnear |79.7,1098.66,196.56,1179|9388.532|3.562|263.166|47.880|

Both retain0 actual obstacle hits and the same one-type/one-instance/zero-cycle scope. The selected render was personally LOOKed: Anear stops below the upper-left band with a clear gap, Bnear remains below the upper-right band; neither covers the red reset/control boxes or existing band/FT sites. No density, pin window, clock, frame or RTL override is introduced. No canonical change or route before actual placement LOOK and GRT0. Normal pin-register locality and timing are still unmeasured.

Independent second LOOK (S81 parent, 2026-11-01 12:49 PST): selected_candidates.png shows Anear in the clear lower-left pocket beneath the existing cyan rings, Bnear in the clear pocket below the upper-right rings. Both avoid shown FT/fixed control sites and improve the N-face offset. PASS-COND for private GEN/PLACE prototypes only; normal pin-register locality, actual GRT0, TT/FF and route gates remain required. Prototype controllers use the read-only portable b1 source/bind bundle on Intel2, with private plan/sidecar/spec/output directories. No canonical adoption.

## Corrected exact GEN kit LOOK, 13:40 PST

Personally viewed Anear_kit_plan.png and Bnear_kit_plan.png generated from the actual corrected GEN pin manifests (15,262 pins), budget clock metadata (78 unchanged explicit taps) and the corresponding private candidate physical reservations. PASS-COND for normal BUILD and PLACE-only prototypes. Actual N-face ft2_i pins remain on the published window; the expanded green band occupies its reviewed clear NW pocket, avoids red fixed reset/control boxes and leaves the FT/interior rows unchanged. Anear has the narrower gap beside the W landing bands; Bnear leaves a wider W-side pocket and a shorter N-face offset. Local routing density and pin-register locality remain real risks, to be judged on actual placed geometry and GRT, not waived. No clock/pin/core/RTL/cycle changes. No CTS/route and no canonical adoption; actual placed LOOK precedes any GRT continuation.

The original flagless GENs continue unchanged but their parent controllers are explicitly held (SIGSTOP only local controller bash 2695538/2695871) to prevent duplicate BUILD/PLACE. Corrected R2 source is separate; the bound+landing emitter comparison passed all83 kit files byte-identical after output-dir normalization. The frozen explicit-tap report is now correct (actual78 endpoints, not a new k-medians discovery). Anear physical work uses an independent copy of the passed optimized kit, preserving the benchmark's immutable comparison artifacts. Bnear corrected GEN completed normally. Controllers collect both BUILD checks then stop at PLACE and generate a grt=false review image; no auto CTS/route/GRT.


## Actual placed pair, 15:0x PST

Both corrected normal BUILD/preflight passed and PLACE completed: Intel2 units oth-ubuntu-2634281-1793569379 (Anear,14:54:55) and oth-ubuntu-2669325-1793569421 (Bnear,14:56:34). Actual images personally LOOKed at /home/ubuntu/coord/tmp/t41_actual_1101/{Anear,Bnear}.png; protected raw geometry is codex-s81-bound-landing-r2-1131/{Anear,Bnear}_corrected/placed_geom on Intel2. NW captures remain near the declared N window without long unregistered paths; Anear max pin-register135.36um, Bnear135.95um, both p90=24.69um/unregistered0. Actual r2r393.15/392.55um, over405 captures0; pin density4.4/um; channel estimate0.569/0.570.

Verdict remains FAIL/HELD for normal closure, no canonical adoption or CTS/route. Generic check returned RC1: sparse full-outline fill2.04%/empty83.6% or83.4%, existing E/W partial-face2636pins on50% at4.3/um, and actual pre-CTS nearest assignment overload clk_t27=1580/1586 against1500. Other grid taps <=1388, no empty grid tap. The clk_t27 hotspot is away from the modified NW band; clock positions were deliberately unchanged. The actual config already exports OT_TAP_MAX_SINKS=1500, and the existing PRE_CTS hook applies a bounded capacity-constrained assignment after nearest split, preserving FT groups/followers. The generic pre-CTS checker models nearest split only. Therefore these1580/1586 predictions do not yet prove a new tap-source event is needed: actual post-hook counts remain unmeasured, and the normal1500 rule remains held. Four fixed FT input roots carry2077 sinks each and are not counted by the grid-tap test. Nearest-entry reach188.63um;1341um own root-to-sink is pre-CTS INFO, not a balanced-tree claim. Raw check omitted parent/template rules_args, hence outline/macros/pin-table/tap-set NA. GRT was deliberately not run. A scoped congestion-only GRT experiment may diagnose whether the band enlargement solves the original4750-overflow hotspot, but these remaining failures must stay visible; it cannot qualify the prototype for release.


Existing pre-CTS hook actual ownership probe (unit2752112-1793576567) PASS bothvariants, noCTS/GRT/STA: maxgridload1500, zeroemptytaps, maxownport→sink189.579/189.039um. Original instance geometry/data/reset and inboundforwarded ownership unchanged;8normal declaredforwardBUFFs added/0oldremoved and all8exports have literalexpectedtap source. The prior nearest-only>1500 prediction is resolved by the existing cap pass without newtap positions/topology rules. ActualGROUP_RE is OFF.44/89(A)/43/89(B) FTstages spanmultipletaps; finalstage ft0_o148/1105FF differfrom exportedclk_t8, ft10_o52/513(A)/51/513(B) differfromclk_t68, ft12_o101/277(A)/102/277(B) differfromclk_t69. Fiveotherexports singleowner. These measured existing-hook splits require source-clock/timing interpretation before claimingforwarded-group qualification; no inferredautomaticgroupoverride. Original2GB audit exit137preserved asresourcefailure; unstartedR2cancelled for localTclregexquoting beforefreshR3actual4GBpass. PosthookODBprotected separately; original3_place unchanged. Canonicaladoption/CTS/GRT remainheld pendingS81review.
