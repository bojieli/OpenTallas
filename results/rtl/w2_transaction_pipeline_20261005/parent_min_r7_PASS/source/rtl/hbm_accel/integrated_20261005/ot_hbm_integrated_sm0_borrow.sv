`timescale 1ns/1ps
// One shared ledger, once per selected SM0/AW3 CDC. No parallel SU/W2/index
// owner. Native outstanding response debt retires before a borrower can GO.
// External native_clients_drained/cdc_drained MUST be real enclosing debt;
// FIFO empty alone does not prove that a previously accepted HBM job finished.
module ot_hbm_integrated_sm0_borrow #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire native_clients_drained,cdc_drained,
 input wire [3:0] observe_req,observe_rsp,observe_req_we,observe_rsp_we,
 input wire [63:0] observe_req_tag,observe_rsp_tag,
 input wire [3:0] return_offer,output wire [3:0] response_authorized,
 input wire [31:0] native_job,input wire [3:0] native_gen,
 input wire [16:0] native_token,input wire [19:0] native_pos,
 output wire native_credit_empty,
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
 assign m_rsp_rdy=0;assign idle=0;assign fault=0;assign native_credit_empty=0;assign response_authorized=0;
 end else begin:on
 // Five control rows charged to bridge/control allowance; passive prior
 // ledger below is exactly2592 FF ONCE. No nested SU borrowing wrapper.
 wire prior_debt,prior_violation,prior_bad;
 ot_hbm_integrated_prior_debt #(.ENABLE(1),.NC(4)) u_prior(
  .clk(clk),.por_n(por_n),.observe_req(observe_req),.observe_rsp(observe_rsp),
  .observe_req_we(observe_req_we),.observe_rsp_we(observe_rsp_we),
  .observe_req_tag(observe_req_tag),.observe_rsp_tag(observe_rsp_tag),
  .debt(prior_debt),.violation(prior_violation),.uncorrectable(prior_bad),
  .return_offer(return_offer),.response_authorized(response_authorized),
  .native_job(native_job),.native_gen(native_gen),.native_token(native_token),.native_pos(native_pos));
 reg [71:0] control_code,frame_lo,frame_hi,debt_code,quiet_code;
 wire [65:0] c=decode64(control_code),fl=decode64(frame_lo),fh=decode64(frame_hi),
  debt=decode64(debt_code),q=decode64(quiet_code);
 wire bad=c[65]||fl[65]||fh[65]||debt[65]||q[65];
 wire owned=c[0],failed=c[1];wire [1:0] owner=c[3:2];
 wire outstanding=debt[0];wire [1:0] return_route=debt[2:1];
 wire held_we=debt[3];wire [15:0] held_tag=debt[19:4];
 wire request_sent=debt[20],rq_captured=debt[21],rs_captured=debt[22];
 wire [3:0] rq_age=debt[26:23],rs_age=debt[30:27];
 reg [71:0] request_hold[0:5],response_hold[0:4];
 wire [383:0] request_raw;wire [319:0] response_raw;
 wire [5:0] rq_bad;wire [4:0] rs_bad;
 for(genvar k=0;k<6;k=k+1)begin:request_rows
  wire [65:0] d=decode64(request_hold[k]);assign request_raw[k*64+:64]=d[63:0];assign rq_bad[k]=|d[65:64];
 end
 for(genvar k=0;k<5;k=k+1)begin:response_rows
  wire [65:0] d=decode64(response_hold[k]);assign response_raw[k*64+:64]=d[63:0];assign rs_bad[k]=|d[65:64];
 end
 wire [127:0] frame={fh[63:0],fl[63:0]};
 wire [1:0] route=owned?owner+2'd1:2'd0;
 wire [2:0] wanted=lease_v&borrower_quiet;
 reg [1:0] pick;reg have;
 always @*begin
  pick=0;have=0;
  for(integer k=2;k>=0;k=k-1)if(wanted[k])begin pick=2'(k);have=1;end
 end
 wire other_quiet=(borrower_quiet|(3'b001<<pick))==3'b111;
 assign native_credit_empty=!prior_debt&&!(|observe_req)&&!(|observe_rsp)&&!fault;
 wire safe=native_clients_drained&&cdc_drained&&native_credit_empty&&!outstanding&&have&&other_quiet&&!req_v[0];
 wire release_match=release_job[owner*32+:32]==frame[31:0]&&
  release_gen[owner*4+:4]==frame[35:32]&&release_token[owner*17+:17]==frame[52:36]&&
  release_pos[owner*20+:20]==frame[72:53];
 assign fault=bad||failed||prior_bad||(rq_captured&&|rq_bad)||(rs_captured&&|rs_bad);
 assign idle=!owned&&!outstanding&&!fault;
 assign lease_granted=owned&&!fault?(3'b001<<owner):3'b0;
 // ONE common protected tuple path for every raw route, including SU.
 // Source holds through encode2; captured tuple holds through decode3.
 wire source_v=req_v[route];
 wire [336:0] source_req={req_we[route],req_addr[route*32+:32],req_wdata[route*256+:256],
                         req_wstrb[route*32+:32],req_tag[route*16+:16]};
 wire source_ready=!outstanding&&!rq_captured&&rq_age==2&&!fault;
 assign req_rdy=source_v&&source_ready?(4'b0001<<route):0;
 wire source_accept=source_v&&source_ready;
 assign m_req_v=rq_captured&&rq_age==5&&!fault;
 assign {m_req_we,m_req_addr,m_req_wdata,m_req_wstrb,m_req_tag}=request_raw[336:0];
 wire response_match=outstanding&&request_sent&&m_rsp_tag==held_tag&&m_rsp_we==held_we;
 assign m_rsp_rdy=response_match&&!rs_captured&&rs_age==2&&!fault;
 assign rsp_v=rs_captured&&rs_age==5&&!fault?(4'b0001<<return_route):0;
 for(genvar k=0;k<4;k=k+1)begin:responses
  assign rsp_we[k]=response_raw[256];assign rsp_tag[k*16+:16]=response_raw[272:257];
  assign rsp_data[k*256+:256]=response_raw[255:0];
 end
 wire sink_accept=rs_captured&&rs_age==5&&!fault&&rsp_rdy[return_route];
 assign release_r=owned&&!outstanding&&!rq_captured&&!rs_captured&&cdc_drained&&native_credit_empty&&
  release_match&&!fault&&!req_v[route]?(3'b001<<owner):0;
 reg [127:0] new_frame;reg [63:0] next_debt;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin control_code<=encode64(0);frame_lo<=encode64(0);frame_hi<=encode64(0);
   debt_code<=encode64(0);quiet_code<=encode64(0);
   for(integer k=0;k<6;k=k+1)request_hold[k]<=encode64(0);
   for(integer k=0;k<5;k=k+1)response_hold[k]<=encode64(0);end
  else if(fault||prior_violation||(m_rsp_v&&!response_match)||
    (owned&&release_v[owner]&&!release_match)||
    (owned&&((borrower_quiet|(3'b001<<owner))!=3'b111)))control_code<=encode64(2);
  else begin
   next_debt=debt[63:0];
   if(!outstanding&&!rq_captured)begin
    if(source_v)begin
     if(rq_age<2)next_debt[26:23]=rq_age+1;
     if(source_accept)begin
      for(integer k=0;k<6;k=k+1)request_hold[k]<=encode64(64'(384'(source_req)>>(64*k)));
      next_debt[0]=1;next_debt[2:1]=route;next_debt[3]=source_req[336];
      next_debt[19:4]=source_req[15:0];next_debt[20]=0;next_debt[21]=1;next_debt[26:23]=3;
     end
    end else next_debt[26:23]=0;
   end else if(rq_captured&&rq_age<5)next_debt[26:23]=rq_age+1;
   if(m_req_v&&m_req_rdy)begin next_debt[21]=0;next_debt[26:23]=0;next_debt[20]=1;end
   if(m_rsp_v&&!rs_captured&&response_match)begin
    if(rs_age<2)next_debt[30:27]=rs_age+1;
    if(m_rsp_rdy)begin
     for(integer k=0;k<5;k=k+1)response_hold[k]<=encode64(64'(320'({m_rsp_tag,m_rsp_we,m_rsp_data})>>(64*k)));
     next_debt[22]=1;next_debt[30:27]=3;
    end
   end else if(rs_captured&&rs_age<5)next_debt[30:27]=rs_age+1;
   if(sink_accept)next_debt=0;
   debt_code<=encode64(next_debt);
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
