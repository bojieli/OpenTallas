`timescale 1ns/1ps
module tb_owner128;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0, ready=0;
  reg [127:0] valid=0;
  reg [128*303-1:0] bundles=0;
  wire [127:0] take;
  wire ov; wire [302:0] payload; wire [6:0] index;
  localparam [302:0] OWNED={1'b1,46'h3fedcba98765,256'hf1234567};
  ot_gpu_held_return_merge #(.ENABLE(1),.N(128),.W(303)) dut(
    .clk(clk),.rst_n(rst_n),.in_valid(valid),.in_ready(take),.in_payload(bundles),
    .out_valid(ov),.out_ready(ready),.out_payload(payload),.out_index(index));
  task tick; begin @(posedge clk); #1; end endtask
  integer i;
  initial begin
    bundles[127*303+:303]=OWNED;
    bundles[0+:303]={1'b0,46'h123456789ab,256'h76543210};
    tick(); @(negedge clk); rst_n=1; valid[127]=1;
    tick(); @(negedge clk); valid[0]=1;
    for(i=0;i<4;i=i+1) begin
      tick(); if(!ov || index!==7'd127 || payload!==OWNED || take!==0)
        $fatal(1,"128PC owner46/direction/payload changed under hold");
    end
    @(negedge clk); ready=1; #1;
    if(take!==(128'b1<<127)) $fatal(1,"lost high-index port");
    tick(); @(negedge clk); valid[127]=0; #1;
    if(!ov || index!==0 || take!==128'b1 || payload!==bundles[0+:303])
      $fatal(1,"128PC wrap/source ownership");
    $display("PASS 128PC full owner46 + direction + 32B held return");
    $finish;
  end
endmodule
