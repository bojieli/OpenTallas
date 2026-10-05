#!/usr/bin/env python3
"""Existing cached XMAP gate with production-hierarchy diagnostic bench selection."""
import dshbm_sm_xmap_seq as gate

gate.SRC = [
    'rtl/test/hbm_opt_integrated_20261005/tb_hbm_accel_sm_pq_xmap_seq.sv'
    if path == 'rtl/test/tb_hbm_accel_sm_pq_xmap_seq.sv' else path
    for path in gate.SRC
]

if __name__ == '__main__':
    gate.main()
