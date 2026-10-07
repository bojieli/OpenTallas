`timescale 1ns/1ps
// DEFAULT OFF. Immutable original bank/cut remain the legacy implementation.
module ot_hbm_w2_protected_bank_current_pipeline #(
 parameter integer WORDS=1, REGISTERED_CURRENT=0
)(input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing);
 generate if(!REGISTERED_CURRENT)begin:g_legacy
  ot_hbm_w2_protected_bank #(.WORDS(WORDS)) u_bank(.*);
 end else begin:g_current
  ot_hbm_w2_protected_bank_current_on #(.WORDS(WORDS)) u_bank(.*);
 end endgenerate
endmodule

// CHECK captures each stripe separately. EVAL grants only a clean, protected
// result still matching CURRENT. REPAIR cannot load or publish. Repaired data
// goes through CHECK again. No selected-word mux, no cached owner permission,
// no unprotected raw snapshot, and no re-encoding corrupt payload as authority.
module ot_hbm_w2_protected_bank_current_on #(parameter integer WORDS=1)(
 input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing);
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbm_w2_boundary_pkg::*;
 reg [71:0] code[0:WORDS-1];
 reg [71:0] snapshot_lo[0:WORDS-1],snapshot_hi[0:WORDS-1];
 reg [71:0] syndrome[0:WORDS-1];
 reg [71:0] phase_code;
 (* keep=1, dont_touch=1 *) reg failed,failed_n;
 wire [63:0] phase_raw=raw64(phase_code);
 wire [1:0] phase=phase_raw[1:0]; // 0 CHECK, 1 EVAL, 2 REPAIR
 wire [WORDS-1:0] same,bad,ce,ue,clean;
 wire [71:0] snap[0:WORDS-1];
 wire [7:0] syn[0:WORDS-1];
 for(genvar g=0;g<WORDS;g=g+1)begin:word
  wire [63:0] hi=raw64(snapshot_hi[g]);
  wire [63:0] status=raw64(syndrome[g]);
  assign snap[g]={hi[7:0],raw64(snapshot_lo[g])};
  assign syn[g]=status[7:0];
  assign same[g]=(code[g]===snap[g]);
  assign bad[g]=check72(snapshot_lo[g])!=0 || check72(snapshot_hi[g])!=0 ||
                check72(syndrome[g])!=0 || hi[63:8]!=0 || status[63:8]!=0;
  assign ce[g]=syn[g][7] && syn[g][6:0]<=71;
  assign ue[g]=syn[g][6:0]!=0 && (!syn[g][7] || syn[g][6:0]>71);
  assign clean[g]=syn[g]==0;
  assign q[g*64+:64]=raw64(code[g]);
  assign encoded_q[g*72+:72]=code[g];
 end
 wire control_bad=check72(phase_code)!=0 || phase_raw[63:2]!=0 || phase>2;
 assign fault=failed || failed==failed_n || control_bad || (|bad) ||
              (phase!=0 && (&same) && (|ue)) || (phase==2 && !(&same));
 assign normal=!fault && phase==1 && (&same) && (&clean);
 assign repairing=!fault && !normal;
 integer i;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   failed<=0;failed_n<=1;phase_code<=encode64(1);
   for(i=0;i<WORDS;i=i+1)begin
    code[i]<=encode64(0);snapshot_lo[i]<=encode64(0);
    snapshot_hi[i]<=encode64(0);syndrome[i]<=encode64(0);
   end
  end else if(fault || fatal)begin failed<=1;failed_n<=0;end
  else case(phase)
   0:begin
    for(i=0;i<WORDS;i=i+1)begin
     snapshot_lo[i]<=encode64(code[i][63:0]);
     snapshot_hi[i]<=encode64({56'b0,code[i][71:64]});
     syndrome[i]<=encode64({56'b0,check72(code[i])});
    end
    phase_code<=encode64(1);
   end
   1:if(!(&same))phase_code<=encode64(0);
     else if(|ce)phase_code<=encode64(2);
     else if(normal && load)begin
      for(i=0;i<WORDS;i=i+1)
       code[i]<=load_encoded ? encoded_d[i*72+:72] : encode64(d[i*64+:64]);
      phase_code<=encode64(0);
     end
   2:begin
    for(i=0;i<WORDS;i=i+1)if(ce[i])
     code[i]<=snap[i] ^ (72'b1 << (syn[i][6:0]==0 ? 7'd71 : syn[i][6:0]-1'b1));
    phase_code<=encode64(0);
   end
   default:begin failed<=1;failed_n<=0;end
  endcase
 end
endmodule

module ot_hbm_w2_protected_cut_current_pipeline #(
 parameter integer W=337, REGISTERED_CURRENT=0
)(input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault);
 generate if(!REGISTERED_CURRENT)begin:g_legacy
  ot_hbm_w2_protected_cut #(.W(W)) u_cut(.*);
 end else begin:g_current
  ot_hbm_w2_protected_cut_current_on #(.W(W)) u_cut(.*);
 end endgenerate
endmodule
module ot_hbm_w2_protected_cut_current_on #(parameter integer W=337)(
 input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault);
 localparam integer N=(W+1+63)/64;
 wire [N*64-1:0] q;wire normal,repairing;
 wire valid=q[W];
 assign in_r=normal&&(!valid||out_r);
 assign out_v=normal&&valid;assign out_d=q[W-1:0];
 assign empty=normal&&!valid;
 ot_hbm_w2_protected_bank_current_on #(.WORDS(N)) u_state(
  .clk(clk),.por_n(por_n),.load(in_r&&(in_v||valid)),.load_encoded(1'b0),.fatal(1'b0),
  .d({{(N*64-W-1){1'b0}},in_v,(in_v?in_d:{W{1'b0}})}),.encoded_d({N*72{1'b0}}),
  .q(q),.encoded_q(),.normal(normal),.fault(fault),.repairing(repairing));
endmodule
