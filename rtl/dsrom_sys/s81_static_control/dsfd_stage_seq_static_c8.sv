`timescale 1ns/1ps
`default_nettype none
// dsfd_stage_seq_static_c8 (S-BIND 2026-10-14, owner static-cycle rule 18:59): die-name master of the STATIC stage
// sequencer on an S81 layer die.  Engines present: fld 0, su 1, hc 2, coll 3, svc 4, sel 5, col 6, hop 7 and the VM
// sequencer engine 12 (dsfd_sp_vm c_cmd/c_done/c_st).  head 8 / emb 9 / Engram 10 / HC projection 11 live on other die
// kinds: they have no die pins here; ENG_PRESENT masks their completion/status inputs, so a calendar row routed to one is
// rejected by the boot scan (cfg fault 3) and never issued.  Same core and timing as dsfd_stage_seq_static_c: every
// issue / KIT / END edge comes from the compiled calendar; done/status pins only detect faults (no credit, no ready).
module dsfd_stage_seq_static_c8 #(parameter integer NOPS=128,STAGE=0)(
 input wire[0:0]ckv,rsv,ck,rst,
 input wire[52:0]f_ks,output wire[53:0]t_kd,
 input wire[35:0]f_pw,input wire[7:0]f_plen,output wire[5:0]t_st,
 output wire[84:0]c0,c1,c2,c3,c4,c5,c6,c7,c12,
 input wire[8:0]d0,d1,d2,d3,d4,d5,d6,d7,d12,
 input wire[1:0]s0,s1,s2,s3,s4,s5,s6,s7,s12
);
`ifdef OT_SSEQS_MUT_VM_ABSENT
 localparam[12:0]PRESENT=13'h00ff; // negative control: VM engine rows must not be accepted silently
`else
 localparam[12:0]PRESENT=13'h10ff;
`endif
 wire[84:0]c8_nc,c9_nc,c10_nc,c11_nc; // absent engines: no command consumer on this die kind
 dsfd_stage_seq_static_c #(.NOPS(NOPS),.STAGE(STAGE),.ENG_PRESENT(PRESENT))u_s(
  .ckv(ckv),.rsv(rsv),.ck(ck),.rst(rst),.f_ks(f_ks),.t_kd(t_kd),.f_pw(f_pw),.f_plen(f_plen),.t_st(t_st),
  .c0(c0),.c1(c1),.c2(c2),.c3(c3),.c4(c4),.c5(c5),.c6(c6),.c7(c7),.c8(c8_nc),.c9(c9_nc),.c10(c10_nc),.c11(c11_nc),.c12(c12),
  .d0(d0),.d1(d1),.d2(d2),.d3(d3),.d4(d4),.d5(d5),.d6(d6),.d7(d7),.d8(9'd0),.d9(9'd0),.d10(9'd0),.d11(9'd0),.d12(d12),.d13(9'd0),
  .s0(s0),.s1(s1),.s2(s2),.s3(s3),.s4(s4),.s5(s5),.s6(s6),.s7(s7),.s8(2'd0),.s9(2'd0),.s10(2'd0),.s11(2'd0),.s12(s12),.s13(2'd0));
endmodule
`default_nettype wire
