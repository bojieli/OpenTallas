`timescale 1ns/1ps
// Declared external configuration -> 128 actual SRAM macro models -> fixed controller.
// The reference word functions are used only for external boot stimuli and comparisons.
module tb_s81_su_calendar_store_full #(parameter BAD_READY=0);
 localparam DEPTH=4096, AW=12;
 reg clk=0,rst=0,we=0,commit=0,arm=0,raw_phase=1,raw_arm=0,raw_run=0;
 always #0.4167 clk=~clk;
 reg [31:0] raw_cycle=0;
 reg [AW-1:0] addr=0;reg [3:0] lane=0;reg [63:0] data=0;
 wire [1023:0] cw;wire valid,sfault,run,flt,st,done;wire [31:0] cycle;
 wire [15:0] rq;wire [223:0] ra;wire [3:0] kind,code;wire [1:0] gs;
 wire f4;wire [7:0] jid,tag;wire mv;wire [13:0] mr;
 ot_s81_su_calendar_store #(.DEPTH(DEPTH),.AW(AW)) mem(
  .clk(clk),.rst_n(rst),.arm(raw_phase?raw_arm:arm),.running(raw_phase?raw_run:run),
  .cycle(raw_phase?raw_cycle:cycle),.boot_we(we),.boot_commit(commit),.boot_addr(addr),
  .boot_lane(lane),.boot_data(data),.calendar_word(cw),.program_valid(valid),.fault(sfault));
 ot_s81_su_calendar_ctl ctl(.clk(clk),.rst_n(rst),.arm(arm),.calendar_valid(valid),
  .calendar_cycle(cycle),.calendar_word(cw),.cycle(cycle),.rq_v(rq),.rq_row(ra),
  .rs_v(16'd0),.wq_v(16'd0),.wq_row(224'd0),.wq_mask(256'd0),.dn_st(st),
  .dn_kind(kind),.dn_gsel(gs),.dn_fp4(f4),.dn_jid(jid),.moe_v(mv),.moe_row(mr),
  .done(done),.done_tag(tag),.up_fu(1'b0),.up_fo(1'b0),.up_alive(1'b1),
  .up_den(1'b1),.up_rdy(!(BAD_READY&&run&&cycle==128)),.up_rjid(8'd77),.fault(flt),.fault_code(code),.running(run));
 function automatic [1023:0] raw_word(input integer n);
  reg [1023:0] v;integer j;
  begin
   for(j=0;j<16;j=j+1)v[64*j+:64]=(64'(n)*64'h9e3779b97f4a7c15)^(64'(j)*64'hd1b54a32d192ed03)^64'hb5ad4eceda1ce2a9;
   raw_word=v;
  end
 endfunction
 function automatic [1023:0] instruction(input integer n);
  reg [1023:0] v;integer j;
  begin
   v=0;v[15:0]=16'h1<<(n%16);
   for(j=0;j<16;j=j+1)v[16+14*j+:14]=14'(n*17+j*31);
   v[752]=(n%64==0);v[756:753]=4'(n);v[758:757]=2'(n>>4);
   v[759]=n[5];v[767:760]=8'(n>>6);v[777]=1;v[778]=1;v[779]=1;v[787:780]=77;
   v[789]=(n%127==0);v[803:790]=14'(n+9000);
   if(n==DEPTH-1)begin v[768]=1;v[776:769]=42;v[788]=1;end
   instruction=v;
  end
 endfunction
 integer i,j,seen=0,raw_seen=0,nd=0,cy=0,last_c=-1;
 reg [1023:0] v,expected;
 always @(posedge clk)cy=cy+1;
 always @(negedge clk)if(!raw_phase && rq)begin
  expected=instruction(seen);
  if(last_c>=0 && cy!=last_c+1)$fatal(1,"calendar bubble");last_c=cy;
  if(rq!==expected[15:0]||ra!==expected[239:16])$fatal(1,"controller request mismatch word=%0d",seen);
  if({st,kind,gs,f4,jid}!=={expected[752],expected[756:753],expected[758:757],expected[759],expected[767:760]})$fatal(1,"controller announcement mismatch");
  if({mv,mr}!=={expected[789],expected[803:790]})$fatal(1,"controller MOE mismatch");
  if(done!==(seen==DEPTH-1)||(done&&tag!=42))$fatal(1,"controller completion moved");
  seen=seen+1;if(done)nd=nd+1;
 end
 task boot(input integer pattern);
  begin
   for(i=0;i<DEPTH;i=i+1)begin
    v=pattern?instruction(i):raw_word(i);
    for(j=0;j<16;j=j+1)begin @(negedge clk);we=1;addr=AW'(i);lane=4'(j);data=v[64*j+:64];end
   end
   @(negedge clk);we=0;commit=1;
   @(negedge clk);commit=0;
  end
 endtask
 initial begin
  repeat(3)@(negedge clk);rst=1;
  boot(0);
  raw_arm=1;@(negedge clk);
  if(cw!==raw_word(0))$fatal(1,"full-width raw mismatch row=0");raw_seen=1;raw_arm=0;raw_run=1;raw_cycle=0;
  for(i=1;i<DEPTH;i=i+1)begin
   @(negedge clk);if(cw!==raw_word(i))$fatal(1,"full-width raw mismatch row=%0d",i);
   raw_seen=raw_seen+1;raw_cycle=i;
  end
  raw_run=0;if(sfault||raw_seen!=DEPTH)$fatal(1,"raw store fault/count");
  // A reset clears validity/control, never supplies SRAM contents.
  rst=0;repeat(3)@(negedge clk);
  if(valid||flt||run||rq)$fatal(1,"reset did not clear control/validity");
  rst=1;boot(1);raw_phase=0;arm=1;
  @(negedge clk);arm=0;
  repeat(DEPTH+4)@(negedge clk);
  if(seen!=DEPTH||nd!=1||sfault||run||cycle!=DEPTH||(BAD_READY?(!flt||code!=8):flt))$fatal(1,"full calendar failure seen=%0d flt=%b code=%0d sfault=%b cycle=%0d",seen,flt,code,sfault,cycle);
  $display("PASS CALENDAR_FULL128 depth4096 width1024 raw4096 instructions4096 macros128 bubbles0 reset1 done1 bad_ready=%0d fault=%0d code=%0d",BAD_READY,flt,code);$finish;
 end
endmodule
