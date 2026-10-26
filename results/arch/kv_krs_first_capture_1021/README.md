# Actual KRS ES6 first-capture geometry

Read-only model, no source change or GEN/gate launch. Reference source052ce32dc actual CLOSED S6C group every-bit pins; K-DIE confirmed its1122tile placement unchanged from74eb40c66. Relay-layout sourceSHA matches actual052 source exactly (receipt). Reference snapshot is ../kv_ctl_central_1021/pre_relays_central.json.

Source slg_ES_6 isMY at11885.184,9892.8. Use actual CLOSED group LEF388.8x432 for physical mirror geometry, preserving every1062krsp bit. The1062b standard row is528+528+36(6used), offsets0/32.4/64.8, lastdy34.56, frame77.76x82.08. Actual CLOSED a[] pin rectangles were read fromqkd_rlys_528/36 LEFs. The existing kv_rly_std expander supports whole-frameMY by mirroring both replica locations and each replica; no synthetic input anchor substituted.

AtLLx11785.824 (21.6um frame gap), exact matching-bit optimization on the2.16um y lattice gives:
- R0: LLy10074.24, max303.216um, worstbit1; zero static-frame intersections.
- MY: LLy10106.64, max257.94um, worstbit1; zero static-frame intersections.

Both satisfy340/405um. MY improves this best static-case first hop by45.276um; it is not an essential orientation fix proved by this model. Since R0 already has a legal static slot, currentstage0 refusal requires the actual partial-relay occupancy/frontier snapshot before redesign. Clock/reset/output-chain/native qualification remain owed. No fullchain, closure or performance claim.

To rerun, stage the three exact LEFs named/hashes inRECEIPT.json into a flat directory and setMODEL_LEF_DIR to it, then runpython3 model.py. MODEL_GEOMETRY, MODEL_REPO_ROOT andMODEL_OUTPUT may override reference paths. Default outputkrs_receipt.json preserves the committed receipt. No source/view files are mutated.
