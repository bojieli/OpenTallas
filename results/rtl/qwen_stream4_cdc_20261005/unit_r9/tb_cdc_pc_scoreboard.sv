`timescale 1ns/1ps
module tb;
  parameter RS = 1;
  reg clk=0, hclk=0, rst=0;
  always #0.4167 clk=~clk;
  always #0.512 hclk=~hclk;
  wire lv; wire [16:0] ls; wire [7:0] lr; wire [255:0] ld; wire [2:0] cr; wire hf;
  reg pop=0, hlv=0; reg [16:0] hs=0; reg [7:0] hr=0; reg [255:0] hd=0;
  ot_qwen_stream4_cdc_pc #(.RSEL(RS),.RNG(10)) b(.clk(clk),.c_arst_n(rst),.l_v(lv),.l_sec(ls),.l_row(lr),.l_data(ld),.l_pop(pop),
    .w_v(1'b0),.w_sec(24'd0),.w_data(256'd0),.w_tag(9'd0),.hclk(hclk),.h_arst_n(rst),.h_lv(hlv),.h_lsec(hs),.h_lrow(hr),.h_ldata(hd),
    .h_cred(cr),.h_hand(1'b0),.h_wcon(1'b0),.h_av(1'b0),.h_atag(9'd0),.h_fault(hf));
  reg [280:0] q [0:1<<20]; integer wp=0, rp=0, cred=64, mism=0, nv=0, held=0;
  reg [280:0] prev; reg prevhold=0;
  always @(posedge hclk) if (rst) begin
    cred = cred + cr;
    if (hlv) begin q[wp] = {hs,hr,hd}; wp = wp + 1; cred = cred - 1; end
    if ($time > 100 && cred > 0 && ($random & 3)) begin hlv <= 1; hs <= $random; hr <= $random; hd <= {8{$random}}; end else hlv <= 0;
  end
  always @(posedge clk) if (rst) begin
    if (prevhold && {ls,lr,ld} !== prev) held = held + 1;
    if (lv && pop) begin if ({ls,lr,ld} !== q[rp]) mism = mism + 1; rp = rp + 1; nv = nv + 1; end
    prevhold = lv && !pop; prev = {ls,lr,ld};
    pop <= ($random & 1);
  end
  initial begin #20 rst=1; #40000; $display("RSEL=%0d popped=%0d mism=%0d held_changed=%0d fault=%0d", RS, nv, mism, held, hf); $finish; end
endmodule
