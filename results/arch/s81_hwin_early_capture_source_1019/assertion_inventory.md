# Private reset assertion observation correction

Original fail source51e3f48f3 preserves the original DSDV_MU_POINTER_ASSERT build. At first posedge1000ps external rst_n is0 and the source-initialized local reset-tree leaves may be random1 until async assertion cascades through root/group/local NBA updates. Existing event-count assertion checks a random local leaf without external reset qualification; it observes pre-reset random count/vld mismatch. No observed event/output date had occurred.

ROOT explicitly authorized a new-bench-only correction. Source HWIN, memory, reset tree and old bench remain untouched. Private runner no longer enables DSDV_MU_POINTER_ASSERT except the original anchor-alone reproduction. New private bench copies all original checks with only rst_n added to their existing enable; it leaves every original reset edge and the original four-low/four-release schedule unchanged. New captures remain unreset. No candidate valid/fault/output is masked.

| Original source check | Original enable | Private additional qualification |
|---|---|---|
| live count equals valid population | rn && rr[COPY_END] | rst_n |
| each event boot count equals valid population | rr[RBOOT_BASE+ce] | rst_n |
| each event selector lookahead | rn && LOCAL_BOOT!=0 && cfg_w1_r | rst_n |
| retire one-hot/binary pointer | posedge ck or negedge rn; else rn | rst_n |
| slot one-hot/binary pointer | same | rst_n |
| gap one-hot/binary pointer | same | rst_n |
| each event one-hot/binary pointer | same | rst_n |

All seven forms are instantiated for both original anchor and candidate. Existing width casts SJ and EI are reproduced as SI+1 and EI in bench. Full output/fault miter remains unconditional at every negedge; internal control miter retains original rn qualification. ANCHOR_ONLY_REPRO removes candidate and aliases original observations. ORIGINAL_ASSERT_REPRO selects original source assertions, with exact seed1 and original stimulus. ASSERT_CORRUPT forces event0 count to1 on the first negedge after external reset and local release; the replicated event-count assertion must reject it at next edge. Initial guarded correction run uses immutable run_guarded_assertions_01 receipts, never replaces initial_failure.
