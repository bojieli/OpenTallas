`timescale 1ps/1ps
// ot_hgi_vm_core bench (hgi-takeover): 3 clients, random word-masked writes / reads over a 4,096-sector window that
// exercises every bank and same-bank conflicts, random response back-pressure, a reference word array; then single-
// bit (CE) and double-bit (UE) injections.  PASS needs every read exact, ce == number of CE injections read back,
// ue only after a UE injection, no mask fault.
module tb_hgi_vm_core;
 parameter integer MUT = 0;
 localparam integer NC = 3;
 reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
 reg [NC-1:0] req_v = 0, rsp_r = 0; reg [NC*337-1:0] req = 0; wire [NC-1:0] req_r, rsp_v; wire [NC*273-1:0] rsp;
 wire [15:0] ce; wire ue, mask_fault;
 reg inj_v = 0; reg [4:0] inj_bank = 0; reg [2:0] inj_word = 0; reg [38:0] inj_mask = 0;
 ot_hgi_vm_core #(.NC(NC), .MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .req_v(req_v), .req_r(req_r), .req(req), .rsp_v(rsp_v),
  .rsp_r(rsp_r), .rsp(rsp), .ce(ce), .ue(ue), .mask_fault(mask_fault), .inj_v(inj_v), .inj_bank(inj_bank), .inj_word(inj_word),
  .inj_mask(inj_mask));
 reg [31:0] ref_m [0:32767];               // window: sectors 0..4095 (32,768 words)
 integer i, c, n, w, nrd = 0, nwr = 0, cycles = 0, seed = 7;
 reg [NC-1:0] pend, acc_c = 0; reg [14:0] psec [0:NC-1]; reg pwe [0:NC-1]; reg [15:0] ptag [0:NC-1];
 reg [255:0] wd; reg [31:0] bm; reg [255:0] exp_d [0:NC-1];
reg [255:0] last;
 task xact(input we, input [14:0] sec, input [255:0] data);
  begin
   issue(0, we, sec, data, 32'hffffffff, 16'h0a00);
   @(posedge clk); while (!(req_v[0] && req_r[0])) @(posedge clk);
   @(negedge clk); req_v[0] = 0;
   @(posedge clk); while (!rsp_v[0]) @(posedge clk);
   last = rsp[255:0]; @(negedge clk);
  end
 endtask
 task issue(input integer cc, input we, input [14:0] sec, input [255:0] data, input [31:0] mask, input [15:0] tag);
  begin req[cc*337 +: 337] = {we, {12'd0, sec, 5'd0}, data, mask, tag}; req_v[cc] = 1; psec[cc] = sec; pwe[cc] = we; ptag[cc] = tag; end
 endtask
 initial begin
  for (i = 0; i < 32768; i = i + 1) ref_m[i] = 0;
  repeat (4) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
  pend = 0;
  while (nrd + nwr < 6000) begin
   @(posedge clk); cycles = cycles + 1; if (cycles > 200000) $fatal(1, "FATAL: liveness");
   for (c = 0; c < NC; c = c + 1) begin          // handshakes complete at this edge (pre-edge values)
    if (rsp_v[c] && rsp_r[c]) begin
     if (rsp[c*273 + 257 +: 16] !== ptag[c] || rsp[c*273 + 256] !== pwe[c]) $fatal(1, "FATAL: client %0d tag / echo", c);
     if (!pwe[c] && rsp[c*273 +: 256] !== exp_d[c]) $fatal(1, "FATAL: client %0d read sector %0d: %h != %h", c, psec[c], rsp[c*273 +: 256], exp_d[c]);
     pend[c] = 0;
    end
   end
   // reads see the memory before this edge's writes (1R1W: same-edge read of a row being written returns old data)
   for (c = 0; c < NC; c = c + 1) if (req_v[c] && req_r[c] && !pwe[c]) begin
    acc_c[c] = 1; nrd = nrd + 1; for (w = 0; w < 8; w = w + 1) exp_d[c][w*32 +: 32] = ref_m[psec[c]*8 + w];
   end
   for (c = 0; c < NC; c = c + 1) if (req_v[c] && req_r[c] && pwe[c]) begin
    acc_c[c] = 1; nwr = nwr + 1;
    for (w = 0; w < 8; w = w + 1) if (&req[c*337 + 16 + w*4 +: 4]) ref_m[psec[c]*8 + w] = req[c*337 + 48 + w*32 +: 32];
   end
   @(negedge clk);
   for (c = 0; c < NC; c = c + 1) begin
    if (acc_c[c]) begin req_v[c] = 0; pend[c] = 1; acc_c[c] = 0; end
    rsp_r[c] = $random(seed) & 1;
    if (!req_v[c] && !pend[c] && ($random(seed) & 3) != 0) begin
     n = $unsigned($random(seed)) % 4096;
     for (w = 0; w < 8; w = w + 1) begin wd[w*32 +: 32] = $random(seed); bm[w*4 +: 4] = ($random(seed) & 1) ? 4'hf : 4'h0; end
     issue(c, ($random(seed) & 1), n[14:0], wd, bm, 16'(c*4096 + (nrd + nwr) % 4096));
    end
   end
  end
  // drain
  while (pend != 0 || req_v != 0) begin @(negedge clk); for (c = 0; c < NC; c = c + 1) begin rsp_r[c] = 1; if (rsp_v[c]) pend[c] = 0; end end
  if (ce !== 0 || ue || mask_fault) $fatal(1, "FATAL: fault-free phase reported ce=%0d ue=%0d mask=%0d", ce, ue, mask_fault);
  // CE: a single-bit flip on a write of sector 5 word 3 (bank 5), read back corrected
  rsp_r = {NC{1'b1}};
  @(negedge clk); inj_v = 1; inj_bank = 5; inj_word = 3; inj_mask = 39'd1 << 17;
  xact(1, 15'd5, {8{32'h12345678}}); inj_v = 0;
  xact(0, 15'd5, 256'd0);
  if (last[3*32 +: 32] !== 32'h12345678 || ce != 1 || ue) $fatal(1, "FATAL: CE not corrected (data %h ce %0d ue %0d)", last[3*32 +: 32], ce, ue);
  // UE: a double-bit flip, read back -> ue
  @(negedge clk); inj_v = 1; inj_bank = 6; inj_word = 0; inj_mask = (39'd1 << 2) | (39'd1 << 30);
  xact(1, 15'd6, {8{32'h0f0f0f0f}}); inj_v = 0;
  xact(0, 15'd6, 256'd0);
  if (!ue) $fatal(1, "FATAL: UE not reported");
  $display("PASS HGI-VM core clients=%0d reads=%0d writes=%0d cycles=%0d CE corrected UE flagged", NC, nrd, nwr, cycles);
  $finish;
 end
endmodule
