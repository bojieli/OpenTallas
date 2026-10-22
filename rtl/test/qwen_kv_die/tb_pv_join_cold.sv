`timescale 1ns/1ps
module tb_pv_join_cold;
 parameter integer MUT=0,COLD=1,RP=0;
 reg clk=0,rst_n=0; always #1 clk=~clk;
 reg[1:0] rr; always @(posedge clk)rr<={rr[0],rst_n};
 wire ref_rst=COLD?rr[1]:rst_n;
 reg[1023:0] ts0,ts1,ts2,ts3; reg go=0;reg[7:0]sf=0;
 wire[511:0]a,b;wire av,bv,af,bf;
 ot_qwen_tp8_pv_join_t #(.J_LAT(7),.RESET_PIN(RP)) ref_dut(.clk(clk),.rst_n(ref_rst),.ts0(ts0),.ts1(ts1),.ts2(ts2),.ts3(ts3),.join_go(go),.sf(sf),.y(a),.y_valid(av),.fault(af));
 ot_qwen_tp8_pv_join_cold_t #(.J_LAT(7),.RESET_PIN(RP),.COLD_INIT(COLD),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.ts0(ts0),.ts1(ts1),.ts2(ts2),.ts3(ts3),.join_go(go),.sf(sf),.y(b),.y_valid(bv),.fault(bf));
 integer errors=0,checks=0,valids=0,i,j,e;
 task drive;
  begin for(j=0;j<32;j=j+1)begin
   ts0[32*j+:32]=$urandom;ts1[32*j+:32]=$urandom;
   ts2[32*j+:32]=$urandom;ts3[32*j+:32]=$urandom;
  end end
 endtask
 task compare;
  begin
   checks=checks+1;
   if(av!==bv||af!==bf)begin errors=errors+1;if(errors<8)$display("MISMATCH ctrl av=%b bv=%b af=%b bf=%b",av,bv,af,bf);end
   if(av&&bv)begin valids=valids+1;if(a!==b)begin errors=errors+1;if(errors<8)$display("MISMATCH valid data");end end
  end
 endtask
 initial begin
  ts0=0;ts1=0;ts2=0;ts3=0;
  for(e=0;e<3;e=e+1)begin
   @(negedge clk);rst_n=0;go=0;sf=0;
   repeat(8)@(negedge clk);
   if(COLD)begin
    checks=checks+1;
    if(dut.xr!==512'd0||dut.yr!==512'd0||b!==512'd0)begin
     errors=errors+1;$display("MISMATCH cold state xr=%h yr=%h y=%h",dut.xr,dut.yr,b);
    end
   end
   rst_n=1;
   // The two boot edges are explicit. First legal issue is immediate after them.
   repeat((COLD?2:0)+RP)@(negedge clk);
   for(i=0;i<4000;i=i+1)begin
    go=(i%40)==0;drive();
    @(negedge clk);compare();
   end
  end
  if(valids<100)begin errors=errors+1;$display("MISMATCH insufficient valid observations %0d",valids);end
  if(errors)$display("PV_JOIN_COLD FAIL MUT=%0d COLD=%0d errors=%0d checks=%0d valid=%0d",MUT,COLD,errors,checks,valids);
  else $display("PV_JOIN_COLD PASS MUT=%0d COLD=%0d checks=%0d valid=%0d",MUT,COLD,checks,valids);
  $finish;
 end
endmodule
