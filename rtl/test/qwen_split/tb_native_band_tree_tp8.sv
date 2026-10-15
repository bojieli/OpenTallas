`timescale 1ns/1ps
// Full 16-lane expected upper arithmetic versus four real quarter upper leaves.
// Expected side uses the real unsliced NL16 upper master; DUT owns all real
// mapped-SRAM band lanes. No expected value feeds a DUT port.
module tb_native_band_tree_tp8;
 reg ck=0; always #5 ck=~ck;
 reg rst_n=0;
 reg [25:0] c=0,sel=0;
 reg [4095:0] tw0=0,tw1=0,tw2=0;
 wire [4095:0] ty0,ty1,ty2;
 wire [3:0] uf;wire [2:0] bf;
 qfd_native_band_tree_tp8 dut(.ck_band({3{ck}}),.ck_lane({48{ck}}),.ck_upper({4{ck}}),
 .rst_n(rst_n),.lnk(18'd0),.sel(sel),.lc0(c),.lc1(c),.lc2(c),
 .tw0(tw0),.tw1(tw1),.tw2(tw2),.ty0(ty0),.ty1(ty1),.ty2(ty2),.uf(uf),.band_fault(bf));
 wire [1535:0] exp_ty;wire exp_use,exp_v,exp_fault;
 ot_qfd_band_upper #(.NL(16),.NB(3),.LNK(0),.DLY(1),.TREE_LAT(7),.TCUT(7),.LG(12),.RPIN(1)) expected(
 .clk(ck),.rst_n(rst_n),.pw({dut.u_band2.pw[511:0],dut.u_band1.pw[511:0],dut.u_band0.pw[511:0]}),
 .pw_v({dut.u_band2.pw[512],dut.u_band1.pw[512],dut.u_band0.pw[512]}),
 .lf(bf),.sel_e(sel[12:0]),.tv_e(sel[25:13]),.tt_ty(exp_ty),.tt_use(exp_use),.tt_v(exp_v),.fault(exp_fault));
 integer cycle,l,k,errs=0,checks=0; reg[31:0]seed=32'h26ab091e;
 function automatic[31:0] next(input[31:0]x);next=(x^(x<<13))^((x^(x<<13))>>17);endfunction
 initial begin
 repeat(8)@(negedge ck);rst_n=1;
 for(cycle=0;cycle<450;cycle=cycle+1)begin
 @(negedge ck);
 // Distinct, exactly representable finite positive FP32 words per lane/band.
 for(k=0;k<8;k=k+1)for(l=0;l<16;l=l+1)begin
 seed=next(seed);seed=seed^(seed<<5);
 tw0[32*(16*k+l)+:32]=32'h3f000000|{9'd0,seed[22:0]};
 tw1[32*(16*k+l)+:32]=32'h40000000|{9'd0,seed[22:0]};
 tw2[32*(16*k+l)+:32]=32'h40800000|{9'd0,seed[22:0]};
 end
 c={13'h1fff,cycle[12:0]};sel={13'h1fff,cycle[12:0]};
 @(posedge ck);#1;
 if(cycle>160)begin
 checks=checks+1;
 if(dut.tt0 !== {exp_v,exp_use,exp_ty})begin
 errs=errs+1;if(errs<4)$display("upper lane mismatch cycle=%0d",cycle);
 end
 end
 end
 $display("NATIVE_BAND_TREE checks=%0d errors=%0d",checks,errs);
 if(errs || checks!=289)$fatal(1,"native tree quarter composition mismatch");
 $finish;
 end
endmodule
