`timescale 1ns/1ps
module tb_static_frame_transport;
 parameter integer MUT=0;
 localparam integer N=1839;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,ts=0,rs=0,slot=0,ev=0;
 reg [611:0] ed=0;
 wire due,tv,rv,fault;
 wire [486:0] tw;
 wire [611:0] rd;
 wire wirevalid=(MUT==2 && cycle==7)?1'b0:tv;
 wire [486:0] wireword=tw ^ ((MUT==3 && cycle==3)?487'b1:487'b0);
 integer cycle=0,k,e,checked=0,idles=0;
 reg [613:0] tx[0:N-1],rx[0:N-1];
 string vec;
 ot_hbm_static_frame_transport u(clk,rst_n,ts,rs,slot,ev,ed,due,tv,tw,wirevalid,wireword,rv,rd,fault);
 initial begin
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"missing VEC");
  $readmemh({vec,"/tx.hex"},tx);$readmemh({vec,"/rx.hex"},rx);
  for(e=0;e<2;e=e+1)begin
   @(negedge clk);rst_n=0;ts=0;rs=0;slot=0;ev=0;
   repeat(3)@(posedge clk);
   @(negedge clk);rst_n=1;ts=1;
   @(posedge clk);#1;
   for(k=0;k<N+2;k=k+1)begin
    @(negedge clk);cycle=k;ts=0;rs=(k==0);
    slot=tx[k%N][613];ev=tx[k%N][612];ed=tx[k%N][611:0];
    if(MUT==1 && k==0)ev=~ev;
    #1;if(due!==slot)$fatal(1,"reservation %0d",k);
    @(posedge clk);#1;
    if(fault)$fatal(1,"word reservation fault %0d",k);
    if(k>=2)begin
     if(rv!==(rx[k-2][613] && rx[k-2][612]))$fatal(1,"endpoint valid %0d",k);
     if(rv)begin
      if(rd!==rx[k-2][611:0])$fatal(1,"payload %0d",k);
      checked=checked+1;
     end else if(rx[k-2][613])idles=idles+1;
    end
   end
  end
  if(checked==0 || idles==0 || checked+idles!=2922)$fatal(1,"coverage data%0d idle%0d",checked,idles);
  $display("PASS actual613validtransport data=%0d idle=%0d total2922 epochs2",checked,idles);$finish;
 end
endmodule
