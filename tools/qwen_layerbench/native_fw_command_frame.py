#!/usr/bin/env python3
"""Encode real frozen native FW boundary frames for the producer component.

This is the actual qfd_qc_slw_fw output ABI, not a direct SU or fabricated
command port. Boundary clocks/START/epoch timing remain external requirements.
"""
import hashlib
import json
from pathlib import Path
import argparse


def encode(cmd, chd=0, hr=0, pc_bad=0, epoch=1):
    for name, value, bits in [('cmd',cmd,116),('chd',chd,1038),('hr',hr,453),('pc_bad',pc_bad,1),('epoch',epoch,1)]:
        if type(value) is not int or not 0 <= value < 1 << bits:
            raise ValueError('out of actual FW field bounds: '+name)
    # Original three ot_dp_st output expressions, each data536+epoch1.
    low = chd & ((1 << 536)-1)
    p1 = (chd >> 536) | ((cmd & ((1 << 34)-1)) << 502)
    p2 = (cmd >> 34) | (hr << 82) | (pc_bad << 535)
    return {name: value | (epoch << 536) for name,value in [('x_ctl_o',low),('x_ctl_p1_o',p1),('x_ctl_p2_o',p2)]}


def source_guard(source):
    expected = [
        'ot_dp_st #(.W(536)) u_bout_x_ctl_o (.clk(clk), .rst_n(rst_n), .d(w_core_chd_q[535:0]), .ea(rst_n), .q(x_ctl_o[535:0]), .eq(x_ctl_o[536]));',
        'ot_dp_st #(.W(536)) u_bout_x_ctl_p1_o (.clk(clk), .rst_n(rst_n), .d({w_core_cmd_q[33:0], w_core_chd_q[1037:536]}), .ea(rst_n), .q(x_ctl_p1_o[535:0]), .eq(x_ctl_p1_o[536]));',
        'ot_dp_st #(.W(536)) u_bout_x_ctl_p2_o (.clk(clk), .rst_n(rst_n), .d({w_core_pc_bad[0], w_core_hr_q[452:0], w_core_cmd_q[115:34]}), .ea(rst_n), .q(x_ctl_p2_o[535:0]), .eq(x_ctl_p2_o[536]));']
    text=source.read_text()
    if any(line not in text for line in expected):
        raise ValueError('actual selected FW output register ABI changed')
    return dict(module='qfd_qc_slw_fw',sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_output_register_edges=1,
                boundary='after actual FW output register; its edge already priced in bound source latency')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fw-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    abi=source_guard(a.fw_source);cases=[]
    for user in range(4):
        pidx=17+128*user;cmd=(pidx << 4)|3
        cases.append(dict(user=user,pidx=pidx,cmd_hex=f'{cmd:029x}',frames={k:f'{v:0135x}' for k,v in encode(cmd).items()}))
    a.out.write_text(json.dumps(dict(schema='native_fw_component_frame_source/1',status='SOURCE_ONLY_TEST_STIMULUS_NOT_CALENDAR',abi=abi,
        cases=cases,programme='genuine per-user HEAD pair8 upper pidx17 must be installed before issue',
        sixpart_boundary='p1 enters real FW→STM→SC→CTL chain; high command fragment p2 and low CHD p0 take unselected neighbors and remain explicit boundaries',
        holds=['all stage/native/forwarded clock source and start/epoch phase','actual programme/table/VM fixture initialization and accepted-command witness','source-frame injection times are TEST_ONLY, no global date inference'],executable=False),indent=2)+'\n')
    print('NATIVE_FW_FRAME_SOURCE users4 pidx17/145/273/401 actual3fragments no_dates')


if __name__=='__main__':main()
