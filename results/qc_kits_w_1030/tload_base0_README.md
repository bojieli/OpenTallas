# QC table ROM loader base[0] (QC-KITS-W 2026-10-30)

Failure (CHECKED): sle_stm_v3 and sle_stm_v1__clbe630b9c pre-floor LEC NOT EQUIVALENT, 12 points
u_core.u_tload.u_ld.rom_addr[*]; "RTL registers removed by synthesis although not constant: u_ld.base[0]".
stage_base = 106*k is always even (all 64 stage values x MUT, CHECKED), so base[0] is constant 0 and synthesis drops
it; base sits on the derived addr_reset (kept reset copy under CAPTURE_STAGE), so LEC treats gold base[0] as free state.

Fix: store base[11:1] only; base = {base_hi, 1'b0}. Same value on every edge, -1 FF, 0 cycles.
Bench tload_base0_tb.sv (iverilog; old vs new module, CAPTURE_STAGE=1/LOCAL_CTRL=1/WE_COPIES=4 and the legacy form,
behavioural ROM model, all outputs + rom_addr compared): LOCKSTEP_PASS 200000 edges, 400000 checks, 2393 starts;
mutant (base_hi xor 1) caught (FATAL at 66 ns). Kit LEC on the regenerated stm kits follows.
