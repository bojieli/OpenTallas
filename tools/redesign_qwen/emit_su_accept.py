#!/usr/bin/env python3
"""Emit opt-in SU acceptance-count successor; never alter the released master."""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'rtl/qwen_sys/vm_me_20261008/ot_qfd_su_master_bv.sv'
OUTPUT=ROOT/'rtl/qwen_sys/redesign_qwen/ot_qfd_su_master_bv_acc.sv'

def emit():
    s=BASE.read_text()
    changes=[
        ('module ot_qfd_sp_su64_sfu_bv #(', 'module ot_qfd_sp_su64_sfu_bv_acc #('),
        ('    output wire              ready,','    output wire [23:0]       accepted_ops, // real endpoint accept, same clock/epoch/status OS\n    output wire              ready,'),
        ('    // ---- output stations ----','''    // Counter follows the actual vstream accept condition, after embedding
    // prefetch releases go_s. Controller go/go_q may precede this by many edges.
    reg [23:0] accepted_count;
    always @(posedge clk or negedge rs)
        if (!rs) accepted_count <= 24'd0;
        else if (go_s && s_ready) accepted_count <= accepted_count + 1'b1;
    // ---- output stations ----'''),
        ('localparam integer FS = 1 + 1 + 1 + 8 + 1 + 1 + 1 + 1 + SW + SW + 32;','localparam integer FS = 24 + 1 + 1 + 1 + 8 + 1 + 1 + 1 + 1 + SW + SW + 32;'),
        ('.d({s_ready && !e_pend, s_idle && !e_pend,','.d({accepted_count, s_ready && !e_pend, s_idle && !e_pend,'),
        ('.q({ready, idle, obs_active,','.q({accepted_ops, ready, idle, obs_active,'),
    ]
    for before,after in changes:
        assert s.count(before)==1,f'anchor mismatch:{before}'
        s=s.replace(before,after)
    return '// Opt-in successor; old ot_qfd_su_master_bv.sv remains immutable.\n'+s
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=OUTPUT)
    ap.parse_args().out.write_text(emit())
