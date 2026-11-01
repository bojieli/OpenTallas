module oldcone(input ck,rst_n,output reg rl0,rl1); always @(posedge ck or negedge rst_n) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end endmodule
module newcone(input ck,rst_n,output reg rl0,rl1); always @(posedge ck) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end   // QC-CORES kit patch (OWNER DECISION 13): rst_n = synchronous registered input; 2-stage synchronous relay, same release depth
endmodule
module tb;
reg ck=0;always #5 ck=~ck;
reg rst_n=1;wire a0,a1,b0,b1;reg baddepth=0;integer errs=0,wrong=0;
oldcone a(ck,rst_n,a0,a1);newcone b(ck,rst_n,b0,b1);
always @(posedge ck) if(!rst_n)baddepth<=0;else baddepth<=1;
initial begin
 @(negedge ck);rst_n=0;
 repeat(64)begin @(posedge ck);#1;if({a0,a1}!=={b0,b1})errs=errs+1;end
 @(negedge ck);rst_n=1;
 repeat(12)begin @(posedge ck);#1;if({a0,a1}!=={b0,b1})errs=errs+1;if(baddepth!==b1)wrong=wrong+1;end
 if(errs || wrong!=1)$fatal(1,"legal boot mismatch %d wrongdepth caught %d",errs,wrong);
 @(negedge ck);#1;rst_n=0;#1;
 if(a1!==0 || b1!==1)$fatal(1,"short-reset negative control escaped");
 rst_n=1;
 $display("PASS legal64boot lockstep; same2edge release; wrongdepth caught1; shortreset caught");
 $finish;
end
endmodule
