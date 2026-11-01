`timescale 1ns/1fs
// DIE-QC-58 (COORD 10-31 default, 12.28b): QC boot holds the die rst_n low >= 64 clocks with the clock running (same
// form as S81/HBM/KV).  QC reset distribution = tools/die_plan/gen_rtl.py OWNER DECISION 13 wavefront (die_plan.json
// reset: sync_stages 2, release wavefront, start broadcast): root ot_dp_rsync_s2 -> pin register + ot_dp_rrelay /
// ot_dp_rrelay_drive relay stages -> core rst_n pins, START-gated consumer taps ot_dp_rgate.  Every relay depth 0..64
// and every rgate tap must see >= 64 known-low edges, cold (X power-up) and warm.  Mutant HOLD=61 must fail (<64).
module tb;
parameter integer HOLD=64;
reg clk=0,rst_n=1,run=1;
always #0.4165 clk=~clk;
wire [64:0] r; wire [64:0] g;
ot_dp_rsync_s2 root(.clk(clk),.async_rst_n(rst_n),.sync_rst_n(r[0]));
genvar k;
generate for(k=1;k<=64;k=k+1)begin:c
  if(k%2) begin:d ot_dp_rrelay_drive relay(.clk(clk),.d(r[k-1]),.q(r[k])); end
  else begin:p ot_dp_rrelay relay(.clk(clk),.d(r[k-1]),.q(r[k])); end
end
for(k=0;k<=64;k=k+1)begin:t ot_dp_rgate tap(.clk(clk),.d(r[k]),.run(run),.q(g[k])); end endgenerate
integer lowr[0:64]; integer lowg[0:64]; integer i,minr,ming;
always @(posedge clk) for(i=0;i<=64;i=i+1) begin if(r[i]===1'b0) lowr[i]=lowr[i]+1; if(g[i]===1'b0) lowg[i]=lowg[i]+1; end
task go(input integer warm); begin
 for(i=0;i<=64;i=i+1) begin lowr[i]=0; lowg[i]=0; end
 @(negedge clk); rst_n=0; repeat(HOLD)@(negedge clk); rst_n=1; repeat(140)@(negedge clk);
 minr=1<<30; ming=1<<30;
 for(i=0;i<=64;i=i+1) begin if(lowr[i]<minr) minr=lowr[i]; if(lowg[i]<ming) ming=lowg[i]; end
 $display("%s HOLD=%0d relay depth0..64 min_sink_known_low=%0d depth0=%0d depth64=%0d rgate_min=%0d",
          warm?"WARM":"COLD", HOLD, minr, lowr[0], lowr[64], ming);
 if(minr<64 || ming<64) $display("BELOW64"); end endtask
initial begin go(0); go(1); $finish; end
endmodule
