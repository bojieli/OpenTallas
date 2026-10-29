# ECTL q3 legal native clock prototype

The unchanged 410-buffer/5490-sink native clock topology was evaluated at exact legal row/site coordinates using the same R7 NLDM/Elmore model, before build. Predicted TT mean252.72ps/window10.71ps and FF191.66ps/window12.77ps. Conversion of those frozen positions has zero displacement and zero new-new/new-original body overlaps.

Actual OpenROAD insertion, DPL and check_placement PASS: all17721 original instances retain exact master/origin/orientation, all410 new buffers match the frozen plan, zero displacement. Both SRAM bodies and447South face FFs remain fixed. Reviewed actual_dpl_clock_overlay.png (the q3_actual_dpl_clock_overlay.png filename) for one CTS/GRT50 prototype only, no DRT. Clock buffers follow perimeter FF banks and existing macro channels.

Actual CTS PASS; TT setup+153.37ps at unchanged833ps/60ps uncertainty. Explicit complete native tree uses core_infra_cts with zero CTS-open nets and report-only leaf affinity. No added command cycles. Final FF hold/related-pair skew/PG and clock-inclusive GRT50 remain pending, no SIGNED claim.

Own remote kit: intel1:/srv/opentallas-scratch2/claude/codex-kv-kits-1029c/q3_native_trial2
Original source checkpoint copied into original_3_place.{odb,sdc}; native inserted checkpoint stored separately. native_grt.log tracks running normal ORFS GRT, including clocks and normal5ps hold margin.

Prior failed evidence retained: first stale converter packed clock buffers at insufficient pitch (native_trial, not this candidate); initial CTS integration here omitted the wrapper after PRE_CTS replacement and TritonCTS attempted to alter a dont_touch planned driver (native_cts_missing_wrapper_FAIL.log). Restored explicit wrapper; exact same checked ODB succeeded. No clock constraint or physical-plan waiver.
