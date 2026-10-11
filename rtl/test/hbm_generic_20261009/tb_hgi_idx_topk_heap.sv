`timescale 1ns/1ps
// hgi-1010/g2: exact + throughput bench of the SRAM-heap IDX.TOPK (rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_heap.sv).
// -DDROPIN: through ot_hgi_idx_topk_registered (the die's wrapper, one score a cycle); else the wide engine with
// -DIW=<n> -DHW=<heaps>.  Mutant defines (OT_TOPK_HEAP_MUT_*) must FAIL.  Reference: heapsort of the unique 64-bit keys
// {monotone(canonical score), ~index} in the bench (the golden's sorted-insertion order: score descending, ties to the
// lowest index, -0 == +0 for ordering, the raw score returned).  Prints a CASE line per command with its cycles.
module tb_hgi_idx_topk_heap;
`ifndef IW
 `define IW 1
`endif
`ifndef HW
 `define HW 2
`endif
 localparam integer IW = `IW;
 reg clk = 0; always #0.4165 clk = ~clk;
 reg rst_n = 0;
 longint cyc = 0; always @(posedge clk) cyc <= cyc + 1;
 reg cv = 0, iv = 0, ordy = 1, vals = 1; reg [5:0] op = 2; reg [24:0] prm; reg [31:0] cn, cm;
 reg [IW*32-1:0] isc; reg [$clog2(IW+1)-1:0] inw;
 wire cr, ir, ov, olast, ovv, done; wire [3:0] err; wire [31:0] oid, osc, orow;
`ifdef DROPIN
 ot_hgi_idx_topk_registered #(.ENABLE(1), .MAX_K(2048)) dut (.clk(clk), .rst_n(rst_n), .cmd_valid(cv), .cmd_ready(cr),
  .cmd_unit(4'd9), .cmd_op(op), .cmd_param(prm), .cmd_n(cn), .cmd_m(cm), .cmd_values(vals), .in_valid(iv), .in_ready(ir),
  .in_score(isc[31:0]), .out_valid(ov), .out_ready(ordy), .out_id(oid), .out_score(osc), .out_row(orow), .out_last(olast),
  .out_values_valid(ovv), .done(done), .error(err));
`else
 ot_hgi_idx_topk_hw #(.ENABLE(1), .MAX_K(2048), .IW(IW), .W(`HW)
