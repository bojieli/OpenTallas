# HHP c708 typed phase-issue guard + directed boundary-fault bench (TOK-ALL-14, 2026-10-27 15:51 PDT)

Guard: tools/qwen_kv_die/hhp_phase_guard.py (typed PhaseSchedule/PhaseWindow/Event; PHASE_DELAY d = 1 for c708).
Enforces COORD's three c708 constraints: W first writer word >= BOOT_END+2; S first slice write >= REOPEN+1;
E embedding issue >= BOOT_END and issue->return >= 2 edges (return in [BOOT_END+2, REOPEN+1]); plus the unchanged main
bounds (writer <= REOPEN, slice <= BOOT_END-1, slice returns in the boot window).
Bench: tools/qwen_kv_die/hhp_phase_boundary_bench.py. DUT = real qkd_static_kv_pc_es_merge_b + its real embedding
endpoint, transformed by kvspc_phase_delivery.transform (c708836e35 helper, optional nface_ff). 64 isolated directed
cases per RTL: RISE/FALL x {writer, slice, er, completion} x offsets T-3..T+4, each from reset (iverilog -g2012).
Result c708 (c708/result.json) PASS and c708+nface_ff (c708_nface_ff/result.json) PASS:
- exact edge model hw_predict == RTL on all 64 cases for main (d 0) and c708 (d 1);
- RTL mutant (c708 helper without the phase FF) CAUGHT: 8 (7 with nface_ff) cases differ from the d 1 model;
- guard soundness: every single-event schedule the guard admits is RTL-safe (0 unsound, c708 and main);
- tightness: just below each bound the RTL is unsafe (writer at BOOT_END+1 faults; slice at REOPEN+0 faults;
  embedding return at BOOT_END+1 is steered to the slice);
- guard mutants W/S/E (each bound weakened by one edge) all CAUGHT (each admits an RTL-unsafe case).
Optional N-face FF (nface_ff): register wes[0] && own_pin at the N face, OR into m_fault next edge: +1 FF (total +5),
0 data/steady/token cycles, 0 extra boot edges; restores main's writer-in-boot fault at REOPEN+1 (flagged: true).
Price unchanged: +1 edge at BOOT_END and each REOPEN, 0 steady/token cycles.
Not done here: wiring the guard into the KV production boot/REOPEN calendar emitter (none exists on main yet) and the
gen_core_kit_kv.py hook (on codex/kv-cores-1351, not main).
