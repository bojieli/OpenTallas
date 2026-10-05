# Qwen G4/W4 reduced tile: limited hold-repair diagnostic

The source and driver are pinned to commit `5affbef8cd03cc8a2b6c7b46a76c55b99248778f`. The focused differential RTL gate passed all 16 × 16 output slots before this run. This experiment used the same reduced G4/W4 tile and 1.5 ns ASAP7 RVT TT setup as the baseline, with `OT_TNS_END_PERCENT=5` supplied to OpenROAD's `repair_timing -repair_tns`. The runner set a 24-hour wall timeout; this failure occurred before that timeout.

The flow **failed during CTS** (`RSZ-0060: Max buffer count reached`), after 40,998 hold buffers had been inserted. The final *incomplete CTS repair iteration* reported hold WNS −222.657 ps and hold TNS −17,561.387 ps, with `kv_load_data_q[224]/D` as the worst endpoint. `RSZ-0066` also reported that it could not repair all hold violations. The raw error and immutable source/Liberty hashes are in [physical.json](physical.json). The 5% setting did not produce a route or solve the input-register hold topology; it is not evidence of improved area or power.

There is **no completed CTS, global route, detailed route, extracted timing, final hold-buffer area, DRC, antenna, or final slew verdict** for this diagnostic. The original G4/W4 and G4/W8 full runs and the split-ingress-clock G4/W4 run are separate source-pinned experiments. Their results must not be inferred from this error record.

The tile uses analytical ROM/SRAM LEF and Liberty views, with no characterized memory internals or macro GDS. ASAP7 is an academic predictive PDK. This is reduced-tile characterization, not Qwen3 8B core closure.
