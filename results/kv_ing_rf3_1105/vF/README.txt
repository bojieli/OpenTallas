KV-ING-5 vF (2026-11-06): vE kit + cut 19 + registered reset fan-out.
cut 19: st_wa_r kcode/kscal adds as carry-select (3-bit low add selects ap_*[31:3] or ap_*[31:3]+1); exact, 0 cycles, no new state.
 RTL: ../rtl/qkd_hr_ingest_eng/qkd_host_native_engine_ing3.sv. Proofs: eq.ys (wa_fix RTL vs r3 next-state wa_ref) SUCCESS,
 eqg.ys (synthesized gates + liberty vs wa_ref) SUCCESS, eq_mut.ys (kc_lo[2] mutant) FAIL as required, eq_kshi.ys (no +1 on ks hi) FAIL as required.
 Bench run_ing_f.sh: 48 seeds + full-rate lock-step vs r3 engine, LOCKSTEP diffs=0; mutants m_kchi m_kslo m_kcsel m_scale m_take m_addr detected,
 m_kshi survives the bench (kscal low carry not reached) but is caught by eq_kshi.ys; m_kclo (drop st_ph[2] on the kcode add) is an
 equivalent mutant: kc_sum is selected only when st_ph<3.
Physical: wa_fix gate netlist spliced into vE 1_2_yosys.v (splice.py) so Codex name-based banks keep their names; control_local.tcl
 minus the 56 loads eliminate_dead_logic removes with the old chain (probe_missing.json), 27 banks. OT_RESET_REPLICA_LOADS=64.
