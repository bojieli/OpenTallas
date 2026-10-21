# Actual s4 gate, separate bank-distance replay and review

Gate WARN0fail, GRT overflow0. TT diagnostic setup+91.72ps/hold+48.60ps; TT/FF insertion251.0/207.1ps and pin-flop spreads35.0/28.3ps (SS spread46.5ps). Mandatory actual mapped native census PASS max16;320FF+4SRAM+16keptselectcopies survive, depth91.7ps. Independent pre-gate transitive census zero>32 is preserved beside exact12k5.050 whole-word PASS and bankmutantFAIL137. No imported ASR functional model.

Both actual PNGs personally viewed: macros2x2 at x43.2/172.8,y43.2/129.6,43.2lattice;45.3um continuous channel, full-width N capture band, centered clock. W/E512data faces now flank their SRAM pairs. Actual1318pin geometries all accessible/ontrack/in-outline, max sliding-window pin density2.52/um. Aspect1.4, outline302.4x216um, fill24% is pin/macro constrained.

BEFORE submitting, separately replayed the exact canonical fp_margin_lint on the immutable gate3_2_place_iop.odb via read-only native OpenDB dump (source hashes saved). Full PASS with zero fails/warns; bank_far0, slivers0, worstchannel0.134, util25.06%. This directly checks the predecessor failure mechanism: s3 bank2/3 distances173.1/167.3um>100 are preserved as failed and were not waived or rerouted.

Eight checks: (1) registered boundary PASS SRAM write captures/select captures/outputFF, reset N/A; (2) planned reach PASS<405um, physical full-route audit owed; (3) native32 PASS actual max16 + independent transitive0>32; (4) storage PASS4SRAM/320FF; (5) macrogrid/continuousband PASS; (6) fullface pins PASS<=6/um, aspect1.4, pin-bound area; (7) center clock PASS35.0/28.3ps, io hold margin30ps; (8) static schedule PASS0addeddata/reset/warmupedges and exact word {tw_hi,tw_lo}. Parent explicit bindings compiled separately for flat/D4/D8.

No final route/SSsetup/FFhold/nativePG/clock/reach closure is claimed. No kit source or README changed after the gate; this review packet is separate evidence.
