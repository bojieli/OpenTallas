# Wide PV shared-generator slice candidate

Source physical event64b502e407, geometry-only PV projection of its exact plan, all3 exact event pinviews and committed current mesh. Source plan compressed bytes retained. Canonical plan.clock.mesh.core_islands omits PVjoin:0joinpushdowns after160parentclock cells resited outside joins. Shared tools/die_plan/kv_core_slice.py and renderer run unchanged from own pinned source9e715bd6d7. Outputs are MODEL UNCHECKED, no measured timing claim or new RTL/cycle change.

Actual shared result: centre entry129.6,86.4; islands64.8/194.4,86.4; grid2x1, leafreach151.2, no conflicts; model221.7TT before one designedBUFx4 trunk,245.6TT/197.5FF after trunk. Targets remain250TT/202.5FF. CLOCK-KV static PASS-COND accepts this geometry/model provided actual native pins/spacing pass and exact resetdelta folded into oneevent.

Actual generator moves resetM5 x130.008->129.960 (clock129.624 unchanged),64typedef instances. No ad-hoc postedit. Sharedcheck_taps_cores on all295744PVpins PASS0offtrack/0errors; clk/reset shapes unchanged and centrespacing.336um. reset_pin_delta.json records exact pertype/inst/view old/new,0cycles. Derived3pinviews and slice are immutable candidate inputs. Shared-rendered PNG personally viewed: centreentry and symmetricquarter islands/trunks fit body,0diepushdowns. Staticacceptance does not certify physicalCTS or timing.

Trial kit preparation may proceed after staticowner acceptance. Route held until actual new placed pin/reach/image review and clock implementation; actual CTS/related-STA signoff owed. Full event G0C must fold resetdelta and rerun once; this focusedpincheck is not that full verdict. `input/pd/die_plan.json` is a PV-onlyprojection, never a canonical replacement for the full event plan.
