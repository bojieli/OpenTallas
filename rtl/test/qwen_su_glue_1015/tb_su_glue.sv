`timescale 1ns/1ps
module tb_su_glue;
 parameter integer MC=6;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [499:0] b; reg [2:0] bv;reg live;
 reg [95:0] cur,stride;
 reg [159:0] mem;
 reg [10:0] ov; reg [290:0] od;
 reg [383:0] vm;reg [255:0] cr;reg [127:0] em;reg[3:0]es;reg[11:0]mask;
 wire [383:0] eff,ve;wire[255:0] cm,cc;wire[127:0]ee,ec;wire[3:0]ss,sc;
 ot_qfd_su_align_group4 #(.ML(15),.VL(14),.MC(MC)) align_dut(clk,rst_n,vm,cr,em,es,mask,eff,cm,ee,ss);
 wire [383:0] vn; wire [11:0] mk;
 reg [383:0] hold_v;
 ot_hdc_delay #(.W(384),.D(1)) r_vm(clk,rst_n,vm,vn);
 ot_hdc_delay #(.W(256),.D(15-MC)) r_cr(clk,rst_n,cr,cc);
 ot_hdc_delay #(.W(132),.D(15)) r_em(clk,rst_n,{es,em},{sc,ec});
 ot_hdc_delay #(.W(12),.D(15),.RESET(1)) r_mk(clk,rst_n,mask,mk);
 genvar j;
 generate for(j=0;j<12;j=j+1)begin:hm
 assign ve[32*j+:32]=mk[j]?vn[32*j+:32]:hold_v[32*j+:32];
 end endgenerate
 always @(posedge clk) hold_v<=ve;
 function [23:0] offset_ref(input [23:0] base,input [23:0] step,input integer idx);
 integer n;reg[23:0] sum;begin sum=base;for(n=0;n<idx;n=n+1)sum=sum+step;offset_ref=sum;end
 endfunction
 wire [63:0] mismatch;
 genvar l;
 generate for(l=0;l<64;l=l+1)begin:lane
 wire [23:0] a=cur[95:72]+l*stride[95:72];
 wire [23:0] c=cur[71:48]+l*stride[71:48];
 wire [23:0] d=cur[47:24]+l*stride[47:24];
 wire [23:0] e=cur[23:0]+l*stride[23:0];
 wire [1062:0] got,exp;
 ot_qfd_su_lane_relay dut(clk,rst_n,b,bv,live,a,c,d,e,mem,ov,od,got[1062],got[1061:562],got[561:559],got[558],got[557:302],got[301:291],got[290:0]);
 ot_qfd_su_lane_relay_reference ref0(clk,rst_n,b,bv,live,offset_ref(cur[95:72],stride[95:72],l),offset_ref(cur[71:48],stride[71:48],l),offset_ref(cur[47:24],stride[47:24],l),offset_ref(cur[23:0],stride[23:0],l),mem,ov,od,exp[1062],exp[1061:562],exp[561:559],exp[558],exp[557:302],exp[301:291],exp[290:0]);
 assign mismatch[l]=(got!==exp);
 end endgenerate
 integer cycle,k,checks=0;
 reg [31:0] rng=32'h9a3742b1;
 function [31:0] next_r(input[31:0]q);begin next_r=(q^(q<<13));next_r=next_r^(next_r>>17);next_r=next_r^(next_r<<5);end endfunction
 initial begin
 b=0;bv=0;live=0;cur=0;stride=0;mem=0;ov=0;od=0;vm=0;cr=0;em=0;es=0;mask=0;
 for(cycle=0;cycle<700;cycle=cycle+1)begin
 @(negedge clk);
 rst_n=!(cycle<3 || (cycle>=230&&cycle<234) || (cycle>=450&&cycle<453));
 for(k=0;k<16;k=k+1)begin rng=next_r(rng);b[k*31+:31]=rng[30:0];end
 for(k=0;k<3;k=k+1)begin rng=next_r(rng);cur[k*32+:32]=rng; rng=next_r(rng);stride[k*32+:32]=rng;end
 for(k=0;k<5;k=k+1)begin rng=next_r(rng);mem[k*32+:32]=rng;end
 for(k=0;k<9;k=k+1)begin rng=next_r(rng);od[k*32+:32]=rng;end
 rng=next_r(rng);{bv,live,ov}=rng[14:0];
 for(k=0;k<12;k=k+1)begin rng=next_r(rng);vm[k*32+:32]=rng;end
 for(k=0;k<8;k=k+1)begin rng=next_r(rng);cr[k*32+:32]=rng;end
 for(k=0;k<4;k=k+1)begin rng=next_r(rng);em[k*32+:32]=rng;end
 rng=next_r(rng);es=rng[3:0];mask=cycle<25?12'hfff:rng[15:4];
 @(posedge clk); #1;
 if(cycle>30)begin
 if(|mismatch || {eff,cm,ee,ss}!=={ve,cc,ec,sc})begin $display("FAIL su_glue MC=%0d cycle=%0d lane=%h",MC,cycle,mismatch);$fatal;end
 checks=checks+1;
 end
 end
 $display("PASS su_glue MC=%0d cycles=%0d lane_checks=%0d align_checks=%0d resets=3",MC,checks,checks*64,checks);$finish;
 end
endmodule
