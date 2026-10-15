`timescale 1ns/1ps
module tb_hbm_su_static_side_native6r2;
 reg clock=0;always #0.4166665 clock=~clock;
 wire [5:0] clk={6{clock}};
 reg rst_n=0,v=0;
 reg [2:0] fn=0,fn_out=0;reg [31:0] x=0;
 wire [31:0] y,reference_y,fn_mutant_y,eg_mutant_y;
 wire fault,reference_fault,fn_mutant_fault,eg_mutant_fault;
 ot_hbm_su_static_side_native6r2 dut(.ck0($test$plusargs("MUT_CLOCK") ? 1'b0:clock),.ck1(clock),.ck2(clock),.ck3(clock),.ck4(clock),.ck5(clock),.rst_n(rst_n),.v(v),.fn(fn),.fn_out(fn_out),.x(x),.y(y),.fault(fault));
 ot_hdc_v41x_vec_side original(.clk(clock),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn_out),.y(reference_y),.fault(reference_fault));
 ot_hbm_su_static_side_native6r2 #(.MUT(1)) fn_mutant(.ck0(clock),.ck1(clock),.ck2(clock),.ck3(clock),.ck4(clock),.ck5(clock),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn_out),.y(fn_mutant_y),.fault(fn_mutant_fault));
 ot_hbm_su_static_side_native6r2 #(.MUT(2)) eg_mutant(.ck0(clock),.ck1(clock),.ck2(clock),.ck3(clock),.ck4(clock),.ck5(clock),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn_out),.y(eg_mutant_y),.fault(eg_mutant_fault));
 reg [31:0] ref_d0,ref_d1; reg fault_d0,fault_d1;
 always @(posedge clock)begin ref_d0<=reference_y;ref_d1<=ref_d0;fault_d0<=reference_fault;fault_d1<=fault_d0;end
 reg [71:0] drive_record,expected_record;
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
  for(i=0;i<rows+2;i=i+1)begin
   @(negedge clock);
   drive_record=(i<rows)?schedule[i]:72'd0;
   expected_record=(i>=2)?schedule[i-2]:72'd0;
   {v,fn,x}=drive_record[35:0];fn_out=drive_record[70:68];
   @(posedge clock);#0.01;
   if(expected_record[71])begin
    if(y!==expected_record[67:36])$fatal(1,"SIDE_WORD cycle=%0d fn=%0d actual=%h expected=%h",i,fn_out,y,expected_record[67:36]);
    if(y!==ref_d1)$fatal(1,"SIDE_REFERENCE cycle=%0d actual=%h original=%h",i,y,ref_d1);
    if(fn_mutant_y!==expected_record[67:36])begin
     fn_diffs=fn_diffs+1;
     if(fn_mode)$fatal(1,"SIDE_FN_MUTANT cycle=%0d fn=%0d",i,fn_out);
    end
    if(expected_record[70:68]==7 && eg_mutant_y!==expected_record[67:36])begin
     eg_diffs=eg_diffs+1;
     if(eg_mode)$fatal(1,"SIDE_EG_MUTANT cycle=%0d fn=%0d",i,fn_out);
    end
    checks=checks+1;per_fn[expected_record[70:68]]=per_fn[expected_record[70:68]]+1;
   end
   if(fault!==fault_d1)$fatal(1,"SIDE_FAULT_EQUIV");
  end
  if(checks!=16384||fn_diffs==0||eg_diffs==0)$fatal(1,"SIDE_COUNT %0d %0d %0d",checks,fn_diffs,eg_diffs);
  $display("PASS actualSIDE R2registeredfaces plus2edges sixphase0roots exactgolden=%0d originalcycleequiv=%0d RSQRT37=%0d SQRT31=%0d SPSQRT162=%0d EGATE104=%0d fnmutantdiff=%0d egatemutantdiff=%0d rows=%0d physicaltimingUNQUALIFIED",checks,checks,per_fn[2],per_fn[3],per_fn[6],per_fn[7],fn_diffs,eg_diffs,rows);
  $finish;
 end
endmodule
