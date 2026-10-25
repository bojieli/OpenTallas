`timescale 1ns/1ps
module tb_tkm_buffer_reset;
 parameter integer MUT=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,w_v=0,r_v=0;reg[9:0]w_addr=0,r_addr=0;reg[343:0]w_data=0;
 wire v,lv;wire[343:0]d,ld;
 ot_hgi_coll_tkm_buffer #(.DW(344),.DELIVERED_RESET(1),.MUT(MUT)) dut(.*,.rd_v(v),.rd_data(d));
 ot_hgi_coll_tkm_buffer #(.DW(344)) legacy(.*,.rd_v(lv),.rd_data(ld));
 reg[2:0] reset_model=0;
 integer edges=0,reads=0;reg compare=0;reg[343:0]expected;
 task automatic edge_step;
  begin
   @(posedge clk);reset_model={reset_model[1:0],rst_n};#0.01;edges++;
   if(edges>=4 && dut.rr[0]!==reset_model[2])$fatal(1,"RESET_DEPTH edge=%0d actual=%b expected=%b",edges,dut.rr[0],reset_model[2]);
   if(compare)begin
    if(v!==lv)$fatal(1,"VALID_EDGE edge=%0d",edges);
    if(v)begin
     reads++;
     if(d!==ld || d!==expected)$fatal(1,"SRAM_DATA edge=%0d",edges);
    end
   end
   @(negedge clk);
  end
 endtask
 task automatic idle(input integer n);repeat(n)edge_step();endtask
 task automatic transaction(input integer addr,input reg[343:0]payload);
  begin
   expected=payload;w_addr=addr;w_data=payload;w_v=1;edge_step();w_v=0;idle(4);
   r_addr=addr;r_v=1;edge_step();r_v=0;idle(7);
  end
 endtask
 initial begin
  // Cold delivered reset and three-edge release. Both actual SRAM models used.
  idle(6);rst_n=1;idle(6);compare=1;
  transaction(13,344'h123456789abcdef123456789abcdef);
  transaction(511,~344'h123456789abcdef123456789abcdef);
  // Warm reset while a read is pending. Public transactions are invalid until
  // the local reset cohort drains, then old SRAM content must remain intact.
  r_addr=13;r_v=1;edge_step();r_v=0;compare=0;rst_n=0;idle(7);
  rst_n=1;idle(6);compare=1;expected=344'h123456789abcdef123456789abcdef;
  r_addr=13;r_v=1;edge_step();r_v=0;idle(7);
  transaction(1023,344'hfedcba9876543210fedcba9876543210);
  if(reads!=4)$fatal(1,"READ_COUNT %0d",reads);
  $display("TKM_BUFFER_DELIVERED_RESET PASS edges=%0d reads=%0d release_depth=3 data_cycles_delta=0 cold_warm=2",edges,reads);$finish;
 end
endmodule
