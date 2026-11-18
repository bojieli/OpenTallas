# KV-HUBWI-O handoff (2026-11-18 ~06:50 PST) -- kv3_hub_Wi clustered host for D23b/D24

Owner KV-HG-OPUS; cc COORD, KV-D23-COMPOSE. Successor of KV-D23-HUBWI (Fable, weekly limit). DO_NOT_COUNT (plan proposal).

Rows: ~/coord/lanes/handoff/KV-HUBWI-HOST-rows-d23.json (plan rows, asbuilt delta, apply_recipe, file sha, gate/kit/size/portbind records).

Writer on main @04df4c77f065: tools/die_plan/kv_hubwi_host_rows.py (+test, 11 pass) and physical/die_plan/qwen_kvsys/bind/kv_host_wi/.
Apply on the D23 tree: copy views epyc9|epyc7 /srv/opentallas-scratch2/claude/kv-d23-hubwi/views_src/<m>/ ->
physical/die_plan/qwen_kvsys/kvd23_hr_views_1118/<m>/ (14), then
`python3 -I tools/die_plan/kv_hubwi_host_rows.py --tree T --plan P --asbuilt A --views physical/die_plan/qwen_kvsys/kvd23_hr_views_1118 --out-plan P --out-asbuilt A`.
It sets lef/lib on the 21 qkd_hr rows, swaps kv45 host -> bind/kv_host_wi/parent.sv in files+prefer, adds the 14 wrappers_s
to portbind_files/prefer and the 2 leaf prefers (hr_tx_predecode token_service, fault_dreg rx_class_admission). No cycle/outline/pin change.

Measured on private mirror of D22 (epyc9 /srv/opentallas-scratch2/claude/kv-d23-hubwi; plan 4cf7246f1510, asbuilt cc713020e084):
- PRE PASS; G0 0 err/2403 warn; strict bind 0 errors (160 part, 2545 crossings); LATCHECK 2404/2404 PASS; clock tie 11/11.
- R8 FAIL 64 groups/2 inversions/6 types = identical to D16 baseline (diff 0 lines): pre-existing, nothing new.
- Kit from the GATE bind (kit1/): kit-rtl rc0 20 files, dry GEN rc0, KIT_PREFLIGHT PASS 0, GEN_LINT PASS. Shell synth 299,999 cells (flat 1,155,115).
- Portbind strict (pb3/): ambiguous_children 0 (run1 had 2 = the two leaves, fixed by prefer). Remaining FAIL = 4 unresolved
  children qkd_kvs_pcc/pcf(_h_head_p) in the 6 kv3_pc types: no RTL in D22 either -> pc lane / compose, not hub_Wi.
- Equivalence (predecessor): 53962/53962 glue cells, 14/14 wrappers byte-identical regen.
Open: qkd_hr_core_prompt signoff is LOCAL_PASS_NEEDS_PARENT; 4 of 14 views source=routed final=false (ingest_eng, core_order, core_peer, core_prompt).
Running jobs: none of mine (pb run2 finished; predecessor pid 3390259 done).
