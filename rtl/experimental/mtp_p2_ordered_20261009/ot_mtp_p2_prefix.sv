`timescale 1ns/1ps
`default_nettype none
// Exact +0,E0,E1,E2 prefix; systematic Hsiao code matches ordered transport.
//
// el1011-ds-mtp [p2pfx] 2026-10-11: STREAMING rebuild (owner throughput rule: the serial FSM measured 6,092 / 5,467 =
// 1.114 in the wave bench; ~17-20 states per word x 320 words + an 80-word serial drain).  Words are independent: word w
// of expert e reads the accumulator word written by expert e-1 >= 80 accepts earlier, so a fixed 16-cycle pipeline
// accepts one word per cycle with no RAW hazard.  An 80-bit in-flight vector (set at read issue, cleared at write)
// enforces it: an accumulate read of an in-flight word is a FAULT, a drain read of one stalls.
//
//  stage 1  accept regs (code + meta + expected expert / word snapshot); meta compare -> fault; SRAM read from the
//           REGISTERED word (expert != 0); input SECDED decode starts            (drain: credit-gated read issue)
//  stage 2  SRAM clk->q                       stage 3  mcap = registered SRAM capture; input decode out -> di_q / flags
//  stage 4  input UE / native-bad -> fault    stage 5  accumulator decode out -> add_a (+0 for expert 0), add_b, flags
//  stage 6  accumulator UE -> fault; 16-lane LAT8 ot_v41_fadd issue      (drain: SECDED encode of add_a)
//  stage 7  (drain) push into the 4-entry credit-counted output queue
//  stage 14 fadd out -> sum_q / err_q        stage 15 adder err -> fault; SECDED encode        stage 16 SRAM write
// Every fault / corrected semantic of the FSM is kept (identity / expert / word / row_last / transaction_last, input UE,
// native-bad, adder err, accumulator UE, abort, the duplicated-control compare); MUT_COPY_FIRST copies E0 instead of
// adding it to +0.  BREG keeps its meaning (registered duplicate-state gating); DSTAGE / ROOTPIPE are now no-ops (every
// verdict is registered).  The probe names state (11 = write stage), expert_index, word_index, sum_q describe stage 15.
// EXT_ADD=1 (el1011-ds-mtp [p2pfx] hierarchical rebuild 2026-10-11): the 16-lane adder array is the separate hard tile
// ot_p2h_fadd16 (its own clock tree; input pin flops + LAT8 ot_v41_fadd, registered outputs), driven from the add_a /
// add_b / issue-valid registers through the x_add_* ports; FL = 10 (fadd tile input register + 8 + arith result pin register).
module ot_mtp_p2_prefix #(parameter integer ENABLE=0, MUT_COPY_FIRST=0, BREG=0, DSTAGE=0, ROOTPIPE=0, EXT_ADD=0)(
 input wire clk,rst_n,start_v, output wire start_r,
 input wire [73:0] start_identity,input wire [26:0] start_ids,
 input wire in_v,output wire in_r,input wire [73:0] in_identity,
 input wire [8:0] in_expert,input wire in_shared,in_row_last,in_transaction_last,
 input wire [6:0] in_word,input wire [575:0] in_secded,
 output wire out_v,input wire out_r,output wire [73:0] out_identity,
 output wire [6:0] out_word,output wire out_last,output wire [575:0] out_secded,
 input wire abort,output wire done,fault,corrected,
 output wire x_add_v,output wire [511:0] x_add_a,x_add_b,
 input wire [511:0] x_add_y,input wire [31:0] x_add_err,input wire [15:0] x_add_vo
);
 generate if(!ENABLE) begin: disabled
 assign start_r=0;assign in_r=0;assign out_v=0;assign out_identity=0;
 assign out_word=0;assign out_last=0;assign out_secded=0;
 assign done=0;assign fault=0;assign corrected=0;
 assign x_add_v=0;assign x_add_a=0;assign x_add_b=0;
 end else begin: enabled
 localparam [1:0] P_IDLE=0,P_ACC=1,P_DRAIN=2;
 localparam integer FL=EXT_ADD?10:8; // ot_v41_fadd LATENCY at CUT 1_0111_1011 (+1: ot_p2h_fadd16 input pin flops, +1: ot_p2h_arith result pin flops) (checked: add_v vs tag valid)
 localparam integer S_ADD=6, S_SUM=S_ADD+FL, S_WR=S_SUM+2;   // 6, 14, 16
 localparam integer QD=4;          // output queue entries = drain credits
 // ---------------- control (duplicated) ----------------
 reg [1:0] phase,phase_c;reg [1:0] eidx,eidx_c;reg [6:0] widx,widx_c;
 reg [73:0] identity,identity_c;reg [26:0] ids,ids_c;
 reg [6:0] diw,diw_c;              // drain read-issue word (80 = all issued)
 reg [2:0] cred,cred_c;            // outstanding drain beats (issued, not yet popped)
 reg [1:0] qwp,qwp_c,qrp,qrp_c;reg [2:0] qcnt,qcnt_c;
 reg fault_q,done_q,corrected_q,bad_q;
 wire bad=(phase!=phase_c)||(eidx!=eidx_c)||(widx!=widx_c)||(identity!=identity_c)||(ids!=ids_c)||
   (diw!=diw_c)||(cred!=cred_c)||(qwp!=qwp_c)||(qrp!=qrp_c)||(qcnt!=qcnt_c);
 wire healthy=!fault_q&&!(BREG?bad_q:bad)&&!abort;
 assign start_r=healthy&&phase==P_IDLE;
 assign in_r=healthy&&phase==P_ACC;
 assign done=done_q;assign fault=fault_q||bad;assign corrected=corrected_q;
 wire accept=in_v&&in_r;
 // ---------------- stage 1: accept registers ----------------
 reg a_v;reg [575:0] a_code;reg [73:0] a_id;reg [8:0] a_exp,a_xexp;reg a_sh,a_rl,a_tl;reg [6:0] a_w,a_w_in;reg [1:0] a_e;
 always @(posedge clk)if(accept)begin a_code<=in_secded;a_id<=in_identity;a_exp<=in_expert;a_sh<=in_shared;
   a_rl<=in_row_last;a_tl<=in_transaction_last;a_w_in<=in_word;a_w<=widx;a_e<=eidx;a_xexp<=ids[9*eidx+:9];end
 wire a_meta_bad=(a_id!=identity)||(a_exp!=a_xexp)||a_sh||(a_w!=a_w_in)||(a_rl!=(a_w==79))||(a_tl!=((a_e==2)&&(a_w==79)));
 // ---------------- in-flight vector (RAW hazard assertion) ----------------
 reg [79:0] inflight;
 // ---------------- drain issue ----------------
 wire d_issue=healthy&&phase==P_DRAIN&&!a_v&&(diw<80)&&(cred<QD)&&!inflight[diw];
 // ---------------- tag pipeline: stages 2..S_WR ----------------
 reg t_v[2:S_WR];reg t_dr[2:S_WR];reg [1:0] t_e[2:S_WR];reg [6:0] t_w[2:S_WR];
 integer k;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin for(k=2;k<=S_WR;k=k+1)t_v[k]<=0;end
  else begin t_v[2]<=a_v||d_issue;for(k=3;k<=S_WR;k=k+1)t_v[k]<=t_v[k-1];end
 always @(posedge clk)begin
  t_dr[2]<=d_issue;t_e[2]<=d_issue?2'd0:a_e;t_w[2]<=d_issue?diw:a_w;
  for(k=3;k<=S_WR;k=k+1)begin t_dr[k]<=t_dr[k-1];t_e[k]<=t_e[k-1];t_w[k]<=t_w[k-1];end
 end
 // ---------------- codecs, memories, adders ----------------
 wire [511:0] input_data,acc_data,add_data;
 wire [7:0] iov,ice,iue,aov,ace,aue;
 wire [15:0] add_v;wire [31:0] add_err;wire [767:0] mem_q;
 wire [575:0] encoded,d_encoded;
 reg [575:0] mcap;                      // stage 3: registered SRAM capture
 reg [511:0] di_q,di_q2,add_a,add_b,sum_q;
 wire a_rd=a_v&&a_e!=0;
 wire r_ce=a_rd||d_issue;
 wire [6:0] r_addr=d_issue?diw:a_w;
 wire w_ce=t_v[S_WR]&&!t_dr[S_WR]&&!fault_q&&!bad_q;
 wire acc_use3=t_v[3]&&(t_dr[3]||t_e[3]!=0);
 for(genvar slice=0;slice<8;slice=slice+1)begin: codecs
 ot_secded_dec #(.K(64),.R(8)) id(.clk(clk),.rst_n(rst_n),.v(a_v),
 .w(a_code[72*slice+:72]),.ov(iov[slice]),.d(input_data[64*slice+:64]),
 .ce(ice[slice]),.ue(iue[slice]),.n_ce(),.n_ue());
 ot_secded_dec #(.K(64),.R(8)) ad(.clk(clk),.rst_n(rst_n),.v(acc_use3),
 .w(mcap[72*slice+:72]),.ov(aov[slice]),.d(acc_data[64*slice+:64]),
 .ce(ace[slice]),.ue(aue[slice]),.n_ce(),.n_ue());
 ot_secded_enc #(.K(64),.R(8)) enc(.clk(clk),.d(sum_q[64*slice+:64]),.q(encoded[72*slice+:72]));
 ot_secded_enc #(.K(64),.R(8)) denc(.clk(clk),.d(add_a[64*slice+:64]),.q(d_encoded[72*slice+:72]));
 end
 if(EXT_ADD)begin: ext_adds
 assign x_add_v=t_v[S_ADD]&&!t_dr[S_ADD];assign x_add_a=add_a;assign x_add_b=add_b;
 assign add_data=x_add_y;assign add_err=x_add_err;assign add_v=x_add_vo;
 end else begin: int_adds
 assign x_add_v=0;assign x_add_a=0;assign x_add_b=0;
 for(genvar lane=0;lane<16;lane=lane+1)begin: adds
 ot_v41_fadd #(.CUT(9'b1_0111_1011),.SPLIT9(0)) a(.clk(clk),.rst_n(rst_n),
 .valid_in(t_v[S_ADD]&&!t_dr[S_ADD]),.a(add_a[32*lane+:32]),.b(add_b[32*lane+:32]),
 .y(add_data[32*lane+:32]),.err(add_err[2*lane+:2]),.valid_out(add_v[lane]));
 end
 end
 for(genvar mi=0;mi<3;mi=mi+1)begin: memories
 wire [767:0] mw={192'd0,encoded};
 ot_sram_1r1w_128x256_m1_r2c2 m(.clk(clk),.r_ce_in(r_ce),
 .r_addr_in(r_addr),.rd_out(mem_q[256*mi+:256]),.w_ce_in(w_ce),
 .w_addr_in(t_w[S_WR]),.wd_in(mw[256*mi+:256]),.w_mask_in({256{1'b1}}),
 .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end
 reg input_native_bad;integer lane;
 always @*begin input_native_bad=0;
 for(lane=0;lane<16;lane=lane+1)if(input_data[32*lane+:16]!=0)input_native_bad=1;
 end
 // ---------------- datapath registers (no reset) ----------------
 reg ue_q,nb_q,ce_q,f_ue,f_ce,err_q;
 wire [511:0] b_dly;
 wire acc_beat3=t_v[3]&&!t_dr[3];
 always @(posedge clk)begin
  mcap<=mem_q[575:0];
  di_q<=input_data;di_q2<=di_q;
  add_a<=(t_e[5]==0&&!t_dr[5])?512'd0:acc_data;add_b<=di_q2;
  sum_q<=(MUT_COPY_FIRST&&t_e[S_SUM]==0)?b_dly:add_data;
 end
 // MUT_COPY_FIRST: E0 is copied (b delayed through the adder latency) instead of added to +0
 if(MUT_COPY_FIRST)begin: mut_copy
  reg [511:0] bd[1:FL];integer j;
  always @(posedge clk)begin bd[1]<=add_b;for(j=2;j<=FL;j=j+1)bd[j]<=bd[j-1];end
  assign b_dly=bd[FL];
 end else begin: no_mut
  assign b_dly=512'd0;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin ue_q<=0;nb_q<=0;ce_q<=0;f_ue<=0;f_ce<=0;err_q<=0;end
  else begin
   ue_q<=acc_beat3&&(|iue);nb_q<=acc_beat3&&input_native_bad;ce_q<=acc_beat3&&(|ice);
   f_ue<=t_v[5]&&(t_dr[5]||t_e[5]!=0)&&(|aue);f_ce<=t_v[5]&&(t_dr[5]||t_e[5]!=0)&&(|ace);
   err_q<=t_v[S_SUM]&&!t_dr[S_SUM]&&(|add_err);
  end
 // structural alignment checks (a mis-timed decoder / adder is a fault, never silent data)
 wire align_bad=((&iov)!=acc_beat3)||((|iov)!=acc_beat3)||
   ((&aov)!=(t_v[5]&&(t_dr[5]||t_e[5]!=0)))||((|aov)!=(&aov))||
   ((&add_v)!=(t_v[S_SUM]&&!t_dr[S_SUM]))||((|add_v)!=(&add_v));
 // ---------------- output queue (drain), credit-counted ----------------
 reg [575:0] q_code[0:QD-1];reg [6:0] q_word[0:QD-1];reg q_last[0:QD-1];
 reg qne;                                   // registered "queue non-empty"
 wire push=t_v[7]&&t_dr[7]&&!fault_q;
 wire pop=out_v&&out_r;
 assign out_v=healthy&&qne;
 assign out_secded=q_code[qrp];assign out_word=q_word[qrp];assign out_last=q_last[qrp];
 assign out_identity=identity;
 always @(posedge clk)if(push)begin q_code[qwp]<=d_encoded;q_word[qwp]<=t_w[7];q_last[qwp]<=t_w[7]==79;end
 // probe names (stage 15 = the write-data stage; tb_mtp_p2_prefix's MUT_COPY_FIRST probe)
 wire [4:0] state=(t_v[S_SUM+1]&&!t_dr[S_SUM+1])?5'd11:5'd0;
 wire [1:0] expert_index=t_e[S_SUM+1];wire [6:0] word_index=t_w[S_SUM+1];
 wire [2:0] qcnt_nx=qcnt+(push?3'd1:3'd0)-(pop?3'd1:3'd0);
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin phase<=P_IDLE;phase_c<=P_IDLE;eidx<=0;eidx_c<=0;widx<=0;widx_c<=0;
  identity<=0;identity_c<=0;ids<=0;ids_c<=0;diw<=0;diw_c<=0;cred<=0;cred_c<=0;
  qwp<=0;qwp_c<=0;qrp<=0;qrp_c<=0;qcnt<=0;qcnt_c<=0;qne<=0;
  fault_q<=0;done_q<=0;corrected_q<=0;bad_q<=0;a_v<=0;inflight<=0;end
 else begin done_q<=0;bad_q<=bad;a_v<=accept;
  if(bad||abort||phase==2'd3)fault_q<=1;
  // stage-1 verdicts
  if(a_v&&(a_meta_bad||inflight[a_w]))fault_q<=1;
  // stage-4 / 6 / 15 verdicts
  if(ue_q||nb_q||f_ue||err_q||align_bad)fault_q<=1;
  if(ce_q||f_ce)corrected_q<=1;
  // in-flight words: set at read issue (stage 1), cleared at write (stage 16)
  if(w_ce)inflight[t_w[S_WR]]<=1'b0;
  if(a_v)inflight[a_w]<=1'b1;
  // output queue
  if(push)begin qwp<=qwp+1;qwp_c<=qwp_c+1;if(qcnt==QD&&!pop)fault_q<=1;end
  if(pop)begin qrp<=qrp+1;qrp_c<=qrp_c+1;end
  qcnt<=qcnt_nx;qcnt_c<=qcnt_nx;qne<=qcnt_nx!=0;
  if(d_issue&&!pop)begin cred<=cred+1;cred_c<=cred_c+1;end
  else if(pop&&!d_issue)begin cred<=cred-1;cred_c<=cred_c-1;end
  if(d_issue)begin diw<=diw+1;diw_c<=diw_c+1;end
  if(healthy)case(phase)
  P_IDLE:if(start_v&&start_r)begin
   if(!(start_ids[8:0]<start_ids[17:9]&&start_ids[17:9]<start_ids[26:18]&&start_ids[26:18]<384))fault_q<=1;
   else begin identity<=start_identity;identity_c<=start_identity;ids<=start_ids;ids_c<=start_ids;
    eidx<=0;eidx_c<=0;widx<=0;widx_c<=0;corrected_q<=0;phase<=P_ACC;phase_c<=P_ACC;end end
  P_ACC:if(accept)begin
   if(widx==79)begin widx<=0;widx_c<=0;
    if(eidx==2)begin phase<=P_DRAIN;phase_c<=P_DRAIN;diw<=0;diw_c<=0;cred<=0;cred_c<=0;end
    else begin eidx<=eidx+1;eidx_c<=eidx_c+1;end end
   else begin widx<=widx+1;widx_c<=widx_c+1;end end
  P_DRAIN:if(pop&&out_last)begin done_q<=1;phase<=P_IDLE;phase_c<=P_IDLE;end
  default:fault_q<=1;
  endcase end end
 end endgenerate
endmodule
`default_nettype wire
