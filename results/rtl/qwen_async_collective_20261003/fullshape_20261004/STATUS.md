# qwen-async-full (Claude, 2026-10-04) -- STATUS
Branch claude/qwen-async-fullshape-20261004 (source commit in src/SOURCE_COMMIT). Task: validate+adopt the Qwen TP4 async collective at full shape.
chain.sh (detached, log chain.log, rc chain.rc):
 A) layer-parallel full token, ideal memory, ONE ASYNC_COLL=1 binary (lpbuild): plans/fc (fused+cut imgFC, 37 stages), plans/legacy (img256, cut bit absent = baseline), plans/fc-poison (entry poison). Verify with tools/qwen_rom_layer_parallel_sim.py --verify.
 B) REAL_MEM E+L0-L2 at P0/P255/P1023 on rm-async binary (rmbuild): res/rm_{img256,imgFC}_p{0,255,1023}.json.
Golden: 36-layer P255 oracle does NOT exist (CPU goldens banned; GPU oracle not built) -> full token only at P0; nonzero positions are E+L0-L2 prefixes.
Next for a resumed agent: when chain.rc exists, copy plans/*/verdict*.json, res/*.json, logs into results/rtl/qwen_async_collective_20261003/fullshape_20261004/ on the branch, compare cycles, apply owner rule, commit explicit paths.
- r2: imgFC r1 jobs failed at open (doubled paths); chain2.sh reruns plans/fc-r2, fc-poison-r2, rm_imgFC_*_r2
- 01:30Z raised max_load_per_core to 4.0 in plans/fc-r2, fc-poison-r2 (host load ~300 from other streams). legacy verified: 144,522 composed, all 37 singles pass.
