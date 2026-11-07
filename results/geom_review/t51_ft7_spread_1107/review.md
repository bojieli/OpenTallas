# T51 FT7 ring spread actual PLACE

PLACE completed rc0 at 2026-11-07 12:46:57 PST, E6 unit oth-ubuntu-4056236-1794083163. Exact3_place checkpoint203387630bytes. Proof122e6be00c57e48e0ec9cf80730b69f44752f8399c122325d4fab94ae8cf6dfb reused and checked after refreshed synthesis. Actualdensity/floorplan images personally viewed; this is PLACE, not GRT/route/signoff.

Density peak0.658 with ZERO96x96bins above0.7, compared with original PLACE0.711/3bins. Earlier originalCTS peak0.761 is a later-stage comparison still owed; this result does not establish postCTS density. Die794.88x1209.6um,0macros,11509pins,14993.5um²stdarea/1.6%fill, outline retained for native parent slot and ports. The north band is visibly broader with no >.7clump; source poses/pins/RTL/cycles otherwise fixed.

Read-only wire measurement:65832single-driverBUF/INV two-pinSIGNAL nets; median91.28,p90108.682,p99117.021,max121.444um endpointManhattan span.27>120um/0>150um legalization tails. These are neither routed lengths nor full reg-to-reg paths; no DRV closure claimed. Actualclass120umstage objective is preserved. M5-M6 globalcapacity estimate and lower-layer pin via-access risk remain in earlier form review; no GRT release from this result.

SMELLS:8 cleared atPLACE.3/9 no macro obstruction(0macros).5/10 buffered-wire subset measured above, full timing/routing still owed.1/2/6/7 pin-to-register/flightline/access census remains conditional; movedringFF reach can increase≤26.46um, no newpin-reach waiver.4 actualclocktree/arrival is not measured by this PLACEview; regularredvertical lines are PGspecial wires, not proof of routedclock geometry. Currentrenderer omitted optional layout_review.tcl so pinreg/root arrays are empty; futureCTSreview will include that helper. No independentPGconnectivity claim.

PASS-COND for CTS-only. Existingnonportwrapper launched normal48G16T E6 unit oth-ubuntu-677827-1794084858/container klegacy-t51e_m5_120_ft7spread_vB-678437, proofreused. No GRT/route attached. Next: actualCTSdensity/clock+TT/FFpostCTSgate review before routing decision.
