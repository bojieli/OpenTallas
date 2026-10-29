# HEAD endpoint/credit native cuts — PREP HOLD

Viewed `results/head_lep_next_1029/native_geometry/native_geometry.png` after
adding all2,607 endpoint and2,261 credit pins. Endpoint328.32×362.88; credit
112.32×207.36. Actual unchanged36/9 SRAM masters have4.32um halos and clear
core margins/channels. Endpoint FIFO array lies toward gearbox W, replay array
toward credit E; opposing MY/R0 macro read faces point toward control channel.

Exact gearbox E→endpoint W per-original-bit/layer positions are preserved with
GB relative y60.48, an8.64multiple that preserves M4/M6 phases. Endpoint↔credit
1,112bits preserve original data/last/control correspondence with credit
relative y77.76. No cycle or pin is dropped. Native credit parent-facing face
retains all1,110bits. Distinct original reset leaves occupy N; clock has a clear
central-channel M5 entry. These are preparation positions, subject to actual
parent reset-tree and clock/tap composition.

Verdict PREP HOLD. Macro/pin geometry is coherent for the next register model.
This is not a G1 PASS or route admission. Clock tap islands, PDN, exact boundary
register placement and combinational channel census remain required. Endpoint
outline bound exceeds405um, so registered dataflow reach must be demonstrated;
credit whole-outline core bound302.4um is below405um. The fullLEP trial7 density
failure is not overwritten. No P&R or STA launched for these candidates.
