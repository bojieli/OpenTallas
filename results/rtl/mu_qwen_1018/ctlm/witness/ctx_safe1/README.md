# Unified MU controller component evidence

Verilator 5.050, fleet ot-run jobs only. This proves the controller component on the existing compiled opcal shape; full production programme/store, admission lifecycle and real die clock/timing remain separate obligations.

- `land0.out`: source a07556339; NU4/OPSEG1/CTX_SRC1/FCTX1 versus landed parent. Red 845,539 comparisons and masked-context 283,907 comparisons, zero mismatch. Correct filler native contexts, users and token/position values. Output offsets remain six edges, TL three; inputs ctx_x/mu_fault zero relative input offset. 25 landings/5,080 landing flops.
- `land1.out`, `land2.out`: same source, committed landing mutants fail with 845,539 and 9,199 mismatches respectively. Behavioral reference remains PASS.
- `observer_m0.out`, `observer_m37.out`: source c9c80ccaf; actual OPSEG observer input raises op_fault at cycle1601 and landed lockstep passes4,592 comparisons. Ignoring observer input (MUT37) fails. The existing head fixture already has an independent core fault before this event; these logs alone do not prove a clean STATUS transition.
- `status_clean_m0.out`, `status_clean_m1.out`: source531d7c365; minimum actual GI→GO hardware with a clean initial STATUS. Observer pulse raises dc[52] and cf, stays sticky, reset clears. Disconnecting observer input fails. This discharges the STATUS observability gap without an invalid head/program image masking the test.
- `../../../../ctx_guard/{m0,m1}.out` (results/rtl/mu_qwen_1018/ctx_guard): fresh-context guard accepts consumption then results, independent users and reset; flags overwrite before first bank consumer, same-edge consume/write, and retire/re-admit overwrite. Disabled-guard mutant fails. Guard only reports compiler faults; it never drops writes, stalls, or selects programmes.

Fresh-context consumption is the first LOCAL EMB or SEG bank read. Production INIT/steady variants must be selected by explicit compiled admission metadata, not the guard. New full-identity context validation is being folded into sys_face and its bank-load age must be composed separately.
