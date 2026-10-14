`timescale 1ns/1ps
`default_nettype none
// One physical node of the golden padded binary reduction heap. Operands,
// readiness and row-clear enter pin flops; the held sum and its publication
// pulse leave flops. One local clock root, no combinational ready path.
module ot_hbm_norm_sum_node #(parameter integer LAT=6,MUT=0)(
 input wire clk,rst_n,go,left_ready,right_ready,
 input wire [31:0]left_data,right_data,
 output reg ready,published,fault,output reg [31:0]data
);
 wire[0:0]rn;ot_rst_relay #(.REGIONS(1))u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
 reg go_q,lq,rq;reg[31:0]ld,rd;reg issued;localparam integer FW=$clog2(LAT+3);reg[FW-1:0]flush;
 always @(posedge clk)begin ld<=left_data;rd<=right_data;end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin go_q<=0;lq<=0;rq<=0;end
  else begin go_q<=go;lq<=left_ready;rq<=right_ready;end
 end
 wire fire=lq&&rq&&!issued&&!go_q&&flush==0;
 wire[LAT:0]av;wire[31:0]sum;wire af;
 ot_hdc_vline #(.D(LAT))u_v(.clk(clk),.rst_n(rn[0]),.v(fire),.vd(av));
 ot_dsrom_qadd #(.LAT(LAT))u_add(clk,rn[0],fire,ld,MUT==1?ld:rd,sum,af);
 always @(posedge clk)if(av[LAT])data<=sum;
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin issued<=0;ready<=0;published<=0;fault<=0;flush<=0;end
  else if(go_q)begin issued<=0;ready<=0;published<=0;fault<=0;flush<=FW'(LAT+2);end
  else begin
   published<=av[LAT]&&flush==0;
   if(flush!=0)flush<=flush-1;
   if(fire)issued<=1;
   if(av[LAT]&&flush==0)ready<=1;
   if(af&&flush==0)fault<=1;
  end
 end
endmodule
`default_nettype wire
