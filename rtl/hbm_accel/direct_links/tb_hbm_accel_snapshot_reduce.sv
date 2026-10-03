`timescale 1ns/1ps
module tb_hbm_accel_snapshot_reduce;
 reg clk=0; always #0.416666667 clk=~clk;
 reg rst_n=0,v=0;
 reg [3071:0] data=0;
 wire ov,err; wire [31:0] y;
 reg [31:0] inputs[0:1151],expected[0:11];
 integer count=0,errors=0,cycle=0,issued[0:11];
 string dir;
 ot_hbm_accel_snapshot_reduce #(.ENABLE(1),.LANES(1)) dut(
 .clk(clk),.rst_n(rst_n),.valid_in(v),.data_in(data),.valid_out(ov),.data_out(y),.fault(err));
 always @(posedge clk) cycle<=cycle+1;
 always @(negedge clk) if(ov) begin
 if(y!==expected[count] || err) errors=errors+1;
 $display("HA2_REDUCE case=%0d cycles=%0d got=%08x expected=%08x fault=%0d",count,cycle-issued[count],y,expected[count],err);
 count=count+1;
 end
 initial begin
 if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
 $readmemh({dir,"/inputs.hex"},inputs); $readmemh({dir,"/expected.hex"},expected);
 repeat(4) @(negedge clk); rst_n=1;
 for(integer c=0;c<12;c=c+1) begin
 @(negedge clk); v=1; issued[c]=cycle;
 for(integer r=0;r<96;r=r+1) data[r*32+:32]=inputs[c*96+r];
 end
 @(negedge clk); v=0;
 wait(count==12); @(negedge clk);
 $display("HA2_REDUCE_TERMINAL checks=%0d mismatches=%0d",count,errors);
 if(errors) $fatal(1,"reduction mismatch");
 $finish;
 end
endmodule
