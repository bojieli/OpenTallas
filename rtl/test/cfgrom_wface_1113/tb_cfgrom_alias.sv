`timescale 1ns/1ps
module tb_cfgrom_alias;
  reg clk=0; always #5 clk=~clk;
  reg ce=0; reg [11:0] addr=0;
  wire [71:0] old_i,new_i,old_f,new_f;
  reg [71:0] late_i=0,late_f=0;
  reg [71:0] expected[0:4095],prev=0,want;
  integer mut=0,checks=0,bad=0,idx;
  ot_rom_4096x72_m8 #(.INSTANCE("cfg_fixture")) a(.clk(clk),.ce_in(ce),.addr_in(addr),.rd_out(old_i));
  ot_rom_4096x72_m8_wface_1113 #(.INSTANCE("cfg_fixture")) b(.clk(clk),.ce_in(ce),.addr_in(addr),.rd_out(new_i));
  ot_rom_4096x72_m8 #(.VIAMAP("cfg_fixture.viamap.hex")) c(.clk(clk),.ce_in(ce),.addr_in(addr),.rd_out(old_f));
  ot_rom_4096x72_m8_wface_1113 #(.VIAMAP("cfg_fixture.viamap.hex")) d(.clk(clk),.ce_in(ce),.addr_in(addr),.rd_out(new_f));
  always @(posedge clk) begin late_i<=new_i;late_f<=new_f;end
  task automatic step(input integer aa,input bit en);
    reg[71:0] ni,nf;
    begin
      @(negedge clk); addr=aa[11:0];ce=en;
      want=en?expected[aa]:prev;
      @(posedge clk);#1;
      ni=(mut==2)?late_i:new_i;nf=(mut==2)?late_f:new_f;
      if(mut==1) begin ni=ni^72'h2000000000;nf=nf^72'h2000000000;end
      checks+=4;
      if(old_i!==want||old_f!==want) $fatal(1,"original/oracle mismatch addr%0d",aa);
      if(ni!==want||nf!==want) begin
        bad+=1;
        if(bad<3) $display("ALIAS_MISMATCH mut%0d addr%0d enable%0d expected%018h got%018h",mut,aa,en,want,ni);
      end
      prev=want;
    end
  endtask
  initial begin
    if($value$plusargs("MUT=%d",mut)) begin end
    $readmemh("logical_words.hex",expected);
    for(integer i=0;i<4096;i++) step(i,1);
    for(integer i=0;i<4096;i++) step((i*2053+71)%4096,(i%4)!=1);
    for(integer i=0;i<4096;i++) step((i*2053+19)%4096,0);
    $display("CFGROM_ALIAS mut%0d addresses4096 word_checks%0d bit_checks%0d mismatching_cycles%0d",mut,checks,checks*72,bad);
    if(bad) $fatal(1,"alias mismatch");
    $display("CFGROM_ALIAS_PASS");
    $finish;
  end
endmodule
