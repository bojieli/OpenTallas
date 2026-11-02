# HBM lattice contact repair PREP

Verdict: PASS-COND for six-type geometry proposal; no P&R, STA, SIGNED or die qualification.

Viewed `review.png`: q_b000 and q_b010 keep their data columns and neighbouring FT streets; q_su01 retains its lower common bus corridor. Clock contacts occupy actual PG-safe M7/M6 tracks with macro halos. No source/RTL/pin-profile/outline/count/mission-cycle change. PDN continuity and clock/source/START composition require the full current parent event.

The former 161 off-lattice placements cannot be accepted as origins. For the six types in this packet, the intended source pose differs from an allowed lattice pose by 2.16um. Each repaired pose uses a declared +/-2.112um track offset (33 64nm pitches, strictly below the 2.16um schema limit). The resulting body is only 48nm from the intended pose. Actual early-clock contacts follow that body; the original native view/profile remains independent.

Production clock legalization and exact nearest+capacity assignment pass at all original named taps: q_b000 153; q_b010 245; q_su01 167; physical variants 153,245,166. Every tap is nonempty, load<=1500 and radius<=220um. Actual FT cell/body collision census is zero for all six, with every original FT bit site retained. The clock and reset/START source still require coherent parent regeneration; these are plan inputs, not timing evidence.

Independent review rejected the earlier q_b101 horizontal-bay fragment because moved bodies overlapped 673/2195 actual FT cells. That failed candidate remains outside this six-type patch. Its same-stage actual-input/output repair is running separately. Root widening with minimum x projections produced 9975 duplicate FT sites and remains FAIL despite its clock-only pass. Neither failed candidate is adopted here.

Apply the keyed patch only against its listed old field values, then run current parent G0/G0C and actual pin/sink/native-source gates. Clock phase/load timing must be rebuilt; no old timing claim carries over. No cycles were added.
