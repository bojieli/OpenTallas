#!/usr/bin/env python3
"""Production default-off PQ source selection; reuse the exact retained sequence/golden driver."""
import dshbm_sm_pq_seq as P
P.SRC = [s.replace("rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv", "rtl/hbm_accel/sm/pq_production_20261005/ot_hbm_accel_issue_pq.sv").replace("rtl/hbm_accel/sm/ot_hbm_accel_sm_pq.sv", "rtl/hbm_accel/sm/pq_production_20261005/ot_hbm_accel_sm_pq.sv").replace("rtl/test/tb_hbm_accel_sm_pq_seq.sv", "rtl/test/tb_hbm_accel_sm_pq_production_seq.sv") for s in P.SRC]
if __name__ == "__main__":
    raise SystemExit(P.main())
