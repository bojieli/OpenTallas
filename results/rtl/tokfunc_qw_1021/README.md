# TOK-FUNC-QW: Qwen ROM RTL-functional token pass (source assembly), 10-21

One command: `tools/qwen_tokfunc/run_tok_func_qw.sh` (assemble RTL -> stage on gold hosts -> 8 stage benches on the fleet ->
collect -> compose 1u token + 4u frame vs the MODEL 4,403.2 / 11,750.6 tok/s). Grade "RTL-functional (source assembly)";
at die closure rerun with `--asm <frozen> --die-netlist <compute GEN out>:<KV GEN out>` (TOK.FREEZE checklist section 6).

Assembly: claude/tok-func-qw-asm-1021 c0f8097f3 (recipe tools/qwen_tokfunc/asm_recipe.json); run-1 fixes merged since -> 02e04473c.
Composition engine: toksim_compose @94cd97b7a; `compose_tokfunc.py --base-only` reproduces 272,641 cyc / 4,403.2 / 11,750.6 exactly.

## Stage verdicts (run 1, Verilator 5.050, ot-gold1/2)
| stage | verdict | grade | key cycles |
|---|---|---|---|
| xdie (compute<->KV D2D, 35 layers bit-exact, ew595_r16 bound both dies) | PASS 22/22 configs, 13 mutants FAIL | RTL-functional + fix de2280f53 overlay | C2K 32 / R31 31 / STATUS 27 / roundtrip 1842 / KV svc 1779 / exposed 64 per layer |
| head (h16yb head leaf RTL, img0/imgh) | PASS 123/123, 131/131, bmut3 FAIL | control RTL; slices answer at compiled status | LM-head span 3,135 (price 3,101: +34) |
| ctx4u (MU context real link) | PASS, mutants 1-5 FAIL | RTL-functional (PHY model) | slot->load 19 |
| ovl4u (4u OVL D2D pair fullframe) | PASS, mutants FAIL | DIAG: assembly has no OVL link-end form (967c24eed end stand-in) | frame 4,026,800, tokens 16/15/8/7, 13,708.2 agg |
| stg (DV families x36 layers, ARF/RP) | running | | |
| xt1 (slice->near/far ROM clusters + 11 landings) | running | | |
| tp8 (TP8 AR256, g5r2b coll lanes) | running (baseline LS 378 bit-exact) | | |
| kv (KV attention u1/u4 = KV-MU7 job4b, source = assembly attention RTL) | job4b compiling | | |

Interim compose (compose_interim/): 1u 272,675 cyc = 4,402.6 tok/s (-0.01% vs model; head +34), 4u 11,750.6; REL share
low until stg/xt1/tp8/kv land (record REL terms re-graded DIAG until re-measured on the assembly).

## Findings
- native59 dv_service left kernel_request_pub open since 087c61d9a: every CMD record carried Q data/tag -> fixed de2280f53 (NOTICE QW2-DIEFIX, Q-N59).
- compute GEN die_params default image is still d2d_cal_image.svh (shift0/sd0) unless OT_QWEN_D2D_IMAGE -> ew595_r16; ROPE build includes a missing ew1627 image.
- head landed parent qfd_tt_ctlm_dv_lpf / lpf_lp predates SEGCAL: imgh lockstep 3,317 mismatches in the LM-head stage (NOTICE FAM-QW2).
- assembly mu_calendar lacked the OVL compiler consumer -> f98fd830f; release D2D end has no OVL form (NOTICE MU-D2D-OVL).

## Codex collection repair, 10-21 09:40

Collection expands legacy stage-prefixed evidence paths and bench placeholders, and retains
existing local evidence if a remote fetch fails. STG publishes rel slice/vec/stn ages for
composition and requires all 36 x 7 nominal stages in both configurations, lm/emb, scheduled
mutants and successful fixture reproduction. Future STG runs retain completed build objects.
The interim report now records each stage source/grade and `diagnostic_stages=[ovl4u]`;
a diagnostic stage cannot qualify a TOKEN PASS. Rates above remain interim composition.

The die rerun interface routes the compute GEN directory to compute stages and the second
colon-separated directory to KV. It remains an unproven closure hook: STG and XDIE explicitly
refuse netlist mode until their carves are wired; head requires head_leaf.v, KV requires
sources.txt for its attention carve, ctx4u requires ctx_sources.f, and ovl4u requires
xq_stages.txt. TP8 currently consumes netlist lane latencies while its collective stays RTL.
A complete die-netlist token claim requires those replacements and source provenance.
