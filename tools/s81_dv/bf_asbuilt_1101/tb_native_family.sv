`timescale 1ns/1ps
module tb_native_family;
  reg clk=0;
  initial forever begin #0.416 clk=1; #0.417 clk=0; end
  reg rst=0,cv=0,go=0,family=0;
  reg [74:0] action=0;
  wire [609:0] broadcast;
  wire [68:0] bf_valid;
  wire fault;
  integer samples=0;
  ot_s81sl_xs4_ctl dut(.clk(clk),.rc({4{rst}}),.rh({32{rst}}),.rb({3{rst}}),.rx({24{rst}}),
    .calendar_v(cv),.calendar_action(action),.go(go),.i_ph(10'd106),.i_np(3'd0),
    .rom_gobf(family),.rom_sq(48'd0),.hq_o(),.qc_o(),.hb_o(),.hbk_o(),.bc_o(),
    .bc_hr_o(broadcast),.bv_o(bf_valid),.fault(fault));
  task launch(input bit fam,input reg [1:0] tag);
    begin
      @(negedge clk);cv=1;family=fam;action=0;action[1:0]=tag;go=1;
      @(negedge clk);go=0;action=0;
      repeat(12) @(negedge clk);
      action[62]=1;action[64:63]=tag;
      @(negedge clk);action=0;
      repeat(4) @(negedge clk);
      action[65]=1;action[67:66]=tag;
      @(negedge clk);action=0;
      repeat(12) @(negedge clk);
      repeat(32) begin
        @(negedge clk);
        if(fault || broadcast[595] || broadcast[594]!==fam || bf_valid!=={69{fam}})
          $fatal(1,"NATIVE_FAMILY_FAIL tag%0d family%0d actual%0b valid%h fault%0b",tag,fam,broadcast[594],bf_valid,fault);
        samples=samples+1;
      end
    end
  endtask
  initial begin
    repeat(5) @(negedge clk);rst=1;
    repeat(8) @(negedge clk);
    launch(1,0);launch(0,1);launch(1,2);
    $display("NATIVE_FAMILY_PASS samples=%0d clock_ps=833",samples);$finish;
  end
endmodule
