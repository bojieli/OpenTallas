module prove_tree3 #(parameter integer MUT=0)(
 input wire clk,reset_q,input wire [5:0]rawlnk,
 input wire [15:0]lf,lpv,output wire exact
);
 wire [3:0]oldp,oldf,newp,newf;wire newglobal;
 ot_qfd_band_upper_faces original(.clk(clk),.reset_q(reset_q),.lnk(rawlnk),.lpv(lpv),.lf(lf),.quarter_pv(oldp),.quarter_fault(oldf));
 // This is the actual separate f_q expression in the ORIGINAL current BAND.
 reg oldglobal;
 always @(posedge clk)
  if(!reset_q)oldglobal<=0;
  else oldglobal<=(&rawlnk)| |lf | (|(lpv^{16{lpv[0]}}));
 reg [8:0]delay1,delay2;
 always @(posedge clk)begin delay1<={oldglobal,oldf,oldp};delay2<=delay1;end
 ot_qfd_band_fault_tree3 #(.MUT(MUT)) candidate(.ck_q0(clk),.ck_q1(clk),.ck_q2(clk),.ck_q3(clk),.ck_join(clk),.ck_out(clk),.reset_q(reset_q),.rawlnk(rawlnk),.lf(lf),.lpv(lpv),.globalf(newglobal),.quarter_pv(newp),.quarter_fault(newf));
 assign exact={newglobal,newf,newp}==delay2;
endmodule
