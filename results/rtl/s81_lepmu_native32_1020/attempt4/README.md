# Revision4 native32 and production campaign receipts

Pinned RTL9a4faab57. A/H native mapped non-clock maximum32, resets included, refusedchecks empty. A18128FF,H19729FF,20SRAM each. No new static edge. Plain-source native area A7693.76394/H8441.17848um2 from actual used RVT TT cell-library areas; $scopeinfo ignored and20realSRAM counted separately. Physical gate synthesis may differ by allowed cell set. Native source was packaged before helper sync4005eaa52; ot_keep_regs.tcl/ot_pin_regs.tcl are byte-identical across that sync.

Both full production campaigns PASS: all validcases and all expected mutant regexes matched. Captured buildlogs report Verilator5.050; rawcase outputs and campaign verdicts preserved. Scripts reproduce admitted synth-only mapping and campaigns, no layout gate in these receipts. Preserve earlier failedcensus attempts as structural history.
