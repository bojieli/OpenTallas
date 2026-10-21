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
| xt1 (slice->near/far ROM clusters + 11 landings) | PASS near+far64/64 at both spacings, 3mutants caught | source carve; clocks functional | firstRS187/248, landings add6/12 |
| tp8 (TP8 AR256, g5r2b coll lanes) | PASS, 9 mutants caught | current collective RTL; historical lane ages DIAG | E 286, LS 378, AR256 span797, MU window38138 |
| kv (KV attention u1/u4 = KV-MU7 job4b, source = assembly attention RTL) | job4b compiling | | |

Interim compose after XT1 collection (compose_interim/): 1u 279,731 cyc = 4,291.6 tok/s (-2.53% vs model; head +34, tile +7,056), 4u 11,750.6; REL share
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

## Coherent RoPE source generation

`compile_rope_pair.py` recovers the e18e3d597 recurring Ckind12 reservation, then feeds
that sole calendar to the existing MU frame compiler and four-ROM release generator.
Run on the fleet, against the selected source assembly:

```sh
python3 tools/qwen_tokfunc/compile_rope_pair.py --source-dir ASSEMBLY \
  --ages actual_gen_inputs.json --token-path token_path_compiled.json \
  --link-handoff actual_decision.json --out NEW_OUTPUT_DIRECTORY
```

The null-valued `rope_actual_gen_inputs.template.json` lists required source and actual
GEN facts. Unknown fields refuse before creating outputs. `head_prepare_edges` is the
source-composed earliest safe SLOT in native edges, including clock conversions for
TT-to-native and native-to-sysface transport. `kv_descriptor_to_header_edges` includes
the actual selected KV fork, context-start, HBM traversals and row capture through the
header deadline. No HOST RESULT or inferred next-token authority is used. One recurring
Ckind12 RX plus that actual fill path must meet the compiled first header. Old K-to-C
HOST CONTEXT budget is insufficient for this new source law.

Generated outputs are source programmes only, not playback or functional PASS. The die
owners must select real descriptor producer/consumer and MU OVL sequencers. At 09:50
current 595 GEN lacks HEAD_PREP buses; those ages and this generation remain pending.

XT1 landed near first-RS is187 and far248 (delta61), versus baseline181/delta18.
Four matvecs per layer add4*(6+43)=196edges, across36layers +7,056edges.
Current STG/KV are still pending; TP8 historical lane ages and OVL old-end stand-in
remain DIAG, so neither 1u nor 4u rates qualify a complete current-source token PASS.
Admission callbacks must preserve phase: SEG2/base16 before actual adm_done allows
HOST filler O61 owners1..3 while cal_user0; recurrent Ckind12 after admission uses
the actual scheduled user and held O61. The old diagnostic OVL bench has no admission
playback, so it does not establish that phase contract.
