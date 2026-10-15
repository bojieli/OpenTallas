// Standalone candidate. No parent integration or clock/physical qualification.
// Each local captures FIFTEEN source bits into FIVE semantic fields, not a
// generic status copy: {reset,bad_lnk,representative_valid,local_mismatch,fault}.
module ot_qfd_band_fault_q4 #(parameter integer MUT=0)(
 input wire clk,reset_q,input wire [5:0]rawlnk,
 input wire [3:0]lf,lpv,output reg [4:0]q
);
 always @(posedge clk)
  q<={reset_q,(&rawlnk),lpv[0],(MUT==2?1'b0:|(lpv^{4{lpv[0]}})),(MUT==1?1'b0:|lf)};
endmodule

// q = {globalf,quarter_fault[3:0],quarter_pv[3:0]}.
// Common source reset and equal-age quarter clocks guarantee all reset fields
// agree; the standalone proof quantifies arbitrary common reset sequences.
module ot_qfd_band_fault_join #(parameter integer MUT=0)(
 input wire clk,input wire [19:0]d,output reg [8:0]q
);
 wire [3:0]lf,mis,pv,bad,rst;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gd
  assign lf[g]=d[5*g];assign mis[g]=d[5*g+1];
  assign pv[g]=d[5*g+2];assign bad[g]=d[5*g+3];assign rst[g]=d[5*g+4];
 end endgenerate
 wire mismatch=(|mis)|((MUT==1)?1'b0:(|(pv^{4{pv[0]}})));
 wire bad_lnk=(MUT==2)?1'b0:(|bad);
 wire [3:0] f,p;
 generate for(g=0;g<4;g=g+1)begin:go
  assign p[g]=((MUT==3)?1'b1:rst[g])&pv[g];
  assign f[g]=((MUT==3)?1'b1:rst[g])&(lf[g]|mismatch|bad_lnk);
 end endgenerate
 wire globalf=((MUT==3)?1'b1:rst[0])&((|lf)|mismatch|bad_lnk);
 always @(posedge clk)q<={globalf,f,p};
endmodule

// Explicit physical output capture: all nine semantic outputs gain one edge.
// Synchronous reset is DATA already masked at join; there is no async reset or
// unpriced local reset relay. Reset assertion/release both take three captures.
module ot_qfd_band_fault_output #(parameter integer MUT=0)(
 input wire clk,input wire [8:0]d,output wire [8:0]q
);
 reg [8:0]out_q;
 always @(posedge clk)out_q<=d;
 assign q=(MUT==1)?d:out_q;
endmodule

module ot_qfd_band_fault_tree3 #(parameter integer MUT=0)(
 input wire ck_q0,ck_q1,ck_q2,ck_q3,ck_join,ck_out,
 input wire reset_q,input wire [5:0]rawlnk,input wire [15:0]lf,lpv,
 output wire globalf,output wire [3:0]quarter_pv,quarter_fault
);
 wire [3:0]clks={ck_q3,ck_q2,ck_q1,ck_q0};
 wire [19:0]local_q;wire [8:0]joined,output_q;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gq
  ot_qfd_band_fault_q4 #(.MUT((MUT==1&&g==3)?1:(MUT==4&&g==2)?2:0)) local_stage
   (.clk(clks[g]),.reset_q(reset_q),.rawlnk(rawlnk),.lf(lf[4*g+:4]),.lpv(lpv[4*g+:4]),.q(local_q[5*g+:5]));
 end endgenerate
 ot_qfd_band_fault_join #(.MUT(MUT==2?1:MUT==5?2:MUT==6?3:0)) join_stage(.clk(ck_join),.d(local_q),.q(joined));
 ot_qfd_band_fault_output #(.MUT(MUT==3?1:0)) output_stage(.clk(ck_out),.d(joined),.q(output_q));
 assign {globalf,quarter_fault,quarter_pv}=output_q;
endmodule
