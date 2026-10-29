# Trial geometry reviews: S81 reach17 and QC node a0k10t

## S81 reach17 — PASS-COND for a trial GRT

Personally viewed all ten panels of the die owner's `results/codex_s81_2340/reach17.png`, against `/srv/opentallas-scratch/claude/codex-s81-2340/reach17/reach_plan.json`. This fixes all ten existing physical edges>405um, including the eight previously reported>450um, while preserving old endpoints/taps. Nine edges add2inverters; bk_sel adds4. Twenty-two newclockcells are0.024% of the tree. Planned maximum new hop262.764um. Seven feed paths bypass the454.5um-wide core by using a parallel channel~63um above it; bk_sel bypasses the652um square core on the right. New cells occupy channel sites rather than macro bodies; these physical blockage bypasses do not serve as timing-padding/meander balancing. Existing signal/pin/core locations stay fixed.

Condition before trial route: the emitted netlist preserves polarity with the even inverter chains and the newcellsite halo/overlap checks pass, as the die owner already planned. The actual routed TT/FF duty, slew, CA, and timing must be collected afterward; this review does not claim timing closure. No new gate, reset/data cycle, or interface change.

## QC ot_qwen_tile_node a0k10t — PASS-COND CTS/GRT trial only

Source codex/qc-a0-2340-1028@662af204d, APba7c5b18f1e2. Personally viewed the owner's actual `node_triton_place.png` and fresh independent `qcnode.png`, both show a contiguous, approximately uniform47.52x432um logic strip with the clock entry at(23.772,216), no macro wall or isolated logic sliver. Independent read-only geometry dump pid2697029 on epyc2 completed; no repeat GRT was launched because AP already owns the CTS/GRT trial.

Measured fill.3649, empty.1278,12102clock sinks, no unregistered ports, no collapsed chains, r2r240.84um/zero>405. Automated aspect9.09 is the already accepted plan slot. Partial-face E515pins on27% of face has4.3pins/um, peak5.3/um, so this is a source/sink window rather than inaccessible congestion.

The apparent pin-regp90 failure42.07um/max43.97 is the existing one-station feedthrough exception, not a new omitted register. Checked actual kit `ft_stations.txt`: pair t_d t_out and pair t_vd t_vout. The shared station FF must remain near the E input; moving it to the W output would break the input-side registration. For the five worst output bits507/436/18/39/171, Einput→that same FF distance is5.787..6.387um. The opposite-face registered hop is the47.52um slot width, safely within405. This is the same mechanism already reviewed on a0k3/a0k8 (per owner), and no extra register or cycle is proposed.

Center-clock farthest sink230.35um is a pre-CTS structural estimate; TritonCTS has yet to build the tree. PASS-COND scope is CTS/GRT trial only. Detailed route still needs the existing actual-clock/timing/GRT gates and review; no signoff claim is made.
