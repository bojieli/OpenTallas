module qfd_wtn_kept_select #(parameter integer W=1,ID=0,RST=1)(
 input wire ck,rst_n,input wire[W-1:0]d,output reg[W-1:0]q);
 generate if(RST)begin:ar
  always@(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=d;
 end else begin:nr
  always@(posedge ck)q<=d;
 end endgenerate
endmodule
