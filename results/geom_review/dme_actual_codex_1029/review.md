# bk_sel physical DME coupon review

Picture personally viewed: body_clock.png. Clock cells remain in the
channels and along the macro shorelines; the large macro roofs have no
clock-cell bodies on them. Leaves land beside their51 plan clock pins.
The left/right macro banks use local branches and a channel trunk with
intermediate native cells. No unregistered clock hop exceeds405um
(actual maximum391.5). Some branches share narrow inter-macro channels;
the clock-only routing trial must measure that capacity and routed delay.

The exact246 physical primitives have0 body overlaps,0 macro/PHY halo
hits,0 off-grid sites (.054um site / .54um R0 row pitch). All51 taps have
true polarity. Final costs are recomputed from the same frozen physical
homes that are exported. PDN and data pins are unchanged in this coupon;
there is no whole-die PG, signal or release claim.

Verdict: PASS-COND for ONE clock-only coupon GRT/STA trial. The frozen
homes must remain unchanged; any body overlay move invalidates the model
and requires replanning/repricing before use. Baseline and first point-
only candidates retain their12/20 body-overlap FAIL records.

Independent GEOM reviewer /root/geom also personally viewed the image
and returned PASS-COND one clock-only GRT trial. Explicit planned clock
construction cost:9 elongated DME legs,2526.6um added wire,25 buffers
reported by the selected-tree statistics. These are plan-computed before
measurement; no post-route residual rescue was applied. The actual trial
must use the shared inverter calibration and report TT/FF/CPPR/CA.
