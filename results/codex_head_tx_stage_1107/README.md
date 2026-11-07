# TX chunk capture reform, candidate only
Baseline93c061c396c; branch codex/head-tx-stage-1107. Old TX thirdlateECO
eco_dh80 remains stopped; this is fresh RTL, not an ECO or unchanged retry.

The opt-in CH_STAGE works with LA2/FF1. The TX wrapper enables it through
parameterCH_STAGE=1 or defineOT_HEAD_TX_CH_STAGE; default0 is unchanged.
The shared chunk mux now captures one520b kept mid bank before four cq copies.
Flagmid preserves the old synchronous-reset semantics, then delays f0v/fv
one edge. Explicit delayed par_load and word-select banks align the feedback
parity state and output selection. Beatd8 and output header delay align data.
p_v/fault are explicit one-edge delays, including output-visible reset edges.
Input acceptance and sustained output interval remain one word per cycle.
PMA data/fault outputs add1PINcycle, declared in added_rx_clk_PIN_cycles.json.
No die plan/compiler/token/POR adoption is made; the private kit is DO_NOT_COUNT.

Actual old routed placement/clocks/congestion images were viewed. Four native
nets cause all9TT/8FFslew failures: net11430 control reaches~170um, four Dloads;
three shared ch_n data nets drive four copies spanning58–73x43–44um. Loads
are32–34fF despitefanout4. No macro wall; DRC0; pairskew63TT/60FFps.
See TX_REDESIGN.md for measured details, with its original recommendation.
The IMPLEMENTED form uses explicit delay banks instead of incrementing
multiple flag-array indices; this preserves reset boundaries exactly.

The new-state anchor file tx_ch_stage_place.tcl accompanies changedRTL:
only three measured data mid bits and four control mid bits are homed at the
midpoints of the measured failing reaches. Existing pin anchors remain.
The existing PRE_DETAIL_PLACE release handles these seven FIRM anchors.
new_stage_plan.png is the planned anchor view, inspected before PLACE;
it is NOT a placed result. Actual PLACE review remains required.

Proof reproduction (use your OWN clone, never central):
  python3 -I prepare_proof.py --repo /your/clone --out /scratch/isolated/proof
  ot-run --mem8 --threads4 --dir /scratch/isolated/proof --stage /scratch/isolated/proof -- bash /scratch/isolated/proof/run_sims.sh
The preparation reads unchanged dependencies and old encoder from93c061c396c
bygitshow, and candidate encoder from the working source. Bench is one full
encoder against the old encoder: default-off samecycle; opt-in delayed1cycle.
Continuous frames cross seqwrap, missingbeats raisefault, reset is exercised
at all10phase offsets. It compares p_v/fault each cycle and p_d whenevervalid.
CH_MUT1/2/3/5/6 are non-equivalent controls. CH_MUT4 bypasses output header
delay; classify separately if equivalent under framed timing, never claimcaught.
No simulation substitutes for kitLEC, setupTT/holdFF, DRV/DRC or finalsignoff.
No objects/binaries/corefiles are part of this source change.
