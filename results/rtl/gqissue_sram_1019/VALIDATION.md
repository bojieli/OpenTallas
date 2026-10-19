# Validation scope

- Historical r4 source manifest/checklist/logs preserve the paused source. Its >9kb/quantiser flop storage was rejected; its old KQ seam is historical only.
- `aq_sram_exact_pass.log` / `aq_sram_mut_slot_fail.log`: initial SRAM offset8 variant, no read-capture stage, AQ13 golden exact and wrong-slot negative.
- `mainseam_positive_precapture.log`: current-main registered KQ+2/read-share/landing fault-face retained; only r4 issue module transplanted. Positive rows6/loops2/2644VMwords, faults4 and AQ13 pass on5.050. Eight-mutant regression continues (m6 land face, m7 SRAM slot, kq1 share). It uses the offset8 component contract.
- `capture_exact_pass.log` / `capture_mut_slot_fail.log`: final implementation has full-cycle macro-local read capture and read-offset7; AQ13 exact1024blocks/32768elements/lat13/II1/warmreset PASS; wrong slot fails block3. This component proof establishes identical latency/numerics against the same golden while protecting S9 arithmetic from SRAM SSclkq455.32ps. The main-seam integration stays applicable by this unchanged component contract.
- Root must inspect fresh gate PNGs/checklist and the completed eight-mutant integration before adoption. No routing closure is claimed here.
