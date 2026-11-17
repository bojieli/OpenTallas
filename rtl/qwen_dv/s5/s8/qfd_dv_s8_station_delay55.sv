`timescale 1ns/1ps
// Default-off selected-CB55 correction. Reuses real32x64 native delay macros;
// there is no64-row SRAM or changed SRAM port contract.
module qfd_dv_s8s_selected_delay #(
 parameter integer W=64, D=14, MUT=0, ENABLE_DELAY55=0
)(input wire ck,rst_n,rst_n_second,input wire[W-1:0]d,output wire[W-1:0]q);
 generate
  if(D<=27)begin:g_legacy
   qfd_dv_s8s_sram_delay #(.W(W),.D(D),.MUT(MUT)) u_same(.ck(ck),.rst_n(rst_n),.d(d),.q(q));
  end else if(ENABLE_DELAY55 && D==55 && W==64)begin:g_cb55
   wire[W-1:0]a,b;
   qfd_dv_s8s_sram_delay #(.W(W),.D(27),.MUT(MUT)) u_first(.ck(ck),.rst_n(rst_n),.d(d),.q(a));
   qfd_dv_s8s_sram_delay #(.W(W),.D(27)) u_second(.ck(ck),.rst_n(rst_n_second),.d(a),.q(b));
   reg[W-1:0]last;
   always @(posedge ck)last<=b;
   assign q=last;
  end else begin:g_bad
   initial $fatal(1,"STN_DELAY55 requires explicit ENABLE_DELAY55=1,W64,D55; legacy native delay maximum27");
   assign q={W{1'b0}};
  end
 endgenerate
endmodule

// Four equal-depth existing station reset leaves; each drives <=28 FF.
module qfd_dv_s8s_control55 #(parameter integer D=55)(
 input wire ck,input wire[3:0]rst_n,input wire[1:0]d,output wire[1:0]q);
 reg[1:0]p[0:D-1];
 for(genvar i=0;i<D;i++)begin:g_stage
  if(i==0)begin:g_first
   always @(posedge ck or negedge rst_n[i/14]) if(!rst_n[i/14])p[i]<=0;else p[i]<=d;
  end else begin:g_next
   always @(posedge ck or negedge rst_n[i/14]) if(!rst_n[i/14])p[i]<=0;else p[i]<=p[i-1];
  end
 end
 assign q=p[D-1];
 initial if(D!=54&&D!=55)$fatal(1,"control55 only nominal55 or oneedge control54");
endmodule
