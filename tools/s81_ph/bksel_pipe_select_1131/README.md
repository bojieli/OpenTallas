# Opt-in actual A+B selector candidates

These two recipes patch the active ot_s81ph_sel_su_pipe selected by SEARCH_PIPE1 in production dsdv_bksel_c. They replace only the A acca and B aboveb dynamic selectors with constant-index highest-one-mask OR trees. R1 adds no selector state. R2 registers masks from compare-NEXT on the existing sum-capture edge. A bucket15 returns zero; B bucket15 returns acc_b4; mask0 retains index1 fallback. No external port, arithmetic order or cycle change. No production/default source or recipe is changed.

The current-main production pipeline baseline matches source/original.sv byte for byte (SHA256 da2becfa97afb74a5d2c4767958d174a11865b2ba00ff1b25531e1329056ab29). Full opt-in source copies and exact-anchor patches are included; recipes apply only the selected anchors to kit-local source.

Qualification is production Q4/CB11/XR6, QW11 and21, XW21 in both SUs. The actual A+B cut miter preserves compare/sum/result edge coupling and A/B fallback differences. It passed524304 checks across all65536 masks/case with changing21-bit data, and caught stale-gea/geb selector mutants. Reproduce with `python3 tools/s81_ph/bksel_pipe_select_1131/run_cut.py OWN_OUT` through normal ot-run admission. This is a source-cut proof, not a claim of full-SU old/new simulation.

The five controller/command correspondence hints are untrusted. Each candidate has its own exact-AIG64-edge reset base and individual induction receipts. R1 and R2 whole-kit normal native LEC then passed independently:55682/55682 and55768/55768 points, zero differs/undecided. Only five explicit hints were supplied; normal anonymous-register proposals were also fully reproved. Original failure history is retained on the experimental branch; no failed verdict is overwritten. See results/rtl/bksel_pipe_select_1131/{cut,r1_correspondence_lemmas,r2_correspondence_lemmas,r1_official_eq,r2_official_eq}.

Generate a fresh opt-in candidate on current main:

    python3 physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py \
      --module dsdv_bksel_c_pipe_ab_r2 \
      --recipes tools/s81_ph/bksel_pipe_select_1131/recipes.json \
      --out OWN_KITS --trial

Use ab_r1 for R1. The generator copies the five hints; the normal engine must prove them and the complete fresh source miter. Source hashes, exact proof bases/tool version and official receipts are pinned. Current main has a later independent-Slang compilation-unit correction; this intake does not transplant an old proof as a waiver for changed future inputs.

This batch contains no physical moves, failed experimental helpers, view adoption, timing/capacity/DRV/clock waiver or token-performance claim. Continue normal model/LOOK/SYNTH/LEC/PLACE/CTS/GRT/route/signoff gates for every actual physical candidate.
