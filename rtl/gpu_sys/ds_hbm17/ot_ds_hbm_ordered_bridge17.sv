`timescale 1ns/1ps
// Actual shared-edge DSpark controller -> command processor stream sequencer.
// Original D.expand order; completion only from all real CP ports. This does
// not generate SM results, router selections or expert-union acknowledgments.
module ot_ds_hbm_ordered_bridge17 #(
 parameter integer ENABLE=0,ND=2,NSM=2,PM=8,B=5,NL=40,NST=3,CB=8
)(
 input wire clk,rst_n,
 input wire cmd_v,output wire cmd_ready,input wire [3:0] cmd_op,
 input wire [7:0] cmd_idx,input wire [3:0] cmd_ncol,
 input wire [31:0] cmd_pos,input wire [16:0] cmd_tok1,
 input wire [PM*17-1:0] cmd_toks,
 input wire [11*32-1:0] entry_pc,input wire [16:0] noise_token,
 output reg eng_done,am_v,output reg [16:0] am_idx,output reg fault,
 output wire [ND-1:0] cp_cmd_we,output wire [ND*CB-1:0] cp_cmd_addr,
 output wire [ND*64-1:0] cp_cmd_data,
 output wire [ND-1:0] db_v,input wire [ND-1:0] db_rdy,
 output wire [ND*17-1:0] db_token,output wire [ND*16-1:0] db_pos,
 input wire [ND-1:0] cpl_v,output wire [ND-1:0] cpl_rdy,
 input wire [ND*53-1:0] cpl_data
);
generate if(ENABLE==0) begin:g_off
 assign cmd_ready=0;assign cp_cmd_we=0;assign cp_cmd_addr=0;assign cp_cmd_data=0;
 assign db_v=0;assign db_token=0;assign db_pos=0;assign cpl_rdy=0;
 always @(posedge clk) begin eng_done<=0;am_v<=0;am_idx<=0;fault<=0;end
end else begin:g_on
 localparam [2:0] IDLE=0,LOAD0=1,LOAD1=2,DB=3,WAIT_CPL=4,FAILED=5;
 reg [2:0] state;
 reg [3:0] op,ncol;
 reg [7:0] idx;
 reg [31:0] pos;
 reg [16:0] tok1;
 reg [PM*17-1:0] toks;
 reg [2:0] col,substep;
 reg draft_back;
 reg [ND-1:0] sent,got;
 reg [16:0] result[0:ND-1];
 reg [3:0] kind,last_step;
 reg [16:0] token;
 reg [31:0] position;
 reg result_kernel,all_same;
 integer i;
 always @(*) begin
  kind=0;token=0;position=0;last_step=0;
  case(op)
   0:begin // VLAYER
    last_step=(idx==0)?3:2;
    case(substep)
     0:begin kind=0;token=col;position=idx;end
     1:begin kind=(idx==0)?2:3;token=toks[col*17+:17];position=pos+col;end
     2:begin kind=(idx==0)?3:1;token=(idx==0)?toks[col*17+:17]:17'(col);position=pos+col;end
     3:begin kind=1;token=col;position=pos+col;end
    endcase
   end
   1,4:begin // VHEAD / DHEAD
    last_step=1;
    if(substep==0) begin kind=0;token=(op==4)?PM+col:col;position=63;end
    else begin kind=(op==4)?9:4;token=(op==4)?col:0;position=pos+col+((op==4)?1:0);end
   end
   2:begin kind=5;token=col;position=pos+col;end // SEED
   3:begin // DSTAGE: every front before any back
    last_step=(!draft_back && idx==0)?3:2;
    if(substep==0) begin kind=0;token=PM+col;position=40+idx;end
    else if(!draft_back && idx==0 && substep==1) begin kind=6;token=(col==0)?tok1:noise_token;position=0;end
    else if(substep==last_step) begin kind=1;token=PM+col;position=0;end
    else begin kind=draft_back?8:7;token=col;position=pos+1+col;end
   end
   5:begin kind=10;token=tok1;position=idx;end
  endcase
  result_kernel=(kind==4 || kind==10);
  all_same=1;
  for(i=1;i<ND;i=i+1) if(result[i]!=result[0]) all_same=0;
 end
 assign cmd_ready=(state==IDLE && !fault);
 for(genvar d=0;d<ND;d=d+1) begin:g_port
  assign cp_cmd_we[d]=(state==LOAD0 || state==LOAD1) && (&db_rdy) && !(|cpl_v);
  assign cp_cmd_addr[d*CB+:CB]=(state==LOAD1)?1:0;
  assign cp_cmd_data[d*64+:64]=(state==LOAD1)?64'h2000000000000000:
    (64'h1000000000000000 | (64'((1<<NSM)-1)<<44) | 64'(entry_pc[kind*32+:32]));
  assign db_v[d]=(state==DB) && !sent[d];
  assign db_token[d*17+:17]=token;
  assign db_pos[d*16+:16]=position[15:0];
  assign cpl_rdy[d]=(state==WAIT_CPL) && !got[d];
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE;op<=0;idx<=0;ncol<=0;pos<=0;tok1<=0;toks<=0;col<=0;substep<=0;draft_back<=0;
   sent<=0;got<=0;eng_done<=0;am_v<=0;am_idx<=0;fault<=0;
   for(integer d=0;d<ND;d=d+1) result[d]<=0;
  end else begin
   eng_done<=0;am_v<=0;
   case(state)
    IDLE:if(cmd_v && cmd_ready) begin
     if(cmd_op>5 || cmd_ncol==0 || cmd_ncol>PM || cmd_pos>65535 ||
        cmd_pos+cmd_ncol+1>65535 || (cmd_op==0 && cmd_idx>=NL) ||
        (cmd_op==3 && (cmd_idx>=NST || cmd_ncol!=B)) ||
        (cmd_op==4 && cmd_ncol!=B) || (cmd_op==5 && (cmd_idx>=B || cmd_ncol!=1))) begin
      fault<=1;state<=FAILED;
     end else begin
      op<=cmd_op;idx<=cmd_idx;ncol<=cmd_ncol;pos<=cmd_pos;tok1<=cmd_tok1;toks<=cmd_toks;
      col<=0;substep<=0;draft_back<=0;state<=LOAD0;
     end
    end
    LOAD0,LOAD1:begin
     if(!(&db_rdy) || |cpl_v || position>65535) begin fault<=1;state<=FAILED;end
     else if(state==LOAD0) state<=LOAD1;
     else begin state<=DB;sent<=0;got<=0;end
    end
    DB:begin
     sent<=sent | (db_v & db_rdy);
     if((sent | (db_v & db_rdy))=={ND{1'b1}}) state<=WAIT_CPL;
    end
    WAIT_CPL:begin
     for(integer d=0;d<ND;d=d+1) if(cpl_v[d] && cpl_rdy[d]) begin
      got[d]<=1;result[d]<=cpl_data[d*53+:17];
      if(cpl_data[d*53+17+:4]!=(result_kernel?4'd0:4'd2)) begin fault<=1;state<=FAILED;end
     end
     if(&got) begin
      if(result_kernel && !all_same) begin fault<=1;state<=FAILED;end
      else begin
       if(result_kernel) begin am_v<=1;am_idx<=result[0];end
       if(substep<last_step) begin substep<=substep+1;state<=LOAD0;end
       else if(col+1<ncol) begin col<=col+1;substep<=0;state<=LOAD0;end
       else if(op==3 && !draft_back) begin draft_back<=1;col<=0;substep<=0;state<=LOAD0;end
       else begin eng_done<=1;state<=IDLE;end
      end
     end
    end
    FAILED:state<=FAILED;
    default:begin fault<=1;state<=FAILED;end
   endcase
  end
 end
end endgenerate
endmodule
