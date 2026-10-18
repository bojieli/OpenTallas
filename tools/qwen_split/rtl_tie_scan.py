#!/usr/bin/env python3
"""RTL-internal constant ties below the die masters (RTL-BUILD-QC 10-18; coordinator 0da rule (c): list them per die).

usage: rtl_tie_scan.py CLOSURE_FILES ROOT --out OUT.json
  CLOSURE_FILES: the file list printed by `tools/die_port_bind.py DIE_V ... --closure M` for every die master
  (memory-macro models are skipped).  Every `.port(<literal>)` connection inside an instantiation is listed and given a
  class from the rules below; class UNCLASSIFIED means a functional input with a constant and no rule: it needs a real
  producer (0da d) or a coordinator ruling.
"""
import argparse, json, re
from collections import Counter

LIT = (r"(?:'[01]|\{\s*\w*\s*\{\s*\d*'[bdh][0-9a-fA-F_xz]+\s*\}\s*\}|\d+'[bdh][0-9a-fA-F_xz]+|"
       r"\{\s*\d+\s*\{\s*1'b[01]\s*\}\s*\}|1'b[01])")

# (class, file regex, port regex, reason) -- first match wins
RULES = [
    ('test_repair', r'.', r'^(rr_en|rr_addr|cr_en|cr_sel|SE)$',
     'SRAM row/column redundancy repair or scan enable: test/repair port (allowed tied, no DFT phase)'),
    ('arith_const', r'ot_hdc_|ot_qwen_w12_|ot_qwen_rom_core_ctrl_static', r'^(cin|b)$',
     'adder carry-in / zero operand inside an arithmetic primitive (structure, not a functional input)'),
    ('mem_strobe_const', r'.', r'^(w_mask_in|sw_m|r_ce_in|w_ce_in)$',
     'full-word write mask / always-enabled macro strobe (structure)'),
    ('no_reset_datapath', r'ot_coll_tp8_static', r'^rst_n$', 'data registers without reset (reset only on control)'),
    ('static_ready', r'.', r'^(b_r|n_r|s_r|x_ofin|w_ok|emb_ok|me_mem_ok)$',
     'static cycle schedule: no ready/backpressure (owner 10-14); the consumer is always ready by construction'),
    ('chain_end_idle', r'qfd_tile_nl_rp2_45|ot_qwen_rom_tile_w12|ot_qwen_w12_matvec|ot_qwen_me_array_w12',
     r'^(n_a|n_b|n_va|t_fault_in|i_gbase)$', 'reduction / fault chain head: the idle word (zero) at the chain end'),
    ('mode_unused_nk_kv_write', r'ot_qwen_rom_tile_nk', r'^kvw_', 'nk ROM tile: KV write port unused in this tile mode'),
    ('mode_unused_alt_write', r'qfd_dv_heads', r'^aw_', 'xs tap alternate write port unused with STATIC_SCHEDULE=1'),
    ('mode_unused_sfu_external', r'qfd_dv_su8_entries', r'^sy_', 'SFH=0: special functions inside the lane; external SFU tile ports unused'),
    ('mode_unused_head_su', r'ot_qfd_tt_ctlm_split', r'.',
     'ME head controller (qfd_tt_ctlm_head_static) reuses the ROM core controller with RT_SU=0: the SU / memory-return '
     'ports have no peer on the dv die (SU, VM, embedding live in the slices); rule c, PROOF OWED (head program has no SU op)'),
    ('mode_unused_cp', r'qfd_tt_ctlm_dv', r'^cp_active$', 'CP copy engine left the die with dv (header GONE list)'),
    ('mode_unused_d2d_slave', r'ot_qwen_d2d_dies', r'^(reset_req|recovery_clear|boot_begin|fwd_epoch_i)$',
     'D2D recovery: compute side is MASTER(0) (host reset / boot come from the KV die); the master does not take fwd_epoch_i'),
    ('mode_unused_seg', r'qfd_sys_face', r'^start_seg$', 'calendars started at segment 0 only'),
    ('phy_model', r'qfd_link_slots', r'^(far_v|far_flit)$', 'PHY model far-end loopback unused (allowed model)'),
    ('compiled_const', r'qfd_native59_dv_service', r'^issue_nout$', 'formatter issues one output per native write (compiled constant)'),
    ('compiled_const', r'ot_qwen_rom_core_ctrl_static', r'^split_log2$', 'no K split in the head program (compiled constant)'),
    ('identity_const', r'ot_qfd_coll_static_face', r'^epoch$', 'collective slot-link epoch id: same constant on both peers (identity, 0da a)'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('closure_files'); ap.add_argument('root'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    files = [l.strip() for l in open(a.closure_files) if l.strip().endswith(('.sv', '.v')) and 'asap7_memory' not in l]
    rows = []
    for f in files:
        p = f if f.startswith('/') else a.root + '/' + f
        t = open(p, errors='replace').read()
        t = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), re.sub(r'//[^\n]*', '', t), flags=re.S)
        for m in re.finditer(r"\.(\w+)\s*\(\s*(" + LIT + r")\s*\)", t):
            port, val = m.group(1), m.group(2)
            cls, why = 'UNCLASSIFIED', 'no rule: needs a producer (0da d) or a ruling'
            for c, fr, pr, r in RULES:
                if re.search(fr, f) and re.search(pr, port):
                    cls, why = c, r
                    break
            rows.append(dict(file=f.split(a.root + '/')[-1], line=t[:m.start()].count('\n') + 1, port=port, value=val,
                             cls=cls, reason=why))
    rec = dict(schema='opentallas.rtl_internal_ties.v1', files=len(files), ties=len(rows),
               classes=dict(Counter(r['cls'] for r in rows)), rows=rows)
    open(a.out, 'w').write(json.dumps(rec, indent=1) + '\n')
    print('RTL_TIE_SCAN files=%d ties=%d unclassified=%d %s' % (len(files), len(rows), rec['classes'].get('UNCLASSIFIED', 0),
                                                                 json.dumps(rec['classes'])))
    return 1 if rec['classes'].get('UNCLASSIFIED') else 0


if __name__ == '__main__':
    raise SystemExit(main())
