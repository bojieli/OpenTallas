# QC VMR F4J residual data hold review 2026-10-27

Pictures viewed: results/qc_cores_1027_vmr_f4i/f4i_place.png and f4j_hold_path.png (same directory).

F4I placement follows the two SRAM columns and leaves the PG via-stack escape bands clear. Routed baseline DRC0 confirms the F4I structural pin-access repair. FF worst path pa_addr[73] -> inverter _12932_ -> s1_off[10] lies in the NW perimeter, with a short local data path between different clock leaves. Launch/capture insertion191.59/218.13ps and library hold19.45ps leave data250.72ps below required261.54ps. This is a residual internal hold shortfall after RCX (35 endpoints, -10.83ps), not an IO-vclk failure. Data hold repair is allowed; no clock edit or interface change. Existing nonfiller cells remain FIRM; only new local delay cells are placed. Require sparse repair <=500 cells, unchanged clock, DRC0, TT setup/FF hold and routed LEC before accepting.

Verdict PASS-COND for F4J trial, subject to those gates. A0 mid-row drivers remain deferred by COORD07:18 until intra-A0 STA demonstrates need.
