// Behavioural gate of the die's static x2-pair column entry dsfd_cfifo (S-ELEM-PQ/COLL 2026-10-16, S81F-02).
// Reference = the S-BIND packing spec, not the RTL: the column record R = {x2 536 | cc 15 | x1 266 | x0 283 | v}
// travels as xd = {R[564:0], marker} on xf and xd2 = {R[1100:565], v, marker2} on xf2 (equal station count, small
// forwarded-clock skew).  Outputs: xa = x0 (bit 282 qualified by v), xb = x1, cc = cc (bits 1:0 qualified by v),
// x2 = x2 (bits 0 and 4 qualified by v), all on cr.  Checks, on EVERY cr edge after the first record: both lanes
// deliver the SAME source word (x0/x1/cc lane and x2 lane aligned), words advance by exactly one per edge (no skip,
// hold or duplicate), the delivery time is the fixed epoch (constant edge offset), the status word rd carries
// {st | fault, st, ri} one edge late with fault 0, rs = synchronised reset.  PHA/PHB = xf/xf2 phase vs cr (ns).
`timescale 1ns/1ps
module tb_dsfd_cfifo_x2pair;
 parameter integer PHA=2, PHB=2, TRUNK=9, NW=400, WARM=0;
 reg cr=0, xf=0, xf2=0, rst=0;
 initial forever #5 cr=~cr;
 initial begin #(PHA); forever #5 xf=~xf; end
 initial begin #(PHB); forever #5 xf2=~xf2; end
 reg [1100:0] R=0; reg [65:0] ri=0; reg [1:0] st=0;
 wire [282:0] xa; wire [265:0] xb; wire [14:0] cc; wire [535:0] x2; wire [69:0] rd; wire co, rf, rs;
 reg [565:0] xd = 0; reg [537:0] xd2 = 0; reg go = 0;
 dsfd_cfifo dut(.cc(cc), .cr(cr), .rd(rd), .ri(ri), .rs(rs), .rst(rst), .st(st),
                .xa(xa), .xb(xb), .xd(xd), .xf(xf), .x2(x2), .xd2(xd2), .xf2(xf2));
 reg [1100:0] gold [0:4095]; integer n=0, n2=0, k; reg [1100:0] w2;
 function automatic [1100:0] word(input integer s);
  integer b; begin for (b=0;b<1101;b=b+1) word[b] = ((s*1103515245+12345+b*2654435761) >> (b%29)) ^ (s>>(b%5)) ^ (b%3==0);
   word[0] = ((s*7)%11) > 3;          // valid: ~64% of source words, bubbles in between
  end
 endfunction
 // each lane launches its half of source word s on its own forwarded clock, 1 ns after the edge (source-synchronous);
 // the lane starts (marker 1) at the first edge after go, so equal-skew lanes start on the same source edge
 always @(posedge xf) begin #1; if (go) begin R = word(n); gold[n] = R; xd = {R[564:0], 1'b1}; n = n + 1; end end
 always @(posedge xf2) begin #1; if (go) begin w2 = word(n2); xd2 = {w2[1100:565], w2[0], 1'b1}; n2 = n2 + 1; end end
 // reference outputs from the spec packing
 function automatic [1100:0] expect_out(input [1100:0] w);
  reg v; begin v = w[0];
   expect_out = 0;
   expect_out[282:0]    = {w[283] & v, w[282:1]};
   expect_out[548:283]  = w[549:284];
   expect_out[563:549]  = {w[564:552], w[551] & v, w[550] & v};
   expect_out[1099:564] = {w[1100:570], w[569] & v, w[568:566], w[565] & v};
  end
 endfunction
 wire [1099:0] got = {x2, cc, xb, xa}; reg [1100:0] eo;
 integer first=-1, cur=0, seen=0, t0=0, bad=0; reg checking=1; time go_time; integer cold_seen=0; reg [65:0] ri_d=0; reg [1:0] st_d=0;
 always @(posedge cr) begin
  #2;
  if (checking) begin
  if (rs !== 1'b1 && first >= 0) begin $display("CFIFO_X2 FAIL rs dropped"); bad=bad+1; end
  if (first < 0 && got !== 0 && (^got) !== 1'bx) begin
   for (k=0;k<n;k=k+1) begin eo = expect_out(gold[k]); if (got === eo[1099:0]) first = k; end
   if (first < 0) begin $display("CFIFO_X2 FAIL unrecognised first record t=%0t", $time); $finish; end
   cur = first; t0 = $time - 10*first;
   // The reserved source launch is one ns after the forwarded edge. With
   // go on cr+4, the compiled sampling calendar discards source word0 during
   // warm-up and delivers word1 at cr+9/10 depending on the declared phase.
   // Check that absolute calendar; learning any constant latency is insufficient.
   if (first != 1 || t0 != go_time + ((PHA <= 2) ? 88 : 78)) begin
    $display("CFIFO_X2 FAIL fixed first epoch first=%0d t0=%0t go=%0t",first,t0,go_time); bad=bad+1;
   end
  end
  if (first >= 0) begin
   eo = expect_out(gold[cur]);
   if (got !== eo[1099:0]) begin
    if (bad < 5) $display("CFIFO_X2 FAIL word %0d mismatch xa%0d xb%0d cc%0d x2%0d t=%0t", cur,
      xa !== eo[282:0], xb !== eo[548:283], cc !== eo[563:549], x2 !== eo[1099:564], $time);
    bad = bad + 1;
   end
   if ($time - 10*cur != t0) begin $display("CFIFO_X2 FAIL epoch moved word %0d", cur); bad = bad + 1; end
   if (rd[69:2] !== {st_d[1], st_d[0], ri_d} || rd[1] !== ri_d[0] || rd[0] !== 1'b1) begin
    if (bad < 5) $display("CFIFO_X2 FAIL status rd=%h st_d=%b fault/ri", rd, st_d); bad = bad + 1; end
   cur = cur + 1; seen = seen + 1;
  end
 end
 end
 // status path: ri/st change 1 ns after cr; rr captures them on the next cr edge (rd = rr), st through sti (2 edges)
 reg [1:0] st_q=0, st_qq=0; always @(posedge cr) begin st_q <= st; st_qq <= st_q; end
 always @(posedge cr) begin #1; ri_d = ri; st_d = st_qq; ri = {$random,$random,$random}; st = $random; end
 initial begin
  #23; rst = 1;
  repeat (TRUNK) @(posedge cr); #4; go = 1; go_time=$time;
  repeat (NW) @(posedge cr);
  if (WARM) begin
   cold_seen=seen;
   if (seen < NW-30) begin $display("CFIFO_X2 FAIL cold count %0d",seen); bad=bad+1; end
   #3; checking=0; go=0; xd=0; xd2=0; rst=0;
   repeat (TRUNK) @(posedge cr); #3; n=0; n2=0; first=-1; cur=0; seen=0; t0=0;
   #23; rst=1; repeat (TRUNK) @(posedge cr); #4; go=1; go_time=$time; checking=1;
   repeat (NW) @(posedge cr);
  end
  if (seen < NW-30) begin $display("CFIFO_X2 FAIL only %0d words", seen); bad = bad + 1; end
  if (rd[69] !== st_d[1]) bad = bad + 1;
  if (bad == 0) $display("CFIFO_X2 PASS pha=%0d phb=%0d words=%0d first=%0d offset=%0t warm=%0d cold_words=%0d", PHA, PHB, seen, first, t0,WARM,cold_seen);
  else $display("CFIFO_X2 FAIL bad=%0d words=%0d", bad, seen);
  $finish;
 end
endmodule
