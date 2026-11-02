`timescale 1ps/1ps
module column #(parameter INSTANCE="", parameter integer MB=0)(input wire clk,input wire issue,input wire[12:0] counter,output wire[273:0] rd0,rd1);
ot_rom_4096x274_m8 #(.INSTANCE(MB == 0 ? $sformatf("%s_0", INSTANCE) : $sformatf("%sb_0", INSTANCE))) r0(.clk(clk),.ce_in(issue&&!counter[0]),.addr_in(counter[12:1]),.rd_out(rd0));
ot_rom_4096x274_m8 #(.INSTANCE(MB == 0 ? $sformatf("%s_1", INSTANCE) : $sformatf("%sb_1", INSTANCE))) r1(.clk(clk),.ce_in(issue&&counter[0]),.addr_in(counter[12:1]),.rd_out(rd1));
endmodule
module tb;localparam NC=14,NA=9;reg clk=0;always begin #416 clk=1;#417 clk=0;end
reg issue=0;reg[12:0]counter=0;wire[273:0]d0[0:NC-1],d1[0:NC-1];reg[273:0]gold[0:NC*2*NA-1];
integer i,c,b,n,errors=0;reg[11:0]addr[0:NA-1];reg[273:0]old0[0:NC-1],old1[0:NC-1];
column #(.INSTANCE("u_f_0L01.u_r0.u_e1e"),.MB(0)) c0(clk,issue,counter,d0[0],d1[0]);
column #(.INSTANCE("u_f_0L01.u_r0.u_e1w"),.MB(0)) c1(clk,issue,counter,d0[1],d1[1]);
column #(.INSTANCE("u_f_0L01.u_r1.u_e10e"),.MB(0)) c2(clk,issue,counter,d0[2],d1[2]);
column #(.INSTANCE("u_f_0L01.u_r1.u_e10w"),.MB(0)) c3(clk,issue,counter,d0[3],d1[3]);
column #(.INSTANCE("u_f_0L01.u_r1.u_e5e"),.MB(0)) c4(clk,issue,counter,d0[4],d1[4]);
column #(.INSTANCE("u_f_0L01.u_r1.u_e5w"),.MB(0)) c5(clk,issue,counter,d0[5],d1[5]);
column #(.INSTANCE("u_f_0L01.u_r2.u_e15e"),.MB(0)) c6(clk,issue,counter,d0[6],d1[6]);
column #(.INSTANCE("u_f_0L01.u_r2.u_e15w"),.MB(0)) c7(clk,issue,counter,d0[7],d1[7]);
column #(.INSTANCE("u_f_0L02.u_r0.u_e4e"),.MB(0)) c8(clk,issue,counter,d0[8],d1[8]);
column #(.INSTANCE("u_f_0L02.u_r0.u_e4w"),.MB(0)) c9(clk,issue,counter,d0[9],d1[9]);
column #(.INSTANCE("u_f_0L02.u_r1.u_e8e"),.MB(0)) c10(clk,issue,counter,d0[10],d1[10]);
column #(.INSTANCE("u_f_0L02.u_r1.u_e8w"),.MB(0)) c11(clk,issue,counter,d0[11],d1[11]);
column #(.INSTANCE("u_f_0L02.u_r2.u_e13e"),.MB(0)) c12(clk,issue,counter,d0[12],d1[12]);
column #(.INSTANCE("u_f_0L02.u_r2.u_e13w"),.MB(0)) c13(clk,issue,counter,d0[13],d1[13]);
initial begin $readmemh("wanted.hex",gold);
addr[0]=0;
addr[1]=1;
addr[2]=7;
addr[3]=8;
addr[4]=63;
addr[5]=511;
addr[6]=1023;
addr[7]=2047;
addr[8]=4095;
for(i=0;i<NA;i=i+1)begin for(b=0;b<2;b=b+1)begin
@(negedge clk);issue=1;counter={addr[i],1'b0}+b;
for(c=0;c<NC;c=c+1)begin old0[c]=d0[c];old1[c]=d1[c];end
@(posedge clk);#1;
for(c=0;c<NC;c=c+1)begin
if((b?d1[c]:d0[c])!==gold[(c*2+b)*NA+i])begin errors=errors+1;$display("BF_IMAGE_MISMATCH c%0d bank%0d address%0d",c,b,addr[i]);end
if(i>0 && (b?d0[c]:d1[c])!==(b?old0[c]:old1[c]))errors=errors+1;
end end end
$display("BF_IMAGE_RESULT columns%0d images%0d samples%0d errors%0d clock833",NC,NC*2,NC*2*NA,errors);
if(errors)$fatal(1,"BF_IMAGE_SELECTOR_FAIL");$display("BF_IMAGE_SELECTOR_PASS");$finish;end endmodule
