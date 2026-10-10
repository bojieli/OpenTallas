`timescale 1ps/1ps
// IDX unit THROUGHPUT bench (hgi-1010/g): ot_hgi_idx_unit (die record bus) <-> the real ot_hgi_vm_unit (client 0),
// the bench as VM client 1.  Every record's A operand is preloaded through client 1 (untimed); the records (DS-V4.1 1M
// IDX.TOPK route.top6 and IDX.OWNED row_gather.owned, tools/hgi_unit_tput/idx_vectors.py) are then dispatched BACK TO
// BACK: a record is on the bus the cycle the unit reports ready.  Prints TPUT k op <op> issue <c> ret <c> cost_milli <p>,
// then reads every expected output word back through client 1 and compares it (the simulator's / G24 golden).
// MUT 1: the ascending-id sort compares scores (unit MUT 1) -> must FAIL.  PREF 1 / MUT_PREF 1: see ot_hgi_idx_unit.
module tb_hgi_idx_tput;
 parameter integer MUT = 0, PREF = 0, MUT_PREF = 0;   // PREF: the opt-in streaming reader (MUT_PREF: early pop, must FAIL)
 reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
 reg [1818:0] rec = 0; wire [2:0] ret; wire [337:0] vmq; wire [273:0] vmr;
 reg [337:0] bq = 0; wire [273:0] br; wire [18:0] status;
 ot_hgi_idx_unit #(.MUT(MUT), .PREF(PREF), .MUT_PREF(MUT_PREF)) dut (.clk(clk), .rst_n(rst_n), .rec(rec), .ret(ret), .vmq(vmq), .vmr(vmr),
  .sel_fs(), .sel_qb(), .sel_qbr(1'b0), .sel_kin(), .sel_to(612'd0), .sel_toc(), .sel_co(72'd0), .sel_coc(), .sel_ev(2'b00));
 ot_hgi_vm_unit #(.NC(2)) vm (.clk(clk), .rst_n(rst_n), .cq({bq, vmq}), .cr({br, vmr}), .status(status));
 integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
 task vm_word(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
  begin @(negedge clk); bq = {1'b1, we, {12'd0, word[17:3], 5'd0}, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0003};
   @(negedge clk); bq[337] = 0; while (!br[273]) @(negedge clk); qd = br[32 * word[2:0] +: 32]; end
 endtask
 function [255:0] desc(input [2:0] fmt, input [39:0] base, input [19:0] nn);
  begin desc = 256'd0; desc[1:0] = 2'd1; desc[4:2] = fmt; desc[47:8] = base; desc[67:48] = nn; desc[87:68] = 20'd1; end
 endfunction
 integer fd, nrec, k, j, op [0:15], kk [0:15], die [0:15], cost [0:15], a [0:15], o [0:15], r [0:15], d [0:15];
 integer na [0:15], no [0:15], nr [0:15], nd [0:15], ne [0:15], issue, t0, t1, bad = 0, bk, words = 0;
 reg [127:0] hdr [0:15]; reg [31:0] aw [0:8191]; reg [63:0] ew [0:8191]; reg [31:0] qd; string dir;
 reg [255:0] dA, dO, dR, dD;
 initial begin
  if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
  fd = $fopen({dir, "/recs.txt"}, "r"); void'($fscanf(fd, "%d", nrec));
  for (k = 0; k < nrec; k = k + 1)
   void'($fscanf(fd, "%d %d %d %d %d %d %d %d %d %d %d %d %h %d", op[k], kk[k], die[k], cost[k], a[k], o[k], r[k], d[k],
                 na[k], no[k], nr[k], nd[k], hdr[k], ne[k]));
  repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
  for (k = 0; k < nrec; k = k + 1) begin
   $readmemh($sformatf("%s/a_%0d.mem", dir, k), aw, 0, na[k] - 1);
   for (j = 0; j < na[k]; j = j + 1) vm_word(1'b1, a[k] + j, aw[j], qd);
  end
  repeat (8) @(negedge clk); t0 = cyc;
  for (k = 0; k < nrec; k = k + 1) begin
   while (!ret[0]) @(negedge clk);
   dA = desc(op[k] == 2 ? 3'd0 : 3'd5, 40'(a[k]), 20'(na[k])); dO = desc(3'd5, 40'(o[k]), 20'(no[k]));
   dR = op[k] == 3 ? desc(3'd5, 40'(r[k]), 20'(nr[k])) : 256'd0; dD = op[k] == 3 ? desc(3'd5, 40'(d[k]), 20'(nd[k])) : 256'd0;
   rec = {8'(die[k]), 20'd0, 21'(nr[k]), 21'(no[k]), 21'(nd[k]), 21'd0, 21'd0, 21'(na[k]), dR, dO, dD, 256'd0, 256'd0, dA, hdr[k], 1'b1};
   issue = cyc - t0; @(negedge clk); rec[0] = 0;
   while (!ret[1] && !ret[2]) begin @(negedge clk); if (cyc - t0 > 5000000) $fatal(1, "FATAL: liveness"); end
   t1 = cyc - t0;
   if (ret[2]) begin $display("FAULT record %0d", k); bad = bad + 1; end
   $display("TPUT %0d op %0d issue %0d ret %0d cost_milli %0d", k, op[k], issue, t1, cost[k]);
   @(negedge clk);
  end
  for (k = 0; k < nrec; k = k + 1) begin
   bk = bad; $readmemh($sformatf("%s/e_%0d.mem", dir, k), ew, 0, ne[k] - 1);
   for (j = 0; j < ne[k]; j = j + 1) begin
    vm_word(1'b0, ew[j][63:32], 0, qd);
    if (qd !== ew[j][31:0]) begin if (bad < 12) $display("MISMATCH rec %0d word %0d @%0d: %h != %h", k, j, ew[j][63:32], qd, ew[j][31:0]); bad = bad + 1; end
    words = words + 1;
   end
   $display("EXACT %0d mismatch %0d", k, bad - bk);
  end
  if (status[18:16] != 0) $display("VM status %b", status[18:16]);
  if (bad) $display("HGI_IDX_TPUT FAIL %0d", bad); else $display("PASS HGI_IDX_TPUT records=%0d words=%0d cycles=%0d", nrec, words, t1);
  $finish;
 end
endmodule
