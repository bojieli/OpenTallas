`timescale 1ns/1ps
// Additive successor; original CURRENT and all its PASS/failure pins unchanged.
// REGISTERED_CHECK defaults OFF and preserves the selected CURRENT setting.
module ot_hbm_w2_protected_bank_check_pipeline #(
 parameter integer WORDS=1, REGISTERED_CURRENT=0, REGISTERED_CHECK=0
)(input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing);
 generate if(!REGISTERED_CHECK)begin:g_prior
  ot_hbm_w2_protected_bank_current_pipeline #(.WORDS(WORDS),.REGISTERED_CURRENT(REGISTERED_CURRENT)) u_bank(.*);
 end else begin:g_check
  ot_hbm_w2_protected_bank_check_on #(.WORDS(WORDS)) u_bank(.*);
 end endgenerate
endmodule

// Local checkers terminate at protected verdict registers in VERIFY. EVAL
// checks the exact retained W6 inputs against live snapshot/status, and CURRENT
// against the decoded snapshot. Every repair traverses CHECK/VERIFY again.
module ot_hbm_w2_protected_bank_check_on #(parameter integer WORDS=1)(
 input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing);
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbm_w2_boundary_pkg::*;
 reg [71:0] code[0:WORDS-1];
 reg [71:0] snapshot_lo[0:WORDS-1],snapshot_hi[0:WORDS-1];
 reg [71:0] syndrome[0:WORDS-1];
 reg [71:0] checked_lo[0:WORDS-1],checked_hi[0:WORDS-1],checked_syn[0:WORDS-1];
 reg [71:0] verdict[0:WORDS-1];
 reg [71:0] phase_code;
 (* keep=1, dont_touch=1 *) reg failed,failed_n;
 wire [63:0] phase_raw=raw64(phase_code);
 wire [1:0] phase=phase_raw[1:0]; // 0 CHECK, 1 VERIFY, 2 EVAL, 3 REPAIR
 wire [WORDS-1:0] same,bad,ce,ue,clean,input_bad;
 wire [71:0] snap[0:WORDS-1];
 wire [7:0] syn[0:WORDS-1];
 for(genvar g=0;g<WORDS;g=g+1)begin:word
  wire [63:0] hi=raw64(snapshot_hi[g]);
  wire [63:0] status=raw64(syndrome[g]);
  assign snap[g]={hi[7:0],raw64(snapshot_lo[g])};
  assign syn[g]=status[7:0];
  assign same[g]=(code[g]===snap[g]);
  assign input_bad[g]=check72(snapshot_lo[g])!=0 || check72(snapshot_hi[g])!=0 ||
                check72(syndrome[g])!=0 || hi[63:8]!=0 || status[63:8]!=0;
  wire [63:0] v=raw64(verdict[g]);
  wire bound=(checked_lo[g]===snapshot_lo[g]) && (checked_hi[g]===snapshot_hi[g]) &&
             (checked_syn[g]===syndrome[g]);
  // Mirror words retain the original W6 codes. Exact equality invalidates
  // either copy's corruption, including parity bits; no unprotected digest.
  assign bad[g]=!bound || check72(verdict[g])!=0 || v[63:4]!=0 || v[3];
  assign ce[g]=v[1];assign ue[g]=v[2];assign clean[g]=v[0];
  assign q[g*64+:64]=raw64(code[g]);
  assign encoded_q[g*72+:72]=code[g];
 end
 wire control_bad=check72(phase_code)!=0 || phase_raw[63:2]!=0 || phase>3;
 assign fault=failed || failed==failed_n || control_bad || ((phase==2 || phase==3) && (|bad)) ||
              (phase==2 && (&same) && (|ue)) || (phase==3 && !(&same));
 assign normal=!fault && phase==2 && (&same) && (&clean);
 assign repairing=!fault && !normal;
 integer i;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   failed<=0;failed_n<=1;phase_code<=encode64(2);
   for(i=0;i<WORDS;i=i+1)begin
    code[i]<=encode64(0);snapshot_lo[i]<=encode64(0);
    snapshot_hi[i]<=encode64(0);syndrome[i]<=encode64(0);
    checked_lo[i]<=encode64(0);checked_hi[i]<=encode64(0);checked_syn[i]<=encode64(0);
    verdict[i]<=encode64(1);
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
   1:begin
    for(i=0;i<WORDS;i=i+1)begin
     checked_lo[i]<=snapshot_lo[i];checked_hi[i]<=snapshot_hi[i];checked_syn[i]<=syndrome[i];
     verdict[i]<=encode64({60'b0,input_bad[i],
       (syn[i][6:0]!=0 && (!syn[i][7] || syn[i][6:0]>71)),
       (syn[i][7] && syn[i][6:0]<=71),(syn[i]==0)});
    end
    phase_code<=encode64(2);
   end
   2:if(!(&same))phase_code<=encode64(0);
     else if(|ce)phase_code<=encode64(3);
     else if(normal && load)begin
      for(i=0;i<WORDS;i=i+1)
       code[i]<=load_encoded ? encoded_d[i*72+:72] : encode64(d[i*64+:64]);
      phase_code<=encode64(0);
     end
   3:begin
    for(i=0;i<WORDS;i=i+1)if(ce[i])
     code[i]<=snap[i] ^ (72'b1 << (syn[i][6:0]==0 ? 7'd71 : syn[i][6:0]-1'b1));
    phase_code<=encode64(0);
   end
   default:begin failed<=1;failed_n<=0;end
  endcase
 end
endmodule

module ot_hbm_w2_protected_cut_check_pipeline #(
 parameter integer W=337, REGISTERED_CURRENT=0, REGISTERED_CHECK=0
)(input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault);
 generate if(!REGISTERED_CHECK)begin:g_prior
  ot_hbm_w2_protected_cut_current_pipeline #(.W(W),.REGISTERED_CURRENT(REGISTERED_CURRENT)) u_cut(.*);
 end else begin:g_check
  ot_hbm_w2_protected_cut_check_on #(.W(W)) u_cut(.*);
 end endgenerate
endmodule
module ot_hbm_w2_protected_cut_check_on #(parameter integer W=337)(
 input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault);
 localparam integer N=(W+1+63)/64;
 wire [N*64-1:0] q;wire normal,repairing;
 wire valid=q[W];
 assign in_r=normal&&(!valid||out_r);
 assign out_v=normal&&valid;assign out_d=q[W-1:0];
 assign empty=normal&&!valid;
 ot_hbm_w2_protected_bank_check_on #(.WORDS(N)) u_state(
  .clk(clk),.por_n(por_n),.load(in_r&&(in_v||valid)),.load_encoded(1'b0),.fatal(1'b0),
  .d({{(N*64-W-1){1'b0}},in_v,(in_v?in_d:{W{1'b0}})}),.encoded_d({N*72{1'b0}}),
  .q(q),.encoded_q(),.normal(normal),.fault(fault),.repairing(repairing));
endmodule
