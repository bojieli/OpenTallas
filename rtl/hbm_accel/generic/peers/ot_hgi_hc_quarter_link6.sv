`timescale 1ns/1ps
`default_nettype none
// Fixed six-edge quarter command/chunk/scalar/status seam. One local clock root,
// captured input pins and registered output pins; no arithmetic or shared state.
module ot_hgi_hc_quarter_link6(
 input wire clk,rst_n,
 input wire[139:0]dn_i,input wire[89:0]ck_i,input wire[258:0]sc_i,input wire[7:0]fb_i,
 output wire[139:0]dn_o,output wire[89:0]ck_o,output wire[258:0]sc_o,output wire[7:0]fb_o
);
 wire[0:0]rn;ot_rst_relay #(.REGIONS(1))u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
 reg[484:0]data[0:5];reg[3:0]valid[0:5];reg[7:0]feedback[0:5];
 integer k;
 always @(posedge clk)begin
  data[0]<={dn_i[138:0],ck_i[87:0],sc_i[257:0]};
  for(k=1;k<6;k=k+1)data[k]<=data[k-1];
 end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin for(integer j=0;j<6;j=j+1)begin valid[j]<=0;feedback[j]<=0;end end
  else begin
   valid[0]<={dn_i[139],ck_i[89:88],sc_i[258]};feedback[0]<=fb_i;
   for(integer j=1;j<6;j=j+1)begin valid[j]<=valid[j-1];feedback[j]<=feedback[j-1];end
  end
 end
 assign dn_o={valid[5][3],data[5][484:346]};
 assign ck_o={valid[5][2:1],data[5][345:258]};
 assign sc_o={valid[5][0],data[5][257:0]};assign fb_o=feedback[5];
endmodule
// Independent negative adapter: quarter chunk0/chunk1 association is wrong.
module ot_hgi_hc_quarter_link6_assoc_mut(
 input wire clk,rst_n,input wire[139:0]dn_i,input wire[89:0]ck_i,
 input wire[258:0]sc_i,input wire[7:0]fb_i,
 output wire[139:0]dn_o,output wire[89:0]ck_o,output wire[258:0]sc_o,output wire[7:0]fb_o
);
 wire[89:0]bad_ck={ck_i[89:88],ck_i[87:76],ck_i[31:0],ck_i[43:32],ck_i[75:44]};
 ot_hgi_hc_quarter_link6 u(.clk(clk),.rst_n(rst_n),.dn_i(dn_i),.ck_i(bad_ck),.sc_i(sc_i),.fb_i(fb_i),.*);
endmodule
`default_nettype wire
