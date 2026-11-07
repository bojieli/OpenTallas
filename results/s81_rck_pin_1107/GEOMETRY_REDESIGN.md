# RCK t16 private TX PIN/compact successor — GEOMETRY / REDESIGN

Reviewed 2026-11-07 07:35 PST. Planned image `rck_tx_planned_geometry.png` was viewed; it is not a new placed result. Existing t16 grouped CTS remains FAIL (actual FF gate -596.13 ps /3956). Native parent pins, clock-tap positions and 180 ps source window are unchanged. No POR adoption, CTS/GRT authorization, or RX/FT closure claim.

The failed form aliases an eastern input BIN boundary (centroid2478.5,402) to ENC (2178.8,640.6), forcing 7500 capture sinks behind a 26-stage clock tree while CLAND launches from a 9-stage tree. BIN is not the output face. Existing FT strays are local to the clock root, not a geometric span driver. Capture insertion779 vs launch171ps is a topology failure, not balance pads.

New form moves BIN into 2770..2874 x105..265 near CLAND, separates its tap alias from ENC, and owns the actual encoder registered combinational cone in 2065..2265 x466..666 around fixed clk_t34(2164.832,566.048). Read-only backwards fan-in walk:67048cells/10564.53678um², or26.41% of40,000um². Prefix-only FF area would undercount anonymous ABC gates and is not used. Encoder final p_d is posed near y650. The compact fence is conditional on no conflicting prior group; conflicts must be reported and reviewed.

Three coherent input data/valid/reset-calendar stages bridge BIN to ENC. Existing chain_even positions these stages on their actual per-bit paths. At the worst proposed box corners, input reach/4 <351um. TXL changes2→7, with seven output relay rows; the post-detail helper clamps cells below945.24um. Worst proposed output path from ENC x2265,y650 to PMA far pin x338.856,y1093.056 has final clamped stub<389um. RX PMA OBS are M1–M5; M6/M7 overpass is legal. These are planning estimates, not measured new PLACE paths. Density, legalization displacement, actual chain association/hops, macro pin access and every new placed image must be reviewed before CTS/GRT.

Absolute model ledger:
- Against current actual COL TXL2/POR:TX+8=3 coherent input stages+(7−2) output stages;6.664ns at833ps. RX inherits opt-in RM_STAGED+1, which is still unadopted and must not be silently called current POR.
- Against untried vF COL TXL2 with RM_STAGED:TX+8 by the same equation;RX+0. Existing vF has no completed new physical qualification.
- Encoder reset release and TX fault/FEC calendar shift+3edges, separately from mission TX+8. Parent HOLD_EDGES64 contract required; same throughput, no backpressure change.
- Existing RCK4 SERDES_RST_COPIES is in unused ot_pdie_serdes, not actual COL; do not claim that reset fix applies.

Proof: earlier N3+PAD5 experiment passed2099 checks,0errors,2031mutant mismatches, including64-edge warm reset and valid gaps. Final N3+PAD7 actual-ENC proof also passed2099checks/0errors/2031mutant mismatches, including warm reset/valid gaps, with PIN_TX_ADDED=8 and RESET_RELEASE_ADDED=3. See final_pad7_run.log and exact input manifest. The +6 experiment is not substituted for this final +8 proof. Mapped/routed LEC remains future work. After final proof, one actual private t16 PLACE pilot only; no unchanged retry of existing grouped/vF forms.

S81-RCK-5 2026-11-07: pilot PLACE failed DPL-0033 (2011 cells stuck on fence edges) and pilot LEC UNPROVEN (duplicate PMA modules, not a differ). On copies of the failed DB: keeping fences, re-legalize passed but improve_placement or mirroring broke 131 region members; fences released, one pass, 2.3 um max displacement, checks clean. vG therefore uses the fences for global place only and strips the behavioural PMA modules from the kit column file. Logic, PIN CYCLES and bench unchanged. No route result yet.
