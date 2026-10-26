`timescale 1ns/1ps
// One registered station at each of32 logical PC positions in a stack. Forward
// sector word291 passes every PC; exactly the matching lpc consumes it into
// host_es288 (qkd_host_static_pc). Source credits and real write ACKs travel on
// separate reverse32-bit pulse vectors. Adjacent clocks/pins use the die budget.
// No combinational wire crosses this station; each direction adds2 edges.
module qkd_host_ingest_station_debt #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[4:0]lpc,
 input wire[290:0]fi,output wire[290:0]fo,
 output wire[287:0]host_es,input wire host_cr,host_ack,host_fault,
 input wire[31:0]ci,output reg[31:0]co,
 input wire[31:0]ai,output reg[31:0]ao,
 input wire fault_i,output reg fault_o,output reg station_quiet
);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)station_quiet<=0;
  else station_quiet<=!fi[0]&&!fvq&&!fov&&!hev&&!host_cr&&!host_ack&&!crq&&!ackq&&
   !(|ci)&&!(|ai)&&!(|cq)&&!(|aq)&&!(|co)&&!(|ao)&&!host_fault&&!fault_i&&!hfq&&!ffq&&!fault_o;
 end
 reg[289:0]fdq,fod;reg fvq,fov;
 reg[286:0]hed;reg hev;
 wire[290:0]fq={fdq,fvq};assign fo={fod,fov};assign host_es={hed,hev};reg[31:0]cq,aq;reg[4:0]lq;
 reg crq,ackq,hfq,ffq;
 wire[4:0]target=(MUT==1)?fq[5:1]^5'd1:fq[5:1];
 wire mine=fq[0]&&target==lq;
 wire[31:0]credit=32'(crq)<<lq,ack=32'(ackq)<<lq;
 always @(posedge ck)begin
  lq<=lpc;fdq<=fi[290:1];fod<=fq[290:1];
  hed<={1'b1,1'b1,fq[10:6],fq[15:11],fq[34:16],fq[290:35]};
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin fvq<=0;fov<=0;hev<=0;cq<=0;aq<=0;crq<=0;ackq<=0;hfq<=0;ffq<=0;co<=0;ao<=0;fault_o<=0;end
  else begin
   fvq<=fi[0];fov<=fq[0];hev<=mine;
   cq<=ci;aq<=ai;crq<=host_cr;ackq<=host_ack;hfq<=host_fault;ffq<=fault_i;
   co<=cq|credit;ao<=aq|ack;
   fault_o<=fault_o|hfq|ffq|(|(cq&credit))|(|(aq&ack));
  end
 end
endmodule
