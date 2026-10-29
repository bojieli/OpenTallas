`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=1;
always #0.4165 clk=~clk;
wire [12:0] r;
assign r[0]=root;
wire root;
ot_dp_rsync_s2 sync(.clk(clk),.async_rst_n(rst_n),.sync_rst_n(root));
genvar k;
generate for(k=1;k<=12;k=k+1)begin:g
 ot_dp_rrelay relay(.clk(clk),.d(r[k-1]),.q(r[k]));
end endgenerate
integer edge_count=0,rootlow=0,sinklow=0;
always @(posedge clk)begin
 edge_count=edge_count+1;
 if(r[0]===1'b0)rootlow=rootlow+1;
 if(r[12]===1'b0)sinklow=sinklow+1;
end
initial begin
 #0.1;rst_n=0;
 repeat(1)@(negedge clk);rst_n=1;
 repeat(35)@(negedge clk);
 $display("ACTUAL_CELLS relay_depth=12 expected_release_latency=14 root_known_low=%0d sink_known_low=%0d",rootlow,sinklow);
 if(sinklow<2 || sinklow>=14)$fatal(1,"counterexample inconclusive");
 $display("OFFSET_PLUS_SYNC_IS_NOT_ASSERT_WINDOW: depth12 and sync2 yield only %0d low edges",sinklow);
 rootlow=0;sinklow=0;
 @(negedge clk);rst_n=0;
 @(negedge clk);rst_n=1;
 repeat(35)@(negedge clk);
 $display("WARM_RESET root_low=%0d sink_low=%0d",rootlow,sinklow);
 if(sinklow<2 || sinklow>=14)$fatal(1,"warm-reset counterexample inconclusive");
 $finish;
end
endmodule
