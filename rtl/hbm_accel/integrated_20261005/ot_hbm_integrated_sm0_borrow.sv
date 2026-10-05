`timescale 1ns/1ps
// One shared ledger, once per selected SM0/AW3 CDC. No parallel SU/W2/index
// owner. Native outstanding response debt retires before a borrower can GO.
// External native_clients_drained/cdc_drained MUST be real enclosing debt;
// FIFO empty alone does not prove that a previously accepted HBM job finished.
module ot_hbm_integrated_sm0_borrow #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire native_clients_drained,cdc_drained,
 // index=0, SU=1, W2=2. Issuers hold tuple and lease request until grant.
 input wire [2:0] lease_v, input wire [2:0] borrower_quiet,
 input wire [95:0] lease_job,input wire [11:0] lease_gen,
 input wire [50:0] lease_token,input wire [59:0] lease_pos,
 output wire [2:0] lease_granted,
 input wire [2:0] release_v,output wire [2:0] release_r,
 input wire [95:0] release_job,input wire [11:0] release_gen,
 input wire [50:0] release_token,input wire [59:0] release_pos,
 // Four real SM-side requesters: native=0,index=1,SU=2,W2=3.
 input wire [3:0] req_v,output wire [3:0] req_rdy,input wire [3:0] req_we,
 input wire [127:0] req_addr,input wire [1023:0] req_wdata,
 input wire [127:0] req_wstrb,input wire [63:0] req_tag,
 output wire [3:0] rsp_v,input wire [3:0] rsp_rdy,output wire [3:0] rsp_we,
 output wire [63:0] rsp_tag,output wire [1023:0] rsp_data,
 output wire m_req_v,input wire m_req_rdy,output wire m_req_we,
 output wire [31:0] m_req_addr,output wire [255:0] m_req_wdata,
 output wire [31:0] m_req_wstrb,output wire [15:0] m_req_tag,
 input wire m_rsp_v,output wire m_rsp_rdy,input wire m_rsp_we,
 input wire [15:0] m_rsp_tag,input wire [255:0] m_rsp_data,
 output wire idle,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE==0)begin:off
 assign lease_granted=0;assign release_r=0;assign req_rdy=0;assign rsp_v=0;
 assign rsp_we=0;assign rsp_tag=0;assign rsp_data=0;
 assign m_req_v=0;assign m_req_we=0;assign m_req_addr=0;
 assign m_req_wdata=0;assign m_req_wstrb=0;assign m_req_tag=0;
 assign m_rsp_rdy=0;assign idle=0;assign fault=0;
 end else begin:on
 // Five protected rows360 FF. 2592 shared model allowance is a ceiling,
 // not padded storage or a physical result. Additional enclosing debt belongs
 // to real source owners and must be counted once at parent integration.
 reg [71:0] control_code,frame_lo,frame_hi,debt_code,quiet_code;
 wire [65:0] c=decode64(control_code),fl=decode64(frame_lo),fh=decode64(frame_hi),
  debt=decode64(debt_code),q=decode64(quiet_code);
 wire bad=c[65]||fl[65]||fh[65]||debt[65]||q[65];
 wire owned=c[0],failed=c[1];wire [1:0] owner=c[3:2];
 wire outstanding=debt[0];wire [1:0] return_route=debt[2:1];
 wire held_we=debt[3];wire [15:0] held_tag=debt[19:4];
 wire [127:0] frame={fh[63:0],fl[63:0]};
 wire [1:0] route=owned?owner+2'd1:2'd0;
 wire [2:0] wanted=lease_v&borrower_quiet;
 reg [1:0] pick;reg have;
 always @*begin
  pick=0;have=0;
  for(integer k=2;k>=0;k=k-1)if(wanted[k])begin pick=2'(k);have=1;end
 end
 wire other_quiet=(borrower_quiet|(3'b001<<pick))==3'b111;
 wire safe=native_clients_drained&&cdc_drained&&!outstanding&&have&&other_quiet&&!req_v[0];
 wire release_match=release_job[owner*32+:32]==frame[31:0]&&
  release_gen[owner*4+:4]==frame[35:32]&&release_token[owner*17+:17]==frame[52:36]&&
  release_pos[owner*20+:20]==frame[72:53];
 assign fault=bad||failed;
 assign idle=!owned&&!outstanding&&!fault;
 assign lease_granted=owned&&!fault?(3'b001<<owner):3'b0;
 // Native requests already presented remain serviceable while a lease waits.
 // safe includes !req_v[0], preventing late-accept/grant races and starvation
 // of an existing held native request. Accepted debt remains routed.
 assign m_req_v=req_v[route]&&!outstanding&&!fault;
 assign m_req_we=req_we[route];assign m_req_addr=req_addr[route*32+:32];
 assign m_req_wdata=req_wdata[route*256+:256];
 assign m_req_wstrb=req_wstrb[route*32+:32];assign m_req_tag=req_tag[route*16+:16];
 assign req_rdy=m_req_v&&m_req_rdy?(4'b0001<<route):4'b0;
 wire response_match=m_rsp_tag==held_tag&&m_rsp_we==held_we;
 assign rsp_v=m_rsp_v&&outstanding&&response_match&&!fault?(4'b0001<<return_route):0;
 assign m_rsp_rdy=outstanding&&response_match&&!fault&&rsp_rdy[return_route];
 for(genvar k=0;k<4;k=k+1)begin:responses
  assign rsp_we[k]=m_rsp_we;assign rsp_tag[k*16+:16]=m_rsp_tag;
  assign rsp_data[k*256+:256]=m_rsp_data;
 end
 assign release_r=owned&&!outstanding&&cdc_drained&&release_match&&!fault&&
  !req_v[route]?(3'b001<<owner):0;
 reg [127:0] new_frame;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin control_code<=encode64(0);frame_lo<=encode64(0);frame_hi<=encode64(0);
   debt_code<=encode64(0);quiet_code<=encode64(0);end
  else if(bad||failed||(m_rsp_v&&(!outstanding||!response_match))||
    (owned&&release_v[owner]&&!release_match)||
    (owned&&((borrower_quiet|(3'b001<<owner))!=3'b111)))control_code<=encode64(2);
  else begin
   if(m_req_v&&m_req_rdy)debt_code<=encode64({44'b0,m_req_tag,m_req_we,route,1'b1});
   if(m_rsp_v&&m_rsp_rdy)debt_code<=encode64(0);
   if(!owned)begin
    if(safe)begin
     // quiet row retains both count and selected borrower so a changed request
     // cannot inherit another requester's quiet interval.
     if(q[3:2]!=pick)quiet_code<=encode64({60'b0,pick,2'd1});
     else if(q[1:0]<2)quiet_code<=encode64({60'b0,pick,q[1:0]+2'd1});
     else begin
      new_frame={55'b0,lease_pos[pick*20+:20],lease_token[pick*17+:17],lease_gen[pick*4+:4],lease_job[pick*32+:32]};
      frame_lo<=encode64(new_frame[63:0]);frame_hi<=encode64(new_frame[127:64]);
      control_code<=encode64({60'b0,pick,1'b0,1'b1});quiet_code<=encode64(0);
     end
    end else quiet_code<=encode64(0);
   end else if(release_v[owner]&&release_r[owner])begin
    control_code<=encode64(0);quiet_code<=encode64(0);
   end
  end
 end
 end endgenerate
endmodule
