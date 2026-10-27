# CODEX QC coverage 2026-10-26 20:08 PDT

- INFRA-FIRST: QC infra holds; R4 window80 merged, R5 DRT model caveats collected. Next R9 die-related-pair STA integrates mesh+R8 stack. No stale crop rerun.
- INFRA2: Backup+sync operational lane; no QC-specific active failure. Ops remains root auxiliary coverage.
- PATH-QC: All68 type routes held by one QC plan event. New core trials continue; physical interfaces wait for R9 clock+master plan.
- QC-CLK-MESH: r3 b6b245b1d1 completed: nominal12.8/10.9, MC293/258 whole-die INFO, pair97/93; COORD19:52 selected per-pair STA with approved data hold. No multi-root redesign. Mesh tool integration at root.
- QC-SU-F4: F4D both finished FAIL: rp1 TT235.6/FFhold-55.50(741eps), insertion178.5/143.4; vmr TT137.85/FFhold-55.17(1259), insertion169.9/137.8. DRC0; LEC3703/5342 EQ. Non-tree M6 111/120 nets. F4E tails started19:58 still live; no duplicate. F4A vmr still DRT; rp1 corrected ftarc SIGNED historical view, no recheck.
- QC-SU-LAT: Old SU kits/prog predicted failure superseded by F4D+F4E/PROG-L2/BTAB-R5. No rebuild old topology. Preflight empty-param config parser fixed4d6f32c477,10focused testsPASS.
- QC-SU-PROG-L1: L1 options rejected/next3level already implemented by PROG-L2; restrict sizer calibrated BUFx8..24. No old topology rebuild.
- QC-SU-PROG-L2: epyc2 qc-su-prog-l2-1026/kit_l2 route_l2.log remains live at44th guides iteration20:01; no duplicate. GRT window20.96 FAIL target20; structural node/RCX collection needed after route.
- QC-SU-BTAB-R5: intel1 qc-su-btab-r5-1026/btab_m0_r5 route finished report stage; DRT0 from17:30 review. RCX already measured by MODEL-REFIT3: window48.9 (GRT19.5); unequal leaves/island root cause. No redundant RCX repeat. Per-bank spread for next kit remains.
- MASTER-PLAN: Current regional tool c4x4 c0ee/32fa variants have high detour and plain seam hold failures; mesh supersedes path. R9 declares full266cell sites incl3trunk; row delta170 moves,48westward MY, exact fullbody hosts. Template kit regeneration in own epyc2 tree.
- MODEL-REFIT: uf_phys3_v1 c46af260b owns predictor; GRT11/10ps guard,window14. No via-term adoption. F4D straight tree insertion169..178 vs predicted means exposes new datapoint; preserve native RCX data before refit. Need landed-hub+HEAD new measurement imports, assigned S81/HEAD peers.
- CLOCK-128: CODEX took over QC R9 on codex/qc-r9-2000 from R8e6b5c249a3. 266declaredsites,170rowmoves+48MY. Build2 success;16focused R7/R8/R9testsPASS; fresh windows generating. R9render viewed; maxriser2.325 requires window margin2.6. DRC+RCX pending; not SIGNED.

Jobs: inherited F4E epyc2 qc-su-f4d-1026/kits/*/f4d_chain.txt; F4A vmr intel1 qc-plan-f4a-1026/kits/*vmr*/; PROG-L2 epyc2 kit_l2; R9 own kitgen2 light script then planned ot-run. No owner questions.
