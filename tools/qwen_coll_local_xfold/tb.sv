`timescale 1ns/1ps
module tb;
parameter integer MUT=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,red=0;reg[1:0]pkg=0;
reg[127:0]td=0,sr0=0,sr1=0,sr2=0;
wire[511:0]old_src;
for(genvar rank=0;rank<4;rank=rank+1)begin:g_old
 wire[1:0]jqs=2'(rank)-pkg+2'd3;
 wire[3:0]sel;
 ot_coll_rep_reg #(.W(4),.ID(32+rank*4),.RST(0))u_sel(.clk(clk),.rst_n(1'b1),
  .d({2'(rank)==pkg,(2'(rank)!=pkg)&&jqs==2'd2,(2'(rank)!=pkg)&&jqs==2'd1,(2'(rank)!=pkg)&&jqs==2'd0}),.q(sel));
 assign old_src[rank*128+:128]=(td&{128{sel[3]}})|(sr2&{128{sel[2]}})|(sr1&{128{sel[1]}})|(sr0&{128{sel[0]}});
end
wire[127:0]ref_sum,sum;wire ref_v,ref_e,v,e;
ot_coll_fold_slice #(.N(4),.ADD_LAT(7),.SEAM(1))u_ref(
 .clk(clk),.rst_n(rst_n),.red_in(red),.src(old_src),.sum(ref_sum),.v_out(ref_v),.e_out(ref_e));
ot_coll_local_xfold #(.MUT_RANK(MUT))u_dut(.ctl_ck(clk),.fold_ck(clk),.rst_n(rst_n),.pkg_s(pkg),.red_in(red),
 .td(td),.sr0(sr0),.sr1(sr1),.sr2(sr2),.sum(sum),.v_out(v),.e_out(e));
reg[22:0]valid_history=0;
always @(posedge clk or negedge rst_n)if(!rst_n)valid_history<=0;else valid_history<={valid_history[21:0],red};
integer errors=0,samples=0,data_errors=0,valid_errors=0,error_errors=0;
always @(negedge clk)begin
 if(v!==ref_v||v!==valid_history[22])begin errors=errors+1;valid_errors=valid_errors+1;end
 if(ref_v)begin
  samples=samples+1;
  if(sum!==ref_sum)begin errors=errors+1;data_errors=data_errors+1;end
  if(e!==ref_e)begin errors=errors+1;error_errors=error_errors+1;end
 end
end
integer ep,i,l;
initial begin
 for(ep=0;ep<4;ep=ep+1)begin
  @(negedge clk);rst_n=0;red=0;pkg=2'(ep);repeat(5)@(negedge clk);rst_n=1;
  repeat(20)@(negedge clk);
  for(i=0;i<128;i=i+1)begin
   red=(i%8)!=7;
   for(l=0;l<4;l=l+1)begin
    case(i%4)
     0:begin // Non-associative cancellation: swapping ranks changes rounding.
      td[32*l+:32]=32'h60ad78ec+32'(l);sr0[32*l+:32]=32'he0ad78ec+32'(l);
      sr1[32*l+:32]=32'h40400000+32'(i+l);sr2[32*l+:32]=32'h40800000+32'(l);
     end
     1:begin
      td[32*l+:32]=32'h3f000000+32'(i*7919+l);sr0[32*l+:32]=32'hbf100000+32'(i*1543+l);
      sr1[32*l+:32]=32'h3e000000+32'(i*971+l);sr2[32*l+:32]=32'h3d000000+32'(i*197+l);
     end
     2:begin td[32*l+:32]=32'h80000000;sr0[32*l+:32]=0;sr1[32*l+:32]=32'(1+l);sr2[32*l+:32]=32'h00800000;end
     3:begin td[32*l+:32]=32'h7f800000;sr0[32*l+:32]=32'hff800000;sr1[32*l+:32]=32'h7fc12345;sr2[32*l+:32]=32'h3f800000;end
    endcase
   end
   @(negedge clk);
  end
  red=0;repeat(40)@(negedge clk);
 end
 $display("LOCAL_XFOLD MUT=%0d samples=%0d data_errors=%0d valid_errors=%0d error_errors=%0d errors=%0d",MUT,samples,data_errors,valid_errors,error_errors,errors);
 if(samples!=448)$fatal(1,"wrong full-shape sample count");
 if(errors)$fatal(1,"LOCAL_XFOLD FAIL");
 $display("LOCAL_XFOLD PASS");$finish;
end
endmodule
