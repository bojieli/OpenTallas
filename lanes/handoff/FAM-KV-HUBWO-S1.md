# FAM-KV-HUBWO-S1 handoff
- 21:5x 11-22: class ef2cd1801a = ASTK-MERGE (see post). D29 row d88e5b5ffaa5 already posted by HUB-R6.
- Sealed private kits goal route on plan 240c9e69c3f1: specs ~/coord/autopilot/private_specs/FAM-KV-HUBWO-S1/qwen_kvsys_kv3_hub_{Eo_1122215550,Wo_1122215611}; runners intel2 pids 3761495/3769881, logs ~/tmp/famkvhubwo/kitS1_*.log; script ~/tmp/famkvhubwo/sealed_s1.sh. rt must be d8e3d23798be (bind generator).
- NEXT: ot-wait --durable; on sign-off + EQUIVALENT routed LEC run kit_wave.py private-provenance <spec dir> --lec <lec.json>. Hub_Ei sealed (HUB-R6) separate.
- 22:2x: sealed Eo/Wo (1122215550/1122215611) FAILED kit_rtl rc2: relay_depth row astk_*.u_strip..zn_0_u_zn__rst_n has no connection (bound-chain regex used raw double-underscore port; bind names chains collapsed). Fixed on main 934ebc63141a (KIT-RD-DUNDER-1122, lane clone epyc8 FAM-KV-HUBWO-S1/clone). Posted to KV-PLAN-R6/FLOW-OPS-R2 for rt publish.
- NEXT: when rt >= 934ebc63141a exists: strict rebind of plan 240c9e69c3f1 (tree_r fork, as rebind_r6c.sh), then private-spec --goal route sealed Eo/Wo with that --rt; then provenance + LEC.
