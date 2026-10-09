`timescale 1ps/1ps
// Connected HGI quant + VM bench (hgi-takeover): ot_hgi_quant_unit (normative record bus) <-> ot_hgi_vm_unit
// (ECC VM, client 0) with the bench as VM client 1.  For each CF-QDQ mode, the bench loads the released vector inputs
// into VM through client 1, issues ONE record per mode (A = all beats as m rows of 32 FP32 words, O = m rows of 32 FP32
// words {bf16, 16'b0}), waits for the record's done, reads O back through client 1 and compares every word with the
// released golden outputs.  MUT 1: the bench record header drops the A operand bit -> the unit must fault, no done.
module tb_hgi_quant_vm_connected;
 parameter integer MUT = 0;
 reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
 reg [682:0] rec = 0; wire [2:0] ret; wire [337:0] vmq; wire [273:0] vmr0;
 reg [337:0] bq = 0; wire [273:0] br; wire [18:0] status;
 ot_hgi_quant_unit dut (.clk(clk), .rst_n(rst_n), .rec(rec), .ret(ret), .vmq(vmq), .vmr(vmr0));
 ot_hgi_vm_unit #(.NC(2)) vm (.clk(clk), .rst_n(rst_n), .cq({bq, vmq}), .cr({br, vmr0}), .status(status));
 reg [1023:0] gin [0:127]; reg [511:0] gout [0:127];
 string vectors, tag, fin, fout; integer nb, b, k, s, m, mode, cycles = 0, words = 0;
 reg [255:0] sd;
 task vm_write(input [14:0] sec, input [255:0] d);
  begin @(negedge clk); bq = {1'b1, 1'b1, {12'd0, sec, 5'd0}, d, 32'hffffffff, 16'h0001}; @(negedge clk); bq[337] = 0;
   while (!br[273]) @(negedge clk); end
 endtask
 task vm_read(input [14:0] sec);
  begin @(negedge clk); bq = {1'b1, 1'b0, {12'd0, sec, 5'd0}, 256'd0, 32'd0, 16'h0002}; @(negedge clk); bq[337] = 0;
   while (!br[273]) @(negedge clk); sd = br[255:0]; end
 endtask
 function [255:0] desc(input [2:0] fmt, input [39:0] base, input [19:0] n, input [19:0] mm, input [31:0] stride);
  begin desc = 256'd0; desc[1:0] = 2'd1; desc[4:2] = fmt; desc[47:8] = base; desc[67:48] = n; desc[87:68] = mm; desc[119:88] = stride; end
 endfunction
 reg [127:0] h; reg [255:0] da, dd;
 initial begin
  if (!$value$plusargs("VECTORS=%s", vectors)) vectors = "results/hgi_generic/cf_qdq_891b4b555";
  repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
  for (mode = 4; mode <= 6; mode = mode + 1) begin
   nb = (mode == 6) ? 86 : 49;
   if (mode == 4) tag = "fp8_e8m0"; else if (mode == 5) tag = "fp4_e8m0"; else tag = "fp4_e4m3";
   fin = {vectors, "/", tag, ".in.hex"}; fout = {vectors, "/", tag, ".out.hex"};
   $readmemh(fin, gin, 0, nb - 1);
   $readmemh(fout, gout, 0, nb - 1);
   // A at word 0: beat b = words 32b .. 32b+31 = sectors 4b .. 4b+3
   for (b = 0; b < nb; b = b + 1) for (s = 0; s < 4; s = s + 1) vm_write(15'(4*b + s), gin[b][s*256 +: 256]);
   // O at word 65,536
   h = 128'd0; h[127:124] = 4'd4; h[123:118] = 6'(mode); h[99:93] = (MUT == 1) ? 7'b0010000 : 7'b0010001;
   if (mode == 6) h[71:64] = 8'd16;
   da = desc(3'd0, 40'd0, 20'd32, 20'(nb), 32'd32); dd = desc(3'd0, 40'd65536, 20'd32, 20'(nb), 32'd32);
   @(negedge clk); rec = {21'd32, 21'd32, dd, da, h, 1'b1}; @(negedge clk); rec[0] = 0;
   cycles = 0;
   while (!ret[1] && !ret[2]) begin @(negedge clk); cycles = cycles + 1; if (cycles > 2000000) $fatal(1, "FATAL: liveness"); end
   if (ret[2]) begin
    if (MUT == 1) begin $display("FATAL: mutant record faulted (expected)"); $fatal(1, "FATAL: record fault"); end
    $fatal(1, "FATAL: record fault mode %0d", mode);
   end
   for (b = 0; b < nb; b = b + 1) for (s = 0; s < 4; s = s + 1) begin
    vm_read(15'(8192 + 4*b + s));
    for (k = 0; k < 8; k = k + 1) begin
     if (sd[k*32 +: 32] !== {gout[b][(8*s + k)*16 +: 16], 16'h0000})
      $fatal(1, "FATAL: mode %0d beat %0d lane %0d: %h != %h", mode, b, 8*s + k, sd[k*32 +: 32], {gout[b][(8*s + k)*16 +: 16], 16'h0000});
     words = words + 1;
    end
   end
   $display("mode %0d: %0d beats in one record, %0d cycles to done", mode, nb, cycles);
  end
  if (status[18:16] != 0) $fatal(1, "FATAL: VM status %b", status[18:16]);
  $display("PASS HGI-QUANT-VM connected modes=3 words=%0d (record bus -> transport -> ECC VM -> readback)", words);
  $finish;
 end
endmodule
