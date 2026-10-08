#!/usr/bin/env python3
"""Full-width refill positive and wrong-output mutant, reusing identical checker."""
import hbm_collective_cdc_gate as base
base.FILES=base.FILES[:3]+[
 'rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc_refill.sv',
 'rtl/hbm_accel/collective_cdc_20261007/tb_protected_cdc_refill.sv']
if __name__=='__main__':raise SystemExit(base.main())
