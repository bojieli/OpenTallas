HBM-039 source structural candidate, 2026-10-29 18:58 PDT

Default-off LOCAL_CTRL_REPLICAS and PRESERVE_STATUS_VALID reach the actual hfd_hgi_vms_glue_nw_t top through the regenerated glue wrappers. No protocol, arithmetic, output edge, or calendar changes. Eight276-bit payload bays and one16-bit header bay get independent4-bit ring controls:36 additional FF per ring,72 for CW+CCW. Status uses a preserved2-bit startup-valid hierarchy, preventing its valid flops from merging with unrelated ID/control flops;0 additional FF,0 cycles.

Measured minimum actual mechanisms:
- Original pinned ring vs candidate,5000 full-width edges,all outputs compared,reset every127cycles,all8 selector encodings:0 mismatches. Wrong lane0 selector mutant caught1191 edges (run4_intel1.log).
- Original status vs candidate,2000edges,reset every37cycles:0 mismatches. Early-valid mutant caught54edges(status.log).
- Yosys proc;flatten;opt retains9 helper instances with9 distinct4-bit source/enable outputs(replicas_check.py); keep/dont_touch on register NETS ALONE failed this test(all9 drivers merged). This root cause is fixed with keep_hierarchy+keep on helper CELLS.
- Both generation checks PASS. NW top with both opts=1 elaborates with original hub/replay and actual generated tile.

Rejected trials preserved: run_intel1.log has481 mismatches from implicit function global sensitivities, fixed by explicit complete function inputs; run3 exactness passed but net-level keep allowed synthesis merging and was rejected. run2/run3 are intermediate evidence; final source is run4 plus generator parameter propagation.

Scope/next required work: this is NOT a physical closure or whole-glue equivalence claim. No route or STA launched. The per-bay controls need corresponding physical bay placement AND input/control pin reach treatment; duplicating same-D captures alone does not guarantee input reach. Hub be/br fanout, N-face bank-status pins to S, and overall glue outline remain open HBM-039 work. Current plan/kit does not enable these opts. Build a reviewed bay-aware kit and prove complete-glue LEC before adoption. Source default behavior preserved; other quadrants keep both opts0.
