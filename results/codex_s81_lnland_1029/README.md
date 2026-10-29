Natural LP LN one-clock master, 2026-10-29

Prepared opt-in master ot_s81_mu72_lnland_nst_1ck preserves the exact current NST ports except redundant ck_n. All four exact bound-parent instances tie ck_k=ck_n=clk; evidence/actual_clock_aliases.json enforces this before the miter runs. Independent resets remain independent. Added latency:0cycles. No parent selects this master yet.

Full Verilator5.050 strict WIDTH/SELRANGE lockstep:4096cycles,4527296bit-checks PASS; removed-landing mutant4064 mismatching cycles and tied-reset mutant3102. Common reader comparison requires shared c5f63a4c8 (full-width semantic SAT + mutant), already proved separately. The build used SYNTHESIS; the six component source files have no other functional preprocessor choices.

Standalone Yosys mapped census:39666std cells,10486DFF,4881.384um². Exact full parent census556766 includes four retained39665-cell LN instances. Hardening those four predicts398106 residual parent cells. The extra standalone cell is boundary optimization, not a new RTL stage. No timing/geometry signoff claimed.

112.32um square candidate,45.4% estimated fill after4.32um core margin;2231unique pins, ck_k centre56.172,56.16 M5. Actual legacy core lattice0.012um offset; PG-aware schema.spread allocation max59pins/10um,<=30.7% track occupancy. W K-input556 / S K-output558 / E N-input558 / N N-output556. Parent proposes allR180 and owns exact four-lot/relay/FT obstacle model. Both resets are timed ports.

Kit PREPARED on intel2:/srv/opentallas-scratch2/claude/codex-s81-lnland-1029/kits/ot_s81_mu72_lnland_nst_1ck_ready1029, hash09909b8090025135. Generation0; NO PLACE. Mandatory actual placed sink-family/tree model, parent lot event and actual geometry still required before CTS/GRT/STA. Candidate.png personally viewed, review.txt records findings.

Earlier preparation failures are preserved under intel2:codex-s81-lnland-1029/genkit*.log: undeclared interior clock whitelist (shared af5ba0b27+562c58ae6), missing own sparse source directory, wrong die-vs-core track phase, metadata pins path. Corrected recipe does not modify source behavior except the separately proved common width fix. Earlier Icarus frontend and strict-width failures preserved on intel1:codex-s81-lnland-1029/proof*/. Actual full bench at proof_vlt_width, standalone synth at synth_1ck.

Private kit_plan.json is a source-master generator vehicle, not a die-plan adoption. Root must take only the candidate commit, not this branch ancestry. Parent owner supplies the canonical plan event. Kit source needs shared declared-clock generator fixes and width fix; no clock-name prefix waiver.
