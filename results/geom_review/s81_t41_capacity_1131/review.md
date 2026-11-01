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
