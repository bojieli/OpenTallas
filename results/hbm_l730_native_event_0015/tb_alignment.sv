`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;
reg rst_n=0;reg [1021:0] ctl;reg [319:0] a,b;
wire [1021:0] xo0,xo1,oldxo0,oldxo1;
wire ex0,ex1,oex0,oex1;
ot_dp_st #(.W(1022)) ux0(clk,rst_n,ctl,rst_n,xo0,ex0);
ot_dp_st #(.W(1022)) ux1(clk,rst_n,ctl,rst_n,xo1,ex1);
ot_dp_st #(.W(1022)) uoldx0(clk,rst_n,ctl,rst_n,oldxo0,oex0);
ot_dp_st #(.W(1022)) uoldx1(clk,rst_n,ctl,rst_n,oldxo1,oex1);
wire [1661:0] oldq,g0,gold;wire oe,ge0,golde;
ot_dp_st #(.W(1662)) oldface(clk,rst_n,{b,a,ctl},rst_n,oldq,oe);
ot_dp_st #(.W(1662)) gold0(clk,rst_n,oldq,oe,g0,ge0);
ot_dp_st #(.W(1662)) gold1(clk,rst_n,g0,ge0,gold,golde);
wire [639:0] sq;wire se;
ot_dp_st #(.W(640)) store0(clk,rst_n,{b,a},rst_n,sq,se);
wire [1021:0] selected_ctl;
`ifdef MUTANT_CTL_BYPASS
assign selected_ctl=ctl;
`else
assign selected_ctl=xo0;
`endif
wire [1661:0] s1,nq;wire e1,ne;
ot_dp_st #(.W(1662)) stage1(clk,rst_n,{sq,selected_ctl},se&ex0,s1,e1);
ot_dp_st #(.W(1662)) newface(clk,rst_n,s1,e1,nq,ne);
// Local group epoch variant: two additional epoch FFs, same two added edges.
wire [1021:0] lc;wire [319:0] la,lb;wire ec,ea,eb,le;wire [1661:0] lq;
ot_dp_st #(.W(1022)) localc(clk,rst_n,xo0,ex0,lc,ec);
ot_dp_st #(.W(320)) locala(clk,rst_n,sq[319:0],se,la,ea);
ot_dp_st #(.W(320)) localb(clk,rst_n,sq[639:320],se,lb,eb);
ot_dp_st #(.W(1662)) localface(clk,rst_n,{lb,la,lc},ec&ea&eb,lq,le);
integer i,j,checked=0,caught=0,resets=0,reset_edges=0;reg [31:0] rng=32'h7301234;
function [31:0] step(input [31:0] x);step=(x<<1)^((x[31])?32'h04c11db7:0);endfunction
initial begin
ctl=0;a=0;b=0;
for(i=0;i<4200;i=i+1)begin
 @(negedge clk);
 if(i%79==0)resets=resets+1;
 rst_n=(i%79>=4);if(!rst_n)reset_edges=reset_edges+1;
 for(j=0;j<1022;j=j+1)begin rng=step(rng);ctl[j]=rng[13];end
 for(j=0;j<320;j=j+1)begin rng=step(rng);a[j]=rng[11];rng=step(rng);b[j]=rng[17];end
 @(posedge clk);#1;
 if(i>3)begin
  if(xo0!==oldxo0||xo1!==oldxo1||ex0!==oex0||ex1!==oex1)$fatal(1,"existing XO output changed");
  if(ne!==golde||le!==golde)$fatal(1,"epoch alignment changed");
  if(golde)begin
   checked=checked+1;
   if(lq!==gold)$fatal(1,"local group epoch variant differs");
   if(nq!==gold)begin
`ifdef MUTANT_CTL_BYPASS
    caught=caught+1;
`else
    $fatal(1,"source payload alignment differs cycle%0d",i);
`endif
   end
  end
 end
end
`ifdef MUTANT_CTL_BYPASS
if(caught==0)$fatal(1,"mutant not caught");
$display("PASS MUTANT_CAUGHT=%0d CHECKED=%0d RESETS=%0d RESET_EDGES=%0d CLOCK_PS=833",caught,checked,resets,reset_edges);
`else
if(checked<3800)$fatal(1,"insufficient checked cycles");
$display("PASS ALIGNMENT_OLD_PLUS2 CHECKED=%0d XO_UNCHANGED=2 RESETS=%0d RESET_EDGES=%0d CLOCK_PS=833 DATA_BITS=1662",checked,resets,reset_edges);
`endif
$finish;end
endmodule
