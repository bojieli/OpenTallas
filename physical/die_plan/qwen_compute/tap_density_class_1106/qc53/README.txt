plan_qc53 (START4 candidate) composition of the QC tap class (DIE-QC-84 11-06 10:4x, COORD 10:0x (7)).
Base: Codex START4 candidate plan_qc53_candidate_v2.json (intel2 /srv/opentallas-scratch2/claude/codex-qc-start-1106,
sha256 in model.json). 46 of the 50 class patches hash-match their qc53 base type unchanged (copied from ../); the 4
START4 re-formed types must be re-measured on their START4 3_place:
- slw_fe_v1__clfe325744__cl08d14f0d (Codex FE PLACE 09:55) and slw_fw_v3 (DIE-QC-84 PLACE 10:1x): re-measured here,
  bins/ + model.json: 111 taps (load 905, reach 164.8 um) / 80 taps (load 1154, reach 167.2 um);
- coll_ftm (DIE-QC-84 PLACE 10:30): 50 taps (cap 1000, load 787, reach 185.7 um) (update 11:0x);
- slw_fw_v2__cl8537f156: PLACE running (after the relay-copy face_guard fix 650a2d7c7d); add it with the same
  model_class.py (../) once its 3_place exists.
validate.py (../, run with the START4 src_bm tools): apply on plan_qc53_candidate_v2 + reload + recomputed taps equal
the model + gen_phys exports legal: VALIDATE PASS 49 types, 5434 taps.  Candidate only; the CBN ring split event
(main 5129225f79) is not in this base; its types hash-mismatch after composition and must be re-measured then.