`ifdef OT_TOPK_HEAP_MUT_BYP
  , .MUT_BYP(1)
`endif
`ifdef OT_TOPK_HEAP_MUT_CLR
  , .MUT_CLR(1)
`endif
`ifdef OT_TOPK_HEAP_MUT_REV
  , .MUT_REV(1)
`endif
 ) dut (.clk(clk), .rst_n(rst_n), .cmd_valid(cv), .cmd_ready(cr),
  .cmd_unit(4'd9), .cmd_op(op), .cmd_param(prm), .cmd_n(cn), .cmd_m(cm), .cmd_values(vals), .in_valid(iv), .in_ready(ir),
  .in_score(isc), .in_nw(inw), .out_valid(ov), .out_ready(ordy), .out_id(oid), .out_score(osc), .out_row(orow),
  .out_last(olast), .out_values_valid(ovv), .done(done), .error(err));
`endif
 // ---------------------------------------------------------------- reference
 localparam integer NMAX = 65536;
 reg [31:0] sc [0:NMAX-1]; longint ky [0:NMAX-1];
 function automatic longint key64(input [31:0] s, input integer i);
  reg [31:0] c, mo; begin c = (s[30:0] == 0) ? 32'd0 : s; mo = c[31] ? ~c : (c | 32'h80000000);
  key64 = {12'd0, mo, ~i[19:0]}; end
 endfunction
 task automatic sift(input integer a, input integer nn);   // max-heap sift on ky[0..nn-1] (unsigned)
  integer c; longint t; begin
   while (2 * a + 1 < nn) begin
    c = 2 * a + 1; if (c + 1 < nn && $unsigned(ky[c + 1]) > $unsigned(ky[c])) c = c + 1;
    if ($unsigned(ky[c]) > $unsigned(ky[a])) begin t = ky[c]; ky[c] = ky[a]; ky[a] = t; a = c; end else a = nn;
   end
  end
 endtask
 task automatic hsort(input integer nn);                  // ascending; read descending from the top
  integer a; longint t; begin
   for (a = nn / 2 - 1; a >= 0; a = a - 1) sift(a, nn);
   for (a = nn - 1; a > 0; a = a - 1) begin t = ky[0]; ky[0] = ky[a]; ky[a] = t; sift(0, a); end
  end
 endtask
 integer seed = 11;
 initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 11; $display("SEED=%0d", seed); end  // runtime seed (+SEED=<n> overrides): Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
 function automatic [31:0] gen(input integer mode, input integer i, input integer r);
  reg [31:0] x; begin
   case (mode)
    0: begin x = $random(seed); if (x[30:23] == 8'hff && x[22:0] != 0) x[22] = 1'b0; if (x[30:23] == 8'hff && x[22:0] != 0) x = 32'h7f800000; end
    1: x = 32'h3f800000 + i;                             // ascending: every score survives (worst case)
    2: x = 32'h47000000 - i;                             // descending
    3: case ($unsigned($random(seed)) % 7) 0: x = 0; 1: x = 32'h80000000; 2: x = 32'h3f800000; 3: x = 32'hbf800000;
        4: x = 32'h7f800000; 5: x = 32'hff800000; default: x = 32'h40000000; endcase
    default: case (i % 13) 0: x = 32'h80000000; 1: x = 0; 2: x = 32'hff800000; 3: x = 32'h7f800000;
        4: x = 32'hbf800000 + ((i * 31 + r * 17) % 67); default: x = 32'h3f800000 + ((i * 31 + r * 17) % 67); endcase
   endcase
   gen = x;
  end
 endfunction
 // ---------------------------------------------------------------- driver / checker
 integer errors = 0, ncase = 0;
 integer t, r, j, w, got;
 longint c0;
 reg [31:0] eid, esc;
 task automatic run(input integer n, input integer k, input integer rows, input integer mode, input integer nan_at);
  begin
   @(negedge clk); while (!cr) @(negedge clk);
   op = 2; prm = k; cn = n; cm = rows; cv = 1; c0 = cyc; @(negedge clk); cv = 0;
   for (r = 0; r < rows; r = r + 1) begin
    for (j = 0; j < n; j = j + 1) begin sc[j] = gen(mode, j, r); if (j == nan_at) sc[j] = 32'h7fc00001; ky[j] = key64(sc[j], j); end
    hsort(n);
    fork
     begin : feed
      j = 0;
      while (j < n) begin
       if (($random(seed) & 7) == 0) begin iv = 0; @(negedge clk); end
       iv = 1; inw = (n - j < IW) ? n - j : IW;
       for (w = 0; w < IW; w = w + 1) isc[32 * w +: 32] = (j + w < n) ? sc[j + w] : 32'h0;
       while (!ir) @(negedge clk);                       // handshake at the coming edge
       @(negedge clk);
       if (nan_at >= 0 && j + IW > nan_at) j = n; else j = j + IW;
      end
      iv = 0;
     end
     begin : check
      got = 0;
      while (got < k && !(nan_at >= 0)) begin
       @(negedge clk); ordy = ($random(seed) & 3) != 0;
       if (ov && ordy) begin
        eid = ~ky[n - 1 - got][19:0] & 32'h000fffff; esc = sc[eid];
        if (oid !== eid || osc !== esc || orow !== r || olast !== (got == k - 1) || ovv !== vals) begin
         if (errors < 10) $display("ERR case %0d row %0d out %0d: id %0d score %h last %0d | expected id %0d score %h", ncase, r, got, oid, osc, olast, eid, esc);
         errors = errors + 1;
        end
        got = got + 1;
       end
      end
      ordy = 1;
     end
    join
   end
   if (nan_at >= 0) begin
    t = 0; while (!done && t < 1000) begin @(posedge clk); if (ov) begin errors = errors + 1; $display("ERR NaN case emitted"); end t = t + 1; end
    if (err != 4'd3) begin errors = errors + 1; $display("ERR NaN case error %0d", err); end
   end else begin
    t = 0; while (!done && t < 100000) begin @(posedge clk); t = t + 1; end
    if (!done || err != 0) begin errors = errors + 1; $display("ERR case %0d: done %0d error %0d", ncase, done, err); end
   end
   $display("CASE %0d n %0d k %0d rows %0d mode %0d IW %0d heaps %0d cycles %0d (%0.1f a row)", ncase, n, k, rows, mode, IW, `HW,
            cyc - c0, (cyc - c0) * 1.0 / rows);
   ncase = ncase + 1; @(negedge clk);
  end
 endtask
 task automatic bad(input [5:0] o, input integer n, input integer k, input [3:0] e);
  begin
   @(negedge clk); while (!cr) @(negedge clk); op = o; prm = k; cn = n; cm = 1; cv = 1; @(negedge clk); cv = 0; op = 2;
   t = 0; while (!done && t < 100) begin @(posedge clk); t = t + 1; end
   if (err !== e || ov) begin errors = errors + 1; $display("ERR bad command op %0d n %0d k %0d: error %0d expected %0d", o, n, k, err, e); end
   @(negedge clk);
  end
 endtask
 initial begin
  repeat (4) @(negedge clk); rst_n = 1;
  vals = 0; run(17, 1, 2, 4, -1); vals = 1;
  run(17, 2, 2, 4, -1); run(384, 6, 2, 4, -1); run(65, 8, 2, 4, -1); run(5, 5, 3, 0, -1);
  run(1024, 512, 2, 0, -1); run(4096, 2048, 1, 4, -1); run(3000, 2048, 1, 0, -1); run(4096, 2048, 2, 3, -1);
  run(100, 4, 1, 0, 50);                                   // NaN mid-row: fail closed, then a clean command
  run(300, 7, 2, 3, -1);
  bad(6'd63, 17, 1, 4'd1); bad(6'd2, 4, 5, 4'd2);
`ifndef SHORT
  run(6000, 2048, 2, 1, -1); run(6000, 2048, 1, 2, -1);
  run(49152, 2048, 1, 0, -1); run(49152, 2048, 1, 1, -1); run(49152, 2048, 1, 3, -1);
`endif
  if (errors == 0) $display("HGI_TOPK_HEAP PASS (%0d cases)", ncase); else $display("HGI_TOPK_HEAP FAIL errors=%0d", errors);
  $finish;
 end
 initial begin #50000000; $display("HGI_TOPK_HEAP FAIL timeout"); $finish; end
endmodule
