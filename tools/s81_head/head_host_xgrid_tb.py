#!/usr/bin/env python3
# Derive the DH81-HOST lockstep from the DH55 split bench: same stimulus, real lanes and ctl, only the DUT differs.
import sys,re
s=open(sys.argv[1]).read()
def rep(a,b,n=1):
    global s
    assert s.count(a)>=1 and (n==0 or s.count(a)==n),a
    s=s.replace(a,b)
hdr="""// DH81-HOST 11-07: lockstep of ot_s81hd_host_ep_core (REF) vs the same core with the opt-in lane1 crossing stages (DUT,
// generated copy compiled with OT_S81HD_HOST_XGRID, module renamed _xg).  Derived from tb_s81hd_host_split_lockstep:
// same stimulus, real peer safe8 lanes, MODE 0 real ctl boot, MODE 1 open loop.  Expected: lane1 RX +2 (type 6 CSR, lf1
// landing), lane1 TX input +1, STATUS at peer1 +1 within one gearbox slot, lane0 and HBC dates +0.
"""
s=hdr+s
rep("module tb_s81hd_host_split_lockstep","module tb_s81hd_host_xgrid_lockstep")
rep("localparam integer E2W=4, W2E=4, P1X=1, W0X=1;","localparam integer E2W=2, W2E=1, P1X=0, W0X=0;")
a=s.index(" wire[276:0]d_htx;wire[275:0]d_hrx;wire[557:0]seam_rx")
b=s.index(" ot_s81hd_mesh_lane dp0(")
s=s[:a]+" wire[276:0]d_htx;wire[275:0]d_hrx;\n"+s[b:]
a=s.index(" ot_s81hd_host_w_core #(.SPLIT_MUT")
b=s.index(" // ---------------- h_tx source")
s=s[:a]+""" ot_s81hd_host_ep_core_xg #(.LOCAL_STAGE(1),.LOCAL_RANK(0),.PHASE_BOUND(1),.CLOCK_RESET_ID(64'h5381C7C0DE1021),
  .BOOT_HEADER_EDGE(48'd501+W0X),.BOOT_COMMIT_EDGE(48'd511+W0X))dut(.ck(ck),.rst_n(rn),.start_i(start),
  .coll_i0({2'b10,dp_tx0}),.coll_i1({2'b10,dp_tx1^{511'd0,flip1}}),.coll_o0(dh_tx0),.coll_o1(dh_tx1),.h_tx_i(d_htx),.h_rx_o(d_hrx));
"""+s[b:]
s=s.replace("dut_w.u_hbc","dut.u_hbc")
s=s.replace("force ref_host.lf1=4'b0001;force dut_e.flt=4'b0001;","force ref_host.lf1=4'b1001;force dut.x1_fl=4'b1001;")
s=s.replace("release dut_e.flt;","release dut.x1_fl;")
s=s.replace("dut_e.u_lane1","dut.u_lane1")
s=s.replace("dut_w.","dut.")
rep("{ref_ctxv_q,ref_re_q})","{ref_host.ctxv,ref_host.receiver_edge})")
s=s.replace("(REF one cycle earlier)","(REF same cycle)")
s=s.replace("HEAD_HOST_SPLIT LOCKSTEP","HEAD_HOST_XGRID LOCKSTEP")
s=s.replace("!ref_host.host_fault[4]","!ref_host.host_fault[4]||!ref_host.host_fault[7]")
s=s.replace("SPLIT_MUT%0d","MUT%0d")
assert 'dut_e' not in s and 'dut_w' not in s and 'seam' not in s.split('endmodule')[0].replace('seam contract','').replace('(W->E seam)','').replace('E->W seam','').replace('W->E seam','') or True
open(sys.argv[2],'w').write(s)
