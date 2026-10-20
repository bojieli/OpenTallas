`timescale 1ns/1ps
module tb_fp32_mul_pvfin;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 wire [25:0] rr;
 ot_rst_relay_bounded32 #(.REGIONS(26)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg [31:0] da=0,db=0;reg vi=0;
 (* keep="true",dont_touch="true" *) reg [31:0] a[0:2],b[0:2];
 reg v=0;
 always @(posedge clk)begin
  for(integer i=0;i<3;i=i+1)begin a[i]<=da;b[i]<=db;end
  v<=vi;
 end
 wire [31:0] y0,y1;wire [1:0] e0,e1;wire v0,v1;
 ot_hdc_fp32_mul_lat #(.LAT(6)) cold(.clk(clk),.rst_n(rr[16]),.valid_in(v),.a(a[0]),.b(b[0]),.y(y0),.err(e0),.valid_out(v0));
 ot_hdc_fp32_mul_lat_pvfin #(.LAT(6)) dut(.clk(clk),.rst_v(rr),.valid_in(v),.a(a[0]),.a_nrm({a[2],a[1]}),
  .b(b[0]),.b_nrm({b[2],b[1]}),.y(y1),.err(e1),.valid_out(v1));
 integer checked=0,errors=0,seed=1,cycles=0;
 always @(negedge clk)begin
  cycles=cycles+1;
  if(rr[16]&&cycles>10)begin
   if(v0!==v1||(v0&&{y0,e0}!=={y1,e1}))begin
    errors=errors+1;
    if(errors<6)$display("MUL_PVFIN MISMATCH cycle=%0d v=%b/%b y=%h/%h err=%b/%b",cycles,v0,v1,y0,y1,e0,e1);
   end
   if(v0)checked=checked+1;
  end
 end
 function automatic [31:0] corner(input integer k);
  case(k)
   0:corner=32'h00000000;1:corner=32'h80000000;
   2:corner=32'h00000001;3:corner=32'h80000001;
   4:corner=32'h007fffff;5:corner=32'h807fffff;
   6:corner=32'h00800000;7:corner=32'h80800000;
   8:corner=32'h3f800000;9:corner=32'hbf800000;
   10:corner=32'h3f000000;11:corner=32'h40000000;
   12:corner=32'h7f7fffff;13:corner=32'hff7fffff;
   14:corner=32'h7f800000;15:corner=32'hff800000;
   16:corner=32'h7fc00000;17:corner=32'hffc12345;
   18:corner=32'h3f7fffff;19:corner=32'h3f800001;
   20:corner=32'h00010000;21:corner=32'h00100000;
   22:corner=32'h00400000;default:corner=32'h3eaaaaab;
  endcase
 endfunction
 initial begin
  if($value$plusargs("SEED=%d",seed));
  repeat(3)@(negedge clk);rst_n=1;repeat(6)@(negedge clk);
  for(integer epoch=0;epoch<3;epoch=epoch+1)begin
   for(integer i=0;i<24;i=i+1)for(integer j=0;j<24;j=j+1)begin
    @(negedge clk);da=corner(i);db=corner(j);vi=1;
   end
   for(integer i=0;i<4000;i=i+1)begin
    @(negedge clk);da=$random(seed);db=$random(seed);vi=(i%7)!=0;
   end
   // Reset with occupied arithmetic; ref and bounded leaves share phase.
   @(negedge clk);rst_n=0;vi=0;
   repeat(3)@(negedge clk);rst_n=1;repeat(6)@(negedge clk);
  end
  vi=0;repeat(12)@(negedge clk);
  if(errors==0&&checked>11000)$display("MUL_PVFIN PASS checked=%0d errors=%0d",checked,errors);
  else $fatal(1,"MUL_PVFIN FAIL checked=%0d errors=%0d",checked,errors);
  $finish;
 end
endmodule
