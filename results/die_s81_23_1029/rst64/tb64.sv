`timescale 1ns/1fs
// DIE-S81-23: OWNER 10-29 05:3x boot holds rst_n low >=64 clocks. Actual cells (ot_dp_rsync_s2 + ot_dp_rrelay chain):
// every relay depth 0..64 sees >=64 known-low sink edges, cold and warm. Mutant HOLD=63 must fail (<64).
module tb;
parameter integer HOLD=64;
reg clk=0,rst_n=1;
always #0.4165 clk=~clk;
wire [64:0] r; wire root; assign r[0]=root;
ot_dp_rsync_s2 sync(.clk(clk),.async_rst_n(rst_n),.sync_rst_n(root));
genvar k;
generate for(k=1;k<=64;k=k+1)begin:g ot_dp_rrelay relay(.clk(clk),.d(r[k-1]),.q(r[k])); end endgenerate
integer lowc[0:64]; integer i,minlow,pass;
always @(posedge clk) for(i=0;i<=64;i=i+1) if(r[i]===1'b0) lowc[i]=lowc[i]+1;
task run(input integer warm); begin
 for(i=0;i<=64;i=i+1) lowc[i]=0;
 @(negedge clk); rst_n=0; repeat(HOLD)@(negedge clk); rst_n=1; repeat(140)@(negedge clk);
 minlow=1<<30; for(i=0;i<=64;i=i+1) if(lowc[i]<minlow) minlow=lowc[i];
 $display("%s HOLD=%0d depth0..64 min_sink_known_low=%0d depth0=%0d depth64=%0d", warm?"WARM":"COLD", HOLD, minlow, lowc[0], lowc[64]);
 if(minlow<64) $display("BELOW64"); end endtask
initial begin run(0); run(1); $finish; end
endmodule
