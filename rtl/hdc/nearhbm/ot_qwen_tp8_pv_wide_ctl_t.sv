`timescale 1ns/1ps
// KVPLAN 1815 (2026-10-16, COORDINATOR STANDARD item 1): the PV pair control tile for the TRUNKED pair successor
// (ot_qwen_tp8_pv_wide_pair_t).  Identical to ot_qwen_tp8_pv_wide_ctl (rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv, unchanged,
// its closed kits stay valid) except two static parameters of the die distribution:
//   TRUNK_D  registered station stages between this tile's cmd pin register and every tile's command pin (the V / e words
//            take the same TRUNK_D stages from the pair face, so command and data meet exactly as in the original pair);
//   FLAG_D   registered stages from every column's y_valid / fault pins back to col_valid / col_fault here.
// The column output check slot moves by TRUNK_D + FLAG_D (COL_CHK), the static output age by TRUNK_D; wage widens 6 -> 8 b.
// Defaults TRUNK_D = FLAG_D = 0 reproduce the original tile cycle for cycle (pinned by the pair_t bench at D = 0).
// Pair control tile: calendar walk, V requests, arrival identity per port, the column command word, output check.
// Every port is registered at the pin: inputs (start/context/epoch, arrival identities, column flags) one edge in,
// outputs (V requests, command word, flags, out_age) one edge out. Internal age 'pa' counts from the registered start.
module ot_qwen_tp8_pv_wide_ctl_t #(parameter integer FIRST_INPUT_AGE=20,parameter integer RESET_PIN=0,
 parameter integer TRUNK_D=0,   // registered stages ctl cmd pin -> every tile's command pin (balanced, KVPLAN trunk)
 parameter integer FLAG_D=0     // registered stages every column flag pin -> this tile's col_valid / col_fault pins (balanced)
)(
 input wire clk,rst_n,
 input wire pair_id,                            // die strap: one master serves both pairs
 input wire start,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[7:0] in_valid,input wire[111:0] in_t,input wire[127:0] in_epoch,
 output reg[7:0] req_valid,output reg[111:0] req_t,
 output reg[59:0] cmd,input wire[31:0] col_valid,input wire[31:0] col_fault,
 output reg[15:0] out_epoch,output reg fault,output reg busy,output reg[15:0] out_age
);
 wire local_rst_n;
 generate if(RESET_PIN)begin:g_reset_pin
  // The reset input ends at this pin flop. Cold release is one edge later;
  // production start and every scheduled data edge are unchanged.
  (* keep *)reg rst_q;
  always @(posedge clk)rst_q<=rst_n;
  assign local_rst_n=rst_q;
 end else begin:g_reset_legacy
  assign local_rst_n=rst_n;
 end endgenerate

 localparam IDLE=0,FEED=1,DRAIN=2,TRA=3,TRB=4,TRADD=5,TRDRAIN=6,JOIN=7;
 localparam integer FIRSTI=FIRST_INPUT_AGE+1;      // + the request pin register: arrival pa of q = 0
 localparam integer JGO=2;                       // join_go 2 edges into JOIN: bank tree sums cross the bank out + join in pin regs
 localparam integer COL_LAT=JGO+3+3*7+3+1;      // JOIN -> column y_valid: + cmd reg, join pin reg, jrun start, J_OUT 24, y reg
 localparam integer COL_CHK=COL_LAT+TRUNK_D+FLAG_D;   // KVPLAN trunk: the column flags reach this tile TRUNK_D + FLAG_D later
 // ---- input pin registers ----
 reg start_r;reg[13:0] ctx_r;reg[15:0] epoch_r;reg[7:0] iv_r;reg[111:0] it_r;reg[127:0] ie_r;reg[31:0] cv_r,cf_r;
 reg pid;                                         // pair_id strap, registered (constant; the gate saw pair_id -> wage 15 levels)
 always @(posedge clk)pid<=pair_id;
 always @(posedge clk or negedge local_rst_n)
  if(!local_rst_n)begin start_r<=0;iv_r<=0;cv_r<=0;cf_r<=0;end
  else begin start_r<=start;iv_r<=in_valid;cv_r<=col_valid;cf_r<=col_fault;end
 always @(posedge clk)begin ctx_r<=context_len;epoch_r<=epoch;it_r<=in_t;ie_r<=in_epoch;end
 reg[3:0] state;reg[15:0] age;reg[15:0] ep;reg[13:0] lim;reg[15:0] nq;reg flt;
 reg[4:0] nodes;reg[2:0] ti;reg[3:0] drain_left,reduce_left;reg[7:0] wage;
 wire[15:0] pa=age+16'd1;                         // cycles since the registered start
 // checks: the registered arrival seen at pa arrived at pa-1, i.e. q = pa - 1 - FIRSTI
 wire[15:0] qc=pa-16'd1-16'(FIRSTI);
 wire chk_window=(state!=IDLE)&&pa>=16'(FIRSTI+1)&&qc<nq;
 wire[11:0] rc=qc[15:4];wire[3:0] ac=qc[3:0];
 // slice takes: the command word for the arrival at pa+1 (cmd reg + column pin reg = 2 edges, payload 1 edge)
 wire[15:0] qn=pa+16'd1-16'(FIRSTI);
 wire next_window=(state==FEED)&&pa+16'd1>=16'(FIRSTI)&&qn<nq;
 wire[11:0] rn=qn[15:4];wire[3:0] an=qn[3:0];
 reg[7:0] exp_take,pexp_v;reg[13:0] pexp_t[0:7];
 integer l,wn,wt,wp;                          // loop temporaries (blocking, combinational only; no automatic decls for yosys)
 always @*begin
  exp_take=0;pexp_v=0;wn=0;wt=0;wp=0;
  for(l=0;l<8;l=l+1)pexp_t[l]=0;
  // per PORT (constant index): port wp carries bank l = (wp&3) + 4h of step n = rc - h with n&1 == wp>>2, i.e.
  // h = (rc ^ (wp>>2)) & 1 -- the same (bank, step) -> port map as before, without a runtime-indexed write
  for(wp=0;wp<8;wp=wp+1)begin
   l=(wp&3)+4*((int'(rc)^(wp>>2))&1);
   wn=int'(rc)-(l>>2);
   wt=256*wn+128*int'(pid)+16*l+int'(ac);
   if(chk_window&&wn>=0&&wt<int'(lim))begin pexp_v[wp]=1'b1;pexp_t[wp]=14'(wt);end
  end
  for(l=0;l<8;l=l+1)begin
   wn=int'(rn)-(l>>2);
   wt=256*wn+128*int'(pid)+16*l+int'(an);
   if(next_window&&wn>=0&&wt<int'(lim))exp_take[l]=1'b1;
  end
 end
 wire[7:0] rq;wire[111:0] rqt;
 ot_qwen_tp8_vrow_wide u_req(.clk(clk),.rst_n(local_rst_n),.pair_id(pid),.start(start_r),.context_len(ctx_r),
  .req_valid(rq),.req_t(rqt),.fault());
 always @(posedge clk or negedge local_rst_n)if(!local_rst_n)req_valid<=0;else req_valid<=rq;
 always @(posedge clk)req_t<=rqt;
 reg cbad;integer k;
 wire out_slot=(state==JOIN)&&wage==8'(COL_CHK+1);
 always @*begin
  cbad=0;
  if(state!=IDLE&&iv_r!=pexp_v)cbad=1;
  for(k=0;k<8;k=k+1)if(iv_r[k]&&(it_r[14*k+:14]!=pexp_t[k]||ie_r[16*k+:16]!=ep))cbad=1;
  if(|cf_r)cbad=1;
  if(cv_r!={32{cv_r[0]}})cbad=1;
  if(state!=IDLE&&cv_r[0]!=out_slot)cbad=1;
 end
 // column command word, registered at this tile's output pin (the column registers it again at its input pin)
 wire n0_lo=(rn==0),n0_hi=(rn==1);
 always @(posedge clk or negedge local_rst_n)
  if(!local_rst_n)cmd<=0;
  else begin
   cmd<=0;
   cmd[0]<=rn[0];cmd[8:1]<=exp_take&{8{!flt}};cmd[9]<=n0_lo;cmd[10]<=n0_hi;cmd[14:11]<=an;
   cmd[15]<=(state==FEED)&&pa>=1&&pa<=16;cmd[19:16]<=4'(pa-1);
   cmd[20]<=(state==TRA)||(state==TRB);cmd[24:21]<={ti,1'b0}+4'(state==TRB);
   cmd[25]<=state==TRADD;cmd[26]<=state==TRB;cmd[27]<=nodes==2;cmd[30:28]<=ti;
   cmd[31]<=(state==JOIN)&&wage==8'(JGO);
  end
 // output pin registers: flags and the static output age (service cycles after start_pv: + the start pin register)
 always @(posedge clk or negedge local_rst_n)
  if(!local_rst_n)begin fault<=0;busy<=0;out_age<=0;out_epoch<=0;end
  else begin
   fault<=flt;busy<=state!=IDLE;out_epoch<=ep;
   out_age<=16'd1+16'(FIRSTI)+nq-16'd1+16'd13+16'd73+16'(COL_LAT)+16'(TRUNK_D);
  end
 always @(posedge clk or negedge local_rst_n)begin
  if(!local_rst_n)begin state<=IDLE;flt<=0;age<=0;ep<=0;lim<=0;nq<=0;nodes<=0;ti<=0;drain_left<=0;reduce_left<=0;wage<=0;end
  else if((start_r&&state!=IDLE)||(state!=IDLE&&cbad))begin state<=IDLE;flt<=1;end
  else begin
   if(state!=IDLE)age<=age+1'b1;
   case(state)
    IDLE:if(start_r)begin
     ep<=epoch_r;lim<=ctx_r;age<=0;
     nq<=(ctx_r>14'(128*int'(pid)))?16'(16*(((int'(ctx_r)-128*int'(pid)+255)>>8)+1)):16'd0;
     if(ctx_r==0||ctx_r>8192)flt<=1;else state<=FEED;
    end
    FEED:if(pa>=16'(FIRSTI)+nq-16'd1&&pa>=16'd16)begin state<=DRAIN;drain_left<=12;end
    DRAIN:begin
     drain_left<=drain_left-1'b1;
     if(drain_left<=1)begin nodes<=16;ti<=0;state<=TRA;end
    end
    TRA:state<=TRB;
    TRB:state<=TRADD;
    TRADD:begin reduce_left<=7;if(5'(ti)+1==nodes/2)state<=TRDRAIN;else begin ti<=ti+1'b1;state<=TRA;end end
    TRDRAIN:begin
     reduce_left<=reduce_left-1'b1;
     if(reduce_left==1)begin
      if(nodes==2)begin state<=JOIN;wage<=0;end else begin nodes<=nodes/2;ti<=0;state<=TRA;end
     end
    end
    JOIN:begin wage<=wage+1'b1;if(wage==8'(COL_CHK+1))state<=IDLE;end
    default:;
   endcase
  end
 end
endmodule

