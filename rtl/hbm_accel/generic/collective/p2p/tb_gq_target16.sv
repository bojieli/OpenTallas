`timescale 1ns/1ps
module tb_gq_target16;
reg clk=0;always #5 clk=~clk;
wire clk_cap=clk;
reg rst_n=0,cfg_v=0,desc_v=0,launch_v=0,program_active=0;
reg[7:0]tgt=48,cfg_target=48;reg[11:0]cfg_addr=0,desc_base=0;
reg[255:0]cfg_data=0;reg[12:0]desc_limit=0;reg[15:0]desc_loops=1;
wire we0,we1,sv0,sv1,ready0,ready1,fault0,fault1;
wire[7:0]wa0,wa1,sb0,sb1;wire[8:0]sl0,sl1;wire[15:0]lp0,lp1;
wire[255:0]wd0,wd1;wire[12:0]bw;wire[103:0]ba;wire[12:0]bs;
integer mode=0,checks=0,writes=0,starts=0;reg compare=1;
ot_static_program_target #(.PCW(8),.TGT_PIN(1)) u0(.clk(clk),.rst_n(rst_n),.clk_cap(clk_cap),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.program_cfg_we(we0),.program_cfg_addr(wa0),.program_cfg_data(wd0),.program_start_v(sv0),.program_start_base(sb0),.program_start_limit(sl0),.program_start_loops(lp0),.configured(ready0),.fault(fault0));
ot_hgi_coll_gq_target16 #(.PCW(8),.TGT_PIN(1)) u1(.clk(clk),.rst_n(rst_n),.clk_cap(clk_cap),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.program_cfg_we(we1),.program_cfg_addr(wa1),.program_cfg_data(wd1),.program_start_v(sv1),.program_start_base(sb1),.program_start_limit(sl1),.program_start_loops(lp1),.configured(ready1),.fault(fault1),.cfg_bank_we(bw),.cfg_bank_addr(ba),.start_bank_v(bs));

always @(posedge clk) begin
 #1;
 if(rst_n) begin
  checks=checks+1;
  if(u1.reset_ctrl_copies!=={8{u1.reset_ctrl_copies[0]}})$fatal(1,"T16 RESET copies diverged");
  if(compare && {we0,sv0,ready0,fault0}!=={we1,sv1,ready1,fault1})
   $fatal(1,"T16 DIFFERENTIAL control mode%0d old%b new%b",mode,{we0,sv0,ready0,fault0},{we1,sv1,ready1,fault1});
  if(compare && we0 && {wa0,wd0}!=={wa1,wd1})$fatal(1,"T16 DIFFERENTIAL write");
  if(compare && sv0 && {sb0,sl0,lp0}!=={sb1,sl1,lp1})$fatal(1,"T16 DIFFERENTIAL launch");
  if(bw!=={13{we1}} || bs!=={13{sv1}})$fatal(1,"T16 PRIVATE strobe mismatch");
  if(we1)begin
   writes=writes+1;
   for(integer k=0;k<13;k=k+1)if(ba[8*k+:8]!==wa1)$fatal(1,"T16 PRIVATE address copy%0d",k);
  end
  if(sv1)starts=starts+1;
 end
end
task step;begin @(posedge clk);#2;end endtask
task reset;begin @(negedge clk);rst_n=0;cfg_v=0;desc_v=0;launch_v=0;repeat(3)step();@(negedge clk);rst_n=1;repeat(5)step();end endtask
task write_row(input integer row);begin
 @(negedge clk);cfg_addr=row;cfg_data={32'hc7a10000|row,32'h12345678^row,32'h87654321^row,32'hfedcba98^row,32'h76543210^row,32'h01234567^row,32'h89abcdef^row,32'h55aa00ff^row};cfg_v=1;
 step();if(we1)$fatal(1,"T16 write early");
 @(negedge clk);cfg_v=0;step();
 if(row<16&&!we1)$fatal(1,"T16 write missed second edge");
 step();if(we1)$fatal(1,"T16 write pulse too long");
 repeat(2)step();
end endtask
task descriptor(input integer base,input integer lim);begin
 @(negedge clk);desc_base=base;desc_limit=lim;desc_loops=3;desc_v=1;
 step();@(negedge clk);desc_v=0;step();
end endtask
task wait_ready;begin
 for(integer k=0;k<25;k=k+1)begin step();if(ready1)break;end
 if(!ready1||fault1)$fatal(1,"T16 descriptor not ready fault%b",fault1);
end endtask
task launch;begin
 @(negedge clk);launch_v=1;step();if(sv1)$fatal(1,"T16 launch early");
 @(negedge clk);launch_v=0;step();if(!sv1)$fatal(1,"T16 launch missed second edge");
 step();if(sv1)$fatal(1,"T16 launch pulse too long");
end endtask
initial begin
 void'($value$plusargs("mode=%d",mode));compare=(mode==0);reset();
 if(mode==0)begin
  for(integer r=0;r<16;r=r+1)write_row(r);
  descriptor(0,16);wait_ready();launch();
  descriptor(0,16);wait_ready();launch();
  reset();for(integer r=0;r<6;r=r+1)write_row(r);
  descriptor(0,6);wait_ready();launch();
  // New image generation invalidates unwritten old rows.
  write_row(0);descriptor(0,6);repeat(20)step();
  if(!fault1||ready1)$fatal(1,"T16 stale installed generation escaped");
  reset();write_row(15);descriptor(15,16);wait_ready();launch();
  if(writes!=24||starts!=4)$fatal(1,"T16 witness count writes%0d starts%0d",writes,starts);
  $display("GQ_TARGET16 PASS checks%0d writes%0d launches%0d cfg_launch_edges2 rows16 resetreload reuse generation",checks,writes,starts);
 end else if(mode==1)begin
  for(integer j=0;j<5;j=j+1)begin
   reset();case(j)0:write_row(16);1:write_row(31);2:write_row(255);3:write_row(256);4:write_row(4095);endcase
   if(!fault1||we1||bw!=0)$fatal(1,"T16 malformed address escaped index%0d",j);
   repeat(4)step();if(!fault1)$fatal(1,"T16 fault not sticky");
   @(negedge clk);launch_v=1;step();@(negedge clk);launch_v=0;repeat(3)step();
   if(sv1||starts!=0||writes!=0)$fatal(1,"T16 bad address launched or aliased");
  end
  $display("GQ_TARGET16 ADDR PASS fullwidth16_31_255_256_4095 stickyfault noalias nolaunch");
 end else begin
  write_row(0);descriptor(0,17);
  if(!fault1||sv1||ready1)$fatal(1,"T16 oversized descriptor not earlyfault");
  repeat(20)step();if(!fault1||sv1||ready1)$fatal(1,"T16 oversized descriptor escaped");
  $display("GQ_TARGET16 LIMIT PASS limit17 immediate stickyfault nolaunch");
 end
 $finish;
end
endmodule
