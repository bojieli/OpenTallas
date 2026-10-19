`timescale 1ns/1ps
`default_nettype none
// Shared fixed-calendar core. The application hard top includes this core AND R/C.
module ot_smh_calendar_banked_central #(parameter integer W=135,AW=11,XW=46,MUT=0,TW=62+XW,QW=(W+15)/16)(
 input wire clk,rst_n,cfg_we,input wire[AW-1:0]cfg_addr,input wire[255:0]cfg_data,
 input wire start_v,input wire[AW-1:0]start_base,input wire[AW:0]start_limit,
 input wire[15:0]start_loops,input wire[XW-1:0]start_ctx,
 output reg cfg0_we,cfg1_we,output reg[9:0]bank_cfg_addr,output reg[255:0]bank_cfg_data,
 output wire[TW-1:0]request0,request1,
 input wire[W-1:0]row0,row1,input wire[QW-1:0]ok0,ok1,input wire[TW-1:0]token0,token1,
 output reg[W-1:0]calendar,output reg[XW-1:0]calendar_ctx,output reg[15:0]calendar_iter,
 output reg calendar_lastit,calendar_v,output reg[31:0]ordinal,output reg active,done,fault,output wire app_reset_n
);
 initial if(AW!=11||W<1||W>223)$fatal(1,"banked provider requires AW11 and protected payload");
 (* keep=1 *) reg[1:0]reset_landing;
 always @(posedge clk or negedge rst_n)if(!rst_n)reset_landing<=0;else reset_landing<={reset_landing[0],1'b1};
 wire[7:0]reset_branch;
 assign app_reset_n=reset_branch[0];
 for(genvar g=0;g<8;g=g+1)begin:g_reset
  (* keep=1 *) ot_smh_banked_reset_branch u_reset(.clk(clk),.rst_n(rst_n),.phase0(reset_landing[0]),.q(reset_branch[g]));
 end
 reg cw,sv;reg[10:0]ca,sb;reg[255:0]cd;reg[11:0]sl;reg[15:0]sn;reg[XW-1:0]sx;
 always @(posedge clk)begin ca<=cfg_addr;cd<=cfg_data;sb<=start_base;sl<=start_limit;sn<=start_loops;sx<=start_ctx;end
 always @(posedge clk or negedge reset_branch[0])if(!reset_branch[0])begin cw<=0;sv<=0;end else begin cw<=cfg_we;sv<=start_v;end
 reg running,valid0,valid1;reg[10:0]pc,base;reg[11:0]limit;reg[15:0]loops_left,iter_r;
 reg[31:0]issued;reg[XW-1:0]ctx_r;reg lastit_q,lastword_q,bank0_v,bank1_v;
 reg[1:0]online;
 always @(posedge clk or negedge reset_branch[0])if(!reset_branch[0])online<=0;else if(online!=3)online<=online+1'b1;
 wire end_word={1'b0,pc}+1'b1==limit;
 wire final_issue=end_word&&loops_left==1;
 wire legal_start=sl>{1'b0,sb}&&sl<=2048&&sn!=0;
 wire[TW-1:0] source_token={running,lastword_q,lastit_q,iter_r,ctx_r,issued,pc};
 localparam integer PAD=((TW+3)/4)*4;
 wire[PAD-1:0]src_pad={{(PAD-TW){1'b0}},source_token};wire[PAD-1:0]expected_pad;
 for(genvar g=0;g<PAD/4;g=g+1)begin:g_expected_ring
  (* keep=1 *) ot_smh_banked_ring4 #(.DELAY(3)) u_ring(.clk(clk),.rst_n(reset_branch[2+g%6]),.din(src_pad[4*g+:4]),.dout(expected_pad[4*g+:4]));
 end
 wire[TW-1:0] expected_raw=expected_pad[TW-1:0];
 reg[TW-2:0]expected_q;reg[W-1:0]row0_q,row1_q;reg[QW-1:0]ok0_q,ok1_q;reg[TW-1:0]token0_q,token1_q;
 always @(posedge clk)begin
  expected_q<=expected_raw[TW-2:0];row0_q<=row0;row1_q<=row1;ok0_q<=ok0;ok1_q<=ok1;token0_q<=token0;token1_q<=token1;
 end
 localparam integer OUT_BITS=W+XW+16+32+1;
 localparam integer NV=(OUT_BITS+15)/16;
 wire[NV-1:0]exp_valid;wire[QW-1:0]select_q,select_good_q;
 for(genvar g=0;g<NV;g=g+1)begin:g_output_valid
  (* keep=1 *) ot_smh_banked_rbit u_v(.clk(clk),.rst_n(reset_branch[0]),.d(online>=3&&expected_raw[TW-1]),.q(exp_valid[g]));
 end
 for(genvar g=0;g<QW;g=g+1)begin:g_select
  (* keep=1 *) ot_smh_banked_bit u_sel(.clk(clk),.d(expected_raw[10]^1'(MUT==1)),.q(select_q[g]));
  (* keep=1 *) ot_smh_banked_bit u_good_sel(.clk(clk),.d(expected_raw[10]^1'(MUT==1)),.q(select_good_q[g]));
 end
 wire expected_v=exp_valid[0];
 // Ring output covers the gap between the original2 flags and central input capture.
 wire busy=running||valid0||valid1||(online>=3&&expected_raw[TW-1])||expected_v;
 wire accepted=sv&&!busy&&!cw&&legal_start;
 localparam integer NS=7+(XW+15)/16;
 wire[NS-1:0]start_copy,accept_copy;
 for(genvar g=0;g<NS;g=g+1)begin:g_start
  (* keep=1 *) ot_smh_banked_rbit u_start(.clk(clk),.rst_n(reset_branch[1]),.d(start_v),.q(start_copy[g]));
  assign accept_copy[g]=start_copy[g]&&!busy&&!cw&&legal_start;
 end
 wire next_running=(running&&!final_issue)||accepted;
 wire[10:0]pc_inc=pc+1'b1;
 wire next_bank=accepted?sb[10]:running?(end_word?base[10]:pc_inc[10]):pc[10];
 wire next_lastit=accepted?(sn==1):(running&&end_word&&loops_left!=1)?(loops_left==2):(loops_left==1);
 wire next_lastword=accepted?({1'b0,sb}+1'b1==sl&&sn==1):running?
   (end_word?({1'b0,base}+1'b1==limit&&loops_left==2):({1'b0,pc}+2'd2==limit&&loops_left==1)):final_issue;
 wire[5:0]run_copy;
 for(genvar g=0;g<6;g=g+1)begin:g_run
  (* keep=1 *) ot_smh_banked_rbit u_run(.clk(clk),.rst_n(reset_branch[1]),.d(next_running),.q(run_copy[g]));
 end
 always @(posedge clk)begin lastit_q<=next_lastit;lastword_q<=next_lastword;end
 always @(posedge clk or negedge reset_branch[1])
  if(!reset_branch[1])begin running<=0;bank0_v<=0;bank1_v<=0;end
  else begin running<=next_running;bank0_v<=next_running&&!next_bank;bank1_v<=next_running&&next_bank;end
 assign request0={bank0_v,lastword_q,lastit_q,iter_r,ctx_r,issued,pc};
 assign request1={bank1_v,lastword_q,lastit_q,iter_r,ctx_r,issued,pc};
 wire[31:0]issued_inc=issued+1'b1;
 always @(posedge clk)begin if(accept_copy[0])pc<=sb;if(run_copy[0])pc<=end_word?base:pc+1'b1;end
 always @(posedge clk)if(accept_copy[1])base<=sb;
 always @(posedge clk)if(accept_copy[2])limit<=sl;
 // Distinct same-edge running copies keep each decrement enable local to8bits.
 wire[15:0]loops_dec=loops_left-1'b1;
 always @(posedge clk)begin
  if(accept_copy[3])loops_left<=sn;
  if(run_copy[1]&&end_word&&loops_left!=1)loops_left[7:0]<=loops_dec[7:0];
  if(run_copy[5]&&end_word&&loops_left!=1)loops_left[15:8]<=loops_dec[15:8];
 end
 always @(posedge clk)begin if(accept_copy[4])issued[15:0]<=0;if(run_copy[2])issued[15:0]<=issued_inc[15:0];end
 always @(posedge clk)begin if(accept_copy[5])issued[31:16]<=0;if(run_copy[3])issued[31:16]<=issued_inc[31:16];end
 always @(posedge clk)begin if(accept_copy[6])iter_r<=0;if(run_copy[4]&&end_word&&loops_left!=1)iter_r<=iter_r+1'b1;end
 for(genvar g=0;g<(XW+15)/16;g=g+1)begin:g_context
  localparam integer BW=(XW-16*g<16)?XW-16*g:16;
  always @(posedge clk)if(accept_copy[7+g])ctx_r[16*g+:BW]<=sx[16*g+:BW];
 end
 // Registered installation boundary. Only the addressed SRAM gets write-enable.
 always @(posedge clk)begin bank_cfg_addr<=ca[9:0];bank_cfg_data<=cd;end
 always @(posedge clk or negedge reset_branch[0])
  if(!reset_branch[0])begin cfg0_we<=0;cfg1_we<=0;end
  else begin cfg0_we<=cw&&!busy&&!sv&&!ca[10];cfg1_we<=cw&&!busy&&!sv&&ca[10];end
 wire select_canonical=expected_q[10]^1'(MUT==1);
 wire identity0=token0_q[TW-2:0]==expected_q&&token0_q[TW-1];
 wire identity1=token1_q[TW-2:0]==expected_q&&token1_q[TW-1];
 wire identity_ok=select_canonical?identity1:identity0;
 wire selected_ok=select_canonical?ok1_q[0]:ok0_q[0];
 for(genvar g=0;g<QW;g=g+1)begin:g_calendar_out
  localparam integer BW=(W-16*g<16)?W-16*g:16;
  wire good=select_good_q[g]?ok1_q[g]:ok0_q[g];
  always @(posedge clk)calendar[16*g+:BW]<=exp_valid[g]&&good?(select_q[g]?row1_q[16*g+:BW]:row0_q[16*g+:BW]):{BW{1'b0}};
 end
 // Payload metadata outputs have local validity copies, no shared wide reset/enable cone.
 for(genvar g=0;g<(XW+15)/16;g=g+1)begin:g_ctx_out
  localparam integer BW=(XW-16*g<16)?XW-16*g:16;
  always @(posedge clk)calendar_ctx[16*g+:BW]<=exp_valid[QW+g]?expected_q[43+16*g+:BW]:{BW{1'b0}};
 end
 for(genvar g=0;g<2;g=g+1)begin:g_ord_out
  always @(posedge clk)ordinal[16*g+:16]<=expected_q[11+16*g+:16];
 end
 always @(posedge clk)begin
  calendar_iter<=exp_valid[NV-2]?expected_q[43+XW+:16]:16'b0;
  calendar_lastit<=expected_v&&expected_q[59+XW];
 end
 always @(posedge clk or negedge reset_branch[0])
  if(!reset_branch[0])begin valid0<=0;valid1<=0;calendar_v<=0;active<=0;done<=0;fault<=0;end
  else begin
   valid0<=running;valid1<=valid0;calendar_v<=expected_v;active<=busy;done<=expected_v&&expected_q[60+XW];
   if(expected_v&&(!identity_ok||!selected_ok))fault<=1;
   if(cw&&(busy||sv))fault<=1;
   if(sv&&(busy||cw||!legal_start))fault<=1;
  end
endmodule
`default_nettype wire
