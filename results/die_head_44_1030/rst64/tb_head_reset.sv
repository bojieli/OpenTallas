`timescale 1ns/1fs
// DIE-HEAD-44 2026-10-30: HEAD die reset contract bench (S81 DIE-S81-23 tb64 form, OWNER 10-29 boot rst_n low >= 64 clk).
// HEAD reset = OWNER DECISION 13 wavefront: ONE root ot_dp_rsync_s2 on the die rst_n (sp5 = ot_s81hd_spn_end_strip
// u_rst_root), then every partition re-drives a registered reset: pin register ot_dp_rrelay on arst_n + ot_dp_rrelay
// relays to its taps / rst_o (latest release 107 clocks), START-gated consumer taps ot_dp_rgate (q <= d & run).
// Cells = byte copy of the HEAD l43 / HOST-kit ot_dp_cells.sv (sha256 7926db02...).  Every relay depth 0..DEPTH and an
// rgate tap at every depth (run = the START wavefront released EARLY or LATE) must see >= 64 known-low sink edges,
// cold (X power-up) and warm (reset re-armed after normal operation).
// MUT 0 = contract; MUT 1 = an rgate whose run term ignores reset (q <= run) must FAIL; HOLD < 64 must FAIL (BELOW64).
module tb;
parameter integer HOLD=64;
parameter integer MUT=0;
parameter integer DEPTH=128;
reg clk=0, rst_n=1, start_n=0;
always #0.4165 clk=~clk;
wire root, run_root;
wire [DEPTH:0] r, s, g;
ot_dp_rsync_s2 u_rst_root (.clk(clk), .async_rst_n(rst_n),   .sync_rst_n(root));
ot_dp_rsync_s2 u_run_root (.clk(clk), .async_rst_n(start_n), .sync_rst_n(run_root));
assign r[0]=root; assign s[0]=run_root;
genvar k;
generate for(k=1;k<=DEPTH;k=k+1) begin:g_rl
  ot_dp_rrelay u_rrl (.clk(clk), .d(r[k-1]), .q(r[k]));
  ot_dp_rrelay u_srl (.clk(clk), .d(s[k-1]), .q(s[k]));
end endgenerate
generate for(k=0;k<=DEPTH;k=k+1) begin:g_gt
  if (MUT==1) begin:m
    reg q; always @(posedge clk) q <= s[k];        // MUTANT: run-only gate, reset term dropped
    assign g[k]=q;
  end else begin:c
    ot_dp_rgate u_g (.clk(clk), .d(r[k]), .run(s[k]), .q(g[k]));
  end
end endgenerate
integer lowr[0:DEPTH], lowg[0:DEPTH]; integer i, minr, ming, fails;
reg count;
always @(posedge clk) if (count) for(i=0;i<=DEPTH;i=i+1) begin
  if(r[i]===1'b0) lowr[i]=lowr[i]+1;
  if(g[i]===1'b0) lowg[i]=lowg[i]+1;
end
task run(input integer warm, input integer start_late); begin
  for(i=0;i<=DEPTH;i=i+1) begin lowr[i]=0; lowg[i]=0; end
  count=1;
  @(negedge clk); rst_n=0; if(!start_late) start_n=1; else start_n=0;
  repeat(HOLD) @(negedge clk); rst_n=1;
  if(start_late) begin repeat(37) @(negedge clk); start_n=1; end
  repeat(DEPTH+80) @(negedge clk);
  count=0;
  minr=1<<30; ming=1<<30;
  for(i=0;i<=DEPTH;i=i+1) begin if(lowr[i]<minr) minr=lowr[i]; if(lowg[i]<ming) ming=lowg[i]; end
  $display("%s START_LATE=%0d HOLD=%0d MUT=%0d depth0..%0d min_relay_known_low=%0d min_rgate_known_low=%0d relay_d0=%0d relay_d%0d=%0d",
           warm?"WARM":"COLD", start_late, HOLD, MUT, DEPTH, minr, ming, lowr[0], DEPTH, lowr[DEPTH]);
  if(minr<64 || ming<64) begin $display("BELOW64"); fails=fails+1; end
end endtask
initial begin
  fails=0; count=0;
  run(0,0); run(1,0); run(1,1);
  if(fails==0) $display("HEADRST_PASS HOLD=%0d MUT=%0d", HOLD, MUT); else $display("HEADRST_FAIL HOLD=%0d MUT=%0d fails=%0d", HOLD, MUT, fails);
  $finish;
end
endmodule
