`timescale 1ns/1ps
module tb_hbm_su_static_side;
 reg clock=0;always #0.4166665 clock=~clock;
 wire [5:0] clk={6{clock}};
 reg rst_n=0,v=0;
 reg [2:0] fn=0,fn_out=0;reg [31:0] x=0;
 wire [31:0] y,reference_y,fn_mutant_y,eg_mutant_y;
 wire fault,reference_fault,fn_mutant_fault,eg_mutant_fault;
 ot_hbm_su_static_side dut(.*);
 ot_hdc_v41x_vec_side original(.clk(clock),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn_out),.y(reference_y),.fault(reference_fault));
 ot_hbm_su_static_side #(.MUT(1)) fn_mutant(.clk(clk),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn_out),.y(fn_mutant_y),.fault(fn_mutant_fault));
 ot_hbm_su_static_side #(.MUT(2)) eg_mutant(.clk(clk),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn_out),.y(eg_mutant_y),.fault(eg_mutant_fault));
 reg [71:0] schedule[0:65535];
 reg [1023:0] data_dir;
 integer rows=0,i,checks=0,fn_diffs=0,eg_diffs=0;
 integer per_fn[0:7];
 reg fn_mode=0,eg_mode=0;
 initial begin
  for(i=0;i<8;i=i+1)per_fn[i]=0;
  fn_mode=$test$plusargs("MUT_FN");eg_mode=$test$plusargs("MUT_EG");
  if(!$value$plusargs("DATA=%s",data_dir)||!$value$plusargs("ROWS=%d",rows))$fatal(1,"ARGS");
  $readmemh({data_dir,"/schedule.hex"},schedule,0,rows-1);
  repeat(8)@(negedge clock);rst_n=1;
  for(i=0;i<rows;i=i+1)begin
   @(negedge clock);
   {v,fn,x}=schedule[i][35:0];fn_out=schedule[i][70:68];
   @(posedge clock);#0.01;
   if(schedule[i][71])begin
    if(y!==schedule[i][67:36])$fatal(1,"SIDE_WORD cycle=%0d fn=%0d actual=%h expected=%h",i,fn_out,y,schedule[i][67:36]);
    if(y!==reference_y)$fatal(1,"SIDE_REFERENCE cycle=%0d actual=%h original=%h",i,y,reference_y);
    if(fn_mutant_y!==schedule[i][67:36])begin
     fn_diffs=fn_diffs+1;
     if(fn_mode)$fatal(1,"SIDE_FN_MUTANT cycle=%0d fn=%0d",i,fn_out);
    end
    if(fn_out==7 && eg_mutant_y!==schedule[i][67:36])begin
     eg_diffs=eg_diffs+1;
     if(eg_mode)$fatal(1,"SIDE_EG_MUTANT cycle=%0d fn=%0d",i,fn_out);
    end
    checks=checks+1;per_fn[fn_out]=per_fn[fn_out]+1;
   end
   if(fault!==reference_fault)$fatal(1,"SIDE_FAULT_EQUIV");
  end
  if(checks!=16384||fn_diffs==0||eg_diffs==0)$fatal(1,"SIDE_COUNT %0d %0d %0d",checks,fn_diffs,eg_diffs);
  $display("PASS actualSIDE sixphase0roots exactgolden=%0d originalcycleequiv=%0d RSQRT37=%0d SQRT31=%0d SPSQRT162=%0d EGATE104=%0d fnmutantdiff=%0d egatemutantdiff=%0d rows=%0d physicaltimingUNQUALIFIED",checks,checks,per_fn[2],per_fn[3],per_fn[6],per_fn[7],fn_diffs,eg_diffs,rows);
  $finish;
 end
endmodule
