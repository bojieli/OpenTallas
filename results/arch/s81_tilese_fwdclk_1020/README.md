# Forwarded-clock class on current main (S81-TILES-E 10-20)
Branch claude/s81-fwdclk-main-1020 = origin/main 98070b1b5 + cherry-pick of a2381593a (frame-branch forwarded-clock class,
spec key forwarded_clock_ports; opt-in, generated SDC byte-identical without the key). Needed by S81 frames col_h9/col_h10
rf2: main tools fail OT_LANDED 124/132, 136/144 (rf2m 806339/40) because the 8 xk forwarded child clock pins have no class.
Fleet ot-epyc5 (python3 -m unittest, real ORFS image):
- cand: test_landed_forwarded_clock + test_landed_cluster_kit + test_landed_raw_child_pins + test_landed_multi_root_record
  + test_hybrid_clock_rule_0dq: Ran 43, OK (3 skipped: pgslice_lg child views not shipped) -- unittest_cand.log
- base (same 4 existing modules without the new one): 2 import errors = loader-order artifact (test_landed_cluster_kit's
  tests/ sys.path insert happens only when another module imports it first); no test failure -- unittest_base.log
