`timescale 1ns/1ps
// Additive successor; original CURRENT and all its PASS/failure pins unchanged.
// REGISTERED_CHECK defaults OFF and preserves the selected CURRENT setting.
module ot_hbm_w2_protected_bank_balanced_pipeline #(
 parameter integer WORDS=1, REGISTERED_CURRENT=0, REGISTERED_CHECK=0
)(input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing);
 generate if(!REGISTERED_CHECK)begin:g_prior
  ot_hbm_w2_protected_bank_current_pipeline #(.WORDS(WORDS),.REGISTERED_CURRENT(REGISTERED_CURRENT)) u_bank(.*);
 end else begin:g_check
  ot_hbm_w2_protected_bank_balanced_on #(.WORDS(WORDS)) u_bank(.*);
 end endgenerate
endmodule

// Local checkers terminate at protected verdict registers in VERIFY. EVAL
// checks the exact retained W6 inputs against live snapshot/status, and CURRENT
// against the decoded snapshot. Every repair traverses CHECK/VERIFY again.
module ot_hbm_w2_protected_bank_balanced_on #(parameter integer WORDS=1)(
 input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing);
function automatic [71:0] encode64(input [63:0] data);
  begin encode64={^{data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}},data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}};end
 endfunction
function automatic [63:0] raw64(input [71:0] c);
  begin raw64={c[70],c[69],c[68],c[67],c[66],c[65],c[64],c[62],c[61],c[60],c[59],c[58],c[57],c[56],c[55],c[54],c[53],c[52],c[51],c[50],c[49],c[48],c[47],c[46],c[45],c[44],c[43],c[42],c[41],c[40],c[39],c[38],c[37],c[36],c[35],c[34],c[33],c[32],c[30],c[29],c[28],c[27],c[26],c[25],c[24],c[23],c[22],c[21],c[20],c[19],c[18],c[17],c[16],c[14],c[13],c[12],c[11],c[10],c[9],c[8],c[6],c[5],c[4],c[2]};end
 endfunction
function automatic [7:0] check72(input [71:0] c);
  begin check72={^c,^{c[63],c[64],c[65],c[66],c[67],c[68],c[69],c[70]},^{c[31],c[32],c[33],c[34],c[35],c[36],c[37],c[38],c[39],c[40],c[41],c[42],c[43],c[44],c[45],c[46],c[47],c[48],c[49],c[50],c[51],c[52],c[53],c[54],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[15],c[16],c[17],c[18],c[19],c[20],c[21],c[22],c[23],c[24],c[25],c[26],c[27],c[28],c[29],c[30],c[47],c[48],c[49],c[50],c[51],c[52],c[53],c[54],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[7],c[8],c[9],c[10],c[11],c[12],c[13],c[14],c[23],c[24],c[25],c[26],c[27],c[28],c[29],c[30],c[39],c[40],c[41],c[42],c[43],c[44],c[45],c[46],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[3],c[4],c[5],c[6],c[11],c[12],c[13],c[14],c[19],c[20],c[21],c[22],c[27],c[28],c[29],c[30],c[35],c[36],c[37],c[38],c[43],c[44],c[45],c[46],c[51],c[52],c[53],c[54],c[59],c[60],c[61],c[62],c[67],c[68],c[69],c[70]},^{c[1],c[2],c[5],c[6],c[9],c[10],c[13],c[14],c[17],c[18],c[21],c[22],c[25],c[26],c[29],c[30],c[33],c[34],c[37],c[38],c[41],c[42],c[45],c[46],c[49],c[50],c[53],c[54],c[57],c[58],c[61],c[62],c[65],c[66],c[69],c[70]},^{c[0],c[2],c[4],c[6],c[8],c[10],c[12],c[14],c[16],c[18],c[20],c[22],c[24],c[26],c[28],c[30],c[32],c[34],c[36],c[38],c[40],c[42],c[44],c[46],c[48],c[50],c[52],c[54],c[56],c[58],c[60],c[62],c[64],c[66],c[68],c[70]}};end
 endfunction
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
  // Keep word-local comparisons separate from the global permission tree.
  (* keep=1 *) wire [2:0] bound_part;
  assign bound_part[0]=(checked_lo[g]===snapshot_lo[g]);
  assign bound_part[1]=(checked_hi[g]===snapshot_hi[g]);
  assign bound_part[2]=(checked_syn[g]===syndrome[g]);
  (* keep=1 *) wire bound=&bound_part;
  // Mirror words retain the original W6 codes. Exact equality invalidates
  // either copy's corruption, including parity bits; no unprotected digest.
  assign bad[g]=!bound || check72(verdict[g])!=0 || v[63:4]!=0 || v[3];
  assign ce[g]=v[1];assign ue[g]=v[2];assign clean[g]=v[0];
  assign q[g*64+:64]=raw64(code[g]);
  assign encoded_q[g*72+:72]=code[g];
 end
 localparam integer NG=(WORDS+3)/4;
 (* keep=1 *) wire [NG-1:0] same4,bad4,ce4,ue4,clean4;
 for(genvar t=0;t<NG;t=t+1)begin:group4
  localparam integer L=(WORDS-t*4<4)?WORDS-t*4:4;
  assign same4[t]=&same[t*4+:L]; assign bad4[t]=|bad[t*4+:L];
  assign ce4[t]=|ce[t*4+:L]; assign ue4[t]=|ue[t*4+:L];
  assign clean4[t]=&clean[t*4+:L];
 end
 (* keep=1 *) wire all_same=&same4,any_bad=|bad4,any_ce=|ce4,any_ue=|ue4,all_clean=&clean4;
 wire control_bad=check72(phase_code)!=0 || phase_raw[63:2]!=0 || phase>3;
 assign fault=failed || failed==failed_n || control_bad || ((phase==2 || phase==3) && any_bad) ||
              (phase==2 && all_same && any_ue) || (phase==3 && !all_same);
 assign normal=!fault && phase==2 && all_same && all_clean;
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
   2:if(!all_same)phase_code<=encode64(0);
     else if(any_ce)phase_code<=encode64(3);
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

module ot_hbm_w2_protected_cut_balanced_pipeline #(
 parameter integer W=337, REGISTERED_CURRENT=0, REGISTERED_CHECK=0
)(input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault);
 generate if(!REGISTERED_CHECK)begin:g_prior
  ot_hbm_w2_protected_cut_current_pipeline #(.W(W),.REGISTERED_CURRENT(REGISTERED_CURRENT)) u_cut(.*);
 end else begin:g_check
  ot_hbm_w2_protected_cut_balanced_on #(.W(W)) u_cut(.*);
 end endgenerate
endmodule
module ot_hbm_w2_protected_cut_balanced_on #(parameter integer W=337)(
 input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault);
 localparam integer N=(W+1+63)/64;
 wire [N*64-1:0] q;wire normal,repairing;
function automatic [71:0] encode64(input [63:0] data);
  begin encode64={^{data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}},data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}};end
 endfunction
function automatic [63:0] raw64(input [71:0] c);
  begin raw64={c[70],c[69],c[68],c[67],c[66],c[65],c[64],c[62],c[61],c[60],c[59],c[58],c[57],c[56],c[55],c[54],c[53],c[52],c[51],c[50],c[49],c[48],c[47],c[46],c[45],c[44],c[43],c[42],c[41],c[40],c[39],c[38],c[37],c[36],c[35],c[34],c[33],c[32],c[30],c[29],c[28],c[27],c[26],c[25],c[24],c[23],c[22],c[21],c[20],c[19],c[18],c[17],c[16],c[14],c[13],c[12],c[11],c[10],c[9],c[8],c[6],c[5],c[4],c[2]};end
 endfunction
function automatic [7:0] check72(input [71:0] c);
  begin check72={^c,^{c[63],c[64],c[65],c[66],c[67],c[68],c[69],c[70]},^{c[31],c[32],c[33],c[34],c[35],c[36],c[37],c[38],c[39],c[40],c[41],c[42],c[43],c[44],c[45],c[46],c[47],c[48],c[49],c[50],c[51],c[52],c[53],c[54],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[15],c[16],c[17],c[18],c[19],c[20],c[21],c[22],c[23],c[24],c[25],c[26],c[27],c[28],c[29],c[30],c[47],c[48],c[49],c[50],c[51],c[52],c[53],c[54],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[7],c[8],c[9],c[10],c[11],c[12],c[13],c[14],c[23],c[24],c[25],c[26],c[27],c[28],c[29],c[30],c[39],c[40],c[41],c[42],c[43],c[44],c[45],c[46],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[3],c[4],c[5],c[6],c[11],c[12],c[13],c[14],c[19],c[20],c[21],c[22],c[27],c[28],c[29],c[30],c[35],c[36],c[37],c[38],c[43],c[44],c[45],c[46],c[51],c[52],c[53],c[54],c[59],c[60],c[61],c[62],c[67],c[68],c[69],c[70]},^{c[1],c[2],c[5],c[6],c[9],c[10],c[13],c[14],c[17],c[18],c[21],c[22],c[25],c[26],c[29],c[30],c[33],c[34],c[37],c[38],c[41],c[42],c[45],c[46],c[49],c[50],c[53],c[54],c[57],c[58],c[61],c[62],c[65],c[66],c[69],c[70]},^{c[0],c[2],c[4],c[6],c[8],c[10],c[12],c[14],c[16],c[18],c[20],c[22],c[24],c[26],c[28],c[30],c[32],c[34],c[36],c[38],c[40],c[42],c[44],c[46],c[48],c[50],c[52],c[54],c[56],c[58],c[60],c[62],c[64],c[66],c[68],c[70]}};end
 endfunction
 wire valid=q[W];
 wire [N*64-1:0] raw_input={{(N*64-W-1){1'b0}},1'b1,in_d};
 (* keep=1 *) wire [N*72-1:0] preencoded;
 for(genvar e=0;e<N;e=e+1)begin:encode_before_accept
  assign preencoded[e*72+:72]=encode64(raw_input[e*64+:64]);
 end
 (* keep=1 *) wire [N*72-1:0] selected_code=in_v?preencoded:{N*72{1'b0}};
 assign in_r=normal&&(!valid||out_r);
 assign out_v=normal&&valid;assign out_d=q[W-1:0];
 assign empty=normal&&!valid;
 ot_hbm_w2_protected_bank_balanced_on #(.WORDS(N)) u_state(
  .clk(clk),.por_n(por_n),.load(in_r&&(in_v||valid)),.load_encoded(1'b1),.fatal(1'b0),
  .d({N*64{1'b0}}),.encoded_d(selected_code),
  .q(q),.encoded_q(),.normal(normal),.fault(fault),.repairing(repairing));
endmodule
