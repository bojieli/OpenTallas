`timescale 1ps/1fs
module tb;
  parameter integer D=4;
  parameter integer MUT=0;
  reg clk=0;
  always #416.5 clk=~clk;
  reg [9:0] cw_a=0;
  reg [255:0] cw_d=0;
  reg cw_v=0, epoch=0, rst=1;
  wire [7:0] native_address={cw_a[9:8],cw_a[5:0]};
  wire [267:0] old_packet={epoch,2'b00,cw_v,cw_d,native_address};
  wire [265:0] new_packet={epoch,cw_v,cw_d,native_address};
  reg [267:0] old_pipe[0:D-1];
  reg [265:0] new_pipe[0:D-1];
  reg [D-1:0] valid=0;
  integer i,cycle,checks=0,mismatches=0;
  always @(posedge clk) begin
    valid <= rst ? 0 : {valid[D-2:0],1'b1};
    old_pipe[0] <= old_packet;
    new_pipe[0] <= new_packet ^ (MUT ? 266'b1000000 : 266'b0);
    for(i=1;i<D;i=i+1)begin old_pipe[i]<=old_pipe[i-1];new_pipe[i]<=new_pipe[i-1];end
  end
  initial begin
    for(cycle=0;cycle<4000;cycle=cycle+1) begin
      @(negedge clk);
      if(valid[D-1])begin
        checks=checks+1;
        if({old_pipe[D-1][267],old_pipe[D-1][264:0]} !== new_pipe[D-1]) mismatches=mismatches+1;
      end
      cw_a=$random;
      for(i=0;i<8;i=i+1) cw_d[i*32+:32]=$random;
      cw_v=$random;epoch=$random;
      rst=(cycle%97<5);
    end
    $display("PAYLOAD_MITER D=%0d MUT=%0d checks=%0d mismatches=%0d",D,MUT,checks,mismatches);
    if(checks<3000 || (!MUT && mismatches) || (MUT && !mismatches)) $fatal(1,"miter/control failed");
    $finish;
  end
endmodule
