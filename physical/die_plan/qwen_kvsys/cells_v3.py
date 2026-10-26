#!/usr/bin/env python3
"""PLAN-KVv3 10-23: L1 std-cell estimate per partition (leaf RTL flattened; only SRAM/ROM macros + PHY/SerDes/UCIe
models stay hard).  Per-master cells: measured Yosys synth_stat top-module counts (fleet ref_gate / closure-loop runs,
10-23) where one exists; otherwise outline_um2 x class density, calibrated on the measured masters:
  datapath (ot_qkh_*, ot_qwen_tp8_pv_*): lane8 113,901 cells / 16,796 um2 = 6.78, ktree_lk 91,912 / 14,697 = 6.25 -> 6.5
  control / SRAM-bearing (qkd_*): grp_r2c 0.24, kvs_attn 0.39, seq_fan 0.66, embgw 1.95 -> 1.0 (upper-side median)
Hard: SRAM macros inside leaves are counted as 0 cells only where measured (grp); elsewhere the density covers them."""
import re

HARD = {'qkd_hbm3e_phy_pc', 'ot_qfd_serdes_112g_x12_phy', 'ot_qkvd_ucie_x64_phy'}
MEASURED = {  # master: (cells, source run)
    'ot_qkh_lane8': (113901, 'ep7 closure-loop ot_qkh_lane8_nc32c-g1-68c8bea30'),
    'ot_qkh_ktree_lk': (91912, 'ep7 closure-loop ot_qkh_ktree_lk_nc32c-g1-1c272f08e'),
    'qkd_kvs_grp_r2c': (62708, 'ep5 ref_gate qkd_kvs_grp_r2a-20261022-215245'),
    'qkd_kvs_grp_h_r2c': (53243, 'ep9 ref_gate grp_h_r2c'),
    'qkd_kvs_attn': (18254, 'agidock ref_gate qkd_kvs_attn_fl'),
    'qkd_embgw': (72692, 'agidock ref_gate qkd_embgw'),
    'qkd_seq_fan_s': (2303, 'agidock qkd_seq_fan_s'),
    'qkd_seq_core_static_s': (3247, 'agidock qkd_seq_core_static_s'),
    'qkd_astk_rly_296_fl': (621, 'ep7 closure-loop'),
    'qkd_astk_fault_join': (4, 'agidock'),
}
DENS = dict(datapath=6.5, control=1.0)


def master_cells(m, w, h):
    if m in HARD:
        return 0.0, 'hard'
    if m in MEASURED:
        return float(MEASURED[m][0]), 'measured'
    cls = 'datapath' if re.match(r'ot_qkh_|ot_qwen_tp8_pv_', m) else 'control'
    return w * h * DENS[cls], cls
