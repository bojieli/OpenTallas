`timescale 1ns/1ps
module tb_selector_reset_program;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [3:0] op=0;reg[1:0] pass=0;reg[7:0] addr=0;reg[9:0]k=32;
 reg[2367:0]in_line=0;
 wire[3:0] gv,lv,cv,mv;wire[2367:0]gl,ll,cl,ml;wire gf,lf,cf,mf;
 ot_hbm_idx_selector_static_sel_gold #(.STRUCT(1)) gold(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(op),.pass(pass),.addr(addr),.k(k),.in_line(in_line),.selected_v(gv),.selected_line(gl),.fault(gf));
 ot_hbm_idx_selector_static_sel #(.STRUCT(1),.LOCAL_RESET(0)) legacy(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(op),.pass(pass),.addr(addr),.k(k),.in_line(in_line),.selected_v(lv),.selected_line(ll),.fault(lf));
 ot_hbm_idx_selector_static_sel #(.STRUCT(1),.LOCAL_RESET(1)) candidate(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(op),.pass(pass),.addr(addr),.k(k),.in_line(in_line),.selected_v(cv),.selected_line(cl),.fault(cf));
 ot_hbm_idx_selector_static_sel #(.STRUCT(1),.LOCAL_RESET(1),.MUT(4)) mutant(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(op),.pass(pass),.addr(addr),.k(k),.in_line(in_line),.selected_v(mv),.selected_line(ml),.fault(mf));
 integer checked=0,caught=0,nonzero=0,phase=0;reg compare=0;
 always @(negedge clk)if(compare)begin
  checked=checked+1;
  if({gv,gl,gf}!=={lv,ll,lf})$fatal(1,"default-off differs cycle %0d phase %0d",checked,phase);
  if({gv,gl,gf}!=={cv,cl,cf})$fatal(1,"local reset differs cycle %0d phase %0d",checked,phase);
  if({gv,gl,gf}!=={mv,ml,mf})caught=caught+1;
  if(|gv)nonzero=nonzero+1;
 end
 task automatic tick(input integer o,input integer a,input integer p);
  begin @(negedge clk);op=4'(o);addr=8'(a);pass=2'(p);end
 endtask
 task automatic reset_boot;
  begin compare=0;tick(0,0,0);repeat(8)tick(0,0,0);rst_n=0;repeat(16)tick(0,0,0);rst_n=1;repeat(8)tick(0,0,0);compare=1;end
 endtask
 initial begin
  for(integer frame=0;frame<3;frame=frame+1)begin
   reset_boot();phase=1;tick(1,0,0);tick(3,0,0);
   for(integer a=0;a<8;a=a+1)begin
    tick(2,a,0);
    for(integer q=0;q<4;q=q+1)for(integer l=0;l<16;l=l+1)begin
     in_line[q*592+l*37]=1;
     in_line[q*592+l*37+1+:16]=16'(16'h3e00+frame*31+q*13+l+a);
     in_line[q*592+l*37+17+:20]=20'(a*64+q*16+l);
    end
   end
   tick(0,0,0);repeat(3)tick(0,0,0);
   for(integer b=31;b>=0;b=b-1)tick(5,b,0);
   for(integer p=1;p<3;p=p+1)begin
    phase=2;tick(3,0,p);for(integer a=0;a<8;a=a+1)tick(4,a,p);
    repeat(3)tick(0,0,p);
    for(integer b=(p==2?63:31);b>=0;b=b-1)tick(5,b,p);
   end
   phase=3;for(integer a=0;a<8;a=a+1)tick(6,a,2);
   repeat(3)tick(0,0,2);tick(7,0,2);repeat(6)tick(0,0,2);
   phase=4;tick(8,0,0);repeat(4)tick(0,0,0);
  end
  if(nonzero<12||caught<12)$fatal(1,"insufficient meaningful outputs or mutant sensitivity %0d %0d",nonzero,caught);
  $display("SELECTOR_RESET_PROGRAM_PASS compared=%0d valid_cycles=%0d mutant_caught=%0d extra_boot_cycles=2",checked,nonzero,caught);$finish;
 end
endmodule
