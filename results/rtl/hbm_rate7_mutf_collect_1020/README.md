# Frozen MUT_FORCE component collection (2026-10-20 08:12 PT)

Qualification: **false**. Read-only collection; no new build, replay, source edit, or physical gate.

The existing ep9 suvop run terminated with all five records reporting POS_PASS=1 and MUT_FORCE_FAIL=1. The ten complete logs are saved under `witnesses/`; their SHA256 values match `remote_identity.json`. Each positive checks the selected programme's numeric/edge observations, and the +MUT_FORCE intervention corrupts lane 0 of VM read 0. This establishes causal component evidence for this frozen vehicle only.

The actual remote runner builds profile mr10 with RR=12, WR=10, RF_RELAY=32, MLAT=4, ALAT=3, LEAF=1, RF_LOCAL=1 and RF_TREE=1. The bench uses MULTIRATE=0 and COLLPORT=0 on one serial clock; compiler bridge offsets model the mr10 profile. The remote source lacks the PRETREE/tree_cmd ports and modes present in current main. It therefore does not test the current PRETREE=1 production composition.

`frozen_vehicle/` preserves the runner, intervention runner, testbench and all 30 explicitly compiled RTL/model files. `Vtb_toksim_su_top__verFiles.dat` preserves the generated compiler command; binary SHA256 is 6f51f325b078fc374c1013fb6395626a151d38ad831b52cc2dfa71fdb652ff5c. The 570 MB binary remains remote. These source and binary hashes were observed at collection time, not independently witnessed at compile time; no repository commit identity is invented for the remote bundle.

Against main 28e76b629, 25 of 30 compiled files match exactly. Four top wrappers and the testbench differ by PRETREE integration. The runner differs too. `source_comparison_main28e.json` gives each exact source SHA and the five `.main.diff` files retain the differences. Main runner and bench are saved for direct comparison. No semantic equivalence between these vehicles is claimed.

The five `programme.json` and `compile.txt` files are saved. Large programme/vector inputs remain remote with exact SHA256 and byte sizes in `remote_identity.json`. Whole-bench raw logs were hash-verified after collection. Current source-age/protocol, native-32, physical timing, whole composed token rate, and release qualification remain open; this packet does not clear their holds. The separate R6 full numeric PROGRAMME_Q1 failure remains unchanged.
