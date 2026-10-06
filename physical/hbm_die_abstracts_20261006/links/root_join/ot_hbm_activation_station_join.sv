`timescale 1ns/1ps
// Actual VM root + four copies of ONE parameterized station implementation.
// Owner-selected order SW/SE/NW/NE. Fanout0 is unresolved, not an assumed1.
// ENABLE0 inert; enabled integration must explicitly bind every real fanout.
// Cold POR only. Warm request is quiesce/drain, never an ownership reset.
module ot_hbm_activation_station_join #(
 parameter integer ENABLE=0,F_SW=0,F_SE=0,F_NW=0,F_NE=0,
 parameter integer N_SW=(F_SW>0?F_SW:1),N_SE=(F_SE>0?F_SE:1),
 parameter integer N_NW=(F_NW>0?F_NW:1),N_NE=(F_NE>0?F_NE:1),
 parameter integer NOUT=N_SW+N_SE+N_NW+N_NE
)(
 input wire clk_stream,por_stream_n,warm_req,
 input wire wr_v,output wire wr_ready,input wire wr_bank,input wire [6:0] wr_addr,
 input wire [2062:0] wr_data,input wire [191:0] wr_owner,
 output wire wr_ACK_v,input wire wr_ACK_ready,output wire [191:0] wr_ACK_owner,
 input wire rd_v,output wire rd_ready,input wire rd_bank,input wire [6:0] rd_addr,input wire [191:0] rd_owner,
 output wire [3:0] fclk_o,
 output wire [NOUT-1:0] out_v,input wire [NOUT-1:0] out_r,
 output wire [NOUT*2063-1:0] out_data,output wire [NOUT*192-1:0] out_owner,
 input wire [NOUT-1:0] ACK_v,input wire [NOUT*192-1:0] ACK_owner,
 output wire native_release,activation_drained,warm_drained,paused,fault
);
 initial if(ENABLE)begin
  if(F_SW<1||F_SW>4||F_SE<1||F_SE>4||F_NW<1||F_NW>4||F_NE<1||F_NE>4)
   $fatal(1,"bind actual SW/SE/NW/NE fanout1..4; unresolved count cannot be qualified");
  if(N_SW!=F_SW||N_SE!=F_SE||N_NW!=F_NW||N_NE!=F_NE||NOUT!=F_SW+F_SE+F_NW+F_NE)
   $fatal(1,"no overridden port width/truncated quarter fanout");
 end
 wire root_wr_ready,root_rd_ready,root_drained,root_fault;
 wire [3:0] tap_v,tap_ready,child_release,child_drained,child_paused,child_fault;
 wire [8251:0] tap_data;wire [767:0] tap_owner,root_ACK_owner;
 assign fault=root_fault||(|child_fault);
 assign wr_ready=root_wr_ready&&!warm_req&&!fault;
 assign rd_ready=root_rd_ready&&!warm_req&&!fault;
 ot_hbm_die_vm_multicast_root #(.ENABLE(ENABLE)) u_root(
  .clk(clk_stream),.por_n(por_stream_n),
  .wr_v(wr_v&&!warm_req&&!fault),.wr_ready(root_wr_ready),.wr_bank(wr_bank),.wr_addr(wr_addr),
  .wr_data(wr_data),.wr_owner(wr_owner),.wr_ACK_v(wr_ACK_v),.wr_ACK_ready(wr_ACK_ready),.wr_ACK_owner(wr_ACK_owner),
  .rd_v(rd_v&&!warm_req&&!fault),.rd_ready(root_rd_ready),.rd_bank(rd_bank),.rd_addr(rd_addr),.rd_owner(rd_owner),
  .tap_v(tap_v),.tap_ready(tap_ready),.tap_data(tap_data),.tap_owner(tap_owner),
  .tap_ACK_v(child_release),.tap_ACK_owner(root_ACK_owner),.native_release(native_release),.drained(root_drained),.fault(root_fault));
 for(genvar q=0;q<4;q=q+1)begin:quarter
  localparam integer COUNT=q==0?N_SW:q==1?N_SE:q==2?N_NW:N_NE;
  localparam integer BASE=q==0?0:q==1?N_SW:q==2?N_SW+N_SE:N_SW+N_SE+N_NW;
  wire [COUNT*192-1:0] child_owner;
  ot_hbm_native_station #(.MODE(1),.ENABLE(ENABLE),.W(2063),.IW(2063),.NI(1),.NO(COUNT)) u_station(
   .fclk_i(clk_stream),.rst_n({4{por_stream_n}}),.i_v(1'b0),.i_d(2063'b0),.fclk_o(fclk_o[q]),.o_v(),.o_d(),
   // Do not block acceptance of a root transaction admitted before warm_req.
   // root_drained is false throughout its retained publication/ACK debt.
   .quiesce(warm_req&&root_drained),
   .in_v(tap_v[q]),.in_r(tap_ready[q]),.in_data(tap_data[q*2063+:2063]),.in_owner(tap_owner[q*192+:192]),
   .out_v(out_v[BASE+:COUNT]),.out_r(out_r[BASE+:COUNT]),.out_data(out_data[BASE*2063+:COUNT*2063]),.out_owner(child_owner),
   .ACK_v(ACK_v[BASE+:COUNT]),.ACK_owner(ACK_owner[BASE*192+:COUNT*192]),
   .source_release(child_release[q]),.drained(child_drained[q]),.paused(child_paused[q]),.fault(child_fault[q]));
  assign out_owner[BASE*192+:COUNT*192]=child_owner;
  // At release the input seat is still checked and held; root samples owner
  // on that same edge before the child retires it. No readyless ACK queue cut.
  assign root_ACK_owner[q*192+:192]=child_owner[191:0];
 end
 assign paused=|child_paused;
 assign activation_drained=root_drained&&(&child_drained)&&!fault;
 // Activation-only enclosing drain term. Not CP/global reset_ack and no reset.
 assign warm_drained=ENABLE&&warm_req&&activation_drained;
endmodule
