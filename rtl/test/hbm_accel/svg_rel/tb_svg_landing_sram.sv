`timescale 1ps/1ps
module tb_svg_landing_sram;
 parameter integer MUT=0;
 reg hbm_clk=0,stream_clk=0,hbm_rst_n=0,stream_rst_n=0;
 always #512 hbm_clk=~hbm_clk;always #417 stream_clk=~stream_clk;
 reg in_v=0;wire in_ready,ir1,overflow,ov1;reg[284:0]in_data=0;
 reg reserve_v=0;reg[1:0]reserve_bank=0;reg[15:0]reserve_epoch=0;reg[11:0]reserve_total=272;reg stop=0;
 wire complete_v,cv1,fault,f1;wire[1:0]complete_bank,cb1;
 reg read_v=0;reg[1:0]read_bank=0;reg[5:0]read_row=0;wire[255:0]read_data,rd1;
 integer errors=0,completes=0,b,r,reads=0,tx=0;
 reg[255:0]exp_data;reg exp_v=0;
 function automatic[255:0]pattern(input integer bank,row);begin pattern={32'(bank),32'(row),32'(bank^row),32'(bank+row),32'(row*17),32'(bank+99),32'(row^32'hdeadbeef),32'(bank*64+row)};end endfunction
 ot_hbm_svc_sm8_landing_bank #(.BANK(3),.LBANKS(4)) old_bank(.*);
 ot_hbm_svc_sm8_landing_bank_sram285 #(.BANK(3),.FMUT(MUT)) new_bank(
 .hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),
 .in_v(in_v),.in_ready(ir1),.in_data(in_data),.overflow(ov1),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_total(reserve_total),.stop(stop),.complete_v(cv1),.complete_bank(cb1),.fault(f1),.read_v(read_v),.read_bank(read_bank),.read_row(read_row),.read_data(rd1));
 always @(posedge hbm_clk)begin #1;if(in_ready!==ir1||overflow!==ov1)errors=errors+1;end
 always @(posedge stream_clk)begin
  if(complete_v)completes=completes+1;
  if(complete_v!==cv1||(complete_v&&complete_bank!==cb1)||fault!==f1)errors=errors+1;
  if(read_v)begin exp_data=pattern(read_bank,read_row);exp_v=1;end else exp_v=0;
  #1;
  if(exp_v)begin reads=reads+1;if(read_data!==rd1||rd1!==exp_data)begin errors=errors+1;if(errors<6)$display("LANDING_DATA old=%h new=%h expected=%h",read_data,rd1,exp_data);end end
 end
 task idle;input integer n;begin repeat(n)@(negedge stream_clk);end endtask
 initial begin
  idle(4);hbm_rst_n=1;stream_rst_n=1;idle(16);
  for(b=0;b<4;b=b+1)begin
   @(negedge stream_clk);reserve_v=1;reserve_bank=2'(b);reserve_epoch=16'(b+7);@(negedge stream_clk);reserve_v=0;stop=1;idle(3);
   for(r=0;r<34;r=r+1)begin
    @(negedge hbm_clk);while(!in_ready)@(negedge hbm_clk);
    in_data={11'(3+8*r),2'(b),16'(b+7),pattern(b,r)};in_v=1;
    @(negedge hbm_clk);in_v=0;tx=tx+1;
    if(r==7)begin @(negedge stream_clk);stop=0;end
   end
   idle(12);
  end
  for(b=0;b<4;b=b+1)for(r=0;r<34;r=r+1)begin
   @(negedge stream_clk);read_v=1;read_bank=2'(b);read_row=6'(r);
  end
  @(negedge stream_clk);read_v=0;idle(4);
  if(completes!=4||reads!=136||fault||overflow)errors=errors+1;
  $display("SVG_LANDING_SRAM %s mut=%0d errors=%0d tx=%0d reads=%0d completes=%0d fault=%0d",errors==0?"PASS":"FAIL",MUT,errors,tx,reads,completes,f1);
  if(errors)$fatal(1,"landing mismatch");$finish;
 end
endmodule
