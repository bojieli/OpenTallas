`timescale 1ns/1ps
// Additive source successor for the actual 37-word station repair selector.
// Default0 instantiates the pinned existing bank. ON changes no sequential
// statement, repair phase, check, owner permission, register or latency edge.
module ot_hbm_w2_protected_bank_ce_tree #(parameter integer WORDS=1,BALANCED_CE_SELECT=0)(
 input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing
);
 generate if(!BALANCED_CE_SELECT)begin:g_legacy
  ot_hbm_w2_protected_bank #(.WORDS(WORDS)) u_legacy(.*);
 end else begin:g_tree
  ot_hbm_w2_protected_bank_ce_tree_on #(.WORDS(WORDS)) u_tree(.*);
 end endgenerate
endmodule
module ot_hbm_w2_protected_bank_ce_tree_on #(parameter integer WORDS=1)(
 input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,
 input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,
 output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing
);
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbm_w2_boundary_pkg::*;
 reg [71:0] code[0:WORDS+4];
 (* keep=1, dont_touch=1 *) reg failed,failed_n;
 wire [WORDS-1:0] ce,ue;
 wire [63:0] ctl=raw64(code[WORDS]);
 wire [2:0] phase=ctl[2:0];wire [15:0] index=ctl[18:3];
 wire [7:0] syn=ctl[26:19];
 wire [63:0] snapshot_hi=raw64(code[WORDS+2]);
 wire [71:0] snapshot={snapshot_hi[7:0],raw64(code[WORDS+1])};
 wire [63:0] mask_hi=raw64(code[WORDS+4]);
 wire [71:0] mask={mask_hi[7:0],raw64(code[WORDS+3])};
 wire [71:0] next_mask=72'b1<<(syn[6:0]==0?7'd71:syn[6:0]-1'b1);
 wire [4:0] control_bad;
 for(genvar g=0;g<WORDS;g=g+1)begin:word
  wire [7:0] s=check72(code[g]);
  assign ce[g]=s[7]&&s[6:0]<=71;
  assign ue[g]=s[6:0]!=0&&(!s[7]||s[6:0]>71);
  assign q[g*64+:64]=raw64(code[g]);assign encoded_q[g*72+:72]=code[g];
 end
 for(genvar g=0;g<5;g=g+1)begin:control
  assign control_bad[g]=check72(code[WORDS+g])!=0;
 end
 assign fault=failed||failed==failed_n||(|ue)||(|control_bad)||phase>4;
 assign normal=!fault&&phase==0&&!(|ce);
 assign repairing=!fault&&((|ce)||phase!=0);
 // A balanced lowest-index selector. Padding leaves never win; each level
 // selects the lower half if any current correctable stripe is present there.
 // No selected/current flags or permissions are stored outside W6 state.
 localparam integer LEAVES=1<<$clog2(WORDS);
 wire [2*LEAVES-2:0] any_ce;
 wire [15:0] selected[0:2*LEAVES-2];
 for(genvar g=0;g<LEAVES;g=g+1)begin:ce_leaf
  if(g<WORDS)assign any_ce[LEAVES-1+g]=ce[g];
  else assign any_ce[LEAVES-1+g]=1'b0;
  assign selected[LEAVES-1+g]=16'(g);
 end
 for(genvar g=0;g<LEAVES-1;g=g+1)begin:ce_node
  assign any_ce[g]=any_ce[2*g+1]||any_ce[2*g+2];
  assign selected[g]=any_ce[2*g+1]?selected[2*g+1]:selected[2*g+2];
 end
 wire [15:0] first=any_ce[0]?selected[0]:16'b0;
 integer i;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   failed<=0;failed_n<=1;
   for(i=0;i<WORDS+5;i=i+1)code[i]<=encode64(0);
  end else if(fault||fatal)begin failed<=1;failed_n<=0;end
  else case(phase)
   0:if(|ce)begin
    code[WORDS+1]<=encode64(code[first][63:0]);
    code[WORDS+2]<=encode64({56'b0,code[first][71:64]});
    code[WORDS]<=encode64({37'b0,check72(code[first]),16'(first),3'd1});
   end else if(load)begin
    for(i=0;i<WORDS;i=i+1)
     code[i]<=load_encoded?encoded_d[i*72+:72]:encode64(d[i*64+:64]);
   end
   1:begin
    code[WORDS+3]<=encode64(next_mask[63:0]);
    code[WORDS+4]<=encode64({56'b0,next_mask[71:64]});
    code[WORDS]<=encode64({ctl[63:3],3'd2});
   end
   2:if(index>=WORDS||code[index]!==snapshot)begin failed<=1;failed_n<=0;end
     else begin code[index]<=snapshot^mask;code[WORDS]<=encode64({ctl[63:3],3'd3});end
   3:if(check72(code[index])!=0)begin failed<=1;failed_n<=0;end
     else code[WORDS]<=encode64({ctl[63:3],3'd4});
   4:begin
    for(i=0;i<5;i=i+1)code[WORDS+i]<=encode64(0);
   end
   default:begin failed<=1;failed_n<=0;end
  endcase
 end
endmodule
