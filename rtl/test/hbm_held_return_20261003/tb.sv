`timescale 1ns/1ps
module tb;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0, ready=0;
  reg [2:0] valid=0;
  reg [3*292-1:0] data=0;
  wire [2:0] taken;
  wire offered;
  wire [291:0] payload;
  wire [1:0] index;
  wire [2:0] disabled_ready; wire disabled_valid;
  wire [291:0] disabled_data; wire [1:0] disabled_index;
  ot_gpu_held_return_merge #(.ENABLE(1),.N(3),.W(292)) dut(
    .clk(clk),.rst_n(rst_n),.in_valid(valid),.in_ready(taken),.in_payload(data),
    .out_valid(offered),.out_ready(ready),.out_payload(payload),.out_index(index));
  ot_gpu_held_return_merge #(.N(3),.W(292)) disabled(
    .clk(clk),.rst_n(rst_n),.in_valid(valid),.in_ready(disabled_ready),.in_payload(data),
    .out_valid(disabled_valid),.out_ready(ready),.out_payload(disabled_data),.out_index(disabled_index));
  task edge_tick; begin @(posedge clk); #1; end endtask
  task check(input bit ok, input string message);
    begin if (!ok) $fatal(1,"%s",message); end
  endtask
  integer i, transactions;
  reg [291:0] captured;
  initial begin
    // Every bundle includes high tag/owner/direction bits: not a low-tag fixture.
    data[0*292+:292]={36'hf12345678,256'h10};
    data[1*292+:292]={36'h812345679,256'h20};
    data[2*292+:292]={36'hfabcdef01,256'h30};
    edge_tick(); @(negedge clk); rst_n=1; valid=3'b100;
    edge_tick(); captured=payload;
    check(index==2 && offered,"initial held offer");
    @(negedge clk); valid=3'b111;
    for(i=0;i<8;i=i+1) begin
      edge_tick(); check(offered && payload===captured && index==2 && taken==0,"late arrivals changed held tuple");
    end
    @(negedge clk); ready=1; #1;
    check(taken==3'b100,"accepted wrong input");
    edge_tick(); @(negedge clk); valid=3'b011; #1;
    check(index==0 && taken==3'b001,"round-robin wrap");
    edge_tick(); @(negedge clk); valid=3'b010; #1;
    check(index==1 && taken==3'b010,"second ready source");
    edge_tick(); @(negedge clk); valid=0; #1;
    check(!offered && taken==0,"phantom completion");
    // One accepted transaction per clock, all three sources permanently valid.
    valid=3'b111; transactions=0;
    for(i=0;i<12;i=i+1) begin
      #1; check(index==(i+2)%3 && taken==(3'b001<<((i+2)%3)),"fair full-rate ordering");
      transactions=transactions+1; edge_tick(); @(negedge clk);
    end
    ready=0; edge_tick();
    @(negedge clk); rst_n=0; #1;
    check(!offered && taken==0,"reset must not accept"); edge_tick();
    @(negedge clk); valid=3'b010; rst_n=1; #1;
    check(index==1 && offered,"fresh reset selection");
    check(disabled_ready==0 && !disabled_valid && disabled_data==0 && disabled_index==0,"default-off not inert");
    $display("PASS held full-width merge late-arrival/backpressure/wrap/reset/defaultoff transactions=%0d",transactions);
    $finish;
  end
endmodule
