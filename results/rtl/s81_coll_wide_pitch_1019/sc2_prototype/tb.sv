`timescale 1ns/1ps
module tb;
  reg clk=0, r_ce_in=0, w_ce_in=0;
  reg [8:0] r_addr_in=0, w_addr_in=0;
  reg [127:0] wd_in=0, w_mask_in=0;
  wire [127:0] rd_out;
  reg [1:0] rr_en=0, cr_en=0;
  reg [13:0] rr_addr=0, cr_sel=0;
  reg [127:0] gold[0:511];
  reg [127:0] expected, held, pat, mask;
  integer i, mode, checks=0;
  ot_sram_1r1w_512x128_m4_r2c2_p192_sc2 dut(.*);
  task tick;
    begin #2; clk=1; #2; clk=0; #1; end
  endtask
  task check(input [127:0] value, input integer code);
    begin
      checks++;
      if(rd_out !== value) $fatal(1,"SC2_FUNCTION_MISMATCH code=%0d got=%h expected=%h",code,rd_out,value);
    end
  endtask
  initial begin
    // No reliance on power-up zeros: initialize all addressed words explicitly.
    for(mode=0;mode<2;mode++) begin
      rr_en=mode ? 2'b11:0; rr_addr={7'd111,7'd7};
      cr_en=mode ? 2'b11:0; cr_sel={7'd127,7'd0};
      r_ce_in=0; w_ce_in=1; w_mask_in='1;
      for(i=0;i<512;i++) begin
        w_addr_in=i; wd_in={32'h6b42c193,32'hdecaf00d,32'h12345678,32'h98abc531}^{96'b0,i}; gold[i]=wd_in; tick();
      end
      w_ce_in=0; r_ce_in=1;
      for(i=0;i<512;i++) begin r_addr_in=i; tick(); check(gold[i],10+mode); end
      // Every mux lane, masks including repaired IOs, and OLD same-edge collision.
      for(i=0;i<512;i++) begin
        r_ce_in=1; w_ce_in=1; r_addr_in=i; w_addr_in=i;
        wd_in=~gold[i]; w_mask_in=128'h5555aaaa5555aaaa5555aaaa5555aaaa;
        expected=gold[i]; tick(); check(expected,20+mode);
        gold[i]=(expected & ~w_mask_in)|(wd_in&w_mask_in);
        w_ce_in=0; tick(); check(gold[i],30+mode);
        held=rd_out; r_ce_in=0; r_addr_in=(i+1)%512; tick(); check(held,40+mode);
      end
    end
    $display("SC2_FUNCTION_PASS checks=%0d all_words=512 repair_modes=2 OLD=1 masked=1 disabled_hold=1",checks);
    $finish;
  end
endmodule
