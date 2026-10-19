#!/usr/bin/env python3
"""Generate the two member-local reset landings in core_order; shared members stay unchanged."""
from pathlib import Path
from gen_prompt_rr import wrapper

OUT = Path(__file__).resolve().parents[3] / 'rtl/qwen_sys/host_cluster_20261017/order_rr'
MEMBERS = [
    ('qkd_host_ingest_chain_pt', 'rtl/qwen_sys/split_20261014/qkd_host_root_pt.sv', 'ck_map'),
    ('qkd_host_boot_dispatch_debt', 'rtl/qwen_sys/host_20261013/qkd_host_boot_dispatch_debt.sv', 'ck'),
]
if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    for mod, src, ck in MEMBERS:
        t = wrapper(mod, src, ck).replace('QKD_HR_PR_RR_MUTANT', 'QKD_HR_ORD_RR_MUTANT')
        start, end = t.index('// GENERATED'), t.index('module ')
        t = t[:start] + (f'// HKV-HRORD: member-local reset landing for {mod}.\n'
            f'// Original member unchanged. Asynchronous assertion; release +3 {ck} edges.\n'
            '// Zero steady-state cycles; compiler must reserve three reset-release edges before traffic.\n'
            '// QKD_HR_ORD_RR_MUTANT bypasses relay for the reset-contract witness.\n') + t[end:]
        (OUT / (mod + '_rr.sv')).write_text(t)
