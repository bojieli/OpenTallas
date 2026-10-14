# Engram reset-domain diagnostic: not qualified

Source `eb196b4b71c102199ec2f8f7e209979f5ad558ed`, immutable remote snapshot `reset3`.
Actual CTS completed. Sixteen retained reset DFFs, two per hard child, use exactly that child clock net. DFFs lie 3.2–6.4 um from their reset pin. Exact software source at `7c6422212` passed five positive scenarios and all five negatives; separate earlydone failed as required. That source has identical RTL to this physical hook correction.

This is not a route or release gate. Raw saved SDC uses setup123; strict probes use setup150 or conservative210 and H1 hold100. Uniform probe uncertainty is conservative on external IO that already contains a150ps arrival allowance: only the intertile pair table proves the stated same-level/cross-level budget. External reset must use its actual source clock, not the scalar data virtual clock.

At minimum intertile setup150, WIN->SINK is -26.4ps and SINK->WIN -78.8ps: their -105.2ps cycle deficit cannot be fixed with a clock phase shift. PB1->PB0 is -70.6ps. Raw reset-input recovery is negative (worst -165.1ps) and FF H100 includes negative removal/hold. All are retained without waivers. The legacy gate_report checks spread/slew only and must not qualify these paths.

`reset_corrected_*` selects sequential QN/D and RESETN pins, excluding anonymous reset-input inverter outputs from the stage label. The PB2 stage remains slow: stage_expanded shows a far anonymous mapped inverter between near-pin DFFs, QN208ps + wire187 + INV209 + wire168. Subsequent source places the entire local inversion/transport cone, not only HDL-named DFFs. No original snapshot or source was patched.

`pairs_*` includes three-corner raw/strict full-clock paths. `ckp_*`, `place_probe.out` and topology lines preserve physical evidence. `gate.json`, bench.log and neg.log are the earlier reset-domain functional proof, not the later status-pipeline proof.
